# Tracking Vidéo

**TL;DR** : Détection faciale avec MediaPipe (CPU multiprocessing) ou InsightFace (GPU unique). 478 landmarks + 52 blendshapes ARKit par frame. Architecture simplifiée : pas d'OpenCV/EOS/YuNet depuis v4.3.

## Le Problème : Tracking Manuel Impossible

Tu dois suivre les visages et expressions dans tes vidéos frame par frame, mais le faire manuellement est inenvisageable pour des contenus longs. Tu as besoin d'une solution automatique qui détecte les visages, extrait les points faciaux précis, et génère les données d'animation 3D.

## Notre Solution : Duo de Tracking Simplifié

Nous utilisons deux approches complémentaires : MediaPipe pour le traitement CPU robuste en multiprocessing, et InsightFace pour la haute précision GPU. Le système génère des données denses avec landmarks faciaux et blendshapes ARKit, parfaitement synchronisées avec les frames vidéo. **Les moteurs historiques (OpenCV, YuNet, EOS, OpenSeeFace) ont été retirés en v4.3**.

### ❌ Anciens moteurs retirés (anti-pattern)
```bash
# Approche obsolète - moteurs supprimés en v4.3
STEP5_TRACKING_ENGINE=yunet      # Plus supporté
STEP5_TRACKING_ENGINE=opencv     # Plus supporté  
STEP5_TRACKING_ENGINE=eos        # Plus supporté
STEP5_TRACKING_ENGINE=openseeface # Plus supporté
# Résultat : erreur de validation, fallback MediaPipe automatique
```

### ✅ Duo simplifié (pattern recommandé)
```python
# Approche claire - choix explicite du moteur
if gpu_available and high_precision_required:
    engine = "insightface"  # GPU haute précision, worker unique
else:
    engine = ""            # vide = MediaPipe CPU, 15 workers
# Résultat : ressources optimisées selon le besoin
```

### Flux de Tracking Intelligent

1. **Découverte vidéos** : Scan des projets avec vidéos et analyses audio
2. **Sélection moteur** : MediaPipe (CPU) ou InsightFace (GPU) selon configuration
3. **Multiprocessing** : Workers parallèles pour traitement optimisé
4. **Détection faciale** : Identification des visages par frame
5. **Extraction landmarks** : 468 points faciaux précis
6. **Génération blendshapes** : 52 coefficients ARKit pour animation 3D
7. **Export JSON** : Structure dense optimisée pour STEP6

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 5 : Tracking vidéo" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP5

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
# Mode MediaPipe CPU (défaut)
source tracking_env_slim/bin/activate
cd projets_extraits
python ../workflow_scripts/step5/run_tracking_manager.py

# Mode InsightFace GPU (optionnel)
STEP5_TRACKING_ENGINE=insightface python ../workflow_scripts/step5/run_tracking_manager.py
```

### Résultat Attendu

```
# Fichier JSON généré
projets_extraits/projet_camille_001/docs/video1_tracking.json

# Contenu JSON simplifié
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "tracked_objects": [
    {
      "frame": 1,
      "faces": [
        {
          "id": 0,
          "landmarks": [[x1,y1,z1], [x2,y2,z2], ...],
          "blendshapes": {
            "jawOpen": 0.12,
            "mouthSmileLeft": 0.34,
            ...
          }
        }
      ]
    }
  ]
}
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Moteur de tracking (défaut: MediaPipe)
STEP5_TRACKING_ENGINE=              # vide = MediaPipe, "insightface" = GPU

# GPU (réservé à InsightFace)
STEP5_ENABLE_GPU=0                  # 1 pour activer GPU InsightFace
STEP5_GPU_ENGINES=insightface        # Moteurs GPU autorisés
STEP5_GPU_FALLBACK_AUTO=1           # Bascule CPU auto si GPU échoue

# Performance CPU (MediaPipe)
TRACKING_CPU_WORKERS=15              # Workers MediaPipe (défaut)
STEP5_BLENDSHAPES_THROTTLE_N=2       # Calcul blendshapes toutes les N frames

# Options avancées
STEP5_ENABLE_PROFILING=0            # Logs performance toutes les 20 frames
STEP5_EXPORT_VERBOSE_FIELDS=0        # Export landmarks/verbose
```

> **Note v4.3** : Les variables suivantes ont été supprimées et ne sont plus prises en compte :
> - `STEP5_ENABLE_OBJECT_DETECTION` (plus de fallback object detector)
> - `STEP5_OPENCV_*`, `STEP5_YUNET_*`, `STEP5_EOS_*`, `STEP5_OPENSEEFACE_*` (moteurs retirés)
> - `STEP5_BLENDSHAPES_PROFILE` (profil unique conservé)

### Configuration MediaPipe (CPU)

```json
{
  "mediapipe": {
    "max_faces": 5,
    "min_detection_confidence": 0.5,
    "model_complexity": 1
  }
}
```

### Configuration InsightFace (GPU)

```json
{
  "insightface": {
    "gpu_only": true,
    "model_name": "antelopev2",
    "max_faces": 5,
    "min_face_size": 32
  }
}
```

## Les Deux Moteurs de Tracking

> **Architecture v4.3** : Seuls MediaPipe et InsightFace sont supportés. Les autres moteurs ont été retirés pour simplifier la maintenance et améliorer la fiabilité.

### MediaPipe (CPU - Défaut Recommandé)

**Avantages** :
- **Stable** : Pas de dépendance GPU
- **Multiprocessing** : 15 workers parallèles
- **Léger** : Environnement `tracking_env_slim` minimal
- **Compatible** : Fonctionne sur toutes les machines

**Caractéristiques** :
- 478 landmarks faciaux
- 52 blendshapes ARKit
- 15 workers multiprocessing
- CPU-only (jamais de GPU même si activé)
- Throttling blendshapes configurable

**Cas d'usage** :
- Production stable
- Traitement batch massif
- Machines sans GPU
- Environnements contraints

### InsightFace (GPU - Optionnel Haute Précision)

**Avantages** :
- **Précision supérieure** : RetinaFace + Antelopev2
- **Embeddings faciaux** : Vecteurs par visage
- **GPU optimisé** : ONNX Runtime CUDA
- **Haute qualité** : Détection plus robuste

**Contraintes** :
- GPU NVIDIA obligatoire (CUDA ≥ 12.0)
- 2+ Go VRAM minimum (4+ recommandés)
- **1 worker séquentiel** (pas de parallélisme)
- Environnement `insightface_env` dédié

**Cas d'usage** :
- Haute précision requise
- GPU disponible
- Contenus courts/complexes
- Analyse avancée

## Trade-offs par Moteur de Tracking

| Moteur | Précision | Ressources | Workers | Risques | Quand l'utiliser |
|--------|-----------|------------|---------|---------|-----------------|
| **MediaPipe CPU** | Bonne (478 landmarks) | 15 workers CPU | 15 | Lent sur vidéos longues | Production stable, batch massif |
| **InsightFace GPU** | Excellente (embeddings) | 1 worker GPU | 1 | VRAM limitée, CUDA requis | Haute précision, contenus courts |
| **Hybrid Auto** | Adaptatif | Variable | Variable | Complexité configuration | Environnements mixtes |

## Trade-offs par Configuration Workers

| Workers CPU | Performance | Risques | Quand l'utiliser |
|-------------|------------|---------|-----------------|
| **5-8** | Modérée | Stable | Laptop, CPU limité |
| **15** (défaut) | Optimale | Équilibrée | Production standard |
| **20+** | Maximale | Surcharge CPU | Serveur puissant |

> **Note** : Les workers ne s'appliquent qu'à MediaPipe. InsightFace utilise toujours 1 worker GPU unique.

## Analogie : Studio de Capture vs Laboratoire

Pense au tracking comme un **studio de capture** vs un **laboratoire de recherche**. **MediaPipe** est le studio de capture : rapide, efficace, produit des résultats standards pour tous les projets avec 15 assistants (workers) qui travaillent en parallèle. **InsightFace** est le laboratoire : précis, analytique, parfait pour les projets qui demandent une qualité exceptionnelle, mais avec un seul chercheur (worker GPU) très spécialisé. Les **moteurs historiques** étaient des équipements obsolètes qui ont été retirés pour simplifier l'exploitation.

## Formats Supportés

### Vidéos en Entrée

```python
# Formats supportés
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')

# Prérequis
- 25 FPS (standardisé par STEP2)
- Analyses audio disponibles (STEP4)
- Scènes détectées (STEP3)
```

### Structure de Données

```json
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "tracked_objects": [
    {
      "frame": 1,
      "faces": [
        {
          "id": 0,
          "confidence": 0.95,
          "bbox": [x, y, w, h],
          "landmarks": [
            [x1, y1, z1],  # 468 points 3D
            [x2, y2, z2],
            ...
          ],
          "blendshapes": {
            "jawOpen": 0.12,
            "mouthSmileLeft": 0.34,
            "mouthSmileRight": 0.31,
            "browDownLeft": 0.08,
            "browDownRight": 0.06,
            ...  # 52 coefficients ARKit
          },
          "head_pose": {
            "rotation": [rx, ry, rz],
            "translation": [tx, ty, tz]
          }
        }
      ]
    }
  ]
}
```

## Performance et Optimisations

### MediaPipe CPU Optimizations

```python
# Multiprocessing configuration
TRACKING_CPU_WORKERS=15  # Workers parallèles

# Blendshapes throttling
STEP5_BLENDSHAPES_THROTTLE_N=2  # Calcul toutes les 2 frames

# Profiling optionnel
STEP5_ENABLE_PROFILING=1  # Logs toutes les 20 frames
```

### InsightFace GPU Optimizations

```python
# GPU validation
STEP5_GPU_FALLBACK_AUTO=1  # Bascule CPU auto si GPU échoue

# Memory management
# ONNX Runtime GPU avec VRAM monitoring
# CUDA paths discovery automatique
```

### Export Optimizations

```python
# JSON réduit (défaut)
STEP5_EXPORT_VERBOSE_FIELDS=0  # Pas de landmarks dans export

# Blendshapes filtering
STEP5_BLENDSHAPES_PROFILE=full    # Tous les 52 coefficients
STEP5_BLENDSHAPES_PROFILE=mouth   # Uniquement bouche
STEP5_BLENDSHAPES_PROFILE=none    # Désactive blendshapes
```

## Monitoring et Logs

### Structure des Logs

```
logs/step5/
├── manager_tracking_20240120_143022.log
├── worker_1_20240120_143022.log
├── worker_2_20240120_143022.log
└── ...
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Using MediaPipe engine (CPU)
2024-01-20 14:30:23 - INFO - Adaptive chunking enabled: selected_chunk_size=25
2024-01-20 14:30:24 - INFO - [PROFILING] Engine: MediaPipe, FPS: 12.5
2024-01-20 14:30:25 - INFO - [Progression-MultiLine] Processing chunk 1/25 (frames 1-625)
2024-01-20 14:30:45 - INFO - Successfully wrote video1_tracking.json
```

### Patterns de Progression

```python
# Standard progression
logger.info(f"Processing chunk {current}/{total} (frames {start}-{end})")

# Profiling (toutes les 20 frames)
if frame_count % 20 == 0:
    logger.info(f"[PROFILING] Engine: {engine}, FPS: {fps:.2f}")

# Multi-line progression
logger.info(f"[Progression-MultiLine] Processing chunk {chunk_id}/{total_chunks}")
```

## Dépendances et Prérequis

### Environnement MediaPipe (CPU)

```bash
# Création environnement CPU
python3 -m venv tracking_env_slim
source tracking_env_slim/bin/activate

# Installation dépendances
pip install mediapipe opencv-python numpy onnxruntime
pip install -r requirements-tracking-env-lite.txt
```

### Environnement InsightFace (GPU)

```bash
# Prérequis GPU
nvidia-smi  # NVIDIA GPU
python -c "import torch; print(torch.cuda.is_available())"

# Création environnement GPU
python3 -m venv insightface_env
source insightface_env/bin/activate

# Installation GPU
pip install onnxruntime-gpu
pip install insightface==0.7.3
pip install -r requirements-insightface_env.txt
```

### Vérification GPU

```bash
# Diagnostic GPU complet
python -c "
import onnxruntime as ort
print('Providers:', ort.get_available_providers())
print('GPU available:', ort.get_device() == 'GPU')
"

# Validation VRAM
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv
```

## Résolution de Problèmes

### GPU Non Disponible

```bash
# Diagnostic
nvidia-smi
python -c "import onnxruntime as ort; print('GPU:', 'GPU' in ort.get_available_providers())"

# Solutions
# 1. Forcer CPU
STEP5_ENABLE_GPU=0 python workflow_scripts/step5/run_tracking_manager.py

# 2. Vérifier drivers CUDA
sudo apt install nvidia-driver-470
sudo apt install nvidia-cuda-toolkit
```

### Workers Insuffisants

```bash
# Diagnostic
htop  # Vérifier charge CPU
ps aux | grep python | wc -l  # Compter processus

# Solution
# Réduire workers
TRACKING_CPU_WORKERS=8 python workflow_scripts/step5/run_tracking_manager.py

# Ou augmenter si machine puissante
TRACKING_CPU_WORKERS=20 python workflow_scripts/step5/run_tracking_manager.py
```

### OOM GPU

```bash
# Diagnostic
nvidia-smi
python -c "import torch; print(torch.cuda.memory_allocated()/1024**3)"

# Solutions
# 1. Fallback CPU automatique
STEP5_GPU_FALLBACK_AUTO=1 python workflow_scripts/step5/run_tracking_manager.py

# 2. Réduire concurrents
# Arrêter autres processus GPU
```

### Fichiers Sans Audio

```bash
# Comportement attendu
# Les vidéos sans analyse audio STEP4 sont traitées quand même
# L'audio améliore la détection mais n'est pas obligatoire
```

## Tests et Validation

### Test MediaPipe CPU

```bash
# Créer vidéo test
ffmpeg -f lavfi -i testsrc=duration=5:size=640x480:rate=25 -c:v libx264 test_face.mp4

# Préparer structure
mkdir -p test_tracking/docs
mv test_face.mp4 test_tracking/docs/

# Exécuter tracking
source tracking_env_slim/bin/activate
cd test_tracking
python ../workflow_scripts/step5/run_tracking_manager.py

# Vérifier résultat
head docs/test_face_tracking.json | jq '.tracked_objects[0].faces[0].blendshapes'
```

### Test InsightFace GPU

```bash
# Activer GPU
STEP5_TRACKING_ENGINE=insightface source insightface_env/bin/activate

# Exécuter tracking
cd test_tracking
python ../workflow_scripts/step5/run_tracking_manager.py

# Vérifier GPU utilisé
grep "ONNX providers" logs/step5/manager_*.log
```

### Validation Automatique

```python
def validate_step5_output():
    """Vérifie que tous les JSON tracking sont valides."""
    import json
    from pathlib import Path
    
    base_dir = Path("projets_extraits")
    
    for json_file in base_dir.rglob("*_tracking.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # Vérifier structure minimale
            required_keys = ['video_filename', 'total_frames', 'fps', 'tracked_objects']
            if not all(key in data for key in required_keys):
                print(f"❌ {json_file}: Structure JSON invalide")
                return False
            
            # Vérifier cohérence frames
            total_frames = data['total_frames']
            tracked_objects = data['tracked_objects']
            
            if len(tracked_objects) != total_frames:
                print(f"❌ {json_file}: Incohérence frames ({len(tracked_objects)} vs {total_frames})")
                return False
            
            # Compter visages et blendshapes
            total_faces = 0
            total_blendshapes = 0
            
            for frame_data in tracked_objects:
                faces = frame_data.get('faces', [])
                total_faces += len(faces)
                
                for face in faces:
                    blendshapes = face.get('blendshapes', {})
                    if blendshapes:
                        total_blendshapes += len(blendshapes)
            
            print(f"✅ {json_file}: {total_faces} visages, {total_blendshapes} blendshapes")
            
        except Exception as e:
            print(f"❌ Erreur lecture {json_file}: {e}")
            return False
    
    print("✅ Validation réussie: tous les JSON tracking sont valides")
    return True
```

## Intégration Pipeline

### Entrée pour STEP6

L'étape 5 prépare les données brutes pour la réduction JSON :
- **Landmarks 3D** : 468 points par visage
- **Blendshapes ARKit** : 52 coefficients pour animation 3D
- **Head pose** : Rotation et translation 3D
- **Confiance** : Scores de détection par frame

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP5", "running")
ws.set_step_field("STEP5", "current_video", "video1.mp4")
ws.update_step_progress("STEP5", current=1, total=3)
```

### Compatibilité STEP6

Le format JSON dense est optimisé pour STEP6 :
```python
# Utilisation dans STEP6
for frame_data in tracking_data['tracked_objects']:
    frame_num = frame_data['frame']
    faces = frame_data.get('faces', [])
    
    for face in faces:
        landmarks = face['landmarks']
        blendshapes = face['blendshapes']
        
        # Réduction et optimisation
        optimized_data = reduce_tracking_data(landmarks, blendshapes)
```

## Pièges Courants et Solutions

### Piège #1 : Anciens moteurs dans la configuration
**Solution** : Les variables `STEP5_TRACKING_ENGINE=yunet/opencv/eos/openseeface` ne sont plus supportées. Le système fallback automatiquement vers MediaPipe.

### Piège #2 : GPU activé inutilement
**Solution** : MediaPipe reste CPU-only même si `STEP5_ENABLE_GPU=1`. GPU réservé à InsightFace.

### Piège #3 : Trop de workers CPU
**Solution** : Surveiller la charge CPU et ajuster `TRACKING_CPU_WORKERS` (15 par défaut).

### Piège #4 : VRAM insuffisante
**Solution** : Activer `STEP5_GPU_FALLBACK_AUTO=1` pour basculer CPU automatiquement.

### Piège #5 : JSON trop volumineux
**Solution** : Utiliser `STEP5_EXPORT_VERBOSE_FIELDS=0` pour réduire la taille.

### Piège #6 : Fichiers sans audio STEP4
**Solution** : Le tracking fonctionne sans audio, mais la détection de parole améliore les résultats.

### Piège #7 : Variables obsolètes
**Solution** : Supprimer les variables `STEP5_ENABLE_OBJECT_DETECTION` et `STEP5_*ENGINE_*` des fichiers `.env`.

L'étape 5 transforme les vidéos en données faciales 3D précises avec une architecture simplifiée et fiable. La double approche CPU/GPU garantit que le système fonctionne dans tous les environnements tout en offrant une haute précision quand les ressources le permettent. Le retrait des moteurs historiques simplifie la maintenance et élimine les points de défaillance.

---

## Golden Rule

**Choisis ton moteur avant de lancer ; sinon tu gaspilles des ressources GPU avec MediaPipe ou tu manques de précision avec InsightFace.**
