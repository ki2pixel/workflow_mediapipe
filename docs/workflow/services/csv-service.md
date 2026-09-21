# CSV Service Documentation

> [!NOTE]
> Depuis l'audit du 2026-09-21 (`docs/audits/audit_telechargement_r2.md`), les téléchargements sont
> **repris via `.part` + `Range`**, **validés** (rejet des pages HTML/JSON servies en 200), typés
> (`DownloadResult.error_kind`) et suivis dans la table `download_failures` avec un cooldown exponentiel.
> Les copies R2 côté worker sont **éphémères** : le repli sur `source_url` (Dropbox) est le chemin nominal
> pour toute archive non récupérée le jour même.

## TL;DR
Le CSV Service gère la surveillance et le téléchargement automatique des archives depuis le webhook, avec
normalisation d'URL pour éviter les doublons, filtrage strict des téléchargements automatiques (sources
Dropbox / proxy worker R2) et repli automatique sur le lien Dropbox d'origine.

## Contexte Métier
Le service traite des flux de données CSV provenant de webhooks externes, contenant des URLs de fichiers multimédia (vidéos, audio). Le défi principal est de détecter les nouveaux téléchargements éligibles tout en évitant les doublons dus aux variations d'URLs (encodage HTML, paramètres query, etc.).

## Architecture Service

### Responsabilités
- Surveillance des données CSV webhook
- Normalisation d'URLs pour déduplication
- Téléchargement automatique sélectif (Dropbox uniquement)
- Gestion historique des téléchargements

### Fonctions Clés

#### `_normalize_url(url: str) -> str` (Complexité F)
**Rôle** : Normalise les URLs pour prévenir les doublons dus aux variations mineures.

**Algorithme détaillé** :
1. **Nettoyage initial** : Trim espaces, unescape HTML entities (`&amp;` → `&`)
2. **Décodage récursif** : Gestion des double-encodages (`amp%3B` → `&`) avec limite d'itérations (3 max)
3. **Parsing URL** : Séparation scheme/netloc/path/query/fragment
4. **Normalisation composants** :
   - Scheme/netloc en minuscules
   - Suppression ports par défaut (80/443)
   - Tri paramètres query par clé/valeur
   - Suppression paramètres vides
5. **Gestion spéciale Dropbox** : Consolidation paramètres `dl=1`, suppression doublons
6. **Finalisation** : Suppression trailing slash, ré-encodage path sécurisé

**Edge cases gérés** :
- URLs double-encodées (`amp%3Bdl=0&dl=1`)
- Paramètres malformés (`?amp%3Bdl=0&dl=1`)
- Encodage HTML dans CSV (`&amp;dl=1`)
- Variations ports/casse dans hostnames

#### `check_csv_for_downloads() -> None` (Complexité F) — `services/csv_monitor.py`
**Rôle** : Analyse les enregistrements du webhook pour identifier les nouveaux téléchargements éligibles.
(`CSVService._check_csv_for_downloads()` reste un simple wrapper de compatibilité pour les tests.)

**Logique de filtrage** :
1. **Validation base** : URL présente, non déjà trackée, scheme HTTP/HTTPS
2. **Détermination type URL** :
   - `dropbox` : Hostnames Dropbox ou proxy workers.dev
   - `fromsmash`/`swisstransfer` : Domaines spécifiques
   - `external` : Autres
3. **Critères auto-download** :
   - Type Dropbox-like uniquement
   - Ressemble à une archive (`.zip`, `/scl/fo/`, filename `.zip`)
   - Présence hints nouveau schéma (`original_filename`, `fallback_url`, proxy URL)
4. **Cooldown des échecs** : une URL présente dans `download_failures` est ignorée pendant
   `min(15 s × 2^(tentatives-1), DOWNLOAD_COOLDOWN_MAX_S)` avant nouvel essai

**Stratégies anti-duplication** :
- Normalisation URL avec `_normalize_url`
- Comparaison avec l'historique existant
- Gestion des URLs de fallback
- Tracking des URLs traitées par passe

#### Chaîne de téléchargement (`services/csv_downloader.py` → `services/download_service.py`)
1. `r2_url` (proxy worker) est tenté en premier, `source_url` (Dropbox) sert de repli — et passe en premier
   si le R2 est déjà connu comme manquant (`error_kind='not_found'` enregistré).
2. `DownloadService.download_dropbox_file()` écrit dans `<nom>.part`, reprend via HTTP `Range`, et ne renomme
   en `<nom>.zip` qu'après contrôle de taille **et** validation ZIP (rejet des pages HTML/JSON en 200).
3. `DownloadResult.error_kind` ∈ `not_found | auth | http_error | network | stalled | invalid_payload |
   incomplete | local_io`, avec `status_code`, `attempts`, `resumed_from`.
4. Succès → historique (`download_history`) + purge de `download_failures` ; échec définitif →
   `download_failures` + message UI.

## Gestion Erreurs

### Cas d'échec normalisation URL
- **Comportement** : Retour URL vide silencieusement
- **Logging** : Aucun (fonction utilitaire)

### Erreurs parsing CSV
- **Comportement** : Skip ligne problématique, continue traitement
- **Logging** : Debug level pour diagnostics

### Échecs téléchargement
- **Comportement** : Thread daemon, échec isolé, reprise possible au cycle suivant (`.part` conservé)
- **Typage** : `error_kind` + `status_code` ; un objet R2 expiré (`not_found`) bascule immédiatement sur Dropbox
- **Logging** : `CSV DOWNLOAD: R2_MISSING …` (WARNING), `DOWNLOAD [CSV-DL-…]: … FAILED after N attempt(s)` (ERROR)

## Optimisations Performance

### Cache in-memory
- `_LAST_KNOWN_HISTORY_SET` : Backup en cas d'erreur lecture DB
- Évite bursts sur erreurs transitoires

### Tri paramètres query
- Normalisation canonique pour hash maps efficaces
- Comparaisons O(1) dans historique

### Décodage limité
- Maximum 3 itérations pour éviter boucles infinies
- Protection contre URLs malicieuses

## Trade-offs

### ❌ Normalisation agressive vs ❌ Précision sémantique
- **Choix** : Normalisation agressive (tri params, suppression ports) pour déduplication robuste
- **Coût** : URLs sémantiquement différentes peuvent être considérées identiques
- **Bénéfice** : Prévention doublons fiables dans historique grandissant

### ❌ Auto-download restrictif vs ❌ Commodité utilisateur
- **Choix** : Restriction Dropbox + archives uniquement
- **Coût** : Téléchargements manuels requis pour autres sources
- **Bénéfice** : Contrôle backlog, prévention abus

### ❌ Complexité code vs ❌ Maintenabilité
- **Choix** : Logique centralisée dans fonctions complexes
- **Coût** : Tests unitaires lourds, debugging difficile
- **Bénéfice** : Cohérence traitement, edge cases couverts

## Golden Rule
**Toute modification de logique normalisation doit être accompagnée de migration historique complète** pour éviter inconsistances entre anciennes et nouvelles URLs normalisées.

## Configuration Essentielle

### Variables d'Environnement

```bash
# Source de données
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/webhook_proxy.php
WEBHOOK_TIMEOUT=10
WEBHOOK_CACHE_TTL=60
WEBHOOK_MONITOR_INTERVAL=15

# Fiabilité des téléchargements (cf. .env.example sections 13 et 14)
DOWNLOAD_MAX_ATTEMPTS=3
DOWNLOAD_CHUNK_TIMEOUT_S=60          # watchdog de stall
DOWNLOAD_VALIDATE_ZIP=true
DOWNLOAD_PROGRESS_MIN_INTERVAL_S=1.0
DOWNLOAD_COOLDOWN_MAX_S=3600

# Sécurité / divers
DRY_RUN_DOWNLOADS=false
DISABLE_EXPLORER_OPEN=1

# Métriques système (widget CPU/GPU/RAM)
SYSTEM_SNAPSHOT_INTERVAL_S=2.0
SLOW_API_THRESHOLD_MS=1000
```

### Configuration Webhook

```python
# config/settings.py
webhook_config = {
    'url': os.environ.get('WEBHOOK_JSON_URL'),
    'timeout': int(os.environ.get('WEBHOOK_TIMEOUT', '10')),
    'cache_ttl': int(os.environ.get('WEBHOOK_CACHE_TTL', '60')),
    'monitor_interval': int(os.environ.get('WEBHOOK_MONITOR_INTERVAL', '15')),
}
```

## Résolution de Problèmes

### Objets R2 manquants (404) côté worker

```bash
# Diagnostic : liste les r2_url indisponibles (lecture seule, aucune écriture)
python scripts/check_r2_objects.py --show-ok

# Interprétation
# - Les copies R2 sont éphémères : seuls les objets récents répondent 200.
# - Une archive [EN ATTENTE] manquante est récupérée automatiquement via le lien Dropbox
#   (message UI « R2 absent - repli Dropbox utilisé »).
# - Une archive [déjà traité] en 404 est normale (objet expiré après récupération).
```

### Téléchargement interrompu / repris

```bash
ls -la ~/Téléchargements/*.part          # reliquat conservé pour la reprise
grep "resuming at" logs/app.log          # la reprise repart de l'octet atteint
grep "R2_MISSING\|FAILED after" logs/app.log
```

### Webhook Indisponible

```bash
# Diagnostic
curl -s "$WEBHOOK_JSON_URL"

# Solutions
# 1. Vérifier la connectivité réseau
# 2. Vérifier WEBHOOK_JSON_URL (.env)
```

### SQLite Corrompu

```bash
# Diagnostic
python -c "import sqlite3; sqlite3.connect('download_history.sqlite3').tables"

# Solution
# Recréer la base de données
python scripts/migrate_download_history_to_sqlite.py
```

### Fichiers CSV Corrompus

```bash
# Diagnostic
python -c "import csv; csv.reader(open('data.csv'))"

# Solution
# Le système ignore les lignes invalides et continue
# Logs détaillés pour identification
```

### Permissions Insuffisantes

```bash
# Diagnostic
ls -la download_history.sqlite3
sudo chown $USER:$USER download_history.sqlite3
chmod 644 download_history.sqlite3

# Solution
# Utiliser l'environnement principal avec permissions appropriées
source env/bin/python
# Le service utilise les permissions de l'utilisateur courant
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer fichiers test
mkdir -p test_csv/docs
echo "url,status,timestamp" > test.csv
echo "https://dl.dropbox.com/s/file1.mp4,downloaded,2024-01-20T14:30:22" >> test.csv

# Exécuter monitoring
source env/bin/activate
cd test_csv
python ../workflow_scripts/step7/csv_monitor.py

# Vérifier résultats
sqlite3 download_history.sqlite3 "SELECT COUNT(*) FROM downloads"
ls -la archives/
```

### Validation Automatique

```python
def validate_csv_service():
    """Validation complète du service CSV"""
    # Vérifier la connexion SQLite
    # Vérifier la configuration webhook
    # Tester la normalisation URLs
    # Valider les patterns CSV
    # Vérifier la persistance SQLite
    return True
```

## Intégration Pipeline

### Position dans l'Architecture

```mermaid
graph LR
    A[STEP4 Audio] --> B[STEP5 Tracking]
    B --> C[STEP6 Réduction]
    C --> D[STEP7 Pré-traitement AE]
    D --> E[STEP8 Finalisation]
    
    subgraph "Monitoring"
        F[Webhook JSON] --> G[CSVService]
        H[SQLite Repository]
        I[WorkflowState]
    end
```

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("CSV_MONITOR", "running")
ws.set_step_field("CSV_MONITOR", "webhook_available", True)
ws.update_step_progress("CSV_MONITOR", current=25, total=100)
```

### Flux de Données

```python
# Webhook → CSVService → SQLite → WorkflowState
webhook_records → csv_service.monitor_csv_downloads() → csv_service._persist_download_result() → ws.set_step_field()
```</content>
<parameter name="path">/home/kidpixel/workflow_mediapipe/docs/workflow/services/csv_service.md