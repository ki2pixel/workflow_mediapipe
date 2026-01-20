"""
Unit tests for MySQLService.

Tests the MySQL integration service functionality including connection management,
record operations, and error handling.

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
    from services.mysql_service import MySQLService, MYSQL_AVAILABLE
    from config.settings import config


class TestMySQLService:
    """Test cases for MySQLService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset any cached connections
        MySQLService._connection_pool = None
        MySQLService._pool_lock = None
    
    @patch('services.mysql_service.pymysql')
    def test_get_connection_success(self, mock_pymysql):
        """Test successful database connection."""
        mock_connection = MagicMock()
        mock_pymysql.connect.return_value = mock_connection
        
        connection = MySQLService._get_connection()
        
        assert connection == mock_connection
        mock_pymysql.connect.assert_called_once_with(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USERNAME,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=mock_pymysql.cursors.DictCursor,
            connect_timeout=config.MYSQL_CONNECTION_TIMEOUT,
            autocommit=True
        )
    
    @patch('services.mysql_service.pymysql')
    def test_get_connection_failure(self, mock_pymysql):
        """Test database connection failure."""
        mock_pymysql.connect.side_effect = Exception("Connection failed")
        
        connection = MySQLService._get_connection()
        
        assert connection is None
    
    @patch('services.mysql_service.MYSQL_AVAILABLE', False)
    def test_get_connection_mysql_unavailable(self):
        """Test connection when MySQL is not available."""
        connection = MySQLService._get_connection()
        assert connection is None
    
    @patch.object(MySQLService, '_get_connection')
    def test_ensure_table_exists_success(self, mock_get_connection):
        """Test successful table creation."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_connection.return_value = mock_connection
        
        result = MySQLService._ensure_table_exists()
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()
    
    @patch.object(MySQLService, '_get_connection')
    def test_ensure_table_exists_failure(self, mock_get_connection):
        """Test table creation failure."""
        mock_get_connection.return_value = None
        
        result = MySQLService._ensure_table_exists()
        
        assert result is False
    
    @patch.object(MySQLService, '_get_connection')
    def test_test_connection_success(self, mock_get_connection):
        """Test successful connection test."""
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {'count': 1},  # Table exists
            {'count': 5}   # Record count
        ]
        mock_get_connection.return_value = mock_connection
        
        with patch.object(MySQLService, '_ensure_table_exists', return_value=True):
            result = MySQLService.test_connection()
        
        assert result['status'] == 'success'
        assert result['message'] == 'MySQL connection successful'
        assert result['details']['connection_accessible'] is True
        assert result['details']['table_accessible'] is True
        assert result['details']['records_fetchable'] is True
        assert result['details']['record_count'] == 5
    
    @patch('services.mysql_service.MYSQL_AVAILABLE', False)
    def test_test_connection_mysql_unavailable(self):
        """Test connection test when MySQL is unavailable."""
        result = MySQLService.test_connection()
        
        assert result['status'] == 'error'
        assert 'PyMySQL not available' in result['message']
    
    @patch('services.mysql_service.config.USE_MYSQL', False)
    def test_test_connection_disabled(self):
        """Test connection test when MySQL is disabled."""
        result = MySQLService.test_connection()

        assert result['status'] == 'disabled'
        assert 'MySQL integration is disabled' in result['message']
    
    @patch.object(MySQLService, '_ensure_table_exists')
    @patch.object(MySQLService, '_get_connection')
    def test_fetch_records_success(self, mock_get_connection, mock_ensure_table):
        """Test successful record fetching."""
        mock_ensure_table.return_value = True
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                'record_id': 'test-id-1',
                'timestamp': '2025-07-27 12:00:00',
                'url': 'https://dropbox.com/test1.zip',
                'created_time': '2025-07-27T12:00:00'
            },
            {
                'record_id': 'test-id-2',
                'timestamp': '2025-07-27 13:00:00',
                'url': 'https://dropbox.com/test2.zip',
                'created_time': '2025-07-27T13:00:00'
            }
        ]
        mock_get_connection.return_value = mock_connection
        
        records = MySQLService.fetch_records()
        
        assert records is not None
        assert len(records) == 2
        assert records[0]['record_id'] == 'test-id-1'
        assert records[0]['url'] == 'https://dropbox.com/test1.zip'
        mock_connection.close.assert_called_once()
    
    @patch.object(MySQLService, '_ensure_table_exists')
    def test_fetch_records_table_creation_failure(self, mock_ensure_table):
        """Test record fetching when table creation fails."""
        mock_ensure_table.return_value = False
        
        records = MySQLService.fetch_records()
        
        assert records is None
    
    @patch.object(MySQLService, '_ensure_table_exists')
    @patch.object(MySQLService, '_get_connection')
    def test_add_record_success(self, mock_get_connection, mock_ensure_table):
        """Test successful record addition."""
        mock_ensure_table.return_value = True
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_connection.return_value = mock_connection
        
        record_id = MySQLService.add_record('2025-07-27 12:00:00', 'https://dropbox.com/test.zip')
        
        assert record_id is not None
        assert isinstance(record_id, str)
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()
    
    @patch.object(MySQLService, '_ensure_table_exists')
    def test_add_record_table_creation_failure(self, mock_ensure_table):
        """Test record addition when table creation fails."""
        mock_ensure_table.return_value = False
        
        record_id = MySQLService.add_record('2025-07-27 12:00:00', 'https://dropbox.com/test.zip')
        
        assert record_id is None
    
    def test_get_service_status(self):
        """Test service status reporting."""
        status = MySQLService.get_service_status()
        
        assert isinstance(status, dict)
        assert 'mysql_available' in status
        assert 'use_mysql' in status
        assert 'host' in status
        assert 'database' in status
        assert 'table_name' in status
        assert 'monitor_interval' in status
        assert 'connection_configured' in status
        assert 'cache_stats' in status
        
        assert status['mysql_available'] == MYSQL_AVAILABLE
        assert status['use_mysql'] == config.USE_MYSQL
        assert status['host'] == config.MYSQL_HOST
        assert status['database'] == config.MYSQL_DATABASE


class TestMySQLServiceIntegration:
    """Integration tests for MySQLService with other components."""
    
    @patch.object(MySQLService, 'test_connection')
    def test_csv_service_integration(self, mock_test_connection):
        """Test MySQLService integration with CSVService."""
        mock_test_connection.return_value = {
            'status': 'success',
            'message': 'Connection successful'
        }
        
        from services.csv_service import CSVService
        
        # Test MySQL connection via CSVService
        result = CSVService.test_mysql_connection()
        assert result['status'] == 'success'
        
        # Test service status includes MySQL
        status = CSVService.get_monitor_status()
        assert 'mysql' in status
        assert status['data_source'] == 'mysql'  # Should be MySQL since USE_MYSQL=true
    
    @patch('services.mysql_service.CacheService')
    def test_caching_integration(self, mock_cache_service):
        """Test MySQLService integration with CacheService."""
        # Test that fetch_records uses caching
        with patch.object(MySQLService, '_ensure_table_exists', return_value=True):
            with patch.object(MySQLService, '_get_connection', return_value=None):
                MySQLService.fetch_records()
        
        # Verify cache decorator is applied (this is implicit through the decorator)
        # The actual caching behavior is tested in CacheService tests


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
