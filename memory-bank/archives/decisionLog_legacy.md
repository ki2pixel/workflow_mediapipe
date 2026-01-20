# Journal des Décisions — Archive historique

> Cette archive regroupe les décisions antérieures au **8 octobre 2025**. Les entrées conservent leur format original pour préserver la traçabilité complète (timestamps, contexte, impacts).

## 2025-10-07 01:20:07+02:00: UI/UX Frontend – Micro-interactions, A11y, Loaders et Fallback Téléchargements
- **Décision** : Améliorer l'UX avec des micro-interactions sur les étapes, un focus management unifié et des spinners de chargement.

## 2025-10-06 18:24:56+02:00: Amélioration de l'affichage de la progression pour l'Étape 3 (Analyse des transitions)
- **Décision** : Afficher correctement les noms de fichiers et la progression intermédiaire (ex: 2/5) via regex de logs améliorées.

## 2025-10-06 15:29:19+02:00: Optimisation des performances de l'Étape 4 (Analyse Audio)
- **Décision** : Remplacer MoviePy par ffmpeg pour l'extraction et utiliser `inference_mode` PyTorch pour accélérer le traitement.

## 2025-10-06 14:42:00+02:00: Correction de la barre de progression globale pour l'Étape 5 (Tracking)
- **Décision** : Éviter les sauts à 100% en limitant la contribution de chaque fichier à 0.99 tant que le lot n'est pas terminé.

## 2025-10-06 10:19:24+02:00: Optimisations de performance Étape 3 (TransNetV2 PyTorch)
- **Décision** : Accélérer via `torch.inference_mode()` et TorchScript, avec décodage FFmpeg en streaming.

## 2025-10-06 08:31:16+02:00: Rapport mensuel agrégé
- **Décision** : Ajouter `ReportService.generate_monthly_archive_report()` pour agréger les stats de toutes les archives d'un mois.

## 2025-10-06 08:31:16+02:00: Normalisation UI projets avec timestamp
- **Décision** : Afficher les noms propres des projets tout en conservant le suffixe temporel via tooltip A11y.

## 2025-10-06 08:31:16+02:00: Archivage unique avec suffixe horodaté
- **Décision** : Écrire les archives dans des dossiers suffixés `YYYY-MM-DD_HH-MM-SS` pour éviter les collisions entre projets homonymes.

## 2025-10-06 01:30:00+02:00: Optimisation du pipeline de tracking en mode full CPU
- **Décision** : Désactiver le GPU (`TRACKING_DISABLE_GPU=1`) au profit de 15 workers CPU internes pour de meilleures performances sur la config actuelle.

## 2025-10-06 01:15:00+02:00: Correction de la détection des vidéos à traiter
- **Décision** : Ignorer les fichiers `*_audio.json` lors du scan pour éviter les faux positifs de vidéos "déjà traitées".

## 2025-10-03 14:17:30+02:00: Suppression du mode minimal interne de « Téléchargements Locaux »
- **Décision** : Supprimer la croix de réduction interne au profit du toggle global de la barre unifiée.

## 2025-10-03 14:12:30+02:00: Toggle de visibilité dans la barre unifiée pour « Téléchargements Locaux »
- **Décision** : Ajouter un bouton "📥 Téléchargements" dans les contrôles unifiés pour masquer la section sans arrêter le polling.

## 2025-10-03 14:01:50+02:00: Mode réduit/collapsible pour « Téléchargements Locaux »
- **Décision** : Introduire un mode réduit par défaut avec persistance `localStorage` pour diminuer l'empreinte visuelle.

## 2025-10-03 11:41:59+02:00: Réinitialisation mensuelle de `processed_archives.txt` (Étape 1)
- **Décision** : Vider automatiquement la liste des archives traitées au changement de mois pour permettre le retraitement d'archives portant le même nom.

## 2025-10-03 11:35:00+02:00: Ajout de l'endpoint API pour lister les projets dans les rapports
- **Décision** : Créer `GET /api/visualization/projects` pour corriger les erreurs 404 du frontend.

## 2025-10-03 11:35:00+02:00: Robustification de l'Étape 7 pour la gestion des destinations existantes
- **Décision** : Utiliser `dirs_exist_ok=True` pour éviter les échecs de copie si le répertoire de destination existe déjà.

## 2025-10-02 21:52:55+02:00: Mode compact unique pour les étapes
- **Décision** : Supprimer le mode "normal" ; la grille compacte devient l'unique mode d'affichage pour une ergonomie accrue.

## 2025-10-02 21:24:25+02:00: Step 7 — Exécution via environnement virtuel
- **Décision** : Forcer l'utilisation de l'interpréteur `env/bin/python` pour l'Étape 7 afin d'éviter les manques de dépendances système.

## 2025-10-02 21:24:25+02:00: Diagnostic Permissions et ACLs
- **Décision** : Corriger les permissions via ACLs sur `archives/` pour garantir l'accès en écriture au groupe `wfgroup`.

## 2025-10-02 21:24:25+02:00: Finalisation Step 7 — Compatibilité NTFS (fuseblk) et copie sans permissions
- **Décision** : Désactiver la préservation des permissions (`--no-perms`) lors de la copie vers des partitions NTFS pour éviter les erreurs `EPERM`.

## 2025-10-02 01:05:22+02:00: Archivage avant suppression en Étape 7
- **Décision** : Appeler systématiquement `ResultsArchiver` avant de nettoyer le dossier projet.

## 2025-10-02 01:05:22+02:00: Robustesse VisualizationService (schémas et noms d’artefacts)
- **Décision** : Supporter les variations de nommage (ex: `.csv` vs `.json`) et inférer `total_frames` depuis les données observées.

## 2025-10-02 01:05:22+02:00: Correctifs Flask et UI Report
- **Décision** : Corriger des erreurs de syntaxe Python et ajouter la case à cocher "Projet uniquement" dans l'interface des rapports.

## 2025-10-02 01:05:22+02:00: Rapports HTML-only et endpoint projet
- **Décision** : Supprimer le support PDF (complexe/instable) au profit du HTML uniquement, et ajouter des rapports consolidés par projet.

## 2025-10-01 10:49:05+02:00: Harmonisation des styles et états hover/focus
- **Décision** : Uniformiser les styles (couleurs, transitions) entre le panneau de réglages et les contrôles globaux.

## 2025-10-01 10:49:05+02:00: Gestion d’état et accessibilité du panneau Settings
- **Décision** : Utiliser `AppState` pour la persistance et implémenter les attributs ARIA pour l'accessibilité du panneau repliable.

## 2025-10-01 10:49:05+02:00: Suppression des widgets flottants et intégration inline
- **Décision** : Déplacer les contrôles flottants vers la top bar unifiée pour réduire l'encombrement visuel.

## 2025-10-01 10:49:05+02:00: Top bar unifiée et panneau de réglages repliable
- **Décision** : Créer une barre supérieure fixe regroupant les actions principales (Stats, Rapports, Settings).

## 2025-10-01 00:01:48+02:00: Frontend Report Viewer (A11y/XSS/Performances)
- **Decision** : Implémenter une modale sécurisée (échappement XSS) pour la visualisation des rapports.

## 2025-10-01 00:01:48+02:00: Générateur de Rapport Visuel (ReportService)
- **Décision** : Utiliser Jinja2 pour générer des rapports HTML complets à partir des métriques archivées.

## 2025-10-01 00:01:48+02:00: Finalisation Step 7 — Préserver les archives et restauration optionnelle
- **Décision** : Sanctuariser `ARCHIVES_DIR` ; l'Étape 7 ne doit jamais supprimer ce dossier.

## 2025-10-01 00:01:48+02:00: Persistance des analyses et provenance (ResultsArchiver)
- **Décision** : Introduire un service d'archivage avec hash SHA-256 pour garantir l'intégrité et la disponibilité des résultats à long terme.

## 2025-09-29 15:05:00+02:00: Cache-busting CSS systématique
- **Décision** : Ajouter un paramètre de version (`?v=...`) aux URLs CSS pour forcer le rechargement après mise à jour.

## 2025-09-29 15:05:00+02:00: Séquençage des transitions (logs-entering/logs-leaving) et alignement
- **Décision** : Utiliser des classes d'état CSS et `transitionend` en JS pour synchroniser l'affichage du panneau de logs.

## 2025-09-29 15:05:00+02:00: Panneau de logs en overlay fixe en mode compact
- **Décision** : Fixer le panneau de logs à droite de l'écran en mode compact pour éviter de tasser les étapes.

## 2025-09-29 15:05:00+02:00: Mode compact stable pour les étapes (grille persistante)
- **Décision** : Maintenir une grille 2x4 persistante même lors des transitions pour éviter les "sauts" visuels.

## 2025-09-26: Implémentation de Diagnostics Système
- **Décision** : Ajouter une modale affichant les versions, l'état du disque et des services pour faciliter le support technique.

## 2025-09-26: Corrections de Bugs Frontend (ReferenceError)
- **Décision** : Corriger les problèmes d'initialisation JS en garantissant que les éléments du DOM sont chargés avant l'attachement des handlers.

## 2025-09-25 22:04:16+02:00: Élévation des pratiques récentes au statut MANDATORY (Standards v4.1)
- **Décision** : Rendre obligatoire l'usage de l'accessibilité (A11y), du batching DOM et de la sécurité XSS pour tout nouveau développement frontend.

## 2025-09-25 21:48:30+02:00: Stratégie de tests frontend légère (ESM/Node)
- **Décision** : Valider les utilitaires frontend via des tests unitaires exécutables sous Node.js (sans navigateur).

## 2025-09-25 21:48:30+02:00: Hardening Smart Upload (A11y & XSS)
- **Décision** : Sécuriser l'affichage des noms de fichiers dans la modale d'upload pour prévenir les injections.

## 2025-09-25 21:48:30+02:00: Sélection de source dynamique MySQL/Airtable
- **Décision** : Évaluer les flags `USE_MYSQL/USE_AIRTABLE` à chaque appel pour permettre le basculement à chaud (utile pour les tests).

## 2025-09-25 21:48:30+02:00: Garde-fou DRY_RUN pour téléchargements
- **Décision** : Ajouter `DRY_RUN_DOWNLOADS` pour simuler les téléchargements sans consommer de bande passante/disque lors des tests.

## 2025-09-25 21:48:30+02:00: Backoff adaptatif du Polling côté frontend
- **Décision** : Augmenter progressivement l'intervalle entre deux requêtes si le serveur est indisponible ou ne renvoie aucun changement.

## 2025-09-25 19:40:09+02:00: Simplification de la modale Smart Upload
- **Décision** : Afficher uniquement les dossiers créés le jour même pour simplifier le choix de l'utilisateur.

## 2025-09-22: Support des URLs FromSmash avec modal adapté
- **Décision** : Ouvrir les liens FromSmash dans un nouvel onglet via une modale explicative (le téléchargement auto n'étant pas possible).

## 2025-09-17: Passage au monitoring via Airtable
- **Décision** : Utiliser Airtable comme base de données de monitoring principale pour une mise à jour en temps réel.

## 2025-09-15: Simplification de la navigation des diagrammes
- **Décision** : Ouvrir les schémas techniques dans un nouvel onglet plutôt que dans une lightbox pour simplifier le code.

## 2025-09-12: Adoption d'une architecture orientée services
- **Décision** : Isoler la logique métier dans des classes `Service` (ex: `WorkflowService`, `CSVService`) indépendantes des routes Flask.

## 2025-09-10: Utilisation d'environnements virtuels spécialisés
- **Décision** : Créer des venvs séparés (`audio_env`, `tracking_env`) pour éviter les conflits entre les différentes versions de PyTorch/CUDA.

## 2025-09-10: Gestion d'état centralisée pour le frontend
- **Décision** : Utiliser un singleton `AppState` pour synchroniser l'interface web sans dépendre de variables globales éparpillées.
