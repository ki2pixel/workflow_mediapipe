# Suivi de Progression — Archive historique

> Cette archive conserve les entrées antérieures au **1er décembre 2025** avec leur format original afin de préserver la traçabilité complète.

## Novembre 2025
- [2025-11-18 16:32] **Stabilisation STEP4 GPU (CUDA 11.x)** : environnement Python 3.10 dédié, gestion OOM et succès partiel.
- [2025-11-18 13:35] **Plan de migration WorkflowState** : définition des 4 étapes pour l'unification de l'état.
- [2025-11-18 13:32] **Migration WorkflowState (Phase active)** : élimination des références à `PROCESS_INFO` dans l'application principale.
- [2025-11-18 13:30] **Refactoring de maintenabilité (Phases 1-3a)** : création de `WorkflowState`, `WorkflowCommandsConfig` et `DownloadService`. 102 nouveaux tests.
- [2025-11-12 11:30] **Mise à jour Documentation** : synchronisation via workflow docs-updater.
- [2025-11-02 12:00] **Suppression fonctionnalités de rapport** : retrait de `report_service.py` et passage en gestion manuelle via `archives/`.
- [2025-11-02 00:38] **Alignement rapports mensuels** : harmonisation du comptage et robustesse du parsing HTML.

## Octobre 2025
- [2025-10-27 20:42] **Gestion Dropbox** : correction de la gestion des URLs de dossiers partagés (`/scl/fo/`).
- [2025-10-27 13:20] **Stabilisation CSVService** : support `html.unescape` pour les URLs et fiabilisation de la suite de tests.
- [2025-10-27 11:30] **Fix URLs double-encodées** : suppression des doublons dans l'historique et décodage récursif des paramètres.
- [2025-10-17 13:20] **Source Webhook externe** : mise en place du proxy PHP et priorisation des sources (Webhook > MySQL).
- [2025-10-08 16:40] **Compression Vidéo Étape 2** : intégration de la compression (NVENC/x264) post-conversion FPS.
- [2025-10-07 01:20] **UI/UX Frontend** : micro-interactions, accessibilité modales et loaders unifiés.
- [2025-10-06 18:24] **Progression Étape 3** : affichage correct du nom de fichier et des compteurs intermédiaires.
- [2025-10-06 16:45] **Tracking Full CPU** : passage à 15 workers CPU pour STEP5 pour plus de stabilité.
- [2025-10-06 15:29] **Optimisation Étape 4** : passage à FFmpeg pour l'extraction audio et optimisations PyTorch inference.
- [2025-10-06 14:42] **Barre de progression Étape 5** : correction des sauts à 100% et initialisation des compteurs.
- [2025-10-06 10:19] **Optimisation Étape 3** : intégration TorchScript et décodage FFmpeg asynchrone pour TransNetV2.
- [2025-10-06 08:31] **Archivage & Rapports** : dossiers horodatés uniques, rapports mensuels agrégés et normalisation UI projets.
- [2025-10-03 14:17] **UI Téléchargements** : ajout du toggle de visibilité dans la barre unifiée et mode réduit par défaut.
- [2025-10-03 11:54] **Réinitialisation mensuelle logs** : reset auto de `processed_archives.txt` chaque début de mois.
- [2025-10-03 11:35] **Robustesse Étape 7** : gestion `dirs_exist_ok=True` et fallbacks de copie NTFS.
- [2025-10-02 21:52] **Standardisation UI** : mode compact unique pour l'affichage des étapes.
- [2025-10-02 01:05] **Rapports HTML-only** : suppression du support PDF et ajout des rapports consolidés par projet.

## Septembre 2025 (et antérieur)
- [2025-09-29] **Transitions UI** : panneau de logs en overlay fixe et cache-busting CSS.
- [2025-09-26] **Diagnostics & Notifications** : ajout d'outils de diagnostics système et notifications navigateur.
- [2025-09-25] **Standards v4.1** : élévation des pratiques A11y, XSS et batching DOM au statut MANDATORY.
- [2025-09-22] **Support FromSmash** : intégration des liens avec ouverture forcée en nouvel onglet.
- [2025-09-17] **Monitoring Airtable** : (Legacy) remplacement initial du monitoring fichier.
- [2025-09-12] **Architecture Services** : structuration backend Flask orientée services.
- [2025-09-10] **Environnements Virtuels** : isolation des dépendances deep learning par étape.
- [2025-09-08] **État Frontend** : implémentation de `AppState.js` pour une gestion centralisée.
