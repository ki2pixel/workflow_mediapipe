# -*- coding: utf-8 -*-
"""
Gunicorn configuration file for production deployment.
"""
import os
import multiprocessing

# Port configuration
port = os.environ.get('FLASK_PORT', '5003')
bind = f"0.0.0.0:{port}"

# Concurrency configuration
# MUST use 1 worker because state (WorkflowState) is in-memory singleton
workers = 1
threads = 4

# Timeout and logging
timeout = 120
keepalive = 5
loglevel = "info"
accesslog = "-"
errorlog = "-"
