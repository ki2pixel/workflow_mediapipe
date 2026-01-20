#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for WorkflowService.
Tests service methods that interact with workflow_state.
"""

import contextlib
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

from services.workflow_service import WorkflowService
from services.workflow_state import WorkflowState


@contextlib.contextmanager
def patched_workflow_state(mock_state):
    """Context manager to patch the WorkflowState singleton."""
    with patch('services.workflow_service.get_workflow_state', return_value=mock_state):
        yield mock_state


@contextlib.contextmanager
def patched_commands_config(display_name='Test Step', validate=True):
    """Context manager to patch WorkflowCommandsConfig for deterministic behavior."""
    with patch('config.workflow_commands.WorkflowCommandsConfig') as MockConfig:
        instance = MockConfig.return_value
        instance.get_step_display_name.return_value = display_name
        instance.validate_step_key.return_value = validate
        instance.get_step_config.return_value = {'display_name': display_name}
        yield instance


@contextlib.contextmanager
def patched_app_new(**attrs):
    """Patch sys.modules['app_new'] with a lightweight object exposing given attributes."""
    mock_app = Mock()
    for key, value in attrs.items():
        setattr(mock_app, key, value)
    with patch.dict(sys.modules, {'app_new': mock_app}, clear=False):
        yield mock_app


def build_workflow_state(**overrides) -> Mock:
    """Create a workflow state mock with sane defaults."""
    state = Mock()
    state.is_sequence_running.return_value = overrides.get('is_sequence_running', False)
    state.is_step_running.return_value = overrides.get('is_step_running', False)
    state.get_step_info.return_value = overrides.get('step_info', {'status': 'idle'})
    state.get_all_steps_info.return_value = overrides.get('all_steps_info', {})
    state.get_sequence_outcome.return_value = overrides.get('sequence_outcome', {'status': 'unknown'})
    state.get_step_process.return_value = overrides.get('step_process')
    return state


class TestWorkflowServiceInitialization:
    """Test WorkflowService initialization."""
    
    def test_initialize_without_workflow_state(self):
        """Test initialization fails gracefully when WorkflowState is unavailable."""
        # Reset the singleton state first
        WorkflowService._initialized = False
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            with pytest.raises(RuntimeError, match="WorkflowService cannot initialize without access to WorkflowState"):
                WorkflowService.initialize({})
    
    def test_initialize_with_valid_state(self):
        """Test successful initialization with valid app_new state."""
        with patch('services.workflow_service.get_workflow_state', return_value=WorkflowState()):
            # Should not raise
            WorkflowService.initialize({'STEP1': {'display_name': 'Test Step'}})
    
    def test_get_workflow_state_proxy(self):
        """Test that _get_workflow_state proxies to module-level helper."""
        sentinel = object()
        with patch('services.workflow_service.get_workflow_state', return_value=sentinel):
            result = WorkflowService._get_workflow_state()
            assert result is sentinel


class TestWorkflowServiceGetStepStatus:
    """Test get_step_status method."""
    
    def test_get_step_status_without_app_state(self):
        """Test get_step_status raises error when WorkflowState is unavailable."""
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            with pytest.raises(RuntimeError, match="WorkflowService cannot access workflow state"):
                WorkflowService.get_step_status('STEP1')
    
    def test_get_step_status_nonexistent_step(self):
        """Test get_step_status with nonexistent step."""
        mock_state = Mock()
        mock_state.get_step_info.return_value = {}
        with patched_workflow_state(mock_state):
            with pytest.raises(ValueError, match="not found or not initialized"):
                WorkflowService.get_step_status('NONEXISTENT')
    
    def test_get_step_status_success(self):
        """Test successful get_step_status."""
        step_info = {
            'status': 'running',
            'return_code': None,
            'progress_current': 5,
            'progress_total': 10,
            'progress_text': 'Processing...',
            'log': ['line1', 'line2']
        }
        
        mock_state = Mock()
        mock_state.get_step_info.return_value = step_info
        mock_state.is_sequence_running.return_value = False
        
        with patched_workflow_state(mock_state), patched_commands_config('Test Step'):
            result = WorkflowService.get_step_status('STEP1', include_logs=True)
            
            assert result['step'] == 'STEP1'
            assert result['display_name'] == 'Test Step'
            assert result['status'] == 'running'
            assert result['progress_current'] == 5
            assert result['progress_total'] == 10
            assert result['is_any_sequence_running'] is False
            assert result['log'] == ['line1', 'line2']
    
    def test_get_step_status_without_logs(self):
        """Test get_step_status excludes logs when include_logs=False."""
        step_info = {
            'status': 'idle',
            'return_code': None,
            'progress_current': 0,
            'progress_total': 0,
            'progress_text': '',
            'log': ['line1', 'line2']
        }
        
        mock_state = Mock()
        mock_state.get_step_info.return_value = step_info
        mock_state.is_sequence_running.return_value = False
        
        with patched_workflow_state(mock_state), patched_commands_config('Test'):
            result = WorkflowService.get_step_status('STEP1', include_logs=False)
            
            assert 'log' not in result


class TestWorkflowServiceRunStep:
    """Test run_step method."""
    
    def test_run_step_without_app_state(self):
        """Test run_step fails when WorkflowState is unavailable."""
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            result = WorkflowService.run_step('STEP1')
            
            assert result['status'] == 'error'
            assert 'WorkflowState not available' in result['message']
    
    def test_run_step_without_run_process_async(self):
        """Test run_step fails when run_process_async is not available."""
        workflow_state = build_workflow_state()
        mock_app = Mock()
        # Deliberately do NOT set run_process_async attribute
        del mock_app.run_process_async
        
        with patched_workflow_state(workflow_state), patched_commands_config():
            with patch.dict('sys.modules', {'app_new': mock_app}):
                with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                    result = WorkflowService.run_step('STEP1')
                    
                    assert result['status'] == 'error'
                    assert 'Execution function not available' in result['message']
    
    def test_run_step_sequence_running(self):
        """Test run_step refuses when sequence is running."""
        workflow_state = build_workflow_state(is_sequence_running=True)
        with patched_workflow_state(workflow_state), patched_commands_config(), patched_app_new(run_process_async=Mock()):
            result = WorkflowService.run_step('STEP1')
            
            assert result['status'] == 'error'
            assert 'séquence de workflow est en cours' in result['message']
    
    def test_run_step_already_running(self):
        """Test run_step refuses when step is already running."""
        workflow_state = build_workflow_state(is_step_running=True)
        with patched_workflow_state(workflow_state), patched_commands_config('Test Step'), patched_app_new(run_process_async=Mock()):
            result = WorkflowService.run_step('STEP1')
            
            assert result['status'] == 'error'
            assert 'déjà en cours' in result['message']
    
    def test_run_step_success(self):
        """Test successful run_step."""
        workflow_state = build_workflow_state()
        run_async = Mock()
        with patched_workflow_state(workflow_state), patched_commands_config('Test Step'), patched_app_new(run_process_async=run_async):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                result = WorkflowService.run_step('STEP1')
                
                assert result['status'] == 'initiated'
                assert 'Test Step' in result['message']


class TestWorkflowServiceStopStep:
    """Test stop_step method."""
    
    def test_stop_step_without_app_state(self):
        """Test stop_step raises error when WorkflowState is unavailable."""
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            with pytest.raises(RuntimeError, match="WorkflowService cannot access workflow state"):
                WorkflowService.stop_step('STEP1')
    
    def test_stop_step_nonexistent(self):
        """Test stop_step with nonexistent step."""
        mock_state = Mock()
        mock_state.get_step_info.return_value = {}
        with patched_workflow_state(mock_state):
            with pytest.raises(ValueError, match="not found"):
                WorkflowService.stop_step('NONEXISTENT')
    
    def test_stop_step_not_running(self):
        """Test stop_step when step is not running."""
        mock_state = Mock()
        mock_state.get_step_info.return_value = {'status': 'idle'}
        with patched_workflow_state(mock_state):
            result = WorkflowService.stop_step('STEP1')
            
            assert result['status'] == 'error'
            assert 'not running' in result['message']
    
    def test_stop_step_no_process(self):
        """Test stop_step when no process exists."""
        mock_state = Mock()
        mock_state.get_step_info.return_value = {'status': 'running'}
        mock_state.get_step_process.return_value = None
        with patched_workflow_state(mock_state):
            result = WorkflowService.stop_step('STEP1')
            
            assert result['status'] == 'error'
            assert 'No process found' in result['message']
    
    def test_stop_step_success(self):
        """Test successful stop_step."""
        mock_process = Mock()
        
        mock_state = Mock()
        mock_state.get_step_info.return_value = {'status': 'running'}
        mock_state.get_step_process.return_value = mock_process
        
        with patched_workflow_state(mock_state):
            result = WorkflowService.stop_step('STEP1')
            
            assert result['status'] == 'success'
            mock_process.terminate.assert_called_once()
            mock_state.update_step_info.assert_called_once_with(
                'STEP1',
                status='stopped',
                return_code=-1
            )


class TestWorkflowServiceSequenceOperations:
    """Test sequence-related methods."""
    
    def test_get_sequence_status_without_app_state(self):
        """Test get_sequence_status handles missing workflow state."""
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            result = WorkflowService.get_sequence_status()
            
            assert result['is_running'] is False
            assert 'error' in result
    
    def test_get_sequence_status_success(self):
        """Test successful get_sequence_status."""
        mock_workflow_state = build_workflow_state(
            is_sequence_running=True,
            all_steps_info={
                'STEP1': {'status': 'completed'},
                'STEP2': {'status': 'running'},
                'STEP3': {'status': 'idle'}
            },
            sequence_outcome={'status': 'running'}
        )
        
        with patched_workflow_state(mock_workflow_state):
            result = WorkflowService.get_sequence_status()
            
            assert result['is_running'] is True
            assert result['current_step'] == 'STEP2'
            assert result['progress']['current'] == 1  # One completed
            assert result['progress']['total'] == 3
    
    def test_stop_sequence_not_running(self):
        """Test stop_sequence when no sequence is running."""
        workflow_state = build_workflow_state(is_sequence_running=False)
        
        with patched_workflow_state(workflow_state):
            result = WorkflowService.stop_sequence()
            
            assert result['status'] == 'error'
            assert 'Aucune séquence' in result['message']
    
    def test_stop_sequence_success(self):
        """Test successful stop_sequence."""
        mock_process = Mock()
        
        workflow_state = build_workflow_state(
            is_sequence_running=True,
            all_steps_info={
                'STEP1': {'status': 'running'},
                'STEP2': {'status': 'idle'}
            },
            step_process=mock_process
        )
        workflow_state.get_step_process.return_value = mock_process
        
        with patched_workflow_state(workflow_state):
            result = WorkflowService.stop_sequence()
            
            assert result['status'] == 'success'
            assert 'STEP1' in result['message']
            workflow_state.complete_sequence.assert_called_once()
            mock_process.terminate.assert_called_once()


class TestWorkflowServiceStatusSummary:
    """Test get_current_workflow_status_summary."""
    
    def test_status_summary_without_app_state(self):
        """Test status summary handles missing workflow state."""
        with patch('services.workflow_service.get_workflow_state', return_value=None):
            result = WorkflowService.get_current_workflow_status_summary()
            
            assert result['is_sequence_running'] is False
            assert 'error' in result
    
    def test_status_summary_success(self):
        """Test successful status summary."""
        mock_workflow_state = build_workflow_state(
            is_sequence_running=False,
            all_steps_info={
                'STEP1': {
                    'status': 'completed',
                    'progress_current': 10,
                    'progress_total': 10,
                    'return_code': 0
                },
                'STEP2': {
                    'status': 'idle',
                    'progress_current': 0,
                    'progress_total': 0,
                    'return_code': None
                }
            },
            sequence_outcome={'status': 'success'}
        )
        
        with patched_workflow_state(mock_workflow_state):
            result = WorkflowService.get_current_workflow_status_summary()
            
            assert result['is_sequence_running'] is False
            assert len(result['steps']) == 2
            assert result['steps']['STEP1']['status'] == 'completed'
            assert result['steps']['STEP2']['status'] == 'idle'
            assert result['last_sequence_outcome']['status'] == 'success'
            assert 'timestamp' in result


class TestWorkflowServiceCreateTrackingTempFile:
    """Test create_tracking_temp_file method."""
    
    def test_creates_file_with_raw_list_format(self):
        """Test that create_tracking_temp_file writes a raw JSON list."""
        import json
        import os
        
        test_videos = [
            "/path/to/video1.mp4",
            "/path/to/video2.mov",
            "/path/to/video3.avi"
        ]
        
        temp_file = None
        try:
            temp_file = WorkflowService.create_tracking_temp_file(test_videos)
            
            # Verify file exists
            assert temp_file.exists()
            assert temp_file.suffix == '.json'
            assert 'tracking_videos_' in temp_file.name
            
            # Verify content is a raw list (not wrapped in object)
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert isinstance(data, list), "Expected raw JSON list, not object"
            assert data == test_videos
            assert len(data) == 3
            
        finally:
            # Cleanup
            if temp_file and temp_file.exists():
                os.unlink(temp_file)
    
    def test_creates_empty_list_when_no_videos(self):
        """Test that empty video list creates valid empty JSON array."""
        import json
        import os
        
        test_videos = []
        
        temp_file = None
        try:
            temp_file = WorkflowService.create_tracking_temp_file(test_videos)
            
            # Verify file exists and contains empty list
            assert temp_file.exists()
            
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert isinstance(data, list)
            assert len(data) == 0
            
        finally:
            if temp_file and temp_file.exists():
                os.unlink(temp_file)
    
    def test_file_content_is_valid_json(self):
        """Test that created file contains valid, parseable JSON."""
        import json
        import os
        
        test_videos = ["/test/video.mp4"]
        
        temp_file = None
        try:
            temp_file = WorkflowService.create_tracking_temp_file(test_videos)
            
            # Should not raise JSONDecodeError
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data == test_videos
            
        finally:
            if temp_file and temp_file.exists():
                os.unlink(temp_file)
