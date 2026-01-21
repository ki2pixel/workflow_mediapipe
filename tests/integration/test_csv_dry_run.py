"""
Integration tests for DRY_RUN_DOWNLOADS guard in CSVService._check_csv_for_downloads.

Ensures that when DRY_RUN_DOWNLOADS=true, no real download workers are started
and the history is still updated to avoid duplicate processing.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch
from types import ModuleType
from unittest.mock import MagicMock

# Add project root to Python path (consistent with other integration tests)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_csv_dry_run_prevents_worker(monkeypatch, tmp_path):
    monkeypatch.setenv("BASE_PATH_SCRIPTS_ENV", str(tmp_path))
    monkeypatch.setenv("DRY_RUN_DOWNLOADS", "true")

    # This test must not rely on a previously imported services.csv_service module,
    # because other integration tests may delete/reload it via sys.modules.
    for mod in ['config.settings', 'services.webhook_service', 'services.download_history_repository', 'services.csv_service']:
        if mod in sys.modules:
            del sys.modules[mod]

    import services.csv_service as csv_service_module
    CSVService = csv_service_module.CSVService

    # Mock Webhook returning one new Dropbox record
    webhook_data = [{
        'url': 'https://dropbox.com/dry-run-file.zip',
        'timestamp': '2025-07-27 12:00:00',
        'source': 'webhook',
        'original_filename': 'dry-run-file.zip'
    }]
    
    from services.workflow_state import reset_workflow_state
    reset_workflow_state()

    with patch.object(csv_service_module, 'webhook_fetch_records', return_value=webhook_data):
        dummy_app_new = ModuleType('app_new')
        dummy_app_new.execute_csv_download_worker = MagicMock()
        sys.modules['app_new'] = dummy_app_new
        try:
            CSVService._check_csv_for_downloads()
            dummy_app_new.execute_csv_download_worker.assert_not_called()
        finally:
            sys.modules.pop('app_new', None)

    history = CSVService.get_download_history()
    assert len(history) == 1


def test_csv_non_eligible_links_are_ignored(monkeypatch, tmp_path):
    """Non-eligible webhook entries must not create manual UI items nor write history."""
    monkeypatch.setenv("BASE_PATH_SCRIPTS_ENV", str(tmp_path))
    monkeypatch.setenv("DRY_RUN_DOWNLOADS", "true")

    for mod in ['config.settings', 'services.webhook_service', 'services.download_history_repository', 'services.csv_service']:
        if mod in sys.modules:
            del sys.modules[mod]

    import services.csv_service as csv_service_module
    CSVService = csv_service_module.CSVService

    webhook_data = [
        {
            'url': 'https://fromsmash.com/some-file',
            'timestamp': '2025-07-27 12:00:00',
            'source': 'webhook',
            'provider': 'FromSmash',
        },
        {
            # Dropbox-like but missing new schema hints (no original_filename/fallback_url, not a proxy)
            'url': 'https://www.dropbox.com/s/abc123/file.zip?dl=1',
            'timestamp': '2025-07-27 12:01:00',
            'source': 'webhook',
            'provider': 'dropbox',
        },
    ]

    from services.workflow_state import reset_workflow_state
    reset_workflow_state()

    with patch.object(csv_service_module, 'webhook_fetch_records', return_value=webhook_data):
        with patch.object(CSVService, 'add_csv_download') as mock_add_download:
            with patch.object(CSVService, 'update_csv_download') as mock_update_download:
                dummy_app_new = ModuleType('app_new')
                dummy_app_new.execute_csv_download_worker = MagicMock()
                sys.modules['app_new'] = dummy_app_new
                try:
                    CSVService._check_csv_for_downloads()
                    dummy_app_new.execute_csv_download_worker.assert_not_called()
                finally:
                    sys.modules.pop('app_new', None)

    history = CSVService.get_download_history()
    assert len(history) == 0
    mock_add_download.assert_not_called()
    mock_update_download.assert_not_called()
