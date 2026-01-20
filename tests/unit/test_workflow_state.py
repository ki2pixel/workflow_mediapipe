#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for WorkflowState service.
Tests the centralized state management functionality.
"""

import pytest
import threading
import time
from collections import deque

from services.workflow_state import WorkflowState, get_workflow_state, reset_workflow_state


class TestWorkflowStateInitialization:
    """Test WorkflowState initialization."""
    
    def test_init_creates_empty_state(self):
        """Test that initialization creates empty state."""
        state = WorkflowState()
        
        assert not state.is_sequence_running()
        assert not state.is_any_step_running()
        assert state.get_all_steps_info() == {}
    
    def test_initialize_step(self):
        """Test step initialization."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        info = state.get_step_info('STEP1')
        assert info['status'] == 'idle'
        assert info['progress_current'] == 0
        assert info['progress_total'] == 0
        assert isinstance(info['log'], list)  # Converted from deque
    
    def test_initialize_all_steps(self):
        """Test initialization of all steps."""
        state = WorkflowState()
        step_keys = ['STEP1', 'STEP2', 'STEP3']
        state.initialize_all_steps(step_keys)
        
        all_info = state.get_all_steps_info()
        assert len(all_info) == 3
        assert all(key in all_info for key in step_keys)


class TestProcessInfoManagement:
    """Test process info management methods."""
    
    def test_get_step_info_nonexistent(self):
        """Test getting info for non-existent step."""
        state = WorkflowState()
        info = state.get_step_info('NONEXISTENT')
        assert info == {}
    
    def test_update_step_status(self):
        """Test updating step status."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        state.update_step_status('STEP1', 'running')
        assert state.get_step_status('STEP1') == 'running'
        
        state.update_step_status('STEP1', 'completed')
        assert state.get_step_status('STEP1') == 'completed'
    
    def test_update_step_progress(self):
        """Test updating step progress."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        state.update_step_progress('STEP1', 50, 100, 'Processing...')
        
        info = state.get_step_info('STEP1')
        assert info['progress_current'] == 50
        assert info['progress_total'] == 100
        assert info['progress_text'] == 'Processing...'
    
    def test_append_step_log(self):
        """Test appending log messages."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        state.append_step_log('STEP1', 'Log message 1')
        state.append_step_log('STEP1', 'Log message 2')
        
        info = state.get_step_info('STEP1')
        assert 'Log message 1' in info['log']
        assert 'Log message 2' in info['log']
    
    def test_clear_step_log(self):
        """Test clearing step log."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        state.append_step_log('STEP1', 'Message')
        state.clear_step_log('STEP1')
        
        info = state.get_step_info('STEP1')
        assert len(info['log']) == 0
    
    def test_update_step_info_multiple_fields(self):
        """Test updating multiple fields atomically."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        state.update_step_info('STEP1', status='running', return_code=0, duration_str='10s')
        
        info = state.get_step_info('STEP1')
        assert info['status'] == 'running'
        assert info['return_code'] == 0
        assert info['duration_str'] == '10s'
    
    def test_is_step_running(self):
        """Test checking if step is running."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        assert not state.is_step_running('STEP1')
        
        state.update_step_status('STEP1', 'running')
        assert state.is_step_running('STEP1')
        
        state.update_step_status('STEP1', 'completed')
        assert not state.is_step_running('STEP1')
    
    def test_is_any_step_running(self):
        """Test checking if any step is running."""
        state = WorkflowState()
        state.initialize_all_steps(['STEP1', 'STEP2', 'STEP3'])
        
        assert not state.is_any_step_running()
        
        state.update_step_status('STEP2', 'running')
        assert state.is_any_step_running()


class TestSequenceManagement:
    """Test sequence management methods."""
    
    def test_start_sequence(self):
        """Test starting a sequence."""
        state = WorkflowState()
        
        result = state.start_sequence('Full')
        assert result is True
        assert state.is_sequence_running()
        
        outcome = state.get_sequence_outcome()
        assert outcome['type'] == 'Full'
        assert 'running' in outcome['status']
    
    def test_start_sequence_already_running(self):
        """Test that starting sequence while running fails."""
        state = WorkflowState()
        
        state.start_sequence('Full')
        result = state.start_sequence('Remote')
        
        assert result is False
        assert state.is_sequence_running()
    
    def test_complete_sequence_success(self):
        """Test completing sequence successfully."""
        state = WorkflowState()
        state.start_sequence('Full')
        
        state.complete_sequence(success=True, message='All steps completed', sequence_type='Full')
        
        assert not state.is_sequence_running()
        outcome = state.get_sequence_outcome()
        assert outcome['status'] == 'success'
        assert outcome['message'] == 'All steps completed'
    
    def test_complete_sequence_failure(self):
        """Test completing sequence with failure."""
        state = WorkflowState()
        state.start_sequence('Full')
        
        state.complete_sequence(success=False, message='Step failed', sequence_type='Full')
        
        assert not state.is_sequence_running()
        outcome = state.get_sequence_outcome()
        assert outcome['status'] == 'error'


class TestCSVDownloadManagement:
    """Test CSV download management methods."""
    
    def test_add_csv_download(self):
        """Test adding a CSV download."""
        state = WorkflowState()
        
        download_info = {
            'filename': 'test.zip',
            'status': 'pending',
            'progress': 0
        }
        
        state.add_csv_download('download_1', download_info)
        
        status = state.get_csv_downloads_status()
        assert status['total_active'] == 1
        assert status['active'][0]['filename'] == 'test.zip'
    
    def test_update_csv_download(self):
        """Test updating CSV download status."""
        state = WorkflowState()
        
        download_info = {'status': 'pending', 'progress': 0}
        state.add_csv_download('download_1', download_info)
        
        state.update_csv_download('download_1', 'downloading', progress=50, message='Downloading...')
        
        status = state.get_csv_downloads_status()
        active = status['active'][0]
        assert active['status'] == 'downloading'
        assert active['progress'] == 50
        assert active['message'] == 'Downloading...'
    
    def test_remove_csv_download_with_history(self):
        """Test removing download and keeping in history."""
        state = WorkflowState()
        
        download_info = {'status': 'completed', 'progress': 100}
        state.add_csv_download('download_1', download_info)
        
        state.remove_csv_download('download_1', keep_in_history=True)
        
        status = state.get_csv_downloads_status()
        assert status['total_active'] == 0
        assert status['total_kept'] == 1
    
    def test_csv_monitor_status(self):
        """Test CSV monitor status management."""
        state = WorkflowState()
        
        state.update_csv_monitor_status('running', last_check='2024-01-01')
        
        status = state.get_csv_monitor_status()
        assert status['status'] == 'running'
        assert status['last_check'] == '2024-01-01'
    
    def test_get_active_csv_downloads_dict(self):
        """Test getting active CSV downloads as dictionary."""
        state = WorkflowState()
        
        download_info1 = {'filename': 'file1.zip', 'status': 'downloading', 'progress': 50}
        download_info2 = {'filename': 'file2.zip', 'status': 'pending', 'progress': 0}
        
        state.add_csv_download('download_1', download_info1)
        state.add_csv_download('download_2', download_info2)
        
        downloads_dict = state.get_active_csv_downloads_dict()
        
        assert isinstance(downloads_dict, dict)
        assert len(downloads_dict) == 2
        assert 'download_1' in downloads_dict
        assert 'download_2' in downloads_dict
        assert downloads_dict['download_1']['filename'] == 'file1.zip'
        assert downloads_dict['download_2']['status'] == 'pending'
    
    def test_get_kept_csv_downloads_list(self):
        """Test getting kept CSV downloads as list."""
        state = WorkflowState()
        
        download_info = {'filename': 'test.zip', 'status': 'completed', 'progress': 100}
        state.add_csv_download('download_1', download_info)
        state.remove_csv_download('download_1', keep_in_history=True)
        
        kept_list = state.get_kept_csv_downloads_list()
        
        assert isinstance(kept_list, list)
        assert len(kept_list) == 1
        assert kept_list[0]['filename'] == 'test.zip'
        assert kept_list[0]['status'] == 'completed'
    
    def test_move_csv_download_to_history(self):
        """Test moving CSV download from active to history."""
        state = WorkflowState()
        
        download_info = {'filename': 'archive.zip', 'status': 'completed', 'progress': 100}
        state.add_csv_download('download_1', download_info)
        
        # Verify it's in active downloads
        active_before = state.get_active_csv_downloads_dict()
        assert 'download_1' in active_before
        
        # Move to history
        state.move_csv_download_to_history('download_1')
        
        # Verify it's no longer in active and is in kept
        active_after = state.get_active_csv_downloads_dict()
        kept_after = state.get_kept_csv_downloads_list()
        
        assert 'download_1' not in active_after
        assert len(kept_after) == 1
        assert kept_after[0]['filename'] == 'archive.zip'
    
    def test_move_nonexistent_download_to_history(self):
        """Test moving non-existent download to history (should not error)."""
        state = WorkflowState()
        
        # Should not raise an error
        state.move_csv_download_to_history('nonexistent_download')
        
        kept_list = state.get_kept_csv_downloads_list()
        assert len(kept_list) == 0


class TestThreadSafety:
    """Test thread-safety of WorkflowState."""
    
    def test_concurrent_updates(self):
        """Test concurrent updates to state."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        def update_worker():
            for i in range(100):
                state.update_step_progress('STEP1', i, 100)
        
        threads = [threading.Thread(target=update_worker) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not raise any exceptions and state should be consistent
        info = state.get_step_info('STEP1')
        assert 0 <= info['progress_current'] <= 100
    
    def test_concurrent_log_appends(self):
        """Test concurrent log appends."""
        state = WorkflowState()
        state.initialize_step('STEP1')
        
        def log_worker(worker_id):
            for i in range(50):
                state.append_step_log('STEP1', f'Worker {worker_id} - Message {i}')
        
        threads = [threading.Thread(target=log_worker, args=(i,)) for i in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have all 250 messages (or truncated to maxlen)
        info = state.get_step_info('STEP1')
        assert len(info['log']) > 0


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_reset_all(self):
        """Test resetting all state."""
        state = WorkflowState()
        state.initialize_all_steps(['STEP1', 'STEP2'])
        state.start_sequence('Full')
        state.add_csv_download('dl_1', {'status': 'pending'})
        
        state.reset_all()
        
        assert state.get_all_steps_info() == {}
        assert not state.is_sequence_running()
        assert state.get_csv_downloads_status()['total_active'] == 0
    
    def test_get_summary(self):
        """Test getting state summary."""
        state = WorkflowState()
        state.initialize_all_steps(['STEP1', 'STEP2', 'STEP3'])
        state.update_step_status('STEP1', 'running')
        state.start_sequence('Full')
        state.add_csv_download('dl_1', {'status': 'pending'})
        
        summary = state.get_summary()
        
        assert summary['steps_count'] == 3
        assert 'STEP1' in summary['running_steps']
        assert summary['sequence_running'] is True
        assert summary['active_downloads'] == 1


class TestSingletonPattern:
    """Test singleton pattern for global state."""
    
    def test_get_workflow_state_singleton(self):
        """Test that get_workflow_state returns same instance."""
        reset_workflow_state()  # Ensure clean start
        
        state1 = get_workflow_state()
        state2 = get_workflow_state()
        
        assert state1 is state2
    
    def test_reset_workflow_state(self):
        """Test resetting global singleton."""
        state1 = get_workflow_state()
        state1.initialize_step('STEP1')
        
        reset_workflow_state()
        
        state2 = get_workflow_state()
        # Should be a new instance
        assert state2.get_all_steps_info() == {}
