# Plan de continuité — STEP3 audio (2026-10-17)

Ce document est la note de reprise après la modernisation STEP3 livrée dans le commit
`59200d7`. Il couvre les deux chantiers qui restent ouverts : la validation du stride
d'embeddings K=2 sur un corpus élargi, et le passage réel de YAMNet sur l'Edge TPU via
un modèle scindé « frontend CPU + CNN compilé ».

## 1. État livré et points d'entrée

### Ce qui est en place

- Harnais acoustique VoxConverse : `scripts/fetch_voxconverse_dev.py`,
  `scripts/bench_step3_tpu_der.py`, `scripts/bench_step3_der_eval.py`.
- Banc fournisseurs ONNX : `scripts/bench_ecapa_providers.py`.
- Tests : `scripts/run_step3_tests.sh` (52 tests STEP3 ; 93 tests avec STEP5 et
  l'orchestrateur).
- Déterminisme VAD : écriture du tenseur, `invoke()` et lecture sous un même verrou par
  bloc (256 fenêtres) ; la course legacy (`set_tensor`/`get_tensor` hors verrou) est
  corrigée.
- OpenVINO : `onnxruntime-openvino==1.24.1` dans `coral_env`, EP CPU FP32 sélectionné
  automatiquement, batch 8, `STEP3_DISABLE_OPENVINO=1` pour forcer le CPU.
- Stride ECAPA : `STEP3_EMBEDDING_STRIDE` (défaut `1`), assignation au plus proche
  temporel ; K=2 validé en opt-in, K=4 rejeté.
- Garde-fous : `validate_startup.py` (pcie_aspm=off, `/dev/apex_0`, groupe apex),
  détection `edgetpu-custom-op` dans le flatbuffer, `STEP3_REQUIRE_EDGETPU=1`.

### Mesures de référence (VoxConverse dev, 1 worker)

| Configuration | Extraits | Total | DER strict | Commentaire |
|---|---|---|---|---|
| K=1 CPU | 5 | 186 s | 36,85 % | référence |
| K=1 OpenVINO | 5 | 121 s | 36,85 % | parité exacte, 1,54× |
| K=2 OpenVINO | 5 | 73 s | 21,53 % | 2,55×, aucun extrait dégradé sur ces 5 |
| K=2 OpenVINO | 10 | 122 s (vs 211 s) | 21,12 % (vs 30,25 %) | 3/10 extraits +1,5 à +3,2 pts |
| K=4 CPU | 5 | 60 s | 23,90 % | akthc +4,1 pts → rejeté |

### Variables d'environnement utiles

- `STEP3_EMBEDDING_STRIDE` : `1` (défaut, parité stricte) ou `2` (opt-in).
- `STEP3_DISABLE_OPENVINO` : `0` (défaut) / `1` (CPU strict).
- `STEP3_REQUIRE_EDGETPU` : `0` (défaut, repli explicite) / `1` (échec si non compilé).
- `STEP3_MAX_WORKERS` : `4` en production ; **`1` pour tout benchmark déterministe**.

### Artefacts locaux (gitignorés)

`scratch/bench_step3_der/{ov_k1,ov_k2,ov_k1_10,ov_k2_10}` contiennent les rapports
Markdown/JSON et les timings. Le corpus VoxConverse extrait (WAV + RTTM) n'est plus
conservé localement : il a été supprimé le 2026-10-24 pour limiter l'empreinte disque.
Le retélécharger avec `python3 scripts/fetch_voxconverse_dev.py` (~2 Go) avant tout
benchmark.

---

## 2. Axe 1 — Valider K=2 sur un corpus élargi

### Objectif

Décider si `STEP3_EMBEDDING_STRIDE=2` peut devenir le défaut, ou rester un réglage
opt-in. Le critère n'est pas seulement le DER agrégé : une dégradation locale sur un
extrait peut être inacceptable même si la moyenne s'améliore.

### Protocole

1. Sélectionner 20 à 50 clips VoxConverse dev, stratifiés par durée (<2 min, 2–5 min,
   >5 min), par nombre de locuteurs RTTM et par densité de parole. Le harnais prend
   aujourd'hui les N premiers clips triés : ajouter une option `--clips-file` (liste de
   stems) ou `--manifest` pour rendre la sélection explicite et reproductible.
2. Garder **K=1 OpenVINO, 1 worker** comme référence déterministe.
3. Évaluer **K=2** (puis K=3 si K=2 est acceptable mais perfectible), mêmes réglages.
4. Comparer par extrait : DER, JER, Missed/FA/Confusion, et temps ECAPA/total.
5. Tester ensuite une règle **adaptative** plutôt qu'un K global : appliquer K=2
   uniquement au-delà d'un nombre de fenêtres de parole (par exemple ≥ 300–500) et
   conserver K=1 sur les extraits courts, où les effets de bord de locuteur dominent.
   Les résultats 10 clips suggèrent que les dégradations apparaissent sur des extraits
   courts, mais la taille de l'échantillon ne permet pas encore de conclure.

### Commandes

```bash
python3 scripts/fetch_voxconverse_dev.py

# Référence (à refaire sur la sélection retenue)
python3 scripts/bench_step3_tpu_der.py --limit 30 \
    --out scratch/bench_step3_der/k1_ref \
    --env STEP3_MAX_WORKERS=1 --env STEP3_EMBEDDING_STRIDE=1

# Candidat K=2 (contrôle de non-régression agrégée)
python3 scripts/bench_step3_tpu_der.py --limit 30 \
    --out scratch/bench_step3_der/k2_eval \
    --baseline scratch/bench_step3_der/k1_ref/der_report.json \
    --env STEP3_MAX_WORKERS=1 --env STEP3_EMBEDDING_STRIDE=2

# Vérification de parité stricte pour un réglage neutre
python3 scripts/bench_step3_tpu_der.py --limit 30 --require-parity \
    --baseline scratch/bench_step3_der/k1_ref/der_report.json \
    --env STEP3_MAX_WORKERS=1 --env STEP3_EMBEDDING_STRIDE=1
```

### Critères d'acceptation

- ΔDER agrégé ≤ 0 (pas de dégradation globale) et **aucun extrait** ne se dégrade de
  plus de 0,5 point (seuil à confirmer).
- JER stable ou meilleur ; contrat JSON inchangé (clés, frames, `speaker_stats`).
- Gain de temps ≥ 1,5× sur le total et ≥ 1,8× sur l'étage ECAPA.
- Si un extrait se dégrade au-delà du seuil : conserver le défaut `1` et documenter
  K=2 comme réglage manuel, ou implémenter la règle adaptative.

### Livrables

- Rapports `der_report.json` des deux configurations + tableau comparatif par extrait.
- Mise à jour éventuelle du harnais (`--clips-file`) et de `bench_step3_der_eval.py`
  (rapport par extrait déjà présent).
- Décision consignée dans `memory-bank/decisionLog.md` et `docs/workflow/pipeline/03-audio-analysis.md`.
- Si la règle adaptative est validée : implémentation dans `run_vad_and_embedding`
  (seuil sur `len(speech_indices)`), tests unitaires associés.

### Risques

- Échantillon initial de 5/10 clips : ne pas généraliser sans la sélection élargie.
- Les changements de locuteur en bordure de fenêtre expliquent probablement les
  dégradations locales ; la règle adaptative ou un embedding par segment fusionné sont
  les pistes à comparer.
- Le DER dépend aussi de la VAD (YAMNet), pas seulement du clustering ; lire les
  composantes Missed/FA/Confusion avant d'attribuer un écart au stride.

---

## 3. Axe 2 — YAMNet : frontend CPU + CNN compilé Edge TPU

### Constat actuel

Le modèle `yamnet_audio_classificator_quantized_edgetpu.tflite` n'est pas compilé pour
l'Edge TPU : il contient le frontend log-mel (`LOG`, `SQRT`, `MEAN`, `GATHER`) et
`edgetpu_compiler` ne mappe que 3 opérations sur 53 (un seul sous-graphe TPU autorisé).
Le tarball officiel PINTO ne fournit aucun modèle compilé. La VAD s'exécute donc sur
CPU/XNNPACK (~4,9 ms par fenêtre), avec une erreur explicite au démarrage.

### Architecture cible

1. **Frontend CPU** : calcul des patches log-mel YAMNet en NumPy/Numba, à parité avec le
   frontend intégré actuel. Paramètres à relever depuis le SavedModel YAMNet :
   `sample_rate=16000`, `frame_length=400`, `frame_step=160`, `fft_length=512`,
   `mel_bins=64`, `patch_frames=96`, `patch_hop_seconds=0.48`, `log_offset=0.001`,
   `log_scale=1.0`, moyenne/écart-type de standardisation. Le patch d'entrée du CNN est
   `(96, 64)`.
2. **CNN TFLite INT8** : MobileNetV1 depthwise + tête de classification (521 scores,
   éventuellement 1024D), sans le frontend. Quantification full-int8 avec un jeu
   représentatif de patches log-mel (parole, musique, bruit, silence) issus de
   VoxConverse et d'enregistrements variés.
3. **Compilation Edge TPU** : `edgetpu_compiler -s` puis contrôle du log ; objectif :
   la majorité des `CONV_2D`/`DEPTHWISE_CONV_2D`/`FULLY_CONNECTED` sur TPU, et présence
   de `edgetpu-custom-op` dans le flatbuffer.
4. **Intégration** : nouveau modèle `assets/yamnet_split_edgetpu_compiled.tflite`,
   frontend dans `workflow_scripts/step3/yamnet_frontend.py` (ou dans le script STEP3),
   réutilisation du producteur-consommateur double tampon existant (le producteur
   prépare les patches, le consommateur invoque le modèle). Feature flag
   `STEP3_YAMNET_SPLIT=1` (défaut `0`) tant que la parité n'est pas prouvée ; le modèle
   actuel reste le fallback. `STEP3_REQUIRE_EDGETPU=1` doit fonctionner avec le nouveau
   modèle.

### Étapes de réalisation

1. Créer un venv de build **hors `coral_env`** (TensorFlow 2.x) ; récupérer le
   SavedModel YAMNet (TF Hub `google/yamnet/1` ou `saved_model.pb` du tarball PINTO).
2. Extraire le sous-graphe CNN : entrée `(1, 96, 64)` standardisée, sorties scores (et
   embeddings) ; vérifier en float la parité avec le modèle actuel sur des waveforms
   réelles.
3. Exporter en TFLite float, puis full-int8 (PTQ) avec le jeu représentatif ; mesurer
   l'écart des scores entre float et int8 et l'accord de décision au seuil 0.20.
4. Compiler pour l'Edge TPU ; inspecter le log et le flatbuffer ; mesurer la latence
   réelle par patch avec le délégué.
5. Intégrer derrière le feature flag ; conserver le chemin actuel comme fallback et
   conserver les formats de progression.
6. Valider avec le harnais : scores VAD (parité/accord), DER/JER K=1 sur 5 puis 10–30
   clips, latence VAD et temps total, `validate_startup.py`, tests unitaires.

### Critères d'acceptation

- Frontend : écart max sur les patches et les scores compatible avec le seuil de
  décision ; accord de décision VAD ≥ 99,5 % au seuil 0.20 (à ajuster après mesure).
- Modèle : `edgetpu-custom-op` présent, majorité des convolutions sur TPU, latence
  VAD par fenêtre nettement inférieure au CPU (objectif indicatif : ≤ 1,5 ms).
- Acoustique : ΔDER ≤ 0,05 point (ou aucune dégradation par extrait > 0,1) sur le
  corpus de validation ; JER stable.
- Système : `STEP3_REQUIRE_EDGETPU=1` passe, `validate_startup.py` OK, progression et
  JSON inchangés.

### Fichiers et commandes

- Nouveaux : `scripts/export_yamnet_split.py` (build TF), `workflow_scripts/step3/yamnet_frontend.py`,
  `assets/yamnet_split_edgetpu_compiled.tflite`, tests dédiés.
- Modifiés : `workflow_scripts/step3/run_audio_diarization_tpu.py` (frontend + flag),
  docs pipeline 03, skill `coral-tpu-hybrid-algorithms`, coding standards.
- Banc : `scripts/bench_step3_tpu_der.py`, `scripts/bench_step3_der_eval.py`,
  `scripts/bench_ecapa_providers.py` (pour vérifier que la VAD libère bien le CPU).

### Risques et points de vigilance

- **Parité du frontend** : padding/centrage STFT, filtre mel, offset/échelle log et
  standardisation sont les points les plus sensibles ; comparer d'abord sur des
  waveforms synthétiques et réelles avant de toucher au pipeline.
- **Dérive INT8** : le seuil 0.20 a été calibré sur le modèle actuel ; ne le changer
  qu'après mesure du DER, et documenter.
- **Partitionnement du compilateur** : vérifier le nombre d'ops réellement mappées ;
  un modèle qui ne compile que quelques ops n'apporte rien.
- **Provenance/licence** des poids YAMNet : conserver le modèle actuel comme fallback.
- **ROI** : la VAD ne pèse que 2–7 s par vidéo contre 8–79 s pour ECAPA. Le gain direct
  est faible, mais déporter la VAD libère le CPU pour ECAPA ; mesurer l'effet de bout
  en bout avant de généraliser. Si le gain reste marginal, prioriser l'optimisation
  ECAPA (export/modèle, réduction des embeddings, providers).

---

## 4. Ordre recommandé

1. **Axe 1 d'abord** : il est peu coûteux, réutilise le harnais existant et tranche une
   configuration de production (K=1 vs K=2/adaptatif).
2. **Axe 2 ensuite** : chantier de build plus lourd, à n'engager que si le gain de bout
   en bout (VAD + libération CPU pour ECAPA) est mesuré comme significatif.
3. Toute modification acoustique doit passer par le harnais avec une référence K=1
   déterministe et un contrôle par extrait, pas seulement agrégé.

## 5. Définition de fin

- Décision K=2/K=1/adaptatif consignée, avec rapports DER par extrait et mise à jour
  des valeurs par défaut ou de la documentation.
- Si l'axe 2 est poursuivi : modèle compilé validé, flag documenté, parité VAD et DER
  mesurés, fallback et mode strict vérifiés.
- `memory-bank/decisionLog.md`, `docs/workflow/pipeline/03-audio-analysis.md` et
  `requirements-coral_env.txt` alignés sur l'état final.
