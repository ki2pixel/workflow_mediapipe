---
name: logs-overlay-conductor
description: Operate and refine the unified Logs Overlay (Phases 2-4). Use when adjusting overlay layout, auto-open preferences, header context, or focus management tied to Timeline.
---

# Logs Overlay Conductor

## Composants clés
- HTML : `templates/index_new.html` (overlay structure, header contextuel, boutons globaux "logs spécifiques", toggle Settings).
- CSS : `static/css/components/logs.css`, `static/css/layout.css` (lightbox centrée, responsive, animations).
- JS : `static/uiUpdater.js`, `static/eventHandlers.js`, `static/popupManager.js`, `static/sequenceManager.js`.
- Tests : `tests/frontend/test_timeline_logs_phase2.mjs`.
- Ressource : `resources/overlay_focus_playbook.md` (scénarios auto-open, focus trap, commandes npm/diagnostics).

## Principes UX
1. Overlay centrée (Phase 4 option A) avec focus trap complet.
2. Header contextuel affiche étape active, statut, timer (alimenté via `AppState` + `WorkflowState`).
3. Boutons "logs spécifiques" regroupés dans un conteneur global, accessibles clavier.
4. Auto-ouverture configurable : toggle "📟 Auto-ouverture des logs" (Settings). `openLogPanelUI()` respecte `AppState.getAutoOpenLogOverlay()`.

## Checklist implémentation
1. **Structure** : maintenir `data-log-type`, `aria-modal="true"`, `role="dialog"`. Ajouter `aria-live` uniquement si nécessaire.
2. **Styles** : utiliser variables `--panel-bg`, `--motion-duration-*`. Mobile friendly (`max-width: 640px`, `height: min(90vh, 720px)`).
3. **State** : `AppState.setState({ logPanel: { isOpen: true, source: 'auto' } })`. Pas de mutation directe.
4. **Focus** : `popupManager` gère focus trap/restauration. Ajouter nouveaux éléments aux hooks existants.
5. **Sécurité & DOM** : Toujours utiliser `DOMUpdateUtils.escapeHtml()` avant d'insérer du contenu dans l'overlay. Jamais d'`innerHTML` direct. Le code doit respecter les standards ES11 (complexité réduite, résorption SonarCloud).
6. **Polling** : Les requêtes périodiques liées aux logs doivent passer par `PollingManager` exclusivement. Le remote polling est interdit.
7. **Auto-open toggle** : stocker dans `localStorage` (`AUTO_OPEN_LOGS_PREF`). `Settings` checkbox synchronisée via `eventHandlers.js` + `uiUpdater.js`.
8. **Tests** : `npm run test:frontend` doit réussir (`test_timeline_logs_phase2.mjs` vérifie header/boutons/auto-open).

## Diagnostics rapides
- Overlay ne s'ouvre pas → vérifier `AppState.getAutoOpenLogOverlay()` (toggle). Forcer via bouton `Logs`.
- Header vide → confirmer que `uiUpdater._updateLogPanelHeader()` reçoit `activeStep`. Revoir `WorkflowState` payload.
- Focus trap cassé → inspecter `popupManager.js` (hooks `onOpenLogPanel`, `onCloseLogPanel`). Vérifier `DOMUpdateUtils.escapeHtml()` sur contenu logs.

## Références
- `memory-bank/progress.md` (Phases Logs Overlay 2-4, toggle auto-open).

**Locking Instruction:** NE PAS essayer de lire les fichiers de la memory-bank via le filesystem (outil read_text_file). Utilise EXCLUSIVEMENT les outils du serveur MCP 'fast-filesystem' (outils fast_*) pour lire ou écrire dans la Memory Bank avec des chemins absolus.
