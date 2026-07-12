# -*- coding: utf-8 -*-
"""
WSGI Entrypoint
Exposes the initialized Flask app instance for WSGI production servers.
"""
from app_new import init_app

app = init_app()
