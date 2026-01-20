"""
Centralized configuration management for workflow_mediapipe.

This module provides environment-based configuration management
following the project's development guidelines.
"""

import os
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


def _parse_bool(raw: Optional[str], default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_optional_int(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except Exception:
        return None


def _parse_optional_positive_int(raw: Optional[str]) -> Optional[int]:
    value = _parse_optional_int(raw)
    if value is None:
        return None
    if value <= 0:
        return None
    return value


def _parse_csv_list(raw: Optional[str]) -> List[str]:
    if raw is None:
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


@dataclass
class Config:
    """
    Centralized configuration class for the workflow_mediapipe application.
    
    All configuration values are loaded from environment variables with
    sensible defaults to maintain backward compatibility.
    """
    
    # Flask Application Settings
    SECRET_KEY: str = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    HOST: str = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT: int = int(os.environ.get('FLASK_PORT', '5000'))
    
    # Security Tokens (loaded from environment)
    INTERNAL_WORKER_TOKEN: Optional[str] = os.environ.get('INTERNAL_WORKER_COMMS_TOKEN')
    RENDER_REGISTER_TOKEN: Optional[str] = os.environ.get('RENDER_REGISTER_TOKEN')
    
    # Webhook JSON Source (single data source for monitoring)
    WEBHOOK_JSON_URL: str = os.environ.get(
        'WEBHOOK_JSON_URL',
        'https://webhook.kidpixel.fr/data/webhook_links.json'
    )
    WEBHOOK_TIMEOUT: int = int(os.environ.get('WEBHOOK_TIMEOUT', '10'))
    WEBHOOK_CACHE_TTL: int = int(os.environ.get('WEBHOOK_CACHE_TTL', '60'))
    WEBHOOK_MONITOR_INTERVAL: int = int(os.environ.get('WEBHOOK_MONITOR_INTERVAL', '15'))
    
    # Directory Configuration
    BASE_PATH_SCRIPTS: Path = Path(os.environ.get(
        'BASE_PATH_SCRIPTS_ENV', 
        os.path.dirname(os.path.abspath(__file__ + '/../'))
    ))
    LOCAL_DOWNLOADS_DIR: Path = Path(os.environ.get(
        'LOCAL_DOWNLOADS_DIR', 
        Path.home() / 'Téléchargements'
    ))
    DOWNLOAD_HISTORY_SHARED_GROUP: Optional[str] = os.environ.get('DOWNLOAD_HISTORY_SHARED_GROUP')
    # LOGS_DIR is normalized in __post_init__ to be absolute under BASE_PATH_SCRIPTS by default.
    # If LOGS_DIR is set in env and is relative, it will be resolved against BASE_PATH_SCRIPTS.
    LOGS_DIR: Path = Path(os.environ.get('LOGS_DIR', ''))
    # Virtual environments base directory (defaults to project root if not set)
    VENV_BASE_DIR: Optional[Path] = Path(os.environ.get('VENV_BASE_DIR', '')) if os.environ.get('VENV_BASE_DIR') else None
    # Projects directory for visualization/timeline features
    PROJECTS_DIR: Path = Path(os.environ.get('PROJECTS_DIR', '')) if os.environ.get('PROJECTS_DIR') else None
    # Archives directory for persistent analysis results (timeline)
    ARCHIVES_DIR: Path = Path(os.environ.get('ARCHIVES_DIR', '')) if os.environ.get('ARCHIVES_DIR') else None
    
    # Python Environment Configuration
    PYTHON_VENV_EXE: str = os.environ.get('PYTHON_VENV_EXE_ENV', '')
    
    # Processing Configuration
    MAX_CPU_WORKERS: int = int(os.environ.get(
        'MAX_CPU_WORKERS', 
        str(max(1, os.cpu_count() - 2 if os.cpu_count() else 2))
    ))
    
    # Polling Intervals (in milliseconds for frontend, seconds for backend)
    POLLING_INTERVAL: int = int(os.environ.get('POLLING_INTERVAL', '1000'))
    LOCAL_DOWNLOAD_POLLING_INTERVAL: int = int(os.environ.get('LOCAL_DOWNLOAD_POLLING_INTERVAL', '3000'))

    SYSTEM_MONITOR_POLLING_INTERVAL: int = int(os.environ.get('SYSTEM_MONITOR_POLLING_INTERVAL', '5000'))
    
    # MediaPipe Configuration
    MP_LANDMARKER_MIN_DETECTION_CONFIDENCE: float = float(os.environ.get(
        'MP_LANDMARKER_MIN_DETECTION_CONFIDENCE', '0.5'
    ))
    MP_LANDMARKER_MIN_TRACKING_CONFIDENCE: float = float(os.environ.get(
        'MP_LANDMARKER_MIN_TRACKING_CONFIDENCE', '0.5'
    ))
    
    # GPU Configuration
    ENABLE_GPU_MONITORING: bool = os.environ.get('ENABLE_GPU_MONITORING', 'true').lower() == 'true'
    
    # Lemonfox API Configuration (STEP4 alternative)
    LEMONFOX_API_KEY: Optional[str] = os.environ.get('LEMONFOX_API_KEY')
    LEMONFOX_TIMEOUT_SEC: int = int(os.environ.get('LEMONFOX_TIMEOUT_SEC', '300'))
    LEMONFOX_EU_DEFAULT: bool = os.environ.get('LEMONFOX_EU_DEFAULT', '0') == '1'

    LEMONFOX_DEFAULT_LANGUAGE: Optional[str] = os.environ.get("LEMONFOX_DEFAULT_LANGUAGE")
    LEMONFOX_DEFAULT_PROMPT: Optional[str] = os.environ.get("LEMONFOX_DEFAULT_PROMPT")
    LEMONFOX_SPEAKER_LABELS_DEFAULT: bool = _parse_bool(
        os.environ.get("LEMONFOX_SPEAKER_LABELS_DEFAULT"),
        default=True,
    )
    LEMONFOX_DEFAULT_MIN_SPEAKERS: Optional[int] = _parse_optional_int(
        os.environ.get("LEMONFOX_DEFAULT_MIN_SPEAKERS")
    )
    LEMONFOX_DEFAULT_MAX_SPEAKERS: Optional[int] = _parse_optional_int(
        os.environ.get("LEMONFOX_DEFAULT_MAX_SPEAKERS")
    )
    LEMONFOX_TIMESTAMP_GRANULARITIES: List[str] = field(
        default_factory=lambda: _parse_csv_list(os.environ.get("LEMONFOX_TIMESTAMP_GRANULARITIES", "word"))
    )
    LEMONFOX_SPEECH_GAP_FILL_SEC: float = float(os.environ.get("LEMONFOX_SPEECH_GAP_FILL_SEC", "0.15"))
    LEMONFOX_SPEECH_MIN_ON_SEC: float = float(os.environ.get("LEMONFOX_SPEECH_MIN_ON_SEC", "0.0"))
    LEMONFOX_MAX_UPLOAD_MB: Optional[int] = _parse_optional_positive_int(
        os.environ.get("LEMONFOX_MAX_UPLOAD_MB")
    )
    LEMONFOX_ENABLE_TRANSCODE: bool = _parse_bool(
        os.environ.get("LEMONFOX_ENABLE_TRANSCODE"),
        default=False,
    )
    LEMONFOX_TRANSCODE_AUDIO_CODEC: str = os.environ.get("LEMONFOX_TRANSCODE_AUDIO_CODEC", "aac")
    LEMONFOX_TRANSCODE_BITRATE_KBPS: int = int(os.environ.get("LEMONFOX_TRANSCODE_BITRATE_KBPS", "96"))

    STEP4_USE_LEMONFOX: bool = os.environ.get('STEP4_USE_LEMONFOX', '0') == '1'
    
    # STEP5 Object Detection Configuration
    # Model selection for fallback object detection when face detection fails (MediaPipe only)
    STEP5_OBJECT_DETECTOR_MODEL: str = os.environ.get(
        'STEP5_OBJECT_DETECTOR_MODEL',
        'efficientdet_lite2'  # Default: current baseline, backward compatible
    )
    STEP5_OBJECT_DETECTOR_MODEL_PATH: Optional[str] = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH')
    STEP5_ENABLE_OBJECT_DETECTION: bool = os.environ.get('STEP5_ENABLE_OBJECT_DETECTION', '0') == '1'
    
    # STEP5 Performance Optimizations (opencv_yunet_pyfeat)
    STEP5_ENABLE_PROFILING: bool = os.environ.get('STEP5_ENABLE_PROFILING', '0') == '1'
    STEP5_ONNX_INTRA_OP_THREADS: int = int(os.environ.get('STEP5_ONNX_INTRA_OP_THREADS', '2'))
    STEP5_ONNX_INTER_OP_THREADS: int = int(os.environ.get('STEP5_ONNX_INTER_OP_THREADS', '1'))
    STEP5_BLENDSHAPES_THROTTLE_N: int = int(os.environ.get('STEP5_BLENDSHAPES_THROTTLE_N', '1'))  # 1 = every frame (no throttling)
    STEP5_YUNET_MAX_WIDTH: int = int(os.environ.get('STEP5_YUNET_MAX_WIDTH', '640'))  # Max width for YuNet detection (coordinates rescaled)

    STEP5_OPENCV_MAX_FACES: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_OPENCV_MAX_FACES')
    )
    STEP5_OPENCV_JAWOPEN_SCALE: float = float(os.environ.get('STEP5_OPENCV_JAWOPEN_SCALE', '1.0'))

    STEP5_MEDIAPIPE_MAX_FACES: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_MEDIAPIPE_MAX_FACES')
    )
    STEP5_MEDIAPIPE_JAWOPEN_SCALE: float = float(os.environ.get('STEP5_MEDIAPIPE_JAWOPEN_SCALE', '1.0'))
    STEP5_MEDIAPIPE_MAX_WIDTH: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_MEDIAPIPE_MAX_WIDTH')
    )

    # STEP5 OpenSeeFace Engine Configuration
    # Lightweight CPU tracking via ONNX Runtime (OpenSeeFace-style models)
    STEP5_OPENSEEFACE_MODELS_DIR: Optional[str] = os.environ.get('STEP5_OPENSEEFACE_MODELS_DIR')
    STEP5_OPENSEEFACE_MODEL_ID: int = int(os.environ.get('STEP5_OPENSEEFACE_MODEL_ID', '1'))
    STEP5_OPENSEEFACE_DETECTION_MODEL_PATH: Optional[str] = os.environ.get('STEP5_OPENSEEFACE_DETECTION_MODEL_PATH')
    STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH: Optional[str] = os.environ.get('STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH')
    STEP5_OPENSEEFACE_DETECT_EVERY_N: int = int(os.environ.get('STEP5_OPENSEEFACE_DETECT_EVERY_N', '1'))
    STEP5_OPENSEEFACE_MAX_WIDTH: int = int(
        os.environ.get('STEP5_OPENSEEFACE_MAX_WIDTH')
        or os.environ.get('STEP5_YUNET_MAX_WIDTH', '640')
    )
    STEP5_OPENSEEFACE_DETECTION_THRESHOLD: float = float(os.environ.get('STEP5_OPENSEEFACE_DETECTION_THRESHOLD', '0.6'))
    STEP5_OPENSEEFACE_MAX_FACES: int = int(os.environ.get('STEP5_OPENSEEFACE_MAX_FACES', '1'))
    STEP5_OPENSEEFACE_JAWOPEN_SCALE: float = float(os.environ.get('STEP5_OPENSEEFACE_JAWOPEN_SCALE', '1.0'))

    STEP5_EOS_ENV_PYTHON: Optional[str] = os.environ.get('STEP5_EOS_ENV_PYTHON')
    STEP5_EOS_MODELS_DIR: Optional[str] = os.environ.get('STEP5_EOS_MODELS_DIR')
    STEP5_EOS_SFM_MODEL_PATH: Optional[str] = os.environ.get('STEP5_EOS_SFM_MODEL_PATH')
    STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH: Optional[str] = os.environ.get('STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH')
    STEP5_EOS_LANDMARK_MAPPER_PATH: Optional[str] = os.environ.get('STEP5_EOS_LANDMARK_MAPPER_PATH')
    STEP5_EOS_EDGE_TOPOLOGY_PATH: Optional[str] = os.environ.get('STEP5_EOS_EDGE_TOPOLOGY_PATH')
    STEP5_EOS_MODEL_CONTOUR_PATH: Optional[str] = os.environ.get('STEP5_EOS_MODEL_CONTOUR_PATH')
    STEP5_EOS_CONTOUR_LANDMARKS_PATH: Optional[str] = os.environ.get('STEP5_EOS_CONTOUR_LANDMARKS_PATH')
    STEP5_EOS_FIT_EVERY_N: int = int(os.environ.get('STEP5_EOS_FIT_EVERY_N', '1'))
    STEP5_EOS_MAX_FACES: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_EOS_MAX_FACES')
    )
    STEP5_EOS_MAX_WIDTH: int = int(os.environ.get('STEP5_EOS_MAX_WIDTH', '1280'))
    STEP5_EOS_JAWOPEN_SCALE: float = float(os.environ.get('STEP5_EOS_JAWOPEN_SCALE', '1.0'))
    
    def __post_init__(self):
        """Post-initialization to ensure paths are Path objects and create directories."""
        # Ensure all path attributes are Path objects
        if isinstance(self.BASE_PATH_SCRIPTS, str):
            self.BASE_PATH_SCRIPTS = Path(self.BASE_PATH_SCRIPTS)
        if isinstance(self.LOCAL_DOWNLOADS_DIR, str):
            self.LOCAL_DOWNLOADS_DIR = Path(self.LOCAL_DOWNLOADS_DIR)
        if isinstance(self.LOGS_DIR, str):
            self.LOGS_DIR = Path(self.LOGS_DIR)
        
        # Default VENV_BASE_DIR to BASE_PATH_SCRIPTS if not set
        if self.VENV_BASE_DIR is None or (isinstance(self.VENV_BASE_DIR, str) and not self.VENV_BASE_DIR):
            self.VENV_BASE_DIR = self.BASE_PATH_SCRIPTS
        elif isinstance(self.VENV_BASE_DIR, str):
            self.VENV_BASE_DIR = Path(self.VENV_BASE_DIR)

        # Resolve PYTHON_VENV_EXE via VENV_BASE_DIR logic.
        # If PYTHON_VENV_EXE_ENV is provided and is relative, resolve it against VENV_BASE_DIR.
        if not self.PYTHON_VENV_EXE:
            self.PYTHON_VENV_EXE = str(self.get_venv_python("env"))
        else:
            python_exe_path = Path(self.PYTHON_VENV_EXE)
            if not python_exe_path.is_absolute():
                self.PYTHON_VENV_EXE = str((self.VENV_BASE_DIR / python_exe_path).resolve())
        
        # Normalize LOGS_DIR to avoid CWD-dependent side effects when importing config from step scripts.
        # Default to <BASE_PATH_SCRIPTS>/logs if not provided. If provided and relative, make it absolute
        # under BASE_PATH_SCRIPTS. This prevents accidental creation of logs under working directories
        # like 'projets_extraits/logs' when steps run with a different CWD.
        if (not str(self.LOGS_DIR)) or (str(self.LOGS_DIR).strip() == '.'):
            self.LOGS_DIR = (self.BASE_PATH_SCRIPTS / 'logs').resolve()
        elif not self.LOGS_DIR.is_absolute():
            self.LOGS_DIR = (self.BASE_PATH_SCRIPTS / self.LOGS_DIR).resolve()
        # Default PROJECTS_DIR if not set
        if self.PROJECTS_DIR is None or (isinstance(self.PROJECTS_DIR, str) and not self.PROJECTS_DIR):
            self.PROJECTS_DIR = self.BASE_PATH_SCRIPTS / 'projets_extraits'
        elif isinstance(self.PROJECTS_DIR, str):
            self.PROJECTS_DIR = Path(self.PROJECTS_DIR)
        # Default ARCHIVES_DIR if not set
        if self.ARCHIVES_DIR is None or (isinstance(self.ARCHIVES_DIR, str) and not self.ARCHIVES_DIR):
            self.ARCHIVES_DIR = self.BASE_PATH_SCRIPTS / 'archives'
        elif isinstance(self.ARCHIVES_DIR, str):
            self.ARCHIVES_DIR = Path(self.ARCHIVES_DIR)
            
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories_to_create = [
            self.LOGS_DIR,
            self.LOGS_DIR / 'step1',
            self.LOGS_DIR / 'step2',
            self.LOGS_DIR / 'step3',
            self.LOGS_DIR / 'step4',
            self.LOGS_DIR / 'step5',
            self.LOGS_DIR / 'step6',
            self.LOGS_DIR / 'step7',
            # Ensure projects directory exists by default to avoid confusion
            self.PROJECTS_DIR,
            # Ensure archives directory exists
            self.ARCHIVES_DIR,
        ]
        
        for directory in directories_to_create:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
    
    def validate(self, strict: bool = None) -> bool:
        """
        Validate the configuration and ensure all required settings are present.

        Args:
            strict: If None, uses DEBUG mode to determine strictness.
                   If True, raises errors. If False, logs warnings.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If required configuration is missing or invalid and strict=True
        """
        if strict is None:
            strict = not self.DEBUG  # Strict in production, lenient in development

        errors = []
        warnings = []

        # Security validation
        if not self.INTERNAL_WORKER_TOKEN:
            msg = "INTERNAL_WORKER_COMMS_TOKEN environment variable is required"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
                # Set development default
                self.INTERNAL_WORKER_TOKEN = "dev-internal-worker-token"

        if not self.RENDER_REGISTER_TOKEN:
            msg = "RENDER_REGISTER_TOKEN environment variable is required"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
                # Set development default
                self.RENDER_REGISTER_TOKEN = "dev-render-register-token"

        # Production security checks
        if not self.DEBUG and self.SECRET_KEY in ['dev-key-change-in-production', 'dev-secret-key-change-in-production-12345678901234567890']:
            errors.append("FLASK_SECRET_KEY must be changed in production (DEBUG=false)")

        # Webhook validation (single data source)
        if not self.WEBHOOK_JSON_URL:
            msg = "WEBHOOK_JSON_URL must be set"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
        if self.WEBHOOK_TIMEOUT <= 0:
            warnings.append("WEBHOOK_TIMEOUT should be > 0; using default")
        if self.WEBHOOK_CACHE_TTL < 0:
            warnings.append("WEBHOOK_CACHE_TTL should be >= 0; using default")
        
        # Path validation
        if not self.BASE_PATH_SCRIPTS.exists():
            warnings.append(f"Base scripts path does not exist: {self.BASE_PATH_SCRIPTS}")
        
        if not self.LOCAL_DOWNLOADS_DIR.exists():
            warnings.append(f"Downloads directory does not exist: {self.LOCAL_DOWNLOADS_DIR}")
        
        # Python executable validation
        python_exe_path = Path(self.PYTHON_VENV_EXE)
        if not python_exe_path.exists():
            warnings.append(f"Python executable not found: {python_exe_path}")
        
        # Log warnings
        for warning in warnings:
            logger.warning(warning)
        
        # Log warnings
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
            if not strict:
                logger.warning("Using development defaults - NOT SUITABLE FOR PRODUCTION")

        # Raise errors if any
        if errors:
            error_msg = f"Configuration validation failed: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings and not strict:
            logger.info("Configuration validation completed with warnings (development mode)")
        else:
            logger.info("Configuration validation successful")
        return True
    
    def get_venv_path(self, venv_name: str) -> Path:
        """
        Get the path to a virtual environment.
        
        Args:
            venv_name: Name of the virtual environment (e.g., 'env', 'audio_env', 'tracking_env')
            
        Returns:
            Path object to the virtual environment directory
        """
        return self.VENV_BASE_DIR / venv_name
    
    def get_venv_python(self, venv_name: str) -> Path:
        """
        Get the path to the Python executable in a virtual environment.
        
        Args:
            venv_name: Name of the virtual environment
            
        Returns:
            Path object to the Python executable
        """
        return self.get_venv_path(venv_name) / "bin" / "python"
    
    def get_allowed_base_paths(self) -> List[Path]:
        """
        Get list of allowed base paths for file operations.
        
        Returns:
            List of Path objects representing allowed base directories
        """
        return [
            self.BASE_PATH_SCRIPTS,
            self.LOCAL_DOWNLOADS_DIR,
            self.LOGS_DIR,
            self.BASE_PATH_SCRIPTS / 'workflow_scripts',
            self.BASE_PATH_SCRIPTS / 'static',
            self.BASE_PATH_SCRIPTS / 'templates',
            self.BASE_PATH_SCRIPTS / 'utils',
        ]
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary for serialization.
        
        Returns:
            Dictionary representation of configuration (excluding sensitive data)
        """
        config_dict = {}
        for key, value in self.__dict__.items():
            # Exclude sensitive information
            if 'TOKEN' in key or 'SECRET' in key:
                config_dict[key] = '***HIDDEN***' if value else None
            elif isinstance(value, Path):
                config_dict[key] = str(value)
            else:
                config_dict[key] = value
        
        return config_dict
    
    @staticmethod
    def check_gpu_availability() -> dict:
        """
        Vérifier la disponibilité GPU pour STEP5 (MediaPipe + OpenSeeFace).
        
        Returns:
            dict: {
                'available': bool,
                'reason': str (si non disponible),
                'vram_total_gb': float (si disponible),
                'vram_free_gb': float (si disponible),
                'cuda_version': str (si disponible),
                'onnx_cuda': bool,
                'tensorflow_gpu': bool
            }
        """
        result = {
            'available': False,
            'reason': '',
            'onnx_cuda': False,
            'tensorflow_gpu': False
        }
        
        # Check PyTorch CUDA (indicateur général)
        try:
            import torch
            if not torch.cuda.is_available():
                result['reason'] = 'CUDA not available (PyTorch check)'
                return result
            
            # Vérifier VRAM
            vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # Go
            vram_free = (torch.cuda.mem_get_info()[0]) / (1024**3)  # Go
            
            result['vram_total_gb'] = round(vram_total, 2)
            result['vram_free_gb'] = round(vram_free, 2)
            result['cuda_version'] = torch.version.cuda
            
            # Vérifier VRAM minimale (2 Go libres recommandés)
            if vram_free < 1.5:
                result['reason'] = f'VRAM insuffisante ({vram_free:.1f} Go libres < 1.5 Go)'
                return result
        
        except ImportError:
            result['reason'] = 'PyTorch not installed in tracking_env'
            return result
        except Exception as e:
            result['reason'] = f'PyTorch CUDA check failed: {e}'
            return result
        
        # Check ONNXRuntime CUDA provider (requis pour OpenSeeFace / InsightFace)
        try:
            import onnxruntime as ort
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                result['onnx_cuda'] = True
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"ONNXRuntime check failed: {e}")

        # Optional external ONNXRuntime CUDA check (useful when ORT GPU lives in a dedicated venv)
        if not result.get('onnx_cuda'):
            ort_gpu_python = os.environ.get('STEP5_INSIGHTFACE_ENV_PYTHON', '').strip()
            if ort_gpu_python:
                try:
                    ort_check_code = (
                        "import sys\n"
                        "import onnxruntime as ort\n"
                        "providers = ort.get_available_providers()\n"
                        "sys.stdout.write('1' if 'CUDAExecutionProvider' in providers else '0')"
                    )
                    completed = subprocess.run(
                        [ort_gpu_python, "-c", ort_check_code],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    if completed.returncode == 0:
                        result['onnx_cuda'] = completed.stdout.strip() == "1"
                    else:
                        logger.warning(
                            "ONNXRuntime GPU check failed (external env returned code %s): %s",
                            completed.returncode,
                            completed.stderr.strip(),
                        )
                except FileNotFoundError:
                    logger.warning(
                        "STEP5_INSIGHTFACE_ENV_PYTHON '%s' introuvable pour la vérification GPU ONNXRuntime",
                        ort_gpu_python,
                    )
                except subprocess.TimeoutExpired:
                    logger.warning("ONNXRuntime GPU check timed out via STEP5_INSIGHTFACE_ENV_PYTHON")
                except Exception as exc:
                    logger.warning(f"ONNXRuntime GPU check failed via STEP5_INSIGHTFACE_ENV_PYTHON: {exc}")
        
        # Déterminer disponibilité finale (InsightFace s'appuie uniquement sur ONNX Runtime GPU)
        if result['onnx_cuda']:
            result['available'] = True
        else:
            result['reason'] = 'ONNXRuntime GPU indisponible (installer onnxruntime-gpu)'
        
        return result
    
    @staticmethod
    def is_step5_gpu_enabled() -> bool:
        """
        Vérifier si le mode GPU STEP5 est activé via configuration.
        
        Returns:
            bool: True si STEP5_ENABLE_GPU=1
        """
        return _parse_bool(os.environ.get('STEP5_ENABLE_GPU'), default=False)
    
    @staticmethod
    def get_step5_gpu_engines() -> List[str]:
        """
        Récupérer la liste des moteurs STEP5 autorisés à utiliser le GPU.
        
        Returns:
            List[str]: ['mediapipe_landmarker', 'openseeface', ...]
        """
        engines_str = os.environ.get('STEP5_GPU_ENGINES', '')
        engines = _parse_csv_list(engines_str)
        # Normaliser les noms
        return [e.strip().lower() for e in engines if e.strip()]
    
    @staticmethod
    def get_step5_gpu_max_vram_mb() -> int:
        """
        Récupérer la limite VRAM maximale pour STEP5 GPU (Mo).
        
        Returns:
            int: Limite en Mo (défaut: 2048)
        """
        return _parse_optional_positive_int(
            os.environ.get('STEP5_GPU_MAX_VRAM_MB')
        ) or 2048


# Global configuration instance
config = Config()
