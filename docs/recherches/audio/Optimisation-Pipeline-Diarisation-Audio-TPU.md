L'audit croisé entre le référentiel du dépôt `workflow_mediapipe` (`workflow_scripts/step3/`, `config/workflow_commands.py`, `config/settings.py` et les skills associés) et le rapport de recherche `Optimisation-Pipeline-Diarisation-Audio-Hybride.md` met en évidence des goulets d'étranglement majeurs liés à la sérialisation Python, aux copies mémoire inter-runtimes et à la granularité de verrouillage du bus PCIe M.2 (`/dev/apex_0`).

---

## 1. Audit de l'Existant STEP3 (`run_audio_diarization_tpu.py` & Écosystème Audio)

### 1.1 Architecture d'Orchestration et Routage STEP3

* **Routage dynamique (`config/workflow_commands.py`)** : La méthode `_get_step3_config()` aiguille l'exécution de la STEP3 vers l'environnement isolé `coral_env/bin/python` et le script `workflow_scripts/step3/run_audio_diarization_tpu.py` dès lors que les drapeaux `ENABLE_CORAL_TPU_ACCELERATION=true` et `STEP3_ENABLE_CORAL_TPU=true` sont actifs dans `config/settings.py`.


* **Méthodes alternatives (`audio_env`)** : Lorsque l'accélération TPU est désactivée, `config.resolve_audio_method()` sélectionne `run_audio_analysis.py` (Pyannote 3.1 GPU/CPU avec profil `AUDIO_PROFILE=gpu_fp32` et isolation `AUDIO_GPU_ISOLATION=1`), `run_audio_analysis_lemonfox.py` (API cloud Lemonfox avec fallback Pyannote) ou `run_audio_analysis_deepinfra.py` (Whisper large-v3 via DeepInfra avec fallback Pyannote).


* **Contrat de sortie aval (STEP4 / STEP5 / STEP6)** : Les scripts de la STEP3 génèrent un fichier `<video>_audio.json` dans `projets_extraits/<projet>/docs/` qui alimente le tracking vidéo (STEP4), la réduction JSON en streaming O(1) via `ijson` (STEP5 `json_reducer.py`) et le pré-traitement After Effects (STEP6 `preprocess_ae_json.py`).



### 1.2 Inspection des 4 Étages Algorithmiques de `run_audio_diarization_tpu.py`

1. **Extraction Log-Mel Spectrogram sur CPU** :
* L'implémentation actuelle découpe les segments vocaux en fenêtres de **3.0 s** (**48 000 échantillons** à **16 kHz**) et applique séquentiellement `scipy.signal.stft` dans une boucle Python.


* Chaque itération invoque une transformée de Fourier réelle mono-threadée sur un petit tenseur avec `n_fft=400` (**25 ms**), `hop_length=160` (**10 ms**), une fenêtre de Hann périodique (`sym=False`) et les paramètres par défaut de SciPy (`boundary='zeros'`, `scaling='spectrum'`), suivie de la projection sur 80 banques Mel, d'un écrêtage logarithmique $\log(\max(\text{mel}, 10^{-10}))$ et d'une normalisation cepstrale moyenne (CMN) allouant des tableaux temporaires à chaque étape.




2. **Inférence ECAPA-TDNN sous ONNX Runtime (CPU)** :
* Afin d'éviter la dégradation de précision liée à la quantification INT8 sur l'ASIC Coral, l'extraction des *d-vectors* 192D (avec fallback sur les embeddings YAMNet 1024D) est déportée sur le CPU en FP32 via ONNX Runtime.


* Le partitionnement actuel divise les cœurs du processeur entre plusieurs workers (`intra_op_num_threads = cpu_count // workers`) et invoque l'API standard `session.run(["output"], {"input": batch_np})` sur des lots `(32, 80, 300)`, entraînant une vérification de contiguïté mémoire, l'allocation de tampons intermédiaires C++ à chaque inférence et une contention du cache L3 entre processus.




3. **Boucle VAD YAMNet sur Google Coral Edge TPU (`/dev/apex_0`)** :
* Le signal audio est analysé par YAMNet INT8 avec un fenêtrage glissant de **0.96 s** (**15 360 échantillons**) et un recouvrement de **50%** (`hop = 0.48 s`, soit **7 680 échantillons**).


* L'exécution est strictement séquentielle et synchrone : à chaque trame unitaire, le thread acquiert le verrou local `_tpu_lock`, quantifie la fenêtre en INT8 sur le CPU, effectue une copie défensive via `interpreter.set_tensor()`, bloque sur l'appel DMA PCIe `interpreter.invoke()`, copie la sortie via `interpreter.get_tensor()` et relâche `_tpu_lock`.




4. **Clustering AHC et Post-Filtrage Temporel** :
* Le lissage des probabilités VAD repose sur `scipy.signal.medfilt(scores, kernel_size=5)`, suivi d'un seuillage calibré à **0.20** et d'un automate à états finis (FSM) *Hangover* de **1.0 s** exécuté en Python natif.


* Le regroupement des segments utilise `sklearn.cluster.AgglomerativeClustering(metric='cosine', linkage='average')` au seuil calibré de **0.32** (ou optionnellement `SpectralClustering` par Eigen-gap/Silhouette), suivi d'une boucle Python imbriquée réassignant les locuteurs mineurs (durée cumulée $< 7.0\text{ s}$) au centroïde du locuteur majeur le plus proche.





---

## 2. Confrontation Axe par Axe & Matrice d'Écart (Gap Analysis)

| Axe d'Optimisation | Composant / Fonction STEP3 Actuelle | Recommandation du Rapport de Recherche | Diagnostic d'Écart Technique (Latence, Mémoire, GIL, Concurrence) | Faisabilité d'Intégration dans `coral_env` | Risque Algorithmique & Garantie $\Delta\text{DER}$ |
| --- | --- | --- | --- | --- | --- |
| **Axe 1 : Prétraitement CPU Log-Mel** | Boucle Python séquentielle appelant `scipy.signal.stft` segment par segment sur des fenêtres de 48 000 échantillons.

 | Vue glissante zéro-copie `sliding_window_view` sur lot `(B, 48240)` + fenêtre de Hann pré-divisée par `window.sum()` (`200.0`) + `scipy.fft.rfft(..., workers=-1)` (`pocketfft` C++) + `np.matmul` BLAS + noyau Numba JIT `@njit(parallel=True, fastmath=True)` fusionnant `log` + CMN en place.

 | **Latence** : **4.75 s** (0.95 ms/fenêtre) contre **0.20 s** (0.04 ms/fenêtre) pour 5 000 segments (**Speedup 15x à 30x**).

<br>

<br>**Mémoire & GIL** : Élimine l'allocation de 3 tenseurs temporaires `(32, 80, 300)` par lot et relâche le GIL pendant la RFFT multithreadée et la passe CMN en cache L1/L2.

 | **Immédiate**. `numpy`, `scipy` et `numba` sont déjà présents et utilisés dans `coral_env` (notamment pour la STEP2 `run_scene_detect_tpu.py` et la STEP4 `OneEuroFilterND`).

 | **Risque Nul ($\Delta\text{DER} = 0.00\%$)**. L'intégration du facteur `1.0 / np.sum(raw_window)` reproduit exactement `scaling='spectrum'` avant l'écrêtage à $10^{-10}$, limitant l'erreur max FP32 à $< 6 \cdot 10^{-7}$.

 |
| **Axe 2 : Inférence ONNX ECAPA-TDNN** | Sessions multiples (`intra_op = cpu_count // workers`), appels `session.run()` avec copies mémoire, tentatives historiques de PTQ INT8.

 | Maintien strict du **FP32** (`ORT_ENABLE_ALL`), session unique (`ORT_SEQUENTIAL`, `intra_op = N_physical_cores - 1`), `OMP_WAIT_POLICY=PASSIVE`, `OMP_PROC_BIND=CLOSE`, `allow_spinning=0`, **IOBinding zéro-copie** (`OrtValue`) et option `OpenVINOExecutionProvider` avec `cache_dir`.

 | **Latence** : Gain de **12% à 18%** via IOBinding + tuning MLAS, et speedup de **2.2x** (**10.6 s** vs **23.4 s** sur 100 lots) avec OpenVINO.

<br>

<br>**Concurrence** : Supprime l'invalidation du cache L3 causée par la réplication des poids (25–80 Mo) et l'attente active OpenMP qui affame le thread DMA du Coral TPU.

 | **Élevée**. Le tuning MLAS et `io_binding()` reposent sur `onnxruntime` standard déjà installé. `onnxruntime-openvino` est activable dynamiquement s'il est détecté dans `ort.get_available_providers()`.

 | **Risque Nul ($\Delta\text{DER} = 0.00\%$ en ORT FP32 / $< 0.02\%$ sous OpenVINO)**. Proscrire absolument le PTQ INT8 qui dégrade le DER de **+4.0% à +12.0%**.

 |
| **Axe 3 : Pipelining VAD Coral Edge TPU** | Boucle synchrone trame par trame sous `_tpu_lock` (~15 000 acquisitions/2h) avec copies `set_tensor()` / `get_tensor()`.

 | Pipeline **Producteur-Consommateur à Double Buffering (Ping-Pong)** par blocs de **256 trames** `(256, 15360)` en `int8`, quantification CPU vectorisée SIMD, maintien de `_tpu_lock` par bloc, et vues directes C++ `interpreter.tensor(idx)()`.

 | **Latence** : **4.5 s** contre **8.2 s** (**Speedup 1.8x** sur le VAD) et **-35%** d'overhead Python par trame.

<br>

<br>**GIL & Bus PCIe** : `interpreter.invoke()` relâche le GIL lors du transfert DMA (< 15 µs sur PCIe Gen2 x1), permettant un recouvrement total CPU/ASIC et réduisant la contention mutex d'un facteur 256.

 | **Immédiate**. Repose uniquement sur `threading`, `queue`, `numpy` et l'API native `tflite_runtime` déjà utilisée dans `coral_env` (architecture analogue au Producer-Consumer de la STEP2).

 | **Risque Algorithmique Nul ($\Delta\text{DER} = 0.00\%$)**. Requiert le verrouillage noyau `pcie_aspm=off` et la vérification explicite du délégué `edgetpu-custom-op`.

 |
| **Axe 4 : Clustering AHC & Post-Filtrage** | `sklearn.cluster.AgglomerativeClustering` (matrice $N \times N$ complète), réassignation mineurs par boucles Python, `scipy.signal.medfilt` + FSM Hangover en Python pur.

 | Matrice de Gram BLAS `X @ X.T` + extraction triangulaire supérieure Numba + `fastcluster.linkage(method='average')` avec `t = np.nextafter(0.32, 0.0)` + réassignation BLAS `E_min @ C_maj.T` + noyau Numba `@njit` fusionnant médian (tri par insertion 5 éléments) et FSM Hangover.

 | **Latence** : Clustering réduit de **5.4 s à 0.45 s** pour $N=10\,000$ (**Speedup 8x à 12x**), réassignation centroïdes de **4.5 ms à 0.15 ms** (**30x**), et Médian+FSM de **2.37 ms à 0.032 ms** (**74x**, combiné **28x**).

<br>

<br>**Mémoire** : Divise par 2 l'empreinte RAM du clustering (vecteur condensé $N(N-1)/2$ vs 800 Mo en FP64).

 | **Élevée**. `numba` et `scipy.cluster.hierarchy` sont natifs ; l'ajout de la roue C++ `fastcluster` dans `coral_env` est léger et sécurisé par un fallback automatique vers `scipy.cluster.hierarchy.linkage` (`_HAS_FASTCLUSTER`).

 | **Risque Nul ($\Delta\text{DER} = 0.00\%$, $ARI = 1.0000$)**. L'usage de `np.nextafter` et le décalage d'index `- 1` garantissent une parité bit-à-bit de l'arbre UPGMA avec `scikit-learn`.

 |
| **Axe 5 : Benchmarking & Métriques** | Profilage intrusif `cProfile` (recommandé dans `coral-tpu-hybrid-algorithms`) et validation fonctionnelle par tests unitaires sans métrique acoustique stricte.

 | Profilage hors-processus `py-spy record --native`, `VizTracer` (Perfetto), compteurs PMU `perf stat`, horloge `time.perf_counter_ns()`, et validation `pyannote.metrics` (DER + JER) sur VoxConverse/AMI sous double collar (**0.0s** et **0.25s**).

 | **Biais d'observation** : `cProfile` injecte un surcoût de **+30% à +80%** sur les boucles Python et ignore les threads C++ d'ONNX Runtime et `libedgetpu.so.1`, là où `py-spy` induit **< 1%** d'overhead.

 | **Immédiate**. `time.perf_counter_ns()` est intégré en standard ; `pyannote.metrics` peut être exécuté dans `audio_env` (où Pyannote est déjà installé) pour valider les fichiers JSON générés par `coral_env`.

 | **Garde-fou Qualité**. Le calcul conjoint du DER et du JER sous `collar=0.0s` (précision à la trame vidéo de 40 ms à 25 fps) verrouille la contrainte $\Delta\text{DER} \le 0.1\%$.

 |

---

## 3. Évaluation des Garde-fous Critiques & Incompatibilités Architecturales

### 3.1 Exclusion Stricte du PTQ INT8 sur ECAPA-TDNN (Preuve Mathématique ASP)

Conformément aux règles de `codingstandards.md` (§8 *TPU Anti-Patterns*) et aux conclusions de l'Axe 2 du rapport, toute tentative de quantification post-entraînement (PTQ dynamique via `quantize_dynamic` ou statique QDQ) du modèle ECAPA-TDNN doit être définitivement bannie :

1. **Amplification du bruit dans les blocs `SERes2NetBlock**` : L'accumulation résiduelle récursive $y_i = k_i(x_i + y_{i-1})$ sur $s=8$ sous-bandes de convolutions 1D dilatées ($d \in \{2, 3, 4\}$) et le recalibrage multiplicatif *Squeeze-and-Excitation* ($\tilde{x}_c = s_c \cdot x_c$) amplifient l'erreur de troncature INT8 à chaque couche.


2. **Annulation catastrophique (*Catastrophic Cancellation*) dans la couche ASP** : Le bloc *Channel-Dependent Attentive Statistics Pooling* calcule l'écart-type temporel pondéré par attention softmax $\alpha_{t,c}$ selon la formule :



$$\sigma_c = \sqrt{\sum_{t=1}^{T} \alpha_{t,c} \, h_{t,c}^2 - \mu_c^2 + \epsilon} \quad \text{avec} \quad \mu_c = \sum_{t=1}^{T} \alpha_{t,c} \, h_{t,c}$$



Évaluer la différence $\sum \alpha_{t,c} h_{t,c}^2 - \mu_c^2$ en arithmétique entière 8 bits avant la racine carrée et la `BatchNorm1d` détruit les bits de poids faible lorsque la variance est faible.


3. **Effondrement du seuil AHC** : La similarité cosinus entre l'embedding INT8 et la référence FP32 tombe sous **0.92** (contre **> 0.99** requis), induisant une dérive anisotrope de **0.03 à 0.06** sur la matrice de distance $d_{\cos}(e_i, e_j) = 1 - \cos(\theta_{i,j})$. Avec le seuil AHC fixe calibré à **0.32**, cette dérive déclenche des fusions prématurées de locuteurs (*Speaker Confusion*) et dégrade le DER de **+4.0% à +12.0%**, violant la tolérance maximale $\Delta\text{DER} \le 0.1\%$.



### 3.2 Compatibilité du Double Buffering TPU avec `coral_tpu_orchestrator.py` et la SRAM 8 Mo

L'intégration du pattern Producteur-Consommateur Ping-Pong (blocs de 256 trames) respecte intégralement les invariants matériels du Google Coral M.2 PCIe (`/dev/apex_0`) :

* **Empreinte en SRAM interne (8 Mo) inchangée** : Le modèle TFLite YAMNet INT8 reste compilé pour une dimension d'entrée unitaire `(1, 15360)` (`batch=1` côté ASIC). Les deux tampons Ping-Pong de forme `(256, 15360)` en `int8` occupent seulement $2 \times 256 \times 15\,360 = 7.86\text{ Mo}$ dans la **RAM hôte (CPU)** et non dans la SRAM de l'Edge TPU. L'ASIC ne reçoit qu'une seule trame de 15.36 Ko par appel DMA `invoke()` via la vue mappée `in_view.flat[:] = block_data[i]`, éliminant tout risque d'éviction de cache ou d'erreur OOM sur les 8 Mo de SRAM.


* **Articulation Macro-Verrou / Micro-Verrou** :
* Au niveau **Macro**, le singleton `services/coral_tpu_orchestrator.py` sérialise les étapes du pipeline afin que STEP2, STEP3 et STEP4 n'accèdent jamais simultanément à `/dev/apex_0`.


* Au niveau **Micro** (interne au sous-processus `run_audio_diarization_tpu.py`), l'encapsulation de la boucle de 256 appels `invoke()` dans un unique bloc `with self.tpu_lock:` réduit le nombre d'acquisitions/libérations du mutex de **15 000 à 59** pour 2 heures d'audio. La durée de maintien du verrou par bloc est de $256 \times 0.40\text{ ms} \approx 102\text{ ms}$, ce qui sature le bus PCIe Gen2 x1 tout en permettant à un éventuel thread de télémétrie d'interroger l'état entre deux blocs sans famine.




* **Protection contre le *Silent Fallback* XNNPACK et le blocage ASPM D3** : Le pilote `gasket`/`apex` pouvant échouer avec l'erreur noyau `-110` (`RAM did not enable within timeout`) si l'ASPM PCIe est actif, l'initialisation du délégué `libedgetpu.so.1` dans `run_audio_diarization_tpu.py` ne doit jamais ignorer silencieusement une `ValueError` et doit vérifier la présence effective de l'opérateur `edgetpu-custom-op` dans le graphe TFLite pour éviter une bascule silencieuse sur CPU (20x plus lente).



### 3.3 Parité Mathématique de `fastcluster` et `scipy.cluster.hierarchy.fcluster`

Le remplacement de `sklearn.cluster.AgglomerativeClustering(n_clusters=None, distance_threshold=0.32, metric='cosine', linkage='average')` par `fastcluster.linkage` présente deux subtilités algorithmiques qui doivent être neutralisées :

1. **Inégalité de coupure d'arbre ($<$ vs $\le$)** : `scikit-learn` fusionne les clusters tant que la distance est strictement inférieure au seuil ($d < \text{distance\_threshold}$), tandis que `scipy.cluster.hierarchy.fcluster(Z, t=threshold, criterion='distance')` regroupe les nœuds selon une inégalité large ($d \le t$). Pour obtenir le même partitionnement sur les cas limites en virgule flottante, il est impératif de passer `strict_thresh = np.nextafter(np.float64(distance_threshold), 0.0)` à `fcluster`.


2. **Convention d'indexation des étiquettes (1-based vs 0-based)** : `fcluster` retourne des identifiants de clusters débutant à `1` ($1, 2, \dots, K$), alors que `scikit-learn` retourne des étiquettes `0-indexed` ($0, 1, \dots, K-1$). Appliquer `raw_labels = sch.fcluster(...) - 1` restaure l'invariant d'indexation attendu par l'étape de renommage canonique `SPEAKER_00, SPEAKER_01, ...`.



### 3.4 Préservation Stricte du Contrat JSON Aval (`<video>_audio.json`)

Le snippet C du rapport de recherche retourne uniquement `{"diarization_result": [...], "speaker_stats": {}}`. Or, dans l'architecture `workflow_mediapipe`, les étapes aval STEP4, STEP5 (`json_reducer.py`) et STEP6 (`preprocess_ae_json.py`) consomment le fichier `<video>_audio.json` indexé à **25 fps** (contrat de normalisation STEP1) contenant obligatoirement `frames_analysis` (avec `is_speech_present` et `active_speaker_labels`), `speaker_stats` et optionnellement `speaker_embeddings`. La modernisation de `run_audio_diarization_tpu.py` doit donc injecter les segments `diarization_result` et `speaker_stats` issus de `fast_ahc_clustering_and_postprocess` directement dans le constructeur existant de `frames_analysis` sans altérer aucune clé du schéma JSON.

---

## 4. Plan d'Action et Recommandations de Modernisation Priorisées

### Phase 1 : Quick Wins (Priorité P0 — Risque Nul, Sans Rupture d'Architecture)

#### 1.1 Verrouillage Système PCIe et Détection Anti-Fallback (`coral_tpu_orchestrator.py` & `run_audio_diarization_tpu.py`)

* Vérifier dans le script de diagnostic de démarrage (`scripts/validate_startup.py`) la présence de `pcie_aspm=off` dans `/proc/cmdline` lorsque `ENABLE_CORAL_TPU_ACCELERATION=true`.


* Ajouter une assertion post-chargement du délégué `libedgetpu.so.1` pour garantir qu'aucun fallback silencieux sur le CPU XNNPACK ne se produit.



#### 1.2 Tuning MLAS/OpenMP, Session Unique et IOBinding Zéro-Copie ONNX Runtime

Dans `workflow_scripts/step3/run_audio_diarization_tpu.py`, configurer les variables d'environnement OpenMP **avant** l'import de `onnxruntime`, fixer `intra_op_num_threads` au nombre de cœurs physiques disponibles moins 1 (réservé au thread Edge TPU), et remplacer `session.run()` par `session.run_with_iobinding()` :

```python
# Dans workflow_scripts/step3/run_audio_diarization_tpu.py (Avant import onnxruntime)
import os
import psutil

os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
os.environ.setdefault("OMP_PROC_BIND", "CLOSE")
os.environ.setdefault("OMP_PLACES", "cores")

import numpy as np
import onnxruntime as ort

def create_optimized_ecapa_session(
    onnx_model_path: str,
    use_openvino: bool = True,
    openvino_cache_dir: str = "/var/tmp/ort_openvino_cache",
) -> tuple[ort.InferenceSession, int]:
    """Initialise une session ONNX Runtime FP32 unique optimisée pour ECAPA-TDNN."""
    physical_cores = psutil.cpu_count(logical=False) or max(1, (os.cpu_count() or 4) // 2)
    ort_threads = max(1, physical_cores - 1)  # 1 coeur physique réservé au thread DMA Edge TPU

    sess_options = ort.SessionOptions()
    sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.intra_op_num_threads = ort_threads
    sess_options.inter_op_num_threads = 1
    sess_options.add_session_config_entry("session.intra_op.allow_spinning", "0")

    providers: list = []
    available = ort.get_available_providers()
    if use_openvino and "OpenVINOExecutionProvider" in available:
        os.makedirs(openvino_cache_dir, exist_ok=True)
        providers.append(
            (
                "OpenVINOExecutionProvider",
                {
                    "device_type": "CPU_FP32",
                    "num_of_threads": str(ort_threads),
                    "cache_dir": openvino_cache_dir,
                },
            )
        )
    providers.append("CPUExecutionProvider")

    session = ort.InferenceSession(onnx_model_path, sess_options=sess_options, providers=providers)
    return session, ort_threads

```

#### 1.3 Vectorisation BLAS de la Réassignation des Locuteurs Mineurs ($< 7.0\text{ s}$)

Remplacer immédiatement la double boucle Python de calcul de distance cosinus entre segments mineurs et centroïdes majeurs par un produit matriciel BLAS `np.matmul` (gain **30x**, de 4.5 ms à 0.15 ms) :

```python
# Remplacement drop-in de la réassignation des locuteurs mineurs (< 7.0s)
if minor_cids and major_cids:
    k_maj = len(major_cids)
    major_centroids = np.empty((k_maj, unit_embs.shape[1]), dtype=np.float32)

    for idx_k, m_cid in enumerate(major_cids):
        c_vec = np.mean(unit_embs[raw_labels == m_cid], axis=0)
        c_norm = np.linalg.norm(c_vec)
        major_centroids[idx_k] = c_vec / max(float(c_norm), 1e-12)

    minor_mask = np.isin(raw_labels, minor_cids)
    minor_indices = np.flatnonzero(minor_mask)
    minor_embs = unit_embs[minor_indices]  # Forme (N_mineurs, 192)

    # Produit matriciel BLAS SGEMM : (N_mineurs, 192) @ (192, K_majeurs)
    sim_matrix = np.matmul(minor_embs, major_centroids.T)
    best_major_idx = np.argmax(sim_matrix, axis=1)

    major_cids_arr = np.asarray(major_cids, dtype=final_labels.dtype)
    final_labels[minor_indices] = major_cids_arr[best_major_idx]

```

---

### Phase 2 : Accélération Algorithmique Haute Densité (Priorité P1 — Gain 8x à 74x)

#### 2.1 Extracteur Log-Mel Vectorisé par Lots + Noyau Numba CMN + IOBinding

Intégrer la classe `BatchedLogMelECAPAExtractor` dans `workflow_scripts/step3/run_audio_diarization_tpu.py` pour remplacer la boucle `scipy.signal.stft` et l'appel `session.run()` :

* Pré-calculer la fenêtre de Hann périodique divisée par sa somme : `raw_window = scipy.signal.windows.hann(400, sym=False).astype(np.float32)` puis `scaled_window = np.ascontiguousarray(raw_window / np.sum(raw_window), dtype=np.float32)`.


* Appliquer `np.pad(wav_batch, ((0, 0), (120, 120)), mode="constant", constant_values=0.0)` puis `sliding_window_view(wav_padded, window_shape=400, axis=-1)[:, ::160, :]` pour générer la vue `(B, 300, 400)` sans copie.


* Exécuter `scipy.fft.rfft(windowed, n=400, axis=-1, workers=self.fft_workers)`, projeter via `np.matmul(self.mel_basis, mag, out=self._in_buffer[:cur_bs])` directement dans le tampon pré-alloué lié à `self._in_ortval` (`OrtValue`), appliquer le noyau `@njit(parallel=True, fastmath=True, nogil=True, cache=True)` `_fused_log_cmn_inplace`, et déclencher `self.session.run_with_iobinding(self._io_binding)`.



#### 2.2 Clustering AHC Condensé via Matrice de Gram BLAS et `fastcluster`

Ajouter `fastcluster>=1.2.6` aux dépendances de `coral_env` et remplacer `AgglomerativeClustering` par le calcul de la matrice de Gram et l'extraction triangulaire supérieure Numba :

```python
import scipy.cluster.hierarchy as sch
from numba import njit

try:
    import fastcluster
    _HAS_FASTCLUSTER = True
except ImportError:
    _HAS_FASTCLUSTER = False

@njit(fastmath=True, nogil=True, cache=True)
def _extract_upper_triangle_cosine_dist(gram_matrix: np.ndarray) -> np.ndarray:
    """Extrait le vecteur de distance cosinus condensé 1D float64 depuis la matrice de Gram."""
    n = gram_matrix.shape[0]
    size = (n * (n - 1)) // 2
    condensed = np.empty(size, dtype=np.float64)
    idx = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            dist = 1.0 - float(gram_matrix[i, j])
            if dist < 0.0:
                dist = 0.0
            condensed[idx] = dist
            idx += 1
    return condensed

def compute_ahc_labels(unit_embs: np.ndarray, distance_threshold: float = 0.32) -> np.ndarray:
    """Calcule les étiquettes AHC (average linkage, cosine) avec parité exacte scikit-learn."""
    n_segs = unit_embs.shape[0]
    if n_segs == 0:
        return np.empty(0, dtype=np.int32)
    if n_segs == 1:
        return np.array([0], dtype=np.int32)

    gram = np.matmul(unit_embs, unit_embs.T)
    condensed_dist = _extract_upper_triangle_cosine_dist(gram)

    if _HAS_FASTCLUSTER:
        linkage_matrix = fastcluster.linkage(condensed_dist, method="average")
    else:
        linkage_matrix = sch.linkage(condensed_dist, method="average")

    strict_thresh = np.nextafter(np.float64(distance_threshold), 0.0)
    return (sch.fcluster(linkage_matrix, t=strict_thresh, criterion="distance") - 1).astype(np.int32)

```

#### 2.3 Fusion Numba JIT du Filtre Médian VAD et de la FSM Hangover

Remplacer l'enchaînement `scipy.signal.medfilt(scores, kernel_size=5)` + boucle Python Hangover par le noyau compilé `fused_medfilt5_binarize_hangover_fsm(raw_scores, threshold=0.20, hangover_frames=2)` utilisant un tri par insertion en registre sur 5 éléments avec bourrage zéro aux frontières (identique à la convention de `scipy.signal.medfilt`) et libération du GIL (`nogil=True`).

---

### Phase 3 : Refactorisation Pipeline Asynchrone Edge TPU (Priorité P2 — Recouvrement DMA/CPU)

Refondre l'étage VAD dans `workflow_scripts/step3/run_audio_diarization_tpu.py` autour de la classe `AsyncEdgeTPUVADPipeline` (Snippet B du rapport) en s'intégrant avec le verrou `_tpu_lock` et le format de progression UI de `WorkflowCommandsConfig` :

1. **Découpage Zéro-Copie** : Générer la vue globale `all_windows = sliding_window_view(audio_pcm, window_shape=15360)[::7680]` sur le tampon PCM 16 kHz.


2. **Double Tampon Circulaire (`block_size = 256`)** : Allouer deux tampons `ping_pong_buffers` de dimension `(256, 15360)` en `int8` orchestrés par deux files `ready_queue` (`maxsize=1`) et `free_queue` (`maxsize=2`).


3. **Thread Producteur CPU (`daemon=True`)** : Normaliser (`1.0 / 32768.0` si `int16`) et quantifier en SIMD (`np.clip(np.rint(float_win * inv_scale + zp), -128, 127, out=dst_buffer[:count], casting="unsafe")`) le bloc $K+1$ pendant que le TPU traite le bloc $K$.


4. **Boucle Consommateur Edge TPU sans Copie** : Acquérir `with self.tpu_lock:` une seule fois par bloc de 256 fenêtres, obtenir les accesseurs directs `in_view = self._in_tensor_accessor()` et `out_view = self._out_tensor_accessor()` initialisés via `interpreter.tensor(idx)`, copier dans le tampon DMA `in_view.flat[:] = block_data[i]`, appeler `self.interpreter.invoke()` et lire `raw_q_outputs[start_idx + i] = out_view.flat[0]`.



---

### Phase 4 : Validation Scientifique, Benchmarking & Non-Régression JSON

1. **Validation Unitaire et Contrat JSON (`tests/unit/test_step3_audio_diarization_tpu.py`)** :
* Ajouter un test d'équivalence numérique vérifiant que `BatchedLogMelECAPAExtractor.compute_logmel_batch` présente une erreur absolue maximale $< 10^{-6}$ vis-à-vis de la boucle historique `scipy.signal.stft(..., scaling='spectrum')`.


* Ajouter un test d'identité du clustering vérifiant que `compute_ahc_labels` retourne un indice de Rand ajusté $ARI = 1.0$ par rapport à `sklearn.cluster.AgglomerativeClustering(n_clusters=None, distance_threshold=0.32, metric='cosine', linkage='average')`.


* Vérifier que le fichier `<video>_audio.json` généré conserve strictement les clés `frames_analysis`, `speaker_stats`, `is_speech_present`, `active_speaker_labels` et la compatibilité avec le réducteur streaming `ijson` de la STEP5 (`tests/unit/test_step5_json_reducer.py`).




2. **Protocole de Benchmarking Acoustique (`scripts/bench_step3_tpu_der.py`)** :
* Déployer le script d'évaluation basé sur `pyannote.metrics` (`DiarizationErrorRate`, `JaccardErrorRate`) exécutable via l'interpréteur `audio_env/bin/python` sur des extraits de référence annotés en RTTM (VoxConverse / AMI Meeting et échantillons broadcast internes "Camille").


* Exiger la validation automatique du double critère sous `skip_overlap=False` :
* **Protocole Post-Production Strict (`collar = 0.00s`)** : $\vert{}\text{DER}_{\text{optimisé}} - \text{DER}_{\text{baseline}}\vert{} \le 0.05\%$ (garantissant a fortiori la contrainte $\vert{}\Delta\text{DER}\vert{} \le 0.1\%$) et stabilité du **JER** sur les locuteurs secondaires autour du seuil de $7.0\text{ s}$.


* **Protocole Académique (`collar = 0.25s`)** : Traçabilité des composantes *Missed Speech*, *False Alarm* et *Speaker Confusion* dans les rapports de performance.






3. **Profilage Non-Intrusif et Mise à Jour Documentaire** :
* Mettre à jour `.agents/skills/coral-tpu-hybrid-algorithms/SKILL.md` et `docs/workflow/pipeline/03-audio-analysis.md` pour remplacer l'usage de `cProfile` par `py-spy record --native -F -r 500` et `perf stat` lors des diagnostics de performance CPU/TPU.