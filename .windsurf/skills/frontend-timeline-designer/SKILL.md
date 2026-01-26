---
name: frontend-timeline-designer
description: Create or adjust the Connected Timeline UI (HTML/CSS/JS) with AppState + DOMBatcher patterns. Use when touching timeline structure, steps styling, auto-scroll, or Step Details interactions.
---

# Frontend Timeline Designer

## Portée
- `templates/index_new.html` (structure Timeline, Step Details, Logs overlay hook)
- `static/css/{components/steps.css, layout.css, variables.css, base.css}`
- `static/{uiUpdater.js, scrollManager.js, sequenceManager.js, stepDetailsPanel.js}`
- Ressource annexe : `resources/timeline_design_tokens.md` (variables CSS, structure HTML, hooks JS, scénarios de test visuels).

## Principes clés
1. **Structure sémantique** : `<section class="workflow-pipeline">`, `.pipeline-timeline[role=list]`, `.timeline-step[role=listitem]` avec spine/nœud/connecteur.
2. **Compatibilité JS** : Conserver IDs (`#step-{{ step_key }}`) et classes (`.step`, `.run-button`, `.specific-log-button`).
3. **AppState immuable** : Toute mise à jour via `AppState.setState()`. Les consommateurs utilisent `subscribeToProperty`.
4. **DOMBatcher** : `DOMBatcher.scheduleUpdate()` pour chaque mutation DOM.
5. **Accessibility** : `aria-live="polite"` pour statuts, `aside` Step Details avec focus trap/restore, support `prefers-reduced-motion`.
6. **Auto-scroll** : Utiliser `scrollManager.scrollToActiveStep()` qui calcule `calculateOptimalScrollPosition()` (respect topbar fixe). Pas de `scrollIntoView()` brut.

## Workflow Modifs Timeline
1. **Analyser le besoin** (phase, layout, state).
2. **Mettre à jour HTML** : ajuster la boucle Jinja en maintenant les attributs data (`data-step-key`, `data-status`).
3. **CSS** : utiliser les variables `--timeline-*` (voir `static/css/variables.css`). Ajouter animations via `color-mix()` et `transition` paramétrées (`--motion-duration-fast`, etc.).
4. **JS** : mettre à jour `uiUpdater.js` pour refléter les nouveaux champs (ex: badges, progress). Utiliser `DOMUpdateUtils.escapeHtml()` pour texte.
5. **Tests** : lancer `npm run test:frontend` (couvre `test_step_details_panel.mjs`, `test_timeline_logs_phase2.mjs`).

## Step Details Panel
- Contrôlé par `AppState` (`stepDetailsPanel.js`).
- Interaction clavier : Enter/Espace ouvre, Escape ferme, focus trap.
- Ferme automatiquement quand logs overlay s’ouvre.

## Auto-scroll & Sequences
- `sequenceManager.js` doit appeler `scrollToActiveStep({behavior:"smooth", scrollDelay:0})`.
- `uiUpdater.js` contient un recentrage throttlé (700 ms) pendant les séquences → ne pas supprimer.
- `timeline-scroll-spacer` assure l’espace en bas (hauteur `calc(100vh - var(--topbar-height))`).

## Logs Overlay coexistence
- La timeline doit laisser l’espace pour l’overlay (Classes `.pipeline-wrapper` + `.timeline-scroll-spacer`).
- Boutons “logs spécifiques” globalisés (`templates/index_new.html`).

## Références
- `memory-bank/progress.md` (entrées Timeline Connectée Phases 1‑3).
- `docs/workflow/audits/AUDIT_UX_DASHBOARD_UNIFIED-2026-01-20.md`.
