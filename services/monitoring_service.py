"""
System Monitoring Service
Provides centralized system resource monitoring (CPU, RAM, GPU).
"""

import logging
import time
import sys
import platform
import subprocess
import psutil
from typing import Dict, Any, Optional
from functools import lru_cache
from config.settings import config

logger = logging.getLogger(__name__)

# GPU monitoring setup
PYNVML_AVAILABLE = False
try:
    import pynvml
    if config.ENABLE_GPU_MONITORING:
        PYNVML_AVAILABLE = True
        pynvml.nvmlInit()
        logger.info("GPU monitoring initialized successfully")
    else:
        logger.info("GPU monitoring disabled by configuration")
except ImportError:
    logger.warning("pynvml not available. GPU monitoring disabled.")
except Exception as e:
    logger.error(f"Failed to initialize GPU monitoring: {e}")


class MonitoringService:
    """
    Centralized service for system resource monitoring.
    Provides CPU, memory, and GPU usage statistics.
    """
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_gpu_device_info() -> Optional[Dict[str, Any]]:
        """
        Get GPU device information (cached).
        
        Returns:
            GPU device info or None if not available
        """
        if not PYNVML_AVAILABLE:
            return None
            
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            # Handle both string and bytes return types
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            return {
                "handle": handle,
                "name": name
            }
        except Exception as e:
            logger.warning(f"Unable to get GPU device info: {e}")
            return None
    
    @staticmethod
    def get_cpu_usage() -> float:
        """
        Get current CPU usage percentage.
        
        Returns:
            CPU usage percentage (0-100)
        """
        try:
            return round(psutil.cpu_percent(interval=0.1), 1)
        except Exception as e:
            logger.error(f"CPU usage error: {e}")
            return 0.0
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """
        Get current memory usage statistics.
        
        Returns:
            Memory usage dictionary:
            {
                "percent": float,
                "used_gb": float,
                "total_gb": float,
                "available_gb": float
            }
        """
        try:
            memory_info = psutil.virtual_memory()
            return {
                "percent": round(memory_info.percent, 1),
                "used_gb": round(memory_info.used / (1024**3), 2),
                "total_gb": round(memory_info.total / (1024**3), 2),
                "available_gb": round(memory_info.available / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"Memory usage error: {e}")
            return {
                "percent": 0.0,
                "used_gb": 0.0,
                "total_gb": 0.0,
                "available_gb": 0.0
            }
    
    @staticmethod
    def get_gpu_usage() -> Optional[Dict[str, Any]]:
        """
        Get current GPU usage statistics.
        
        Returns:
            GPU usage dictionary or None if not available:
            {
                "name": str,
                "utilization_percent": int,
                "memory": {
                    "percent": float,
                    "used_gb": float,
                    "total_gb": float
                },
                "temperature_c": int
            }
        """
        if not PYNVML_AVAILABLE:
            return None
            
        device_info = MonitoringService._get_gpu_device_info()
        if not device_info:
            return {"error": "GPU data not available"}
            
        try:
            handle = device_info["handle"]
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            return {
                "name": device_info["name"],
                "utilization_percent": utilization.gpu,
                "memory": {
                    "percent": round((mem_info.used / mem_info.total) * 100, 1),
                    "used_gb": round(mem_info.used / (1024**3), 2),
                    "total_gb": round(mem_info.total / (1024**3), 2),
                },
                "temperature_c": temperature
            }
        except Exception as e:
            logger.warning(f"GPU usage error: {e}")
            return {"error": "GPU data not available"}
    
    @staticmethod
    def get_disk_usage(path: str = None) -> Dict[str, float]:
        """
        Get disk usage statistics for a specific path.
        
        Args:
            path: Path to check (defaults to base path)
            
        Returns:
            Disk usage dictionary:
            {
                "percent": float,
                "used_gb": float,
                "total_gb": float,
                "free_gb": float
            }
        """
        if path is None:
            path = str(config.BASE_PATH_SCRIPTS)
            
        try:
            disk_info = psutil.disk_usage(path)
            return {
                "percent": round((disk_info.used / disk_info.total) * 100, 1),
                "used_gb": round(disk_info.used / (1024**3), 2),
                "total_gb": round(disk_info.total / (1024**3), 2),
                "free_gb": round(disk_info.free / (1024**3), 2)
            }
        except Exception as e:
            logger.error(f"Disk usage error for {path}: {e}")
            return {
                "percent": 0.0,
                "used_gb": 0.0,
                "total_gb": 0.0,
                "free_gb": 0.0
            }
    
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """
        Get comprehensive system status including CPU, memory, GPU, and disk.
        
        Returns:
            System status dictionary:
            {
                "cpu_percent": float,
                "memory": dict,
                "gpu": dict|null,
                "disk": dict,
                "timestamp": str
            }
        """
        try:
            # Ensure projects directory exists
            projects_dir = config.BASE_PATH_SCRIPTS / 'projets_extraits'
            projects_dir.mkdir(parents=True, exist_ok=True)
            
            from datetime import datetime, timezone
            
            return {
                "cpu_percent": MonitoringService.get_cpu_usage(),
                "memory": MonitoringService.get_memory_usage(),
                "gpu": MonitoringService.get_gpu_usage(),
                "disk": MonitoringService.get_disk_usage(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"System status error: {e}")
            raise

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """
        Provide environment diagnostics useful for troubleshooting.

        Returns:
            dict: Environment information including versions, GPU availability,
                  and filtered configuration flags (no secrets).
        """
        # Python
        python_version = sys.version.split(" (", 1)[0]
        implementation = platform.python_implementation()

        # FFmpeg version (best-effort, non-fatal)
        ffmpeg_version = "unknown"
        try:
            proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=2)
            if proc.returncode == 0 and proc.stdout:
                first_line = proc.stdout.splitlines()[0].strip()
                ffmpeg_version = first_line
            elif proc.stderr:
                # Some builds print to stderr
                first_line = proc.stderr.splitlines()[0].strip()
                ffmpeg_version = first_line
        except Exception as e:
            logger.debug(f"FFmpeg version check failed: {e}")

        # GPU info (availability + name if possible)
        gpu_available = bool(PYNVML_AVAILABLE and MonitoringService._get_gpu_device_info())
        gpu_name = None
        if gpu_available:
            info = MonitoringService._get_gpu_device_info()
            if info and isinstance(info.get("name"), str):
                gpu_name = info["name"]

        # Filtered configuration flags (no secrets)
        filtered_config = {
            "ENABLE_GPU_MONITORING": bool(getattr(config, "ENABLE_GPU_MONITORING", False)),
            "DRY_RUN_DOWNLOADS": bool(getattr(config, "DRY_RUN_DOWNLOADS", False)),
            "FLASK_DEBUG": bool(getattr(config, "DEBUG", False)),
        }

        from datetime import datetime, timezone
        return {
            "python": {
                "version": python_version,
                "implementation": implementation,
            },
            "ffmpeg": {
                "version": ffmpeg_version,
            },
            "gpu": {
                "available": gpu_available,
                "name": gpu_name,
            },
            "config_flags": filtered_config,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """
        Get information about the current process.
        
        Returns:
            Process information dictionary:
            {
                "pid": int,
                "cpu_percent": float,
                "memory_mb": float,
                "threads": int,
                "uptime_seconds": float
            }
        """
        try:
            process = psutil.Process()
            create_time = process.create_time()
            
            return {
                "pid": process.pid,
                "cpu_percent": round(process.cpu_percent(), 1),
                "memory_mb": round(process.memory_info().rss / (1024**2), 1),
                "threads": process.num_threads(),
                "uptime_seconds": round(time.time() - create_time, 1)
            }
        except Exception as e:
            logger.error(f"Process info error: {e}")
            return {
                "pid": 0,
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "threads": 0,
                "uptime_seconds": 0.0
            }
    
    @staticmethod
    def is_system_healthy() -> Dict[str, Any]:
        """
        Check if system resources are within healthy limits.
        
        Returns:
            Health status dictionary:
            {
                "healthy": bool,
                "warnings": list,
                "critical": list
            }
        """
        warnings = []
        critical = []
        
        try:
            # Check CPU usage
            cpu_percent = MonitoringService.get_cpu_usage()
            if cpu_percent > 90:
                critical.append(f"High CPU usage: {cpu_percent}%")
            elif cpu_percent > 75:
                warnings.append(f"Elevated CPU usage: {cpu_percent}%")
            
            # Check memory usage
            memory = MonitoringService.get_memory_usage()
            if memory["percent"] > 95:
                critical.append(f"Critical memory usage: {memory['percent']}%")
            elif memory["percent"] > 85:
                warnings.append(f"High memory usage: {memory['percent']}%")
            
            # Check disk usage
            disk = MonitoringService.get_disk_usage()
            if disk["percent"] > 95:
                critical.append(f"Critical disk usage: {disk['percent']}%")
            elif disk["percent"] > 85:
                warnings.append(f"High disk usage: {disk['percent']}%")
            
            # Check GPU temperature if available
            gpu = MonitoringService.get_gpu_usage()
            if gpu and "temperature_c" in gpu:
                temp = gpu["temperature_c"]
                if temp > 85:
                    critical.append(f"High GPU temperature: {temp}°C")
                elif temp > 75:
                    warnings.append(f"Elevated GPU temperature: {temp}°C")
            
            return {
                "healthy": len(critical) == 0,
                "warnings": warnings,
                "critical": critical
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "healthy": False,
                "warnings": [],
                "critical": [f"Health check failed: {str(e)}"]
            }
