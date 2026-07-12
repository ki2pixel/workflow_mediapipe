#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Process Executor Service
Handles running step scripts as subprocesses asynchronously,
redirecting output to step-specific log files, and parsing real-time progress.
"""

import os
import time
import html
import subprocess
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import config
from config.workflow_commands import WorkflowCommandsConfig
from services.workflow_service import WorkflowService
from services.workflow_state import get_workflow_state
from services.types import StepKey, StepStatus

logger = logging.getLogger(__name__)

# Constants
BASE_PATH_SCRIPTS = config.BASE_PATH_SCRIPTS
BASE_TRACKING_LOG_SEARCH_PATH = Path(os.environ.get('BASE_TRACKING_LOG_SEARCH_PATH_ENV', str(BASE_PATH_SCRIPTS)))

# Initialize config
workflow_commands_config = WorkflowCommandsConfig(
    base_path=BASE_PATH_SCRIPTS,
    hf_token=os.environ.get("HF_AUTH_TOKEN")
)

def parse_and_update_progress(line: str, step_key: str, step_progress_patterns: dict, state_vars: dict) -> None:
    """Helper to parse a single line of output and update step progress in WorkflowState."""
    line_strip = line.strip()
    workflow_state = get_workflow_state()

    if line_strip.startswith("[Progression-MultiLine]"):
        progress_data = line_strip.replace("[Progression-MultiLine]", "", 1)
        text_progress = progress_data.replace(" || ", "\n")
        workflow_state.set_step_field(step_key, 'progress_text', text_progress)
        return

    if '\r' in line or '\x1b[' in line or '\033[' in line:
        return

    # Add to in-memory log deque
    log_deque = workflow_state.get_step_log_deque(step_key)
    if log_deque is not None:
        log_deque.append(html.escape(line))
        
    try:
        logger.debug(f"[{step_key}] SCRIPT_OUT: {line_strip}")
    except UnicodeEncodeError:
        logger.debug(f"[{step_key}] SCRIPT_OUT (ascii): {line_strip.encode('ascii', 'replace').decode('ascii')}")

    total_pattern_re = step_progress_patterns.get("total")
    current_pattern_re = step_progress_patterns.get("current")
    current_success_line_pattern_re = step_progress_patterns.get("current_success_line_pattern")
    current_failure_line_pattern_re = step_progress_patterns.get("current_failure_line_pattern")

    if total_pattern_re:
        total_match = total_pattern_re.search(line_strip)
        if total_match:
            try:
                workflow_state.set_step_field(step_key, 'progress_total', int(total_match.group(1)))
                files_completed = workflow_state.get_step_field(step_key, 'files_completed')
                if files_completed is None or not isinstance(files_completed, int):
                    workflow_state.set_step_field(step_key, 'files_completed', 0)
            except (ValueError, IndexError):
                logger.warning(f"[{step_key}] ProgTotal parse error: {line_strip}")

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
                elif len(groups) >= 1 and step_key in (StepKey.STEP3.value, StepKey.STEP4.value, StepKey.STEP5.value):
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
                logger.warning(f"[{step_key}] ProgCurrent parse error: {line_strip}")

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
                    return

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
                logger.warning(f"[{step_key}] Internal progress parse error: {line_strip}")

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
                logger.warning(f"[{step_key}] Internal simple progress parse error: {line_strip}")

    item_finished = False
    finished_name = ""
    if current_success_line_pattern_re:
        success_match = current_success_line_pattern_re.search(line_strip)
        if success_match:
            item_finished = True
            try:
                finished_name = success_match.group(1).strip()
            except IndexError:
                pass
    if not item_finished and current_failure_line_pattern_re:
        failure_match = current_failure_line_pattern_re.search(line_strip)
        if failure_match:
            item_finished = True
            try:
                finished_name = failure_match.group(1).strip()
            except IndexError:
                pass

    if item_finished:
        state_vars["current_item_counter"] += 1
        workflow_state.set_step_field(step_key, 'progress_current', state_vars["current_item_counter"])
        workflow_state.set_step_field(step_key, 'files_completed', state_vars["current_item_counter"])
        workflow_state.set_step_field(step_key, 'progress_current_fractional', None)
        if step_progress_patterns.get("current_item_text_from_success_line") and finished_name:
            workflow_state.set_step_field(step_key, 'progress_text', html.escape(finished_name))


def tail_log_and_parse_progress(log_path: Path, step_key: str, process: subprocess.Popen, step_progress_patterns: dict, state_vars: dict) -> None:
    """Tails the step log file and parses its progress in real-time."""
    time.sleep(0.1)  # Allow process to start writing
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            while True:
                line = f.readline()
                if not line:
                    if process.poll() is not None:
                        # Process finished, read remaining lines
                        for trailing_line in f.readlines():
                            parse_and_update_progress(trailing_line, step_key, step_progress_patterns, state_vars)
                        break
                    time.sleep(0.1)
                    continue
                parse_and_update_progress(line, step_key, step_progress_patterns, state_vars)
    except Exception as e:
        logger.error(f"Error in tailing thread for {step_key}: {e}", exc_info=True)


def _run_process_async_internal(step_key: str):
    """Executes a step script as a subprocess, redirects to log file, and starts a tailing thread."""
    workflow_state = get_workflow_state()
    logger.info(f"[RUN_PROCESS] Starting execution for {step_key}")

    projects_dir = os.path.join(BASE_PATH_SCRIPTS, 'projets_extraits')
    os.makedirs(projects_dir, exist_ok=True)

    step_config = workflow_commands_config.get_step_config(step_key)
    if not step_config:
        logger.error(f"Invalid step_key: {step_key}")
        return
        
    workflow_state.update_step_status(step_key, StepStatus.STARTING.value)
    workflow_state.clear_step_log(step_key)
    workflow_state.append_step_log(step_key, f"--- Lancement de: {html.escape(step_config['display_name'])} ---\n")
    workflow_state.update_step_info(
        step_key,
        return_code=None,
        progress_current=0,
        progress_total=0,
        progress_text='',
        start_time_epoch=time.time(),
        duration_str=None
    )

    cmd_str_list = [str(c) for c in step_config['cmd']]
    temp_json_path_for_tracking = None

    if step_key == StepKey.STEP5.value:
        workflow_state.append_step_log(step_key, "Préparation de l'étape de tracking : recherche des vidéos à traiter...\n")
        try:
            videos_to_process = WorkflowService.prepare_tracking_step(
                BASE_TRACKING_LOG_SEARCH_PATH,
                config.FOLDER_KEYWORD,
                config.SUBFOLDER_NAME
            )
            
            if not videos_to_process:
                logger.info(f"{step_key}: No videos require tracking, completing immediately")
                workflow_state.append_step_log(step_key, "Toutes les vidéos candidates semblent déjà traitées (aucun .mp4/.mov/... sans .json trouvé). Étape terminée.\n")
                workflow_state.update_step_info(step_key, status=StepStatus.COMPLETED.value, return_code=0)
                start_time = workflow_state.get_step_field(step_key, 'start_time_epoch')
                workflow_state.set_step_field(step_key, 'duration_str', WorkflowService.calculate_step_duration(start_time))
                return

            temp_json_path_for_tracking = WorkflowService.create_tracking_temp_file(videos_to_process)
            cmd_str_list.extend(["--videos_json_path", str(temp_json_path_for_tracking)])
            workflow_state.append_step_log(step_key, f"{len(videos_to_process)} vidéo(s) ajoutée(s) au lot de traitement.\nLe script gestionnaire va maintenant prendre le relais.\n\n")

        except Exception as e_prep:
            logger.error(f"{step_key}: Preparation failed - {e_prep}", exc_info=True)
            error_msg = f"Erreur lors de la préparation de l'étape de tracking: {e_prep}"
            workflow_state.append_step_log(step_key, html.escape(error_msg))
            workflow_state.update_step_info(step_key, status=StepStatus.FAILED.value, return_code=-1)
            return

    workflow_state.append_step_log(step_key, f"Commande: {html.escape(' '.join(cmd_str_list))}\n")
    workflow_state.append_step_log(step_key, f"Dans: {html.escape(str(step_config['cwd']))}\n\n")
    
    step_progress_patterns = step_config.get("progress_patterns", {})
    state_vars = {"current_item_counter": 0}

    # Prepare log path (absolute path via config.LOGS_DIR)
    log_dir = Path(config.LOGS_DIR)
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / f"step_{step_key}.log"

    # Manual log file rotation if size exceeds 5MB
    if log_file_path.exists() and log_file_path.stat().st_size > 5 * 1024 * 1024:
        try:
            max_backups = 5
            for i in range(max_backups - 1, 0, -1):
                src = log_file_path.with_suffix(f".log.{i}")
                dst = log_file_path.with_suffix(f".log.{i+1}")
                if src.exists():
                    src.replace(dst)
            log_file_path.replace(log_file_path.with_suffix(".log.1"))
            logger.info(f"[{step_key}] Rotated step log file.")
        except Exception as e_rot:
            logger.warning(f"[{step_key}] Failed to rotate log file: {e_rot}")

    try:
        logger.info(f"[SUBPROCESS_DEBUG] {step_key} executing command: {cmd_str_list}")
        logger.info(f"[SUBPROCESS_DEBUG] {step_key} working directory: {step_config['cwd']}")

        process_env = os.environ.copy()
        process_env["PYTHONIOENCODING"] = "UTF-8"; process_env["PYTHONUTF8"] = "1"
        process_env["PYTHONUNBUFFERED"] = "1"

        # Inject standard project environment variables into subprocess env
        process_env.setdefault("ROOT_SCAN_DIR", str(config.PROJECTS_DIR))
        process_env.setdefault("FOLDER_KEYWORD", config.FOLDER_KEYWORD)
        process_env.setdefault("SUBFOLDER_NAME", config.SUBFOLDER_NAME)
        process_env.setdefault("TRACKING_DISABLE_GPU", "1" if config.TRACKING_DISABLE_GPU else "0")
        process_env.setdefault("TRACKING_CPU_WORKERS", str(config.TRACKING_CPU_WORKERS))

        try:
            coral_lib_path = os.path.join(str(BASE_PATH_SCRIPTS), "coral_env", "lib")
            current_ld = process_env.get("LD_LIBRARY_PATH", "")
            ld_paths = [coral_lib_path]
            if current_ld:
                ld_paths.append(current_ld)

            # Détection et injection dynamique des répertoires nvidia/*/lib du venv de l'étape
            if cmd_str_list:
                try:
                    step_python = cmd_str_list[0]
                    venv_root = Path(step_python).parent.parent
                    venv_site_packages = venv_root / "lib" / "python3.10" / "site-packages"
                    if not venv_site_packages.exists():
                        lib_dir = venv_root / "lib"
                        if lib_dir.exists():
                            py_dirs = list(lib_dir.glob("python3.*"))
                            if py_dirs:
                                venv_site_packages = py_dirs[0] / "site-packages"
                    
                    if venv_site_packages.exists():
                        nvidia_dirs = list(venv_site_packages.glob("nvidia/*/lib"))
                        for d in nvidia_dirs:
                            ld_paths.insert(0, str(d))
                        logger.info(f"[{step_key}] LD_LIBRARY_PATH enrichi avec les packages nvidia du venv: {len(nvidia_dirs)} répertoires ajoutés.")
                except Exception as e_ld:
                    logger.warning(f"[{step_key}] Échec de la détection des librairies nvidia du venv: {e_ld}")

            process_env["LD_LIBRARY_PATH"] = ":".join(ld_paths)

        except Exception as _e:
            logger.warning(f"Unable to set LD_LIBRARY_PATH: {_e}")

        if step_key == StepKey.STEP3.value:
            try:
                process_env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
            except Exception as _e:
                logger.warning(f"Unable to set PYTORCH_CUDA_ALLOC_CONF: {_e}")

        if step_key == StepKey.STEP4.value:
            try:
                process_env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
                process_env["AUDIO_PARTIAL_SUCCESS_OK"] = "1"
                process_env["AUDIO_GPU_ISOLATION"] = os.environ.get("AUDIO_GPU_ISOLATION", "1")
            except Exception as _e:
                logger.warning(f"Unable to set PYTORCH_CUDA_ALLOC_CONF for STEP4: {_e}")

        # Open log file to redirect output in append mode 'a'
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                cmd_str_list, cwd=str(step_config['cwd']),
                stdout=log_file, stderr=subprocess.STDOUT,
                text=True, env=process_env
            )

            logger.info(f"[SUBPROCESS_DEBUG] {step_key} subprocess started successfully (PID: {process.pid})")

            workflow_state.set_step_process(step_key, process)
            workflow_state.update_step_status(step_key, StepStatus.RUNNING.value)
            running_status_start_time = time.time()

            # Start background tail thread to read log file and update progress in real time
            tail_thread = threading.Thread(
                target=tail_log_and_parse_progress,
                args=(log_file_path, step_key, process, step_progress_patterns, state_vars),
                name=f"Tailing-step-{step_key}"
            )
            tail_thread.daemon = True
            tail_thread.start()

            # Wait for subprocess to complete with timeout
            subprocess_start_time = time.time()
            timeout = step_config.get("timeout") or getattr(config, "SUBPROCESS_TIMEOUT", 1800)
            try:
                process.wait(timeout=timeout)
                subprocess_duration = time.time() - subprocess_start_time
                logger.info(f"[SUBPROCESS_DEBUG] {step_key} subprocess completed in {subprocess_duration:.2f} seconds (return_code: {process.returncode})")
            except subprocess.TimeoutExpired:
                logger.error(f"[{step_key}] Subprocess exceeded timeout of {timeout}s. Terminating process...")
                workflow_state.append_step_log(step_key, f"\n⚠️ ERREUR : Le script a dépassé le délai maximum de {timeout} secondes.\nArrêt forcé en cours...\n")
                process.terminate()
                try:
                    process.wait(timeout=5)
                    logger.info(f"[{step_key}] Subprocess terminated successfully after terminate()")
                except subprocess.TimeoutExpired:
                    logger.warning(f"[{step_key}] Subprocess did not terminate after 5s. Killing...")
                    process.kill()
                    process.wait()  # reap zombie
                    logger.info(f"[{step_key}] Subprocess killed successfully")
                
                workflow_state.update_step_info(
                    step_key,
                    return_code=-9,
                    status=StepStatus.FAILED.value
                )
                return

        running_status_duration = time.time() - running_status_start_time
        min_running_time = 0.6

        if running_status_duration < min_running_time:
            sleep_time = min_running_time - running_status_duration
            logger.info(f"[TIMING_FIX] {step_key} ensuring minimum running time: sleeping {sleep_time:.3f}s (total running time will be {min_running_time:.3f}s)")
            time.sleep(sleep_time)

        workflow_state.update_step_info(
            step_key,
            return_code=process.returncode,
            status=StepStatus.COMPLETED.value if process.returncode == 0 else StepStatus.FAILED.value
        )
        log_suffix = "terminé avec succès" if process.returncode == 0 else f"a échoué (code: {process.returncode})"
        workflow_state.append_step_log(step_key, f"\n--- {html.escape(step_config['display_name'])} {log_suffix} ---")

        status = workflow_state.get_step_status(step_key)
        progress_total = workflow_state.get_step_field(step_key, 'progress_total', 0)
        progress_current = workflow_state.get_step_field(step_key, 'progress_current', 0)
        if status == StepStatus.COMPLETED.value and progress_total > 0 and progress_current < progress_total:
            workflow_state.set_step_field(step_key, 'progress_current', progress_total)
        progress_text = workflow_state.get_step_field(step_key, 'progress_text', '')
        if not progress_text and status == StepStatus.COMPLETED.value:
            workflow_state.set_step_field(step_key, 'progress_text', "Terminé")
            
    except FileNotFoundError:
        logger.error(f"[EARLY_RETURN_DEBUG] {step_key} failing - executable not found: {cmd_str_list[0] if cmd_str_list else 'N/A'}")

        error_msg = f"Erreur: Exécutable non trouvé pour {step_key}: {cmd_str_list[0]}"
        workflow_state.append_step_log(step_key, html.escape(error_msg))
        workflow_state.update_step_info(step_key, status=StepStatus.FAILED.value, return_code=-1)
        logger.error(error_msg)
    except Exception as e:
        logger.error(f"[EARLY_RETURN_DEBUG] {step_key} failing - general exception: {e}")

        error_msg = f"Erreur exécution {step_key}: {str(e)}"
        workflow_state.append_step_log(step_key, html.escape(error_msg))
        workflow_state.update_step_info(step_key, status=StepStatus.FAILED.value, return_code=-1)
        logger.error(f"Exception run_process_async pour {step_key}: {e}", exc_info=True)
    finally:
        start_time = workflow_state.get_step_field(step_key, 'start_time_epoch')
        workflow_state.set_step_field(step_key, 'duration_str', WorkflowService.calculate_step_duration(start_time))
        workflow_state.set_step_process(step_key, None)
        if temp_json_path_for_tracking and temp_json_path_for_tracking.exists():
            try:
                os.remove(temp_json_path_for_tracking)
                logger.info(f"Fichier temporaire de tracking '{temp_json_path_for_tracking.name}' supprimé.")
            except Exception as e_clean:
                logger.error(f"Impossible de supprimer le fichier temporaire de tracking '{temp_json_path_for_tracking.name}': {e_clean}")


def run_process_async(step_key: str):
    """
    Point d'entrée pour exécuter une étape. Si le Coral TPU est activé, 
    les requêtes d'inférence (STEP3, 4, 5) sont envoyées à l'orchestrateur de queue asynchrone 
    pour un traitement par micro-lots (protection de la SRAM 8Mo).
    """
    is_tpu_step = False
    if step_key == StepKey.STEP3.value:
        is_tpu_step = config.ENABLE_CORAL_TPU_ACCELERATION and getattr(config, "STEP3_ENABLE_CORAL_TPU", True)
    elif step_key == StepKey.STEP4.value:
        is_tpu_step = config.ENABLE_CORAL_TPU_ACCELERATION and getattr(config, "STEP4_ENABLE_CORAL_TPU", True)
    elif step_key == StepKey.STEP5.value:
        is_tpu_step = config.ENABLE_CORAL_TPU_ACCELERATION and getattr(config, "STEP5_ENABLE_CORAL_TPU", True)

    if is_tpu_step:
        from services.coral_tpu_orchestrator import tpu_orchestrator
        logger.info(f"[{step_key}] Routage vers l'orchestrateur TPU Asynchrone (Micro-lots)")
        tpu_orchestrator.submit_task(lambda: _run_process_async_internal(step_key))
    else:
        _run_process_async_internal(step_key)
