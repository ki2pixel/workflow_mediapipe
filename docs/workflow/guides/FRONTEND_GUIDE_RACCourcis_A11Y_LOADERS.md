# Frontend: Raccourcis, A11y, Loaders – Guide rapide

## Raccourcis clavier (dans `static/main.js`)
- 1–7 → Scroll vers `STEP1..STEP7`.
- L → Ouvrir/fermer le panneau Logs (focus sur le titre).
- S → Ouvrir Stats (focus sur le titre).
- R → Ouvrir Rapports (focus sur le titre).
- D → Ouvrir Diagnostics.
- U → Ouvrir Smart Upload.
- Échap → Fermer modales/panneaux ouverts.
- Throttle: `PerformanceOptimizer.throttle('kb_shortcuts', ..., 120ms)`.

## Accessibilité (A11y)
- Focus visible universel (boutons d’action, widgets, modales).
- Focus management: après ouverture via raccourci, focus sur le titre/zone principale.
- `aria-live="polite"` pour:
  - `#global-progress-text`
  - logs principaux et spécifiques
- Reduced Motion: `prefers-reduced-motion` neutralise animations (modales, cartes, etc.).

## Loaders unifiés
- Helper: `fetchWithLoadingState(url, options, buttonElOrId)` (dans `static/apiService.js`).
- Ajout automatique de `data-loading="true"` + `disabled` sur le bouton pendant le fetch.
- Styles spinner: `static/css/components/widgets.css` + `static/css/utils/animations.css`.
- Intégrations notables:
  - Diagnostics, Smart Upload
  - Lancer/Annuler d’étapes (run/cancel)
  - Logs spécifiques (bouton de log passé à l’API)

## Micro-interactions (confort visuel)
- Cartes d’étapes:
  - Effet “breathing” pour l’étape active/en cours.
  - Halo discret pour les autres cartes quand « any step running ».
  - Survol (hover) subtile: élévation + accent d’icône; neutralisé si reduced motion.
- Téléchargements Locaux: affichage/masquage immédiat (sans animation) pour stabilité.

## Bonnes pratiques (MANDATORY)
- XSS: ne jamais insérer de HTML non échappé; utiliser `DOMUpdateUtils.escapeHtml` pour le texte dynamique.
- Perf: privilégier `transform/opacity`, utiliser `DOMBatcher.scheduleUpdate()` pour grouper les mises à jour fréquentes.
- Architecture: routes minces; logique métier dans `services/`; état partagé via `AppState`.

## Références
- JS: `static/main.js`, `static/apiService.js`, `static/uiUpdater.js`
- CSS: `static/css/components/steps.css`, `static/css/components/widgets.css`, `static/css/components/popups.css`, `static/css/utils/animations.css`
- HTML: `templates/index_new.html`

---

## Optimisations Performance v4.2

### DOMBatcher & Mises à Jour Groupées

**Principe** : Réduire la pression sur le DOM en groupant les mises à jour fréquentes.

```javascript
// Utilisation de DOMBatcher pour les mises à jour multiples
domBatcher.scheduleUpdate(() => {
    // Toutes les modifications DOM sont groupées
    updateStepCards();
    updateProgressBar();
    refreshLogPanel();
});
```

**Bénéfices** :
- Réduction des reflows/repaints
- Meilleure gestion du garbage collector
- UI plus responsive pendant les opérations intensives

### Performance vs Accessibility

**Approche équilibrée** : Maintenir l'accessibilité tout en optimisant les performances.

```javascript
// parseAndStyleLogContent() - Optimisé ET sécurisé
function parseAndStyleLogContent(content) {
    // 1. Sécurité XSS OBLIGATOIRE
    const escapedContent = DOMUpdateUtils.escapeHtml(content);
    
    // 2. Optimisations performance
    const patterns = {
        error: /\[ERROR\]|\[ERREUR\]/gi,
        warning: /\[WARNING\]|\[AVERTISSEMENT\]/gi
    };
    
    // 3. Traitement linéaire optimisé
    return escapedContent
        .replace(/\n/g, '<br>')
        .replace(patterns.error, '<span class="log-error">$&</span>')
        .trim();
}
```

**Points clés** :
- `textContent` privilégié sur `innerHTML` quand possible
- `DOMUpdateUtils.escapeHtml()` obligatoire pour tout contenu dynamique
- Animations respectant `prefers-reduced-motion`

### Métriques & Monitoring

**Indicateurs de performance** :
- Temps de réponse UI < 100ms pour les interactions
- Utilisation mémoire stable (pas de leaks)
- Garbage collection efficace (moins de 5ms par cycle)

**Outils de mesure** :
- `PerformanceMonitor` dans `static/utils/PerformanceMonitor.js`
- `measure_api()` pour les endpoints backend
- Profiling navigateur pour les goulots d'étranglement

### Recommandations Développement

1. **Utiliser DOMBatcher** pour toute mise à jour multiple
2. **Privilégier textContent** quand le markup n'est pas nécessaire
3. **Échapper systématiquement** avec `DOMUpdateUtils.escapeHtml()`
4. **Tester avec reduced motion** pour l'accessibilité
5. **Monitorer les métriques** pendant le développement
