# 🛡️ Audit Frontend : Workflow MediaPipe

## 1. Vue d'ensemble de l'Architecture
**Stack :** Vanilla JavaScript (ES Modules), CSS3 (Variables, Grid/Flexbox), Jinja2 (HTML).
**État :** Application mature, modulaire, avec une gestion avancée de la performance (batching DOM, monitoring) et de l'état (State Management).

### ✅ Points Forts
*   **Modularité ES6 :** Excellente séparation des responsabilités (`apiService`, `uiUpdater`, `state`, `domElements`). L'utilisation de `type="module"` est moderne et propre.
*   **Performance First :** L'implémentation de `DOMBatcher.js` (utilisant `requestAnimationFrame`) et de `PerformanceMonitor.js` prouve une grande attention portée à la fluidité de l'interface.
*   **Gestion d'État Centralisée :** `AppState.js` implémente un pattern Observer/PubSub robuste, permettant de découpler la logique métier de l'interface utilisateur.
*   **Design System :** Utilisation intensive des variables CSS (`variables.css`) et gestion de thèmes (`themes.css`) incluant un mode "Cinematic".

### ⚠️ Points de Vigilance (Dette Technique)
*   **Migration AppState Terminée (21/01/2026) :** Les exports legacy de `state.js` ont été retirés au profit d’`AppState` (timers, logs, séquences, popups). Le risque de double source de vérité est désormais levé, mais la vigilance reste de mise lors des prochains ajouts de features reliant backend et AppState.
    *   *Validation :* Tests `npm run test:frontend` + `pytest tests/integration/test_step_key_validation.py` exécutés avec succès.
*   **Couplage DOM/JS Fort :** `domElements.js` exporte des références statiques par ID au chargement. Si un élément est rendu conditionnellement ou dynamiquement plus tard, la référence peut être nulle ou obsolète (bien que des getters "lazy" aient été ajoutés).

---

## 2. Analyse Détaillée

### A. Performance & Optimisation
Le frontend est très bien optimisé pour une application Vanilla.

*   **DOM Batching :** La classe `DOMUpdateBatcher` est excellente pour éviter le "Layout Thrashing" (recalculs forcés de mise en page).
*   **Polling Intelligent :** `PollingManager.js` gère les intervalles avec nettoyage automatique (`beforeunload`, `pagehide`) et backoff exponentiel en cas d'erreur. C'est rare et très bienvenu dans ce type d'app.
*   **Optimisation JS :**
    *   *Problème :* Dans `AppState.js`, la méthode `_deepClone` utilise une récursion manuelle.
    *   *Suggestion :* Utiliser `structuredClone(obj)` (natif et plus rapide dans les navigateurs modernes) pour le clonage profond.
    *   *Problème :* `_stateChanged` utilise `JSON.stringify` pour comparer les états. C'est lent pour les gros objets. Une comparaison superficielle (shallow compare) est souvent suffisante pour l'UI.

### B. Qualité du Code & Maintenabilité
*   **Gestion des Erreurs :** `ErrorHandler.js` est robuste. Il capture les promesses non gérées et les erreurs globales, tout en fournissant un feedback visuel (`showNotification`).
*   **Nommage :** Les conventions sont respectées (`_privateMethods`, `CONSTANTS`).
*   **Documentation :** Le code est bien commenté, avec des JSDoc présents sur les fonctions utilitaires complexes.

### C. Interface Utilisateur & CSS
*   **CSS Moderne :** Utilisation de `color-mix(in oklab, ...)` pour les variations de couleurs. C'est très moderne, mais assurez-vous que les navigateurs cibles le supportent (récent sur Chrome/Safari/FF).
*   **Mode Compact :** La logique est dispersée entre CSS (`.compact-mode`) et JS. Le CSS gère bien les transitions, mais la complexité des sélecteurs (ex: `.workflow-wrapper.compact-mode:not(.logs-active) .step`) rend la maintenance CSS difficile.
*   **Responsive :** `responsive.css` gère les petits écrans, mais certaines largeurs fixes (`min-width: 500px` dans `csv-workflow-prompt.css`) pourraient casser sur mobile très étroit.

### D. Sécurité (Frontend)
*   **XSS (Cross-Site Scripting) :**
    *   L'application manipule beaucoup de HTML via JS (`innerHTML`).
    *   *Bon point :* Utilisation systématique de `DOMUpdateUtils.escapeHtml` avant l'insertion dans `uiUpdater.js` et `csvWorkflowPrompt.js`.
    *   *Risque résiduel :* `reportViewer.js` injecte du HTML brut dans `srcdoc` d'une iframe : `srcdoc='${html.replace(/'/g, "&#39;")}'`. Bien que sandboxée, c'est un vecteur potentiel si le contenu du rapport n'est pas fiable.

---

## 3. Plan d'Action Recommandé

### 🔴 Priorité Haute (Correctifs) — ✅ Résolus le 21/01/2026
1.  **Migration Legacy State (COMPLET) :** Tous les accès aux timers, panneaux de logs, séquences et popups passent désormais par `AppState`. Les proxys legacy ont été supprimés et la synchronisation d’état est unique.
    *   *Couverture tests :* `npm run test:frontend`, `tests/frontend/test_dom_elements_step_guard.mjs`.
2.  **Validation HTML/Ids (COMPLET) :** Le backend (`CacheService`) rejette désormais les `step_key` invalides et les helpers frontend (`domElements.getStepElement`) vérifient systématiquement les IDs avant accès.
    *   *Couverture tests :* `pytest tests/integration/test_step_key_validation.py`.

### 🟡 Priorité Moyenne (Optimisations)
1.  **Optimisation AppState** — *À planifier (TODO suivi)* :
    ```javascript
    // Dans AppState.js
    _deepClone(obj) {
        return structuredClone(obj); // Plus performant et natif
    }
    ```
    - Remplacer également la comparaison `JSON.stringify` de `_stateChanged` par un diff superficiel ciblé pour réduire la charge CPU sur les gros états.
2.  **Lazy DOM** — *À planifier* : Supprimer les `const` statiques dans `domElements.js` (comme `runAllButton`) qui sont évaluées à l'import, et ne garder que les fonctions getters (`getRunAllButton()`) pour éviter les erreurs si le DOM n'est pas encore prêt ou si des éléments sont recréés.

### 🟢 Priorité Basse (Améliorations)
1.  **Build Tool :** Le projet utilise beaucoup de fichiers CSS/JS chargés individuellement. Pour la production, l'ajout d'un bundler (Vite ou Webpack) permettrait de minifier et concaténer les assets, réduisant les requêtes HTTP.
2.  **Refactoring CSS :** Passer à une méthodologie BEM plus stricte ou utiliser des Modules CSS pour éviter les conflits de spécificité (surtout avec les modes `compact`, `logs-active`, `details-active` qui s'empilent).

---

## 4. Score de l'Audit

| Catégorie | Score | Commentaire |
| :--- | :---: | :--- |
| **Architecture** | A- | Très propre pour du Vanilla JS, mais dette technique sur le State. |
| **Performance** | A | Batching DOM et monitoring excellents. |
| **Sécurité** | B+ | Échappement XSS présent, attention aux iframes. |
| **UI/UX** | A | Transitions soignées, thèmes, feedback sonore et visuel riche. |
| **Code Cleanliness** | B+ | Bien commenté, mais quelques fichiers très longs (`uiUpdater.js`, `main.js`). |

**Conclusion :** C'est une application frontend de très haute qualité pour du "Vanilla JS", surpassant souvent des applications React/Vue mal optimisées grâce à sa gestion fine du DOM et de la mémoire. L'effort principal doit porter sur l'élimination de l'ancien système de gestion d'état pour éviter des bugs de régression futurs.