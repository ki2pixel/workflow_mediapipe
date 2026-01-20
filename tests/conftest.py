import os
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--step5-gpu-log",
        action="store",
        default=None,
        help="Path to a STEP5 worker GPU log to validate (optional).",
    )


# Ensure project root is on sys.path for 'config' and 'services' imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_sessionstart(session):
    """Set deterministic environment defaults for tests.
    Individual tests can override these before importing modules.
    """
    # Safety: prevent any real downloads or external side-effects in CI/tests
    os.environ.setdefault('DRY_RUN_DOWNLOADS', 'true')

    # Do not force BASE_PATH_SCRIPTS_ENV here globally; tests that need isolation
    # should set it to a tmp_path BEFORE importing modules that read config.
    # This keeps behavior explicit and avoids surprising path leaks.


# Standard fixtures for test patterns
@pytest.fixture
def mock_workflow_state():
    """Mock WorkflowState with sensible defaults."""
    from services.workflow_state import WorkflowState
    return Mock(spec=WorkflowState)


@pytest.fixture
def mock_app(mock_workflow_state):
    """Mock app_new module with workflow_state."""
    app = Mock()
    app.workflow_state = mock_workflow_state
    app.run_process_async = Mock()
    app.execute_step_sequence_worker = Mock()
    return app


@pytest.fixture(scope="session")
def transnet_env_info():
    """Information about TransNet environment for STEP3 tests."""
    return {
        "env_path": "/mnt/venv_ext4/transnet_env",
        "required_modules": ["torch", "transnetv2_pytorch"],
        "test_files": ["test_step3_transnet.py"]
    }


@pytest.fixture(scope="session")
def tracking_env_info():
    """Information about Tracking environment for STEP5 tests."""
    return {
        "env_path": "/mnt/venv_ext4/tracking_env",
        "required_modules": ["numpy", "cv2", "mediapipe"],
        "test_files": ["test_step5_*.py", "test_tracking_optimizations_*.py"]
    }
