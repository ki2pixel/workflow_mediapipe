#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow State Management Service

Centralized state management for workflow execution with thread-safety.
Replaces global variables with a clean, testable interface.
"""

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WorkflowState:
    """Centralized workflow state management with thread-safety."""
    
    def __init__(self):
        self._lock = threading.RLock()

        self._process_info: Dict[str, Dict[str, Any]] = {}
        self._sequence_running = False
        self._sequence_outcome = {
            "status": "never_run",
            "type": None,
            "message": None,
            "timestamp": None
        }
        self._active_csv_downloads: Dict[str, Dict[str, Any]] = {}
        self._kept_csv_downloads = deque(maxlen=20)
        self._csv_monitor_status = {
            "status": "stopped",
            "last_check": None,
            "error": None
        }
        
        logger.info("WorkflowState initialized")
    
    def initialize_step(self, step_key: str) -> None:
        with self._lock:
            self._process_info[step_key] = {
                'status': 'idle',
                'log': deque(maxlen=300),
                'return_code': None,
                'process': None,
                'progress_current': 0,
                'progress_total': 0,
                'progress_text': '',
                'start_time_epoch': None,
                'duration_str': None
            }
            logger.debug(f"Initialized state for {step_key}")
    
    def initialize_all_steps(self, step_keys: List[str]) -> None:
        with self._lock:
            for step_key in step_keys:
                self.initialize_step(step_key)
            logger.info(f"Initialized state for {len(step_keys)} steps")
    
    def get_step_info(self, step_key: str) -> Dict[str, Any]:
        with self._lock:
            if step_key not in self._process_info:
                logger.warning(f"Step {step_key} not initialized, returning empty dict")
                return {}
            
            # Deep copy to prevent external mutations
            info = self._process_info[step_key].copy()
            # Convert deque to list for JSON serialization
            if 'log' in info and isinstance(info['log'], deque):
                info['log'] = list(info['log'])
            return info
    
    def get_all_steps_info(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                step_key: self.get_step_info(step_key)
                for step_key in self._process_info.keys()
            }
    
    def update_step_status(self, step_key: str, status: str) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['status'] = status
                logger.debug(f"{step_key} status updated to: {status}")
    
    def update_step_progress(self, step_key: str, current: int, total: int, text: str = '') -> None:
        with self._lock:
            if step_key in self._process_info:
                info = self._process_info[step_key]
                info['progress_current'] = current
                info['progress_total'] = total
                info['progress_text'] = text
    
    def append_step_log(self, step_key: str, message: str) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['log'].append(message)
    
    def clear_step_log(self, step_key: str) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['log'].clear()
    
    def update_step_info(self, step_key: str, **kwargs) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key].update(kwargs)
                logger.debug(f"{step_key} updated with: {list(kwargs.keys())}")
    
    def get_step_status(self, step_key: str) -> Optional[str]:
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key]['status']
            return None
    
    def is_step_running(self, step_key: str) -> bool:
        status = self.get_step_status(step_key)
        return status in ['running', 'starting', 'initiated']
    
    def is_any_step_running(self) -> bool:
        with self._lock:
            return any(
                info['status'] in ['running', 'starting', 'initiated']
                for info in self._process_info.values()
            )
    
    def set_step_process(self, step_key: str, process: Any) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['process'] = process
    
    def get_step_process(self, step_key: str) -> Optional[Any]:
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key].get('process')
            return None
    
    def get_step_field(self, step_key: str, field_name: str, default: Any = None) -> Any:
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key].get(field_name, default)
            return default
    
    def set_step_field(self, step_key: str, field_name: str, value: Any) -> None:
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key][field_name] = value
    
    def get_step_log_deque(self, step_key: str) -> Optional[deque]:
        if step_key in self._process_info:
            return self._process_info[step_key]['log']
        return None
    
    def is_sequence_running(self) -> bool:
        with self._lock:
            return self._sequence_running
    
    def start_sequence(self, sequence_type: str) -> bool:
        with self._lock:
            if self._sequence_running:
                logger.warning(f"Cannot start {sequence_type} sequence: already running")
                return False
            
            self._sequence_running = True
            self._sequence_outcome = {
                "status": f"running_{sequence_type.lower()}",
                "type": sequence_type,
                "message": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"{sequence_type} sequence started")
            return True
    
    def complete_sequence(self, success: bool, message: str = None, sequence_type: str = None) -> None:
        with self._lock:
            self._sequence_running = False
            status = "success" if success else "error"
            self._sequence_outcome = {
                "status": status,
                "type": sequence_type or self._sequence_outcome.get("type"),
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Sequence completed: {status}")
    
    def get_sequence_outcome(self) -> Dict[str, Any]:
        with self._lock:
            return self._sequence_outcome.copy()
    
    def add_csv_download(self, download_id: str, download_info: Dict[str, Any]) -> None:
        with self._lock:
            self._active_csv_downloads[download_id] = download_info.copy()
            logger.debug(f"CSV download added: {download_id}")
    
    def update_csv_download(self, download_id: str, status: str, 
                           progress: int = None, message: str = None, 
                           filename: str = None) -> None:
        with self._lock:
            if download_id in self._active_csv_downloads:
                download = self._active_csv_downloads[download_id]
                download['status'] = status
                if progress is not None:
                    download['progress'] = progress
                if message is not None:
                    download['message'] = message
                if filename is not None:
                    download['filename'] = filename
    
    def remove_csv_download(self, download_id: str, keep_in_history: bool = True) -> None:
        with self._lock:
            if download_id in self._active_csv_downloads:
                download = self._active_csv_downloads.pop(download_id)
                if keep_in_history:
                    self._kept_csv_downloads.append(download)
                logger.debug(f"CSV download removed: {download_id}")
    
    def get_csv_downloads_status(self) -> Dict[str, Any]:
        with self._lock:
            active = [d.copy() for d in self._active_csv_downloads.values()]
            kept = list(self._kept_csv_downloads)
            
            return {
                "active": active,
                "kept": kept,
                "total_active": len(active),
                "total_kept": len(kept)
            }
    
    def get_active_csv_downloads_dict(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {k: v.copy() for k, v in self._active_csv_downloads.items()}
    
    def get_kept_csv_downloads_list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._kept_csv_downloads)
    
    def move_csv_download_to_history(self, download_id: str) -> None:
        with self._lock:
            if download_id in self._active_csv_downloads:
                download = self._active_csv_downloads.pop(download_id)
                self._kept_csv_downloads.append(download)
                logger.debug(f"CSV download moved to history: {download_id}")
    
    def get_csv_monitor_status(self) -> Dict[str, Any]:
        with self._lock:
            return self._csv_monitor_status.copy()
    
    def update_csv_monitor_status(self, status: str, last_check: str = None, error: str = None) -> None:
        with self._lock:
            self._csv_monitor_status['status'] = status
            if last_check is not None:
                self._csv_monitor_status['last_check'] = last_check
            if error is not None:
                self._csv_monitor_status['error'] = error
    
    def reset_all(self) -> None:
        with self._lock:
            self._process_info.clear()
            self._sequence_running = False
            self._sequence_outcome = {
                "status": "never_run",
                "type": None,
                "message": None,
                "timestamp": None
            }
            self._active_csv_downloads.clear()
            self._kept_csv_downloads.clear()
            self._csv_monitor_status = {
                "status": "stopped",
                "last_check": None,
                "error": None
            }
            logger.info("WorkflowState reset to initial values")
    
    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "steps_count": len(self._process_info),
                "running_steps": [
                    key for key, info in self._process_info.items()
                    if info['status'] in ['running', 'starting']
                ],
                "sequence_running": self._sequence_running,
                "sequence_outcome": self._sequence_outcome.copy(),
                "active_downloads": len(self._active_csv_downloads),
                "csv_monitor_status": self._csv_monitor_status['status']
            }


_workflow_state: Optional[WorkflowState] = None
_state_lock = threading.Lock()


def get_workflow_state() -> WorkflowState:
    global _workflow_state
    
    if _workflow_state is None:
        with _state_lock:
            if _workflow_state is None:
                _workflow_state = WorkflowState()
    
    return _workflow_state


def reset_workflow_state() -> None:
    global _workflow_state
    
    with _state_lock:
        if _workflow_state is not None:
            _workflow_state.reset_all()
        _workflow_state = None
