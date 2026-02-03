# Guide Utilisateur : Support GPU pour STEP5

> **🔴 Known Hotspot** – Critical complexity (radon F/E) in STEP5 workers. GPU operations require careful monitoring due to high complexity in `process_video_worker.py` and `run_tracking_manager.py`. See `../complexity_report.txt` for detailed analysis.

**Version** : 4.2+  
**Date** : 27 décembre 2025  
**Statut** : STABLE — GPU réservé exclusivement à InsightFace

---

## Vue d'ensemble

⚠️ **IMPORTANT** : Le support GPU pour STEP5 est **réservé exclusivement au moteur InsightFace**.

STEP5 supporte 2 modes :
- **Mode MediaPipe (défaut)** : `STEP5_TRACKING_ENGINE` vide (CPU)
- **InsightFace** : `STEP5_TRACKING_ENGINE=insightface` (GPU-only)

---

## 🔴 Critical Complexity Areas (GPU Operations)

### High-Risk Components Requiring Careful Monitoring

#### STEP5 Workers (Radon F/E)
- **`process_video_worker.py`** : Complexité critique (radon F) dans `main` et `process_frame_chunk`
- **`run_tracking_manager.py`** : Complexité critique (radon F) dans `main`
- **`face_engines.py`** : Complexité élevée (radon E) principalement sur InsightFace

#### GPU-Specific Risks
- **Memory Management** : OOM fréquent avec InsightFace GPU
- **Resource Contention** : 1 seul worker GPU séquentiel autorisé
- **Fallback Complexity** : Basculement CPU/GPU ajoute à la complexité
- **Error Recovery** : Les crashes GPU nécessitent des procédures de récupération spécifiques

#### Monitoring Recommendations
- Surveiller `CUDAExecutionProvider` dans les logs
- Vérifier l'utilisation VRAM toutes les 20 frames (profiling intégré)
- Implémenter des timeouts stricts pour les opérations GPU
- Tester les scénarios de fallback GPU→CPU

---

### Caractéristiques

✅ **Moteur compatible GPU** :
- ⚡ **InsightFace (GPU-only)** :
  - **Seul moteur autorisé** à utiliser le GPU depuis la stabilisation v4.2+
  - Réintroduit en mode séquentiel exclusif : le gestionnaire refuse de le lancer si `STEP5_ENABLE_GPU=0`, si l'engine n'est pas listé dans `STEP5_GPU_ENGINES`, ou si la validation GPU (`Config.check_gpu_availability()`) échoue.
  - Utilise un environnement dédié `insightface_env` (ONNX Runtime GPU + dépendances InsightFace). Override possible via `STEP5_INSIGHTFACE_ENV_PYTHON` si les venvs sont relocalisés.
  - Le manager complète automatiquement `LD_LIBRARY_PATH` avec les bibliothèques CUDA du venv InsightFace **et** celles du système (`/usr/lib/x86_64-linux-gnu`, `/usr/local/cuda-*/targets/...`) pour garantir que `CUDAExecutionProvider` soit disponible.

❌ **Moteurs en mode CPU-only uniquement** :
- **Mode MediaPipe (défaut)** : CPU (avec multiprocessing)

⚠️ **Contraintes importantes** :
- **1 seul worker GPU séquentiel** (pas de parallélisation GPU)
- **CPU-only reste le mode par défaut** pour tous les moteurs sauf InsightFace
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
[1/6] Checking NVIDIA GPU...
✓ GPU detected: NVIDIA GeForce GTX 1650
  VRAM: 4096 MiB
  Driver: 580.95.05

[4/6] Checking PyTorch CUDA support...
✓ PyTorch CUDA enabled
  PyTorch: 2.9.1+cu128
  CUDA available: True
  CUDA version: 12.8

[5/6] Checking ONNXRuntime providers...
✓ ONNX CUDA provider available (InsightFace GPU will work)
```

### Étape 2 : Installation des Dépendances GPU

```bash
# Installation manuelle dans insightface_env
source /mnt/venv_ext4/insightface_env/bin/activate
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu==1.23.2

# Vérifier l'installation
python -c "import onnxruntime as ort; print('Providers:', ort.get_available_providers())"
# Attendu: ['CUDAExecutionProvider', 'CPUExecutionProvider', ...]
```

### Étape 3 : Exporter LD_LIBRARY_PATH (CUDA providers)

Pour que ONNX Runtime charge correctement les bibliothèques CUDA embarquées dans `insightface_env`, exportez `LD_LIBRARY_PATH` avant de lancer STEP5 (ou ajoutez-le à votre profil shell) :

```bash
export LD_LIBRARY_PATH=/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cublas/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cuda_runtime/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cufft/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/curand/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cusolver/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cusparse/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/cudnn/lib:\
/mnt/venv_ext4/insightface_env/lib/python3.10/site-packages/nvidia/nvjitlink/lib:$LD_LIBRARY_PATH
```

> ℹ️ Le gestionnaire STEP5 injecte automatiquement ces chemins pour ses sous-processus, mais l'export manuel facilite les tests ponctuels (`python -c ...`, `pytest`, etc.).

---

## Configuration

### Fichier `.env`

Éditez `/home/kidpixel6/kidpixel_files/kidpixel/workflow_mediapipe/.env` :

```bash
# ========================
# 6b. SUPPORT GPU OPTIONNEL (v4.2+)
# ========================

# Activation globale GPU pour STEP5 (0=désactivé par défaut, 1=activé)
# IMPORTANT: GPU réservé exclusivement à InsightFace
STEP5_ENABLE_GPU=1

# Moteur compatible GPU : UNIQUEMENT 'insightface'
# Tous les autres moteurs sont forcés en mode CPU même si listés ici
STEP5_GPU_ENGINES=insightface

# Limite VRAM maximale (Mo) - Réserve mémoire pour STEP2 et système
# GTX 1650 (4096 Mo) : recommandé 2048 Mo pour laisser 2 Go libres
STEP5_GPU_MAX_VRAM_MB=2048

# Fallback automatique vers CPU si GPU échoue ou VRAM insuffisante
STEP5_GPU_FALLBACK_AUTO=1
```

> ℹ️ Depuis la restriction GPU du 27/12/2025, `STEP5_TF_GPU_ENV_PYTHON` n'existe plus.
> ℹ️ Le mode CPU par défaut est désormais le mode MediaPipe (engine vide).

### Lazy Imports MediaPipe

Pour minimiser le coût d'import, le système utilise un lazy import pour MediaPipe :

```python
# Dans process_video_worker_multiprocessing.py
def _ensure_mediapipe_loaded(required=False):
    """Import MediaPipe uniquement lorsque nécessaire."""
    if required:
        try:
            import mediapipe as mp
            return mp
        except ImportError as e:
            logger.error(f"MediaPipe required but not available: {e}")
            raise
    else:
        # Mode non requis : retourne None pour éviter l'import
        return None
```

- **Mode MediaPipe (défaut)** : utilise `required=True` lorsque MediaPipe est indispensable
- **Subprocess ONNXRuntime GPU** : les vérifications GPU utilisent `STEP5_INSIGHTFACE_ENV_PYTHON` pour isoler les tests ONNXRuntime GPU

### Validation dynamique (run_tracking_manager.py)

Au lancement, `workflow_scripts/step5/run_tracking_manager.py` applique systématiquement la logique suivante :

1. **Normalisation moteur** : si aucun moteur n'est fourni, le mode MediaPipe par défaut est utilisé (`STEP5_TRACKING_ENGINE` vide).
2. **Vérification d'éligibilité GPU** : seul InsightFace peut activer le GPU. En mode MediaPipe, le manager force l'exécution en CPU.
3. **`Config.check_gpu_availability()`** : la vérification matérielle tourne dans un sous-processus isolé pour vérifier VRAM, CUDA providers, etc.
4. **Fallback automatique** : si `available=False` et `STEP5_GPU_FALLBACK_AUTO=1`, le gestionnaire continue en mode CPU.
5. **Injection des librairies CUDA** : lorsqu'un worker InsightFace GPU est lancé, le gestionnaire ajoute les chemins `.../nvidia/*/lib` dans `LD_LIBRARY_PATH`.

### Configurations Recommandées

#### GTX 1650 (4 Go VRAM)

```bash
STEP5_ENABLE_GPU=1
STEP5_GPU_ENGINES=insightface          # Seul moteur GPU supporté
STEP5_GPU_MAX_VRAM_MB=2048             # Limite stricte
STEP5_TRACKING_ENGINE=insightface      # Moteur InsightFace
```

#### RTX 3060 (12 Go VRAM)

```bash
STEP5_ENABLE_GPU=1
STEP5_GPU_ENGINES=insightface
STEP5_GPU_MAX_VRAM_MB=8192
STEP5_TRACKING_ENGINE=insightface
```

---

## Utilisation

### Mode 1 : Via Interface Web

1. Accéder à l'interface Flask : `http://localhost:5000`
2. Onglet **Étape 5 : Suivi Vidéo**
3. Sélectionner le moteur :
   - **InsightFace** (GPU uniquement si `STEP5_ENABLE_GPU=1`)
   - **Mode MediaPipe par défaut** (CPU)
4. Lancer le traitement normalement

**Logs attendus** (console Flask) :
```
[INFO] GPU mode requested for engine: insightface
[INFO] GPU validation passed: VRAM 3.2 Go free, CUDA 12.8
[INFO] ✓ GPU mode ENABLED for insightface
```

**Logs mode MediaPipe (CPU)** :
```
[INFO] CPU-only mode (GPU disabled or not supported for this engine)
```

### Mode 2 : Ligne de Commande

```bash
cd workflow_scripts/step5

# Test avec InsightFace GPU (seul moteur GPU supporté)
STEP5_ENABLE_GPU=1 \
STEP5_GPU_ENGINES=insightface \
python run_tracking_manager.py \
  --videos_json_path ../../videos_to_track.json \
  --tracking_engine insightface \
  --cpu_internal_workers 1

# Test avec MediaPipe en mode CPU (même avec STEP5_ENABLE_GPU=1)
STEP5_ENABLE_GPU=1 \
STEP5_GPU_ENGINES=insightface \
python run_tracking_manager.py \
  --videos_json_path ../../videos_to_track.json \
  --cpu_internal_workers 15
```

**Variables d'environnement temporaires** :
```bash
# Activer InsightFace GPU pour cette session uniquement
STEP5_ENABLE_GPU=1 \
STEP5_GPU_ENGINES=insightface \
STEP5_TRACKING_ENGINE=insightface \
python run_tracking_manager.py --videos_json_path ...

# Forcer CPU même pour InsightFace (erreur attendue, InsightFace est GPU-only)
STEP5_ENABLE_GPU=0 \
STEP5_TRACKING_ENGINE=insightface \
python run_tracking_manager.py --videos_json_path ...
# Note: InsightFace ne fonctionnera pas en mode CPU, erreur attendue
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
STEP5_ENABLE_PROFILING=1
```

**Logs attendus** (dans les sorties worker) :
```
[InsightFace] Available ONNXRuntime providers: ['CUDAExecutionProvider', ...]
[PROFILING] InsightFace after 20 frames: resize=12.3ms/frame, detect=8.5ms/frame, post=20.8ms/frame
```

---

## Troubleshooting

### Problème 1 : "GPU mode is reserved for InsightFace only"

**Symptôme** :
```
[INFO] CPU-only mode (GPU disabled or not supported for this engine)
```

**Explication** : C'est le comportement attendu. Seul InsightFace peut utiliser le GPU.

**Solution** : Pour utiliser le GPU, basculer vers InsightFace :
```bash
STEP5_TRACKING_ENGINE=insightface
STEP5_GPU_ENGINES=insightface
```

### Problème 2 : "CUDA provider NOT available"

**Symptôme** :
```
⚠ ONNX CUDA provider NOT available (InsightFace GPU will not work)
```

**Solution** :
```bash
source /mnt/venv_ext4/insightface_env/bin/activate
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu==1.23.2

# Vérifier
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

### Problème 3 : "GPU requested but unavailable: VRAM insuffisante"

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

### Problème 4 : OOM (Out of Memory) pendant le traitement

**Symptôme** :
```
RuntimeError: CUDA out of memory. Tried to allocate 1.50 GiB
```

**Solutions** :
1. **Réduire la résolution** :
   ```bash
   # Dans .env
   STEP5_INSIGHTFACE_MAX_WIDTH=640   # Au lieu de 1280
   STEP5_INSIGHTFACE_DET_SIZE=480    # Au lieu de 640
   ```

2. **Traiter 1 vidéo à la fois** :
   - Ne pas lancer plusieurs instances STEP5 simultanément
   - Le worker GPU est déjà séquentiel (1 vidéo à la fois)

---

## Performances Attendues

### Comparatif GPU vs CPU (GTX 1650, vidéo 1080p)

| Moteur | Mode | FPS Moyen | VRAM Utilisée | CPU % |
|--------|------|-----------|---------------|-------|
| **InsightFace** | 1 worker GPU | 25-30 FPS | 1500 Mo | 20% |
| **MediaPipe (défaut)** | 15 workers CPU | 25-30 FPS | 0 Mo | 100% |

**Notes** :
- Les FPS GPU sont pour **1 vidéo à la fois** (worker séquentiel)
- Pour traiter **10+ vidéos simultanément**, le mode CPU reste plus rapide (parallélisation massive)

### Cas d'Usage Recommandés

✅ **GPU InsightFace recommandé** :
- Traitement prioritaire de 1-2 vidéos urgentes nécessitant InsightFace
- Détection de visages robuste avec RetinaFace
- Latence réduite pour workflows interactifs

❌ **CPU préférable** :
- Batch processing de 10+ vidéos (tous moteurs)
- Utilisation du mode MediaPipe (CPU)
- Systèmes avec VRAM limitée (< 2 Go libres)
- STEP2 (conversion vidéo) actif simultanément

---

## Limitations et Risques

### Limitations Techniques

1. **GPU réservé à InsightFace uniquement**
   - Le mode MediaPipe fonctionne en CPU
   - Décision de stabilité basée sur les tests v4.2+

2. **1 worker GPU séquentiel uniquement**
   - Pas de parallélisation GPU (contrairement aux 15 workers CPU)
   - VRAM 4 Go insuffisante pour plusieurs workers GPU simultanés

3. **Contention VRAM avec STEP2**
   - STEP2 (NVENC) consomme 200-400 Mo
   - Risque d'OOM si STEP2 et STEP5 actifs simultanément

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
tests/unit/test_step5_gpu_support.py::TestInsightFaceGPU::test_insightface_gpu_only PASSED

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

Pour proposer des améliorations (support d'autres moteurs en GPU, TensorRT, etc.), consulter :
- Rapport de faisabilité : `docs/workflow/STEP5_GPU_FEASIBILITY.md`
- Memory Bank : `memory-bank/decisionLog.md`

---

## Limitations et Contraintes

### Restrictions GPU (v4.2+)

⚠️ **Important** : Suite à la stabilisation du 27/12/2025, le support GPU est soumis aux contraintes suivantes :

- **GPU réservé exclusivement à InsightFace** : le mode MediaPipe reste CPU
- **1 worker GPU séquentiel uniquement** : Aucune parallélisation GPU possible
- **Pas de fallback GPU pour les autres moteurs** : Même avec `STEP5_ENABLE_GPU=1`, les moteurs non-InsightFace restent en CPU
- **Dépendances isolées** : Nécessite `insightface_env` avec `onnxruntime-gpu`

### Considérations Performance

- **CPU recommandé pour batch** : Pour 10+ vidéos, le mode CPU avec 15 workers offre de meilleures performances globales
- **VRAM partagée** : STEP2 (NVENC) peut entrer en contention avec InsightFace GPU sur les cartes < 8 Go
- **Overhead GPU** : L'initialisation GPU ajoute ~2-3 secondes de démarrage par vidéo

### Alternatives Recommandées

Pour des performances optimales sans GPU :
- **MediaPipe CPU** : 15 workers multiprocessing, le plus rapide pour la plupart des cas

---

## Références

- [ONNXRuntime CUDA Provider](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
- [InsightFace Documentation](https://github.com/deepinsight/insightface)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- Standards de développement : `.windsurf/rules/codingstandards.md`
