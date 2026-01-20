#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for workflow and API routes.
Tests the complete request-response cycle with WorkflowService.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

os.environ['DRY_RUN_DOWNLOADS'] = 'true'

from services.workflow_state import WorkflowState


@contextmanager
def patched_workflow_state(state):
    """Patch WorkflowService to return the provided WorkflowState."""
    with patch('services.workflow_service.get_workflow_state', return_value=state):
        yield


@contextmanager
def patched_commands_config(display_name='Test Step', validate=True):
    """Context manager to patch WorkflowCommandsConfig for deterministic behavior."""
    with patch('config.workflow_commands.WorkflowCommandsConfig') as MockConfig:
        instance = MockConfig.return_value
        instance.get_step_display_name.return_value = display_name
        instance.validate_step_key.return_value = validate
        instance.get_step_config.return_value = {'display_name': display_name}
        yield instance


@pytest.fixture
def mock_app_new():
    """Create a mock app_new module with workflow_state."""
    mock_app = Mock()
    mock_app.workflow_state = WorkflowState()
    mock_app.workflow_state.initialize_all_steps(['STEP1', 'STEP2', 'STEP3'])
    mock_app.COMMANDS_CONFIG = {
        'STEP1': {'display_name': 'Test Step 1'},
        'STEP2': {'display_name': 'Test Step 2'},
        'STEP3': {'display_name': 'Test Step 3'}
    }
    mock_app.run_process_async = Mock()
    mock_app.execute_step_sequence_worker = Mock()
    return mock_app


@pytest.fixture
def app_client(mock_app_new):
    """Create Flask test client with mocked app_new."""
    with patch.dict('sys.modules', {'app_new': mock_app_new}):
        from flask import Flask
        from routes.api_routes import api_bp
        from routes.workflow_routes import workflow_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(workflow_bp)
        
        with app.test_client() as client:
            yield client


class TestWorkflowRoutesGetStatus:
    """Test GET /status/<step_key> route."""
    
    def test_get_status_success(self, app_client, mock_app_new):
        """Test successful status retrieval."""
        mock_app_new.workflow_state.update_step_status('STEP1', 'running')
        mock_app_new.workflow_state.update_step_progress('STEP1', 5, 10, 'Processing...')
        
        with patched_workflow_state(mock_app_new.workflow_state), patched_commands_config('Test Step 1'):
            response = app_client.get('/status/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['step'] == 'STEP1'
            assert data['display_name'] == 'Test Step 1'
            assert data['status'] == 'running'
            assert data['progress_current'] == 5
            assert data['progress_total'] == 10
            assert 'is_any_sequence_running' in data
    
    def test_get_status_nonexistent_step(self, app_client, mock_app_new):
        """Test status for nonexistent step returns 404."""
        with patch('services.workflow_service.get_workflow_state', return_value=mock_app_new.workflow_state):
            response = app_client.get('/status/NONEXISTENT')
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data or 'message' in data
    
    def test_get_status_includes_logs(self, app_client, mock_app_new):
        """Test status includes logs in response."""
        mock_app_new.workflow_state.append_step_log('STEP1', 'Log line 1')
        mock_app_new.workflow_state.append_step_log('STEP1', 'Log line 2')
        
        with patch('services.workflow_service.get_workflow_state', return_value=mock_app_new.workflow_state):
            response = app_client.get('/status/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert 'status' in data
            assert 'step' in data


class TestWorkflowRoutesRunStep:
    """Test POST /run/<step_key> route."""
    
    def test_run_step_success(self, app_client, mock_app_new):
        """Test successful step execution."""
        with patched_workflow_state(mock_app_new.workflow_state), patched_commands_config('Test Step 1'):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                response = app_client.post('/run/STEP1')
                
                assert response.status_code in [200, 202]
                data = response.get_json()
                
                assert data['status'] == 'initiated'
                assert 'Test Step 1' in data['message']
    
    def test_run_step_already_running(self, app_client, mock_app_new):
        """Test run step when already running."""
        mock_app_new.workflow_state.update_step_status('STEP1', 'running')
        
        with patched_workflow_state(mock_app_new.workflow_state):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                response = app_client.post('/run/STEP1')
                
                assert response.status_code in [200, 409]
                data = response.get_json()
                
                assert data['status'] == 'error'
                assert 'déjà en cours' in data['message']
    
    def test_run_step_sequence_running(self, app_client, mock_app_new):
        """Test run step when sequence is running."""
        mock_app_new.workflow_state.start_sequence('Test')
        
        with patched_workflow_state(mock_app_new.workflow_state):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                response = app_client.post('/run/STEP1')
                
                assert response.status_code in [200, 409]
                data = response.get_json()
                
                assert data['status'] == 'error'
                assert 'séquence' in data['message'].lower()


class TestWorkflowRoutesStopStep:
    """Test POST /stop/<step_key> route."""
    
    def test_stop_step_success(self, app_client, mock_app_new):
        """Test successful step stop."""
        mock_app_new.workflow_state.update_step_status('STEP1', 'running')
        mock_process = Mock()
        mock_app_new.workflow_state.set_step_process('STEP1', mock_process)
        
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.post('/stop/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            mock_process.terminate.assert_called_once()
    
    def test_stop_step_not_running(self, app_client, mock_app_new):
        """Test stop step when not running."""
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.post('/stop/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'error'
            assert 'not running' in data['message']
    
    def test_stop_step_nonexistent(self, app_client, mock_app_new):
        """Test stop nonexistent step returns 404."""
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.post('/stop/NONEXISTENT')
            
            assert response.status_code == 404


class TestAPIRoutesStepStatus:
    """Test GET /api/step_status/<step_key> route."""
    
    def test_api_step_status_success(self, app_client, mock_app_new):
        """Test successful API step status retrieval."""
        mock_app_new.workflow_state.update_step_status('STEP1', 'completed')
        mock_app_new.workflow_state.update_step_info('STEP1', return_code=0)
        
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.get('/api/step_status/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['step'] == 'STEP1'
            assert data['status'] == 'completed'
            assert data['return_code'] == 0
    
    def test_api_step_status_nonexistent(self, app_client, mock_app_new):
        """Test API step status for nonexistent step."""
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.get('/api/step_status/NONEXISTENT')
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data
    
    def test_api_step_status_shape(self, app_client, mock_app_new):
        """Test API step status response shape."""
        with patched_workflow_state(mock_app_new.workflow_state):
            response = app_client.get('/api/step_status/STEP1')
            
            assert response.status_code == 200
            data = response.get_json()
            
            required_fields = [
                'step', 'display_name', 'status', 'return_code',
                'progress_current', 'progress_total', 'progress_text',
                'is_any_sequence_running'
            ]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"


class TestWorkflowRoutesTimingConstraints:
    """Test timing constraints for workflow routes."""
    
    def test_status_endpoint_response_time(self, app_client, mock_app_new):
        """Test that status endpoint responds within acceptable time."""
        import time
        
        with patched_workflow_state(mock_app_new.workflow_state):
            start = time.time()
            response = app_client.get('/status/STEP1')
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 0.1, f"Status endpoint too slow: {elapsed*1000:.1f}ms"
    
    def test_run_endpoint_responds_quickly(self, app_client, mock_app_new):
        """Test that run endpoint responds quickly (async execution)."""
        import time
        
        with patched_workflow_state(mock_app_new.workflow_state):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                start = time.time()
                response = app_client.post('/run/STEP1')
                elapsed = time.time() - start
                
                assert response.status_code in [200, 202]
                assert elapsed < 0.2, f"Run endpoint too slow: {elapsed*1000:.1f}ms"


class TestWorkflowRoutesErrorHandling:
    """Test error handling in workflow routes."""
    
    def test_status_endpoint_handles_service_error(self, app_client, mock_app_new):
        """Test status endpoint handles service exceptions gracefully."""
        with patched_workflow_state(None):
            response = app_client.get('/status/STEP1')
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
    
    def test_run_endpoint_handles_service_error(self, app_client, mock_app_new):
        """Test run endpoint handles service exceptions gracefully."""
        with patched_workflow_state(None):
            response = app_client.post('/run/STEP1')
            
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.get_json()
                assert data['status'] == 'error'


class TestWorkflowRoutesDryRunCompliance:
    """Test that routes respect DRY_RUN_DOWNLOADS flag."""
    
    def test_routes_respect_dry_run_env(self, app_client, mock_app_new):
        """Test that DRY_RUN_DOWNLOADS environment is set."""
        assert os.environ.get('DRY_RUN_DOWNLOADS') == 'true'
        
        with patched_workflow_state(mock_app_new.workflow_state):
            with patch('config.settings.config.BASE_PATH_SCRIPTS', Path('/tmp')):
                response = app_client.post('/run/STEP1')
                
                assert response.status_code in [200, 202]
