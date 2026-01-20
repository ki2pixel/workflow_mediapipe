#!/bin/bash
# Script de validation des tests de non-régression

echo "=== Validation Tests Backend ==="

# Exécuter les tests principaux
echo "1. Tests principaux..."
source /mnt/venv_ext4/env/bin/activate
DRY_RUN_DOWNLOADS=true pytest tests/unit/ tests/integration/ --ignore=tests/unit/test_step3_transnet.py --ignore=tests/unit/test_step5_export_verbose_fields.py --ignore=tests/unit/test_step5_yunet_pyfeat_optimizations.py --ignore=tests/unit/test_tracking_optimizations_blendshapes_filter.py -x --tb=short | tee test_results.log

# Vérifier le nombre de tests passants
passed=$(grep "PASSED" test_results.log | wc -l)
failed=$(grep "FAILED" test_results.log | wc -l)
echo "Résultats tests principaux : $passed passants, $failed échouants"

# Exécuter les tests STEP3 si environnement disponible
if [ -d "/mnt/venv_ext4/transnet_env" ]; then
    echo "2. Tests STEP3..."
    source /mnt/venv_ext4/transnet_env/bin/activate
    DRY_RUN_DOWNLOADS=true pytest tests/unit/test_step3_transnet.py -v --tb=short | tee test_results_step3.log
    passed3=$(grep "PASSED" test_results_step3.log | wc -l)
    failed3=$(grep "FAILED" test_results_step3.log | wc -l)
    echo "Résultats STEP3 : $passed3 passants, $failed3 échouants"
else
    echo "2. Tests STEP3 : environnement non disponible"
fi

# Exécuter les tests STEP5 si environnement disponible
if [ -d "/mnt/venv_ext4/tracking_env" ]; then
    echo "3. Tests STEP5..."
    source /mnt/venv_ext4/tracking_env/bin/activate
    DRY_RUN_DOWNLOADS=true pytest tests/unit/test_step5_*.py tests/unit/test_tracking_optimizations_*.py -v --tb=short | tee test_results_step5.log
    passed5=$(grep "PASSED" test_results_step5.log | wc -l)
    failed5=$(grep "FAILED" test_results_step5.log | wc -l)
    echo "Résultats STEP5 : $passed5 passants, $failed5 échouants"
else
    echo "3. Tests STEP5 : environnement non disponible"
fi

# Nettoyage
rm -f test_results*.log

echo "=== Validation terminée ==="
