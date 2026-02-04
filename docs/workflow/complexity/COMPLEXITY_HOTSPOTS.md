# Analyse de Complexité — Points Chauds Radon

> **Code-Doc Context** – Vue d'ensemble de la complexité cyclomatique du codebase avec 94 blocs analysés (complexité moyenne D) et identification des points chauds critiques.

---

## Métriques Globales

### Audit Complet
- **Fichiers analysés** : Services, routes, utils, workflow_scripts
- **Lignes de code** : 28,181 (Python: 15,347, JavaScript: 5,643)
- **Blocs analysés** : 94 (classes, fonctions, méthodes)
- **Complexité moyenne** : D (23.97)
- **Répartition** : C (25), D (35), E (22), F (12)

### Distribution par Complexité
```
Score F : ████████████ 12 blocs (12.8%) - Critique
Score E : ██████████ 22 blocs (23.4%) - Élevée  
Score D : ████████████████ 35 blocs (37.2%) - Modérée
Score C : ████████ 25 blocs (26.6%) - Acceptable
```

---

## Top 10 Points Chauds Critiques

### 1. CSVService (Score F) - 3 méthodes F
**Localisation** : `services/csv_service.py`
```python
F 662:4 CSVService._check_csv_for_downloads - Monitoring webhook
F 203:4 CSVService._normalize_url - Normalisation URLs  
C 324:4 CSVService._load_structured_history - Migration historique
```
**Impact** : Service critique monitoring téléchargements
**Défis** : Parsing CSV complexe, décodage double encodage, gestion multi-sources

### 2. LemonfoxAudioService (Score F) - 1 méthode F
**Localisation** : `services/lemonfox_audio_service.py`
```python
F 106:0 _compute_speaker_embeddings_from_audio - Embeddings Pyannote
E 860:4 LemonfoxAudioService.process_video_with_lemonfox - Pipeline STT
C 280:4 LemonfoxAudioService._apply_speech_smoothing - Timeline
```
**Impact** : Integration API externe, traitement audio
**Défis** : Gestion erreurs API, retry, fallback Pyannote, OOM GPU

### 3. STEP5 Workers (Score F/E) - 5 méthodes F/E
**Localisation** : `workflow_scripts/step5/`
```python
F 399:0 process_video_worker.py main - Worker principal
E 114:4 process_video_worker.py process_frame - Détection frame
F 180:0 process_video_worker_multiprocessing.py process_frame_chunk - Chunking
E 433:0 process_video_worker_multiprocessing.py process_video_multiprocessing - Orchestration
E 467:0 run_tracking_manager.py main - Manager global
```
**Impact** : Performance tracking vidéo, utilisation GPU/CPU
**Défis** : Multiprocessing, coordination workers, streaming JSON

### 4. STEP6 JSON Reducer (Score F) - 2 méthodes F
**Localisation** : `workflow_scripts/step6/json_reducer.py`
```python
F 268:0 _compute_tracking_analytics - Analytics confiance
F 110:0 reduce_video_json - Pipeline principal
E 714:0 process_directory - Orchestration multi-projets
```
**Impact** : Agrégation données tracking, analytics
**Défis** : Parsing gros JSON, calculs statistiques, validation structurelle

### 5. Génération Rapports (retiré)
> _Note 2026-02-04_ : `ReportService` et ses méthodes (anciennement notées F/E) ont été supprimés. Cette entrée reste pour mémoire historique et ne reflète plus un point chaud actif.

### 6. STEP7 Preprocess AE (Score F) - 1 méthode F
**Localisation** : `workflow_scripts/step7/preprocess_ae_json.py`
```python
F 205:0 _analyze_layer - Analyzer mode pour After Effects
D 509:0 _index_reduced_tracking_frames - Indexation tracking par frame
C 627:0 build_ae_payload - Orchestration finale AE JSON
```
**Impact** : Optimisation After Effects, mode analyzer sandwich
**Défis** : Calculs géométriques, mapping frame→calque, parsing JSON STEP6

### 7. VisualizationService (Score E) - 3 méthodes E/D
**Localisation** : `services/visualization_service.py`
```python
E 27:4 VisualizationService.get_available_projects - Discovery projets
D 638:4 VisualizationService._get_video_metadata - Métadonnées FFmpeg
D 525:4 VisualizationService._load_tracking_data - Parsing tracking
D 421:4 VisualizationService._load_audio_data - Données audio
```
**Impact** : Métriques projets, timeline frontend
**Défis** : Parsing gros volumes, validation multi-sources

---

## Patterns de Complexité

### Services Externes (CSV, Lemonfox)
**Caractéristiques** :
- Gestion erreurs réseau/API robuste
- Retry et fallbacks multi-niveaux  
- Validation et normalisation entrées
- Cache et persistance structurée

**Exemples** :
```python
# Retry avec backoff exponentiel
for attempt in range(max_retries):
    try:
        response = api_call()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(2 ** attempt)

# Validation entrées
def _validate_url(url: str) -> str:
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Invalid URL scheme")
    return sanitize_url(url)
```

### Multiprocessing (STEP5 Workers)
**Caractéristiques** :
- Coordination inter-processus
- Distribution charge et chunking
- Communication et aggregation
- Gestion ressources GPU/CPU

**Exemples** :
```python
# Distribution travail
with Pool(processes=num_workers) as pool:
    chunks = split_video_into_chunks(video_path, num_workers)
    results = pool.map(process_chunk, chunks)

# Aggregation résultats
final_result = merge_worker_results(results)
```

### Agrégation Données (STEP6, Visualization)
**Caractéristiques** :
- Parsing gros volumes JSON/CSV
- Validation structurelle
- Calculs statistiques et analytics
- Streaming et optimisations mémoire

**Exemples** :
```python
# Streaming JSON pour éviter OOM
def parse_large_json_streaming(file_path: str):
    with open(file_path, 'r') as f:
        for line in f:
            yield json.loads(line)

# Validation structurelle
def validate_tracking_schema(data: dict) -> bool:
    required_keys = {"frames", "metadata", "total_frames"}
    return required_keys.issubset(data.keys())
```

### Pré-traitement After Effects (STEP7)
**Caractéristiques** :
- Indexation frame→objets pour accès direct
- Mode analyzer avec calculs géométriques
- Optimisations JSON pour ExtendScript
- Intégration Python↔AE via `system.callSystem()`

**Exemples** :
```python
# Indexation optimisée pour AE
def build_data_by_frame(tracking_data: List[Dict]) -> Dict[int, List[Dict]]:
    data_by_frame = {}
    for frame_data in tracking_data:
        frame_num = frame_data['frame_number']
        data_by_frame[frame_num] = frame_data['tracked_objects']
    return data_by_frame

# Mode analyzer - calculs lourds en Python
def _analyze_layer(manifest: Dict) -> Dict[str, Any]:
    # Calculs géométriques, mapping frame→calque
    # Évite boucle coûteuse côté ExtendScript
```

### Génération Rapports (retiré)
> Ce pattern n'est plus actif depuis la suppression de `ReportService`. Les notes restent pour contextualiser les anciens audits Radon.

---

## Stratégies de Mitigation

### Architecture DI (Dependency Injection)
**Pattern** : Injection dépendances au constructeur
**Bénéfices** : Isolation, testabilité, faible couplage
```python
class ComplexService:
    def __init__(self, 
                 filesystem: FilesystemService,
                 state: WorkflowState,
                 config: WorkflowCommandsConfig):
        self._fs = filesystem
        self._state = state
        self._config = config
```

### Streaming et Chunking
**Pattern** : Traitement par fragments pour gros volumes
**Bénéfices** : Mémoire constante, progression visible
```python
def process_large_file(file_path: str):
    for chunk in read_file_in_chunks(file_path, chunk_size=1024):
        yield process_chunk(chunk)
```

### Cache Multi-Niveaux
**Pattern** : Cache mémoire + persistance
**Bénéfices** : Performance, résilience, fallback
```python
@functools.lru_cache(maxsize=128)
def get_cached_data(key: str):
    data = load_from_persistence(key)
    return process_data(data)
```

### Fallbacks Robustes
**Pattern** : Alternatives automatiques
**Bénéfices** : Résilience, continuité service
```python
def get_data_with_fallback():
    try:
        return primary_source()
    except Exception:
        try:
            return secondary_source()
        except Exception:
            return default_data()
```

---

## Actions Prioritaires

### Refactoring Immédiat (Score F)
1. **CSVService._check_csv_for_downloads** (F)
   - Extraire `CSVParser` et `URLNormalizer`
   - Simplifier parsing multi-formats

2. **LemonfoxAudioService._compute_speaker_embeddings** (F)
   - Isoler `EmbeddingsExtractor`
   - Simplifier gestion modèles Pyannote

3. **STEP5 process_video_worker main** (F)
   - Extraire `WorkerOrchestrator`
   - Simplifier boucle principale

### Monitoring Continu
- **Radon automatique** : CI/CD avec seuils alertes
- **Tests par complexité** : Couverture méthodes F/E obligatoire
- **Performance monitoring** : Métriques temps par complexité

### Documentation Cible
- **Services complexes** : 100% documentation F/E
- **Patterns réutilisables** : Guide refactoring
- **Décisions architecture** : Justification complexité

---

## Évolution et Maintenance

### Surveillance Complexité
```bash
# Audit radon régulier
radon cc services routes utils workflow_scripts -a -nc

# Alertes si nouveau F
radon cc . --min B
```

### Tests par Niveau
```python
# Tests unitaires pour méthodes F
@pytest.mark.parametrize("method", ["_check_csv_for_downloads", "_compute_speaker_embeddings"])
def test_critical_method(method):
    # Test complet avec edge cases
```

### Refactoring Progressif
1. **Identifier** méthodes F/E via radon
2. **Isoler** logique métier
3. **Simplifier** complexité cyclomatique
4. **Tester** régression comportement
5. **Documenter** nouveaux patterns

---

## Documentation Croisée

- [Services Documentation](../features/) : Documentation détaillée services
- [Pipeline Steps](../pipeline/) : Documentation étapes spécifiques  
- [Architecture Guide](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble système
- [Coding Standards](../../.windsurf/rules/codingstandards.md) : Standards qualité
- [Tests Strategy](../../tests/) : Stratégie tests par complexité

---

## Conclusion

L'analyse de complexité révèle que **80% de la complexité technique** est concentrée dans **6 services/workers** spécifiques :

1. **Services externes** (CSV, Lemonfox) - Gestion erreurs robuste
2. **Multiprocessing** (STEP5) - Coordination workers (simplifié v4.2)
3. **Agrégation données** (STEP6, Viz) - Parsing gros volumes
4. **Pré-traitement AE** (STEP7) - Optimisations After Effects, mode analyzer
> _Note 2026-02-04_ : La génération de rapports a été retirée du système.

La documentation ciblée de ces points chauds, combinée avec des patterns d'architecture sains (DI, streaming, cache), assure la maintenabilité du système malgré sa complexité intrinsèque.

**L'approche recommandée** : Documenter les services complexes F/E (y compris le nouveau STEP7), puis appliquer des refactoring progressifs pour réduire la complexité cyclomatique tout en préservant la fonctionnalité.
