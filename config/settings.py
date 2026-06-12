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


def _parse_optional_float(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except Exception:
        return None


def _normalize_step4_method(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    method = raw.strip().lower()
    if method in {"pyannote", "lemonfox", "deepinfra"}:
        return method
    return None


DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL = "https://api.deepinfra.com/v1/openai/audio/transcriptions"


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
    CACHE_ROOT_DIR: Path = Path(os.environ.get('CACHE_ROOT_DIR', '/mnt/cache'))
    LOCAL_DOWNLOADS_DIR: Path = Path(os.environ.get(
        'LOCAL_DOWNLOADS_DIR', 
        Path.home() / 'Téléchargements'
    ))
    DISABLE_EXPLORER_OPEN: bool = _parse_bool(os.environ.get('DISABLE_EXPLORER_OPEN'), default=False)
    ENABLE_EXPLORER_OPEN: bool = _parse_bool(os.environ.get('ENABLE_EXPLORER_OPEN'), default=False)
    DOWNLOAD_HISTORY_SHARED_GROUP: Optional[str] = os.environ.get('DOWNLOAD_HISTORY_SHARED_GROUP')
    DOWNLOAD_HISTORY_DB_PATH: Path = Path(os.environ.get('DOWNLOAD_HISTORY_DB_PATH', ''))
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

    STEP4_METHOD: str = os.environ.get("STEP4_METHOD", "")
    STEP4_USE_LEMONFOX: bool = os.environ.get('STEP4_USE_LEMONFOX', '0') == '1'

    # DeepInfra API Configuration (STEP4 alternative)
    DEEPINFRA_API_KEY: Optional[str] = os.environ.get("DEEPINFRA_API_KEY")
    DEEPINFRA_BASE_URL: str = os.environ.get("DEEPINFRA_BASE_URL", "https://api.deepinfra.com")
    DEEPINFRA_TRANSCRIPTIONS_ENDPOINT: str = os.environ.get(
        "DEEPINFRA_TRANSCRIPTIONS_ENDPOINT",
        "/v1/openai/audio/transcriptions",
    )
    DEEPINFRA_TRANSCRIPTIONS_URL: str = os.environ.get("DEEPINFRA_TRANSCRIPTIONS_URL", "")
    DEEPINFRA_MODEL: str = os.environ.get("DEEPINFRA_MODEL", "openai/whisper-large-v3")
    DEEPINFRA_TIMEOUT_SEC: int = int(os.environ.get("DEEPINFRA_TIMEOUT_SEC", "600"))
    DEEPINFRA_CONNECT_TIMEOUT_SEC: int = int(os.environ.get("DEEPINFRA_CONNECT_TIMEOUT_SEC", "10"))
    DEEPINFRA_MAX_RETRIES: int = int(os.environ.get("DEEPINFRA_MAX_RETRIES", "2"))
    DEEPINFRA_BACKOFF_SEC: float = float(os.environ.get("DEEPINFRA_BACKOFF_SEC", "1.5"))
    DEEPINFRA_DEFAULT_LANGUAGE: Optional[str] = os.environ.get("DEEPINFRA_DEFAULT_LANGUAGE")
    DEEPINFRA_DEFAULT_PROMPT: Optional[str] = os.environ.get("DEEPINFRA_DEFAULT_PROMPT")
    DEEPINFRA_RESPONSE_FORMAT: str = os.environ.get("DEEPINFRA_RESPONSE_FORMAT", "verbose_json")
    DEEPINFRA_TIMESTAMP_GRANULARITIES: List[str] = field(
        default_factory=lambda: _parse_csv_list(os.environ.get("DEEPINFRA_TIMESTAMP_GRANULARITIES", "segment"))
    )
    DEEPINFRA_TEMPERATURE: Optional[float] = _parse_optional_float(os.environ.get("DEEPINFRA_TEMPERATURE"))
    DEEPINFRA_FALLBACK_TO_PYANNOTE: bool = _parse_bool(
        os.environ.get("STEP4_DEEPINFRA_FALLBACK_TO_PYANNOTE"),
        default=True,
    )
    DEEPINFRA_SPEECH_GAP_FILL_SEC: float = float(os.environ.get("DEEPINFRA_SPEECH_GAP_FILL_SEC", "0.15"))
    DEEPINFRA_SPEECH_MIN_ON_SEC: float = float(os.environ.get("DEEPINFRA_SPEECH_MIN_ON_SEC", "0.0"))
    
    # STEP5 Object Detection Configuration
    # Model selection for fallback object detection when face detection fails (MediaPipe only)
    STEP5_OBJECT_DETECTOR_MODEL: str = os.environ.get(
        'STEP5_OBJECT_DETECTOR_MODEL',
        'efficientdet_lite2'  # Default: current baseline, backward compatible
    )
    STEP5_OBJECT_DETECTOR_MODEL_PATH: Optional[str] = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH')
    STEP5_ENABLE_OBJECT_DETECTION: bool = os.environ.get('STEP5_ENABLE_OBJECT_DETECTION', '0') == '1'
    
    # STEP5 Tracking configuration
    STEP5_ENABLE_PROFILING: bool = os.environ.get('STEP5_ENABLE_PROFILING', '0') == '1'
    STEP5_BLENDSHAPES_THROTTLE_N: int = int(os.environ.get('STEP5_BLENDSHAPES_THROTTLE_N', '1'))  # 1 = every frame (no throttling)

    STEP5_MEDIAPIPE_MAX_FACES: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_MEDIAPIPE_MAX_FACES')
    )
    STEP5_MEDIAPIPE_JAWOPEN_SCALE: float = float(os.environ.get('STEP5_MEDIAPIPE_JAWOPEN_SCALE', '1.0'))
    STEP5_MEDIAPIPE_MAX_WIDTH: Optional[int] = _parse_optional_positive_int(
        os.environ.get('STEP5_MEDIAPIPE_MAX_WIDTH')
    )
    
    def __post_init__(self):
        """Post-initialization to ensure paths are Path objects and create directories."""
        # Ensure all path attributes are Path objects
        if isinstance(self.BASE_PATH_SCRIPTS, str):
            self.BASE_PATH_SCRIPTS = Path(self.BASE_PATH_SCRIPTS)
        if isinstance(self.CACHE_ROOT_DIR, str):
            self.CACHE_ROOT_DIR = Path(self.CACHE_ROOT_DIR)
        if isinstance(self.LOCAL_DOWNLOADS_DIR, str):
            self.LOCAL_DOWNLOADS_DIR = Path(self.LOCAL_DOWNLOADS_DIR)
        if isinstance(self.LOGS_DIR, str):
            self.LOGS_DIR = Path(self.LOGS_DIR)

        if isinstance(self.DOWNLOAD_HISTORY_DB_PATH, str):
            self.DOWNLOAD_HISTORY_DB_PATH = Path(self.DOWNLOAD_HISTORY_DB_PATH)
        
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

        if (not str(self.DOWNLOAD_HISTORY_DB_PATH)) or (str(self.DOWNLOAD_HISTORY_DB_PATH).strip() == '.'):
            self.DOWNLOAD_HISTORY_DB_PATH = (self.BASE_PATH_SCRIPTS / 'download_history.sqlite3').resolve()
        elif not self.DOWNLOAD_HISTORY_DB_PATH.is_absolute():
            self.DOWNLOAD_HISTORY_DB_PATH = (self.BASE_PATH_SCRIPTS / self.DOWNLOAD_HISTORY_DB_PATH).resolve()

        if (not str(self.CACHE_ROOT_DIR)) or (str(self.CACHE_ROOT_DIR).strip() == '.'):
            self.CACHE_ROOT_DIR = Path('/mnt/cache')
        elif not self.CACHE_ROOT_DIR.is_absolute():
            self.CACHE_ROOT_DIR = (self.BASE_PATH_SCRIPTS / self.CACHE_ROOT_DIR).resolve()
        else:
            self.CACHE_ROOT_DIR = self.CACHE_ROOT_DIR.resolve()

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

        self.DEEPINFRA_RESPONSE_FORMAT = (self.DEEPINFRA_RESPONSE_FORMAT or "verbose_json").strip().lower() or "verbose_json"
        if self.DEEPINFRA_RESPONSE_FORMAT not in {"json", "verbose_json", "text", "srt", "vtt"}:
            logger.warning(
                "DEEPINFRA_RESPONSE_FORMAT invalide ('%s'), fallback vers 'verbose_json'.",
                self.DEEPINFRA_RESPONSE_FORMAT,
            )
            self.DEEPINFRA_RESPONSE_FORMAT = "verbose_json"

        if self.DEEPINFRA_TIMEOUT_SEC <= 0:
            self.DEEPINFRA_TIMEOUT_SEC = 600
        if self.DEEPINFRA_CONNECT_TIMEOUT_SEC <= 0:
            self.DEEPINFRA_CONNECT_TIMEOUT_SEC = 10
        if self.DEEPINFRA_MAX_RETRIES < 0:
            self.DEEPINFRA_MAX_RETRIES = 0
        if self.DEEPINFRA_BACKOFF_SEC <= 0:
            self.DEEPINFRA_BACKOFF_SEC = 1.5

        self.DEEPINFRA_TRANSCRIPTIONS_URL = self.resolve_deepinfra_transcriptions_url()
            
        # Create necessary directories
        self._create_directories()

    def resolve_step4_method(self) -> str:
        """
        Resolve active STEP4 method with backward compatibility.

        Priority:
          1) STEP4_METHOD when valid (pyannote|lemonfox|deepinfra)
          2) Legacy STEP4_USE_LEMONFOX toggle
          3) Default pyannote
        """
        normalized = _normalize_step4_method(getattr(self, "STEP4_METHOD", None))
        if normalized:
            return normalized
        if bool(getattr(self, "STEP4_USE_LEMONFOX", False)):
            return "lemonfox"
        return "pyannote"

    def resolve_deepinfra_transcriptions_url(self) -> str:
        """Resolve DeepInfra transcription URL and guard against known typo endpoint variants."""
        direct_url = (getattr(self, "DEEPINFRA_TRANSCRIPTIONS_URL", "") or "").strip()
        if direct_url:
            candidate = direct_url
        else:
            base_url = (getattr(self, "DEEPINFRA_BASE_URL", "") or "").strip().rstrip("/")
            endpoint = (getattr(self, "DEEPINFRA_TRANSCRIPTIONS_ENDPOINT", "") or "").strip()
            if endpoint and not endpoint.startswith("/"):
                endpoint = f"/{endpoint}"
            candidate = f"{base_url}{endpoint}" if base_url else endpoint

        if not candidate:
            return DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL

        if "wisper" in candidate.lower():
            logger.warning(
                "DEEPINFRA endpoint '%s' contient 'wisper' (typo connu). Fallback endpoint officiel.",
                candidate,
            )
            return DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL

        if not candidate.startswith("http://") and not candidate.startswith("https://"):
            logger.warning(
                "DEEPINFRA endpoint '%s' invalide (URL absolue requise). Fallback endpoint officiel.",
                candidate,
            )
            return DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL

        return candidate
    
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
        elif self.INTERNAL_WORKER_TOKEN.startswith("dev-") or self.INTERNAL_WORKER_TOKEN == "dev-internal-worker-token":
            msg = f"INTERNAL_WORKER_COMMS_TOKEN cannot be a development/default token in production: '{self.INTERNAL_WORKER_TOKEN}'"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)



        # Production security checks
        if not self.DEBUG and (self.SECRET_KEY.startswith('dev-') or self.SECRET_KEY in ['dev-key-change-in-production', 'dev-secret-key-change-in-production-12345678901234567890']):
            errors.append(f"FLASK_SECRET_KEY must be a secure value and cannot start with 'dev-' in production: '{self.SECRET_KEY}'")

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
        path = self.VENV_BASE_DIR / venv_name
        if not path.exists():
            fallback_path = self.BASE_PATH_SCRIPTS / venv_name
            if fallback_path.exists():
                return fallback_path
        return path
    
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
        Vérifier la disponibilité GPU pour STEP5 (InsightFace uniquement).
        
        Returns:
            dict: {
                'available': bool,
                'reason': str (si non disponible),
                'vram_total_gb': float (si disponible),
                'vram_free_gb': float (si disponible),
                'cuda_version': str (si disponible),
                'onnx_cuda': bool
            }
        """
        result = {
            'available': False,
            'reason': '',
            'onnx_cuda': False,
        }
        
        # Check GPU availability via pynv (NVML) first, fallback to nvidia-smi
        gpu_checked = False
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_total = mem_info.total / (1024 ** 3)
            vram_free = mem_info.free / (1024 ** 3)
            result['vram_total_gb'] = round(vram_total, 2)
            result['vram_free_gb'] = round(vram_free, 2)
            try:
                cuda_v_raw = pynvml.nvmlSystemGetCudaDriverVersion()
                result['cuda_version'] = f"{cuda_v_raw // 1000}.{(cuda_v_raw % 1000) // 10}"
            except Exception:
                result['cuda_version'] = os.environ.get('CUDA_VERSION') or ''
            gpu_checked = True

            if vram_free < 1.5:
                result['reason'] = f'VRAM insuffisante ({vram_free:.1f} Go libres < 1.5 Go)'
                return result
        except ImportError:
            logger.debug('pynvml not available; falling back to nvidia-smi for GPU detection')
        except Exception as e:
            logger.warning(f"pynvml check failed: {e}; falling back to nvidia-smi")

        if not gpu_checked:
            try:
                completed = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.total,memory.free', '--format=csv,noheader,nounits'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if completed.returncode == 0:
                    line = completed.stdout.strip().split('\n')[0]
                    total_str, free_str = [part.strip() for part in line.split(',')]
                    vram_total = float(total_str) / 1024
                    vram_free = float(free_str) / 1024
                    result['vram_total_gb'] = round(vram_total, 2)
                    result['vram_free_gb'] = round(vram_free, 2)
                    gpu_checked = True
                    if vram_free < 1.5:
                        result['reason'] = f'VRAM insuffisante ({vram_free:.1f} Go libres < 1.5 Go)'
                        return result
                else:
                    logger.warning(
                        "nvidia-smi GPU check failed (code %s): %s",
                        completed.returncode,
                        completed.stderr.strip(),
                    )
            except FileNotFoundError:
                logger.warning("nvidia-smi introuvable pour la vérification GPU")
            except subprocess.TimeoutExpired:
                logger.warning("nvidia-smi GPU check timed out")
            except Exception as e:
                logger.warning(f"nvidia-smi GPU check failed: {e}")

        if not gpu_checked:
            result['reason'] = 'Impossible de déterminer la disponibilité GPU (pynvml/nvidia-smi indisponibles)'
            return result
        
        # Check ONNXRuntime CUDA provider (requis pour InsightFace)
        try:
            import onnxruntime as ort  # type: ignore
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
        
        # Fallback to torch for CUDA version if still empty
        if not result.get('cuda_version'):
            try:
                import torch
                if torch.cuda.is_available():
                    result['cuda_version'] = torch.version.cuda or ''
            except Exception:
                pass

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
            List[str]: ['insightface'] (valeurs non supportées ignorées)
        """
        engines_str = os.environ.get('STEP5_GPU_ENGINES', '')
        engines = _parse_csv_list(engines_str)

        normalized = [e.strip().lower() for e in engines if e.strip()]
        allowed = {"insightface", "all"}
        return [e for e in normalized if e in allowed]
    
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

    # ========================
    # Coral TPU Acceleration
    # ========================
    ENABLE_CORAL_TPU_ACCELERATION: bool = os.environ.get('ENABLE_CORAL_TPU_ACCELERATION', 'false').lower() == 'true'
    STEP3_ENABLE_CORAL_TPU: bool = _parse_bool(os.environ.get('STEP3_ENABLE_CORAL_TPU'), default=True)
    STEP4_ENABLE_CORAL_TPU: bool = _parse_bool(os.environ.get('STEP4_ENABLE_CORAL_TPU'), default=True)
    STEP5_ENABLE_CORAL_TPU: bool = _parse_bool(os.environ.get('STEP5_ENABLE_CORAL_TPU'), default=True)



# Global configuration instance
config = Config()
