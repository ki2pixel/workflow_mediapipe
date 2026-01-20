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
    """Centralized workflow state management with thread-safety.
    
    This class manages all mutable state for workflow execution, including:
    - Process information for each step
    - Sequence execution status
    - CSV download tracking
    - Thread-safe access to all state
    
    All methods are thread-safe using internal locks.
    """
    
    def __init__(self):
        """Initialize workflow state with default values."""
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        
        # Process information for each workflow step
        self._process_info: Dict[str, Dict[str, Any]] = {}
        
        # Sequence execution state
        self._sequence_running = False
        self._sequence_outcome = {
            "status": "never_run",
            "type": None,
            "message": None,
            "timestamp": None
        }
        
        # CSV download tracking
        self._active_csv_downloads: Dict[str, Dict[str, Any]] = {}
        self._kept_csv_downloads = deque(maxlen=20)
        
        # CSV monitor status
        self._csv_monitor_status = {
            "status": "stopped",
            "last_check": None,
            "error": None
        }
        
        logger.info("WorkflowState initialized")
    
    def initialize_step(self, step_key: str) -> None:
        """Initialize state for a workflow step.
        
        Args:
            step_key: Step identifier (e.g., 'STEP1', 'STEP2')
        """
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
        """Initialize state for all workflow steps.
        
        Args:
            step_keys: List of step identifiers
        """
        with self._lock:
            for step_key in step_keys:
                self.initialize_step(step_key)
            logger.info(f"Initialized state for {len(step_keys)} steps")
    
    def get_step_info(self, step_key: str) -> Dict[str, Any]:
        """Get information for a specific step (thread-safe copy).
        
        Args:
            step_key: Step identifier
            
        Returns:
            Dictionary with step information (copy)
        """
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
        """Get information for all steps (thread-safe copy).
        
        Returns:
            Dictionary mapping step_key to step information
        """
        with self._lock:
            return {
                step_key: self.get_step_info(step_key)
                for step_key in self._process_info.keys()
            }
    
    def update_step_status(self, step_key: str, status: str) -> None:
        """Update status for a step.
        
        Args:
            step_key: Step identifier
            status: New status ('idle', 'starting', 'running', 'completed', 'failed')
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['status'] = status
                logger.debug(f"{step_key} status updated to: {status}")
    
    def update_step_progress(self, step_key: str, current: int, total: int, text: str = '') -> None:
        """Update progress information for a step.
        
        Args:
            step_key: Step identifier
            current: Current progress value
            total: Total progress value
            text: Optional progress text description
        """
        with self._lock:
            if step_key in self._process_info:
                info = self._process_info[step_key]
                info['progress_current'] = current
                info['progress_total'] = total
                info['progress_text'] = text
    
    def append_step_log(self, step_key: str, message: str) -> None:
        """Append a log message to a step's log.
        
        Args:
            step_key: Step identifier
            message: Log message to append
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['log'].append(message)
    
    def clear_step_log(self, step_key: str) -> None:
        """Clear the log for a step.
        
        Args:
            step_key: Step identifier
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['log'].clear()
    
    def update_step_info(self, step_key: str, **kwargs) -> None:
        """Update multiple fields for a step atomically.
        
        Args:
            step_key: Step identifier
            **kwargs: Fields to update
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key].update(kwargs)
                logger.debug(f"{step_key} updated with: {list(kwargs.keys())}")
    
    def get_step_status(self, step_key: str) -> Optional[str]:
        """Get current status of a step.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Current status or None if step not found
        """
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key]['status']
            return None
    
    def is_step_running(self, step_key: str) -> bool:
        """Check if a step is currently running.
        
        Args:
            step_key: Step identifier
            
        Returns:
            True if step is running or starting
        """
        status = self.get_step_status(step_key)
        return status in ['running', 'starting', 'initiated']
    
    def is_any_step_running(self) -> bool:
        """Check if any step is currently running.
        
        Returns:
            True if any step is running
        """
        with self._lock:
            return any(
                info['status'] in ['running', 'starting', 'initiated']
                for info in self._process_info.values()
            )
    
    def set_step_process(self, step_key: str, process: Any) -> None:
        """Set the subprocess for a step.
        
        Args:
            step_key: Step identifier
            process: Subprocess instance (or None to clear)
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key]['process'] = process
    
    def get_step_process(self, step_key: str) -> Optional[Any]:
        """Get the subprocess for a step.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Subprocess instance or None
        """
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key].get('process')
            return None
    
    def get_step_field(self, step_key: str, field_name: str, default: Any = None) -> Any:
        """Get a specific field from step info.
        
        Args:
            step_key: Step identifier
            field_name: Name of field to retrieve
            default: Default value if field not found
            
        Returns:
            Field value or default
        """
        with self._lock:
            if step_key in self._process_info:
                return self._process_info[step_key].get(field_name, default)
            return default
    
    def set_step_field(self, step_key: str, field_name: str, value: Any) -> None:
        """Set a specific field in step info.
        
        Args:
            step_key: Step identifier
            field_name: Name of field to set
            value: Value to set
        """
        with self._lock:
            if step_key in self._process_info:
                self._process_info[step_key][field_name] = value
    
    def get_step_log_deque(self, step_key: str) -> Optional[deque]:
        if step_key in self._process_info:
            return self._process_info[step_key]['log']
        return None
    
    def is_sequence_running(self) -> bool:
        """Check if a sequence is currently running.
        
        Returns:
            True if a sequence is running
        """
        with self._lock:
            return self._sequence_running
    
    def start_sequence(self, sequence_type: str) -> bool:
        """Mark sequence as started.
        
        Args:
            sequence_type: Type of sequence ('Full', 'Remote', etc.)
            
        Returns:
            True if sequence started, False if already running
        """
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
        """Mark sequence as completed.
        
        Args:
            success: True if sequence succeeded, False otherwise
            message: Optional completion message
            sequence_type: Type of sequence
        """
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
        """Get last sequence outcome.
        
        Returns:
            Dictionary with sequence outcome information
        """
        with self._lock:
            return self._sequence_outcome.copy()
    
    def add_csv_download(self, download_id: str, download_info: Dict[str, Any]) -> None:
        """Add a CSV download to tracking.
        
        Args:
            download_id: Unique download identifier
            download_info: Download information dictionary
        """
        with self._lock:
            self._active_csv_downloads[download_id] = download_info.copy()
            logger.debug(f"CSV download added: {download_id}")
    
    def update_csv_download(self, download_id: str, status: str, 
                           progress: int = None, message: str = None, 
                           filename: str = None) -> None:
        """Update CSV download status.
        
        Args:
            download_id: Download identifier
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            filename: Filename (if changed)
        """
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
        """Remove a CSV download from active tracking.
        
        Args:
            download_id: Download identifier
            keep_in_history: If True, move to kept downloads history
        """
        with self._lock:
            if download_id in self._active_csv_downloads:
                download = self._active_csv_downloads.pop(download_id)
                if keep_in_history:
                    self._kept_csv_downloads.append(download)
                logger.debug(f"CSV download removed: {download_id}")
    
    def get_csv_downloads_status(self) -> Dict[str, Any]:
        """Get status of all CSV downloads.
        
        Returns:
            Dictionary with active and kept downloads
        """
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
        """Get active CSV downloads as a dictionary.
        
        Returns:
            Dictionary mapping download_id to download info
        """
        with self._lock:
            return {k: v.copy() for k, v in self._active_csv_downloads.items()}
    
    def get_kept_csv_downloads_list(self) -> List[Dict[str, Any]]:
        """Get list of kept (recent) CSV downloads.
        
        Returns:
            List of download info dictionaries
        """
        with self._lock:
            return list(self._kept_csv_downloads)
    
    def move_csv_download_to_history(self, download_id: str) -> None:
        """Move a CSV download from active to history.
        
        Args:
            download_id: Download identifier
        """
        with self._lock:
            if download_id in self._active_csv_downloads:
                download = self._active_csv_downloads.pop(download_id)
                self._kept_csv_downloads.append(download)
                logger.debug(f"CSV download moved to history: {download_id}")
    
    def get_csv_monitor_status(self) -> Dict[str, Any]:
        """Get CSV monitor status.
        
        Returns:
            Dictionary with monitor status
        """
        with self._lock:
            return self._csv_monitor_status.copy()
    
    def update_csv_monitor_status(self, status: str, last_check: str = None, error: str = None) -> None:
        """Update CSV monitor status.
        
        Args:
            status: Monitor status ('running', 'stopped', 'error')
            last_check: Timestamp of last check
            error: Error message if any
        """
        with self._lock:
            self._csv_monitor_status['status'] = status
            if last_check is not None:
                self._csv_monitor_status['last_check'] = last_check
            if error is not None:
                self._csv_monitor_status['error'] = error
    
    def reset_all(self) -> None:
        """Reset all state to initial values (useful for testing)."""
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
        """Get a summary of current workflow state.
        
        Returns:
            Dictionary with state summary
        """
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
    """Get the global WorkflowState singleton instance.
    
    Returns:
        WorkflowState singleton instance
    """
    global _workflow_state
    
    if _workflow_state is None:
        with _state_lock:
            if _workflow_state is None:
                _workflow_state = WorkflowState()
    
    return _workflow_state


def reset_workflow_state() -> None:
    """Reset the global WorkflowState (useful for testing)."""
    global _workflow_state
    
    with _state_lock:
        if _workflow_state is not None:
            _workflow_state.reset_all()
        _workflow_state = None
