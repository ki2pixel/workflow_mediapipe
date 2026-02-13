# Mistral Fine-Tuning for Workflow MediaPipe

**TL;DR**: Création d'un modèle Mistral spécialisé pour le pipeline workflow_mediapipe avec un dataset de 100 exemples techniques ciblés.

Vous voulez déployer un assistant IA qui comprend les subtilités de votre pipeline vidéo, mais les modèles génériques se trompent sur les commandes d'environnement et ne connaissent pas votre architecture. Ce projet fine-tune Mistral pour qu'il devienne un expert de votre workflow.

## 🎯 Objectif du Projet

Développer un LLM spécialisé capable de :
- Répondre aux questions techniques sur le pipeline avec précision
- Générer les commandes d'exécution correctes avec les bons environnements  
- Diagnostiquer les problèmes courants et proposer des solutions
- Expliquer l'architecture et les patterns de code
- Aider à l'intégration avec After Effects

## 📊 Structure du Dataset

| Catégorie | Pourcentage | Nombre d'exemples | Focus |
|-----------|-------------|-------------------|-------|
| **Architecture knowledge** | 40% | ~40 | Structure, patterns, services, frontend |
| **Pipeline operations** | 35% | ~35 | Commandes, erreurs, optimisations |
| **After Effects integration** | 15% | ~15 | ExtendScript, ponts, workflows |
| **Best practices/security** | 10% | ~10 | Sécurité, tests, déploiement |

## 📚 Documentation

### 🏗️ Vue d'Ensemble
- [Project Overview](project/overview.md) - Objectifs, stratégie et état actuel

### 🔧 Documentation Technique  
- [Dataset Strategy](technical/dataset-strategy.md) - Stratégie de création du dataset
- [Model Selection](technical/model-selection.md) - Comparaison des modèles Mistral
- [API Reference](technical/api-reference.md) - Documentation API fine-tuning
- [Training Pipeline](technical/training-pipeline.md) - Pipeline d'entraînement complet

### 📖 Guides Pratiques
- [Dataset Creation Guide](guides/dataset-creation.md) - Guide pratique de création
- [Model Evaluation](guides/model-evaluation.md) - Métriques et validation
- [Deployment Guide](guides/deployment.md) - Guide de déploiement

### 🔬 Recherche
- [Text-Vision Fine-tuning](research/text-vision-finetuning.md) - Recherche vision/texte
- [Classifier Patterns](research/classifier-patterns.md) - Patterns pour classifieurs

### 🌍 Documentation Universelle
- [Universal Fine-Tuning Method](universal/README.md) - **Méthode réutilisable pour tous projets**
- [Replication Guide](universal/guides/replication-guide.md) - Guide pour répliquer sur d'autres projets
- [Universal Patterns](universal/patterns/dataset-design.md) - Patterns adaptables à tout domaine
- [Project Templates](universal/templates/project-template.md) - Template de projet complet

## 🚀 Quick Start

1. **Comprendre le projet** : Lisez [Project Overview](project/overview.md)
2. **Choisir un modèle** : Consultez [Model Selection](technical/model-selection.md)  
3. **Créer le dataset** : Suivez [Dataset Creation Guide](guides/dataset-creation.md)
4. **Lancer l'entraînement** : Utilisez [Training Pipeline](technical/training-pipeline.md)

## 📈 État Actuel

- **Progression dataset** : 17/100 exemples (17% complété)
- **Architecture Knowledge** : 17/40 (42.5%) ✅
- **Pipeline Operations** : 0/35 (0%) 🔄  
- **After Effects Integration** : 0/15 (0%) ❌
- **Best Practices/Security** : 0/10 (0%) ❌

## 🏆 Golden Rule

**Dataset spécialisé > modèle générique** : Un modèle Mistral fine-tuné sur 100 exemples techniques ciblés surpasse un modèle plus grand mais générique pour les questions spécifiques au pipeline.

---

*Ce projet suit les [standards de documentation du projet](../../.windsurf/skills/documentation/SKILL.md) et s'intègre dans l'écosystème workflow_mediapipe.*
