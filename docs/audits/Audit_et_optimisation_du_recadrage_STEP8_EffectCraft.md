## 1. Matrice de cohérence des artefacts consommés (STEP1 → STEP8)

Le pipeline génère une chaîne d'artefacts normalisés à **25 fps** (`MP4 / H.264 / yuv420p`) dès la `STEP1`. Pourtant, `MediaSolution.jsx` (`STEP8`) n'exploite qu'une fraction des métadonnées produites par les étapes amont (`STEP2` à `STEP6`).

| Artefact & Étape | Données produites en amont | Consommation actuelle dans `MediaSolution.jsx` (STEP8) | Données perdues ou sous-exploitées | Impact en post-production |
| --- | --- | --- | --- | --- |
| **`.csv`**<br>

<br>*(STEP2 : TransNetV2 / MobileNetV2 TPU)*<br> | Index de frames de début/fin de scène, timecodes `HH:MM:SS.mmm`, probabilités de transition.

 | **Exploité** : Découpage temporel des calques avec tolérance d'accroche (*snap* de $1.5\text{ frame}$). | Pas de distinction entre coupe franche (*hard cut*) et fondu lent issue des scores de transition. | Risque de saut brutal d'ancrage X au milieu d'un fondu enchaîné. |
| **`*_audio.json`**<br>

<br>*(STEP3 : Lemonfox / Pyannote / YAMNet+ECAPA)*<br> | Segments VAD (`is_speech_present`), diarisation (`active_speaker_labels`, `SPEAKER_XX`), `speaker_embeddings`.

 | **Chargé mais ignoré** : `loadVideoTrackingData()` peuple `audioByFrame` et normalise les labels locuteurs, mais ne les transmet jamais au score. | Corrélation voix/visage actif, détection des silences, dominance d'un locuteur sur la durée du cut. | En plan à deux personnes (interview), cadrage arbitraire sur la personne muette. |
| **`*_tracking.json`**<br>

<br>*(STEP4 Tracking + STEP5 Reducer)*<br> | Pistes d'objets (`face_landmarker`, `object_detector`), boîtes englobantes $(x, y, w, h)$, centroïdes $(c_x, c_y)$, scores de confiance, `tracking_analytics`, `expression_summary` (`jawOpen`), `temporal_alignment`.

 | **Partiellement exploité** : Utilisé en fallback si `*_ae.json` est absent. Seuls la présence, la confiance moyenne, le centre $X$ et l'aire moyenne de la bbox sont lus. | Source du détecteur (`face` vs `person`), coordonnée verticale $Y$, ouverture de bouche (`jawOpen` / blendshapes), alignement temporel.

 | Confusion entre un corps entier au premier plan et un visage en arrière-plan ; absence de cadrage vertical. |
| **`*_ae.json`**<br>

<br>*(STEP6 : `preprocess_ae_json.py`)*<br> | Indexation frame-par-frame compacte, croisement audio/vidéo pré-qualifié, analytiques de stabilité.

 | **Prioritaire** (`findTrackingJsonForVideo()` cherche `_ae.json` → `_tracking.json` → `.json`), mais **recalculé de zéro** de manière dégradée par le JSX. | Toute la hiérarchie multi-critères (`best_audio_face` > `best_audio_person` > `best_face` > `best_person`) calculée ou préparée en `STEP6`. | Double travail inutile et régression qualitative majeure entre l'analyse Python et le rendu EffectCraft. |

---

## 2. Audit comparatif des logiques de sélection et de cadrage

### 2.1 Comparaison algorithmique : `_analyze_layer` (STEP6 Python) vs `pickBestObjectInRange` (STEP8 JSX)

Le décalage principal du pipeline réside dans la divergence entre l'intelligence analytique de `workflow_scripts/step6/preprocess_ae_json.py` et l'heuristique simplifiée de `scripts/MediaSolution-EC/MediaSolution.jsx`.

* **Modèle de sélection STEP6 (`preprocess_ae_json.py`)** :
Établit une **hiérarchie lexicographique stricte** en 5 paliers :

$$\text{Priorité}_{\text{STEP6}} : \texttt{best\_audio\_face} \succ \texttt{best\_audio\_person} \succ \texttt{best\_face} \succ \texttt{best\_person} \succ \texttt{best\_fallback}$$



Un objet visuel reçoit un bonus déterminant uniquement s'il coïncide temporellement avec `is_speech_present == True` et la correspondance du locuteur actif (`active_speaker_labels`). De plus, un visage (`face_landmarker`) surclasse systématiquement une silhouette générique (`object_detector` / `person`).
* **Modèle de sélection STEP8 (`MediaSolution.jsx` — `pickBestObjectInRange`)** :
Évalue tous les candidats dans un espace plat via une formule scalaire unique :

$$S_i = N_{\text{frames}}(i) \times \left(1 + \overline{C_i} \times 0.35\right)$$



où $N_{\text{frames}}(i)$ est le nombre de frames d'apparition de l'objet $i$ sur le segment CSV et $\overline{C_i} \in [0, 1]$ sa confiance moyenne. En cas d'égalité (ou d'écart marginal), le tie-break s'effectue sur la **surface moyenne de la boîte englobante** ($\overline{A_i} = \overline{w_i \times h_i}$).

| Critère algorithmique | `preprocess_ae_json.py` (STEP6) | `MediaSolution.jsx` (STEP8) | Verdict d'écart |
| --- | --- | --- | --- |
| **Arbitrage Audio (VAD + Speaker)** | Croisement actif (`is_speech_present` + label locuteur). | **Nul** (`audioByFrame` chargé en RAM mais non branché). | **Critique** : Perte totale de la diarisation STEP3.

 |
| **Hiérarchie Visage vs Corps** | Stricte (`face_landmarker` > `person`). | **Aucune** : `face` et `person` ont le même poids. | **Critique** : La bbox `person` gagne systématiquement au tie-break de surface. |
| **Sensibilité aux expressions** | Exploite `expression_summary` (`jawOpen`) si activé en STEP5.

 | Ignoré. | **Moyen** : Utile pour départager deux visages détectés simultanément. |
| **Calcul de la coordonnée cible** | Moyenne pondérée / filtrée sur la piste retenue. | Moyenne arithmétique simple des centres $X$ ($\mu_X$). | **Moyen** : Sensible aux valeurs aberrantes (*outliers*) en début/fin de cut. |
| **Sécurité de bordure (Clamp)** | Déléguée ou bornée. | `clampAnchorToCoverage()` avec échelle **180 %** et parent Null (`createSegmentNull`). | **Conforme côté JSX** : Robuste contre les bandes noires latérales. |

### 2.2 Conséquences concrètes en situation réelle de post-production

1. **Cas d'une interview ou d'un dialogue (deux personnes à l'écran)** :
* *Phénomène* : Les deux interlocuteurs $A$ et $B$ sont présents sur 100 % des frames du segment ($N_{\text{frames}}(A) = N_{\text{frames}}(B)$). Leurs scores de confiance MediaPipe/InsightFace sont proches ($\approx 0.88$ vs $0.91$).


* *Résultat STEP8* : Le script sélectionne systématiquement celui dont le détecteur affiche $+0.03$ de confiance ou une boîte légèrement plus large, même s'il écoute en silence pendant 15 secondes. Sur une série de cuts alternés, la caméra virtuelle reste figée sur le mauvais invité ou oscille aléatoirement.


2. **Cas d'un plan large avec passant ou silhouette au premier plan** :
* *Phénomène* : Un orateur parle en plan moyen (visage détecté par `face_landmarker`, surface bbox $\approx 150 \times 150\text{ px}$). Une personne de dos ou un objet `person` entre dans le champ (détecté par `object_detector`, surface bbox $\approx 500 \times 900\text{ px}$).
* *Résultat STEP8* : Comme `object_detector` a souvent une confiance élevée sur la classe `person` et une surface $30\times$ supérieure au visage, `pickBestObjectInRange` verrouille le cadrage sur le passant ou sur le torse, éjectant le visage de l'orateur hors du cadre 9:16.


3. **Cas d'un mouvement de caméra (panoramique) ou déplacement du sujet (`spread > 200 px`)** :
* *Phénomène* : Le sujet marche de $X = 400\text{ px}$ à $X = 1400\text{ px}$ sur un plan de 4 secondes ($\text{spread} = 1000\text{ px}$).
* *Résultat STEP8* : Le centrage statique place l'ancre sur la moyenne $\mu_X = 900\text{ px}$. Le sujet entre par le bord gauche à $t_0$, traverse l'écran, et sort par le bord droit à $t_{\text{fin}}$ : il n'est correctement cadré qu'au milieu du segment. De plus, si la piste retenue est de type `person` et non `face`, la condition d'alerte `LABEL_HIGH_SPREAD` (qui vérifie si la piste est un visage) peut ne même pas déclencher le label orange (12).



---

## 3. Évaluation ergonomique & métier (Monteur / Motion Designer)

### 3.1 Pertinence du centrage statique en X par segment CSV

* **La règle des 80/20 en montage vertical (Reels / TikTok / Shorts)** :
Sur des formats parlés (plateaux TV, podcasts, interviews), **80 à 85 % des plans sont statiques** entre deux cuts CSV. Un centrage statique par cut (via l'objet nul parent généré par `createSegmentNull`) est **idéal ergonomiquement** : il évite l'effet « caméra de surveillance flottante » (mal de mer visuel provoqué par un suivi continu mal amorti) et laisse au monteur une timeline propre avec une seule valeur de position à corriger si nécessaire.
* **Les 15 à 20 % d'exceptions (mouvements significatifs)** :
Lorsque l'écart-type ou l'amplitude ($\text{spread} = X_{\max} - X_{\min}$) dépasse **200 px à 250 px** sur un segment de plus de $1.5\text{ s}$, le centrage fixe échoue. Toutefois, générer une clé par frame (25 clés/seconde) est **indésirable** : cela pollue la timeline EffectCraft/After Effects et rend toute retouche manuelle impossible sans tout supprimer. Le monteur a besoin au maximum de **2 clés linéaires/Bézier** (début et fin de mouvement significatif) sur l'objet Null du segment.

### 3.2 Intérêt d'une gestion de l'axe Y (Hauteur des yeux / Règle des tiers)

* Actuellement, `MediaSolution.jsx` fige l'ancre en haut-centre et la position à $[W/2, 0]$ avec une échelle de **180 %**.
* En partant d'une source 16:9 ($1920 \times 1080$) mise à l'échelle à $180\text{ \%}$ dans une composition 9:16 ($1080 \times 1920$), la hauteur effective du calque vidéo est :

$$H_{\text{eff}} = 1080 \times 1.80 = 1944\text{ px} \quad (\text{soit une marge verticale totale de } 1944 - 1920 = 24\text{ px})$$


* **Conclusion géométrique importante** : À l'échelle **180 %**, la réserve verticale sans bandes noires n'est que de **$24\text{ px}$** ($\pm 12\text{ px}$). Il est mathématiquement impossible de effectuer un grand recadrage vertical sans créer de bandes noires en haut ou en bas, sauf si le script augmente dynamiquement l'échelle (ex. à 200–220 %) lorsque le visage est trop bas.
* **Recommandation métier sur Y** : Ne pas modifier l'échelle par défaut de 180 % (pour préserver le piqué d'image), mais utiliser la marge de $24\text{ px}$ via un `clampAnchorY` doux vers la ligne des tiers supérieure ($Y_{\text{cible}} \approx 640\text{ px}$ dans le repère 1920p) uniquement lorsque `scale > 177.8 %`, et signaler en log si un visage se trouve dans le tiers inférieur de l'image source ($Y_{\text{source}} > 750\text{ px}$, risquant d'être masqué par les sous-titres en 9:16).

### 3.3 Clarté du feedback monteur (Labels & Logs)

* Le système actuel à 2 états (`LABEL_STABLE` = Jaune/3, `LABEL_HIGH_SPREAD` = Orange/12 si $\text{spread} > 200\text{ px}$ sur un visage) est insuffisant car il masque les cas où le cadrage est **stable mais incertain** (ex. aucun visage trouvé, repli sur une silhouette `person`, ou absence totale de détection avec cadrage par défaut au centre).
* Étendre la taxonomie visuelle à **4 labels de couleur** permet au monteur de repérer en une seconde les plans à vérifier sur sa timeline :
1. **Vert / Jaune (`LABEL_AUDIO_FACE` = 3)** : Visage parlant confirmé et stable ($\text{spread} \le 200\text{ px}$). Aucune action requise.
2. **Cyan / Bleu (`LABEL_SILENT_OR_BODY` = 8)** : Recentrage sur un visage muet ou sur un corps (`person`) sans visage. Vérification visuelle rapide conseillée.
3. **Orange (`LABEL_HIGH_SPREAD` = 12)** : Sujet identifié mais forte amplitude horizontale ($\text{spread} > 200\text{ px}$). Vérifier si un pano (2 keyframes) est souhaité.
4. **Rouge / Violet (`LABEL_FALLBACK_CENTER` = 1)** : Aucune piste fiable détectée sur le cut (cadrage centré par défaut). Retouche manuelle obligatoire.



---

## 4. Propositions d'améliorations et arbitrages d'architecture

Conformément à `codingstandards.md`, le backend Python (`STEP6`) doit utiliser `ijson` en streaming $O(1)$ RAM, tandis que `MediaSolution.jsx` (`STEP8`) doit rester en **JavaScript ES3 strict** (`var`, boucles `for`, pas de dépendances externes, rapidité d'exécution maximale).

### Option A : Enrichissement en amont dans `STEP6` (`preprocess_ae_json.py`)

Faire calculer ou consolider les métadonnées de sélection directement dans `*_ae.json` lors de la `STEP6`.

* **Principe** : Puisque `preprocess_ae_json.py` possède déjà la logique `_analyze_layer` et croise le tracking avec `*_audio.json`, il peut injecter dans chaque entrée frame de `*_ae.json` (et/ou dans un dictionnaire pré-agrégé `segment_recommendations` si le `.csv` STEP2 est présent dans le dossier projet) le `recommended_object_id` et la catégorie de priorité (`1: best_audio_face` à `5: fallback`).


* **Avantage** : Décharge `MediaSolution.jsx` des croisements matriciels lourds ; garantit 100 % de parité entre les tests unitaires Python (`test_step6_ae_analyzer.py`) et le rendu EffectCraft.



### Option B : Raffinement interne de `MediaSolution.jsx` (ES3 pur)

Même avec l'Option A, `MediaSolution.jsx` doit pouvoir fonctionner sur des fichiers `*_tracking.json` bruts (fallback prévu par `findTrackingJsonForVideo()`) ou lorsque le monteur ajuste les cuts. Il est donc indispensable de corriger `pickBestObjectInRange` directement en JS ES3.

#### Code corrigé pour `MediaSolution.jsx` (Conforme ES3 & `codingstandards.md`)

```javascript
// Hiérarchie alignée sur STEP6 (preprocess_ae_json.py) :
// 4 = best_audio_face, 3 = best_audio_person, 2 = best_face, 1 = best_person
function isFaceCandidate(obj) {
    var src = (obj.source || obj.label || "").toLowerCase();
    return src.indexOf("face") !== -1;
}

function isObjectSpeakingInFrame(obj, audioFrame) {
    if (!audioFrame || !audioFrame.is_speech_present) {
        return false;
    }
    if (obj.is_speaking === true || obj.audio_match === true) {
        return true;
    }
    var activeSpeakers = audioFrame.active_speakers || audioFrame.video_speakers || [];
    if (obj.speaker_label && activeSpeakers.length > 0) {
        for (var s = 0; s < activeSpeakers.length; s++) {
            if (activeSpeakers[s] === obj.speaker_label) {
                return true;
            }
        }
    }
    // Si la parole est active sur la frame et qu'un visage a une ouverture de bouche significative
    if (isFaceCandidate(obj) && obj.jawOpen && obj.jawOpen > 0.12) {
        return true;
    }
    return false;
}

function pickBestObjectInRange(trackingData, startFrame, endFrame) {
    var statsById = {};
    var framesByIndex = trackingData.framesByIndex || {};
    var audioByFrame = trackingData.audioByFrame || {};
    var totalSegmentFrames = Math.max(1, endFrame - startFrame + 1);

    for (var f = startFrame; f <= endFrame; f++) {
        var frameObjs = framesByIndex[f];
        if (!frameObjs || !frameObjs.length) {
            continue;
        }
        var audioFrame = audioByFrame[f] || null;
        var speechActiveOnFrame = Boolean(audioFrame && audioFrame.is_speech_present);

        for (var i = 0; i < frameObjs.length; i++) {
            var obj = frameObjs[i];
            var id = String(obj.id !== undefined ? obj.id : obj.object_id);
            if (!statsById[id]) {
                statsById[id] = {
                    id: id,
                    isFace: isFaceCandidate(obj),
                    presence: 0,
                    speechFrames: 0,
                    confSum: 0,
                    areaSum: 0,
                    xValues: [],
                    minX: Infinity,
                    maxX: -Infinity
                };
            }
            var st = statsById[id];
            if (isFaceCandidate(obj)) {
                st.isFace = true;
            }
            st.presence += 1;
            st.confSum += (typeof obj.confidence === "number") ? obj.confidence : 0.5;
            st.areaSum += (obj.width && obj.height) ? (obj.width * obj.height) : 0;

            if (typeof obj.center_x === "number") {
                st.xValues.push(obj.center_x);
                if (obj.center_x < st.minX) st.minX = obj.center_x;
                if (obj.center_x > st.maxX) st.maxX = obj.center_x;
            }

            if (isObjectSpeakingInFrame(obj, audioFrame) || (speechActiveOnFrame && frameObjs.length === 1)) {
                st.speechFrames += 1;
            }
        }
    }

    var bestCandidate = null;
    for (var key in statsById) {
        if (!statsById.hasOwnProperty(key)) continue;
        var cand = statsById[key];
        // Rejeter les pistes fantômes (< 10% du segment et < 3 frames)
        if (cand.presence < 3 && (cand.presence / totalSegmentFrames) < 0.10) {
            continue;
        }

        var avgConf = cand.confSum / cand.presence;
        var speechRatio = cand.speechFrames / cand.presence;
        var hasAudioSupport = (cand.speechFrames >= 3) || (speechRatio >= 0.20);

        // Palier hiérarchique strict (STEP6 parity) :
        // Tier 4: Audio + Face | Tier 3: Audio + Person | Tier 2: Face | Tier 1: Person
        if (hasAudioSupport && cand.isFace) {
            cand.tier = 4;
        } else if (hasAudioSupport && !cand.isFace) {
            cand.tier = 3;
        } else if (cand.isFace) {
            cand.tier = 2;
        } else {
            cand.tier = 1;
        }

        // Score intra-palier : présence + bonus confiance + bonus ratio parole
        cand.score = cand.presence * (1.0 + (avgConf * 0.35) + (speechRatio * 0.50));
        cand.avgArea = cand.areaSum / cand.presence;
        cand.spreadX = (cand.maxX > cand.minX) ? (cand.maxX - cand.minX) : 0;

        if (!bestCandidate) {
            bestCandidate = cand;
        } else if (cand.tier > bestCandidate.tier) {
            bestCandidate = cand;
        } else if (cand.tier === bestCandidate.tier) {
            if (cand.score > bestCandidate.score) {
                bestCandidate = cand;
            } else if (Math.abs(cand.score - bestCandidate.score) < 1e-4 && cand.avgArea > bestCandidate.avgArea) {
                bestCandidate = cand;
            }
        }
    }

    return bestCandidate;
}

```

### Option C : Assistance au recadrage dynamique amorti (2 Keyframes sur `SegmentNull`)

Pour traiter les segments où $\text{spread} > 200\text{ px}$ sans imposer un keyframing image par image destructif :

* **Détection de dérive directionnelle vs oscillation** :
Diviser les coordonnées $X$ du segment en deux moitiés temporelles : calculer la moyenne du premier tiers ($\mu_{X,\text{début}}$) et du dernier tiers ($\mu_{X,\text{fin}}$).
* Si $\vert{}\mu_{X,\text{fin}} - \mu_{X,\text{début}}\vert{} > 180\text{ px}$ (vrai déplacement latéral ou panoramique) et si une option `enableSmartPanKeyframes` est activée dans la config du panel : poser **exactement 2 keyframes** sur la propriété `Position` ou `Anchor Point` du Null créé par `createSegmentNull` (aux frames `startFrame + 3` et `endFrame - 3`, chacune bornée par `clampAnchorToCoverage`).
* Si $\vert{}\mu_{X,\text{fin}} - \mu_{X,\text{début}}\vert{} \le 180\text{ px}$ malgré un $\text{spread} > 200\text{ px}$ (il s'agit d'un aller-retour rapide ou d'un tremblement de détection) : conserver **1 seule valeur statique** (en utilisant la **médiane** ou la **moyenne tronquée à 10 %** plutôt que la moyenne arithmétique pour ignorer les pics) et appliquer `LABEL_HIGH_SPREAD` (Orange/12).



---

## 5. Synthèse : Bilan des Forces/Faiblesses, Risques et Roadmap

### 5.1 Tableau comparatif de l'architecture actuelle (`STEP6` + `STEP8`)

| Dimension | Forces actuelles | Faiblesses actuelles |
| --- | --- | --- |
| **Architecture & Isolation** | Exécution autonome de `MediaSolution.jsx` en JS pur sans dépendance Node/CEP ; support CLI headless (`effectcraft-cli`) en `STEP8`.

 | Duplication divergente de la logique de sélection entre `preprocess_ae_json.py` (`STEP6`) et `MediaSolution.jsx` (`STEP8`).

 |
| **Pertinence du choix de sujet** | Découpage temporel fiable calé sur le CSV (`STEP2`) avec snap $1.5\text{ frame}$. | `audioByFrame` chargé mais non utilisé ; aucune priorité de `face_landmarker` sur `object_detector` (`person`). |
| **Stabilité géométrique** | `createSegmentNull` offre une hiérarchie propre pour le monteur ; `clampAnchorToCoverage` empêche strictement les bords noirs à 180 %. | Moyenne arithmétique sensible aux *outliers* aux bords des cuts ; élargissement (`spread > 200 px`) subi sans amortissement ni médiane. |
| **Observabilité Monteur** | Marquage couleur existant (`LABEL_STABLE` vs `LABEL_HIGH_SPREAD`) et logs de batch (`MS_BATCH_PROGRESS`).

 | `LABEL_HIGH_SPREAD` restreint aux visages ; absence de label spécifique pour les cadrages en mode dégradé (corps seul ou fallback centré). |

### 5.2 Matrice des risques de faux cadrage en production

| Risque identifié | Cause racine dans `MediaSolution.jsx` | Fréquence en prod | Gravité métier | Correctif cible |
| --- | --- | --- | --- | --- |
| **Cadrage sur l'interlocuteur muet** | Ignorance de `audioByFrame` (`is_speech_present`, `active_speakers`) dans `pickBestObjectInRange`. | **Très élevée** (tout dialogue/interview) | **Critique** | Activer le palier `Tier 4 (best_audio_face)` dans `pickBestObjectInRange` (Option B) + pré-calcul STEP6 (Option A). |
| **Verrouillage sur un torse ou passant** | Égalité de traitement `face_landmarker` / `object_detector` + tie-break sur la surface de la bbox. | **Élevée** (plans larges / B-roll) | **Critique** | Séparer strictement les paliers Visage (`Tier 4/2`) des paliers Personne (`Tier 3/1`). |
| **Décalage d'ancre dû à une fausse détection sur 1-2 frames** | Moyenne arithmétique simple sur tous les points $X$ de la piste, sans seuil minimal de présence ni filtrage des extrêmes. | **Moyenne** | **Moyenne** | Imposer un seuil de présence ($\ge 3\text{ frames}$ ou $10\text{ \%}$ du cut) et calculer la **moyenne tronquée (10–90 %)** ou la **médiane** en $X$. |
| **Sujet sortant du cadre en cours de plan** | Cadrage statique unique sur un déplacement continu ($\text{spread} > 200\text{ px}$). | **Moyenne** (plans en marche / panos) | **Haute** | Détecter le delta $\vert{}\mu_{\text{fin}} - \mu_{\text{début}}\vert{} > 180\text{ px}$ pour poser 2 clés amorties (Option C) et étendre `LABEL_HIGH_SPREAD` aux pistes `person`. |

### 5.3 Roadmap d'implémentation priorisée (Impact Métier / Complexité)

1. **Priorité P0 — Quick Win à fort impact (Complexité : Faible | Impact : Immédiat, -70 % de retouches manuelles)**
* **Action** : Mettre à jour `pickBestObjectInRange()` dans `scripts/MediaSolution-EC/MediaSolution.jsx` (Option B) pour :
1. Brancher `audioByFrame` déjà présent en mémoire dans `loadVideoTrackingData()`.
2. Instaurer la hiérarchie à 4 paliers (`best_audio_face` > `best_audio_person` > `best_face` > `best_person`).
3. Remplacer la moyenne arithmétique de `center_x` par une **moyenne tronquée** (excluant les 10 % de valeurs extrêmes sur les segments $> 10\text{ frames}$) avant l'appel à `clampAnchorToCoverage()`.
4. Étendre `LABEL_HIGH_SPREAD` (Orange/12) à tout objet suivi (visage ou corps) ayant un $\text{spread} > 200\text{ px}$, et ajouter un label distinct pour les segments sans suivi (`LABEL_FALLBACK`).


* **Tests** : Ajouter les cas correspondants dans `tests/unit/test_step8_mediasolution.py` et `tests/unit/test_recentering_anchor_clamp.py`.




2. **Priorité P1 — Alignement architectural STEP6 → STEP8 (Complexité : Moyenne | Impact : Élevé)**
* **Action** : Enrichir `workflow_scripts/step6/preprocess_ae_json.py` (Option A) pour exporter directement dans `*_ae.json` les indicateurs de correspondance locuteur (`is_speaking`, `tier`) et un bloc optionnel `segment_recommendations` indexé sur les cuts du `.csv` de `STEP2`.


* **Bénéfice** : Temps d'exécution de `STEP8` réduit au minimum (lecture directe O(1) par segment dans `MediaSolution.jsx`) et source unique de vérité algorithmique en Python testée par `tests/unit/test_step6_ae_analyzer.py`.




3. **Priorité P2 — Recadrage dynamique amorti à 2 clés & garde-fou vertical Y (Complexité : Moyenne | Impact : Moyen)**
* **Action** : Implémenter l'Option C dans `MediaSolution.jsx` (2 keyframes linéaires bornées par `clampAnchorToCoverage` sur le Null généré par `createSegmentNull` lorsque $\vert{}\mu_{X,\text{fin}} - \mu_{X,\text{début}}\vert{} > 180\text{ px}$, activable par flag de configuration dans `STEP8_PANEL_CONFIG`), ainsi qu'un avertissement dans les logs `STEP8` lorsqu'un visage parlé est détecté trop bas en Y (zone des sous-titres).