#!/bin/bash
# Script pour exécuter les tests STEP3 (TransNet) dans l'environnement approprié

echo "=== Exécution des tests STEP3 (TransNet) ==="

# Vérifier que l'environnement existe
if [ ! -d "/mnt/venv_ext4/transnet_env" ]; then
    echo "❌ Erreur : l'environnement transnet_env n'existe pas"
    exit 1
fi

# Activer l'environnement TransNet
echo "🔄 Activation de l'environnement transnet_env..."
source /mnt/venv_ext4/transnet_env/bin/activate

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
echo "🧪 Exécution des tests STEP3..."
export DRY_RUN_DOWNLOADS=true
pytest tests/unit/test_step3_transnet.py -v --tb=short

echo "✅ Tests STEP3 terminés"
