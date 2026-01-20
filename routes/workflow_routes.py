"""
Workflow Routes Blueprint
Handles workflow execution, step management, and sequence operations.
"""

import logging
import time
from functools import wraps
from flask import Blueprint, jsonify, request, render_template, send_from_directory
from services.workflow_service import WorkflowService
from services.cache_service import CacheService
from services.performance_service import PerformanceService
from config.settings import config

# Configure route logger to capture all debug statements
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure we capture all debug statements

# Used for cache-busting static assets in templates. This value changes on server restart,
# which is enough to force browsers to fetch updated JS/CSS after a deploy/restart.
_STATIC_CACHE_BUSTER = str(int(time.time()))

# Create workflow blueprint
workflow_bp = Blueprint('workflow', __name__)


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


@workflow_bp.route('/')
def index():
    """
    Main application page.
    
    Returns:
        Rendered HTML template with steps configuration
        
    Status Codes:
        200: Success
    """
    try:
        # Use cached configuration for better performance
        frontend_safe_steps_config = CacheService.get_cached_frontend_config()
        return render_template(
            'index_new.html',
            steps_config=frontend_safe_steps_config,
            cache_buster=_STATIC_CACHE_BUSTER,
        )
    except Exception as e:
        logger.error(f"Index page error: {e}")
        return render_template('error.html', error="Unable to load application"), 500


@workflow_bp.route('/run/<step_key>', methods=['POST'])
@measure_api('/workflow/run')
def run_step(step_key):
    """
    Execute a single workflow step.
    
    Args:
        step_key (str): Step identifier (STEP1, STEP2, etc.)
        
    Returns:
        JSON response:
        {
            "status": "initiated|error",
            "message": str
        }
        
    Status Codes:
        202: Step initiated successfully
        404: Step not found
        409: Step already running or sequence in progress
        500: Server error
    """
    try:
        result = WorkflowService.run_step(step_key)
        
        if result["status"] == "initiated":
            return jsonify(result), 202
        elif result["status"] == "error":
            if "inconnue" in result["message"]:
                return jsonify(result), 404
            elif "en cours" in result["message"]:
                return jsonify(result), 409
            else:
                return jsonify(result), 500
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Run step error for {step_key}: {e}")
        return jsonify({
            "status": "error", 
            "message": f"Internal error running step {step_key}"
        }), 500


@workflow_bp.route('/run_custom_sequence', methods=['POST'])
@measure_api('/workflow/run_custom_sequence')
def run_custom_sequence():
    """
    Execute a custom sequence of workflow steps.
    
    Request Body:
        {
            "steps": ["STEP1", "STEP2", ...]
        }
        
    Returns:
        JSON response:
        {
            "status": "initiated|error",
            "message": str
        }
        
    Status Codes:
        202: Sequence initiated successfully
        400: Invalid request data
        409: Sequence already running
        500: Server error
    """
    try:
        data = request.get_json()
        if not data or not isinstance(data.get('steps'), list):
            return jsonify({
                "status": "error", 
                "message": "Invalid steps list"
            }), 400
            
        result = WorkflowService.run_custom_sequence(data['steps'])
        
        if result["status"] == "initiated":
            return jsonify(result), 202
        elif result["status"] == "error":
            if "en cours" in result["message"]:
                return jsonify(result), 409
            else:
                return jsonify(result), 400
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Custom sequence error: {e}")
        return jsonify({
            "status": "error", 
            "message": "Internal error running custom sequence"
        }), 500


@workflow_bp.route('/status/<step_key>', methods=['GET'])
@measure_api('/workflow/status')
def get_status(step_key):
    """
    Get detailed status of a workflow step.
    
    Args:
        step_key (str): Step identifier
        
    Returns:
        JSON response with detailed step status including logs
        
    Status Codes:
        200: Success
        404: Step not found
        500: Server error
    """
    try:
        status_data = WorkflowService.get_step_status(step_key, include_logs=True)

        # DEBUG: Log what we're returning to the frontend during AutoMode
        if status_data.get('is_any_sequence_running', False):
            logger.info(f"[ROUTE_DEBUG] /status/{step_key} returning: status='{status_data.get('status')}', progress={status_data.get('progress_current')}/{status_data.get('progress_total')}")

        return jsonify(status_data)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Get status error for {step_key}: {e}")
        return jsonify({"error": "Unable to retrieve step status"}), 500


@workflow_bp.route('/stop/<step_key>', methods=['POST'])
@measure_api('/workflow/stop')
def stop_step(step_key):
    """
    Stop a running workflow step.
    
    Args:
        step_key (str): Step identifier
        
    Returns:
        JSON response:
        {
            "status": "success|error",
            "message": str
        }
        
    Status Codes:
        200: Success
        404: Step not found
        409: Step not running
        500: Server error
    """
    try:
        result = WorkflowService.stop_step(step_key)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Stop step error for {step_key}: {e}")
        return jsonify({
            "status": "error", 
            "message": f"Internal error stopping step {step_key}"
        }), 500


@workflow_bp.route('/get_specific_log_test/<step_key>/<int:log_index>')
def get_specific_log_test(step_key, log_index):
    """
    Test version of get specific log that bypasses cache service.
    """
    try:
        result = WorkflowService.get_step_log_file(step_key, log_index)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Test log endpoint error for {step_key}/{log_index}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@workflow_bp.route('/get_specific_log/<step_key>/<int:log_index>')
def get_specific_log(step_key, log_index):
    """
    Get specific log file content for a step.
    
    Args:
        step_key (str): Step identifier
        log_index (int): Log file index
        
    Returns:
        JSON response with log content
        
    Status Codes:
        200: Success
        404: Step or log not found
        500: Server error
    """
    try:
        result = WorkflowService.get_step_log_file(step_key, log_index)
        return jsonify(result)
    except ValueError as e:
        logger.error(f"ValueError in get_specific_log for {step_key}/{log_index}: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Get specific log error for {step_key}/{log_index}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Unable to retrieve log content"}), 500


@workflow_bp.route('/sound-design/<filename>')
def serve_sound_file(filename):
    """
    Serve sound files from the sound-design directory.
    
    Args:
        filename (str): Sound file name
        
    Returns:
        Sound file content
        
    Status Codes:
        200: Success
        404: File not found
    """
    try:
        sound_dir = config.BASE_PATH_SCRIPTS / 'sound-design'
        return send_from_directory(sound_dir, filename)
    except Exception as e:
        logger.error(f"Sound file serve error for {filename}: {e}")
        return jsonify({"error": "Sound file not found"}), 404


@workflow_bp.route('/test-sound')
def test_sound():
    """
    Serve the sound test page.
    
    Returns:
        Sound test HTML page
        
    Status Codes:
        200: Success
        404: File not found
    """
    try:
        return send_from_directory(config.BASE_PATH_SCRIPTS, 'test_sound.html')
    except Exception as e:
        logger.error(f"Test sound page error: {e}")
        return jsonify({"error": "Test sound page not found"}), 404


@workflow_bp.route('/sequence/status')
@measure_api('/workflow/sequence/status')
def sequence_status():
    """
    Get current sequence execution status.
    
    Returns:
        JSON response with sequence status:
        {
            "is_running": bool,
            "current_step": str|null,
            "progress": {
                "current": int,
                "total": int
            },
            "last_outcome": dict
        }
        
    Status Codes:
        200: Success
        500: Server error
    """
    try:
        return jsonify(WorkflowService.get_sequence_status())
    except Exception as e:
        logger.error(f"Sequence status error: {e}")
        return jsonify({"error": "Unable to retrieve sequence status"}), 500


@workflow_bp.route('/sequence/stop', methods=['POST'])
@measure_api('/workflow/sequence/stop')
def stop_sequence():
    """
    Stop the currently running sequence.

    Returns:
        JSON response:
        {
            "status": "success|error",
            "message": str
        }

    Status Codes:
        200: Success
        409: No sequence running
        500: Server error
    """
    try:
        result = WorkflowService.stop_sequence()
        if result["status"] == "error" and "aucune" in result["message"]:
            return jsonify(result), 409
        return jsonify(result)
    except Exception as e:
        logger.error(f"Stop sequence error: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal error stopping sequence"
        }), 500


@workflow_bp.route('/cancel/<step_key>', methods=['POST'])
@measure_api('/workflow/cancel')
def cancel_step(step_key):
    """
    Cancel a running workflow step.

    Args:
        step_key (str): Step identifier

    Returns:
        JSON response:
        {
            "status": "success|error",
            "message": str
        }

    Status Codes:
        200: Success
        400: Step not running or doesn't exist
        500: Server error
    """
    try:
        result = WorkflowService.stop_step(step_key)
        if result["status"] == "error":
            if "not running" in result["message"] or "not found" in result["message"]:
                return jsonify(result), 400
            else:
                return jsonify(result), 500
        return jsonify(result)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Cancel step error for {step_key}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Internal error cancelling step {step_key}"
        }), 500


# Additional workflow routes that were moved from app_new.py
# Note: Duplicate routes removed to prevent conflicts
@workflow_bp.route('/sound-design/<filename>')
def serve_sound_file_blueprint(filename):
    """
    Serve sound files from the sound-design directory (moved from app_new.py).

    Args:
        filename (str): Sound file name

    Returns:
        Sound file content

    Status Codes:
        200: Success
        404: File not found
    """
    try:
        sound_dir = config.BASE_PATH_SCRIPTS / 'sound-design'
        return send_from_directory(sound_dir, filename)
    except Exception as e:
        logger.error(f"Sound file serve error for {filename}: {e}")
        return jsonify({"error": "Sound file not found"}), 404


@workflow_bp.route('/test-sound')
def test_sound_blueprint():
    """
    Serve the sound test page (moved from app_new.py).

    Returns:
        Sound test HTML page

    Status Codes:
        200: Success
        404: File not found
    """
    try:
        return send_from_directory(config.BASE_PATH_SCRIPTS, 'test_sound.html')
    except Exception as e:
        logger.error(f"Test sound page error: {e}")
        return jsonify({"error": "Test sound page not found"}), 404
