#!/bin/bash
# Installation de onnxruntime-gpu pour OpenSeeFace GPU
set -e

VENV_PATH="/mnt/venv_ext4/tracking_env"

echo "=========================================="
echo "Installing ONNXRuntime GPU"
echo "=========================================="
echo ""

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: tracking_env not found at $VENV_PATH"
    exit 1
fi

echo "[1/3] Uninstalling existing onnxruntime..."
$VENV_PATH/bin/pip uninstall -y onnxruntime onnxruntime-gpu || true
echo ""

echo "[2/3] Installing onnxruntime-gpu 1.23.2..."
$VENV_PATH/bin/pip install onnxruntime-gpu==1.23.2
echo ""

echo "[3/3] Verifying CUDA provider..."
$VENV_PATH/bin/python -c "
import onnxruntime as ort
providers = ort.get_available_providers()
print('Available providers:', providers)

if 'CUDAExecutionProvider' in providers:
    print('\n✓ SUCCESS: CUDA provider is available')
    print('OpenSeeFace can now use GPU')
else:
    print('\n✗ WARNING: CUDA provider not found')
    print('Check CUDA installation and compatibility')
    exit(1)
"

echo ""
echo "✓ ONNXRuntime GPU installation complete"
