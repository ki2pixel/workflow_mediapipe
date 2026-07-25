"""
Centralized business exceptions for the workflow_mediapipe domain.

All service-level errors inherit from WorkflowError so that consumers
can catch a single root type. Route handlers use these typed exceptions
instead of bare except: or blind Exception catches.
"""


class WorkflowError(Exception):
    """Root exception for all workflow-domain errors."""


class StepExecutionError(WorkflowError):
    """Raised when a step fails to launch or complete."""


class ConfigError(WorkflowError):
    """Raised for missing or invalid configuration / environment variables."""


class TokenValidationError(WorkflowError):
    """Raised when worker-token authentication fails."""


class AudioServiceError(WorkflowError):
    """Raised when an external STT service (Lemonfox / DeepInfra) fails."""
