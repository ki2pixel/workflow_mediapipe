# Monitoring des Téléchargements - Source Webhook (Architecture v4.1)

## Objectif

Ce document décrit l'architecture simplifiée du monitoring des téléchargements utilisant exclusivement une source Webhook externe. Cette approche remplace les anciennes sources multiples (MySQL, Airtable, CSV) par une solution unifiée et maintenable.

## Architecture Webhook-Only

### Changement majeur (v4.1)
Le système a migré vers une architecture **Webhook-only** pour simplifier la maintenance et améliorer la fiabilité :

- ❌ **Plus de MySQL** : Base de données locale supprimée
- ❌ **Plus d'Airtable** : Service externe déprécié
- ❌ **Plus de CSV monitoring** : Fichiers locaux remplacés
- ✅ **Webhook unique** : Source JSON centralisée

### Configuration Requise

Variables d'environnement essentielles :
```bash
# Configuration Webhook (obligatoire)
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/data/webhook_links.json
WEBHOOK_MONITOR_INTERVAL=15
WEBHOOK_CACHE_TTL=60
WEBHOOK_TIMEOUT=10

# Variables obsolètes (ne plus utiliser)
# USE_MYSQL=true          # Supprimé
# USE_AIRTABLE=true        # Supprimé  
# USE_WEBHOOK=true         # Supprimé (webhook est maintenant par défaut)
# CSV_MONITOR_URL=...      # Supprimé
# CSV_MONITOR_INTERVAL=... # Supprimé
```

## Source de Données

Le système utilise exclusivement une source Webhook externe JSON pour le monitoring des téléchargements.

### Caractéristiques du Webhook

- **Format JSON** : Données structurées et faciles à parser
- **Cache TTL** : Mise en cache pour éviter les requêtes excessives
- **Retry automatique** : Gestion des erreurs réseau
- **Classification URLs** : Dropbox (auto-download), proxy PHP (auto-download), autres sources (ignorées)

### Services Impliqués

1. **WebhookService** (`services/webhook_service.py`)
   - Communication avec le endpoint Webhook
   - Gestion du cache et des retries
   - Validation des données reçues

2. **CSVService** (`services/csv_service.py`)
   - Interface vers le monitoring (nom historique conservé)
   - Normalisation des URLs et déduplication
   - Gestion de l'historique des téléchargements

3. **WorkflowState** (`services/workflow_state.py`)
   - Suivi de l'état des téléchargements
   - Intégration avec le workflow principal

### Références

- Documentation complète : [WEBHOOK_INTEGRATION.md](WEBHOOK_INTEGRATION.md)
- Gestion de l'historique : [DOWNLOAD_HISTORY_MANAGEMENT.md](DOWNLOAD_HISTORY_MANAGEMENT.md)

## Historique des téléchargements

L’historique des téléchargements est stocké dans `download_history.json` au format structuré :

- `{ "url": str, "timestamp": "YYYY-MM-DD HH:MM:SS" }` (heure locale)
- Données triées chronologiquement, puis par URL pour stabilité.

Points clés (voir `DOWNLOAD_HISTORY_MANAGEMENT.md` et `FIX_DOUBLE_ENCODED_URLS.md`) :

- Normalisation avancée des URLs (`CSVService._normalize_url()`)
- Migrer les anciens formats via `migrate_history_to_local_time()`
- Éviter les doublons même en présence d’URLs HTML‑échappées ou doublement encodées

## DRY_RUN_DOWNLOADS

En environnement de test et d'intégration continue, le paramètre `DRY_RUN_DOWNLOADS=true` est obligatoire pour prévenir tout téléchargement réel. Ce mécanisme garantit que les tests s'exécutent de manière sécurisée, sans effet de bord sur les environnements de production ou de développement.

### Comportement en mode DRY_RUN

- **Aucun téléchargement** n'est effectué sur le système de fichiers
- Les URLs sont validées mais non traitées
- Les logs indiquent clairement le mode de simulation
- ⚠️ **Note importante** : En mode DRY_RUN, les URLs détectées sont tout de même ajoutées à l'historique des téléchargements pour éviter les doublons lors d'une exécution réelle. Ce comportement garantit qu'une URL n'est pas ignorée en production sous prétexte qu'elle a été vue en mode test.

### Configuration des tests

Les tests unitaires et d'intégration sont configurés pour utiliser ce mode par défaut. Pour plus de détails sur la stratégie de test, consultez [TESTING_STRATEGY.md](TESTING_STRATEGY.md).

## Flux de Monitoring Mise à Jour

Le monitoring utilise la fonction `_check_csv_for_downloads()` (@services/csv_service.py#731-905) qui implémente la logique suivante :

### 1. Classification des URLs

Chaque URL récupérée du Webhook est classifiée selon `url_type` :

```python
# Détermination automatique du type d'URL
url_type = (
    str(row.get('url_type') or '').strip().lower()
    or (
        'dropbox' if (_is_dropbox_url(url) or _is_dropbox_proxy_url(url) or provider_lower == 'dropbox') else 'external'
    )
)
```

### 2. Conditions de Téléchargement Automatique

Le téléchargement automatique n'est activé que pour les URLs Dropbox-like avec les conditions suivantes :

```python
# Vérification si le téléchargement automatique est autorisé
is_dropbox_like = (
    url_type == 'dropbox'
    or provider_lower == 'dropbox'
    or _is_dropbox_url(url)
    or _is_dropbox_proxy_url(url)
)

has_new_schema_hints = bool(
    (original_filename and str(original_filename).strip())
    or (fallback_url and str(fallback_url).strip())
    or _is_dropbox_proxy_url(url)  # Détection des proxies R2
)

auto_download_allowed = (
    is_dropbox_like
    and _looks_like_archive_download(url, original_filename)
    and has_new_schema_hints
)
```

### 3. Comportement par Type d'URL

- **Dropbox + Proxy PHP** : Téléchargement automatique + popup "Téléchargement Terminé"
- **Autres fournisseurs (externes, etc.)** : Ignorés (aucune entrée UI, aucun téléchargement)

### 3.1. Détection des URLs Proxy (v4.2)

Le système inclut désormais des fonctions de détection avancées pour les URLs Dropbox via proxy :

```javascript
// Frontend - static/csvWorkflowPrompt.js
function isDropboxProxyUrl(rawUrl) {
    try {
        const url = new URL(rawUrl);
        return url.hostname.includes('r2proxy') && 
               url.pathname.includes('/dropbox/');
    } catch {
        return false;
    }
}

function isDropboxLikeDownload(download) {
    return isDropboxUrl(download.original_url) || 
           isDropboxProxyUrl(download.original_url);
}
```

**Points clés de la détection** :
- **Proxy R2** : Détection automatique des URLs `*.r2proxy.*/dropbox/*`
- **Frontend unifié** : Les mêmes fonctions de détection sont utilisées dans le popup et le monitoring
- **Cache-busting** : Les URLs proxy incluent un paramètre `_STATIC_CACHE_BUSTER` pour éviter les caches intermédiaires

### 4. Historique des Téléchargements

Les URLs sont ajoutées à l'historique uniquement lorsqu'elles sont réellement traitées (ou simulées en DRY RUN) :

```python
# Ajout à l'historique (URL primaire + fallback si présent) uniquement en DRY RUN
# ou après succès réel dans execute_csv_download_worker().
CSVService.add_to_download_history_with_timestamp(norm_url, timestamp_str)
if norm_fallback_url:
    CSVService.add_to_download_history_with_timestamp(norm_fallback_url, timestamp_str)
```

#### Exceptions introduites en 2026-01-09

- Les liens **non éligibles** (hors Dropbox/proxy R2 ou ne satisfaisant pas les heuristiques) sont ignorés et ne doivent pas impacter les réessais.
- Seuls deux cas écrivent désormais dans l’historique :
  1. Mode `DRY_RUN_DOWNLOADS=true`, pour simuler le comportement réel sans toucher au disque.
  2. Téléchargement réel réussi (exécuté par `execute_csv_download_worker()`).
- `_is_url_already_tracked()` s’appuie sur `WorkflowState` pour éviter de lancer un nouveau worker lorsque l’URL est déjà active/terminée. Les statuts `failed`, `cancelled` et `unknown_error` sont ignorés pour autoriser un réessai.
- `_check_csv_for_downloads()` tient à jour un set `handled_in_this_pass` (URL primaire/fallback) afin qu’une même itération du monitor ne spawn pas plusieurs workers identiques.

### 5. Synthèse Opérationnelle (Webhook only)

- **Source unique** : `WebhookService.fetch_records()` fournit la totalité des entrées surveillées ; aucune lecture MySQL/Airtable/CSV n’est conservée dans le code.
- **Auto-download contrôlé** : la logique `_looks_like_archive_download()` + `has_new_schema_hints` garantit que seuls les paquets Dropbox conformes (original_filename/fallback_url ou proxy `/dropbox/`) peuvent déclencher `execute_csv_download_worker()`. Tout lien hors scope est ignoré.
- **Historique structuré** : `CSVService.save_download_history()` persiste uniquement les URLs véritablement traitées afin d’éviter les faux positifs et d’autoriser les réessais pilotés par Webhook sur les entrées en échec.

## Sécurité et Validation

### Protection des Téléchargements

- **Validation des domaines** : Seules les URLs Dropbox (directes ou proxy R2) peuvent déclencher un téléchargement.
- **Nettoyage des URLs** : Échappement et normalisation des caractères spéciaux
- **Protection contre les doublons** : Détection des URLs similaires ou doublement encodées

### Journalisation et Audit

- Toutes les tentatives de téléchargement sont journalisées
- Les erreurs sont enregistrées avec un niveau de sévérité approprié
- Les journaux incluent des métadonnées pour le débogage

### Conformité

- Respect des bonnes pratiques de sécurité OWASP
- Journalisation des activités sensibles
- Protection contre les attaques par injection

Pour plus de détails sur les mécanismes de sécurité, consultez [SECURITY.md](SECURITY.md).

## Pour aller plus loin

- `INTEGRATION_AIRTABLE.md` — guide complet Airtable
- `WEBHOOK_INTEGRATION.md` — service Webhook JSON externe
- `DOWNLOAD_HISTORY_MANAGEMENT.md` — format et gestion d’historique
- `FIX_DOUBLE_ENCODED_URLS.md` — résolution des doublons liés aux URLs doublement encodées
