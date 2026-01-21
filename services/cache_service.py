"""
Cache Service
Centralized caching service for improved performance.
"""

import logging
import json
import time
import re
from functools import lru_cache, wraps
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from flask_caching import Cache

from config.settings import config
from services.workflow_state import get_workflow_state

logger = logging.getLogger(__name__)

_SAFE_STEP_KEY_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

# Global cache instance (will be initialized by Flask app)
cache_instance: Optional[Cache] = None

# Cache statistics
cache_stats = {
    "hits": 0,
    "misses": 0,
    "errors": 0,
    "last_reset": time.time()
}


class CacheService:
    """
    Centralized caching service with performance tracking.
    Provides intelligent caching for expensive operations.
    """
    
    @staticmethod
    def initialize(cache: Cache) -> None:
        """
        Initialize the cache service with Flask-Caching instance.
        
        Args:
            cache: Flask-Caching instance
        """
        global cache_instance
        cache_instance = cache
        logger.info("Cache service initialized")
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Cache statistics dictionary
        """
        total_requests = cache_stats["hits"] + cache_stats["misses"]
        hit_rate = (cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": cache_stats["hits"],
            "misses": cache_stats["misses"],
            "errors": cache_stats["errors"],
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "uptime_seconds": round(time.time() - cache_stats["last_reset"], 1)
        }
    
    @staticmethod
    def clear_cache() -> None:
        """Clear all cached data."""
        if cache_instance:
            cache_instance.clear()
            logger.info("Cache cleared")
    
    @staticmethod
    def reset_stats() -> None:
        """Reset cache statistics."""
        global cache_stats
        cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "last_reset": time.time()
        }
        logger.info("Cache statistics reset")
    
    @staticmethod
    def cached_with_stats(timeout: int = 300, key_prefix: str = ""):
        """
        Decorator for caching with statistics tracking.
        
        Args:
            timeout: Cache timeout in seconds
            key_prefix: Prefix for cache keys
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not cache_instance:
                    cache_stats["errors"] += 1
                    return func(*args, **kwargs)
                
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                try:
                    # Try to get from cache
                    result = cache_instance.get(cache_key)
                    if result is not None:
                        cache_stats["hits"] += 1
                        return result
                    
                    # Cache miss - execute function
                    cache_stats["misses"] += 1
                    result = func(*args, **kwargs)
                    
                    # Store in cache
                    cache_instance.set(cache_key, result, timeout=timeout)
                    return result
                    
                except Exception as e:
                    cache_stats["errors"] += 1
                    logger.error(f"Cache error for {func.__name__}: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_video_metadata(video_path: str) -> Dict[str, Any]:
        """
        Get video metadata with caching to avoid repeated file reads.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video metadata dictionary
        """
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            try:
                if not cap.isOpened():
                    raise ValueError(f"Cannot open video: {video_path}")
                
                metadata = {
                    'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    'fps': cap.get(cv2.CAP_PROP_FPS),
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'duration_seconds': None
                }
                
                # Calculate duration
                if metadata['fps'] > 0 and metadata['frame_count'] > 0:
                    metadata['duration_seconds'] = metadata['frame_count'] / metadata['fps']
                
                return metadata
            finally:
                cap.release()
                
        except Exception as e:
            logger.error(f"Video metadata error for {video_path}: {e}")
            return {
                'frame_count': 0,
                'fps': 0,
                'width': 0,
                'height': 0,
                'duration_seconds': None,
                'error': str(e)
            }
    
    @staticmethod
    def get_cached_frontend_config() -> Dict[str, Any]:
        """
        Get cached frontend configuration.

        Returns:
            Frontend-safe configuration dictionary
        """
        try:
            # Try to use cache if available
            if cache_instance:
                try:
                    cached_result = cache_instance.get("frontend_config")
                    if cached_result is not None:
                        cache_stats["hits"] += 1
                        logger.debug("Frontend config cache hit")
                        return cached_result
                except Exception as cache_error:
                    logger.warning(f"Cache access failed, generating fresh config: {cache_error}")

            # Generate fresh config
            from config.workflow_commands import WorkflowCommandsConfig

            commands_config = WorkflowCommandsConfig().get_config()
            if not commands_config:
                logger.error("WorkflowCommandsConfig is empty or not available")
                cache_stats["errors"] += 1
                return {}

            result: Dict[str, Any] = {}
            for step_key, step_data_orig in commands_config.items():
                if not isinstance(step_key, str) or not _SAFE_STEP_KEY_PATTERN.match(step_key):
                    logger.error(
                        "Unsafe step_key detected in WorkflowCommandsConfig; skipping for frontend DOM safety: %r",
                        step_key,
                    )
                    continue
                frontend_step_data: Dict[str, Any] = {}
                for key, value in step_data_orig.items():
                    if key == "progress_patterns":
                        continue
                    if isinstance(value, Path):
                        frontend_step_data[key] = str(value)
                    elif key == "cmd" and isinstance(value, list):
                        frontend_step_data[key] = [str(item) for item in value]
                    elif key == "specific_logs" and isinstance(value, list):
                        safe_logs = []
                        for log_entry in value:
                            if not isinstance(log_entry, dict):
                                continue
                            safe_entry = log_entry.copy()
                            if 'path' in safe_entry and isinstance(safe_entry['path'], Path):
                                safe_entry['path'] = str(safe_entry['path'])
                            safe_logs.append(safe_entry)
                        frontend_step_data[key] = safe_logs
                    else:
                        frontend_step_data[key] = value
                result[step_key] = frontend_step_data
            logger.debug(f"Generated fresh frontend config with {len(result)} steps")

            # Cache the result if cache is available
            if cache_instance:
                try:
                    cache_instance.set("frontend_config", result, timeout=300)
                    cache_stats["misses"] += 1
                    logger.debug("Frontend config cached successfully")
                except Exception as cache_error:
                    logger.warning(f"Failed to cache frontend config: {cache_error}")

            return result
        except Exception as e:
            logger.error(f"Frontend config cache error: {e}")
            cache_stats["errors"] += 1
            return {}
    
    @staticmethod
    def get_cached_log_content(step_key: str, log_index: int) -> Dict[str, Any]:
        """
        Get cached log file content.

        Args:
            step_key: Step identifier
            log_index: Log file index

        Returns:
            Log content dictionary

        Raises:
            ValueError: If step or log not found
        """
        try:
            # Try to use cache if available
            cache_key = f"log_content:{step_key}:{log_index}"
            if cache_instance:
                cached_result = cache_instance.get(cache_key)
                if cached_result is not None:
                    cache_stats["hits"] += 1
                    return cached_result

            from services.workflow_service import WorkflowService

            result = WorkflowService.get_step_log_file(step_key, log_index)

            # Cache the result if cache is available
            if cache_instance:
                cache_instance.set(cache_key, result, timeout=60)
                cache_stats["misses"] += 1

            return result
            
        except Exception as e:
            logger.error(f"Log content cache error for {step_key}/{log_index}: {e}")
            raise
    
    @staticmethod
    def get_cached_step_status(step_key: str) -> Dict[str, Any]:
        """
        Get cached step status to reduce computation.
        
        Args:
            step_key: Step identifier
            
        Returns:
            Step status dictionary
        """
        try:
            step_info = get_workflow_state().get_step_info(step_key)

            if not step_info:
                raise ValueError(f"Step '{step_key}' not found")

            return step_info.copy()
            
        except Exception as e:
            logger.error(f"Step status cache error for {step_key}: {e}")
            raise
    
    @staticmethod
    def invalidate_step_cache(step_key: str) -> None:
        """
        Invalidate cache entries for a specific step.
        
        Args:
            step_key: Step identifier
        """
        if not cache_instance:
            return
        
        try:
            # Clear step-specific cache entries
            cache_keys_to_clear = [
                f"step_status:{step_key}",
                f"log_content:{step_key}"
            ]
            
            for key in cache_keys_to_clear:
                cache_instance.delete(key)
            
            logger.debug(f"Invalidated cache for step {step_key}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error for {step_key}: {e}")
    
    @staticmethod
    def warm_cache() -> None:
        """
        Pre-populate cache with commonly accessed data.
        """
        try:
            logger.info("Starting cache warm-up")
            
            # Warm up frontend config
            CacheService.get_cached_frontend_config()
            
            # Warm up step statuses
            workflow_state = get_workflow_state()
            step_keys = list((workflow_state.get_all_steps_info() or {}).keys())
            if not step_keys:
                from config.workflow_commands import WorkflowCommandsConfig
                step_keys = WorkflowCommandsConfig().get_all_step_keys()

            for step_key in step_keys:
                try:
                    CacheService.get_cached_step_status(step_key)
                except Exception:
                    pass  # Skip errors during warm-up
            
            logger.info("Cache warm-up completed")
            
        except Exception as e:
            logger.error(f"Cache warm-up error: {e}")
    
    @staticmethod
    def get_cache_size_estimate() -> Dict[str, Any]:
        """
        Get an estimate of cache memory usage.
        
        Returns:
            Cache size information
        """
        try:
            # This is a rough estimate since Flask-Caching doesn't provide direct size info
            stats = CacheService.get_cache_stats()
            
            # Estimate based on number of cached items
            estimated_items = stats["hits"] + stats["misses"]
            estimated_size_mb = estimated_items * 0.001  # Rough estimate: 1KB per item
            
            return {
                "estimated_items": estimated_items,
                "estimated_size_mb": round(estimated_size_mb, 2),
                "cache_type": "SimpleCache",
                "note": "Size estimates are approximate"
            }
            
        except Exception as e:
            logger.error(f"Cache size estimation error: {e}")
            return {
                "estimated_items": 0,
                "estimated_size_mb": 0,
                "error": str(e)
            }
