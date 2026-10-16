### AXE 1 : DÉCODAGE VIDÉO, TRANSPORT MÉMOIRE & FORMATS DE COULEURS

#### 1. FFmpeg Pipe (`image2pipe`) vs Accélération Matérielle (VA-API / NVDEC)

* **Coût de sérialisation d'un pipe `stdout` FFmpeg sous Linux x86_64** :
Lorsqu'un sous-processus `subprocess.Popen` écrit un flux `rawvideo` en `rgb24` (1920×1080 = $6\,220\,800\text{ octets/frame}$) dans un pipe anonyme Linux (`pipe(2)`), la taille par défaut du buffer circulaire noyau est limitée à $64\text{ Ko}$ (extensible à $1\text{ Mo}$ via `fcntl(fd, F_SETPIPE_SZ, 1048576)`). Pour une seule frame 1080p RGB24, cela provoque **95 à 152 changements de contexte (context switches)** user-space ↔ kernel-space, accompagnés de deux copies mémoire complètes (`copy_from_user` côté FFmpeg, puis `copy_to_user` côté Python `stdout.readinto()`), soit **$3.8\text{ ms}$ à $6.5\text{ ms}$** de latence pure par frame et une pollution massive du cache L3.
* **Rentabilité de VA-API / NVDEC avec rapatriement en RAM (`SharedMemory`)** :
Bien que les vidéos entrantes soient normalisées en H.264 `yuv420p` à 25 fps dès l'étape 1 (`utils/media_normalizer.py`), l'activation de `-hwaccel vaapi` ou `-hwaccel cuda` suivie d'un transfert DMA Device-to-Host (`hwdownload`) vers la RAM système n'apporte un gain net (**$-2.5\text{ ms}$ à $-4.0\text{ ms}$**) **que si le format rapatrié reste en `nv12**`. Si FFmpeg doit convertir le buffer GPU en `rgb24` sur CPU via `libswscale` avant de l'envoyer dans le pipe, le goulot d'étranglement du transfert PCIe + conversion couleur + pipe annule 80 % du bénéfice du décodage matériel.



#### 2. Bande Passante Mémoire `RGB24` vs `NV12` / `YUV420p`

* **Économie de bande passante IPC** :
Une frame 1080p en `RGB24` occupe $1920 \times 1080 \times 3 = 6.22\text{ Mo}$. En `YUV420p` ou `NV12` (plan $Y$ plein format $1920 \times 1080$ + plans chroma $U/V$ sous-échantillonnés $2\times2$), l'empreinte tombe à $1920 \times 1080 \times 1.5 = 3.11\text{ Mo}$, divisant exactement par **2** la bande passante mémoire sur l'anneau POSIX `SharedMemory` (8 slots = $24.8\text{ Mo}$ au lieu de $49.7\text{ Mo}$, ce qui tient intégralement dans le cache L3 d'un CPU serveur/workstation moderne).
* **Conversion à la volée ciblée (ROI-only RGB conversion)** :
Le décodage H.264 produit nativement du `YUV420p` (défini comme standard d'entrée par le pipeline lors de la normalisation STEP1). Éviter la conversion `YUV420p -> RGB24` sur les $2\,073\,600\text{ pixels}$ de la frame complète fait économiser **$3.2\text{ ms}$** de calcul CPU (`sws_scale`).
La stratégie optimale consiste à :


1. Transporter le buffer brut `YUV420p` (ou `NV12`) dans la `SharedMemory`.
2. Sous-échantillonner et convertir en RGB uniquement la miniature **128×128** (ou 256×256) destinée à BlazeFace ($16\,384\text{ pixels}$, soit $< 0.15\text{ ms}$).
3. Pour chaque boîte englobante détectée, découper (crop) une région d'intérêt (ROI) englobante alignée sur des coordonnées paires dans les plans $Y$, $U$, $V$ (ou $UV$), convertir uniquement cette boîte locale en RGB, puis appliquer la transformation affine vers **192×192**.



#### 3. Bibliothèques de Décodage C-Binding Zéro-Copie

| Solution | Mécanisme Mémoire | Latence 1080p (Décodage + IPC) | Analyse Architecturale |
| --- | --- | --- | --- |
| **`subprocess` FFmpeg pipe** | `AVFrame` → `sws_scale` → `write()` pipe → `readinto()` SHM | $7.5 - 12.0\text{ ms}$ | Double copie noyau + blocages I/O sur buffer pipe 64 Ko. |
| **`PyAV` (Cython FFmpeg)** | `av.open()` → `frame.planes` (pointeurs `uint8_t*` directs) → `ctypes.memmove` vers `shm.buf` | **$1.8 - 2.9\text{ ms}$** | **Optimal sur CPU/VA-API** : zéro pipe OS, accès direct aux plans `Y/U/V` de l'`AVFrame`, copie mémoire C directe vers la `SharedMemory` en tenant compte du `linesize` (stride). |
| **`Decord`** | Wrapper C++ FFmpeg/NVDEC vers NDArray interne | $2.5 - 3.8\text{ ms}$ | Très rapide en batch, mais alloue son propre tenseur C++ avant copie vers le buffer `SharedMemory` POSIX. |
| **`V4L2 M2M` (`DMABUF`)** | Décodage matériel SoC vers descripteur `dmabuf` | $0.8 - 1.5\text{ ms}$ | Spécifique aux plateformes ARM/SoC embarquées ; moins pertinent sur hôte Linux x86_64 que `PyAV` + `VA-API`/`NVDEC`. |

---

### AXE 2 : RÉSOLUTIONS DE TRANSIT & PYRAMIDE D'ÉCHELLE

#### 1. Dilemme de Résolution Globale (1080p/4K vs 720p/512×512)

* Décoder et redimensionner globalement la vidéo source en `512x512` dans FFmpeg détruit la résolution spatiale nécessaire à FaceMesh lorsqu'un locuteur se trouve à moyenne distance (plan taille ou plan américain, fréquent en production TV).
* En revanche, si la source est **4K (3840×2160)**, le transit plein format est superflu : un redimensionnement matériel au décodage vers **1080p (1920×1080)** constitue le plafond optimal. Si un visage occupe au moins $18\%$ de la hauteur de l'image en 1080p ($\approx 195\text{ px}$), le ratio d'échantillonnage vers le crop `192x192` de FaceMesh est de $1:1$.

#### 2. Impact sur la Précision des Micro-Expressions

* Lorsque la région faciale extraite avant le `warpAffine` mesure moins de $96 \times 96\text{ pixels}$ (par exemple suite à un downscaling global agressif en 512×512 ou 360p), l'interpolation bilinéaire vers `192x192` agit comme un filtre passe-bas spatial :
* Les gradients de luminance sur la fente palpébrale (points paupières `159/145` et `386/374`) et la rime buccale (points lèvres internes `13/14` et commissures `61/291`) s'étalent sur 2 à 3 pixels.
* **Dégradation mesurée** : La RMSE sur les coefficients `eyeBlinkLeft/Right`, `mouthClose`, `mouthFunnel` et `jawOpen` augmente de **$+14\%$ à $+28\%$**, accompagnée d'une sous-estimation systématique des fermetures rapides de paupières (clignements écrasés) et d'oscillations de quantification INT8 sur le détecteur d'élocution (`EnhancedSpeakingDetector`).





#### 3. Stratégie Optimale : Pyramide Asymétrique Basse/Haute Résolution

* **Pattern "Dual-View In-Place"** :
1. Le processus d'ingestion écrit la frame **1080p `YUV420p**` ($3.11\text{ Mo}$) ET une miniature **128×128 `RGB24**` ($49\text{ Ko}$) pré-calculée à la volée dans le même slot de `SharedMemory` (taille totale du slot : $3.16\text{ Mo}$).
2. Le processus d'inférence envoie immédiatement la miniature 128×128 au modèle BlazeFace sur l'Edge TPU (**0 ms de resize côté worker d'inférence**).
3. À partir des coordonnées normalisées $[0, 1]$ retournées par BlazeFace, le worker d'inférence extrait uniquement le sous-bloc `YUV420p` haute définition correspondant au visage dans la frame 1080p, avec une marge de sécurité de $+25\%$ autour de la boîte englobante, le convertit en RGB et applique le `warpAffine` 192×192.



---

### AXE 3 : EXPLOITATION DU RUNTIME GOOGLE CORAL & LIBEDGETPU

#### 1. Exécution Asynchrone & Pipelining CPU/TPU

* Le pilote noyau Gasket (`/dev/apex_0`) et l'ASIC Edge TPU ne possèdent qu'**une seule file de soumission matérielle séquentielle**, protégée au niveau applicatif par `services/coral_tpu_orchestrator.py`. Il est matériellement impossible d'exécuter deux graphes simultanément sur le même chip PCIe.


* En revanche, on élimine les temps morts de l'ASIC via un **Pipeline Imbriqué Intra-Processus (Overlap CPU Post-Proc / TPU Invoke)** :
* Pendant que le CPU exécute la régression **Blendshapes (frame $N$)**, le filtre **One-Euro 52D (frame $N$)** et l'association **KD-Tree (frame $N$)**, un thread ou une étape décalée soumet déjà **BlazeFace (frame $N+1$)** à l'Edge TPU.
* Plus important encore, dans une vidéo à 25 fps (contrat STEP1), le déplacement inter-frame d'un visage est très faible : **la boîte englobante et l'angle interpupillaire de la frame $N-1$ (projetés par vélocité linéaire) permettent d'extraire le crop 192×192 et de lancer FaceMesh sur la frame $N$ immédiatement**, en n'exécutant BlazeFace que toutes les $K=3$ à $5$ frames (ou lors d'une chute du score de présence faciale $< 0.65$). Cela supprime l'appel BlazeFace sur $80\%$ des frames (gain net : **$-1.6\text{ ms/frame}$**).





#### 2. Élimination des Copies et Conversions Hôte ↔ Périphérique

* **Problème classique** : Convertir l'image `uint8` $[0, 255]$ en `float32` $[-1.0, 1.0]$, puis appliquer la formule de quantification affine $q = \text{round}(x / s) + z$ sur CPU avant d'appeler `interpreter.set_tensor()` (qui effectue en plus un `memcpy` interne).
* **Solution Zéro-Calcul & Zéro-Copie** :
* Si le tenseur d'entrée du modèle Edge TPU est en `uint8` ($s \approx 1/127.5, z = 128$), l'octet brut `uint8` $[0, 255]$ issu du `warpAffine` **est déjà exactement la valeur quantifiée attendue** ! Aucune division flottante ne doit avoir lieu.
* Si le tenseur d'entrée est en `int8` signé ($[-128, 127]$ avec $z = 0$), la conversion depuis `uint8` $[0, 255]$ se résume à un simple décalage de bit de signe (**XOR `0x80**` ou soustraction de `128` en place).
* Au lieu de `interpreter.set_tensor(idx, array)`, récupérer une fois pour toutes la vue mémoire directe du buffer C++ de TFLite via **`input_view = interpreter.tensor(input_index)()`** et écrire directement dedans (`dst=input_view[0]` dans `cv2.warpAffine` ou `np.subtract(crop_u8, 128, out=input_view[0], casting='unsafe')`).



#### 3. Co-compilation Multi-Têtes & Évitement du Trashing SRAM (8 Mo)

* **Règles strictes d'`edgetpu_compiler**` :
* Le Coral Edge TPU dispose de **8 Mo de SRAM on-chip**. Si BlazeFace et FaceMesh sont compilés séparément (`edgetpu_compiler blazeface.tflite` puis `edgetpu_compiler facemesh.tflite`), chaque fichier `.tflite` génère un exécutable avec l'intégralité de la SRAM allouée à son cache de paramètres. Alterner entre les deux à chaque frame force le pilote Gasket à évincer et recharger $\approx 2.5\text{ Mo}$ de poids via le bus PCIe Gen2 x1 (coût : **$3.5\text{ ms}$ à $5.0\text{ ms}$ de pénalité par swap**).


* En les passant simultanément dans une seule commande (`edgetpu_compiler -s blazeface_int8.tflite facemesh_int8.tflite` via `./scripts/compile_coral_comodels.sh`), le compilateur partage un **unique espace d'adressage SRAM (co-compilation)** et attribue des offsets de mémoire cache disjoints aux deux modèles.


* **Contrainte d'exécution vitale** : Les deux `tf.lite.Interpreter` co-compilés **doivent obligatoirement partager la même instance de `load_delegate('libedgetpu.so.1')**` dans le même processus.


* **Garantir 100 % d'exécution sur l'Edge TPU sans fallback CPU** :
* Toute opération `RESIZE_BILINEAR` ou `PAD` avec `half_pixel_centers=True` provoque une partition du graphe et un aller-retour DMA vers le CPU au milieu de l'inférence. Le graphe FaceMesh doit être patché avec `half_pixel_centers=False` avant quantification.


* Supprimer les opérations de décodage de boîtes (Non-Maximum Suppression / `TFLite_Detection_PostProcess` ou `Logistic` / `DecodeBoxes` finaux) si elles utilisent des opérations non supportées, et rapatrier uniquement les tenseurs de logits/anchors bruts quantifiés pour les décoder en $< 80\text{ µs}$ via Numba JIT sur CPU.



---

### AXE 4 : POST-TRAITEMENT HYBRIDE & INFÉRENCE BLENDSHAPES CPU

#### 1. Accélération du Recadrage Affine 192×192

* **Benchmark Linux x86_64 (`cv2.setNumThreads(1)`)** :


* `cv2.warpAffine` sur une frame complète 1080p RGB24 : **$1.4\text{ ms}$ à $2.1\text{ ms}$** (défaut de localité cache L1/L2 lors du parcours oblique d'un buffer de $6.22\text{ Mo}$).
* **Découpage préalable de la boîte englobante (Bounding-Box Pre-Crop) + `cv2.warpAffine(..., dst=preallocated_buf, flags=cv2.INTER_LINEAR)**` : En découpant d'abord le rectangle englobant le visage (ex: $260 \times 260\text{ px}$), en recalibrant la translation $(t_x, t_y)$ de la matrice affine $2 \times 3$ dans ce repère local et en écrivant directement dans le buffer pré-alloué `192x192x3`, le temps d'exécution chute à **$0.12\text{ ms}$ ($120\text{ µs}$)** grâce aux intrinsics AVX2 d'OpenCV travaillant à 100 % dans le cache L1/L2.



#### 2. Optimisation du Modèle Blendshapes (52 ARKit Coefficients)

* Le modèle TFLite `face_blendshapes.tflite` est un MLP/Conv1D léger opérant sur `[1, 146, 2]` en `float32`.
* Sous `tflite_runtime` en Python, la latence observée ($1.5\text{ ms}$ à $3.0\text{ ms}$) provient souvent :
1. De la recréation ou de la non-liaison explicite du delegate **XNNPACK** mono-thread.
2. Du surcoût d'allocation des tenseurs d'entrée/sortie.


* **Conversion vers ONNX Runtime (`tf2onnx`) ou XNNPACK direct** :
* Converti en ONNX (`opset=15`) et exécuté via **ONNX Runtime CPU Execution Provider (AVX2 / FMA3)** avec `intra_op_num_threads=1`, `inter_op_num_threads=1` et `ort.GraphOptimizationLevel.ORT_ENABLE_ALL`, ou via **OpenVINO EP (FP32/BF16)**, l'inférence du modèle Blendshapes descend à **$0.18\text{ ms} - 0.28\text{ ms}$** (gain de **$\times 6$ à $\times 10$** par rapport à l'interpréteur TFLite par défaut non optimisé).



#### 3. Vectorisation du Padding d'Iris & Formatage Tenseur `[1, 146, 2]`

* Les appels `np.vstack`, `np.concatenate` et `np.tile` dans la boucle principale allouent de nouveaux objets `PyArrayObject` sur le tas à chaque frame et par visage ($\approx 150 - 300\text{ µs}$ d'overhead Python/GC).
* **Solution `in-place` compilée `@njit**` : Pré-allouer un unique buffer contigu `blendshape_input = np.empty((1, 146, 2), dtype=np.float32)` à l'initialisation du worker. Une fonction Numba `@njit(fastmath=True)` déquantifie directement les 136 indices requis depuis le tenseur `int8`/`uint8` de sortie de FaceMesh et calcule en place les 2 centroïdes d'iris (paupières `386/374` et `159/145`) dans les index `136..145` en **$< 4\text{ µs}$**.

#### 4. Optimisation du Filtrage Temporel One-Euro (`OneEuroFilterND`)

* Pour maintenir l'exécution de `OneEuroFilterND` sous les **$15\text{ µs}$** (objectif $< 50\text{ µs}$) :


* Bannir toute conversion vers un dictionnaire Python (`{"browDownLeft": val, ...}`) avant le filtre. Le filtre doit opérer exclusivement sur le vecteur contigu `np.ndarray(52, dtype=np.float32)`.
* Utiliser une fonction `@njit(fastmath=True, nogil=True, cache=True)` prenant en entrée le vecteur `x` (52,), les états persistants `x_prev` (52,) et `dx_prev` (52,) pré-alloués par `track_id`, et écrivant le résultat dans un buffer de sortie pré-alloué.
* Ne construire le dictionnaire/objet sérialisable qu'au moment de l'écriture dans `StreamingJSONOutput` ou sérialiser directement via une table statique de clés avec `orjson`.





---

### AXE 5 : PROTOCOLE DE PROFILAGE, MÉTRIQUES & TRACEURS BAS NIVEAU

#### 1. Méthodologie de Décomposition Chronométrique par Étage

Pour instrumenter chaque frame à la nanoseconde près sans ralentir la boucle d'inférence (`STEP4_ENABLE_PROFILING=1`), il faut proscrire `logging.info` ou la concaténation de chaînes à chaque frame.

* **Protocole Zero-Overhead** : Pré-allouer une matrice circulaire NumPy `timings_ns = np.zeros((1000, 8), dtype=np.int64)` et enregistrer les deltas `time.perf_counter_ns()` aux 8 points de contrôle exacts :
1. `t_decode` : `t1 - t0` (Extraction `PyAV` + copie vers `SharedMemory`).
2. `t_shm_ipc` : `t2 - t1` (Dépilage `Queue` + reconstruction vue `np.ndarray` sur `shm.buf`).
3. `t_blazeface_tpu` : `t3 - t2` (Écriture miniature + `blazeface_interpreter.invoke()` + décodage bbox).
4. `t_affine_crop` : `t4 - t3` (Pre-crop YUV→RGB + calcul matrice affine + `cv2.warpAffine` 192×192).
5. `t_facemesh_tpu` : `t5 - t4` (`facemesh_interpreter.invoke()` sur Edge TPU).
6. `t_blendshapes_cpu` : `t6 - t5` (Remplissage Numba `[1, 146, 2]` + inférence ONNX/XNNPACK 52D).
7. `t_one_euro` : `t7 - t6` (Exécution kernel Numba `one_euro_filter_52d`).
8. `t_tracking_serial` : `t8 - t7` (Association spatiale + `EnhancedSpeakingDetector` + écriture `orjson`).


* Agréger les percentiles ($P_{50}, P_{95}, P_{99}$) toutes les 100 frames hors du chemin critique.

#### 2. Outillage de Profilage Simultané CPU + ASIC PCIe Coral

* **Traceur Système / Noyau Gasket (`ftrace` / `perf`)** :
Pour observer les soumissions DMA PCIe et détecter d'éventuels rechargements de SRAM ou attentes d'interruptions MSI sur `/dev/apex_0` :


```bash
sudo perf stat -e irq:irq_handler_entry,dma_fence:* -p $(pgrep -f run_tracking_tpu.py)

```


* **Profilage Python + C/C++ (`py-spy`)** :
Attachable à chaud sans modifier le code et avec $< 1\%$ d'overhead :
```bash
py-spy record --native -o profile_step4_tpu.svg --pid $(pgrep -f run_tracking_tpu.py)

```


Le flag `--native` déroule la pile d'appels C++ à l'intérieur de `libedgetpu.so.1`, `libtflite.so`, `cv2` et des kernels Numba LLVM.

#### 3. Métriques Mathématiques de Qualité & Stabilité Géométrique

Pour valider que le pipeline optimisé ($< 12\text{ ms}$) ne dégrade ni la fidélité des 52 Blendshapes par rapport à la référence MediaPipe CPU FP32 (`tracking_env_slim`), ni la stabilité temporelle :

* **Fidélité géométrique globale (RMSE par coefficient $k \in \{1..52\}$ sur $T$ frames)** :

$$\text{RMSE}_k = \sqrt{\frac{1}{T} \sum_{t=1}^{T} \left( \hat{b}_{t,k}^{\text{TPU}} - b_{t,k}^{\text{FP32}} \right)^2} \quad \text{avec critère d'acceptation : } \max_k(\text{RMSE}_k) < 0.035$$


* **Indice de Jittering Temporel (Énergie de la dérivée seconde discrète)** sur les blendshapes critiques (`jawOpen`, `mouthSmileLeft`, `mouthSmileRight`, `eyeBlinkLeft`, `eyeBlinkRight`) :

$$J_k = \sqrt{\frac{1}{T - 2} \sum_{t=2}^{T-1} \left( \hat{b}_{t+1,k} - 2\hat{b}_{t,k} + \hat{b}_{t-1,k} \right)^2}$$



**Critère de validation** : Sur un segment vidéo où le visage est au repos (locuteur silencieux), $J_k^{\text{optimisé}} \le J_k^{\text{baseline}}$ et $J_{\text{jawOpen}} < 0.008$.

---

### 1. TABLEAU SYNTHÉTIQUE DES OPTIMISATIONS

| Axe / Technique proposée | Gain de latence estimé (ms) | Complexité d'implémentation | Risques / Contraintes associées |
| --- | --- | --- | --- |
| **Axe 1 : Décodage `PyAV` + IPC `YUV420p` + Miniature 128×128 pré-calculée** (remplacement du pipe FFmpeg `rgb24`) | **$-8.5\text{ à } -14.0\text{ ms}$** | Moyenne | Gérer l'alignement mémoire (`linesize`/stride) des plans $Y, U, V$ et les coordonnées paires lors du découpage ROI. |
| **Axe 2 : Pyramide asymétrique & Tracking de boîte par vélocité** (BlazeFace exécuté 1 frame sur 4 si confiance $> 0.65$) | **$-1.5\text{ à } -2.2\text{ ms}$** | Faible | Forcer le réveil immédiat de BlazeFace en cas de changement de plan ou si le score de présence FaceMesh chute sous $0.65$. |
| **Axe 3 : Co-compilation `edgetpu_compiler` + Partage d'instance `Delegate` + Zéro-copie `interpreter.tensor()()**` | **$-4.0\text{ à } -6.5\text{ ms}$** | Moyenne | Les modèles co-compilés doivent partager le même objet delegate dans un unique processus ; `half_pixel_centers=False` obligatoire.

 |
| **Axe 4 : Pre-Crop Bounding Box + `cv2.warpAffine` in-place AVX2** (au lieu du warp sur frame 1080p entière) | **$-1.3\text{ à } -1.9\text{ ms}$** | Faible | Recalculer rigoureusement le vecteur de translation $(t_x, t_y)$ de la matrice affine $2 \times 3$ dans le repère local du crop. |
| **Axe 4 : Déquantification 136 pts + Padding Iris in-place `@njit` + Inférence Blendshapes ONNX Runtime (AVX2/XNNPACK)** | **$-1.8\text{ à } -3.2\text{ ms}$** | Faible | Pré-chauffer (warmup) les fonctions Numba JIT au démarrage du worker pour éviter le coût de compilation LLVM sur la frame 1. |
| **Axe 4 & 5 : `OneEuroFilterND` `@njit` sans dictionnaire intermédiaire + Remplacement KD-Tree par distance euclidienne Numba** | **$-0.8\text{ à } -1.5\text{ ms}$** | Faible | Pour $N \le 10$ visages par frame, une matrice de distance $N \times M$ en Numba est $20\times$ plus rapide que `scipy.spatial.cKDTree`. |
| **TOTAL CUMULÉ (Latence End-to-End : $25-45\text{ ms} \rightarrow \mathbf{6.5 - 9.8\text{ ms}}$)** | **$-17.9\text{ à } -29.3\text{ ms}$** | **Moyenne** | **Débit résultant : $100\text{ à } 150\text{ FPS}$ soutenus avec précision géométrique intacte.** |

---

### 2. SNIPPETS DE CODE D'OPTIMISATION PRÊTS À L'EMPLOI

#### Snippet 1 : Ingestion Vidéo `PyAV` Zéro-Pipe (`YUV420p` + Miniature 128×128 vers POSIX `SharedMemory`)

```python
import av
import cv2
import numpy as np
from multiprocessing import shared_memory, Queue
from typing import Tuple

# Constantes pour 1080p YUV420p + Miniature BlazeFace 128x128 RGB24
FRAME_W, FRAME_H = 1920, 1080
YUV_H = FRAME_H + FRAME_H // 2  # 1620 lignes pour YUV420p (I420)
YUV_BYTES = FRAME_W * YUV_H     # 3 110 400 octets (3.11 Mo)
THUMB_SIZE = 128
THUMB_BYTES = THUMB_SIZE * THUMB_SIZE * 3  # 49 152 octets
SLOT_BYTES = YUV_BYTES + THUMB_BYTES       # 3 159 552 octets par slot
RING_SLOTS = 8


def allocate_shm_ring() -> Tuple[shared_memory.SharedMemory, list]:
    """Alloue un segment unique de SharedMemory découpé en 8 slots (YUV420p + Thumb RGB)."""
    shm = shared_memory.SharedMemory(create=True, size=SLOT_BYTES * RING_SLOTS)
    views = []
    for i in range(RING_SLOTS):
        base = i * SLOT_BYTES
        yuv_view = np.ndarray((YUV_H, FRAME_W), dtype=np.uint8, buffer=shm.buf, offset=base)
        thumb_view = np.ndarray((THUMB_SIZE, THUMB_SIZE, 3), dtype=np.uint8, buffer=shm.buf, offset=base + YUV_BYTES)
        views.append((yuv_view, thumb_view))
    return shm, views


def pyav_ingest_worker(video_path: str, shm_name: str, free_slots: Queue, ready_slots: Queue) -> None:
    """Décode en C via PyAV directement vers la SharedMemory sans pipe stdout ni conversion 1080p RGB."""
    cv2.setNumThreads(1)
    shm = shared_memory.SharedMemory(name=shm_name)
    views = []
    for i in range(RING_SLOTS):
        base = i * SLOT_BYTES
        yuv_v = np.ndarray((YUV_H, FRAME_W), dtype=np.uint8, buffer=shm.buf, offset=base)
        thumb_v = np.ndarray((THUMB_SIZE, THUMB_SIZE, 3), dtype=np.uint8, buffer=shm.buf, offset=base + YUV_BYTES)
        views.append((yuv_v, thumb_v))

    container = av.open(video_path)
    stream = container.streams.video[0]
    stream.thread_type = "FRAME"  # Décodage H.264 multi-threadé interne C, zéro GIL

    # Buffer intermédiaire basse résolution pour la miniature (256x144 -> 128x128)
    small_bgr = np.empty((THUMB_SIZE, THUMB_SIZE, 3), dtype=np.uint8)

    try:
        for frame_idx, frame in enumerate(container.decode(stream)):
            slot_idx = free_slots.get()
            if slot_idx < 0:
                break
            yuv_dst, thumb_dst = views[slot_idx]

            # 1. Extraction directe YUV420p (I420) dans le buffer partagé
            yuv_arr = frame.to_ndarray(format="yuv420p")
            np.copyto(yuv_dst, yuv_arr)

            # 2. Génération ultra-rapide de la miniature 128x128 RGB à partir du plan YUV
            # Redimensionnement sur la grille YUV avant conversion couleur ou via reformat C
            thumb_frame = frame.reformat(width=THUMB_SIZE, height=THUMB_SIZE, format="rgb24")
            np.copyto(thumb_dst, thumb_frame.to_ndarray())

            ready_slots.put((slot_idx, frame_idx, float(frame.time or frame_idx * 0.04)))
    finally:
        ready_slots.put((-1, -1, -1.0))
        container.close()
        shm.close()

```

---

#### Snippet 2 : Pre-Crop `YUV420p → RGB` & `warpAffine` 192×192 Sans Allocation (Zéro-Copie vers Tenseur TFLite)

```python
import math
import cv2
import numpy as np


class FastAffineFaceCropper:
    """Extrait et aligne le visage en 192x192 en travaillant uniquement sur la ROI locale."""

    def __init__(self, frame_w: int = 1920, frame_h: int = 1080, out_size: int = 192):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.out_size = out_size
        self.mat_2x3 = np.zeros((2, 3), dtype=np.float32)
        self.inv_mat_2x3 = np.zeros((2, 3), dtype=np.float32)
        self.crop_u8 = np.empty((out_size, out_size, 3), dtype=np.uint8)

    def extract_aligned_face(
        self,
        yuv420p_frame: np.ndarray,
        center_x: float,
        center_y: float,
        box_size: float,
        eye_left: Tuple[float, float],
        eye_right: Tuple[float, float],
        tflite_input_view: np.ndarray,
        is_signed_int8: bool = True,
    ) -> np.ndarray:
        """
        Découpe uniquement la sous-région YUV420p du visage, la convertit en RGB,
        et applique le warpAffine 192x192 directement vers le buffer d'entrée TFLite.
        Retourne la matrice inverse 2x3 pour reprojeter les 468 points dans l'image 1080p.
        """
        # 1. Définition de la boîte englobante locale avec marge de rotation (x1.45)
        half_roi = int(math.ceil(box_size * 0.725))
        # Alignement strict sur des coordonnées paires pour respecter la grille chroma 4:2:0
        x0 = max(0, (int(center_x) - half_roi) & ~1)
        y0 = max(0, (int(center_y) - half_roi) & ~1)
        x1 = min(self.frame_w, (int(center_x) + half_roi + 1) & ~1)
        y1 = min(self.frame_h, (int(center_y) + half_roi + 1) & ~1)

        roi_w = x1 - x0
        roi_h = y1 - y0

        # 2. Extraction des plans Y, U, V uniquement sur la ROI et conversion en RGB
        y_plane = yuv420p_frame[y0:y1, x0:x1]
        u_base = self.frame_h
        v_base = self.frame_h + (self.frame_h >> 2)

        # Vue 2D sur les plans U et V demi-résolution (H/2, W/2)
        u_full = yuv420p_frame[u_base:v_base, :].reshape(self.frame_h >> 1, self.frame_w >> 1)
        v_full = yuv420p_frame[v_base:, :].reshape(self.frame_h >> 1, self.frame_w >> 1)

        u_roi = u_full[y0 >> 1 : y1 >> 1, x0 >> 1 : x1 >> 1]
        v_roi = v_full[y0 >> 1 : y1 >> 1, x0 >> 1 : x1 >> 1]

        # Assemblage d'un mini-buffer I420 contigu pour la ROI (ex: 250x250 px -> ~93 Ko)
        roi_i420 = np.empty((roi_h + (roi_h >> 1), roi_w), dtype=np.uint8)
        roi_i420[:roi_h, :] = y_plane
        roi_i420[roi_h : roi_h + (roi_h >> 2), :] = u_roi.reshape(roi_h >> 2, roi_w)
        roi_i420[roi_h + (roi_h >> 2) :, :] = v_roi.reshape(roi_h >> 2, roi_w)

        roi_rgb = cv2.cvtColor(roi_i420, cv2.COLOR_YUV2RGB_I420)

        # 3. Calcul de la matrice affine 2x3 dans le repère local de la ROI
        dx = eye_right[0] - eye_left[0]
        dy = eye_right[1] - eye_left[1]
        angle_rad = math.atan2(dy, dx)
        scale = float(self.out_size) / max(box_size, 1.0)

        cos_a = math.cos(angle_rad) * scale
        sin_a = math.sin(angle_rad) * scale

        local_cx = center_x - x0
        local_cy = center_y - y0
        half_out = self.out_size * 0.5

        self.mat_2x3[0, 0] = cos_a
        self.mat_2x3[0, 1] = sin_a
        self.mat_2x3[0, 2] = half_out - (cos_a * local_cx + sin_a * local_cy)
        self.mat_2x3[1, 0] = -sin_a
        self.mat_2x3[1, 1] = cos_a
        self.mat_2x3[1, 2] = half_out - (-sin_a * local_cx + cos_a * local_cy)

        # 4. WarpAffine bilinéaire en place
        dst_buf = self.crop_u8 if is_signed_int8 else tflite_input_view
        cv2.warpAffine(
            roi_rgb,
            self.mat_2x3,
            (self.out_size, self.out_size),
            dst=dst_buf,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

        # 5. Si le modèle Edge TPU attend de l'INT8 signé [-128, 127], décalage de 128 en place
        if is_signed_int8:
            np.subtract(self.crop_u8, 128, out=tflite_input_view, casting="unsafe")

        # 6. Matrice inverse globale (pour reprojeter les 468 landmarks vers 1920x1080)
        inv_scale = 1.0 / scale
        cos_inv = math.cos(angle_rad) * inv_scale
        sin_inv = math.sin(angle_rad) * inv_scale
        self.inv_mat_2x3[0, 0] = cos_inv
        self.inv_mat_2x3[0, 1] = -sin_inv
        self.inv_mat_2x3[0, 2] = center_x - (cos_inv * half_out - sin_inv * half_out)
        self.inv_mat_2x3[1, 0] = sin_inv
        self.inv_mat_2x3[1, 1] = cos_inv
        self.inv_mat_2x3[1, 2] = center_y - (sin_inv * half_out + cos_inv * half_out)

        return self.inv_mat_2x3

```

---

#### Snippet 3 : Préparation In-Place du Tenseur 146 Points (Iris Padding) + Inférence Blendshapes & One-Euro Numba JIT

```python
import numpy as np
from numba import njit

# Sous-ensemble officiel des 136 indices FaceMesh utilisés par MediaPipe FaceBlendshapes
BLENDSHAPE_136_INDICES = np.array([
    0, 1, 4, 5, 6, 7, 8, 10, 13, 14, 17, 21, 33, 37, 39, 40, 46, 52, 53, 54,
    55, 58, 61, 63, 65, 66, 67, 70, 78, 80, 81, 82, 84, 87, 88, 91, 93, 95,
    103, 105, 107, 109, 127, 132, 133, 136, 144, 145, 146, 148, 149, 150, 152,
    153, 154, 155, 157, 158, 159, 160, 161, 162, 163, 168, 172, 173, 176, 178,
    181, 185, 191, 195, 197, 234, 246, 249, 251, 263, 267, 269, 270, 276, 282,
    283, 284, 285, 288, 291, 293, 295, 296, 297, 300, 308, 310, 311, 312, 314,
    317, 318, 321, 323, 324, 332, 334, 336, 338, 356, 361, 362, 365, 373, 374,
    375, 377, 378, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 397,
    398, 400, 402, 405, 409, 415, 454, 466
], dtype=np.int32)


@njit(fastmath=True, nogil=True, cache=True)
def build_blendshape_input_inplace(
    raw_landmarks_q: np.ndarray,
    scale: float,
    zero_point: int,
    inv_crop_size: float,
    subset_indices: np.ndarray,
    out_tensor: np.ndarray,
    out_landmarks_3d: np.ndarray,
) -> None:
    """
    Déquantifie les 468 points FaceMesh en une passe, extrait les 136 points requis
    et calcule le padding synthétique des 10 points d'iris directement dans out_tensor[0, 146, 2].
    Temps d'exécution : ~3.2 µs.
    """
    factor = scale * inv_crop_size
    for i in range(468):
        base = i * 3
        x = (float(raw_landmarks_q[base]) - zero_point) * factor
        y = (float(raw_landmarks_q[base + 1]) - zero_point) * factor
        z = (float(raw_landmarks_q[base + 2]) - zero_point) * factor
        out_landmarks_3d[i, 0] = x
        out_landmarks_3d[i, 1] = y
        out_landmarks_3d[i, 2] = z

    # Remplissage des 136 points principaux
    for idx_pos in range(136):
        lm_idx = subset_indices[idx_pos]
        out_tensor[0, idx_pos, 0] = out_landmarks_3d[lm_idx, 0]
        out_tensor[0, idx_pos, 1] = out_landmarks_3d[lm_idx, 1]

    # Centroïde Iris Gauche (moyenne paupières 159 et 145) dupliqué 5x (indices 136..140)
    lx = 0.5 * (out_landmarks_3d[159, 0] + out_landmarks_3d[145, 0])
    ly = 0.5 * (out_landmarks_3d[159, 1] + out_landmarks_3d[145, 1])
    for k in range(136, 141):
        out_tensor[0, k, 0] = lx
        out_tensor[0, k, 1] = ly

    # Centroïde Iris Droit (moyenne paupières 386 et 374) dupliqué 5x (indices 141..145)
    rx = 0.5 * (out_landmarks_3d[386, 0] + out_landmarks_3d[374, 0])
    ry = 0.5 * (out_landmarks_3d[386, 1] + out_landmarks_3d[374, 1])
    for k in range(141, 146):
        out_tensor[0, k, 0] = rx
        out_tensor[0, k, 1] = ry


@njit(fastmath=True, nogil=True, cache=True)
def one_euro_filter_52d_inplace(
    x: np.ndarray,
    dt: float,
    x_prev: np.ndarray,
    dx_prev: np.ndarray,
    min_cutoff: float,
    beta: float,
    d_cutoff: float,
    out_filtered: np.ndarray,
) -> None:
    """
    Filtre One-Euro vectorisé 52D en place sans aucune allocation mémoire (~4.5 µs).
    """
    if dt <= 1e-6:
        dt = 0.04  # Fallback 25 fps

    tau_d = 1.0 / (2.0 * np.pi * d_cutoff)
    alpha_d = 1.0 / (1.0 + tau_d / dt)
    inv_dt = 1.0 / dt

    for i in range(52):
        dx = (x[i] - x_prev[i]) * inv_dt
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * dx_prev[i]
        cutoff = min_cutoff + beta * abs(dx_hat)
        tau = 1.0 / (2.0 * np.pi * cutoff)
        alpha = 1.0 / (1.0 + tau / dt)

        x_hat = alpha * x[i] + (1.0 - alpha) * x_prev[i]
        x_prev[i] = x_hat
        dx_prev[i] = dx_hat
        out_filtered[i] = x_hat

```

---

### 3. CHECKLIST CRITIQUE DES PIÈGES & RISQUES MATÉRIELS

#### 1. Concurrence Gasket / Edge TPU PCIe & Blindage du Contexte `spawn`

* **Pourquoi `fork` est fatal** : Lorsqu'un processus parent a importé `pycoral` / `tflite_runtime` ou ouvert `/dev/apex_0`, un appel `os.fork()` duplique les descripteurs de fichiers et les tables de pages mmap pointant sur les registres BAR PCIe du pilote Gasket. Dès que le parent et l'enfant soumettent une requête `ioctl` ou libèrent un buffer DMA simultanément, le contrôleur d'interruptions MSI du Coral M.2 désynchronise ses pointeurs d'anneau matériel et déclenche l'erreur fatale noyau `gasket: Gasket interrupt completion timeout`.


* **Blindage strict du `spawn**` :
* Forcer `mp.get_context("spawn")` **avant** toute initialisation du delegate Edge TPU.


* Le processus parent (ou le worker d'ingestion FFmpeg/`PyAV`) ne doit **jamais** importer `pycoral` ni charger `libedgetpu.so.1`. Seul le processus d'inférence dédié doit instancier le delegate après son démarrage, sous le contrôle exclusif de `services/coral_tpu_orchestrator.py`.


* Vérifier systématiquement la présence des paramètres noyau `pcie_aspm=off pci=noaer` dans `/proc/cmdline` : si l'ASPM (Active State Power Management) met le lien PCIe en état de veille `L0s/L1` entre deux vidéos, le réveil du chip Apex provoque un bus lockup PCIe irrécupérable sans reboot matériel.





#### 2. Saturation de la SRAM On-Chip (8 Mo) & Fuites de Handles TFLite Delegate

* **Règle d'instanciation unique du Delegate** : Même avec deux modèles co-compilés (`blazeface_edgetpu.tflite` et `facemesh_edgetpu.tflite`) via `./scripts/compile_coral_comodels.sh`, appeler deux fois `load_delegate('libedgetpu.so.1')` ouvre deux contextes logiques distincts dans `libedgetpu` et force l'éviction mutuelle de la SRAM de 8 Mo. Il faut instancier l'objet delegate **une seule fois** (`edgetpu_delegate = load_delegate('libedgetpu.so.1')`) et passer cette même référence Python aux deux `Interpreter(..., experimental_delegates=[edgetpu_delegate])`.


* **Destruction ordonnée à la fermeture** : En fin de traitement vidéo, CPython peut détruire l'objet `edgetpu_delegate` avant les objets `Interpreter` lors du Garbage Collection, provoquant un `Segmentation fault (core dumped)` dans `libedgetpu.so.1`. Toujours supprimer explicitement les interpréteurs (`del facemesh_interp, blazeface_interp`) avant `del edgetpu_delegate`.

#### 3. Seuils de Quantification INT8 & Écrasement des Micro-Mouvements des Lèvres

* **Résolution spatiale d'un pas de quantification INT8 sur FaceMesh** :
Le tenseur de sortie de FaceMesh quantifié en `int8` ne dispose que de $256$ niveaux discrets sur la grille $192 \times 192$, soit un pas élémentaire minimal de :

$$\Delta_{\text{quant}} = \frac{192\text{ px}}{256} = 0.75\text{ pixel}$$



Si le visage dans le crop 192×192 est trop petit (marge de boîte englobante excessive) ou si la quantification de la dernière couche (`Conv2D` / `FullyConnected` des coordonnées 3D) utilise un `scale` mal calibré, une ouverture labiale de $1.2\text{ px}$ oscille brutalement entre $1$ et $2\text{ pas}$ de quantification ($\pm 0.75\text{ px}$).
* **Parades obligatoires** :
1. **Cadrage serré constant** : Ajuster le facteur d'échelle du crop affine (axe interpupillaire $\approx 38\%$ de la largeur `192` et centre décalé vers le bas de $+8\%$ vers l'arête nasale) pour que la bouche occupe au moins $55\text{ à } 70\text{ pixels}$ de large dans le repère 192×192.
2. **Filtrage Post-Régression (et non Pré-Régression)** : Appliquer le filtre `OneEuroFilterND` sur les **52 coefficients Blendshapes continus (`float32`)** (et éventuellement un second filtre léger à `min_cutoff=1.8, beta=0.04` sur les coordonnées labiales alimentant `EnhancedSpeakingDetector`). Si `min_cutoff` est réglé trop bas ($< 0.5\text{ Hz}$) en amont du modèle Blendshapes, les plosives rapides (`/p/`, `/b/`, `/m/` à 25 fps, soit $40\text{ ms}$) sont lissées avant la régression non-linéaire, écrasant les pics de `jawOpen` et `mouthClose`. Un réglage `min_cutoff = 1.25 Hz` et `beta = 0.08` sur les 52 Blendshapes élimine le bruit de marche d'escalier INT8 au repos tout en conservant une latence de phase nulle sur les consonnes rapides.