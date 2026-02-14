---
description: logs-overlay-conductor skill migrated from Windsurf as contextual rules
alwaysApply: false
---

# Logs Overlay Conductor

## Composants clés

- HTML : `templates/index_new.html` (overlay structure, header contextuel, boutons globaux "logs spécifiques", toggle Settings).
- CSS : `static/css/components/logs.css`, `static/css/layout.css` (lightbox centrée, responsive, animations).
- JS : `static/uiUpdater.js`, `static/eventHandlers.js`, `static/popupManager.js`, `static/sequenceManager.js`.
- Tests : `tests/frontend/test_timeline_logs_phase2.mjs`.
- Ressource : `resources/overlay_focus_playbook.md` (scénarios auto-open, focus trap, commandes npm/diagnostics).

## Principes UX

### 1. Overlay centrée (Phase 4 option A) avec focus trap complet.
### 2. Header contextuel affiche étape active, statut, timer (alimenté via `AppState` + `WorkflowState`).
### 3. Boutons "logs spécifiques" regroupés dans un conteneur global, accessibles clavier.
### 4. Auto-ouverture configurable : toggle "📟 Auto-ouverture des logs" (Settings). `openLogPanelUI()` respecte `AppState.getAutoOpenLogOverlay()`.

## Structure HTML de l'Overlay

```html
<div class="logs-overlay" 
     id="logs-overlay" 
     role="dialog" 
     aria-modal="true" 
     aria-labelledby="logs-header"
     data-log-type="{{ current_log_type or 'all' }}">
  
  <!-- Header contextuel -->
  <div class="logs-header" id="logs-header">
    <div class="logs-context">
      <span class="step-indicator" data-step="{{ active_step }}">
        Étape: {{ active_step }}
      </span>
      <span class="status-indicator" data-status="{{ step_status }}">
        Statut: {{ step_status }}
      </span>
      <span class="timer" id="logs-timer">
        {{ elapsed_time }}
      </span>
    </div>
    
    <div class="logs-controls">
      <button class="close-button" onclick="closeLogsOverlay()" aria-label="Fermer les logs">
        ✕
      </button>
    </div>
  </div>
  
  <!-- Conteneur de logs -->
  <div class="logs-content" role="document">
    <div class="specific-logs-buttons">
      <button onclick="showLogType('step1')" class="log-type-button">STEP1</button>
      <button onclick="showLogType('step2')" class="log-type-button">STEP2</button>
      <button onclick="showLogType('step3')" class="log-type-button">STEP3</button>
      <button onclick="showLogType('step4')" class="log-type-button">STEP4</button>
      <button onclick="showLogType('step5')" class="log-type-button">STEP5</button>
      <button onclick="showLogType('step6')" class="log-type-button">STEP6</button>
      <button onclick="showLogType('step7')" class="log-type-button">STEP7</button>
      <button onclick="showLogType('step8')" class="log-type-button">STEP8</button>
      <button onclick="showLogType('all')" class="log-type-button active">Tous</button>
    </div>
    
    <div class="logs-display" id="logs-display">
      <!-- Contenu des logs inséré ici -->
    </div>
  </div>
</div>
```

## CSS Variables et Styles

```css
:root {
  --overlay-bg: rgba(0, 0, 0, 0.95);
  --panel-bg: #ffffff;
  --header-height: 60px;
  --control-height: 40px;
  
  --motion-duration-fast: 0.2s;
  --motion-duration-normal: 0.3s;
  --motion-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
}

.logs-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--overlay-bg);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  
  /* Mobile responsive */
  max-width: min(90vw, 1200px);
  max-height: min(90vh, 800px);
  margin: auto;
}

.logs-header {
  height: var(--header-height);
  background: var(--panel-bg);
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.logs-content {
  flex: 1;
  overflow-y: auto;
  background: var(--panel-bg);
}
```

## Patterns JavaScript

### Focus Trap Management
```javascript
// popupManager.js
class PopupManager {
  static focusTrap = null;
  
  static createFocusTrap(element) {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    element.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    });
  }
  
  static removeFocusTrap() {
    if (this.focusTrap) {
      this.focusTrap.removeEventListener('keydown');
      this.focusTrap = null;
    }
  }
}
```

### Auto-ouverture Intelligente
```javascript
// uiUpdater.js
class UIUpdater {
  static autoOpenLogOverlay() {
    const shouldAutoOpen = AppState.getAutoOpenLogOverlay();
    const activeStep = AppState.getActiveStep();
    
    if (shouldAutoOpen && activeStep && activeStep.status === 'running') {
      this.openLogPanelUI({
        source: 'auto',
        logType: activeStep.key
      });
    }
  }
  
  static openLogPanelUI(options = {}) {
    domBatcher.scheduleUpdate(() => {
      const overlay = document.getElementById('logs-overlay');
      const source = options.source || 'manual';
      const logType = options.logType || 'all';
      
      // Mise à jour attributs
      overlay.setAttribute('data-log-type', logType);
      overlay.setAttribute('data-source', source);
      
      // Focus trap
      PopupManager.createFocusTrap(overlay);
      
      // Notification AppState
      AppState.setState({
        logPanel: {
          isOpen: true,
          source: source,
          logType: logType
        }
      });
      
      // Focus sur contenu logs
      document.getElementById('logs-display').focus();
    });
  }
}
```

### Synchronisation Timeline ↔ Overlay
```javascript
// Synchronisation automatique
AppState.subscribeToProperty(['activeStep'], (newStep, oldStep) => {
  if (newStep && newStep.key !== oldStep?.key) {
    UIUpdater.updateLogsHeader(newStep);
  }
});

AppState.subscribeToProperty(['logPanel'], (logPanel) => {
  if (logPanel.isOpen) {
    TimelineManager.highlightActiveStep(logPanel.logType);
  } else {
    TimelineManager.clearHighlight();
  }
});
```

## Tests et Validation

### Scénarios de Test
1. **Navigation clavier** : Tab/Shift+Tab dans l'overlay
2. **Focus trap** : Vérifier confinement du focus
3. **Auto-ouverture** : Test déclenchement automatique
4. **Responsive** : Adaptation mobile/tablette
5. **Performance** : Vérifier DOMBatcher batching

### Checklist d'Implémentation
- [ ] Structure HTML sémantique respectée
- [ ] Attributs ARIA présents et corrects
- [ ] Focus trap fonctionnel
- [ ] Auto-ouverture respecte les préférences
- [ ] Synchronisation Timeline/Overlay active
- [ ] Styles responsive appliqués
- [ ] DOMBatcher utilisé pour toutes mutations

Utilisez ce prompt en tapant `/logs-overlay-conductor` dans Continue.
