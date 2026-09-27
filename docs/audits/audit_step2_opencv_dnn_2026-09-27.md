# Audit — Warning de chargement OpenCV DNN dans STEP2 (`run_transnet_cv5.py`)

**Date** : 2026-09-27
**Périmètre** : `workflow_scripts/step2/run_transnet_cv5.py`, environnement `transnet_cv5_env`, modèle `assets/models/onnx/transnetv2.onnx`
**Déclencheur** : WARNING observé à chaque exécution de STEP2 après la renumérotation du pipeline

---

## TL;DR

Le warning **n'est pas un incident** : l'importeur OpenCV refuse **structurellement** `transnetv2.onnx`
(2 nœuds `Flatten` dont `axis == rang`), le fallback ONNX Runtime prend le relais et **constitue de fait le
chemin nominal** — en CUDA, 3/3 vidéos, ~5-7 s par vidéo. Deux corrections de forme sont recommandées :
ne plus présenter cet échec attendu comme une anomalie et afficher le **backend réellement utilisé**.

---

## 1. Symptôme observé

Run du 2026-09-27 21:48 (projet « 255 Camille », séquence 1→7) :

```
INFO  - Tentative de chargement du modèle ONNX avec OpenCV DNN...
WARNING - Échec de chargement avec OpenCV DNN (OpenCV(4.13.0) /io/opencv/modules/dnn/src/onnx/onnx_importer.cpp:1059:
          error: (-2:Unspecified error) in function 'handleNode'
        > Node [Flatten@ai.onnx]:(onnx_node!/base/frame_sim_layer/Flatten) parse error:
          ... shape_utils.hpp:243: error: ... in function 'int cv::dnn::normalize_axis(int, int)')
INFO  - ONNX Runtime : Accélération GPU CUDA disponible et activée.
INFO  - Session ONNX Runtime initialisée avec les providers actifs : ['CUDAExecutionProvider', 'CPUExecutionProvider']
INFO  - Modèle ONNX chargé via ONNX Runtime (fallback) : transnetv2.onnx
[...]
INFO  - Succès: 66m - CHARGES BOULANGERIE_TAT_M6.csv créé avec 38 scènes (5.80s, OpenCV 5.0 DNN)
INFO  - --- Analyse terminée. 3/3 réussie(s). Temps total: 18.2s ---
```

L'étape réussit donc intégralement ; seul le niveau de log et le libellé du backend sont trompeurs.

## 2. Chaîne de chargement (code)

| Étape | Emplacement |
| --- | --- |
| Tentative OpenCV : `cv2.dnn.readNetFromONNX` → backend `DNN_BACKEND_OPENCV` / cible `DNN_TARGET_CPU` → `ENGINE_NEW` si disponible | `load_opencv_dnn_model()` l. 173-201 |
| Fallback : wrapper `ORTDNNNet` (même API que `cv2.dnn.Net`) | l. 122-170 |
| Sélection des providers ORT (`CUDAExecutionProvider` puis `CPUExecutionProvider`, `STEP2_CV5_FORCE_CPU`) | l. 128-155 |
| Bascule à chaud GPU → CPU en cas d'erreur mémoire/CUDA à l'inférence | l. 380-386 |
| Validation pré-vol (`validate_onnx_slice_operator`, inférence synthétique 100 frames, `sys.exit(1)` si sortie vide) | l. 77-118, appelée l. 629 |

## 3. Cause racine (vérifiée sur le modèle)

Inspection du graphe (`onnx` 1.21, venv `transnet_env`) :

```
nœuds Flatten: 2
  /base/frame_sim_layer/Flatten   input=/base/frame_sim_layer/Pad_output_0   attrs={'axis': 3}
  /base/color_hist_layer/Flatten  input=/base/color_hist_layer/Pad_output_0  attrs={'axis': 3}
  tenseur Pad_output_0   : ['unk__3', 100, 200]   ← RANG 3
  tenseur Flatten_output_0: ['unk__11', 1]
```

- La spécification ONNX autorise `axis ∈ [-r, r]` **bornes incluses** pour `Flatten` ; `axis == r` signifie
  « aplatir toutes les dimensions en une seule colonne » (ici `[dyn×100×200, 1]`, cohérent avec la sortie déclarée).
- OpenCV 4.13 réutilise `normalize_axis(axis, dims)` (partagé avec `Concat`/`Split`), qui exige `axis < dims`
  → exception à l'import, avant même toute inférence.
- Le blocage est **structurel**, pas accidentel : un patch `Flatten → Reshape([-1, 1])` appliqué sur une copie du
  modèle débloque ce nœud mais bute immédiatement sur le suivant :
  ```
  Node [Mul@ai.onnx]:(onnx_node!/base/frame_sim_layer/Mul_2) parse error: onnx_importer.cpp:392
  ```
  → le graphe TransNetV2 n'est pas importable par OpenCV 4.13, quelle que soit la correction des `Flatten`.
- Environnement : `transnet_cv5_env` embarque **OpenCV 4.13.0** (et non 5.0) ; `cv2.dnn.DNN_ENGINE_NEW`
  et `DNN_ENGINE_AUTO` sont **absents** (`hasattr` → False), d'où le log `Engine: LEGACY`.

## 4. Le fallback est nominal — et il tourne sur GPU

- L'échec de l'import OpenCV est le chemin **prévu** par la règle d'or de la skill `opencv5-dnn-engine-expert`
  (« toujours prévoir le fallback ONNX Runtime »). Le code est correct sur ce point.
- L'injection dynamique de `LD_LIBRARY_PATH` (packages nvidia du venv) est effective en production :
  `CUDA_PATH_SETUP: LD_LIBRARY_PATH enrichi avec les packages nvidia du venv: 9 répertoires ajoutés`
  → provider actif `CUDAExecutionProvider` dans le run de production.
- ⚠️ **Piège de l'injection `LD_LIBRARY_PATH` (vérifié)** : exécuté hors du lanceur applicatif, ORT ne trouve pas CUDA 12 :
  ```
  Failed to load library libonnxruntime_providers_cuda.so with error: libcufft.so.11: cannot open shared object file
  Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 12.*
  providers actifs : ['CPUExecutionProvider']      ← repli silencieux sur CPU
  ```
  **Cause** : `libcufft.so.11` est pourtant présent dans le venv (`nvidia/cufft/lib/`), mais `setup_cuda_paths()`
  ne modifiait `LD_LIBRARY_PATH` qu'*après* le démarrage du processus, or l'éditeur de liens fige cet
  environnement au lancement : `dlopen` ne voit donc jamais l'ajout. La production fonctionne uniquement parce
  que `services/workflow_executor.py` (l. 340-366) injecte déjà ces répertoires dans l'environnement du
  **sous-processus**, avant son démarrage.
  **Impact mesuré** (clip de 12 s, même machine) : 1,07 s avec CUDA contre 8,84 s sur CPU — soit ~8× plus lent,
  sans aucun message d'erreur avant que le libellé de backend ne soit fiabilisé.
  **Correctif appliqué** : injection puis ré-exécution unique du script (`os.execv`) gardée par
  `STEP2_CV5_CUDA_ENV_READY`, et court-circuit lorsque les chemins sont déjà présents (cas de la production,
  qui ne se ré-exécute donc pas).

## 5. Constats annexes

1. **Libellé de backend trompeur** : le message de succès code en dur `(…, OpenCV 5.0 DNN)` (l. 502-503) alors
   que le backend effectif est ONNX Runtime. Ce texte remonte dans l'UI via `current_success_line_pattern`.
   Même imprécision dans le docstring de module (l. 5), le docstring `detect_scenes_cv5` (l. 216), la description
   argparse (l. 538) et le log de démarrage (l. 620). **Corrigé** (voir §7).
2. **Sonde du moteur CV5 incohérente entre documents et code** : le code teste `cv2.dnn.ENGINE_NEW` et appelle
   `net.setEngineType(...)` (l. 191-193) ; la skill documente `cv2.dnn.DNN_ENGINE_NEW` + `net.set(...)`, tandis que
   `codingstandards.md` écrit `ENGINE_NEW`. Les deux docs internes divergent → **à vérifier sur un vrai build 5.0**.
   Conséquence actuelle : le chemin « moteur graphe » n'a jamais été exercé, et le nom exact de l'API n'est pas
   validé.
3. **`config/step2_cv5.json` inexistant** : le script cherche ce fichier (l. 571) mais retombe sur ses valeurs par
   défaut (`threshold=0.5`, `window=100`, `stride=50`, `padding=25`, `ffmpeg_threads=0`, `batch_size=8`).
   `codingstandards.md` mentionne `ffmpeg_threads=1` comme optimal — l'écart n'est pas tranché.
4. **Warnings ORT bénins** : `MergeShapeInfo ... Falling back to lenient merge` (dimensions dynamiques du modèle
   exporté). Sans impact fonctionnel, silenciés par `log_severity_level = 3` (**corrigé**, voir §7).
5. **Variable d'environnement** : `STEP2_CV5_FORCE_CPU` est bien lue (nom mis à jour par la renumérotation).

## 6. Options de correction

| # | Action | Apport | Effort | Risque |
| --- | --- | --- | --- | --- |
| **A** | Distinguer les échecs d'importeur *connus* (`Flatten`/`Mul`) d'une panne réelle : log `INFO` motivé, `WARNING` conservé pour le reste | Fin du faux signal d'alarme dans les logs et l'UI | ~15 lignes | nul |
| **B** | Ne tenter OpenCV que si le moteur graphe est réellement disponible, sinon aller directement à ORT | Une tentative inutile en moins, message explicite | ~10 lignes | nul |
| **C** | Afficher le **backend réel** (`ORTDNNNet` ou `cv2.dnn.Net`) dans les messages de succès/démarrage | Traçabilité correcte, base saine pour comparer les backends | ~10 lignes | nul |
| **D** | Aligner la sonde `ENGINE_NEW` / `setEngineType` sur l'API réellement exposée par OpenCV 5.x | Débloque l'usage effectif du moteur graphe | ~10 lignes | faible (à valider sur un build 5.0) |
| **E** | Réduire le bruit ORT (`log_severity_level = 3`) | Logs plus lisibles | 2 lignes | nul |
| **F** | Rendre le modèle importable par OpenCV (au-delà de `Flatten`, corriger `Mul`) ou installer OpenCV 5.x | Seul moyen d'exploiter le moteur graphe | élevé | moyen |

**Recommandation** : livrer **A + B + C + E** (aucun changement de comportement fonctionnel, uniquement de la
traçabilité) ; engager **D** lors de l'installation d'un vrai OpenCV 5.0 ; garder **F** pour un chantier dédié,
l'échec étant aujourd'hui sans conséquence.

## 7. Correctifs appliqués

| Option | Statut | Détail |
| --- | --- | --- |
| **A** — échecs d'importeur en `INFO` | ✅ | `_IMPORTER_NODE_RE` identifie le nœud fautif (`Flatten`, `Mul`) : `INFO` motivé, détail complet en `DEBUG`, `WARNING` réservé aux erreurs inattendues |
| **B** — pas de tentative OpenCV sans moteur graphe | ✅ | `graph_engine_available()` sonde `DNN_ENGINE_NEW` **puis** `ENGINE_NEW` ; sinon chargement direct d'ONNX Runtime avec message explicite |
| **C** — backend réel affiché | ✅ | `backend_label()` alimente la ligne de chargement, la validation pré-vol et chaque ligne de succès (`ONNX Runtime (CUDA)`, `ONNX Runtime (CPU)` ou `OpenCV DNN x.y.z`) |
| **D** — alignement de l'API CV5 | ✅ partiel | `activate_graph_engine()` tente `net.set(DNN_ENGINE_NEW, True)` puis `setEngineType(ENGINE_NEW)` ; reste **à valider sur un vrai build OpenCV 5.x** |
| **E** — bruit ORT | ✅ | `set_default_logger_severity(3)` + `SessionOptions.log_severity_level = 3` → 0 ligne de bruit ORT sur le run de contrôle |
| **Injection CUDA** (hors audit initial) | ✅ | Ré-exécution unique du script après enrichissement de `LD_LIBRARY_PATH`, court-circuitée quand les chemins sont déjà fournis par le lanceur applicatif |

**Non traité** : **F** (compatibilité du graphe avec l'importeur OpenCV), inchangé — deux nœuds `Flatten` et un
nœud `Mul` restent non supportés par OpenCV 4.13.

**Vérifications** : `tests/integration/test_step2_cv5_integration.py` **3/3** ; run isolé sur un clip de 12 s en
CUDA (**1,08 s**) et en CPU forcé (`STEP2_CV5_FORCE_CPU=true`, **5,26 s**), 4 scènes détectées dans les deux cas ;
aucune ligne de bruit ORT dans le log produit. Effet de bord du re-exec en lancement manuel : un second fichier de
log ne contenant que la ligne `CUDA_PATH_SETUP` (la production, déjà correctement configurée, n'est pas concernée).

## Annexe A — Reproductible en une commande

```bash
/mnt/venv_ext4/transnet_cv5_env/bin/python -c "
import cv2; print(cv2.__version__, hasattr(cv2.dnn,'DNN_ENGINE_NEW'))
cv2.dnn.readNetFromONNX('assets/models/onnx/transnetv2.onnx')"
```

## Annexe B — Vérifier le backend réellement utilisé par un lancement manuel

```bash
grep -E "providers actifs|Modèle ONNX chargé" logs/step2/transnet_cv5_*.log | tail -2
# 'CPUExecutionProvider' seul ⇒ repli CPU (vérifier que les libs nvidia du venv sont accessibles)
```
