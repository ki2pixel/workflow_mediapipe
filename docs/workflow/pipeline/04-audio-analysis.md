# Analyse Audio

**TL;DR** : Analyse audio STEP4 avec trois méthodes compatibles : **Pyannote** (défaut), **Lemonfox** (cloud diarisation), **DeepInfra** (OpenAI-compatible STT). Sélection centralisée via `STEP4_METHOD`, contrat JSON inchangé pour STEP5/STEP6.

## Le Problème : Analyse Audio Manuelle Inefficace

Tu dois identifier qui parle et quand dans tes vidéos, mais le faire manuellement est impossible sur des contenus longs. Tu as besoin d'une solution automatique qui distingue les locuteurs et synchronise parfaitement l'analyse audio avec les frames vidéo pour la post-production.

## Notre Solution : Diarisation / Transcription avec Triple Option

Nous utilisons Pyannote.audio 3.1 (local), Lemonfox API (cloud diarisation), et DeepInfra (cloud STT OpenAI-compatible). Le système convertit chaque méthode en timeline frame par frame et conserve le même schéma JSON en sortie.

### ❌ AMP FP16 (anti-pattern)
```bash
# Approche risquée - fausses détections massives
AUDIO_PROFILE=gpu_optimized  # Active AMP FP16
# Résultat : -85% de détection de parole perdue !
```

### ✅ GPU FP32 (pattern recommandé)
```bash
# Approche sûre - cohérence GPU/CPU garantie
AUDIO_PROFILE=gpu_fp32  # FP32 pur, pas d'AMP
# Résultat : détection fiable, cohérence parfaite
```

### Flux d'Analyse Audio

1. **Extraction audio** : FFmpeg convertit la vidéo en WAV 16kHz mono
2. **Diarisation** : Pyannote/Lemonfox identifie les segments de parole par locuteur
3. **Timeline mapping** : Conversion temps → frames (25 FPS)
4. **Post-traitement** : Lissage des détections et comblement des trous
5. **Export JSON** : Format standardisé pour STEP5

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 4 : Analyse audio" dans l'interface

# Via API
curl -X POST http://localhost:5000/run/STEP4

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
# Activation environnement spécialisé
source audio_env/bin/activate

# Exécution depuis projets_extraits
cd projets_extraits
python ../workflow_scripts/step4/run_audio_analysis.py

# Monitoring des logs
tail -f logs/step4/audio_analysis_*.log
```

### Résultat Attendu

```
# Fichier JSON généré
projets_extraits/projet_camille_001/docs/video1_audio.json

# Contenu JSON simplifié
{
  "video_filename": "video1.mp4",
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

## Configuration Essentielle

### Variables d'Environnement

```bash
# Sélection méthode STEP4 (prioritaire)
STEP4_METHOD=pyannote          # pyannote | lemonfox | deepinfra

# Profil de performance (recommandé)
AUDIO_PROFILE=gpu_fp32          # gpu_fp32, gpu_optimized, cpu_only

# GPU/CPU
AUDIO_DISABLE_GPU=0              # 1 pour forcer CPU
AUDIO_CPU_WORKERS=4             # Threads CPU si GPU désactivé

# Authentification Hugging Face (obligatoire pour Pyannote)
HUGGINGFACE_HUB_TOKEN=your_token_here

# Options avancées
AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=1    # Inclure vecteurs locuteurs
AUDIO_PARTIAL_SUCCESS_OK=1             # Succès si ≥1 fichier traité
PYANNOTE_BATCH_SIZE=1                  # Taille batch GPU
```

### Configuration Pyannote (optimal_tv_config.json)

```json
{
  "segmentation": {
    "model": "pyannote/segmentation"
  },
  "embedding": {
    "model": "pyannote/embedding"
  },
  "diarization": {
    "clustering": "AgglomerativeClustering",
    "threshold": 0.5
  }
}
```

### Option Lemonfox (Cloud)

```bash
# Activation Lemonfox
STEP4_USE_LEMONFOX=1
LEMONFOX_API_KEY=votre_cle_api_ici

# Configuration Lemonfox
LEMONFOX_DEFAULT_LANGUAGE=fr
LEMONFOX_DEFAULT_PROMPT="Transcription de contenu vidéo"
LEMONFOX_SPEAKER_LABELS_DEFAULT=1
LEMONFOX_DEFAULT_MIN_SPEAKERS=1
LEMONFOX_DEFAULT_MAX_SPEAKERS=4

# Post-traitement
LEMONFOX_SPEECH_GAP_FILL_SEC=0.15    # Comblement trous courts
LEMONFOX_SPEECH_MIN_ON_SEC=0.0       # Durée min îlots parole
LEMONFOX_TIMESTAMP_GRANULARITIES=word

# Option DeepInfra (Cloud STT OpenAI-compatible)
DEEPINFRA_API_KEY=votre_cle_api_ici
DEEPINFRA_BASE_URL=https://api.deepinfra.com
DEEPINFRA_TRANSCRIPTIONS_ENDPOINT=/v1/openai/audio/transcriptions
DEEPINFRA_MODEL=openai/whisper-large-v3
DEEPINFRA_RESPONSE_FORMAT=verbose_json
DEEPINFRA_TIMESTAMP_GRANULARITIES=segment
DEEPINFRA_TIMEOUT_SEC=300
DEEPINFRA_MAX_RETRIES=2
DEEPINFRA_BACKOFF_SEC=1.5
STEP4_DEEPINFRA_FALLBACK_TO_PYANNOTE=1
```

### Priorité de sélection STEP4

1. `STEP4_METHOD` si valeur valide (`pyannote|lemonfox|deepinfra`)
2. Fallback legacy `STEP4_USE_LEMONFOX=1` (→ Lemonfox)
3. Sinon défaut historique Pyannote

> Endpoint DeepInfra officiel appliqué avec garde-fou typo :
> `https://api.deepinfra.com/v1/openai/audio/transcriptions`
> 
> Toute variante contenant `wisper` est rejetée et remplacée automatiquement.

## Trade-offs par Profil Audio

| Profil | Device | AMP | Usage | Risques | Quand l'utiliser |
|--------|--------|-----|-------|---------|-----------------|
| **gpu_fp32** | CUDA | ❌ | **Recommandé** | VRAM plus élevée | Production, qualité requise |
| gpu_optimized | CUDA | ✅ | VRAM <4GB | **-85% détection** | Tests rapides, VRAM limitée |
| cpu_only | CPU | ❌ | Debug | Lent | Développement, GPU indisponible |

## Trade-offs par Option d'Analyse

| Option | Confidentialité | Coût | Performance | Risques | Quand l'utiliser |
|--------|----------------|------|-------------|---------|-----------------|
| **Pyannote Local** | Totale | Gratuit | GPU requis | Installation complexe | Données sensibles, on-premise |
| **Lemonfox Cloud** | Données externes | Par usage | Stable | Dépendance réseau | Projets ponctuels, pas de GPU |
| **DeepInfra Cloud** | Données externes | Par usage | Stable (retry/backoff) | Dépendance réseau, pas de diarisation native | Transcription rapide compatible API OpenAI |
| **Hybrid** | Configurable | Variable | Flexible | Complexité gestion | Environnements mixtes |

## Analogie : Studio Mixage vs Transcription Cloud

Pense à l'analyse audio comme un **studio mixage** vs un **service de transcription cloud**. **Pyannote** est le studio où tu contrôles tout : l'équipement (GPU), les réglages (profil), et les données restent dans tes murs. **Lemonfox** est le service de transcription externe : rapide et pratique, mais tu envoies tes masters à l'extérieur. Le **profil gpu_fp32** est le mode haute fidélité qui garantit que chaque mot est capturé avec précision.

## Formats Supportés

### Vidéos en Entrée

```python
# Formats supportés (excluant .mov souvent sans audio)
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.webm', '.flv')
```

### Spécifications Audio

- **Extraction** : WAV 16kHz mono via FFmpeg
- **Résolution** : Frame-précise (25 FPS)
- **Locuteurs** : Détection automatique du nombre
- **Timeline** : Synchronisation parfaite avec vidéo

### Format JSON de Sortie

```json
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "speaker_embeddings": {
    "model_id": "pyannote/embedding",
    "embedding_dim": 256,
    "vectors_by_label": {
      "SPEAKER_00": [0.1234, -0.5678, ...],
      "SPEAKER_01": [0.9876, -0.4321, ...]
    }
  },
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

## Performance et Optimisations

### Profils GPU

| Profil | Device | AMP | Usage | Notes |
|--------|--------|-----|-------|-------|
| **gpu_fp32** | CUDA | ❌ | **Recommandé** | FP32 pur, cohérence GPU/CPU |
| gpu_optimized | CUDA | ✅ | VRAM <4GB | **Attention** : -85% détection |
| cpu_only | CPU | ❌ | Debug | Baseline sans GPU |

**⚠️ Important** : AMP (FP16) cause jusqu'à 85% de faux négatifs. Utiliser `gpu_fp32` en production.

### Optimisations Mémoire

```python
# Configuration GPU recommandée
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32

# Gestion OOM automatique
- Vidage cache CUDA en cas d'erreur
- Bascule CPU automatique pour fichier en cours
- Libération explicite des tensors
```

### Optimisations I/O

```python
# Extraction audio via FFmpeg (remplace MoviePy)
cmd = [
    "ffmpeg", "-i", str(video_path),
    "-vn", "-acodec", "pcm_s16le",
    "-ar", "16000", "-ac", "1",
    str(audio_path)  # WAV 16kHz mono
]

# Préférence tmpfs pour performance
temp_dir = Path("/dev/shm") / "audio_analysis_temp"
```

## Monitoring et Logs

### Structure des Logs

```
logs/step4/
└── audio_analysis_20240120_143022.log
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Using GPU profile: gpu_fp32 (FP32, no AMP)
2024-01-20 14:30:23 - INFO - Hugging Face token validated successfully
2024-01-20 14:30:24 - INFO - Processing video: 1/3: video1.mp4
2024-01-20 14:30:45 - INFO - Diarization: 15 segments detected
2024-01-20 14:30:45 - INFO - Timeline audio: 1247/2500 frames with speech (49.9%)
2024-01-20 14:30:46 - INFO - Successfully wrote video1_audio.json
```

### Métriques Clés

```python
# Statistiques finales
logging.info(f"Diarization: {len(segments)} segment(s) détecté(s)")
logging.info(f"Timeline audio: {speech_frames}/{total_frames} frames avec parole ({speech_percent}%)")

# Validation
if speech_percent < 5:
    logging.warning("Faible détection de parole - vérifier configuration")
```

## Dépendances et Prérequis

### Environnement Audio Spécialisé

```bash
# Création environnement isolé
python3 -m venv audio_env
source audio_env/bin/activate

# Installation dépendances Pyannote
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install pyannote.audio
pip install librosa numpy ffmpeg-python
```

### PyTorch CUDA Compatibilité

```bash
# Version recommandée (CUDA 11.x compatible)
pip install torch==1.12.1+cu113 torchvision==0.12.1+cu113 torchaudio==0.12.1+cu113

# Vérification
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, version: {torch.version.cuda}')"
```

### Token Hugging Face (Obligatoire)

```bash
# Configuration du token
export HUGGINGFACE_HUB_TOKEN=hf_your_token_here

# Validation
python -c "from huggingface_hub import HfApi; print(HfApi().whoami())"
```

### FFmpeg (Obligatoire)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Vérification extraction audio
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
```

## Résolution de Problèmes

### GPU OOM (Mémoire Insuffisante)

```bash
# Diagnostic
nvidia-smi
python -c "import torch; print(torch.cuda.memory_allocated()/1024**3)"

# Solutions
# 1. Réduire batch size
PYANNOTE_BATCH_SIZE=1 python workflow_scripts/step4/run_audio_analysis.py

# 2. Forcer CPU
AUDIO_DISABLE_GPU=1 python workflow_scripts/step4/run_audio_analysis.py

# 3. Configuration mémoire
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
```

### Token Hugging Face Invalide

```bash
# Diagnostic
python -c "from huggingface_hub import HfApi; HfApi().whoami()"

# Solution
# 1. Générer nouveau token sur https://huggingface.co/settings/tokens
# 2. Exporter la variable
export HUGGINGFACE_HUB_TOKEN=hf_your_new_token
```

### Fichiers MOV Sans Audio

```bash
# Diagnostic
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name video.mov

# Comportement attendu
# Les fichiers .mov sont automatiquement exclus (souvent sans piste audio)
```

### Lemonfox API Erreurs

```bash
# Diagnostic
curl -H "Authorization: Bearer $LEMONFOX_API_KEY" https://api.lemonfox.ai/v1/status

# Solutions
# 1. Vérifier clé API et quota
# 2. Désactiver Lemonfox (fallback Pyannote)
export STEP4_USE_LEMONFOX=0
```

### DeepInfra API Erreurs

```bash
# Diagnostic endpoint résolu
python - <<'PY'
from config.settings import config
print(config.resolve_deepinfra_transcriptions_url())
PY

# Solutions
# 1. Vérifier DEEPINFRA_API_KEY
# 2. Vérifier endpoint officiel (/v1/openai/audio/transcriptions)
# 3. Laisser fallback actif vers Pyannote
export STEP4_DEEPINFRA_FALLBACK_TO_PYANNOTE=1
```

## Tests et Validation

### Test de Fonctionnement

```bash
# Créer vidéo test avec parole
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=25 -f lavfi -i sine=frequency=1000:duration=10 -c:v libx264 -c:a aac test_speech.mp4

# Préparer structure
mkdir -p test_audio/docs
mv test_speech.mp4 test_audio/docs/

# Exécuter analyse
source audio_env/bin/activate
cd test_audio
python ../workflow_scripts/step4/run_audio_analysis.py

# Vérifier résultat
head docs/test_speech_audio.json | jq '.frames_analysis[0].audio_info'
```

### Validation Automatique

```python
def validate_step4_output():
    """Vérifie que tous les JSON audio sont valides."""
    import json
    from pathlib import Path
    
    base_dir = Path("projets_extraits")
    
    for json_file in base_dir.rglob("*_audio.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
            
            # Vérifier structure minimale
            required_keys = ['video_filename', 'total_frames', 'fps', 'frames_analysis']
            if not all(key in data for key in required_keys):
                print(f"❌ {json_file}: Structure JSON invalide")
                return False
            
            # Vérifier cohérence frames
            total_frames = data['total_frames']
            analysis_frames = len(data['frames_analysis'])
            
            if total_frames != analysis_frames:
                print(f"❌ {json_file}: Incohérence frames ({total_frames} vs {analysis_frames})")
                return False
            
            # Compter locuteurs
            speakers = set()
            for frame in data['frames_analysis']:
                speakers.update(frame['audio_info'].get('active_speaker_labels', []))
            
            print(f"✅ {json_file}: {len(speakers)} locuteurs, {total_frames} frames")
            
        except Exception as e:
            print(f"❌ Erreur lecture {json_file}: {e}")
            return False
    
    print("✅ Validation réussie: tous les JSON audio sont valides")
    return True
```

### Test Performance GPU vs CPU

```bash
# Test GPU
source audio_env/bin/activate
time python workflow_scripts/step4/run_audio_analysis.py

# Test CPU
AUDIO_DISABLE_GPU=1 time python workflow_scripts/step4/run_audio_analysis.py
```

## Intégration Pipeline

### Entrée pour STEP5

L'étape 4 prépare les données audio pour le tracking vidéo :
- **Timeline synchronisée** : `is_speech_present` par frame
- **Identification locuteurs** : `active_speaker_labels` uniques
- **Embeddings optionnels** : Vecteurs par locuteur pour analyses avancées

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP4", "running")
ws.set_step_field("STEP4", "current_video", "video1.mp4")
ws.update_step_progress("STEP4", current=1, total=3)
```

### Compatibilité STEP5

Le format JSON est parfaitement compatible avec STEP5 :
```python
# Utilisation dans enhanced_speaking_detection.py
for frame_data in audio_analysis['frames_analysis']:
    frame_num = frame_data['frame']
    audio_info = frame_data['audio_info']
    
    if audio_info['is_speech_present']:
        # Améliorer détection faciale pendant la parole
        enhance_speaking_detection(frame_num, audio_info)
```

## Pièges Courants et Solutions

### Piège #1 : AMP réduisant la détection
**Solution** : Utiliser profil `gpu_fp32` (désactive AMP) pour éviter les -85% de faux négatifs.

### Piège #2 : Token Hugging Face manquant
**Solution** : Générer token sur https://huggingface.co/settings/tokens et configurer `HUGGINGFACE_HUB_TOKEN`.

### Piège #3 : Fichiers MOV sans audio
**Solution** : Les fichiers `.mov` sont automatiquement exclus par le système.

### Piège #4 : OOM GPU sur vidéos longues
**Solution** : Configuration `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32` et fallback CPU automatique.

### Piège #5 : Lemonfox API coûteuse
**Solution** : Surveiller l'utilisation et basculer vers Pyannote local si nécessaire.

L'étape 4 transforme l'audio brut en intelligence structurée, identifiant précisément qui parle et quand. La timeline frame-précise permet une synchronisation parfaite avec le tracking vidéo, créant une base riche pour l'analyse multimodale.

---

## Golden Rule

**Toujours valider token HF + profil GPU avant run ; sinon tu obtiens des analyses audio incomplètes qui désynchronisent tout le pipeline.**
