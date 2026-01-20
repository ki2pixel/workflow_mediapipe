"""
Integration test for double-encoded URL handling in CSV monitoring.

This test validates that URLs with double-encoded sequences (e.g., amp%3Bdl=0)
do not trigger duplicate downloads when processed by the monitoring system.
"""
import os
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import ModuleType


def test_double_encoded_urls_no_duplicate_download(tmp_path):
    """Test that malformed and clean URL variants are treated as duplicates."""
    # Setup test environment
    os.environ['BASE_PATH_SCRIPTS_ENV'] = str(tmp_path)
    os.environ['DRY_RUN_DOWNLOADS'] = 'true'

    # Clean up module cache
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith('services.') or mod.startswith('config.'):
            del sys.modules[mod]

    # Import after env setup
    from services.csv_service import CSVService
    from config.settings import config
    
    # Initialize service
    CSVService.initialize()
    
    # Simulate webhook data with double-encoded URLs
    base_url = 'https://www.dropbox.com/scl/fo/test123/TestFolder'
    malformed_url = base_url + '?amp%3Bdl=0&dl=1&rlkey=testkey'
    clean_url = base_url + '?dl=1&rlkey=testkey'
    
    webhook_data = [
        {
            'url': malformed_url,
            'timestamp': '2025-10-27 10:00:00',
            'source': 'webhook',
            'url_type': 'dropbox',
            'original_filename': 'Test.zip'
        },
        {
            'url': clean_url,
            'timestamp': '2025-10-27 10:00:01',
            'source': 'webhook',
            'url_type': 'dropbox',
            'original_filename': 'Test.zip'
        }
    ]
    
    download_count = 0
    
    def mock_execute_csv_download_worker(url, timestamp, fallback_url=None, original_filename=None):
        nonlocal download_count
        download_count += 1
    
    # Provide a lightweight dummy app_new module so patching doesn't import the real Flask app.
    dummy_app_new = ModuleType('app_new')
    dummy_app_new.execute_csv_download_worker = lambda *args, **kwargs: None
    import sys
    sys.modules['app_new'] = dummy_app_new

    try:
        # Mock the download worker (it's imported in csv_service from app_new)
        with patch('app_new.execute_csv_download_worker', side_effect=mock_execute_csv_download_worker) as mock_execute:
            with patch('services.csv_service.webhook_fetch_records', return_value=webhook_data):
                # Trigger check in DRY RUN mode (no worker threads, history is updated)
                CSVService._check_csv_for_downloads()

        # Verify no real worker was started in dry-run mode
        mock_execute.assert_not_called()
    finally:
        sys.modules.pop('app_new', None)
    
    # Verify history contains only one normalized entry
    history = CSVService.get_download_history()
    assert len(history) == 1, f"Expected 1 entry in history, got {len(history)}"
    
    # Verify the normalized URL doesn't contain malformed sequences
    normalized = list(history)[0]
    assert 'amp%3B' not in normalized.lower(), f"Malformed sequence in normalized URL: {normalized}"
    assert normalized.count('dl=1') == 1, f"Expected exactly one dl=1: {normalized}"


def test_csv_monitoring_dedup_across_batches(tmp_path):
    """Test that duplicate URLs across multiple monitoring cycles are detected."""
    os.environ['BASE_PATH_SCRIPTS_ENV'] = str(tmp_path)
    os.environ['DRY_RUN_DOWNLOADS'] = 'true'

    # Clean up module cache
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith('services.') or mod.startswith('config.'):
            del sys.modules[mod]

    from services.csv_service import CSVService
    
    CSVService.initialize()
    
    base_url = 'https://www.dropbox.com/scl/fo/abc/Folder'
    
    # First batch with malformed URL
    batch1 = [
        {
            'url': base_url + '?amp%3Bdl=0&dl=1&rlkey=key1',
            'timestamp': '2025-10-27 10:00:00',
            'source': 'webhook',
            'url_type': 'dropbox',
            'original_filename': 'Test.zip'
        }
    ]
    
    # Second batch with clean URL (same logical resource)
    batch2 = [
        {
            'url': base_url + '?dl=1&rlkey=key1',
            'timestamp': '2025-10-27 10:05:00',
            'source': 'webhook',
            'url_type': 'dropbox',
            'original_filename': 'Test.zip'
        }
    ]
    
    download_count = 0
    
    def mock_download(url, timestamp, fallback_url=None, original_filename=None):
        nonlocal download_count
        download_count += 1
    
    dummy_app_new = ModuleType('app_new')
    dummy_app_new.execute_csv_download_worker = lambda *args, **kwargs: None
    import sys
    sys.modules['app_new'] = dummy_app_new

    try:
        with patch('app_new.execute_csv_download_worker', side_effect=mock_download) as mock_execute:
            # First check - should record in history (dry-run) and avoid starting worker
            with patch('services.csv_service.webhook_fetch_records', return_value=batch1):
                CSVService._check_csv_for_downloads()

            # Second check - should NOT trigger anything (duplicate detected via history)
            with patch('services.csv_service.webhook_fetch_records', return_value=batch2):
                CSVService._check_csv_for_downloads()

            mock_execute.assert_not_called()
    finally:
        sys.modules.pop('app_new', None)
    
    # Verify history
    history = CSVService.get_download_history()
    assert len(history) == 1, f"Expected 1 unique entry, got {len(history)}"


def test_real_world_urls_from_history():
    """Test normalization using actual problematic URLs from download_history.json."""
    from services.csv_service import CSVService
    
    # Real-world cases that caused duplicate downloads
    test_cases = [
        # Case 1: Lines 514-517 from download_history.json
        (
            'https://www.dropbox.com/scl/fo/oy6vg46u1vrdhsk080zs9/ALlPIDw5bpPaOMSZRVMZVUs?amp%3Bdl=0&dl=1&rlkey=itwttqb1mwptzr8zyenucbj93',
            'https://www.dropbox.com/scl/fo/oy6vg46u1vrdhsk080zs9/ALlPIDw5bpPaOMSZRVMZVUs?dl=1&rlkey=itwttqb1mwptzr8zyenucbj93'
        ),
        # Case 2: Lines 522-529
        (
            'https://www.dropbox.com/scl/fo/adiekb4eb33kthz1i4ynt/AFMG4tzu_M-74n9KxUNFq10?amp%3Bdl=0&dl=1&rlkey=f2m5oyg4gpkkwmqwcmn3sv993',
            'https://www.dropbox.com/scl/fo/adiekb4eb33kthz1i4ynt/AFMG4tzu_M-74n9KxUNFq10?dl=1&rlkey=f2m5oyg4gpkkwmqwcmn3sv993'
        ),
    ]
    
    for malformed, clean in test_cases:
        norm_malformed = CSVService._normalize_url(malformed)
        norm_clean = CSVService._normalize_url(clean)
        
        assert norm_malformed == norm_clean, (
            f"URLs should normalize to same value:\n"
            f"  Malformed: {norm_malformed}\n"
            f"  Clean:     {norm_clean}"
        )
        
        # Verify cleaning
        assert 'amp%3B' not in norm_malformed.lower()
        assert 'dl=0' not in norm_malformed
        assert norm_malformed.count('dl=1') == 1
