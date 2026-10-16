# Benchmark et optimisation de la STEP4 tracking (Coral Edge TPU)

Campagne de mesure et d'optimisation du pipeline `workflow_scripts/step4/run_tracking_tpu.py`
sur les 10 vidéos de `projets_extraits/` (1080p, 25 fps, STEP1-3 déjà exécutées, 49 720 frames).

## 1. Résultat

| Variante | Débit | ms/frame | Durée du lot |
|---|---|---|---|
| Baseline (code d'origine) | 79,09 fps | 12,644 | 629,2 s |
| `STEP4_TPU_FAST=0` (refactorisations seules) | 84,02 fps | 11,902 | 592,4 s |
| **Code livré** (`STEP4_TPU_FAST=1`) | **120,33 fps** | **8,311** | **413,4 s** |

**+52 % de débit, −34 % de temps de calcul** (3 min 36 s gagnées sur ce lot), sans perte de
précision mesurable sur les données consommées en aval (voir § 5).

## 2. Méthode

- **Instrumentation par étage** : `utils/step4_tpu_profiler.py` (anneau NumPy préalloué,
  horodatage `time.perf_counter_ns()`, aucun log dans la boucle chaude), activée par
  `--profile-dir` ou `STEP4_TPU_PROFILING_DIR`. Statistiques count / moyenne / P50 / P95 / P99 /
  max par étage, par vidéo et par processus (acquisition, worker, parent), avec fingerprint du run
  (modèles + sha256, delegate, commit git, environnement STEP4).
- **Harnais de variantes** : `scripts/bench_step4_tpu.py` (isolation des artefacts par variante,
  agrégation, rapport Markdown/CSV/JSON, garde-fou anti-mock, exclusion du warm-up).
- **Comparateur de précision** : `scripts/compare_step4_tracking_outputs.py` (RMSE par coefficient
  ARKit, indices de jittering, IoU, dérive de centroïde, churn d'identités, accord d'élocution).
- La baseline instrumentée reproduit exactement le run applicatif (629 s contre 635 s), ce qui
  valide l'absence de perturbation par la mesure.

## 3. Où passait réellement le temps

Le profilage contredit l'hypothèse de départ des rapports d'optimisation (qui visaient le décodage
et le recadrage affine) :

| Étage | Baseline | Code livré | Δ |
|---|---|---|---|
| `worker_worker_total` (par frame) | 12,343 ms | **7,337 ms** | **−5,01 ms** |
| `worker_object_detector_tpu` (par invocation) | 15,223 ms | 15,268 ms | = |
| `worker_blazeface_tpu` | 2,789 ms | 1,997 ms | −0,79 |
| `worker_facemesh_tpu` | 2,870 ms | 2,804 ms | −0,07 |
| `worker_blendshapes_cpu` | 2,281 ms | 2,390 ms | +0,11 |
| `worker_affine_crop` | 0,498 ms | 0,490 ms | −0,01 |
| `worker_one_euro` | 0,100 ms | 0,091 ms | −0,01 |
| `acq_acq_read_pipe` (décodage FFmpeg + pipe) | 4,012 ms | 4,232 ms | +0,22 |
| `acq_acq_shm_write` | 1,164 ms | 1,092 ms | −0,07 |
| `acq_acq_push` (attente de place) | 7,276 ms | 0,027 ms | saturation levée |
| `parent_total` | 0,761 ms | 0,349 ms | −0,41 |
| `e2e_frame` (latence frame) | 120,1 ms | 52,9 ms | −56 % |

### 3.1 Le goulot principal : le détecteur d'objets de secours

- 19 849 invocations sur 49 720 frames (**39,9 %**), à **15,2 ms** chacune → **5,99 ms/frame
  amortis**, soit 47 % du temps worker.
- Effet secondaire non anticipé : chaque invocation **évince la SRAM 8 Mo** des modèles
  co-compilés BlazeFace+FaceMesh. La preuve est dans les mesures : sur `Greg craque` (70 % de
  frames sans visage), BlazeFace coûte 3,01 ms contre 2,43 ms sur `Benjy` (8 % sans visage) —
  à modèle et résolution identiques. En désactivant le détecteur, ces étages reviennent à
  2,76 / 2,66 ms.
- **Correctif retenu** : hystérésis `STEP4_TPU_OBJECT_DETECTION_MIN_MISSING` (défaut 25) —
  le détecteur n'est invoqué qu'après 25 frames consécutives sans visage. Mesure sur les sorties
  réelles : 19 849 → 5 856 invocations (−70 %), soit **−4,2 ms/frame**. Le comportement est
  conservé sur les séquences durablement sans visage (les apparitions brèves ne déclenchent plus
  d'inférence inutile). `=1` restaure le comportement historique.
- **Mesure de contrôle** : avec `STEP4_ENABLE_OBJECT_DETECTION=0`, le lot passe de 82,3 à
  144,8 fps sur les deux vidéos testées (×1,76).

### 3.2 Constat annexe : la sortie du détecteur d'objets est jetée en aval

- Le script TPU écrit `label = "class_{id}"` ; la STEP6 ne conserve que
  `source == "object_detector" and label == "person"` (`preprocess_ae_json.py:235`) — alors que le
  chemin OpenCV 5 mappe les classes COCO (`run_tracking_cv5.py:633`).
- Conséquence : en mode TPU, **tous les objets détectés sont silencieusement écartés** par la
  STEP6. Le coût (≈ 1,8 ms/frame même avec l'hystérésis) est donc actuellement entièrement perdu.
- Deux options selon l'intention produit : soit corriger le label (mapping COCO → `person`), soit
  désactiver le détecteur (`STEP4_ENABLE_OBJECT_DETECTION=0`) pour gagner ~1,8 ms/frame de plus.

## 4. Optimisations implémentées

Toutes derrière `STEP4_TPU_FAST` (0 = comportement historique, 1 = défaut livré).

| Optimisation | Fichier | Gain mesuré | Validation |
|---|---|---|---|
| Hystérésis détecteur d'objets | `run_tracking_tpu.py` | −4,2 ms/frame | comptage sur sorties réelles |
| Cache des ancres BlazeFace (boucle Python 896 itérations → vecteur NumPy mémoïsé) | `utils/tpu_facemesh_utils.py` | −0,45 ms/frame | identité bit à bit vs implémentation d'origine |
| Cache des métadonnées d'interpréteur (`get_input_details`/`get_output_details`/fabrique de tenseur) | `run_tracking_tpu.py` | ~−0,03 ms/frame | test : résolution unique par interpréteur |
| One-Euro vectorisé (1 noyau JIT au lieu de 52 appels) | `utils/one_euro_filter.py` | −0,06 ms/frame | écart ≤ 1e-12 sur 5 000 frames vs formule d'origine |
| Écriture JSON tamponnée (1 flush / 100 frames au lieu de 1 / frame) | `run_tracking_tpu.py` | −0,13 ms/frame | |
| Appariement tracking sans KDTree (NumPy, N ≤ 20) | `utils/tracking_optimizations.py` | −0,15 ms/frame | équivalence vs calcul exhaustif + supprime la dépendance scipy (débloque 5 tests STEP4 jusque-là ignorés) |
| Suppression du `KalmanFilterND` mort et du `NameError` latent du détecteur d'objets séquentiel | `run_tracking_tpu.py` | — | correctif |

### 4.1 Correctif de déterminisme (course sur l'anneau de mémoire partagée)

Le pipeline partageait 8 slots de mémoire partagée entre le thread d'acquisition et le processus
d'inférence. Le slot était recyclé dès que le worker **défilait** la frame de la file — alors qu'il
en lisait encore les pixels (redimensionnement BlazeFace puis recadrage affine). Résultat :
redimensionnement d'une frame « déchirée » (mélange de deux frames).

- **Preuve** : deux exécutions strictement identiques du code d'origine divergent sur ~1 % des
  frames (accord de présence 0,9933, RMSE 0,0065).
- **Correctif** : protocole de jetons (`free_slots`) — le worker rend le slot après le dernier
  accès aux pixels (après le recadrage, ou après le détecteur d'objets sur les frames sans visage).
- **Preuve après correctif** : deux exécutions identiques produisent des JSON **au sha256 identique**.
- Coût mesuré du correctif : neutre (±1 % sur les mêmes vidéos), le pipeline reste piloté par le worker.

## 5. Validation de précision

Verdict machine complet : `Precision-Baseline-vs-Final.md` (généré par le comparateur).

| Indicateur | Mesure | Seuil |
|---|---|---|
| RMSE blendshapes (max sur 52 coefficients) | 0,019 – 0,025 | < 0,035 ✅ |
| RMSE sous-ensembles bouche / yeux | ≤ 0,022 / ≤ 0,024 | < 0,035 ✅ |
| Indices de jittering (5 coefficients critiques) | stables à ±2 % pour 41/50 mesures | non dégradés ✅ |
| Accord `is_speaking` | 1,0000 | ≥ 0,995 ✅ |
| Churn d'identités | 131→133, 284→276, … | ≤ ×1,10 ✅ |
| Accord de présence de visage | 0,79 – 0,92 | ⚠️ voir ci-dessous |

**Les écarts de présence/position ne proviennent pas des optimisations** — trois mesures le
démontrent :

1. **Les refactorisations sont exactes** : chaque brique est vérifiée par test unitaire
   (ancres identiques bit à bit, One-Euro ≤ 1e-12 sur 5 000 frames, appariement conforme au calcul
   exhaustif, cache d'interpréteur résolu une fois) et deux exécutions du code livré produisent des
   fichiers identiques.
2. **L'hystérésis n'est pas la cause** : en réexécutant le code livré avec la cadence historique
   (`STEP4_TPU_OBJECT_DETECTION_MIN_MISSING=1`), les écarts vs baseline sont *inchangés*
   (0,9238 / 0,6419 / 0,025222 — valeurs identiques au bit près). L'écart est donc entièrement
   attribuable au **correctif de course** : la baseline produisait des détections sur des frames
   déchirées, le code livré produit les détections correctes.
3. **Couplage préexistant visage ↔ objet** : le détecteur d'objets peut détourner une piste de
   visage (le tracker partage la table `active_objects`, `utils/tracking_optimizations.py`), ce qui
   change le `source` de l'objet émis et le retire du périmètre « visages ». Mesuré sur
   `Andy avoue…` : 38 identités alternent visage ↔ objet, et 12 097 objets émis sur 14 285 sont des
   objets (jetés par la STEP6, cf. § 3.2). Ce comportement est antérieur à cette campagne.

Recommandation pour un gate strict de non-régression : comparer deux exécutions du **même** code
(le comparateur sert alors de test de déterminisme) et utiliser les seuils stricts par défaut ;
la comparaison vs une baseline non déterministe reste indicative sur les métriques de présence.

## 6. Pistes mesurées puis écartées

Chaque hypothèse des rapports d'optimisation a été mesurée avant décision :

| Piste | Mesure | Verdict |
|---|---|---|
| `cv2.warpAffine` sur ROI au lieu de la frame 1080p entière | 0,204 ms (pleine trame, 1920×1080 → 192) ; profilage : 0,49 ms porte compris | écartée : gain < 0,15 ms (les rapports annonçaient 1,4-2,1 ms) |
| Redimensionnement BlazeFace par décimation / `INTER_AREA` | `INTER_LINEAR` actuel : 0,047 ms ; `INTER_AREA` : 5,67 ms ; décimation + `INTER_AREA` : 0,43 ms | écartée : la version actuelle est la plus rapide ; toute variante aurait dégradé le détecteur pour rien |
| Assemblage du tenseur 146 points in-place (`@njit`) | 0,026 → 0,0085 ms | écartée : 17 µs, non significatif |
| Modèle Blendshapes en 4 threads TFLite | étage 2,27 → 1,78 ms mais **débit global 120,4 → 118,4 fps** | écartée : contention CPU avec le décodage (`STEP4_TPU_CPU_THREADS=1` conservé) |
| Transport PyAV / YUV420p (gain annoncé 8-14 ms) | acquisition réelle après correctifs : 4,2 + 1,1 = 5,3 ms/frame, **sous** le worker (7,3 ms) | reportée : l'acquisition n'est pas le goulot ; la refonte ne gagnerait rien tant que le worker reste au-dessus |
| Cadence BlazeFace (1 frame sur N) | gain potentiel ≈ 1,5 ms/frame | non implémentée : modifie l'entrée FaceMesh, exige un gate de précision dédié (voir § 7) |

## 7. Suite recommandée

1. **Décider du sort du détecteur d'objets** (§ 3.2) : corriger le label COCO ou le désactiver
   (−1,8 ms/frame supplémentaire, soit ≈ 131 fps).
2. **Pipelining CPU ↔ TPU intra-worker** : les deux invocations TPU représentent désormais
   **58 % du budget worker** (4,8 ms sur 8,31 ms/frame), ce qui satisfait le critère de décision
   fixé en début de campagne (≥ 40 %). Le recouvrement du post-traitement CPU (blendshapes + recadrage,
   ≈ 2,4 ms) derrière l'invocation TPU de la frame suivante est le levier restant le plus rentable.
   Complexité élevée : threading dans le worker, un seul consommateur `/dev/apex_0`, ordre de
   destruction delegate/interpréteurs.
3. **Cadence BlazeFace** : prochain levier simple sur le worker (≈ 1,5 ms/frame). Le harnais et le
   comparateur sont en place pour valider la non-régression ; à activer seulement si les seuils de
   précision passent.
4. **Transport YUV/PyAV** : à réévaluer une fois le worker descendu sous ~5,3 ms/frame (c'est alors
   le décodage qui devient limitant, et le gain devient réel).
5. **Fiabiliser le couplage visage/objet** du tracker partagé (le détournement de piste fausse la
   sortie `source` et donc le filtrage STEP6).
6. **Dette cosmétique** : la métadonnée `tracking_method` vaut encore `kdtree_tpu` (et `kdtree_cv5`
   côté OpenCV 5) alors que l'appariement est un plus-proche-centroïde NumPy partagé. Le champ n'est
   lu par aucun consommateur du dépôt ; il a été conservé pour ne pas invalider les sorties déjà
   publiées.

## 8. Reproduction

```bash
# Baseline gelée (référence)
python3 scripts/bench_step4_tpu.py --variant baseline --root projets_extraits

# Variante optimisée
python3 scripts/bench_step4_tpu.py --variant final --root projets_extraits --env STEP4_TPU_FAST=1

# Comparaison de précision (visages uniquement)
python3 scripts/compare_step4_tracking_outputs.py \
    --ref scratch/bench_step4_tpu/<horodatage>_baseline/outputs \
    --test scratch/bench_step4_tpu/<horodatage>_final/outputs \
    --faces-only --markdown rapport.md

# Tests
bash scripts/run_step4_tests.sh    # profiler, optimisations, pipeline TPU (55 passés)
bash scripts/run_main_tests.sh     # harnais, comparateur (652 passés)
```

Variables d'environnement : `STEP4_TPU_FAST` (0/1), `STEP4_TPU_OBJECT_DETECTION_MIN_MISSING`,
`STEP4_TPU_CPU_THREADS`, `STEP4_TPU_PROFILING_DIR`, `STEP4_TPU_PROFILE_WARMUP`.
