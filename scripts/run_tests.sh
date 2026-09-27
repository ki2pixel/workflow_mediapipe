#!/usr/bin/env bash

set -euo pipefail

export DRY_RUN_DOWNLOADS=true

# Résoudre VENV_BASE_DIR depuis .env : le python système n'a pas forcément python-dotenv,
# auquel cas config.PYTHON_VENV_EXE retomberait sur un chemin de venv inexistant.
if [ -z "${VENV_BASE_DIR:-}" ] && [ -f ".env" ]; then
  VENV_BASE_DIR="$(grep -E '^VENV_BASE_DIR=' .env | tail -n 1 | cut -d= -f2-)"
  VENV_BASE_DIR="${VENV_BASE_DIR%\"}"
  VENV_BASE_DIR="${VENV_BASE_DIR#\"}"
  VENV_BASE_DIR="${VENV_BASE_DIR%\'}"
  VENV_BASE_DIR="${VENV_BASE_DIR#\'}"
  export VENV_BASE_DIR
fi

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
  # Pas de -q ici : pytest.ini fournit déjà addopts = -q (un second -q masquerait le bilan).
  "${PYTHON_VENV_EXE}" -m pytest "$@"
else
  echo "⚠️  Interpréteur de l'application introuvable (${PYTHON_VENV_EXE:-non résolu}) : repli sur le pytest du PATH." >&2
  pytest "$@"
fi
