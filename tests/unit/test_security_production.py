import os
import pytest
from unittest import mock
from config.security import SecurityConfig
from config.settings import Config

class TestProductionSecurity:
    
    def setup_method(self):
        # Create fresh configurations for each test
        self.config = Config()
        self.security_config = SecurityConfig()

        # Set default required fields to avoid unrelated validation errors
        self.config.WEBHOOK_JSON_URL = "https://example.com/webhook"
        
        # Mock paths so it doesn't fail on directory existence checks
        self.config.BASE_PATH_SCRIPTS = mock.MagicMock()
        self.config.BASE_PATH_SCRIPTS.exists.return_value = True
        self.config.LOCAL_DOWNLOADS_DIR = mock.MagicMock()
        self.config.LOCAL_DOWNLOADS_DIR.exists.return_value = True

    def test_security_config_strict_rejects_dev_tokens(self):
        self.security_config.INTERNAL_WORKER_TOKEN = "dev-internal-worker-token"
        
        with pytest.raises(ValueError) as exc:
            self.security_config.validate_tokens(strict=True)
            
        assert "cannot be a development/default token in production" in str(exc.value)

    def test_security_config_non_strict_allows_dev_tokens(self):
        self.security_config.INTERNAL_WORKER_TOKEN = "dev-internal-worker-token"
        
        # Should not raise exception
        result = self.security_config.validate_tokens(strict=False)
        assert result is False  # returns False because of warnings

    def test_config_strict_rejects_dev_secret_key(self):
        self.config.DEBUG = False
        self.config.SECRET_KEY = "dev-key-change-in-production"
        self.config.INTERNAL_WORKER_TOKEN = "secure-token-1"
        
        with pytest.raises(ValueError) as exc:
            self.config.validate(strict=True)
            
        assert "FLASK_SECRET_KEY must be a secure value" in str(exc.value)

    def test_config_strict_rejects_dev_tokens(self):
        self.config.DEBUG = False
        self.config.SECRET_KEY = "secure-secret-key"
        self.config.INTERNAL_WORKER_TOKEN = "dev-internal-worker-token"
        
        with pytest.raises(ValueError) as exc:
            self.config.validate(strict=True)
            
        assert "cannot be a development/default token in production" in str(exc.value)

    def test_config_production_valid_tokens(self):
        self.config.DEBUG = False
        self.config.SECRET_KEY = "secure-secret-key"
        self.config.INTERNAL_WORKER_TOKEN = "secure-internal-token"
        
        # Ensure the mock paths are correctly handled for the boolean check in validate
        with mock.patch("pathlib.Path.exists", return_value=True):
            # Should not raise exception
            assert self.config.validate(strict=True) is True
