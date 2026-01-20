"""
Performance Service
Centralized performance monitoring and profiling service.
"""

import logging
import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)

# Global profiling statistics
PROFILING_STATS = defaultdict(lambda: {"total_time": 0, "calls": 0, "avg_time": 0})
PROFILING_LOCK = threading.Lock()

# Performance metrics history
PERFORMANCE_HISTORY = deque(maxlen=100)  # Keep last 100 measurements
PERFORMANCE_LOCK = threading.Lock()

# Performance alerts
PERFORMANCE_ALERTS = deque(maxlen=50)  # Keep last 50 alerts
ALERT_THRESHOLDS = {
    "cpu_percent": 85.0,
    "memory_percent": 90.0,
    "response_time_ms": 1000.0,
    "error_rate_percent": 5.0
}

# Background monitoring state
BACKGROUND_MONITORING_ACTIVE = False
MONITORING_THREAD = None
MONITORING_LOCK = threading.Lock()


class PerformanceService:
    """
    Centralized service for performance monitoring and profiling.
    Tracks system performance, response times, and provides profiling capabilities.
    """
    
    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary:
            {
                "profiling_stats": dict,
                "cache_stats": dict,
                "system_performance": dict,
                "performance_history": list,
                "alerts": list
            }
        """
        try:
            from services.cache_service import CacheService
            
            with PROFILING_LOCK:
                profiling_data = {k: dict(v) for k, v in PROFILING_STATS.items()}
            
            with PERFORMANCE_LOCK:
                history_data = list(PERFORMANCE_HISTORY)
                alerts_data = list(PERFORMANCE_ALERTS)
            
            return {
                "profiling_stats": profiling_data,
                "cache_stats": CacheService.get_cache_stats(),
                "system_performance": MonitoringService.get_system_status(),
                "performance_history": history_data,
                "alerts": alerts_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance metrics error: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @staticmethod
    def reset_profiling_stats() -> None:
        """Reset profiling statistics."""
        global PROFILING_STATS
        
        with PROFILING_LOCK:
            PROFILING_STATS = defaultdict(lambda: {"total_time": 0, "calls": 0, "avg_time": 0})
        
        logger.info("Profiling statistics reset")
    
    @staticmethod
    @contextmanager
    def profile_section(section_name: str):
        """
        Context manager for profiling code sections.
        
        Args:
            section_name: Name of the section being profiled
            
        Usage:
            with PerformanceService.profile_section("video_processing"):
                # Code to profile
                process_video()
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            with PROFILING_LOCK:
                stats = PROFILING_STATS[section_name]
                stats["total_time"] += elapsed_time
                stats["calls"] += 1
                stats["avg_time"] = stats["total_time"] / stats["calls"]
    
    @staticmethod
    def record_api_response_time(endpoint: str, response_time_ms: float, status_code: int) -> None:
        """
        Record API response time for performance tracking.
        
        Args:
            endpoint: API endpoint name
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            metric = {
                "timestamp": timestamp,
                "endpoint": endpoint,
                "response_time_ms": round(response_time_ms, 2),
                "status_code": status_code,
                "is_error": status_code >= 400
            }
            
            with PERFORMANCE_LOCK:
                PERFORMANCE_HISTORY.append(metric)
            
            # Check for performance alerts
            PerformanceService._check_performance_alerts(metric)
            
        except Exception as e:
            logger.error(f"Response time recording error: {e}")
    
    @staticmethod
    def record_system_metrics() -> None:
        """Record current system metrics for trend analysis."""
        try:
            system_status = MonitoringService.get_system_status()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            metric = {
                "timestamp": timestamp,
                "type": "system",
                "cpu_percent": system_status["cpu_percent"],
                "memory_percent": system_status["memory"]["percent"],
                "disk_percent": system_status.get("disk", {}).get("percent", 0)
            }
            
            # Add GPU metrics if available
            if system_status.get("gpu") and "utilization_percent" in system_status["gpu"]:
                metric["gpu_percent"] = system_status["gpu"]["utilization_percent"]
                metric["gpu_memory_percent"] = system_status["gpu"]["memory"]["percent"]
            
            with PERFORMANCE_LOCK:
                PERFORMANCE_HISTORY.append(metric)
            
            # Check for system alerts
            PerformanceService._check_system_alerts(metric)
            
        except Exception as e:
            logger.error(f"System metrics recording error: {e}")
    
    @staticmethod
    def get_profiling_summary() -> Dict[str, Any]:
        """
        Get formatted profiling summary.
        
        Returns:
            Profiling summary with top performers and statistics
        """
        try:
            with PROFILING_LOCK:
                if not PROFILING_STATS:
                    return {
                        "message": "No profiling data collected",
                        "total_sections": 0,
                        "top_sections": []
                    }
                
                # Calculate total time across all sections
                total_time_all = sum(stats["total_time"] for stats in PROFILING_STATS.values())
                
                # Sort by total time descending
                sorted_stats = sorted(
                    PROFILING_STATS.items(),
                    key=lambda item: item[1]["total_time"],
                    reverse=True
                )
                
                # Format top sections
                top_sections = []
                for name, stats in sorted_stats[:10]:  # Top 10
                    percentage = (stats["total_time"] / total_time_all * 100) if total_time_all > 0 else 0
                    
                    top_sections.append({
                        "name": name,
                        "total_time_ms": round(stats["total_time"], 2),
                        "calls": stats["calls"],
                        "avg_time_ms": round(stats["avg_time"], 4),
                        "percentage": round(percentage, 2)
                    })
                
                return {
                    "total_sections": len(PROFILING_STATS),
                    "total_time_ms": round(total_time_all, 2),
                    "top_sections": top_sections
                }
                
        except Exception as e:
            logger.error(f"Profiling summary error: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_performance_trends() -> Dict[str, Any]:
        """
        Analyze performance trends from historical data.
        
        Returns:
            Performance trends analysis
        """
        try:
            with PERFORMANCE_LOCK:
                if len(PERFORMANCE_HISTORY) < 2:
                    return {
                        "message": "Insufficient data for trend analysis",
                        "data_points": len(PERFORMANCE_HISTORY)
                    }
                
                # Separate API and system metrics
                api_metrics = [m for m in PERFORMANCE_HISTORY if m.get("endpoint")]
                system_metrics = [m for m in PERFORMANCE_HISTORY if m.get("type") == "system"]
                
                trends = {}
                
                # API response time trends
                if api_metrics:
                    response_times = [m["response_time_ms"] for m in api_metrics[-20:]]  # Last 20
                    trends["api"] = {
                        "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
                        "max_response_time_ms": max(response_times),
                        "min_response_time_ms": min(response_times),
                        "error_rate_percent": round(
                            sum(1 for m in api_metrics[-20:] if m["is_error"]) / len(api_metrics[-20:]) * 100, 2
                        )
                    }
                
                # System resource trends
                if system_metrics:
                    recent_system = system_metrics[-10:]  # Last 10
                    trends["system"] = {
                        "avg_cpu_percent": round(
                            sum(m["cpu_percent"] for m in recent_system) / len(recent_system), 1
                        ),
                        "avg_memory_percent": round(
                            sum(m["memory_percent"] for m in recent_system) / len(recent_system), 1
                        ),
                        "max_cpu_percent": max(m["cpu_percent"] for m in recent_system),
                        "max_memory_percent": max(m["memory_percent"] for m in recent_system)
                    }
                
                return {
                    "trends": trends,
                    "data_points": {
                        "api": len(api_metrics),
                        "system": len(system_metrics)
                    },
                    "analysis_period": "last_20_measurements"
                }
                
        except Exception as e:
            logger.error(f"Performance trends error: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _check_performance_alerts(metric: Dict[str, Any]) -> None:
        """
        Check for performance alerts based on thresholds.
        
        Args:
            metric: Performance metric to check
        """
        try:
            alerts = []
            
            # Check API response time
            if "response_time_ms" in metric:
                if metric["response_time_ms"] > ALERT_THRESHOLDS["response_time_ms"]:
                    alerts.append({
                        "type": "slow_response",
                        "message": f"Slow API response: {metric['response_time_ms']}ms for {metric['endpoint']}",
                        "severity": "warning",
                        "timestamp": metric["timestamp"]
                    })
            
            # Add alerts to queue
            for alert in alerts:
                PERFORMANCE_ALERTS.append(alert)
                logger.warning(f"Performance alert: {alert['message']}")
                
        except Exception as e:
            logger.error(f"Performance alert check error: {e}")
    
    @staticmethod
    def _check_system_alerts(metric: Dict[str, Any]) -> None:
        """
        Check for system resource alerts.
        
        Args:
            metric: System metric to check
        """
        try:
            alerts = []
            
            if metric.get("cpu_percent", 0) > ALERT_THRESHOLDS["cpu_percent"]:
                alerts.append({
                    "type": "cpu_high",
                    "severity": "warning",
                    "message": f"CPU usage high: {metric['cpu_percent']}%",
                    "timestamp": metric["timestamp"]
                })
            
            if metric.get("memory_percent", 0) > ALERT_THRESHOLDS["memory_percent"]:
                alerts.append({
                    "type": "memory_high",
                    "severity": "warning",
                    "message": f"Memory usage high: {metric['memory_percent']}%",
                    "timestamp": metric["timestamp"]
                })
            
            if alerts:
                with PERFORMANCE_LOCK:
                    PERFORMANCE_ALERTS.extend(alerts)
                    
        except Exception as e:
            logger.error(f"System alerts check error: {e}")
    
    @staticmethod
    def clear_alerts() -> None:
        """Clear all performance alerts."""
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.clear()
        logger.info("Performance alerts cleared")
    
    @staticmethod
    def update_alert_thresholds(thresholds: Dict[str, float]) -> None:
        """
        Update performance alert thresholds.
        
        Args:
            thresholds: Dictionary of threshold values
        """
        global ALERT_THRESHOLDS
        
        for key, value in thresholds.items():
            if key in ALERT_THRESHOLDS:
                ALERT_THRESHOLDS[key] = value
                logger.info(f"Updated alert threshold {key} to {value}")
    
    @staticmethod
    def start_background_monitoring(interval_seconds: int = 30) -> None:
        """
        Start background system monitoring thread.

        Args:
            interval_seconds: Monitoring interval in seconds
        """
        global BACKGROUND_MONITORING_ACTIVE, MONITORING_THREAD

        with MONITORING_LOCK:
            if BACKGROUND_MONITORING_ACTIVE:
                logger.debug("Background monitoring already active, skipping")
                return

            def monitor_loop():
                global BACKGROUND_MONITORING_ACTIVE
                while BACKGROUND_MONITORING_ACTIVE:
                    try:
                        PerformanceService.record_system_metrics()
                        time.sleep(interval_seconds)
                    except Exception as e:
                        logger.error(f"Background monitoring error: {e}")
                        time.sleep(interval_seconds)

            BACKGROUND_MONITORING_ACTIVE = True
            MONITORING_THREAD = threading.Thread(target=monitor_loop, daemon=True)
            MONITORING_THREAD.start()
            logger.info(f"Background performance monitoring started (interval: {interval_seconds}s)")

    @staticmethod
    def stop_background_monitoring() -> None:
        """Stop background system monitoring."""
        global BACKGROUND_MONITORING_ACTIVE, MONITORING_THREAD

        with MONITORING_LOCK:
            if BACKGROUND_MONITORING_ACTIVE:
                BACKGROUND_MONITORING_ACTIVE = False
                logger.info("Background performance monitoring stopped")
            else:
                logger.debug("Background monitoring was not active")

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Get comprehensive statistics for the performance dashboard.
        
        Returns:
            Dashboard statistics including:
            - API response time trends (last 50)
            - System resource trends (last 50)
            - Step execution history
            - Performance alerts
            - Cache statistics
            - Summary metrics
        """
        try:
            from services.cache_service import CacheService
            
            with PERFORMANCE_LOCK:
                history_data = list(PERFORMANCE_HISTORY)
            
            # Separate API and system metrics
            api_metrics = [m for m in history_data if m.get("endpoint")][-50:]
            system_metrics = [m for m in history_data if m.get("type") == "system"][-50:]
            
            # Calculate summary statistics
            summary = {
                "total_api_calls": len(api_metrics),
                "total_errors": sum(1 for m in api_metrics if m.get("is_error", False)),
                "avg_response_time_ms": 0,
                "error_rate_percent": 0
            }
            
            if api_metrics:
                response_times = [m["response_time_ms"] for m in api_metrics]
                summary["avg_response_time_ms"] = round(sum(response_times) / len(response_times), 2)
                summary["error_rate_percent"] = round((summary["total_errors"] / len(api_metrics)) * 100, 2)
            
            # Get step execution data from WorkflowService
            step_history = PerformanceService._get_step_execution_summary()
            
            # Get recent alerts
            with PERFORMANCE_LOCK:
                recent_alerts = list(PERFORMANCE_ALERTS)[-20:]
            
            return {
                "summary": summary,
                "api_metrics": api_metrics,
                "system_metrics": system_metrics,
                "step_history": step_history,
                "alerts": recent_alerts,
                "cache_stats": CacheService.get_cache_stats(),
                "profiling_summary": PerformanceService.get_profiling_summary(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Dashboard stats error: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @staticmethod
    def _get_step_execution_summary() -> Dict[str, Any]:
        """
        Get summary of workflow step executions from profiling data.
        
        Returns:
            Step execution summary with counts and average times
        """
        try:
            with PROFILING_LOCK:
                step_stats = {}
                
                # Filter profiling stats for workflow steps
                for section_name, stats in PROFILING_STATS.items():
                    # Check if this is a step execution
                    if section_name.startswith("step_") or "STEP" in section_name.upper():
                        step_stats[section_name] = {
                            "executions": stats["calls"],
                            "total_time_ms": round(stats["total_time"], 2),
                            "avg_time_ms": round(stats["avg_time"], 2)
                        }
                
                return {
                    "steps": step_stats,
                    "total_step_executions": sum(s["executions"] for s in step_stats.values()),
                    "total_time_ms": round(sum(s["total_time_ms"] for s in step_stats.values()), 2)
                }
                
        except Exception as e:
            logger.error(f"Step execution summary error: {e}")
            return {
                "steps": {},
                "total_step_executions": 0,
                "total_time_ms": 0,
                "error": str(e)
            }
    
    @staticmethod
    def get_historical_data(data_type: str = "all", limit: int = 100) -> Dict[str, Any]:
        """
        Get historical performance data for specific type.
        
        Args:
            data_type: Type of data ("api", "system", or "all")
            limit: Maximum number of records to return
            
        Returns:
            Historical data filtered by type
        """
        try:
            with PERFORMANCE_LOCK:
                history_data = list(PERFORMANCE_HISTORY)
            
            if data_type == "api":
                filtered_data = [m for m in history_data if m.get("endpoint")][-limit:]
            elif data_type == "system":
                filtered_data = [m for m in history_data if m.get("type") == "system"][-limit:]
            else:
                filtered_data = history_data[-limit:]
            
            return {
                "data_type": data_type,
                "count": len(filtered_data),
                "data": filtered_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Historical data retrieval error: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
