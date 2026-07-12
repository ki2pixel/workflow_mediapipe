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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import psutil
import requests
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_caching import Cache

try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Dotenv configuration loaded")
except ImportError:
    logger.warning("python-dotenv not available; relying on environment variables only")

from config.settings import config
from config.security import SecurityConfig, require_internal_worker_token
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
from services.csv_downloader import execute_csv_download_worker
from services.csv_monitor import csv_monitor_service
from services.cleanup_monitor import orphan_cleanup_service
from services.workflow_executor import run_process_async
import urllib.parse

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available; Excel files cannot be processed")

BASE_PATH_SCRIPTS = config.BASE_PATH_SCRIPTS
PYTHON_VENV_EXE = config.PYTHON_VENV_EXE

PARALLEL_TRACKING_SCRIPT_PATH = BASE_PATH_SCRIPTS / "workflow_scripts" / "step5" / "run_tracking_manager.py"

LOGS_BASE_DIR = BASE_PATH_SCRIPTS / "logs"
os.makedirs(LOGS_BASE_DIR, exist_ok=True)

for step in range(1, 9):
    os.makedirs(LOGS_BASE_DIR / f"step{step}", exist_ok=True)

STEP0_PREP_LOG_DIR = Path(os.environ.get('STEP0_PREP_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step1")))
MEDIA_ENCODER_LOGS_DIR = Path(os.environ.get('MEDIA_ENCODER_LOGS_DIR_ENV', str(LOGS_BASE_DIR / "step2")))
SCENE_DETECT_LOG_DIR = Path(os.environ.get('SCENE_DETECT_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step3")))
AUDIO_ANALYSIS_LOG_DIR = Path(os.environ.get('AUDIO_ANALYSIS_LOG_DIR_ENV', str(LOGS_BASE_DIR / "step4")))

BASE_TRACKING_LOG_SEARCH_PATH = Path(os.environ.get('BASE_TRACKING_LOG_SEARCH_PATH_ENV', str(BASE_PATH_SCRIPTS)))
BASE_TRACKING_PROGRESS_SEARCH_PATH = Path(os.environ.get('BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV', str(BASE_PATH_SCRIPTS)))
HF_AUTH_TOKEN_ENV = os.environ.get("HF_AUTH_TOKEN")

security_config = SecurityConfig()


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
        logger.critical(f"CRITICAL: Configuration validation failed: {e}")
        if not config.DEBUG:
            logger.critical("FATAL: Application cannot start in production with invalid configuration!")
            import sys
            sys.exit(1)

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



if not HF_AUTH_TOKEN_ENV:
    APP_LOGGER.warning("HF_AUTH_TOKEN environment variable not set. Step 4 (Audio Analysis) will fail if executed.")
else:
    APP_LOGGER.info("HF_AUTH_TOKEN environment variable found and will be used for Analyze Audio.")

try:
    is_strict = not config.DEBUG
    security_config.validate_tokens(strict=is_strict)
    logger.info("Security tokens validated successfully")
    if INTERNAL_WORKER_COMMS_TOKEN_ENV:
        logger.info(f"CFG TOKEN: INTERNAL_WORKER_COMMS_TOKEN_ENV configured: '...{INTERNAL_WORKER_COMMS_TOKEN_ENV[-5:]}'")

except ValueError as e:
    logger.critical(f"Security configuration error: {e}")
    if not config.DEBUG:
        logger.critical("CRITICAL: Application cannot start in production mode with insecure or missing tokens!")
        sys.exit(1)
    else:
        logger.error("Application will continue in development mode, but some endpoints will be INSECURE")

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
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            mode='a',
            encoding='utf-8'
        )
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

        APP_LOGGER.info("Workflow launcher initialized (Ubuntu profile)")

        os.makedirs(BASE_PATH_SCRIPTS / 'projets_extraits', exist_ok=True)

        if not HF_AUTH_TOKEN_ENV:
            APP_LOGGER.warning("HF_AUTH_TOKEN non défini. L'étape 4 (Analyse Audio) nécessitera cette variable d'environnement.")

        if not INTERNAL_WORKER_COMMS_TOKEN_ENV:
            APP_LOGGER.warning("INTERNAL_WORKER_COMMS_TOKEN non défini. API critiques INSECURES.")
        else:
            APP_LOGGER.info("INTERNAL_WORKER_COMMS_TOKEN configuré correctement.")



        initialize_services()

        if not getattr(APP_FLASK, "_polling_threads_started", False):
            from services.csv_monitor import stop_csv_monitor
            from services.cleanup_monitor import stop_cleanup_monitor
            atexit.register(stop_csv_monitor)
            atexit.register(stop_cleanup_monitor)

            csv_monitor_thread = threading.Thread(target=csv_monitor_service, name="CSVMonitorService")
            csv_monitor_thread.daemon = True
            csv_monitor_thread.start()

            cleanup_thread = threading.Thread(target=orphan_cleanup_service, name="OrphanCleanupService")
            cleanup_thread.daemon = True
            cleanup_thread.start()

            APP_FLASK._polling_threads_started = True

        APP_LOGGER.info("WEBHOOK MONITOR: Système de monitoring activé et prêt (Webhook uniquement).")

        _app_initialized = True
        return APP_FLASK

initialize_services()




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




if __name__ == '__main__':
    init_app()

    APP_FLASK.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        threaded=True,
        use_reloader=False
    )