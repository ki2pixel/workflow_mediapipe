# CSVService - Monitoring et Historique des Téléchargements

> **Code-Doc Context** – Service critique pour le monitoring des téléchargements avec persistance SQLite et complexité radon F sur les méthodes principales.

---

## Purpose & System Role

### Objectif
`CSVService` orchestre la surveillance des téléchargements via webhook JSON, la déduplication des URLs et la persistance structurée dans SQLite. Il sert de couche d'abstraction entre les sources externes (Dropbox, FromSmash, SwissTransfer) et le système de monitoring.

### Rôle dans l'Architecture
- **Position** : Service backend central (`services/csv_service.py`)
- **Prérequis** : Webhook JSON, configuration `.env`
- **Sortie** : Historique structuré SQLite, monitoring temps réel
- **Dépendances** : `download_history_repository`, `WorkflowState`

### Valeur Ajoutée
- **Source unique** : Webhook JSON comme point d'entrée unique
- **Déduplication** : Normalisation URLs et détection doublons
- **Persistance** : SQLite avec verrouillage multi-processus
- **Cache** : TTL configurable et retry automatique

---

## Architecture

### Composants Principaux
```python
class CSVService:
    def __init__(self, 
                 download_repo: DownloadHistoryRepository,
                 webhook_service: WebhookService,
                 workflow_state: WorkflowState):
        self._repo = download_repo
        self._webhook = webhook_service
        self._state = workflow_state
```

### Flux de Données
1. **Webhook → CSVService** : Réception URLs depuis webhook.kidpixel.fr
2. **Normalisation** : `_normalize_url()` (Score F) - décodage double encodage
3. **Détection** : `_check_csv_for_downloads()` (Score F) - parsing CSV complexe
4. **Persistance** : `download_history_repository` - écriture SQLite atomique

---

## Complexité (Radon Analysis)

### Points Critiques (Score F)

#### `_normalize_url()` (Score F)
- **Complexité** : Parsing URLs doublement encodées, entités HTML
- **Défis** : Gestion `amp%3Bdl=0`, caractères spéciaux, validation
- **Impact** : Service critique pour éviter les doublons

#### `_check_csv_for_downloads()` (Score F)
- **Complexité** : Parsing CSV multi-formats, gestion erreurs
- **Défis** : Détection téléchargements, validation structure
- **Impact** : Monitoring temps réel des téléchargements

#### `_load_structured_history()` (Score C)
- **Complexité** : Migration historique, format structuré
- **Défis** : Rétrocompatibilité, conversion temps local

---

## Configuration

### Variables d'Environnement
```bash
# Monitoring
CSV_DOWNLOAD_ENABLED=1
CSV_POLLING_INTERVAL=30
CSV_CACHE_TTL=300

# Sécurité
DROPBOX_PROXY_ENABLED=1
DISABLE_EXPLORER_OPEN=1

# Performance
DRY_RUN_DOWNLOADS=false
WEBHOOK_TIMEOUT=10
```

### WorkflowCommandsConfig Intégration
```python
# Accès à la configuration du service
config = WorkflowCommandsConfig()
csv_config = config.get_step_config('csv_monitoring')
```

---

## API & Méthodes

### Méthodes Principales
```python
# Monitoring principal
async def monitor_csv_downloads(self) -> None:
    """Orchestrateur du monitoring avec retry et cache"""

# Normalisation URLs (Score F)
def _normalize_url(self, url: str) -> str:
    """Normalisation complète avec décodage double encodage"""

# Détection téléchargements (Score F)  
def _check_csv_for_downloads(self, csv_data: List[Dict]) -> List[DownloadResult]:
    """Parsing CSV complexe avec gestion multi-formats"""

# Persistance
def _persist_download_result(self, result: DownloadResult) -> None:
    """Écriture SQLite atomique via repository"""
```

### Patterns d'Utilisation
```python
# Initialisation
csv_service = CSVService(download_repo, webhook_service, workflow_state)

# Monitoring continu
await csv_service.monitor_csv_downloads()

# Validation URL
normalized = csv_service._normalize_url(raw_url)
```

---

## Performance & Monitoring

### Indicateurs Clés
- **Débit URLs** : URLs traitées par seconde
- **Taux déduplication** : % URLs dupliquées évitées
- **Latence webhook** : Temps réponse webhook.kidpixel.fr
- **Taille cache** : Entrées en mémoire vs SQLite

### Patterns de Logging
```python
# Monitoring progression
logger.info(f"[CSV] Processed {len(urls)} URLs, {duplicates} duplicates")

# Erreurs réseau
logger.warning(f"[CSV] Webhook timeout, retrying in {interval}s")

# Normalisation
logger.debug(f"[CSV] Normalized URL: {original} -> {normalized}")
```

---

## Actions Recommandées

### Refactoring Priorité Haute
1. **Extraire `URLNormalizer`** :
   ```python
   class URLNormalizer:
       def normalize(self, url: str) -> str:
           # Isoler la logique de décodage double encodé
   ```

2. **Créer `DownloadDetector`** :
   ```python
   class DownloadDetector:
       def detect_downloads(self, csv_data: List[Dict]) -> List[DownloadResult]:
           # Simplifier parsing CSV complexe
   ```

3. **Simplifier `_check_csv_for_downloads`** :
   - Réduire complexité cyclomatique
   - Extraire helpers de validation

### Monitoring Continu
- **Radon** : Surveillance complexité méthodes F
- **Tests unitaires** : Couverture normalisation URLs
- **Performance** : Benchmark débit traitement

---

## Documentation Croisée

- [Architecture Complète](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble système
- [Analyse Complexité](../core/COMPLEXITY_ANALYSIS.md) : Métriques radon détaillées
- [Download History Repository](../features/DOWNLOAD_HISTORY_REPOSITORY.md) : Persistance SQLite
- [Webhook Service](../features/WEBHOOK_SERVICE.md) : Source webhook JSON
