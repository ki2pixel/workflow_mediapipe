# Démarrage Rapide

**TL;DR** : Installe les dépendances, configure `.env`, lance `./start_workflow.sh`, et ouvre `http://localhost:5000`. Tu seras prêt à analyser des vidéos en moins de 5 minutes.

## Le Problème : Tu Veux Analyser des Vidéos Maintenant

Tu as des vidéos à analyser pour la post-production After Effects, mais tu ne veux pas passer des heures à installer des bibliothèques Python incompatibles ou configurer des outils complexes. Tu as besoin d'une solution qui fonctionne rapidement.

## Notre Solution : Installation en 4 Étapes

### 1. Prépare ton Système

**Exigences minimales** :
- OS : Linux/macOS/Windows 10+
- Python : 3.8+
- RAM : 8 GB minimum (16 GB recommandé)
- GPU NVIDIA : optionnel mais recommandé
- Espace disque : 10 GB pour les environnements

**Installe les outils de base** :
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg git python3-pip python3-venv

# macOS (Homebrew)
brew install ffmpeg git python3

# Windows : télécharge FFmpeg depuis ffmpeg.org et ajoute au PATH
```

### 2. Clone et Configure

```bash
# Clone le projet
git clone <repository-url> workflow_mediapipe
cd workflow_mediapipe

# Rends les scripts exécutables
chmod +x start_workflow.sh
```

### ❌ Installation manuelle (anti-pattern)
```bash
# Approche risquée - dépendances conflictuelles
pip install torch torchvision  # Global !
pip install mediapipe       # Conflit TensorFlow
pip install pyannote.audio  # Versions incompatibles
# Résultat : environnement cassé
```

### ✅ Installation automatisée (pattern recommandé)
```bash
# Approche sûre - environnements isolés
./start_workflow.sh  # Gère tout automatiquement
# Ou manuellement avec les venv dédiés (voir étape 3)
```

**Crée ton fichier `.env`** :
```bash
touch .env
nano .env
```

**Configuration minimale obligatoire** :
```bash
# Sécurité - génère ces tokens
FLASK_SECRET_KEY=your-unique-secret-key-here
INTERNAL_WORKER_COMMS_TOKEN=your-secure-token-here
RENDER_REGISTER_TOKEN=your-render-token-here

# Application
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
DEBUG=false

# Environnements (optionnel - pour les déplacer sur SSD/NAS)
VENV_BASE_DIR=/mnt/cache/venv/workflow_mediapipe

# Monitoring webhook (source unique de données)
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/data/webhook_links.json
WEBHOOK_MONITOR_INTERVAL=15
WEBHOOK_CACHE_TTL=60
WEBHOOK_TIMEOUT=10
```

### 3. Installe les Environnements Virtuels

```bash
# Crée les environnements (utilise VENV_BASE_DIR si défini)
python3 -m venv "${VENV_BASE_DIR:-.}/env"
python3 -m venv "${VENV_BASE_DIR:-.}/transnet_env"
python3 -m venv "${VENV_BASE_DIR:-.}/audio_env"
python3 -m venv "${VENV_BASE_DIR:-.}/tracking_env_slim"

# Environnement principal
source "${VENV_BASE_DIR:-.}/env/bin/activate"
pip install -r requirements.txt

# Environnement TransNet (détection scènes)
source "${VENV_BASE_DIR:-.}/transnet_env/bin/activate"
pip install torch torchvision tensorflow ffmpeg-python
deactivate

# Environnement Audio (Pyannote/Lemonfox)
source "${VENV_BASE_DIR:-.}/audio_env/bin/activate"
pip install pyannote.audio torch torchaudio
deactivate

# Environnement Tracking (MediaPipe CPU)
source "${VENV_BASE_DIR:-.}/tracking_env_slim/bin/activate"
pip install -r requirements-tracking-env-lite.txt
deactivate
```

### 4. Démarre l'Application

```bash
# Retour à l'environnement principal
source env/bin/activate

# Lance le serveur
./start_workflow.sh
```

**Tu devrais voir** :
```
========================================================
Le serveur Flask a été lancé avec succès!
Interface web: http://127.0.0.1:5000/
========================================================
```

Ouvre ton navigateur à `http://localhost:5000`.

## Ta Première Analyse Vidéo

### Prépare tes Fichiers

1. **Extrais tes archives** dans `projets_extraits/` :
```
projets_extraits/
├── mon_projet_001/
│   ├── video1.mp4
│   └── video2.mov
```

2. **Le système détecte automatiquement** les vidéos si tu utilises le webhook Dropbox.

### Lance le Pipeline Complet

Dans l'interface web :
1. Sélectionne toutes les étapes (STEP1 à STEP8)
2. Clique sur "Exécuter la séquence"
3. Regarde la progression en temps réel

**Ou lance une étape individuelle** si tu préfères contrôler manuellement.

### Résultats

Les fichiers de sortie apparaissent dans ton projet :
```
mon_projet_001/
├── video1.mp4              # Original
├── video1.csv              # Scènes (STEP3)
├── video1_audio.json       # Audio (STEP4)
├── video1_tracking.json    # Tracking optimisé pour AE (STEP6)
└── video1_ae.json          # Pré-traitement AE (STEP7)
```

## Configuration Essentielle par Étape

### STEP4 - Analyse Audio

**Pyannote (défaut, GPU si disponible)** :
```bash
HF_AUTH_TOKEN=ton_token_huggingface
AUDIO_DISABLE_GPU=0          # 1 pour forcer CPU
```

**Lemonfox (alternative cloud)** :
```bash
STEP4_USE_LEMONFOX=1
LEMONFOX_API_KEY=ta_cle_api
LEMONFOX_DEFAULT_LANGUAGE=fr
```

### STEP5 - Tracking Vidéo

**MediaPipe CPU (défaut recommandé)** :
```bash
# Vide = MediaPipe par défaut
STEP5_TRACKING_ENGINE=
TRACKING_CPU_WORKERS=15        # Ajuste selon tes cœurs CPU
```

**InsightFace GPU (optionnel)** :
```bash
STEP5_ENABLE_GPU=1
STEP5_TRACKING_ENGINE=insightface
STEP5_GPU_ENGINES=insightface
STEP5_GPU_MAX_VRAM_MB=2048     # Ajuste selon ta carte
```

### STEP6 - Réduction JSON

```bash
STEP6_INCLUDE_TRACKING_ANALYTICS=1
STEP6_INCLUDE_EXPRESSION_SUMMARY=1
```

## Commandes Utiles

### Vérification et Monitoring

```bash
# Test l'API
curl http://localhost:5000/api/system_monitor

# Statut d'une étape
curl http://localhost:5000/api/step_status/STEP1

# Logs en temps réel
tail -f logs/app.log

# Logs d'une étape spécifique
tail -f logs/step4/*.log
```

### Gestion des Problèmes

**Port déjà utilisé** :
```bash
lsof -i :5000
kill -9 <PID>
# ou utilise FLASK_PORT=5001
```

**FFmpeg manquant** :
```bash
ffmpeg -version
sudo apt install ffmpeg  # Ubuntu
brew install ffmpeg    # macOS
```

**Environnement corrompu** :
```bash
rm -rf env/
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Trade-offs par Mode d'Installation

| Mode d'installation | Temps | Coût | Risques | Quand l'utiliser |
|---------------------|-------|------|---------|-----------------|
| **Local (GPU)** | 15-30 min | Gratuit | Conflits deps si manuel | Développement, tests GPU |
| **Local (CPU only)** | 10-20 min | Gratuit | Performance limitée | Laptop, démo rapide |
| **Render Cloud** | 5-10 min | $5-20/mois | Configuration GPU | Production, équipe distante |
| **Docker** | 20-40 min | Variable | Complexité réseau | CI/CD, déploiement standardisé |

## Analogie : Pit-Stop vs Marathon

Pense à l'installation comme une course. Pour une **démonstration**, c'est un **pit-stop** : rapide, utilitaire, avec fallbacks CPU si GPU indisponible. Pour la **production**, c'est un **marathon** : préparation soignée des environnements, validation GPU, monitoring continu. Les deux utilisent la même piste (pipeline), mais avec des stratégies différentes.

## Tests et Validation

```bash
# Tests frontend (sécurité et performance)
npm run test:frontend

# Validation configuration
python -c "from config.settings import config; config.validate(); print('Config OK')"
```

## Monitoring et Diagnostics

**Endpoints API disponibles** :
- `GET /api/system/diagnostics` - informations système complètes
- `GET /api/system_monitor` - métriques temps réel
- `GET /api/csv_monitor_status` - statut webhook

```bash
# Diagnostics complets
curl http://localhost:5000/api/system/diagnostics | jq
```

## Pièges Courants et Solutions

### Piège #1 : Conflits de dépendances
**Solution** : Environnements virtuels isolés. Chaque étape a son propre environnement Python.

### Piège #2 : GPU non détecté
**Solution** : Le système fonctionne en CPU si GPU indisponible. Pour GPU :
```bash
nvidia-smi  # Vérifie les drivers
export CUDA_VISIBLE_DEVICES=0
```

### Piège #3 : Téléchargements automatiques
**Politique Dropbox-only** : Seules les URLs Dropbox directes et proxys PHP déclenchent un téléchargement automatique. Les autres sources nécessitent une action manuelle.

### Piège #4 : Logs non visibles
**Solution** : Vérifie les permissions et redémarre l'application. Les logs sont dans `logs/app.log` et `logs/step*/`.

## Production et Sécurité

**Mode production** :
```bash
DEBUG=false
FLASK_ENV=production
```

**Avec Gunicorn** :
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_new:APP_FLASK
```

**Sécurité** :
- Tokens obligatoires dans `.env`
- Aucun secret en dur dans le code
- Échappement XSS systématique
- Validation des entrées

## Support

Pour aller plus loin :
- Documentation complète : `docs/workflow/core/architecture.md`
- Logs détaillés : `logs/app.log`
- Configuration : `config/settings.py`

Le système est maintenant prêt. Lance ta première analyse vidéo et vois la puissance du pipeline MediaPipe en action.

---

## Golden Rule

**Utilise toujours les environnements dédiés ; sinon tu crées des conflits de dépendances impossibles à déboguer.**
