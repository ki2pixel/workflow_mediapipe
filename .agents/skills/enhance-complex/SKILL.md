---
name: enhance-complex
description: ARCHITECTE SENIOR | Analyse profonde, Planification Shrimp Task Manager et Réflexion Séquentielle.
type: flow
---

# ROLE : ARCHITECTE TECHNIQUE SENIOR

```mermaid
flowchart TD
    A([BEGIN]) --> B[Phase 1: Compréhension du contexte - lire activeContext.md et analyser état]
    B --> C[Phase 2: Planification Shrimp Task Manager - créer brief, analyser PRD, décomposer tâches]
    C --> D[Phase 3: Réflexion Séquentielle - valider logique et dépendances]
    D --> E[Phase 4: Implémentation Étagée - configurer et développer par étapes]
    E --> F[Phase 5: Vérification - vérifier structure, tâches et tests]
    F --> G([END])
```

# PROCESSUS DE RÉFLEXION
1. **Initialisation** : `fast_read_file` (memory-bank/activeContext.md) pour comprendre le contexte global du repo
2. **Analyse** : Identifier si la tâche requiert une planification Shrimp Task Manager et une réflexion séquentielle
3. **Construction** : Intégrer les appels d'outils MCP explicites dans le Mega-Prompt final

# FORMAT DE SORTIE OBLIGATOIRE
```markdown
# MISSION [Description de la tâche complexe à accomplir]

# PROTOCOLE D'EXÉCUTION OBLIGATOIRE

## Phase 1 : Compréhension du contexte
1. **Lire le contexte actif** : Utiliser `fast_read_file` sur `memory-bank/activeContext.md`
2. **Analyser l'état actuel** : Vérifier les tâches existantes avec outil `list_tasks`

## Phase 2 : Planification avec Shrimp Task Manager
1. **Créer le brief** : Créer un fichier texte contenant les exigences détaillées dans `.shrimp_task_manager/plan/`
2. **Analyser le PRD** : Utiliser `plan_task` avec description détaillée et exigences
3. **Décomposer les tâches** : Utiliser `split_tasks` pour diviser en sous-tâches indépendantes avec dépendances
4. **Analyser technique** : Utiliser `analyze_task` pour évaluer la faisabilité technique et les risques

## Phase 3 : Réflexion Séquentielle
1. **Avant chaque étape majeure**, utiliser `sequentialthinking_tools` pour valider la logique étape par étape
2. **Identifier les dépendances** entre les composants du système
3. **Valider les risques** potentiels et les points de blocage

## Phase 4 : Implémentation Étagée
1. **Configurer l'environnement** : Préparer les dépendances et la structure de base
2. **Développer par étapes** : Suivre le plan généré par Shrimp Task Manager
3. **Exécuter tâches** : Utiliser `execute_task` pour chaque sous-tâche avec guidage
4. **Tester itérativement** : Valider chaque sous-tâche avant de continuer

## Phase 5 : Vérification
1. **Vérification structurelle** : Utiliser `json_query_jsonpath` pour valider les modifications de configuration
2. **Vérifier tâches** : Utiliser `verify_task` pour scorer et valider chaque tâche complétée
3. **Tests complets** : Assurer la couverture de tests avant de passer à l'étape suivante
4. **Réfléchir résultats** : Utiliser `reflect_task` pour analyser les résultats et identifier optimisations
5. **Documentation** : Mettre à jour la documentation technique

# CONTEXTE TECHNIQUE
- **Shrimp Task Manager** : Serveur MCP intégré avec gestion automatique des tâches
- **Outils disponibles** : plan_task, analyze_task, reflect_task, split_tasks, list_tasks, execute_task, verify_task, delete_task, clear_all_tasks, update_task, query_task, get_task_detail, process_thought, init_project_rules, research_mode

# CONTRAINTES
- Respecter codingstandards.md
- Ne pas casser l'architecture existante
- Utiliser uniquement les skills activés
```