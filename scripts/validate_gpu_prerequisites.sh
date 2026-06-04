#!/bin/bash
# Script de validation des prérequis GPU pour STEP5
# Usage: ./scripts/validate_gpu_prerequisites.sh

set -e

echo "=========================================="
echo "STEP5 GPU Prerequisites Validation"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VENV_PATH="/mnt/venv_ext4/tracking_env_slim"
INSIGHTFACE_PYTHON="${STEP5_INSIGHTFACE_ENV_PYTHON:-}"
if [ -z "$INSIGHTFACE_PYTHON" ]; then
    if [ -x "/mnt/venv_ext4/insightface_env/bin/python" ]; then
        INSIGHTFACE_PYTHON="/mnt/venv_ext4/insightface_env/bin/python"
    else
        INSIGHTFACE_PYTHON="$VENV_PATH/bin/python"
    fi
fi
ERRORS=0
WARNINGS=0

# 1. Check NVIDIA GPU
echo "[1/6] Checking NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader)
    
    echo -e "${GREEN}✓${NC} GPU detected: $GPU_NAME"
    echo "  VRAM: ${VRAM_TOTAL} MiB"
    echo "  Driver: $DRIVER_VERSION"
    
    if [ "$VRAM_TOTAL" -lt 3000 ]; then
        echo -e "${YELLOW}⚠${NC} Warning: VRAM < 3GB, GPU mode may cause OOM"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC} nvidia-smi not found. Install NVIDIA drivers."
    ((ERRORS++))
fi
echo ""

# 2. Check CUDA availability
echo "[2/6] Checking CUDA..."
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | sed -n 's/.*release \([0-9.]*\).*/\1/p')
    echo -e "${GREEN}✓${NC} CUDA Toolkit: $CUDA_VERSION"
else
    echo -e "${YELLOW}⚠${NC} nvcc not found (CUDA Toolkit not in PATH)"
    echo "  This is OK if PyTorch bundles CUDA runtime"
    ((WARNINGS++))
fi
echo ""

# 3. Check tracking_env_slim exists
echo "[3/6] Checking tracking_env_slim..."
if [ -d "$VENV_PATH" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found: $VENV_PATH"
else
    echo -e "${RED}✗${NC} tracking_env_slim not found at: $VENV_PATH"
    echo "  Check VENV_BASE_DIR in .env"
    ((ERRORS++))
    exit 1
fi
echo ""

# 4. Check PyTorch CUDA
echo "[4/6] Checking PyTorch CUDA support..."
TORCH_ENV="/mnt/venv_ext4/transnet_env"
if [ ! -d "$TORCH_ENV" ] && [ -d "/mnt/venv_ext4/audio_env" ]; then
    TORCH_ENV="/mnt/venv_ext4/audio_env"
fi

if [ -d "$TORCH_ENV" ]; then
    PYTORCH_CHECK=$($TORCH_ENV/bin/python -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA version:', torch.version.cuda)
    print('Device:', torch.cuda.get_device_name(0))
" 2>&1)

    if echo "$PYTORCH_CHECK" | grep -q "CUDA available: True"; then
        echo -e "${GREEN}✓${NC} PyTorch CUDA enabled (checked in $(basename $TORCH_ENV))"
        echo "$PYTORCH_CHECK" | sed 's/^/  /'
    else
        echo -e "${RED}✗${NC} PyTorch CUDA not available (checked in $(basename $TORCH_ENV))"
        echo "$PYTORCH_CHECK" | sed 's/^/  /'
        ((ERRORS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} PyTorch environment (transnet_env) not found, skipping PyTorch CUDA check"
    ((WARNINGS++))
fi
echo ""

# 5. Check ONNXRuntime providers
echo "[5/6] Checking ONNXRuntime providers..."
ONNX_CHECK=$($INSIGHTFACE_PYTHON -c "
import onnxruntime as ort
print('ONNXRuntime:', ort.__version__)
providers = ort.get_available_providers()
print('Providers:', ', '.join(providers))
print('CUDA provider:', 'CUDAExecutionProvider' in providers)
" 2>&1)

echo "$ONNX_CHECK" | sed 's/^/  /'

if echo "$ONNX_CHECK" | grep -q "CUDA provider: True"; then
    echo -e "${GREEN}✓${NC} ONNX CUDA provider available"
else
    echo -e "${YELLOW}⚠${NC} ONNX CUDA provider NOT available (InsightFace GPU will not work)"
    echo "  Install onnxruntime-gpu in insightface_env"
    ((WARNINGS++))
fi
echo ""

# 6. Check MediaPipe
echo "[6/6] Checking MediaPipe..."
MP_CHECK=$($VENV_PATH/bin/python -c "
import mediapipe as mp
print('MediaPipe:', mp.__version__)
try:
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print('MediaPipe Tasks: OK')
except Exception as e:
    print('MediaPipe Tasks: ERROR -', str(e))
" 2>&1)

echo "$MP_CHECK" | sed 's/^/  /'

if echo "$MP_CHECK" | grep -q "MediaPipe Tasks: OK"; then
    echo -e "${GREEN}✓${NC} MediaPipe Tasks loaded successfully"
else
    echo -e "${RED}✗${NC} MediaPipe Tasks failed to load"
    ((ERRORS++))
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. If ONNX CUDA missing: install onnxruntime-gpu in insightface_env"
    echo "  2. Enable GPU: Set STEP5_ENABLE_GPU=1 in .env"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) - GPU partially available${NC}"
    echo ""
    echo "GPU will work with limitations (see warnings above)"
else
    echo -e "${RED}✗ $ERRORS error(s), $WARNINGS warning(s)${NC}"
    echo ""
    echo "Fix errors before enabling GPU mode"
    exit 1
fi

echo ""
echo "Current GPU usage:"
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
