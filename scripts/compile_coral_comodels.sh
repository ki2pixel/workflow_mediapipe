#!/bin/bash
# Co-compile BlazeFace + FaceMesh for shared SRAM cache on Coral Edge TPU
set -euo pipefail

ASSETS_DIR="$(cd "$(dirname "$0")/../assets" && pwd)"
OUTPUT_DIR="${ASSETS_DIR}/cocompiled"
mkdir -p "${OUTPUT_DIR}"

BLAZEFACE="${ASSETS_DIR}/blazeface_front_quantized.tflite"
FACEMESH="${ASSETS_DIR}/facemesh_quantized.tflite"

echo "Co-compiling BlazeFace + FaceMesh for shared SRAM (8MB)..."
edgetpu_compiler "${BLAZEFACE}" "${FACEMESH}" -o "${OUTPUT_DIR}"
echo "Done. Check ${OUTPUT_DIR} for co-compiled models."
