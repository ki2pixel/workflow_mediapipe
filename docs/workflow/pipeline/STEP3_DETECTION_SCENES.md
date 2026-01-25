# Documentation Technique - Étape 3 : Détection de Scènes

> **Code-Doc Context** – Part of the 7‑step pipeline; see `../README.md` for the uniform template. Backend hotspots: high complexity in `run_transnet.py` and `transnetv2_pytorch.py` (radon E/D), requiring careful monitoring.

---

## Purpose & Pipeline Role

### Objectif
L'Étape 3 utilise le modèle TransNetV2 basé sur PyTorch pour détecter automatiquement les changements de scène dans les vidéos. Cette analyse temporelle identifie les transitions visuelles significatives, créant une segmentation précise du contenu vidéo en scènes distinctes.

### Rôle dans le Pipeline
- **Position** : Troisième étape du pipeline (STEP3)
- **Prérequis** : Vidéos converties à 25 FPS par l'Étape 2
- **Sortie** : Fichiers CSV avec timestamps et numéros de frames des scènes détectées
- **Étape suivante** : Analyse audio (STEP4)

### Valeur Ajoutée
- **Segmentation automatique** : Identification précise des changements de scène sans intervention manuelle
- **Modèle pré-entraîné** : Utilisation de TransNetV2, un modèle state-of-the-art pour la détection de transitions
- **Optimisation GPU/CPU** : Traitement adaptatif selon les ressources disponibles
- **Format standardisé** : Sortie CSV compatible avec les outils de post-production
- **Métriques temporelles** : Conversion automatique frames ↔ timecodes

---

## Inputs & Outputs

### Inputs
- **Vidéos standardisées** : Fichiers vidéo à 25 FPS de STEP2
- **Configuration** : Paramètres TransNetV2 via JSON ou variables d'environnement
- **Métadonnées** : Informations de framerate pour conversion temps/frame

### Outputs
- **Fichiers CSV** : Scènes détectées avec timestamps et numéros de frame
- **Logs détaillés** : Journal de détection dans `logs/step3/`
- **Métriques** : Nombre de scènes, temps de traitement, utilisation GPU/CPU

---

## Command & Environment

### Commande WorkflowCommandsConfig
```python
# Exemple de commande (voir WorkflowCommandsConfig pour la commande exacte)
python workflow_scripts/step3/run_transnet.py --input-dir projets_extraits/ --config config/step3_transnet.json
```

### Environnement Virtuel
- **Environnement utilisé** : `transnet_env/` (environnement spécialisé)
- **Activation** : `source transnet_env/bin/activate`
- **Partage** : Isolé pour éviter les conflits PyTorch/TensorFlow

---

## Dependencies

### Bibliothèques Principales
```python
import torch              # PyTorch pour TransNetV2
import torchvision        # Transformations et modèles
import numpy as np        # Calcul numérique
import pandas as pd       # Manipulation CSV
import cv2                # Traitement vidéo OpenCV
import json               # Configuration
```

### Dépendances Externes
- **TransNetV2** : Modèle pré-entraîné pour la détection de scènes
- **PyTorch** : Framework deep learning (version compatible CUDA)
- **OpenCV** : Lecture et décodage vidéo

---

## Configuration

### Variables d'Environnement
- **STEP3_THRESHOLD** : Seuil de détection (défaut: 0.5)
- **STEP3_WINDOW_SIZE** : Taille de la fenêtre d'analyse (défaut: 100)
- **STEP3_STRIDE** : Pas d'analyse (défaut: 50)
- **STEP3_DEVICE** : 'auto', 'cuda', ou 'cpu'
- **STEP3_BATCH_SIZE** : Taille du lot pour traitement par lots

### Configuration JSON
```json
{
  "threshold": 0.5,
  "window": 100,
  "stride": 50,
  "padding": 25,
  "device": "auto",
  "batch_size": 1
}
```

---

## Known Hotspots

### Complexité Backend (Critique)
- **`run_transnet.py`** : Complexité élevée (radon E) dans la fonction `main`
- **`transnetv2_pytorch.py`** : Complexité élevée (radon D) dans `forward`
- **Points d'attention** : Gestion mémoire GPU, traitement par lots, validation des entrées

---

## Metrics & Monitoring

### Indicateurs de Performance
- **Débit de détection** : Images/seconde traitées
- **Utilisation GPU** : % GPU et mémoire VRAM
- **Précision** : Qualité des détections (validation manuelle)
- **Temps par vidéo** : Durée moyenne de traitement

### Patterns de Logging
```python
# Logs de progression
logger.info(f"Détection scènes {video_path} - {current}/{total}")

# Logs GPU
logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1024**3:.2f}GB")

# Logs d'erreur
logger.error(f"Échec détection {video_path}: {error}")
```

---

## Failure & Recovery

### Modes d'Échec Communs
1. **GPU mémoire insuffisante** : Basculement sur CPU ou réduction batch_size
2. **Modèle non chargé** : Retry avec téléchargement du modèle
3. **Format vidéo incompatible** : Logging et passage au fichier suivant
4. **Timeout** : Augmentation du délai ou traitement par lots plus petits

### Procédures de Récupération
```bash
# Réessayer avec CPU uniquement
STEP3_DEVICE=cpu python workflow_scripts/step3/run_transnet.py

# Réduire la taille des lots
STEP3_BATCH_SIZE=1 python workflow_scripts/step3/run_transnet.py

# Validation post-détection
python scripts/validate_step3_output.py
```

---

## Related Documentation

- **Pipeline Overview** : `../README.md`
- **Testing Strategy** : `../technical/TESTING_STRATEGY.md`
- **GPU Usage Guide** : `../pipeline/STEP5_GPU_USAGE.md`
- **WorkflowState Integration** : `../core/ARCHITECTURE_COMPLETE_FR.md`

---

*Generated with Code-Doc protocol – see `../cloc_stats.json` and `../complexity_report.txt`.*
  "ffmpeg_threads": 4,
  "mixed_precision": true,
  "amp_dtype": "float16",
  "num_workers": 1,
  "torchscript": true,
  "warmup": true,
  "warmup_batches": 2,
  "torchscript_auto_fallback": true
}
```

**Paramètres configurables** :
- `threshold` : Seuil de détection des transitions (0.0-1.0)
- `window` : Taille de la fenêtre glissante en frames
- `stride` : Pas de la fenêtre glissante
- `padding` : Frames ajoutées au début/fin pour stabilité
- `device` : Device PyTorch (`cuda`, `cpu`, `auto`)
- `ffmpeg_threads` : Threads FFmpeg pour décodage streaming
- `mixed_precision` : Activer AMP (Automatic Mixed Precision)
- `amp_dtype` : Type pour AMP (`float16` ou `bfloat16`)
- `num_workers` : Workers pour parallélisation multi-vidéos (max 1 en CUDA)
- `torchscript` : Activer compilation TorchScript (trace+freeze)
- `warmup` : Warm-up du modèle avant traitement
- `warmup_batches` : Nombre de batches de warm-up
- `torchscript_auto_fallback` : Fallback automatique vers Eager si TorchScript échoue

#### Optimisations PyTorch
- **Exécution en `torch.inference_mode()`** : Réduit overhead et mémoire
- **AMP optionnelle** : Mixed precision pour accélération GPU (float16/bfloat16)
- **`cudnn.benchmark=True`** : Optimisation automatique des kernels CUDA
- **Décodage FFmpeg streaming** : Fenêtre glissante avec padding, évite chargement complet en mémoire
- **FPS forcé à 25.0** : Constante via `get_video_fps()` pour cohérence pipeline
- **Parallélisation multi-vidéos bornée** : Process pool avec limitation à 1 worker en CUDA

#### Compilation TorchScript
- **Wrapper `InferenceWrapper`** : Sortie tensor-only pour éviter warnings liés aux dicts
- **Trace + freeze** : Compilation statique du modèle pour accélération
- **Fallback automatique** : Bascule vers Eager mode par vidéo si TorchScript échoue (`torchscript_auto_fallback=true`)

#### Résultats Observés
- Temps d'exécution réduit : ~1m02s vs ~1m51s (gain ~47%)
- Logs plus propres sans warnings TorchScript
- Comportement stable avec fallback sur erreurs de compilation
- Tuning aisé via JSON sans modification du code

### Amélioration de l'Affichage de la Progression
L'étape 3 a été optimisée pour fournir un meilleur retour visuel sur l'avancement du traitement :
- **Support étendu des messages de progression** : Gestion des formats `PROCESSING_VIDEO` avec nom de fichier uniquement et `INTERNAL_PROGRESS` simples sans pourcentages.
- **Expressions régulières améliorées** : Mise à jour dans `app_new.py` pour parser correctement les logs variés de l'étape 3.
- **Corrections syntaxiques** : Résolution des erreurs dans `uiUpdater.js` pour une gestion robuste des états intermédiaires.
- **Cache du nom de fichier** : Conservation du nom du fichier en cours entre les mises à jour pour éviter le flickering.

#### Formats de Logs Supportés
**Backend (`app_new.py` — `COMMANDS_CONFIG['STEP3']['progress_patterns']`)** :

```python
"progress_patterns": {
    # Total accepte underscore ou espace
    "total": re.compile(r"TOTAL[_ ]VIDEOS[_ ]TO[_ ]PROCESS:\s*(\d+)", re.IGNORECASE),
    
    # Nom de fichier seul (sans cur/total)
    "current": re.compile(r"PROCESSING[_ ]VIDEO:\s*(.*)$", re.IGNORECASE),
    
    # Progression simple : "INTERNAL_PROGRESS: N batches - filename"
    "internal_simple": re.compile(r"INTERNAL[_ ]PROGRESS:\s*(\d+)\s*batches\s*-\s*(.*)$", re.IGNORECASE),
    
    # Ligne de succès avec filename
    "current_success_line_pattern": re.compile(r"Succès:\s*(.*?)(?:\.csv|\.json)\s+créé", re.IGNORECASE),
    "current_item_text_from_success_line": True
}
```

**Exemples de logs reconnus** :
```
INFO - TOTAL_VIDEOS_TO_PROCESS: 5
INFO - PROCESSING_VIDEO: video1.mp4
INFO - INTERNAL_PROGRESS: 10 batches - video1.mp4
INFO - Succès: video1.csv créé avec 12 scènes.
```

## Spécifications Techniques

### Environnement Virtuel
- **Environnement utilisé** : `transnet_env/` (spécialisé PyTorch)
- **Activation** : `source transnet_env/bin/activate`
- **Isolation** : Environnement dédié pour éviter les conflits de dépendances

### Technologies et Bibliothèques Principales

#### PyTorch et Deep Learning
```python
import torch              # Framework de deep learning
import torch.nn as nn     # Modules de réseaux de neurones
import torch.nn.functional as F  # Fonctions d'activation et utilitaires
```

#### Traitement Vidéo et Audio
```python
import ffmpeg            # Interface Python pour FFmpeg
import numpy as np       # Calculs numériques et manipulation d'arrays
from scenedetect import FrameTimecode  # Conversion frames/timecodes
```

#### Modèle TransNetV2 Personnalisé
```python
from transnetv2_pytorch import TransNetV2 as TransNetV2_PyTorch_Model
```

### Formats d'Entrée et de Sortie

#### Formats Vidéo Supportés
```python
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
```

#### Structure d'Entrée Attendue
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4     # 25 FPS (converti par STEP2)
│       └── video2.mov     # 25 FPS (converti par STEP2)
```

#### Structure de Sortie Générée
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4
│       ├── video1.csv     # Scènes détectées
│       ├── video2.mov
│       └── video2.csv     # Scènes détectées
```

### Paramètres de Configuration

#### Configuration du Modèle
```python
# Chemin vers les poids pré-entraînés
PYTORCH_WEIGHTS_PATH = "assets/transnetv2-pytorch-weights.pth"

# Seuil de détection des transitions
DETECTION_THRESHOLD = 0.5  # Valeur entre 0.0 et 1.0

# Résolution d'analyse (optimisée pour TransNetV2)
ANALYSIS_RESOLUTION = "48x27"  # Résolution réduite pour efficacité

# Taille des batches pour traitement
BATCH_SIZE = 100  # Frames par batch
BATCH_OVERLAP = 50  # Overlap entre batches
```

#### Paramètres de Traitement
```python
# Padding pour stabilité du modèle
PADDING_FRAMES = 25  # Frames ajoutées au début/fin

# Fréquence de rapport de progression
PROGRESS_REPORT_INTERVAL = 10  # Toutes les 10 batches

# Device de traitement (auto-détection)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

## Architecture Interne

### Structure du Code

#### Module Principal (`run_transnet.py`)
```python
def main():
    """Point d'entrée avec chargement du modèle et traitement des vidéos."""
    
def detect_scenes_with_pytorch(video_path, model, device, threshold=0.5):
    """Détection de scènes pour une vidéo individuelle."""
    
def get_video_fps(video_path):
    """Extraction du framerate via FFmpeg pour conversion timecodes."""
```

#### Modèle TransNetV2 (`transnetv2_pytorch.py`)
```python
class TransNetV2(nn.Module):
    """Implémentation PyTorch du modèle TransNetV2."""
    
class StackedDDCNNV2(nn.Module):
    """Bloc de convolutions dilatées empilées."""
    
class DilatedDCNNV2(nn.Module):
    """Convolution dilatée avec multiple taux de dilatation."""
    
class FrameSimilarity(nn.Module):
    """Calcul de similarité entre frames."""
    
class ColorHistograms(nn.Module):
    """Extraction d'histogrammes de couleur."""
```

### Algorithmes et Méthodes

#### Workflow de Détection de Scènes
1. **Extraction de frames** : Conversion vidéo en frames RGB 48x27 via FFmpeg
2. **Préparation des données** : Padding et normalisation des frames
3. **Traitement par batches** : Analyse séquentielle avec overlap
4. **Prédiction du modèle** : Calcul des probabilités de transition
5. **Post-traitement** : Application du seuil et détection des pics
6. **Génération des scènes** : Création des segments temporels
7. **Export CSV** : Conversion en format standardisé

#### Algorithme de Traitement par Batches
```python
def process_video_in_batches(video_frames, model, device):
    # 1. Padding pour stabilité
    padded_frames = add_padding(video_frames, PADDING_FRAMES)
    
    # 2. Traitement par batches avec overlap
    predictions = []
    ptr = 0
    while ptr + BATCH_SIZE <= len(padded_frames):
        batch = padded_frames[ptr:ptr + BATCH_SIZE]
        batch_tensor = torch.from_numpy(batch).unsqueeze(0).to(device)
        
        # 3. Prédiction du modèle
        with torch.no_grad():
            logits, _ = model(batch_tensor)
            probs = torch.sigmoid(logits).cpu().numpy()
            
        # 4. Extraction de la partie centrale (sans padding)
        central_probs = probs[0, PADDING_FRAMES:BATCH_SIZE-PADDING_FRAMES, 0]
        predictions.append(central_probs)
        
        ptr += BATCH_OVERLAP
    
    return np.concatenate(predictions)
```

#### Algorithme de Détection des Transitions
```python
def detect_scene_boundaries(predictions, threshold=0.5):
    # 1. Application du seuil
    shot_boundaries = np.where(predictions > threshold)[0]
    
    # 2. Création des segments de scène
    scenes = []
    last_cut = -1
    
    for cut in shot_boundaries:
        if cut > last_cut:
            scenes.append([last_cut + 1, cut])
        last_cut = cut
    
    # 3. Ajout de la dernière scène
    if last_cut < len(predictions) - 1:
        scenes.append([last_cut + 1, len(predictions) - 1])
    
    return scenes
```

### Architecture du Modèle TransNetV2

#### Structure Générale
```python
class TransNetV2(nn.Module):
    def __init__(self, F=16, L=3, S=2, D=1024):
        # F: Nombre de filtres de base
        # L: Nombre de couches SDDCNN
        # S: Nombre de blocs par couche
        # D: Dimension de la couche dense
        
        # 1. Couches de convolution dilatées empilées
        self.SDDCNN = nn.ModuleList([...])
        
        # 2. Couche de similarité entre frames
        self.frame_sim_layer = FrameSimilarity(...)
        
        # 3. Couche d'histogrammes de couleur
        self.color_hist_layer = ColorHistograms(...)
        
        # 4. Couches de classification
        self.fc1 = nn.Linear(output_dim, D)
        self.cls_layer1 = nn.Linear(D, 1)
```

#### Convolutions Dilatées (DDCNN)
```python
class DilatedDCNNV2(nn.Module):
    def __init__(self, in_filters, filters):
        # Convolutions avec différents taux de dilatation
        self.Conv3D_1 = Conv3DConfigurable(in_filters, filters, dilation=1)
        self.Conv3D_2 = Conv3DConfigurable(in_filters, filters, dilation=2)
        self.Conv3D_4 = Conv3DConfigurable(in_filters, filters, dilation=4)
        self.Conv3D_8 = Conv3DConfigurable(in_filters, filters, dilation=8)
        
    def forward(self, inputs):
        # Concaténation des sorties de différentes dilatations
        conv_outputs = [self.Conv3D_1(inputs), self.Conv3D_2(inputs),
                       self.Conv3D_4(inputs), self.Conv3D_8(inputs)]
        return torch.cat(conv_outputs, dim=1)
```

### Gestion des Erreurs et Logging

#### Niveaux de Logging
```python
logging.INFO     # Progression normale et statistiques
logging.WARNING  # Problèmes de FPS ou de format
logging.ERROR    # Échecs de traitement FFmpeg ou modèle
logging.CRITICAL # Modèle non trouvé ou erreurs fatales
```

#### Types d'Erreurs Gérées
- **Modèle non trouvé** : Fichier de poids PyTorch manquant
- **Erreurs FFmpeg** : Problèmes d'extraction de frames
- **Erreurs CUDA** : Problèmes de mémoire GPU ou drivers
- **Formats non supportés** : Codecs vidéo incompatibles
- **Erreurs de traitement** : Exceptions durant l'inférence

#### Structure des Logs
```
logs/step3/transnet_pytorch_20240120_143022.log
```

Exemple de sortie :
```
2024-01-20 14:30:22 - INFO - Utilisation du device: cuda
2024-01-20 14:30:23 - INFO - Modèle TransNetV2 (PyTorch) chargé avec succès.
2024-01-20 14:30:24 - INFO - PROCESSING_VIDEO: 1/3: video1.mp4
2024-01-20 14:30:25 - INFO - INTERNAL_PROGRESS: 10/25 batches (40%) - video1.mp4
2024-01-20 14:30:30 - INFO - Succès: video1.csv créé avec 12 scènes.
```

### Optimisations de Performance

#### Optimisations GPU
- **Traitement par batches** : Maximise l'utilisation GPU
- **Résolution réduite** : 48x27 pour efficacité sans perte de précision
- **Gestion mémoire** : `torch.no_grad()` pour économiser la VRAM
- **Précision mixte** : Support FP16 pour GPU modernes (optionnel)

#### Optimisations CPU
- **Fallback automatique** : Basculement CPU si GPU indisponible
- **Optimisations NumPy** : Vectorisation des opérations post-traitement
- **Gestion mémoire** : Libération explicite des tensors

#### Optimisations I/O
```python
# Extraction optimisée via FFmpeg
video_stream, err = (
    ffmpeg.input(str(video_path))
    .output("pipe:", format="rawvideo", pix_fmt="rgb24", s="48x27")
    .run(capture_stdout=True, capture_stderr=True, quiet=True)
)
```

## Interface et Utilisation

### Paramètres d'Exécution

#### Exécution Automatique via Workflow
```python
# Via WorkflowService
result = WorkflowService.run_step("STEP3")

# Via API REST
curl -X POST http://localhost:5000/run/STEP3
```

#### Exécution Manuelle (Debug)
```bash
# Activation de l'environnement spécialisé
source transnet_env/bin/activate

# Exécution depuis le répertoire projets_extraits
cd projets_extraits
python ../workflow_scripts/step3/run_transnet.py --weights_dir ../assets

# Avec logging détaillé
cd projets_extraits
python ../workflow_scripts/step3/run_transnet.py --weights_dir ../assets 2>&1 | tee scene_detection.log
```

#### Arguments de Ligne de Commande
```bash
python run_transnet.py [--weights_dir WEIGHTS_DIR]

# --weights_dir : Répertoire des poids (argument de compatibilité, ignoré)
```

### Exemples d'Utilisation

#### Test de Détection sur Vidéo Unique
```bash
# Préparation d'un test
mkdir -p test_scenes/docs
cp sample_video.mp4 test_scenes/docs/

# Activation de l'environnement
source transnet_env/bin/activate

# Exécution du test
cd test_scenes
python ../workflow_scripts/step3/run_transnet.py

# Vérification du résultat
ls -la docs/sample_video.csv
head docs/sample_video.csv
```

#### Intégration dans Séquence
```javascript
// Frontend - Monitoring spécifique de l'étape 3
pollingManager.startPolling('step3Status', async () => {
    const status = await apiService.getStepStatus('STEP3');
    if (status.status === 'running') {
        updateSceneDetectionProgress(status.progress);
    }
}, 1000);
```

### Structure des Fichiers de Sortie

#### Format CSV Généré
```csv
No,Timecode In,Timecode Out,Frame In,Frame Out
1,00:00:00:00,00:00:03:15,1,90
2,00:00:03:16,00:00:07:22,91,197
3,00:00:07:23,00:00:12:08,198,302
4,00:00:12:09,00:00:18:14,303,464
```

#### Description des Colonnes
- **No** : Numéro séquentiel de la scène (1, 2, 3, ...)
- **Timecode In** : Timestamp de début (format HH:MM:SS:FF)
- **Timecode Out** : Timestamp de fin (format HH:MM:SS:FF)
- **Frame In** : Numéro de frame de début (base 1)
- **Frame Out** : Numéro de frame de fin (base 1)

#### Conversion Frames/Timecodes
```python
# Utilisation de scenedetect.FrameTimecode
fps = get_video_fps(video_path)  # Ex: 25.0
frame_number = 125  # Frame 125

# Conversion frame → timecode
timecode = FrameTimecode(frame_number, fps)
timecode_str = timecode.get_timecode()  # "00:00:05:00"

# Calcul manuel
seconds = frame_number / fps  # 125 / 25 = 5.0 secondes
```

### Métriques de Progression et Monitoring

#### Indicateurs de Progression Console
```python
# Sortie standardisée pour l'interface utilisateur
print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
print(f"PROCESSING_VIDEO: {i + 1}/{total_videos}: {video_name}")
print(f"INTERNAL_PROGRESS: {batch_count}/{total_batches} batches ({progress_percent}%) - {video_name}")
```

#### Métriques de Performance
```python
# Statistiques de détection
logging.info(f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes.")
logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")

# Temps de traitement par vidéo
start_time = time.time()
scenes = detect_scenes_with_pytorch(video_path, model, device)
processing_time = time.time() - start_time
```

#### Monitoring via Logs Structurés
```python
# Progression détaillée
logging.info(f"PROCESSING_VIDEO: {i + 1}/{total_videos}: {video_path.name}")
logging.info(f"INTERNAL_PROGRESS: {batch_count}/{total_batches} batches ({progress_percent}%) - {video_path.name}")
logging.info(f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes.")
```

## Dépendances et Prérequis

### Logiciels Externes Requis

#### FFmpeg (Obligatoire)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Vérification de l'installation
ffmpeg -version
ffmpeg -formats | grep rgb24
```

#### Support GPU NVIDIA (Optionnel)
```bash
# Vérification du support CUDA
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# Installation CUDA (Ubuntu)
sudo apt install nvidia-driver-470
sudo apt install nvidia-cuda-toolkit
```

### Versions Spécifiques des Bibliothèques

#### Requirements Python (transnet_env/)
```txt
# Deep Learning
torch>=1.9.0
torchvision>=0.10.0

# Traitement vidéo
ffmpeg-python>=0.2.0
scenedetect>=0.6.0

# Calculs numériques
numpy>=1.21.0

# Utilitaires
pathlib2>=2.3.7
```

#### Versions Recommandées
```bash
# PyTorch avec support CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# FFmpeg Python
pip install ffmpeg-python

# Scene detection
pip install scenedetect[opencv]

# Vérification des installations
python -c "import torch, ffmpeg, scenedetect; print('All dependencies OK')"
```

### Configuration Système Recommandée

#### Ressources Minimales
- **RAM** : 8 GB minimum, 16 GB recommandé
- **GPU** : NVIDIA GTX 1060 ou supérieure (4 GB VRAM minimum)
- **CPU** : 4 cœurs minimum pour traitement CPU
- **Espace disque** : 2 GB pour le modèle + espace de travail

#### Optimisations Système
```bash
# Augmentation des limites de mémoire partagée (pour PyTorch)
echo 'kernel.shmmax = 68719476736' | sudo tee -a /etc/sysctl.conf
echo 'kernel.shmall = 4294967296' | sudo tee -a /etc/sysctl.conf

# Optimisation GPU
nvidia-smi -pm 1  # Mode persistance
nvidia-smi -ac 4004,1590  # Fréquences maximales (exemple GTX 1080)
```

#### Fichiers de Modèle Requis
```bash
# Structure attendue
assets/
└── transnetv2-pytorch-weights.pth  # ~50 MB

# Téléchargement (si nécessaire)
wget https://github.com/soCzech/TransNetV2/releases/download/v1.0/transnetv2-pytorch-weights.pth
mv transnetv2-pytorch-weights.pth assets/
