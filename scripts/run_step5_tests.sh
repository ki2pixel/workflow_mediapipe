#!/bin/bash
# Script pour exécuter les tests STEP5 (Tracking) dans l'environnement approprié

echo "=== Exécution des tests STEP5 (Tracking) ==="

# Vérifier que l'environnement existe
if [ ! -d "/mnt/venv_ext4/tracking_env_slim" ]; then
    echo "❌ Erreur : l'environnement tracking_env_slim n'existe pas"
    exit 1
fi

# Activer l'environnement Tracking
echo "🔄 Activation de l'environnement tracking_env_slim..."
source /mnt/venv_ext4/tracking_env_slim/bin/activate

# Vérifier les dépendances critiques
echo "🔍 Vérification des dépendances..."
python -c "
try:
    import numpy
    print('✅ numpy disponible')
except ImportError:
    print('❌ numpy manquant')
    exit(1)

try:
    import mediapipe
    print('✅ mediapipe disponible')
except ImportError:
    print('❌ mediapipe manquant')
    exit(1)

try:
    import cv2
    print('✅ opencv disponible')
except ImportError:
    print('❌ opencv manquant')
    exit(1)
    print('ℹ️  Environment tracking_env_slim allégé (MediaPipe CPU) validé')
"

if [ $? -ne 0 ]; then
    echo "❌ Dépendances manquantes, arrêt"
    exit 1
fi

# Exécuter les tests
echo "🧪 Exécution des tests STEP5..."
export DRY_RUN_DOWNLOADS=true
pytest tests/unit/test_step5_*.py tests/unit/test_tracking_optimizations_*.py -v --tb=short

echo "✅ Tests STEP5 terminés"
