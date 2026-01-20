"""
API Routes Blueprint
Handles all API endpoints for system monitoring, step status, and remote communication.
"""

import logging
import time
from functools import wraps
from flask import Blueprint, jsonify, request
from config.security import require_internal_worker_token, require_render_register_token
from services.monitoring_service import MonitoringService
from services.workflow_service import WorkflowService
from services.performance_service import PerformanceService
from services.filesystem_service import FilesystemService
from services.visualization_service import VisualizationService
from services.lemonfox_audio_service import LemonfoxAudioService

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__)


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

@api_bp.route('/system_monitor')
@measure_api('/api/system_monitor')
def system_monitor():
    """
    Get current system resource usage (CPU, RAM, GPU).

    Returns:
        JSON response with system status:
        {
            "cpu_percent": float,
            "memory": {
                "percent": float,
                "used_gb": float,
                "total_gb": float
            },
            "gpu": dict|null
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        # Thin controller: delegate to service layer
        status = MonitoringService.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"System monitor error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Unable to retrieve system information"}), 500


@api_bp.route('/system/diagnostics')
@measure_api('/api/system/diagnostics')
def system_diagnostics():
    """
    Get environment diagnostics (Python/FFmpeg versions, GPU availability, filtered config flags).

    Returns:
        JSON response with environment info:
        {
            "python": {"version": str, "implementation": str},
            "ffmpeg": {"version": str},
            "gpu": {"available": bool, "name": str|null},
            "config_flags": { ... },
            "timestamp": str
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        info = MonitoringService.get_environment_info()
        return jsonify(info)
    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        return jsonify({"error": "Unable to retrieve diagnostics"}), 500


@api_bp.route('/step_status/<step_key>')
@measure_api('/api/step_status')
def step_status(step_key):
    """
    Get current status of a workflow step.
    
    Args:
        step_key (str): Step identifier (STEP1, STEP2, etc.)
        
    Returns:
        JSON response with step status:
        {
            "step": str,
            "display_name": str,
            "status": "idle|running|completed|error",
            "progress_current": int,
            "progress_total": int,
            "progress_text": str,
            "return_code": int|null,
            "duration_str": str|null,
            "is_any_sequence_running": bool
        }
        
    Status Codes:
        200: Success
        404: Step not found
        500: Server error
    """
    try:
        return jsonify(WorkflowService.get_step_status(step_key))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Step status error for {step_key}: {e}")
        return jsonify({"error": "Unable to retrieve step status"}), 500


@api_bp.route('/csv_monitor_status')
@measure_api('/api/csv_monitor_status')
def csv_monitor_status():
    """
    Get CSV monitoring service status.

    Returns:
        JSON response with CSV monitor status:
        {
            "csv_monitor": {
                "status": str,
                "last_check": str|null,
                "error": str|null
            },
            "csv_url": str,
            "check_interval": int
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        from services.csv_service import CSVService

        # Use CSVService to get monitor status
        monitor_data = CSVService.get_monitor_status()

        return jsonify(monitor_data)
    except Exception as e:
        logger.error(f"CSV monitor status error: {e}")
        return jsonify({"error": "Unable to retrieve CSV monitor status"}), 500


@api_bp.route('/ping', methods=['GET'])
@measure_api('/api/ping')
@require_internal_worker_token
def api_ping():
    """
    Health check endpoint for remote servers.
    Requires internal worker token authentication.

    Returns:
        JSON response:
        {
            "status": "pong",
            "worker_type": "ubuntu_new"
        }

    Status Codes:
        200: Success
        401: Unauthorized
    """
    return jsonify({"status": "pong", "worker_type": "ubuntu_new"}), 200


@api_bp.route('/get_remote_status_summary', methods=['GET'])
@measure_api('/api/get_remote_status_summary')
@require_internal_worker_token
def api_get_remote_status_summary():
    """
    Get workflow status summary for remote servers.
    Requires internal worker token authentication.

    Returns:
        JSON response with comprehensive workflow status

    Status Codes:
        200: Success
        401: Unauthorized
        500: Server error
    """
    try:
        return jsonify(WorkflowService.get_current_workflow_status_summary())
    except Exception as e:
        logger.error(f"Remote status summary error: {e}")
        return jsonify({"error": "Unable to retrieve status summary"}), 500


@api_bp.route('/performance/metrics')
@measure_api('/api/performance/metrics')
def performance_metrics():
    """
    Get performance metrics and profiling data.
    
    Returns:
        JSON response with performance metrics:
        {
            "profiling_stats": dict,
            "cache_stats": dict,
            "system_performance": dict
        }
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        return jsonify(PerformanceService.get_performance_metrics())
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        return jsonify({"error": "Unable to retrieve performance metrics"}), 500


@api_bp.route('/performance/reset', methods=['POST'])
@measure_api('/api/performance/reset')
def reset_performance_metrics():
    """
    Reset performance profiling statistics.
    
    Returns:
        JSON response:
        {
            "status": "success",
            "message": "Performance metrics reset"
        }
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        PerformanceService.reset_profiling_stats()
        return jsonify({
            "status": "success", 
            "message": "Performance metrics reset"
        })
    except Exception as e:
        logger.error(f"Performance reset error: {e}")
        return jsonify({"error": "Unable to reset performance metrics"}), 500


@api_bp.route('/cache/stats')
@measure_api('/api/cache/stats')
def cache_stats():
    """
    Get cache statistics and hit rates.
    
    Returns:
        JSON response with cache statistics
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        from services.cache_service import CacheService
        return jsonify(CacheService.get_cache_stats())
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return jsonify({"error": "Unable to retrieve cache statistics"}), 500



@api_bp.route('/cache/search', methods=['GET'])
@measure_api('/api/cache/search')
def cache_search():
    """
    Search for folders under /mnt/cache that start with a given number.

    Query Params:
        number (str): Numeric identifier, e.g., "115"

    Returns:
        JSON response:
        {
            "number": str,
            "matches": [str],
            "best_match": str|null
        }

    Status Codes:
        200: Success
        400: Missing parameter
        500: Server error
    """
    try:
        number = request.args.get('number', '').strip()
        if not number:
            return jsonify({"error": "Missing 'number' parameter"}), 400

        result = FilesystemService.find_cache_folder_by_number(number)
        return jsonify({
            "number": result.number,
            "matches": result.matches,
            "best_match": result.best_match
        })
    except Exception as e:
        logger.error(f"Cache search error: {e}")
        return jsonify({"error": "Unable to search cache"}), 500


@api_bp.route('/cache/list_today', methods=['GET'])
@measure_api('/api/cache/list_today')
def cache_list_today():
    """
    List folders under /mnt/cache that were created/modified today.

    Returns:
        JSON response:
        {
            "folders": [
                {"path": str, "name": str, "number": str|null, "mtime": str}
            ]
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        folders = FilesystemService.list_today_cache_folders()
        return jsonify({"folders": folders})
    except Exception as e:
        logger.error(f"Cache list_today error: {e}")
        return jsonify({"error": "Unable to list today's cache folders"}), 500

@api_bp.route('/cache/open', methods=['POST'])
@measure_api('/api/cache/open')
def cache_open():
    """
    Open a folder path in the system's file explorer (server-side).

    Request Body (JSON):
        {
            "path": "/mnt/cache/115 Camille",
            "select_parent": false   # optional, open parent and preselect target when supported
        }

    Returns:
        JSON response:
        {
            "success": bool,
            "message": str
        }

    Status Codes:
        200: Success/Failure message
        400: Invalid body
        500: Server error
    """
    try:
        data = request.get_json(silent=True) or {}
        path = (data.get('path') or '').strip()
        select_parent = bool(data.get('select_parent', False))
        if not path:
            return jsonify({"success": False, "message": "Paramètre 'path' manquant"}), 400

        success, message = FilesystemService.open_path_in_explorer(path, select_parent=select_parent)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Cache open error: {e}")
        return jsonify({"success": False, "message": "Erreur interne pour l'ouverture du dossier"}), 500
@api_bp.route('/cache/clear', methods=['POST'])
@measure_api('/api/cache/clear')
def clear_cache():
    """
    Clear application cache.

    Returns:
        JSON response:
        {
            "status": "success",
            "message": "Cache cleared"
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        from services.cache_service import CacheService
        CacheService.clear_cache()
        return jsonify({
            "status": "success",
            "message": "Cache cleared"
        })
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"error": "Unable to clear cache"}), 500





@api_bp.route('/csv_downloads_status')
def get_csv_downloads_status():
    """
    Get CSV downloads status.

    Returns:
        JSON response with CSV downloads status

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        from services.csv_service import CSVService
        from datetime import datetime

        # Use CSVService to get download status
        downloads_status = CSVService.get_csv_downloads_status()

        # Combine active and recent downloads
        active_downloads = downloads_status.get("active_downloads", {})
        recent_statuses = downloads_status.get("recent_statuses", [])

        # Convert active downloads dict to list
        active_list = list(active_downloads.values()) if active_downloads else []

        # Combine and sort all downloads
        all_downloads = active_list + recent_statuses
        all_downloads.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)

        # Clean timestamps for JSON serialization
        json_safe_downloads = []
        for download in all_downloads:
            download_copy = download.copy()
            # Remove datetime objects that can't be JSON serialized
            download_copy.pop('timestamp', None)
            json_safe_downloads.append(download_copy)

        return jsonify(json_safe_downloads)
    except Exception as e:
        logger.error(f"CSV downloads status error: {e}")
        return jsonify({"error": "Unable to retrieve CSV downloads status"}), 500






@api_bp.route('/stats/dashboard')
@measure_api('/api/stats/dashboard')
def stats_dashboard():
    """
    Get comprehensive statistics for the performance dashboard.

    Returns:
        JSON response with dashboard statistics:
        {
            "summary": {
                "total_api_calls": int,
                "total_errors": int,
                "avg_response_time_ms": float,
                "error_rate_percent": float
            },
            "api_metrics": list,
            "system_metrics": list,
            "step_history": dict,
            "alerts": list,
            "cache_stats": dict,
            "profiling_summary": dict
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        stats = PerformanceService.get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({"error": "Unable to retrieve dashboard statistics"}), 500


@api_bp.route('/stats/history')
@measure_api('/api/stats/history')
def stats_history():
    """
    Get historical performance data.

    Query Parameters:
        type (str): Data type - "api", "system", or "all" (default: "all")
        limit (int): Maximum number of records (default: 100, max: 500)

    Returns:
        JSON response with historical data:
        {
            "data_type": str,
            "count": int,
            "data": list
        }

    Status Codes:
        200: Success
        400: Invalid parameters
        500: Server error
    """
    try:
        data_type = request.args.get('type', 'all')
        limit = request.args.get('limit', 100, type=int)
        
        # Validate parameters
        if data_type not in ['api', 'system', 'all']:
            return jsonify({"error": "Invalid data type. Must be 'api', 'system', or 'all'"}), 400
        
        if limit < 1 or limit > 500:
            return jsonify({"error": "Limit must be between 1 and 500"}), 400
        
        history = PerformanceService.get_historical_data(data_type, limit)
        return jsonify(history)
        
    except Exception as e:
        logger.error(f"Historical data error: {e}")
        return jsonify({"error": "Unable to retrieve historical data"}), 500



@api_bp.route('/visualization/projects', methods=['GET'])
@measure_api('/api/visualization/projects')
def visualization_projects():
    """
    List available projects and their videos for visualization/reporting.

    Returns:
        JSON response:
        {
            "projects": [
                {"name": str, "path": str, "videos": [str], "video_count": int,
                 "has_scenes": bool, "has_audio": bool, "has_tracking": bool, "source": "projects|archives"}
            ],
            "count": int,
            "timestamp": str
        }

    Status Codes:
        200: Success
        500: Server error
    """
    try:
        data = VisualizationService.get_available_projects()
        # If service reports an error, surface as 500 while returning payload
        if data.get("error"):
            return jsonify(data), 500
        return jsonify(data)
    except Exception as e:
        logger.error(f"Visualization projects error: {e}", exc_info=True)
        return jsonify({"error": "Unable to list visualization projects"}), 500


@api_bp.route('/step4/lemonfox_audio', methods=['POST'])
@measure_api('/api/step4/lemonfox_audio')
def lemonfox_audio_analysis():
    """
    Process video audio analysis using Lemonfox Speech-to-Text API.
    
    Generates a STEP4-compatible {video_stem}_audio.json file with frame-by-frame
    audio analysis including speaker diarization.
    
    Request JSON:
        {
            "project_name": str (required),
            "video_name": str (required, relative path within project),
            "language": str (optional),
            "prompt": str (optional),
            "speaker_labels": bool (optional, default: true),
            "min_speakers": int (optional),
            "max_speakers": int (optional),
            "timestamp_granularities": array[str] (optional, e.g., ["word"]),
            "eu_processing": bool (optional, uses LEMONFOX_EU_DEFAULT if not set)
        }
    
    Returns:
        JSON response on success:
        {
            "status": "success",
            "output_path": str,
            "fps": float,
            "total_frames": int
        }
        
        JSON response on error:
        {
            "status": "error",
            "error": str
        }
    
    Status Codes:
        200: Success
        400: Invalid input parameters
        404: Project or video not found
        502: Lemonfox API upstream error
        500: Server error
    """
    try:
        # Parse and validate request
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body must be JSON"
            }), 400
        
        # Required fields
        project_name = data.get('project_name', '').strip()
        video_name = data.get('video_name', '').strip()
        
        if not project_name:
            return jsonify({
                "status": "error",
                "error": "project_name is required"
            }), 400
        
        if not video_name:
            return jsonify({
                "status": "error",
                "error": "video_name is required"
            }), 400
        
        # Optional fields
        language = data.get('language')
        prompt = data.get('prompt')
        speaker_labels = data.get('speaker_labels')
        min_speakers = data.get('min_speakers')
        max_speakers = data.get('max_speakers')
        timestamp_granularities = data.get('timestamp_granularities')
        eu_processing = data.get('eu_processing')
        
        # Validate types
        if min_speakers is not None and not isinstance(min_speakers, int):
            return jsonify({
                "status": "error",
                "error": "min_speakers must be an integer"
            }), 400
        
        if max_speakers is not None and not isinstance(max_speakers, int):
            return jsonify({
                "status": "error",
                "error": "max_speakers must be an integer"
            }), 400
        
        if timestamp_granularities is not None and not isinstance(timestamp_granularities, list):
            return jsonify({
                "status": "error",
                "error": "timestamp_granularities must be an array"
            }), 400

        if speaker_labels is not None and not isinstance(speaker_labels, bool):
            return jsonify({
                "status": "error",
                "error": "speaker_labels must be a boolean"
            }), 400
        
        # Call service
        result = LemonfoxAudioService.process_video_with_lemonfox(
            project_name=project_name,
            video_name=video_name,
            language=language,
            prompt=prompt,
            speaker_labels=speaker_labels,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            timestamp_granularities=timestamp_granularities,
            eu_processing=eu_processing
        )
        
        if not result.success:
            error_msg = result.error or "Unknown error"
            
            # Determine appropriate status code
            if "not found" in error_msg.lower():
                status_code = 404
            elif "lemonfox api" in error_msg.lower():
                status_code = 502
            elif "not configured" in error_msg.lower():
                status_code = 500
            else:
                status_code = 400
            
            return jsonify({
                "status": "error",
                "error": error_msg
            }), status_code
        
        # Success response
        return jsonify({
            "status": "success",
            "output_path": str(result.output_path),
            "fps": result.fps,
            "total_frames": result.total_frames
        }), 200
        
    except Exception as e:
        logger.error(f"Lemonfox audio analysis error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Internal server error"
        }), 500
