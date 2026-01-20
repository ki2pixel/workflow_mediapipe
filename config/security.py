"""
Security configuration and authentication management for workflow_mediapipe.

This module provides secure token management and authentication decorators
following the project's security guidelines.
"""

import os
import logging
from functools import wraps
from typing import Optional
from flask import request, jsonify

logger = logging.getLogger(__name__)


class SecurityConfig:
    """
    Centralized security configuration management.
    
    Loads security tokens from environment variables and provides
    validation methods to ensure proper configuration.
    """
    
    def __init__(self):
        """Initialize security configuration from environment variables."""
        self.INTERNAL_WORKER_TOKEN = os.environ.get('INTERNAL_WORKER_COMMS_TOKEN')
        self.RENDER_REGISTER_TOKEN = os.environ.get('RENDER_REGISTER_TOKEN')
        
    def validate_tokens(self, strict: bool = True) -> bool:
        """
        Validate that all required security tokens are configured.

        Args:
            strict: If True, raise errors for missing tokens. If False, log warnings.

        Returns:
            bool: True if all tokens are valid, False otherwise

        Raises:
            ValueError: If required tokens are missing and strict=True
        """
        errors = []
        warnings = []

        if not self.INTERNAL_WORKER_TOKEN:
            msg = "INTERNAL_WORKER_COMMS_TOKEN environment variable is required"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
                # Set a development default
                self.INTERNAL_WORKER_TOKEN = "dev-internal-worker-token"
                logger.warning(f"{msg} - using development default")

        if not self.RENDER_REGISTER_TOKEN:
            msg = "RENDER_REGISTER_TOKEN environment variable is required"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
                # Set a development default
                self.RENDER_REGISTER_TOKEN = "dev-render-register-token"
                logger.warning(f"{msg} - using development default")

        if errors:
            error_msg = f"Security configuration errors: {'; '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            logger.warning(f"Security configuration warnings: {'; '.join(warnings)}")
            logger.warning("Using development defaults - NOT SUITABLE FOR PRODUCTION")
            return False

        logger.info("Security tokens validated successfully")
        return True
    
    def get_token(self, token_name: str) -> Optional[str]:
        """
        Get a specific token by name.
        
        Args:
            token_name: Name of the token to retrieve
            
        Returns:
            Token value or None if not found
        """
        return getattr(self, token_name, None)


def require_internal_worker_token(func):
    """
    Decorator for endpoints requiring internal worker authentication.
    
    Validates the X-Worker-Token header against the configured
    INTERNAL_WORKER_COMMS_TOKEN.
    
    Args:
        func: Flask route function to protect
        
    Returns:
        Decorated function with token validation
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        security_config = SecurityConfig()
        
        if not security_config.INTERNAL_WORKER_TOKEN:
            logger.error("Internal worker token not configured")
            return jsonify({"error": "Authentication not configured"}), 500
        
        received_token = request.headers.get('X-Worker-Token')
        if not received_token:
            logger.warning("Missing X-Worker-Token header in request")
            return jsonify({"error": "Missing authentication token"}), 401
            
        if received_token != security_config.INTERNAL_WORKER_TOKEN:
            logger.warning(f"Invalid worker token received from {request.remote_addr}")
            return jsonify({"error": "Invalid authentication token"}), 401
        
        logger.debug("Internal worker token validated successfully")
        return func(*args, **kwargs)
    
    return wrapper


def require_render_register_token(func):
    """
    Decorator for endpoints requiring render registration authentication.
    
    Validates the X-Render-Token header against the configured
    RENDER_REGISTER_TOKEN.
    
    Args:
        func: Flask route function to protect
        
    Returns:
        Decorated function with token validation
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        security_config = SecurityConfig()
        
        if not security_config.RENDER_REGISTER_TOKEN:
            logger.error("Render register token not configured")
            return jsonify({"error": "Authentication not configured"}), 500
        
        received_token = request.headers.get('X-Render-Token')
        if not received_token:
            logger.warning("Missing X-Render-Token header in request")
            return jsonify({"error": "Missing authentication token"}), 401
            
        if received_token != security_config.RENDER_REGISTER_TOKEN:
            logger.warning(f"Invalid render token received from {request.remote_addr}")
            return jsonify({"error": "Invalid authentication token"}), 401
        
        logger.debug("Render register token validated successfully")
        return func(*args, **kwargs)
    
    return wrapper


def validate_file_path(file_path: str, allowed_base_paths: list) -> bool:
    """
    Validate file path to prevent directory traversal attacks.
    
    Args:
        file_path: Path to validate
        allowed_base_paths: List of allowed base directory paths
        
    Returns:
        bool: True if path is safe, False otherwise
    """
    try:
        from pathlib import Path
        
        # Resolve the path to handle any .. or . components
        resolved_path = Path(file_path).resolve()
        
        # Check if the resolved path starts with any allowed base path
        for base_path in allowed_base_paths:
            base_resolved = Path(base_path).resolve()
            try:
                resolved_path.relative_to(base_resolved)
                return True
            except ValueError:
                continue
                
        logger.warning(f"File path validation failed for: {file_path}")
        return False
        
    except Exception as e:
        logger.error(f"Error validating file path {file_path}: {e}")
        return False
