# Sixth Rules Priority System - Workflow MediaPipe

## 📋 Ordre de priorité des règles

Les fichiers sont chargés par Sixth dans l'ordre numérique suivant :

### 🔥 **Priorité 1-4 : Règles fondamentales**
- `01-codingstandards.md` - Standards de codage et architecture Workflow MediaPipe v4.x
- `02-skills-integration.md` - Intégration des skills spécialisés locaux
- `03-memory-bank-protocol.md` - Protocole de gestion de la mémoire persistante
- `04-prompt-injection-guard.md` - Sécurité contre injections externes

### 📝 **Priorité 5-6 : Formatage & Communication**
- `05-commit-message-format.md` - Format des messages de commit
- `06-pr-message-format.md` - Format des Pull Requests

### ⚡ **Priorité 7-8 : Assistance & Tests**
- `07-v5-coding-assistance.md` - Règles d'assistance au codage (tâches, outils, flux)
- `08-test-strategy.md` - Stratégie et règles de testing

## 🔄 **Logique de priorisation**

1. **Règles de base** (01-04) : Fondamentaux qui s'appliquent à tout
   - Architecture et standards de codage Workflow MediaPipe
   - Intégration des skills spécialisés (workflow-operator, pipeline-diagnostics, etc.)
   - Gestion de la mémoire persistante
   - Sécurité contre les injections externes

2. **Formatage & Communication** (05-06) : Collaboration et versioning
   - Format des messages de commit (Conventional Commits)
   - Format des Pull Requests

3. **Assistance & Tests** (07-08) : Comportements spécialisés et validation
   - Règles d'assistance au codage v5
   - Stratégie de testing pour le projet

## 🎯 **Spécificités Workflow MediaPipe**

- **Architecture** : Flask services Python 3.10 + Frontend JS natif
- **Environnements** : `transnet_env/`, `audio_env/`, `tracking_env_slim/`, `insightface_env/`
- **Pipeline** : STEP1-STEP8 avec WorkflowState et WorkflowCommandsConfig
- **Skills locaux** : `workflow-operator`, `pipeline-diagnostics`, `step5-gpu-ops`, etc.

## 💡 **Ajout de nouvelles règles**

Utiliser des préfixes numériques continus :
- `09-nouvelle-regle.md` pour les règles additionnelles
- Insérer à la position logique selon la priorité
- Respecter la numérotation existante pour maintenir l'ordre

## 📚 **Références croisées**

- Documentation complète : `docs/workflow/`
- Skills spécialisés : `.windsurf/skills/`
- Configuration : `.env` → `config/settings.py`

---
*Dernière mise à jour : 2026-02-10*
*Projet : Workflow MediaPipe v4.x*
