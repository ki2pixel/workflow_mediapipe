#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, argparse, subprocess, threading, time, logging
from pathlib import Path
from collections import OrderedDict, deque
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _load_env_file():
    """Load the project .env even if python-dotenv is unavailable."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    if load_dotenv:
        load_dotenv(env_path)
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        cleaned = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, cleaned)


_load_env_file()


def _read_env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default

    normalized = str(raw).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


step5_enable_object_detection = _read_env_bool("STEP5_ENABLE_OBJECT_DETECTION", default=True)

def _log_env_snapshot():
    relevant_keys = [
        "STEP5_ENABLE_GPU",
        "STEP5_GPU_ENGINES",
        "STEP5_TRACKING_ENGINE",
        "TRACKING_DISABLE_GPU",
        "TRACKING_CPU_WORKERS",
        "STEP5_GPU_FALLBACK_AUTO",
        "STEP5_ENABLE_OBJECT_DETECTION",
        "INSIGHTFACE_HOME",
    ]
    snapshot = {k: os.environ.get(k) for k in relevant_keys}
    logging.info(f"[EnvSnapshot] {snapshot}")


# --- CONFIGURATIONS GLOBALES ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

try:
    sys.path.insert(0, str(BASE_DIR))
    from config.settings import config as app_config
    TRACKING_ENV_PYTHON = app_config.get_venv_python("tracking_env")
    EOS_ENV_PYTHON = app_config.get_venv_python("eos_env")
    INSIGHTFACE_ENV_PYTHON = app_config.get_venv_python("insightface_env")
except (ImportError, AttributeError):
    TRACKING_ENV_PYTHON = BASE_DIR / "tracking_env" / "bin" / "python"
    EOS_ENV_PYTHON = BASE_DIR / "eos_env" / "bin" / "python"
    INSIGHTFACE_ENV_PYTHON = BASE_DIR / "insightface_env" / "bin" / "python"
    
WORKER_SCRIPT = Path(__file__).parent / "process_video_worker.py"

TRACKING_ENGINE = None

TF_GPU_ENV_PYTHON = os.environ.get("STEP5_TF_GPU_ENV_PYTHON", "").strip()
if TF_GPU_ENV_PYTHON:
    TF_GPU_ENV_PYTHON = Path(TF_GPU_ENV_PYTHON)

CUDA_LIB_SUBDIRS = [
    "cublas/lib",
    "cuda_runtime/lib",
    "cuda_nvrtc/lib",
    "cufft/lib",
    "curand/lib",
    "cusolver/lib",
    "cusparse/lib",
    "cudnn/lib",
    "nvjitlink/lib",
]

SYSTEM_CUDA_DEFAULTS = [
    "/usr/local/cuda-12.4",
    "/usr/local/cuda-12",
    "/usr/local/cuda-11.8",
    "/usr/local/cuda",
]

def _build_venv_cuda_paths(python_exe: Path) -> list[str]:
    """Return CUDA library directories bundled in a venv (for ONNX Runtime CUDA provider)."""
    try:
        venv_dir = Path(python_exe).expanduser().parent.parent
    except Exception:
        return []

    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = venv_dir / "lib" / python_version / "site-packages"
    nvidia_dir = site_packages / "nvidia"
    if not nvidia_dir.exists():
        return []

    paths = []
    for sub in CUDA_LIB_SUBDIRS:
        candidate = nvidia_dir / sub
        if candidate.exists():
            paths.append(str(candidate))
    return paths


def _discover_system_cuda_lib_paths() -> list[str]:
    """
    Detect CUDA libraries available on the host for engines that bundle their own interpreter (InsightFace).
    Priority order:
      1. Explicit STEP5_CUDA_LIB_PATH (colon-separated).
      2. STEP5_CUDA_HOME / CUDA_HOME lib64 folders.
      3. Common /usr/local/cuda-* lib64 folders.
      4. /usr/lib/x86_64-linux-gnu in case distro ships the libs there.
    """
    explicit_paths = os.environ.get("STEP5_CUDA_LIB_PATH", "").strip()
    if explicit_paths:
        resolved = [
            str(Path(p.strip()).expanduser())
            for p in explicit_paths.split(":")
            if p.strip() and Path(p.strip()).expanduser().exists()
        ]
        if resolved:
            return resolved

    candidates: list[Path] = []
    for env_var in ("STEP5_CUDA_HOME", "CUDA_HOME"):
        value = os.environ.get(env_var, "").strip()
        if value:
            candidates.append(Path(value).expanduser())
    for default_path in SYSTEM_CUDA_DEFAULTS:
        candidates.append(Path(default_path))

    discovered: list[str] = []
    for base_dir in candidates:
        if not base_dir.exists():
            continue
        for sub in ("lib64", "targets/x86_64-linux/lib"):
            candidate = base_dir / sub
            if candidate.exists():
                discovered.append(str(candidate))
    debian_cuda = Path("/usr/lib/x86_64-linux-gnu")
    if debian_cuda.exists():
        expected = ["libcufft.so.11", "libcublas.so.12"]
        if all((debian_cuda / lib_name).exists() for lib_name in expected):
            discovered.append(str(debian_cuda))
    return discovered

# --- CONFIGURATION DU LOGGER ---
LOG_DIR = BASE_DIR / "logs" / "step5"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"manager_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MANAGER] - %(message)s',
                    handlers=[logging.FileHandler(log_file, 'w', 'utf-8'), logging.StreamHandler(sys.stdout)])

WORKER_CONFIG_TEMPLATE = {
    "mp_landmarker_num_faces": 5, "mp_landmarker_min_face_detection_confidence": 0.5,
    "mp_landmarker_min_face_presence_confidence": 0.3, "mp_landmarker_min_tracking_confidence": 0.5,
    "mp_landmarker_output_blendshapes": True, "enable_object_detection": step5_enable_object_detection,
    "object_score_threshold": 0.5, "object_max_results": 5, "mp_max_distance_tracking": 70,
    "mp_frames_unseen_deregister": 7, "speaking_detection_jaw_open_threshold": 0.08,
    "object_detector_model": os.environ.get('STEP5_OBJECT_DETECTOR_MODEL', 'efficientdet_lite2'),
    "object_detector_model_path": os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH'),
}

CPU_OPTIMIZED_CONFIG = {
    "mp_landmarker_min_face_detection_confidence": 0.3,
    "mp_landmarker_min_face_presence_confidence": 0.2,
    "mp_landmarker_min_tracking_confidence": 0.3,
    "object_score_threshold": 0.4,
    "mp_max_distance_tracking": 80,
}


def log_reader_thread(process, video_name, progress_map, lock):
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            logging.info(f"[{video_name}] {line}")
            if line.startswith("[Progression]|"):
                try:
                    _, percent, _, _ = line.split('|')
                    with lock:
                        progress_map[video_name] = f"{int(percent)}%"
                    try:
                        print(f"{video_name}: {int(percent)}%", flush=True)
                    except Exception:
                        pass
                except:
                    pass
        process.stdout.close()


def monitor_progress(processes, progress_map, lock, total_jobs_to_run):
    while len(processes) < total_jobs_to_run or any(p.poll() is None for p in processes.values()):
        time.sleep(1)
        with lock:
            progress_copy = progress_map.copy()
        progress_parts = [f"{name}: {status}" for name, status in sorted(progress_copy.items())]
        if progress_parts: print(f"[Progression-MultiLine]{' || '.join(progress_parts)}", flush=True)
    time.sleep(1)


def launch_worker_process(video_path, use_gpu, internal_workers=1, tracking_engine=None):
    video_name = Path(video_path).name
    worker_type_log = "GPU" if use_gpu else f"CPU (x{internal_workers})"
    logging.info(f"Préparation du job {worker_type_log} pour: {video_name}")

    config = WORKER_CONFIG_TEMPLATE.copy()

    engine_norm = (str(tracking_engine).strip().lower() if tracking_engine is not None else "")
    if engine_norm in {"mediapipe", "mediapipe_landmarker"}:
        engine_norm = ""

    gpu_capable_engines = {"openseeface", "opencv_yunet_pyfeat", "insightface"}
    
    if engine_norm and engine_norm not in gpu_capable_engines:
        if use_gpu:
            logging.info(f"Engine {engine_norm} not GPU-capable, forcing CPU mode")
        use_gpu = False

    if not use_gpu:
        config.update(CPU_OPTIMIZED_CONFIG)
        config["mp_num_workers_internal"] = internal_workers

        if internal_workers > 1:
            worker_script = "process_video_worker_multiprocessing.py"
            logging.info(f"Using multiprocessing worker with {internal_workers} processes")
        else:
            worker_script = "process_video_worker.py"
            logging.info("Using single-threaded CPU worker")

        logging.info(f"Applied CPU optimizations: lower confidence thresholds for better detection rate")
    else:
        worker_script = "process_video_worker.py"
        logging.info("Using GPU worker with sequential processing")
        if step5_enable_object_detection and internal_workers > 1:
            config["mp_num_workers_internal"] = internal_workers

    models_dir_path = Path(__file__).resolve().parent / "models"
    worker_script_path = Path(__file__).resolve().parent / worker_script

    worker_python_override_eos = os.environ.get("STEP5_EOS_ENV_PYTHON")
    worker_python_override_insightface = os.environ.get("STEP5_INSIGHTFACE_ENV_PYTHON")
    worker_python = TRACKING_ENV_PYTHON
    
    if engine_norm == "eos":
        worker_python = Path(worker_python_override_eos) if worker_python_override_eos else EOS_ENV_PYTHON
        if not worker_python.exists():
            raise RuntimeError(
                f"EOS engine selected but python interpreter not found: {worker_python}. "
                "Create eos_env or set STEP5_EOS_ENV_PYTHON to the eos_env python path."
            )
    elif engine_norm == "insightface":
        if not use_gpu:
            raise RuntimeError(
                "InsightFace engine is GPU-only. Enable STEP5_ENABLE_GPU=1 and include 'insightface' in STEP5_GPU_ENGINES."
            )

        worker_python = (
            Path(worker_python_override_insightface)
            if worker_python_override_insightface
            else INSIGHTFACE_ENV_PYTHON
        )
        if not worker_python.exists():
            raise RuntimeError(
                f"InsightFace engine selected but python interpreter not found: {worker_python}. "
                "Create insightface_env or set STEP5_INSIGHTFACE_ENV_PYTHON to the insightface_env python path."
            )
    elif use_gpu and not engine_norm:
        if TF_GPU_ENV_PYTHON and isinstance(TF_GPU_ENV_PYTHON, Path):
            if TF_GPU_ENV_PYTHON.exists():
                worker_python = TF_GPU_ENV_PYTHON
                logging.info(f"Using TensorFlow GPU interpreter for MediaPipe: {worker_python}")
            else:
                logging.warning(
                    "STEP5_TF_GPU_ENV_PYTHON is set but the interpreter was not found "
                    f"({TF_GPU_ENV_PYTHON}). Falling back to tracking_env."
                )

    command_args = [str(worker_python), str(worker_script_path), video_path, "--models_dir", str(models_dir_path)]
    if use_gpu: command_args.append("--use_gpu")

    if engine_norm:
        command_args.extend(["--tracking_engine", engine_norm])

    for key, value in config.items():
        if key == "mp_num_workers_internal" and use_gpu and not (step5_enable_object_detection and internal_workers > 1):
            continue
        if isinstance(value, bool):
            if value:
                command_args.append(f"--{key}")
            continue
        if value is not None:
            command_args.extend([f"--{key}", str(value)])

    if (not use_gpu) and internal_workers > 1:
        command_args.extend(["--chunk_size", "0"])  # 0 = adaptive in worker

    try:
        env = os.environ.copy()
        cuda_paths: list[str] = []
        cuda_paths_worker = _build_venv_cuda_paths(Path(worker_python))
        cuda_paths_tracking = _build_venv_cuda_paths(Path(TRACKING_ENV_PYTHON))
        if cuda_paths_worker:
            cuda_paths.extend(cuda_paths_worker)
        elif cuda_paths_tracking:
            cuda_paths.extend(cuda_paths_tracking)

        if engine_norm == "insightface":
            system_cuda_paths = _discover_system_cuda_lib_paths()
            for path in system_cuda_paths:
                if path not in cuda_paths:
                    cuda_paths.append(path)

        if cuda_paths:
            extra_ld_path = ":".join(cuda_paths)
            existing_ld_path = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = (
                f"{extra_ld_path}:{existing_ld_path}" if existing_ld_path else extra_ld_path
            )
            logging.info("[MANAGER] Injected CUDA library paths for ONNX Runtime")
        env.setdefault('OMP_NUM_THREADS', '1')
        env.setdefault('OPENBLAS_NUM_THREADS', '1')
        env.setdefault('MKL_NUM_THREADS', '1')
        env.setdefault('NUMEXPR_NUM_THREADS', '1')
        env.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
        env.setdefault('GLOG_minloglevel', '2')
        env.setdefault('ABSL_LOGGING_MIN_LOG_LEVEL', '2')

        p = subprocess.Popen(
            command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
        )
        return p
    except Exception as e:
        logging.error(f"ERREUR LANCEMENT de {video_name}: {e}")
        return None


def run_job_and_monitor(job_info, processes, progress_map, lock):
    video_path = job_info['path']
    video_name = Path(video_path).name
    internal_workers = job_info.get('cpu_internal_workers', 15) if (not job_info['use_gpu'] or step5_enable_object_detection) else 1
    tracking_engine = job_info.get('tracking_engine')
    p = launch_worker_process(video_path, job_info['use_gpu'], internal_workers, tracking_engine=tracking_engine)

    if p:
        with lock:
            processes[video_name] = p
            progress_map[video_name] = "Démarrage..."

        reader_thread = threading.Thread(target=log_reader_thread, args=(p, video_name, progress_map, lock),
                                         daemon=True)
        reader_thread.start()
        p.wait()
        reader_thread.join(timeout=1)

        try:
            if p.returncode == 0:
                print(f"[Gestionnaire] Succès pour {video_name}", flush=True)
            else:
                print(f"[Gestionnaire] Échec pour {video_name}", flush=True)
        except Exception:
            pass



def resource_worker_loop(resource_name, use_gpu, videos_deque, deque_lock, processes, progress_map, lock):
    """Continuously pull videos from the shared deque and process them on the given resource.

    Args:
        resource_name (str): Human-readable resource label (e.g., 'GPU' or 'CPU').
        use_gpu (bool): Whether to use GPU for the worker process.
        videos_deque (collections.deque): Shared queue of video paths to process.
        deque_lock (threading.Lock): Lock protecting access to the shared deque.
        processes (OrderedDict): Shared mapping of video_name -> subprocess.Popen.
        progress_map (OrderedDict): Shared mapping of video_name -> progress string.
        lock (threading.Lock): Lock protecting shared maps.
    """
    while True:
        with deque_lock:
            if videos_deque:
                video_path = videos_deque.popleft()
            else:
                break
        video_name = Path(video_path).name
        logging.info(f"[Scheduler] Assigning {video_name} to {resource_name}")
        run_job_and_monitor(
            {
                'path': video_path,
                'use_gpu': use_gpu,
                'cpu_internal_workers': CPU_INTERNAL_WORKERS,
                'tracking_engine': TRACKING_ENGINE,
            },
            processes,
            progress_map,
            lock,
        )


def main():
    parser = argparse.ArgumentParser(description="Gestionnaire de tracking parallèle intelligent.")
    parser.add_argument("--videos_json_path", required=True, help="Chemin JSON des vidéos.")
    parser.add_argument("--disable_gpu", action="store_true", help="Désactiver le worker GPU et utiliser uniquement le CPU")
    parser.add_argument("--cpu_internal_workers", type=int, default=15, help="Nombre de workers internes CPU par vidéo")
    parser.add_argument(
        "--tracking_engine",
        default=None,
        help="Moteur de tracking: mediapipe_landmarker (défaut), opencv_haar, opencv_yunet, opencv_yunet_pyfeat, openseeface, eos, insightface",
    )
    args = parser.parse_args()
    try:
        import os as _os
        if _os.environ.get('TRACKING_DISABLE_GPU', '').strip() in {'1','true','TRUE','yes','YES'}:
            args.disable_gpu = True
        if 'TRACKING_CPU_WORKERS' in _os.environ:
            try:
                args.cpu_internal_workers = int(_os.environ['TRACKING_CPU_WORKERS'])
            except ValueError:
                pass

        if args.tracking_engine is None and 'STEP5_TRACKING_ENGINE' in _os.environ:
            raw_engine = str(_os.environ.get('STEP5_TRACKING_ENGINE', '')).strip()
            if raw_engine:
                args.tracking_engine = raw_engine
    except Exception:
        pass

    _engine_norm = (str(args.tracking_engine).strip().lower() if args.tracking_engine is not None else "")
    
    gpu_enabled_global = _os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
    gpu_engines_str = _os.environ.get('STEP5_GPU_ENGINES', '').strip().lower()
    gpu_engines = [e.strip() for e in gpu_engines_str.split(',') if e.strip()]
    _log_env_snapshot()
    
    engine_normalized = _engine_norm if _engine_norm else "mediapipe_landmarker"
    if engine_normalized in {"mediapipe", "mediapipe_landmarker"}:
        engine_normalized = "mediapipe_landmarker"
    
    engine_supports_gpu = False
    if gpu_enabled_global and not args.disable_gpu:
        if engine_normalized == "insightface":
            if engine_normalized in gpu_engines or 'all' in gpu_engines:
                engine_supports_gpu = True
                logging.info(f"GPU mode requested for engine: {engine_normalized}")
                
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                    from config.settings import Config
                    gpu_status = Config.check_gpu_availability()
                    
                    if not gpu_status['available']:
                        logging.warning(f"GPU requested but unavailable: {gpu_status['reason']}")
                        fallback_auto = _os.environ.get('STEP5_GPU_FALLBACK_AUTO', '1').strip() == '1'
                        if fallback_auto:
                            logging.info("Auto-fallback to CPU enabled")
                            args.disable_gpu = True
                            engine_supports_gpu = False
                        else:
                            logging.error("GPU fallback disabled, aborting")
                            raise RuntimeError(f"GPU unavailable: {gpu_status['reason']}")
                    else:
                        logging.info(f"GPU validation passed: VRAM {gpu_status['vram_free_gb']:.1f} Go free, CUDA {gpu_status.get('cuda_version', 'N/A')}")
                except ImportError as e:
                    logging.error(f"Failed to import config.settings: {e}")
                    args.disable_gpu = True
                    engine_supports_gpu = False
                except Exception as e:
                    logging.error(f"GPU validation failed: {e}")
                    args.disable_gpu = True
                    engine_supports_gpu = False
            else:
                logging.warning(f"InsightFace not listed in STEP5_GPU_ENGINES ({gpu_engines_str}), forcing CPU-only mode")
                args.disable_gpu = True
        else:
            logging.info(f"GPU mode is reserved for InsightFace only. Engine '{engine_normalized}' will run in CPU-only mode.")
            args.disable_gpu = True
    
    if _engine_norm in {"opencv_haar", "opencv_yunet", "eos"}:
        if not args.disable_gpu:
            args.disable_gpu = True
            logging.info(f"Engine {_engine_norm} does not support GPU, forcing CPU-only mode")
    
    if not args.disable_gpu and engine_supports_gpu:
        logging.info(f"✓ GPU mode ENABLED for {_engine_norm or 'mediapipe_landmarker'}")
    else:
        logging.info(f"CPU-only mode (GPU disabled or not supported for this engine)")

    if _engine_norm == "insightface" and (args.disable_gpu or not engine_supports_gpu):
        logging.error(
            "InsightFace engine is GPU-only, but GPU mode is disabled or not authorized. "
            "Set STEP5_ENABLE_GPU=1 and include 'insightface' in STEP5_GPU_ENGINES."
        )
        sys.exit(1)

    with open(args.videos_json_path, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        videos_list = data
    elif isinstance(data, dict) and 'videos' in data:
        logging.info("Legacy videos JSON schema detected; using 'videos' key.")
        videos_list = data['videos']
    else:
        logging.error(f"Invalid JSON format in {args.videos_json_path}. Expected a list or object with 'videos' key.")
        sys.exit(1)
    
    videos_to_process = deque(videos_list)
    if not videos_to_process: logging.info("Aucune vidéo à traiter."); return

    logging.info(f"--- DÉMARRAGE DU GESTIONNAIRE DE TRACKING (Planificateur Dynamique GPU/CPU) ---")
    total_jobs = len(videos_to_process)
    logging.info(f"Vidéos à traiter: {total_jobs}")
    global CPU_INTERNAL_WORKERS
    CPU_INTERNAL_WORKERS = max(1, int(args.cpu_internal_workers))

    global TRACKING_ENGINE
    TRACKING_ENGINE = args.tracking_engine
    if args.disable_gpu:
        logging.info("Mode FULL CPU activé: le worker GPU est désactivé")

    processes, video_progress_map, progress_lock = OrderedDict(), OrderedDict(), threading.Lock()

    monitor_thread = threading.Thread(target=monitor_progress,
                                      args=(processes, video_progress_map, progress_lock, total_jobs), daemon=True)
    monitor_thread.start()

    deque_lock = threading.Lock()

    threads = []
    if not args.disable_gpu:
        gpu_thread = threading.Thread(
            target=resource_worker_loop,
            args=("GPU", True, videos_to_process, deque_lock, processes, video_progress_map, progress_lock),
            daemon=True,
        )
        threads.append(gpu_thread)
    if _engine_norm != "insightface":
        cpu_thread = threading.Thread(
            target=resource_worker_loop,
            args=("CPU", False, videos_to_process, deque_lock, processes, video_progress_map, progress_lock),
            daemon=True,
        )
        threads.append(cpu_thread)
    else:
        logging.info("InsightFace is GPU-only: CPU worker thread disabled")

    if args.disable_gpu:
        workers_label = "CPU seul"
    else:
        workers_label = "GPU seul" if _engine_norm == "insightface" else "GPU et CPU"
    logging.info("Lancement des workers: " + workers_label)
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    monitor_thread.join(timeout=2)

    success_count = sum(1 for p in processes.values() if p.returncode == 0)
    logging.info(f"--- FIN DU GESTIONNAIRE ---")
    logging.info(f"Traitement terminé. {success_count}/{total_jobs} jobs réussis.")
    if success_count < total_jobs: sys.exit(1)


if __name__ == "__main__":
    main()