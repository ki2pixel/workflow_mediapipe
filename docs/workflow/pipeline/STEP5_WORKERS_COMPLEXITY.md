# STEP5 Workers — Architecture Multiprocessing

> **Code-Doc Context** – Workers multiprocessing pour le tracking vidéo avec complexité radon F/E, gestion GPU/CPU et optimisations performance.

---

## Purpose & System Role

### Objectif
Les workers STEP5 orchestrent le traitement parallèle du tracking vidéo via multiprocessing, avec support MediaPipe CPU (défaut) et InsightFace GPU (optionnel), chunking adaptatif et export JSON dense frame-by-frame.

### Rôle dans l'Architecture
- **Position** : Scripts spécialisés STEP5 (`workflow_scripts/step5/`)
- **Prérequis** : Environnements `tracking_env_slim`/`insightface_env`
- **Sortie** : Fichiers `{video}_tracking.json` avec `tracked_objects` par frame
- **Dépendances** : MediaPipe, InsightFace, ONNX Runtime, OpenCV

### Valeur Ajoutée
- **Multiprocessing** : Parallélisation configurable via `TRACKING_CPU_WORKERS`
- **GPU Optionnel** : InsightFace ONNX Runtime avec accélération CUDA
- **Chunking** : Adaptation automatique taille chunks pour mémoire optimale
- **Streaming** : Export JSON progressif pour éviter OOM

---

## Architecture Workers

### Composants Principaux
```python
# Manager principal
class TrackingManager:
    def __init__(self):
        self.cpu_workers = int(os.getenv('TRACKING_CPU_WORKERS', '15'))
        self.enable_gpu = os.getenv('STEP5_ENABLE_GPU', '0') == '1'
        self.engine = os.getenv('STEP5_TRACKING_ENGINE', 'mediapipe')

# Worker individuel
def process_video_worker(video_path: str, config: Dict) -> Dict[str, Any]:
    """Traitement parallèle d'une vidéo"""

# Multiprocessing orchestrator
def process_video_multiprocessing(video_path: str, config: Dict) -> Dict[str, Any]:
    """Coordination workers et aggregation résultats"""
```

### Flux de Données
1. **Manager → Workers** : Distribution vidéos + configuration
2. **Workers → Engines** : Détection visages/objets frame par frame
3. **Engines → JSON** : Export dense `tracked_objects` par frame
4. **Aggregation** : Fusion résultats workers en JSON unique

### Environnements Spécialisés
```bash
# CPU-only (défaut)
tracking_env_slim/     # MediaPipe CPU, OpenCV, multiprocessing

# GPU-only (optionnel)  
insightface_env/       # InsightFace ONNX, CUDA, GPU memory
```

---

## Complexité (Radon Analysis)

### Points Critiques (Score F/E)

#### `process_video_worker.py` (Score F)
- **Complexité** : 399 lignes main (F), 114 lignes process_frame (E)
- **Défis** : Coordination worker, gestion mémoire, export streaming
- **Impact** : Performance tracking, utilisation GPU/CPU

#### `process_video_worker_multiprocessing.py` (Score F/E)
- **Complexité** : 180 lignes process_frame_chunk (F), 433 lignes process_video_multiprocessing (D)
- **Défis** : Chunking adaptatif, communication inter-processus
- **Impact** : Scalabilité, gestion mémoire multi-gigaoctets

#### `run_tracking_manager.py` (Score E)
- **Complexité** : 467 lignes main (E), 309 lignes launch_worker (D)
- **Défis** : Discovery CUDA, configuration engines, orchestration
- **Impact** : Point d'entrée principal, configuration GPU/CPU

---

## Configuration

### Variables d'Environnement
```bash
# Workers CPU
TRACKING_CPU_WORKERS=15          # Nombre workers parallèles
STEP5_TRACKING_ENGINE=mediapipe # mediapipe (défaut) ou insightface

# GPU (optionnel)
STEP5_ENABLE_GPU=1              # Activer GPU InsightFace
STEP5_GPU_ENGINES=insightface   # Moteurs GPU autorisés
CUDA_VISIBLE_DEVICES=0         # GPU spécifique

# Performance
STEP5_ENABLE_PROFILING=1        # Logs performance toutes 20 frames
STEP5_BLENDSHAPES_THROTTLE_N=5   # Throttling blendshapes
STEP5_EXPORT_VERBOSE_FIELDS=0   # Réduction taille JSON (95%)

# Engines spécifiques (simplifié v4.2)
STEP5_INSIGHTFACE_MAX_FACES=5
STEP5_INSIGHTFACE_MAX_WIDTH=1280
# Note: Variables OpenCV/YuNet/EOS supprimées - plus supportées
```

### WorkflowCommandsConfig Intégration
```python
# Configuration STEP5
config = WorkflowCommandsConfig()
step5_config = config.get_step_config('step5')
tracking_engine = step5_config.get('engine', 'mediapipe')
cpu_workers = step5_config.get('cpu_workers', 15)
```

---

## API & Méthodes Workers

### Manager Principal
```python
def main() -> None:
    """Point d'entrée STEP5 avec validation GPU/CPU"""
    # Discovery CUDA, configuration engines
    # Lancement workers multiprocessing
    # Aggregation résultats et logs

def launch_worker_process(video_path: str, worker_id: int, config: Dict) -> Dict[str, Any]:
    """Lancement worker individuel avec environnement dédié"""
    # Configuration engine (MediaPipe/InsightFace)
    # Validation prérequis (modèles, GPU)
    # Appel worker principal
```

### Worker Individuel
```python
def process_video_worker(video_path: str, config: Dict) -> Dict[str, Any]:
    """Worker principal avec gestion engine"""
    # Initialisation engine (lazy import MediaPipe)
    # Boucle frames avec détection
    # Export JSON streaming

def process_frame(frame: np.ndarray, engine: FaceEngine) -> List[Dict[str, Any]]:
    """Détection visages/objets frame unique"""
    # Appel engine.detect()
    # Normalisation coordonnées
    # Filtrage blendshapes
```

### Multiprocessing Orchestrator
```python
def process_video_multiprocessing(video_path: str, config: Dict) -> Dict[str, Any]:
    """Coordination workers et aggregation"""
    # Découpage vidéo en chunks
    # Distribution workers via Pool
    # Fusion résultats JSON

def process_frame_chunk(chunk_data: Tuple) -> List[Dict[str, Any]]:
    """Traitement chunk frames par worker"""
    # Initialisation engine locale
    # Boucle frames chunk
    # Retour résultats partiels
```

---

## Engines de Tracking

### MediaPipe (CPU - Défaut)
```python
# Lazy import pour éviter conflits TensorFlow
def _ensure_mediapipe_loaded(required: bool = True):
    if required and not hasattr(_ensure_mediapipe_loaded, '_mp'):
        import mediapipe as mp
        _ensure_mediapipe_loaded._mp = mp
        _ensure_mediapipe_loaded._face_mesh = mp.solutions.face_mesh
    return _ensure_mediapipe_loaded._mp

# Détection avec 478 landmarks + 52 blendshapes ARKit
with _ensure_mediapipe_loaded().FaceMesh(...) as face_mesh:
    results = face_mesh.process(frame_rgb)
```

### InsightFace (GPU - Optionnel)
```python
# ONNX Runtime avec providers CUDA
import onnxruntime as ort
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
session = ort.InferenceSession(model_path, providers=providers)

# Détection RetinaFace + blendshapes 52 ARKit
results = session.run(None, {'input': input_tensor})
```

> **Note de version (2026-02-03)** : Suite à la simplification de l'architecture STEP5, seuls **MediaPipe (CPU)** et **InsightFace (GPU)** sont désormais supportés. Les moteurs OpenCV/YuNet/EOS ont été supprimés pour réduire la complexité et améliorer la maintenabilité.

### Registry de Modèles (InsightFace uniquement)
```python
class ObjectDetectorRegistry:
    """Registry centralisé des modèles de détection (limité à InsightFace)"""
    
    @staticmethod
    def resolve_model_path(model_name: str) -> str:
        """Résolution chemin modèle InsightFace avec fallback"""
        
    @staticmethod
    def get_available_models() -> List[str]:
        """Liste modèles InsightFace disponibles localement"""
```

> **Simplification 2026-02-03** : Le registry ne gère plus que les modèles InsightFace. Les détecteurs OpenCV/YuNet/EOS ont été retirés de l'architecture.

---

## Performance & Optimisations

### Chunking Adaptatif
```python
def calculate_optimal_chunk_size(total_frames: int, num_workers: int) -> int:
    """Calcul taille chunk optimale selon mémoire"""
    # Base: 1000 frames par worker
    # Ajustement: mémoire disponible, taille vidéo
    # Minimum: 100 frames pour éviter overhead
    return max(100, total_frames // (num_workers * 2))
```

### Streaming JSON Export
```python
def export_tracking_json_streaming(results: List[Dict], output_path: str) -> None:
    """Export progressif pour éviter OOM"""
    with open(output_path, 'w') as f:
        f.write('{"frames": [')
        for i, frame_result in enumerate(results):
            if i > 0:
                f.write(',')
            json.dump(frame_result, f)
        f.write(']}')
```

### Profiling Intégré
```python
# Logs performance toutes les 20 frames
if frame_count % 20 == 0:
    elapsed = time.time() - start_time
    fps = frame_count / elapsed
    logger.info(f"[PROFILING] Frame {frame_count}, FPS: {fps:.2f}, "
                f"Engine: {engine_name}, GPU: {gpu_enabled}")
```

---

## Gestion GPU/CPU

### Configuration GPU (InsightFace)
```python
def _discover_system_cuda_lib_paths() -> List[str]:
    """Discovery automatique librairies CUDA"""
    cuda_paths = []
    cuda_home = os.getenv('CUDA_HOME', '/usr/local/cuda')
    
    # Chemins standards CUDA 11.x/12.x
    for lib_dir in ['lib64', 'lib']:
        lib_path = os.path.join(cuda_home, lib_dir)
        if os.path.exists(lib_path):
            cuda_paths.append(lib_path)
    
    return cuda_paths

def _setup_cuda_environment():
    """Injection LD_LIBRARY_PATH pour ONNX Runtime"""
    cuda_paths = _discover_system_cuda_lib_paths()
    if cuda_paths:
        ld_path = ':'.join(cuda_paths)
        current_ld = os.environ.get('LD_LIBRARY_PATH', '')
        os.environ['LD_LIBRARY_PATH'] = f"{ld_path}:{ld_path}"
```

### Fallback CPU Automatique
```python
def initialize_engine(engine_name: str) -> FaceEngine:
    """Initialisation avec fallback CPU si GPU échoue"""
    try:
        if engine_name == 'insightface' and gpu_enabled:
            return InsightFaceEngine(gpu=True)
    except Exception as e:
        logger.warning(f"[GPU] InsightFace GPU failed, falling back to CPU: {e}")
    
    # Fallback CPU
    return InsightFaceEngine(gpu=False)
```

### Memory Management GPU
```python
# Configuration ONNX Runtime pour éviter OOM
session_options = ort.SessionOptions()
session_options.enable_mem_pattern = False
session_options.enable_cpu_mem_arena = False

# Nettoyage mémoire GPU entre vidéos
if hasattr(torch, 'cuda'):
    torch.cuda.empty_cache()
```

---

## Format de Sortie JSON

### Structure Dense
```json
{
  "metadata": {
    "video_name": "video_stem",
    "engine": "mediapipe",
    "total_frames": 3012,
    "fps": 25.0,
    "gpu_enabled": false,
    "processing_time": 45.2
  },
  "frames": [
    {
      "frame_number": 1,
      "tracked_objects": []
    },
    {
      "frame_number": 150,
      "tracked_objects": [
        {
          "id": "face_0",
          "type": "face",
          "confidence": 0.92,
          "bbox": [100, 50, 200, 250],
          "centroid": [150, 150],
          "landmarks": [[110, 60], [120, 65], ...],
          "blendshapes": [0.1, 0.2, 0.0, ...]
        }
      ]
    }
  ]
}
```

### Optimisations Taille
```python
# STEP5_EXPORT_VERBOSE_FIELDS=false réduit taille de 74-95%
if not verbose_fields:
    # Supprimer landmarks/blendshapes pour non-MediaPipe
    if engine_name != 'mediapipe':
        for obj in frame_objects:
            obj.pop('landmarks', None)
            obj.pop('blendshapes', None)
```

---

## Cas d'Usage

### Pipeline STEP5 Complet
```bash
# Lancement avec configuration CPU (défaut)
STEP5_TRACKING_ENGINE=mediapipe \
TRACKING_CPU_WORKERS=15 \
python workflow_scripts/step5/run_tracking_manager.py video.mp4

# Lancement avec GPU InsightFace
STEP5_ENABLE_GPU=1 \
STEP5_TRACKING_ENGINE=insightface \
CUDA_VISIBLE_DEVICES=0 \
python workflow_scripts/step5/run_tracking_manager.py video.mp4
```

### Monitoring Performance
```python
# Logs typiques pendant traitement
[INFO] [STEP5] Starting video processing with 15 workers
[INFO] [STEP5] Engine: mediapipe, GPU: disabled
[PROFILING] Frame 1000, FPS: 28.5, Engine: mediapipe
[PROFILING] Frame 2000, FPS: 27.8, Engine: mediapipe  
[INFO] [STEP5] Completed 3012 frames in 108.3s (27.8 FPS)
```

---

## Sécurité & Robustesse

### Validation Entrées
```python
def validate_video_file(video_path: str) -> None:
    """Validation sécurité fichier vidéo"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Taille limite (configurable)
    max_size = int(os.getenv('MAX_VIDEO_SIZE', '2147483648'))  # 2GB
    if os.path.getsize(video_path) > max_size:
        raise ValueError(f"Video too large: {video_path}")
```

### Gestion Erreurs Workers
```python
def worker_error_handler(error: Exception, worker_id: int, video_path: str) -> None:
    """Gestion centralisée erreurs workers"""
    logger.error(f"[WORKER-{worker_id}] Error processing {video_path}: {error}")
    
    # Nettoyage ressources
    if hasattr(worker_error_handler, '_engine'):
        del worker_error_handler._engine
    
    # Notification monitoring
    workflow_state.update_step_status('step5', 'error', str(error))
```

### Isolation Environnements
```python
# Chaque worker utilise son environnement virtuel
venv_python = config.get_step_command('step5')['python_path']
subprocess.run([venv_python, worker_script, args], env=worker_env)
```

---

## Actions Recommandées

### Refactoring Priorité Haute
1. **Extraire `TrackingEngineFactory`** :
   ```python
   class TrackingEngineFactory:
       @staticmethod
       def create_engine(engine_name: str, gpu_enabled: bool) -> FaceEngine:
           # Isoler création engines avec fallback
   ```

2. **Créer `ChunkingStrategy`** :
   ```python
   class ChunkingStrategy:
       def calculate_chunks(self, total_frames: int, workers: int) -> List[Tuple]:
           # Optimiser distribution chunks
   ```

3. **Simplifier `process_video_worker`** :
   - Réduire complexité cyclomatique
   - Extraire helpers de streaming et validation

### Monitoring Continu
- **Radon** : Surveillance complexité méthodes F/E
- **Tests unitaires** : Couverture engines et multiprocessing
- **Performance** : Benchmark FPS par engine/CPU/GPU

---

## Documentation Croisée

- [Architecture Complète](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble pipeline
- [STEP5 Suivi Vidéo](../pipeline/STEP5_SUIVI_VIDEO.md) : Documentation étape utilisateur
- [InsightFace Engine](../workflow_scripts/step5/face_engines.py) : Implementation engine GPU
- [GPU Usage Guide](../legacy/STEP5_GPU_USAGE.md) : Configuration GPU détaillée
- [Object Detector Registry](../workflow_scripts/step5/object_detector_registry.py) : Modèles disponibles
