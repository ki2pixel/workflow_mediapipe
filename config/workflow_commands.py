#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Commands Configuration

Centralized configuration for all workflow steps.
Defines commands, working directories, log paths, and progress patterns.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from config.settings import config

logger = logging.getLogger(__name__)


class WorkflowCommandsConfig:
    """Centralized workflow commands configuration.
    
    This class provides configuration for all 7 workflow steps, including:
    - Command line arguments
    - Working directories
    - Log file locations
    - Progress parsing patterns
    - Display names for UI
    """
    
    def __init__(self, base_path: Path = None, hf_token: str = None):
        """Initialize workflow commands configuration.
        
        Args:
            base_path: Base path for scripts (defaults to config.BASE_PATH_SCRIPTS)
            hf_token: HuggingFace authentication token for Step 4
        """
        self.base_path = base_path or config.BASE_PATH_SCRIPTS
        self.hf_token = hf_token
        
        # Setup log directories
        self.logs_base_dir = self.base_path / "logs"
        self._ensure_log_directories()
        
        # Build configuration
        self._config = self._build_configuration()
        
        logger.info(f"WorkflowCommandsConfig initialized with base_path: {self.base_path}")
    
    def _ensure_log_directories(self) -> None:
        """Ensure all log directories exist."""
        self.logs_base_dir.mkdir(exist_ok=True)
        for step in range(1, 8):
            (self.logs_base_dir / f"step{step}").mkdir(exist_ok=True)
    
    def _build_configuration(self) -> Dict[str, Dict[str, Any]]:
        """Build the complete workflow commands configuration.
        
        Returns:
            Dictionary mapping step keys to their configuration
        """
        return {
            "STEP1": self._get_step1_config(),
            "STEP2": self._get_step2_config(),
            "STEP3": self._get_step3_config(),
            "STEP4": self._get_step4_config(),
            "STEP5": self._get_step5_config(),
            "STEP6": self._get_step6_config(),
            "STEP7": self._get_step7_config(),
        }
    
    def _get_step1_config(self) -> Dict[str, Any]:
        """Get configuration for Step 1: Archive Extraction.
        
        Returns:
            Step 1 configuration dictionary
        """
        step1_log_dir = self.logs_base_dir / "step1"
        
        return {
            "display_name": "1. Extraction des archives",
            "cmd": [
                str(config.get_venv_python("env")),
                str(self.base_path / "workflow_scripts" / "step1" / "extract_archives.py"),
                "--source-dir", str(Path.home() / "Téléchargements")
            ],
            "cwd": str(self.base_path),
            "specific_logs": [
                {
                    "name": "Log Extraction",
                    "type": "directory_latest",
                    "path": step1_log_dir,
                    "pattern": "*.log",
                    "lines": 150
                },
                {
                    "name": "Liste Archives Traitées",
                    "type": "file",
                    "path": step1_log_dir / "processed_archives.txt",
                    "lines": 50
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"Trouvé (\d+) archive\(s\) à traiter", re.IGNORECASE),
                "current_success_line_pattern": re.compile(
                    r"Extraction terminée pour (.*?)$", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            }
        }
    
    def _get_step2_config(self) -> Dict[str, Any]:
        """Get configuration for Step 2: Video Conversion.
        
        Returns:
            Step 2 configuration dictionary
        """
        step2_log_dir = self.logs_base_dir / "step2"
        
        return {
            "display_name": "2. Conversion des vidéos",
            "cmd": [
                str(config.get_venv_python("env")),
                str(self.base_path / "workflow_scripts" / "step2" / "convert_videos.py")
            ],
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Conversion",
                    "type": "directory_latest",
                    "path": step2_log_dir,
                    "pattern": "*.log",
                    "lines": 200
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"TOTAL_VIDEOS_TO_PROCESS:\s*(\d+)", re.IGNORECASE),
                "current": re.compile(
                    r"--- Traitement de la vidéo \((\d+)/(\d+)\): (.*?) ---", re.IGNORECASE
                )
            }
        }
    
    def _get_step3_config(self) -> Dict[str, Any]:
        """Get configuration for Step 3: Scene Detection.
        
        Returns:
            Step 3 configuration dictionary
        """
        step3_log_dir = self.logs_base_dir / "step3"
        
        return {
            "display_name": "3. Analyse des transitions",
            "cmd": [
                str(config.get_venv_python("transnet_env")),
                str(self.base_path / "workflow_scripts" / "step3" / "run_transnet.py"),
            ],
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Analyse Transitions",
                    "type": "directory_latest",
                    "path": step3_log_dir,
                    "pattern": "*.log",
                    "lines": 150
                }
            ],
            "progress_patterns": {
                # Accept both underscore and space variants
                "total": re.compile(r"TOTAL[_ ]VIDEOS[_ ]TO[_ ]PROCESS:\s*(\d+)", re.IGNORECASE),
                "current": re.compile(r"PROCESSING[_ ]VIDEO:\s*(.*)$", re.IGNORECASE),
                "internal_simple": re.compile(
                    r"INTERNAL[_ ]PROGRESS:\s*(\d+)\s*batches\s*-\s*(.*)$", re.IGNORECASE
                ),
                "current_success_line_pattern": re.compile(
                    r"Succès:\s*(.*?)(?:\.csv|\.json)\s+créé", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            }
        }
    
    def _get_step4_config(self) -> Dict[str, Any]:
        """Get configuration for Step 4: Audio Analysis.
        
        Returns:
            Step 4 configuration dictionary
        """
        step4_log_dir = self.logs_base_dir / "step4"

        step4_script_name = "run_audio_analysis_lemonfox.py" if config.STEP4_USE_LEMONFOX else "run_audio_analysis.py"
        cmd = [
            str(config.get_venv_python("audio_env")),
            str(self.base_path / "workflow_scripts" / "step4" / step4_script_name),
            "--log_dir", str(step4_log_dir),
        ]
        
        return {
            "display_name": "4. Analyse audio",
            "cmd": cmd,
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Analyse Audio",
                    "type": "directory_latest",
                    "path": step4_log_dir,
                    "pattern": "*.log",
                    "lines": 150
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"TOTAL_AUDIO_TO_ANALYZE:\s*(\d+)", re.IGNORECASE),
                "current": re.compile(r"ANALYZING_AUDIO:\s*(\d+)/(\d+):\s*(.*)", re.IGNORECASE),
                "internal": re.compile(
                    r"INTERNAL_PROGRESS:\s*(\d+)/(\d+)\s*frames\s*\((\d+)%\)\s*-\s*(.*)",
                    re.IGNORECASE
                ),
                "current_success_line_pattern": re.compile(
                    r"Succès: analyse audio terminée pour (.*?)$", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            }
        }
    
    def _get_step5_config(self) -> Dict[str, Any]:
        """Get configuration for Step 5: Tracking Analysis.
        
        Returns:
            Step 5 configuration dictionary
        """
        step5_log_dir = self.logs_base_dir / "step5"
        
        return {
            "display_name": "5. Analyse du tracking",
            "cmd": [
                str(config.get_venv_python("tracking_env")),
                str(self.base_path / "workflow_scripts" / "step5" / "run_tracking_manager.py")
            ],
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Tracking Manager",
                    "type": "directory_latest",
                    "path": step5_log_dir,
                    "pattern": "manager_tracking*.log",
                    "lines": 100
                },
                {
                    "name": "Log Worker CPU",
                    "type": "directory_latest",
                    "path": step5_log_dir,
                    "pattern": "*worker_CPU*.log",
                    "lines": 100
                },
                {
                    "name": "Log Worker GPU",
                    "type": "directory_latest",
                    "path": step5_log_dir,
                    "pattern": "*worker_GPU*.log",
                    "lines": 100
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"Vidéos à traiter: (\d+)", re.IGNORECASE),
                "current": re.compile(r"Traitement de (.*?):\s*(\d+)%", re.IGNORECASE),
                "internal": re.compile(r"(.*?):\s*(\d+)%", re.IGNORECASE),
                "current_success_line_pattern": re.compile(
                    r"\[Gestionnaire\] Succès pour (.*?)$", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            },
            "post_completion_message_ui": "Traitement du tracking terminé."
        }
    
    def _get_step6_config(self) -> Dict[str, Any]:
        """Get configuration for Step 6: JSON Reduction.
        
        Returns:
            Step 6 configuration dictionary
        """
        step6_log_dir = self.logs_base_dir / "step6"
        
        return {
            "display_name": "6. Réduction JSON",
            "cmd": [
                str(config.get_venv_python("env")),
                str(self.base_path / "workflow_scripts" / "step6" / "json_reducer.py"),
                "--log_dir", str(step6_log_dir),
                "--work_dir", str(self.base_path / "projets_extraits")
            ],
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Réduction JSON",
                    "type": "directory_latest",
                    "path": step6_log_dir,
                    "pattern": "*.log",
                    "lines": 150
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"TOTAL_JSON_TO_REDUCE:\s*(\d+)", re.IGNORECASE),
                "current": re.compile(r"REDUCING_JSON:\s*(\d+)/(\d+):\s*(.*)", re.IGNORECASE),
                "internal": re.compile(
                    r"INTERNAL_PROGRESS:\s*(\d+)/(\d+)\s*items\s*\((\d+)%\)\s*-\s*(.*)",
                    re.IGNORECASE
                ),
                "current_success_line_pattern": re.compile(
                    r"Succès: réduction JSON terminée pour (.*?)$", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            }
        }
    
    def _get_step7_config(self) -> Dict[str, Any]:
        """Get configuration for Step 7: Finalization.
        
        Returns:
            Step 7 configuration dictionary
        """
        step7_log_dir = self.logs_base_dir / "step7"
        
        return {
            "display_name": "7. Finalisation",
            "cmd": [
                str(config.get_venv_python("env")),
                str(self.base_path / "workflow_scripts" / "step7" / "finalize_and_copy.py")
            ],
            "cwd": str(self.base_path / "projets_extraits"),
            "specific_logs": [
                {
                    "name": "Log Finalisation",
                    "type": "directory_latest",
                    "path": step7_log_dir,
                    "pattern": "*.log",
                    "lines": 150
                }
            ],
            "progress_patterns": {
                "total": re.compile(r"(\d+) projet\(s\) à finaliser", re.IGNORECASE),
                "current_success_line_pattern": re.compile(
                    r"Finalisation terminée pour '(.*?)'", re.IGNORECASE
                ),
                "current_item_text_from_success_line": True
            },
            "post_completion_message_ui": "Finalisation des projets terminée."
        }
    
    # ========== Public API ==========
    
    def get_config(self) -> Dict[str, Dict[str, Any]]:
        """Get the complete workflow commands configuration.
        
        Returns:
            Dictionary mapping step keys to their configuration
        """
        return self._config.copy()
    
    def get_step_config(self, step_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific step.
        
        Args:
            step_key: Step identifier (e.g., 'STEP1', 'STEP2')
            
        Returns:
            Step configuration dictionary or None if not found
        """
        return self._config.get(step_key)
    
    def validate_step_key(self, step_key: str) -> bool:
        """Validate if a step key exists in configuration.
        
        Args:
            step_key: Step identifier to validate
            
        Returns:
            True if step key is valid
        """
        return step_key in self._config
    
    def get_all_step_keys(self) -> List[str]:
        """Get all valid step keys.
        
        Returns:
            List of step keys
        """
        return list(self._config.keys())
    
    def get_step_display_name(self, step_key: str) -> Optional[str]:
        """Get display name for a step.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Display name or None if step not found
        """
        step_config = self.get_step_config(step_key)
        return step_config.get('display_name') if step_config else None
    
    def get_step_command(self, step_key: str) -> Optional[List[str]]:
        """Get command line for a step.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Command line as list of strings or None if step not found
        """
        step_config = self.get_step_config(step_key)
        return step_config.get('cmd') if step_config else None
    
    def get_step_cwd(self, step_key: str) -> Optional[str]:
        """Get working directory for a step.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Working directory path or None if step not found
        """
        step_config = self.get_step_config(step_key)
        return step_config.get('cwd') if step_config else None
    
    def update_hf_token(self, hf_token: str) -> None:
        """Update HuggingFace token and rebuild Step 4 configuration.
        
        Args:
            hf_token: New HuggingFace authentication token
        """
        self.hf_token = hf_token
        self._config["STEP4"] = self._get_step4_config()
        logger.info("HuggingFace token updated in configuration")
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"WorkflowCommandsConfig(base_path={self.base_path}, steps={len(self._config)})"
