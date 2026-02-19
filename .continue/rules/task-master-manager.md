---
name: task-master-manager
description: Expert en planification utilisant l'API Mistral pour la gestion de tâches complexes et la priorisation de backlog.
alwaysApply: false
---

# Task Master Manager

## Overview
Expert en planification utilisant l'API Mistral pour la gestion de tâches complexes et la priorisation de backlog.

## Actions Principales
- `task-master parse-prd` : Analyser un cahier des charges (PRD) pour extraire les tâches
- `analyze-complexity` : Évaluer la complexité technique et les dépendances
- `task-master next` : Déterminer la prochaine tâche à exécuter dans le backlog

## Workflow Standard
1. **Initialisation** : Utiliser `task-master parse-prd` sur la demande utilisateur
2. **Analyse** : Appliquer `analyze-complexity` pour évaluer les risques et effort
3. **Priorisation** : Vérifier systématiquement `task-master next` avant chaque action
4. **Exécution** : Procéder étape par étape selon le backlog établi

## Configuration Mistral
- **API** : Mistral API avec `mistral-large-latest`
- **Usage** : Analyse de tâches, estimation de complexité, génération de backlog
- **Fallback** : Si API indisponible, utiliser logique heuristique locale

## Intégration
- Toujours appelé pour les demandes impliquant `tâche`, `task`, `backlog`, `planification`, `roadmap`
- Priorité 1 pour les tâches de planification
- Compatible avec `sequentialthinking` pour la validation logique
