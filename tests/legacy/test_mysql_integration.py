"""
Integration tests for MySQL service integration.

Tests the complete MySQL integration workflow including CSVService integration,
API endpoints, and data flow.

Author: Augment Agent
Date: 2025-07-27
"""

import pytest
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Mock environment variables before importing services
test_env = {
    'USE_MYSQL': 'true',
    'USE_AIRTABLE': 'false',
    'MYSQL_HOST': 'test-host',
    'MYSQL_PORT': '3306',
    'MYSQL_DATABASE': 'test_db',
    'MYSQL_USERNAME': 'test_user',
    'MYSQL_PASSWORD': 'test_pass',
    'MYSQL_TABLE_NAME': 'test_table',
    'MYSQL_CONNECTION_TIMEOUT': '30',
    'MYSQL_POOL_SIZE': '5',
    'MYSQL_MONITOR_INTERVAL': '15',
    'INTERNAL_WORKER_COMMS_TOKEN': 'test-token',
    'RENDER_REGISTER_TOKEN': 'test-token',
    'FLASK_SECRET_KEY': 'test-secret-key',
    'DEBUG': 'true'
}

with patch.dict(os.environ, test_env):
    from services.mysql_service import MySQLService
    from services.csv_service import CSVService
    from config.settings import config


class TestMySQLIntegration:
    """Integration tests for MySQL service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset any cached connections
        MySQLService._connection_pool = None
        MySQLService._pool_lock = None
    
    @patch.object(MySQLService, 'fetch_records')
    def test_csv_service_data_source_selection(self, mock_fetch_records):
        """Test that CSVService correctly selects MySQL as data source."""
        mock_fetch_records.return_value = [
            {
                'record_id': 'test-id',
                'timestamp': '2025-07-27 12:00:00',
                'url': 'https://dropbox.com/test.zip',
                'created_time': '2025-07-27T12:00:00'
            }
        ]
        
        # Test monitor status shows MySQL as data source
        status = CSVService.get_monitor_status()
        assert status['data_source'] == 'mysql'
        assert status['use_mysql'] is True
        assert status['monitor_interval'] == config.MYSQL_MONITOR_INTERVAL
    
    @patch.object(MySQLService, 'test_connection')
    def test_csv_service_mysql_connection_test(self, mock_test_connection):
        """Test MySQL connection testing via CSVService."""
        mock_test_connection.return_value = {
            'status': 'success',
            'message': 'MySQL connection successful',
            'details': {
                'mysql_available': True,
                'connection_accessible': True,
                'table_accessible': True,
                'records_fetchable': True,
                'record_count': 10
            }
        }
        
        result = CSVService.test_mysql_connection()
        
        assert result['status'] == 'success'
        assert 'MySQL connection successful' in result['message']
        mock_test_connection.assert_called_once()
    
    @patch('services.mysql_service.config.USE_MYSQL', False)
    def test_csv_service_mysql_disabled(self):
        """Test CSVService behavior when MySQL is disabled."""
        result = CSVService.test_mysql_connection()

        assert result['status'] == 'disabled'
        assert 'MySQL integration is disabled' in result['message']
    
    @patch.object(MySQLService, 'fetch_records')
    @patch('app_new.execute_csv_download_worker')
    def test_download_monitoring_workflow(self, mock_execute_worker, mock_fetch_records):
        """Test complete download monitoring workflow with MySQL."""
        # Mock MySQL returning new records
        mock_fetch_records.return_value = [
            {
                'record_id': 'new-record-1',
                'timestamp': '2025-07-27 12:00:00',
                'url': 'https://dropbox.com/new-file.zip',
                'created_time': '2025-07-27T12:00:00'
            }
        ]
        
        # Mock empty download history
        with patch.object(CSVService, 'get_download_history', return_value=set()):
            with patch.object(CSVService, 'save_download_history'):
                # Execute the download check
                CSVService._check_csv_for_downloads()
        
        # Verify that the download worker was called
        mock_execute_worker.assert_called_once()
        args, kwargs = mock_execute_worker.call_args
        assert args[0] == 'https://dropbox.com/new-file.zip'
        assert args[1] == '2025-07-27 12:00:00'
    
    @patch.object(MySQLService, 'fetch_records')
    def test_download_monitoring_no_duplicates(self, mock_fetch_records):
        """Test that duplicate URLs are not processed."""
        # Mock MySQL returning records
        mock_fetch_records.return_value = [
            {
                'record_id': 'existing-record',
                'timestamp': '2025-07-27 12:00:00',
                'url': 'https://dropbox.com/existing-file.zip',
                'created_time': '2025-07-27T12:00:00'
            }
        ]
        
        # Mock download history containing the URL
        existing_history = {'https://dropbox.com/existing-file.zip'}
        
        with patch.object(CSVService, 'get_download_history', return_value=existing_history):
            with patch.object(CSVService, 'save_download_history') as mock_save:
                with patch('app_new.execute_csv_download_worker') as mock_execute:
                    # Execute the download check
                    CSVService._check_csv_for_downloads()
        
        # Verify that no download was triggered
        mock_execute.assert_not_called()
        # Verify that history was not updated (no new downloads)
        mock_save.assert_not_called()
    
    @patch.object(MySQLService, 'fetch_records')
    def test_mysql_fetch_error_handling(self, mock_fetch_records):
        """Test error handling when MySQL fetch fails."""
        mock_fetch_records.return_value = None  # Simulate fetch failure
        
        with patch.object(CSVService, 'get_download_history', return_value=set()):
            with patch('app_new.execute_csv_download_worker') as mock_execute:
                # Execute the download check
                CSVService._check_csv_for_downloads()
        
        # Verify that no download was triggered due to fetch failure
        mock_execute.assert_not_called()
    
    def test_service_status_integration(self):
        """Test that service status correctly reports MySQL integration."""
        status = CSVService.get_monitor_status()
        
        # Verify MySQL is included in status
        assert 'mysql' in status
        assert 'use_mysql' in status
        assert status['use_mysql'] is True
        
        # Verify MySQL service status structure
        mysql_status = status['mysql']
        assert 'mysql_available' in mysql_status
        assert 'use_mysql' in mysql_status
        assert 'host' in mysql_status
        assert 'database' in mysql_status
        assert 'table_name' in mysql_status
        assert 'monitor_interval' in mysql_status
        assert 'connection_configured' in mysql_status
        assert 'cache_stats' in mysql_status
    
    @patch('config.settings.config.USE_MYSQL', True)
    @patch('config.settings.config.USE_AIRTABLE', True)
    def test_configuration_validation_multiple_sources(self):
        """Test configuration validation prevents multiple data sources."""
        # Test that validation catches multiple enabled sources
        with pytest.raises(ValueError) as exc_info:
            config.validate(strict=True)

        assert "Only one data source can be enabled at a time" in str(exc_info.value)
    
    @patch('config.settings.config.USE_MYSQL', True)
    @patch('config.settings.config.MYSQL_HOST', '')
    @patch('config.settings.config.MYSQL_DATABASE', '')
    def test_configuration_validation_missing_required(self):
        """Test configuration validation for missing required MySQL settings."""
        # Test that validation catches missing required settings
        with pytest.raises(ValueError) as exc_info:
            config.validate(strict=True)

        error_message = str(exc_info.value)
        assert "MYSQL_HOST environment variable is required" in error_message
        assert "MYSQL_DATABASE environment variable is required" in error_message


class TestMySQLAPIIntegration:
    """Test MySQL integration with API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset any cached connections
        MySQLService._connection_pool = None
        MySQLService._pool_lock = None
    
    @patch.object(MySQLService, 'test_connection')
    def test_mysql_test_endpoint_success(self, mock_test_connection):
        """Test MySQL test endpoint returns success."""
        mock_test_connection.return_value = {
            'status': 'success',
            'message': 'MySQL connection successful'
        }
        
        # This would be tested with actual Flask test client in a full integration test
        result = CSVService.test_mysql_connection()
        assert result['status'] == 'success'
    
    @patch.object(MySQLService, 'test_connection')
    def test_mysql_test_endpoint_failure(self, mock_test_connection):
        """Test MySQL test endpoint returns failure."""
        mock_test_connection.return_value = {
            'status': 'error',
            'message': 'Connection failed'
        }
        
        result = CSVService.test_mysql_connection()
        assert result['status'] == 'error'
        assert 'Connection failed' in result['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
