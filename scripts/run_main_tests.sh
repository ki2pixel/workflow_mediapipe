#!/bin/bash
# Script pour exécuter tous les tests backend (hors environnements spécialisés)

echo "=== Exécution des tests backend principaux ==="

# Activer l'environnement principal
echo "🔄 Activation de l'environnement principal..."
source /mnt/venv_ext4/env/bin/activate

# Exécuter les tests principaux (excluant STEP3/STEP5 spécialisés)
echo "🧪 Exécution des tests principaux..."
export DRY_RUN_DOWNLOADS=true

# Liste des tests à exclure (nécessitant des environnements spécialisés)
EXCLUDE_TESTS=(
    "tests/unit/test_step3_transnet.py"
    "tests/unit/test_step5_export_verbose_fields.py"
    "tests/unit/test_step5_face_engines.py"
    "tests/unit/test_step5_gpu_logs.py"
    "tests/unit/test_step5_gpu_support.py"
    "tests/unit/test_step5_insightface_engine.py"
    "tests/unit/test_step5_insightface_gpu_only.py"
    "tests/unit/test_step5_yunet_pyfeat_optimizations.py"
    "tests/unit/test_tracking_optimizations_blendshapes_filter.py"
    "tests/integration/test_step5_json_formats.py"
    "tests/integration/test_step5_cv5_json_formats.py"
)

# Construire la commande pytest avec les exclusions
PYTEST_CMD="pytest tests/unit/ tests/integration/"
for test in "${EXCLUDE_TESTS[@]}"; do
    PYTEST_CMD="$PYTEST_CMD --ignore=$test"
done

# Exécuter les tests
echo "Commande: $PYTEST_CMD"
$PYTEST_CMD -v --tb=short

echo "✅ Tests principaux terminés"
