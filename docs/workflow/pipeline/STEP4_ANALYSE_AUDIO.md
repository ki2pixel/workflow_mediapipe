# Documentation Technique - Étape 4 : Analyse Audio

## Description Fonctionnelle

### Objectif
L'Étape 4 effectue une analyse audio avancée des vidéos en utilisant la diarisation de locuteurs via Pyannote.audio. Cette étape identifie automatiquement les segments de parole, distingue les différents locuteurs et génère une timeline audio détaillée frame par frame pour optimiser les analyses suivantes.

### Rôle dans le Pipeline
- **Position** : Quatrième étape du pipeline (STEP4)
- **Prérequis** : Vidéos avec fichiers CSV de scènes générés par l'Étape 3
- **Sortie** : Fichiers JSON avec analyse audio détaillée par frame
- **Étape suivante** : Suivi vidéo (STEP5)

### Valeur Ajoutée
- **Diarisation automatique** : Identification et séparation des locuteurs multiples
- **Timeline frame-précise** : Analyse audio synchronisée avec les frames vidéo
- **Modèle pré-entraîné** : Utilisation de Pyannote.audio 3.1, state-of-the-art en diarisation
- **Support multi-locuteurs** : Détection automatique du nombre de locuteurs
- **Intégration workflow** : Données audio utilisées par l'étape de tracking pour améliorer la détection de parole

## Améliorations Récentes (v4.1+)

### Configuration Optimisée de Pyannote (v4.1.2)

**Nouveauté** : Chargement automatique du preset `config/optimal_tv_config.json`

**Détails** :
- Le preset est chargé automatiquement au démarrage du service audio
- Gestion automatique du `batch_size` en fonction de la mémoire disponible
- Optimisation pour la cohérence GPU/CPU via le profil `AUDIO_PROFILE=gpu_fp32`

**Configuration recommandée** :
```bash
# Dans .env ou la configuration du service
AUDIO_PROFILE=gpu_fp32  # Désactive AMP (FP16) pour éviter les faux négatifs
PYANNOTE_BATCH_SIZE=auto  # Ajustement automatique selon la mémoire disponible
```

**Logs de diagnostic** :
```
[INFO] Chargement du preset Pyannote: config/optimal_tv_config.json
[INFO] Configuration GPU/CPU: profile=gpu_fp32, batch_size=16
[PROFILING] Pyannote inference: 42.3ms/segment (moyenne sur 100 segments)
```

### Intégration de Lemonfox avec Fallback Pyannote (v4.1.1)

#### Nouveau : Support de Lemonfox pour l'Analyse Audio

**Fonctionnalité** : 
- **Lemonfox** est maintenant la solution principale pour l'analyse audio, avec un fallback automatique vers Pyannote en cas d'échec.
- Activation via la variable d'environnement `STEP4_USE_LEMONFOX=1`

**Avantages** :
- Meilleure précision de la détection de parole
- Réduction des faux positifs
- Support natif du français et d'autres langues
- Détection automatique du nombre de locuteurs

#### Synthèse des variables `LEMONFOX_*`

| Domaine | Variables principales | Description |
| --- | --- | --- |
| Activation & API | `STEP4_USE_LEMONFOX`, `LEMONFOX_API_KEY`, `LEMONFOX_TIMEOUT_SEC`, `LEMONFOX_EU_DEFAULT` | Active l’intégration Lemonfox, configure la clé API et choisit l’endpoint (EU/global). |
| Paramètres linguistiques | `LEMONFOX_DEFAULT_LANGUAGE`, `LEMONFOX_DEFAULT_PROMPT`, `LEMONFOX_DETECT_LANGUAGE`, `LEMONFOX_LANGUAGE` | Détermine la langue par défaut, le prompt et la détection automatique. |
| Diarisation / locuteurs | `LEMONFOX_SPEAKER_LABELS_DEFAULT`, `LEMONFOX_DEFAULT_MIN_SPEAKERS`, `LEMONFOX_DEFAULT_MAX_SPEAKERS`, `LEMONFOX_ENABLE_DIARIZATION`, `LEMONFOX_MIN_SPEAKERS`, `LEMONFOX_MAX_SPEAKERS` | Contrôle le nombre de locuteurs détectés et la labellisation automatique. |
| Upload & transcodage | `LEMONFOX_MAX_UPLOAD_MB`, `LEMONFOX_ENABLE_TRANSCODE`, `LEMONFOX_TRANSCODE_AUDIO_CODEC`, `LEMONFOX_TRANSCODE_BITRATE_KBPS` | Limite d’upload et fallback audio-only (mono 16 kHz) déclenché automatiquement. |
| Performance & modèle | `LEMONFOX_BATCH_SIZE`, `LEMONFOX_CHUNK_LENGTH`, `LEMONFOX_NUM_WORKERS`, `LEMONFOX_MODEL`, `LEMONFOX_TEMPERATURE`, `LEMONFOX_COMPRESSION_RATIO` | Réglages Throughput/Whisper, chunking, compression. |
| Smoothing timeline | `LEMONFOX_SPEECH_GAP_FILL_SEC`, `LEMONFOX_SPEECH_MIN_ON_SEC`, `LEMONFOX_TIMESTAMP_GRANULARITIES` | Stabilise `is_speech_present` et les timestamps exportés. |
| VAD & fiabilité | `LEMONFOX_VAD_FILTER`, `LEMONFOX_VAD_THRESHOLD`, `LEMONFOX_VAD_MIN_SILENCE_DURATION`, `LEMONFOX_RETRY_ATTEMPTS`, `LEMONFOX_RETRY_DELAY`, `LEMONFOX_DEBUG`, `LEMONFOX_VERBOSE` | Filtrage VAD et stratégie de retry/logging. |

> ℹ️ Toutes les variables sont définies dans `config/settings.py`. Valider la configuration via `python -c "from config.settings import config; config.validate(); print('Config OK')"` avant de lancer STEP4.

**Configuration requise** :
```bash
# Activation de Lemonfox (1=activé, 0=désactivé)
STEP4_USE_LEMONFOX=1
LEMONFOX_API_KEY=votre_cle_api_ici
LEMONFOX_MAX_UPLOAD_MB=95            # Limite imposée par Lemonfox (MB). Déclenche le transcodage audio-only si activé.
LEMONFOX_ENABLE_TRANSCODE=1          # 1 = autorise le transcodage automatique pour respecter la limite d'upload
LEMONFOX_TRANSCODE_AUDIO_CODEC=aac   # Codec ffmpeg utilisé pour l'audio-only
LEMONFOX_TRANSCODE_BITRATE_KBPS=96   # Bitrate cible du transcodage audio-only
LEMONFOX_TIMEOUT_SEC=300
LEMONFOX_EU_DEFAULT=0  # 1 pour endpoint EU, 0 pour standard

# Paramètres avancés
LEMONFOX_DEFAULT_LANGUAGE=fr
LEMONFOX_DEFAULT_PROMPT="Transcription de contenu vidéo"
LEMONFOX_SPEAKER_LABELS_DEFAULT=1
LEMONFOX_DEFAULT_MIN_SPEAKERS=1
LEMONFOX_DEFAULT_MAX_SPEAKERS=4

# Post-traitement et lissage
LEMONFOX_SPEECH_GAP_FILL_SEC=0.3  # Combler les silences < 300ms
LEMONFOX_SPEECH_MIN_ON_SEC=0.5     # Ignorer les segments < 500ms
LEMONFOX_CONFIDENCE_THRESHOLD=0.7  # Seuil de confiance minimum

# Configuration du modèle
LEMONFOX_MODEL=whisper-large-v3    # Modèle Whisper à utiliser
LEMONFOX_TEMPERATURE=0.2           # Contrôle de la créativité (0-1)
LEMONFOX_COMPRESSION_RATIO=2.0      # Contrôle de la compression

# Détection de langue
LEMONFOX_DETECT_LANGUAGE=1         # Détection automatique de la langue
LEMONFOX_LANGUAGE=fr               # Forcer une langue spécifique

# Optimisation des performances
LEMONFOX_BATCH_SIZE=16             # Taille des lots pour l'inférence
LEMONFOX_CHUNK_LENGTH=30           # Découpage en segments de 30s
LEMONFOX_NUM_WORKERS=4             # Nombre de workers pour le prétraitement

# Détection de locuteurs
LEMONFOX_ENABLE_DIARIZATION=1      # Activer la diarisation
LEMONFOX_MIN_SPEAKERS=1            # Nombre minimum de locuteurs
LEMONFOX_MAX_SPEAKERS=4            # Nombre maximum de locuteurs

# Post-traitement avancé
LEMONFOX_VAD_FILTER=1              # Filtrage par Voice Activity Detection
LEMONFOX_VAD_THRESHOLD=0.5         # Seuil de détection de parole
LEMONFOX_VAD_MIN_SILENCE_DURATION=0.3  # Durée minimale de silence

# Logging et débogage
LEMONFOX_DEBUG=0                   # Activer les logs de débogage
LEMONFOX_VERBOSE=1                 # Niveau de verbosité des logs

# Gestion des erreurs
LEMONFOX_RETRY_ATTEMPTS=3          # Nombre de tentatives en cas d'échec
LEMONFOX_RETRY_DELAY=5             # Délai entre les tentatives (secondes)
LEMONFOX_TIMEOUT=300               # Délai d'attente maximal (secondes)
LEMONFOX_TIMESTAMP_GRANULARITIES=word
LEMONFOX_SPEECH_GAP_FILL_SEC=0.15  # Comblement des trous courts
LEMONFOX_SPEECH_MIN_ON_SEC=0.0     # Durée minimum des îlots de parole
```

> **Nouveau (2025-12-29)** : `_call_lemonfox_api()` applique désormais une politique stricte de taille d'upload.  
> - Si la vidéo dépasse `LEMONFOX_MAX_UPLOAD_MB`, un transcodage audio-only (mono 16 kHz) est tenté quand `LEMONFOX_ENABLE_TRANSCODE=1`.  
> - En cas de dépassement persistant ou si le transcodage est désactivé, STEP4 échoue explicitement avec un message d'erreur guidant l'opérateur.  
> - Les logs Lemonfox indiquent désormais la taille locale et la limite configurée pour faciliter le diagnostic des HTTP 413.

#### Mécanisme de Fallback Automatique

1. **Tentative avec Lemonfox** :
   - Le système tente d'abord d'utiliser l'API Lemonfox
   - En cas d'échec (timeout, erreur API, etc.), le système bascule automatiquement vers Pyannote
   - Un message est enregistré dans les logs pour indiquer le fallback

2. **Utilisation de Pyannote** :
   - Charge automatiquement la configuration optimisée depuis `config/optimal_tv_config.json` (profil TV documenté)
   - Conserve les optimisations précédentes (extraction FFmpeg, etc.)
   - Utilise le même format de sortie JSON pour assurer la compatibilité
   - Si le preset échoue (incompatibilité selon version Pyannote), un fallback minimal est appliqué puis journalisé

> **Important** : Les scripts `workflow_scripts/step4/run_audio_analysis.py` et `run_audio_analysis_lemonfox.py` résolvent les services via `importlib` au lieu d’importer le package `services`. Cela évite de charger `flask_caching` dans `audio_env` et rend les workers Lemonfox autonomes.
>
> **Recommandation** : conserver l’environnement Pyannote opérationnel même lorsque Lemonfox est activé afin de garantir un fallback immédiat (voir `memory-bank/decisionLog.md`, entrée du 13 janvier 2026).

#### Optimisations de Performance et Fiabilité (2025-10-06 15:29:19+02:00)

#### 1. Extraction Audio via ffmpeg (Remplace MoviePy)
**Problème** : MoviePy était lent et ajoutait des dépendances lourdes (imageio, decorator, proglog).

**Solution** : Extraction directe via ffmpeg subprocess avec sortie vers tmpfs.

```python
import subprocess
import tempfile
from pathlib import Path

def extract_audio_to_wav(video_path: Path) -> Path:
    """Extrait l'audio via ffmpeg vers tmpfs si disponible."""
    # Préférence tmpfs (/dev/shm) pour I/O rapides
    tmpfs_dir = Path("/dev/shm")
    if tmpfs_dir.exists() and tmpfs_dir.is_dir():
        temp_dir = tmpfs_dir / "audio_analysis_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = Path(tempfile.gettempdir()) / "audio_analysis_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    audio_path = temp_dir / f"{video_path.stem}_audio.wav"
    
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn",  # Pas de vidéo
        "-acodec", "pcm_s16le",  # WAV PCM
        "-ar", "16000",  # 16kHz (Pyannote compatible)
        "-ac", "1",  # Mono
        str(audio_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path
```

**Avantages** :
- Réduction de la latence d'extraction audio (tmpfs RAM-based)
- Suppression dépendances MoviePy
- Contrôle fin des paramètres FFmpeg

#### 2. Métadonnées Vidéo via ffprobe (Remplace OpenCV)
**Problème** : OpenCV (`cv2.VideoCapture`) était lent et parfois instable.

**Solution** : Utilisation de ffprobe avec fallback FPS=25.

```python
import subprocess
import json

def get_video_metadata_ffprobe(video_path: Path) -> dict:
    """Extrait métadonnées via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration,nb_frames",
        "-of", "json",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    stream = data["streams"][0]
    fps_frac = stream["r_frame_rate"].split("/")
    fps = float(fps_frac[0]) / float(fps_frac[1]) if len(fps_frac) == 2 else 25.0
    
    # Fallback FPS=25 si non détectable
    if fps <= 0 or fps > 120:
        fps = 25.0
    
    return {
        "fps": fps,
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "total_frames": int(stream.get("nb_frames", 0)),
        "duration": float(stream.get("duration", 0.0))
    }
```

**Avantages** :
- Métadonnées plus fiables
- Réduction dépendances (pas besoin d'OpenCV pour métadonnées)
- Fallback FPS=25 pour cohérence pipeline

#### 3. Écriture JSON en Streaming
**Problème** : Stockage complet de la liste de diarisation en mémoire avant écriture.

**Solution** : Mapping segments→frames à la volée avec écriture streaming.

```python
import json

def write_audio_analysis_streaming(output_path: Path, video_meta: dict, diarization):
    """Écrit JSON frame par frame sans matérialiser la liste complète."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        f.write(f'  "video_filename": "{video_meta["filename"]}",\n')
        f.write(f'  "total_frames": {video_meta["total_frames"]},\n')
        f.write(f'  "fps": {video_meta["fps"]},\n')
        f.write('  "frames_analysis": [\n')
        
        fps = video_meta["fps"]
        total_frames = video_meta["total_frames"]
        
        # Mapping segments→frames sans liste intermédiaire
        for frame_num in range(1, total_frames + 1):
            timecode_sec = (frame_num - 1) / fps
            
            # Recherche du segment actif
            active_speaker_labels = []
            for turn, track, speaker in diarization.itertracks(yield_label=True):
                if turn.start <= timecode_sec <= turn.end:
                    active_speaker_labels = [speaker]
                    break
            
            frame_data = {
                "frame": frame_num,
                "audio_info": {
                    "is_speech_present": len(active_speaker_labels) > 0,
                    "num_distinct_speakers_audio": len(active_speaker_labels),
                    "active_speaker_labels": active_speaker_labels,
                    "timecode_sec": round(timecode_sec, 3),
                }
            }
            
            # Écriture immédiate (pas de stockage)
            json.dump(frame_data, f)
            if frame_num < total_frames:
                f.write(',\n    ')
        
        f.write('\n  ]\n')
        f.write('}\n')
```

**Avantages** :
- Réduction drastique de l'usage mémoire (pas de liste de N frames)
- Évite les pics mémoire sur vidéos longues (>10k frames)
- Écriture progressive

#### 4. Optimisations PyTorch
**Implémentation** :

```python
import torch

# Context managers pour désactiver grad et autocast
with torch.inference_mode():
    with torch.no_grad():
        # Diarisation sans calcul de gradients
        diarization = pipeline(audio_path)
```

**Configuration Device** :

```python
import os

# Politique device configurable via env
disable_gpu = os.getenv("AUDIO_DISABLE_GPU", "0") == "1"
cpu_workers = int(os.getenv("AUDIO_CPU_WORKERS", "4"))

if disable_gpu:
    device = torch.device("cpu")
    torch.set_num_threads(cpu_workers)
else:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(cpu_workers)

pipeline = Pipeline.from_pretrained(model_name, use_auth_token=hf_token)
pipeline.to(device)
```

**Variables d'environnement** :
- `AUDIO_DISABLE_GPU=1` : Force CPU
- `AUDIO_CPU_WORKERS=N` : Nombre de threads PyTorch CPU

#### 5. Nettoyage Robuste des Répertoires Temporaires
**Implémentation** :

```python
import shutil
import logging

def cleanup_temp_audio(temp_dir: Path):
    """Suppression robuste avec gestion d'erreurs."""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logging.info(f"Nettoyage: {temp_dir} supprimé")
    except Exception as e:
        logging.warning(f"Échec nettoyage {temp_dir}: {e}")

# Appel systématique dans finally
try:
    # ... traitement audio ...
finally:
    cleanup_temp_audio(temp_audio_dir)
```

#### 6. Réduction des Logs
- Suppression des prints dupliqués lors du traitement batch
- Logs structurés avec niveaux appropriés (INFO/WARNING/ERROR)
- Rapport de progression condensé (toutes les 1000 frames)

#### 7. Compatibilité STEP5
**Schéma de sortie JSON inchangé** pour garantir la compatibilité avec l'Étape 5 (tracking).

```json
{
  "video_filename": "video.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "frames_analysis": [
    {
      "frame": 1,
      "audio_info": {
        "is_speech_present": true,
        "num_distinct_speakers_audio": 1,
        "active_speaker_labels": ["SPEAKER_00"],
        "timecode_sec": 0.0
      }
    },
    {
      "frame": 2,
      "audio_info": {
        "is_speech_present": true,
        "num_distinct_speakers_audio": 1,
        "active_speaker_labels": ["SPEAKER_00"],
        "timecode_sec": 0.04
      }
    }
  ]
}
```

### Résultats Observés
- **Temps d'extraction audio** : Réduction ~40% grâce à ffmpeg+tmpfs
- **Usage mémoire** : Réduction ~60% grâce au streaming JSON
- **Compatibilité** : Aucune régression, schéma identique
- **Stabilité** : Nettoyage robuste, pas de fichiers temporaires résiduels

## Mises à jour v4.1 — 2025-11-18 (GPU rétrocompatible + robustesse)
### Environnement GPU rétrocompatible (CUDA 11.x)
- Environnement `audio_env` recréé en Python 3.10 avec `torch==1.12.1+cu113` et `torchaudio==0.12.1+cu113`.
- Compatible drivers NVIDIA CUDA 11.x sur machines legacy.

### Authentification Hugging Face (obligatoire)
- Variable `HUGGINGFACE_HUB_TOKEN` requise (ou `--hf_auth_token`).
- Persistance du token via `HfFolder.save_token()` lorsque disponible.
- Vérification d'auth via `HfApi().whoami()` (journalisée, tolérante aux erreurs).

### Chargement de pipeline pyannote
- Tentative v3.1 (`pyannote/speaker-diarization-3.1`) avec `token` (API Hugging Face ≥ 0.19) et fallback automatique `use_auth_token` si la version installée ne supporte pas `token`.
- Fallback automatique v2 (`pyannote/speaker-diarization`) si v3.1 indisponible.
- Gestion des pipelines ne supportant pas `.to()` (message d'information, exécution sans déplacement explicite).

### Mitigations OOM et Optimisation Mémoire

#### Gestion de la Mémoire GPU

1. **Configuration Recommandée** :
   ```bash
   export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
   ```
   - Optimisé pour PyTorch 1.12.1+cu113
   - Désactive `expandable_segments` pour éviter la fragmentation mémoire
   - Limite la taille des blocs mémoire alloués

2. **Gestion des Dépassements de Mémoire (OOM)** :
   - Vidage automatique du cache CUDA en cas d'erreur OOM
   - Bascule automatique sur le CPU pour le fichier en cours
   - Journalisation détaillée pour le débogage

3. **Optimisations Supplémentaires** :
   - Vidage du cache GPU entre chaque fichier traité
   - Libération explicite des tenseurs inutilisés
   - Désallocation des modèles après utilisation

### Exclusions et politiques
- Les fichiers `.mov` sont exclus de l'analyse audio (souvent sans piste audio).
- Politique de succès partiel: définir `AUDIO_PARTIAL_SUCCESS_OK=1` pour considérer l'étape comme réussie si ≥1 fichier a abouti (code de sortie 0), sinon code 1 en cas d'échecs partiels.

### Profils de Configuration (v4.1.1 - 2025-12-15)

Quatre profils disponibles via `AUDIO_PROFILE` dans `.env`:

| Profil | Device | AMP | Batch Size | Usage |
|--------|--------|-----|------------|-------|
| **`gpu_fp32`** | CUDA | ❌ | 1 | **Recommandé** - FP32 pur, cohérence GPU/CPU |
| `gpu_optimized` | CUDA | ✅ | 1 | VRAM <4GB - **Qualité réduite** (faux négatifs) |
| `gpu_no_amp` | CUDA | ❌ | 1 | Alias de `gpu_fp32` |
| `cpu_only` | CPU | ❌ | - | Debug / Baseline |

#### Comportement des profils

1. **`gpu_fp32` (recommandé)** :
   - Désactive AMP via `AUDIO_ENABLE_AMP=0`
   - Force `AUDIO_PYANNOTE_BATCH_SIZE=1`
   - Active le GPU avec FP32 natif
   - **Logs** : `[INFO] Using GPU profile: gpu_fp32 (FP32, no AMP)`

2. **`gpu_optimized`** :
   - Active AMP via `AUDIO_ENABLE_AMP=1`
   - Utilise `AUDIO_PYANNOTE_BATCH_SIZE=1`
   - **Attention** : Peut causer jusqu'à 85% de faux négatifs
   - **Logs** : `[WARNING] Using GPU profile with AMP - may have reduced accuracy`

3. **`cpu_only`** :
   - Désactive le GPU via `CUDA_VISIBLE_DEVICES=""`
   - Logs explicites sur l'utilisation CPU
   - **Logs** : `[INFO] Running in CPU-only mode (debug/validation)`

**⚠️ IMPORTANT**: AMP (mixed precision FP16) peut causer des **divergences massives** dans la détection de parole (jusqu'à -85% de frames détectées). Privilégier `gpu_fp32` en production.

#### Signaux de validation

À la fin de l'analyse, le script loggue des métriques clés :
```
[INFO] Diarization: X segment(s) détecté(s)
[INFO] Timeline audio: Y/Z frames avec parole (W%)
```

**Documentation complète**: Voir `docs/workflow/STEP4_GPU_CPU_COHERENCE.md` pour l'analyse détaillée du problème AMP et le protocole de validation.

## Intégration Lemonfox (v4.1+) - Mise à jour 2025-12-19

### Import Dynamique avec importlib

**Nouveauté** : Chargement dynamique de `LemonfoxAudioService` pour éviter les conflits de dépendances

**Implémentation** :
```python
try:
    # Chargement dynamique pour éviter les conflits Flask
    from importlib import import_module
    LemonfoxAudioService = getattr(
        import_module('services.lemonfox_audio_service'),
        'LemonfoxAudioService'
    )
    lemonfox_service = LemonfoxAudioService()
except ImportError as e:
    logger.warning(f"Lemonfox non disponible: {e}")
    lemonfox_service = None
```

**Avantages** :
- Isolation des dépendances dans `audio_env`
- Évite les conflits avec les dépendances de l'application principale
- Permet une désactivation propre en cas d'erreur

### Vue d'ensemble
Lemonfox est une alternative à Pyannote.audio pour l'analyse audio, utilisant une API externe de speech-to-text avec diarisation. Cette intégration permet de traiter les vidéos via un service cloud tout en conservant la compatibilité complète avec le pipeline existant.

### Architecture Lemonfox

#### Composants principaux
1. **LemonfoxAudioService** (`services/lemonfox_audio_service.py`)
   - Service principal pour l'interaction avec l'API Lemonfox
   - Conversion des données Lemonfox vers format STEP4
   - Gestion des erreurs et fallback automatique

2. **Wrapper d'exécution** (`workflow_scripts/step4/run_audio_analysis_lemonfox.py`)
   - Script d'orchestration pour l'environnement `audio_env`
   - Import du service via `importlib` (évite les dépendances Flask)
   - Fallback automatique vers Pyannote en cas d'échec

3. **Configuration centralisée** (`config/settings.py`)
   - Variables d'environnement `LEMONFOX_*`
   - Toggle d'activation `STEP4_USE_LEMONFOX`

### Configuration Lemonfox

#### Variables d'environnement requises

```bash
# Activation de Lemonfox pour STEP4
STEP4_USE_LEMONFOX=1

# Clé API Lemonfox (obligatoire)
LEMONFOX_API_KEY=votre_cle_api_ici

# Configuration API
LEMONFOX_TIMEOUT_SEC=300          # Timeout en secondes
LEMONFOX_EU_DEFAULT=0             # 1 pour endpoint EU, 0 pour standard

# Paramètres par défaut (optionnels)
LEMONFOX_DEFAULT_LANGUAGE=fr
LEMONFOX_DEFAULT_PROMPT="Transcription de contenu vidéo"
LEMONFOX_SPEAKER_LABELS_DEFAULT=1
LEMONFOX_DEFAULT_MIN_SPEAKERS=1
LEMONFOX_DEFAULT_MAX_SPEAKERS=4
LEMONFOX_TIMESTAMP_GRANULARITIES=word

# Post-traitement de la timeline
LEMONFOX_SPEECH_GAP_FILL_SEC=0.15    # Comblement des trous courts
LEMONFOX_SPEECH_MIN_ON_SEC=0.0       # Durée minimum des îlots de parole
```

#### Activation/Désactivation

Pour activer Lemonfox :
```bash
export STEP4_USE_LEMONFOX=1
export LEMONFOX_API_KEY=votre_clé
```

Pour désactiver (retour à Pyannote) :
```bash
export STEP4_USE_LEMONFOX=0
# ou simplement ne pas définir la variable
```

### Flux d'exécution Lemonfox

#### 1. Détection et activation
Le système vérifie `STEP4_USE_LEMONFOX` au démarrage de STEP4 :
- Si `=1` : exécution du wrapper Lemonfox
- Sinon : exécution du script Pyannote standard

#### 2. Processus Lemonfox
```python
# Depuis workflow_scripts/step4/run_audio_analysis_lemonfox.py
def main():
    # Import du service via importlib (isolation environnement)
    lemonfox_service = _import_lemonfox_audio_service()
    
    # Traitement vidéo par vidéo
    for video_path in videos_to_process:
        result = lemonfox_service.process_video_with_lemonfox(
            project_name=project_name,
            video_name=video_name,
            # Paramètres optionnels hérités de la config
        )
        
        if not result.success:
            # Fallback automatique vers Pyannote
            return _run_pyannote_fallback(log_dir)
```

#### 3. Fallback automatique
En cas d'erreur Lemonfox :
- Échec API (timeout, erreur HTTP)
- Import impossible (dépendances manquantes)
- Clé API non configurée

Le système bascule automatiquement vers Pyannote sans intervention manuelle.

### Conversion Lemonfox → Format STEP4

#### Mapping des données
Lemonfox retourne :
```json
{
  "segments": [
    {
      "start": 1.23,
      "end": 3.45,
      "speaker": "A"
    }
  ],
  "words": [
    {
      "start": 1.23,
      "end": 1.45,
      "word": "bonjour",
      "speaker": "A"
    }
  ]
}
```

Conversion vers format STEP4 :
```python
# Timeline frame par frame
for frame_num in range(1, total_frames + 1):
    timecode_sec = (frame_num - 1) / fps
    
    # Détection du locuteur actif
    active_speakers = []
    for word in transcription.words:
        if word.start <= timecode_sec <= word.end:
            active_speakers.append(f"SPEAKER_{speaker_map[word.speaker]}")
    
    frame_data = {
        "frame": frame_num,
        "audio_info": {
            "is_speech_present": len(active_speakers) > 0,
            "num_distinct_speakers_audio": len(active_speakers),
            "active_speaker_labels": active_speakers,
            "timecode_sec": round(timecode_sec, 3)
        }
    }
```

### Post-traitement de la timeline

#### Smoothing de la détection de parole
Pour stabiliser `is_speech_present` sur les contenus TV :

1. **Gap Fill** (`LEMONFOX_SPEECH_GAP_FILL_SEC`)
   - Comble les trous courts entre segments de parole
   - Évite les interruptions artificielles
   - Par défaut : 0.15s

2. **Minimum On** (`LEMONFOX_SPEECH_MIN_ON_SEC`)
   - Supprime les îlots de parole très courts
   - Élimine les faux positifs de bruit
   - Par défaut : 0.0s (désactivé)

#### Exemple de smoothing
```python
# Avant smoothing : [parole]--0.1s--[parole]--0.3s--[bruit]--0.05s--[parole]
# Après smoothing (gap_fill=0.15s, min_on=0.1s) : [parole]---[parole]----------[parole]
```

### Compatibilité et intégration

#### Sortie JSON identique
Lemonfox génère exactement le même format JSON que Pyannote :
```json
{
  "video_filename": "video.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "frames_analysis": [
    {
      "frame": 1,
      "audio_info": {
        "is_speech_present": true,
        "num_distinct_speakers_audio": 1,
        "active_speaker_labels": ["SPEAKER_00"],
        "timecode_sec": 0.0
      }
    }
  ]
}
```

#### Intégration STEP5
- Aucune modification requise dans STEP5
- `enhanced_speaking_detection.py` utilise les mêmes champs
- Compatible avec toutes les étapes en aval

### Avantages de Lemonfox

1. **Service cloud** : Pas besoin de GPU local
2. **Qualité constante** : Modèles optimisés par Lemonfox
3. **Scalabilité** : Traitement parallèle possible
4. **Robustesse** : Fallback automatique vers Pyannote
5. **Flexibilité** : Toggle simple pour basculer entre les deux

### Limitations et considérations

1. **Dépendance réseau** : Connexion internet requise
2. **Coût API** : Utilisation payante du service Lemonfox
3. **Latence réseau** : Temps de traitement variable
4. **Confidentialité** : Données envoyées vers un service externe

### Monitoring et logs

#### Logs spécifiques Lemonfox
```
[INFO] Calling Lemonfox API for video.mp4...
[INFO] Lemonfox API success: 15 segments, duration=62.3s
[INFO] Built timeline with 1247 frames containing speech
[INFO] Successfully wrote /path/to/video_audio.json
```

#### Logs de fallback
```
[ERROR] Impossible d'importer LemonfoxAudioService: No module named 'flask_caching'
[ERROR] Fallback STEP4: exécution de la méthode originale (Pyannote)
```

### Tests et validation

#### Tests unitaires
- `tests/unit/test_lemonfox_audio_service.py`
- Validation de la conversion Lemonfox → STEP4
- Tests des paramètres de smoothing

#### Tests d'intégration
- `tests/integration/test_lemonfox_wrapper.py`
- Validation du fallback automatique
- Tests de configuration des variables d'environnement

### Références
- Service principal : `services/lemonfox_audio_service.py`
- Wrapper : `workflow_scripts/step4/run_audio_analysis_lemonfox.py`
- Configuration : `config/settings.py` (variables `LEMONFOX_*`)
- Tests : `tests/unit/test_lemonfox_audio_service.py`
- Documentation détaillée : `docs/workflow/STEP4_LEMONFOX_IMPLEMENTATION_STATUS.md`

### Références
- Implémentation: `workflow_scripts/step4/run_audio_analysis.py`.
- Implémentation Lemonfox: `services/lemonfox_audio_service.py`.
- Wrapper Lemonfox: `workflow_scripts/step4/run_audio_analysis_lemonfox.py`.
- Logs: `logs/step4/*.log`.
- Cohérence GPU/CPU: `docs/workflow/STEP4_GPU_CPU_COHERENCE.md`.
- Comparateur: `debug/compare_audio_json.py`.
- Statut Lemonfox: `docs/workflow/STEP4_LEMONFOX_IMPLEMENTATION_STATUS.md`.
