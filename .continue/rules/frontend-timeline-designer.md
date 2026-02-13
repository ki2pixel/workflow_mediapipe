---
description: frontend-timeline-designer skill migrated from Windsurf as contextual rules
globs: 
  - "**/*.{py,js,md}"
alwaysApply: true
---

# Frontend Timeline Designer

## Portée

- `templates/index_new.html` (structure Timeline, Logs overlay hook)
- `static/css/{components/steps.css, layout.css, variables.css, base.css}`
- `static/{uiUpdater.js, scrollManager.js, sequenceManager.js}`
- Ressource annexe : `.windsurf/skills/frontend-timeline-designer/resources/timeline_design_tokens.md` (variables CSS, structure HTML, hooks JS, scénarios de test visuels).

## Principes clés

### 1. **Structure sémantique** : `<section class="workflow-pipeline">`, `.pipeline-timeline[role=list]`, `.timeline-step[role=listitem]` avec spine/nœud/connecteur.
### 2. **Compatibilité JS** : Conserver IDs (`#step-{{ step_key }}`) et classes (`.step`, `.run-button`, `.specific-log-button`).
### 3. **AppState immuable** : Toute mise à jour via `AppState.setState()`. Les consommateurs utilisent `subscribeToProperty`.
### 4. **DOMBatcher** : `DOMBatcher.scheduleUpdate()` pour chaque mutation DOM.
### 5. **Accessibility** : `aria-live="polite"` pour statuts, support `prefers-reduced-motion`.
### 6. **Auto-scroll** : Utiliser `scrollManager.scrollToActiveStep()` qui calcule `calculateOptimalScrollPosition()` (respect topbar fixe). Pas de `scrollIntoView()` brut.

## Workflow Modifs Timeline

### 1. **Analyser le besoin** (phase, layout, state).
   - Identifier si modification structurelle, stylistique ou comportementale
   - Considérer l'impact sur AppState et les abonnés

### 2. **Mettre à jour HTML** : ajuster la boucle Jinja en maintenant les attributs data (`data-step-key`, `data-status`).
   ```html
   <div class="timeline-step" 
        data-step-key="{{ step.key }}" 
        data-status="{{ step.status }}"
        role="listitem">
   ```

### 3. **CSS** : utiliser les variables `--timeline-*` (voir `static/css/variables.css`). Ajouter animations via `color-mix()` et `transition` paramétrées (`--motion-duration-fast`, etc.).
   ```css
   .timeline-step {
     --timeline-status-color: var(--color-status-{{ step.status }});
     transition: var(--motion-duration-fast) var(--motion-ease-in-out);
   }
   ```

### 4. **JS** : respecter les patterns DOMBatcher + AppState
   ```javascript
   // Mise à jour avec DOMBatcher
   domBatcher.scheduleUpdate(() => {
     const stepElement = document.getElementById(`step-${stepKey}`);
     if (stepElement) {
       stepElement.setAttribute('data-status', newStatus);
     }
   });
   
   // Notification AppState
   AppState.setState({
     steps: {
       ...AppState.state.steps,
       [stepKey]: {
         ...AppState.state.steps[stepKey],
         status: newStatus
       }
     }
   });
   ```

## Composants Timeline

### Structure HTML de base
```html
<section class="workflow-pipeline" role="main">
  <div class="pipeline-timeline" role="list">
    {% for step in steps %}
    <div class="timeline-step" 
         id="step-{{ step.key }}" 
         data-step-key="{{ step.key }}" 
         data-status="{{ step.status }}"
         role="listitem"
         aria-live="polite">
      <div class="step-connector">
        <div class="step-spine"></div>
      </div>
      <div class="step-node">
        <div class="step-icon">{{ step.key }}</div>
        <div class="step-label">{{ step.name }}</div>
      </div>
      <div class="step-actions">
        <button class="run-button" onclick="runStep('{{ step.key }}')">
          {{ step.status == 'completed' ? 'Rerun' : 'Run' }}
        </button>
        <button class="specific-log-button" onclick="openLog('{{ step.key }}')">
          Logs
        </button>
      </div>
    </div>
    {% endfor %}
  </div>
</section>
```

### CSS Variables
```css
:root {
  --timeline-step-width: 200px;
  --timeline-step-height: 80px;
  --timeline-connector-width: 2px;
  --timeline-spine-length: 20px;
  
  --color-status-pending: #6b7280;
  --color-status-running: #3b82f6;
  --color-status-completed: #10b981;
  --color-status-error: #ef4444;
  
  --motion-duration-fast: 0.2s;
  --motion-duration-normal: 0.3s;
  --motion-ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
}
```

## Patterns Avancés

### Auto-scroll Intelligente
```javascript
// scrollManager.js
class ScrollManager {
  static scrollToActiveStep(stepKey) {
    const activeStepElement = document.getElementById(`step-${stepKey}`);
    if (!activeStepElement) return;
    
    const timeline = document.querySelector('.pipeline-timeline');
    const timelineRect = timeline.getBoundingClientRect();
    const stepRect = activeStepElement.getBoundingClientRect();
    
    // Calcul position optimale avec topbar fixe
    const optimalPosition = this.calculateOptimalScrollPosition(stepRect, timelineRect);
    
    window.scrollTo({
      top: optimalPosition,
      behavior: 'smooth'
    });
  }
  
  static calculateOptimalScrollPosition(stepRect, timelineRect) {
    const scrollTop = window.pageYOffset;
    const topbarHeight = 60; // Ajuster selon hauteur topbar
    
    // Centrer l'élément dans la vue
    const elementCenter = stepRect.top + stepRect.height / 2;
    const viewportCenter = scrollTop + window.innerHeight / 2;
    
    return scrollTop + (elementCenter - viewportCenter);
  }
}
```

### Mise à Jour Conditionnelle
```javascript
// uiUpdater.js
class UIUpdater {
  static updateStepStatus(stepKey, newStatus) {
    domBatcher.scheduleUpdate(() => {
      const stepElement = document.getElementById(`step-${stepKey}`);
      if (stepElement) {
        // Mise à jour attributs
        stepElement.setAttribute('data-status', newStatus);
        stepElement.setAttribute('aria-live', 'polite');
        
        // Mise à jour classes CSS
        stepElement.classList.remove('status-pending', 'status-running', 'status-completed', 'status-error');
        stepElement.classList.add(`status-${newStatus}`);
        
        // Mise à jour texte bouton
        const runButton = stepElement.querySelector('.run-button');
        if (runButton) {
          runButton.textContent = newStatus === 'completed' ? 'Rerun' : 'Run';
        }
      }
    });
    
    // Notification AppState
    AppState.setState({
      steps: {
        ...AppState.state.steps,
        [stepKey]: {
          ...AppState.state.steps[stepKey],
          status: newStatus
        }
      }
    });
  }
}
```

## Tests Visuels

### Scénarios de Test
1. **Navigation clavier** : Tab navigation entre étapes
2. **Screen reader** : Validation aria-live et labels
3. **Responsive** : Adaptation mobile/tablette
4. **Performance** : Vérifier DOMBatcher batching

### Validation Checklist
- [ ] Structure HTML sémantique respectée
- [ ] Attributs ARIA présents et corrects
- [ ] Variables CSS utilisées pour cohérence
- [ ] DOMBatcher utilisé pour toutes mutations
- [ ] AppState immuable respecté
- [ ] Auto-scroll fonctionnel
- [ ] Compatibilité navigateurs testée

Utilisez ce prompt en tapant `/frontend-timeline-designer` dans Continue.
