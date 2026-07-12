# -*- coding: utf-8 -*-
"""
Shared decorator utilities for route blueprints.
"""
import time
import logging
from functools import wraps
from services.performance_service import PerformanceService

logger = logging.getLogger(__name__)

def measure_api(endpoint_name: str):
    """Decorator to measure API response time and record it via PerformanceService.

    Args:
        endpoint_name: Logical name of the endpoint for metrics.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            status_code = 200
            try:
                resp = fn(*args, **kwargs)
                # Flask can return a tuple (payload, status)
                if isinstance(resp, tuple) and len(resp) >= 2:
                    status_code = resp[1]
                return resp
            except Exception:
                status_code = 500
                raise
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                try:
                    PerformanceService.record_api_response_time(endpoint_name, elapsed_ms, status_code)
                except Exception:
                    logger.debug("Failed to record API performance metric", exc_info=True)
        return wrapper
    return decorator
