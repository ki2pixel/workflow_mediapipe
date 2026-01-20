import os
import sys
import json
import importlib
from types import ModuleType


def setup_tmp_base(tmp_path):
    os.environ['BASE_PATH_SCRIPTS_ENV'] = str(tmp_path)
    # Clean module cache for a fresh config and service import
    for mod in ['config.settings', 'services.csv_service']:
        if mod in sys.modules:
            del sys.modules[mod]
    settings = importlib.import_module('config.settings')
    importlib.reload(settings)
    csv_service = importlib.import_module('services.csv_service')
    importlib.reload(csv_service)
    return settings, csv_service


def test_monitor_does_not_retrigger_for_normalized_duplicate(tmp_path):
    settings, csv_service = setup_tmp_base(tmp_path)

    # Prepare history file with canonical URL (normalized)
    hist_file = settings.config.BASE_PATH_SCRIPTS / 'download_history.json'
    hist_file.parent.mkdir(parents=True, exist_ok=True)

    canonical = 'https://www.dropbox.com/scl/fo/tokenABC/Folder?dl=1&rlkey=KEY'
    data = [{
        'url': canonical,
        'timestamp': '2025-10-13 12:00:00'
    }]
    hist_file.write_text(json.dumps(data), encoding='utf-8')

    # Prepare a dummy app_new module with fetch_csv_data and a sentinel for download worker
    dummy = ModuleType('app_new')
    started = []

    def execute_csv_download_worker(url, ts, fallback_url=None, original_filename=None):
        started.append((url, ts, fallback_url, original_filename))

    def fetch_csv_data():
        # Variant order to simulate duplicate input
        return [{'timestamp': '2025-10-13 13:00:00', 'url': 'https://www.dropbox.com/scl/fo/tokenABC/Folder?rlkey=KEY&dl=1'}]

    dummy.execute_csv_download_worker = execute_csv_download_worker
    dummy.fetch_csv_data = fetch_csv_data
    sys.modules['app_new'] = dummy

    try:
        # Sanity: history contains exactly one URL (normalized by service on read)
        urls = csv_service.CSVService.get_download_history()
        assert len(urls) == 1

        # Run monitor check; should detect no new download since URL normalizes equal
        csv_service.CSVService._check_csv_for_downloads()

        # Assert no worker started
        assert started == [], f"Download worker should not have started, got: {started}"

        # History should remain single entry
        urls_after = csv_service.CSVService.get_download_history()
        assert len(urls_after) == 1

        # File should still be one structured entry
        loaded = json.loads(hist_file.read_text(encoding='utf-8'))
        assert isinstance(loaded, list) and len(loaded) == 1
    finally:
        # Cleanup dummy module
        sys.modules.pop('app_new', None)
