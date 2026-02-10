---
name: workflow-docs-updater-plus
description: Docs Updater (Context-Aware with Code Verification)
---

# Workflow Docs Updater Plus

## Quand l'utiliser
- Synchroniser `docs/workflow/*` avec des refactors récents (pipeline, UX, audits).
- Mettre à jour `ARCHITECTURE_COMPLETE_FR.md`, `GUIDE_DEMARRAGE_RAPIDE.md`, `REFERENCE_RAPIDE_DEVELOPPEURS.md` après changements backend/frontend.
- Ajouter les décisions correspondantes dans la Memory Bank.

## Processus recommandé
1. **Collecte contexte**
   - Lire Memory Bank (`productContext`, `progress`, `decisionLog`) pour comprendre les évolutions récentes.
   - Inspecter les fichiers code concernés (services, routes, frontend) via `grep_search`/`read_file`.
2. **Identifier docs impactées**
   - Mapper la fonctionnalité modifiée → doc(s) correspondantes (ex: pipeline STEP5 → `STEP5_SUIVI_VIDEO.md`).
3. **Mettre à jour la doc**
   - Respecter le format existant (titres, sections numérotées).
   - Mentionner les variables `.env`, scripts, workflows pertinents.
   - Expliquer le *pourquoi* (règle mémoire : commentaire « pourquoi » pas « comment »).
4. **Vérifications croisées**
   - S’assurer que les informations doc ↔ code concordent (ex: `WorkflowCommandsConfig`, `AppState` toggles).
   - Ajouter références aux tests/commandes exécutées si applicable.
5. **Memory Bank**
   - Ajouter une entrée dans `decisionLog.md` et `progress.md` si la doc reflète une décision/avancement majeur.
 6. **Rappel rapide**
    - Utiliser `resources/docs_sync_checklist.md` pour cocher chaque étape (préparation, collecte, mise à jour, validation, sortie).

## Outils utiles
- `code_search docs/workflow/ '<mot-clé>'` pour repérer sections.
- `python scripts/docs-updater.py` (si disponible) ou run manuel via `apply_patch`.
- `npm run test:frontend` / `pytest ...` pour vérifier que la doc reflète un comportement réellement testé.

## Checklist finale
- [ ] Reference aux audits (`docs/workflow/audits/...`) mise à jour si besoin.
- [ ] Variables `.env` documentées et alignées.
- [ ] Liens internes (ancres, figures) valides.
- [ ] Memory Bank synchronisée (decision/progress).
