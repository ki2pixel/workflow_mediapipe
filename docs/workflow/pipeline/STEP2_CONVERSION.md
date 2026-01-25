# Documentation Technique - Étape 2 : Conversion Vidéo

> **Code-Doc Context** – Part of the 7‑step pipeline; see `../README.md` for the uniform template. Backend hotspots: moderate complexity in `convert_videos.py` (radon C), but no critical hotspots.

---

## Purpose & Pipeline Role

### Objectif
L'Étape 2 normalise toutes les vidéos extraites à un framerate standard de 25 FPS, garantissant une cohérence temporelle pour les étapes suivantes du pipeline de traitement. Cette standardisation est cruciale pour l'efficacité des algorithmes de détection de scènes, d'analyse audio et de tracking vidéo.

### Rôle dans le Pipeline
- **Position** : Deuxième étape du pipeline (STEP2)
- **Prérequis** : Fichiers vidéo extraits par l'Étape 1 dans `projets_extraits/*/docs/`
- **Sortie** : Vidéos converties à 25 FPS remplaçant les fichiers originaux
- **Étape suivante** : Détection de scènes (STEP3)

### Valeur Ajoutée
- **Standardisation temporelle** : Framerate uniforme pour optimiser les traitements suivants
- **Optimisation GPU** : Utilisation exclusive du GPU NVIDIA pour des performances maximales
- **Gestion intelligente de l'audio** : Copie directe ou ré-encodage selon la compatibilité
- **Traitement sélectif** : Conversion uniquement des vidéos nécessitant une modification
- **Compression optimisée** : Réduction jusqu'à 70% de la taille des fichiers sans perte de qualité visible
- **Qualité préservée** : Paramètres d'encodage optimisés pour maintenir la qualité visuelle

---

## Inputs & Outputs

### Inputs
- **Vidéos brutes** : Fichiers vidéo extraits par STEP1 dans `projets_extraits/*/docs/`
- **Formats supportés** : MP4, MOV, AVI, MKV, WEBM, FLV, WMV
- **Métadonnées** : Informations de résolution, codec, et bitrate

### Outputs
- **Vidéos standardisées** : Fichiers vidéo à 25 FPS, optimisés en taille
- **Logs détaillés** : Journal de conversion dans `logs/step2/`
- **Métriques de performance** : Temps de traitement, débit, utilisation GPU

---

## Command & Environment

### Commande WorkflowCommandsConfig
```python
# Exemple de commande (voir WorkflowCommandsConfig pour la commande exacte)
python workflow_scripts/step2/convert_videos.py --input-dir projets_extraits/ --fps 25 --use-gpu
```

### Environnement Virtuel
- **Activation** : `source env/bin/activate`
- **Partage** : Utilisé également par les étapes 1 et 6

---

## Dependencies

### Bibliothèques Principales
```python
import subprocess        # Interface avec FFmpeg
import pathlib           # Manipulation des chemins
import re                # Expressions régulières
import json              # Métadonnées
import logging           # Journalisation
```

### Dépendances Externes
- **FFmpeg** : Conversion vidéo et manipulation des codecs
- **NVIDIA GPU** : Accélération matérielle via `h264_nvenc`
- **CPU fallback** : `libx264` si GPU non disponible

---

## Configuration

### Variables d'Environnement
- **STEP2_FPS_TARGET** : Framerate cible (défaut: 25)
- **STEP2_USE_GPU** : Forcer l'utilisation GPU (true/false)
- **STEP2_QUALITY_CRF** : Constant Rate Factor (défaut: 28)
- **STEP2_AUDIO_BITRATE** : Bitrate audio (défaut: 192k)
- **STEP2_MAX_CONCURRENT** : Conversions parallèles maximum

### Paramètres d'Encodage
- **GPU** : `h264_nvenc` avec `cq=28` pour qualité optimale
- **CPU** : `libx264` avec `crf=28` comme fallback
- **Audio** : AAC 192k ou copie directe si compatible

---

## Known Hotspots

### Complexité Backend
- **`convert_videos.py`** : Complexité modérée (radon C) dans la gestion des conversions parallèles
- **Points d'attention** : Gestion des ressources GPU et validation des codecs

---

## Metrics & Monitoring

### Indicateurs de Performance
- **Débit de conversion** : Vidéos/seconde
- **Utilisation GPU** : % GPU et mémoire VRAM
- **Taux de compression** : % réduction taille
- **Qualité préservée** : PSNR/SSIM si disponible

### Patterns de Logging
```python
# Logs de progression
logger.info(f"Conversion {video_path} - {current}/{total} ({progress:.1f}%)")

# Logs GPU
logger.info(f"GPU utilization: {gpu_util}% - VRAM: {vram_used}MB")

# Logs d'erreur
logger.error(f"Échec conversion {video_path}: {error}")
```

---

## Failure & Recovery

### Modes d'Échec Communs
1. **GPU indisponible** : Basculement automatique sur CPU
2. **Codec incompatible** : Tentative avec codec alternatif
3. **Espace disque insuffisant** : Pause et alerte
4. **Fichier corrompu** : Logging et passage au fichier suivant

### Procédures de Récupération
```bash
# Réessayer avec CPU uniquement
python workflow_scripts/step2/convert_videos.py --force-cpu

# Nettoyer les fichiers temporaires
python workflow_scripts/step2/convert_videos.py --cleanup-temp

# Validation post-conversion
python scripts/validate_step2_output.py
```

---

## Related Documentation

- **Pipeline Overview** : `../README.md`
- **GPU Usage Guide** : `../pipeline/STEP5_GPU_USAGE.md`
- **Testing Strategy** : `../technical/TESTING_STRATEGY.md`
- **WorkflowState Integration** : `../core/ARCHITECTURE_COMPLETE_FR.md`

---

*Generated with Code-Doc protocol – see `../cloc_stats.json` and `../complexity_report.txt`.*
    3. Compression avec les paramètres optimisés pour GPU ou CPU
    4. Vérification de l'intégrité du fichier résultant
    5. Remplacement du fichier original si la compression réussit
    
    Paramètres:
        video_path (Path): Chemin vers le fichier vidéo source
        use_gpu (bool): Utiliser l accélération GPU si disponible
    
    Retourne:
    bool: True si la compression a réussi, False sinon
        bool: True si la compression a réussi, False sinon
    """
    # Configuration de l'encodeur en fonction du matériel
    if use_gpu:
        # NVIDIA NVENC avec qualité élevée (CQ 28)
        video_params = ['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-cq', '28']
    else:
        # CPU libx264 avec qualité équivalente (CRF 28)
        video_params = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '28']
    
    # Tentative de copie directe de l'audio d'abord
    command = [FFMPEG_PATH, '-y', '-hide_banner', '-i', str(video_path)]
    command.extend(video_params)
    command.extend(['-pix_fmt', 'yuv420p', '-c:a', 'copy'])  # Copie audio
    
    # Si échec, réessayer avec ré-encodage audio
    # ...
```

##### Paramètres de Compression
- **Qualité Vidéo** :
  - GPU: `h264_nvenc` avec `-cq 28` (Constant Quality)
  - CPU: `libx264` avec `-crf 28` (Constant Rate Factor)
  - Format de pixel: `yuv420p` pour une compatibilité maximale

- **Audio** :
  - Copie directe du flux original si possible
  - Fallback sur encodage AAC à 192kbps si nécessaire

- **Métadonnées** :
  - Conservation des métadonnées originales
  - Préservation des flux de sous-titres et chapitres

##### Workflow de Compression
1. **Détection des fichiers** : Scan pour les fichiers .mp4 (hors fichiers temporaires)
2. **Traitement séquentiel** : Un seul worker GPU dédié pour éviter les conflits
3. **Gestion des erreurs** : Nettoyage des fichiers temporaires en cas d'échec
4. **Remplacement atomique** : Écriture dans un fichier temporaire puis renommage
5. **Journalisation** : Suivi détaillé de la progression et des erreurs

##### Avantages
- **Réduction de taille** : Jusqu'à 70% d'économie d'espace disque
- **Qualité préservée** : Paramètres optimisés pour maintenir la qualité visuelle
- **Performance** : Utilisation efficace du GPU pour des temps de traitement rapides
- **Robustesse** : Gestion complète des erreurs et reprise sur incident

##### Références Code et Intégration Progression
- **Fichier** : `workflow_scripts/step2/convert_videos.py`
- **Fonctions clés** :
  - `compress_single_video()` — Compression d'un fichier .mp4 (GPU/CPU, préservation framerate/résolution, métadonnées, audio copy→fallback AAC)
  - `gpu_compress_worker_thread()` — Orchestration séquentielle dédiée GPU avec gestion des erreurs et nettoyage des temporaires
- **Intégration progression** : Mise à jour unifiée de la progression conversion+compression dans les logs Step2, compatible avec le parseur backend (`app_new.py`).

### Technologies et Bibliothèques Principales

#### FFmpeg (Logiciel Externe)
```bash
# Vérification de la disponibilité
ffmpeg -version
ffprobe -version

# Encodeurs supportés
ffmpeg -encoders | grep -E "(h264_nvenc|libx264)"
```

#### Bibliothèques Python Standard
```python
import subprocess    # Exécution des commandes FFmpeg
import threading     # Gestion du worker GPU dédié
import queue         # Communication inter-threads
import concurrent.futures  # Gestion des tâches asynchrones
import pathlib       # Manipulation de chemins
import shutil        # Opérations fichiers
```

#### Modules de Performance
```python
import time          # Mesure des performances
import os            # Détection du nombre de CPU
```

### Formats d'Entrée et de Sortie

#### Formats Vidéo Supportés
```python
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')
```

#### Spécifications de Sortie
- **Framerate cible** : 25.0 FPS exactement
- **Codec vidéo** : H.264 (GPU: h264_nvenc, CPU: libx264)
- **Qualité** : CRF 23 (CPU) / CQ 23 (GPU)
- **Format pixel** : yuv420p (compatibilité maximale)
- **Audio** : Copie directe ou AAC 192k si ré-encodage nécessaire

### Paramètres de Configuration

#### Configuration Principale
```python
# Framerate cible standardisé
TARGET_FPS = 25.0

# Répertoire de travail (projets_extraits)
WORK_DIR = Path(os.getcwd())

# Chemins des exécutables FFmpeg
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"

# Tolérance pour la détection de conversion nécessaire
FPS_TOLERANCE = 0.1  # Conversion si |current_fps - target_fps| > 0.1
```

#### Paramètres d'Encodage GPU (NVIDIA)
```python
GPU_ENCODER_PARAMS = [
    '-c:v', 'h264_nvenc',    # Encodeur NVIDIA
    '-preset', 'p5',         # Preset haute qualité
    '-tune', 'hq',           # Optimisation qualité
    '-cq', '23',             # Qualité constante
    '-pix_fmt', 'yuv420p'    # Format pixel standard
]
```

#### Paramètres d'Encodage CPU (Fallback)
```python
CPU_ENCODER_PARAMS = [
    '-c:v', 'libx264',       # Encodeur x264
    '-preset', 'medium',     # Compromis vitesse/qualité
    '-crf', '23',            # Facteur de qualité constant
    '-pix_fmt', 'yuv420p'    # Format pixel standard
]
```

## Architecture Interne

### Structure du Code

#### Module Principal (`convert_videos.py`)
```python
def main():
    """Point d'entrée principal avec vérification des dépendances."""
    
def find_videos_to_convert():
    """Découverte et filtrage des vidéos nécessitant une conversion."""
    
def get_video_framerate(video_path):
    """Extraction du framerate actuel via FFprobe."""
    
def convert_single_video(video_path, use_gpu=False):
    """Conversion d'une vidéo individuelle avec gestion d'erreurs."""
```

#### Système de Worker GPU
```python
def gpu_worker_thread():
    """Thread dédié pour traitement GPU séquentiel continu."""
    
# Variables globales pour coordination
GPU_QUEUE = queue.Queue()           # Queue des vidéos à traiter
GPU_RESULTS_QUEUE = queue.Queue()   # Queue des résultats
GPU_WORKER_SHUTDOWN = threading.Event()  # Signal d'arrêt
PROGRESS_LOCK = threading.Lock()     # Synchronisation progression
```

### Algorithmes et Méthodes

#### Workflow de Conversion
1. **Découverte des vidéos** : Scan récursif du répertoire de travail
2. **Analyse du framerate** : Extraction via FFprobe pour chaque vidéo
3. **Filtrage sélectif** : Conversion uniquement si |fps_actuel - 25.0| > 0.1
4. **Traitement GPU exclusif** : Un seul worker pour éviter les conflits mémoire
5. **Conversion avec fallback audio** : Copie directe puis ré-encodage si échec
6. **Remplacement atomique** : Fichier temporaire puis déplacement final
7. **Compression non destructive** : Réduction de la taille des fichiers .mp4 après conversion

#### Algorithme de Détection de Framerate
```python
def get_video_framerate(video_path):
    # 1. Exécution FFprobe avec paramètres spécifiques
    command = [FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0', 
               '-show_entries', 'stream=r_frame_rate', '-of', 
               'default=noprint_wrappers=1:nokey=1', str(video_path)]
    
    # 2. Parsing du résultat (format "num/den" ou décimal)
    if '/' in framerate_str:
        num, den = map(int, framerate_str.split('/'))
        return float(num) / den if den != 0 else 0.0
    
    # 3. Retour du framerate calculé
    return float(framerate_str)
```

#### Stratégie de Traitement Audio
```python
def convert_with_audio_strategy(video_path, base_command):
    # 1. Tentative de copie audio directe (plus rapide)
    command_copy = base_command + ['-c:a', 'copy', temp_output]
    result = subprocess.run(command_copy)
    
    # 2. Fallback vers ré-encodage AAC si échec
    if result.returncode != 0:
        command_reencode = base_command + ['-c:a', 'aac', '-b:a', '192k', temp_output]
        result = subprocess.run(command_reencode)
    
    return result.returncode == 0
```

### Gestion des Erreurs et Logging

#### Niveaux de Logging
```python
logging.INFO     # Progression normale et statistiques
logging.WARNING  # Problèmes audio nécessitant ré-encodage
logging.ERROR    # Échecs de conversion FFmpeg
logging.CRITICAL # Dépendances manquantes (FFmpeg/FFprobe)
```

#### Types d'Erreurs Gérées
- **Dépendances manquantes** : FFmpeg/FFprobe non installés ou inaccessibles
- **Erreurs FFmpeg** : Formats non supportés, corruption, paramètres invalides
- **Problèmes d'E/O** : Espace disque insuffisant, permissions, fichiers verrouillés
- **Erreurs de threading** : Exceptions dans le worker GPU

#### Structure des Logs
```
logs/step2/convert_videos_20240120_143022.log
```

Exemple de sortie :
```
2024-01-20 14:30:22 - MainThread - INFO - Recherche de vidéos (.mp4, .mov, .avi, .mkv, .webm, .flv, .wmv) dans /path/projets_extraits...
2024-01-20 14:30:23 - MainThread - INFO - Conversion requise pour video1.mov (FPS actuel: 29.97)
2024-01-20 14:30:24 - GPU-Worker - INFO - Conversion (GPU) démarrée pour video1.mov
2024-01-20 14:30:45 - GPU-Worker - INFO - Succès (GPU): video1.mov a été converti et mis à jour.
2024-01-20 14:30:45 - GPU-Worker - INFO - --- Traitement de la vidéo (1/3): video1.mov ---
```

### Optimisations de Performance

#### Architecture GPU Exclusive
- **Un seul worker GPU** : Évite les conflits de mémoire VRAM
- **Traitement séquentiel** : Optimise l'utilisation des ressources GPU
- **Queue dédiée** : Communication thread-safe entre main et worker

#### Optimisations FFmpeg
```python
# Paramètres GPU optimisés
GPU_PARAMS = [
    '-preset', 'p5',      # Preset le plus rapide avec qualité élevée
    '-tune', 'hq',        # Optimisation qualité
    '-cq', '23'           # Qualité constante (équivalent CRF)
]

# Gestion audio intelligente
AUDIO_COPY = ['-c:a', 'copy']           # Copie directe (rapide)
AUDIO_REENCODE = ['-c:a', 'aac', '-b:a', '192k']  # Ré-encodage fallback
```

#### Gestion Mémoire
- **Fichiers temporaires** : Évite la corruption en cas d'interruption
- **Remplacement atomique** : `shutil.move()` pour opération atomique
- **Nettoyage automatique** : Suppression des fichiers temporaires en cas d'erreur

#### Monitoring de Progression
```python
# Variables globales thread-safe
PROGRESS_LOCK = threading.Lock()
COMPLETED_VIDEOS = 0
TOTAL_VIDEOS_COUNT = 0

# Mise à jour synchronisée
with PROGRESS_LOCK:
    COMPLETED_VIDEOS += 1
    print(f"--- Traitement de la vidéo ({COMPLETED_VIDEOS}/{TOTAL_VIDEOS_COUNT}): {video_name} ---")
```

## Interface et Utilisation

### Paramètres d'Exécution

#### Exécution Automatique via Workflow
L'Étape 2 est généralement exécutée automatiquement par le système de workflow sans paramètres spécifiques.

```python
# Via WorkflowService
result = WorkflowService.run_step("STEP2")

# Via API REST
curl -X POST http://localhost:5000/run/STEP2
```

#### Exécution Manuelle (Debug)
```bash
# Activation de l'environnement
source env/bin/activate

# Exécution depuis le répertoire projets_extraits
cd projets_extraits
python ../workflow_scripts/step2/convert_videos.py

# Avec logging détaillé
cd projets_extraits
python ../workflow_scripts/step2/convert_videos.py 2>&1 | tee conversion.log
```

#### Variables d'Environnement Optionnelles
```bash
# Personnalisation du framerate cible (non recommandé)
export TARGET_FPS=30.0

# Chemin personnalisé pour FFmpeg
export FFMPEG_PATH="/usr/local/bin/ffmpeg"
export FFPROBE_PATH="/usr/local/bin/ffprobe"

# Désactivation du GPU (force CPU)
export CUDA_VISIBLE_DEVICES=""
```

### Exemples d'Utilisation

#### Intégration dans Séquence Complète
```javascript
// Frontend - Séquence automatique
const fullWorkflow = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(fullWorkflow);

// Monitoring spécifique de l'étape 2
pollingManager.startPolling('step2Status', async () => {
    const status = await apiService.getStepStatus('STEP2');
    if (status.status === 'running') {
        updateConversionProgress(status.progress);
    }
}, 1000);
```

#### Test de Conversion Individuelle
```bash
# Préparation d'un test
mkdir -p test_conversion/docs
cp sample_video.mov test_conversion/docs/

# Exécution du test
cd test_conversion
python ../workflow_scripts/step2/convert_videos.py

# Vérification du résultat
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 docs/sample_video.mov
```

### Structure des Fichiers de Sortie

#### Transformation des Fichiers
```
# Avant conversion
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video_29fps.mov     # 29.97 FPS original
│       ├── video_24fps.mp4     # 24.0 FPS original
│       └── video_25fps.avi     # 25.0 FPS (pas de conversion)

# Après conversion
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video_29fps.mov     # 25.0 FPS converti
│       ├── video_24fps.mp4     # 25.0 FPS converti
│       └── video_25fps.avi     # 25.0 FPS (inchangé)
```

#### Préservation des Métadonnées
- **Nom de fichier** : Conservé identique
- **Extension** : Conservée identique
- **Emplacement** : Remplacement in-place du fichier original
- **Permissions** : Préservées autant que possible

#### Fichiers Temporaires (Pendant Traitement)
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video_29fps.mov                    # Original
│       └── video_29fps.temp_conversion.mov    # Temporaire (supprimé après)
```

### Métriques de Progression et Monitoring

#### Indicateurs de Progression Console
```python
# Sortie standardisée pour l'interface utilisateur
print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
print(f"--- Traitement de la vidéo ({current}/{total}): {video_name} ---")
```

#### Métriques de Performance
```python
# Temps de conversion par vidéo
start_time = time.time()
success = convert_single_video(video_path, use_gpu=True)
conversion_time = time.time() - start_time

# Statistiques finales
logging.info(f"Résumé: {successful}/{total} conversion(s) réussie(s) (traitement GPU exclusif)")
```

#### Monitoring via Logs Structurés
```python
# Progression détaillée
logging.info(f"Conversion requise pour {video_name} (FPS actuel: {current_fps:.2f})")
logging.info(f"Conversion non requise pour {video_name} (FPS actuel: {current_fps:.2f})")
logging.info(f"Conversion (GPU) démarrée pour {video_name}")
logging.info(f"Succès (GPU): {video_name} a été converti et mis à jour.")
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

# Windows (via chocolatey)
choco install ffmpeg

# Vérification de l'installation
ffmpeg -version
ffprobe -version
```

#### Support GPU NVIDIA (Optionnel mais Recommandé)
```bash
# Vérification du support NVIDIA
nvidia-smi
ffmpeg -encoders | grep nvenc

# Installation des drivers NVIDIA (Ubuntu)
sudo apt install nvidia-driver-470
sudo apt install nvidia-cuda-toolkit

# Test de l'encodeur GPU
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -c:v h264_nvenc test_gpu.mp4
```

### Versions Spécifiques des Bibliothèques

#### Requirements Python (env/)
```txt
# Aucune dépendance Python externe spécifique
# Utilise uniquement la bibliothèque standard Python 3.8+
```

#### Versions FFmpeg Recommandées
```bash
# Version minimale
ffmpeg version 4.2.0 ou supérieure

# Version recommandée
ffmpeg version 4.4.0 ou supérieure

# Vérification des codecs supportés
ffmpeg -codecs | grep -E "(h264|aac)"
```

### Configuration Système Recommandée

#### Ressources Minimales
- **RAM** : 4 GB minimum, 8 GB recommandé
- **CPU** : 4 cœurs minimum pour traitement CPU
- **GPU** : NVIDIA GTX 1060 ou supérieure (optionnel)
- **Espace disque** : 2x la taille des vidéos (pour fichiers temporaires)

#### Optimisations Système
```bash
# Augmentation des limites de fichiers ouverts
ulimit -n 4096

# Optimisation des performances I/O (SSD recommandé)
echo mq-deadline | sudo tee /sys/block/sda/queue/scheduler

# Vérification de l'espace disque disponible
df -h projets_extraits/
```

#### Configuration GPU
```bash
# Variables d'environnement CUDA
export CUDA_VISIBLE_DEVICES=0  # Utiliser le premier GPU
export NVIDIA_VISIBLE_DEVICES=0

# Vérification de la mémoire GPU
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv
```

## Debugging et Résolution de Problèmes

### Erreurs Courantes et Solutions

#### 1. Erreur : "ffmpeg ou ffprobe n'est pas installé"
```bash
# Erreur
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'

# Diagnostic
which ffmpeg
which ffprobe
echo $PATH

# Solutions
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Vérification
ffmpeg -version && ffprobe -version
```

#### 2. Erreur : "Encodeur h264_nvenc non disponible"
```bash
# Erreur
Unknown encoder 'h264_nvenc'

# Diagnostic
ffmpeg -encoders | grep nvenc
nvidia-smi

# Solutions
# Installer les drivers NVIDIA
sudo apt install nvidia-driver-470

# Recompiler FFmpeg avec support NVENC (si nécessaire)
# Ou utiliser le mode CPU automatiquement
```

#### 3. Erreur : "No space left on device"
```bash
# Erreur
OSError: [Errno 28] No space left on device

# Diagnostic
df -h
du -sh projets_extraits/

# Solutions
# Nettoyer les fichiers temporaires
find projets_extraits/ -name "*.temp_conversion.*" -delete

# Augmenter l'espace disque ou déplacer vers un autre volume
```

#### 4. Erreur : "Permission denied"
```bash
# Erreur
PermissionError: [Errno 13] Permission denied

# Diagnostic
ls -la projets_extraits/
whoami

# Solutions
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/
```

### Logs Spécifiques à Surveiller

#### Logs de Conversion
```bash
# Succès de conversion
grep "Succès (GPU)" logs/step2/convert_*.log
grep "Succès (CPU)" logs/step2/convert_*.log

# Échecs de conversion
grep "Erreur FFmpeg" logs/step2/convert_*.log
grep "returncode != 0" logs/step2/convert_*.log
```

#### Logs de Performance
```bash
# Temps de traitement
grep "Traitement de la vidéo" logs/step2/convert_*.log

# Statistiques finales
grep "Résumé:" logs/step2/convert_*.log
grep "conversion(s) réussie(s)" logs/step2/convert_*.log
```

#### Logs d'Erreurs Audio
```bash
# Problèmes de copie audio
grep "La copie audio a échoué" logs/step2/convert_*.log
grep "tentative de ré-encodage audio" logs/step2/convert_*.log
```

### Tests de Validation et Vérification

#### Test de Fonctionnement Basique
```bash
# Créer une vidéo de test avec framerate non-standard
ffmpeg -f lavfi -i testsrc=duration=5:size=640x480:rate=30 -c:v libx264 test_30fps.mp4

# Placer dans la structure attendue
mkdir -p test_project/docs
mv test_30fps.mp4 test_project/docs/

# Exécuter la conversion
cd test_project
python ../workflow_scripts/step2/convert_videos.py

# Vérifier le résultat
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 docs/test_30fps.mp4
# Doit retourner: 25/1
```

#### Test de Performance GPU vs CPU
```bash
# Test GPU
time python workflow_scripts/step2/convert_videos.py

# Test CPU (désactiver GPU)
CUDA_VISIBLE_DEVICES="" time python workflow_scripts/step2/convert_videos.py

# Comparer les temps d'exécution
```

#### Validation de l'Intégrité
```python
#!/usr/bin/env python3
"""Script de validation pour l'étape 2."""

def validate_step2_output():
    """Valide que toutes les vidéos sont à 25 FPS."""
    import subprocess
    from pathlib import Path

    base_dir = Path("projets_extraits")
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']

    for video_file in base_dir.rglob("*"):
        if video_file.suffix.lower() in video_extensions:
            try:
                # Vérifier le framerate
                cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                       '-show_entries', 'stream=r_frame_rate', '-of',
                       'default=noprint_wrappers=1:nokey=1', str(video_file)]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                framerate_str = result.stdout.strip()
                if '/' in framerate_str:
                    num, den = map(int, framerate_str.split('/'))
                    fps = num / den if den != 0 else 0
                else:
                    fps = float(framerate_str)

                if abs(fps - 25.0) > 0.1:
                    print(f"❌ {video_file}: FPS incorrect ({fps:.2f})")
                    return False
                else:
                    print(f"✅ {video_file}: FPS correct ({fps:.2f})")

            except Exception as e:
                print(f"❌ Erreur lors de la vérification de {video_file}: {e}")
                return False

    print("✅ Validation réussie: toutes les vidéos sont à 25 FPS")
    return True

if __name__ == "__main__":
    validate_step2_output()
```

### Monitoring et Alertes

#### Surveillance des Ressources GPU
```bash
# Monitoring continu de l'utilisation GPU
watch -n 1 nvidia-smi

# Log de l'utilisation GPU
while true; do
    echo "$(date): $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits)"
    sleep 5
done > gpu_usage.log
```

#### Surveillance de l'Espace Disque
```bash
# Monitoring de l'espace disque pendant conversion
while true; do
    usage=$(df -h projets_extraits/ | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -gt 90 ]; then
        echo "ALERTE: Espace disque critique ($usage%)"
    fi
    sleep 30
done
```

#### Métriques de Performance
```bash
# Calcul du débit de conversion
start_time=$(date +%s)
python workflow_scripts/step2/convert_videos.py
end_time=$(date +%s)
duration=$((end_time - start_time))

video_count=$(find projets_extraits/ -name "*.mp4" -o -name "*.mov" -o -name "*.avi" | wc -l)
throughput=$(echo "scale=2; $video_count / $duration" | bc)
echo "Débit de conversion: $throughput vidéos/seconde"
```
