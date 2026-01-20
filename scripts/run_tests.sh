#!/usr/bin/env bash

set -euo pipefail

export DRY_RUN_DOWNLOADS=true

BOOTSTRAP_PY=""
if command -v python3 >/dev/null 2>&1; then
  BOOTSTRAP_PY="python3"
elif command -v python >/dev/null 2>&1; then
  BOOTSTRAP_PY="python"
fi

PYTHON_VENV_EXE=""
if [ -n "${BOOTSTRAP_PY}" ]; then
  PYTHON_VENV_EXE="$("${BOOTSTRAP_PY}" -c 'from config.settings import config; print(config.PYTHON_VENV_EXE)' 2>/dev/null || true)"
fi

if [ -n "${PYTHON_VENV_EXE}" ] && [ -x "${PYTHON_VENV_EXE}" ]; then
  "${PYTHON_VENV_EXE}" -m pytest -q "$@"
else
  pytest -q "$@"
fi
