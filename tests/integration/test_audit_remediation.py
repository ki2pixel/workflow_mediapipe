#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_app_new():
    mock_app = Mock()
    return mock_app


@pytest.fixture
def app_client(mock_app_new, tmp_path):
    # Given: a Flask app with blueprints registered and isolated BASE_PATH_SCRIPTS
    with patch.dict('sys.modules', {'app_new': mock_app_new}):
        from flask import Flask
        from routes.workflow_routes import workflow_bp

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(workflow_bp)

        with patch('config.settings.config.BASE_PATH_SCRIPTS', tmp_path):
            with app.test_client() as client:
                yield client


class TestAuditRemediationLogEndpoints:
    def test_get_specific_log_step1_index0_no_500(self, app_client):
        # Given: Preconditions
        # When:  Operation to execute
        resp = app_client.get('/get_specific_log/STEP1/0')

        # Then:  Expected result/verification
        assert resp.status_code in (200, 404)
        data = resp.get_json()
        assert isinstance(data, dict)
        if resp.status_code == 200:
            assert 'content' in data
            assert 'error' in data
            assert 'path' in data
            assert 'type' in data

    def test_get_specific_log_unknown_step_returns_404(self, app_client):
        # Given: Preconditions
        # When:  Operation to execute
        resp = app_client.get('/get_specific_log/UNKNOWN_STEP/0')

        # Then:  Expected result/verification
        assert resp.status_code == 404
        data = resp.get_json()
        assert isinstance(data, dict)
        assert 'error' in data

    def test_get_specific_log_index_out_of_range_returns_404(self, app_client):
        # Given: Preconditions
        # When:  Operation to execute
        resp = app_client.get('/get_specific_log/STEP1/9999')

        # Then:  Expected result/verification
        assert resp.status_code == 404
        data = resp.get_json()
        assert isinstance(data, dict)
        assert 'error' in data


class TestAuditRemediationCacheServiceWorkflowState:
    def test_get_cached_step_status_success(self):
        # Given: Preconditions
        from services.workflow_state import WorkflowState
        from services.cache_service import CacheService

        ws = WorkflowState()
        ws.initialize_all_steps(['STEP1'])
        ws.update_step_status('STEP1', 'running')
        ws.update_step_progress('STEP1', 1, 10, 'Processing...')

        with patch('services.cache_service.get_workflow_state', return_value=ws):
            # When:  Operation to execute
            result = CacheService.get_cached_step_status('STEP1')

        # Then:  Expected result/verification
        assert isinstance(result, dict)
        assert result.get('status') == 'running'
        assert result.get('progress_current') == 1
        assert result.get('progress_total') == 10

    def test_get_cached_step_status_missing_step_raises_value_error(self):
        # Given: Preconditions
        from services.workflow_state import WorkflowState
        from services.cache_service import CacheService

        ws = WorkflowState()
        ws.initialize_all_steps(['STEP1'])

        with patch('services.cache_service.get_workflow_state', return_value=ws):
            # When:  Operation to execute
            # Then:  Expected result/verification
            with pytest.raises(ValueError) as exc:
                CacheService.get_cached_step_status('NOPE')

        assert "Step 'NOPE' not found" in str(exc.value)


class TestAuditRemediationWebhookUrlValidation:
    def test_check_csv_for_downloads_accepts_https_dropbox(self):
        # Given: Preconditions
        from services.csv_service import CSVService
        from services.workflow_state import WorkflowState

        ws = WorkflowState()

        fake_rows = [
            {
                'url': 'https://www.dropbox.com/scl/fo/abc123?rlkey=def&dl=1',
                'fallback_url': '',
                'original_filename': 'proj.zip',
                'provider': 'dropbox',
                'timestamp': '2026-01-01 00:00:00',
                'source': 'webhook',
                'url_type': 'dropbox',
            }
        ]

        fake_app_new = SimpleNamespace(execute_csv_download_worker=lambda *args, **kwargs: None)

        with patch.dict(sys.modules, {'app_new': fake_app_new}):
            with patch('services.csv_service.WEBHOOK_SERVICE_AVAILABLE', True):
                with patch('services.workflow_state.get_workflow_state', return_value=ws):
                    with patch('services.csv_service.webhook_fetch_records', return_value=fake_rows):
                        with patch('services.csv_service.CSVService.get_download_history', return_value=set()):
                            with patch('services.csv_service.CSVService.add_to_download_history_with_timestamp') as add_hist:
                                with patch.dict(os.environ, {'DRY_RUN_DOWNLOADS': 'true'}):
                                    # When:  Operation to execute
                                    CSVService._check_csv_for_downloads()

        # Then:  Expected result/verification
        assert add_hist.called

    def test_check_csv_for_downloads_rejects_ftp_scheme(self):
        # Given: Preconditions
        from services.csv_service import CSVService
        from services.workflow_state import WorkflowState

        ws = WorkflowState()

        fake_rows = [
            {
                'url': 'ftp://dropbox.com/scl/fo/abc123?dl=1',
                'fallback_url': '',
                'original_filename': 'proj.zip',
                'provider': 'dropbox',
                'timestamp': '2026-01-01 00:00:00',
                'source': 'webhook',
                'url_type': 'dropbox',
            }
        ]

        fake_app_new = SimpleNamespace(execute_csv_download_worker=lambda *args, **kwargs: None)

        with patch.dict(sys.modules, {'app_new': fake_app_new}):
            with patch('services.csv_service.WEBHOOK_SERVICE_AVAILABLE', True):
                with patch('services.workflow_state.get_workflow_state', return_value=ws):
                    with patch('services.csv_service.webhook_fetch_records', return_value=fake_rows):
                        with patch('services.csv_service.CSVService.get_download_history', return_value=set()):
                            with patch('services.csv_service.CSVService.add_to_download_history_with_timestamp') as add_hist:
                                with patch.dict(os.environ, {'DRY_RUN_DOWNLOADS': 'true'}):
                                    # When:  Operation to execute
                                    CSVService._check_csv_for_downloads()

        # Then:  Expected result/verification
        add_hist.assert_not_called()

    def test_check_csv_for_downloads_rejects_file_scheme(self):
        # Given: Preconditions
        from services.csv_service import CSVService
        from services.workflow_state import WorkflowState

        ws = WorkflowState()

        fake_rows = [
            {
                'url': 'file:///tmp/proj.zip',
                'fallback_url': '',
                'original_filename': 'proj.zip',
                'provider': 'dropbox',
                'timestamp': '2026-01-01 00:00:00',
                'source': 'webhook',
                'url_type': 'dropbox',
            }
        ]

        fake_app_new = SimpleNamespace(execute_csv_download_worker=lambda *args, **kwargs: None)

        with patch.dict(sys.modules, {'app_new': fake_app_new}):
            with patch('services.csv_service.WEBHOOK_SERVICE_AVAILABLE', True):
                with patch('services.workflow_state.get_workflow_state', return_value=ws):
                    with patch('services.csv_service.webhook_fetch_records', return_value=fake_rows):
                        with patch('services.csv_service.CSVService.get_download_history', return_value=set()):
                            with patch('services.csv_service.CSVService.add_to_download_history_with_timestamp') as add_hist:
                                with patch.dict(os.environ, {'DRY_RUN_DOWNLOADS': 'true'}):
                                    # When:  Operation to execute
                                    CSVService._check_csv_for_downloads()

        # Then:  Expected result/verification
        add_hist.assert_not_called()
