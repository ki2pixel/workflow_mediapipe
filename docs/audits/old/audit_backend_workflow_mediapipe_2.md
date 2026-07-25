---

# Audit Backend Complet — `workflow_mediapipe`

## Vue d'ensemble

Application Flask backend orchestrant un pipeline de traitement video/audio en 8 etapes (MediaPipe, Coral TPU, TransNet, Pyannote, Lemonfox/DeepInfra). Architecture modulaire avec separation des couches (routes -> services -> state). L'application tourne sur une machine Ubuntu locale avec GPU NVIDIA et/ou Coral Edge TPU.

---

## 1. Architecture & Structure

### Points forts

- **Blueprints Flask** : separation claire entre `api_bp` (./routes/api_routes.py) et `workflow_bp` (./routes/workflow_routes.py)
- **Service layer pattern** : 17 services avec methodes statiques (./services/)
- **WorkflowState singleton** (./services/workflow_state.py) : gestion d'etat centralisee avec `threading.RLock`
- **Configuration centralisee** : `Config` dataclass (./config/settings.py) avec `__post_init__` pour normalisation des paths
- **Pipeline configurable** : `WorkflowCommandsConfig` (./config/workflow_commands.py) definit les commandes par step avec patterns de progression regex
- **Isolation des venvs** : chaque step a son propre venv (`env`, `audio_env`, `coral_env`, `tracking_env_slim`, `transnet_cv5_env`, etc.)

### Points faibles

- **`app_new.py` melange responsabilites** : initialise l'app Flask ET contient encore de la logique metier (`execute_step_sequence_worker`, `create_frontend_safe_config`, routes directes)
- **Imports circulaires potentiels** : `workflow_executor.py` instancie un nouveau `WorkflowCommandsConfig` au niveau module, et `workflow_service.py` en instancie un aussi dans `get_step_status()`

---

## 2. Securite

### CRITICAL

| # | Probleme | Fichier | Ligne(s) |
|---|----------|---------|----------|
| S1 | **Routes dupliquees** `/sound-design/<filename>` et `/test-sound` definies 2x dans le meme blueprint — Flask garde uniquement la derniere, l'autre est du code mort silencieux | ./routes/workflow_routes.py | 293/441, 316/464 |
| S2 | **Aucune configuration CORS** — aucune trace de `flask-cors` ou de headers `Access-Control-*` | Global | - |
| S3 | **Aucun rate limiting** — aucun `flask-limiter` ou mechanisme equivalent | Global | - |
| S4 | **Pas de WSGI server** — l'app utilise `app.run()` (dev server Flask) en production | ./app_new.py | 461-466 |

### HIGH

| # | Probleme | Fichier | Ligne(s) |
|---|----------|---------|----------|
| S5 | **1 seul endpoint authentifie** sur 31 : seul `/api/ping` a `@require_internal_worker_token`. Tous les autres endpoints (`/run/<step_key>`, `/cache/clear`, `/performance/reset`, `/sequence/stop`, etc.) sont **completement ouverts** | ./routes/api_routes.py, ./routes/workflow_routes.py | Global |
| S6 | **Execution de subprocess sans auth** : `POST /run/<step_key>` permet a n'importe qui de lancer des scripts Python arbitraires sur le serveur | ./routes/workflow_routes.py | 81 |
| S7 | **Endpoint test expose en production** : `/get_specific_log_test/<step_key>/<int:log_index>` (bypass du cache) | ./routes/workflow_routes.py | 248 |

### MEDIUM

| # | Probleme | Fichier | Ligne(s) |
|---|----------|---------|----------|
| S8 | `SECRET_KEY` default `'dev-key-change-in-production'` — validation seulement si `not DEBUG` | ./config/settings.py | 86 |
| S9 | Dev token fallback `"dev-internal-worker-token"` en mode non-strict | ./config/settings.py | 419 |
| S10 | `send_from_directory` pour sound files : pas de validation supplementaire du filename (Flask protege contre `..` mais pas contre les symlinks) | ./routes/workflow_routes.py | 308 |

### Points positifs

- **Aucun `shell=True`** dans tout le codebase — tous les `subprocess.Popen`/`subprocess.run` utilisent des listes d'arguments
- **Aucun `eval()`/`exec()`/`os.system()` dangereux** (les `.eval()` trouves sont des appels PyTorch `model.eval()`)
- **Requetes SQL parametrees** dans `download_history_repository.py` (sqlite3 avec `?` placeholders)
- **Prevention path traversal** : `validate_file_path()` (./config/security.py), `FilenameSanitizer` (./utils/filename_security.py), `find_cache_folder_by_number` sanitise les entrees numeriques
- **HTML escaping** sur les logs et progress text (`html.escape()`)
- **`.gitignore`** exclut correctement `.env`, `download_history.sqlite3`, logs, venvs
- **`to_dict()`** masque les tokens/secrets dans la config serialisee
- **Hardcoded `HF_AUTH_TOKEN`** uniquement via `os.environ.get()`, jamais en clair dans le code

---

## 3. Service Layer

### Points forts

- **Error handling systematique** : try/except sur toutes les methodes publiques avec logging
- **WorkflowState thread-safe** : `RLock` sur toutes les operations de lecture/ecriture
- **CleanupService protected paths** : `PROTECTED_DIR_NAMES` + verification `is_path_protected()` avant suppression
- **CoralTPUOrchestrator** : bon design singleton avec queue asyncio pour serialiser l'acces TPU (8Mo SRAM)
- **WebhookService** : retry avec exponential backoff (3 tentatives, backoff 1s -> 2s)
- **DownloadService** : validation des ZIPs (taille minimum 1MB, content-type), resolution de conflits de noms

### Problemes

| # | Probleme | Fichier | Severity |
|---|----------|---------|----------|
| L1 | **WebhookService : globals sans locks** — `_cache_data`, `_cache_fetched_at`, `_last_error`, `_last_status` sont modifiés sans protection thread alors que le CSV monitor tourne dans un thread daemon | ./services/webhook_service.py | MEDIUM |
| L2 | **CacheService : `cache_stats` sans locks** — dict module-level modifié concurremment par `@measure_api` (threads Flask) sans `threading.Lock` | ./services/cache_service.py | MEDIUM |
| L3 | **CacheService : `cache_instance` global mutable** sans protection | ./services/cache_service.py | LOW |
| L4 | **`workflow_executor.py`** : `config = workflow_commands_config.get_step_config(step_key)` ecrase la variable `config` importee globalement (shadowing) | ./services/workflow_executor.py | 225 |
| L5 | **DownloadHistoryRepository** : `initialize()` appele dans chaque methode (count, get_urls, upsert...) — overhead de creation de table a chaque appel | ./services/download_history_repository.py | LOW |

---

## 4. API / Routes

### Points forts

- **Decorator `@measure_api`** : mesure le temps de reponse et enregistre via `PerformanceService` (duplique dans les deux blueprints — devrait etre factorise)
- **Codes HTTP appropries** : 202 (initiated), 409 (conflict), 404 (not found), 500 (server error)
- **Validation d'input** : les endpoints POST (`/step4/lemonfox_audio`, `/step4/deepinfra_audio`) valident les types et champs requis
- **Headers anti-cache** sur les endpoints de status (`Cache-Control: no-store`)

### Problemes

| # | Probleme | Fichier | Severity |
|---|----------|---------|----------|
| A1 | **31 endpoints, 1 authentifie** — voir S5 | Global | CRITICAL |
| A2 | **Routes dupliquees** — voir S1 | ./routes/workflow_routes.py | CRITICAL |
| A3 | **`measure_api` duplique** dans `api_routes.py` et `workflow_routes.py` — code identique, devrait etre dans un module shared | ./routes/ | LOW |
| A4 | **`/cache/open` POST** : permet d'ouvrir des dossiers dans l'explorateur systeme — contingent sur `CACHE_ROOT` mais l'activation est configurable | ./routes/api_routes.py | 348 |
| A5 | **Pas de validation de `step_key`** dans les routes URL params — deleguee aux services qui levent `ValueError`, mais aucune whitelist explicite | ./routes/workflow_routes.py | Global |

### Inventaire des endpoints

| Endpoint | Methode | Auth | Description |
|----------|---------|------|-------------|
| `/api/system_monitor` | GET | Non | CPU/RAM/GPU |
| `/api/system/diagnostics` | GET | Non | Env diagnostics |
| `/api/step_status/<step_key>` | GET | Non | Status etape |
| `/api/csv_monitor_status` | GET | Non | Status CSV monitor |
| `/api/ping` | GET | **Oui** | Health check |
| `/api/performance/metrics` | GET | Non | Metriques perf |
| `/api/performance/reset` | POST | Non | Reset metriques |
| `/api/cache/stats` | GET | Non | Stats cache |
| `/api/cache/search` | GET | Non | Recherche cache |
| `/api/cache/list_today` | GET | Non | Dossiers du jour |
| `/api/cache/open` | POST | Non | Ouvrir explorateur |
| `/api/cache/clear` | POST | Non | Vider cache |
| `/api/csv_downloads_status` | GET | Non | Status downloads |
| `/api/stats/dashboard` | GET | Non | Dashboard stats |
| `/api/stats/history` | GET | Non | Historique perf |
| `/api/step4/lemonfox_audio` | POST | Non | Analyse audio Lemonfox |
| `/api/step4/deepinfra_audio` | POST | Non | Analyse audio DeepInfra |
| `/` | GET | Non | Page principale |
| `/run/<step_key>` | POST | Non | **Lancer etape** |
| `/run_custom_sequence` | POST | Non | **Lancer sequence** |
| `/status/<step_key>` | GET | Non | Status detaille |
| `/stop/<step_key>` | POST | Non | **Stopper etape** |
| `/get_specific_log_test/...` | GET | Non | **Endpoint test** |
| `/get_specific_log/...` | GET | Non | Log specifique |
| `/sound-design/<filename>` | GET | Non | Fichier son |
| `/test-sound` | GET | Non | Page test son |
| `/sequence/status` | GET | Non | Status sequence |
| `/sequence/stop` | POST | Non | **Stopper sequence** |
| `/cancel/<step_key>` | POST | Non | **Annuler etape** |

---

## 5. Configuration & Environnement

### Points forts

- **Dataclass `Config`** avec 60+ parametres charges depuis env vars
- **`__post_init__`** normalise les paths (absolu, creation des repertoires)
- **`validate()`** verifie tokens, SECRET_KEY, paths — `sys.exit(1)` en production si echec
- **`.env.example`** complet et documente (132 lignes)
- **Detection de typo** `wisper` -> `whisper` dans `resolve_deepinfra_transcriptions_url()`
- **Validation DeepInfra** : timeout, retries, backoff, response format

### Problemes

| # | Probleme | Fichier | Severity |
|---|----------|---------|----------|
| C1 | **`Config` instanciee au niveau module** (`config = Config()`) — importe dans presque tous les modules, difficile a mocker pour les tests | ./config/settings.py | MEDIUM |
| C2 | **`os.environ.get` dans la definition de la dataclass** — les valeurs sont figees a l'import, pas re-evaluees | ./config/settings.py | LOW |
| C3 | **Hardcoded `KEYWORD_FILTER_TRACKING_ENV = "Camille"`** dans `app_new.py` avant d'etre overriden par env var | ./app_new.py | 84-85 |
| C4 | **`os.environ.setdefault`** pour `TRACKING_DISABLE_GPU` et `TRACKING_CPU_WORKERS` — modifie l'environnement global au runtime | ./app_new.py | 88-89 |

---

## 6. Subprocess & Processus Externes

### Points forts

- **Toutes les commandes en liste** (pas de `shell=True`) — prevention injection shell
- **Environnement copie** : `process_env = os.environ.copy()` puis modifications specifiques
- **`PYTHONIOENCODING=UTF-8`**, `PYTHONUTF8=1`, `PYTHONUNBUFFERED=1` — robustesse encodage
- **LD_LIBRARY_PATH dynamique** : detection auto des packages nvidia du venv pour CUDA
- **Cleanup temp files** dans `finally` block
- **Coral TPU orchestrator** : serialise l'acces TPU via queue asyncio pour proteger la SRAM 8Mo

### Problemes

| # | Probleme | Fichier | Severity |
|---|----------|---------|----------|
| P1 | **Pas de timeout sur `process.wait()`** — un script qui hang bloque le thread indefiniment, le step reste `running` pour toujours | ./services/workflow_executor.py | 365 | MEDIUM |
| P2 | **Log file ouvert avec `mode='w'`** — ecrase le log a chaque execution, pas d'append ni de rotation | ./services/workflow_executor.py | 341 | LOW |
| P3 | **`log_dir = Path("logs")`** — path relatif, depend du CWD au moment de l'execution | ./services/workflow_executor.py | 281 | MEDIUM |
| P4 | **Thread tail daemon** — si le process crash avant d'ecrire, le thread tail boucle avec `time.sleep(0.1)` jusqu'a ce que `process.poll()` retourne non-None | ./services/workflow_executor.py | 197-214 | LOW |

---

## 7. Performance & Fiabilite

### Points forts

- **`deque(maxlen=300)`** pour les logs en memoire — borne la consommation
- **`deque(maxlen=20)`** pour l'historique des downloads
- **`lru_cache(maxsize=1)`** pour GPU device info
- **SimpleCache Flask** — rapide pour usage local
- **Background monitoring** : CPU/RAM/GPU via thread daemon
- **Alerts system** : seuils configurables (CPU 85%, RAM 90%, response 1000ms, error rate 5%)
- **Performance history** : `deque(maxlen=100)` pour tendances

### Problemes

| # | Probleme | Fichier | Severity |
|---|----------|---------|----------|
| R1 | **CSV monitor : boucle infinie** `while True` sans flag de shutdown — pas d'arret propre | ./services/csv_monitor.py | MEDIUM |
| R2 | **Orphan cleanup : boucle infinie** similaire sans graceful shutdown | ./services/cleanup_monitor.py | MEDIUM |
| R3 | **SimpleCache non distribue** — OK pour single-process, mais `threaded=True` + multiprocessing pourrait donner des resultats incoherents | ./app_new.py | 131 | LOW |
| R4 | **`PROFILING_STATS` defaultdict** — grandit indefiniment avec le nombre d'endpoints uniques | ./services/performance_service.py | 19 | LOW |
| R5 | **NVML init au niveau module** dans `app_new.py` ET `monitoring_service.py` — double initialisation potentielle | ./app_new.py:66, ./services/monitoring_service.py:24 | LOW |
| R6 | **File handler log mode `'w'`** — ecrase les logs a chaque redemarrage, pas de retention | ./app_new.py | 246 | MEDIUM |

---

## 8. Tests

### Structure

- **35+ tests unitaires** (./tests/unit/)
- **17+ tests d'integration** (./tests/integration/)
- **Tests frontend** en `.mjs`/`.cjs` (./tests/frontend/)
- **Tests legacy** MySQL archive (./tests/legacy/)
- **conftest.py** : reset `WorkflowState` avant/apres chaque test, `DRY_RUN_DOWNLOADS=true`
- **pytest.ini** : exclut les tests nécessitant des venvs specialises (STEP3 TransNet, STEP5 Tracking)

### Couverture

| Domaine | Couverture | Fichiers cles |
|---------|-----------|---------------|
| WorkflowState | Bonne | ./tests/unit/test_workflow_state.py |
| WorkflowService | Bonne | ./tests/unit/test_workflow_service.py |
| CSVService / URL normalization | Bonne | ./tests/unit/test_csv_service_url_normalization.py |
| DownloadService | Bonne | ./tests/unit/test_download_service.py |
| FilesystemService | Bonne | ./tests/unit/test_filesystem_service.py |
| LemonfoxAudioService | Bonne | ./tests/unit/test_lemonfox_audio_service.py |
| DeepinfraAudioService | Bonne | ./tests/unit/test_deepinfra_audio_service.py |
| Security production | Presente | ./tests/unit/test_security_production.py |
| Workflow routes | Presente | ./tests/integration/test_workflow_routes.py |
| Coral TPU orchestrator | Presente | ./tests/unit/test_coral_tpu_orchestrator.py |

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| T1 | **Pas de test d'authentification API** — aucun test verifie qu'un endpoint sans token retourne 401 | HIGH |
| T2 | **Pas de test des routes dupliquees** — le bug S1 n'est pas detecte | MEDIUM |
| T3 | **Pas de test de timeout subprocess** — P1 non couvert | MEDIUM |
| T4 | **Pas de test de concurrence WebhookService** — L1 non couvert | LOW |
| T5 | **Tests frontend non integres au CI** (fichiers `.mjs` separes) | LOW |

---

## 9. Synthese - Priorites de remediation

### Priorite 1 — Critique (a traiter immediatement)

1. **Ajouter l'authentification sur tous les endpoints sensibles** — appliquer `@require_internal_worker_token` ou un mechanisme equivalent sur `/run/<step_key>`, `/run_custom_sequence`, `/stop/<step_key>`, `/sequence/stop`, `/cancel/<step_key>`, `/cache/clear`, `/performance/reset`, `/cache/open`
2. **Supprimer les routes dupliquees** dans ./routes/workflow_routes.py (lignes 441-481)
3. **Retirer ou gate l'endpoint test** `/get_specific_log_test/...` en production
4. **Deployer avec un WSGI server** (gunicorn/uwsgi) au lieu de `app.run()`

### Priorite 2 — Haute

5. **Ajouter CORS configuration** (`flask-cors`) si l'app est accessible depuis un navigateur sur un autre domaine
6. **Ajouter rate limiting** (`flask-limiter`) au minimum sur les endpoints POST
7. **Ajouter un timeout sur `process.wait()`** dans `workflow_executor.py` avec gestion du kill
8. **Thread safety WebhookService** : proteger les globals avec un `threading.Lock`

### Priorite 3 — Moyenne

9. **Logger en mode append** (`mode='a'`) avec rotation (`RotatingFileHandler`) au lieu de `mode='w'`
10. **Utiliser un path absolu** pour `log_dir` dans `workflow_executor.py` (utiliser `config.LOGS_DIR`)
11. **Graceful shutdown** des threads daemon (CSV monitor, cleanup) via un flag `threading.Event`
12. **Thread safety CacheService** : proteger `cache_stats` avec un lock
13. **Tests d'authentification API** : verifier que les endpoints proteges rejettent les requetes sans token
14. **Factoriser `measure_api`** dans un module shared au lieu de le dupliquer

### Priorite 4 — Faible

15. **Extraire `execute_step_sequence_worker`** de `app_new.py` vers un service dedie
16. **Initialiser `DownloadHistoryRepository`** une seule fois, pas dans chaque methode
17. **Faire de `Config` un singleton injectable** pour faciliter le mocking en tests
18. **Nettoyer `os.environ.setdefault`** dans `app_new.py` — utiliser la config au lieu de muter l'env global