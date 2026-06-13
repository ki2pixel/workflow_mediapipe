# Journal des Décisions

Ce document enregistre les décisions architecturales et techniques importantes prises au cours du projet.

> **Politique de conservation**  
> - Ce fichier conserve intégralement les décisions des ~90 derniers jours ou celles toujours actives dans le code.  
> - Les décisions antérieures sont synthétisées ci-dessous et disponibles en détail dans `memory-bank/archives/decisionLog_legacy.md`.

## Historique synthétique (avant mars 2026)

Cette section contient le résumé des décisions majeures jusqu'à mars 2026. Pour les détails chronologiques complets, consultez `archives/decisionLog_legacy.md`.
## Juin 2026

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
  - **Impact** : La documentation reflète désormais avec précision l'état optimal et sécurisé de l'architecture, éliminant la dette technique documentaire sur les étapes centrales du pipeline.

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
