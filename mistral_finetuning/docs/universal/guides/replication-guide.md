# Project Replication Guide

**TL;DR**: Répliquez la méthode de fine-tuning sur n'importe quel projet en 4 étapes : analyse de domaine → adaptation des templates → création dataset → pipeline training.

Vous avez un nouveau projet et vous voulez créer un LLM expert, mais vous ne savez pas comment adapter la méthode workflow_mediapipe à votre domaine. C'est le "Replication Gap" - une méthode qui fonctionne mais pas de guide pour la répliquer.

## 🚀 Méthode de Réplication en 4 Phases

### Phase 1 : Analyse de Domaine (1-2 jours)

#### 1.1 Identifier l'Expertise Unique
```bash
# Questions clés à vous poser :
- Quelles commandes spécifiques les gens utilisent-ils ?
- Quels erreurs reviennent constamment ?
- Quels patterns architecturaux sont uniques ?
- Quelles intégrations sont critiques ?
```

#### 1.2 Collecter les Sources
```bash
# Sources à analyser :
find . -name "*.md" -o -name "*.rst" | head -20        # Documentation
find . -name "*.py" -o -name "*.js" | head -20        # Code source  
find . -name "*.sh" -o -name "*.yaml" | head -10      # Scripts/Config
grep -r "TODO\|FIXME\|BUG" --include="*.py" . | head -10  # Problèmes
```

#### 1.3 Cartographier les Connaissances
```markdown
# Domain Mapping Template
## Architecture Concepts (40%)
- [Concept 1] : [Description]
- [Pattern 1] : [Usage]

## Operations (35%) 
- [Command 1] : [Contexte]
- [Workflow 1] : [Étapes]

## Integration (15%)
- [API 1] : [Pont]
- [Tool 1] : [Intégration]

## Best Practices (10%)
- [Security 1] : [Règle]
- [Quality 1] : [Standard]
```

### Phase 2 : Adaptation des Templates (1 jour)

#### 2.1 Copier la Structure Universelle
```bash
# Copier les templates universels
cp -r mistral_finetuning/docs/universal/templates/ votre_projet/docs/
cp -r mistral_finetuning/docs/universal/patterns/ votre_projet/docs/
```

#### 2.2 Adapter le Template Projet
```markdown
# votre_projet/docs/project/overview.md
# Remplacer les placeholders :
- [DOMAIN] → votre domaine (ex: "e-commerce", "IoT", "biotech")
- [KEY_TOOLS] → vos outils principaux
- [SPECIFIC_PATTERNS] → vos patterns uniques
```

#### 2.3 Personnaliser le System Prompt
```python
# Adapter le system prompt template
SYSTEM_PROMPT_TEMPLATE = """
Tu es un expert senior du domaine {domain} avec {experience} années d'expérience. 
Tu maîtrises {key_concepts}, {specific_tools}, et {patterns}.
Tes réponses sont toujours précises, incluent les commandes exactes 
avec les bons chemins/paramètres, et expliquent le 'pourquoi' derrière chaque décision technique.
""".format(
    domain="votre_domaine",
    experience="X", 
    key_concepts="vos_concepts",
    specific_tools="vos_outils",
    patterns="vos_patterns"
)
```

### Phase 3 : Création Dataset (2-5 jours)

#### 3.1 Utiliser le Template Dataset
```bash
# Copier le template
cp mistral_finetuning/docs/universal/templates/dataset-template.jsonl votre_projet/dataset/
```

#### 3.2 Créer les Exemples par Catégorie

**Architecture Knowledge (40 exemples)**
```bash
# Sources : README, architecture docs, design decisions
./scripts/extract_architecture_examples.py \
  --source docs/ \
  --output dataset/architecture_examples.jsonl \
  --target_count 40
```

**Operations (35 exemples)**
```bash
# Sources : scripts, CLI tools, error logs
./scripts/extract_operations_examples.py \
  --source scripts/ logs/ \
  --output dataset/operations_examples.jsonl \
  --target_count 35
```

**Integration (15 exemples)**
```bash
# Sources : API docs, integration guides
./scripts/extract_integration_examples.py \
  --source docs/api/ \
  --output dataset/integration_examples.jsonl \
  --target_count 15
```

**Best Practices (10 exemples)**
```bash
# Sources : security docs, coding standards
./scripts/extract_best_practices_examples.py \
  --source docs/security/ docs/standards/ \
  --output dataset/best_practices_examples.jsonl \
  --target_count 10
```

#### 3.3 Fusionner et Valider
```bash
# Fusionner tous les exemples
cat dataset/*_examples.jsonl > dataset/complete_dataset.jsonl

# Valider le format
python scripts/validate_dataset.py \
  --input dataset/complete_dataset.jsonl \
  --output dataset/validated_dataset.jsonl
```

### Phase 4 : Pipeline Training (1-2 jours)

#### 4.1 Adapter la Configuration
```yaml
# config/training_config.yaml
training:
  model: "mistral-small-latest"
  dataset: "dataset/validated_dataset.jsonl"
  
  # Adapter les hyperparamètres
  learning_rate: 2e-5
  batch_size: 4
  epochs: 3
  
  # Spécifique au domaine
  domain: "votre_domaine"
  expertise_level: "senior"
```

#### 4.2 Lancer le Pipeline
```bash
# Utiliser le pipeline universel
python mistral_finetuning/scripts/train_model.py \
  --config config/training_config.yaml \
  --output_dir models/ \
  --monitor
```

#### 4.3 Évaluer les Résultats
```bash
# Tests spécifiques au domaine
python scripts/domain_evaluation.py \
  --model models/best_model \
  --test_cases domain_test_cases.json
```

## 🛠️ Scripts de Réplication

### Script d'Analyse de Domaine
```python
# scripts/analyze_domain.py
import os
import json
from pathlib import Path

class DomainAnalyzer:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.analysis = {
            "architecture_concepts": [],
            "operations": [],
            "integrations": [],
            "best_practices": []
        }
    
    def scan_documentation(self):
        """Scan la documentation pour les concepts clés"""
        for md_file in self.project_path.rglob("*.md"):
            with open(md_file) as f:
                content = f.read()
                
            # Extraire les patterns architecturaux
            if "pattern" in content.lower() or "architecture" in content.lower():
                self.analysis["architecture_concepts"].append({
                    "file": str(md_file),
                    "concepts": self._extract_concepts(content)
                })
    
    def scan_code_patterns(self):
        """Scan le code pour les patterns récurrents"""
        for py_file in self.project_path.rglob("*.py"):
            with open(py_file) as f:
                content = f.read()
            
            # Extraire les patterns de code
            patterns = self._extract_code_patterns(content)
            if patterns:
                self.analysis["operations"].extend(patterns)
    
    def generate_domain_report(self):
        """Génère un rapport d'analyse de domaine"""
        report = f"""
# Domain Analysis Report

## Architecture Concepts ({len(self.analysis['architecture_concepts'])})
{self._format_concepts(self.analysis['architecture_concepts'])}

## Operations ({len(self.analysis['operations'])})
{self._format_operations(self.analysis['operations'])}

## Integrations ({len(self.analysis['integrations'])})
{self._format_integrations(self.analysis['integrations'])}

## Best Practices ({len(self.analysis['best_practices'])})
{self._format_best_practices(self.analysis['best_practices'])}
"""
        return report
    
    def _extract_concepts(self, content):
        """Extrait les concepts architecturaux du texte"""
        # Implémentation NLP simple
        concepts = []
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['pattern', 'architecture', 'design']):
                concepts.append(line.strip())
        return concepts
    
    def _extract_code_patterns(self, content):
        """Extrait les patterns de code"""
        patterns = []
        # Chercher les classes, fonctions récurrentes
        if 'class ' in content:
            patterns.append({"type": "class_pattern", "content": content})
        return patterns

# Usage
analyzer = DomainAnalyzer("/path/to/project")
analyzer.scan_documentation()
analyzer.scan_code_patterns()
report = analyzer.generate_domain_report()

with open("domain_analysis.md", "w") as f:
    f.write(report)
```

### Script de Génération Dataset
```python
# scripts/generate_dataset.py
import json
import random
from pathlib import Path

class DatasetGenerator:
    def __init__(self, domain_analysis):
        self.domain = domain_analysis
        self.templates = self._load_templates()
    
    def generate_examples(self, category, count):
        """Génère des exemples pour une catégorie"""
        examples = []
        
        for i in range(count):
            example = self._create_example(category, i)
            examples.append(example)
        
        return examples
    
    def _create_example(self, category, index):
        """Crée un exemple spécifique"""
        template = self.templates[category]
        
        # Adapter le template au domaine
        system_prompt = self._adapt_system_prompt(template["system"])
        user_question = self._generate_question(category, index)
        assistant_answer = self._generate_answer(category, user_question)
        
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question},
                {"role": "assistant", "content": assistant_answer}
            ]
        }
    
    def _adapt_system_prompt(self, template):
        """Adapte le system prompt au domaine"""
        return template.format(
            domain=self.domain["name"],
            experience=self.domain.get("experience", "5"),
            key_concepts=", ".join(self.domain["architecture_concepts"][:5]),
            specific_tools=", ".join(self.domain["tools"][:3]),
            patterns=", ".join(self.domain["patterns"][:3])
        )
    
    def generate_complete_dataset(self, output_path):
        """Génère le dataset complet"""
        dataset = []
        
        # Distribution 40/35/15/10
        categories = {
            "architecture": 40,
            "operations": 35, 
            "integration": 15,
            "best_practices": 10
        }
        
        for category, count in categories.items():
            examples = self.generate_examples(category, count)
            dataset.extend(examples)
        
        # Mélanger et sauvegarder
        random.shuffle(dataset)
        
        with open(output_path, "w") as f:
            for example in dataset:
                f.write(json.dumps(example) + "\n")
        
        print(f"Dataset généré : {len(dataset)} exemples dans {output_path}")

# Usage
domain_analysis = json.load(open("domain_analysis.json"))
generator = DatasetGenerator(domain_analysis)
generator.generate_complete_dataset("project_dataset.jsonl")
```

## 📋 Checklist de Réplication

### Phase 1 : Analyse ✅
- [ ] Documentation scannée et concepts extraits
- [ ] Code analysé et patterns identifiés
- [ ] Rapport de domaine généré
- [ ] Distribution 40/35/15/10 validée

### Phase 2 : Adaptation ✅
- [ ] Templates copiés et adaptés
- [ ] System prompt personnalisé
- [ ] Configuration projet créée
- [ ] Structure documentation mise en place

### Phase 3 : Dataset ✅
- [ ] Exemples générés par catégorie
- [ ] Dataset fusionné et validé
- [ ] Format JSONL vérifié
- [ ] Qualité exemples contrôlée

### Phase 4 : Training ✅
- [ ] Configuration training adaptée
- [ ] Pipeline lancé avec monitoring
- [ ] Évaluation domaine spécifique
- [ ] Modèle validé pour production

## 🎯 Golden Rule de Réplication

**Domain first, tools second** : Commencez toujours par comprendre profondément le domaine avant de penser aux outils techniques. Un dataset qui reflète la vraie expertise métier vaut mieux qu'un pipeline technique parfait sur des données génériques.

---

*Voir [Domain Analysis Guide](domain-analysis.md) pour l'analyse approfondie et [Templates](../templates/) pour les éléments adaptables.*
