"""
Performance Utilities
Comprehensive performance optimization utilities for backend operations.
"""

import time
import logging
import threading
from functools import lru_cache, wraps
from typing import Dict, Any, Optional, Callable, List
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)

# Performance tracking
performance_stats = {
    "function_calls": {},
    "cache_hits": 0,
    "cache_misses": 0,
    "parallel_operations": 0
}
stats_lock = threading.Lock()


def track_performance(func_name: str = None):
    """
    Decorator to track function performance.
    
    Args:
        func_name: Optional custom name for the function
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration = (time.perf_counter() - start_time) * 1000  # Convert to ms
                
                with stats_lock:
                    if name not in performance_stats["function_calls"]:
                        performance_stats["function_calls"][name] = {
                            "total_time": 0,
                            "calls": 0,
                            "errors": 0,
                            "avg_time": 0
                        }
                    
                    stats = performance_stats["function_calls"][name]
                    stats["total_time"] += duration
                    stats["calls"] += 1
                    if not success:
                        stats["errors"] += 1
                    stats["avg_time"] = stats["total_time"] / stats["calls"]
                
                # Log slow operations
                if duration > 1000:  # More than 1 second
                    logger.warning(f"Slow operation: {name} took {duration:.2f}ms")
            
            return result
        
        return wrapper
    return decorator


@contextmanager
def profile_section(section_name: str):
    """
    Context manager for profiling code sections.
    
    Args:
        section_name: Name of the section being profiled
        
    Usage:
        with profile_section("video_processing"):
            # Code to profile
            process_video()
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
        
        with stats_lock:
            if section_name not in performance_stats["function_calls"]:
                performance_stats["function_calls"][section_name] = {
                    "total_time": 0,
                    "calls": 0,
                    "errors": 0,
                    "avg_time": 0
                }
            
            stats = performance_stats["function_calls"][section_name]
            stats["total_time"] += elapsed_time
            stats["calls"] += 1
            stats["avg_time"] = stats["total_time"] / stats["calls"]


@lru_cache(maxsize=128)
def get_video_metadata_cached(video_path: str) -> Dict[str, Any]:
    """
    Get video metadata with caching to avoid repeated file reads.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Video metadata dictionary
    """
    try:
        import cv2
        
        with stats_lock:
            performance_stats["cache_misses"] += 1
        
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


def cached_with_stats(maxsize: int = 128, typed: bool = False):
    """
    LRU cache decorator with statistics tracking.
    
    Args:
        maxsize: Maximum cache size
        typed: Whether to consider argument types
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        cached_func = lru_cache(maxsize=maxsize, typed=typed)(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if result is in cache
            cache_info = cached_func.cache_info()
            initial_hits = cache_info.hits
            
            result = cached_func(*args, **kwargs)
            
            # Update statistics
            new_cache_info = cached_func.cache_info()
            if new_cache_info.hits > initial_hits:
                with stats_lock:
                    performance_stats["cache_hits"] += 1
            else:
                with stats_lock:
                    performance_stats["cache_misses"] += 1
            
            return result
        
        # Expose cache methods
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        
        return wrapper
    
    return decorator


@track_performance("parallel_video_processing")
def process_videos_parallel(video_list: List[Path], 
                          process_func: Callable,
                          max_workers: int = 4,
                          **kwargs) -> List[bool]:
    """
    Process multiple videos with controlled parallelism.
    
    Args:
        video_list: List of video file paths
        process_func: Function to process each video
        max_workers: Maximum number of parallel workers
        **kwargs: Additional arguments for process_func
        
    Returns:
        List of success/failure results
    """
    if not video_list:
        return []
    
    results = []
    
    with stats_lock:
        performance_stats["parallel_operations"] += 1
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_video = {
            executor.submit(process_func, video, **kwargs): video
            for video in video_list
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Completed processing: {video.name}")
            except Exception as e:
                logger.error(f"Failed processing {video.name}: {e}")
                results.append(False)
    
    return results


@track_performance("batch_file_operations")
def batch_file_operations(file_paths: List[Path], 
                         operation: Callable,
                         batch_size: int = 10,
                         **kwargs) -> List[Any]:
    """
    Process files in batches for memory efficiency.
    
    Args:
        file_paths: List of file paths to process
        operation: Function to apply to each file
        batch_size: Number of files to process in each batch
        **kwargs: Additional arguments for operation
        
    Returns:
        List of operation results
    """
    results = []
    
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        
        with profile_section(f"batch_{i//batch_size + 1}"):
            batch_results = []
            for file_path in batch:
                try:
                    result = operation(file_path, **kwargs)
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Batch operation failed for {file_path}: {e}")
                    batch_results.append(None)
            
            results.extend(batch_results)
    
    return results


class PerformanceTimer:
    """
    Context manager for timing operations with automatic logging.
    """
    
    def __init__(self, operation_name: str, log_threshold_ms: float = 100.0):
        """
        Initialize performance timer.
        
        Args:
            operation_name: Name of the operation being timed
            log_threshold_ms: Log warning if operation takes longer than this
        """
        self.operation_name = operation_name
        self.log_threshold_ms = log_threshold_ms
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration_ms = (self.end_time - self.start_time) * 1000
        
        if duration_ms > self.log_threshold_ms:
            logger.warning(f"Slow operation: {self.operation_name} took {duration_ms:.2f}ms")
        else:
            logger.debug(f"Operation: {self.operation_name} took {duration_ms:.2f}ms")
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


def optimize_memory_usage():
    """
    Perform memory optimization operations.
    """
    import gc
    
    # Clear function caches
    get_video_metadata_cached.cache_clear()
    
    # Force garbage collection
    collected = gc.collect()
    
    logger.info(f"Memory optimization: collected {collected} objects")


def get_performance_stats() -> Dict[str, Any]:
    """
    Get comprehensive performance statistics.
    
    Returns:
        Performance statistics dictionary
    """
    with stats_lock:
        stats = {
            "function_calls": dict(performance_stats["function_calls"]),
            "cache_stats": {
                "hits": performance_stats["cache_hits"],
                "misses": performance_stats["cache_misses"],
                "hit_rate": (
                    performance_stats["cache_hits"] / 
                    (performance_stats["cache_hits"] + performance_stats["cache_misses"])
                    if (performance_stats["cache_hits"] + performance_stats["cache_misses"]) > 0
                    else 0
                )
            },
            "parallel_operations": performance_stats["parallel_operations"]
        }
    
    # Add cache info for cached functions
    try:
        stats["video_metadata_cache"] = {
            "info": get_video_metadata_cached.cache_info()._asdict()
        }
    except AttributeError:
        pass
    
    return stats


def reset_performance_stats():
    """Reset all performance statistics."""
    global performance_stats
    
    with stats_lock:
        performance_stats = {
            "function_calls": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_operations": 0
        }
    
    # Clear function caches
    get_video_metadata_cached.cache_clear()
    
    logger.info("Performance statistics reset")


def print_performance_summary(logger_fn: Callable = logger.info):
    """
    Print a formatted summary of performance statistics.
    
    Args:
        logger_fn: Function to use for logging output
    """
    stats = get_performance_stats()
    
    logger_fn("\n--- PERFORMANCE SUMMARY ---")
    
    # Function call statistics
    if stats["function_calls"]:
        logger_fn("Function Call Statistics:")
        sorted_functions = sorted(
            stats["function_calls"].items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )
        
        for func_name, func_stats in sorted_functions[:10]:  # Top 10
            logger_fn(
                f"  {func_name}: {func_stats['calls']} calls, "
                f"{func_stats['total_time']:.2f}ms total, "
                f"{func_stats['avg_time']:.2f}ms avg"
            )
    
    # Cache statistics
    cache_stats = stats["cache_stats"]
    logger_fn(f"Cache Statistics: {cache_stats['hit_rate']:.1%} hit rate "
             f"({cache_stats['hits']} hits, {cache_stats['misses']} misses)")
    
    # Parallel operations
    logger_fn(f"Parallel Operations: {stats['parallel_operations']}")
    
    logger_fn("--- END PERFORMANCE SUMMARY ---\n")


# Utility functions for common performance patterns

def memoize_with_ttl(ttl_seconds: int = 300):
    """
    Memoization decorator with time-to-live.
    
    Args:
        ttl_seconds: Time to live for cached results
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            # Check if result is cached and not expired
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    with stats_lock:
                        performance_stats["cache_hits"] += 1
                    return result
                else:
                    del cache[key]
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            
            with stats_lock:
                performance_stats["cache_misses"] += 1
            
            return result
        
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: {"size": len(cache)}
        
        return wrapper
    
    return decorator
