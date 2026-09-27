#!/bin/bash
# Script pour exécuter les tests STEP2 (TransNet) dans l'environnement approprié

echo "=== Exécution des tests STEP2 (TransNet) ==="

# Vérifier que l'environnement existe
if [ ! -d "/mnt/venv_ext4/transnet_env" ]; then
    echo "❌ Erreur : l'environnement transnet_env n'existe pas"
    exit 1
fi

# Activer l'environnement TransNet
echo "🔄 Activation de l'environnement transnet_env..."
source /mnt/venv_ext4/transnet_env/bin/activate

# Le module transnetv2_pytorch vit dans workflow_scripts/step2 (import local, pas un paquet pip)
PROJECT_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
export PYTHONPATH="${PROJECT_ROOT}/workflow_scripts/step2${PYTHONPATH:+:${PYTHONPATH}}"

# Vérifier les dépendances critiques
echo "🔍 Vérification des dépendances..."
python -c "
try:
    import torch
    print('✅ torch disponible')
except ImportError:
    print('❌ torch manquant')
    exit(1)

try:
    import transnetv2_pytorch
    print('✅ transnetv2_pytorch disponible')
except ImportError:
    print('❌ transnetv2_pytorch manquant')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Dépendances manquantes, arrêt"
    exit 1
fi

# Exécuter les tests
echo "🧪 Exécution des tests STEP2..."
export DRY_RUN_DOWNLOADS=true
python -m pytest tests/unit/test_step2_transnet.py -v --tb=short
status=$?

if [ $status -ne 0 ]; then
    echo "❌ Tests STEP2 en échec (code $status)"
    exit $status
fi

echo "✅ Tests STEP2 terminés"
