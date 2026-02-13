---
description: Maintain and execute the backend/frontend test suites with environment-specific runners. Use when wiring pytest skips, running step-specific scripts, or diagnosing failing tests.
globs: 
  - "**/*.{py,js,md}"
alwaysApply: true
---

# Tests Suite Guardian

## Portée

- Backends : `pytest`, scripts `run_step3_tests.sh`, `run_step5_tests.sh`, `run_main_tests.sh`, `run_step7_tests.sh`, `run_step8_tests.sh`.
- Frontend : `npm run test:frontend` (Node/ESM tests : DOMBatcher, logs overlay, focus trap).
- Guides : `tests/fixtures`, `conftest.py`, `diagnose_tests.sh`, `fix_backend_tests.sh`, `validate_tests.sh`.
- Ressource annexe : `.windsurf/skills/tests-suite-guardian/resources/test_execution_matrix.md` (qui résume commandes, environnements, prérequis, checklist pré-run).
- Nouveautés STEP7/8 : 28 tests WorkflowCommandsConfig + 2 tests finalisation STEP8 intégrés à la suite principale.

## Procédure Générale

### 1. Activer l'environnement `/mnt/venv_ext4/env`.
```bash
source /mnt/venv_ext4/env/bin/activate
export DRY_RUN_DOWNLOADS=true
```

### 2. Nettoyer cache Python
```bash
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 3. Lancer les suites de tests

#### Backend Principal
```bash
# Suite complète backend
bash scripts/run_main_tests.sh

# Vérifier la couverture
bash scripts/coverage_report.sh
```

#### Tests Spécifiques par Étape
```bash
# STEP3 (TransNet)
bash scripts/run_step3_tests.sh

# STEP5 (Tracking)
bash scripts/run_step5_tests.sh

# STEP7 (AE Preprocess)
bash scripts/run_step7_tests.sh

# STEP8 (Finalize)
bash scripts/run_step8_tests.sh
```

#### Frontend
```bash
# Tests UI/UX
npm run test:frontend

# Tests E2E (optionnel)
npm run test:e2e
```

## Scripts de Test Disponibles

### run_main_tests.sh
```bash
#!/bin/bash
cd /home/kidpixel/workflow_mediapipe
source /mnt/venv_ext4/env/bin/activate

# Exécuter les tests backend
python -m pytest tests/unit/ -v --cov=services --cov-report=html
python -m pytest tests/integration/ -v --cov=routes --cov-append --cov-report=html

# Tests de configuration
python -m pytest tests/config/ -v

# Rapport de couverture
python -m pytest --cov=. --cov-report=html --cov-fail-under=80
```

### run_step5_tests.sh
```bash
#!/bin/bash
cd /home/kidpixel/workflow_mediapipe
source /mnt/venv_ext4/tracking_env_slim/bin/activate

# Tests spécifiques STEP5
python -m pytest tests/unit/test_step5/ -v --cov=workflow_scripts.step5
python -m pytest tests/integration/test_tracking/ -v --cov-append

# Tests de performance (optionnel)
python -m pytest tests/performance/test_tracking_performance.py -v
```

### Frontend Tests (package.json)
```json
{
  "scripts": {
    "test:frontend": "node --experimental-modules tests/frontend/test_timeline_logs_phase2.mjs",
    "test:e2e": "playwright tests/e2e/",
    "test:coverage": "nyc --reporter=html npm run test:frontend"
  }
}
```

## Validation et Couverture

### Backend Coverage Targets
```bash
# Services (90% minimum)
python -m pytest tests/unit/services/ --cov=services --cov-fail-under=90

# Routes (85% minimum)
python -m pytest tests/unit/routes/ --cov=routes --cov-fail-under=85

# Global (80% minimum)
python -m pytest --cov=. --cov-fail-under=80
```

### Frontend Coverage Targets
```bash
# DOMBatcher tests
npm run test:frontend -- --coverage

# UI Components tests
npm run test:frontend tests/ui/test_components.test.mjs

# Integration tests
npm run test:e2e
```

## Dépannage des Tests

### Erreurs Communes
| Erreur | Solution |
|---|---|
| `ImportError` | Venv incorrect | `source /mnt/venv_ext4/env/bin/activate` |
| `ModuleNotFoundError` | Package manquant | `pip install -r requirements.txt` |
| `pytest: not found` | pytest non installé | `pip install pytest` |
| `node: not found` | Node.js manquant | Installer Node.js 18+ |

### Configuration pytest (conftest.py)
```python
import pytest
import os
import sys

# Ajouter racine du projet au Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Fixtures communes
@pytest.fixture
def mock_workflow_state():
    """Mock WorkflowState pour les tests"""
    from unittest.mock import Mock
    return Mock()

@pytest.fixture
def temp_directory():
    """Répertoire temporaire pour les tests"""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

# Skip conditionnels
def pytest_configure(config):
    """Configuration des skips conditionnels"""
    
    def pytest_collection_modifyitems(config, items):
        # Skip tests STEP3 si TransNet non disponible
        if not os.path.exists("/mnt/venv_ext4/transnet_env"):
            for item in items:
                if "step3" in item.nodeid:
                    item.add_marker(pytest.mark.skip("TransNet environment not available"))
        
        # Skip tests GPU si InsightFace non disponible
        if not os.path.exists("/mnt/venv_ext4/insightface_env"):
            for item in items:
                if "insightface" in item.nodeid.lower():
                    item.add_marker(pytest.mark.skip("InsightFace environment not available"))
    
    config.hook.pytest_collection_modifyitems = pytest_collection_modifyitems
```

## Scripts de Diagnostic

### diagnose_tests.sh
```bash
#!/bin/bash

echo "=== Diagnostic Tests ==="

# Vérifier environnements
echo "Python environments:"
ls -la /mnt/venv_ext4/*/bin/python

echo "Node.js:"
node --version
npm --version

# Vérifier dépendances
echo "Backend dependencies:"
/mnt/venv_ext4/env/bin/pip list | grep -E "(pytest|flask|sqlalchemy)"

echo "Frontend dependencies:"
npm list --depth=0

# Vérifier fichiers de test
echo "Test files:"
find tests/ -name "*.py" | wc -l
find tests/frontend -name "*.mjs" | wc -l
```

### validate_tests.sh
```bash
#!/bin/bash

# Lancer tous les tests
echo "Running full test suite..."
bash scripts/run_main_tests.sh
bash scripts/run_step3_tests.sh
bash scripts/run_step5_tests.sh
npm run test:frontend

# Générer rapport
echo "Generating test report..."
python -m pytest --cov=. --cov-report=html --cov-report=xml

# Vérifier seuils de couverture
COVERAGE=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
coverage = root.get('line-rate').text
print(float(coverage) * 100)
")

if [ $COVERAGE -lt 80 ]; then
    echo "⚠️ Coverage below 80%: $COVERAGE%"
    exit 1
else
    echo "✅ Coverage acceptable: $COVERAGE%"
fi
```

## Checklist d'Exécution

### Avant de Lancer
- [ ] Environnements activés correctement
- [ ] Cache Python nettoyé
- [ ] Dépendances vérifiées
- [ ] Fichiers de configuration présents

### Pendant l'Exécution
- [ ] Logs surveillés pour les erreurs
- [ ] Couverture générée en temps réel
- [ ] Tests marqués skip/success correctement

### Après l'Exécution
- [ ] Rapports de couverture générés
- [ ] Seuils de qualité vérifiés
- [ ] Échecs documentés avec solutions

Utilisez ce prompt en tapant `/tests-suite-guardian` dans Continue.
