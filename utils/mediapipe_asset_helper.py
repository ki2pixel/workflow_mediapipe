import os
import shutil
import time
import uuid
import mediapipe as mp
import sys

def _get_mediapipe_assets_dir():
    """
    Finds the 'assets' directory within the installed MediaPipe package.
    This is the most reliable way to locate it.
    """
    try:
        # The __file__ attribute of the mediapipe package gives us the path to its __init__.py
        mp_package_path = os.path.dirname(mp.__file__)
        assets_path = os.path.join(mp_package_path, 'tasks', 'python', 'vision', 'pybind', 'assets')
        
        # A fallback path seen in some installations
        if not os.path.exists(assets_path):
            assets_path = os.path.join(mp_package_path, 'tasks', 'python', 'assets')
            
        if os.path.exists(assets_path):
            return assets_path
        else:
            # If all else fails, create a local assets dir as a last resort
            local_assets = os.path.join(os.getcwd(), 'mediapipe_assets')
            os.makedirs(local_assets, exist_ok=True)
            print(f"WARNING: MediaPipe assets directory not found. Using local fallback: {local_assets}", file=sys.stderr)
            return local_assets
            
    except Exception as e:
        print(f"ERROR: Could not determine MediaPipe assets path: {e}", file=sys.stderr)
        return None

def create_mediapipe_asset_copy(original_model_path):
    """
    Copies a model file to the MediaPipe assets directory to ensure it can be loaded.
    MediaPipe tasks often require models to be in this specific 'assets' folder.
    
    Args:
        original_model_path (str): The absolute path to the model file.

    Returns:
        dict: A dictionary with path information, or None on failure.
              {'asset_path': '...', 'asset_name': '...'}
    """
    assets_dir = _get_mediapipe_assets_dir()
    if not assets_dir:
        print("ERROR: Cannot create model copy because MediaPipe assets directory was not found.", file=sys.stderr)
        return None

    if not os.path.exists(original_model_path):
        print(f"ERROR: Original model file does not exist: {original_model_path}", file=sys.stderr)
        return None
        
    try:
        original_filename = os.path.basename(original_model_path)
        # Create a unique name to avoid conflicts if multiple processes run
        unique_suffix = uuid.uuid4().hex[:8]
        temp_filename = f"temp_{unique_suffix}_{original_filename}"
        
        destination_path = os.path.join(assets_dir, temp_filename)
        
        # Copy the file
        shutil.copy2(original_model_path, destination_path)
        
        print(f"INFO: Model '{original_filename}' copied to MediaPipe assets as '{temp_filename}' for processing.", file=sys.stderr)
        
        return {
            "asset_path": os.path.abspath(destination_path),
            "asset_name": temp_filename
        }
    except Exception as e:
        print(f"ERROR: Failed to copy model to MediaPipe assets directory: {e}", file=sys.stderr)
        return None

def cleanup_mediapipe_temp_assets(max_age_hours=1):
    """
    Deletes temporary model files from the MediaPipe assets directory that are older
    than a specified age. This prevents the folder from filling up with old temp files.

    Args:
        max_age_hours (int): The maximum age of a file in hours to be kept.
    
    Returns:
        tuple: (number_of_files_deleted, total_space_freed_in_bytes)
    """
    assets_dir = _get_mediapipe_assets_dir()
    if not assets_dir:
        print("WARNING: Cannot clean up assets, directory not found.", file=sys.stderr)
        return 0, 0
        
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    deleted_count = 0
    freed_space = 0
    
    try:
        for filename in os.listdir(assets_dir):
            if filename.startswith("temp_"):
                file_path = os.path.join(assets_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_count += 1
                            freed_space += file_size
                            print(f"CLEANUP: Removed old temp asset: {filename}", file=sys.stderr)
                except Exception as e_inner:
                    # This can happen if another process deletes the file in the meantime
                    print(f"WARNING: Could not process asset '{filename}' during cleanup: {e_inner}", file=sys.stderr)

    except Exception as e:
        print(f"ERROR: An error occurred during asset cleanup: {e}", file=sys.stderr)
        
    return deleted_count, freed_space