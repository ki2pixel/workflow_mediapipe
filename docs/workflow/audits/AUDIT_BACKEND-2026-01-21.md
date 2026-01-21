### Résumé Exécutif
L'application est une solution sophistiquée d'orchestration de traitement vidéo (ETL) conçue pour s'exécuter localement ou sur un serveur contrôlé (Ubuntu/GPU). L'architecture est modulaire et utilise abondamment le multi-threading et le multi-processing pour gérer des tâches lourdes (FFmpeg, IA/ML).

**Points forts :**
*   **Architecture Modulaire :** Séparation claire entre Routes, Services, Config et Scripts Workers.
*   **Gestion de la Concurrence :** Utilisation correcte des verrous (`RLock`) pour les ressources partagées (`WorkflowState`, `CSVService`).
*   **Robustesse :** Gestion des ressources via Context Managers (`VideoResourceManager`) et nettoyage automatique des fichiers temporaires.
*   **Optimisation :** Profilage fin des performances et stratégies de fallback (GPU -> CPU, Pyannote -> Lemonfox).

**Points d'attention majeurs :**
*   **Sécurité :** Certaines commandes système sont exécutées avec des arguments dynamiques qui nécessitent une validation stricte.
*   **Scalabilité :** La persistance basée sur des fichiers JSON (`download_history.json`) posera problème si l'application passe en mode multi-processus (ex: Gunicorn avec plusieurs workers).
*   **Complexité :** La logique de l'étape 5 (Tracking) est extrêmement complexe avec beaucoup d'injection de variables d'environnement.

---

### 1. Architecture et Qualité du Code

#### 1.1. Structure du projet
L'utilisation du pattern **Service Layer** (dans `services/`) injecté dans les **Blueprints** Flask (`routes/`) est excellente. Cela découple la logique métier de la couche HTTP.
*   **Point positif :** L'initialisation via `WorkflowService.initialize()` et le singleton `WorkflowState` garantit une source de vérité unique pour l'état de l'application.
*   **Amélioration :** `app_new.py` contient encore trop de logique d'initialisation (logging, threads de monitoring). Cela devrait être déplacé dans une fonction `create_app` plus propre ou un `AppFactory`.

#### 1.2. Gestion des Dépendances
Le chargement dynamique des modules (ex: `mediapipe`, `pynvml`) est bien géré pour éviter les crashs si les dépendances optionnelles manquent.
*   **Observation :** `services/__init__.py` utilise un `__getattr__` personnalisé pour l'import lazy. C'est astucieux mais rend l'analyse statique et l'autocomplétion difficiles dans les IDE.

---

### 2. Audit de Sécurité

#### 2.1. Injection de Commandes (Subprocess)
L'application utilise massivement `subprocess.Popen`.
*   **Analyse :** La plupart des appels utilisent une liste d'arguments (`['cmd', arg1, arg2]`), ce qui protège contre l'injection shell directe.
*   **Statut (2026-01-21) :** Ce risque est désormais **atténué**. `config.settings` expose `CACHE_ROOT_DIR` (ENV) et deux garde-fous (`DISABLE_EXPLORER_OPEN`, `ENABLE_EXPLORER_OPEN`). `FilesystemService.open_path_in_explorer()` refuse toute ouverture si l'application n'est pas en mode DEBUG, si l'environnement est headless (`DISPLAY`/`WAYLAND_DISPLAY` absents) ou si la cible sort du `CACHE_ROOT_DIR`. Les tests unitaires (`tests/unit/test_filesystem_service.py`) couvrent ces cas. 
*   **Recommandation résiduelle :** Documenter clairement l’activation volontaire d’`ENABLE_EXPLORER_OPEN=1` lorsque l’application est exécutée sur un poste bureau contrôlé ; le laisser à 0 pour tout déploiement serveur/headless.

#### 2.2. Validation des Entrées (Path Traversal)
*   **Point positif :** `utils/filename_security.py` implémente une classe `FilenameSanitizer` robuste pour l'extraction d'archives. C'est une excellente pratique.
*   **Point positif :** `config/security.py` possède une fonction `validate_file_path` qui vérifie que les chemins sont relatifs aux dossiers autorisés.

#### 2.3. Authentification
*   **Observation :** Les décorateurs `@require_internal_worker_token` et `@require_render_register_token` protègent les routes sensibles.
*   **Risque (Faible) :** Les tokens sont stockés dans `config.security.py`. Si `DEBUG=True`, des valeurs par défaut non sécurisées ("dev-...") sont utilisées. Assurez-vous que la production force toujours `strict=True`.

---

### 3. Concurrence et Performance

#### 3.1. Modèle d'Exécution
Flask tourne en mode `threaded=True`.
*   **Statut (2026-01-21) :** Résolu via la migration officielle vers **SQLite** (`services/download_history_repository.py`). `CSVService.initialize()` crée la base `download_history.sqlite3`, applique WAL et relaie toutes les lectures/écritures via le repository (`upsert_many`, `replace_all`). Le script `scripts/migrate_download_history_to_sqlite.py` assure l'import des anciens `download_history.json` avant suppression. 
*   **Recommandation résiduelle :** Vérifier que `DOWNLOAD_HISTORY_DB_PATH` pointe vers un volume partagé si plusieurs machines doivent consulter l’historique.

#### 3.2. Workers Longue Durée
Les étapes du workflow (Step 1-7) sont lancées via `subprocess.Popen` et gérées par `WorkflowState`.
*   **Analyse :** C'est la bonne approche pour éviter de bloquer le thread principal de Flask (GIL).
*   **Étape 5 (Tracking) :** Le script `process_video_worker_multiprocessing.py` utilise `ProcessPoolExecutor`.
    *   **Attention :** Le chargement de `.env` à l'intérieur des sous-processus est critique. Le mécanisme actuel (`load_dotenv` conditionnel) semble correct, mais la gestion de la mémoire VRAM GPU lors du multiprocessing peut être instable. Le code semble gérer cela en forçant `num_workers=1` si le GPU est utilisé, ce qui est prudent.

#### 3.3. Monitoring
`MonitoringService` utilise `psutil` et `pynvml`. C'est propre et efficace. Le polling frontend est adaptatif (`PollingManager.js`), ce qui réduit la charge serveur.

---

### 4. Gestion des Données et Persistance

#### 4.1. Système de Fichiers
L'application dépend fortement d'une structure de dossiers spécifique (`projets_extraits`, `archives`, `logs`).
*   **Statut (2026-01-21) :** **Atténué** — `CACHE_ROOT_DIR` est désormais configurable (ENV) et normalisé (`Path.resolve()`) dans `config.settings.Config.__post_init__()`. Tous les appels (`FilesystemService`, scripts STEP) consomment ce chemin centralisé.
*   **Recommandation :** Définir `CACHE_ROOT_DIR` par environnement (local vs serveur) pour refléter la hiérarchie réelle des données et supprimer les mentions restantes de `/mnt/cache` dans la documentation historique.

#### 4.2. Archives et Résultats
`services/results_archiver.py` utilise un hash SHA256 du contenu vidéo pour indexer les résultats.
*   **Excellent :** Cela évite les collisions de noms et permet de retrouver les analyses même si le fichier est renommé.

---

### 5. Analyse Spécifique des Services

#### 5.1. `DownloadService`
*   Gère les téléchargements Dropbox.
*   **Point fort :** Validation de l'intégrité des ZIP (`_validate_download`) et renommage en cas de conflit.
*   **Risque :** Le timeout de requête est long (3600s), ce qui est nécessaire pour les gros fichiers, mais attention aux connexions "zombies".

#### 5.2. `LemonfoxAudioService` (Step 4)
*   Implémente une logique de téléversement avec transcodage conditionnel (ffmpeg) si le fichier est trop gros.
*   **Amélioration :** La gestion des erreurs API (413 Payload Too Large) est bien gérée avec un message clair.

#### 5.3. `CSVService` & `WebhookService`
*   Transition de l'architecture MySQL/Airtable vers une source unique Webhook JSON.
*   Le code semble robuste, avec une normalisation des URLs pour éviter les doublons.

---

### 6. Synthèse et Recommandations Prioritaires

| Priorité | Catégorie | Problème / Observation | Recommandation |
| :--- | :--- | :--- | :--- |
| **Haute** | **Architecture** | Persistance JSON non safe pour multi-process | **RÉSOLU** : Migration de `download_history.json` vers SQLite (repository `download_history_repository`, refactor `CSVService`, script CLI `scripts/migrate_download_history_to_sqlite.py`, exécuté avec succès, fichiers legacy supprimés). |
| **Moyenne** | **Sécurité** | `/mnt/cache` en dur et `open_path_in_explorer` | **RÉSOLU** : `CACHE_ROOT_DIR` (ENV) remplace les chemins en dur et `open_path_in_explorer()` est bloqué par défaut en prod/headless (`DISABLE_EXPLORER_OPEN`, `ENABLE_EXPLORER_OPEN`, détection DISPLAY/WAYLAND). Tests : `pytest -q tests/unit/test_filesystem_service.py`. |
| **Moyenne** | **Maintenabilité** | Logique Step 5 très dispersée | **RÉSOLU (2026-01-21)** : Refactor `workflow_scripts/step5/run_tracking_manager.py` avec `_EnvConfig` (lecture typed des ENV), helpers `_build_subprocess_env`/`_collect_cuda_lib_paths` pour l'injection `LD_LIBRARY_PATH`, et normalisation du flux GPU/CPU. Validation : `python3 -m py_compile workflow_scripts/step5/run_tracking_manager.py`. |
| **Faible** | **Code** | Nettoyage `app_new.py` | Déplacer l'initialisation des threads (Polling) dans une fonction `init_app()` propre. |

**Conclusion :**
Le backend est de qualité professionnelle, conçu spécifiquement pour des charges de travail lourdes et locales. Il privilégie la fiabilité (retry, fallback, verrous) sur la scalabilité horizontale pure (stateless), ce qui est cohérent pour un moteur de workflow vidéo. Les risques de sécurité sont principalement liés au contexte d'exécution (accès système local) et sont atténués si l'environnement est contrôlé.