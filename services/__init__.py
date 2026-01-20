# services package initialization

from importlib import import_module
from typing import Any

__all__ = [
    'WorkflowService',
    'CSVService',
    'CacheService',
    'MonitoringService',
    'PerformanceService'
]


def __getattr__(name: str) -> Any:
    if name == 'WorkflowService':
        return import_module('services.workflow_service').WorkflowService
    if name == 'CSVService':
        return import_module('services.csv_service').CSVService
    if name == 'CacheService':
        return import_module('services.cache_service').CacheService
    if name == 'MonitoringService':
        return import_module('services.monitoring_service').MonitoringService
    if name == 'PerformanceService':
        return import_module('services.performance_service').PerformanceService
    raise AttributeError(f"module 'services' has no attribute {name!r}")
