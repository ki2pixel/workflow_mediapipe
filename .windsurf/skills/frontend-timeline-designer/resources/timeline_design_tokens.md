# Timeline Design Tokens & Hooks

> Référence rapide pour modifier la Timeline connectée sans casser les phases 1‑3.

## 1. Variables CSS clés (`static/css/variables.css`)
| Variable | Description | Notes |
| --- | --- | --- |
| `--timeline-spine-width` | Largeur de la ligne verticale principale | Ajuster avec précaution pour conserver l’alignement des nœuds |
| `--timeline-node-size` | Diamètre des nœuds | Couplé aux animations `@keyframes pulse-node` |
| `--timeline-connector-gap` | Espace entre cartes | Impacte le scroll auto (voir spacer) |
| `--status-running-rgb` etc. | Palette RGB pour `color-mix()` | Utilisées pour badges et connecteurs |
| `--motion-duration-fast` / `-medium` / `-slow` | Durées transitions | Réutiliser pour micro-interactions cohérentes |

## 2. Structure HTML (rappel)
```html
<section class="workflow-pipeline">
  <div class="pipeline-timeline" role="list">
    <div id="step-{{ step_key }}" class="timeline-step step" role="listitem" data-step-key="{{ step_key }}" data-status="{{ state }}">
      <div class="timeline-rail" aria-hidden="true">
        <div class="timeline-node"></div>
        <div class="timeline-connector"></div>
      </div>
      <div class="timeline-card">...</div>
    </div>
  </div>
</section>
```
- Garder `data-step-key` + `data-status` pour `uiUpdater.js`.
- `timeline-scroll-spacer` suit la section pour gérer la fin de page.

## 3. JS touchpoints
| Module | Responsabilité | Hooks |
| --- | --- | --- |
| `uiUpdater.js` | Badges statut, progress text, auto-centering throttlé | `updateTimelineStep()` doit utiliser `DOMBatcher` |
| `scrollManager.js` | Calcul `calculateOptimalScrollPosition()` | Toute nouvelle hauteur topbar → mettre à jour `TOPBAR_OFFSET_PX` |
| `sequenceManager.js` | Scroll lors des séquences | Toujours appeler `scrollToActiveStep({ behavior: 'smooth', scrollDelay: 0 })` |
| `stepDetailsPanel.js` | Synchronisation Step Details | Fermer panel si step n’existe plus (`domElements.getStepElement`) |

## 4. Scénarios de test visuels
1. **Auto-scroll** : lancer une séquence et vérifier que l’étape active reste centrée (Chrome + Firefox).
2. **Responsive** : Viewport 1280px, 1024px, 768px. Vérifier que la spine reste alignée et que Step Details/Logs peuvent coexister.
3. **Prefers Reduced Motion** : `chrome://flags/#prefers-reduced-motion` → transitions réduites.
4. **Keyboard Nav** : Tab jusqu’aux boutons d’une carte, Enter/Espace déclenchent les actions et Step Details.

## 5. Diff rapide avant PR
```bash
git diff --stat templates/index_new.html static/css/components/steps.css static/uiUpdater.js
```
- Relecture obligatoire de `docs/workflow/audits/AUDIT_UX_DASHBOARD_UNIFIED-2026-01-20.md` pour rester aligné avec la phase courante.
