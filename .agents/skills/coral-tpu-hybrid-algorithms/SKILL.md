---
name: coral-tpu-hybrid-algorithms
description: Expert des algorithmes CPU (Numba JIT, Filtre de Kalman, Clustering Spectral, fastcluster) mis en place pour compenser la perte de précision INT8 et les limites de l'ASIC Coral.
trigger: kalman, spectral, clustering, cosine, hybrid, jittering, numba, jit, welford, fastcluster, iobinding
---

# Coral TPU Hybrid Algorithms Skill

Ce skill encadre les heuristiques mathématiques déportées sur le CPU pour compenser la limitation matérielle (précision INT8, manque d'opérations complexes) du TPU Coral.

## 🎯 Rôle
Déboguer, profiler et optimiser les calculs lourds qui s'exécutent sur le CPU en complément des inférences TPU. Cela inclut la vectorisation compilée Numba JIT (STEP2: Dugad Welford, Twin-Comparison FSM, Filtre médian ; STEP3: noyau fusionné médian + seuil + FSM Hangover, extraction du triangle cosinus condensé), le Filtre One-Euro (52 dimensions) pour réduire le jittering (avec le Filtre de Kalman vectorisé en secours), le Clustering Hiérarchique Agglomératif condensé (`fastcluster` + matrice de Gram BLAS) et le Regroupement Spectral via `scikit-learn` pour l'audio.

## 📋 Checklist de Préparation
Avant d'optimiser le code algorithmique :
- [ ] Profiler hors-processus avec `py-spy record --native -F -r 500` (surcoût < 1 %, résout les piles C/C++ d'ONNX Runtime et libedgetpu) ; compléter au besoin par `perf stat` pour les défauts de cache et `time.perf_counter_ns()` dans le code.
- [ ] S'assurer que les dépendances (`scikit-learn`, `numpy`, `scipy`, `numba`, `fastcluster`) sont à jour dans le bon environnement (`requirements-coral_env.txt`).

## 🛠 Commandes Types
- Profiling d'un composant de clustering sans biais d'observation :
  ```bash
  py-spy record --native -F -r 500 -o scratch/profile.svg -- \
      coral_env/bin/python workflow_scripts/step3/run_audio_diarization_tpu.py --log_dir logs/step3
  ```
- Vérifier la parité numérique des optimisations STEP3 :
  ```bash
  ./scripts/run_step3_tests.sh
  ```
- Benchmark acoustique DER/JER (ΔDER strict ≤ 0.05 point) :
  ```bash
  python3 scripts/bench_step3_tpu_der.py --limit 5 --baseline scratch/bench_step3_der/baseline/der_report.json
  ```
- Comparer les fournisseurs ONNX Runtime (CPU vs OpenVINO) :
  ```bash
  coral_env/bin/python scripts/bench_ecapa_providers.py --batch-sizes 1,8,16,32 --runs 3
  ```

## 🚑 Checklist Diagnostique & Résolution

### Incident 1 : Jittering extrême (Tremblement) sur le Tracking (STEP4)
- **Symptôme** : Les points de repère faciaux générés par le modèle quantisé BlazeFace/FaceMesh tremblent fortement par rapport à la version FP32 CPU.
- **Action** : Valider que le filtre One-Euro (`OneEuroFilterND`) est activé par défaut. Ajuster ses paramètres `min_cutoff` (seuil de coupure minimum pour stabiliser à basse vitesse) et `beta` (sensibilité à la vitesse pour éviter la traînée/décalage). En cas de fallback sur le Filtre de Kalman vectorisé, ajuster les matrices de covariance de bruit de processus ($Q$) et de bruit de mesure ($R$) pour lisser le bruit quantique spécifique à l'INT8.

### Incident 2 : Le clustering audio (STEP3) est inexact ou engorge le CPU
- **Symptôme** : Division fictive des locuteurs ou lenteurs lors du regroupement des d-vectors ECAPA-TDNN.
- **Action** : Les d-vectors sont extraits en FP32 via ONNX Runtime (jamais en INT8). Le clustering AHC utilise une matrice de Gram BLAS puis un vecteur de distances cosinus condensé (`N(N−1)/2`, deux fois moins de RAM) traité par `fastcluster.linkage(method='average')` — repli automatique sur `scipy.cluster.hierarchy` si la roue C++ est absente. Conserver `t = np.nextafter(0.32, 0.0)` et le décalage `-1` des étiquettes pour la parité exacte avec `sklearn.AgglomerativeClustering(metric='cosine', linkage='average', distance_threshold=0.32)`. Le seuil de réassignation des locuteurs mineurs reste 7.0s, la fusion des segments contigus < 1.0s et le renommage `SPEAKER_XX` par durée décroissante.
- **Optimisations mesurées (VoxConverse dev)** : l'EP OpenVINO CPU (`onnxruntime-openvino`, batch 8) apporte 1,5–1,7× sur ECAPA à parité stricte (`STEP3_DISABLE_OPENVINO=1` pour forcer le CPU). `STEP3_EMBEDDING_STRIDE=2` réduit ECAPA de 2× et améliore le DER agrégé (5 extraits : 36,85 % → 21,53 % ; 10 extraits : 30,25 % → 21,12 %) mais dégrade 3/10 extraits de +1,5 à +3,2 pts : l'activer après vérification par extrait. K=4 atteint 4× mais dégrade akthc de 4,1 pts. La combinaison K=2 + OpenVINO donne 2,5× sur le run complet à 5 extraits (186 s → 73 s).

### Incident 3 : Le fallback XNNPACK remplace silencieusement l'Edge TPU
- **Symptôme** : Charge CPU anormale pendant la STEP3 et débit divisé par ~20, sans erreur explicite.
- **Action** : `_assert_edgetpu_delegate_active()` vérifie la présence de `edgetpu-custom-op` dans le **flatbuffer** du modèle, puis celle de sous-graphes `DELEGATE` après `allocate_tensors()`. Un modèle non compilé est journalisé en **erreur** (repli CPU explicite, plus silencieux) ; `STEP3_REQUIRE_EDGETPU=1` rend le repli bloquant. Contrôler `/dev/apex_0`, la présence de `libedgetpu.so.1` (repli `tmp_lib/usr/lib/x86_64-linux-gnu/`) et `pcie_aspm=off` dans `/proc/cmdline`. Constat 2026-10 : le YAMNet fourni n'est pas compilable intégralement (3 ops sur 53) et s'exécute sur CPU/XNNPACK.

## ⚠️ Séparation des Responsabilités
Se concentre purement sur la viabilité et la performance des algorithmes mathématiques CPU. Intervient "après" le TPU, là où l'ASIC s'arrête, sans se substituer aux orchestrateurs globaux de STEP2, STEP3 ou STEP4.
