# Project Template for Fine-Tuning

**TL;DR**: Template complet et adaptable pour créer un projet de fine-tuning LLM spécialisé sur n'importe quel domaine technique.

Copiez ce template, adaptez les placeholders [DOMAIN], [TOOLS], etc., et vous aurez une base solide pour votre projet de fine-tuning.

## 📁 Structure du Projet

```
[PROJECT_NAME]/
├── docs/
│   ├── README.md                    # Ce fichier adapté
│   ├── project/
│   │   └── overview.md              # Vue d'ensemble du projet
│   ├── technical/
│   │   ├── dataset-strategy.md      # Stratégie dataset (40/35/15/10)
│   │   ├── model-selection.md       # Comparaison modèles pour [DOMAIN]
│   │   ├── api-reference.md         # Documentation API fine-tuning
│   │   └── training-pipeline.md     # Pipeline d'entraînement
│   ├── guides/
│   │   ├── dataset-creation.md      # Guide création dataset [DOMAIN]
│   │   ├── model-evaluation.md      # Métriques évaluation [DOMAIN]
│   │   └── deployment.md            # Guide déploiement
│   └── universal/                   # Documentation universelle (copiée)
├── dataset/
│   ├── raw/                         # Données brutes collectées
│   ├── prepared/                    # Données préparées
│   └── [PROJECT_NAME]_train.jsonl   # Dataset final
├── scripts/
│   ├── analyze_domain.py            # Analyse domaine [DOMAIN]
│   ├── generate_dataset.py          # Génération dataset
│   ├── train_model.py               # Entraînement modèle
│   ├── evaluate_model.py            # Évaluation spécifique [DOMAIN]
│   └── deploy_model.py              # Déploiement production
├── config/
│   ├── training_config.yaml         # Configuration entraînement
│   ├── model_config.yaml            # Configuration modèle
│   └── deployment_config.yaml       # Configuration production
├── models/
│   ├── checkpoints/                 # Checkpoints entraînement
│   ├── best_model/                   # Meilleur modèle
│   └── production/                   # Modèle production
└── tests/
    ├── dataset/                      # Tests dataset
    ├── model/                        # Tests modèle
    └── integration/                  # Tests intégration
```

## 🎯 Adaptation des Placeholders

### Remplacer dans tout le projet :

| Placeholder | Remplacement | Exemple |
|-------------|---------------|---------|
| `[PROJECT_NAME]` | Nom de votre projet | `ecommerce_assistant` |
| `[DOMAIN]` | Votre domaine technique | `e-commerce`, `IoT`, `biotech` |
| `[KEY_TOOLS]` | Outils principaux | `Shopify, Magento, WooCommerce` |
| `[SPECIFIC_PATTERNS]` | Patterns uniques | `Microservices architecture, Event-driven` |
| `[EXPERIENCE_YEARS]` | Années d'expérience | `5`, `10`, `15` |
| `[TARGET_USERS]` | Utilisateurs cibles | `Developers, DevOps, Data Scientists` |

## 📝 Documentation Adaptée

### docs/README.md (Adapter)

```markdown
# [PROJECT_NAME] Fine-Tuning

**TL;DR**: Création d'un modèle LLM spécialisé pour [DOMAIN] avec un dataset de 100 exemples techniques ciblés.

Vous voulez un assistant IA qui comprend les subtilités de [DOMAIN], mais les modèles génériques se trompent sur [SPECIFIC_CHALLENGE]. Ce projet fine-tune Mistral pour qu'il devienne un expert de votre domaine.

## 🎯 Objectif

Développer un LLM spécialisé capable de :
- Répondre aux questions techniques sur [DOMAIN] avec précision
- Générer les commandes [KEY_TOOLS] correctes
- Diagnostiquer les problèmes courants [DOMAIN]
- Expliquer les patterns [SPECIFIC_PATTERNS]
- Aider à l'intégration avec [ECOSYSTEM]

## 📊 Distribution Dataset

| Catégorie | Pourcentage | Nombre | Focus |
|-----------|-------------|--------|-------|
| **Architecture Knowledge** | 40% | ~40 | [DOMAIN_PATTERNS], concepts, design |
| **Operations** | 35% | ~35 | Commandes [KEY_TOOLS], workflows |
| **Integration** | 15% | ~15 | APIs, ponts [ECOSYSTEM] |
| **Best Practices** | 10% | ~10 | Sécurité, qualité, standards |

## 🚀 Quick Start

1. **Analyser le domaine** : `python scripts/analyze_domain.py`
2. **Créer le dataset** : `python scripts/generate_dataset.py`  
3. **Entraîner le modèle** : `python scripts/train_model.py`
4. **Déployer** : `python scripts/deploy_model.py`

## 🎯 Golden Rule

**[DOMAIN] expertise beats model size** : Un modèle Mistral fine-tuné sur 100 exemples [DOMAIN] surpasse un modèle plus grand mais générique pour les questions spécifiques à votre domaine.
```

### docs/project/overview.md (Adapter)

```markdown
# [PROJECT_NAME] Project Overview

## 🎯 Objectif

Créer un modèle LLM Mistral spécialisé pour [DOMAIN] qui comprend :

### Connaissances Clés
- **Architecture** : [SPECIFIC_PATTERNS], concepts [DOMAIN]
- **Outils** : [KEY_TOOLS] avec commandes exactes
- **Intégrations** : APIs [ECOSYSTEM], ponts techniques
- **Best Practices** : Standards [DOMAIN], sécurité, qualité

### Cas d'Usage Principaux
1. **Assistance Technique** : Répondre aux questions [TARGET_USERS]
2. **Génération de Code** : Patterns [SPECIFIC_PATTERNS], commandes [KEY_TOOLS]
3. **Diagnostic** : Problèmes courants [DOMAIN], troubleshooting
4. **Intégration** : Connecter [ECOSYSTEM] avec votre stack

## 📈 État Actuel

- **Progression dataset** : 0/100 exemples (0% complété)
- **Architecture Knowledge** : 0/40 (0%) 
- **Operations** : 0/35 (0%)
- **Integration** : 0/15 (0%)
- **Best Practices** : 0/10 (0%)

## 🔄 Prochaines Étapes

1. **Phase 1** : Analyse domaine [DOMAIN] (1-2 jours)
2. **Phase 2** : Création dataset (3-5 jours)  
3. **Phase 3** : Entraînement modèle (1-2 jours)
4. **Phase 4** : Déploiement production (1 jour)
```

## ⚙️ Configuration Templates

### config/training_config.yaml

```yaml
# Adapter les valeurs pour votre domaine
training:
  model: "mistral-small-latest"
  dataset: "dataset/[PROJECT_NAME]_train.jsonl"
  
  # Hyperparamètres (adapter si besoin)
  learning_rate: 2e-5
  batch_size: 4
  epochs: 3
  warmup_steps: 100
  
  # Spécifique au domaine
  domain: "[DOMAIN]"
  expertise_level: "senior"
  experience_years: [EXPERIENCE_YEARS]
  
  # Distribution dataset (40/35/15/10)
  categories:
    architecture: 40
    operations: 35
    integration: 15
    best_practices: 10

evaluation:
  # Métriques spécifiques au domaine
  technical_accuracy: 90%
  command_precision: 95%
  domain_knowledge: 85%
  integration_accuracy: 80%
  
  # Tests spécifiques
  test_cases: "tests/domain_test_cases.json"
  validation_split: 0.1

deployment:
  model_name: "[PROJECT_NAME]_v1"
  api_version: "v1"
  production_path: "models/production/[PROJECT_NAME]_v1"
```

### config/model_config.yaml

```yaml
# Configuration du modèle spécialisé
model:
  name: "[PROJECT_NAME]_assistant"
  version: "1.0.0"
  base_model: "mistral-small-latest"
  
  # Persona du domaine
  system_prompt: |
    Tu es un expert senior du domaine [DOMAIN] avec [EXPERIENCE_YEARS] années d'expérience. 
    Tu maîtrises [KEY_TOOLS], [SPECIFIC_PATTERNS], et les standards [DOMAIN].
    Tes réponses sont toujours précises, incluent les commandes exactes avec les bons paramètres,
    et expliquent le 'pourquoi' derrière chaque décision technique.

  # Connaissances du domaine
  domain_knowledge:
    tools: [KEY_TOOLS]
    patterns: [SPECIFIC_PATTERNS]
    concepts: [DOMAIN_CONCEPTS]
    integrations: [ECOSYSTEM_TOOLS]
  
  # Style de réponse
  response_style:
    include_commands: true
    explain_reasoning: true
    provide_alternatives: true
    include_examples: true
```

## 📊 Dataset Template

### dataset/[PROJECT_NAME]_train.jsonl (Template)

```json
{"messages": [{"role": "system", "content": "Tu es un expert senior du domaine [DOMAIN] avec [EXPERIENCE_YEARS] années d'expérience. Tu maîtrises [KEY_TOOLS], [SPECIFIC_PATTERNS], et les standards [DOMAIN]. Tes réponses sont toujours précises, incluent les commandes exactes avec les bons paramètres, et expliquent le 'pourquoi' derrière chaque décision technique."}, {"role": "user", "content": "Comment [ACTION_SPECIFIQUE] dans [DOMAIN] ?"}, {"role": "assistant", "content": "Pour [ACTION_SPECIFIQUE], utilisez cette approche :\n\n**Commande exacte** :\n```bash\n[COMMANDE_SPECIFIQUE_AVEC_PARAMS]\n```\n\n**Pourquoi cette approche ?**\n1. [RAISON_1]\n2. [RAISON_2]\n\n**Alternatives** :\n- [ALTERNATIVE_1] : [AVANTAGE]\n- [ALTERNATIVE_2] : [AVANTAGE]\n\n**Vérification** :\n```bash\n[COMMANDE_VERIFICATION]\n```"}]}
```

## 🛠️ Scripts Templates

### scripts/analyze_domain.py

```python
#!/usr/bin/env python3
"""
Analyse de domaine pour [DOMAIN]
Adapter les patterns et concepts spécifiques à votre domaine
"""

import os
import json
from pathlib import Path

class [DOMAIN]Analyzer:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.domain_info = {
            "name": "[DOMAIN]",
            "experience_years": [EXPERIENCE_YEARS],
            "key_tools": [KEY_TOOLS],
            "patterns": [SPECIFIC_PATTERNS],
            "concepts": [],  # À extraire de la documentation
            "integrations": [ECOSYSTEM_TOOLS]
        }
    
    def analyze_documentation(self):
        """Analyse la documentation pour extraire les concepts"""
        # Adapter cette méthode à votre structure de docs
        pass
    
    def analyze_code(self):
        """Analyse le code pour identifier les patterns"""
        # Adapter cette méthode à votre langage/framework
        pass
    
    def generate_domain_analysis(self):
        """Génère l'analyse de domaine"""
        return {
            "domain": self.domain_info,
            "categories": {
                "architecture": {
                    "count": 40,
                    "sources": ["docs/architecture/", "README.md"],
                    "focus": "[SPECIFIC_PATTERNS], concepts, design"
                },
                "operations": {
                    "count": 35,
                    "sources": ["scripts/", "docs/commands/"],
                    "focus": "Commandes [KEY_TOOLS], workflows"
                },
                "integration": {
                    "count": 15,
                    "sources": ["docs/api/", "docs/integrations/"],
                    "focus": "APIs [ECOSYSTEM], ponts techniques"
                },
                "best_practices": {
                    "count": 10,
                    "sources": ["docs/security/", "docs/standards/"],
                    "focus": "Standards [DOMAIN], sécurité, qualité"
                }
            }
        }

if __name__ == "__main__":
    analyzer = [DOMAIN]Analyzer(".")
    analysis = analyzer.generate_domain_analysis()
    
    with open("domain_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    print(f"✅ Analyse [DOMAIN] terminée")
```

## 🚀 Scripts de Lancement

### setup_project.sh

```bash
#!/bin/bash
# Script de setup pour projet [PROJECT_NAME]

echo "🚀 Setup [PROJECT_NAME] Fine-Tuning Project"

# Créer la structure
mkdir -p docs/{project,technical,guides} dataset/{raw,prepared} \
         scripts config models/{checkpoints,best_model,production} tests/{dataset,model,integration}

# Copier la documentation universelle
echo "📚 Copie documentation universelle..."
cp -r mistral_finetuning/docs/universal docs/

# Adapter les templates
echo "⚙️ Adaptation des templates..."
find docs/ -name "*.md" -exec sed -i 's/\[PROJECT_NAME\]/[PROJECT_NAME]/g' {} \;
find docs/ -name "*.md" -exec sed -i 's/\[DOMAIN\]/[DOMAIN]/g' {} \;
find docs/ -name "*.md" -exec sed -i 's/\[KEY_TOOLS\]/[KEY_TOOLS]/g' {} \;

# Créer les configs
echo "📝 Génération configurations..."
cp config/training_config.yaml.template config/training_config.yaml
cp config/model_config.yaml.template config/model_config.yaml

# Installer les dépendances
echo "📦 Installation dépendances..."
pip install -r requirements.txt

echo "✅ Setup terminé !"
echo "📖 Prochaines étapes :"
echo "   1. Adapter les placeholders dans les fichiers"
echo "   2. Lancer : python scripts/analyze_domain.py"
echo "   3. Créer le dataset : python scripts/generate_dataset.py"
```

## 📋 Checklist d'Adaptation

### ✅ Préparation
- [ ] Copier ce template dans votre projet
- [ ] Remplacer tous les placeholders
- [ ] Adapter la structure des dossiers si besoin
- [ ] Personnaliser les configurations

### ✅ Documentation
- [ ] Adapter docs/README.md à votre domaine
- [ ] Personnaliser docs/project/overview.md
- [ ] Mettre à jour les guides techniques
- [ ] Ajouter vos exemples spécifiques

### ✅ Configuration
- [ ] Adapter config/training_config.yaml
- [ ] Personnaliser config/model_config.yaml
- [ ] Configurer les paths et variables
- [ ] Définir les métriques d'évaluation

### ✅ Scripts
- [ ] Adapter scripts/analyze_domain.py
- [ ] Personnaliser les patterns d'analyse
- [ ] Configurer les tests spécifiques
- [ ] Adapter le déploiement

## 🎯 Golden Rule du Template

**Adapt before you train** : Ne lancez jamais l'entraînement sans avoir adapté tous les placeholders et vérifié que la documentation reflète précisément votre domaine. La qualité de l'adaptation détermine la qualité du modèle final.

---

*Voir [Replication Guide](../guides/replication-guide.md) pour le processus complet et [Universal Patterns](../patterns/) pour les patterns adaptables.*
