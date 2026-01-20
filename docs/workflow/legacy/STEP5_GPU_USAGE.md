# Guide Utilisateur : Support GPU pour STEP5

**Version** : 4.2+  
**Date** : 22 décembre 2025  
**Statut** : EXPÉRIMENTAL — 1 worker GPU séquentiel uniquement

---

## Vue d'ensemble

⚠️ **IMPORTANT** : Le support GPU pour STEP5 est **réservé exclusivement au moteur InsightFace**. Tous les autres moteurs (MediaPipe Face Landmarker, OpenSeeFace, OpenCV YuNet + PyFeat, EOS) s'exécutent automatiquement en mode CPU-only, même si `STEP5_ENABLE_GPU=1` est activé.

### Caractéristiques

✅ **Moteurs compatibles ou partiellement accélérés** :
- **MediaPipe Face Landmarker** : TensorFlow Lite GPU delegate complet (détection, landmarks, blendshapes).
- **OpenCV YuNet + PyFeat** : le détecteur YuNet reste CPU (limitation OpenCV), mais le pipeline aval (FaceMesh ONNX + py-feat) s’exécute sur GPU via ONNX Runtime/PyTorch lorsque `use_gpu=True`. Expect ~5-6× de gains sur les blendshapes.
- ⚠️ **OpenSeeFace (CUDA dépendant)** :
  - Depuis la migration 2025-12-21, le moteur peut utiliser ONNX Runtime GPU **uniquement** si `onnxruntime-gpu==1.23.2` (ou supérieur) est installé **et** que les modèles fournis ont été régénérés sans opérateur `FusedConv+Clip`.  
  - Par défaut, les modèles legacy continuent de fonctionner en CPU (log `OpenSeeFace GPU provider unavailable, falling back to CPU`). Le fallback est automatique afin d’éviter toute régression.
  - Pour activer le GPU :  
    1. Installer `onnxruntime-gpu`.  
    2. Vérifier que les providers listent `CUDAExecutionProvider`.  
    3. Mettre à jour les modèles via `./workflow_scripts/step5/models/engines/openseeface/README.md` (procédure décrite).  
    4. Définir `STEP5_GPU_ENGINES=openseeface` et relancer STEP5.
- ⚡ **InsightFace (GPU-only)** :
  - Réintroduit en mode séquentiel exclusif : le gestionnaire refuse de le lancer si `STEP5_ENABLE_GPU=0`, si l’engine n’est pas listé dans `STEP5_GPU_ENGINES`, ou si la validation GPU (`Config.check_gpu_availability()`) échoue.
  - Utilise un environnement dédié `insightface_env` (ONNX Runtime GPU + dépendances InsightFace). Override possible via `STEP5_INSIGHTFACE_ENV_PYTHON` si les venvs sont relocalisés.
  - Le manager complète automatiquement `LD_LIBRARY_PATH` avec les bibliothèques CUDA du venv InsightFace **et** celles du système (`/usr/lib/x86_64-linux-gnu`, `/usr/local/cuda-*/targets/...`) pour garantir que `CUDAExecutionProvider` soit disponible.

❌ **Non compatibles** :
- OpenCV Haar seul (détection pure CPU)
- EOS (CPU-only)

⚠️ **Contraintes importantes** :
- **1 seul worker GPU séquentiel** (pas de parallélisation GPU)
- **CPU-only reste le mode par défaut** (stabilité prouvée v4.1)
- **Fallback automatique vers CPU** si GPU indisponible (log explicite `Auto-fallback to CPU enabled`)

---

## Prérequis Matériels

### GPU Compatible

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| **GPU** | NVIDIA GTX 1650 (4 Go VRAM) | RTX 3060 (12 Go VRAM) |
| **VRAM** | 2 Go libres | 4+ Go libres |
| **Compute Capability** | 7.5+ (Turing) | 8.6+ (Ampere) |
| **Driver NVIDIA** | ≥ 525.x | ≥ 535.x |
| **CUDA Toolkit** | 12.0+ | 12.8+ |

### Vérification Matérielle

```bash
# Vérifier GPU et VRAM
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv

# Vérifier Compute Capability
nvidia-smi --query-gpu=compute_cap --format=csv,noheader
```

**Exemple de sortie attendue** :
```
NVIDIA GeForce GTX 1650, 580.95.05, 4096 MiB, 3500 MiB
7.5
```

---

## Installation

### Étape 1 : Validation des Prérequis

```bash
cd /home/kidpixel6/kidpixel_files/kidpixel/workflow_mediapipe

# Lancer le script de validation
./scripts/validate_gpu_prerequisites.sh
```

**Sortie attendue** :
```
[1/7] Checking NVIDIA GPU...
✓ GPU detected: NVIDIA GeForce GTX 1650
  VRAM: 4096 MiB
  Driver: 580.95.05

[4/7] Checking PyTorch CUDA support...
✓ PyTorch CUDA enabled
  PyTorch: 2.9.1+cu128
  CUDA available: True
  CUDA version: 12.8

[5/7] Checking ONNXRuntime providers...
⚠ ONNX CUDA provider NOT available (OpenSeeFace GPU will not work)
  Install: pip install onnxruntime-gpu

[6/7] Checking TensorFlow GPU...
⚠ TensorFlow not installed (MediaPipe GPU delegate unavailable)
  Install: pip install tensorflow==2.15.0
```

### Étape 2 : Installation ONNXRuntime GPU (pour OpenSeeFace)

```bash
# Installation automatique
./scripts/install_onnxruntime_gpu.sh
```

**OU manuellement** :
```bash
source /mnt/venv_ext4/tracking_env/bin/activate
pip uninstall -y onnxruntime
pip install onnxruntime-gpu==1.23.2

# Vérifier l'installation
python -c "import onnxruntime as ort; print('Providers:', ort.get_available_providers())"
# Attendu: ['CUDAExecutionProvider', 'CPUExecutionProvider', ...]
```

### Étape 3 : Installation TensorFlow GPU (pour MediaPipe)

```bash
# Installation interactive (2 Go de téléchargement)
./scripts/install_tensorflow_gpu.sh
```

**OU manuellement** :
```bash
source /mnt/venv_ext4/tracking_env/bin/activate
pip install tensorflow==2.15.0

# Vérifier l'installation
python -c "import tensorflow as tf; print('GPU devices:', tf.config.list_physical_devices('GPU'))"
```

**⚠️ Note** : TensorFlow GPU est volumineux (~2 Go). Si vous utilisez uniquement OpenSeeFace, vous pouvez l'omettre.

### Étape 4 : Validation Finale

```bash
./scripts/validate_gpu_prerequisites.sh
```

**Sortie attendue après installation** :
```
SUMMARY
✓ All checks passed

Next steps:
  1. Enable GPU: Set STEP5_ENABLE_GPU=1 in .env
  2. Test with a single video
```

### ⚙️ Option recommandée : venv dédié `tf_gpu_env`

Pour éviter les conflits entre TensorFlow (qui exige `ml-dtypes~=0.2.x`) et JAX (`ml-dtypes>=0.5`), un environnement virtuel séparé est fourni pour TensorFlow :

```bash
# 1. Créer le venv dédié
python3 -m venv /mnt/venv_ext4/tf_gpu_env

# 2. Installer TensorFlow GPU à l'intérieur
source /mnt/venv_ext4/tf_gpu_env/bin/activate
pip install --upgrade pip setuptools wheel
pip install tensorflow==2.15.0 tensorflow-io-gcs-filesystem==0.37.1

# 3. Vérifier
python -c "import tensorflow as tf; print('GPU devices:', tf.config.list_physical_devices('GPU'))"
```

Puis, dans `.env`, pointez `STEP5_TF_GPU_ENV_PYTHON` vers ce venv :

```bash
STEP5_TF_GPU_ENV_PYTHON=/mnt/venv_ext4/tf_gpu_env/bin/python
```

Le gestionnaire STEP5 utilisera automatiquement cet interpréteur pour les jobs MediaPipe GPU tout en laissant `tracking_env` intact (PyTorch + ONNX). Si la variable est vide, `tracking_env` sera utilisé (TensorFlow doit alors y être installé).

### Étape 5 : Exporter LD_LIBRARY_PATH (CUDA providers)

Pour que ONNX Runtime charge correctement les bibliothèques CUDA embarquées dans `tracking_env`, exportez `LD_LIBRARY_PATH` avant de lancer STEP5 (ou ajoutez-le à votre profil shell) :

```bash
export LD_LIBRARY_PATH=/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cublas/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cuda_runtime/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cufft/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/curand/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cusolver/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cusparse/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/cudnn/lib:\
/mnt/venv_ext4/tracking_env/lib/python3.10/site-packages/nvidia/nvjitlink/lib:$LD_LIBRARY_PATH
```

Astuce : utilisez `/mnt/venv_ext4/tracking_env/bin/python - <<'PY' ... PY` pour vérifier la présence des providers :

```bash
LD_LIBRARY_PATH=... \
/mnt/venv_ext4/tracking_env/bin/python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

> ℹ️ Le gestionnaire STEP5 injecte automatiquement ces chemins pour ses sous-processus, mais l’export manuel facilite les tests ponctuels (`python -c ...`, `pytest`, etc.).

---

## Configuration

### Fichier `.env`

Éditez `/home/kidpixel6/kidpixel_files/kidpixel/workflow_mediapipe/.env` :

```bash
# ========================
# 6b. SUPPORT GPU OPTIONNEL (v4.2+)
# ========================

# Activation globale GPU pour STEP5 (0=désactivé par défaut, 1=activé)
STEP5_ENABLE_GPU=1

# Moteurs compatibles GPU (séparés par virgule)
# Options: mediapipe_landmarker, openseeface, opencv_yunet_pyfeat, insightface, all
STEP5_GPU_ENGINES=mediapipe_landmarker,openseeface,opencv_yunet_pyfeat,insightface

# Limite VRAM maximale (Mo) - Réserve mémoire pour STEP2 et système
# GTX 1650 (4096 Mo) : recommandé 2048 Mo pour laisser 2 Go libres
STEP5_GPU_MAX_VRAM_MB=2048

# Profiling GPU (logs utilisation VRAM/temps GPU)
STEP5_GPU_PROFILING=0

# Fallback automatique vers CPU si GPU échoue ou VRAM insuffisante
STEP5_GPU_FALLBACK_AUTO=1
```

### Validation dynamique (run_tracking_manager.py)

Au lancement, `workflow_scripts/step5/run_tracking_manager.py` applique systématiquement la logique suivante :

1. **Normalisation moteur** : si aucun moteur n’est fourni, `mediapipe_landmarker` est utilisé.  
2. **Vérification d’éligibilité** : l’engine doit figurer dans `STEP5_GPU_ENGINES` (ou `all`). Sinon, un message `Engine xxx does not support GPU, forcing CPU-only mode` est loggé et `args.disable_gpu` passe à `True`.  
3. **`Config.check_gpu_availability()`** : la vérification matérielle tourne dans un sous-processus isolé (`STEP5_TF_GPU_ENV_PYTHON` si défini) afin d’éviter l’import direct de TensorFlow dans `tracking_env`. Cette étape contrôle :  
   - VRAM restante (`STEP5_GPU_MAX_VRAM_MB`),  
   - Disponibilité des providers ONNX (`CUDAExecutionProvider`),  
   - Visibilité TensorFlow (TFLite delegate).  
4. **Fallback automatique** : si `available=False`, le gestionnaire respecte `STEP5_GPU_FALLBACK_AUTO`.  
   - `1` → log `Auto-fallback to CPU enabled`, l’exécution continue en mode CPU.  
   - `0` → levée d’exception avec la raison (`VRAM insuffisante`, `TensorFlow manquant`, etc.).  
5. **Injection des librairies CUDA** : lorsqu’un worker GPU est lancé, le gestionnaire ajoute les chemins `.../nvidia/*/lib` du `tracking_env` dans `LD_LIBRARY_PATH` du processus enfant. Cela garantit que `onnxruntime-gpu` et TensorFlow retrouvent leurs dépendances même si l’IDE n’a pas exporté ces variables.
6. **Tracing explicite** : les logs contiennent toujours la séquence suivante :  
   ```
   [INFO] GPU mode requested for engine: mediapipe_landmarker
   [INFO] GPU validation passed: VRAM 3.2 Go free, CUDA 12.8
   [INFO] ✓ GPU mode ENABLED for mediapipe_landmarker
   ```
   ou, en cas d’échec :  
   ```
   [WARNING] GPU requested but unavailable: VRAM insuffisante (1.2 Go libres < 2.0 Go requis)
   [INFO] Auto-fallback to CPU enabled
   ```

### Configurations Recommandées

#### GTX 1650 (4 Go VRAM)

```bash
STEP5_ENABLE_GPU=1
STEP5_GPU_ENGINES=openseeface          # Commencer avec OpenSeeFace uniquement
STEP5_GPU_MAX_VRAM_MB=2048             # Limite stricte
STEP5_GPU_PROFILING=1                  # Activer pour surveiller VRAM
STEP5_TRACKING_ENGINE=openseeface      # Forcer moteur OpenSeeFace
```

#### RTX 3060 (12 Go VRAM)

```bash
STEP5_ENABLE_GPU=1
STEP5_GPU_ENGINES=mediapipe_landmarker,openseeface
STEP5_GPU_MAX_VRAM_MB=8192
STEP5_GPU_PROFILING=0
```

---

## Utilisation

### Mode 1 : Via Interface Web

1. Accéder à l'interface Flask : `http://localhost:5000`
2. Onglet **Étape 5 : Suivi Vidéo**
3. Sélectionner le moteur :
   - **MediaPipe Face Landmarker** (GPU si `STEP5_ENABLE_GPU=1`)
   - **OpenSeeFace** (GPU si configuré)
4. Lancer le traitement normalement

**Logs attendus** (console Flask) :
```
[INFO] GPU mode requested for engine: mediapipe_landmarker
[INFO] GPU validation passed: VRAM 3.2 Go free, CUDA 12.8
[INFO] ✓ GPU mode ENABLED for mediapipe_landmarker
[INFO] [WORKER-12345] Attempting to use GPU delegate for MediaPipe
```

### Mode 2 : Ligne de Commande

```bash
cd workflow_scripts/step5

# Test avec MediaPipe GPU
python run_tracking_manager.py \
  --videos_json_path ../../videos_to_track.json \
  --models_dir models \
  --tracking_engine mediapipe_landmarker \
  --cpu_internal_workers 1

# Test avec OpenSeeFace GPU
python run_tracking_manager.py \
  --videos_json_path ../../videos_to_track.json \
  --models_dir models \
  --tracking_engine openseeface \
  --cpu_internal_workers 1

# Test avec InsightFace GPU-only
STEP5_ENABLE_GPU=1 \
STEP5_GPU_ENGINES=mediapipe_landmarker,openseeface,insightface \
python run_tracking_manager.py \
  --videos_json_path ../../videos_to_track.json \
  --tracking_engine insightface \
  --cpu_internal_workers 1
```

**Variables d'environnement temporaires** :
```bash
# Activer GPU pour cette session uniquement
STEP5_ENABLE_GPU=1 STEP5_GPU_ENGINES=openseeface \
python run_tracking_manager.py --videos_json_path ...

# InsightFace uniquement pour ce run
STEP5_ENABLE_GPU=1 \
STEP5_GPU_ENGINES=insightface \
STEP5_TRACKING_ENGINE=insightface \
python run_tracking_manager.py --videos_json_path ...
```

---

## Monitoring et Profiling

### Surveillance VRAM en Temps Réel

**Terminal 1** : Lancer STEP5
```bash
# Via interface web ou CLI
```

**Terminal 2** : Surveiller VRAM
```bash
watch -n 1 'nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.free --format=csv,noheader'
```

**Sortie attendue** :
```
45 %, 38 %, 1500 MiB, 2596 MiB
```

### Logs de Profiling GPU

Activer dans `.env` :
```bash
STEP5_GPU_PROFILING=1
```

**Logs attendus** (dans les sorties worker) :
```
[OpenSeeFace] Detection session using provider: CUDAExecutionProvider
[OpenSeeFace] Landmark session using provider: CUDAExecutionProvider
[PROFILING] Frame 20: detection=12.3ms, landmarks=8.5ms, total=20.8ms, VRAM=1450MB
```

### Vérification rapide via pytest

Pour confirmer que vos logs GPU contiennent `use_gpu=True` et mentionnent `CUDAExecutionProvider`, exécutez le test suivant :

```bash
pytest tests/unit/test_step5_gpu_logs.py -k cuda_provider -v
```

Ce test utilise une fixture qui simule un log worker et vérifie la présence des signatures GPU. Vous pouvez adapter cette fixture pour pointer vers un log réel (`logs/step5/worker_GPU_*.log`) si nécessaire.

---

## Troubleshooting

### Problème 1 : "CUDA provider NOT available"

**Symptôme** :
```
⚠ ONNX CUDA provider NOT available (OpenSeeFace GPU will not work)
```

**Solution** :
```bash
source /mnt/venv_ext4/tracking_env/bin/activate
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu==1.23.2

# Vérifier
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

### Problème 2 : "GPU requested but unavailable: VRAM insuffisante"

**Symptôme** :
```
[WARNING] GPU requested but unavailable: VRAM insuffisante (1.2 Go libres < 1.5 Go)
[INFO] Auto-fallback to CPU enabled
```

**Causes possibles** :
1. STEP2 (conversion vidéo) utilise déjà le GPU
2. Autres processus consomment la VRAM

**Solutions** :
```bash
# 1. Libérer VRAM : arrêter STEP2 avant STEP5
# 2. Réduire la limite VRAM
STEP5_GPU_MAX_VRAM_MB=1024  # Essayer avec 1 Go

# 3. Vérifier processus GPU actifs
nvidia-smi
# Tuer processus si nécessaire : kill <PID>
```

### Problème 3 : "TensorFlow GPU not available"

**Symptôme** :
```
[WARNING] MediaPipe GPU unavailable (install tensorflow-gpu)
```

**Solution** :
```bash
./scripts/install_tensorflow_gpu.sh

# OU
source /mnt/venv_ext4/tracking_env/bin/activate
pip install tensorflow==2.15.0

# Vérifier
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### Problème 4 : OOM (Out of Memory) pendant le traitement

**Symptôme** :
```
RuntimeError: CUDA out of memory. Tried to allocate 1.50 GiB
```

**Solutions** :
1. **Réduire la résolution** :
   ```bash
   # Dans .env
   STEP5_MEDIAPIPE_MAX_WIDTH=640   # Au lieu de 1280
   STEP5_OPENSEEFACE_MAX_WIDTH=640
   ```

2. **Traiter 1 vidéo à la fois** :
   - Ne pas lancer plusieurs instances STEP5 simultanément
   - Le worker GPU est déjà séquentiel (1 vidéo à la fois)

3. **Forcer CPU pour certaines vidéos** :
   ```bash
   STEP5_ENABLE_GPU=0 python run_tracking_manager.py ...
   ```

### Problème 5 : "CUDA provider requested but not active"

**Symptôme** :
```
[WARNING] [OpenSeeFace] CUDA provider requested but not active (falling back to CPU)
```

**Causes** :
- onnxruntime-gpu mal installé
- Conflit avec onnxruntime CPU

**Solution** :
```bash
source /mnt/venv_ext4/tracking_env/bin/activate
pip list | grep onnx  # Vérifier qu'il n'y a qu'un seul onnxruntime

# Réinstallation propre
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu==1.23.2
```

---

## Performances Attendues

### Comparatif GPU vs CPU (GTX 1650, vidéo 1080p)

| Moteur | Mode | FPS Moyen | VRAM Utilisée | CPU % |
|--------|------|-----------|---------------|-------|
| **MediaPipe** | 15 workers CPU | 25-30 FPS | 0 Mo | 100% |
| **MediaPipe** | 1 worker GPU | 35-45 FPS | 800 Mo | 30% |
| **OpenSeeFace** | 15 workers CPU | 18-22 FPS | 0 Mo | 100% |
| **OpenSeeFace** | 1 worker GPU | 28-35 FPS | 600 Mo | 25% |

**Notes** :
- Les FPS GPU sont pour **1 vidéo à la fois** (worker séquentiel)
- Pour traiter **10+ vidéos simultanément**, le mode CPU reste plus rapide (parallélisation massive)

### Cas d'Usage Recommandés

✅ **GPU recommandé** :
- Traitement prioritaire de 1-2 vidéos urgentes
- Preview temps réel avec blendshapes
- Latence réduite pour workflows interactifs

❌ **CPU préférable** :
- Batch processing de 10+ vidéos
- Systèmes avec VRAM limitée (< 3 Go libres)
- STEP2 (conversion vidéo) actif simultanément

---

## Limitations et Risques

### Limitations Techniques

1. **1 worker GPU séquentiel uniquement**
   - Pas de parallélisation GPU (contrairement aux 15 workers CPU)
   - VRAM 4 Go insuffisante pour plusieurs workers GPU simultanés

2. **Contention VRAM avec STEP2**
   - STEP2 (NVENC) consomme 200-400 Mo
   - Risque d'OOM si STEP2 et STEP5 actifs simultanément

3. **Pas de Tensor Cores sur GTX 1650**
   - Pas d'accélération FP16 matérielle
   - Gains GPU ~40-60% vs ~80-100% sur RTX

4. **TensorFlow GPU volumineux**
   - Ajoute ~2 Go à l'environnement virtuel
   - Installation longue (5-10 min)

### Risques Identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **OOM sur vidéos 4K** | Élevé | Downscale auto si VRAM < 1.5 Go libres |
| **Contention STEP2** | Moyen | Monitoring VRAM, limiter `STEP5_GPU_MAX_VRAM_MB` |
| **Regression accuracy** | Faible | Tests unitaires (IOU > 0.95) |
| **Instabilité pilote** | Faible | Fallback CPU automatique activé |

---

## Désactivation du Mode GPU

### Temporaire (session uniquement)

```bash
# Ligne de commande
STEP5_ENABLE_GPU=0 python run_tracking_manager.py ...

# Interface web : arrêter Flask, définir variable, relancer
export STEP5_ENABLE_GPU=0
python app_new.py
```

### Permanente

Éditez `.env` :
```bash
STEP5_ENABLE_GPU=0
```

Le système rebasculera automatiquement sur le mode CPU-only (15 workers internes, v4.1).

---

## Tests Automatisés

### Exécution des Tests GPU

```bash
# Tests unitaires (validation providers, factory functions)
pytest tests/unit/test_step5_gpu_support.py -v

# Tests GPU uniquement (nécessite GPU actif)
pytest tests/unit/test_step5_gpu_support.py -v -m gpu

# Tests sans GPU (CI/CD)
pytest tests/unit/test_step5_gpu_support.py -v -m "not gpu"
```

**Exemple de sortie** :
```
tests/unit/test_step5_gpu_support.py::TestGPUAvailability::test_pytorch_cuda_available PASSED
tests/unit/test_step5_gpu_support.py::TestConfigGPUValidation::test_check_gpu_availability_function PASSED
tests/unit/test_step5_gpu_support.py::TestOpenSeeFaceGPU::test_openseeface_engine_gpu_flag PASSED

====== 8 passed in 3.42s ======
```

---

## Support et Contribution

### Signaler un Problème

Fournir les informations suivantes :
1. Sortie de `./scripts/validate_gpu_prerequisites.sh`
2. Configuration `.env` (section GPU)
3. Logs complets du worker (`logs/step5_*.log`)
4. Sortie de `nvidia-smi` pendant l'erreur

### Améliorer le Support GPU

Pour proposer des améliorations (batch GPU, TensorRT, etc.), consulter :
- Rapport de faisabilité : `docs/workflow/STEP5_GPU_FEASIBILITY.md`
- Backlog technique : section 8 du rapport

---

## Références

- [ONNXRuntime CUDA Provider](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
- [TensorFlow Lite GPU Delegate](https://www.tensorflow.org/lite/performance/gpu)
- [MediaPipe GPU Support](https://developers.google.com/mediapipe/framework/framework_concepts/gpu)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- Standards de développement : `docs/workflow/codingstandards.md`
