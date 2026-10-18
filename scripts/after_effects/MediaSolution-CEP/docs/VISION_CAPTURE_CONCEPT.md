# Concept : extension CEP de capture vision (webcam, face mesh, mains)

**TL;DR** : un panel CEP qui capture le flux webcam via un démon Python (jamais via le navigateur embarqué, qui n'offre pas `getUserMedia`), détecte visage et mains avec MediaPipe, affiche un overlay en direct, et enregistre des séquences vidéo accompagnées de landmarks (JSON) et de tracés vectoriels (SVG). Les coordonnées sont réinjectées dans After Effects via le relais ExtendScript habituel. Statut : faisabilité confirmée par deux rapports de recherche complémentaires (voir [Références](#références-des-recherches)), non planifié.

## Pourquoi ce panel

Le workflow MediaPipe v4.1 produit des fichiers de tracking à partir de séquences vidéo, mais la capture de ces séquences est un chantier séparé, tournant sur Ubuntu. L'idée ici est d'embarquer une partie de cette chaîne dans AE, côté Windows : se filmer avec une webcam, voir le visage ou la main suivi en direct dans le panel, et enregistrer une séquence avec ses données de tracking pour la réutiliser ensuite en production (effets, animation vectorielle, mo-cap low-cost de gestes).

Deux usages distincts :

1. **Live** : préview caméra + overlay du maillage en direct, pour se visualiser pendant la prise.
2. **Post-enregistrement** : détection complète, calcul des landmarks, exports JSON/SVG, réimport dans AE. Rien de tout cela n'a besoin d'être temps réel.

## Faisabilité technique

### Pas de capture caméra dans le CEP

Le navigateur embarqué (CEF) d'AE ne permet pas de façon fiable `getUserMedia`. La capture ne peut pas se faire côté panel. Le rapport *Capture Webcam* évalue pourtant l'option HTML5 native, mais il identifie le vrai goulot d'étranglement ailleurs : même avec un flux fonctionnel dans le panel, le transfert des pixels vers la timeline (RAM disk, WebSocket, UXP hybrid) est insoluble à ce niveau. Les deux rapports convergent sur le même verdict : le démon Python découplé. C'est lui qui capture (OpenCV), détecte (MediaPipe face mesh, hands) et transmet au panel. Le panel ne fait qu'afficher.

### Limite confirmée : pas de caméra live dans la timeline

AE est un moteur de rendu *pull-based* : si la tête de lecture est en pause, l'hôte n'émet aucun ordre de rendu, donc un calque ne peut pas afficher un flux caméra continu sans plugin d'effet C++ natif (récepteur Spout/Syphon/NDI, *Idle Hooks* AEGP, mémoire partagée — ~500 Mo/s en 1080p60, non transportable par socket). C'est un chantier SDK C++ à part entière, hors périmètre de ce concept. Notre usage reste compatible avec cette limite : le live se joue **dans le panel**, l'enregistrement se fait **hors AE**, et la réinjection est **post-enregistrement** par keyframes.

### Trois flux, un démon dédié

```
Caméra ──> [ vision_daemon.py ]
              │ 1. Préview → HTTP MJPEG (localhost) → <img> du panel
              │ 2. Landmarks → pipe nommé maison → canvas overlay en direct
              │ 3. Enregistrement → .mp4 + landmarks JSON horodatés
              └──> [ AE ]  réinjection via le relais ExtendScript
```

- **Préview** : flux MJPEG sur `http://127.0.0.1:<port>/video`, CORS ouvert, affiché dans une `<img>`. Même logique localhost que le pont actuel. Serveur asynchrone **aiohttp** (`multipart/x-mixed-replace`), qui ne bloque pas la boucle d'acquisition.
- **Overlay live** : les landmarks arrivent par le pipe nommé en JSON ; le panel dessine le maillage sur un canvas superposé à la vidéo. Zéro dépendance navigateur.
- **Enregistrement** : `VideoWriter` (mp4) + fichier de landmarks écrit en parallèle.

Le démon est séparé de `bridge_daemon.py` : la capture tourne en boucle permanente, alors que le pipe batch est mono-connection dans son thread principal. Ne pas mélanger les deux.

## Décisions de conception actées

### Découplage live / post-enregistrement

Seule la préview exige de la performance. La capture pendant l'enregistrement est un simple `VideoWriter` sans détection ; l'extraction des landmarks est un job offline qui peut durer ce qu'il faut, avec progression affichée dans le panel. Conséquence directe : le CPU suffit sur Windows, le GPU n'est pas un prérequis.

Mesures de performance connues (CPU x86_64, 8 cœurs, API Tasks) :

- FaceLandmarker seul : 45–60 FPS.
- Visage + deux mains dans le même thread : 18–25 FPS.
- → exécuter la détection faciale et la détection gestuelle dans **deux threads séparés** (`ThreadPoolExecutor`) pour garder ~60 FPS.

### Format de tracking agnostique moteur

Le format du workflow v4.1 est spécifique à ses moteurs et à ses usages (cuts, auto-recentrage du point d'ancrage). Ici les enjeux diffèrent : pas de cuts, esthétique vectorielle. Le format de ce panel est donc neuf et minimal : `frames → landmarks (x, y, z normalisés, visibilité)` + métadonnées (fps, résolution, moteur, version du modèle) + table de connexions (topologie).

Point clé : la topologie n'est pas la même selon le moteur. FaceLandmarker produit **478 points** (468 faciaux + topologie des iris), HandLandmarker **21 points 3D par main**, InsightFace 106/68 points (plus un dense 3D), BlazeFace seulement une boîte englobante. Le fichier stocke donc points + connexions + moteur, et la génération des paths SVG se fait par moteur. L'extension reste compatible avec les trois, et avec les futurs.

Réutiliser les patterns de résilience existants : écriture atomique (temp + rename), matching de nom à la `_resolve_tracking_path()` (normalisation NFD/ASCII, distance de Levenshtein), JSON validé avant usage.

### Lissage et décimation

Les landmarks bruts de MediaPipe scintillent (jitter). Appliquer un **One Euro Filter** par axe côté démon avant export — le même filtre sert à l'overlay live et au JSON final.

Pour l'injection dans AE, deux réductions de données en amont (jamais 468 points × 30 fps en brut) :

- **Spatiale** : simplification Ramer-Douglas-Peucker sur chaque path pour éliminer les points colinéaires.
- **Temporelle** : keyframes posées seulement quand le mouvement dépasse un seuil ; AE interpole entre les keyframes.

### Maillage vectoriel dans AE sans dépendre de PyShiftAE ni py_aep

ExtendScript peut animer des paths de masque (`mask.maskPath.setValueAtTime(t, [points, inTangents, outTangents, closed])`). Un solide + masque du visage animé par keyframes donne le maillage vectoriel dans AE, en DOM pur. Le fait que PyShiftAE ou py_aep ne sachent pas toucher les masques n'est donc pas bloquant.

Directives d'injection issues des recherches (le moteur ES3 est lent, le GC inefficace, les boucles de `setValueAtTime()` gèlent l'UI et peuvent faire planter AE) :

- Utiliser **`setValuesAtTimes(timeArray, shapeArray)`** : des centaines de keyframes en une seule requête interne, au lieu d'appels itératifs.
- Envelopper l'injection dans **`app.beginUndoGroup()` / `app.endUndoGroup()`**.
- Ne jamais lire le DOM (ex. `layer.position.value`) dans les boucles : bufferiser toutes les métadonnées en variables locales avant la phase d'écriture.

### Sortie SVG

Chaque frame peut être rendue en SVG contenant un groupe de paths (contour du visage, sourcils, yeux, bouche, mains). Le code de dessin de l'overlay live est réutilisé pour cet export : même rendu, deux sorties. Génération en Python avec **drawsvg** (maintenu activement, préféré à svgwrite).

### Alignement temporel par index de frame

L'horloge est l'index de frame (fps constant, frame 0), pas une horloge murale. Déterministe, et le JSON/SVG se recalent exactement sur la vidéo. Pour le live, les paquets landmarks portent un `frame_id` (et l'horodatage du démon) : le canvas ignore les frames en retard et redessine dès réception du paquet le plus récent, pour éviter la latence cumulative du flux MJPEG (Chromium bufferise les trames quand le thread de rendu ralentit).

### Capture indépendante d'AE

L'enregistrement n'exige aucun projet ouvert. L'import dans AE n'intervient qu'à la réinjection, après la prise.

## Intégration dans l'écosystème existant

La vidéo enregistrée est une séquence comme les autres : elle peut être ré-analysée par les moteurs du workflow Ubuntu (mediapipe, insightface, blazeface sur TPU) qui deviennent de simples fournisseurs de données au même titre que le démon local. Le format étant agnostique moteur, ces moteurs peuvent déposer les JSON sans que l'extension ne voie de différence.

## Dépendances et risques

Stack recommandée par les recherches (Windows 10/11 x64, versions testées entre elles) :

- **Python 3.10.11** (64 bits), le plus stable pour les wheels OpenCV/MediaPipe sous Windows.
- **opencv-python 4.9.0.80**, ouverture webcam avec le backend **DirectShow** (`cv2.CAP_DSHOW`) pour réduire la latence d'initialisation.
- **mediapipe 0.10.14**, via l'API **`mediapipe.tasks.vision`** (FaceLandmarker / HandLandmarker). L'ancienne distribution `mp.solutions.face_mesh` est abandonnée depuis mars 2023 — ne pas repartir dessus.
- **aiohttp 3.9.5** pour le serveur MJPEG asynchrone.
- **drawsvg 2.4.0** pour l'export SVG.
- Modèles .task en ressources (à télécharger au setup, chargement paresseux avec repli `status:"unavailable"` si une dépendance manque, sur le modèle des fallbacks actuels).

### Environnement virtuel dédié

Toutes ces dépendances s'installent dans un **environnement virtuel Python isolé**, dédié au démon vision — pas dans l'interpréteur du démon batch existant ni dans le Python global. Emplacement proposé : `C:\Users\cam-c\Documents\Scripts\` (dossier dédié au concept, par exemple `C:\Users\cam-c\Documents\Scripts\vision_env\`). Bénéfices :

- zéro risque de conflit de versions avec PyShiftBridge, le workflow v4.1 ou tout autre projet utilisant le même interpréteur ;
- versions épinglées dans le venv (Python 3.10.11 + wheels listées ci-dessus), recréable à l'identique via un `requirements.txt` ;
- le démon batch existant reste intact.

Le chemin de l'interpréteur du venv (`Scripts\python.exe`) est configuré dans le panel, sur le modèle de la config Python existante du pont ; si le venv est introuvable, repli `status:"unavailable"` comme pour les dépendances manquantes.

Performance et GPU :

- Les wheels officielles MediaPipe Windows n'ont **pas de GPU delegate** : exécution CPU via XNNPACK. Confirmé par les mesures ci-dessus, le CPU suffit pour notre usage.
- Upgrade GPU propre sous Windows : modèles ONNX (RetinaFace/InsightFace) avec **onnxruntime-gpu 1.18.0 + CUDA 12.x** (inférence < 5 ms). À investiguer comme voie d'évolution, pas comme prérequis.
- Le pipeline v4.1 utilise déjà MediaPipe ; selon l'interpréteur choisi pour le démon, une partie est peut-être déjà installée.

Risques :

- Latence cumulative du `<img>` MJPEG : préview en résolution modeste (ex. 640×480), JPEG qualité 75, `frame_id` sur les landmarks (voir décision ci-dessus).
- Tout reste local : aucune donnée ne quitte la machine.

## Points à affiner en session dédiée

- Topologie par défaut : tessellation complète du visage ou contours principaux (ou les deux, selon l'usage).
- Seuils du One Euro Filter et de la décimation temporelle : à régler sur de vraies prises pour l'esthétique vectorielle.
- Organisation des fichiers : un dossier par prise contenant `*.mp4`, `*_landmarks.json`, `*_frames.svg` nommés pareil, dans l'esprit des dossiers batch existants.
- Moteur sélectionnable par configuration (mediapipe / insightface / autre), sans toucher au reste de l'extension.
- Résolution d'enregistrement choisie en prise (480p live, résolution de prise indépendante).
- Réinjection des données dans AE : null ou solide suiveur (position/rotation), masques animés, éventuellement expressions plutôt que keyframes.

## Références des recherches

- [Architecture CEP Motion Capture AE](./recherches/Architecture_CEP_Motion_Capture%20AE.md) — état de l'art (KeenTools, MCP, Sammie-Roto-2), briques recommandées (aiohttp, MediaPipe Tasks, `setValuesAtTimes`), pièges ES3 et mesures de performance.
- [Capture Webcam After Effects](./recherches/Capture_Webcam_After_Effects.md) — étude des flux temps réel dans AE : getUserMedia, Spout/Syphon/NDI, plugin C++ et mémoire partagée ; établit la limite *pull-based* de la timeline et valide l'architecture démon découplé.
