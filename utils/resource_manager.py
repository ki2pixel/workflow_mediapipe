"""
Resource management utilities for workflow_mediapipe.

This module provides context managers and utilities for proper resource cleanup,
preventing memory leaks and ensuring resources are properly released.
"""

import logging
import cv2
import tempfile
from pathlib import Path
from typing import Optional, List, Any, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class VideoResourceManager:
    """
    Context manager for safe video capture resource management.
    
    Ensures that cv2.VideoCapture objects are properly released
    even if exceptions occur during processing.
    """
    
    def __init__(self, video_path: Union[str, Path]):
        """
        Initialize video resource manager.
        
        Args:
            video_path: Path to the video file to open
        """
        self.video_path = Path(video_path)
        self.capture: Optional[cv2.VideoCapture] = None
        self.is_opened = False
        
    def __enter__(self) -> cv2.VideoCapture:
        """
        Enter the context manager and open video capture.
        
        Returns:
            cv2.VideoCapture: Opened video capture object
            
        Raises:
            ValueError: If video file cannot be opened
            FileNotFoundError: If video file doesn't exist
        """
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        try:
            self.capture = cv2.VideoCapture(str(self.video_path))
            
            if not self.capture.isOpened():
                raise ValueError(f"Cannot open video file: {self.video_path}")
            
            self.is_opened = True
            logger.debug(f"Video capture opened successfully: {self.video_path.name}")
            
            return self.capture
            
        except Exception as e:
            # Ensure cleanup if opening fails
            if self.capture:
                self.capture.release()
            logger.error(f"Failed to open video capture for {self.video_path}: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and release video capture.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self.capture and self.is_opened:
            try:
                self.capture.release()
                logger.debug(f"Video capture released: {self.video_path.name}")
            except Exception as e:
                logger.error(f"Error releasing video capture for {self.video_path}: {e}")
            finally:
                self.capture = None
                self.is_opened = False
        
        # Log any exceptions that occurred during processing
        if exc_type:
            logger.error(f"Exception in video processing for {self.video_path}: {exc_val}")
        
        # Don't suppress exceptions
        return False


class TempFileManager:
    """
    Context manager for temporary file management.
    
    Ensures temporary files are cleaned up even if exceptions occur.
    """
    
    def __init__(self, suffix: str = "", prefix: str = "workflow_", dir: Optional[Path] = None):
        """
        Initialize temporary file manager.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            dir: Directory to create temp file in (defaults to system temp)
        """
        self.suffix = suffix
        self.prefix = prefix
        self.dir = dir
        self.temp_files: List[Path] = []
        
    def create_temp_file(self, suffix: Optional[str] = None, prefix: Optional[str] = None) -> Path:
        """
        Create a temporary file and track it for cleanup.
        
        Args:
            suffix: Override default suffix
            prefix: Override default prefix
            
        Returns:
            Path: Path to the created temporary file
        """
        actual_suffix = suffix or self.suffix
        actual_prefix = prefix or self.prefix
        
        # Create temporary file
        fd, temp_path = tempfile.mkstemp(
            suffix=actual_suffix,
            prefix=actual_prefix,
            dir=self.dir
        )
        
        # Close the file descriptor (we just need the path)
        import os
        os.close(fd)
        
        temp_path = Path(temp_path)
        self.temp_files.append(temp_path)
        
        logger.debug(f"Created temporary file: {temp_path}")
        return temp_path
    
    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and cleanup temporary files."""
        self.cleanup()
        
        # Don't suppress exceptions
        return False
    
    def cleanup(self):
        """Clean up all tracked temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.error(f"Failed to cleanup temporary file {temp_file}: {e}")
        
        self.temp_files.clear()


@contextmanager
def safe_video_processing(video_path: Union[str, Path], cleanup_temp_files: bool = True):
    """
    Context manager for safe video processing with automatic resource cleanup.
    
    Args:
        video_path: Path to video file
        cleanup_temp_files: Whether to automatically cleanup temporary files
        
    Yields:
        tuple: (video_capture, temp_file_manager)
        
    Example:
        with safe_video_processing("video.mp4") as (cap, temp_mgr):
            # Process video frames
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Create temporary files if needed
                temp_output = temp_mgr.create_temp_file(suffix=".json")
                
                # Process frame...
    """
    video_manager = VideoResourceManager(video_path)
    temp_manager = TempFileManager() if cleanup_temp_files else None
    
    try:
        with video_manager as capture:
            if temp_manager:
                with temp_manager:
                    yield capture, temp_manager
            else:
                yield capture, None
                
    except Exception as e:
        logger.error(f"Error in safe video processing for {video_path}: {e}")
        raise


def get_video_metadata(video_path: Union[str, Path]) -> dict:
    """
    Safely get video metadata with proper resource cleanup.
    
    Args:
        video_path: Path to video file
        
    Returns:
        dict: Video metadata including frame count, fps, width, height
        
    Raises:
        ValueError: If video cannot be opened
        FileNotFoundError: If video file doesn't exist
    """
    with VideoResourceManager(video_path) as capture:
        metadata = {
            'frame_count': int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fps': capture.get(cv2.CAP_PROP_FPS),
            'width': int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration_seconds': None
        }
        
        # Calculate duration if fps is available
        if metadata['fps'] > 0:
            metadata['duration_seconds'] = metadata['frame_count'] / metadata['fps']
        
        logger.debug(f"Retrieved metadata for {Path(video_path).name}: {metadata}")
        return metadata


class ResourceTracker:
    """
    Track and monitor resource usage during processing.
    
    Useful for debugging resource leaks and monitoring performance.
    """
    
    def __init__(self):
        """Initialize resource tracker."""
        self.active_resources = {}
        self.resource_counter = 0
    
    def register_resource(self, resource: Any, resource_type: str, description: str = "") -> str:
        """
        Register a resource for tracking.
        
        Args:
            resource: The resource object to track
            resource_type: Type of resource (e.g., 'video_capture', 'file_handle')
            description: Optional description
            
        Returns:
            str: Resource ID for later reference
        """
        resource_id = f"{resource_type}_{self.resource_counter}"
        self.resource_counter += 1
        
        self.active_resources[resource_id] = {
            'resource': resource,
            'type': resource_type,
            'description': description,
            'created_at': logger.handlers[0].formatter.formatTime(logger.makeRecord(
                '', 0, '', 0, '', (), None
            )) if logger.handlers else 'unknown'
        }
        
        logger.debug(f"Registered resource {resource_id}: {resource_type} - {description}")
        return resource_id
    
    def unregister_resource(self, resource_id: str):
        """
        Unregister a resource.
        
        Args:
            resource_id: ID of resource to unregister
        """
        if resource_id in self.active_resources:
            resource_info = self.active_resources.pop(resource_id)
            logger.debug(f"Unregistered resource {resource_id}: {resource_info['type']}")
        else:
            logger.warning(f"Attempted to unregister unknown resource: {resource_id}")
    
    def get_active_resources(self) -> dict:
        """
        Get information about currently active resources.
        
        Returns:
            dict: Information about active resources
        """
        return {
            'count': len(self.active_resources),
            'resources': {rid: {k: v for k, v in info.items() if k != 'resource'} 
                         for rid, info in self.active_resources.items()}
        }
    
    def cleanup_all(self):
        """
        Attempt to cleanup all tracked resources.
        
        This is a last-resort cleanup method.
        """
        logger.warning(f"Emergency cleanup of {len(self.active_resources)} resources")
        
        for resource_id, resource_info in list(self.active_resources.items()):
            try:
                resource = resource_info['resource']
                resource_type = resource_info['type']
                
                # Attempt cleanup based on resource type
                if resource_type == 'video_capture' and hasattr(resource, 'release'):
                    resource.release()
                elif resource_type == 'file_handle' and hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, '__exit__'):
                    resource.__exit__(None, None, None)
                
                self.unregister_resource(resource_id)
                
            except Exception as e:
                logger.error(f"Failed to cleanup resource {resource_id}: {e}")


# Global resource tracker instance
resource_tracker = ResourceTracker()
