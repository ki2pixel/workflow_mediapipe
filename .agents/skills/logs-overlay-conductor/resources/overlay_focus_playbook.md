# Logs Overlay — Focus & Auto-open Playbook

## 1. Scénarios à valider
| Cas | Étapes | Résultat attendu |
| --- | --- | --- |
| Auto-open actif | Préférence `AppState.getAutoOpenLogOverlay()` = true, lancer STEP1 | Overlay s’ouvre automatiquement, header affiche l’étape courante, Step Details se ferme |
| Auto-open désactivé | Basculer toggle Settings | Aucun déclenchement auto. Ouverture manuelle via bouton fixe `Logs` fonctionne |
| Specific Log buttons | Cliquer bouton `logs spécifiques` d’une step | Header met à jour `logPanel.source = 'specific'`, focus reste dans l’overlay |
| Focus trap | Tab circulaire dans overlay | Focus reste confiné, Escape ferme overlay et rend le focus au déclencheur |
| Mobile narrow | Viewport 375px | Overlay utilise largeur réduite, bouton fermer accessible |

## 2. Commandes utiles
```bash
npm run test:frontend -- --grep "logs overlay"
```
- Couvre `tests/frontend/test_timeline_logs_phase2.mjs`.

## 3. Checklist manuelle
1. `localStorage.getItem('AUTO_OPEN_LOGS_PREF')` reflète le toggle Settings.
2. `AppState.subscribeToProperty(['logPanel', 'isOpen'])` déclenche `popupManager` (voir console pour warnings focus).
3. Inspecter DOM : `.logs-overlay` doit porter `aria-modal="true" role="dialog"` + `data-log-source`.
4. Vérifier `DOMUpdateUtils.escapeHtml()` dans `uiUpdater.parseAndStyleLogContent()`.
5. S’assurer que `openLogPanelUI` ferme `stepDetailsPanel` (`StepDetailsController.closeIfOpen()`).

## 4. Débogage rapide
- Overlay figée → vérifier `DOMBatcher` (pas d’updates en dehors). Forcer via `window.__debugOpenLogsPanel()` si helper dispo.
- Header vide → `AppState.getActiveStepKey()` renvoie `null` → confirmer que `WorkflowState` push les statuts via polling.
- Boutons spécifiques manquants → vérifier que `templates/index_new.html` contient le conteneur global (Phase 2) et que `uiUpdater` le remplit après fetch.
