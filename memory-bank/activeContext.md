# Contexte Actif (Active Context)

## Tâche en Cours
Aucune tâche active. La session d'audit de performance et d'optimisation de la STEP5 a été clôturée avec succès.

## Objectifs
- Maintenir l'intégrité du repo.
- Préparer pour le développement futur.

## Décisions Récentes
- [2026-05-29 19:40:00] **Optimisations de Performance STEP5 (InsightFace GPU & JSON Streaming) (COMPLET)** : Audit et implémentation des optimisations pour le tracking GPU (limite VRAM 4 Go) : restriction de modules (`allowed_modules`), baisse de la résolution (`det_size=480`) et écriture JSON en flux (`StreamingJSONOutput`) en RAM O(1). Gain de +440% (10 à 54+ FPS) validé en conditions réelles.
- [2026-05-29 13:42:00] **Correction Bug Rendu DOMDiff (COMPLET)** : Résolution du bug de rendu de la liste de téléchargements locaux qui arrêtait le polling du frontend et empêchait l'apparition de la popup de workflow. Correction du passage direct des éléments `<li>` à `DOMDiff.morph` par le clonage du `<ul>` conteneur en amont.
- [2026-05-27 19:39:00] **Nettoyage configuration Vultr .env (COMPLET)** : Suppression complète de toutes les variables d'environnement Vultr obsolètes (sections `# STEP5 — Cloud Vultr` et `# STEP5 — Container Runtime`) devenues inutiles suite à l'abandon et à la non-fusion de la feature cloud dans la branche main.
- [2026-05-27 19:27:00] **Nettoyage des variables obsolètes (RENDER_*) (COMPLET)** : Suppression complète de `RENDER_REGISTER_TOKEN`, `RENDER_APP_CALLBACK_URL`, `RENDER_APP_CALLBACK_TOKEN`, `RENDER_REGISTER_URL_ENDPOINT`, `REMOTE_TRIGGER_URL`, `REMOTE_POLLING_INTERVAL` et du poller distant inutilisé (`RemoteWorkflowPoller`). Tous les tests unitaires et d'intégration ont été mis à jour et validés avec succès.
- [2026-05-27 19:13:12] **Persistance Sélective (AppState Middleware) (COMPLET)** : Implémentation de la recommandation de l'audit pour la persistance sélective de l'état frontend. Création d'un middleware déclaratif dans `AppState.js` avec migration automatique des anciennes clés. Refactoring complet de `main.js` et `eventHandlers.js` pour supprimer les accès directs au `localStorage` et restauration dynamique de l'UI des sélections d'étapes personnalisées. Ajout de `test_state_persistence.mjs` validé avec succès.
- [2026-05-27 19:02:00] Implémentation du système Virtual DOM (DOM Morphing) léger via `DOMDiff.js` (O(N) diffing). Remplacement des `innerHTML` destructeurs dans la méthode `updateLocalDownloadsListUI` de `uiUpdater.js`. Ajout et passage complet des tests unitaires `tests/frontend/dom_diff.test.js` exécutés par le script `test:frontend`.
- [2026-05-27 19:10:00] Audit complet de l'architecture frontend natif (vanilla JS). Analyse et documentation des mécanismes `AppState` (état réactif immuable), `DOMBatcher` (évitement du *layout thrashing* via `requestAnimationFrame`), `PollingManager` (boucles réseau résilientes sans fuite), `PerformanceMonitor` (télémétrie intégrée) et `ErrorHandler` (auto-guérison et pénalités exponentielles). Rapport publié dans `docs/audits/frontend_audit.md`.
- [2026-05-27 18:52:00] Alignement complet de la documentation avec le codebase réel via le workflow `docs-updater` : documentation de `ijson` (streaming O(1) RAM) pour STEP6/STEP7 et des safeguards de démarrage sécurisé de production et de `validate_startup.py` dans le guide de sécurité.
- [2026-05-27 18:40:00] Implémentation de la recommandation d'audit "Optimisation I/O pour STEP6/STEP7". Utilisation de `ijson` pour parser les fichiers de tracking en flux. Refonte de `json_reducer.py` et `preprocess_ae_json.py` pour un maintien de la RAM O(1).
- [2026-05-27 18:28:00] Implémentation de la recommandation d'audit "Sécurité en Production". L'application Flask (app_new.py) et le script de validation (validate_startup.py) crashent désormais fermement en production (DEBUG=False) si des secrets/tokens par défaut (dev-*) sont configurés.
- [2026-05-27 18:08:00] Validation (commit) et publication (push) du nettoyage des fichiers non suivis/obsolètes et de l'ajout du rapport d'audit d'architecture.
- [2026-03-13 18:29:00] Rollback Git vers commit 11482b2 ("docs: Replace Kaggle/Google Colab docs with Lightning AI documentation") suite à problème avec la feature STEP5 remote Lightning.
- [2026-03-13 18:29:00] Suppression des fichiers non suivis : services/step5_remote_lightning_service.py, tests associés, et répertoire .shrimp_task_manager/.
- [2026-03-13 18:27:00] Clôture du chantier STEP5 remote Lightning après implémentement, tests, mise à jour de la documentation pipeline et synchronisation complète de la Memory Bank (avant rollback).

## Questions Ouvertes
- Évaluer si la feature STEP5 remote Lightning doit être réimplémentée ou abandonnée.
- Vérifier l'état de la documentation Lightning AI après rollback.

## Prochaines Étapes
- Vérifier le fonctionnement du repo après le commit et push de nettoyage.
- Reprendre le développement selon les besoins.