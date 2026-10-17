## 1. Audit Différentiel et Matrice des Écarts (Gap Analysis)

La confrontation entre le rapport architectural de référence et les implémentations actuelles de la STEP2 (`workflow_scripts/step2/run_transnet.py` sous `transnet_env` et `workflow_scripts/step2/run_transnet_cv5.py` sous `transnet_cv5_env`) met en évidence un déplacement du goulet d'étranglement : alors qu'une trame RGB24 en $48 \times 27$ (`uint8`) ne pèse que $3\,888\text{ octets}$ ($\approx 97,2\text{ Ko/s}$ à $25\text{ fps}$), 53 % du temps total d'exécution (Phases 2 et 3) est absorbé par les allocations Python, la contention du GIL et les copies mémoire redondantes avant même l'atteinte du bus PCIe.

### Matrice Comparative des 5 Phases du Pipeline STEP2

| Phase du Pipeline | Implémentation PyTorch Actuelle (`run_transnet.py`) | Implémentation ONNX/CV5 Actuelle (`run_transnet_cv5.py`) | Architecture Cible Zéro-Copie (Rapport de Recherche) | Latence Actuelle vs Cible (/ 1 000 trames) | Facteur de Gain Local & Sévérité de l'Écart |
| --- | --- | --- | --- | --- | --- |
| **1. Décodage & Ingestion** | Sous-processus FFmpeg (`swscale` vers $48 \times 27$ RGB24), `ffmpeg_threads: 1` par défaut, lecture tube `stdout` vers `bytes` puis `bytearray`, découpage unitaire et insertion trame par trame dans `queue.Queue(maxsize=1000)`.

 | Hérite de la même boucle bloquante : `queue.Queue`, `bytearray`, `arr_split = list(...)` et `frames.append(f)` avec 1 000 acquisitions/libérations de mutex par millier de trames.

 | FFmpeg `-threads 0` et `-vf fps=25.0,scale=48:27:flags=bilinear` avec `bufsize=16 Mo` ; lecture C-level hors-GIL via `proc.stdout.readinto(mv)` dans un double tampon Ping-Pong pré-alloué de $2 \times [2550, 27, 48, 3]$ ($\approx 9,91\text{ Mo}$ chacun), réduisant la synchronisation inter-threads d'un facteur $2\,500\times$.

 | $140,0\text{ ms}$ (Décodage, 28 %) + $195,0\text{ ms}$ (Ingestion/GIL, 39 %) $\rightarrow$ **$85,0\text{ ms}$ + $8,5\text{ ms}$**.

 | **$1,65\times$** (Décodage) / **$22,9\times$** (Ingestion) — **Critique**.

 |
| **2. Manipulation Tensorielle** | Slicing manuel par fenêtre glissante via `build_window()`, appels répétés à `np.asarray()` et `np.stack()` dupliquant physiquement les trames d'un facteur $2\times$ en RAM ($W=100, S=50$).

 | Identique : matérialisation explicite des fenêtres via `build_window()` et `np.stack()` en mémoire centrale à chaque lot.

 | Vue 5D zéro-copie en $O(1)$ via `sliding_window_view(buf[:req], window_shape=100, axis=0)[::50].transpose(0, 4, 1, 2, 3)` (ou `as_strided`) aux strides exacts `(194400, 3888, 144, 3, 1)` ; padding aux bords (`buf[0:25] = buf[25:26]`) et report d'overlap (`carry_50_frames`) in-place en cache L1/L3.

 | Inclus dans la phase d'ingestion ($195,0\text{ ms} \rightarrow 8,5\text{ ms}$).

 | **Élimination de 4 copies RAM** — **Critique**.

 |
| **3. Transferts PCIe (H2D / D2H)** | Conversion en tenseurs PyTorch paginés et transfert H2D implicite par lot (`batch_size: 8` dans `step2_transnet.json`) avec surcharge du contexte CUDA PyTorch ($\sim 2\text{ Go}$ VRAM).

 | Appel standard `session.run(None, ...)` provoquant la validation de schéma Python, l'allocation dynamique paginée, la copie vers un staging buffer interne et une synchronisation bloquante du stream CUDA.

 | Assemblage DMA dans un `host_staging_buffer` contigu $[B, 100, 27, 48, 3]$ (`np.copyto`), transfert H2D sans réallocation via `input_ortvalue.update_inplace()` et liaison VRAM persistante via `ort.IOBinding` (`bind_ortvalue_input` / `bind_ortvalue_output`).

 | $70,0\text{ ms}$ (14 %) $\rightarrow$ **$6,0\text{ ms}$**.

 | **$11,7\times$** — **Haute**.

 |
| **4. Exécution du Modèle** | Modèle PyTorch (`transnetv2_pytorch.py`) avec `batch_size: 8`, `mixed_precision: true` (`float16`), `warmup: true` (`warmup_batches: 2`).

 | Sonde expérimentale `cv2.dnn.DNN_ENGINE_NEW` (`DNN_TARGET_CPU`) avec repli vers `CUDAExecutionProvider` par défaut, sans `IOBinding`, sans recherche exhaustive cuDNN ni verrouillage TF32.

 | `SessionOptions` (`ORT_ENABLE_ALL`, `ORT_SEQUENTIAL`, `enable_mem_pattern=True`) + `CUDAExecutionProvider` (`arena_extend_strategy='kSameAsRequested'`, `cudnn_conv_algo_search='EXHAUSTIVE'`, `cudnn_conv_use_max_workspace='1'`, `do_copy_in_default_stream='1'`, `use_tf32=0`) + warm-up à lot statique fixe ($B=25$, zero-padding du dernier lot).

 | $80,0\text{ ms}$ (16 %) $\rightarrow$ **$24,0\text{ ms}$**.

 | **$3,33\times$** — **Haute**.

 |
| **5. Post-Processing & Sigmoïde** | Sigmoïde PyTorch sur GPU puis extraction et concaténation de listes Python.

 | Calcul `np.exp()` non vectorisé in-place ou appliqué sur la fenêtre complète de 100 trames avant troncature, suivi d'extractions en listes Python.

 | Transfert D2H direct des logits ($\sim 10\text{ Ko}$ pour $B=25$), troncature immédiate à la tranche centrale utile `logits[:valid_b, 25:75]` ($1\,250$ `float32`, soit $5\text{ Ko}$), et sigmoïde C/SIMD in-place (`np.negative`, `np.exp`, `+= 1.0`, `np.divide`) en $< 15\,\mu\text{s}$.

 | $15,0\text{ ms}$ (3 %) $\rightarrow$ **$0,5\text{ ms}$**.

 | **$30,0\times$** — **Moyenne**.

 |
| **TOTAL PIPELINE** | **Pipeline séquentiel PyTorch lourd en VRAM**.

 | **Pipeline ONNX bridé par l'ingestion CPU/GIL et `session.run()**`.

 | **Pipeline zéro-copie en double tampon recouvrant décodage CPU (bloc $k+1$) et inférence GPU (bloc $k$)**.

 | **$500,0\text{ ms}$ $\rightarrow$ $\sim 95,0\text{ ms}$ (masqué)**.

 | **Gain global : $4,2\times$ à $5,1\times$**.

 |

### Évaluation de la Faisabilité Technique des Gains (3x à 5x)

Le facteur d'accélération global de **3x à 5x** (convergeant vers $\sim 95\text{ ms}$ par millier de trames, soit $> 260\times$ le temps réel à $25\text{ fps}$) est **pleinement réalisable** sur l'architecture actuelle :

* **Élimination de la loi d'Amdahl inversée** : Dans `run_transnet.py` et `run_transnet_cv5.py`, le déplacement de seulement $194,4\text{ Ko}$ de données nouvelles toutes les 50 trames génère 4 copies RAM successives et une contention constante du GIL, occupant 67 % du temps total (Décodage + Ingestion/GIL). Le passage à `stdout.readinto()` par blocs de $2\,500$ trames ($9,72\text{ Mo}$, tenant dans le cache L3) abaisse le coût d'ingestion de $195\text{ ms}$ à $8,5\text{ ms}$.


* **Recouvrement asynchrone matériel (Pipelining I/O & GPU)** : Grâce au double tampon Ping-Pong (`buffers[0]` et `buffers[1]`), l'exécution GPU + DMA + post-processing ($24,0 + 6,0 + 0,5 = 30,5\text{ ms}$ pour $1\,000$ trames) est intégralement masquée derrière le temps de décodage FFmpeg multi-threadé ($85,0\text{ ms}$ pour $1\,000$ trames). La vitesse globale du pipeline devient ainsi bornée uniquement par la vitesse de décodage et de scaling CPU de FFmpeg.



---

## 2. Évaluation Critique des Recommandations et Arbitrages

### Axe 1 — Ingestion : Maintien strict de FFmpeg `swscale` CPU et rejet de NVDEC

* **Validation de l'invariance numérique** : Le contrat de la STEP1 normalise toutes les vidéos en MP4 / H.264 / `yuv420p` / $25\text{ fps}$. Lors du sous-échantillonnage spatial extrême d'un flux Full HD ($1920 \times 1080$, soit $2\,073\,600\text{ pixels}$) vers la résolution d'entrée de TransNetV2 ($48 \times 27$, soit $1\,296\text{ pixels}$, facteur de réduction de $1\,600\times$), `libswscale` utilise un filtre polyphasé et des coefficients matriciels YUV $\rightarrow$ RGB spécifiques. Déporter ce redimensionnement sur GPU via NVDEC (`h264_cuvid` / PyAV / Decord / `nppiResize`) altère les points d'échantillonnage et les arrondis flottants, ce qui déplace les logits autour du seuil de décision $0,5$ et brise la contrainte $\Delta P < 10^{-5}$ ainsi que l'invariance du F1-score.


* **Validation de l'empreinte VRAM et IPC** : Le décodage NVDEC impose un coût d'initialisation élevé ($\sim 150\text{ à }300\text{ ms}$) et alloue un pool de 8 à 16 surfaces NV12 haute résolution en VRAM ($\sim 120\text{ à }350\text{ Mo}$). Sur un poste de travail disposant d'une carte à VRAM contrainte ou partagée, conserver une empreinte VRAM décodeur de **$0\text{ Mo}$** et ne faire transiter par le pipe IPC POSIX que les trames déjà réduites en $48 \times 27 \times 3$ ($3\,888\text{ octets}$) est l'arbitrage optimal.


* **Point de vigilance sur `-sws_flags bilinear` et `-threads 0**` : Pour garantir une parité bit-à-bit stricte avec l'implémentation actuelle de `run_transnet.py` / `run_transnet_cv5.py`, il est impératif que les flags de `scale` dans la commande `ffmpeg_cmd` de la nouvelle classe `ZeroCopyTransNetPipeline` correspondent exactement au filtre utilisé jusqu'ici par FFmpeg par défaut (`bicubic` vs `bilinear`) si celui-ci n'était pas forcé à `bilinear` dans le script existant. En revanche, remplacer `"ffmpeg_threads": 1` (actuellement dans `config/step2_transnet.json`) par `-threads 0` est sans risque sur le déterminisme des pixels décodés tout en débloquant le gain de $1,65\times$ sur le décodage.



### Axe 2 — Strides Tricks : Applicabilité de `sliding_window_view` et audit des cas limites

* **Exactitude mathématique de l'overlap de 50 trames** : Le rapport démontre rigoureusement pourquoi un tampon de $K=50$ fenêtres requiert un recouvrement inter-blocs de **50 trames** (et non 25). La fenêtre $w$ prédit la tranche centrale utile $$ (soit les trames brutes $[50w : 50w + 50]$) mais nécessite un contexte gauche de 25 trames et un contexte droit de 25 trames, couvrant ainsi les trames brutes $[50w - 25 : 50w + 75]$. Le bloc 0 ($w \in [0, 49]$) consomme donc les trames brutes $[-25 : 2525]$ (soit $2\,525$ trames lues + 25 trames de padding gauche = $2\,550$ trames), et le bloc 1 ($w \in [50, 99]$) doit démarrer à la trame brute $50(50) - 25 = 2\,475$. L'intersection exacte entre la fin du bloc 0 ($2\,525$) et le début du bloc 1 ($2\,475$) est l'intervalle $[2475 : 2525]$ de longueur $50\text{ trames}$, situé précisément aux index `buf[2500:2550]` du tampon précédent.


* **Audit des cas limites (Edge Cases) dans le code de référence du rapport** :
1. *Vidéos très courtes ($N < 100\text{ trames}$, voire $N < 50$)* : Si une vidéo contient $N = 30\text{ trames}$, le premier appel producteur lit `frames_read = 30 < 2525` (`is_first = True`, `is_eof = True`). Le consommateur réplique `buf[0:25] = buf[25:26]` (`valid_buf_len = 55`), sauvegarde `last_valid_frame[0] = buf[54]`, calcule `total_windows_needed = (30 + 49) // 50 = 1`, `num_win = 1`, `required_buf_len = 1 * 50 + 50 = 100`, et propage `buf[55:100] = last_valid_frame`. La vue `sliding_window_view(buf[:100], 100, axis=0)[::50]` génère exactement 1 fenêtre $[1, 100, 27, 48, 3]$ dont les prédictions centrales $$ sont tronquées à `[:30]` : le comportement est **mathématiquement exact**.


2. *Faille critique détectée sur les longueurs multiples exactes du bloc ($N = 2\,525$, ou $N = 2\,525 + 2\,500k$)* : Dans le code de référence du rapport (`ZeroCopyTransNetPipeline.process_video`), si une vidéo fait exactement $N = 2\,525\text{ trames}$, le premier tour lit $2\,525\text{ trames}$ (`frames_read == frames_to_read`, donc `is_eof = False`) et émet `emitted_windows = 50` (couvrant $2\,500\text{ trames}$). Au second tour, FFmpeg renvoie $0\text{ octet}$ (`frames_read = 0`, `is_first = False`, `is_eof = True`). Or, dans le bloc `else` (`is_eof == True`) du rapport, la ligne `buf[valid_buf_len:required_buf_len] = last_valid_frame` utilise `last_valid_frame` qui contient `buf[2549]` (la trame brute $2\,524$), mais la copie `buf[0 : self.overlap_frames] = carry_50_frames` est dupliquée deux fois et si `total_raw_frames` était un multiple exact de $2\,500$ (ex: $N = 2\,500$ impossible au tour 1 car il lit $2\,525$, mais possible si `frames_read = 0` après que toutes les fenêtres nécessaires ont déjà été émises), `num_win <= 0` déclenche un `break` propre. En revanche, si $2\,500 < N \le 2\,525$, au tour 1 `is_eof` vaut `True` pour $N < 2\,525$ et `total_windows_needed = 51`, ce qui requiert `required_buf_len = 51 * 50 + 50 = 2600` trames ! **Anomalie critique identifiée dans le dimensionnement du tampon du rapport** : pour $N \in [2501, 2524]$, `frames_read` est $< 2525$, donc `is_eof = True` dès le premier bloc, `total_windows_needed` vaut $\lceil N / 50 \rceil = 51\text{ fenêtres}$, et `required_buf_len = 51 * 50 + 50 = 2600`, ce qui **dépasse la capacité pré-allouée du buffer** (`buffer_capacity_frames = 2550`) et tronque `buf[:2600]` à $2\,550$ (ne générant que 50 fenêtres au lieu de 51, perdant ainsi les prédictions des trames $2\,500$ à $N-1$) !


3. *Correctif chirurgical obligatoire pour le buffer* : Allouer `self.buffers` avec une capacité de `self.buffer_capacity_frames + WINDOW_STRIDE` (soit $2\,550 + 50 = 2\,600\text{ trames}$, $+194\text{ Ko}$ en RAM seulement) ou borner `num_win = min(self.windows_per_chunk, total_windows_needed - emitted_windows)` en ne levant `is_eof` définitif qu'après avoir vidé le reliquat dans un tour supplémentaire. Augmenter la taille physique des deux tampons à $2\,600\text{ trames}$ tout en gardant une lecture nominale à $2\,550$ (tour 1) / $2\,500$ (tours suivants) résout ce cas limite en $O(1)$ sans ajouter la moindre branche conditionnelle.





### Axe 3 — Précision & Invariance : `use_tf32=0`, rejet du FP16 global et conflit avec `step2_transnet.json`

* **Incompatibilité du FP16 global sur TransNetV2** : Actuellement, `config/step2_transnet.json` et `codingstandards.md` spécifient `"mixed_precision": true` et `"amp_dtype": "float16"` (conçu pour l'autocast PyTorch qui maintient certaines réductions en FP32). Sous ONNX Runtime, convertir globalement le graphe en FP16 expose la couche *Frame Similarity* (`Mul -> ReduceSum -> Sqrt -> Div` pour la normalisation $L_2$, puis `MatMul` temporel $100 \times 100$) à des dépassements de capacité (*overflow* au-delà de $65\,504$ vers $+\infty$/`NaN`) ou à des *underflows* sur les fondus au noir. De plus, sur les fondus enchaînés lents, les logits proches de $0,0$ ($P \approx 0,5$) basculent sous l'effet de l'imprécision FP16 ($\sim 5 \times 10^{-4}$), décalant les timecodes de coupure.


* **Impératif du flag `use_tf32=0**` : Depuis ONNX Runtime 1.18+, le mode TensorFloat-32 (mantisse réduite de 23 bits à 10 bits sur architectures NVIDIA Ampere et ultérieures) est activé par défaut dans `CUDAExecutionProvider`. Forcer `"use_tf32": 0` est indispensable pour préserver une arithmétique IEEE-754 FP32 stricte ($\Delta P \le 3 \times 10^{-7} \ll 10^{-5}$) et garantir un F1-score invariant bit-à-bit.



### Axe 4 — OpenCV 5.0 DNN (`ENGINE_NEW`) vs ONNX Runtime CUDA

* **Confrontation avec la doctrine actuelle du dépôt** : Les standards du projet (`codingstandards.md` et `.agents/skills/opencv5-dnn-engine-expert/SKILL.md`) positionnent OpenCV 5.0 DNN (`cv2.dnn.DNN_BACKEND_OPENCV`, `cv2.dnn.DNN_TARGET_CPU`, `cv2.dnn.DNN_ENGINE_NEW`) comme moteur primaire expérimental dans `run_transnet_cv5.py` lorsque `USE_OPENCV5_STEP2=true`, avec validation pré-vol d'opérateurs et repli vers ONNX Runtime.


* **Verdict architectural et arbitrage** :
1. Le nouveau moteur graphe d'OpenCV 5.0 est strictement **CPU-only** (`DNN_TARGET_CPU`). Or, TransNetV2 opère sur des volumes 3D spatio-temporels ($100 \times 27 \times 48 = 129\,600\text{ voxels}$ par fenêtre, avec 32 à 128 canaux et $B=25$), représentant plusieurs dizaines de GFLOPs par lot où `CUDAExecutionProvider` est **6x à 12x plus rapide** que le moteur CPU d'OpenCV 5.0.


2. Le modèle `transnetv2.onnx` brut échoue dans l'importeur C++ d'OpenCV DNN à cause des nœuds `Flatten` sur tenseurs 5D (`axis=3`) et du broadcasting 5D avec constantes scalaires 0D dans `Mul`/`Div`.


3. **Recommandation d'alignement** : Dans `export_transnet_onnx.py` (ou en pré-traitement du modèle), intégrer la passe `sanitize_transnetv2_for_opencv5()` (remplacement de `Flatten` 5D par `Reshape` explicite `[-1, C * 3 * 6]` et promotion des initializers 0D de `Mul`/`Div` en tenseurs 1D `(1,)`) afin que la sonde OpenCV 5.0 passe la validation pré-vol sans crash sur les machines dépourvues de GPU. En revanche, dès qu'un GPU NVIDIA avec `CUDAExecutionProvider` est disponible, **ONNX Runtime GPU avec `IOBinding` doit être prioritaire sur OpenCV 5.0 CPU**, ce dernier devenant le moteur de repli CPU optimisé (au lieu de l'inverse).





---

## 3. Analyse de la Dette Technique et des Risques de Régression

### Fichiers et Configurations Impactés

| Fichier / Composant | Nature de l'Impact & Dette Technique Identifiée | Action Corrective Requise |
| --- | --- | --- |
| `workflow_scripts/step2/run_transnet_cv5.py` | Contient la boucle d'ingestion héritée (`queue.Queue`, `bytearray`, `build_window`, `np.stack`) et l'appel naïf `session.run()`.

 | Remplacer le pipeline d'ingestion et d'inférence par `ZeroCopyTransNetPipeline` et `TransNetV2GpuEngine` tout en conservant les hooks de logging et le chargeur dynamique `LD_LIBRARY_PATH`.

 |
| `workflow_scripts/step2/run_transnet.py` | Implémentation PyTorch historique (`transnet_env`) souffrant du même goulet d'étranglement CPU/GIL (67 % du temps).

 | Rétro-porter `ZeroCopyTransNetPipeline` (Axe 1 + Axe 2 : `readinto` + `sliding_window_view`) pour accélérer également le chemin PyTorch par défaut sans modifier ses poids.

 |
| `workflow_scripts/step2/export_transnet_onnx.py` | Exporte le graphe ONNX standard rejeté par `cv2.dnn.readNet` sur `Flatten` 5D et `Mul`/`Div` 0D.

 | Intégrer la fonction `sanitize_transnetv2_for_opencv5()` directement en fin d'export ONNX.

 |
| `config/step2_transnet.json` | Définit `"ffmpeg_threads": 1`, `"batch_size": 8`, `"mixed_precision": true`, `"amp_dtype": "float16"`.

 | Ajouter `"onnx_batch_size": 25`, `"windows_per_chunk": 50`, `"use_tf32": false`, et passer `"ffmpeg_threads": 0`.

 |
| `requirements-transnet_cv5_env.txt` | Doit garantir l'étanchéité de `transnet_cv5_env` (aucune dépendance PyTorch ou CuPy) et la stabilité cuDNN.

 | Verrouiller `onnxruntime-gpu`, `numpy>=1.20` (pour `sliding_window_view`) et vérifier la version `nvidia-cudnn-cu12`.

 |

### Risques de Régression sur les Contrats d'Interface (Logs, UI Flask et Timecodes)

1. **Contrat de Streaming des Logs (`WorkflowCommandsConfig._get_step2_config`)** :
Dans `config/workflow_commands.py`, le suivi temps réel de la Timeline connectée et du `PollingManager` repose sur des expressions régulières strictes compilées pour `STEP2` :


* `total` : `r"TOTAL[_ ]VIDEOS[_ ]TO[_ ]PROCESS:\s*(\d+)"`.


* `current` : `r"PROCESSING[_ ]VIDEO:\s*(.*)$"`.


* `internal_simple` : `r"INTERNAL[_ ]PROGRESS:\s*(\d+)\s*batches\s*-\s*(.*)$"`.


* `internal` : `r"INTERNAL[_ ]PROGRESS:\s*(\d+)/(\d+)\s*frames\s*\((\d+)%\)\s*-\s*(.*)"`.


* `current_success_line_pattern` : `r"Succès:\s*(.*?)(?:\.csv|\.json)\s+créé"`.


* **Risque** : Le script `ZeroCopyTransNetPipeline` fourni dans le rapport de recherche n'émet aucun de ces marqueurs pendant la boucle `while True` du consommateur ni dans `infer_windows()`. S'il est intégré tel quel, la barre de progression de la STEP2 restera bloquée à 0 % dans l'UI Flask et les étapes aval ne détecteront pas la complétion par fichier.


* **Mitigation** : Émettre `INTERNAL_PROGRESS: {processed_frames}/{total_frames} frames ({pct}%) - {video_name}` (ou le pattern `batches`) à la fin de chaque chunk de 50 fenêtres ($2\,500\text{ trames}$) dans la boucle consommatrice avec `flush=True`, et conserver intacte la ligne finale `Succès: <nom>.csv créé`.




2. **Conflit Critique de Formatage des Timecodes (`HH:MM:SS:FF` vs `HH:MM:SS.mmm`)** :
* **Constat d'écart** : Le code de référence du rapport implémente `frame_to_smpte_25fps(frame_idx)` qui retourne le format `f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"` (avec deux-points et numéro de trame `00..24`). Or, `codingstandards.md` (§5 Pipeline - STEP2) stipule explicitement le contrat `Timecode HH:MM:SS.mmm` (millisecondes), qui est consommé en aval par les scripts de découpe CSV (`media_solution_bridge.py` et STEP8 `MediaSolution.jsx`).


* **Mitigation** : Ne **jamais** remplacer le formateur de timecode CSV/JSON existant de `run_transnet.py` / `run_transnet_cv5.py` (`utils/transnetv2_library.py`) par `frame_to_smpte_25fps` du rapport. Conserver strictement les fonctions d'écriture CSV et de conversion `predictions_to_scenes` existantes du dépôt afin de garantir 0 régression sur les étapes 5 à 8.




3. **Compatibilité Logicielles (`onnxruntime-gpu`, CUDA, cuDNN) dans `transnet_cv5_env**` :
* **Alerte cuDNN 9.14–9.20** : Le rapport signale un bug critique documenté sous CUDA 12.9/13.1 et ONNX Runtime 1.22+ où `cudnn_conv_algo_search='EXHAUSTIVE'` provoque un blocage infini (*hang*) lors du benchmarking des convolutions 3D avec cuDNN 9.14 à 9.20. Il faut vérifier la version de `nvidia-cudnn` dans `transnet_cv5_env` (exiger cuDNN $\ge 9.21$ ou cuDNN 8.9.x selon la branche CUDA installée) et prévoir une variable d'environnement de secours `STEP2_CUDNN_ALGO_SEARCH=HEURISTIC` si le matériel ou la version cuDNN locale présente une instabilité au warm-up.


* **Injection dynamique de `LD_LIBRARY_PATH**` : Conformément à `.agents/skills/opencv5-dnn-engine-expert/SKILL.md` et `codingstandards.md`, l'isolation de `transnet_cv5_env` masque parfois les bibliothèques CUDA/cuDNN système ou celles des roues pip `nvidia-*`. Le helper d'injection dynamique de `LD_LIBRARY_PATH` déjà présent dans `run_transnet_cv5.py` doit impérativement être exécuté **avant** l'import et l'initialisation de `ort.InferenceSession`.





---

## 4. Plan d'Action et Feuille de Route d'Implémentation (Roadmap)

### Découpage en Sous-Tâches Incrémentales et Isolées

1. **Tâche 1 — Sanitization ONNX & Alignement de Configuration (`export_transnet_onnx.py`, `config/step2_transnet.json`)** :
* Ajouter `sanitize_transnetv2_for_opencv5()` dans `workflow_scripts/step2/export_transnet_onnx.py` pour corriger les nœuds `Flatten` 5D et promouvoir les scalaires 0D `Mul`/`Div` en 1D.


* Mettre à jour `config/step2_transnet.json` pour exposer `"ffmpeg_threads": 0`, `"onnx_batch_size": 25`, `"windows_per_chunk": 50` et `"use_tf32": false`.




2. **Tâche 2 — Moteur d'Ingestion Asynchrone Zéro-Copie & Strides Tricks (`utils/transnetv2_library.py` ou module partagé STEP2)** :
* Implémenter le producteur-consommateur double tampon Ping-Pong (`2600` trames de capacité physique par buffer pour couvrir le cas limite $N \in [2501, 2524]$ sans débordement, lecture nominale de `2525` puis `2500` trames via `proc.stdout.readinto(mv)`).


* Remplacer `build_window()` et `np.stack()` par `sliding_window_view(buf[:required_buf_len], window_shape=100, axis=0)[::50].transpose(0, 4, 1, 2, 3)` et le padding vectorisé in-place.


* Intégrer l'émission périodique des logs `INTERNAL_PROGRESS` à chaque bloc traité pour maintenir la synchronisation avec `WorkflowState` et l'UI Flask.




3. **Tâche 3 — Moteur GPU ONNX Runtime avec `IOBinding` & Tuning Deterministe (`workflow_scripts/step2/run_transnet_cv5.py`)** :
* Implémenter `TransNetV2GpuEngine` avec `SessionOptions` (`ORT_ENABLE_ALL`, `ORT_SEQUENTIAL`, `enable_mem_pattern=True`) et `CUDAExecutionProvider` (`arena_extend_strategy='kSameAsRequested'`, `cudnn_conv_algo_search='EXHAUSTIVE'`, `cudnn_conv_use_max_workspace='1'`, `do_copy_in_default_stream='1'`, `use_tf32=0`).


* Pré-allouer `host_staging_buffer` ($[25, 100, 27, 48, 3]$ en `uint8`), lier `input_ortvalue` et `output_ortvalues` en VRAM via `io_binding`, exécuter la passe `_warmup()` à lot fixe $B=25$, et implémenter `infer_windows()` avec `update_inplace()`, zero-padding du dernier lot incomplet ($b < 25$), et sigmoïde C/SIMD in-place sur la tranche centrale `[:, 25:75]`.


* Conserver le fallback vers OpenCV 5.0 DNN (`ENGINE_NEW`, `DNN_TARGET_CPU` avec `cv2.setNumThreads(1)` ou séquentiel conformément à `codingstandards.md`) uniquement lorsque `CUDAExecutionProvider` est indisponible ou explicitement désactivé.




4. **Tâche 4 — Rétro-portage de l'Ingestion sur `run_transnet.py` & Suite de Tests Unitaires/Intégration (`tests/unit/test_step2_transnet.py`, `tests/integration/test_step2_cv5_integration.py`)** :
* Connecter le générateur de vues 5D zéro-copie à `run_transnet.py` pour éliminer le goulot d'étranglement `queue.Queue` / `np.stack` sur le chemin PyTorch legacy.


* Exécuter la suite de tests de non-régression et le benchmark comparatif.





---

### Protocole de Test de Non-Régression (Conformément à `test-strategy.md`)

#### Table des Perspectives de Test (Partition d'Équivalence & Valeurs Limites)

| Case ID | Input / Precondition | Perspective (Equivalence / Boundary) | Expected Result | Notes |
| --- | --- | --- | --- | --- |
| **TC-N-01** | Vidéo standard normalisée $25\text{ fps}$ de $3\,200\text{ trames}$ ($\sim 2\text{ min }08\text{ s}$, $> 1\text{ bloc}$ de $2\,500$).

 | Equivalence – normal | $\max \vert{}\Delta P\vert{} < 10^{-5}$ sur les $3\,200$ trames par rapport à la baseline ; liste de plans `(start_frame, end_frame)` et timecodes `HH:MM:SS.mmm` 100 % identiques ; F1-score invariant.

 | Valide la continuité de l'overlap de 50 trames inter-blocs (`carry_50_frames`).

 |
| **TC-B-01** | Vidéo très courte de $N = 1\text{ trame}$ et $N = 49\text{ trames}$ ($< \text{stride } 50$ et $< \text{window } 100$).

 | Boundary – minimum / $< 100$ trames | Exactement $1\text{ fenêtre}$ générée ($[1, 100, 27, 48, 3]$) avec padding gauche (25) et droit (45 ou 26), lot complété par zéros jusqu'à $B=25$, sortie tronquée à `[:N]` sans IndexError.

 | Vérifie le cas limite $N \ll 100$ et le zero-padding du batch IOBinding.

 |
| **TC-B-02** | Vidéo de longueur frontière $N = 2\,500$, $N = 2\,524$, $N = 2\,525$ et $N = 2\,526\text{ trames}$ (autour de la capacité d'ingestion du 1er bloc).

 | Boundary – $\pm 1$ autour de la frontière de bloc | Sortie de longueur exacte $N$, parité bit-à-bit des tenseurs d'entrée $[100, 27, 48, 3]$ avec un `np.pad(..., mode='edge')` global en mémoire.

 | Prévient la régression de dépassement de capacité (`required_buf_len = 2600`) pour $N \in [2501, 2524]$.

 |
| **TC-B-03** | Flux vidéo vide ($0\text{ trame}$ décodée par FFmpeg) ou fichier inexistant.

 | Boundary – 0 / empty / NULL | Lève `FileNotFoundError` (si fichier absent) ou `RuntimeError("Le flux vidéo décodé ne contient aucune trame.")` (si 0 octet lu), sans deadlock du thread producteur.

 | Vérifie le déblocage de `cond.wait()` via la sentinelle `None` dans `ready_chunks`.

 |
| **TC-E-01** | Flux FFmpeg interrompu produisant une trame tronquée (`bytes_read % 3888 != 0`).

 | Error – external dependency failure | Le thread producteur capture l'exception `RuntimeError`, pousse `None` dans `ready_chunks`, réveille le consommateur et tue proprement le sous-processus FFmpeg dans le bloc `finally`.

 | Garantit l'absence de processus zombie FFmpeg et de blocage infini.

 |
| **TC-E-02** | Échec forcé de `CUDAExecutionProvider` (ex: GPU masqué ou OOM simulé par mock) dans `run_transnet_cv5.py`.

 | Error – fallback path | Repli propre vers le moteur CPU (OpenCV 5.0 `ENGINE_NEW` avec graphe sanitizé ou `CPUExecutionProvider`), journalisation explicite et respect du contrat `INTERNAL_PROGRESS`.

 | Conforme à `opencv5-dnn-engine-expert`.

 |

#### Spécification des Tests Automatisés (Format Given / When / Then)

```python
# Fichier cible : tests/unit/test_step2_transnet.py

def test_chunked_sliding_window_bit_exact_parity_with_global_pad():
    # Given: Une séquence synthétique déterministe de N=2524 trames (cas limite frontière de bloc)
    #        et la fonction de référence historique utilisant np.pad(frames, ((25, 75), ...), mode='edge')
    rng = np.random.default_rng(42)
    raw_frames = rng.integers(0, 256, size=(2524, 27, 48, 3), dtype=np.uint8)

    # When:  On extrait les fenêtres 5D via le pipeline en double tampon par blocs (sliding_window_view)
    #        et via l'approche globale historique np.stack / np.pad
    ref_windows = build_reference_windows_global_pad(raw_frames)
    opt_windows = extract_windows_chunked_zero_copy(raw_frames, windows_per_chunk=50)

    # Then:  Les formes (51, 100, 27, 48, 3) et le contenu mémoire sont strictement identiques bit-à-bit
    assert opt_windows.shape == ref_windows.shape == (51, 100, 27, 48, 3)
    np.testing.assert_array_equal(opt_windows, ref_windows)


def test_iobinding_fp32_numerical_invariance_and_scene_parity(transnet_onnx_path, sample_video_25fps):
    # Given: Le modèle transnetv2.onnx exécuté d'une part avec l'implémentation actuelle (session.run)
    #        et d'autre part avec TransNetV2GpuEngine (IOBinding, use_tf32=0, batch_size=25)
    legacy_probs, legacy_scenes = run_legacy_onnx_pipeline(transnet_onnx_path, sample_video_25fps)
    engine = TransNetV2GpuEngine(onnx_path=transnet_onnx_path, batch_size=25, device_id=0)
    pipeline = ZeroCopyTransNetPipeline(engine=engine, windows_per_chunk=50)

    # When:  On exécute le pipeline zéro-copie sur la même vidéo normalisée à 25.0 fps
    opt_probs, opt_scenes = pipeline.process_video(sample_video_25fps, threshold=0.5)

    # Then:  L'écart maximal de probabilité est < 1e-5 et les timecodes de scènes sont identiques à 100 %
    assert len(opt_probs) == len(legacy_probs)
    assert np.max(np.abs(opt_probs - legacy_probs)) < 1e-5
    assert opt_scenes == legacy_scenes

```

#### Commandes d'Exécution et Validation de Couverture

* **Tests unitaires et d'intégration STEP2** :
```bash
bash scripts/run_step2_tests.sh
transnet_cv5_env/bin/pytest tests/unit/test_step2_transnet.py tests/integration/test_step2_cv5_integration.py --cov=workflow_scripts/step2 --cov-branch

```


*(Conformément aux règles de `tests-suite-guardian` et `test-strategy.md`)*.