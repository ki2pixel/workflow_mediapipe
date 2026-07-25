# Audit Frontend — Workflow MediaPipe

**Date** : 2026-07-25
**Périmètre** : `templates/index_new.html`, `static/*.js`, `static/css/**`, `tests/frontend/**`
**Méthodologie** : Revue de code exhaustive, exécution des tests, analyse statique

---

## Synthèse

**Note globale : 7/10** — Bonne qualité architecturale avec des choix techniques modernes, mais plusieurs axes d'amélioration en sécurité, testabilité et maintenabilité.

| Domaine | Score | Remarque |
|---|---|---|
| Architecture & Patterns | 8/10 | State immutable, batching DOM, polling centralisé |
| Qualité de code | 7/10 | Modules propres mais doublons, code mort, globals |
| Performance | 7/10 | Optimisations présentes mais polling lent, pas de lazy loading |
| Sécurité | 6/10 | CSP restrictif, échappement XSS, mais CSRF absent, SRI absent |
| Accessibilité | 7/10 | ARIA, skip-link, focus trap, mais pas de prefers-reduced-motion |
| Tests | 5/10 | Couverture étroite, pas de tests E2E ou composants |

---

## 1. Architecture

### 1.1 Stack technique

- **24 modules JS natifs** (ES modules, pas de bundler) — ~11 000 lignes
- **16 feuilles CSS** avec Custom Properties et 6 thèmes
- **1 template Jinja2/Flask** (`index_new.html`, ~250 lignes)
- **9 fichiers de test** Node ESM (pas de runner navigateur)
- **Pas de framework** — vanilla JS avec state management maison

### 1.2 Points forts

- **AppState** (`state/AppState.js`) : state immutable avec `structuredClone`, `_mergeDeep`, propriétés accessibles par chemin dot-notation, persistence localStorage, et système d'abonnement par propriété (`subscribeToProperty`).
- **DOMBatcher** (`utils/DOMBatcher.js`) : regroupe les mutations DOM dans une seule `requestAnimationFrame` par cycle, avec priorités.
- **DOMDiff** (`utils/DOMDiff.js`) : morphing DOM minimal avec support d'éléments keyed (`data-key`).
- **PollingManager** (`utils/PollingManager.js`) : gestion centralisée des intervals avec nettoyage automatique, backoff, et événements `beforeunload`.
- **ErrorHandler** (`utils/ErrorHandler.js`) : backoff exponentiel, dédoublonnage de notifications, dispatch d'événements customs.
- **WorkerManager** (`utils/WorkerManager.js`) : délégation du parsing de logs à un Web Worker avec canalisation pour éviter les race conditions.
- **Séparation des responsabilités** respectée : routes minces, logique dans `services/`, UI dans `static/`.

### 1.3 Points faibles

- **Dépendances circulaires potentielles** : `uiUpdater.js` ré-exporte `timerManager` et `downloadsListManager` ; `eventHandlers.js` importe `soundManager` en lazy + eager.
- **Double API state** : `state.js` (wrapper legacy) duplique des fonctions de `state/AppState.js`. Deux façons de faire la même chose (`addStepTimer` vs `appState.setState`).
- **Globals abusifs** : 7 variables exposées sur `globalThis` (`showNotification`, `pollingManager`, `errorHandler`, `performanceMonitor`, `appState`, `domBatcher`, `themeManager`).
- **Pas de code splitting / lazy loading** — les 24 modules sont importés eager depuis `main.js`.
- **Étapes hardcodées** : `REMOTE_SEQUENCE_STEP_KEYS` et `defaultSequenceableStepsKeys` dupliqués dans `state.js` et `constants.js`.

---

## 2. Performance

### 2.1 Points forts

- **Batching DOM** via `requestAnimationFrame` (évite les layout thrashing).
- **Web Worker** pour le parsing de logs (libère le thread principal).
- **Debounce/throttle** dans `PerformanceOptimizer`.
- **DOMDiff** avec clés (`data-key`) pour éviter les recréations inutiles de nœuds.
- **PerformanceMonitor** avec `PerformanceObserver` pour les long tasks et `MutationObserver`.

### 2.2 Points faibles

- **`POLLING_INTERVAL` à 2000ms** (constants.js:1) : très lent pour un dashboard temps réel. Le commentaire dit "augmenté pour réduire le logging", mais le problème était le volume de logs console, pas la fréquence de polling.
- **Pas de lazy loading** — tous les modules sont chargés au `DOMContentLoaded`.
- **Pas de `loading="lazy"` sur les ressources** (pas d'images critiques mais le pattern est absent).
- **`PerformanceMonitor` monkey-patch `globalThis.fetch`** (ligne 151) : invasif, peut casser d'autres libs ou WebSocket.
- **Cache buster `?v={{ cache_buster }}`** sur toutes les ressources CSS/JS : empêche tout cache navigateur, chaque rechargement re-télécharge tout.

### 2.3 Données chiffrées

- **11 036 lignes** de code frontend au total
- **Tests existants** : 9 fichiers, tous passent ✓
- **Taille du state initial** : ~500 octets JSON

---

## 3. Sécurité

### 3.1 Points forts

- **Content-Security-Policy** restrictif : `default-src 'self'; script-src 'self'; object-src 'none'`.
- **Échappement XSS systématique** : `DOMUpdateUtils.escapeHtml()` utilisé sur toutes les données dynamiques insérées dans le DOM. Le Web Worker a sa propre fonction `escapeHtml()` sans dépendance DOM.
- **Worker token** : token d'authentification interne injecté via meta tag pour les appels API.
- **Validation de stepKey** : pattern `/^[A-Za-z0-9_-]+$/` dans `domElements.js` avant toute requête DOM.
- **Focus trap** dans les popups (`popupManager.js`) avec restauration du focus à la fermeture.
- **sanitizeExternalUrl()** dans `csvWorkflowPrompt.js` : vérifie le protocole avant d'ouvrir un lien externe.

### 3.2 Points faibles

- **`style-src 'unsafe-inline'`** dans la CSP : nécessaire à cause des styles inline Jinja2 mais réduit la protection XSS.
- **Pas de CSRF token** dans les requêtes fetch (HEADER `X-CSRF-Token` absent).
- **Pas de Subresource Integrity (SRI)** sur les scripts chargés.
- **Token worker exposé** dans le DOM via `<meta name="worker-token">` — lisible par tout script.
- **Ouverture de liens externes** via `globalThis.open()` sans `noopener` explicite dans tous les cas (le `rel="noopener noreferrer"` est sur le `<a>` caché mais pas sur `window.open`).
- **Pas de `X-Content-Type-Options: nosniff`** ni `Referrer-Policy` dans le template.

---

## 4. Accessibilité

### 4.1 Points forts

- **Skip link** : `<a href="#workflow-steps" class="skip-link">` présent.
- **Attributs ARIA** : `aria-live="polite"`, `aria-modal`, `aria-expanded`, `aria-pressed`, `role="progressbar"`, `aria-valuenow/min/max`, `aria-label`, `aria-controls`, `role="dialog"`, `role="group"`, `role="region"`, `role="list"`, `role="listitem"`.
- **Focus management** : restauration du focus après fermeture de popup, `tabindex="-1"` temporaire pour `safeFocusAndHighlight`.
- **`lang="fr"`** sur l'élément `<html>`.
- **Touch target minimum** : variable CSS `--touch-target-min: 44px`.
- **Raccourci clavier** pour les settings (touche `S`).

### 4.2 Points faibles

- **Pas de `prefers-reduced-motion`** : les variables d'animation existent (`--motion-duration-*`) mais aucune media query ne les désactive.
- **Pas de `prefers-color-scheme`** : le thème ne suit pas la préférence système.
- **Pas de `prefers-contrast`** / mode high contrast.
- **Indicateurs de statut purement colorés** : les badges rouge/vert n'ont pas d'icône ou de texte alternatif pour les daltoniens.
- **Raccourci `S`** intercepte TOUS les appuis sur S, même en dehors du contexte settings — conflit avec la recherche navigateur (`Ctrl+F` puis taper).
- **Pas de `aria-describedby`** sur les éléments complexes comme les barres de progression.
- **Logs dans `aria-live="polite"`** : pour des mises à jour fréquentes (polling 2000ms), `aria-live` peut surcharger les lecteurs d'écran. Mieux vaudrait `aria-atomic="false"` ou un mode silencieux.

---

## 5. Qualité de code

### 5.1 Points forts

- **Convention de nommage cohérente** : modules en camelCase, fonctions en anglais, logs et UI en français.
- **JSDoc** partiel sur les fonctions principales.
- **Gestion d'erreur défensive** : try/catch sur pratiquement toutes les fonctions async, fallbacks.
- **Pas de `any` / pas de TypeScript** mais le code vanilla est propre et lisible.
- **`console.debug`** pour les logs non-critiques, `console.warn`/`console.error` pour les vrais problèmes.

### 5.2 Points faibles

- **Code mort** : `uiUpdater.js:378` — return statement suivi de commentaire "Code inaccessible supprimé" avec du code mort restant.
- **Import dupliqué** : `main.js:22` importe `fetchWithLoadingState` déjà importé ligne 2 via `import * as api`.
- **Fonction `parseAndStyleLogContent` dupliquée** dans `uiUpdater.js` et `parseWorker.js` (logique identique, risque de drift).
- **Logique `isDropboxLikeDownload` dupliquée** : `csvWorkflowPrompt.js` a des helpers `isDropboxUrl`, `isDropboxProxyUrl`, `isDropboxLikeDownload` qui sont appelés plusieurs fois avec des vérifications redondantes.
- **Pas de constantes partagées** pour les statuts (`'running'`, `'completed'`, etc.) — chaînes magiques dispersées.
- **Bloc HTML mal formé** : `index_new.html:80` a une `</div>` orpheline (`</div>` après un bloc settings vide).
- **`formatProgressText`** dans `uiUpdater.js` et `formatElapsedTime` dans `utils.js` : fonctions utilitaires non regroupées.
- **Pas de gestion cohérente des timeouts** : certains `setTimeout` sans cleanup (risque de fuite si le composant est détruit).

---

## 6. Tests

### 6.1 État actuel

- **9 fichiers de test**, tous Node ESM (pas de navigateur).
- **Résultat** : tous les tests passent ✓.
- **Tests présents** : `DOMDiff`, `PollingManager` (backoff, timeouts), `DOMUpdateUtils.escapeHtml`, `DOMBatcher` (performance, update dedup), focus trap, timeline logs phase 2, auto-scroll, state persistence, `WorkerManager` fallback.

### 6.2 Lacunes

- **Aucun test E2E** (Playwright, Cypress, Selenium).
- **Aucun test composant** (render de step card, interaction boutons).
- **Modules non testés** : `apiService` (runStepAPI, cancelStepAPI, polling), `uiUpdater` (updateStepCardUI, closeLogPanelUI), `eventHandlers`, `sequenceManager`, `popupManager`, `soundManager`, `csvDownloadMonitor`, `csvWorkflowPrompt`.
- **Pas de test de régression visuelle**.
- **Pas de test d'accessibilité automatisé** (axe-core, pa11y).
- **Pas de test de performance** (Lighthouse CI, Web Vitals).

---

## 7. CSS & Design System

### 7.1 Points forts

- **Design system cohérent** : Custom Properties pour couleurs, espacements, durées d'animation, tailles.
- **6 thèmes** : `dark-pro`, `light-mode`, `pastel-zen`, `neon-cyberpunk`, `forest-night`, `ocean-depth`.
- **Variables de mouvement** : `--motion-duration-fast/medium/slow`, `--motion-ease-standard/emphasized/out-expo/in-expo`.
- **Séparation CSS** : variables, base, layout, themes, components (8 fichiers), utils, features.
- **Responsive** : fichier `features/responsive.css` et variables de layout.

### 7.2 Points faibles

- **Pas de reset/normalize explicite** (base.css fait le minimum).
- **Pas de grid layout** — tout est en flexbox, pas de `display: grid` pour la mise en page principale.
- **Pas de container queries** pour les composants.
- **`!important` non documenté** — probablement présent dans certains fichiers de thème.
- **Pas de minification CSS en production**.

---

## Recommandations

### Court terme (sprint courant)

1. **Réduire `POLLING_INTERVAL` à 500ms** et supprimer les `console.debug` verbeux au lieu d'augmenter l'intervalle.
2. **Supprimer le code mort** dans `uiUpdater.js:378`.
3. **Corriger le bloc HTML orphelin** `index_new.html:80`.
4. **Supprimer l'import dupliqué** dans `main.js:22`.
5. **Ajouter `prefers-reduced-motion`** dans `base.css` :
   ```css
   @media (prefers-reduced-motion: reduce) {
     *, *::before, *::after {
       animation-duration: 0.01ms !important;
       transition-duration: 0.01ms !important;
     }
   }
   ```
6. **Ajouter `X-Content-Type-Options: nosniff`** et `Referrer-Policy: strict-origin-when-cross-origin` dans le template.

### Moyen terme (1-2 sprints)

7. **Déprécier `state.js`** — migrer toutes les fonctions vers `AppState` uniquement.
8. **Ajouter un token CSRF** dans les requêtes fetch (header `X-CSRFToken` + cookie).
9. **Implémenter SRI** sur les balises `<script>`.
10. **Ajouter `prefers-color-scheme`** pour suivre le thème système.
11. **Tests E2E avec Playwright** pour le workflow complet (run step → polling → completion → summary).
12. **Tests d'accessibilité avec axe-core** en CI.
13. **Extraire les chaînes de statut** (`'running'`, `'completed'`, etc.) en constantes partagées.

### Long terme (roadmap)

14. **i18n** : externaliser toutes les chaînes françaises.
15. **PWA** : ajouter un service worker pour le cache offline et un `manifest.json`.
16. **Lazy loading** : charger les modules non-critiques (soundManager, csvWorkflowPrompt, PerformanceMonitor) à la demande.
17. **Code splitting natif** via `import()` dynamique.
18. **Dashboard de monitoring** exposer les métriques du `PerformanceMonitor` dans l'UI.
19. **Remplacer le monkey-patch fetch** par un wrapper explicite (`apiClient`).
20. **Remplacer le cache buster** par du versionnement de build (hash dans le nom de fichier).

---

## Annexes

### A. Inventaire des fichiers

| Fichier | Lignes | Rôle |
|---|---|---|
| `main.js` | 606 | Point d'entrée, initialisation |
| `uiUpdater.js` | 807 | Rendu UI, logs, barres de progression |
| `csvWorkflowPrompt.js` | 468 | Popup post-téléchargement CSV |
| `apiService.js` | 364 | Appels API, polling |
| `utils/PollingManager.js` | 322 | Gestionnaire d'intervalles |
| `utils/ErrorHandler.js` | 345 | Gestion centralisée des erreurs |
| `utils/DOMBatcher.js` | 349 | Batching des updates DOM |
| `utils/PerformanceMonitor.js` | 547 | Monitoring de performance |
| `utils/PerformanceOptimizer.js` | 200+ | Debounce, throttle |
| `utils/DOMDiff.js` | 162 | Diffing/Morphing DOM |
| `utils/WorkerManager.js` | 142 | Web Worker orchestration |
| `state/AppState.js` | 446 | State management immutable |
| `eventHandlers.js` | 257 | Gestionnaires d'événements |
| `popupManager.js` | 189 | Gestion des popups/focus trap |
| `sequenceManager.js` | 195 | Exécution de séquences |
| `soundManager.js` | 202 | Feedback audio |
| `scrollManager.js` | 155 | Scroll automatique |
| `timerManager.js` | 93 | Timers d'étapes |
| `themeManager.js` | 185 | Thèmes (6 thèmes) |
| `csvDownloadMonitor.js` | 211 | Monitoring téléchargements CSV |
| `downloadsListManager.js` | 128 | UI liste de téléchargements |
| `domElements.js` | 135 | Références DOM lazy |
| `state.js` | 89 | Wrapper legacy (à déprécier) |
| `utils.js` | 59 | Utilitaires (notifications, temps) |
| `constants.js` | 14 | Constantes partagées |

### B. Résultats des tests

```
$ npm run test:frontend

✓ DOMDiff basic morph matching and keyed children
✓ DOMDiff attribute morphing
✓ PollingManager backoff, timeout lifecycle, pending resume cleanup
✓ DOMUpdateUtils.escapeHtml XSS safety
✓ DOMBatcher update deduplication, priority, and 16ms warning
✓ Focus trap Escape/Tab behavior and close focus restoration
✓ Timeline-Logs Phase 2
✓ Auto-scroll séquences
✓ WorkerManager fallback

Tous les tests passés ✓
```
