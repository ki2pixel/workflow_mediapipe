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
from config.security import require_internal_worker_token, validate_file_path, SecurityConfig
from routes.decorators import measure_api

# Configure route logger to capture all debug statements
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure we capture all debug statements

# Used for cache-busting static assets in templates. This value changes on server restart,
# which is enough to force browsers to fetch updated JS/CSS after a deploy/restart.
_STATIC_CACHE_BUSTER = str(int(time.time()))

# Create workflow blueprint
workflow_bp = Blueprint('workflow', __name__)


@workflow_bp.route('/', methods=['GET'])
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
        # Retrieve worker token securely
        worker_token = SecurityConfig().INTERNAL_WORKER_TOKEN or ""
        return render_template(
            'index_new.html',
            steps_config=frontend_safe_steps_config,
            cache_buster=_STATIC_CACHE_BUSTER,
            worker_token=worker_token,
        )
    except Exception as e:
        logger.error(f"Index page error: {e}")
        return render_template('error.html', error="Unable to load application"), 500


@workflow_bp.route('/run/<step_key>', methods=['POST'])
@measure_api('/workflow/run')
@require_internal_worker_token
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
@require_internal_worker_token
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

        # Log what we are returning to the frontend for debugging
        logger.info(f"[ROUTE_DEBUG] /status/{step_key} returning: status='{status_data.get('status')}', progress={status_data.get('progress_current')}/{status_data.get('progress_total')}")

        resp = jsonify(status_data)
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"Get status error for {step_key}: {e}")
        return jsonify({"error": "Unable to retrieve step status"}), 500


@workflow_bp.route('/stop/<step_key>', methods=['POST'])
@measure_api('/workflow/stop')
@require_internal_worker_token
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


@workflow_bp.route('/get_specific_log_test/<step_key>/<int:log_index>', methods=['GET'])
@require_internal_worker_token
def get_specific_log_test(step_key, log_index):
    """
    Test version of get specific log that bypasses cache service.
    """
    if not config.DEBUG:
        return jsonify({"error": "Bypassing cache is only allowed in debug mode"}), 403
    try:
        result = WorkflowService.get_step_log_file(step_key, log_index)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Test log endpoint error for {step_key}/{log_index}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@workflow_bp.route('/get_specific_log/<step_key>/<int:log_index>', methods=['GET'])
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


@workflow_bp.route('/sound-design/<filename>', methods=['GET'])
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
        target_path = sound_dir / filename
        if not validate_file_path(str(target_path), [str(sound_dir)]):
            logger.warning(f"File path validation failed for: {filename}")
            return jsonify({"error": "Access denied"}), 403
        return send_from_directory(sound_dir, filename)
    except Exception as e:
        logger.error(f"Sound file serve error for {filename}: {e}")
        return jsonify({"error": "Sound file not found"}), 404


@workflow_bp.route('/test-sound', methods=['GET'])
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


@workflow_bp.route('/sequence/status', methods=['GET'])
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
        status_data = WorkflowService.get_sequence_status()
        resp = jsonify(status_data)
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    except Exception as e:
        logger.error(f"Sequence status error: {e}")
        return jsonify({"error": "Unable to retrieve sequence status"}), 500


@workflow_bp.route('/sequence/stop', methods=['POST'])
@measure_api('/workflow/sequence/stop')
@require_internal_worker_token
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
@require_internal_worker_token
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


