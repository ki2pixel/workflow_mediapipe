# Analyse Audio

**TL;DR** : Analyse audio STEP4 avec isolation GPU forcée (`AUDIO_GPU_ISOLATION=1`) exécutée en sous-processus pour éviter les crashs SIGSEGV et fuites VRAM. Supporte également l'accélération matérielle basse consommation Google Coral Edge TPU. Quatre méthodes compatibles : **Pyannote** (défaut local GPU/CPU), **Lemonfox** (cloud diarisation), **DeepInfra** (cloud STT), et **Edge TPU** (YAMNet local + Spectral Clustering CPU). Sélection centralisée via `STEP3_METHOD`, contrat JSON inchangé pour STEP4/STEP5.

## Le Problème : Analyse Audio Manuelle Inefficace

Tu dois identifier qui parle et quand dans tes vidéos, mais le faire manuellement est impossible sur des contenus longs. Tu as besoin d'une solution automatique qui distingue les locuteurs et synchronise parfaitement l'analyse audio avec les frames vidéo pour la post-production.

## Notre Solution : Diarisation / Transcription avec Quadruple Option

Nous utilisons Pyannote.audio 3.1 (local), Lemonfox API (cloud diarisation), DeepInfra (cloud STT OpenAI-compatible), et l'accélération matérielle Google Coral Edge TPU. Le système convertit chaque méthode en timeline frame par frame et conserve le même schéma JSON en sortie.

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
5. **Export JSON** : Format standardisé pour STEP4

## Utilisation Rapide

### Lancement Automatique

```bash
# Via l'interface web
# Clique sur "Étape 3 : Analyse audio" dans l'interface

# Via API
curl -X POST http://127.0.0.1:5003/run/STEP3

# Dans une séquence complète
const steps = ['STEP1', 'STEP2', 'STEP3', 'STEP4', 'STEP5', 'STEP6', 'STEP7', 'STEP8'];
await apiService.runCustomSequence(steps);
```

### Exécution Manuelle (Debug)

```bash
# Activation environnement spécialisé
source audio_env/bin/activate

# Exécution depuis projets_extraits
cd projets_extraits
python ../workflow_scripts/step3/run_audio_analysis.py

# Monitoring des logs
tail -f logs/step3/audio_analysis_*.log
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
# Sélection méthode STEP4 (lorsque TPU désactivé)
STEP3_METHOD=pyannote          # pyannote | lemonfox | deepinfra

# Accélération matérielle
ENABLE_CORAL_TPU_ACCELERATION=false # true pour activer l'Edge TPU (YAMNet)

# Profil de performance (recommandé lorsque TPU désactivé)
AUDIO_PROFILE=gpu_fp32          # gpu_fp32, gpu_optimized, cpu_only

# GPU/CPU et Isolation
AUDIO_GPU_ISOLATION=1             # Requis : Isolation GPU en sous-processus
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

### Isolation GPU et Stabilité

Le pipeline impose `AUDIO_GPU_ISOLATION=1` pour exécuter l'analyse Pyannote dans un sous-processus isolé. Cela prévient catégoriquement :
- Les crashs `SIGSEGV` liés à la libération de la VRAM
- Les fuites de mémoire PyTorch dans le processus parent
- Les conflits de contexte CUDA avec les étapes suivantes

### Option Lemonfox (Cloud)

```bash
# Activation Lemonfox
STEP3_METHOD=lemonfox
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
STEP3_DEEPINFRA_FALLBACK_TO_PYANNOTE=1
```

### Priorité de sélection STEP4

1. Accélération Coral TPU si `ENABLE_CORAL_TPU_ACCELERATION=true` (→ Exécution de `run_audio_diarization_tpu.py` sous `coral_env`).
2. `STEP3_METHOD` si valeur valide (`pyannote|lemonfox|deepinfra`)
3. Fallback legacy `STEP3_USE_LEMONFOX=1` (→ Lemonfox)
4. Sinon défaut historique Pyannote (local)

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
| **Edge TPU (YAMNet)** | Totale | Gratuit | Très rapide (VAD local TPU) | Faible résolution diarisation (Spectral Clustering CPU) | Postes Edge locaux basse consommation sans GPU dédié |
| **Hybrid** | Configurable | Variable | Flexible | Complexité gestion | Environnements mixtes |

## Accélération Google Coral Edge TPU

Lorsque `ENABLE_CORAL_TPU_ACCELERATION=true` est configuré dans le fichier `.env`, l'étape 3 bascule vers un pipeline de traitement audio local ultra-léger et économe :

* **Script d'exécution** : `workflow_scripts/step3/run_audio_diarization_tpu.py`
* **Fonctionnement** :
  1. **Extraction audio** : FFmpeg convertit la vidéo en fichier audio WAV 16kHz mono.
  2. **VAD par fenêtrage glissant (Edge TPU)** : Inférence du modèle quantifié YAMNet INT8 sur le Coral TPU avec 50% de recouvrement (hop size de 0.48s pour une fenêtre d'analyse de 0.96s). Un pipeline producteur-consommateur à double tampon (blocs de 256 fenêtres) quantifie le bloc suivant en RAM hôte pendant que l'ASIC traite le bloc courant ; le verrou TPU est acquis une fois par bloc et les tenseurs transitent par les vues directes `interpreter.tensor()` (sans copie `set_tensor`/`get_tensor`). L'activation effective du délégué est vérifiée au démarrage via la présence de `edgetpu-custom-op` ; le repli CPU/XNNPACK est journalisé en erreur (bloquant avec `STEP3_REQUIRE_EDGETPU=1`).
  3. **Lissage VAD et FSM Hangover** : Noyau Numba JIT fusionnant le filtre médian 1D (taille 5, bordure zéro identique à `scipy.signal.medfilt`), le seuillage strict à $0.20$ et la Machine à États Finis (FSM) avec *hangover* de 1.0s (3 trames à 0.48s) qui relie les micro-silences physiologiques intra-mots.
  4. **Speaker Embedding (ECAPA-TDNN CPU)** : Extraction de d-vectors 192D via **ONNX Runtime FP32** (jamais de quantification INT8). Session unique partagée (`ORT_SEQUENTIAL`, `intra_op_num_threads = cœurs physiques − 1`, `OMP_WAIT_POLICY=PASSIVE`, `OMP_PROC_BIND=FALSE`, `allow_spinning=0`), IOBinding zéro-copie sur l'entrée (`OrtValue`) et inférence sérialisée. Si `onnxruntime-openvino` est installé, l'**EP OpenVINO CPU FP32** est sélectionné automatiquement (batch 8, +1,5× mesuré) ; `STEP3_DISABLE_OPENVINO=1` force le CPU. Le Log-Mel est calculé par lots (vue glissante zéro-copie + `scipy.fft.rfft` multithreadé + projection Mel BLAS + CMN NumPy en place), avec une erreur maximale < 1e-6 par rapport à la chaîne SciPy historique.
  5. **Diarisation (AHC sur CPU)** :
     - Normalisation L2, matrice de Gram BLAS et vecteur de distances cosinus condensé (`N(N−1)/2`).
     - `fastcluster.linkage(method='average')` (repli automatique sur `scipy.cluster.hierarchy`) avec coupure stricte `t = np.nextafter(0.32, 0.0)` pour une parité exacte avec scikit-learn.
     - Réassignation des locuteurs mineurs (durée cumulée de parole < 7.0s) vectorisée par produit matriciel BLAS.
     - Fusion des segments contigus (< 1.0s) et renommage `SPEAKER_XX` par durée décroissante.
  6. **Timeline & Export JSON Standardisé** : Alignement des segments de voix détectés à 25 fps et écriture du JSON en streaming. Le contrat aval est inchangé : clé racine `speaker_stats` (`total_time_sec`/`percentage` par locuteur) et clé `num_distinct_speakers_audio` dans `audio_info`.

> **Architecture YAMNet Split (Edge TPU & Frontend CPU)** : Pour surmonter l'incompatibilité des
> opérateurs du frontend Log-Mel (`STFT`, `LOG`, `SQRT`) avec le compilateur Edge TPU, le pipeline supporte
> une architecture découplée activée via `STEP3_YAMNET_SPLIT=1` :
> - **Frontend CPU Log-Mel** (`workflow_scripts/step3/yamnet_frontend.py`) : calcul vectorisé en NumPy (STFT 512,
>   Hann 400, hop 160, 64 filtres Mel triangulaires pré-exportés dans `assets/yamnet_mel_matrix.npy`,
>   log-compression et quantification INT8) avec une latence de ~0,7 ms par patch (15360 échantillons).
> - **CNN MobileNetV1 compilé Edge TPU** (`assets/yamnet_split_edgetpu_compiled.tflite`) : sous-graphe convolutif
>   en entrée `(1, 96, 64)` INT8, compilé à 100% sur l'Edge TPU (31/31 opérateurs mappés sur l'ASIC, 0 opérateur CPU,
>   sous-graphe unique `edgetpu-custom-op`), exécutant chaque inférence en ~0,7 ms sur le Coral TPU.
> - **Mode strict `STEP3_REQUIRE_EDGETPU=1`** : avec le modèle split compilé, l'accélération matérielle Edge TPU
>   est totale et validée sans aucun repli CPU/XNNPACK.
> - **Rétrocompatibilité** : si `STEP3_YAMNET_SPLIT=0` ou en l'absence du modèle compilé, le script bascule
>   automatiquement sur le modèle monolithique legacy (`yamnet_audio_classificator_quantized_edgetpu.tflite`).
>
> ⚠️ **Ne pas utiliser `OMP_PROC_BIND=CLOSE` avec `OMP_PLACES=cores`** : dès que scikit-learn initialise
> libgomp, l'affinité du processus est restreinte à 2 cœurs et l'inférence ECAPA devient ~5× plus lente.
> `OMP_PROC_BIND=FALSE` (défaut du script) conserve l'affinité complète.
>
> **Réduction du coût ECAPA et Stratégie de Stride** : `STEP3_EMBEDDING_STRIDE` contrôle l'échantillonnage temporel
> des d-vectors ECAPA-TDNN (assignation au plus proche des fenêtres non calculées) :
> - `STEP3_EMBEDDING_STRIDE=1` (**défaut de production**) : calcul exhaustif, zéro régression acoustique.
> - `STEP3_EMBEDDING_STRIDE=2` : sous-échantillonnage 1 sur 2 (gain de ~43,5 % sur le temps global du pipeline).
> - `STEP3_EMBEDDING_STRIDE=auto` (ou `adaptive`, ou `STEP3_ADAPTIVE_STRIDE=1`) : règle adaptative basculant à
>   $K=2$ uniquement si `len(speech_indices) >= STEP3_ADAPTIVE_THRESHOLD` (défaut `500` fenêtres, ~4 min de parole).
>
> Mesures sur le dataset stratifié VoxConverse dev (24 extraits, 1 worker OpenVINO batch 8) :
>
> | Configuration | Extraits | Durée totale | DER strict | JER | Régressions locales (>0,5 pt) |
> |---|---|---|---|---|---|
> | K=1 OpenVINO (Référence) | 24 | 608,56 s | 28,0066 % | 40,9709 % | Référence absolue |
> | K=2 OpenVINO (Candidat) | 24 | **343,57 s** (-43,5 %) | **24,8479 %** (-3,16 pts) | 41,3107 % | **10 extraits dégradés** (+0,6 à +10,8 pts) |
>
> **Arbitrage industriel** : Bien que le DER agrégé s'améliore globalement de 3,16 points grâce aux monologues/dialogues
> longs (`aisvi` -38 pts, `bauzd` -21 pts), 10 clips sur 24 subissent une régression locale significative (confusion
> de locuteurs sur les répliques brèves <2s ou scènes denses comme `bdopb` +10,8 pts, `asxwr` +3,18 pts, `bydui` +2,98 pts).
> Le **défaut reste donc strictement $K=1$**, garantissant une qualité acoustique déterministe sans compromis,
> le mode adaptatif ou K=2 pouvant être activé au besoin pour les flux longs et peu denses.

## Analogie : Studio Mixage vs Transcription Cloud

Pense à l'analyse audio comme un **studio mixage** vs un **service de transcription cloud**. **Pyannote** est le studio où tu contrôles tout : l'équipement (GPU), les réglages (profil), et les données restent dans tes murs. **Lemonfox** est le service de transcription externe : rapide et pratique, mais tu envoies tes masters à l'extérieur. Le **profil gpu_fp32** est le mode haute fidélité qui garantit que chaque mot est capturé avec précision.

## Formats Supportés

### Vidéos en Entrée

```python
# Formats supportés (.mov alpha et noms de PRESERVED_MOV_NAMES exclus — règle SKIP_MOV_FILES)
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
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
logs/step3/
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

### Environnement Edge TPU (coral_env)

Pour exécuter l'analyse audio sous accélération TPU, configurez l'environnement dédié :

```bash
# Configuration des pilotes et règles udev (requis une seule fois)
sudo bash scripts/install_coral_udev.sh

# Désactiver l'ASPM PCIe dans GRUB (évite le blocage D3 de l'Apex : "RAM did not enable")
# Ajouter pcie_aspm=off à GRUB_CMDLINE_LINUX puis : sudo update-grub && sudo reboot
grep -o 'pcie_aspm=off' /proc/cmdline

# Création et activation de l'environnement virtuel (Python 3.11 validé)
python3.11 -m venv coral_env
source coral_env/bin/activate

# Dépendances épinglées (voir requirements-coral_env.txt)
pip install -r requirements-coral_env.txt
```

`requirements-coral_env.txt` fige : `numpy==1.26.4`, `numba==0.65.1`, `scipy==1.15.3`,
`scikit-learn==1.7.2`, `onnxruntime-openvino==1.24.1` (module `onnxruntime` + EP OpenVINO CPU),
`tflite-runtime==2.16.1`, `pycoral==2.0.1`, `opencv-python-headless==4.9.0.80`,
`fastcluster==1.2.6` et `psutil>=5.9`. Pour un CPU strict, remplacer par `onnxruntime==1.23.2`.

> ⚠️ `fastcluster` est épinglé en 1.2.6 : la version 1.3.0 impose `numpy>=2`, incompatible
> avec numba 0.65, tflite-runtime et pycoral. En l'absence de `fastcluster`, le script
> retombe automatiquement sur `scipy.cluster.hierarchy.linkage`.

`python scripts/validate_startup.py` vérifie `pcie_aspm=off`, la présence de `/dev/apex_0`
et l'appartenance au groupe `apex` lorsque `ENABLE_CORAL_TPU_ACCELERATION=true`.

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
PYANNOTE_BATCH_SIZE=1 python workflow_scripts/step3/run_audio_analysis.py

# 2. Forcer CPU
AUDIO_DISABLE_GPU=1 python workflow_scripts/step3/run_audio_analysis.py

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
# Les .mov alpha (logos) sont préservés et exclus de l'analyse.
# Les .mov sans alpha sont normalisés en .mp4 par l'étape 1 ; sans piste audio,
# ils restent sans transcription, comme tout .mp4 muet.
```

### Lemonfox API Erreurs

```bash
# Diagnostic
curl -H "Authorization: Bearer $LEMONFOX_API_KEY" https://api.lemonfox.ai/v1/status

# Solutions
# 1. Vérifier clé API et quota
# 2. Désactiver Lemonfox (fallback Pyannote)
export STEP3_METHOD=pyannote
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
export STEP3_DEEPINFRA_FALLBACK_TO_PYANNOTE=1
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
python ../workflow_scripts/step3/run_audio_analysis.py

# Vérifier résultat
head docs/test_speech_audio.json | jq '.frames_analysis[0].audio_info'
```

### Tests Automatisés STEP3 TPU

```bash
# Suite unitaire STEP3 + non-régression du contrat JSON STEP5
./scripts/run_step3_tests.sh
```

La suite couvre : équivalence Log-Mel par lots vs chaîne SciPy (`< 1e-6`), parité AHC
(`ARI = 1.0` vs scikit-learn), noyau VAD fusionné (médian + seuil strict + hangover),
garde-fou anti-fallback (`edgetpu-custom-op` + mode strict `STEP3_REQUIRE_EDGETPU=1`),
embeddings ECAPA par lots et schéma JSON.

### Benchmark Acoustique DER/JER (VoxConverse)

Le harnais mesure le DER et le JER (collar 0.0s et 0.25s, `skip_overlap=False`) en
reconstruisant l'hypothèse depuis `frames_analysis` (granularité 25 fps) :

```bash
# Téléchargement du corpus dev (WAV + RTTM, ~2 Go, une seule fois)
python3 scripts/fetch_voxconverse_dev.py

# Capture de la référence (à exécuter avant toute optimisation)
python3 scripts/bench_step3_tpu_der.py --limit 5 --out scratch/bench_step3_der/baseline

# Contrôle de non-régression après optimisation (dégradation ≤ 0.05 point)
python3 scripts/bench_step3_tpu_der.py --limit 5 \
    --baseline scratch/bench_step3_der/baseline/der_report.json

# Parité stricte (interdit aussi les améliorations, |ΔDER| ≤ 0.05)
python3 scripts/bench_step3_tpu_der.py --limit 5 --require-parity \
    --baseline scratch/bench_step3_der/baseline/der_report.json
```

Le rapport (`report.md` + `der_report.json`) contient les composantes *Missed Speech*,
*False Alarm* et *Speaker Confusion*, ainsi que les timings `STAGE_TIMING` par étage
(VAD, ECAPA, clustering, écriture JSON).

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
time python workflow_scripts/step3/run_audio_analysis.py

# Test CPU
AUDIO_DISABLE_GPU=1 time python workflow_scripts/step3/run_audio_analysis.py
```

## Intégration Pipeline

### Entrée pour STEP4

L'étape 3 prépare les données audio pour le tracking vidéo :
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

### Compatibilité STEP4

Le format JSON est parfaitement compatible avec STEP4 :
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
**Solution** : Les `.mov` alpha (logos) sont préservés et exclus de l'analyse (règle partagée `SKIP_MOV_FILES`, cf. `utils/media_filters.py`). Les `.mov` sans alpha sont convertis en `.mp4` par l'étape 1 ; une absence de piste audio est alors traitée comme pour tout `.mp4` muet.

### Piège #4 : OOM GPU sur vidéos longues
**Solution** : Configuration `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32` et fallback CPU automatique.

### Piège #5 : Lemonfox API coûteuse
**Solution** : Surveiller l'utilisation et basculer vers Pyannote local si nécessaire.

L'étape 3 transforme l'audio brut en intelligence structurée, identifiant précisément qui parle et quand. La timeline frame-précise permet une synchronisation parfaite avec le tracking vidéo, créant une base riche pour l'analyse multimodale.

---

## Golden Rule

**Toujours valider token HF + profil GPU avant run ; sinon tu obtiens des analyses audio incomplètes qui désynchronisent tout le pipeline.**
