import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from config.settings import config
from services.workflow_state import get_workflow_state

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WorkflowService:
    """
    Centralized service for workflow management.

    This service follows the Service & Blueprint Architecture pattern by:
    - Using app_new.py as the single source of truth for state
    - Providing clean, stateless methods for workflow operations
    - Implementing proper error handling and fallback mechanisms
    - Maintaining thread-safe operations through proper state access
    """

    _initialized = False
    _initialization_lock = threading.Lock()

    @staticmethod
    def initialize(commands_config: Dict[str, Any]) -> None:
        """
        Initialize the workflow service.

        This method primarily serves as a confirmation that the service is loaded,
        as state is managed via WorkflowState singleton.

        Args:
            commands_config: Dict[str, Any] - Dictionary of step configurations (informational only)
        """
        with WorkflowService._initialization_lock:
            if WorkflowService._initialized:
                logger.debug("[WorkflowService] Already initialized, skipping")
                return

            try:
                workflow_state = get_workflow_state()
                if workflow_state:
                    WorkflowService._initialized = True
                    logger.info(f"Workflow service initialized, linked to WorkflowState singleton with {len(commands_config)} steps.")
                else:
                    raise RuntimeError("WorkflowState singleton not available")
            except Exception as e:
                logger.error(f"Workflow service initialization failed: {e}")
                raise RuntimeError("WorkflowService cannot initialize without access to WorkflowState") from e

    @staticmethod
    def _get_workflow_state():
        return get_workflow_state()
    
    @staticmethod
    def get_step_status(step_key: str, include_logs: bool = False) -> Dict[str, Any]:
        """
        Get current status of a workflow step from the single source of truth.

        Args:
            step_key: Step identifier
            include_logs: Whether to include log entries

        Returns:
            Step status dictionary

        Raises:
            ValueError: If step_key is not found
            RuntimeError: If workflow state is not available
        """
        workflow_state = WorkflowService._get_workflow_state()

        if not workflow_state:
            raise RuntimeError("WorkflowService cannot access workflow state")

        info = workflow_state.get_step_info(step_key)
        if not info:
            raise ValueError(f"Step '{step_key}' not found or not initialized")

        current_sequence_state = workflow_state.is_sequence_running()

        from config.workflow_commands import WorkflowCommandsConfig
        config_instance = WorkflowCommandsConfig()
        step_display_name = config_instance.get_step_display_name(step_key) or step_key

        result = {
            "step": step_key,
            "display_name": step_display_name,
            "status": info['status'],
            "return_code": info['return_code'],
            "progress_current": info['progress_current'],
            "progress_total": info['progress_total'],
            "progress_current_fractional": info.get('progress_current_fractional'),
            "progress_text": info['progress_text'],
            "duration_str": info.get('duration_str', None),
            "is_any_sequence_running": current_sequence_state
        }

        if include_logs:
            result["log"] = info.get('log', [])

        return result

    @staticmethod
    def get_step_log_file(step_key: str, log_index: int) -> Dict[str, Any]:
        from config.workflow_commands import WorkflowCommandsConfig

        config_instance = WorkflowCommandsConfig()
        step_config = config_instance.get_step_config(step_key)
        if not step_config:
            raise ValueError("Step not found")

        specific_logs_config = step_config.get("specific_logs", [])
        if not (0 <= log_index < len(specific_logs_config)):
            raise ValueError("Log index out of range")

        log_conf = specific_logs_config[log_index]
        log_type = log_conf["type"]
        num_lines = log_conf.get("lines", 50)

        content = ""
        error_msg = None
        processed_path_str = "N/A"

        def _read_tail(path: Path, lines: int) -> str:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                tail = deque(f, maxlen=lines)
            if not tail:
                return "Fichier vide."
            return ''.join(tail)

        if log_type == "file":
            log_path = Path(log_conf["path"])
            processed_path_str = str(log_path)
            if not log_path.exists():
                error_msg = "Fichier non trouvé"
                content = f"Fichier non trouvé: {log_path}"
            else:
                try:
                    content = _read_tail(log_path, int(num_lines))
                except Exception as e:
                    error_msg = f"Erreur de lecture: {e}"
                    content = f"Impossible de lire le fichier: {e}"

        elif log_type == "directory_latest":
            log_dir = Path(log_conf["path"])
            pattern = log_conf.get("pattern", "*.log")
            processed_path_str = f"{log_dir}/{pattern}"

            if not (log_dir.exists() and log_dir.is_dir()):
                error_msg = "Répertoire non trouvé"
                content = f"Répertoire non trouvé: {log_dir}"
                processed_path_str = str(log_dir)
            else:
                try:
                    matching_files = [p for p in log_dir.glob(pattern) if p.is_file()]
                    if not matching_files:
                        error_msg = "Aucun fichier trouvé"
                        content = f"Aucun fichier correspondant au pattern '{pattern}' dans {log_dir}"
                    else:
                        latest_path = max(matching_files, key=lambda p: p.stat().st_mtime)
                        processed_path_str = str(latest_path)
                        try:
                            content = _read_tail(latest_path, int(num_lines))
                        except Exception as e:
                            error_msg = f"Erreur de lecture: {e}"
                            content = f"Impossible de lire le fichier: {e}"
                except Exception as e:
                    error_msg = f"Erreur de recherche: {e}"
                    content = f"Erreur lors de la recherche de fichiers: {e}"

        else:
            error_msg = f"Type de log non supporté: {log_type}"
            content = f"Type de log '{log_type}' non supporté"

        return {
            "content": content,
            "error": error_msg,
            "path": processed_path_str,
            "type": log_type,
            "lines_requested": num_lines,
        }
    
    @staticmethod
    def run_step(step_key: str) -> Dict[str, str]:
        """
        Execute a single workflow step.

        Args:
            step_key: Step identifier

        Returns:
            Result dictionary with status and message
        """
                
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            return {"status": "error", "message": "WorkflowState not available."}

                
        from config.workflow_commands import WorkflowCommandsConfig
        config_instance = WorkflowCommandsConfig()
        
                
        if not config_instance.validate_step_key(step_key):
            return {"status": "error", "message": "Étape inconnue"}
        
        step_display_name = config_instance.get_step_display_name(step_key)

                
        projects_dir = config.BASE_PATH_SCRIPTS / 'projets_extraits'
        projects_dir.mkdir(parents=True, exist_ok=True)

                
        if workflow_state.is_sequence_running():
            return {
                "status": "error",
                "message": "Une séquence de workflow est en cours. Veuillez attendre."
            }

                
        if workflow_state.is_step_running(step_key):
            return {
                "status": "error",
                "message": f"'{step_display_name}' est déjà en cours."
            }

                
        import sys
        if 'app_new' not in sys.modules:
            return {"status": "error", "message": "Execution context not available"}
        
        app_new = sys.modules['app_new']
        if not hasattr(app_new, 'run_process_async'):
            logger.error("run_process_async not available in app_new")
            return {"status": "error", "message": "Execution function not available"}

        try:
            thread = threading.Thread(
                target=app_new.run_process_async,
                args=(step_key,)
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"Error starting step execution thread: {e}")
            return {"status": "error", "message": f"Failed to start step execution: {str(e)}"}
        
        return {
            "status": "initiated",
            "message": f"Lancement de: {step_display_name}"
        }
    
    @staticmethod
    def run_custom_sequence(steps: List[str]) -> Dict[str, str]:
        """
        Execute a custom sequence of workflow steps.

        Args:
            steps: List of step identifiers

        Returns:
            Result dictionary with status and message
        """
                
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            return {"status": "error", "message": "WorkflowState not available."}

        from config.workflow_commands import WorkflowCommandsConfig
        config_instance = WorkflowCommandsConfig()

                
        if workflow_state.is_sequence_running():
            return {
                "status": "error",
                "message": "Une autre séquence de workflow est déjà en cours."
            }

                
        for step_key in steps:
            if not config_instance.validate_step_key(step_key):
                return {"status": "error", "message": f"Étape inconnue : {step_key}"}

                
        import sys
        if 'app_new' not in sys.modules:
            return {"status": "error", "message": "Execution context not available"}
        
        app_new = sys.modules['app_new']
        if not hasattr(app_new, 'execute_step_sequence_worker'):
            logger.error("execute_step_sequence_worker not available in app_new")
            return {"status": "error", "message": "Sequence execution function not available"}

        try:
            thread = threading.Thread(
                target=app_new.execute_step_sequence_worker,
                args=(steps, "Custom")
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"Error starting sequence execution thread: {e}")
            return {"status": "error", "message": f"Failed to start sequence execution: {str(e)}"}

        return {
            "status": "initiated",
            "message": f"Séquence personnalisée lancée avec {len(steps)} étapes."
        }

    @staticmethod
    def stop_step(step_key: str) -> Dict[str, str]:
        """
        Stop a running workflow step.

        Args:
            step_key: Step identifier

        Returns:
            Result dictionary with status and message

        Raises:
            ValueError: If step_key is not found
            RuntimeError: If workflow state is not available
        """
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            raise RuntimeError("WorkflowService cannot access workflow state")

                
        info = workflow_state.get_step_info(step_key)
        if not info:
            raise ValueError(f"Step '{step_key}' not found")

        if info['status'] not in ['running', 'starting']:
            return {
                "status": "error",
                "message": f"Step '{step_key}' is not running"
            }

                
        process = workflow_state.get_step_process(step_key)
        
        if process:
            try:
                process.terminate()
                                
                workflow_state.update_step_info(
                    step_key,
                    status='stopped',
                    return_code=-1
                )

                return {
                    "status": "success",
                    "message": f"Step '{step_key}' stopped successfully"
                }
            except Exception as e:
                logger.error(f"Error stopping step {step_key}: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to stop step: {str(e)}"
                }
        else:
            return {
                "status": "error",
                "message": f"No process found for step '{step_key}'"
            }
    
    @staticmethod
    def get_sequence_status() -> Dict[str, Any]:
        """
        Get current sequence execution status.
        
        Returns:
            Sequence status dictionary
        """
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            return {
                "is_running": False,
                "current_step": None,
                "progress": {"current": 0, "total": 0},
                "last_outcome": {"status": "unknown"},
                "error": "Unable to access workflow state"
            }
        
                
        is_running = workflow_state.is_sequence_running()
        
                
        current_step = None
        all_steps_info = workflow_state.get_all_steps_info()
        for step_key, info in all_steps_info.items():
            if info['status'] in ['running', 'starting']:
                current_step = step_key
                break
        
                
        total_steps = len(all_steps_info)
        completed_steps = sum(
            1 for info in all_steps_info.values()
            if info['status'] == 'completed'
        )
        
        return {
            "is_running": is_running,
            "current_step": current_step,
            "progress": {
                "current": completed_steps,
                "total": total_steps
            },
            "last_outcome": workflow_state.get_sequence_outcome()
        }
    
    @staticmethod
    def stop_sequence() -> Dict[str, str]:
        """
        Stop the currently running sequence.
        
        Returns:
            Result dictionary with status and message
        """
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            return {
                "status": "error",
                "message": "Unable to access workflow state"
            }
        
                
        if not workflow_state.is_sequence_running():
            return {
                "status": "error",
                "message": "Aucune séquence en cours d'exécution"
            }
        
                
        workflow_state.complete_sequence(
            success=False,
            message="Sequence manually stopped by user"
        )
        
                
        stopped_steps = []
        all_steps_info = workflow_state.get_all_steps_info()
        for step_key, info in all_steps_info.items():
            if info['status'] in ['running', 'starting']:
                try:
                    process = workflow_state.get_step_process(step_key)
                    if process:
                        process.terminate()
                        workflow_state.update_step_info(
                            step_key,
                            status='stopped',
                            return_code=-1
                        )
                        stopped_steps.append(step_key)
                except Exception as e:
                    logger.error(f"Error stopping step {step_key}: {e}")
        
        return {
            "status": "success",
            "message": f"Sequence stopped. Stopped steps: {', '.join(stopped_steps) if stopped_steps else 'none'}"
        }
    
    @staticmethod
    def get_current_workflow_status_summary() -> Dict[str, Any]:
        """
        Get workflow status summary for remote servers.

        Returns:
            Workflow status summary
        """
        workflow_state = WorkflowService._get_workflow_state()
        if not workflow_state:
            return {
                "is_sequence_running": False,
                "steps": {},
                "last_sequence_outcome": {"status": "unknown"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Unable to access workflow state"
            }

        try:
                    
            sequence_running = workflow_state.is_sequence_running()

                        
            steps_summary = {}
            all_steps_info = workflow_state.get_all_steps_info()
            for step_key, info in all_steps_info.items():
                steps_summary[step_key] = {
                    "status": info['status'],
                    "progress_current": info['progress_current'],
                    "progress_total": info['progress_total'],
                    "return_code": info['return_code']
                }

            return {
                "is_sequence_running": sequence_running,
                "steps": steps_summary,
                "last_sequence_outcome": workflow_state.get_sequence_outcome(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting workflow status summary: {e}")
            return {
                "is_sequence_running": False,
                "steps": {},
                "last_sequence_outcome": {"status": "error"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": f"Failed to get status: {str(e)}"
            }
    
    @staticmethod
    def prepare_step_execution(step_key: str, process_info: Dict, commands_config: Dict) -> Tuple[List[str], str]:
        """Prepare step configuration and command for execution.
        
        Args:
            step_key: Step identifier
            process_info: Process information dictionary
            commands_config: Commands configuration dictionary
            
        Returns:
            Tuple of (command_list, working_directory)
        """
        step_config = commands_config[step_key]
        
                
        process_info['status'] = 'starting'
        process_info['log'].clear()
        process_info['log'].append(f"--- Lancement de: {step_config['display_name']} ---\n")
        process_info['return_code'] = None
        process_info['progress_current'] = 0
        process_info['progress_total'] = 0
        process_info['progress_text'] = ''
        process_info['start_time_epoch'] = time.time()
        
                
        cmd_list = [str(c) for c in step_config['cmd']]
        cwd = step_config['cwd']
        
        logger.info(f"{step_key} preparation complete: {step_config['display_name']}")
        
        return cmd_list, cwd
    
    @staticmethod
    def prepare_tracking_step(base_path: Path, keyword: str, subdir: str) -> Optional[List[str]]:
        """Prepare tracking step (STEP5) by finding videos to process.
        
        Args:
            base_path: Base path for video search
            keyword: Keyword filter for videos
            subdir: Subdirectory filter
            
        Returns:
            List of video paths to process, or None if no videos found
        """
        from services.filesystem_service import FilesystemService
        
        logger.info("STEP5: Searching for videos requiring tracking...")
        
        videos_to_process = FilesystemService.find_videos_for_tracking(
            base_path,
            keyword,
            subdir
        )
        
        if not videos_to_process:
            logger.info("STEP5: No videos to process (all have existing JSON)")
            return None
        
        logger.info(f"STEP5: Found {len(videos_to_process)} videos needing tracking")
        return videos_to_process
    
    @staticmethod
    def create_tracking_temp_file(videos: List[str]) -> Path:
        """Create temporary file with list of videos for tracking.
        
        Writes a JSON array of video paths directly (not wrapped in an object).
        This format is expected by run_tracking_manager.py.
        
        Args:
            videos: List of video file paths
            
        Returns:
            Path to temporary file containing JSON array of video paths
        """
        import tempfile
        import json
        
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='tracking_videos_')
        temp_file = Path(temp_path)
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(videos, f, indent=2)
            
            os.close(temp_fd)
            logger.info(f"Created tracking temp file: {temp_file}")
            return temp_file
            
        except Exception as e:
            os.close(temp_fd)
            logger.error(f"Failed to create tracking temp file: {e}")
            raise
    
    @staticmethod
    def calculate_step_duration(start_time_epoch: Optional[float]) -> str:
        """Calculate duration string for a step.
        
        Args:
            start_time_epoch: Start time as epoch timestamp
            
        Returns:
            Duration string (e.g., "2m 30s")
        """
        if start_time_epoch is None:
            return "N/A"
        
        try:
            elapsed = time.time() - start_time_epoch
            if elapsed < 60:
                return f"{int(elapsed)}s"
            elif elapsed < 3600:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                return f"{minutes}m {seconds}s"
            else:
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception as e:
            logger.warning(f"Failed to calculate duration: {e}")
            return "N/A"
    
    @staticmethod
    def format_duration_seconds(total_seconds: float) -> str:
        """Format duration in seconds to human-readable string.
        
        Args:
            total_seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if total_seconds < 0:
            return "N/A"
        
        try:
            if total_seconds < 60:
                return f"{int(total_seconds)}s"
            elif total_seconds < 3600:
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                return f"{minutes}m {seconds}s"
            else:
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception:
            return "N/A"

