# Guide d'Utilisation des Skills Kimi Code CLI

## Contexte
L'extension Kimi Code IDE ne propose pas de commandes slash (/) pour les workflows comme le fait Windsurf. Cette solution convertit les workflows Windsurf en skills Kimi Code CLI pour permettre leur utilisation via `/skill:<name>`.

## Skills Disponibles

| Commande | Description | Equivalence Windsurf |
|----------|-------------|---------------------|
| `/skill:end` | Terminer la session et synchroniser la Memory Bank | `/end` |
| `/skill:enhance` | Améliorer un prompt avec contexte technique | `/enhance` |
| `/skill:docs-updater` | Mise à jour documentation métrique | `/docs-updater` |
| `/skill:enhance-complex` | Architecture complexe avec Shrimp Task Manager | `/enhance_complex` |
| `/skill:commit-push` | Commit et push automatisé | `/commit-push` |
| `/skill:documentation` | Standards de rédaction documentation | (skill existant) |

## Comment Utiliser

### Chargement Simple
```
/skill:end
```

### Chargement avec Tâche Additionnelle
```
/skill:enhance Analyser le service de workflow pour optimisation
```

### Exécution de Workflow Complexe
1. Chargez d'abord le skill :
```
/skill:enhance-complex
```

2. L'agent lira les instructions et vous proposera un mega-prompt

3. Suivez les instructions du mega-prompt généré

## Différences Clés avec Windsurf

### 1. Outils MCP
- **Windsurf** : `run_command` pour exécuter des commandes shell
- **Kimi Code CLI** : `Shell` tool pour exécuter des commandes shell

### 2. Chemins des Skills
- **Windsurf** : `.windsurf/skills/[SKILL_NAME]/SKILL.md`
- **Kimi Code CLI** : `.agents/skills/[SKILL_NAME]/SKILL.md`

### 3. Découverte Automatique
Kimi Code CLI découvre automatiquement les skills dans :
1. `.agents/skills/` (prioritaire)
2. `.kimi/skills/`
3. `.claude/skills/`
4. `.codex/skills/`

### 4. Commandes Slash
- **Windsurf** : `/workflow-name` directement
- **Kimi Code CLI** : `/skill:workflow-name` (nécessite le préfixe `skill:`)

## Migration de Nouveaux Workflows

Pour migrer un workflow Windsurf existant :

1. **Créer le répertoire du skill** :
```bash
mkdir -p .agents/skills/nom-du-workflow
```

2. **Créer le fichier SKILL.md** :
```bash
cp .windsurf/workflows/nom-du-workflow.md .agents/skills/nom-du-workflow/SKILL.md
```

3. **Ajouter le frontmatter YAML** :
```yaml
---
name: nom-du-workflow
description: Description du workflow
---
```

4. **Ajuster les références d'outils** :
- Remplacer `run_command` par `Shell` tool
- Vérifier les chemins des fichiers référencés

## Conseils d'Utilisation

### Pour les Développeurs
- Utilisez `/skill:commit-push` pour les commits fréquents
- Utilisez `/skill:docs-updater` avant de documenter du code complexe
- Utilisez `/skill:enhance` pour clarifier les requêtes ambiguës

### Pour les Architectes
- Utilisez `/skill:enhance-complex` pour les tâches multi-étapes
- Combinez avec Shrimp Task Manager (`plan_task`, `split_tasks`, etc.)

### Pour la Documentation
- Utilisez `/skill:documentation` pour les standards de rédaction
- Utilisez `/skill:docs-updater` pour les audits de documentation

## Dépannage

### Le Skill n'est pas Reconnu
1. Vérifiez que le répertoire `.agents/skills/[SKILL_NAME]` existe
2. Vérifiez que `SKILL.md` existe dans ce répertoire
3. Vérifiez que le frontmatter YAML est correct

### Erreurs d'Outils MCP
1. Les outils référencés doivent être disponibles dans Kimi Code CLI
2. Vérifiez les noms d'outils (`Shell` au lieu de `run_command`)
3. Vérifiez les chemins absolus si nécessaire

### Problèmes de Performance
1. Limitez la taille des SKILL.md (max 500 lignes recommandé)
2. Déplacez le contenu détaillé dans des sous-répertoires
3. Utilisez des références relatives aux fichiers externes

## Avantages de cette Approche

1. **Compatibilité** : Fonctionne avec Kimi Code CLI et d'autres agents
2. **Portabilité** : Skills indépendants de l'éditeur/IDE
3. **Maintenabilité** : Format standard ouvert (Agent Skills)
4. **Découverte** : Détection automatique par les agents
5. **Réutilisation** : Skills partageables entre projets

## Ressources
- [Format Agent Skills](https://agentskills.io/)
- [Documentation Kimi Code CLI](docs/docs-kimi-code_extension/customization/skills.md)
- [Répertoire des skills](/home/kidpixel/workflow_mediapipe/.agents/skills/)