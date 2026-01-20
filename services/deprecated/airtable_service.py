"""
Airtable Service for workflow_mediapipe application.

This service handles all Airtable API interactions for monitoring download URLs.
Replaces the legacy CSV/XLSX file monitoring system with a more reliable
Airtable-based solution.

Author: Augment Agent
Date: 2025-07-21
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

from config.settings import config
from services.cache_service import CacheService

logger = logging.getLogger(__name__)

try:
    from pyairtable import Api
    AIRTABLE_AVAILABLE = True
except ImportError:
    AIRTABLE_AVAILABLE = False
    logger.warning("pyairtable not available. Airtable integration disabled.")


class AirtableService:
    """
    Service for managing Airtable integration.
    
    Provides methods for fetching records from Airtable and monitoring
    for new download URLs. Designed to replace the legacy CSV monitoring
    system while maintaining the same interface.
    """
    
    _api_instance: Optional[Any] = None
    _table_instance: Optional[Any] = None
    
    @classmethod
    def _get_api(cls) -> Optional[Any]:
        """
        Get or create Airtable API instance.
        
        Returns:
            Airtable API instance or None if not available
        """
        if not AIRTABLE_AVAILABLE:
            logger.error("Airtable integration not available - pyairtable not installed")
            return None
            
        if not config.AIRTABLE_ACCESS_TOKEN:
            logger.error("Airtable access token not configured")
            return None
            
        if cls._api_instance is None:
            try:
                cls._api_instance = Api(config.AIRTABLE_ACCESS_TOKEN)
                logger.info("Airtable API instance created successfully")
            except Exception as e:
                logger.error(f"Failed to create Airtable API instance: {e}")
                return None
                
        return cls._api_instance
    
    @classmethod
    def _get_table(cls) -> Optional[Any]:
        """
        Get or create Airtable table instance.

        Returns:
            Airtable table instance or None if not available
        """
        if cls._table_instance is None:
            api = cls._get_api()
            if api is None:
                return None

            try:
                # Get base by name
                bases = api.bases()
                target_base = None

                for base in bases:
                    if base.name == config.AIRTABLE_BASE_NAME:
                        target_base = base
                        break

                if target_base is None:
                    logger.error(f"Airtable base '{config.AIRTABLE_BASE_NAME}' not found")
                    available_bases = [base.name for base in bases]
                    logger.error(f"Available bases: {available_bases}")
                    return None

                # Get table from base - try by name first, then by ID if available
                try:
                    cls._table_instance = target_base.table(config.AIRTABLE_TABLE_NAME)
                    logger.info(f"Airtable table '{config.AIRTABLE_TABLE_NAME}' connected successfully")
                except Exception as table_error:
                    logger.warning(f"Failed to connect to table by name: {table_error}")

                    # Try to get table info from schema for better error reporting
                    try:
                        schema = target_base.schema()
                        available_tables = [(table.name, table.id) for table in schema.tables]
                        logger.info(f"Available tables: {available_tables}")

                        # Try to find table by name in schema
                        for table_info in schema.tables:
                            if table_info.name == config.AIRTABLE_TABLE_NAME:
                                logger.info(f"Found table in schema: {table_info.name} (ID: {table_info.id})")
                                # Try using table ID instead of name
                                cls._table_instance = target_base.table(table_info.id)
                                logger.info(f"Connected to table using ID: {table_info.id}")
                                break
                        else:
                            logger.error(f"Table '{config.AIRTABLE_TABLE_NAME}' not found in schema")
                            return None

                    except Exception as schema_error:
                        logger.error(f"Failed to get schema information: {schema_error}")
                        return None

            except Exception as e:
                logger.error(f"Failed to connect to Airtable table: {e}")
                return None

        return cls._table_instance
    
    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """
        Test Airtable connection and configuration.
        
        Returns:
            Dictionary with connection test results
        """
        result = {
            "status": "error",
            "message": "",
            "details": {}
        }
        
        try:
            # Check if Airtable is available
            if not AIRTABLE_AVAILABLE:
                result["message"] = "pyairtable library not installed"
                result["details"]["pyairtable_available"] = False
                return result
            
            result["details"]["pyairtable_available"] = True
            
            # Check configuration
            if not config.AIRTABLE_ACCESS_TOKEN:
                result["message"] = "Airtable access token not configured"
                result["details"]["token_configured"] = False
                return result
            
            result["details"]["token_configured"] = True
            result["details"]["base_name"] = config.AIRTABLE_BASE_NAME
            result["details"]["table_name"] = config.AIRTABLE_TABLE_NAME
            
            # Test API connection and schema access
            api = AirtableService._get_api()
            if api is None:
                result["message"] = "Failed to create API instance"
                result["details"]["api_accessible"] = False
                return result

            result["details"]["api_accessible"] = True

            # Test base access
            try:
                bases = api.bases()
                result["details"]["bases_accessible"] = True
                result["details"]["available_bases"] = [base.name for base in bases]

                # Find target base
                target_base = None
                for base in bases:
                    if base.name == config.AIRTABLE_BASE_NAME:
                        target_base = base
                        break

                if target_base is None:
                    result["message"] = f"Base '{config.AIRTABLE_BASE_NAME}' not found"
                    result["details"]["base_found"] = False
                    return result

                result["details"]["base_found"] = True
                result["details"]["base_id"] = target_base.id

            except Exception as e:
                result["message"] = f"Failed to access bases: {e}"
                result["details"]["bases_accessible"] = False
                return result

            # Test schema access
            try:
                schema = target_base.schema()
                result["details"]["schema_accessible"] = True

                # Get table information from schema
                table_info = None
                for table in schema.tables:
                    if table.name == config.AIRTABLE_TABLE_NAME:
                        table_info = table
                        break

                if table_info is None:
                    result["message"] = f"Table '{config.AIRTABLE_TABLE_NAME}' not found in schema"
                    result["details"]["table_found_in_schema"] = False
                    result["details"]["available_tables"] = [(t.name, t.id) for t in schema.tables]
                    return result

                result["details"]["table_found_in_schema"] = True
                result["details"]["table_id"] = table_info.id
                result["details"]["available_fields"] = [field.name for field in table_info.fields]

                # Check for required fields in schema
                field_names = [field.name.lower() for field in table_info.fields]
                has_timestamp = any('timestamp' in field or 'time' in field or 'date' in field for field in field_names)
                has_url = any('url' in field and 'dropbox' in field for field in field_names)

                result["details"]["has_timestamp_field"] = has_timestamp
                result["details"]["has_url_field"] = has_url

            except Exception as e:
                result["message"] = f"Failed to access schema: {e}"
                result["details"]["schema_accessible"] = False
                return result

            # Test table connection
            table = AirtableService._get_table()
            if table is None:
                result["message"] = "Failed to connect to Airtable table"
                result["details"]["table_accessible"] = False
                return result

            result["details"]["table_accessible"] = True

            # Test record access (this may fail due to permissions)
            try:
                records = table.all(max_records=1)
                result["details"]["records_fetchable"] = True
                result["details"]["sample_record_count"] = len(records)

                if result["details"]["has_timestamp_field"] and result["details"]["has_url_field"]:
                    result["status"] = "success"
                    result["message"] = "Airtable connection successful"
                else:
                    result["status"] = "warning"
                    result["message"] = "Connection successful but required fields may be missing"

            except Exception as e:
                error_str = str(e)
                result["details"]["records_fetchable"] = False
                result["details"]["record_access_error"] = error_str

                # Check if it's a permission error
                if "403" in error_str and "INVALID_PERMISSIONS" in error_str:
                    result["status"] = "warning"
                    result["message"] = "Schema access successful but record access denied - token may need 'data.records:read' permission"
                    result["details"]["permission_issue"] = True
                    result["details"]["suggested_scopes"] = ["data.records:read", "data.records:write", "schema.bases:read"]
                else:
                    result["message"] = f"Failed to fetch records: {e}"
                
        except Exception as e:
            result["message"] = f"Connection test failed: {e}"
            logger.error(f"Airtable connection test error: {e}")
            
        return result
    
    @staticmethod
    @CacheService.cached_with_stats(timeout=30, key_prefix="airtable_records")
    def fetch_records() -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all records from Airtable.
        
        Returns:
            List of records with timestamp and url fields, or None on error
        """
        try:
            table = AirtableService._get_table()
            if table is None:
                return None
            
            # Fetch all records
            records = table.all()
            logger.debug(f"Airtable: Fetched {len(records)} records")
            
            # Process records to extract timestamp and URL
            processed_records = []
            for record in records:
                fields = record.get('fields', {})
                
                # Find timestamp field (case-insensitive)
                timestamp_val = None
                for field_name, field_value in fields.items():
                    if 'timestamp' in field_name.lower() or 'time' in field_name.lower() or 'date' in field_name.lower():
                        timestamp_val = str(field_value).strip() if field_value else None
                        break
                
                # Find URL field(s) (case-insensitive). Support Dropbox and FromSmash.
                url_val = None
                url_type = None
                for field_name, field_value in fields.items():
                    field_lower = field_name.lower()
                    if 'url' in field_lower:
                        candidate = str(field_value).strip() if field_value else None
                        if not candidate:
                            continue
                        candidate_lower = candidate.lower()
                        if 'fromsmash.com' in candidate_lower and url_val is None:
                            url_val = candidate
                            url_type = 'fromsmash'
                            # prefer explicit match; don't break in case a better field exists, but this is sufficient
                        elif ('dropbox.com' in candidate_lower or 'dl=1' in candidate_lower) and url_val is None:
                            url_val = candidate
                            url_type = 'dropbox'
                        elif url_val is None:
                            # fallback: take the first URL-looking value
                            if candidate_lower.startswith('http://') or candidate_lower.startswith('https://'):
                                url_val = candidate
                                url_type = 'unknown'

                # Only include records with both timestamp and URL
                if timestamp_val and url_val and timestamp_val != 'None' and url_val != 'None':
                    processed_records.append({
                        'timestamp': timestamp_val,
                        'url': url_val,
                        'url_type': url_type or ('fromsmash' if 'fromsmash.com' in url_val.lower() else ('dropbox' if 'dropbox.com' in url_val.lower() else 'unknown')),
                        'record_id': record.get('id'),
                        'created_time': record.get('createdTime')
                    })
            
            logger.debug(f"Airtable: {len(processed_records)} valid records processed")
            return processed_records
            
        except Exception as e:
            error_str = str(e)
            if "403" in error_str and "INVALID_PERMISSIONS" in error_str:
                logger.error(f"Airtable permission error - token may need 'data.records:read' scope: {e}")
            else:
                logger.error(f"Error fetching Airtable records: {e}")
            return None
    
    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """
        Get Airtable service status.
        
        Returns:
            Service status dictionary
        """
        return {
            "airtable_available": AIRTABLE_AVAILABLE,
            "use_airtable": config.USE_AIRTABLE,
            "base_name": config.AIRTABLE_BASE_NAME,
            "table_name": config.AIRTABLE_TABLE_NAME,
            "monitor_interval": config.AIRTABLE_MONITOR_INTERVAL,
            "token_configured": bool(config.AIRTABLE_ACCESS_TOKEN),
            "cache_stats": CacheService.get_cache_stats()
        }
