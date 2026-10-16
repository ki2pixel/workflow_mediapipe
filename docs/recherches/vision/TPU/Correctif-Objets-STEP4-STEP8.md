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
2. **Bascules de `source` d'une piste** : mesurées et requalifiées au § 9.2 — ce n'est pas un défaut mais
   un chemin de promotion `objet → visage` majoritairement bénéfique.
3. **Faux positifs à faible score** (seuil 0,3 du modèle) : le correctif n'en ajoute pas mais ne les filtre
   pas. Si le recentrage s'avère bruité, le levier propre est un seuil dédié (`person` uniquement), pas un
   élargissement du gate STEP6.
4. **Périmètre** : seules les **personnes** passent le gate STEP6. Transporter d'autres classes (véhicules,
   objets) demanderait de modifier le gate STEP6 **et** les filtres des panneaux EC/CEP.
5. **Confirmation audio** : le décalage `active_speakers` / `video_speakers` est **corrigé** (§ 9.1).

## 9. Pièces connexes

### 9.1 Confirmation audio : `active_speakers` (STEP5) vs `video_speakers` (STEP6)

**Diagnostic.** La STEP5 publie `active_speakers` (alimenté par la diarisation via
`speaking_sources.audio.active_speakers`) tandis que la STEP6 lit `video_speakers` — le champ qu'elle écrit
elle-même en sortie. Le champ d'entrée était donc **toujours vide** dans le flux standard : la confirmation
audio (`audio_confirm_count`, paliers `best_audio_face` / `best_audio_person`) ne se déclenchait jamais.

**Portée.** Les deux panneaux AE normalisent eux-mêmes `active_speakers` → `video_speakers` quand ils lisent
un JSON brut (`MediaSolution.jsx` EC l.451, CEP l.1503/1569) et le panneau EffectCraft n'utilise pas les
orateurs : le **recentrage EC n'est pas concerné**. Le consommateur réellement cassé est l'**analyseur STEP6**
(`--manifest_path`, utilisé par le panneau CEP et le script AE d'analyse), donc la **sélection du sujet**
côté After Effects.

**Correctif.** `_object_speakers()` dans la STEP6 : lit `video_speakers` et retombe sur `active_speakers`,
aux deux points d'entrée (production de `_ae.json` et mode analyseur). Aucun renommage côté STEP5, donc
**aucun re-run de STEP4 nécessaire**.

**Mesure (clip « Greg craque », 23 segments).** Dans `_ae.json` : **6 525 / 6 594** objets portent désormais
leurs orateurs (0 avant). Une piste audio-confirmée est disponible sur **22 des 23 segments**, et le sujet
retenu change sur **1 segment** — le segment 1 passe du gagnant présence×confiance à la piste confirmée par
la diarisation sur 272 frames, c'est-à-dire à la personne qui parle réellement.

**Test de non-régression** : `test_analyze_manifest_accepts_step5_active_speakers`, vérifié discriminant
(sans le repli on obtient `face2 / face_presence` au lieu de `face1 / audio_confirm_face`).

### 9.2 Bascules de `source` d'une piste (24 pistes sur 10 vidéos)

**Mesure.** Sur les 10 JSON publiés, **24 pistes** changent de `source` au cours de leur vie —
**toutes dans le sens `object_detector` → `face_landmarker`**, jamais l'inverse. Ce n'est donc pas un
« détournement » mais une **promotion** : une personne d'abord détectée comme objet devient la piste visage
quand le détecteur de visage la retrouve — l'`id` est conservé, la piste gagne des blendshapes et la
confiance visage. 11 de ces promotions partent de `person` (légitimes) mais **13 partent d'un libellé
non-personne** (chaise, plante, téléphone, carotte…) : une détection parasite devient alors une piste
« visage » à confiance 0,95.

**Impact sur le recentrage** (485 segments sur les 10 vidéos, sélection du panneau reproduite) :
**7 segments** sont gagnés par une piste à bascule, dont **5 légitimes** (la phase visage domine largement :
56/1, 46/12, 67/8 frames) et **2 parasites** — une piste « cell phone » (26 frames visage / 1 objet) et une
piste « carrot » (1 frame visage / 4 frames objet). Seul ce dernier cas est réellement pathologique :
**1 segment sur 485**.

**Recommandation.** Conserver le comportement actuel : la promotion apporte la continuité d'`id` (clé
d'agrégation du panneau) et des pistes plus denses, et son bénéfice dépasse largement ces deux cas. Le
garde-fou propre — n'autoriser la promotion que si la phase objet est étiquetée `person` — vit dans
`utils/tracking_optimizations.py`, **partagé par les trois chemins de tracking** (TPU, OpenCV 5, legacy).

**Simulation du garde-fou (485 segments).** Le garde-fou a été simulé hors ligne en scindant l'identité des
pistes promues depuis un libellé non-personne (14 pistes) : **aucun changement de sujet et aucun déplacement
de centre**. Les 2 seuls segments concernés passent de `obj_549`/`obj_214` à `obj_549__new`/`obj_214__new`,
avec la même source (`face_landmarker`), la même présence et le **même centre** (1161 px dans les deux cas
pour le segment 39).

La raison est structurelle : la STEP6 filtre déjà les frames d'objets non-personnes, seules les frames
visage de ces pistes entrent dans `_ae.json`. Le garde-fou ne modifie donc **que l'identifiant** de la phase
visage — un gain sémantique (une piste « chaise » ne devient plus « visage ») **sans effet mesurable sur le
recentrage**. Au prix d'une modification d'un composant partagé et d'un re-run complet de la STEP4, il n'est
pas retenu ; à reconsidérer si un consommateur futur exploite le champ `source` de façon décisionnelle.

