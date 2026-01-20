import os
import sys
import importlib
from pathlib import Path


def reload_with_base(tmp_path):
    os.environ['BASE_PATH_SCRIPTS_ENV'] = str(tmp_path)
    # Ensure clean module state
    for mod in ['config.settings', 'services.csv_service']:
        if mod in sys.modules:
            del sys.modules[mod]
    settings = importlib.import_module('config.settings')
    importlib.reload(settings)
    csv_service = importlib.import_module('services.csv_service')
    importlib.reload(csv_service)
    return settings, csv_service


def test_normalize_url_variants(tmp_path):
    settings, csv_service = reload_with_base(tmp_path)
    normalize = csv_service.CSVService._normalize_url

    base = 'https://www.dropbox.com/scl/fo/abc123/SomeFolder?rlkey=XYZ'
    variants = [
        base + '&dl=1',
        base + '&dl=1&dl=1',
        base.replace('rlkey=XYZ&dl=1', 'dl=1&rlkey=XYZ'),
        base + '&dl=1#fragment',
        base.replace('www.dropbox.com', 'WWW.DROPBOX.COM') + '&dl=1',
        base + '&dl=1&extra=val',
    ]

    normalized = [normalize(u) for u in variants]
    # All must include dl=1 once and be equal except additional extra param variant
    core = [u for u in normalized if 'extra=val' not in u]
    assert len(set(core)) == 1, f"Normalization mismatch: {set(core)}"
    assert core[0].count('dl=1') == 1


def test_normalize_double_encoded_urls(tmp_path):
    """Test normalization of URLs with double-encoded sequences (e.g., amp%3Bdl=0)."""
    settings, csv_service = reload_with_base(tmp_path)
    normalize = csv_service.CSVService._normalize_url

    # Real-world case from download_history.json showing duplicate downloads
    base_url = 'https://www.dropbox.com/scl/fo/oy6vg46u1vrdhsk080zs9/ALlPIDw5bpPaOMSZRVMZVUs'
    
    # Variant 1: Malformed with double-encoded ampersand + dl=0 (causes 400 error)
    malformed = base_url + '?amp%3Bdl=0&dl=1&rlkey=itwttqb1mwptzr8zyenucbj93'
    
    # Variant 2: Clean version with proper dl=1
    clean = base_url + '?dl=1&rlkey=itwttqb1mwptzr8zyenucbj93'
    
    # Both should normalize to the same URL
    norm_malformed = normalize(malformed)
    norm_clean = normalize(clean)
    
    assert norm_malformed == norm_clean, f"Expected same normalized URL:\nMalformed: {norm_malformed}\nClean: {norm_clean}"
    assert norm_malformed.count('dl=1') == 1, f"Expected exactly one dl=1, got: {norm_malformed}"
    assert 'amp%3B' not in norm_malformed, f"Double-encoded sequence should be cleaned: {norm_malformed}"
    assert 'dl=0' not in norm_malformed, f"Invalid dl=0 param should be removed: {norm_malformed}"


def test_normalize_various_double_encoded_patterns(tmp_path):
    """Test various patterns of double-encoded URLs."""
    settings, csv_service = reload_with_base(tmp_path)
    normalize = csv_service.CSVService._normalize_url

    test_cases = [
        # Case 1: amp%3B prefix (most common)
        (
            'https://www.dropbox.com/file?amp%3Bparam=value&other=test',
            'https://www.dropbox.com/file?dl=1&other=test&param=value'
        ),
        # Case 2: Multiple amp%3B sequences
        (
            'https://www.dropbox.com/file?amp%3Ba=1&amp%3Bb=2&dl=1',
            'https://www.dropbox.com/file?a=1&b=2&dl=1'
        ),
        # Case 3: Mixed case encoding
        (
            'https://www.dropbox.com/file?amp%3BDL=0&dl=1&rlkey=test',
            'https://www.dropbox.com/file?dl=1&rlkey=test'
        ),
    ]

    for malformed, expected_pattern in test_cases:
        result = normalize(malformed)
        # Check that key properties match expected pattern
        assert 'amp%3B' not in result.lower(), f"Double-encoded amp should be cleaned: {result}"
        assert result.count('dl=1') == 1, f"Expected exactly one dl=1: {result}"


def test_history_dedup_on_save_and_load(tmp_path):
    settings, csv_service = reload_with_base(tmp_path)
    history_file = settings.config.BASE_PATH_SCRIPTS / 'download_history.json'
    history_file.parent.mkdir(parents=True, exist_ok=True)

    # Write two variants of the same logical URL
    raw = [
        {
            'url': 'https://www.dropbox.com/scl/fo/token123/Name?rlkey=AA&dl=1',
            'timestamp': '2025-10-13 10:00:00'
        },
        {
            'url': 'https://www.dropbox.com/scl/fo/token123/Name?dl=1&rlkey=AA',
            'timestamp': '2025-10-13 11:00:00'
        }
    ]
    history_file.write_text(__import__('json').dumps(raw), encoding='utf-8')

    # Initialize triggers migration + normalization
    csv_service.CSVService.initialize()

    # Load set should have only one entry for the token
    urls = csv_service.CSVService.get_download_history()
    assert len(urls) == 1

    # File content should be structured and deduplicated
    data = __import__('json').loads(history_file.read_text(encoding='utf-8'))
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['url'].count('dl=1') == 1


def test_history_dedup_with_double_encoded_urls(tmp_path):
    """Test that double-encoded URL variants are properly deduplicated in history."""
    settings, csv_service = reload_with_base(tmp_path)
    history_file = settings.config.BASE_PATH_SCRIPTS / 'download_history.json'
    history_file.parent.mkdir(parents=True, exist_ok=True)

    # Simulate the real-world bug: same URL with malformed and clean variants
    raw = [
        {
            'url': 'https://www.dropbox.com/scl/fo/adiekb4eb33kthz1i4ynt/AFMG4tzu_M-74n9KxUNFq10?amp%3Bdl=0&dl=1&rlkey=f2m5oyg4gpkkwmqwcmn3sv993',
            'timestamp': '2025-10-27 11:04:16'
        },
        {
            'url': 'https://www.dropbox.com/scl/fo/adiekb4eb33kthz1i4ynt/AFMG4tzu_M-74n9KxUNFq10?dl=1&rlkey=f2m5oyg4gpkkwmqwcmn3sv993',
            'timestamp': '2025-10-27 11:04:16'
        }
    ]
    history_file.write_text(__import__('json').dumps(raw), encoding='utf-8')

    # Initialize triggers migration + normalization
    csv_service.CSVService.initialize()

    # Load set should have only one entry (duplicates removed)
    urls = csv_service.CSVService.get_download_history()
    assert len(urls) == 1, f"Expected 1 unique URL after dedup, got {len(urls)}"

    # File content should be deduplicated
    data = __import__('json').loads(history_file.read_text(encoding='utf-8'))
    assert isinstance(data, list)
    assert len(data) == 1, f"Expected 1 entry in history file, got {len(data)}"
    
    # The normalized URL should not contain malformed sequences
    saved_url = data[0]['url']
    assert 'amp%3B' not in saved_url.lower(), f"Double-encoded sequence should be cleaned: {saved_url}"
    assert saved_url.count('dl=1') == 1, f"Expected exactly one dl=1: {saved_url}"
