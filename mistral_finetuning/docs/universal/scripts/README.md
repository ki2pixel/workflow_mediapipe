# Universal Scripts for Fine-Tuning

**TL;DR**: Scripts Python réutilisables et adaptables pour automatiser les 4 phases du fine-tuning sur n'importe quel domaine.

Ces scripts sont le moteur de la méthode universelle. Ils automatisent l'analyse de domaine, la génération de dataset, l'entraînement et l'évaluation. Copiez-les, adaptez les placeholders, et vous aurez un pipeline complet fonctionnel.

## 📁 Structure des Scripts

```
scripts/
├── README.md                    # Ce fichier
├── analyze_domain.py            # Phase 1 : Analyse de domaine
├── generate_dataset.py         # Phase 2 : Génération dataset
├── train_model.py               # Phase 3 : Entraînement modèle
├── evaluate_model.py            # Phase 4 : Évaluation domaine-spécifique
├── deploy_model.py              # Déploiement production
├── utils/                       # Utilitaires réutilisables
│   ├── dataset_validator.py     # Validation format JSONL
│   ├── domain_scanner.py        # Scan automatique de domaine
│   └── template_adapter.py      # Adaptation des templates
└── templates/                   # Templates de configuration
    ├── config_template.yaml     # Configuration entraînement
    └── requirements.txt         # Dépendances Python
```

## 🚀 Quick Start

```bash
# 1. Copier les scripts dans votre projet
cp -r mistral_finetuning/docs/universal/scripts votre_projet/

# 2. Adapter les placeholders
find scripts/ -name "*.py" -exec sed -i 's/\[DOMAIN\]/votre_domaine/g' {} \;

# 3. Installer les dépendances
pip install -r scripts/templates/requirements.txt

# 4. Lancer le pipeline complet
python scripts/analyze_domain.py
python scripts/generate_dataset.py
python scripts/train_model.py
python scripts/evaluate_model.py
```

## 🔄 Pipeline Automatisé

### Phase 1 : Analyse de Domaine
```bash
python scripts/analyze_domain.py \
  --project_path . \
  --output domain_analysis.json \
  --domain "[DOMAIN]"
```

### Phase 2 : Génération Dataset
```bash
python scripts/generate_dataset.py \
  --domain_analysis domain_analysis.json \
  --output dataset/[PROJECT_NAME]_train.jsonl \
  --count 100
```

### Phase 3 : Entraînement
```bash
python scripts/train_model.py \
  --config scripts/templates/config_template.yaml \
  --dataset dataset/[PROJECT_NAME]_train.jsonl \
  --output models/
```

### Phase 4 : Évaluation
```bash
python scripts/evaluate_model.py \
  --model models/best_model \
  --test_cases domain_test_cases.json \
  --report evaluation_report.md
```

## 🛠️ Scripts Principaux

### analyze_domain.py
- **Fonction** : Scan documentation, code, et logs du projet
- **Sortie** : Analyse structurée du domaine avec distribution 40/35/15/10
- **Adaptation** : Remplacer `[DOMAIN]` et les patterns de scan

### generate_dataset.py
- **Fonction** : Génère exemples JSONL basés sur l'analyse de domaine
- **Sortie** : Dataset complet au format Mistral Chat Completions
- **Adaptation** : Adapter les templates de réponses au domaine

### train_model.py
- **Fonction** : Pipeline d'entraînement avec monitoring
- **Sortie** : Modèle fine-tuné avec métriques
- **Adaptation** : Configuration hyperparamètres dans YAML

### evaluate_model.py
- **Fonction** : Évaluation domaine-spécifique avec métriques techniques
- **Sortie** : Rapport d'évaluation détaillé
- **Adaptation** : Test cases personnalisés par domaine

## 📋 Adaptation des Placeholders

### Dans tous les scripts Python :
```python
# Remplacer ces placeholders
[DOMAIN]           # Votre domaine (ex: "e-commerce")
[PROJECT_NAME]     # Nom de votre projet
[KEY_TOOLS]        # Vos outils principaux
[EXPERIENCE_YEARS] # Années d'expérience (ex: "5")
```

### Dans les fichiers de configuration :
```yaml
# Adapter les valeurs
domain: "[DOMAIN]"
model_name: "[PROJECT_NAME]_v1"
expertise_level: "senior"
```

## 🎯 Cas d'Usage par Type de Projet

### Software Engineering
```bash
python scripts/analyze_domain.py \
  --domain "software_engineering" \
  --scan_patterns "class,interface,api,endpoint"
```

### Data Science
```bash
python scripts/analyze_domain.py \
  --domain "data_science" \
  --scan_patterns "model,training,pipeline,feature"
```

### DevOps Infrastructure
```bash
python scripts/analyze_domain.py \
  --domain "devops" \
  --scan_patterns "docker,kubernetes,terraform,ansible"
```

### Creative Tools
```bash
python scripts/analyze_domain.py \
  --domain "creative_tools" \
  --scan_patterns "design,workflow,asset,render"
```

## 🔧 Utilitaires Inclus

### dataset_validator.py
- Validation syntaxique JSONL
- Vérification structure messages
- Contrôle qualité des réponses

### domain_scanner.py
- Scan automatique de fichiers
- Extraction de concepts techniques
- Génération de rapport d'analyse

### template_adapter.py
- Adaptation automatique des templates
- Remplacement des placeholders
- Génération de configurations personnalisées

## 📦 Dépendances

```bash
# Installation automatique
pip install -r scripts/templates/requirements.txt

# Dépendances principales
- mistralai           # API Mistral
- pydantic           # Validation données
- pyyaml             # Configuration YAML
- click              # CLI
- tqdm               # Progress bars
- pandas             # Manipulation données
- nltk               # Traitement texte
```

## 🚨 Points d'Attention

### Avants de lancer :
1. **Adapter les placeholders** dans tous les scripts
2. **Vérifier les chemins** dans les configurations
3. **Configurer les clés API** si nécessaire
4. **Tester sur petit dataset** d'abord

### Pendant l'exécution :
1. **Monitor les logs** pour erreurs
2. **Vérifier la qualité** du dataset généré
3. **Sauvegarder les checkpoints** régulièrement
4. **Valider les résultats** après chaque phase

## 🎯 Golden Rule des Scripts

**Automate but validate** : Les scripts automatisent 90% du travail, mais gardez toujours une validation humaine sur les résultats finaux. Un dataset généré automatiquement doit être revu par un expert du domaine.

---

*Voir [Replication Guide](../guides/replication-guide.md) pour le processus complet et [Universal Patterns](../patterns/) pour les concepts derrière ces scripts.*
