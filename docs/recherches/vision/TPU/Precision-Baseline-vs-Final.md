# Comparaison de précision STEP4 (référence vs variante)

- Référence : `scratch/bench_step4_tpu/20261016_175555_baseline/outputs`
- Variante : `scratch/bench_step4_tpu/20261016_184834_final_v2/outputs`
- Vidéos comparées : 10
- Périmètre : visages uniquement

| vidéo | frames | accord présence | appariement | IoU P5 | centro P95 (px) | max RMSE | coeff | bouche RMSE | yeux RMSE | is_speaking | ids |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Andy avoue à Maeva qu’il n’a jamais été amoureux | 4590 | 0.862963 | 0.699653 | 0.547158 | 65.5409 | 0.02221 | mouthDimpleRight | 0.02221 | 0.019887 | 1.0 | 131→133 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | 4608 | 0.802951 | 0.534278 | 0.46557 | 70.936 | 0.019427 | eyeLookInLeft | 0.018598 | 0.019427 | 1.0 | 172→173 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | 5117 | 0.923783 | 0.64187 | 0.529365 | 65.2763 | 0.025222 | mouthFunnel | 0.025222 | 0.019182 | 1.0 | 174→171 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | 4889 | 0.804459 | 0.664298 | 0.481698 | 65.7875 | 0.021678 | eyeLookOutLeft | 0.019849 | 0.021678 | 1.0 | 132→134 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | 5382 | 0.82107 | 0.642902 | 0.479039 | 67.0186 | 0.020614 | eyeLookOutLeft | 0.018574 | 0.020614 | 1.0 | 170→163 |
| Cédric et Charlotte se rapprochent lors du photoshoot | 4824 | 0.821103 | 0.613373 | 0.425905 | 68.884 | 0.020524 | eyeLookOutLeft | 0.019831 | 0.020524 | 1.0 | 176→174 |
| Greg craque car son amitié avec Maeva lui manque | 4950 | 0.814747 | 0.581145 | 0.519993 | 55.3254 | 0.020206 | eyeLookOutLeft | 0.016834 | 0.020206 | 1.0 | 125→124 |
| Julien organise la soirée des problèmes | 4984 | 0.813804 | 0.577556 | 0.431622 | 71.5178 | 0.022144 | eyeLookDownLeft | 0.020679 | 0.022144 | 1.0 | 193→191 |
| Maeva se lâche et décide d’embrasser Andy | 5043 | 0.793179 | 0.489568 | 0.445999 | 75.0563 | 0.024271 | eyeLookOutLeft | 0.018228 | 0.024271 | 1.0 | 284→276 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | 5333 | 0.837802 | 0.643334 | 0.489875 | 66.6321 | 0.019962 | mouthFunnel | 0.019962 | 0.019895 | 1.0 | 177→178 |

## Jitter (RMS de la dérivée seconde)

| vidéo | coefficient | ref | test |
|---|---|---|---|
| Andy avoue à Maeva qu’il n’a jamais été amoureux | jawOpen | 0.001354 | 0.001278 |
| Andy avoue à Maeva qu’il n’a jamais été amoureux | mouthSmileLeft | 0.000191 | 0.000188 |
| Andy avoue à Maeva qu’il n’a jamais été amoureux | mouthSmileRight | 0.004762 | 0.004135 |
| Andy avoue à Maeva qu’il n’a jamais été amoureux | eyeBlinkLeft | 2.4e-05 | 2.1e-05 |
| Andy avoue à Maeva qu’il n’a jamais été amoureux | eyeBlinkRight | 0.0 | 0.0 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | jawOpen | 0.001473 | 0.001131 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | mouthSmileLeft | 0.000199 | 0.000161 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | mouthSmileRight | 0.0051 | 0.004993 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | eyeBlinkLeft | 2.5e-05 | 2.1e-05 |
| Andy avoue à Maeva qu’il veut participer au jeu des problèmes | eyeBlinkRight | 0.0 | 0.0 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | jawOpen | 0.001348 | 0.001134 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | mouthSmileLeft | 0.00019 | 0.000162 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | mouthSmileRight | 0.004833 | 0.004334 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | eyeBlinkLeft | 2.6e-05 | 2.2e-05 |
| Benjy avoue qu’il quitte la famille des Marseillais pour se consacrer à sa famille avec Maddy | eyeBlinkRight | 0.0 | 0.0 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | jawOpen | 0.001296 | 0.001181 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | mouthSmileLeft | 0.000207 | 0.000201 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | mouthSmileRight | 0.005181 | 0.004784 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | eyeBlinkLeft | 2.2e-05 | 1.7e-05 |
| Cynthia et Greg s’expliquent sur la relation passé de Cynthia | eyeBlinkRight | 0.0 | 0.0 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | jawOpen | 0.001195 | 0.001152 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | mouthSmileLeft | 0.000193 | 0.000189 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | mouthSmileRight | 0.004617 | 0.004429 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | eyeBlinkLeft | 2.1e-05 | 1.9e-05 |
| Cynthia pleure en voyant le bonheur qu’elle aurait pu avoir et Greg fait mine de la soutenir mais se sent trahis | eyeBlinkRight | 0.0 | 0.0 |
| Cédric et Charlotte se rapprochent lors du photoshoot | jawOpen | 0.001243 | 0.001147 |
| Cédric et Charlotte se rapprochent lors du photoshoot | mouthSmileLeft | 0.000163 | 0.000146 |
| Cédric et Charlotte se rapprochent lors du photoshoot | mouthSmileRight | 0.004945 | 0.004727 |
| Cédric et Charlotte se rapprochent lors du photoshoot | eyeBlinkLeft | 2.5e-05 | 2.1e-05 |
| Cédric et Charlotte se rapprochent lors du photoshoot | eyeBlinkRight | 0.0 | 0.0 |
| Greg craque car son amitié avec Maeva lui manque | jawOpen | 0.001182 | 0.001179 |
| Greg craque car son amitié avec Maeva lui manque | mouthSmileLeft | 0.000145 | 0.000175 |
| Greg craque car son amitié avec Maeva lui manque | mouthSmileRight | 0.004763 | 0.004616 |
| Greg craque car son amitié avec Maeva lui manque | eyeBlinkLeft | 2.3e-05 | 2.2e-05 |
| Greg craque car son amitié avec Maeva lui manque | eyeBlinkRight | 0.0 | 0.0 |
| Julien organise la soirée des problèmes | jawOpen | 0.001412 | 0.001234 |
| Julien organise la soirée des problèmes | mouthSmileLeft | 0.000177 | 0.000185 |
| Julien organise la soirée des problèmes | mouthSmileRight | 0.005977 | 0.00506 |
| Julien organise la soirée des problèmes | eyeBlinkLeft | 2.4e-05 | 2.2e-05 |
| Julien organise la soirée des problèmes | eyeBlinkRight | 0.0 | 0.0 |
| Maeva se lâche et décide d’embrasser Andy | jawOpen | 0.001442 | 0.001452 |
| Maeva se lâche et décide d’embrasser Andy | mouthSmileLeft | 0.000211 | 0.000212 |
| Maeva se lâche et décide d’embrasser Andy | mouthSmileRight | 0.005325 | 0.005401 |
| Maeva se lâche et décide d’embrasser Andy | eyeBlinkLeft | 2.4e-05 | 2.3e-05 |
| Maeva se lâche et décide d’embrasser Andy | eyeBlinkRight | 0.0 | 0.0 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | jawOpen | 0.001206 | 0.001065 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | mouthSmileLeft | 0.00018 | 0.00016 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | mouthSmileRight | 0.005146 | 0.00449 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | eyeBlinkLeft | 2.1e-05 | 1.9e-05 |
| Manon veut faire comprendre à Greg que Cynthia et lui sont dans la même situation | eyeBlinkRight | 0.0 | 0.0 |

## Verdict

**ÉCHEC** — 6 seuil(s) franchi(s) :
- accord de présence de visage 0.7932 < 0.999
- IoU P5 0.4259 < 0.99
- dérive centroïde P95 75.056 px > 3.0 px
- appariement d'objets 0.4896 < 0.99
- Greg craque car son amitié avec Maeva lui manque: jitter mouthSmileLeft 0.000175 > 0.000145 (+2%)
- Julien organise la soirée des problèmes: jitter mouthSmileLeft 0.000185 > 0.000177 (+2%)
