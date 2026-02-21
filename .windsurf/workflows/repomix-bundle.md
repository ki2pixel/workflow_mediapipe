---
description: Generate Repomix bundle for LLM analysis
---

# /repomix-bundle — Générer le bundle Repomix

## Objectif
Créer un bundle optimisé du codebase pour analyse par LLMs externes (Claude, ChatGPT, etc.) en utilisant Repomix avec la configuration existante.

## Étapes

1. **Vérification de la configuration**
   - Confirmer que `repomix.config.json` existe et est à jour avec `read_text_file`
   - Vérifier les patterns d'inclusion/exclusion avec `read_text_file`

2. **Génération du bundle**
   // turbo
   ```bash
   run_command "npx repomix --config repomix.config.json"
   ```

3. **Vérification du résultat**
   - Contrôler que `repomix-output.md` a été généré avec `list_directory`
   - Vérifier la taille et le compte de tokens avec `run_command "wc -c repomix-output.md"`
   - Valider que les fichiers critiques sont inclus avec `search_files`

## Résultat attendu

- **Fichier généré**: `repomix-output.md`
- **Taille cible**: ~384k tokens (config actuelle)
- **Contenu**: Code core + docs essentielles, sans gros assets
- **Usage**: Partage avec LLMs externes pour analyse/review

## Notes

- Le bundle exclut automatiquement: archives, modèles, logs, assets volumineux
- La configuration utilise `.gitignore` et patterns par défaut pour la sécurité
- Le header inclut référence aux `codingstandards.md` obligatoires (vérifier avec `read_text_file`)
- Régénérer après modifications significatives du codebase (utiliser `search` pour détecter les changements)

**Locking Instruction:** Utilisez les outils fast-filesystem (fast_*) pour accéder aux fichiers memory-bank avec des chemins absolus.
