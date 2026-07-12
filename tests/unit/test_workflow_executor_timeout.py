# -*- coding: utf-8 -*-
"""
Unit tests for WorkflowExecutor subprocess timeout handling.
"""
import subprocess
import pytest
from unittest import mock
from services.workflow_executor import _run_process_async_internal
from services.workflow_state import get_workflow_state
from services.types import StepStatus

@pytest.fixture
def clean_state():
    state = get_workflow_state()
    state.initialize_all_steps(['STEP1'])
    yield state
    state.initialize_all_steps(['STEP1'])  # clean up

@mock.patch('services.workflow_executor.subprocess.Popen')
@mock.patch('services.workflow_executor.WorkflowCommandsConfig')
@mock.patch('services.workflow_executor.Path.mkdir')
@mock.patch('services.workflow_executor.open')
def test_subprocess_timeout_expired(mock_open, mock_mkdir, MockCommandsConfig, MockPopen, clean_state):
    """
    Given a step execution
    When the subprocess times out
    Then it should be terminated, killed, and status set to FAILED with return code -9
    """
    # Mock step config
    step_config = {
        'display_name': 'Test Step',
        'cmd': ['python', '-c', 'import time; time.sleep(10)'],
        'cwd': '.',
        'timeout': 1  # 1 second timeout
    }
    commands_config_instance = MockCommandsConfig.return_value
    commands_config_instance.get_step_config.return_value = step_config

    # Mock Popen process
    mock_process = mock.Mock()
    # Mock wait() to raise TimeoutExpired for first two calls, and succeed for third call
    mock_process.wait.side_effect = [
        subprocess.TimeoutExpired(cmd=step_config['cmd'], timeout=1),
        subprocess.TimeoutExpired(cmd=step_config['cmd'], timeout=5),
        0
    ]
    mock_process.pid = 99999
    mock_process.returncode = None
    MockPopen.return_value = mock_process

    # Run execution
    # We patch the import of workflow_commands_config in services.workflow_executor
    with mock.patch('services.workflow_executor.workflow_commands_config', commands_config_instance):
        _run_process_async_internal('STEP1')

    # Verify status in WorkflowState
    step_info = clean_state.get_step_info('STEP1')
    assert step_info['status'] == StepStatus.FAILED.value
    assert step_info['return_code'] == -9

    # Verify terminate() and kill() were called
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()
