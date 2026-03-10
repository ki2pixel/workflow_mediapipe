# Project-Level Skills for Kimi Code CLI

Ces skills ont été créés par conversion des workflows Windsurf pour permettre leur utilisation dans Kimi Code CLI via les commandes `/skill:<name>`.

## Skills Disponibles

### `/skill:end` - Terminer la Session et Synchroniser la Memory Bank
**Origine:** `.windsurf/workflows/end.md`
**Description:** Procédure pour clôturer une session et synchroniser la memory bank.

### `/skill:enhance` - Améliorer un Prompt avec Contexte Technique  
**Origine:** `.windsurf/workflows/enhance.md`
**Description:** Transforme une demande brute en spécification technique structurée (MEGA-PROMPT).

### `/skill:docs-updater` - Mise à Jour Documentation Métrique  
**Origine:** `.windsurf/workflows/docs-updater.md`
**Description:** Workflow standardisé pour l'audit et la mise à jour de documentation.

### `/skill:enhance-complex` - Architecture Complexe avec Shrimp Task Manager  
**Origine:** `.windsurf/workflows/enhance_complex.md`
**Description:** Analyse profonde avec planification Shrimp Task Manager et réflexion séquentielle.

### `/skill:commit-push` - Commit et Push Automatisé  
**Origine:** `.windsurf/workflows/commit-push.md`
**Description:** Workflow pour committer et pousser les changements vers le remote.

## Comment Utiliser les Skills

Dans Kimi Code CLI, utilisez les commandes suivantes :

1. **Charger un skill spécifique:**
   ```
   /skill:end
   ```

2. **Charger un skill avec une tâche supplémentaire:**
   ```
   /skill:enhance Analyser le service de workflow
   ```

3. **Exécuter un flow skill (si configuré comme flow):**
   ```
   /flow:docs-updater
   ```

## Migration Windsurf → Kimi Code CLI

Les workflows Windsurf utilisent des commandes slash (/) qui ne sont pas disponibles dans l'extension Kimi Code IDE. Cette conversion permet :

1. **Compatibilité:** Utiliser les mêmes workflows via `/skill:<name>`
2. **Découverte automatique:** Kimi Code CLI découvre automatiquement ces skills
3. **Personnalisation:** Possibilité d'adapter les instructions pour Kimi Code CLI

## Structure des Skills

Chaque skill contient :
- `SKILL.md` : Fichier principal avec métadonnées YAML frontmatter et instructions
- Respecte le format standard Agent Skills (https://agentskills.io/)

## Mise à Jour

Pour mettre à jour un skill, éditez simplement le fichier `SKILL.md` correspondant dans son répertoire.