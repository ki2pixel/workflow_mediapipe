# Diagrammes Interactifs et Lightbox — Vue d’Ensemble

## Objectif

Ce document centralise les informations sur l’intégration des diagrammes interactifs et de la lightbox dans le portail de documentation Workflow MediaPipe.

Il pointe vers :

- la documentation d’intégration,
- les guides de debug avancé,
- les résumés de correctifs.

## Intégration principale

Pour les détails d’implémentation (HTML, JS, fichiers `assets/app.js`, pages `architecture-complete-interactive/`, `workflow-execution-interactive/`), se référer à :

- `INTERACTIVE_DIAGRAMS_INTEGRATION.md`
- `DIAGRAM_INTEGRATION_FINAL_CHANGES.md`

Ces documents décrivent :

- la détection des images cliquables,
- la création de la lightbox (overlay, iframe),
- les URLs relatives vers les diagrammes interactifs,
- l’intégration dans le portail (`index.html`, sous‑pages `flux-execution/`, `architecture-systeme/`).

## Debug & dépannage avancé

Pour diagnostiquer et corriger les problèmes de clics ou d’affichage de la lightbox, utiliser :

- `LIGHTBOX_DEBUG_COMPREHENSIVE.md`
- `LIGHTBOX_FIXES_SUMMARY.md`
- `CLICK_EVENT_FIXES_GUIDE.md`

Ces guides couvrent notamment :

- les fonctions console (`comprehensiveDebug()`, `manualSetupClickListeners()`, `testLightboxVisibility()`, etc.),
- les problèmes de timing/attach des listeners,
- les soucis de chemins relatifs/absolus pour les iframes,
- les permissions sandbox et instructions d’interaction dans la lightbox.

## Bonnes pratiques

- Préférer les URL **relatives** pour les iframes des diagrammes.
- Tester les pages principales *et* les sous‑pages (`flux-execution`, `architecture-systeme`).
- Utiliser les fonctions de debug fournies avant de modifier le code.

## Pour aller plus loin

- `PORTAL_SUMMARY.md` — résumé de création du portail et des diagrammes interactifs.
- `ARCHITECTURE_COMPLETE_FR.md` — vision globale du système, avec références aux diagrammes.
