# Lemonfox Audio Service — Integration STT/LLM

> **Code-Doc Context** – Service critique pour l'analyse audio STEP4 avec complexité radon F sur les méthodes principales, integration API externe et support embeddings.

---

## Purpose & System Role

### Objectif
`LemonfoxAudioService` fournit une interface avec l'API Lemonfox Speech-to-Text pour convertir les transcriptions en données frame-by-frame compatibles STEP4, avec support embeddings locuteurs et fallback Pyannote intégré.

### Rôle dans l'Architecture
- **Position** : Service spécialisé STEP4 (`services/lemonfox_audio_service.py`)
- **Prérequis** : Token API Lemonfox, environnement `audio_env`
- **Sortie** : Fichiers `{video}_audio.json` avec timeline frame-by-frame
- **Dépendances** : FFmpeg (extraction), requests (API), import dynamique

### Valeur Ajoutée
- **API externe** : Accès LLM STT via Lemonfox
- **Embeddings** : Support vecteurs locuteurs (optionnel)
- **Fallback** : Basculement automatique Pyannote si API échoue
- **Smoothing** : Timeline `is_speech_present` stabilisée

---

## Architecture

### Composants Principaux
```python
class LemonfoxAudioService:
    def __init__(self, filesystem_service: FilesystemService):
        self._fs = filesystem_service
        self._api_key = config.LEMONFOX_API_KEY
        self._base_url = config.LEMONFOX_API_URL
```

### Flux de Données
1. **Vidéo → WAV** : Extraction audio via FFmpeg (tmpfs optimisé)
2. **WAV → API** : Upload vers Lemonfox avec retry et timeout
3. **API → JSON** : Conversion transcription → timeline frame-by-frame
4. **JSON → Fichier** : Écriture `{video}_audio.json` compatible STEP4

### Import Dynamique (Isolation Flask)
```python
# Import via importlib pour éviter exécution services/__init__.py
import importlib.util
spec = importlib.util.spec_from_file_location("lemonfox_audio_service", path)
lemonfox_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lemonfox_module)
```

---

## Complexité (Radon Analysis)

### Points Critiques (Score F/E)

#### `_compute_speaker_embeddings_from_audio()` (Score F)
- **Complexité** : 106 lignes, extraction embeddings Pyannote
- **Défis** : Modèle pyannote/embedding, segmentation audio, validation
- **Impact** : Embeddings locuteurs pour After Effects (optionnel)

#### `process_video_with_lemonfox()` (Score E)
- **Complexité** : 860 lignes, orchestration complète
- **Défis** : Gestion erreurs API, retry, fallback Pyannote
- **Impact** : Pipeline principal d'analyse audio

#### `_apply_speech_smoothing()` (Score C)
- **Complexité** : 280 lignes, stabilisation timeline
- **Défis** : Filtrage temporel, détection parole, gaps
- **Impact** : Timeline `is_speech_present` cohérente

---

## Configuration

### Variables d'Environnement
```bash
# API Lemonfox
LEMONFOX_API_KEY=votre_cle_api
LEMONFOX_API_URL=https://api.lemonfox.ai/v1

# Embeddings (optionnel)
AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=1
AUDIO_SPEAKER_EMBEDDINGS_MODEL_ID=pyannote/embedding
AUDIO_SPEAKER_EMBEDDINGS_MIN_SEGMENT_SEC=0.5

# Performance
AUDIO_PROFILE=gpu_fp32  # GPU FP32, AMP désactivé
LEMONFOX_TIMEOUT=30
LEMONFOX_MAX_RETRIES=3

# Fallback
AUDIO_PARTIAL_SUCCESS_OK=1
```

### WorkflowCommandsConfig Intégration
```python
# Configuration STEP4
config = WorkflowCommandsConfig()
step4_config = config.get_step_config('step4')
audio_profile = step4_config.get('profile', 'gpu_fp32')
```

---

## API & Méthodes

### Méthodes Principales
```python
# Pipeline principal (Score E)
def process_video_with_lemonfox(self, project_path: str, video_path: str) -> Dict[str, Any]:
    """Orchestration complète avec retry et fallback"""

# Embeddings locuteurs (Score F)
def _compute_speaker_embeddings_from_audio(self, wav_path: str, segments: List[Dict]) -> Dict[str, Any]:
    """Extraction embeddings Pyannote avec validation"""

# Smoothing timeline (Score C)
def _apply_speech_smoothing(self, is_speech: List[bool], fps: float = 25.0) -> List[bool]:
    """Stabilisation détection parole temporelle"""

# Validation projet
def _validate_project_and_video(self, project_path: str, video_path: str) -> None:
    """Validation chemins et prérequis"""
```

### Patterns d'Utilisation
```python
# Initialisation
lemonfox_service = LemonfoxAudioService(filesystem_service)

# Analyse complète
result = lemonfox_service.process_video_with_lemonfox(project_path, video_path)

# Extraction embeddings (si activé)
if _should_include_speaker_embeddings():
    embeddings = lemonfox_service._compute_speaker_embeddings_from_audio(wav_path, segments)
```

---

## Performance & Monitoring

### Indicateurs Clés
- **Débit API** : Temps réponse Lemonfox par minute audio
- **Taux réussite** : % transcriptions réussies vs fallbacks
- **Taille embeddings** : Volume vecteurs par locuteur
- **Mémoire GPU** : Utilisation CUDA pendant traitement

### Patterns de Logging
```python
# Progression API
logger.info(f"[LEMONFOX] Processing {video_name}, duration: {duration:.2f}s")

# Erreurs API avec retry
logger.warning(f"[LEMONFOX] API timeout {attempt}/{max_retries}, retrying...")

# Embeddings
logger.debug(f"[LEMONFOX] Extracted embeddings for {len(embeddings)} speakers")

# Fallback Pyannote
logger.info(f"[LEMONFOX] Falling back to Pyannote for {video_name}")
```

---

## Gestion des Erreurs & Fallbacks

### Stratégie Multi-Niveaux
1. **API Lemonfox** : Retry 3x avec backoff exponentiel
2. **Fallback Pyannote** : Basculement automatique si API échoue
3. **Succès Partiel** : `AUDIO_PARTIAL_SUCCESS_OK=1` autorise résultats partiels
4. **Validation** : Vérification structure JSON avant écriture

### Gestion OOM GPU
```python
# Configuration PyTorch pour éviter OOM
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"

# Nettoyage mémoire entre fichiers
torch.cuda.empty_cache()
```

### Validation Entrées
```python
# Sécurité fichiers
def _validate_audio_file(self, wav_path: str) -> None:
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Audio file not found: {wav_path}")
    
    # Validation taille et format
    if os.path.getsize(wav_path) > 500 * 1024 * 1024:  # 500MB limit
        raise ValueError(f"Audio file too large: {wav_path}")
```

---

## Format de Sortie STEP4

### Structure JSON
```json
{
  "metadata": {
    "video_name": "video_stem",
    "duration": 120.5,
    "fps": 25.0,
    "total_frames": 3012,
    "source": "lemonfox",
    "model_version": "v1.2"
  },
  "frames": [
    {
      "frame_number": 1,
      "is_speech_present": false,
      "active_speaker": null,
      "confidence": 0.0
    },
    {
      "frame_number": 150,
      "is_speech_present": true,
      "active_speaker": "speaker_0",
      "confidence": 0.87
    }
  ],
  "speaker_embeddings": {
    "speaker_0": [0.1, 0.2, 0.3, ...],
    "speaker_1": [0.4, 0.5, 0.6, ...]
  }
}
```

### Compatibilité STEP5/6
- **Frames 1..N** : Alignement parfait avec tracking vidéo
- **Speaker labels** : Mappage vers `enhanced_speaking_detection.py`
- **Embeddings** : Préservés par `json_reducer.py` STEP6
- **Metadata** : Enrichissement automatique dans STEP6

---

## Cas d'Usage

### Pipeline STEP4 Complet
```python
# Dans workflow_scripts/step4/run_audio_analysis.py
lemonfox_service = LemonfoxAudioService(filesystem_service)

for video_path in video_files:
    try:
        result = lemonfox_service.process_video_with_lemonfox(project_path, video_path)
        logger.info(f"[STEP4] Success: {video_path}")
    except Exception as e:
        logger.error(f"[STEP4] Failed: {video_path}, error: {e}")
        continue
```

### Tests Unitaires
```python
def test_lemonfox_api_timeout():
    """Test retry mechanism sur timeout API"""
    with patch('requests.post', side_effect=TimeoutError):
        with pytest.raises(LemonfoxAPIError):
            lemonfox_service.process_video_with_lemonfox(project_path, video_path)

def test_speaker_embeddings_extraction():
    """Test extraction embeddings Pyannote"""
    embeddings = lemonfox_service._compute_speaker_embeddings_from_audio(wav_path, segments)
    assert len(embeddings) > 0
    assert all(isinstance(v, list) for v in embeddings.values())
```

---

## Sécurité

### Gestion des Secrets
- **API Key** : Jamais en dur, toujours via `config.settings`
- **Validation URLs** : Anti-path-traversal sur fichiers audio
- **Sanitization** : Noms fichiers et chemins validés

### Protection Contre les Attaques
```python
# Validation entrées utilisateur
def _sanitize_video_name(self, video_name: str) -> str:
    """Nettoyage nom fichier pour sécurité"""
    import re
    # Alphanumérique + underscore + point uniquement
    return re.sub(r'[^a-zA-Z0-9_.]', '', video_name)

# Taille limite fichiers
MAX_AUDIO_SIZE = 500 * 1024 * 1024  # 500MB
if os.path.getsize(wav_path) > MAX_AUDIO_SIZE:
    raise ValueError("Audio file exceeds size limit")
```

---

## Actions Recommandées

### Refactoring Priorité Haute
1. **Extraire `LemonfoxAPIClient`** :
   ```python
   class LemonfoxAPIClient:
       def transcribe_audio(self, wav_path: str) -> Dict[str, Any]:
           # Isoler logique API avec retry
   ```

2. **Créer `EmbeddingsExtractor`** :
   ```python
   class EmbeddingsExtractor:
       def extract_embeddings(self, wav_path: str, segments: List[Dict]) -> Dict[str, Any]:
           # Simplifier extraction embeddings
   ```

3. **Simplifier `process_video_with_lemonfox`** :
   - Réduire complexité cyclomatique
   - Extraire helpers de validation et conversion

### Monitoring Continu
- **Radon** : Surveillance complexité méthodes F/E
- **Tests unitaires** : Couverture API retry et embeddings
- **Performance** : Benchmark temps traitement par minute audio

---

## Documentation Croisée

- [Architecture Complète](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble pipeline
- [STEP4 Analyse Audio](../pipeline/STEP4_ANALYSE_AUDIO.md) : Documentation étape complète
- [Enhanced Speaking Detection](../utils/enhanced_speaking_detection.py) : Consommation données STEP4
- [STEP6 JSON Reducer](../features/STEP6_REDUCTION_JSON.md) : Préservation embeddings
- [Lemonfox API Documentation](https://docs.lemonfox.ai) : Référence API externe
