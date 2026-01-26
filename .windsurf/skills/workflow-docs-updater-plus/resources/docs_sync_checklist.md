# Docs Sync Checklist (Workflow Docs Updater Plus)

## 1. Préparation
- [ ] Lire `memory-bank/{productContext,progress,decisionLog}.md` pour connaître les changements récents.
- [ ] Lister les fichiers code impactés (services, routes, frontend) et les commits associés.
- [ ] Identifier les documents cibles (`docs/workflow/...`, `ARCHITECTURE_COMPLETE_FR.md`, etc.).

## 2. Collecte d’évidence
- [ ] Noter les commandes/tests exécutés qui prouvent le comportement.
- [ ] Capturer les variables `.env` concernées (noms uniquement, pas les secrets).

## 3. Mise à jour
- [ ] Éditer les docs en conservant le format existant (titres, sections numérotées, tableaux).
- [ ] Ajouter le *pourquoi* de la modification (contexte métier ou technique).
- [ ] Vérifier la cohérence code ↔ doc (ex: `WorkflowCommandsConfig`, `AppState` toggles).

## 4. Validation croisée
- [ ] Relecture orthographe + liens internes (`[texte](#ancre)` ou chemins relatifs).
- [ ] Si nouvelle variable `.env` → mention dans `GUIDE_DEMARRAGE_RAPIDE.md` + doc spécifique.
- [ ] Ajouter une entrée Memory Bank si décision majeure (decisionLog/progress).

## 5. Sortie
- [ ] Résumer les fichiers modifiés + sections clé dans le ticket/PR.
- [ ] Inclure les commandes/tests exécutés.
- [ ] Lister les follow-ups éventuels (ex: screenshots manquants, migrations docs futures).
