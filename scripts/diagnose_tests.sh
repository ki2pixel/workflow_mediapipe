#!/bin/bash
# Script de diagnostic complet pour les tests backend

echo "=== Diagnostic Tests Backend ==="

# Vérifier les imports manquants
echo "1. Vérification des imports..."
python -c "
import sys
sys.path.append('.')
try:
    from services.workflow_service import WorkflowService
    print('✅ WorkflowService import OK')
except ImportError as e:
    print(f'❌ WorkflowService import error: {e}')

try:
    from services.csv_service import CSVService  
    print('✅ CSVService import OK')
except ImportError as e:
    print(f'❌ CSVService import error: {e}')
"

# Vérifier les environnements
echo "2. Vérification des environnements virtuels..."
for env in env transnet_env audio_env tracking_env; do
    if [ -d "/mnt/venv_ext4/$env" ]; then
        echo "✅ $env existe"
    else
        echo "❌ $env manquant"
    fi
done

# Vérifier les dépendances critiques
echo "3. Vérification des dépendances..."
source /mnt/venv_ext4/env/bin/activate
python -c "
try:
    import numpy
    print('✅ numpy disponible dans env')
except ImportError:
    print('❌ numpy manquant dans env')

try:
    import torch  
    print('✅ torch disponible dans env')
except ImportError:
    print('❌ torch manquant dans env')
"

source /mnt/venv_ext4/transnet_env/bin/activate
python -c "
try:
    import torch
    print('✅ torch disponible dans transnet_env')
except ImportError:
    print('❌ torch manquant dans transnet_env')
"

source /mnt/venv_ext4/tracking_env/bin/activate
python -c "
try:
    import numpy
    print('✅ numpy disponible dans tracking_env')
except ImportError:
    print('❌ numpy manquant dans tracking_env')

try:
    import cv2
    print('✅ opencv disponible dans tracking_env')
except ImportError:
    print('❌ opencv manquant dans tracking_env')
"

# Vérifier les scripts de test
echo "4. Vérification des scripts de test..."
for script in run_main_tests.sh run_step3_tests.sh run_step5_tests.sh; do
    if [ -f "scripts/$script" ]; then
        if [ -x "scripts/$script" ]; then
            echo "✅ $script existe et exécutable"
        else
            echo "⚠️ $script existe mais non exécutable"
        fi
    else
        echo "❌ $script manquant"
    fi
done

# Vérifier la configuration pytest
echo "5. Vérification de pytest.ini..."
if [ -f "pytest.ini" ]; then
    echo "✅ pytest.ini existe"
    if grep -q "test_step3_transnet.py" pytest.ini; then
        echo "✅ Exclusions STEP3 configurées"
    else
        echo "⚠️ Exclusions STEP3 non trouvées"
    fi
    if grep -q "test_step5_" pytest.ini; then
        echo "✅ Exclusions STEP5 configurées"
    else
        echo "⚠️ Exclusions STEP5 non trouvées"
    fi
else
    echo "❌ pytest.ini manquant"
fi

echo "=== Diagnostic terminé ==="
