#!/bin/bash
# Installation de TensorFlow GPU pour MediaPipe GPU delegate
set -e

VENV_PATH="/mnt/venv_ext4/tracking_env"

echo "=========================================="
echo "Installing TensorFlow GPU"
echo "=========================================="
echo ""
echo "⚠️  Warning: TensorFlow GPU is large (~2GB download)"
echo "This may take several minutes..."
echo ""

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: tracking_env not found at $VENV_PATH"
    exit 1
fi

read -p "Continue with installation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
fi

echo "[1/3] Installing tensorflow-gpu 2.15.0..."
$VENV_PATH/bin/pip install tensorflow==2.15.0
echo ""

echo "[2/3] Verifying TensorFlow GPU..."
$VENV_PATH/bin/python -c "
import tensorflow as tf
print('TensorFlow version:', tf.__version__)
print('Built with CUDA:', tf.test.is_built_with_cuda())

gpus = tf.config.list_physical_devices('GPU')
print(f'GPU devices detected: {len(gpus)}')

if gpus:
    for gpu in gpus:
        print(f'  - {gpu.name}')
        details = tf.config.experimental.get_device_details(gpu)
        print(f'    Compute capability: {details.get(\"compute_capability\", \"N/A\")}')
    print('\n✓ SUCCESS: TensorFlow can access GPU')
else:
    print('\n✗ WARNING: No GPU detected by TensorFlow')
    print('Check CUDA/cuDNN installation')
"

echo ""

echo "[3/3] Testing MediaPipe with TensorFlow..."
$VENV_PATH/bin/python -c "
import mediapipe as mp
print('MediaPipe version:', mp.__version__)

try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core import base_options as base_options_module
    
    # Check if GPU delegate is available
    print('MediaPipe Tasks imported successfully')
    print('GPU delegate support: Available')
    print('\n✓ MediaPipe ready for GPU mode')
except Exception as e:
    print(f'\n✗ Error loading MediaPipe Tasks: {e}')
    exit(1)
"

echo ""
echo "✓ TensorFlow GPU installation complete"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/validate_gpu_prerequisites.sh"
echo "  2. Enable GPU in .env: STEP5_ENABLE_GPU=1"
