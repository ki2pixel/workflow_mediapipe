#!/bin/bash

# +-----------------------------------------------------------------+
# |              CONFIGURATION PRINCIPALE DU WORKFLOW               |
# +-----------------------------------------------------------------+

# --- 1. Configuration du test ---
USE_TEST_VENV=true

# --- 2. Chemins de base ---
BASE_PATH_SCRIPTS="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
APP_DIR="$BASE_PATH_SCRIPTS"

# VENV_BASE_DIR: emplacement des environnements virtuels
# Priorité : env exporté > .env > dossier projet
if [ -z "${VENV_BASE_DIR:-}" ] && [ -f "$APP_DIR/.env" ]; then
    VENV_BASE_DIR_LINE="$(grep -E '^VENV_BASE_DIR=' "$APP_DIR/.env" | tail -n 1)"
    if [ -n "$VENV_BASE_DIR_LINE" ]; then
        VENV_BASE_DIR="${VENV_BASE_DIR_LINE#VENV_BASE_DIR=}"
        # Nettoyage des guillemets simples/doubles éventuels
        VENV_BASE_DIR="${VENV_BASE_DIR%\"}"
        VENV_BASE_DIR="${VENV_BASE_DIR#\"}"
        VENV_BASE_DIR="${VENV_BASE_DIR%\'}"
        VENV_BASE_DIR="${VENV_BASE_DIR#\'}"
    fi
fi

if [ -z "${VENV_BASE_DIR:-}" ]; then
    VENV_BASE_DIR="$BASE_PATH_SCRIPTS"
fi

export VENV_BASE_DIR

# --- 3. Variables d'environnement ---
FLASK_PORT=5003
# Navigateur par défaut (modifiable via BROWSER_CMD)
: "${BROWSER_CMD:=firefox}"

# --- 4. Logging unifié ---
export LOGS_BASE_DIR="$BASE_PATH_SCRIPTS/logs"
UNIFIED_LOG_FILE="$LOGS_BASE_DIR/app.log"
STARTUP_LOG_FILE="$LOGS_BASE_DIR/startup.log"
mkdir -p "$LOGS_BASE_DIR"

# --- 5. Variables Flask ---
export FLASK_PORT="$FLASK_PORT"
export FLASK_DEBUG="1"

# +-----------------------------------------------------------------+
# |                    FONCTIONS DE LOGGING                           |
# +-----------------------------------------------------------------+

# Rotation des logs (taille max, backups)
rotate_logs() {
    local log_file="$1"
    local max_size_mb="$2"
    local max_backups="$3"

    if [ -f "$log_file" ]; then
        local file_size_mb=$(du -m "$log_file" | cut -f1)

        if [ "$file_size_mb" -gt "$max_size_mb" ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Rotating log file (size: ${file_size_mb}MB > ${max_size_mb}MB limit)"

            # Rotate existing backups
            for i in $(seq $((max_backups-1)) -1 1); do
                if [ -f "${log_file}.${i}" ]; then
                    mv "${log_file}.${i}" "${log_file}.$((i+1))"
                fi
            done

            # Move current log to .1
            mv "$log_file" "${log_file}.1"

            # Remove old backups beyond max_backups
            for i in $(seq $((max_backups+1)) 10); do
                if [ -f "${log_file}.${i}" ]; then
                    rm -f "${log_file}.${i}"
                fi
            done
        fi
    fi
}

# Logging avec timestamp
log_with_timestamp() {
    local message="$1"
    local log_file="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - STARTUP - $message" | tee -a "$log_file"
}

# Nettoyage à l'arrêt
cleanup_on_exit() {
    log_with_timestamp "=== APPLICATION SHUTDOWN INITIATED ===" "$STARTUP_LOG_FILE"
    log_with_timestamp "Stopping Flask application..." "$STARTUP_LOG_FILE"

    if [ ! -z "$FLASK_PID" ] && kill -0 "$FLASK_PID" 2>/dev/null; then
        kill "$FLASK_PID"
        log_with_timestamp "Flask process (PID: $FLASK_PID) terminated" "$STARTUP_LOG_FILE"
    fi

    log_with_timestamp "=== APPLICATION SHUTDOWN COMPLETE ===" "$STARTUP_LOG_FILE"
    exit 0
}

trap cleanup_on_exit INT TERM

# +-----------------------------------------------------------------+
# |            LOGIQUE D'EXÉCUTION (Ne pas modifier ci-dessous)         |
# +-----------------------------------------------------------------+

# Mode test/production (même venv)
if [ "$USE_TEST_VENV" = "true" ]; then
    echo "*** MODE TEST ACTIF ***"
else
    echo "*** MODE PRODUCTION ACTIF ***"
fi
VENV_NAME="env"

# Définition Python Venv pour app_new.py
PYTHON_VENV_EXE="$VENV_BASE_DIR/$VENV_NAME/bin/python"
APP_SCRIPT_PATH="$APP_DIR/app_new.py"
export PYTHON_VENV_EXE_ENV="$PYTHON_VENV_EXE"

# Rotation logs au démarrage
rotate_logs "$UNIFIED_LOG_FILE" 50 3
rotate_logs "$STARTUP_LOG_FILE" 10 2

# Initialisation logs
log_with_timestamp "=== WORKFLOW APPLICATION STARTUP ===" "$STARTUP_LOG_FILE"
log_with_timestamp "Comprehensive logging system initialized" "$STARTUP_LOG_FILE"
log_with_timestamp "Unified log file: $UNIFIED_LOG_FILE" "$STARTUP_LOG_FILE"

echo
echo "=========================================================="
echo "   LANCEUR DE WORKFLOW (Version Refactorisée)"
echo "=========================================================="
echo
echo "Application: $APP_SCRIPT_PATH"
echo "Environnement: $PYTHON_VENV_EXE"
echo "Port Flask: $FLASK_PORT"
echo "Log unifié: $UNIFIED_LOG_FILE"
echo "Log startup: $STARTUP_LOG_FILE"
echo
echo "STATUT DES FONCTIONNALITÉS:"
echo "  ✓ Workflow principal: ACTIF"
echo "  ✓ Monitoring système: ACTIF"
echo "  ✓ Monitoring CSV webhook: ACTIF"
echo "  ✓ Logging unifié: ACTIF (logs/app.log)"
echo "  ✓ Debug AutoMode: ACTIF ([AUTO_MODE_DEBUG], [SEQUENCE_DEBUG])"
echo "  ✓ Téléchargements Dropbox: ACTIF (Webhook + Proxy R2)"
echo

log_with_timestamp "Application configuration validated" "$STARTUP_LOG_FILE"

if [ ! -f "$PYTHON_VENV_EXE" ]; then
    echo "ERREUR: L'executable Python du VENV est introuvable."
    echo "Chemin vérifié: '$PYTHON_VENV_EXE'"
    log_with_timestamp "ERROR: Python executable not found: $PYTHON_VENV_EXE" "$STARTUP_LOG_FILE"
    read -p "Appuyez sur Entrée pour continuer..."
    exit 1
fi

if [ ! -f "$APP_SCRIPT_PATH" ]; then
    echo "ERREUR: Le script de l'application est introuvable."
    echo "Chemin vérifié: '$APP_SCRIPT_PATH'"
    log_with_timestamp "ERROR: Application script not found: $APP_SCRIPT_PATH" "$STARTUP_LOG_FILE"
    read -p "Appuyez sur Entrée pour continuer..."
    exit 1
fi

log_with_timestamp "All file validations passed" "$STARTUP_LOG_FILE"

echo "Lancement du serveur Flask avec logging unifié..."
echo "Tous les logs sont capturés dans: $UNIFIED_LOG_FILE"

log_with_timestamp "Starting Flask application with unified logging" "$STARTUP_LOG_FILE"
log_with_timestamp "Command: cd $APP_DIR && $PYTHON_VENV_EXE $APP_SCRIPT_PATH" "$STARTUP_LOG_FILE"

# Démarrage Flask avec capture logs (stdout+stderr vers app.log)
cd "$APP_DIR" && "$PYTHON_VENV_EXE" "$APP_SCRIPT_PATH" >> "$UNIFIED_LOG_FILE" 2>&1 &
FLASK_PID=$!

log_with_timestamp "Flask application started with PID: $FLASK_PID" "$STARTUP_LOG_FILE"

echo
echo "Attente de 2 secondes pour le démarrage complet..."
sleep 2

# Vérification démarrage Flask
if ! kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "ERREUR: Le processus Flask semble avoir échoué au démarrage."
    log_with_timestamp "ERROR: Flask process failed to start or crashed immediately" "$STARTUP_LOG_FILE"
    echo "Vérifiez le fichier de log: $UNIFIED_LOG_FILE"
    exit 1
fi

log_with_timestamp "Flask application startup completed successfully" "$STARTUP_LOG_FILE"

# Ouverture navigateur
BROWSER_URL="http://127.0.0.1:$FLASK_PORT/"
if command -v "$BROWSER_CMD" >/dev/null 2>&1; then
    nohup "$BROWSER_CMD" "$BROWSER_URL" >/dev/null 2>&1 &
    log_with_timestamp "Web interface opened with ${BROWSER_CMD} at $BROWSER_URL" "$STARTUP_LOG_FILE"
else
    xdg-open "$BROWSER_URL" >/dev/null 2>&1 || \
        log_with_timestamp "Ouverture du navigateur échouée. Ouvrez manuellement: $BROWSER_URL" "$STARTUP_LOG_FILE"
fi

echo
echo "=========================================================="
echo "Le serveur Flask a été lancé avec succès!"
echo "Interface web: http://127.0.0.1:$FLASK_PORT/"
echo "Log unifié: $UNIFIED_LOG_FILE"
echo "Log startup: $STARTUP_LOG_FILE"
echo ""
echo "FONCTIONNALITÉS DISPONIBLES:"
echo "  • Exécution manuelle des étapes du workflow"
echo "  • Monitoring système (CPU/RAM/GPU)"
echo "  • Suivi des logs en temps réel"
echo "  • Séquences personnalisées"
echo "  • Mode Auto CSV: ACTIF"
echo "  • Monitoring webhook (CSV)"
echo "  • Debug AutoMode complet ([AUTO_MODE_DEBUG], [SEQUENCE_DEBUG])"
echo ""
echo "DEBUGGING AUTOMODE:"
echo "  • Tous les debug statements sont dans: $UNIFIED_LOG_FILE"
echo "  • Surveillez les patterns: [AUTO_MODE_DEBUG], [SEQUENCE_DEBUG]"
echo "  • Utilisez 'tail -f $UNIFIED_LOG_FILE' pour suivre en temps réel"
echo ""
echo "Utilisez Ctrl+C pour arrêter le serveur."
echo "=========================================================="
echo

log_with_timestamp "Application fully started and ready for connections" "$STARTUP_LOG_FILE"
log_with_timestamp "Waiting for user termination signal (Ctrl+C)" "$STARTUP_LOG_FILE"

# En attente de Ctrl+C
wait "$FLASK_PID"
