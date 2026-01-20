# Intégration Source Webhook - Workflow MediaPipe v4.1
> Pour une vue d'ensemble du monitoring des téléchargements, voir également [MONITORING_TELECHARGEMENTS_SOURCES.md](MONITORING_TELECHARGEMENTS_SOURCES.md).

## Vue d'ensemble

L'intégration Webhook est la **source unique de données** pour le monitoring des téléchargements. Elle fournit une source de données JSON externe simple et flexible qui démarre automatiquement avec l'application.

### Avantages de l'Intégration Webhook

- **🔗 Flexibilité** : Source de données externe configurable via URL
- **⚡ Simplicité** : Pas de serveur de base de données requis
- **🛡️ Sécurité** : Accès contrôlé via proxy PHP optionnel
- **📊 Cache intelligent** : TTL configurable pour optimiser les performances
- **🔄 Robustesse** : Retry automatique et gestion d'erreurs avancée

## Configuration Requise

### 1. Structure JSON Requise

Votre endpoint Webhook doit retourner un tableau JSON avec cette structure :

```json
[
  {
    "source_url": "https://www.dropbox.com/scl/fo/...&dl=1",
    "r2_url": "https://server.example.workers.dev/dropbox/<bucket>/<object>/file",
    "provider": "dropbox",
    "created_at": "2026-01-08T20:19:38+00:00",
    "original_filename": "61 Camille.zip"
  },
  {
    "url": "https://fromsmash.com/...",
    "timestamp": "2025-10-17T12:35:00+0200",
    "source": "webhook"
  }
]
```

**Champs requis :**

**Nouveau format (recommandé) :**
- `source_url` : URL d'origine (string)
- `r2_url` : URL clonée directement téléchargeable (string, optionnel)
- `provider` : Identifiant de source (ex: `dropbox`) (string)
- `created_at` : Horodatage ISO 8601 (string)
- `original_filename` : Nom de fichier d'origine (ex: `61 Camille.zip`) (string)

**Format legacy (toujours supporté) :**
- `url` : URL de téléchargement (string)
- `timestamp` : Horodatage ISO 8601 ou format MySQL (string)
- `source` : Identifiant de la source (optionnel, défaut "webhook")

### Priorité de téléchargement & renommage

- Le système **priorise** `r2_url` si présent (souvent plus rapide), sinon utilise `source_url`.
- Si `r2_url` échoue, il y a un **fallback** automatique sur `source_url` pour la même entrée.
- Le champ `original_filename` est utilisé pour **forcer le nom final** du fichier téléchargé.
  Cela évite des noms génériques (ex: `file.zip`, `dropbox_<...>.zip`) et préserve les mots-clés attendus par STEP1 (ex: `Camille`).

### 2. Variables d'Environnement

Ajoutez ces variables à votre fichier `.env` :

```bash
# URL de l'endpoint JSON externe (source unique)
WEBHOOK_JSON_URL=https://your-domain.com/api/downloads

# Configuration du cache (secondes)
WEBHOOK_CACHE_TTL=300

# Timeout des requêtes (secondes)
WEBHOOK_TIMEOUT=30

# Intervalle de monitoring (secondes)
WEBHOOK_MONITOR_INTERVAL=15
```

### 3. Proxy PHP Optionnel (Sécurité)

Pour les environnements de production, utilisez un proxy PHP pour contrôler l'accès :

```php
// proxy.php
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$url = getenv('WEBHOOK_JSON_URL') ?: 'https://internal-api.example.com/downloads';
$context = stream_context_create([
    'http' => [
        'timeout' => 30,
        'user_agent' => 'Workflow-MediaPipe/4.1'
    ]
]);

$data = file_get_contents($url, false, $context);
if ($data === false) {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to fetch data']);
    exit;
}

echo $data;
?>
```

Configuration :
```bash
WEBHOOK_JSON_URL=https://your-proxy.com/proxy.php
```

## Installation et Déploiement

### 1. Activation du Service

```bash
# Démarrage avec intégration Webhook (configuration par défaut)
export WEBHOOK_JSON_URL=https://your-api.com/downloads
python app_new.py
```

Le service Webhook est la source unique de données pour le monitoring des téléchargements. Aucun flag `USE_WEBHOOK` n'est requis ; le système utilise automatiquement le webhook configuré via `WEBHOOK_JSON_URL`.

### 2. Validation de l'Installation

```bash
# Test de la configuration
python -c "
from services.webhook_service import fetch_records, get_service_status
data = fetch_records()
print('Status:', get_service_status())
print('Records:', len(data) if data else 0)
"
```

### 3. Test via API

```bash
# Test de l'endpoint
curl http://localhost:5000/api/csv_monitor_status

# Réponse attendue
{
  "data_source": "webhook",
  "monitor_interval": 15,
  "webhook": {
    "available": true,
    "last_fetch_ts": "2025-10-17 13:24:13",
    "error": null,
    "records_processed": 5
  },
  "csv_monitor": {
    "status": "inactive",
    "last_check": null,
    "error": "Webhook monitoring is active"
  }
}

# Champs de la réponse :
# - data_source: Source des données (toujours "webhook")
# - monitor_interval: Intervalle de rafraîchissement en secondes
# - webhook: État du service webhook
#   - available: Si le service est opérationnel
#   - last_fetch_ts: Dernière récupération réussie
#   - error: Dernière erreur rencontrée (ou null)
#   - records_processed: Nombre d'enregistrements traités
# - csv_monitor: Rétrocompatibilité (toujours inactif en mode webhook)
#   - status: Statut du moniteur CSV (inactive)
#   - last_check: Dernière vérification (null)
#   - error: Message d'information
```

## Utilisation

### Source de Données Unique

Le système utilise exclusivement la source Webhook pour le monitoring des téléchargements :

1. **Webhook** (source unique, configurée via `WEBHOOK_JSON_URL`)
   - Aucun fallback MySQL/Airtable/CSV dans l'implémentation actuelle
   - Le service s'active automatiquement au démarrage de l'application

### Classification des URLs

Le WebhookService classifie automatiquement les URLs pour un traitement approprié :

- **dropbox** : Téléchargement automatique
- **fromsmash** : Mode manuel (nouvel onglet)
- **swisstransfer** : Mode manuel (nouvel onglet)
- **external** : Mode manuel générique

### Cache et Performance

- **TTL configurable** : Évite les requêtes répétées
- **Retry automatique** : 3 tentatives avec backoff exponentiel
- **Gestion d'erreurs** : Fallback gracieux en cas d'indisponibilité

## Monitoring et Surveillance

### Métriques Disponibles

```bash
# Statut détaillé du service
curl http://localhost:5000/api/csv_monitor_status | jq '.webhook'

# Réponse
{
  "available": true,
  "last_fetch_ts": "2025-10-17 13:24:13",
  "error": null,
  "records": 5
}
```

### Logs de l'Application

```bash
# Surveillance des logs Webhook
tail -f logs/app.log | grep -i webhook

# Messages typiques
# INFO: WebhookService: fetched 5 records from webhook
# WARNING: WebhookService: failed to fetch webhook JSON after 3 attempts
# DEBUG: WebhookService: skipping invalid item due to error
```

## Dépannage

### Problèmes Courants

#### 1. Erreur de Connexion
**Cause** : Endpoint inaccessible ou timeout
**Solution** :
```bash
# Test direct de l'URL
curl -v $WEBHOOK_JSON_URL

# Augmenter le timeout
export WEBHOOK_TIMEOUT=60
```

#### 2. Données Invalides
**Cause** : Structure JSON incorrecte
**Solution** :
```bash
# Validation du JSON
curl $WEBHOOK_JSON_URL | jq '.[] | has("url")'

# Vérifier les logs pour les erreurs de parsing
tail -f logs/app.log | grep "skipping invalid item"
```

#### 3. Cache Expiré
**Cause** : TTL trop court ou problème de cache
**Solution** :
```bash
# Forcer un refresh
export WEBHOOK_CACHE_TTL=0
# Puis remettre à la valeur désirée
```

### Mode de Secours

En cas de problème avec le Webhook, le système journalise les erreurs mais ne bascule pas vers une autre source. Assurez-vous que :

- L'URL `WEBHOOK_JSON_URL` est accessible
- Le timeout `WEBHOOK_TIMEOUT` est adapté à votre réseau
- Le cache `WEBHOOK_CACHE_TTL` permet de lisser les indisponibilités ponctuelles

## Sécurité et Bonnes Pratiques

### Protection des Endpoints

- **🔒 Authentification** : Utilisez des tokens API sur votre endpoint
- **📝 Validation** : Sanitisez les données avant exposition
- **🚦 Rate Limiting** : Limitez les requêtes pour éviter la surcharge
- **🔍 Audit** : Logguez les accès pour traçabilité

### Configuration Sécurisée

- **❌ Jamais en dur** : Ne codez jamais l'URL dans le code
- **✅ Variables d'env** : Utilisez exclusivement les variables d'environnement
- **🔄 Rotation** : Changez régulièrement les URLs/tokens si utilisés
- **🛡️ Proxy** : Utilisez un proxy pour contrôler l'accès en production

## Support et Documentation

### Ressources Supplémentaires

- **[Documentation API Flask](https://flask.palletsprojects.com/)**
- **[Guide JSON Schema](https://json-schema.org/)**
- **[RFC 3339 Timestamps](https://tools.ietf.org/html/rfc3339)**

### Exemples d'Implémentation

#### Endpoint Node.js
```javascript
app.get('/api/downloads', (req, res) => {
  const downloads = [
    {
      url: 'https://dropbox.com/s/...',
      timestamp: new Date().toISOString(),
      source: 'webhook'
    }
  ];
  res.json(downloads);
});
```

#### Endpoint Python/FastAPI
```python
@app.get("/api/downloads")
async def get_downloads():
    return [
        {
            "url": "https://dropbox.com/s/...",
            "timestamp": datetime.now().isoformat(),
            "source": "webhook"
        }
    ]
```

L'intégration Webhook offre une solution moderne et flexible pour l'alimentation des données de téléchargement dans le workflow MediaPipe v4.1.
