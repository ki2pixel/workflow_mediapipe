---
description: after-effects-scripts skill migrated from Windsurf as contextual rules
globs: 
  - "**/*.{jsx,ts}"
alwaysApply: false
---

# After Effects Scripts Expert (Post-Production MediaPipe v4.3)

Cette skill couvre l'exploitation des scripts After Effects (ExtendScript) et des ponts Python pour la post-production créative après le pipeline MediaPipe 8 étapes.

## Contexte & Positionnement

### Rôle dans le Pipeline
Les scripts After Effects interviennent **offline sur Windows** (car AE n'existe pas sur Linux) comme phase de post-production créative **après STEP7** :

```
STEP7 (Pré-traitement AE) → Fichiers *_ae.json optimisés
↓
Scripts AE (Windows) → Post-production créative
```

### Scripts Principaux

| Script | Objectif | Fichiers consommés | Sorties |
|---|---|---|---|
| **Media-Solution-v11.2-production.jsx** | Création automatisée de projets AE | `*_ae.json`, CSV scènes, vidéos | Projets AEP avec découpes |
| **Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx** | Recentrage intelligent basé sur tracking | `*_tracking.json` (prioritaire) ou `*.json` (STEP5) | Calques recentrés, analytics |

## Scripts After Effects

### Media-Solution-v11.2-production.jsx
**Objectif** : Création automatisée de projets After Effects à partir des données JSON optimisées.

**Fichiers consommés** :
- `*_ae.json` (prioritaire) - Données optimisées STEP7
- `scenes.csv` - Métadonnées de scènes
- Fichiers vidéos sources - Pour composition

**Fonctionnalités** :
- Création de composition AE avec calques
- Import automatique des données tracking
- Génération de CSV scènes
- Export vidéo final

### Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx
**Objectif** : Recentrage intelligent basé sur les données de tracking.

**Fichiers consommés** :
- `*_tracking.json` (prioritaire) - Données brutes STEP5
- Fichiers JSON alternatifs (STEP5, STEP6)
- Labels vidéo (si disponibles)

**Fonctionnalités** :
- Détection automatique des écarts
- Calques d'analyse recentrés
- Export analytics CSV

## Ponts Python pour After Effects

### system.callSystem()
```javascript
// Dans ExtendScript
var pythonScript = '''
import sys
sys.path.append('/path/to/python/scripts')
import tracking_data_processor

# Traitement des données
result = tracking_data_processor.process_tracking_data(arguments[0], arguments[1])
print(result)
''';

var result = system.callSystem('python', pythonScript);
```

### Fichier de pont Python
```python
# tracking_data_processor.py
import json
import sys
from pathlib import Path

def process_tracking_data(tracking_file, output_dir):
    """Traite les données de tracking pour AE"""
    
    with open(tracking_file, 'r') as f:
        data = json.load(f)
    
    # Traitement spécifique AE
    processed_data = {
        'keyframes': extract_keyframes(data),
        'layers': create_ae_layers(data),
        'markers': create_markers(data)
    }
    
    # Export pour AE
    output_file = Path(output_dir) / f"{Path(tracking_file).stem}_ae_ready.json"
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)
    
    return str(output_file)

if __name__ == "__main__":
    result = process_tracking_data(sys.argv[1], sys.argv[2])
    print(result)
```

## Workflow d'Utilisation

### 1. Préparation STEP7
```bash
# Vérifier les fichiers *_ae.json
ls -la logs/step7/*_ae.json

# Validation du contenu
python3 -c "
import json
import glob

for file in glob.glob('logs/step7/*_ae.json'):
    with open(file, 'r') as f:
        data = json.load(f)
        print(f'{file}: {len(data)} frames processed')
"
```

### 2. Préparation Scripts AE
```bash
# Vérifier les scripts AE
ls -la workflow_scripts/after_effects/

# Test de pont Python
python3 -c "
import sys
sys.path.append('workflow_scripts/after_effects')
import bridge_test
print('Python bridge: OK')
"
```

### 3. Exécution sur Windows
```batch
REM Lancement After Effects avec script
SET AE_PROJECT_FILE=logs/step7/video_name_ae.json
"C:\Program Files\Adobe\Adobe After Effects 2024\Support\afterfx.exe" -r "Media-Solution-v11.2-production.jsx"
```

## Validation et Dépannage

### Erreurs Communes
| Erreur | Cause | Solution |
|---|---|---|
| `File not found` | Fichier manquant | Vérifier chemin STEP7 |
| `Invalid JSON` | Format incorrect | Valider avec `jq` |
| `Python bridge error` | Pont Python cassé | Tester `system.callSystem()` |
| `AE not responding` | After Effects bloqué | Redémarrer AE |

### Scripts de Test
```javascript
// Test dans ExtendScript
var testResult = system.callSystem('python', 'print("Bridge test")');
if (testResult.indexOf("Bridge test") !== -1) {
    alert("Python bridge functional");
} else {
    alert("Python bridge failed");
}
```

## Bonnes Pratiques

### 1. **Sécurité**
- Valider tous les inputs JSON
- Échapper les chaînes de caractères
- Utiliser des chemins absolus pour les ponts

### 2. **Performance**
- Traiter les données par lots
- Utiliser les `*_ae.json` optimisés
- Limiter les appels `system.callSystem()`

### 3. **Compatibilité**
- Tester sur différentes versions d'After Effects
- Documenter les prérequis système
- Gérer les erreurs de pont gracieusement

## Configuration Recommandée

### Variables d'Environnement
```bash
# Pour STEP7
STEP7_EXPORT_FORMAT=ae
STEP7_OPTIMIZE_FOR_AE=true

# Pour ponts AE
AE_PYTHON_PATH=/path/to/scripts
AE_BRIDGE_TIMEOUT=30
```

### Fichiers de Configuration
```json
// ae_config.json
{
  "preferred_script": "Media-Solution-v11.2-production.jsx",
  "auto_load_tracking": true,
  "export_format": "mp4",
  "quality_preset": "high"
}
```

Utilisez ce prompt en tapant `/after-effects-scripts` dans Continue.
