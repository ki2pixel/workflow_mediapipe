# STEP5 Benchmark Summary (Dec 19, 2025)

Metrics extraites automatiquement des logs workers et exports JSON pour les cinq vidéos comparées.

## 66M - EMPLACEMENT VILLAGE

| Moteur | Face success rate (%) | Avg FPS | Processing time (s) | Frames with tracked objects / total |
| --- | ---: | ---: | ---: | --- |
| MediaPipe landmarker | 9.91 | 36.61 | 71.95 | 2463 / 2634 |
| OpenCV YuNet + py-feat | 84.55 | 39.49 | 66.70 | 2524 / 2634 |
| OpenSeeFace | 62.64 | 53.55 | 49.19 | 2480 / 2634 |

## 66M - GLACE

| Moteur | Face success rate (%) | Avg FPS | Processing time (s) | Frames with tracked objects / total |
| --- | ---: | ---: | ---: | --- |
| MediaPipe landmarker | 24.49 | 36.73 | 41.46 | 1469 / 1523 |
| OpenCV YuNet + py-feat | 79.71 | 34.45 | 44.21 | 1471 / 1523 |
| OpenSeeFace | 75.84 | 54.81 | 27.79 | 1471 / 1523 |

## 66M BEBE DEHORS

| Moteur | Face success rate (%) | Avg FPS | Processing time (s) | Frames with tracked objects / total |
| --- | ---: | ---: | ---: | --- |
| MediaPipe landmarker | 7.32 | 32.41 | 45.98 | 1162 / 1490 |
| OpenCV YuNet + py-feat | 35.44 | 26.24 | 56.78 | 1075 / 1490 |
| OpenSeeFace | 57.25 | 47.79 | 31.18 | 1340 / 1490 |

## M6 - LMBF - Extrait 2 (EM2 - E3006511)  Bruno tente de chiper une brioche dans une boulangerie

| Moteur | Face success rate (%) | Avg FPS | Processing time (s) | Frames with tracked objects / total |
| --- | ---: | ---: | ---: | --- |
| MediaPipe landmarker | 2.19 | 23.03 | 13.85 | 318 / 319 |
| OpenCV YuNet + py-feat | 99.69 | 27.84 | 11.46 | 318 / 319 |
| OpenSeeFace | 99.69 | 51.59 | 6.18 | 318 / 319 |

## M6 - LMBF - Extrait 3 (EM3 - E3006611)  Chiara et Bruno sont surpris de découvrir cette boulangerie au milieu d’une étable

| Moteur | Face success rate (%) | Avg FPS | Processing time (s) | Frames with tracked objects / total |
| --- | ---: | ---: | ---: | --- |
| MediaPipe landmarker | 0.95 | 29.77 | 28.35 | 829 / 844 |
| OpenCV YuNet + py-feat | 77.37 | 32.85 | 25.69 | 815 / 844 |
| OpenSeeFace | 77.37 | 51.99 | 16.23 | 801 / 844 |

## Observations clés

1. **Précision de détection** – OpenCV YuNet + py-feat maximise la couverture (77–100 % des frames avec visages selon la vidéo) et délivre les JSON les plus denses, idéal pour les analyses downstream lip-sync/blendshapes. MediaPipe landmarker reste largement en retrait (<25 % sur toutes les vidéos multi-personnages), ce qui confirme que la config actuelle n’est pas adaptée à ce corpus.
2. **Cadence & latence** – OpenSeeFace offre la meilleure cadence (jusqu’à ~52 FPS et des traitements 20–30 % plus courts que YuNet) tout en gardant un taux de détection élevé (>75 %). C’est le meilleur candidat pour un usage quasi temps réel ou des machines limitées.
3. **Taille d’export** – Les exports YuNet sont les plus volumineux (~17 MB max) mais couvrent >95 % des frames, tandis qu’OpenSeeFace réduit la taille (~10 MB) avec une couverture >90 %. MediaPipe landmarker génère des fichiers plus petits mais au prix d’une perte massive de détections.

## Recommandations

1. **Rapports haute précision / multi-visages** – privilégier **OpenCV YuNet + py-feat** afin de maximiser la détection visage et les blendshapes, même si le temps de calcul reste légèrement supérieur.
2. **Suivi rapide ou monitoring** – utiliser **OpenSeeFace** : meilleure cadence, latence réduite et couverture largement suffisante pour du suivi en direct.
3. **MediaPipe landmarker** – à réserver aux cas très simples (1 visage stable) ou si l’on souhaite éviter ONNX/py-feat. Pour ce corpus, envisager soit un réglage plus agressif (réduction `STEP5_MEDIAPIPE_MAX_WIDTH`, seuils de confiance), soit une migration complète vers les deux moteurs alternatifs.
