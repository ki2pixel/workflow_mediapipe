#!/bin/bash
# Script de correction automatisée pour les tests backend

echo "=== Correction Automatisée Tests Backend ==="

# Correction des _get_app_state
echo "1. Correction des _get_app_state..."
find tests/ -name "*.py" -exec sed -i 's/WorkflowService._get_app_state/get_workflow_state/g' {} \;

# Correction des imports app_new
echo "2. Correction des imports app_new..."
find tests/ -name "*.py" -exec sed -i 's/from app_new import app/from app_new import create_app\napp = create_app()/g' {} \;

# Vérification rapide des corrections
echo "3. Vérification des corrections..."
pytest tests/unit/test_workflow_service.py::TestWorkflowServiceInitialization::test_initialize_without_workflow_state -v

echo "=== Correction terminée ==="
