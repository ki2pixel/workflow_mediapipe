# Guide de Démarrage Rapide - Workflow MediaPipe v4.2

> **Note de version v4.2** : Support GPU optionnel pour InsightFace, optimisations CPU v4.1 maintenues, audit sécurité frontend complet.
> **Note de version v4.1** : Mode compact unique, performances CPU optimisées, architecture stabilisée.

## Configuration Système

### Exigences
- **OS** : Linux (recommandé), macOS, Windows 10/11
- **Python** : 3.8+ (testé avec 3.9-3.11)
- **RAM** : 8 GB minimum, 16 GB recommandé
- **GPU** : NVIDIA avec CUDA (optionnel mais recommandé)
- **Espace disque** : 10 GB minimum pour les environnements virtuels

### Logiciels Requis
- **FFmpeg** : Pour la conversion vidéo
- **Git** : Pour le clonage du repository

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg git python3-pip python3-venv

# macOS (avec Homebrew)
brew install ffmpeg git python3

# Windows
# Télécharger FFmpeg depuis https://ffmpeg.org/download.html
# Ajouter FFmpeg au PATH système
```

### Outils de Développement

#### Génération Bundle Repomix
```bash
# Générer un bundle du code applicatif (excluant archives/assets/logs)
npx repomix --config repomix.config.json
```
Le bundle est généré dans `repomix-output.md` pour analyse LLM.
Voir `docs/workflow/guides/REPOMIX_USAGE.md` pour l'utilisation complète.

## Installation

### 1. Clonage et Configuration Initiale

```bash
# Cloner le repository
git clone <repository-url> workflow_mediapipe
cd workflow_mediapipe

# Rendre les scripts exécutables
chmod +x start_workflow.sh
# Le script gère automatiquement les permissions nécessaires
```

### 2. Configuration des Variables d'Environnement

```bash
# Créer le fichier de configuration
touch .env

# Éditer avec vos valeurs
nano .env
```

### Configuration de Base

**Contenu minimal du fichier `.env`** :
```bash
# Sécurité (générer des tokens uniques)
FLASK_SECRET_KEY=your-unique-secret-key-here
INTERNAL_WORKER_COMMS_TOKEN=your-secure-token-here
RENDER_REGISTER_TOKEN=your-render-token-here

# Configuration application
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
DEBUG=false

# Virtualenvs relocalisables (SSD partagé, NAS, etc.)
# Laisser vide pour utiliser le dossier projet par défaut.
VENV_BASE_DIR=/mnt/cache/venv/workflow_mediapipe

# Webhook JSON Source (monitoring des téléchargements) — seule source autorisée depuis v4.1
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/data/webhook_links.json
WEBHOOK_MONITOR_INTERVAL=15   # secondes
WEBHOOK_CACHE_TTL=60          # secondes
WEBHOOK_TIMEOUT=10            # secondes
```

### Fonctionnalités Supprimées (v4.2)

Les fonctionnalités suivantes ont été retirées pour simplifier l'interface :
- **Supervision UI** : Boutons Diagnostics/Statistiques/Téléversement supprimés (2026-01-18)
- **Smart Upload avancé** : Mode compact unifié maintenu, mais fonctionnalités avancées retirées (2026-01-18)
- **Étape 5 · Options avancées** : Configuration dynamique des chunks supprimée (chunking adaptatif avec valeurs par défaut) (2026-01-18)

> **Note** : Ces suppressions réduisent la surface de maintenance sans impacter les fonctionnalités essentielles du workflow.

### Configuration STEP5 (Tracking Vidéo)

**Mode CPU (v4.1 - défaut recommandé)** :
```bash
# Configuration du tracking (STEP5)
TRACKING_DISABLE_GPU=1        # Mode CPU-only v4.1 (défaut recommandé)
TRACKING_CPU_WORKERS=15       # Valeur v4.1 (CPU >= 8 cœurs). Réduire si machine limitée.
STEP5_YUNET_MAX_WIDTH=640     # Downscale YuNet (coords rescalées dans le JSON)
STEP5_OPENSEEFACE_MAX_WIDTH=640  # Même principe pour OpenSeeFace (fallback sur STEP5_YUNET_MAX_WIDTH)
STEP5_OPENSEEFACE_MODEL_ID=1     # Modèle landmarks OpenSeeFace (0 = ultra-rapide, 2/3 = précision accrue)
STEP5_OPENCV_MAX_FACES=2          # Limite le nombre de visages OpenCV (Haar, YuNet, YuNet+py-feat)
STEP5_OPENCV_JAWOPEN_SCALE=1.0    # Ajuste l'intensité jawOpen pour les moteurs OpenCV
STEP5_MEDIAPIPE_MAX_FACES=4       # Limite MediaPipe Tasks (descendre à 1 pour monologue)
STEP5_MEDIAPIPE_JAWOPEN_SCALE=1.0 # Scaling jawOpen MediaPipe pour aligner l'analyse voix/visage
# STEP5_MEDIAPIPE_MAX_WIDTH=960   # Optionnel : downscale MediaPipe comme YuNet si CPU limité
# STEP5_TRACKING_ENGINE=openseeface  # Moteurs supportés: mediapipe_landmarker (défaut), opencv_haar, opencv_yunet, opencv_yunet_pyfeat, openseeface, eos, insightface
# STEP5_EOS_ENV_PYTHON=/mnt/cache/venv/workflow_mediapipe/eos_env/bin/python  # Override optionnel pour le moteur eos
```

**Support GPU InsightFace (v4.2+)** :
```bash
# Support GPU InsightFace uniquement (STEP5 v4.2+)
STEP5_ENABLE_GPU=0                  # 1 pour activer le mode GPU (réservé à InsightFace)
STEP5_GPU_ENGINES=insightface
STEP5_GPU_MAX_VRAM_MB=2048          # Ajuster selon la VRAM disponible (ex: 3072 pour GTX 1650)
STEP5_GPU_FALLBACK_AUTO=1           # Bascule automatique CPU si VRAM indisponible
STEP5_GPU_PROFILING=0               # 1 pour logguer VRAM/temps GPU
# STEP5_INSIGHTFACE_ENV_PYTHON=/mnt/venv_ext4/insightface_env/bin/python  # Override si le venv InsightFace est relocalisé

# InsightFace (GPU-only)
# STEP5_TRACKING_ENGINE=insightface
# STEP5_INSIGHTFACE_MODEL_NAME=antelopev2
```

## Sécurité et Tests Frontend

Le frontend bénéficie d'un audit de sécurité complet avec validation continue :

### Tests Automatisés
```bash
# Exécuter tous les tests frontend (Node/ESM)
npm run test:frontend

# Tests individuels (post-audit 2026-01-17)
npm run test:dom-batcher      # Performance batching DOM
npm run test:focus-trap      # A11y focus management
npm run test:xss-safety      # Sécurité XSS logs
npm run test:step-details    # Timeline Connectée Phase 3 (StepDetailsPanel)
```

### Couverture des Tests
Exécuter la suite de tests frontend pour valider :
- DOMBatcher et performances
- Focus trap et accessibilité WCAG
- Timeline Connectée Phase 3 (StepDetailsPanel)
- Sécurité XSS et échappement HTML

### Sécurité XSS
- Échappement systématique des contenus dynamiques via `DOMUpdateUtils.escapeHtml()`
- Validation continue via `tests/frontend/test_log_safety.mjs`
- Aucune utilisation de `innerHTML` non sécurisée

### Accessibilité (A11y)
- Focus trap et restauration sur toutes les modales
- Support `prefers-reduced-motion` pour utilisateurs sensibles
- Navigation clavier complète (Tab/Shift+Tab/Escape)

### Performance
- Regex pré-compilées pour le traitement des logs
- DOM batching via `requestAnimationFrame`
- Polling adaptatif avec backoff automatique

### Configuration Avancée STEP5

**Blendshapes et Optimisations** :
```bash
# Filtrage des blendshapes (export JSON)
# STEP5_BLENDSHAPES_PROFILE=full     # Exporte toutes les clés (défaut)
# STEP5_BLENDSHAPES_PROFILE=mouth    # Uniquement bouche/mâchoire (+ langue avec INCLUDE_TONGUE=1)
# STEP5_BLENDSHAPES_PROFILE=none     # Désactive l'export blendshapes
# STEP5_BLENDSHAPES_PROFILE=mediapipe# Supprime tongueOut, ajoute _neutral si absent
# STEP5_BLENDSHAPES_PROFILE=custom   # Whitelist via STEP5_BLENDSHAPES_EXPORT_KEYS
# STEP5_BLENDSHAPES_INCLUDE_TONGUE=1 # Inclut tongueOut avec profil mouth
# STEP5_BLENDSHAPES_EXPORT_KEYS=jawOpen,mouthSmileLeft,mouthSmileRight
# STEP5_BLENDSHAPES_THROTTLE_N=2      # Calcul des blendshapes toutes les N frames (cache activé)
# STEP5_ENABLE_PROFILING=0            # 1 pour logs [PROFILING] toutes les 20 frames (diagnostic uniquement)

# Object detection fallback (registry centralisé)
# STEP5_ENABLE_OBJECT_DETECTION=0                # 1 pour activer le fallback (MediaPipe uniquement)
# STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2 # Voir docs/STEP5_SUIVI_VIDEO.md pour la table des modèles
# STEP5_OBJECT_DETECTOR_MODEL_PATH=/chemin/vers/model.tflite  # optionnel pour override absolu/relatif

# Autres optimisations (ONNX Runtime/threads)
# STEP5_ONNX_INTRA_OP_THREADS=2
# STEP5_ONNX_INTER_OP_THREADS=1
```

### Configuration STEP4 (Audio - Lemonfox)

```bash
# Configuration Lemonfox (STEP4 - optionnel)
STEP4_USE_LEMONFOX=0                    # 1 pour activer Lemonfox, 0 pour Pyannote
LEMONFOX_API_KEY=votre_cle_api_ici     # Clé API Lemonfox (si STEP4_USE_LEMONFOX=1)
LEMONFOX_TIMEOUT_SEC=300                # Timeout API en secondes
LEMONFOX_EU_DEFAULT=0                   # 1 pour endpoint EU, 0 pour standard

# Paramètres Lemonfox (optionnels)
LEMONFOX_DEFAULT_LANGUAGE=fr
LEMONFOX_DEFAULT_PROMPT="Transcription de contenu vidéo"
LEMONFOX_SPEAKER_LABELS_DEFAULT=1
LEMONFOX_DEFAULT_MIN_SPEAKERS=1
LEMONFOX_DEFAULT_MAX_SPEAKERS=4
LEMONFOX_TIMESTAMP_GRANULARITIES=word
LEMONFOX_SPEECH_GAP_FILL_SEC=0.15       # Comblement des trous courts (secondes)
LEMONFOX_SPEECH_MIN_ON_SEC=0.0          # Durée minimum des îlots de parole (secondes)
```

### 3. Installation des Environnements Virtuels

```bash
# Création des environnements (utilise VENV_BASE_DIR s'il est défini)
python3 -m venv "${VENV_BASE_DIR:-.}/env"
python3 -m venv "${VENV_BASE_DIR:-.}/transnet_env"
python3 -m venv "${VENV_BASE_DIR:-.}/audio_env"
python3 -m venv "${VENV_BASE_DIR:-.}/tracking_env"
python3 -m venv "${VENV_BASE_DIR:-.}/eos_env"

# Activation de l'environnement principal
source "${VENV_BASE_DIR:-.}/env/bin/activate"   # Linux/Mac
# "${VENV_BASE_DIR:-.}/env\Scripts\activate"    # Windows

# Installation des dépendances principales
pip install -r requirements.txt

# Installation des dépendances spécialisées
source "${VENV_BASE_DIR:-.}/transnet_env/bin/activate"
pip install torch torchvision tensorflow ffmpeg-python
deactivate

source "${VENV_BASE_DIR:-.}/audio_env/bin/activate"
pip install pyannote.audio torch torchaudio
deactivate

source "${VENV_BASE_DIR:-.}/tracking_env/bin/activate"
pip install mediapipe opencv-contrib-python numpy   # opencv-contrib requis pour FaceDetectorYN (YuNet)
deactivate

source "${VENV_BASE_DIR:-.}/eos_env/bin/activate"
pip install eos-py mediapipe opencv-contrib-python numpy scipy
deactivate
```

### 4. Démarrage de l'Application

```bash
# Retour à l'environnement principal
source env/bin/activate

# Démarrage du serveur
./start_workflow.sh
```

> ℹ️ `start_workflow.sh` détecte automatiquement `VENV_BASE_DIR` (ordre : valeur exportée > `.env` > dossier projet), exporte `PYTHON_VENV_EXE_ENV` pour Flask et garantit que `config.get_venv_python()` pointe vers les bons environnements (suivi vertical, `tracking_env`, `eos_env`, etc.). Aucun `env/bin/python` ne doit être codé en dur.
> Lorsque `STEP5_ENABLE_GPU=1`, `workflow_scripts/step5/run_tracking_manager.py` valide l’état du GPU via `Config.check_gpu_availability()`, charge automatiquement l’interpréteur ONNXRuntime défini par `STEP5_INSIGHTFACE_ENV_PYTHON` (si présent) et injecte les chemins CUDA nécessaires dans les workers. En cas d’échec (VRAM insuffisante, ONNXRuntime CUDA indisponible…), un fallback CPU est appliqué si `STEP5_GPU_FALLBACK_AUTO=1`.

**Sortie attendue** :
```text
========================================================
Le serveur Flask a été lancé avec succès!
Interface web: http://127.0.0.1:5000/
Log unifié: logs/app.log
Log startup: logs/startup.log

FONCTIONNALITÉS DISPONIBLES:
  • Exécution manuelle des étapes du workflow
  • Monitoring système (CPU/RAM/GPU)
  • Suivi des logs en temps réel
  • Séquences personnalisées
  • Monitoring Webhook (surveillance automatique des téléchargements)
  • Timeline Connectée : ✅ Pipeline visuel moderne complet avec nœuds connectés et micro-interactions premium
========================================================
```

## Première Utilisation

### 1. Accès à l'Interface Web

Ouvrir un navigateur et aller à : `http://localhost:5000`

> Note (Politique Dropbox-only)
>
> - Seules les URLs Dropbox (directes) et les proxys PHP (`workers.dev/dropbox/...`) peuvent déclencher un téléchargement automatique.
> - Les autres sources (FromSmash, SwissTransfer, externes, etc.) sont ignorées par le système de téléchargement automatique.
> - Backend : `execute_csv_download_worker()` classe les URLs comme `dropbox` ou `proxy_php` pour les téléchargements automatiques.

### Smart Upload (Téléversement Intelligent Simplifié)

#### Architecture et Flux :
- **Point d'entrée :** Bouton `#upload-button` déclenchant `openSmartUploadModal()`
- **Chargement automatique :** `preloadTodayCacheFolders()` récupère les dossiers du jour via API
- **Interface utilisateur :**
  - Affichage avec badges numériques et horodatages
  - États visuels : sélectionné/désactivé pour les éléments
  - Gestion des erreurs via `ErrorHandler.js`
- **Optimisations :**
  - Utilisation de `DOMBatcher` pour les mises à jour groupées
  - Pas de contrôles manuels (recherche, ouverture séparée)
  - Fermeture automatique après sélection

#### Fichiers clés modifiés :
- `static/main.js` : Logique principale et gestion des événements
- `templates/index_new.html` : Structure HTML de la modale simplifiée
- `static/domElements.js` : Nettoyage des sélecteurs obsolètes

#### API Endpoints utilisés :
- `fetchTodayCacheFoldersAPI()` : Récupération des dossiers du jour
- `openCachePathInExplorerAPI()` : Ouverture de l'explorateur avec présélection

#### Changements UX :
- **Avant :** Interface complexe avec recherche manuelle et boutons séparés
- **Après :** Flux en un clic avec affichage automatique des dossiers du jour
- **Impact :** Réduction de la complexité cognitive et accélération du workflow de sauvegarde

### Diagnostics Système

L'interface inclut un outil de diagnostics rapide accessible via le bouton "🩺 Diagnostics" dans les contrôles unifiés.

#### Accès :
- Cliquer sur le bouton "🩺 Diagnostics" dans la barre de contrôles supérieure.
- Une modale s'ouvre affichant les informations système.

#### Informations affichées :
- **Versions logicielles** : Python, FFmpeg
- **GPU** : Disponibilité et nom du GPU NVIDIA (si détecté)
- **Configuration** : Flags de configuration actifs (filtrés pour la sécurité)

#### Utilisation :
- Utile pour le dépannage et la vérification de l'environnement avant l'exécution.
- Les informations sont mises à jour en temps réel lors de l'ouverture de la modale.
 - Détails complets (backend + frontend) : voir [docs/workflow/features/DIAGNOSTICS_FEATURE.md](docs/workflow/features/DIAGNOSTICS_FEATURE.md)

### Dossiers de Travail

```
projets_extraits/
├── projet_camille_001/
│   ├── docs/                    # Fichiers extraits
│   │   ├── video1.mp4          # Vidéos originales
│   │   └── video2.mov
│   ├── video1.csv              # Scènes détectées (Étape 3)
│   ├── video1_audio.json       # Analyse audio (Étape 4)
│   ├── video1_tracking.json    # Données de tracking (Étape 5 et 5.bis)
│   └── final_results/          # Résultats finaux (Étape 6)
└── projet_camille_002/
    └── ...
```

### Logs Système

```
logs/
├── app.log                    # Log principal unifié
├── startup.log                # Logs de démarrage
├── step1/                     # Logs par étape
│   ├── extract_20240120_143022.log
│   └── ...
├── step2/
├── step3/
├── step4/
├── step5/
├── step5_bis/
└── step6/
```

## Commandes Utiles

### Gestion des Services

```bash
# Démarrage normal
./start_workflow.sh

# Démarrage en mode debug
DEBUG=true ./start_workflow.sh

# Arrêt propre
Ctrl+C dans le terminal

# Notes v4.1 (Rapports)

- Sortie standardisée en HTML-only (PDF retiré).
- Prévisualisation inline via iframe sandbox (sécurité XSS renforcée).
- Note: Les endpoints de génération de rapports ont été retirés du système.

# Vérification des processus
ps aux | grep python
```

### Monitoring des Logs

```bash
# Log principal en temps réel
tail -f logs/app.log

# Logs d'une étape spécifique
tail -f logs/step1/extract_*.log

# Recherche dans les logs
grep "ERROR" logs/app.log
grep "STEP1" logs/app.log
# STEP5 tracing : surveiller aussi logs/step5/manager_tracking_*.log et logs/step5/worker_* pour les tags
# [Progression-MultiLine], [Gestionnaire] Succès/Échec, [WORKER-XXXX] (chunk boundaries, retries, profiling)
```

### Gestion des Environnements

```bash
# Activation manuelle d'un environnement
source "${VENV_BASE_DIR:-.}/transnet_env/bin/activate"

# Vérification des dépendances
pip list | grep torch

# Mise à jour des dépendances
pip install --upgrade -r requirements.txt
```

### Tests et Validation

```bash
# Test de l'API
curl http://localhost:5000/api/system_monitor

# Statut d'une étape (API)
curl http://localhost:5000/api/step_status/STEP1

# Test d'une étape via API
curl -X POST http://localhost:5000/run/STEP1

# Validation de la configuration
python -c "from config.settings import config; config.validate(); print('Config OK')"
```

## Résolution de Problèmes Courants

### Erreur : "Port 5000 déjà utilisé"

```bash
# Trouver le processus utilisant le port
lsof -i :5000

# Tuer le processus
kill -9 <PID>

# Ou utiliser un autre port
FLASK_PORT=5001 ./start_workflow.sh
```

### Erreur : "FFmpeg non trouvé"

```bash
# Vérifier l'installation
ffmpeg -version

# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows : ajouter FFmpeg au PATH
```

### Erreur : "Environnement virtuel corrompu"

```bash
# Supprimer et recréer l'environnement
rm -rf env/
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### Erreur : "CUDA non disponible"

```bash
# Vérifier CUDA
nvidia-smi

# Installer les drivers NVIDIA si nécessaire
# Le système fonctionnera en mode CPU si CUDA n'est pas disponible
```

### Problème : "Logs non visibles dans l'interface"

1. Vérifier les permissions des fichiers de logs
2. Redémarrer l'application
3. Vérifier la configuration dans `config/settings.py`

### Problème : "Étape bloquée en statut 'running'"

```bash
# Vérifier les processus Python
ps aux | grep python

# Redémarrer l'application
Ctrl+C puis ./start_workflow.sh

# Nettoyer les fichiers de verrous si nécessaire
rm -f /tmp/workflow_*.lock
```

## Configuration Avancée

### Configuration Lemonfox (Analyse Audio v4.1)

Lemonfox est une alternative à Pyannote.audio pour l'analyse audio via API cloud.

#### Activation de Lemonfox
```bash
# Activer Lemonfox dans .env
STEP4_USE_LEMONFOX=1
LEMONFOX_API_KEY=votre_cle_api_ici

# Redémarrer l'application
./start_workflow.sh
```

#### Variables Lemonfox expliquées

| Variable | Description | Valeur par défaut |
|----------|-------------|------------------|
| `STEP4_USE_LEMONFOX` | Toggle Lemonfox/Pyannote | `0` (Pyannote) |
| `LEMONFOX_API_KEY` | Clé API Lemonfox (obligatoire si activé) | - |
| `LEMONFOX_TIMEOUT_SEC` | Timeout API en secondes | `300` |
| `LEMONFOX_EU_DEFAULT` | Endpoint EU (1) ou standard (0) | `0` |
| `LEMONFOX_DEFAULT_LANGUAGE` | Langue de transcription | `fr` |
| `LEMONFOX_SPEAKER_LABELS_DEFAULT` | Activer diarisation locuteurs | `1` |
| `LEMONFOX_SPEECH_GAP_FILL_SEC` | Comblement trous courts | `0.15` |
| `LEMONFOX_SPEECH_MIN_ON_SEC` | Durée minimum îlots parole | `0.0` |

#### Comportement et fallback
- **Si Lemonfox échoue** : bascule automatiquement vers Pyannote
- **Logs spécifiques** : monitoring dans `logs/step4/`
- **Sortie compatible** : même format JSON que Pyannote

#### Avantages/Limitations
**Avantages** :
- Pas besoin de GPU local
- Qualité constante via API cloud
- Scalabilité et parallélisation

**Limitations** :
- Connexion internet requise
- Coût d'utilisation API
- Données envoyées vers service externe

### Optimisation GPU

```bash
# Vérifier la configuration GPU
nvidia-smi

# Configurer CUDA_VISIBLE_DEVICES si plusieurs GPU
export CUDA_VISIBLE_DEVICES=0
./start_workflow.sh```

### Mode Production

```bash
# Configuration production dans .env
DEBUG=false
FLASK_ENV=production

# Utilisation d'un serveur WSGI (optionnel)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_new:APP_FLASK
```

### Monitoring Avancé

Le statut du monitoring des téléchargements est disponible via l'API :

```bash
curl http://localhost:5000/api/csv_monitor_status
```

Réponse JSON :
```json
{
  "data_source": "webhook",
  "monitor_interval": 15,
  "webhook": {
    "available": true,
    "last_fetch_ts": "2025-03-15T10:30:00Z",
    "error": null,
    "records_processed": 42
  },
  "csv_monitor": {
    "status": "inactive",
    "last_check": null,
    "error": "Webhook monitoring is active"
  }
}
```

> **Note** : Le système utilise désormais exclusivement le Webhook pour le monitoring des téléchargements. L'ancien système basé sur les fichiers CSV est maintenu pour compatibilité mais n'est plus actif.

## Support et Documentation

- **Documentation complète** : `docs/ARCHITECTURE_COMPLETE_FR.md`
- **Guidelines de développement** : `docs/DEVELOPMENT_GUIDELINES.md`
- **Logs détaillés** : `logs/app.log`
- **Configuration** : `config/settings.py` et `.env`
- **Statut Lemonfox** : `docs/workflow/STEP4_LEMONFOX_IMPLEMENTATION_STATUS.md`
- **Intégration Webhook** : `docs/workflow/WEBHOOK_INTEGRATION.md`

Pour toute question ou problème, consulter les logs et la documentation technique complète.