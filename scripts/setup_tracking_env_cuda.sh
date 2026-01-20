#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
==========================================
STEP5 — CUDA/cuDNN helper for tracking_env
==========================================

This script prints the directories that need to be appended to
LD_LIBRARY_PATH so that onnxruntime-gpu (OpenSeeFace) can locate
libcublas/libcufft/libcudnn shipped with the nvidia-* Python wheels
installed in tracking_env. Source the generated export command or add it
to your shell profile before launching STEP5.
EOF

TRACKING_ENV_DIR="/mnt/venv_ext4/tracking_env"
PYTHON_VERSION="python3.10"
SITE_PACKAGES_DIR="$TRACKING_ENV_DIR/lib/$PYTHON_VERSION/site-packages"
NVIDIA_DIR="$SITE_PACKAGES_DIR/nvidia"

if [[ ! -d "$NVIDIA_DIR" ]]; then
  echo "[ERROR] NVIDIA directory not found in $SITE_PACKAGES_DIR" >&2
  exit 1
fi

LIB_DIRS=(
  "$NVIDIA_DIR/cublas/lib"
  "$NVIDIA_DIR/cuda_runtime/lib"
  "$NVIDIA_DIR/cuda_nvrtc/lib"
  "$NVIDIA_DIR/cufft/lib"
  "$NVIDIA_DIR/curand/lib"
  "$NVIDIA_DIR/cusolver/lib"
  "$NVIDIA_DIR/cusparse/lib"
  "$NVIDIA_DIR/cudnn/lib"
  "$NVIDIA_DIR/nvjitlink/lib"
)

EXISTING_DIRS=()
for path in "${LIB_DIRS[@]}"; do
  if [[ -d "$path" ]]; then
    EXISTING_DIRS+=("$path")
  fi
done

if [[ ${#EXISTING_DIRS[@]} -eq 0 ]]; then
  echo "[ERROR] No CUDA library directories found under $NVIDIA_DIR" >&2
  exit 1
fi

CUDA_EXPORT=$(IFS=:; echo "${EXISTING_DIRS[*]}")

cat <<EOF

# Add this to your shell before running STEP5
export LD_LIBRARY_PATH=$CUDA_EXPORT:\${LD_LIBRARY_PATH:-}
EOF
