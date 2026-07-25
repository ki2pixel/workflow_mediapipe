# Audit Backend Complet — workflow_mediapipe

**Date** : 2026-07-25
**Périmètre** : `app_new.py`, `routes/`, `services/`, `config/`, `workflow_scripts/step{1..8}/`
**Méthodologie** : Analyse statique complète du code source, sans exécution de tests dynamiques (SAST).

---

## Table des matières

1. [Architecture](#1-architecture)
2. [Sécurité](#2-sécurité)
3. [Qualité de code & Tests](#3-qualité-de-code--tests)
4. [Workflow Scripts & Venvs](#4-workflow-scripts--venvs)
5. [Synthèse & Recommandations](#5-synthèse--recommandations)

---

## 1. Architecture

### 1.1 Stack applicative

```
┌─────────────────────────────────────────────┐
│  Gunicorn (workers=1, threads=4) / Flask dev│
├─────────────────────────────────────────────┤
│  app_new.py — factory, init, bg threads     │
├──────────────────┬──────────────────────────┤
│  routes/         │  services/ (18 modules)  │
│  api_routes.py   │  workflow_state.py       │
│  workflow_routes │  workflow_service.py     │
│  decorators.py   │  workflow_executor.py    │
│                  │  csv_service.py          │
│                  │  csv_downloader.py       │
│                  │  csv_monitor.py          │
│                  │  download_service.py     │
│                  │  download_history_repo   │
│                  │  cache_service.py        │
│                  │  performance_service.py  │
│                  │  monitoring_service.py   │
│                  │  filesystem_service.py   │
│                  │  webhook_service.py      │
│                  │  cleanup_service.py      │
│                  │  cleanup_monitor.py      │
│                  │  coral_tpu_orchestrator  │
│                  │  lemonfox_audio_service  │
│                  │  deepinfra_audio_service │
│                  │  results_archiver.py     │
├──────────────────┴──────────────────────────┤
│  config/                                    │
│  settings.py, security.py, workflow_cmds.py │
└─────────────────────────────────────────────┘
```

### 1.2 Blueprints & Endpoints

#### `api_bp` — préfixe `/api` (21 endpoints)

| Route | Méthode | Auth | Rôle |
|---|---|---|---|
| `/api/system_monitor` | GET | ❌ | CPU/RAM/GPU/disque |
| `/api/system/diagnostics` | GET | ❌ | Python/FFmpeg/GPU/Config |
| `/api/step_status/<step_key>` | GET | ❌ | Progression d'une étape |
| `/api/csv_monitor_status` | GET | ❌ | Santé du moniteur CSV/webhook |
| `/api/ping` | GET | ✅ Token | Health check |
| `/api/performance/metrics` | GET | ❌ | Profilage/cache/système |
| `/api/performance/reset` | POST | ✅ Token | Réinitialiser profilage |
| `/api/cache/stats` | GET | ❌ | Statistiques cache |
| `/api/cache/search` | GET | ❌ | Recherche dossiers cache |
| `/api/cache/list_today` | GET | ❌ | Dossiers cache du jour |
| `/api/cache/open` | POST | ✅ Token | Ouvrir dossier dans explorateur |
| `/api/cache/clear` | POST | ✅ Token | Vider le cache |
| `/api/csv_downloads_status` | GET | ❌ | Téléchargements actifs/récents |
| `/api/stats/dashboard` | GET | ❌ | Métriques tableau de bord |
| `/api/stats/history` | GET | ❌ | Historique performance |
| `/api/step4/lemonfox_audio` | POST | ❌ | Analyse STT Lemonfox |
| `/api/step4/deepinfra_audio` | POST | ❌ | Analyse STT DeepInfra |

#### `workflow_bp` — préfixe `/` (12 endpoints)

| Route | Méthode | Auth | Rôle |
|---|---|---|---|
| `/` | GET | ❌ | UI principale (`index_new.html`) |
| `/run/<step_key>` | POST | ✅ Token | Exécuter une étape |
| `/run_custom_sequence` | POST | ✅ Token | Exécuter une séquence |
| `/status/<step_key>` | GET | ❌ | Statut + logs d'une étape |
| `/stop/<step_key>` | POST | ✅ Token | Arrêter une étape |
| `/get_specific_log/<step_key>/<log_index>` | GET | ❌ | Lire fin de fichier log |
| `/get_specific_log_test/<step_key>/<log_index>` | GET | ✅ Token | Log sans cache (DEBUG) |
| `/sound-design/<filename>` | GET | ❌ | Fichier audio statique |
| `/test-sound` | GET | ❌ | Page de test |
| `/sequence/status` | GET | ❌ | Progression séquence |
| `/sequence/stop` | POST | ✅ Token | Arrêter séquence |
| `/cancel/<step_key>` | POST | ✅ Token | Annuler étape |

**Constats** :
- 7 endpoints API seulement protégés sur 21
- Les endpoints de monitoring et statistiques sont tous ouverts
- Les endpoints audio payants (`lemonfox_audio`, `deepinfra_audio`) n'ont **aucune authentification**

### 1.3 Services — Responsabilités

| Service | Rôle | Thread-safe |
|---|---|---|
| `WorkflowState` | State partagé thread-safe (RLock) | ✅ RLock |
| `WorkflowService` | Orchestration stateless des étapes/séquences | ✅ Stateless |
| `WorkflowExecutor` | Lancement subprocess + parsing progression | ⚠️ Daemon threads |
| `CacheService` | Wrapper Flask-Caching, stats | ⚠️ TOCTOU |
| `CSVService` | Historique téléchargements, normalisation URL | ✅ Via WorkflowState |
| `CSVDownloader` | Téléchargement background avec fallback | ⚠️ Daemon thread |
| `CSVMonitor` | Polling webhook (daemon 15s) | ✅ Event shutdown |
| `DownloadService` | Téléchargements HTTP Dropbox | ✅ Stateless |
| `DownloadHistoryRepo` | Persistance SQLite (WAL mode) | ✅ Thread-safe SQLite |
| `PerformanceService` | Métriques, profilage, alertes | ⚠️ ALERT_THRESHOLDS sans lock |
| `MonitoringService` | CPU/RAM/GPU/disque via psutil + pynvml | ✅ Stateless |
| `FilesystemService` | Recherche cache, explorateur, scan vidéos | ⚠️ Path validation |
| `WebhookService` | Fetch JSON externe avec cache TTL | ✅ RLock |
| `CleanupService` | Nettoyage projets/logs orphelins | ✅ Stateless |
| `CleanupMonitor` | Daemon nettoyage (12h) | ✅ Event shutdown |
| `CoralTPUOrchestrator` | Queue asyncio pour accès série TPU | ⚠️ Bloquant via `future.result()` |
| `LemonfoxAudioService` | STT cloud Lemonfox | ✅ Stateless |
| `DeepinfraAudioService` | STT cloud DeepInfra (Whisper) | ✅ Stateless |
| `ResultsArchiver` | Persistance artefacts d'analyse | ✅ Stateless |

### 1.4 Gestion d'état

| Composant | Stockage | Persistant ? |
|---|---|---|
| État workflow (étapes, logs, process) | Mémoire (`WorkflowState` singleton) | ❌ Volatil |
| Historique téléchargements | SQLite (`download_history.sqlite3`) | ✅ WAL mode |
| Cache | Mémoire (`SimpleCache` Flask-Caching) | ❌ Volatil |
| Métriques performance | Mémoire (deques) | ❌ Volatil |
| Stats profilage | Mémoire (`defaultdict`) | ❌ Volatil |
| Cache webhook | Mémoire (dict) | ❌ Volatil |

**Note** : `gunicorn.conf.py` force `workers=1` car le `WorkflowState` est en mémoire — configuration correcte et documentée.

### 1.5 Background threads

| Thread | Type | Intervalle | Arrêt gracieux |
|---|---|---|---|
| `CSVMonitorService` | Daemon | 15s | ✅ `threading.Event` |
| `OrphanCleanupService` | Daemon | 12h | ✅ `threading.Event` |
| `PerformanceService` monitor | Daemon | 30s | ✅ Flag + lock |
| `CoralTPU_AsyncLoop` | Daemon | Event-driven | ❌ Boucle infinie |
| Threads d'exécution d'étape | Daemon | Jusqu'à fin subprocess | ❌ Tué au `SIGTERM` |
| Threads de téléchargement | Daemon | Jusqu'à fin download | ❌ Tué au `SIGTERM` |
| Threads de séquence | Daemon | Jusqu'à fin séquence | ❌ Tué au `SIGTERM` |

### 1.6 Findings architecturaux

| ID | Sévérité | Description | Localisation |
|---|---|---|---|
| ARC-01 | 🔴 Critique | Couplage via `sys.modules` : `WorkflowService.run_step()` accède `app_new` via `sys.modules.get('app_new')`. Échoue si l'app est lancée via `wsgi.py`. | `services/workflow_service.py:262-273` |
| ARC-02 | 🟡 Moyen | `initialize_services()` appelée deux fois (module-level + `init_app()`). Le double-checked locking évite la double initialisation mais c'est un code smell. | `app_new.py:~260` |
| ARC-03 | 🟡 Moyen | `WorkflowCommandsConfig()` instancié à chaque appel de méthode au lieu d'être un singleton injecté. | `services/workflow_service.py` |
| ARC-04 | 🟢 Mineur | Pas de middleware CORS — le frontend doit être servi depuis la même origine. Limite la flexibilité de déploiement. | `app_new.py` |
| ARC-05 | 🟢 Mineur | Pas de structured logging (JSON, trace IDs). Logs bilingues (français/anglais). | Tous les services |
| ARC-06 | 🟢 Mineur | `gunicorn.conf.py` bind `0.0.0.0` — expose le service sur toutes les interfaces réseau. | `gunicorn.conf.py:10` |

---

## 2. Sécurité

### 2.1 Matrice des vulnérabilités

| ID | Sévérité | Catégorie | Description |
|---|---|---|---|
| SEC-01 | 🔴 **CRITIQUE** | Secrets exposés | Secrets de production dans `.env` (clés API Lemonfox, DeepInfra, Groq, HuggingFace, token worker, FLASK_SECRET_KEY). Si `.env` n'est pas dans `.gitignore`, les secrets sont dans le dépôt. |
| SEC-02 | 🔴 **CRITIQUE** | Auth bypass | Le token d'authentification interne est injecté dans le template HTML (`worker_token=worker_token`). Visible en `view-source` par tout visiteur. |
| SEC-03 | 🔴 **CRITIQUE** | Auth manquante | `/api/step4/lemonfox_audio` et `/api/step4/deepinfra_audio` sont des POST sans authentification — n'importe qui peut consommer des crédits API payants. |
| SEC-04 | 🟠 **HAUT** | CSRF | Aucune protection CSRF (pas de tokens, pas de `SameSite`). Tous les POST sont vulnérables. |
| SEC-05 | 🟠 **HAUT** | CORS | Aucune politique CORS configurée. Si `flask-cors` est ajouté sans restriction, toutes les origines auront accès. |
| SEC-06 | 🟠 **HAUT** | Rate limiting | Aucun rate limiting. Un attaquant peut brute-force le token worker ou saturer les endpoints coûteux. |
| SEC-07 | 🟠 **HAUT** | Injection commande | Le chemin utilisateur dans `/api/cache/open` passe par `subprocess.Popen`. La liste d'arguments empêche l'injection shell, mais un bypass de `relative_to(CACHE_ROOT)` permettrait l'exécution arbitraire. |
| SEC-08 | 🟠 **HAUT** | Dépendance vulnérable | `requests==2.31.0` est vulnérable à CVE-2024-35195 (fuite header proxy sur redirection cross-origin). Fixé dans `>=2.32.0`. |
| SEC-09 | 🟡 **Moyen** | TLS absent | Flask et Gunicorn bindent en HTTP uniquement (`0.0.0.0:5000/5003`). Le token worker transite en clair. |
| SEC-10 | 🟡 **Moyen** | Fuite partielle dans logs | `logger.info(f"...INTERNAL_WORKER_COMMS_TOKEN_ENV configured: '...{token[-5:]}'")` — 5 derniers caractères du token loggés. | `app_new.py:154` |
| SEC-11 | 🟡 **Moyen** | Environnement hérité | `os.environ.copy()` dans `workflow_executor.py:327` — toutes les variables d'env (incluant secrets) sont passées aux subprocess. |
| SEC-12 | 🟡 **Moyen** | Timing attack | `received_token != security_config.INTERNAL_WORKER_TOKEN` — comparaison non timing-safe. | `config/security.py:119` |
| SEC-13 | 🟡 **Moyen** | Debug mode | Si `DEBUG=true`, le debugger Flask expose une console Python interactive sur les erreurs. | `app_new.py` |
| SEC-14 | 🟡 **Moyen** | Commandes dans logs | Les commandes shell complètes sont écrites dans les fichiers de log, accessibles via `/get_specific_log`. | `workflow_executor.py:307` |
| SEC-15 | 🟢 **Bas** | Bind 0.0.0.0 | Exposition sur toutes les interfaces réseau sans TLS. | `gunicorn.conf.py` |
| SEC-16 | 🟢 **Bas** | Taille body illimitée | Pas de `MAX_CONTENT_LENGTH` configuré sur Flask. | `app_new.py` |
| SEC-17 | 🟢 **Bas** | SECRET_KEY par défaut | `'dev-key-change-in-production'` comme fallback si `FLASK_SECRET_KEY` absent. | `config/settings.py:86` |
| SEC-18 | 🟢 **Bas** | html.escape incohérent | Certains logs utilisent `html.escape()`, d'autres écrivent directement dans le JSON de réponse. | Multiple |

### 2.2 Détail des vulnérabilités critiques

#### SEC-01 : Secrets de production dans `.env`

**Fichier** : `.env`
**Risque** : Si `.env` est commité dans Git, toutes les clés API sont exposées publiquement. Même sans commit, un accès en lecture au fichier donne le contrôle complet.

**Clés concernées** :
- `LEMONFOX_API_KEY` — accès API payant Lemonfox
- `DEEPINFRA_API_KEY` — accès API payant DeepInfra
- `GROQ_API_KEY` — accès API Groq
- `HF_AUTH_TOKEN` / `HUGGINGFACE_HUB_TOKEN` — accès modèles HuggingFace
- `FLASK_SECRET_KEY` — fabrication de sessions Flask
- `INTERNAL_WORKER_COMMS_TOKEN` — bypass authentification

**Remédiation** :
1. Vérifier que `.env` est dans `.gitignore` **immédiatement**
2. Si le fichier a déjà été commité : `git filter-repo` pour purger l'historique
3. Faire tourner (regénérer) **toutes** les clés API immédiatement
4. Mettre en place un gestionnaire de secrets (vault, sealed secrets) ou restreindre les permissions à `600`

#### SEC-02 : Token d'authentification exposé au frontend

**Fichier** : `routes/workflow_routes.py`, ligne ~44
```python
worker_token = SecurityConfig().INTERNAL_WORKER_TOKEN or ""
return render_template('index_new.html', ..., worker_token=worker_token, ...)
```

**Risque** : Le token `INTERNAL_WORKER_COMMS_TOKEN` est injecté dans le HTML de la page d'accueil. Tout visiteur peut le lire avec `view-source:`. Cela rend l'authentification `@require_internal_worker_token` **totalement inefficace** — n'importe qui peut appeler les endpoints protégés.

**Remédiation** : Supprimer `worker_token` du contexte de template. Le frontend ne devrait jamais connaître le token worker. Si le frontend a besoin d'authentification, utiliser un mécanisme séparé (session Flask, JWT avec cookie HttpOnly).

#### SEC-03 : Endpoints audio sans authentification

**Fichier** : `routes/api_routes.py`, endpoints `lemonfox_audio_analysis` et `deepinfra_audio_analysis`

**Risque** : Ces deux endpoints POST déclenchent des appels à des API externes **payantes** (Lemonfox, DeepInfra). Sans authentification, n'importe qui peut :
- Épuiser les crédits API
- Déclencher des traitements coûteux (GPU, bande passante)
- Potentiellement causer des frais financiers

**Remédiation** : Ajouter `@require_internal_worker_token` sur ces deux endpoints.

### 2.3 Défenses présentes

- ✅ Protection path traversal via `validate_file_path()` (utilisé dans `/sound-design/`)
- ✅ Commandes subprocess en liste (pas de shell string) → pas d'injection shell
- ✅ Aucun `eval()`/`exec()` sur entrée utilisateur
- ✅ Validation des tokens de production au démarrage (refuse de démarrer avec valeurs par défaut)
- ✅ Écritures atomiques dans les services audio (`write to .tmp` → `os.replace()`)
- ✅ Sanitization des noms de fichiers à l'extraction d'archives
- ✅ Requêtes SQL paramétrées dans `DownloadHistoryRepository`

---

## 3. Qualité de code & Tests

### 3.1 Gestion d'erreurs

#### Problèmes critiques

| ID | Description | Localisation | Impact |
|---|---|---|---|
| CQ-01 | `except:` nu — capture `KeyboardInterrupt`, `SystemExit`, `MemoryError` | `webhook_service.py:52`, `workflow_service.py:638`, `lemonfox_audio_service.py:53`, `deepinfra_audio_service.py:68,72` | Interruption impossible, masquage d'erreurs fatales |
| CQ-02 | `except Exception` trop larges (~520 occurrences) — certaines silencieuses | `workflow_executor.py:164`, `cache_service.py:382` (silent pass), `csv_service.py:24,55,64` | Erreurs masquées sans log |
| CQ-03 | Pas de hiérarchie d'exceptions custom — tout est `ValueError`, `RuntimeError`, `Exception` | Projet entier | Pas de granularité dans la gestion d'erreurs |

#### Patterns corrects observés

- ✅ `workflow_executor.py` capture `FileNotFoundError`, `subprocess.TimeoutExpired`, `requests.RequestException` séparément
- ✅ `deepinfra_audio_service.py` a un retry avec backoff exponentiel
- ✅ `download_service.py` utilise un `DownloadResult` dataclass pour les erreurs structurées
- ✅ Les services audio retournent `result.success` + `result.error`

### 3.2 Tests

#### Couverture

| Composant | Tests unitaires | Tests intégration | Statut |
|---|---|---|---|
| `WorkflowState` | ✅ 22 tests | — | Excellent |
| `WorkflowService` | ✅ 17 tests | — | Bon |
| `CSVService` (normalisation) | ✅ Dédié | — | Bon |
| `DownloadService` | ✅ Présent | — | OK |
| `FilesystemService` | ✅ Présent | — | OK |
| `CleanupService` | ✅ Présent | — | OK |
| `CoralTPUOrchestrator` | ✅ Présent | — | OK |
| `DeepinfraAudioService` | ✅ Présent | ✅ Présent | OK |
| `LemonfoxAudioService` | ✅ Présent | ✅ Présent | OK |
| `MonitoringService` | ✅ Partiel | — | OK |
| `CacheService` | ❌ Aucun | — | **Gap** |
| `PerformanceService` | ❌ Aucun | — | **Gap** |
| `WebhookService` | ⚠️ Concurrence seule | — | **Gap** |
| `DownloadHistoryRepo` | ❌ Aucun | — | **Gap** |
| `csv_monitor` | ❌ Aucun | ⚠️ Dry-run seul | **Gap** |

#### Qualité des tests

- ✅ `conftest.py` a un fixture `clean_workflow_state` autouse qui réinitialise les singletons
- ✅ `DRY_RUN_DOWNLOADS=true` dans `pytest_sessionstart` — empêche les vrais téléchargements
- ✅ `pytest.ini` exclut correctement les tests dépendant d'environnements spécifiques
- ✅ `tests/legacy/README.md` documente la dépréciation proprement
- ⚠️ Tests d'intégration API manquent pour `/api/performance/*`, `/api/cache/*`

### 3.3 Type safety

- ✅ `services/types.py` définit des enums propres (`StepKey`, `StepStatus`, `CSVDownloadStatus`)
- ✅ `config/settings.py` utilise `@dataclass` avec annotations
- ✅ Plusieurs services utilisent `@dataclass` pour les résultats structurés
- ❌ Pas de configuration `mypy` (`.mypy_cache/` existe mais orphelin)
- ❌ `app_new.py` n'a **aucun** type hint
- ❌ `Dict[str, Any]` utilisé partout au lieu de dataclasses typées
- ❌ `workflow_executor.py:parse_and_update_progress` utilise `dict` minuscule au lieu de `Dict`

### 3.4 Concurrence

| Composant | Mécanisme | Problème |
|---|---|---|
| `WorkflowState` | `RLock` sur toutes les méthodes publiques | ✅ Correct |
| `CacheService.cache_instance` | Module-level global | ⚠️ TOCTOU — lu hors lock dans `cached_with_stats()` |
| `PerformanceService.ALERT_THRESHOLDS` | Module-level dict | ⚠️ Muté sans lock dans `update_alert_thresholds()` |
| `CoralTPUOrchestrator` | Singleton + asyncio queue + `future.result()` bloquant | ⚠️ Pas de timeout sur `future.result()` |
| `WebhookService._cache` | `RLock` | ✅ Correct |

### 3.5 Duplication de code

| ID | Description | Impact |
|---|---|---|
| CQ-04 | `lemonfox_audio_service.py` et `deepinfra_audio_service.py` partagent ~400 lignes quasi-identiques (`_apply_speech_smoothing`, `_validate_project_and_video`, `_get_video_duration_ffprobe`, `_build_frame_timeline`, `_write_step4_json_atomically`). | Maintenance : toute correction doit être faite 2x |
| CQ-05 | `create_frontend_safe_config()` dans `app_new.py:261-282` est quasi-identique à `CacheService.get_cached_frontend_config()` — version `app_new` probablement morte. | Code mort |
| CQ-06 | Trois fonctions de formatage de durée différentes : `WorkflowService.calculate_step_duration()`, `WorkflowService.format_duration_seconds()`, `app_new.format_duration_seconds()`. | Incohérence potentielle |

### 3.6 Autres findings

| ID | Sévérité | Description |
|---|---|---|
| CQ-07 | 🟢 Mineur | Log de debug avec emoji dans `app_new.py:318` : `"🔥🔥🔥 [SEQUENCE_WORKER_TEST]..."` — code de debug résiduel. |
| CQ-08 | 🟢 Mineur | Logging bilingue (français/anglais) rend le parsing et l'alerting plus complexes. |
| CQ-09 | 🟢 Mineur | `csv_service.py` référence encore `LEGACY_DOWNLOAD_HISTORY_FILE` pour la migration — à supprimer une fois la migration terminée. |
| CQ-10 | 🟢 Mineur | `csv_service.py` et `csv_monitor.py` s'importent mutuellement via des late imports (risque d'import circulaire). |

---

## 4. Workflow Scripts & Venvs

### 4.1 Environnements virtuels

| Nom | Python | Étapes | Dépendances clés |
|---|---|---|---|
| `env` | `config.get_venv_python("env")` | 1, 2, 6, 7, 8 | Flask, rarfile, ijson, psutil |
| `transnet_env` | `config.get_venv_python("transnet_env")` | 3 (PyTorch) | torch, ffmpeg-python, scenedetect |
| `transnet_cv5_env` | `config.get_venv_python("transnet_cv5_env")` | 3 (OpenCV5 ONNX) | opencv-python-headless>=5.0, onnxruntime |
| `coral_env` | `config.get_venv_python("coral_env")` | 3, 4, 5 (TPU) | tflite-runtime, scipy, scikit-learn, numpy, numba |
| `audio_env` | `config.get_venv_python("audio_env")` | 4 (Pyannote/Cloud) | torch, pyannote.audio, speechbrain, librosa |
| `tracking_env_slim` | `config.get_venv_python("tracking_env_slim")` | 5 (MediaPipe) | mediapipe, opencv-python, numpy |
| `tracking_cv5_env` | `config.get_venv_python("tracking_cv5_env")` | 5 (OpenCV5) | opencv-python-headless>=5.0, numpy |
| `insightface_env` | `config.get_venv_python("insightface_env")` | 5 (InsightFace GPU) | insightface, onnxruntime-gpu |

### 4.2 Analyse par étape

#### STEP 1 — Extraction d'archives

- **Fonction** : Extrait ZIP/RAR/TAR de `~/Téléchargements` vers `projets_extraits/`
- **Venv** : `env`
- **Erreurs** : ✅ Capture `BadZipFile`, `BadRarFile`, `ReadError` ; `finally` nettoie les dossiers temporaires
- **Ressources** : ✅ `shutil.rmtree(temp_extract_dir)` dans `finally` ; `DELETE_ARCHIVE_AFTER_SUCCESS` pour supprimer la source
- **Sécurité** : ✅ Protection path traversal via `FilenameSanitizer` + `validate_extraction_path()`

#### STEP 2 — Conversion vidéo

- **Fonction** : Ré-encode vidéos en 25fps H.264 AAC via FFmpeg (NVENC avec fallback CPU)
- **Venv** : `env`
- **Concurrence** : ✅ `ThreadPoolExecutor(max_workers=3)` avec `PROGRESS_LOCK`
- **Erreurs** : ✅ Fallback GPU→CPU par vidéo ; code de sortie 1 si échec global
- **Ressources** : ⚠️ 3 sessions NVENC simultanées peuvent saturer la VRAM GPU
- **Dépendance CWD** : ⚠️ `WORK_DIR = Path(os.getcwd())` — repose sur le `cwd` défini par l'orchestrateur

#### STEP 3 — Détection de scènes

**3 variantes** (OpenCV5 > Coral TPU > Legacy PyTorch, résolu à la construction de la config) :

| Variante | Venv | Moteur | Multiprocessing |
|---|---|---|---|
| PyTorch (`run_transnet.py`) | `transnet_env` | TransNetV2 via PyTorch + TorchScript | `mp.Pool` si `num_workers > 1` |
| OpenCV5 (`run_transnet_cv5.py`) | `transnet_cv5_env` | TransNetV2 ONNX via OpenCV DNN | Séquentiel uniquement |
| TPU (`run_scene_detect_tpu.py`) | `coral_env` | MobileNetV2 INT8 sur Edge TPU | Séquentiel |

**Findings** :

| ID | Sévérité | Description |
|---|---|---|
| WF-01 | 🔴 Critique | `run_scene_detect_tpu.py:25` : `sys.exit(1)` au **niveau module** si l'import TFLite échoue. Crash immédiat du processus si le TPU est absent, au lieu de reporter une erreur. |
| WF-02 | 🟡 Moyen | `run_transnet.py` : variables globales mutables (`WINDOW_SIZE`, `WINDOW_STRIDE`) — fonctionne car chaque worker Pool a son namespace, mais fragile. |
| WF-03 | 🟡 Moyen | `run_transnet.py` : `ffmpeg` output closure utilise `process.wait(timeout=2)` sans vérifier si le processus est déjà mort. |

#### STEP 4 — Analyse audio

**4 variantes** (Coral TPU > Pyannote/Lemonfox/DeepInfra) :

| Variante | Venv | Moteur |
|---|---|---|
| Pyannote (`run_audio_analysis.py`) | `audio_env` | pyannote/speaker-diarization-3.1 |
| Lemonfox (`run_audio_analysis_lemonfox.py`) | `audio_env` | API cloud Lemonfox → fallback Pyannote |
| DeepInfra (`run_audio_analysis_deepinfra.py`) | `audio_env` | API cloud DeepInfra (Whisper) → fallback Pyannote |
| TPU (`run_audio_diarization_tpu.py`) | `coral_env` | YAMNet INT8 + ECAPA-TDNN + clustering spectral |

**Findings** :

| ID | Sévérité | Description |
|---|---|---|
| WF-04 | 🟠 Haut | `run_audio_analysis.py` : `_run_cpu_diarization_subprocess` spawn `sys.executable` avec le même script. `--cpu_diarize_wav` est terminal, mais si les arguments sont mal configurés, risque de récursion infinie. |
| WF-05 | 🟡 Moyen | `run_audio_diarization_tpu.py` : `_tpu_lock` global déclaré mais jamais assigné — code vestigiel. Les workers `ThreadPoolExecutor` accèdent au TPU en parallèle, ce qui peut causer des contentions sur le bus USB. |
| WF-06 | 🟡 Moyen | `run_audio_analysis.py` : caches globaux (`_GLOBAL_EMBEDDING_MODEL`, `_GLOBAL_INFERENCE`) sans lock — OK en single-video, risqué en mode multi-thread. |

#### STEP 5 — Tracking

- **Fonction** : Détection + suivi de visages via MediaPipe ou InsightFace
- **Orchestrateur** : `run_tracking_manager.py` — distribue les vidéos sur workers GPU/CPU
- **Venv** : `tracking_env_slim` (manager), `insightface_env` (InsightFace workers), `tracking_cv5_env` (OpenCV5)
- **Architecture** : Manager spawn des subprocess workers avec le Python du venv approprié

**Findings** :

| ID | Sévérité | Description |
|---|---|---|
| WF-07 | 🟡 Moyen | `run_tracking_manager.py` : héritage d'environnement (`os.environ.copy()`) — le manager dans `tracking_env_slim` peut fuiter des paths vers les workers InsightFace. |
| WF-08 | 🟢 Mineur | `process_video_worker.py` : `np.complex_ = np.complex128` — monkey-patch fragile pour compatibilité MediaPipe. |
| WF-09 | 🟢 Mineur | `process_video_worker_multiprocessing.py` : `mp.set_start_method('spawn', force=True)` — crash si déjà défini ailleurs. |
| WF-10 | 🟢 Mineur | InsightFace `detect_every_n` throttling : réutilise `_last_detections`, peut causer des bbox stale. |

#### STEP 6 — Réduction JSON

- **Fonction** : Réduit les JSONs tracking/audio en schémas compacts via `ijson` streaming
- **Venv** : `env`
- **Écriture** : ✅ Atomique via `os.replace(tmp, final)`
- **Risque** : ⚠️ Réduction in-place — si le processus est tué pendant le streaming, le fichier temporaire peut rester orphelin

#### STEP 7 — Preprocessing After Effects

- **Fonction** : Prépare les JSONs pour import After Effects (index `dataByFrame`, alignement audio)
- **Venv** : `env`
- **Parsing** : ✅ Streaming ijson
- **Risque** : ⚠️ Détection de schéma fragile (vérifie `ae_preprocessed`, `dataByFrame`, `frames`)

#### STEP 8 — Finalisation

- **Fonction** : Archive artefacts, copie projets vers `OUTPUT_DIR`, supprime la source
- **Venv** : `env`
- **Copie** : ✅ Multi-stratégie (`shutil.copytree` → `rsync` → `cp` → `os.walk` manuel)

**Findings** :

| ID | Sévérité | Description |
|---|---|---|
| WF-11 | 🟠 Haut | `finalize_and_copy.py` : suppression de la source (`_safe_rmtree`) inconditionnelle après copie. Si la copie est partielle et la suppression incomplète, des données peuvent être perdues. `_safe_rmtree` capture les erreurs de permission silencieusement. |

### 4.3 Orchestration

**workflow_executor.py** — `run_process_async()` :
- ✅ Redirection stdout/stderr vers fichier de log
- ✅ Rotation de logs à 5MB (5 backups)
- ✅ Timeout configurable (1800s par défaut) avec escalade `SIGTERM` → `SIGKILL`
- ✅ Injection `LD_LIBRARY_PATH` pour libs CUDA + Coral
- ✅ Parsing de progression multi-format (regex)
- ⚠️ Pas de `preexec_fn=os.setsid` — les subprocess peuvent devenir orphelins si le parent est tué
- ⚠️ Double système de logs : les scripts écrivent dans `logs/stepN/`, l'exécuteur écrit dans `logs/step_STEPX.log`

**CoralTPUOrchestrator** :
- File d'attente asyncio pour sérialiser l'accès au TPU
- `submit_task()` bloque l'appelant avec `future.result()` — **pas vraiment asynchrone**
- Pas de timeout sur `future.result()` — si le worker TPU bloque, l'appelant bloque indéfiniment
- Pas de health check du device Coral

---

## 5. Synthèse & Recommandations

### 5.1 Matrice consolidée des findings

| Priorité | ID | Catégorie | Description |
|---|---|---|---|
| **P0** | SEC-01 | Sécurité | Secrets de production dans `.env` — rotation immédiate requise |
| **P0** | SEC-02 | Sécurité | Token worker exposé dans le template HTML |
| **P0** | SEC-03 | Sécurité | Endpoints audio payants sans authentification |
| **P0** | WF-01 | Workflow | `sys.exit(1)` au import TFLite dans step3 TPU |
| **P1** | ARC-01 | Architecture | Couplage `sys.modules` — échec sous wsgi.py |
| **P1** | SEC-04 | Sécurité | Absence de protection CSRF |
| **P1** | SEC-06 | Sécurité | Absence de rate limiting |
| **P1** | SEC-08 | Sécurité | `requests==2.31.0` vulnérable (CVE-2024-35195) |
| **P1** | WF-04 | Workflow | Risque de récursion infinie dans step4 Pyannote |
| **P1** | WF-11 | Workflow | Risque de perte de données dans step8 |
| **P2** | SEC-09 | Sécurité | Pas de HTTPS/TLS |
| **P2** | SEC-10 | Sécurité | Token partiel dans les logs |
| **P2** | SEC-11 | Sécurité | Environnement complet hérité par les subprocess |
| **P2** | SEC-12 | Sécurité | Comparaison token non timing-safe |
| **P2** | CQ-01 | Qualité | `except:` nus (4 occurrences) |
| **P2** | CQ-04 | Qualité | ~400 lignes dupliquées dans les services audio |
| **P2** | CQ-03 | Qualité | Pas de hiérarchie d'exceptions custom |
| **P2** | ARC-02 | Architecture | `initialize_services()` appelée 2x |
| **P3** | ARC-04 | Architecture | Pas de middleware CORS |
| **P3** | ARC-05 | Architecture | Pas de structured logging |
| **P3** | CQ-05 | Qualité | Code mort `create_frontend_safe_config()` |
| **P3** | CQ-07 | Qualité | Log de debug résiduel avec emoji |
| **P3** | SEC-15 | Sécurité | Bind 0.0.0.0 dans gunicorn.conf.py |
| **P3** | SEC-17 | Sécurité | SECRET_KEY faible par défaut |
| **P3** | WF-02 | Workflow | Variables globales mutables step3 PyTorch |

### 5.2 Quick wins (actions < 1h)

1. **Supprimer `worker_token` du template** (`workflow_routes.py:~44`) — correction 1 ligne
2. **Ajouter `@require_internal_worker_token`** sur `lemonfox_audio_analysis` et `deepinfra_audio_analysis` — 2 décorateurs
3. **Upgrader `requests`** à `>=2.32.0` dans tous les `requirements*.txt`
4. **Ajouter `MAX_CONTENT_LENGTH`** dans la config Flask (ex: 500MB)
5. **Supprimer les `except:` nus** (4 occurrences) — remplacer par `except Exception`
6. **Supprimer le log de debug emoji** (`app_new.py:318`)
7. **Ajouter `secrets.compare_digest()`** dans `config/security.py:119` pour la comparaison de token
8. **Ajouter un timeout** sur `future.result()` dans `CoralTPUOrchestrator.submit_task()`

### 5.3 Chantiers recommandés

| Chantier | Effort estimé | Impact |
|---|---|---|
| **Refacto `sys.modules` → injection propre** : Remplacer l'accès à `sys.modules` dans `WorkflowService` par de la dependency injection. Passer `run_process_async` comme callable au constructeur. | Moyen | Élimine le couplage fragile |
| **Factorisation services audio** : Extraire les ~400 lignes communes entre `LemonfoxAudioService` et `DeepinfraAudioService` dans une classe de base `BaseAudioService`. | Moyen | Maintenance, cohérence |
| **Hiérarchie d'exceptions** : Créer `exceptions.py` avec `WorkflowError`, `StepExecutionError`, `ConfigError`, `TokenValidationError`, `AudioServiceError`. | Moyen | Gestion d'erreurs granulaire |
| **Rate limiting + CSRF** : Ajouter Flask-Limiter (rate limiting) et Flask-WTF (CSRF). Configurer `MAX_CONTENT_LENGTH`. | Moyen | Sécurité |
| **Tests manquants** : Ajouter des tests unitaires pour `CacheService`, `PerformanceService`, `WebhookService`, `DownloadHistoryRepository`. | Important | Couverture |
| **Configuration mypy** : Ajouter `mypy.ini` avec `disallow_untyped_defs = False` initialement, resserrer progressivement. | Moyen | Type safety |
| **TLS** : Configurer HTTPS sur Gunicorn (certificat Let's Encrypt) ou placer un reverse proxy (nginx/Caddy) devant. | Moyen | Sécurité |
| **Structured logging** : Adopter `structlog` ou `python-json-logger` avec trace IDs par requête. | Important | Observabilité |
| **Step3 TPU graceful degradation** : Remplacer `sys.exit(1)` par une exception rattrapable avec fallback. | Faible | Robustesse |

### 5.4 Note globale

**B+** — L'architecture est solide avec une bonne séparation routes/services, un état thread-safe via `RLock`, une couverture de tests correcte sur le cœur, et des scripts de workflow robustes. Les problèmes sont concentrés sur la sécurité (3 vulnérabilités critiques nécessitant une action immédiate), la maintenance (duplication de code, couplage `sys.modules`), et la qualité (gestion d'erreurs incohérente, tests manquants en périphérie).

---

*Rapport généré le 2026-07-25 par analyse statique complète du codebase.*
*Périmètre : 42 fichiers analysés dans `app_new.py`, `routes/`, `services/`, `config/`, `workflow_scripts/step{1..8}/`.*
