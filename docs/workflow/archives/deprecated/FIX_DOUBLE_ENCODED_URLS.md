# Fix: Doublons de Téléchargement (URLs Double-Encodées)
> Ce correctif fait partie du monitoring des téléchargements et de la normalisation des URLs ; pour une vue d'ensemble, voir également [MONITORING_TELECHARGEMENTS_SOURCES.md](MONITORING_TELECHARGEMENTS_SOURCES.md).
> **Niveau : avancé** — Ce document est principalement destiné au debug approfondi et à l’historique des correctifs. Pour une vue d’ensemble, voir d’abord le document pivot correspondant.

**Date:** 2025-10-27
**Version:** v2.2.1
**Statut:** ✅ Résolu

## Problème Identifié

### Symptômes Observés

L'UI affichait systématiquement **2 événements pour chaque téléchargement** :
1. Un téléchargement **réussi** avec le nom du fichier (ex: `259_Camille.zip`)
2. Un téléchargement **échoué** avec l'erreur `400 Client Error: Bad Request`

```
2025-10-27 10:56:35 - 259_Camille.zip - Statut: completed
2025-10-27 10:55:42 - Détermination en cours... - Statut: failed (Erreur réseau: 400 Bad Request)
```

### Cause Racine

Le JSON source externe contenait des **URLs double-encodées** :

```json
{
  "url": "https://www.dropbox.com/scl/fo/...?amp%3Bdl=0&dl=1&rlkey=...",
  "timestamp": "2025-10-27 11:04:16"
}
```

**Séquence double-encodée:** `amp%3Bdl=0`
- `amp%3B` représente `&` (double-encodé)
- Résultat: paramètre malformé `&dl=0` qui cause une erreur HTTP 400

Le système voyait ces URLs comme **différentes** de la version propre :
```
https://www.dropbox.com/scl/fo/...?dl=1&rlkey=...
```

Cela déclenchait **2 téléchargements** :
1. **Malformé** (`amp%3Bdl=0&dl=1`) → échoue avec erreur 400
2. **Propre** (`dl=1`) → réussit

## Solution Implémentée

### 1. Amélioration de la Normalisation d'URL

**Fichier:** `services/csv_service.py` - Méthode `_normalize_url()`

**Ajouts clés :**
- `html.unescape()` pour supprimer les entités HTML (`&amp;` → `&`).
- Décodage récursif avant parsing pour neutraliser les séquences double-encodées.

```python
# Pre-process: recursively decode double-encoded sequences
prev_url = None
max_decode_iterations = 3
iteration = 0
while prev_url != raw and iteration < max_decode_iterations:
    prev_url = raw
    # Decode common double-encoded patterns (HTML entity codes)
    if 'amp%3B' in raw or 'amp%3b' in raw:
        raw = raw.replace('amp%3B', '&').replace('amp%3b', '&')
    # Detect and clean malformed ampersands
    if '%3B' in raw or '%3b' in raw:
        try:
            decoded = urllib.parse.unquote(raw)
            if '://' in decoded:
                raw = decoded
        except Exception:
            pass
    iteration += 1
```

**Résultat:** Les URLs malformées et propres normalisent vers la **même URL canonique**, même lorsque la source transmet des entités HTML.

### 2. Worker Aligné sur la Normalisation

**Fichier:** `app_new.py` — `execute_csv_download_worker()`

- Reconstruit désormais tous les liens directs Dropbox (`?dl=1`) à partir de l'URL normalisée fournie par `CSVService._normalize_url()`.
- Empêche toute réintroduction de paramètres `dl` dupliqués lors de la construction finale de l'URL.

### 3. Tests Ajoutés

#### Tests Unitaires
**Fichier:** `tests/unit/test_csv_service_url_normalization.py`

Nouveaux tests couvrant :
- `test_normalize_double_encoded_urls()` - Cas réels du bug
- `test_normalize_various_double_encoded_patterns()` - Variations
- `test_history_dedup_with_double_encoded_urls()` - Déduplication dans l'historique

```bash
source env/bin/activate
pytest tests/unit/test_csv_service_url_normalization.py -v
# ✓ 5 passed
```

#### Tests d'Intégration
**Fichier:** `tests/integration/test_double_encoded_urls.py`

- `test_double_encoded_urls_no_duplicate_download()` - Vérifie que les variantes malformées/propres issues du webhook ne déclenchent qu'un seul worker.
- `test_csv_monitoring_dedup_across_batches()` - Détecte les doublons entre cycles successifs.
- `test_real_world_urls_from_history()` - Valide les URLs des lignes 514-529 de `download_history.json`.

### 3. Utilitaire de Nettoyage

**Fichier:** `scripts/clean_download_history.py`

Script pour nettoyer l'historique existant :

```bash
# Aperçu des doublons
python scripts/clean_download_history.py --dry-run

# Nettoyage effectif (crée une sauvegarde)
python scripts/clean_download_history.py
```

**Résultats sur le projet :**
- Entrées originales: **132**
- Entrées uniques: **123**
- **9 doublons supprimés**

## Impact

### Avant le Fix

- ❌ Chaque téléchargement générait 2 entrées dans l'historique
- ❌ 1 erreur HTTP 400 affichée par téléchargement
- ❌ Confusion utilisateur (statut "failed" alors que le téléchargement réussit)
- ❌ Pollution de l'historique et des logs

### Après le Fix

- ✅ 1 seule entrée par téléchargement unique
- ✅ Pas d'erreur HTTP 400 pour les URLs normalisées
- ✅ UI cohérente : 1 événement = 1 téléchargement
- ✅ Historique propre (9 doublons supprimés)

## Fichiers Modifiés

| Fichier | Modifications |
|---------|---------------|
| `services/csv_service.py` | Amélioration `_normalize_url()` avec décodage récursif |
| `tests/unit/test_csv_service_url_normalization.py` | +3 nouveaux tests pour double-encodage |
| `tests/integration/test_double_encoded_urls.py` | Nouveaux tests d'intégration |
| `scripts/clean_download_history.py` | Nouvel utilitaire de nettoyage |
| `docs/workflow/DOWNLOAD_HISTORY_MANAGEMENT.md` | Documentation v2.2.0 |
| `download_history.json` | Nettoyé (132 → 123 entrées) |

## Prévention Future

### Déduplication au Démarrage

La fonction `_normalize_and_deduplicate_history()` s'exécute automatiquement au démarrage de l'application pour nettoyer les doublons existants.

### Normalisation à la Source

Tous les points d'entrée d'URLs utilisent maintenant `_normalize_url()` :
- Ajout à l'historique (`add_to_download_history_with_timestamp`)
- Vérification de téléchargement (`is_url_downloaded`)
- Monitoring CSV/Webhook/Airtable (`_check_csv_for_downloads`)

### Tests de Régression

Les tests unitaires incluent maintenant les **cas réels** du bug pour éviter les régressions.

## Recommandations

1. **Valider la source JSON externe** pour éviter les URLs mal encodées à l'avenir
2. **Exécuter le script de nettoyage** périodiquement si le problème persiste
3. **Monitorer les logs** pour détecter des patterns similaires (erreurs 400 systématiques)

## Références

- Issue: URLs double-encodées dans `download_history.json` (lignes 514-529)
- Commit: `fix(services): décodage récursif URLs double-encodées (v2.2.0)`
- Tests: `pytest tests/unit/test_csv_service_url_normalization.py tests/integration/test_double_encoded_urls.py`
