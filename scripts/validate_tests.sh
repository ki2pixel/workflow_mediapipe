#!/bin/bash
# Script de validation des tests de non-régression

echo "=== Validation Tests Backend ==="

# Exécuter les tests principaux
echo "1. Tests principaux..."
source /mnt/venv_ext4/env/bin/activate
DRY_RUN_DOWNLOADS=true pytest tests/unit/ tests/integration/ --ignore=tests/unit/test_step2_transnet.py --ignore=tests/unit/test_step4_export_verbose_fields.py --ignore=tests/unit/test_tracking_optimizations_blendshapes_filter.py -x --tb=short | tee test_results.log

# Vérifier le nombre de tests passants
passed=$(grep "PASSED" test_results.log | wc -l)
failed=$(grep "FAILED" test_results.log | wc -l)
echo "Résultats tests principaux : $passed passants, $failed échouants"

# Exécuter les tests STEP2 si environnement disponible
if [ -d "/mnt/venv_ext4/transnet_env" ]; then
    echo "2. Tests STEP2..."
    source /mnt/venv_ext4/transnet_env/bin/activate
    DRY_RUN_DOWNLOADS=true pytest tests/unit/test_step2_transnet.py -v --tb=short | tee test_results_step2.log
    passed2=$(grep "PASSED" test_results_step2.log | wc -l)
    failed2=$(grep "FAILED" test_results_step2.log | wc -l)
    echo "Résultats STEP2 : $passed2 passants, $failed2 échouants"
else
    echo "2. Tests STEP2 : environnement non disponible"
fi

# Exécuter les tests STEP4 si environnement disponible
if [ -d "/mnt/venv_ext4/tracking_env_slim" ]; then
    echo "3. Tests STEP4..."
    source /mnt/venv_ext4/tracking_env_slim/bin/activate
    DRY_RUN_DOWNLOADS=true pytest tests/unit/test_step4_*.py tests/unit/test_tracking_optimizations_*.py -v --tb=short | tee test_results_step4.log
    passed4=$(grep "PASSED" test_results_step4.log | wc -l)
    failed4=$(grep "FAILED" test_results_step4.log | wc -l)
    echo "Résultats STEP4 : $passed4 passants, $failed4 échouants"
else
    echo "3. Tests STEP4 : environnement non disponible"
fi

# Nettoyage
rm -f test_results*.log

echo "=== Validation terminée ==="
