# Lemonfox Audio Service - Analyse Audio Temps Réel

**TL;DR** : Service d'analyse audio qui appelle l'API Lemonfox pour la transcription et la diarisation, avec fallback Pyannote et support embeddings locuteurs optionnels.

## Le Problème : Analyse Audio Complexité Variable

Tu dois analyser l'audio de tes vidéos pour identifier qui parle quand, mais les modèles locaux (Pyannote) sont lents et les APIs externes sont complexes à intégrer. Tu as besoin d'une solution qui combine la vitesse des APIs avec la fiabilité du fallback local, tout en gérant les erreurs réseau et les quotas.

## Notre Solution : Service Hybride avec Fallback Intelligent

Nous utilisons `LemonfoxAudioService` comme interface unifiée qui orchestre l'API Lemonfox (rapide) avec Pyannote (fallback). Le service gère automatiquement les timeouts, les erreurs réseau, et produit des JSON structurés compatibles avec STEP5 et STEP6.

### ❌ Appel API direct (anti-pattern)
```python
# Approche fragile - pas de fallback, pas de gestion d'erreurs
import requests

def transcribe_audio(audio_file):
    response = requests.post("https://api.lemonfox.ai/v1/transcribe", files={
        "file": open(audio_file, "rb")
    })
    return response.json()  # Crash si réseau down
```

### ✅ Service avec fallback (pattern recommandé)
```python
# Approche robuste - retry, fallback, gestion d'erreurs
class LemonfoxAudioService:
    def __init__(self, api_key: str, fallback_enabled: bool = True):
        self._api_key = api_key
        self._fallback_enabled = fallback_enabled
    
    def process_video_with_lemonfox(self, video_path: str) -> dict:
        try:
            return self._call_lemonfox_api(video_path)
        except (NetworkError, TimeoutError, QuotaExceeded) as e:
            if self._fallback_enabled:
                logger.warning(f"Lemonfox failed, using Pyannote: {e}")
                return self._fallback_to_pyannote(video_path)
            raise
```

### Flux d'Analyse Audio Intelligent

1. **Extraction audio** : FFmpeg extrait WAV depuis la vidéo
2. **Appel Lemonfox** : Transcription + diarisation via API
3. **Validation réponse** : Vérification format et cohérence
4. **Fallback Pyannote** : Si Lemonfox échoue, bascule automatiquement
5. **Embeddings locuteurs** : Optionnel, vecteurs par identifiant
6. **Timeline frame-by-frame** : Synchronisation avec 25 FPS vidéo
7. **Export JSON** : Format standardisé pour pipeline

## Configuration Essentielle

### Variables d'Environnement

```bash
# Clé API Lemonfox
LEMONFOX_API_KEY=your-lemonfox-api-key

# Fallback Pyannote
LEMONFOX_FALLBACK_ENABLED=1          # Activer fallback local
LEMONFOX_FALLBACK_MODEL=pyannote/speaker-diarization-3.1

# Embeddings locuteurs (optionnel)
AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=0     # 1 pour activer
AUDIO_SPEAKER_EMBEDDINGS_MODEL_ID=pyannote/embedding
AUDIO_SPEAKER_EMBEDDINGS_MIN_SEGMENT_SEC=0.5

# Performance et timeouts
LEMONFOX_REQUEST_TIMEOUT=30            # Timeout API (secondes)
LEMONFOX_MAX_RETRIES=3                # Nombre de tentatives
LEMONFOX_RETRY_DELAY=5                 # Délai entre tentatives
```

### Configuration API

```python
# Configuration Lemonfox
lemonfox_config = {
    "api_url": "https://api.lemonfox.ai/v1",
    "model": "whisper-1",
    "language": "auto",           # Détection automatique
    "diarization": True,         # Séparation locuteurs
    "timestamps": "word",        # Précision mot par mot
    "response_format": "json"
}
```

## Architecture Technique

### Service Principal

```python
class LemonfoxAudioService:
    def __init__(self, api_key: str, filesystem: FilesystemService):
        self._api_key = api_key
        self._fs = filesystem
        self._session = requests.Session()
        self._session.timeout = 30
    
    def process_video_with_lemonfox(self, video_path: str) -> dict:
        """Point d'entrée principal pour l'analyse audio."""
        
    def _call_lemonfox_api(self, video_path: str) -> dict:
        """Appel à l'API Lemonfox avec retry."""
        
    def _fallback_to_pyannote(self, video_path: str) -> dict:
        """Fallback local avec Pyannote."""
        
    def _compute_speaker_embeddings_from_audio(self, audio_path: str) -> dict:
        """Calcul des embeddings locuteurs optionnels."""
        
    def _build_frame_timeline(self, transcription: dict, fps: float) -> dict:
        """Conversion transcription vers timeline frame-by-frame."""
```

### Gestion des Erreurs

```python
# Types d'erreurs gérées
class LemonfoxError(Exception):
    """Base class for Lemonfox errors."""
    
class NetworkError(LemonfoxError):
    """Network connectivity issues."""
    
class QuotaExceeded(LemonfoxError):
    """API quota exceeded."""
    
class InvalidResponse(LemonfoxError):
    """Malformed API response."""

# Retry avec backoff exponentiel
def _call_with_retry(self, func, *args, **kwargs):
    for attempt in range(self._max_retries):
        try:
            return func(*args, **kwargs)
        except NetworkError as e:
            if attempt == self._max_retries - 1:
                raise
            delay = (2 ** attempt) * self._retry_delay
            logger.warning(f"Retry {attempt + 1}/{self._max_retries} in {delay}s")
            time.sleep(delay)
```

## Trade-offs par Approche d'Analyse

| Approche | Vitesse | Fiabilité | Coût | Complexité | Quand l'utiliser |
|----------|----------|------------|-------|------------|-----------------|
| **Lemonfox Only** | Excellente | Moyenne | Élevé | Faible | Production stable, bon budget |
| **Pyannote Only** | Faible | Excellente | Gratuit | Moyenne | Développement, budget limité |
| **Hybrid Auto** | Bonne | Excellente | Variable | Élevée | Production critique |
| **Embeddings On** | Variable | Excellente | Élevé | Très élevée | Analyse avancée |

## Trade-offs par Configuration Embeddings

| Embeddings | Usage CPU | Précision | Taille JSON | Cas d'usage |
|------------|------------|------------|--------------|--------------|
| **Désactivés** | Minimal | Standard | Optimale | Production standard |
| **Pyannote** | Élevé | Bonne | +15% | Recherche locuteurs |
| **Lemonfox** | Moyen | Excellente | +20% | Identification précise |

## Analogie : Traducteur Interprète vs Dictionnaire

Pense à l'analyse audio comme un **traducteur interprète** vs un **dictionnaire**. **Lemonfox** est l'interprète : rapide, comprend les nuances, identifie qui parle quand (diarization), mais nécessite une connexion et a un coût. **Pyannote** est le dictionnaire : fiable, toujours disponible, gratuit, mais plus lent et nécessite plus d'effort. Les **embeddings** sont comme des cartes d'identité : chaque locuteur reçoit une signature unique qui permet de le retrouver même s'il change de nom.

## Formats Supportés

### Audio en Entrée

```python
# Formats supportés (via FFmpeg extraction)
AUDIO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
AUDIO_FORMAT = 'wav'           # Extraction WAV 16kHz
AUDIO_SAMPLE_RATE = 16000     # Standard pour les APIs
AUDIO_CHANNELS = 1            # Mono pour diarization
```

### Structure de Données

```json
{
  "video_filename": "video1.mp4",
  "total_frames": 2500,
  "fps": 25.0,
  "audio_analysis": {
    "speakers": [
      {
        "id": "SPEAKER_00",
        "name": "Camille",
        "segments": [
          {
            "start": 0.0,
            "end": 5.2,
            "text": "Bonjour, je vais vous présenter..."
          }
        ],
        "embeddings": [0.12, -0.34, 0.56, ...]  // Optionnel
      }
    ],
    "transcription": [
      {
        "frame": 1,
        "speaker": "SPEAKER_00",
        "text": "Bonjour",
        "confidence": 0.95,
        "start_time": 0.0,
        "end_time": 0.8
      }
    ]
  }
}
```

## Performance et Optimisations

### Optimisations API

```python
# Timeout configurables
LEMONFOX_REQUEST_TIMEOUT=30      # Éviter les hangs
LEMONFOX_CONNECT_TIMEOUT=10      # Timeout connexion

# Retry intelligent
LEMONFOX_MAX_RETRIES=3          # Tentatives maximum
LEMONFOX_RETRY_DELAY=5           # Délai exponentiel
LEMONFOX_BACKOFF_FACTOR=2         # Facteur backoff

# Chunking pour gros fichiers
LEMONFOX_CHUNK_SIZE_MB=25        # Découper fichiers >25MB
```

### Optimisations Fallback

```python
# Modèles Pyannote optimisés
LEMONFOX_FALLBACK_MODEL=pyannote/speaker-diarization-3.1
PYANNOTE_DEVICE=cpu             # Forcer CPU si GPU indisponible
PYANNOTE_BATCH_SIZE=32           # Batch processing
```

### Optimisations Embeddings

```python
# Segmentation minimale
AUDIO_SPEAKER_EMBEDDINGS_MIN_SEGMENT_SEC=0.5  # Segment minimum
AUDIO_SPEAKER_EMBEDDINGS_MAX_SPEAKERS=10       # Limiter locuteurs
AUDIO_SPEAKER_EMBEDDINGS_DIMENSION=192        # Dimension vecteurs
```

## Monitoring et Logs

### Structure des Logs

```
logs/step4/
├── lemonfox_api_20240120_143022.log
├── pyannote_fallback_20240120_143022.log
└── embeddings_computation_20240120_143022.log
```

### Exemple de Logs

```
2024-01-20 14:30:22 - INFO - Starting Lemonfox analysis for video1.mp4
2024-01-20 14:30:23 - INFO - Extracting audio with FFmpeg: video1.mp4 -> video1.wav
2024-01-20 14:30:25 - INFO - Calling Lemonfox API (file size: 15.2MB)
2024-01-20 14:30:45 - INFO - Lemonfox response received: 2 speakers, 156 segments
2024-01-20 14:30:46 - INFO - Building frame timeline: 2500 frames, 25.0 FPS
2024-01-20 14:30:50 - INFO - Computing speaker embeddings: 2 speakers, 12 segments
2024-01-20 14:30:55 - INFO - Successfully wrote video1_audio.json
```

### Patterns de Progression

```python
# Progression API
logger.info(f"Calling Lemonfox API (file size: {file_size_mb:.1f}MB)")

# Progression fallback
logger.warning(f"Lemonfox failed, using Pyannote fallback: {error}")

# Progression embeddings
logger.info(f"Computing embeddings: {len(speakers)} speakers, {len(segments)} segments")

# Progression timeline
logger.info(f"Building frame timeline: {total_frames} frames, {fps:.1f} FPS")
```

## Résolution de Problèmes

### API Timeout

```bash
# Diagnostic
grep "timeout" logs/step4/lemonfox_*.log
curl -I https://api.lemonfox.ai/v1  # Test connectivité

# Solutions
# 1. Augmenter timeout
LEMONFOX_REQUEST_TIMEOUT=60 python workflow_scripts/step4/run_audio_analysis.py

# 2. Réduire taille fichier
LEMONFOX_CHUNK_SIZE_MB=10 python workflow_scripts/step4/run_audio_analysis.py
```

### Quota Dépassé

```bash
# Diagnostic
grep "quota" logs/step4/lemonfox_*.log
curl -H "Authorization: Bearer $LEMONFOX_API_KEY" \
     https://api.lemonfox.ai/v1/usage  # Vérifier quota

# Solutions
# 1. Attendre reset quota (généralement minuit UTC)
# 2. Utiliser fallback Pyannote
LEMONFOX_FALLBACK_ENABLED=1 python workflow_scripts/step4/run_audio_analysis.py
```

### Fallback Pyannote Lent

```bash
# Diagnostic
htop  # Vérifier charge CPU
nvidia-smi  # Vérifier si GPU disponible

# Solutions
# 1. Activer GPU Pyannote
PYANNOTE_DEVICE=cuda python workflow_scripts/step4/run_audio_analysis.py

# 2. Réduire batch size
PYANNOTE_BATCH_SIZE=16 python workflow_scripts/step4/run_audio_analysis.py
```

### Embeddings Échouent

```bash
# Diagnostic
grep "embedding" logs/step4/embeddings_*.log
python -c "import pyannote.audio; print('Embeddings available')" || exit 1

# Solutions
# 1. Désactiver embeddings
AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=0 python workflow_scripts/step4/run_audio_analysis.py

# 2. Augmenter segment minimum
AUDIO_SPEAKER_EMBEDDINGS_MIN_SEGMENT_SEC=1.0 python workflow_scripts/step4/run_audio_analysis.py
```

## Tests et Validation

### Test Lemonfox API

```python
def test_lemonfox_api_integration():
    """Test l'intégration Lemonfox complète."""
    service = LemonfoxAudioService(api_key="test_key")
    
    # Test transcription
    result = service._call_lemonfox_api("test_video.mp4")
    
    # Vérifier structure
    assert "speakers" in result
    assert "transcription" in result
    assert len(result["speakers"]) > 0
    assert len(result["transcription"]) > 0
    
    # Vérifier cohérence
    speakers = set(item["speaker"] for item in result["transcription"])
    assert speakers <= set(speaker["id"] for speaker in result["speakers"])
```

### Test Fallback Pyannote

```python
def test_pyannote_fallback():
    """Test le fallback automatique vers Pyannote."""
    service = LemonfoxAudioService(api_key="invalid_key")
    
    # Forcer l'erreur réseau
    with mock.patch('requests.Session.post') as mock_post:
        mock_post.side_effect = NetworkError("Connection failed")
        
        # Doit utiliser Pyannote
        result = service.process_video_with_lemonfox("test_video.mp4")
        
        # Vérifier fallback utilisé
        assert "speakers" in result
        assert len(result["speakers"]) > 0
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
            required_keys = ['video_filename', 'total_frames', 'fps', 'audio_analysis']
            if not all(key in data for key in required_keys):
                print(f"❌ {json_file}: Structure JSON invalide")
                return False
            
            # Vérifier analyse audio
            audio = data['audio_analysis']
            if 'speakers' not in audio or 'transcription' not in audio:
                print(f"❌ {json_file}: Analyse audio incomplète")
                return False
            
            # Compter éléments
            speakers = audio['speakers']
            transcription = audio['transcription']
            
            print(f"✅ {json_file}: {len(speakers)} speakers, {len(transcription)} segments")
            
        except Exception as e:
            print(f"❌ Erreur lecture {json_file}: {e}")
            return False
    
    print("✅ Validation réussie: tous les JSON audio sont valides")
    return True
```

## Intégration Pipeline

### Entrée pour STEP5

L'étape 4 prépare les données audio pour le tracking facial :
- **Timeline frame-by-frame** : Synchronisation avec 25 FPS vidéo
- **Identification locuteurs** : `SPEAKER_00`, `SPEAKER_01`, etc.
- **Transcription mot par mot** : Pour analyse sémantique
- **Embeddings optionnels** : Vecteurs par locuteur pour clustering

### WorkflowState Integration

```python
# Intégration avec l'état centralisé
ws = get_workflow_state()
ws.update_step_status("STEP4", "running")
ws.set_step_field("STEP4", "current_video", "video1.mp4")
ws.update_step_progress("STEP4", current=1, total=3)
```

### Compatibilité STEP5

Le format JSON audio est optimisé pour STEP5 :
```python
# Utilisation dans STEP5
audio_data = load_audio_analysis("video1_audio.json")
speakers = audio_data['audio_analysis']['speakers']
transcription = audio_data['audio_analysis']['transcription']

# Enrichissement tracking avec données audio
for frame_data in tracking_results:
    frame_num = frame_data['frame']
    audio_segment = find_audio_segment(transcription, frame_num)
    frame_data['audio_speaker'] = audio_segment.get('speaker')
    frame_data['audio_text'] = audio_segment.get('text')
```

## Pièges Courants et Solutions

### Piège #1 : Clé API invalide
**Solution** : Vérifier la clé avec `curl -H "Authorization: Bearer $LEMONFOX_API_KEY" https://api.lemonfox.ai/v1/models`

### Piège #2 : Fichier audio trop gros
**Solution** : Activer le chunking avec `LEMONFOX_CHUNK_SIZE_MB=10`

### Piège #3 : Fallback désactivé
**Solution** : Toujours garder `LEMONFOX_FALLBACK_ENABLED=1` en production

### Piège #4 : Embeddings sur CPU lent
**Solution** : Désactiver embeddings ou utiliser GPU avec `PYANNOTE_DEVICE=cuda`

### Piège #5 : Incohérence temps
**Solution** : Vérifier que `fps` dans le JSON correspond à la vidéo réelle

### Piège #6 : Speakers non identifiés
**Solution** : Ajuster seuil de diarization dans les paramètres Pyannote

### Piège #7 : Timeout réseau
**Solution** : Augmenter `LEMONFOX_REQUEST_TIMEOUT` et activer retries

L'étape 4 transforme l'audio brut en données structurées avec une fiabilité maximale grâce au fallback intelligent. Le service garantit que même si l'API externe échoue, l'analyse continue localement, assurant la robustesse du pipeline complet.

---

## Golden Rule

**Configure toujours le fallback ; sinon une panne réseau ou un quota dépassé arrêtera tout ton pipeline d'analyse audio.**
