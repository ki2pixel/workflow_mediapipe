# Correctif — rendre les pistes d'objets exploitables jusqu'au recentrage STEP8

## 1. Le problème

Le chemin STEP4 actif (Coral TPU, `workflow_scripts/step4/run_tracking_tpu.py`) étiquetait chaque objet
détecté `label = f"class_{indice_brut}"`, alors que la STEP6 ne conserve un objet que si
`source == "object_detector"` **et** `label == "person"` (`preprocess_ae_json.py`, gate appliqué deux fois).
Résultat mesuré : **100 % des pistes d'objets du mode TPU étaient jetées** avant `_ae.json`, alors qu'elles
alimentent le recentrage horizontal par segment du panneau EffectCraft (STEP8,
`scripts/MediaSolution-EC/MediaSolution.jsx`, `pickBestObjectInRange`).

Ces pistes sont précisément le seul signal disponible dans les séquences **sans visage** — c'est-à-dire là
où le recentrage n'avait aucun candidat et restait en repli.

## 2. Vérification empirique de l'espace de classes (étape bloquante)

Avant de figer un mapping, `scripts/inspect_coral_object_detector.py` (venv Coral) a réinjecté des frames
réelles dans `assets/detect_edgetpu.tflite` et comparé ses sorties aux détections déjà publiées.

| Critère | Résultat |
|---|---|
| Reproductibilité des détections publiées | **50/50 (100 %)** avec IoU 0,96-0,998 ; l'indice modèle `0` reproduit les boîtes `class_0`, l'indice `61` les `class_61` |
| Indices observés | 0..89 — jamais ≥ 90, jamais un identifiant mort |
| Indices morts COCO (11, 25, 28, 29, 44, 65, 67, 68, 70, 82) | jamais émis (0 occurrence sur 10 vidéos et 23 frames échantillonnées) |
| Cas discriminants (contrôle visuel) | indice `61` = **fauteuil** (labelmap « chair ») et non des toilettes (COCO-80) ; indice `66` = **table de repas** (labelmap « dining table ») et non un clavier (COCO-80) |
| Contrôle de taille | boîte d'indice 61 : 501×466 px ≈ **1,01 × 0,94 m** (échelle donnée par une personne de 843 px ≈ 1,70 m) — taille d'un fauteuil, jamais de toilettes |

**Mapping retenu : `labelmap.txt[indice + 1]`** (91 lignes, `person` = indice 0).

> ⚠️ La liste COCO-80 du chemin OpenCV 5 (`run_tracking_cv5.py`, YOLO/ONNX) est un espace d'index
> **différent** : la réutiliser aurait étiqueté « person » des objets d'autres classes dès l'indice 12.
> Les deux listes sont désormais commentées comme non interchangeables.

## 3. Correctif livré

- **`utils/step4_tpu_detections.py`** (nouveau, pur stdlib) : liste normative de 91 libellés, `label_for_class_index`,
  `resolve_class_label` (repli `class_N` qui ne peut jamais produire `person` par accident),
  `verify_labelmap_file` (contrôle best-effort au démarrage, non bloquant), et les builders
  `build_face_detection` / `build_object_detections` qui remplacent **les deux blocs dupliqués** du script.
- **Parité du dict visage** : le chemin multiprocessing n'écrivait aucune clé `label` (valeur `""` en sortie).
  Ce n'était pas cosmétique : `scripts/aggregate_step5_metrics.py` calcule son « face rate » sur ce champ et
  renvoyait donc **0 %** en mode TPU. Le libellé est maintenant `"face"` (la confiance historique, `1.0`,
  est conservée pour ne pas déplacer les scores de sélection du panneau).
- **Réglage d'hystérésis** `STEP4_TPU_OBJECT_DETECTION_FACE_RESET_FRAMES` (§ 6).

## 4. Non-régression

| Mesure | Référence (`final_v2`) | Avec correctif |
|---|---|---|
| Débit global | 120,33 fps (8,311 ms/frame) | **122,54 fps (8,16 ms/frame)** |
| Invocations `object_detector_tpu` | **5 422** | **5 422** (invariant exact) |
| Coût OD amorti | 1,68 ms/frame | 1,67 ms/frame |
| BlazeFace / FaceMesh / blendshapes | inchangés | inchangés |

La logique d'invocation n'ayant pas été touchée, le compte d'invocations **identique** est la preuve de
non-régression ; le débit est dans le bruit (+1,8 %).

## 5. Validation bout en bout et valeur pour le recentrage

Chaîne STEP5 → STEP6 rejouée **sur copie** (`scratch/e2e*`), vidéo « Greg craque » :

| | Avant (labels `class_N`) | Après |
|---|---|---|
| Frames `_ae.json` avec une piste personne | **0** (toutes jetées par le gate) | **1 473** |
| Objets personne dans `_ae.json` | 0 | **5 110** |
| Libellés `class_N` | 15 libellés résiduels | **aucun** |

Métriques de valeur (23 segments CSV, sélection reproduite du panneau) :

- **1 segment sans aucune piste en gagne une** : segment 6 (31,88-34,36 s), désormais recentré sur une
  personne (`obj_87`, 8 frames) — il restait auparavant en repli « non recentré ».
- **9 segments passent d'une piste visage à une piste personne**, bien plus dense. Exemple décisif :
  segment 1 — visage détecté sur **7 frames** (centre 791 px) contre **265 frames** de personne (centre 348 px).
- Variation médiane du centre retenu : **4,0 px** (les segments stables ne bougent pas).

**Caveat à valider visuellement** : ces 9 bascules changent la cible du recentrage (la règle du panneau est
« la piste la plus dense gagne », inchangée). Les rendus sont à contrôler dans EffectCraft — c'est le seul
effet visible du correctif.

## 6. Arbitrage de l'hystérésis (mesuré)

`STEP4_TPU_OBJECT_DETECTION_FACE_RESET_FRAMES` (défaut `1`) : nombre de frames **avec** visage nécessaires
pour réarmer le compteur anti-invocations. `1` = comportement historique.

| Variante | Débit | Invocations OD | Coût OD amorti | Couverture objets |
|---|---|---|---|---|
| `= 1` (défaut retenu) | **122,54 fps** | 5 422 | 1,67 ms/frame | 11,8 % des frames |
| `= 3` | 104,14 fps | 10 803 | 3,32 ms/frame | **22,7 % des frames** |

Le raffinement **double la densité des pistes d'objets** (donc la matière du recentrage) mais coûte **15 % de
débit** et ne franchit pas le seuil de 110 fps fixé avant la mesure : le défaut reste `1`. Le passage à `3`
est un choix produit (qualité du recentrage contre vitesse) qui tient à une variable d'environnement.

## 7. Outils livrés

```bash
# Preuve de l'espace de classes (venv Coral, aucune modification de fichiers)
coral_env/bin/python scripts/inspect_coral_object_detector.py \
    --video "<clip>.mp4" --json "<clip>.json" --frames 25,413,1741 --dump-dir <dir>

# Inventaire des libellés, intermittence du visage, plages trop courtes pour le détecteur
python3 scripts/audit_object_labels.py --json-dir <dir_json_step4>

# Présence des pistes personne dans un _ae.json et couverture par segment CSV
python3 scripts/audit_object_labels.py --ae "<clip>_ae.json"
python3 scripts/audit_object_labels.py --segments "<clip>_ae.json" --csv "<clip>.csv" \
    --compare <audit_avant.json> --out <audit_apres.json>

# Tests
bash scripts/run_step4_tests.sh && bash scripts/run_main_tests.sh
```

## 8. Risques et pièces connexes

1. **Libellés `class_N` déjà publiés** : les `<stem>.json` livrés avant ce correctif restent exploitables pour
   les visages mais leurs objets sont perdus ; il faut rejouer STEP4 → STEP5 → STEP6 pour rafraîchir
   (`_tracking.json` et `_ae.json`), STEP5 réécrivant `_audio.json` **en place**.
2. **Pistes détournées** (préexistant) : une détection d'objet peut écraser une piste de visage
   (`utils/tracking_optimizations.py`). Avant, la piste devenait `class_N` et **disparaissait** de
   `_ae.json` (trou) ; désormais elle survit en `person`, centrée sur l'objet — meilleure continuité d'`id`,
   mais dérive possible du centre. À surveiller lors du contrôle visuel.
3. **Faux positifs à faible score** (seuil 0,3 du modèle) : le correctif n'en ajoute pas mais ne les filtre
   pas. Si le recentrage s'avère bruité, le levier propre est un seuil dédié (`person` uniquement), pas un
   élargissement du gate STEP6.
4. **Périmètre** : seules les **personnes** passent le gate STEP6. Transporter d'autres classes (véhicules,
   objets) demanderait de modifier le gate STEP6 **et** les filtres des panneaux EC/CEP.
5. **Pièce connexe identifiée, non traitée** : la STEP5 écrit `active_speakers` alors que la STEP6 lit
   `video_speakers` → la branche de confirmation audio (`best_audio_person`) ne se déclenche jamais dans le
   flux standard. À traiter séparément, avec sa propre mesure.
