# -*- coding: utf-8 -*-
"""
Integration tests for API Authentication.
Verifies that protected routes reject unauthenticated requests.
"""
import json
import pytest
from unittest import mock
from flask import Flask

@pytest.fixture
def auth_client():
    """Create Flask test client with the actual blueprints."""
    # Ensure config mock to set DEBUG=False for strict auth validation tests
    with mock.patch('config.settings.config') as mock_config, \
         mock.patch('config.security.SecurityConfig') as mock_sec_config:
        
        mock_config.DEBUG = False
        mock_config.SECRET_KEY = "secure-secret-key"
        mock_sec_config.return_value.INTERNAL_WORKER_TOKEN = "secure-worker-token"
        
        # Clean import of app and blueprints
        app = Flask(__name__)
        app.config['SECRET_KEY'] = "secure-secret-key"
        app.config['DEBUG'] = False
        
        from routes.api_routes import api_bp
        from routes.workflow_routes import workflow_bp
        
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(workflow_bp)
        
        yield app.test_client()

def test_protected_routes_require_authentication(auth_client):
    """
    Given / When / Then markers
    Given a list of protected API endpoints
    When a request is sent without a worker token
    Then they should return 401 Unauthorized
    """
    protected_endpoints = [
        ('/run/STEP1', 'POST'),
        ('/run_custom_sequence', 'POST'),
        ('/stop/STEP1', 'POST'),
        ('/sequence/stop', 'POST'),
        ('/cancel/STEP1', 'POST'),
        ('/api/performance/reset', 'POST'),
        ('/api/cache/open', 'POST'),
        ('/api/cache/clear', 'POST'),
        ('/get_specific_log_test/STEP1/0', 'GET')
    ]
    
    for url, method in protected_endpoints:
        if method == 'POST':
            response = auth_client.post(url)
        else:
            response = auth_client.get(url)
            
        assert response.status_code == 401, f"Route {url} ({method}) did not return 401 Unauthorized"
        data = response.get_json()
        assert "error" in data
        assert "token" in data["error"].lower()

def test_protected_routes_reject_invalid_token(auth_client):
    """
    Given an invalid worker token
    When a request is sent to a protected endpoint
    Then it should return 401 Unauthorized
    """
    url = '/run/STEP1'
    headers = {'X-Worker-Token': 'wrong-token'}
    response = auth_client.post(url, headers=headers)
    
    assert response.status_code == 401
    data = response.get_json()
    assert "Invalid authentication token" in data["error"]

def test_protected_routes_accept_valid_token(auth_client):
    """
    Given a valid worker token
    When a request is sent to a protected endpoint
    Then it should pass authentication (not return 401)
    """
    url = '/run/STEP1'
    headers = {'X-Worker-Token': 'secure-worker-token'}
    
    # We patch run_step to return 200 so we know we got past the decorator
    with mock.patch('routes.workflow_routes.WorkflowService.run_step') as mock_run:
        mock_run.return_value = {"status": "initiated"}
        response = auth_client.post(url, headers=headers)
        
        # Should not be 401
        assert response.status_code != 401
