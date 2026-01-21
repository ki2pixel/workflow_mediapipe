import csv
import html
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import atexit
from collections import deque
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid

import psutil
import requests
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_caching import Cache

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Dotenv loaded successfully")
except ImportError:
    print("⚠️ Dotenv not available - using environment variables directly")
    pass

from config.settings import config
from config.security import SecurityConfig, require_internal_worker_token, require_render_register_token
from config.workflow_commands import WorkflowCommandsConfig

from routes.api_routes import api_bp
from routes.workflow_routes import workflow_bp
from services.monitoring_service import MonitoringService
from services.csv_service import CSVService
from services.workflow_service import WorkflowService
from services.cache_service import CacheService
from services.performance_service import PerformanceService
from services.filesystem_service import FilesystemService
from services.download_service import DownloadService
from services.workflow_state import get_workflow_state, reset_workflow_state
import urllib.parse

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("AVERTISSEMENT: pandas non disponible. Les fichiers Excel ne pourront pas être traités.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import pynvml
    if config.ENABLE_GPU_MONITORING:
        PYNVML_AVAILABLE = True
        pynvml.nvmlInit()
        logger.info("GPU monitoring initialized successfully")
    else:
        PYNVML_AVAILABLE = False
        logger.info("GPU monitoring disabled by configuration")
except ImportError:
    PYNVML_AVAILABLE = False
    logger.warning("pynvml not available. GPU monitoring disabled.")
except Exception as e:
    PYNVML_AVAILABLE = False
    logger.error(f"Failed to initialize GPU monitoring: {e}")

BASE_PATH_SCRIPTS = config.BASE_PATH_SCRIPTS
PYTHON_VENV_EXE = config.PYTHON_VENV_EXE

PARALLEL_TRACKING_SCRIPT_PATH = BASE_PATH_SCRIPTS / "workflow_scripts" / "step5" / "run_tracking_manager.py"

os.environ['ROOT_SCAN_DIR'] = str(BASE_PATH_SCRIPTS / "projets_extraits")
KEYWORD_FILTER_TRACKING_ENV = "Camille"
os.environ['FOLDER_KEYWORD'] = KEYWORD_FILTER_TRACKING_ENV
SUBDIR_FILTER_TRACKING_ENV = "docs"
os.environ['SUBFOLDER_NAME'] = SUBDIR_FILTER_TRACKING_ENV
os.environ.setdefault('TRACKING_DISABLE_GPU', '1')
os.environ.setdefault('TRACKING_CPU_WORKERS', '15')

LOGS_BASE_DIR = BASE_PATH_SCRIPTS / "logs"
os.makedirs(LOGS_BASE_DIR, exist_ok=True)

for step in range(1, 8):
    os.makedirs(LOGS_BASE_DIR / f"step{step}", exist_ok=True)

STEP0_PREP_LOG_DIR = Path(os.environ.get('STEP0_PREP_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step1")))
MEDIA_ENCODER_LOGS_DIR = Path(os.environ.get('MEDIA_ENCODER_LOGS_DIR_ENV', str(LOGS_BASE_DIR / "step2")))
SCENE_DETECT_LOG_DIR = Path(os.environ.get('SCENE_DETECT_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step3")))
AUDIO_ANALYSIS_LOG_DIR = Path(os.environ.get('AUDIO_ANALYSIS_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step4")))

BASE_TRACKING_LOG_SEARCH_PATH = Path(os.environ.get('BASE_TRACKING_LOG_SEARCH_PATH_ENV', str(BASE_PATH_SCRIPTS)))
BASE_TRACKING_PROGRESS_SEARCH_PATH = Path(os.environ.get('BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV', str(BASE_PATH_SCRIPTS)))
HF_AUTH_TOKEN_ENV = os.environ.get("HF_AUTH_TOKEN")

security_config = SecurityConfig()

RENDER_APP_CALLBACK_URL_ENV = os.environ.get("RENDER_APP_CALLBACK_URL")
RENDER_APP_CALLBACK_TOKEN_ENV = os.environ.get("RENDER_APP_CALLBACK_TOKEN")
RENDER_REGISTER_URL_ENDPOINT_ENV = os.environ.get("RENDER_REGISTER_URL_ENDPOINT")

RENDER_REGISTER_TOKEN_ENV = security_config.RENDER_REGISTER_TOKEN
INTERNAL_WORKER_COMMS_TOKEN_ENV = security_config.INTERNAL_WORKER_TOKEN

WEBHOOK_MONITOR_INTERVAL = config.WEBHOOK_MONITOR_INTERVAL
LOCAL_DOWNLOADS_DIR = config.LOCAL_DOWNLOADS_DIR
DOWNLOAD_HISTORY_FILE = config.BASE_PATH_SCRIPTS / "download_history.json"

def create_app(config_class=None):
    """
    Create and configure Flask application with modular architecture.

    Args:
        config_class: Configuration class to use (defaults to main config)

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    app.config.update({
        'SECRET_KEY': config.SECRET_KEY,
        'DEBUG': config.DEBUG,
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'SEND_FILE_MAX_AGE_DEFAULT': 0
    })

    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    try:
        config.validate()
        logger.info("Application configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")

    cache = Cache(app)

    app._cache_service_initialized = False
    app._services_initialized = False
    app._cache_instance = cache

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(workflow_bp)

    logger.info("Flask application created with modular architecture")
    return app

APP_FLASK = create_app()
APP_LOGGER = APP_FLASK.logger

with APP_FLASK.app_context():
    CACHE = APP_FLASK.extensions['cache']

KEYWORD_FILTER_TRACKING_ENV = os.environ.get('KEYWORD_FILTER_TRACKING_ENV', "Camille")
SUBDIR_FILTER_TRACKING_ENV = os.environ.get('SUBDIR_FILTER_TRACKING_ENV', "docs")

if not HF_AUTH_TOKEN_ENV:
    APP_LOGGER.warning("HF_AUTH_TOKEN environment variable not set. Step 4 (Audio Analysis) will fail if executed.")
else:
    APP_LOGGER.info("HF_AUTH_TOKEN environment variable found and will be used for Analyze Audio.")

try:
    security_config.validate_tokens()
    logger.info("Security tokens validated successfully")
    if INTERNAL_WORKER_COMMS_TOKEN_ENV:
        logger.info(f"CFG TOKEN: INTERNAL_WORKER_COMMS_TOKEN_ENV configured: '...{INTERNAL_WORKER_COMMS_TOKEN_ENV[-5:]}'")
    if RENDER_REGISTER_TOKEN_ENV:
        logger.info(f"CFG TOKEN: RENDER_REGISTER_TOKEN_ENV configured: '...{RENDER_REGISTER_TOKEN_ENV[-5:]}'")
except ValueError as e:
    logger.error(f"Security configuration error: {e}")
    logger.error("Application will continue but some endpoints will be INSECURE")

workflow_commands_config = WorkflowCommandsConfig(
    base_path=BASE_PATH_SCRIPTS,
    hf_token=HF_AUTH_TOKEN_ENV
)

workflow_state = get_workflow_state()
workflow_state.initialize_all_steps(workflow_commands_config.get_all_step_keys())



_services_initialized = False
_services_lock = threading.Lock()

def initialize_services():
    """Initialize all services with proper configuration."""
    global _services_initialized

    with _services_lock:
        if _services_initialized:
            logger.debug("Services already initialized, skipping")
            return

        try:
            with APP_FLASK.app_context():
                if not APP_FLASK._cache_service_initialized:
                    CacheService.initialize(APP_FLASK._cache_instance)
                    APP_FLASK._cache_service_initialized = True
                    logger.info("CacheService initialized")

                if not APP_FLASK._services_initialized:
                    CSVService.initialize()
                    WorkflowService.initialize(workflow_commands_config.get_config())
                    PerformanceService.start_background_monitoring()
                    APP_FLASK._services_initialized = True
                    logger.info("All services initialized successfully")

            _services_initialized = True

        except Exception as e:
            logger.error(f"Service initialization failed: {e}")

_app_initialized = False
_app_init_lock = threading.Lock()

def init_app():
    global _app_initialized

    with _app_init_lock:
        if _app_initialized:
            return APP_FLASK

        APP_LOGGER.handlers.clear()

        logs_dir = BASE_PATH_SCRIPTS / "logs"
        logs_dir.mkdir(exist_ok=True)

        log_file_path = logs_dir / "app.log"
        file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')  # 'w' mode to start fresh each time
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s [in %(pathname)s:%(lineno)d]')
        file_handler.setFormatter(file_formatter)

        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        APP_LOGGER.addHandler(file_handler)
        APP_LOGGER.addHandler(console_handler)
        APP_LOGGER.propagate = False

        is_debug_mode = os.environ.get("FLASK_DEBUG") == "1"
        APP_LOGGER.setLevel(logging.DEBUG)

        APP_LOGGER.info(f"=== COMPREHENSIVE LOGGING INITIALIZED ===")
        APP_LOGGER.info(f"Log file: {log_file_path}")
        APP_LOGGER.info(f"Debug mode: {is_debug_mode}")
        APP_LOGGER.info(f"Logger level: {APP_LOGGER.level}")
        APP_LOGGER.info(f"=== STARTING APPLICATION ===")

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        if not root_logger.handlers:
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

        APP_LOGGER.info("--- Lanceur de Workflow Démarré (Version Ubuntu) ---")

        APP_LOGGER.info("🚀🚀🚀 [STARTUP_TEST] UPDATED CODE WITH COMPREHENSIVE DEBUGGING IS RUNNING! 🚀🚀🚀")
        APP_LOGGER.info(f"🔍 [FILE_PATH_TEST] EXECUTING FROM: {__file__}")
        APP_LOGGER.info(f"🔍 [FILE_PATH_TEST] WORKING DIRECTORY: {os.getcwd()}")
        APP_LOGGER.info(f"🔍 [FILE_PATH_TEST] PYTHON EXECUTABLE: {sys.executable}")
        APP_LOGGER.info(f"BASE_PATH_SCRIPTS: {BASE_PATH_SCRIPTS}")
        APP_LOGGER.info(f"Script de tracking parallèle: {PARALLEL_TRACKING_SCRIPT_PATH}")
        APP_LOGGER.info(f"Répertoire de travail: {BASE_PATH_SCRIPTS / 'projets_extraits'}")

        os.makedirs(BASE_PATH_SCRIPTS / 'projets_extraits', exist_ok=True)

        if not HF_AUTH_TOKEN_ENV:
            APP_LOGGER.warning("HF_AUTH_TOKEN non défini. L'étape 4 (Analyse Audio) nécessitera cette variable d'environnement.")

        if not INTERNAL_WORKER_COMMS_TOKEN_ENV:
            APP_LOGGER.warning("INTERNAL_WORKER_COMMS_TOKEN non défini. API critiques INSECURES.")
        else:
            APP_LOGGER.info("INTERNAL_WORKER_COMMS_TOKEN configuré correctement.")

        if not RENDER_REGISTER_TOKEN_ENV:
            APP_LOGGER.warning("RENDER_REGISTER_TOKEN non défini. Fonctionnalités de rendu INSECURES.")
        else:
            APP_LOGGER.info("RENDER_REGISTER_TOKEN configuré correctement.")

        initialize_services()

        if not getattr(APP_FLASK, "_polling_threads_started", False):
            remote_poll_thread = threading.Thread(target=poll_remote_trigger, name="RemoteWorkflowPoller")
            remote_poll_thread.daemon = True
            remote_poll_thread.start()

            csv_monitor_thread = threading.Thread(target=csv_monitor_service, name="CSVMonitorService")
            csv_monitor_thread.daemon = True
            csv_monitor_thread.start()

            APP_FLASK._polling_threads_started = True

        APP_LOGGER.info("WEBHOOK MONITOR: Système de monitoring activé et prêt (Webhook uniquement).")

        _app_initialized = True
        return APP_FLASK

initialize_services()

REMOTE_TRIGGER_URL = os.environ.get('REMOTE_TRIGGER_URL', "https://render-signal-server.onrender.com/api/check_trigger")
REMOTE_POLLING_INTERVAL = int(os.environ.get('REMOTE_POLLING_INTERVAL', "15"))

REMOTE_SEQUENCE_STEP_KEYS = [
    "STEP1",
    "STEP2",
    "STEP3",
    "STEP4",
    "STEP5",
    "STEP6",
    "STEP7"
]

if PYNVML_AVAILABLE:
    atexit.register(pynvml.nvmlShutdown)
    print("INFO: La fonction de nettoyage pynvml.nvmlShutdown a été enregistrée pour la sortie de l'application.")
def format_duration_seconds(seconds_total: float) -> str:
    if seconds_total is None or seconds_total < 0: return "N/A"
    seconds_total = int(seconds_total)
    hours, remainder = divmod(seconds_total, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = ""
    if hours > 0: time_str += f"{hours}h "
    if minutes > 0 or hours > 0: time_str += f"{minutes}m "
    time_str += f"{seconds}s"
    return time_str.strip() if time_str else "0s"

def create_frontend_safe_config(config_dict: dict) -> dict:
    frontend_config = {}
    for step_key, step_data_orig in config_dict.items():
        frontend_step_data = {}
        for key, value in step_data_orig.items():
            if key == "progress_patterns":
                pass
            elif isinstance(value, Path):
                frontend_step_data[key] = str(value)
            elif key == "cmd" and isinstance(value, list):
                frontend_step_data[key] = [str(item) for item in value]
            elif key == "specific_logs" and isinstance(value, list):
                safe_logs = []
                for log_entry in value:
                    safe_entry = log_entry.copy()
                    if 'path' in safe_entry and isinstance(safe_entry['path'], Path):
                        safe_entry['path'] = str(safe_entry['path'])
                    safe_logs.append(safe_entry)
                frontend_step_data[key] = safe_logs
            else:
                frontend_step_data[key] = value
        frontend_config[step_key] = frontend_step_data
    return frontend_config

def execute_csv_download_worker(dropbox_url, timestamp_str, fallback_url=None, original_filename=None):
    LOCAL_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    download_id = f"csv_{uuid.uuid4().hex[:8]}"
    
    download_info = {
        'id': download_id,
        'filename': 'Détermination en cours...',
        'original_url': dropbox_url,
        'url': dropbox_url,
        'url_type': 'dropbox',
        'status': 'pending',
        'progress': 0,
        'message': 'En attente de démarrage...',
        'timestamp': datetime.now(),
        'display_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'csv_timestamp': timestamp_str
    }
    
    CSVService.add_csv_download(download_id, download_info)
    
    def progress_callback(status, progress, message):
        """Callback to update CSVService with download progress."""
        update_kwargs = {
            'progress': progress,
            'message': message,
            'display_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': datetime.now()
        }
        CSVService.update_csv_download(download_id, status, **update_kwargs)
    
    try:
        urls_to_try = [dropbox_url]
        if fallback_url and str(fallback_url).strip() and str(fallback_url).strip() != str(dropbox_url).strip():
            urls_to_try.append(str(fallback_url).strip())

        forced_name = str(original_filename).strip() if original_filename else None

        result = None
        last_attempt_url = dropbox_url
        for attempt_url in urls_to_try:
            last_attempt_url = attempt_url
            result = DownloadService.download_dropbox_file(
                url=attempt_url,
                timestamp=timestamp_str,
                output_dir=LOCAL_DOWNLOADS_DIR,
                progress_callback=progress_callback,
                forced_filename=forced_name
            )
            if result and result.success:
                break

        if result and result.success:
            CSVService.update_csv_download(
                download_id,
                'completed',
                progress=100,
                message=result.message,
                filename=result.filename,
                display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                timestamp=datetime.now()
            )
            
            try:
                CSVService.add_to_download_history_with_timestamp(dropbox_url, timestamp_str)
                if fallback_url and str(fallback_url).strip():
                    CSVService.add_to_download_history_with_timestamp(str(fallback_url).strip(), timestamp_str)
            except Exception as e:
                APP_LOGGER.error(f"Error adding to download history: {e}")
            
            APP_LOGGER.info(f"CSV DOWNLOAD: File '{result.filename}' downloaded successfully ({result.size_bytes} bytes)")
        else:
            CSVService.update_csv_download(
                download_id,
                'failed',
                message=result.message if result else 'N/A',
                filename=result.filename if (result and result.filename) else 'N/A',
                display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                timestamp=datetime.now()
            )
            APP_LOGGER.error(
                f"CSV DOWNLOAD: Failed - {(result.message if result else 'N/A')} (last_url={last_attempt_url})"
            )
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        APP_LOGGER.error(f"CSV DOWNLOAD: {error_msg}", exc_info=True)
        CSVService.update_csv_download(
            download_id,
            'failed',
            message=error_msg,
            display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            timestamp=datetime.now()
        )
    
    APP_LOGGER.info(f"CSV DOWNLOAD: Worker for {download_id} completed")

def csv_monitor_service():
    """Service de monitoring Webhook qui s'exécute en arrière-plan."""
    APP_LOGGER.info("WEBHOOK MONITOR: Service démarré.")

    from services.csv_service import CSVService

    while True:
        try:
            workflow_state.update_csv_monitor_status(
                status="checking",
                last_check=datetime.now().isoformat(),
                error=None
            )

            try:
                CSVService._check_csv_for_downloads()
                APP_LOGGER.debug("Webhook monitor check completed successfully")
            except Exception as check_error:
                APP_LOGGER.error(f"Webhook monitor check error: {check_error}")
                workflow_state.update_csv_monitor_status(
                    status="error",
                    last_check=datetime.now().isoformat(),
                    error=str(check_error)
                )
                time.sleep(WEBHOOK_MONITOR_INTERVAL)
                continue

            workflow_state.update_csv_monitor_status(
                status="active",
                last_check=datetime.now().isoformat(),
                error=None
            )

        except Exception as e:
            error_msg = f"Erreur dans le service CSV monitor: {e}"
            APP_LOGGER.error(error_msg, exc_info=True)
            workflow_state.update_csv_monitor_status(
                status="error",
                last_check=datetime.now().isoformat(),
                error=error_msg
            )

        time.sleep(WEBHOOK_MONITOR_INTERVAL)


def run_process_async(step_key: str):
    from services.workflow_service import WorkflowService
    
    APP_LOGGER.info(f"[RUN_PROCESS] Starting execution for {step_key}")

    projects_dir = os.path.join(BASE_PATH_SCRIPTS, 'projets_extraits')
    os.makedirs(projects_dir, exist_ok=True)

    config = workflow_commands_config.get_step_config(step_key)
    if not config:
        APP_LOGGER.error(f"Invalid step_key: {step_key}")
        return
    workflow_state.update_step_status(step_key, 'starting')
    workflow_state.clear_step_log(step_key)
    workflow_state.append_step_log(step_key, f"--- Lancement de: {html.escape(config['display_name'])} ---\n")
    workflow_state.update_step_info(
        step_key,
        return_code=None,
        progress_current=0,
        progress_total=0,
        progress_text='',
        start_time_epoch=time.time(),
        duration_str=None
    )


    
    cmd_str_list = [str(c) for c in config['cmd']]
    temp_json_path_for_tracking = None

    if step_key == "STEP5":
        workflow_state.append_step_log(step_key, "Préparation de l'étape de tracking : recherche des vidéos à traiter...\n")
        try:
            videos_to_process = WorkflowService.prepare_tracking_step(
                BASE_TRACKING_LOG_SEARCH_PATH,
                KEYWORD_FILTER_TRACKING_ENV,
                SUBDIR_FILTER_TRACKING_ENV
            )
            
            if not videos_to_process:
                APP_LOGGER.info(f"{step_key}: No videos require tracking, completing immediately")
                workflow_state.append_step_log(step_key, "Toutes les vidéos candidates semblent déjà traitées (aucun .mp4/.mov/... sans .json trouvé). Étape terminée.\n")
                workflow_state.update_step_info(step_key, status='completed', return_code=0)
                start_time = workflow_state.get_step_field(step_key, 'start_time_epoch')
                workflow_state.set_step_field(step_key, 'duration_str', WorkflowService.calculate_step_duration(start_time))
                return

            temp_json_path_for_tracking = WorkflowService.create_tracking_temp_file(videos_to_process)
            cmd_str_list.extend(["--videos_json_path", str(temp_json_path_for_tracking)])
            workflow_state.append_step_log(step_key, f"{len(videos_to_process)} vidéo(s) ajoutée(s) au lot de traitement.\nLe script gestionnaire va maintenant prendre le relais.\n\n")

        except Exception as e_prep:
            APP_LOGGER.error(f"{step_key}: Preparation failed - {e_prep}", exc_info=True)
            error_msg = f"Erreur lors de la préparation de l'étape de tracking: {e_prep}"
            workflow_state.append_step_log(step_key, html.escape(error_msg))
            workflow_state.update_step_info(step_key, status='failed', return_code=-1)
            return

    workflow_state.append_step_log(step_key, f"Commande: {html.escape(' '.join(cmd_str_list))}\n")
    workflow_state.append_step_log(step_key, f"Dans: {html.escape(str(config['cwd']))}\n\n")
    
    step_progress_patterns = config.get("progress_patterns", {})
    total_pattern_re = step_progress_patterns.get("total")
    current_pattern_re = step_progress_patterns.get("current")
    current_success_line_pattern_re = step_progress_patterns.get("current_success_line_pattern")
    current_item_counter = 0

    try:
        APP_LOGGER.info(f"[SUBPROCESS_DEBUG] {step_key} executing command: {cmd_str_list}")
        APP_LOGGER.info(f"[SUBPROCESS_DEBUG] {step_key} working directory: {config['cwd']}")

        process_env = os.environ.copy()
        process_env["PYTHONIOENCODING"] = "UTF-8"; process_env["PYTHONUTF8"] = "1"

        if step_key == "STEP3":
            try:
                process_env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
            except Exception as _e:
                APP_LOGGER.warning(f"Unable to set PYTORCH_CUDA_ALLOC_CONF: {_e}")

        if step_key == "STEP4":
            try:
                process_env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
                process_env["AUDIO_PARTIAL_SUCCESS_OK"] = "1"
            except Exception as _e:
                APP_LOGGER.warning(f"Unable to set PYTORCH_CUDA_ALLOC_CONF for STEP4: {_e}")

        process = subprocess.Popen(
            cmd_str_list, cwd=str(config['cwd']),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding='utf-8', errors='replace', env=process_env
        )

        APP_LOGGER.info(f"[SUBPROCESS_DEBUG] {step_key} subprocess started successfully (PID: {process.pid})")

        workflow_state.set_step_process(step_key, process)
        workflow_state.update_step_status(step_key, 'running')
        running_status_start_time = time.time()

        log_deque = workflow_state.get_step_log_deque(step_key)

        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                line_strip = line.strip()

                if line_strip.startswith("[Progression-MultiLine]"):
                    progress_data = line_strip.replace("[Progression-MultiLine]", "", 1)
                    text_progress = progress_data.replace(" || ", "\n")
                    workflow_state.set_step_field(step_key, 'progress_text', text_progress)
                    continue

                if '\r' in line or '\x1b[' in line or '\033[' in line:
                    continue

                if log_deque is not None:
                    log_deque.append(html.escape(line))
                try:
                    APP_LOGGER.debug(f"[{step_key}] SCRIPT_OUT: {line_strip}")
                except UnicodeEncodeError:
                    APP_LOGGER.debug(f"[{step_key}] SCRIPT_OUT (ascii): {line_strip.encode('ascii', 'replace').decode('ascii')}")

                if total_pattern_re:
                    total_match = total_pattern_re.search(line_strip)
                    if total_match:
                        try:
                            workflow_state.set_step_field(step_key, 'progress_total', int(total_match.group(1)))
                            files_completed = workflow_state.get_step_field(step_key, 'files_completed')
                            if files_completed is None or not isinstance(files_completed, int):
                                workflow_state.set_step_field(step_key, 'files_completed', 0)
                        except (ValueError, IndexError):
                            APP_LOGGER.warning(f"[{step_key}] ProgTotal parse error: {line_strip}")

                if current_pattern_re:
                    current_match = current_pattern_re.search(line_strip)
                    if current_match:
                        try:
                            groups = current_match.groups()

                            if len(groups) >= 3 and groups[0].isdigit() and groups[1].isdigit():
                                current_num = int(groups[0])
                                total_num = int(groups[1])
                                filename = groups[2].strip()
                                workflow_state.set_step_field(step_key, 'progress_current', current_num)
                                if workflow_state.get_step_field(step_key, 'progress_total', 0) == 0:
                                    workflow_state.set_step_field(step_key, 'progress_total', total_num)
                                if filename:
                                    workflow_state.set_step_field(step_key, 'progress_text', html.escape(filename))
                            elif len(groups) >= 1 and step_key == 'STEP3':
                                filename = groups[0].strip()
                                if filename:
                                    workflow_state.set_step_field(step_key, 'progress_text', html.escape(filename))
                                progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
                                if progress_total > 0:
                                    files_completed = int(workflow_state.get_step_field(step_key, 'files_completed', max(0, int(workflow_state.get_step_field(step_key, 'progress_current', 0)))))
                                    workflow_state.set_step_field(step_key, 'progress_current', min(progress_total, max(files_completed, 0) + 1))
                                    workflow_state.set_step_field(step_key, 'progress_current_fractional', min(float(progress_total), float(workflow_state.get_step_field(step_key, 'progress_current', 0)) - 0.0 + 0.01))
                            else:
                                filename = groups[0].strip() if len(groups) >= 1 else ""
                                percent = int(groups[1]) if len(groups) >= 2 and str(groups[1]).isdigit() else None
                                if filename:
                                    workflow_state.set_step_field(step_key, 'progress_text', html.escape(filename))
                                progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
                                if percent is not None and progress_total > 0:
                                    files_completed = int(workflow_state.get_step_field(step_key, 'files_completed', max(0, int(workflow_state.get_step_field(step_key, 'progress_current', 0)))))
                                    current_file_progress = max(0.0, min(0.99, percent / 100.0))
                                    overall_progress = (files_completed + current_file_progress)
                                    workflow_state.set_step_field(step_key, 'progress_current_fractional', max(0.0, min(float(progress_total), overall_progress)))
                        except (ValueError, IndexError):
                            APP_LOGGER.warning(f"[{step_key}] ProgCurrent parse error: {line_strip}")

                internal_pattern_re = step_progress_patterns.get("internal")
                if internal_pattern_re:
                    internal_match = internal_pattern_re.search(line_strip)
                    if internal_match:
                        try:
                            groups = internal_match.groups()

                            if len(groups) >= 4:
                                current_batch = int(groups[0])
                                total_batches = int(groups[1])
                                percent = int(groups[2])
                                filename = groups[3].strip() if groups[3] else ""
                            elif len(groups) >= 2:
                                filename = groups[0].strip() if groups[0] else ""
                                percent = int(groups[1])
                                current_batch = percent
                                total_batches = 100
                            else:
                                continue

                            progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
                            if progress_total > 0:
                                files_completed = int(workflow_state.get_step_field(step_key, 'files_completed', max(0, int(workflow_state.get_step_field(step_key, 'progress_current', 0)))))
                                current_file_progress = max(0.0, min(0.99, percent / 100.0))
                                overall_progress_files = files_completed + current_file_progress
                                overall_progress_files = max(0.0, min(float(progress_total), overall_progress_files))
                                workflow_state.set_step_field(step_key, 'progress_current_fractional', overall_progress_files)

                            if filename:
                                workflow_state.set_step_field(step_key, 'progress_text', html.escape(f"{filename} ({percent}%)"))

                        except (ValueError, IndexError):
                            APP_LOGGER.warning(f"[{step_key}] Internal progress parse error: {line_strip}")

                internal_simple_re = step_progress_patterns.get("internal_simple")
                if internal_simple_re:
                    internal_simple_match = internal_simple_re.search(line_strip)
                    if internal_simple_match:
                        try:
                            batches = int(internal_simple_match.group(1))
                            filename = internal_simple_match.group(2).strip() if internal_simple_match.group(2) else ""
                            progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
                            if progress_total > 0:
                                files_completed = int(workflow_state.get_step_field(step_key, 'files_completed', max(0, int(workflow_state.get_step_field(step_key, 'progress_current', 0)))))
                                current_file_progress = 0.01
                                overall_progress_files = files_completed + current_file_progress
                                overall_progress_files = max(0.0, min(float(progress_total), overall_progress_files))
                                workflow_state.set_step_field(step_key, 'progress_current_fractional', overall_progress_files)
                            if filename:
                                workflow_state.set_step_field(step_key, 'progress_text', html.escape(filename))
                        except Exception:
                            APP_LOGGER.warning(f"[{step_key}] Internal simple progress parse error: {line_strip}")

                if current_success_line_pattern_re:
                    success_match = current_success_line_pattern_re.search(line_strip)
                    if success_match:
                        current_item_counter += 1
                        workflow_state.set_step_field(step_key, 'progress_current', current_item_counter)
                        workflow_state.set_step_field(step_key, 'files_completed', current_item_counter)
                        workflow_state.set_step_field(step_key, 'progress_current_fractional', None)
                        if step_progress_patterns.get("current_item_text_from_success_line"):
                            try:
                                workflow_state.set_step_field(step_key, 'progress_text', html.escape(success_match.group(1).strip()))
                            except IndexError:
                                pass
            
            process.stdout.close()
        subprocess_start_time = time.time()
        process.wait()
        subprocess_duration = time.time() - subprocess_start_time

        APP_LOGGER.info(f"[SUBPROCESS_DEBUG] {step_key} subprocess completed in {subprocess_duration:.2f} seconds (return_code: {process.returncode})")

        running_status_duration = time.time() - running_status_start_time
        min_running_time = 0.6

        if running_status_duration < min_running_time:
            sleep_time = min_running_time - running_status_duration
            APP_LOGGER.info(f"[TIMING_FIX] {step_key} ensuring minimum running time: sleeping {sleep_time:.3f}s (total running time will be {min_running_time:.3f}s)")
            time.sleep(sleep_time)

        workflow_state.update_step_info(
            step_key,
            return_code=process.returncode,
            status='completed' if process.returncode == 0 else 'failed'
        )
        log_suffix = "terminé avec succès" if process.returncode == 0 else f"a échoué (code: {process.returncode})"
        workflow_state.append_step_log(step_key, f"\n--- {html.escape(config['display_name'])} {log_suffix} ---")

        status = workflow_state.get_step_status(step_key)
        progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
        progress_current = workflow_state.get_step_field(step_key, 'progress_current', 0)
        if status == 'completed' and progress_total > 0 and progress_current < progress_total:
            workflow_state.set_step_field(step_key, 'progress_current', progress_total)
        progress_text = workflow_state.get_step_field(step_key, 'progress_text', '')
        if not progress_text and status == 'completed':
            workflow_state.set_step_field(step_key, 'progress_text', "Terminé")
    except FileNotFoundError:
        APP_LOGGER.error(f"[EARLY_RETURN_DEBUG] {step_key} failing - executable not found: {cmd_str_list[0] if cmd_str_list else 'N/A'}")

        error_msg = f"Erreur: Exécutable non trouvé pour {step_key}: {cmd_str_list[0]}"
        workflow_state.append_step_log(step_key, html.escape(error_msg))
        workflow_state.update_step_info(step_key, status='failed', return_code=-1)
        APP_LOGGER.error(error_msg)
    except Exception as e:
        APP_LOGGER.error(f"[EARLY_RETURN_DEBUG] {step_key} failing - general exception: {e}")

        error_msg = f"Erreur exécution {step_key}: {str(e)}"
        workflow_state.append_step_log(step_key, html.escape(error_msg))
        workflow_state.update_step_info(step_key, status='failed', return_code=-1)
        APP_LOGGER.error(f"Exception run_process_async pour {step_key}: {e}", exc_info=True)
    finally:
        start_time = workflow_state.get_step_field(step_key, 'start_time_epoch')
        workflow_state.set_step_field(step_key, 'duration_str', WorkflowService.calculate_step_duration(start_time))
        workflow_state.set_step_process(step_key, None)
        if temp_json_path_for_tracking and temp_json_path_for_tracking.exists():
            try:
                os.remove(temp_json_path_for_tracking)
                APP_LOGGER.info(f"Fichier temporaire de tracking '{temp_json_path_for_tracking.name}' supprimé.")
            except Exception as e_clean:
                APP_LOGGER.error(f"Impossible de supprimer le fichier temporaire de tracking '{temp_json_path_for_tracking.name}': {e_clean}")


def execute_step_sequence_worker(steps_to_run_list: list, sequence_type: str ="Custom"):
    """Execute a sequence of workflow steps.
    
    This function has been migrated to use WorkflowState for sequence management.
    
    Args:
        steps_to_run_list: List of step keys to execute in order
        sequence_type: Type of sequence ('Full', 'Remote', 'Custom', etc.)
    """
    APP_LOGGER.info("🔥🔥🔥 [SEQUENCE_WORKER_TEST] UPDATED SEQUENCE WORKER WITH DEBUGGING IS RUNNING! 🔥🔥🔥")
    
    if sequence_type != "InternalPollingCheck" and workflow_state.is_sequence_running():
        APP_LOGGER.warning(f"{sequence_type.upper()} SEQUENCE: Tentative de lancement alors qu'une séquence est déjà en cours.")
        return
    
    if not workflow_state.start_sequence(sequence_type):
        APP_LOGGER.warning(f"{sequence_type.upper()} SEQUENCE: Could not start - already running")
        return
    
    APP_LOGGER.info(f"{sequence_type.upper()} SEQUENCE: Séquence démarrée.")
    all_steps_succeeded = True; sequence_summary_data = []
    try:
        APP_LOGGER.info(f"{sequence_type.upper()} SEQUENCE: Thread démarré pour {len(steps_to_run_list)} étapes: {steps_to_run_list}")

        APP_LOGGER.info(f"[CACHE_CLEAR_TEST] *** UPDATED CODE IS RUNNING - CACHE CLEARED SUCCESSFULLY ***")
        for i, step_key in enumerate(steps_to_run_list):
            step_config = workflow_commands_config.get_step_config(step_key)
            if not step_config:
                APP_LOGGER.error(f"{sequence_type.upper()} SEQUENCE: Clé invalide '{step_key}'. Interruption.")
                all_steps_succeeded = False; sequence_summary_data.append({"name": f"Étape Invalide ({html.escape(step_key)})", "status": "Erreur de config", "duration": "0s", "success": False}); break
            step_display_name = step_config['display_name']
            APP_LOGGER.info(f"{sequence_type.upper()} SEQUENCE: Lancement étape {i+1}/{len(steps_to_run_list)}: '{step_display_name}' ({step_key})")
            
            workflow_state.update_step_info(
                step_key,
                status='idle',
                progress_current=0,
                progress_total=0,
                progress_text='',
                start_time_epoch=None,
                duration_str=None
            )

            current_status = workflow_state.get_step_status(step_key)

            try:
                run_process_async(step_key)
                final_status = workflow_state.get_step_status(step_key)
                return_code = workflow_state.get_step_field(step_key, 'return_code')
                APP_LOGGER.info(f"[SEQUENCE_DEBUG] run_process_async completed for {step_key} (final status: {final_status}, return_code: {return_code})")
            except Exception as e:
                APP_LOGGER.error(f"[SEQUENCE_DEBUG] Exception in run_process_async for {step_key}: {e}", exc_info=True)
                workflow_state.update_step_info(step_key, status='failed', return_code=-1)
            
            step_info = workflow_state.get_step_info(step_key)
            duration_str_step = step_info.get('duration_str', 'N/A')
            if step_info['status'] == 'completed':
                sequence_summary_data.append({"name": html.escape(step_display_name), "status": "Réussie", "duration": duration_str_step, "success": True})
            else:
                all_steps_succeeded = False
                sequence_summary_data.append({"name": html.escape(step_display_name), "status": f"Échouée ({step_info['status']})", "duration": duration_str_step, "success": False})
                APP_LOGGER.error(f"{sequence_type.upper()} SEQUENCE: Étape '{html.escape(step_display_name)}' Échouée. Interruption.")
                break 
        final_overall_status_text = "Terminée avec succès" if all_steps_succeeded else "Terminée avec erreurs"
        summary_log = [f"{s['name']}: {s['status']} ({s['duration']})" for s in sequence_summary_data]
        full_summary_log_text = f"Séquence {sequence_type} {final_overall_status_text}. Détails: " + " | ".join(summary_log)
        APP_LOGGER.info(f"{sequence_type.upper()} SEQUENCE: {full_summary_log_text}")
        
        workflow_state.complete_sequence(success=all_steps_succeeded, message=full_summary_log_text, sequence_type=sequence_type)
    except Exception as e_seq:
        APP_LOGGER.error(f"{sequence_type.upper()} SEQUENCE: Erreur inattendue dans le worker de séquence: {e_seq}", exc_info=True)
        all_steps_succeeded = False
        workflow_state.complete_sequence(success=False, message=f"Erreur critique durant la séquence: {e_seq}", sequence_type=sequence_type)
    finally:
        if workflow_state.is_sequence_running():
            workflow_state.complete_sequence(success=False, message="Séquence terminée de façon inattendue", sequence_type=sequence_type)
        APP_LOGGER.info(f"{sequence_type.upper()} SEQUENCE: Séquence terminée.")

def run_full_sequence_from_remote():
    """Launch full sequence from remote trigger.
    
    Migrated to use WorkflowState for sequence management.
    """
    APP_LOGGER.info("REMOTE TRIGGER: Demande de lancement de la séquence complète reçue.")
    
    if workflow_state.is_sequence_running():
        APP_LOGGER.warning("REMOTE TRIGGER: Séquence complète non lancée, une autre séquence est déjà en cours.")
        return
    
    seq_thread = threading.Thread(target=execute_step_sequence_worker, args=(list(REMOTE_SEQUENCE_STEP_KEYS), "Remote"))
    seq_thread.daemon = True
    seq_thread.start()

def poll_remote_trigger():
    """Poll remote trigger URL for pending commands.
    
    Migrated to use WorkflowState for sequence status checking.
    """
    APP_LOGGER.info(f"REMOTE POLLER: Démarré. Interrogation de {REMOTE_TRIGGER_URL} toutes les {REMOTE_POLLING_INTERVAL}s.")
    
    while True:
        time.sleep(REMOTE_POLLING_INTERVAL)
        
        if workflow_state.is_sequence_running():
            APP_LOGGER.debug("REMOTE POLLER: Une séquence est marquée comme en cours, attente.")
            continue
        
        if workflow_state.is_any_step_running():
            APP_LOGGER.debug("REMOTE POLLER: Une étape individuelle est active. Attente.")
            continue
        
        try:
            APP_LOGGER.debug(f"REMOTE POLLER: Vérification de {REMOTE_TRIGGER_URL}.")
            response = requests.get(REMOTE_TRIGGER_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('command_pending'):
                APP_LOGGER.info(f"REMOTE POLLER: Commande reçue! Payload: {data.get('payload')}")
                
                if not workflow_state.is_sequence_running():
                    run_full_sequence_from_remote()
                else:
                    APP_LOGGER.warning("REMOTE POLLER: Signal reçu, mais une séquence est déjà en cours.")
            else:
                APP_LOGGER.debug("REMOTE POLLER: Aucune commande en attente.")
        except requests.exceptions.RequestException as e:
            APP_LOGGER.warning(f"REMOTE POLLER: Erreur communication {REMOTE_TRIGGER_URL}: {e}")
        except Exception as e_poll:
            APP_LOGGER.error(f"REMOTE POLLER: Erreur inattendue: {e_poll}", exc_info=True)

@APP_FLASK.route('/test-slideshow-fixes')
def test_slideshow_fixes():
    """Serve the slideshow fixes test page."""
    APP_LOGGER.debug("Serving slideshow fixes test page")

    try:
        with open('test_dom_slideshow_fixes.html', 'r', encoding='utf-8') as f:
            test_content = f.read()

        return test_content, 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        APP_LOGGER.error(f"Error serving test page: {e}")
        return f"Error loading test page: {e}", 500

@APP_FLASK.route('/favicon.ico')
def favicon():
    """
    Handle favicon.ico requests to prevent 404 errors in browser console.
    Returns a 204 No Content response since we don't have a favicon file.
    """
    APP_LOGGER.debug("Favicon requested - returning 204 No Content")
    return '', 204

def get_current_workflow_status_summary():
    """Get comprehensive workflow status summary including CSV downloads.
    
    Migrated to use WorkflowState for all state access.
    """
    overall_status_code_val = "idle"
    overall_status_text_display_val = "Prêt et en attente."
    current_step_name_val = None
    progress_current_val = 0
    progress_total_val = 0
    active_step_key_found = None
    
    is_sequence_globally_active = workflow_state.is_sequence_running()
    
    if is_sequence_globally_active:
        sequence_outcome = workflow_state.get_sequence_outcome()
        active_sequence_type = sequence_outcome.get("type", "Inconnue") if sequence_outcome.get("status", "").startswith("running_") else "Inconnue"
        
        for step_key_seq in REMOTE_SEQUENCE_STEP_KEYS:
            step_status = workflow_state.get_step_status(step_key_seq)
            if step_status in ['running', 'starting']:
                active_step_key_found = step_key_seq
                overall_status_code_val = f"sequence_running_{active_sequence_type.lower()}"
                break
    
    if not active_step_key_found:
        all_steps_info = workflow_state.get_all_steps_info()
        for step_key_ind, info_ind in all_steps_info.items():
            if info_ind['status'] in ['running', 'starting']:
                active_step_key_found = step_key_ind
                overall_status_code_val = f"step_running_{step_key_ind}"
                break
    
    if active_step_key_found:
        active_step_info = workflow_state.get_step_info(active_step_key_found)
        active_step_config = workflow_commands_config.get_step_config(active_step_key_found)
        current_step_name_val = active_step_config['display_name'] if active_step_config else 'Étape inconnue'
        progress_current_val = active_step_info['progress_current']
        progress_total_val = active_step_info['progress_total']
        
        if overall_status_code_val.startswith("sequence_running"):
            seq_type_disp = overall_status_code_val.split("_")[-1].capitalize()
            overall_status_text_display_val = f"Séquence {seq_type_disp} - En cours: {current_step_name_val}"
        elif overall_status_code_val.startswith("step_running"):
            overall_status_text_display_val = f"En cours: {current_step_name_val}"
    else:
        sequence_outcome = workflow_state.get_sequence_outcome()
        if sequence_outcome and sequence_outcome.get("timestamp"):
            last_seq_time_str = sequence_outcome["timestamp"]
            if last_seq_time_str.endswith('Z'):
                last_seq_time_str = last_seq_time_str[:-1] + '+00:00'
            try:
                last_seq_dt = datetime.fromisoformat(last_seq_time_str)
                if last_seq_dt.tzinfo is None:
                    last_seq_dt = last_seq_dt.replace(tzinfo=timezone.utc)
                time_since_last_seq = datetime.now(timezone.utc) - last_seq_dt
                
                if time_since_last_seq < timedelta(hours=1):
                    seq_type_display = sequence_outcome.get('type', 'N/A')
                    if sequence_outcome.get("status") == "success":
                        overall_status_code_val = "completed_success_recent"
                        overall_status_text_display_val = f"Terminé avec succès (Séquence {seq_type_display})"
                        current_step_name_val = sequence_outcome.get("message", "Détails non disponibles.")
                    elif sequence_outcome.get("status") == "error":
                        overall_status_code_val = "completed_error_recent"
                        overall_status_text_display_val = f"Terminé avec erreur(s) (Séquence {seq_type_display})"
                        current_step_name_val = sequence_outcome.get("message", "Détails non disponibles.")
                    elif sequence_outcome.get("status", "").startswith("running_"):
                        seq_type_running = sequence_outcome.get("type", "N/A")
                        overall_status_code_val = f"sequence_starting_{seq_type_running.lower()}"
                        overall_status_text_display_val = f"Démarrage Séquence {seq_type_running}..."
                else:
                    overall_status_code_val = "idle_after_completion"
                    overall_status_text_display_val = "Prêt (dernière opération terminée il y a >1h)."
            except ValueError as e_ts:
                APP_LOGGER.warning(f"Error parsing sequence outcome timestamp '{sequence_outcome['timestamp']}': {e_ts}")
                overall_status_code_val = "idle_parse_error"
                overall_status_text_display_val = "Prêt (erreur parsing dernier statut)."
        else:
            overall_status_code_val = "idle_initial"
            overall_status_text_display_val = "Prêt et en attente (jamais exécuté)."

    active_list_csv = workflow_state.get_active_csv_downloads_list()
    kept_list_csv = workflow_state.get_kept_csv_downloads_list()

    all_csv_downloads_intermediate = active_list_csv + kept_list_csv
    all_csv_downloads_intermediate.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)

    recent_downloads_summary_val = []
    for item_csv in all_csv_downloads_intermediate[:5]:
        recent_downloads_summary_val.append({
            "filename": item_csv.get('filename', 'N/A'),
            "status": item_csv.get('status', 'N/A'),
            "timestamp": item_csv.get('display_timestamp', 'N/A'),
            "csv_timestamp": item_csv.get('csv_timestamp', 'N/A')
        })
    status_text_detail_val = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    return {
        "overall_status_code": overall_status_code_val,
        "overall_status_text_display": overall_status_text_display_val,
        "current_step_name": current_step_name_val,
        "status_text_detail": status_text_detail_val,
        "progress_current": progress_current_val,
        "progress_total": progress_total_val,
        "recent_downloads": recent_downloads_summary_val,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "last_sequence_summary": workflow_state.get_sequence_outcome()
    }


if __name__ == '__main__':
    init_app()

    APP_FLASK.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        threaded=True,
        use_reloader=False
    )