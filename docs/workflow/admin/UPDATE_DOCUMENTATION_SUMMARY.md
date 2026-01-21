# Mise à Jour Documentation - Optimisations v4.1

## Résumé des Modifications

Ce document résume les mises à jour apportées à la documentation pour refléter les optimisations v4.1 incluant les améliorations de progression, le mode CPU-only pour le tracking, et les optimisations audio ffmpeg.

## 2026-01-20 — Audit Logs Panel — Phase 2 (Intégration Timeline-Logs) (COMPLET)
- ✅ **Header contextuel** : Étape/statut/timer dans le panneau logs
- ✅ **Boutons globaux** : Conteneur unifié pour "logs spécifiques"
- ✅ **Ancrage vertical** : Positionnement près de l'étape active en mode compact
- ✅ **Tests frontend** : `test_timeline_logs_phase2.mjs` intégré
- **Validation** : `npm run test:frontend` OK
- **Impact** : Ergonomie améliorée, association Timeline↔Logs explicite

## 2026-01-20 — Timeline Connectée Phase 3 (Advanced Features) - COMPLET
- ✅ **Panneau détails contextuel** : Module `static/stepDetailsPanel.js` avec sélection par clic/clavier, synchronisation AppState/DOMBatcher, fermeture auto logs, focus trap/restore, gestion Escape
- ✅ **Accessibilité WCAG** : `aria-expanded`, navigation clavier complète, aria-live, support `prefers-reduced-motion`
- ✅ **Optimisations UI** : Layout compact coexistence logs/détails, rafraîchissement différé via import dynamique, cache léger WeakMap
- ✅ **Tests frontend** : `tests/frontend/test_step_details_panel.mjs` (Given/When/Then) intégré à `npm run test:frontend`
- **Validation** : `npm run test:frontend` OK, audit mis à jour avec Phase 3 ✅
- **Impact** : Timeline Connectée production-ready avec expérience utilisateur premium, aucune régression fonctionnelle

## 2026-01-20 — Maintenance Tests Backend — Phase 1-3 (COMPLET)
- ✅ **Phase 1 (Corrections Critiques)** : Migration `_get_app_state` → `get_workflow_state` dans `tests/unit/test_workflow_service.py` et `tests/integration/test_workflow_routes.py`, suppression méthodes obsolètes `convert_expanded_onedrive_url` et `fetch_csv_data` dans `tests/unit/test_csv_service_refactored.py`, correction imports `app_new` → `create_app` dans `tests/integration/test_lemonfox_api_endpoint.py`, implémentation locale `parse_progress_from_log_line`.
- ✅ **Phase 2 (Isolation Environnement)** : Scripts spécialisés `run_step3_tests.sh`, `run_step5_tests.sh`, `run_main_tests.sh` et configuration `pytest.ini` pour isoler les tests par environnement virtuel.
- ✅ **Phase 3 (Refactoring Tests)** : Fixtures standardisées dans `conftest.py` (`mock_workflow_state`, `mock_app`, etc.) et scripts d'automatisation (`diagnose_tests.sh`, `fix_backend_tests.sh`, `validate_tests.sh`).
- **Résultats** : 67 tests passés Phase 1, 281 tests principaux Phase 2, patterns standardisés Phase 3.
- **Documentation** : Guide complet créé dans `BACKEND_TESTS_MAINTENANCE_GUIDE.md`.

## 2026-01-18 — Suppression Features UI (Post-Audit)
- ✅ **Supervision UI** : Boutons Diagnostics/Statistiques/Téléversement retirés (templates/index_new.html, static/main.js)
- ✅ **Smart Upload avancé** : Mode compact unifié maintenu, fonctionnalités avancées retirées
- ✅ **Étape 5 · Options avancées** : Configuration dynamique des chunks supprimée (chunking adaptatif avec valeurs par défaut)
- ✅ **API endpoints** : `/api/step5/chunk_bounds` et méthodes associées supprimées
- Impact : Réduction significative de la surface de maintenance sans impacter les fonctionnalités essentielles
- Documentation : GUIDE_DEMARRAGE_RAPIDE.md et REFERENCE_RAPIDE_DEVELOPPEURS.md mises à jour

## 2026-01-18 — Audit Frontend Complet
- ✅ Sécurité XSS : Corrections P0 dans `apiService.js` (remplacement `innerHTML +=`)
- ✅ Accessibilité : Focus trap + restauration sur toutes modales (`statsViewer.js`, `reportViewer.js`)
- ✅ Tests : Ajout `test_dom_batcher_performance.mjs` et `test_focus_trap.mjs`
- ✅ Performance : Regex pré-compilées dans `uiUpdater.js` via `_COMPILED_LOG_PATTERNS`
- ✅ Reduced Motion : Support global `prefers-reduced-motion` dans `base.css`
- Validation : `npm run test:frontend` OK
- Documentation : `ARCHITECTURE_COMPLETE_FR.md` et `GUIDE_DEMARRAGE_RAPIDE.md` mises à jour

### 2025-12-19 — Registry objets STEP5 + Webhook-only + Lemonfox

- `STEP5_SUIVI_VIDEO.md` : ajout de la hiérarchie des modèles (`workflow_scripts/step5/models/`) et d’une table détaillée du registry `ObjectDetectorRegistry` (6 modèles + backends), précisions sur la résolution de chemins et les bonnes pratiques pour le fallback MediaPipe.
- `GUIDE_DEMARRAGE_RAPIDE.md` : clarification de la section `.env` pour refléter **Webhook comme source unique** (`WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/data/webhook_links.json`) et ajout d’annotations sur le registry STEP5.
- `STEP4_ANALYSE_AUDIO.md` : documentation du chargement automatique `config/optimal_tv_config.json`, du fallback minimal et de l’import via `importlib` pour éviter `flask_caching` dans `audio_env`.
- `STEP5_OPENCV_YUNET_PYFEAT.md` : références vers les scripts STEP5 (manager, engines, worker multiprocessing) pour contextualiser les optimisations CPU/profiling.

### 2025-12-19 — Harmonisation STEP5 (limites visages & scaling `jawOpen`)

- `STEP5_SUIVI_VIDEO.md` : ajout d’un tableau dédié aux garde-fous OpenCV/Mediapipe (`STEP5_OPENCV_MAX_FACES`, `STEP5_MEDIAPIPE_MAX_FACES`, `STEP5_*_JAWOPEN_SCALE`, `STEP5_MEDIAPIPE_MAX_WIDTH`), rappel des logs `[WORKER-XXXX]`.
- `GUIDE_DEMARRAGE_RAPIDE.md` : configuration `.env` minimale enrichie avec les nouvelles variables STEP5.
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` : note explicite sur la propagation automatique du `.env` vers les workers multiprocessing STEP5.
- `.env` : commentaires clarifiés pour distinguer OpenCV/Mediapipe et mention du downscale optionnel.

### 2025-12-20 — Virtualenvs relocalisables + optimisations STEP5
### 2025-12-27 — STEP5 scheduler GPU/CPU + documentation alignée
- `STEP5_SUIVI_VIDEO.md` : ajout d'une section sur le planificateur hybride (thread GPU séquentiel + workers CPU multiprocessing), documentation du fallback objet MediaPipe multi-thread en mode GPU et du chunking adaptatif (`--chunk_size 0`).
- `STEP5_GPU_USAGE.md` : couverture du moteur InsightFace GPU-only (env dédié, injection CUDA, exemples CLI), extension des paramètres `.env` (`STEP5_GPU_ENGINES`, `STEP5_INSIGHTFACE_ENV_PYTHON`).
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` : précisions sur les valeurs par défaut STEP5 (`TRACKING_CPU_WORKERS=15`, `TRACKING_DISABLE_GPU=1`, `STEP5_GPU_FALLBACK_AUTO`), override TensorFlow/InsightFace et flux de traitement par défaut.
- `GUIDE_DEMARRAGE_RAPIDE.md` : bloc `.env` mis à jour (CPU workers, commentaire CPU-only, mention d'`STEP5_INSIGHTFACE_ENV_PYTHON`).


- `REFERENCE_RAPIDE_DEVELOPPEURS.md` : nouvelle section “Virtualenvs relocalisables (`VENV_BASE_DIR`)" détaillant l’ordre de résolution (env > `.env` > dossier projet), l’export `PYTHON_VENV_EXE_ENV` dans `start_workflow.sh` et l’utilisation systématique de `Config.get_venv_path/get_venv_python` dans `WorkflowCommandsConfig`.
- `GUIDE_DEMARRAGE_RAPIDE.md` : `.env` minimal enrichi avec `VENV_BASE_DIR`, instructions d’installation/activation des venvs via `${VENV_BASE_DIR:-.}` (création de `env`, `transnet_env`, `audio_env`, `tracking_env`, `eos_env`), rappel sur la relocalisation des environnements, nouveaux commentaires STEP5 (`STEP5_TRACKING_ENGINE`, override `STEP5_EOS_ENV_PYTHON`, retrait InsightFace/Maxine) et note sur les logs `run_tracking_manager.py`.
- `STEP5_SUIVI_VIDEO.md` : documentation complète du moteur `eos` (variables `STEP5_EOS_*`, environnement dédié `eos_env`, export `tracked_objects[].eos`, logs `[PROFILING]` toutes les 20 frames, rescale `STEP5_EOS_MAX_WIDTH`), clarification sur `STEP5_EXPORT_VERBOSE_FIELDS`, nouveaux paragraphes sur le gestionnaire STEP5 (routage venv, logs, chunking) et encart sur la robustesse du worker multiprocessing (chargement `.env`, retries, JSON dense).
- Références explicites aux tests `tests/unit/test_step5_export_verbose_fields.py` et `tests/unit/test_object_detector_registry.py` pour suivre les impacts JSON/blendshapes et la résolution des modèles de fallback.

## Fichiers Modifiés

### 1. `STEP3_DETECTION_SCENES.md`
**Modifications** :
- ✅ Ajout de la section "Améliorations Récentes (v4.1)" décrivant les améliorations de l'affichage de la progression
- ✅ Support étendu des messages de progression et corrections syntaxiques

### 2. `STEP4_ANALYSE_AUDIO.md`
**Modifications** :
- ✅ Ajout de la section "Améliorations Récentes (v4.1)" avec les optimisations ffmpeg et PyTorch
- ✅ Mise à jour de l'exemple de fonction d'extraction audio

### 3. `STEP5_SUIVI_VIDEO.md`
**Modifications** :
- ✅ Ajout de la section "Corrections de la Barre de Progression" pour les fixes backend/frontend
- ✅ Mise à jour de la section mode CPU-only avec détails techniques

### 4. `ARCHITECTURE_COMPLETE_FR.md`
**Modifications** :
- ✅ Mise à jour des descriptions des Étapes 4 et 5 pour inclure les optimisations
- ✅ Note de version v4.1 mise à jour avec les changements

### 5. `GUIDE_DEMARRAGE_RAPIDE.md`
**Modifications** :
- ✅ Mise à jour du titre vers v4.1
- ✅ Ajout d'une note sur les améliorations de performance

### 6. `REFERENCE_RAPIDE_DEVELOPPEURS.md`
**Modifications** :
- ✅ Mise à jour du titre vers v4.1
- ✅ Extension de la section "Optimisations Récentes v4.1" avec détails techniques sur tous les changements

## Changements Conceptuels

### Améliorations de Performance
- **Étape 4** : Passage à ffmpeg pour extraction audio plus rapide
- **Étape 5** : Mode CPU-only par défaut pour stabilité et performance
- **Progression** : Corrections pour éviter les sauts à 100% prématurés

## Nouvelles Fonctionnalités Documentées

### 1. Variables d'Environnement
- `TRACKING_DISABLE_GPU=1` et `TRACKING_CPU_WORKERS=4` (par défaut recommandé pour limiter la contention CPU) pour STEP5
- `STEP5_YUNET_MAX_WIDTH=640` (downscale YuNet, coords rescalées dans le JSON)
- `AUDIO_DISABLE_GPU` et `AUDIO_CPU_WORKERS` pour STEP4

### 2. Optimisations Techniques
- Écriture JSON en streaming pour STEP4
- PyTorch optimizations (inference_mode, no_grad)
- Garde-fous de progression dans UI

### 3. Corrections Bugs
- Parsing de logs amélioré pour STEP3
- Barre de progression stable pour STEP5

## Fichiers Modifiés (sections legacy archivée)

> Depuis la migration Webhook-only (décision du 13/12/2025), **toutes** les références à l'ancienne intégration multi-sources (Airtable, MySQL, CSV fallback, entrées "manual_open") ont été déplacées dans la section `docs/workflow/legacy/`. La documentation active ne couvre plus ces scénarios.

### Documentation active à maintenir
- `ARCHITECTURE_COMPLETE_FR.md` — décrit l'architecture v4.1/v4.2 exclusivement Webhook + WorkflowState/WorkflowCommandsConfig
- `GUIDE_DEMARRAGE_RAPIDE.md` — procédures d'installation et configuration `.env` (Webhook-only, STEP5 CPU par défaut)
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` — conventions obligatoires (measure_api, WorkflowState, DOMBatcher, etc.)
- `WEBHOOK_INTEGRATION.md`, `CSV_DOWNLOADS_MANAGEMENT.md`, `MONITORING_TELECHARGEMENTS_SOURCES.md` — source de vérité pour le monitoring
- Features actives : `DIAGNOSTICS_FEATURE.md`, `RESULTS_ARCHIVER_SERVICE.md` (Smart Upload est désormais archivé, voir ci-dessous)

- ### Documentation historique (consultation uniquement)
- `legacy/SMART_UPLOAD_FEATURE.md` — flux Smart Upload (supprimé le 18 janvier 2026, décision consignée dans `memory-bank/decisionLog.md`)
- `legacy/INTEGRATION_AIRTABLE.md` — ancien guide Airtable/MySQL/CSV (déplacé le 2026-01-13 depuis la racine pour éviter toute confusion)
- Annexes Airtable/CSV dans `legacy/ARCHITECTURE_COMPLETE_FR_AIRTABLE.md`, `legacy/GUIDE_DEMARRAGE_RAPIDE_AIRTABLE.md`, `legacy/REFERENCE_RAPIDE_DEVELOPPEURS_AIRTABLE.md` (copies automatiques à conserver pour traçabilité)
- Toute mention d'API `/api/airtable_*`, variables `USE_AIRTABLE`, `CSV_MONITOR_URL`, `manual_open` appartient désormais à cette archive.

Ces fichiers legacy ne doivent plus être référencés depuis les menus/documents actifs ; ils existent uniquement pour l'historique ou les audits.

## Ajouts liés à FromSmash et Multi-Sources (2025-09-23)

### Contexte
Suite à la décision d'ajouter le support des URLs FromSmash.com avec un comportement spécifique (pas de téléchargement automatique, ouverture manuelle dans un nouvel onglet via une modale), la documentation a été mise à jour pour refléter ces évolutions.

### Fichiers mis à jour
- `ARCHITECTURE_COMPLETE_FR.md` : Section ajoutée sous "Points d'Intégration" → "Sources de Téléchargement (Dropbox, FromSmash)" avec détails d'implémentation et sécurité.
- `GUIDE_DEMARRAGE_RAPIDE.md` : Note utilisateur après "Accès à l'Interface Web" expliquant le comportement pour FromSmash.
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` : Sous-section "Gestion des liens FromSmash (Frontend)" documentant les fonctions clés (`openFromSmashLink`, `sanitizeExternalUrl`, `escapeHtml`) et recommandations de sécurité.
- `INTEGRATION_AIRTABLE.md` : Point explicite ajoutant le support de sources multiples (Dropbox, FromSmash) dans la section "Migration Automatique".

### Points clés
- Pas de téléchargement automatique pour FromSmash ; ouverture contrôlée et sécurisée dans un nouvel onglet.
- Validation et sanitisation basique des URLs externes côté frontend.
- Maintien de l'expérience classique pour Dropbox ; convergence dans l'UI via modale conditionnelle.

## Suppression des Fonctionnalités de Rapport (2025-11-02)

### Fichiers Impactés
- `templates/reports/` — Supprimé (templates de rapport)
- `static/reportViewer.js` — Supprimé (interface de visualisation des rapports)
- `services/report_service.py` — Supprimé (génération des rapports)
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` — Mise à jour de la section rapports
- `RESULTS_ARCHIVER_SERVICE.md` — Clarification de la gestion manuelle des archives
- `PORTAL_SUMMARY.md` — Mise à jour pour refléter la suppression des fonctionnalités

### Changements
- **Suppression complète** du système de génération de rapports automatisé
- Les archives sont maintenant accessibles directement via le système de fichiers dans `/mnt/cache/archives/`
- Mise à jour de la documentation pour refléter la gestion manuelle des archives

## Nouvelles Mises à Jour de Documentation (2025-09-25 21:52:34+02:00)

### Nouveaux fichiers créés
- `SMART_UPLOAD_FEATURE.md` — Description complète du flux Smart Upload simplifié (dossiers du jour, clic unique → explorateur + Dropbox), A11y (focus trap, Escape, aria) et sécurité (échappement XSS via `DOMUpdateUtils.escapeHtml`).
- `SYSTEM_MONITORING_ENHANCEMENTS.md` — Détails sur l'instrumentation des routes API avec `measure_api()`, le batching DOM pour le widget système et le support GPU conditionnel via `pynvml`.
- `TESTING_STRATEGY.md` — Stratégie de tests unifiée (pytest backend/integration + scripts ESM/Node pour utilitaires frontend), usage de `DRY_RUN_DOWNLOADS` et sélection dynamique des sources.

### Fichiers mis à jour
- `PORTAL_SUMMARY.md` — Ajout des nouveaux documents à la structure et mention des améliorations (instrumentation API, batching DOM, backoff adaptatif).

### Alignement avec le code
- Frontend: `static/main.js` implémente Smart Upload (préchargement des dossiers du jour, focus trap, ouverture contrôlée).
- Backend: `routes/api_routes.py` expose `/api/system_monitor` instrumenté par `measure_api()` et endpoints cache (`/api/cache/list_today`, `/api/cache/open`).
- Services: `services/monitoring_service.py` corrige `get_process_info()` (uptime via `time.time()`), agrège CPU/RAM/GPU/disque.
- Utilitaires: `static/utils/PollingManager.js` prend en charge un backoff adaptatif (pause/reprise via délai retourné).

### Tests & Sécurité
- Tests unitaires/intégration mis en place ou prévus selon stratégie documentée.
- Échappement systématique côté UI des noms de dossiers; aucune logique métier dans les routes (controllers minces).

## Nouvelles Mises à Jour de Documentation (2025-09-26 00:25:47+02:00)

### Nouveaux fichiers créés
- Aucun nouveau fichier créé dans cette session.

### Fichiers mis à jour
- `GUIDE_DEMARRAGE_RAPIDE.md` — Ajout d'une section « Diagnostics Système » expliquant l'accès via le bouton "🩺 Diagnostics", les informations affichées (versions Python/FFmpeg, GPU, config flags) et l'utilité pour le dépannage.
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` — Ajout d'une section « API Endpoints » documentant `/api/system/diagnostics` (méthode, paramètres, réponse, erreurs, instrumentation).
- `ARCHITECTURE_COMPLETE_FR.md` — Mise à jour de `MonitoringService` pour inclure `get_environment_info()` et détails sur le backoff adaptatif dans `PollingManager`.

### Alignement avec le code
- Backend: Nouveau service `MonitoringService.get_environment_info()` pour diagnostics (versions, GPU, config filtrée), route `/api/system/diagnostics` instrumentée via `measure_api()`.
- Frontend: Modale diagnostics accessible (A11y complète), notifications utilisateur (navigateur avec fallback UI) pour fins d'étapes ou erreurs.
- Polling: `PollingManager` avec backoff adaptatif (pause/reprise via délai retourné par callback).

### Tests & Sécurité
- Tests unitaires pour le nouveau service et route prévus selon `TESTING_STRATEGY.md`.
- Sécurité: Flags de config filtrés (pas de secrets exposés), échappement XSS maintenu, A11y pour la modale diagnostics.

## Nouvelles Mises à Jour de Documentation (2025-10-02)

### Changements Clés
- Rapports: standardisation HTML-only (suppression totale du PDF côté backend/frontend).
- Note: Les endpoints de génération de rapports ont été retirés du système.
- UI Rapports: option `#report-project-only` documentée (prévisualisation via iframe sandbox).
- Étape 7: compatibilité NTFS/fuseblk, stratégie de copie sans métadonnées POSIX, `rsync --no-times` pour supprimer les warnings.
- ResultsArchiver: documentation des fallbacks `<stem>.csv`/`<stem>.json` et des méthodes `find_analysis_file()` et `archive_project_analysis()`.

### Fichiers mis à jour
- `REPORT_GENERATION_FEATURE.md` — HTML-only, suppression de la section PDF, précisions sandbox.
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` — note sur le retrait des endpoints de génération de rapports.
- `STEP7_FINALISATION.md` — ajout de la stratégie NTFS/fuseblk, sélection de destination avec repli, notes sur `--no-times`.
- `RESULTS_ARCHIVER_SERVICE.md` — alignement API (find_analysis_file, archive_project_analysis), fallbacks et métadonnées vidéo.
- `PORTAL_SUMMARY.md` — ajout de la section « 2025-10-02 » et mention HTML-only.

### Alignement avec le code
- Backend: `ReportService` docstring HTML-only; `generate_project_report()` disponible; `finalize_and_copy.py` implémente la stratégie NTFS/fuseblk.
- Frontend: `reportViewer.js` comment header HTML-only; UI projet consolidé; prévisualisation via iframe sandbox.

### Prochaines Actions
- Vérifier les liens internes du portail après ces mises à jour.

## Nouvelles Mises à Jour de Documentation (2025-11-18)

### Changements Clés
- Alignement du statut de migration `WorkflowState` dans `MIGRATION_STATUS.md` (finalisation côté `WorkflowService` à planifier) avec plan court terme documenté.
- `STEP5_SUIVI_VIDEO.md` : ajout des helpers `WorkflowService.prepare_tracking_step()` / `create_tracking_temp_file()` et de la gestion des fichiers temporaires pour le tracking.
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` : nouvelle section « WorkflowState — Obligatoire » (API minimale + interdiction des anciens globals dans services/routes).
- `TESTING_STRATEGY.md` : ajout des métriques (173 totaux, 154 passants, 122 nouveaux) et des nouvelles suites d’intégration; dépréciation des tests rapports.

### Vérification
- Les sections ajoutées reflètent l’état réel du code (`app_new.py` migré; `WorkflowService` partiellement legacy) afin d’éviter toute ambiguïté.

## Nouvelles Mises à Jour de Documentation (2025-11-19)

### Changements Clés
- Mise à jour de la documentation pour refléter les dernières modifications apportées au code.
- Ajout de nouvelles sections pour décrire les changements apportés.
- Mise à jour des liens internes pour refléter les changements apportés.

## Nouvelles Mises à Jour de Documentation (2025-11-18 — Décision Rapports + STEP4 GPU)
### Changements Clés
- Alignement sur la décision finale « Rapports supprimés » (code encore présent, fonctionnalités non exposées; documentation alignée sans endpoints rapports).
- Ajout des précisions STEP4 sur l’environnement GPU rétrocompatible (CUDA 11.x), auth HF et fallbacks v3.1→v2, exclusions `.mov`, politique de succès partiel.
- Correction de la forme de réponse de `/api/visualization/projects` (inclusion de `display_base` et `archive_timestamp`).

### Fichiers mis à jour
- `API_INSTRUMENTATION.md` — retrait des références aux endpoints rapports supprimés.
- `STEP4_ANALYSE_AUDIO.md` — ajout section v4.1 (2025-11-18) : GPU rétrocompatible, auth HF, fallbacks, OOM mitigations, exclusions `.mov`, succès partiel.
- `RESULTS_ARCHIVER_SERVICE.md` — suppression de la mention « reconstruction automatique des rapports » (archives uniquement).
- `REFERENCE_RAPIDE_DEVELOPPEURS.md` — mise à jour exemple de réponse `/api/visualization/projects` avec `display_base` et `archive_timestamp`.

### Notes
- Une suppression de code ultérieure peut être envisagée pour retirer définitivement `services/report_service.py` et les templates si désiré; la documentation est déjà alignée sur l’absence d’API de rapports.
