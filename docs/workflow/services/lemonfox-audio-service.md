# Lemonfox Audio Service Documentation

## TL;DR
Le Lemonfox Audio Service orchestre l'analyse audio via l'API Lemonfox pour STEP4, générant des JSON compatibles STEP5/STEP6 avec transcription, diarization locuteurs, et embeddings optionnels Pyannote.

## Contexte Métier
STEP4 transforme les vidéos en données audio structurées : transcription texte, timestamps mots/phrases, identification locuteurs, et embeddings vectoriels pour analyses avancées (clustering, reconnaissance).

## Architecture Service

### Flux de données
1. **Validation** : Chemins projet/vidéo sécurisés
2. **Extraction** : Durée vidéo via ffprobe
3. **Préparation** : Upload artifact (transcodage si nécessaire)
4. **API Call** : Transcription Lemonfox avec paramètres
5. **Traitement** : Construction timeline frames + embeddings
6. **Sortie** : JSON atomique `{video_stem}_audio.json`

### Fonctions Clés

#### `_compute_speaker_embeddings_from_audio()` (Complexité F)
**Rôle** : Calcule les embeddings vectoriels des locuteurs via Pyannote pour analyse sémantique avancée.

**Algorithme détaillé** :
1. **Filtrage segments** : Validation durée (>0.5s), mapping labels (`SPEAKER_00`)
2. **Chargement modèle** : Pyannote embedding avec token HF, GPU si disponible
3. **Extraction audio** : ffmpeg vers WAV temporaire (16kHz mono)
4. **Inférence vectorielle** : Par segment locuteur, moyenne temporelle, normalisation L2
5. **Agrégation** : Moyenne segments par locuteur (max 10 segments), arrondi précision 4 décimales

**Optimisations** :
- Tri segments par durée décroissante
- Device CUDA/CPU automatique
- Nettoyage temporaire `/dev/shm`
- Gestion erreurs partielles (skip segments problématiques)

#### `process_video_with_lemonfox()` (Complexité E)
**Rôle** : Pipeline complet analyse audio d'une vidéo.

**Étapes séquentielles** :
1. **Validation chemins** : Anti-traversal, existence fichiers
2. **Métadonnées vidéo** : ffprobe pour durée, calcul frames (25fps)
3. **Préparation upload** : Gestion taille (transcodage si > limite), cleanup sécurisé
4. **Configuration API** : Defaults config + paramètres utilisateur
5. **Appel Lemonfox** : HTTP avec retry, gestion erreurs
6. **Construction timeline** : Mapping transcription vers frames avec smoothing
7. **Embeddings optionnels** : Intégration Pyannote si activé
8. **Écriture JSON** : Atomique avec backup, format STEP4 standard

**Gestion ressources** :
- Cleanup upload artifacts systématique
- Fallbacks silencieux pour embeddings
- Atomic writes pour éviter corruption

## Gestion Erreurs

### Échecs API Lemonfox
- **Comportement** : Retour erreur détaillée, pas de retry automatique
- **Logging** : Warning avec contexte (langue, speakers)

### Problèmes embeddings
- **Comportement** : Skip silencieux, log warning, continuation pipeline
- **Fallback** : Timeline sans embeddings (compatible STEP5/STEP6)

### Erreurs écriture JSON
- **Comportement** : Cleanup temp files, retour échec
- **Atomicité** : os.replace() pour éviter corruption partielle

## Optimisations Performance

### GPU embeddings
- Détection CUDA automatique
- Fallback CPU si indisponible
- Modèle `pyannote/embedding` optimisé

### Smoothing parole
- Gap filling configurable (secondes)
- Minimum duration on/off
- Runs consolidation efficace

### Traitement streaming
- Timeline frame-by-frame (25fps standard)
- JSON écriture buffered
- Mémoire contrôlée (pas de load complet)

## Trade-offs

### ❌ Embeddings lourds vs ❌ Fonctionnalité avancée
- **Choix** : Calcul embeddings optionnel (flag env)
- **Coût** : Overhead computationnel, dépendances PyTorch
- **Bénéfice** : Analyses clustering/reconnaissance possibles

### ❌ API externe vs ❌ Cohérence données
- **Choix** : Service Lemonfox spécialisé
- **Coût** : Dépendance réseau, coûts API
- **Bénéfice** : Qualité transcription supérieure, diarization native

### ❌ Complexité pipeline vs ❌ Robustesse
- **Choix** : Logique centralisée dans service
- **Coût** : Debugging difficile, tests unitaires complexes
- **Bénéfice** : Cohérence traitement, gestion edge cases complète

## Golden Rule
**Les sorties JSON doivent rester compatibles STEP5/STEP6** : tout changement format nécessite migration des scripts consommateurs et tests de régression complets.

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
    with mock.patch('requests.Session.post') as NetworkError("Connection failed"):
        
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
```</content>
<parameter name="path">/home/kidpixel/workflow_mediapipe/docs/workflow/services/lemonfox_audio_service.md