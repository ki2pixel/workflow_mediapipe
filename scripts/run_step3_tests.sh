#!/bin/bash
# Exécute les tests STEP3 (VAD & diarisation audio TPU) dans l'environnement de test principal.
# Les dépendances matérielles (tflite_runtime, pycoral, libedgetpu) sont mockées ; numba et
# fastcluster sont optionnels (repli pur Python / scipy) afin que la suite reste portable.

set -u

PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$PROJECT_ROOT" || exit 1

PYTHON_BIN="${STEP3_TEST_PYTHON:-python3}"

echo "=== Exécution des tests STEP3 (analyse audio TPU) ==="
echo "🔍 Interpréteur : $PYTHON_BIN"

if ! "$PYTHON_BIN" -c "import pytest, numpy, scipy, sklearn, dotenv" 2>/dev/null; then
    echo "❌ Dépendances de test manquantes (pytest, numpy, scipy, scikit-learn, python-dotenv)"
    exit 1
fi
echo "✅ Dépendances de test disponibles"

export PYTHONPATH="${PROJECT_ROOT}/workflow_scripts/step3${PYTHONPATH:+:${PYTHONPATH}}"
export DRY_RUN_DOWNLOADS=true

"$PYTHON_BIN" -m pytest \
    tests/unit/test_step3_audio_diarization_tpu.py \
    tests/unit/test_step5_json_reducer.py \
    tests/unit/test_step5_json_reducer_speaker_embeddings.py \
    -v --tb=short
status=$?

if [ "$status" -ne 0 ]; then
    echo "❌ Tests STEP3 en échec (code $status)"
    exit "$status"
fi

echo "✅ Tests STEP3 terminés"
