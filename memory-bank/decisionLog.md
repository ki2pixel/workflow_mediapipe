# Journal des Décisions

Ce document enregistre les décisions architecturales et techniques importantes prises au cours du projet.

> **Politique de conservation**  
> - Ce fichier conserve intégralement les décisions des ~90 derniers jours ou celles toujours actives dans le code.  
> - Les décisions antérieures sont synthétisées ci-dessous et disponibles en détail dans `memory-bank/archives/decisionLog_legacy.md`.

## Historique synthétique (avant mars 2026)

Cette section contient le résumé des décisions majeures jusqu'à mars 2026. Pour les détails chronologiques complets, consultez `archives/decisionLog_legacy.md`.

## Septembre 2026

- [2026-09-27 22:05:00] **Renumérotation des variables d'environnement STEPn_* et des endpoints audio (COMPLET)**
  - **Décision** : aligner les variables d'environnement d'étape sur la numérotation actuelle du pipeline (décalage d'un cran : STEP3_*→STEP2_* transitions, STEP4_*→STEP3_* audio, STEP5_*→STEP4_* tracking, STEP6_*→STEP5_* réduction JSON, STEP7_*→STEP6_* pré-traitement AE, `USE_OPENCV5_STEP3/5`→`USE_OPENCV5_STEP2/4`) et renommer en dur les deux endpoints audio (`/api/step4/lemonfox_audio`→`/api/audio/lemonfox`, `/api/step4/deepinfra_audio`→`/api/audio/deepinfra`). **Cette décision annule et remplace la « décision annexe » de l'entrée précédente**, qui conservait les noms historiques pour ne pas casser un `.env` existant.
  - **Raison** : la numérotation historique (`STEP4_*` = audio, `STEP5_*` = tracking) entretenait une confusion permanente avec les étapes actuelles ; l'opérateur a explicitement choisi la cohérence, en assumant la migration.
  - **Risque identifié et traité** : le décalage est une **permutation**, pas un renommage neutre. Un `.env` non migré serait interprété de travers sans aucune erreur (l'ancien `STEP4_ENABLE_CORAL_TPU`, audio, désignerait le tracking). Trois protections : (1) `scripts/migrate_env_step_names.py` renomme les clés en une seule passe avec sauvegarde horodatée et appose `ENV_STEP_SCHEMA=2` ; (2) `Config.check_step_env_schema()` détecte un `.env` sans marqueur — erreur bloquante en production, avertissement en développement ; (3) `ENV_STEP_SCHEMA=2` documenté en tête de `.env.example`.
  - **Implémentation** : ~1300 occurrences renommées dans 73 fichiers (config, services, routes, workflow_scripts, utils, tests, docs vivantes, skills et leurs miroirs `.clinerules/`, `.windsurf/`, `.cline/`), identifiants Python dérivés inclus. Les documents d'archive (`docs/audits`, `docs/WIP`, `memory-bank/archives`, entrées historiques de `decisionLog`/`progress`) restent inchangés.
  - **Incident d'exécution** : un premier passage utilisait un motif autorisant `STEPn` sans underscore, ce qui a décalé aussi les *clés d'étapes* (`StepKey.STEP3`, `"STEP4": …`) ; détecté par la suite de tests (enum dupliqué), annulé via `git checkout`, puis repris avec un motif strict `STEPn_`. Un second oubli (`utils/tracking_optimizations.py` absent des cibles) a été détecté par un contrôle de bijection « HEAD vs arbre courant » sur tous les fichiers suivis.
  - **Impact / suite à donner** : tout appelant externe des endpoints audio (`curl`, n8n, règles de reverse-proxy) doit être mis à jour ; l'application doit être redémarrée après migration du `.env`.

- [2026-09-27 20:55:00] **Suppression de l'étape « 2. Conversion des vidéos » et renumérotation STEP1→STEP7 (COMPLET)**
  - **Décision** : supprimer définitivement l'étape de conversion et déplacer sa responsabilité réelle — la normalisation vidéo **MP4 / H.264 / yuv420p / 25 fps** — dans STEP1, via un module partagé `utils/media_normalizer.py` appelé après chaque extraction d'archive. Les clés d'étapes sont renumérotées en continu : STEP1 (extraction + normalisation), STEP2 (analyse des transitions), STEP3 (analyse audio), STEP4 (analyse du tracking), STEP5 (réduction JSON), STEP6 (pré-traitement AE), STEP7 (finalisation).
  - **Raison** : l'ancienne STEP2 n'était pas un simple transcodage mais le **garant du contrat 25 fps** dont dépendent toutes les étapes aval. L'analyse des transitions code en dur `get_video_fps() = 25.0` (`r=25` sur le pipe FFmpeg), l'analyse audio utilise `DEFAULT_FPS = 25`, et les étapes JSON/AE indexent leurs résultats par numéro de frame. Supprimer l'étape sans déplacer la normalisation aurait provoqué une désynchronisation frame/timecode silencieuse (source 23,976/29,97/50/60 fps ré-échantillonnée à la volée).
  - **Alternatives rejetées** :
    1. **Adaptation du framerate réel dans STEP3/STEP4/STEP5** (suppression sans compensation) : refonte large et risque élevé, l'alignement frame/timecode étant la clé de jointure de tout l'aval jusqu'à After Effects.
    2. **Bypass cosmétique** (tuile STEP2 conservée mais désactivée, séquence 1→3) : la normalisation n'aurait plus été exécutée tout en laissant croire le contraire dans l'UI.
    3. **Renommage sémantique des clés** (SCENE_DETECT, AUDIO, …) : écarté au profit d'une renumérotation numérique continue, moins intrusive pour l'UI, les URLs et les tests.
  - **Implémentation** :
    1. `utils/media_normalizer.py` : reprise du script `workflow_scripts/step2/convert_videos.py` (analyse ffprobe, encodage NVENC avec fallback CPU `libx264`, copie audio intelligente, préservation des logos `.mov` alpha), enrichie de `is_conformant()`, `normalize_videos_in(root, force)` et `check_fps_conformance()`.
    2. `workflow_scripts/step1/extract_archives.py` : normalisation post-extraction + modes `--normalize-only` et `--normalize-only --force` pour rattraper les projets extraits antérieurement.
    3. Renumérotation en bloc : `config/workflow_commands.py`, `services/types.py`, `services/workflow_executor.py`, `app_new.py`, dossiers `workflow_scripts/stepN`, dossiers `logs/stepN`, `config/stepN_*.json`, fichiers de tests, `pytest.ini`, runners `run_step2_tests.sh` / `run_step4_tests.sh`.
    4. Frontend : timeline à 7 tuiles, liste `defaultSequenceableStepsKeys` réduite, et **purge one-shot de `selectedStepsOrder`** dans `AppState` — sans elle, une sélection persistée contenant l'ancien `"STEP2"` aurait silencieusement lancé l'analyse des transitions.
    5. Garde-fou : avertissement non bloquant de framerate non conforme dans les trois entrées d'analyse des transitions (`run_transnet.py`, `run_transnet_cv5.py`, `run_scene_detect_tpu.py`).
  - **Décision annexe — variables d'environnement non renommées** : `STEP3_ENABLE_CORAL_TPU`, `USE_OPENCV5_STEP3`, `STEP4_USE_LEMONFOX`, `STEP5_CV5_*`, `STEP5_ENABLE_GPU`, etc. conservent leur numérotation historique. Un renommage ferait retomber silencieusement un `.env` existant sur les valeurs par défaut et changerait le comportement d'exécution sans erreur visible. Une table de correspondance est documentée dans `.env.example`, `docs/workflow/README.md` et `.agents/skills/workflow-operator/`.
  - **Décision annexe — endpoints audio `/api/step4/*` inchangés** : ce sont des déclencheurs externes documentés (exemples `curl` dans `docs/deployment/tls-reverse-proxy.md`) ; leur renommage casserait une automatisation externe sans gain fonctionnel.
  - **Impact** : STEP1 devient plus long (transcode) mais les projets déjà normalisés sont ignorés en mode rattrapage ; les logs de l'ancienne conversion ont été archivés dans `logs/_archive_step2_conversion/` pour ne pas remonter dans le panneau Logs de la nouvelle étape 2.
  - **Validation** : suite backend complète (unit + intégration) et suites frontend Node ESM au vert ; `docs/workflow/**`, `AGENTS.md`, `.agents/rules/codingstandards.md` et les skills alignés (`docs/audits`, `docs/WIP`, `docs/recherches` gelés).

## Juillet 2026

- [2026-07-15 11:31:24] **Pool Adaptatif CPU STEP5 CV5 et Séparation du Device d'Inférence (COMPLET)**
  - **Décision** : Utiliser un pool global d'inférence par chunks en mode CV5 `auto`, plafonné par le budget CPU, la limite mémoire et le volume de frames ; maintenir la réduction temporelle et le tracking ordonné dans le processus parent.
  - **Raison** : Le parallélisme historique par vidéo ne pouvait pas saturer le CPU lorsqu'un lot ne contenait qu'une seule vidéo. Le sweet spot mesuré est de 15 workers sur le système cible.
  - **Implémentation** : Ajout de `STEP5_CV5_CPU_BUDGET`, `STEP5_CV5_MAX_ACTIVE_VIDEOS`, `STEP5_CV5_MIN_FRAMES_PER_WORKER`, `STEP5_CV5_CHUNK_FRAMES`, `STEP5_CV5_MAX_WORKERS_BY_MEMORY` et du mode `video` de repli. Les sorties sont écrites dans un fichier `.partial` puis renommées après réduction complète.
  - **Séparation GPU** : `STEP5_CV5_INFERENCE_DEVICE=cpu` force les modèles CV5 et les fallbacks ONNX Runtime sur CPU, sans considérer `STEP5_ENABLE_GPU`, réservé au pipeline InsightFace historique. Le mode CV5 `cuda` passe directement par ONNX Runtime CUDA et limite le pool à un worker pour empêcher la contention VRAM.
  - **Validation** : Tests ciblés et intégration CV5 réussis ; suite backend : 460 réussites, 28 ignorés ; compilation, lint fatal et typecheck ciblé réussis. Configuration synchronisée dans `.env` et `.env.example`.

- [2026-07-12 16:50:00] **Remédiation Finale de l'Audit Technique Backend (Phase 1-5) (COMPLET)**
  - **Décision** : Sécurisation critique, thread-safety multi-thread gunicorn, durcissement I/O et réorganisation des hooks de cycle de vie (NVML/atexit).
  - **Raison** : Le second audit technique a relevé 18 failles critiques (dont 5 sans protection d'authentification, doubles initialisations de threads et process bloqués indéfiniment).
  - **Implémentation** :
    1. Authentification : Décorateur `@require_internal_worker_token` appliqué à 9 routes d'exécution.
    2. Concurrence : Verrous `Lock` et `RLock` sur `WebhookService` et `CacheService`.
    3. Cycle de vie : Remplacement de `time.sleep` par `threading.Event.wait` et enregistrement de callbacks clean via `atexit.register`.
    4. Subprocess : Timeout forcé avec cascade de signaux `SIGTERM` / `SIGKILL` et rotation manuelle des logs d'étapes (>5MB).
    5. Config : Restructuration de `Config` dans `settings.py` (méthodes `reload` et `_normalize_paths`) pour éviter les mutations directes et isoler l'exécution.
  - **Validation** : Création de `test_api_authentication.py`, `test_webhook_concurrency.py`, `test_workflow_executor_timeout.py`, validation de toute la suite avec 451 tests OK.

## Juin 2026

- [2026-06-14 04:21:00] **Abandon et Nettoyage de l'Optimisation STEP3 Axe A (COMPLET)** : Abandon définitif de la méthode optimisée de décodage GPU TorchCodec + PyTorch compilation en FP16.
  - **Raison** : Les benchmarks sur GTX 1650 (4Go VRAM) ont révélé que le décodage GPU séquentiel (NVDEC) + l'inférence GPU est plus lent (27s par vidéo) que le décodage et redimensionnement CPU en parallèle via FFmpeg pipe combiné à l'inférence GPU (22s). De plus, l'interpolation linéaire simplifiée (`np.linspace`) pour ré-échantillonner à 25 FPS cause des décalages d'indices temporels sur les vidéos à framerate variable (VFR), provoquant des écarts dans la détection de scènes.
  - **Implémentation** : Restauration de la méthode classique consolidée dans `workflow_commands.py` et `app_new.py`. Suppression du script expérimental `run_transnet_opt.py`, de l'export TensorRT `export_transnet_trt.py`, de l'environnement virtuel local `transnet_env` à la racine, et des modèles TensorRT/ONNX. Nettoyage de l'espace disque (~4 Go) et mise à jour de la suite de tests unitaires (34/34 OK).

- [2026-06-13 13:30:00] **Migration ECAPA-TDNN vers ONNX Runtime (Dynamic Batching) (COMPLET)** : Remplacement de l'inférence TFLite séquentielle par ONNX Runtime dans `run_audio_diarization_tpu.py`.
  - **Raison** : L'exécution itérative (`batch_size=1`) sur le CPU générait un *Memory-Bound Bottleneck*, limitant drastiquement les performances d'extraction des vecteurs vocaux malgré le multiprocessing.
  - **Implémentation** : Export dynamique du modèle `speechbrain` en format ONNX via `export_ecapa_onnx.py`. Implémentation du *Dynamic Batching* (taille 32) pour accumuler les spectrogrammes Log-Mel. Tuning manuel de l'affinité mémoire NUMA du Threadripper via `sess_options.intra_op_num_threads` (distribué selon `STEP4_MAX_WORKERS`) et `ORT_SEQUENTIAL`.
  - **Impact** : Le temps de traitement pour 8 vidéos a été divisé par 2 (de ~4m43s à 2m20s), propulsant l'utilisation CPU à 100% de manière fluide sans congestionner l'Edge TPU réservé au modèle VAD.

- [2026-06-12 21:38:00] **Calibration du seuil de clustering audio (AHC = 0.32) (COMPLET)** : Fixation du seuil de clustering AHC par défaut à `0.32` dans `run_audio_diarization_tpu.py`.
  - **Raison** : Le seuil précédent de `0.33` provoquait une sous-segmentation systématique des locuteurs (fusion des dialogues en un locuteur unique, moyenne TPU de 1.0 locuteur vs 1.6 sur GPU).
  - **Bilan** : Le seuil affiné de 0.32 permet de distinguer correctement les locuteurs pour les vidéos de dialogue de *Hélène Romano* et *Sa fille se plaint* (2 locuteurs sur TPU), élevant la moyenne de locuteurs à 1.4, sans introduire de sur-segmentation sur les monologues de *Steffy* ou *Edouard Durand*.

- [2026-06-12 14:55:00] **Implémentation Algorithmes Audit TPU vs GPU Camille (STEP3 & STEP4)** : Réécriture complète des deux scripts TPU pour intégrer les recommandations de l'audit comparatif `docs/audits/audit_tpu_vs_gpu_camille.md`.
  - **Raison** : L'audit a identifié une sur-détection majeure (31.4 faux positifs/vidéo) en STEP3 et un rappel VAD insuffisant (54.89%) en STEP4, causés par l'utilisation de logits bruts 1000D, de seuils statiques, d'un fenêtrage non-chevauchant et d'un clustering fixe à 2 locuteurs.
  - **Implémentation** :
    - STEP3 : Support GAP 1280D (fallback 1000D), EMA sur embeddings (α=0.8), filtre médian 1D (remplace moyenne mobile), seuillage adaptatif de Dugad (μ+k·σ, k=3.0, M=25), twin-comparison (transitions graduelles), timecode `HH:MM:SS.mmm`.
    - STEP4 : Fenêtrage glissant 50% overlap (hop=0.48s), seuil VAD calibré 0.20, filtre médian sur probabilités, FSM Hangover 3 états (1.0s, `ceil(1.0/hop_sec)` frames), clustering spectral adaptatif (eigengap + silhouette), `speaker_stats` dans le JSON.
  - **Alternatives rejetées** : Remplacement complet par Whisper/TransNetV2 sur CPU (trop lent sans GPU). Seuils statiques affinés (insuffisant face à la variabilité du contenu).
  - **Impact** : Tous les paramètres sont configurables via `--config` JSON. 38/38 tests passés. Aucune régression sur la suite complète (434/434 STEP3+STEP4 tests).


- [2026-06-11 19:00:00] **Mise à jour Coding Standards Google Coral Edge TPU** : Décision d'intégrer les spécifications du Coral TPU tout en réduisant drastiquement la verbosité du fichier `.agents/rules/codingstandards.md`.
  - **Raison** : La limite stricte de 12 000 caractères était menacée. Il fallait documenter l'usage obligatoire de `coral_tpu_orchestrator.py` et les modèles INT8 sans dépasser le quota.
  - **Implémentation** : Réécriture complète et condensation des sections "After Effects & CEP" et "Pipeline", et ajout des contraintes TPU.
  - **Impact** : Le fichier reste sous la barre des 5200 caractères, préservant la limite stricte de l'agent tout en incluant la nouvelle architecture Edge.

- [2026-06-02 19:47:00] **Alignement de la Documentation Technique** : Décision de synchroniser l'ensemble de la documentation (`docs/workflow/`) avec les implémentations asynchrones et l'architecture O(1) RAM du pipeline (STEP2-STEP5), et le mécanisme de crash strict au démarrage en production.
  - **Raison** : Les récents audits et refactorisations (multiprocessing MediaPipe, TransNetV2 asynchrone, NVENC passe unique, isolation GPU Pyannote) avaient créé un décalage critique entre le comportement réel (optimisé pour O(1) RAM et sécurité stricte) et la documentation de référence, risquant de biaiser les prochains développements ou diagnostics.
  - **Implémentation** : Mise à jour des guides `02-conversion.md`, `03-scene-detection.md`, `04-audio-analysis.md`, `05-video-tracking.md` et `security.md` en appliquant les normes éditoriales de `documentation/SKILL.md`.
  - **Impact** : La documentation réverbère désormais avec précision l'état optimal et sécurisé de l'architecture, éliminant la dette technique documentaire sur les étapes centrales du pipeline.

- [2026-06-02 19:15:00] **Optimisations de Performance STEP3 (I/O Asynchrone & Batching)** : Implémentation du décodage FFmpeg asynchrone, du pruning mémoire O(1), et du batching GPU (taille 16).
  - **Raison** : La STEP3 était limitée par un traitement image par image synchrone, entraînant une sous-utilisation sévère du GPU et une accumulation exponentielle en RAM (fuite mémoire).
  - **Implémentation** : Refonte de la fonction `detect_scenes_with_pytorch` dans `run_transnet.py`. Déploiement d'un `threading.Thread` avec `queue.Queue` pour bufferiser les frames issues de FFmpeg. Modification du buffer `frames` pour utiliser un slice dynamique (pruning) limitant l'empreinte mémoire RAM à la taille du batch. Utilisation de `np.stack` pour traiter 16 frames à la fois via le modèle TransNetV2.
  - **Impact** : Résolution du goulot d'étranglement I/O, stabilisation de la consommation RAM à un niveau constant O(1), et augmentation du débit GPU (fps) pour l'analyse des scènes.

- [2026-06-02 17:45:00] **Compatibilité Pyannote.audio 4.x (DiarizeOutput) (COMPLET)** : Résolution de l'AttributeError `'DiarizeOutput' object has no attribute 'itertracks'` survenu lors de l'exécution de la STEP4 avec pyannote.
  - **Raison** : Les versions récentes de `pyannote.audio` (4.x+) retournent un objet conteneur `DiarizeOutput` au lieu de l'objet `Annotation` historique, rompant la compatibilité avec l'appel direct de `.itertracks()`.
  - **Implémentation** : Modification de `run_audio_analysis.py` (à la fois dans la fonction d'extraction principale et dans le mode subprocess CPU fallback) pour détecter la présence de l'attribut `speaker_diarization` et en extraire l'objet `Annotation` sous-jacent, tout en conservant une compatibilité totale avec les versions antérieures 3.x/2.x.
  - **Validation** : Les tests unitaires (24 tests passés sur le module STEP4) confirment l'absence de régression.

## Mai 2026

- [2026-05-29 19:40:00] **Optimisations de Performance STEP5 (InsightFace GPU & JSON Streaming)** : Implémentation de trois optimisations majeures pour le tracking InsightFace GPU sur des cartes limitées à 4 Go de VRAM (GTX 1650).
  - **Raison** : Les modèles de tracking facial chargeaient inutilement tous leurs sous-modèles en VRAM (GenderAge, Recognition, etc.) et l'export final de gros volumes de frames vers JSON provoquait des plantages mémoire (OOM) en RAM CPU.
  - **Implémentation** :
    1. Introduction de `STEP5_INSIGHTFACE_ALLOWED_MODULES` (défaut `detection,landmark_3d_68`) pour restreindre les modules chargés.
    2. Réduction de la résolution interne (`STEP5_INSIGHTFACE_DET_SIZE=480`) et configuration robuste du provider CUDA (`arena_extend_strategy=kSameAsRequested`, `cudnn_conv_algo_search=HEURISTIC`).
    3. Implémentation du **Streaming JSON Export** via `StreamingJSONOutput` et `StreamingList` dans `process_video_worker.py` pour écrire les frames au fil de l'eau sur le disque (maintien d'une RAM O(1)).
  - **Impact** : L'empreinte VRAM d'initialisation a été divisée par 3 (descendue sous les 800 Mo de pic en runtime), et la performance de tracking est passée de **10 FPS à plus de 54 FPS (+440% de gain)**. L'export n'a plus aucun impact sur l'allocation de la RAM CPU.
  - **Documentation** : Mise à jour de `docs/workflow/pipeline/05-video-tracking.md` et `.env.example`.
