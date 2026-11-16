---
trigger: model_decision
description: Workflow MediaPipe detailed pipeline specifications (STEP1 to STEP8), GPU zero-copy, TPU YAMNet split, ECAPA embeddings, and AE/EffectCraft bridges.
---

# Workflow MediaPipe — Spécifications Détaillées du Pipeline (STEP1 à STEP8)

> Référence normative par étape. Complément technique de `codingstandards.md` et `AGENTS.md`.

## 1. Spécifications par Étape (STEP1 à STEP8)

### STEP1 (Extraction & Normalisation Vidéo)
- **Contrat Universel** : Vidéo MP4 / codec H.264 / `yuv420p` / cadencement strict 25.0 fps via `utils/media_normalizer.py`.
- **Moteur** : NVENC parallèle (max 3 workers simultanés) avec bascule automatique CPU `libx264`.
- **Intégrité** : Préservation des couches alpha des `.mov` (`PRESERVED_MOV_NAMES`, ProRes 4444 / Animation / PNG).

### STEP2 (Détection de Coupures & Transitions)
- **GPU (Principal)** : TransNetV2 moteur `TransNetV2GpuEngine` ONNX Runtime avec persistance VRAM et IOBinding zéro-copie. Calcul sigmoïde GPU vectorisée in-place sur logits centraux `[25:75]`, batch dynamique adapté à la VRAM (fallback 10 sur GTX 1650), désactivation TF32 (`use_tf32=0`).
- **TPU (Secours)** : MobileNetV2 INT8 (GAP 1280D / logits 1000D) en Producer-Consumer (I/O FFmpeg asynchrone) + EMA embeddings ($\alpha=0.8$) + post-traitement Numba JIT (médian 1D + Dugad $\mu+k\cdot\sigma$ + FSM Twin-Comparison).
- **Format** : Timecodes `HH:MM:SS.mmm` stricts, cadencement 25.0 fps, delta probabilité $< 10^{-5}$.
- **Contrainte OpenCV 5.0** : Exécution strictement séquentielle sous OpenCV 5.0 DNN (coût `spawn` prohibitif).

### STEP3 (Analyse Audio & Diarisation Locuteurs)
- **GPU/CPU (Whisper/Pyannote)** : Sous-processus isolé (`AUDIO_GPU_ISOLATION=1`, profil `gpu_fp32`) pour immuniser le runtime contre les fuites CUDA.
- **TPU (Architecture YAMNet Split)** :
  - `STEP3_YAMNET_SPLIT=1` : Frontend CPU Log-Mel NumPy (`yamnet_frontend.py`) + CNN MobileNetV1 compilé 100% Edge TPU (`assets/yamnet_split_edgetpu_compiled.tflite` sur `/dev/apex_0`, latence ~1.1 ms).
  - Pipeline Producer-Consumer double tampon par blocs de 256 sous verrou `_tpu_lock`.
  - Noyau Numba fusionné Filtre Médian VAD (seuil 0.20) + FSM Hangover (1.0s) + AHC condensé (`fastcluster.linkage`, Gram BLAS, seuil 0.32, `np.nextafter`) + réassignation locuteurs mineurs (<7.0s).
  - Extraction d-vectors ECAPA-TDNN FP32 via ONNX Runtime CPU partagé (OpenVINO EP auto batch 8, `STEP3_EMBEDDING_STRIDE=1`).
  - Validation matérielle : Délégué `edgetpu-custom-op` obligatoire (bloquant si `STEP3_REQUIRE_EDGETPU=1`).

### STEP4 (Tracking Sujets & Détection Faciale)
- **CPU** : MediaPipe (`tracking_env_slim`), multiprocessing avec contexte `spawn` + `cv2.setNumThreads(0)`.
- **GPU** : InsightFace (`insightface_env`, activé via `STEP4_ENABLE_GPU=1`).
- **TPU** : Cascade TFLite (BlazeFace + FaceMesh sans `half_pixel_centers` + Blendshapes) + Filtre One-Euro (OneEuroFilterND @njit 52 dimensions). Mode rapide `STEP4_TPU_FAST=1` (hystérésis 25 frames, caches d'ancres BlazeFace, JSON tamponné).
- **Export O(1)** : `StreamingJSONOutput` obligatoire (interdiction de sérialisation monolithique en mémoire).

### STEP5 & STEP6 (Réduction JSON & Pré-traitement Post-Production)
- **Lecture Streaming** : Parser `ijson` obligatoire sur tous les JSON intermédiaires volumineux.
- **Hiérarchie 4 Paliers** : `Tier 4: best_audio_face` > `Tier 3: best_audio_person` > `Tier 2: best_face` > `Tier 1: best_person`.
- **Taxonomie d'Observabilité** : `LABEL_STABLE: 3`, `LABEL_HIGH_SPREAD: 12` (spread > 200px), `LABEL_FALLBACK_CENTER: 1` (recentrage par défaut 50%).
- **Export AE** : Priorité absolue aux métadonnées `*_ae.json`.

### STEP7 & STEP8 (Finalisation & Rendu Headless EffectCraft)
- **After Effects CEP (ExtendScript ES3)** : Conformité ES3 pure (`var`, boucles `for` classiques, IIFE, polyfill `JSON2`). Batch obligatoire dans `app.beginUndoGroup()` / `endUndoGroup()`.
- **EffectCraft CLI Headless** : Exécution pilotée par `effectcraft-cli script` et passerelle `ecproj_to_prproj.py`.
- **Règle d'Or** : Préservation et non-altération absolue des fichiers `.ecproj` bruts et des flux vidéo sources.

