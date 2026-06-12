# Détection de Scènes

**TL;DR** : Analyse automatique des vidéos avec TransNetV2. Décodage asynchrone FFmpeg (Threading + Queue), pruning glissant de la RAM (O(1) constant) et batching GPU (taille 16) pour une performance maximale avec fallback CPU. Supporte également l'accélération optionnelle via Google Coral Edge TPU (MobileNetV2 Siamois + Cosine Distance CPU). Sortie CSV standardisée.

## Le Problème : Segmentation Manuelle Fastidieuse

Tu dois analyser des vidéos longues pour identifier les changements de scène, mais le faire manuellement est chronophage et imprécis. Tu as besoin d'une solution automatique qui segmente précisément les vidéos pour faciliter le travail de post-production.

## Notre Solution : TransNetV2 avec Intelligence Artificielle

Nous utilisons TransNetV2, un modèle deep learning state-of-the-art entraîné spécifiquement pour la détection de transitions de scènes. Le système analyse chaque frame, calcule les probabilités de transition, et génère des segments temporels précis.

### ❌ Seuil fixe (anti-pattern)
```python
# Approche rigide - pas d'adaptation
THRESHOLD = 0.5  # Fixe pour toutes les vidéos
scenes = detect_scenes(video, THRESHOLD)  # Trop sensible ou pas assez
# Résultat : scènes manquées ou fausses détections
```

### ✅ Seuil adaptatif (pattern recommandé)
```python
# Approche intelligente - adaptation au contenu
def detect_scenes_adaptive(video, base_threshold=0.5):
    # Analyser la distribution des probabilités
    probs = get_transition_probabilities(video)
    
    # Adapter selon le contenu
    if is_high_motion_content(probs):
        threshold = base_threshold + 0.1  # Plus strict
    elif is_low_motion_content(probs):
        threshold = base_threshold - 0.1  # Plus sensible
    
    return detect_scenes(video, threshold)
```

### Flux de Détection Intelligente

1. **Décodage asynchrone** : Lecture FFmpeg via Threading + Queue pour éviter le blocage I/O
2. **Pruning glissant** : Gestion mémoire RAM O(1) constant avec batching GPU (taille 16)
3. **Prédiction IA** : TransNetV2 calcule les probabilités de transition
4. **Seuillage** : Application du seuil pour détecter les vraies transitions
5. **Segmentation** : Création des scènes avec timecodes et frames
6. **Export CSV** : Format standardisé pour post-production

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 3 : Détection de scènes" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP3

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
# Activation environnement spécialisé
source transnet_env/bin/activate

# Exécution depuis projets_extraits
cd projets_extraits
python ../workflow_scripts/step3/run_transnet.py

# Monitoring des logs
tail -f logs/step3/transnet_*.log
```

### Résultat Attendu

```
# Fichier CSV généré
projets_extraits/projet_camille_001/docs/video1.csv

# Contenu CSV
No,Timecode In,Timecode Out,Frame In,Frame Out
1,00:00:00:00,00:00:03:15,1,90
2,00:00:03:16,00:00:07:22,91,197
3,00:00:07:23,00:00:12:08,198,302
4,00:00:12:09,00:00:18:14,303,464
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Seuil de détection (défaut: 0.5)
STEP3_THRESHOLD=0.5

# Paramètres de traitement
STEP3_WINDOW_SIZE=100
STEP3_STRIDE=50
STEP3_PADDING=25

# Accélération matérielle
ENABLE_CORAL_TPU_ACCELERATION=false # true pour activer l'Edge TPU (PCIe/USB)

# Device et performance (lorsque TPU désactivé)
STEP3_DEVICE=auto           # auto, cuda, cpu
STEP3_BATCH_SIZE=8          # GPU: 8 pour VRAM 4Go
STEP3_NUM_WORKERS=1        # Multi-vidéos (CPU only)

# Optimisations PyTorch
STEP3_MIXED_PRECISION=true
STEP3_AMP_DTYPE=float16
STEP3_TORCHSCRIPT=true
```

### Configuration JSON

```json
{
  "threshold": 0.5,
  "window": 100,
  "stride": 50,
  "padding": 25,
  "device": "auto",
  "batch_size": 8,
  "ffmpeg_threads": 1,
  "mixed_precision": true,
  "amp_dtype": "float16",
  "num_workers": 1,
  "torchscript": true,
  "warmup": true,
  "warmup_batches": 2,
  "torchscript_auto_fallback": true
}
```

### Fichier de Configuration

```bash
# config/step3_transnet.json
{
  "threshold": 0.5,
  "window": 100,
  "stride": 50,
  "padding": 25,
  "device": "auto",
  "batch_size": 8
}
```

## Formats Supportés

### Vidéos en Entrée

```python
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
```

### Spécifications d'Entrée

- **Framerate** : 25.0 FPS (standardisé par STEP2)
- **Résolution** : Toute résolution (convertie en 48x27 pour analyse)
- **Codecs** : H.264, H.265, VP9, etc. (via FFmpeg)

### Format CSV de Sortie

```csv
No,Timecode In,Timecode Out,Frame In,Frame Out
1,00:00:00:00,00:00:03:15,1,90
2,00:00:03:16,00:00:07:22,91,197
3,00:00:07:23,00:00:12:08,198,302
```

**Description des colonnes** :
- **No** : Numéro séquentiel de la scène
- **Timecode In/Out** : Timestamps SMPTE (HH:MM:SS:FF)
- **Frame In/Out** : Numéros de frame (base 1)

## Trade-offs par Paramètre de Détection

| Paramètre | Effet | Risques | Quand l'utiliser |
|-----------|-------|---------|-----------------|
| **Threshold 0.3** | Plus de scènes détectées | Sur-segmentation | Contenus dynamiques, clips courts |
| **Threshold 0.5** | Équilibre optimal | Manque quelques transitions | Contenus standards, longs métrages |
| **Threshold 0.7** | Moins de fausses détections | Sous-segmentation | Documentaires, entretiens |
| **Window 50** | Plus granuleux | Plus de calcul | Scènes très courtes |
| **Window 100** | Standard, rapide | Moins précis | Production courante |
| **Window 200** | Moins de bruit | Manque transitions rapides | Contenus lents, paysages |

## Trade-offs GPU vs CPU vs Edge TPU

| Mode | Performance | Mémoire | Risques | Quand l'utiliser |
|------|-------------|---------|---------|-----------------|
| **GPU CUDA** | 5-10× plus rapide (TransNetV2) | 2-4GB VRAM | OOM sur vidéos longues | Production avec GPU dédié |
| **CPU** | Lent mais stable (TransNetV2) | 0GB VRAM | Timeout sur longues vidéos | Développement, laptop |
| **Edge TPU** | Très rapide et économique (MobileNetV2 Siamois) | 0GB VRAM (SRAM 8MB) | Requiert matériel Coral et `coral_env` | Postes Edge sans GPU dédié (consommation 2-4W) |
| **Hybrid** | Auto-fallback | Variable | Complexité configuration | Environnements mixtes |

## Accélération Google Coral Edge TPU

Lorsque `ENABLE_CORAL_TPU_ACCELERATION=true` est configuré dans le fichier `.env`, l'étape 3 bascule du modèle lourd TransNetV2 vers une architecture optimisée pour les puces TPU Coral Edge (M.2 PCIe ou USB) :

* **Script d'exécution** : `workflow_scripts/step3/run_scene_detect_tpu.py`
* **Fonctionnement** :
  1. **Décodage vidéo** : Extraction des frames à 25 FPS au format RGB 224x224 via FFmpeg.
  2. **Inférence TPU** : Utilisation d'un modèle Siamois MobileNetV2 INT8 quantifié exécuté sur l'Edge TPU pour générer un vecteur d'empreinte (logits à 1000 dimensions) pour chaque frame.
  3. **Calcul des transitions** : Calcul de la distance cosinus entre frames successives sur le CPU.
  4. **Lissage temporel** : Application d'un filtre de convolution moyenne mobile sur le CPU pour gommer le bruit d'inférence INT8.
  5. **Détection** : Identification des pics de transition qui franchissent le seuil configuré (par défaut 0.25) et écriture du fichier `.csv` de découpage.

## Benchmarks d'Optimisation VRAM (GPU 4 Go)

Afin d'évaluer de manière réaliste les optimisations sur un volume complet de production (6 vidéos), une campagne de benchmarking a été réalisée. 

| Batch | AMP | TorchScript | FFmpeg | Time (s) | Max VRAM (MB) | Statut |
|-------|-----|-------------|--------|----------|---------------|--------|
| 16    | False| False       | 0      | 135.06   | 2719.53       | OK     |
| 16    | True | False       | 1      | 137.55   | 2720.59       | OK     |
| 8     | True | False       | 1      | 90.42    | 1673.23       | OK     |

**Conclusion** : Par rapport à un temps de traitement historique d'environ 4 minutes sur ces 6 vidéos, la configuration optimale (`batch_size=8`, `mixed_precision=true`, `ffmpeg_threads=1`) abat le travail en **1m 30s** (gain de ~62%), tout en utilisant seulement **1.6 Go de VRAM** au lieu de 2.7 Go pour le lot de 16, la rendant extrêmement robuste pour les configurations à mémoire restreinte (4 Go).

## Analogie : Monteur Cinéma

Pense à la détection de scènes comme un **monteur cinéma expert**. Le **GPU** est l'assistant rapide qui scanne les rushs en temps réel. Le **seuil adaptatif** est le sens artistique du monteur qui sait quand couper selon le rythme du contenu. Les **batches avec overlap** sont les marqueurs de synchronisation qui garantissent que les coupes ne tombent jamais au milieu d'une action importante.

## Monitoring et Logs

### Structure des Logs

```
logs/step3/
└── transnet_pytorch_20240120_143022.log
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Utilisation du device: cuda
2024-01-20 14:30:23 - INFO - Modèle TransNetV2 (PyTorch) chargé avec succès
2024-01-20 14:30:24 - INFO - TOTAL_VIDEOS_TO_PROCESS: 3
2024-01-20 14:30:24 - INFO - PROCESSING_VIDEO: 1/3: video1.mp4
2024-01-20 14:30:25 - INFO - INTERNAL_PROGRESS: 10/25 batches (40%) - video1.mp4
2024-01-20 14:30:30 - INFO - Succès: video1.csv créé avec 12 scènes
```

### Patterns de Progression

```python
# Formats supportés par le parser
print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
print(f"PROCESSING_VIDEO: {current}/{total}: {video_name}")
print(f"INTERNAL_PROGRESS: {batch_count}/{total_batches} batches ({progress}%) - {video_name}")
print(f"Succès: {output_csv.name} créé avec {len(scenes)} scènes.")
```

## Dépendances et Prérequis

### Environnement Virtuel Spécialisé

```bash
# Création de l'environnement isolé
python3 -m venv transnet_env
source transnet_env/bin/activate

# Installation dépendances
pip install torch torchvision ffmpeg-python scenedetect numpy
```

### Environnement Edge TPU (coral_env)

Pour exécuter la détection de scènes sous accélération TPU, configurez l'environnement dédié :

```bash
# Configuration des pilotes et règles udev (requis une seule fois)
sudo bash scripts/install_coral_udev.sh

# Création et activation de l'environnement virtuel (Python 3.10 requis pour pycoral)
python3.10 -m venv coral_env
source coral_env/bin/activate

# Installation des paquets Coral et TFLite Runtime
pip install tflite-runtime==2.17.1 pycoral==2.0.2 numpy
```

### PyTorch avec Support CUDA

```bash
# Installation PyTorch CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Vérification
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### FFmpeg (Obligatoire)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Vérification support RGB24
ffmpeg -formats | grep rgb24
```

### Support GPU NVIDIA

```bash
# Vérification
nvidia-smi
python -c "import torch; print(torch.cuda.get_device_name())"

# Installation drivers (si nécessaire)
sudo apt install nvidia-driver-470
sudo apt install nvidia-cuda-toolkit
```

### Fichiers de Modèle

```bash
# Structure attendue
assets/
└── transnetv2-pytorch-weights.pth  # ~50 MB

# Téléchargement (si nécessaire)
wget https://github.com/soCzech/TransNetV2/releases/download/v1.0/transnetv2-pytorch-weights.pth
mv transnetv2-pytorch-weights.pth assets/
```

## Résolution de Problèmes

### GPU Mémoire Insuffisante

```bash
# Diagnostic
nvidia-smi
python -c "import torch; print(torch.cuda.memory_allocated()/1024**3)"

# Solutions
# 1. Réduire batch_size
STEP3_BATCH_SIZE=1 python workflow_scripts/step3/run_transnet.py

# 2. Forcer CPU
STEP3_DEVICE=cpu python workflow_scripts/step3/run_transnet.py
```

### Modèle Non Trouvé

```bash
# Diagnostic
ls -la assets/transnetv2-pytorch-weights.pth

# Solution
# Télécharger le modèle
wget https://github.com/soCzech/TransNetV2/releases/download/v1.0/transnetv2-pytorch-weights.pth
mv transnetv2-pytorch-weights.pth assets/
```

### FFmpeg Non Disponible

```bash
# Diagnostic
which ffmpeg
ffmpeg -version

# Solution
sudo apt install ffmpeg  # Ubuntu
brew install ffmpeg    # macOS
```

### Format Vidéo Incompatible

```bash
# Diagnostic
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name video.mp4

# Solution
# Convertir vers H.264 si nécessaire
ffmpeg -i video.avi -c:v libx264 video_h264.mp4
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer vidéo test (25 FPS)
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=25 -c:v libx264 test_25fps.mp4

# Préparer structure
mkdir -p test_scenes/docs
mv test_25fps.mp4 test_scenes/docs/

# Exécuter détection
source transnet_env/bin/activate
cd test_scenes
python ../workflow_scripts/step3/run_transnet.py

# Vérifier résultat
head docs/test_25fps.csv
```

### Validation Automatique

```python
def validate_step3_output():
    """Vérifie que tous les CSV de scènes sont valides."""
    import pandas as pd
    from pathlib import Path
    
    base_dir = Path("projets_extraits")
    
    for csv_file in base_dir.rglob("*.csv"):
        try:
            # Vérifier structure CSV
            df = pd.read_csv(csv_file)
            
            required_columns = ['No', 'Timecode In', 'Timecode Out', 'Frame In', 'Frame Out']
            if not all(col in df.columns for col in required_columns):
                print(f"❌ {csv_file}: Colonnes manquantes")
                return False
            
            # Vérifier cohérence timecodes
            for _, row in df.iterrows():
                if row['Frame In'] > row['Frame Out']:
                    print(f"❌ {csv_file}: Frame In > Frame Out à la ligne {row['No']}")
                    return False
            
            print(f"✅ {csv_file}: {len(df)} scènes validées")
            
        except Exception as e:
            print(f"❌ Erreur lecture {csv_file}: {e}")
            return False
    
    print("✅ Validation réussie: tous les CSV de scènes sont valides")
    return True
```

### Test Performance GPU vs CPU

```bash
# Test GPU
source transnet_env/bin/activate
time python workflow_scripts/step3/run_transnet.py

# Test CPU (désactiver GPU)
CUDA_VISIBLE_DEVICES="" time python workflow_scripts/step3/run_transnet.py
```

## Architecture Technique

### Modèle TransNetV2

```python
class TransNetV2(nn.Module):
    def __init__(self, F=16, L=3, S=2, D=1024):
        # F: filtres de base, L: couches SDDCNN, S: blocs par couche
        self.SDDCNN = nn.ModuleList([...])
        self.frame_sim_layer = FrameSimilarity(...)
        self.color_hist_layer = ColorHistograms(...)
        self.fc1 = nn.Linear(output_dim, D)
        self.cls_layer1 = nn.Linear(D, 1)
```

### Convolutions Dilatées (DDCNN)

```python
class DilatedDCNNV2(nn.Module):
    def __init__(self, in_filters, filters):
        # Différents taux de dilatation pour capture contextes variés
        self.Conv3D_1 = Conv3DConfigurable(in_filters, filters, dilation=1)
        self.Conv3D_2 = Conv3DConfigurable(in_filters, filters, dilation=2)
        self.Conv3D_4 = Conv3DConfigurable(in_filters, filters, dilation=4)
        self.Conv3D_8 = Conv3DConfigurable(in_filters, filters, dilation=8)
```

### Algorithme de Détection

```python
def detect_scene_boundaries(predictions, threshold=0.5):
    # 1. Application du seuil
    shot_boundaries = np.where(predictions > threshold)[0]
    
    # 2. Création des segments
    scenes = []
    last_cut = -1
    
    for cut in shot_boundaries:
        if cut > last_cut:
            scenes.append([last_cut + 1, cut])
        last_cut = cut
    
    # 3. Dernière scène
    if last_cut < len(predictions) - 1:
        scenes.append([last_cut + 1, len(predictions) - 1])
    
    return scenes
```

## Intégration Pipeline

### Entrée pour STEP4

L'étape 3 prépare les données temporelles pour l'analyse audio :
- **Scènes segmentées** : CSV avec timecodes précis
- **Frames identifiées** : Numéros de début/fin pour chaque scène
- **Format standardisé** : Compatible avec les outils de post-production

### Conversion Frames/Timecodes

```python
# Utilisation de scenedetect.FrameTimecode
fps = get_video_fps(video_path)  # 25.0
frame_number = 125

# Conversion frame → timecode
timecode = FrameTimecode(frame_number, fps)
timecode_str = timecode.get_timecode()  # "00:00:05:00"

# Calcul manuel
seconds = frame_number / fps  # 125 / 25 = 5.0 secondes
```

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP3", "running")
ws.set_step_field("STEP3", "current_video", "video1.mp4")
ws.update_step_progress("STEP3", current=1, total=3)
```

## Pièges Courants et Solutions

### Piège #1 : Mémoire GPU insuffisante
**Solution** : Batches plus petits, réduction batch_size, ou fallback CPU automatique.

### Piège #2 : Format vidéo incompatible
**Solution** : FFmpeg gère la conversion, mais certains codecs exotiques peuvent échouer.

### Piège #3 : Modèle manquant
**Solution** : Téléchargement automatique du modèle TransNetV2 depuis les releases officielles.

### Piège #4 : Seuil inadapté
**Solution** : Ajustement du threshold selon la vidéo (0.3-0.7 typiquement).

L'étape 3 transforme tes vidéos en segments temporels précis, créant une base solide pour l'analyse audio synchronisée. La détection automatique des scènes élimine le travail manuel et garantit une cohérence parfaite avec le reste du pipeline.

---

## Golden Rule

**Toujours valider GPU/CPU + modèle avant export CSV ; sinon tu obtiens des segments incohérents qui cassent la synchronisation audio.**
