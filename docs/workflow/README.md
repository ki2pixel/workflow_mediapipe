# Workflow MediaPipe - Documentation

**TL;DR** : Pipeline vidéo 8 étapes avec tracking facial, analyse audio et préparation After Effects. Architecture Flask + Python avec environnements spécialisés.

## Pourquoi ce Projet ?

Tu dois transformer des vidéos brutes en données d'animation 3D pour After Effects, mais chaque outil (détection de scènes, analyse audio, tracking facial) demande des bibliothèques Python différentes et souvent incompatibles. Lancer manuellement chaque étape est chronophage, et les résultats sont difficiles à synchroniser.

### ❌ L'approche manuelle
- Installer chaque bibliothèque à la main
- Lancer les scripts un par un
- Gérer les conflits de dépendances
- Synchroniser manuellement les résultats

### ✅ Notre pipeline intégré
- Un seul clic pour lancer les 8 étapes
- Environnements isolés automatiquement
- Progression visible en temps réel
- Résultats optimisés pour After Effects

## Comment Ça Marche ?

Le pipeline traite les vidéos en 8 étapes séquentielles, chacune dans son environnement virtuel optimisé :

1. **Extraction** : Archives ZIP/RAR/TAR avec sécurité renforcée
2. **Conversion** : Vidéos standardisées à 25 FPS avec GPU optimisé
3. **Scènes** : Détection automatique des changements de scène
4. **Audio** : Analyse diarisation avec Pyannote/Lemonfox
5. **Tracking** : Détection faciale MediaPipe (CPU) ou InsightFace (GPU)
6. **Réduction** : JSON optimisé avec analytics enrichis
7. **Pré-traitement AE** : Format optimisé pour After Effects
8. **Finalisation** : Archivage et copie vers destination

## Démarrage Rapide

```bash
# 1. Installation
git clone <repository>
cd workflow_mediapipe
source env/bin/activate
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Éditer .env avec tes clés API et chemins

# 3. Lancement
python app_new.py
# Ouvre http://localhost:5000
```

## Navigation dans la Documentation

### 🏗️ **Core** - Fondations et Architecture
- **[Architecture](core/architecture.md)** : Vue d'ensemble système et flux de données
- **[Quickstart](core/quickstart.md)** : Installation et démarrage en 5 minutes
- **[Developer Guide](core/developer-guide.md)** : Guide pour développeurs

### 🔄 **Pipeline** - Étapes de Traitement
- **[01 Extraction](pipeline/01-extraction.md)** : Extraction d'archives sécurisée
- **[02 Conversion](pipeline/02-conversion.md)** : Conversion vidéo 25 FPS
- **[03 Scene Detection](pipeline/03-scene-detection.md)** : Détection scènes TransNetV2
- **[04 Audio Analysis](pipeline/04-audio-analysis.md)** : Analyse audio Pyannote/Lemonfox
- **[05 Video Tracking](pipeline/05-video-tracking.md)** : Tracking MediaPipe/InsightFace
- **[06 JSON Reduction](pipeline/06-json-reduction.md)** : Réduction JSON avec analytics
- **[07 AE Preprocessing](pipeline/07-ae-preprocessing.md)** : Préparation After Effects
- **[08 Finalization](pipeline/08-finalization.md)** : Archivage et finalisation

### ⚙️ **Services** - Composants Métier
- **[CSV Service](services/csv-service.md)** : Monitoring téléchargements webhook
- **[Workflow Service](services/workflow-service.md)** : Orchestrateur central du pipeline
- **[Results Archiver](services/results-archiver-service.md)** : Archivage automatique
- **(Archive) [VisualizationService](archives/visualization-service.md)** : Service décommissionné (voir [plan de décommissionnement](DECOMMISSIONING_VISUALIZATION_SERVICE.md))

### 🔧 **Ops** - Technique et API
- **[API Reference](ops/api-routes.md)** : Endpoints REST et contrats
- **[Security](ops/security.md)** : Architecture sécurisée webhook-only
- **[Testing](ops/testing-strategy.md)** : Tests robustes pour zones critiques
- **[Monitoring](ops/system-monitoring.md)** : Monitoring système et instrumentation

## Architecture Technique

### Backend Flask
- **Services** : Logique métier isolée avec injection de dépendances
- **État Centralisé** : `WorkflowState` thread-safe pour la cohérence
- **Environnements Spécialisés** : Chaque étape a son venv optimisé

### Frontend Natif
- **JavaScript Vanilla** : Pas de framework, DOM batching optimisé
- **AppState** : État immuable avec synchronisation
- **PollingManager** : Backoff adaptatif pour les mises à jour

### Sécurité
- **Webhook-Only** : Source unique de données externes
- **Tokens Internes** : Protection des endpoints sensibles
- **Validation Entrées** : Sanitisation systématique

### Services Retirés

**VisualizationService** : Décommissionné depuis le 2026‑02‑08. Le service de visualisation a été retiré car l'interface principale ne l'utilisait plus. La documentation complète et le plan de décommissionnement sont disponibles dans `archives/visualization-service.md` et `DECOMMISSIONING_VISUALIZATION_SERVICE.md`.

## Environnements Virtuels

```bash
env/                    # Application principale
├── tracking_env_slim/   # MediaPipe CPU (STEP5)
├── audio_env/           # Analyse audio (STEP4)
├── transnet_env/        # Détection scènes (STEP3)
└── insightface_env/     # InsightFace GPU (optionnel)
```

## Variables d'Environnement Essentielles

```bash
# Application
FLASK_SECRET_KEY=your-secret-key
INTERNAL_WORKER_TOKEN=your-worker-token

# Pipeline
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/data/webhook_links.json
STEP5_TRACKING_ENGINE=mediapipe  # ou insightface
STEP4_USE_LEMONFOX=0              # ou 1 pour SaaS

# Monitoring
ENABLE_GPU_MONITORING=true
SYSTEM_MONITOR_POLLING_INTERVAL=2000
```

## Cas d'Usage

### 🎬 **Post-Production Vidéo**
- Tracking facial pour animation 3D
- Analyse audio pour synchronisation
- Export optimisé pour After Effects

### 🔬 **Analyse Multimédia**
- Détection automatique de scènes
- Diarisation des intervenants
- Métriques de performance système

### 🚀 **Développement**
- Architecture microservices
- Tests robustes (89% couverture)
- Monitoring en temps réel

## Profils d'Utilisation

| Profil | Objectif | Commandes Clés | Risques |
|--------|----------|----------------|---------|
| **Démonstration** | Montrer rapidement le pipeline | `./start_workflow.sh` + UI web | GPU indisponible = fallback CPU |
| **Développement** | Tester et améliorer le système | `pytest` + `npm run test:frontend` | Dépendances manquantes dans venv |
| **Production** | Traitement batch de vidéos | Séquences complètes + monitoring | Espace disque sur workflows longs |
| **Post-production** | Export optimisé pour AE | Focus STEP6/STEP7 + scripts AE | Crash AE si JSON trop volumineux |

## Analogie : Sprint vs Marathon

Pense à ce pipeline comme une course. Pour une **démonstration**, c'est un **sprint** : tout-en-un, rapide, avec fallbacks automatiques. Pour la **production**, c'est un **marathon** : monitoring fin, optimisations GPU, archivage robuste. Les deux modes utilisent la même infrastructure, mais avec des priorités différentes.

## Contribuer

### Architecture des Services
```python
# Pattern d'injection de dépendances
class WorkflowService:
    def __init__(self, filesystem, state, commands):
        self._fs = filesystem
        self._state = state
        self._commands = commands
```

### Tests
```bash
# Lancer tous les tests
./scripts/run_tests.sh

# Tests backend uniquement
pytest tests/unit/ tests/integration/

# Tests frontend
npm run test:frontend
```

## Support

- **Documentation complète** : Explore les sections ci-dessus
- **Issues** : Signaler les problèmes sur GitHub
- **Discussions** : Questions et suggestions sur GitHub Discussions

---

## Golden Rule

**Pipeline → Services → Frontend : respecte la hiérarchie, sinon tu crées des angles morts.**

*Cette documentation suit la méthode SKILL.md pour une lecture rapide et une compréhension immédiate.*
