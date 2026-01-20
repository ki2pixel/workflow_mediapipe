# **Rapport d'analyse technique : Évaluation des moteurs de capture faciale et d'estimation de blendshapes pour architectures GPU NVIDIA Turing non-RTX**

L'évolution des technologies de capture de mouvement facial (mocap) a franchi un seuil critique avec l'intégration généralisée des réseaux de neurones profonds et de la vision par ordinateur en temps réel. Pour les développeurs et les créateurs utilisant des architectures matérielles spécifiques, telles que la NVIDIA GeForce GTX 1650, le défi consiste à équilibrer la fidélité de l'animation, exprimée par les coefficients de blendshapes, et les contraintes de calcul imposées par l'absence de cœurs Tensor dédiés, contrairement aux séries RTX.1 Ce rapport explore de manière exhaustive les moteurs de tracking compatibles avec les GPU de génération Turing non-RTX, en analysant leur architecture, leurs mécanismes d'optimisation et leur interopérabilité avec les standards de l'industrie comme ARKit.

## **Fondements matériels et contraintes de l'architecture Turing SM 7.5**

La compréhension de la performance des moteurs de tracking faciaux nécessite une analyse préalable du processeur graphique cible. La GeForce GTX 1650 repose sur l'architecture Turing (SM 7.5), qui a introduit des améliorations significatives dans l'exécution concurrente d'opérations sur les nombres entiers et à virgule flottante, ainsi qu'un cache de données unifié plus performant.2 Cependant, l'absence de cœurs Tensor et RT limite l'usage de certains SDK propriétaires, notamment NVIDIA Maxine, qui s'appuient sur ces unités spécialisées pour l'accélération de l'intelligence artificielle et le débruitage de haute précision.1

### **Analyse de la compatibilité CUDA et TensorRT**

Malgré l'absence de cœurs Tensor, la GTX 1650 conserve une capacité de calcul CUDA robuste. Les moteurs de tracking peuvent être optimisés via TensorRT, à condition de cibler les capacités de calcul spécifiques à l'architecture SM 7.5.3 TensorRT permet de transformer des modèles entraînés sous PyTorch ou TensorFlow en moteurs d'inférence hautement performants en fusionnant les couches du réseau et en calibrant la précision des calculs.6 Pour un GPU disposant de 4 Go de VRAM, cette optimisation est vitale pour éviter la saturation de la mémoire vidéo lors de l'exécution simultanée du moteur de tracking et de l'environnement de rendu.5

| Composant Matériel | Spécification / Capacité | Impact sur le Tracking Facial |
| :---- | :---- | :---- |
| Architecture | NVIDIA Turing (SM 7.5) | Supporte CUDA 12 et TensorRT.3 |
| Cœurs CUDA | Variable selon le modèle (TU117/TU116) | Gère l'inférence parallélisée des landmarks. |
| VRAM | 4 Go GDDR5/GDDR6 | Limite la résolution d'entrée et la taille des modèles.8 |
| Cœurs Tensor | Absents | Incompatibilité avec NVIDIA Maxine AR SDK.1 |
| Encodage Vidéo | NVENC (Turing) | Accélère le décodage des flux webcam en temps réel. |

## **Le Standard des Blendshapes et la Nomenclature ARKit**

Le pilotage d'un avatar 3D repose sur la manipulation de blendshapes, également appelés "clés de forme". Ces déformations géométriques sont activées par des coefficients allant de 0.0 (neutre) à 1.0 (activation maximale).9 Le standard de facto dans l'industrie est celui d'Apple ARKit, qui définit une liste de 52 expressions faciales basées sur le système FACS (Facial Action Coding System).9

### **Mécanisme mathématique de l'animation faciale**

La position finale d'un sommet $V$ dans un maillage animé est calculée par la sommation pondérée des déplacements de chaque blendshape activé. Si $V\_{base}$ est le sommet au repos et $\\Delta V\_i$ le vecteur de déplacement du blendshape $i$, la formule appliquée est la suivante :

$$V\_{final} \= V\_{base} \+ \\sum\_{i=1}^{52} w\_i \\cdot \\Delta V\_i$$  
L'objectif des moteurs de tracking est d'estimer en temps réel les poids $w\_i$ à partir de l'analyse visuelle des traits du visage, tels que la position des sourcils, l'ouverture de la bouche et le mouvement des paupières.9

## **Analyse des Moteurs de Tracking Alternatifs Compatibles GPU**

L'utilisateur ayant déjà implémenté des solutions comme MediaPipe, OpenSeeFace et EOS, il est nécessaire de se tourner vers des frameworks offrant une fidélité accrue ou des méthodes de reconstruction 3D plus profondes, tout en garantissant une compatibilité avec les instructions CUDA standard.

### **MediaPipe FaceMeshV2 et l'Estimation Native des Blendshapes**

Bien que l'utilisateur utilise déjà MediaPipe, l'introduction récente de FaceMeshV2 (Mars 2023\) change radicalement la donne. Contrairement à la première version qui se contentait de fournir 468 points de repère 3D, FaceMeshV2 intègre un modèle de régression capable de produire directement les coefficients de blendshapes.11 Cette version améliore considérablement la précision du suivi des iris et des clignements d'yeux.11

L'architecture de FaceMeshV2 repose sur un pipeline de deux réseaux de neurones : un détecteur de visage léger (BlazeFace) et un réseau de prédiction de maillage.11 Sur une GTX 1650, ce moteur peut être exécuté via le délégué GPU de TensorFlow Lite, offrant une latence extrêmement faible tout en libérant le CPU pour d'autres tâches.

### **DeepFaceLive : Vers une Capture de Mouvement Haute Densité**

DeepFaceLive, bien que célèbre pour ses capacités de changement de visage (deepfake), contient l'un des moteurs de tracking les plus robustes pour le matériel NVIDIA grand public. Il a été testé avec succès sur des architectures similaires à la GTX 1650, permettant d'extraire des landmarks et de piloter des expressions même avec des ressources VRAM limitées.2

L'intérêt de DeepFaceLive réside dans sa flexibilité. Il permet de choisir entre plusieurs modèles d'extraction (comme RetinaFace ou InsightFace) qui peuvent être configurés pour s'exécuter via l'exécution provider CUDA d'ONNX Runtime.6 Pour un utilisateur de GTX 1650, il offre une alternative viable à Maxine, capable d'atteindre des fréquences d'images suffisantes pour le streaming si la résolution d'entrée est optimisée (par exemple, 640x360 au lieu de 1080p).8

### **DECA (Detailed Expression Capture and Animation)**

DECA est un framework de pointe qui dépasse le simple positionnement de points de repère. Il reconstruit une géométrie 3D complète à l'aide d'un modèle statistique appelé FLAME (Faces Learned with Articulated Motion and Expressions).14 DECA est capable de prédire non seulement la forme globale du visage, mais aussi les détails des expressions (rides, plis de la peau) à partir d'une seule image.15

Sur le plan technique, DECA utilise un encodeur ResNet50 pour prédire les paramètres FLAME.14 Bien que conçu initialement pour des GPU de classe workstation (Quadro RTX 5000), le code CUDA de DECA et son implémentation PyTorch peuvent être adaptés pour la GTX 1650 en utilisant des versions optimisées de PyTorch3D et en exploitant la compilation JIT (Just-In-Time) pour accélérer le rasterizer.15

### **EMOCA (Emotion Capture and Animation)**

EMOCA est une extension directe de DECA qui se concentre sur la capture de l'intensité émotionnelle. Les chercheurs ont constaté que les modèles de reconstruction classiques perdent souvent la "valeur émotionnelle" de l'expression d'origine.14 EMOCA résout ce problème en intégrant une perte de perception émotionnelle (EmoNet) dans son entraînement.16

L'utilisation d'EMOCA sur une GTX 1650 offre une fidélité d'expression inégalée pour des applications de recherche ou de production de haute qualité. Cependant, la charge de calcul est plus importante que celle de MediaPipe, nécessitant une gestion rigoureuse de la file d'attente CUDA.16

| Modèle | Méthode de Sortie | Compatibilité 1650 | Points Forts |
| :---- | :---- | :---- | :---- |
| **MediaPipe V2** | Coefficients Blendshapes | Excellente | Latence minimale, intégration facile.11 |
| **DeepFaceLive** | Landmarks / Face Swap | Bonne | Très stable, modèles variés.2 |
| **DECA** | Maillage FLAME 3D | Moyenne | Détails des expressions, géométrie précise.15 |
| **EMOCA** | Maillage Émotionnel | Moyenne | Fidélité émotionnelle supérieure.16 |
| **InsightFace** | Maillage / Landmarks | Excellente | Très performant en environnement CUDA.18 |

## **Frameworks d'Inférence et Optimisation Logicielle**

Pour qu'un moteur de tracking soit utilisable sur une GTX 1650, le choix du framework d'exécution est aussi important que le choix du modèle lui-même. L'objectif est de réduire la consommation de VRAM et d'augmenter le débit d'inférence.

### **ONNX Runtime et le CUDA Execution Provider**

ONNX Runtime est devenu le standard pour le déploiement de modèles d'IA sur GPU. Il permet d'utiliser le CUDAExecutionProvider qui, contrairement à Maxine, ne nécessite pas de cœurs Tensor.6 Le mécanisme de "partitionnement de graphe" d'ONNX Runtime permet d'envoyer les sous-graphes compatibles vers le GPU tout en conservant les opérations non supportées sur le CPU, garantissant ainsi qu'aucune erreur fatale ne survienne durant l'exécution.6

### **TensorRT et l'Optimisation par Précision Mixte**

Bien que la GTX 1650 ne puisse pas exploiter l'accélération matérielle des cœurs Tensor pour les opérations FP16, elle supporte néanmoins le calcul en demi-précision (FP16) via ses unités CUDA standard.5 TensorRT peut optimiser un modèle pour utiliser cette précision, ce qui divise par deux la mémoire nécessaire pour stocker les poids du réseau, une économie cruciale sur un GPU de 4 Go.5

Une technique avancée consiste à utiliser le "Timing Cache" de TensorRT. Lors du premier lancement du moteur de tracking, TensorRT teste des centaines de configurations de calcul pour chaque couche du modèle et enregistre la plus rapide dans un fichier cache.6 Cela réduit drastiquement le temps de chargement lors des utilisations ultérieures et garantit que le moteur de tracking tire le meilleur parti des unités de calcul de la GTX 1650\.6

## **Logiciels d'Interfaçage et Écosystème de Production**

Le tracking n'est qu'une partie de la chaîne de production. Les données extraites doivent être transmises à un moteur de rendu ou à un logiciel d'animation via des protocoles standardisés.

### **VSeeFace et OpenSeeFace : L'Ancrage du Temps Réel**

VSeeFace est l'application pivot pour le tracking facial avec avatars VRM. Son moteur natif, OpenSeeFace, est conçu pour être léger et compatible avec une large gamme de matériels.19 VSeeFace supporte le protocole VMC (Virtual Motion Capture), permettant de recevoir des données de tracking de sources externes comme DeepFaceLive ou des applications Android.19

Une recommandation importante pour les utilisateurs de GTX 1650 est de désactiver l'ajustement de priorité du GPU dans les paramètres de VSeeFace si des crashs surviennent, une instabilité parfois observée avec les pilotes NVIDIA récents sur les architectures Turing.10 Il est également conseillé d'exécuter le logiciel en mode administrateur pour garantir que le moteur de tracking ne soit pas privé de ressources par le système d'exploitation.10

### **MeFaMo (MediaPipe Face Mocap)**

MeFaMo est une solution intéressante pour les utilisateurs cherchant à intégrer le tracking MediaPipe dans Unreal Engine. Il utilise la bibliothèque PyLiveLinkFace pour envoyer les données de blendshapes directement dans un projet Unreal via le protocole LiveLink.20 Bien que le projet ne soit plus activement maintenu, son code source fournit une base solide pour comprendre comment mapper les coordonnées 3D de MediaPipe vers les 52 blendshapes ARKit sans passer par un SDK propriétaire.20

### **Kalidokit : Le Calculateur de Cinématique et de Blendshapes**

Kalidokit est une bibliothèque JavaScript/TypeScript qui agit comme un pont entre les modèles de vision par ordinateur (comme MediaPipe ou TensorFlow.js) et les modèles 3D.18 Il contient des algorithmes mathématiques sophistiqués pour transformer les points de repère bruts en rotations d'os et en poids de blendshapes.21 Pour un développeur créant son propre script de tracking, l'intégration de Kalidokit permet d'économiser des mois de recherche sur la géométrie faciale.

## **Défis de la Gestion de la Mémoire et Performance**

Sur un GPU avec 4 Go de VRAM, l'exécution d'un moteur de tracking complexe peut rapidement devenir problématique. L'analyse des journaux système de DeepFaceLive montre qu'un modèle de tracking de haute qualité peut consommer entre 1,5 et 2 Go de VRAM, laissant peu de place pour le rendu de l'avatar et les applications de streaming (comme OBS avec encodage NVENC).8

### **Stratégies d'Optimisation du Flux Vidéo**

Pour réduire la charge, il est recommandé de limiter la résolution de la caméra de capture à 640x360 pixels. Les réseaux de neurones de tracking modernes n'ont pas besoin d'une résolution 1080p pour fonctionner ; au contraire, une résolution plus élevée augmente inutilement le temps de convolution sans gain significatif de précision pour les blendshapes.13 De plus, l'utilisation de formats de pixels légers (comme YUV au lieu de RGB) lors de la capture via OpenCV peut réduire la bande passante mémoire consommée.22

### **Dépannage des Pilotes et Priorités Système**

L'utilisation de la GTX 1650 avec des outils de tracking basés sur CUDA nécessite une version de pilote stable. Des problèmes de lag ont été signalés avec des versions de pilotes spécifiques lorsque le tracking s'exécute en arrière-plan.10 L'activation de la "planification matérielle du GPU" (Hardware-accelerated GPU scheduling) dans Windows 10/11 peut aider à réduire la latence de l'inférence en permettant au processeur graphique de gérer sa propre file d'attente de tâches plus efficacement.19

## **Analyse des Protocoles de Communication**

L'interopérabilité entre le moteur de tracking et l'avatar est assurée par deux protocoles majeurs.

| Protocole | Type de Transport | Usage Principal | Avantages |
| :---- | :---- | :---- | :---- |
| **VMC (Virtual Motion Capture)** | OSC (UDP) | Tracking d'avatars VRM | Supporte le mixage de plusieurs sources.19 |
| **LiveLink** | UDP Propriétaire | Unreal Engine | Intégration native, faible latence.20 |
| **iFacialMocap** | TCP/UDP | Communication Mobile-PC | Standard pour les applications Android/iOS.23 |

Le protocole VMC est particulièrement recommandé pour les configurations multi-logiciels car il permet d'envoyer les données de tracking à plusieurs applications simultanément (par exemple, VSeeFace pour le rendu et un script Python pour l'analyse de données).19

## **Vers une Approche Hybride : Le Rôle des Dispositifs Externes**

Si la GTX 1650 atteint ses limites, une approche hybride consiste à déporter l'estimation des blendshapes sur un appareil mobile tout en conservant le rendu sur le GPU PC. MeowFace, sur Android, utilise les API de vision par ordinateur du smartphone pour générer des données compatibles ARKit, qui sont ensuite transmises au PC par WiFi.23 Cette méthode garantit que 100% des ressources de la GTX 1650 sont allouées au rendu de l'avatar, offrant une fluidité maximale pour le streaming.23

## **Conclusion et Recommandations Techniques**

L'utilisateur dispose de plusieurs voies pour enrichir ses scripts de tracking malgré les limitations de son matériel. Si la priorité est la simplicité et la performance brute, l'adoption de MediaPipe FaceMeshV2 avec le support natif des blendshapes est la solution la plus rationnelle. Elle offre une compatibilité GPU parfaite et une intégration facile via Kalidokit.11

Pour des besoins de production plus exigeants où la fidélité de l'expression est primordiale, l'implémentation de DECA ou EMOCA via ONNX Runtime et le CUDA Execution Provider constitue l'alternative de pointe à NVIDIA Maxine.6 Bien que ces modèles demandent une configuration plus complexe, leur capacité à reconstruire la géométrie faciale en 3D permet une animation d'une richesse que les simples landmarks ne peuvent atteindre.

Enfin, la gestion proactive de la VRAM par la réduction des résolutions de capture et l'utilisation de TensorRT pour le caching des noyaux de calcul sera le facteur déterminant de la stabilité du système. En combinant ces moteurs avec des protocoles comme VMC, l'utilisateur peut bâtir un pipeline de capture faciale professionnel, flexible et performant, parfaitement adapté à son architecture Turing.6

#### **Sources des citations**

1. Face tracking CHOP not working with NVIDIA GTX1650 GEFORCE \- TouchDesigner forum, consulté le décembre 20, 2025, [https://forum.derivative.ca/t/face-tracking-chop-not-working-with-nvidia-gtx1650-geforce/295522](https://forum.derivative.ca/t/face-tracking-chop-not-working-with-nvidia-gtx1650-geforce/295522)  
2. Deep Face Llive Tutorial — With Nvidia RTX 1660 Ti \- YouTube, consulté le décembre 20, 2025, [https://www.youtube.com/watch?v=e84a7qW59C8](https://www.youtube.com/watch?v=e84a7qW59C8)  
3. Support Matrix — NVIDIA TensorRT Documentation, consulté le décembre 20, 2025, [https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html)  
4. How to convert Mediapipe Face Mesh to Blendshape weight \- Stack Overflow, consulté le décembre 20, 2025, [https://stackoverflow.com/questions/68169684/how-to-convert-mediapipe-face-mesh-to-blendshape-weight](https://stackoverflow.com/questions/68169684/how-to-convert-mediapipe-face-mesh-to-blendshape-weight)  
5. How to optimize inference using TensorRT on Jetson AGX Orin \- KeyValue, consulté le décembre 20, 2025, [https://www.keyvalue.systems/blog/from-bottlenecks-to-breakthroughs-how-tensorrt-video-analytics-revolutionized-our-pipeline/](https://www.keyvalue.systems/blog/from-bottlenecks-to-breakthroughs-how-tensorrt-video-analytics-revolutionized-our-pipeline/)  
6. NVIDIA \- TensorRT | onnxruntime, consulté le décembre 20, 2025, [https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html)  
7. ONNX Runtime integration with NVIDIA TensorRT in preview | Microsoft Azure Blog, consulté le décembre 20, 2025, [https://azure.microsoft.com/en-us/blog/onnx-runtime-integration-with-nvidia-tensorrt-in-preview/](https://azure.microsoft.com/en-us/blog/onnx-runtime-integration-with-nvidia-tensorrt-in-preview/)  
8. Roop-Cam (deepfake em tempo real com uma única imagem) : r/StableDiffusion \- Reddit, consulté le décembre 20, 2025, [https://www.reddit.com/r/StableDiffusion/comments/14uu7s3/roopcam\_realtime\_deepfake\_with\_a\_single\_image/?tl=pt-br](https://www.reddit.com/r/StableDiffusion/comments/14uu7s3/roopcam_realtime_deepfake_with_a_single_image/?tl=pt-br)  
9. pkhungurn/talking-head-anime-3-demo: Demo Programs ... \- GitHub, consulté le décembre 20, 2025, [https://github.com/pkhungurn/talking-head-anime-3-demo](https://github.com/pkhungurn/talking-head-anime-3-demo)  
10. VSeeFace release notes.md \- GitHub Gist, consulté le décembre 20, 2025, [https://gist.github.com/emilianavt/90bc0b73e2713276e6f630db09977eae?permalink\_comment\_id=3983842](https://gist.github.com/emilianavt/90bc0b73e2713276e6f630db09977eae?permalink_comment_id=3983842)  
11. FaceMeshV2 : Detecting Key Points on Faces in Real Time with Blendshapes \- Medium, consulté le décembre 20, 2025, [https://medium.com/axinc-ai/facemeshv2-detecting-key-points-on-faces-in-real-time-with-blendshapes-6381dbf78756](https://medium.com/axinc-ai/facemeshv2-detecting-key-points-on-faces-in-real-time-with-blendshapes-6381dbf78756)  
12. TensorRT \- ONNXRuntime \- GitHub Pages, consulté le décembre 20, 2025, [https://iot-robotics.github.io/ONNXRuntime/docs/execution-providers/TensorRT-ExecutionProvider.html](https://iot-robotics.github.io/ONNXRuntime/docs/execution-providers/TensorRT-ExecutionProvider.html)  
13. Webcam Motion Capture: Hand Tracking with Only Webcam, consulté le décembre 20, 2025, [https://webcammotioncapture.info/](https://webcammotioncapture.info/)  
14. EMOCA: Emotion Driven Monocular Face Capture and Animation \- Max-Planck-Gesellschaft, consulté le décembre 20, 2025, [https://download.is.tue.mpg.de/emoca/EMOCA\_\_CVPR22.pdf](https://download.is.tue.mpg.de/emoca/EMOCA__CVPR22.pdf)  
15. yfeng95/DECA: DECA: Detailed Expression Capture and ... \- GitHub, consulté le décembre 20, 2025, [https://github.com/yfeng95/DECA](https://github.com/yfeng95/DECA)  
16. \[2204.11312\] EMOCA: Emotion Driven Monocular Face Capture and Animation \- ar5iv, consulté le décembre 20, 2025, [https://ar5iv.labs.arxiv.org/html/2204.11312](https://ar5iv.labs.arxiv.org/html/2204.11312)  
17. SPARK: Self-supervised Personalized Real-time Monocular Face Capture \- arXiv, consulté le décembre 20, 2025, [https://arxiv.org/html/2409.07984v1](https://arxiv.org/html/2409.07984v1)  
18. KBLLR/git-stars: A curated list of GitHub stars ☕️, consulté le décembre 20, 2025, [https://github.com/KBLLR/git-stars](https://github.com/KBLLR/git-stars)  
19. VSeeFace, consulté le décembre 20, 2025, [https://www.vseeface.icu/](https://www.vseeface.icu/)  
20. JimWest/MeFaMo \- GitHub, consulté le décembre 20, 2025, [https://github.com/JimWest/MeFaMo](https://github.com/JimWest/MeFaMo)  
21. Real-Time 3D Avatar Modeling for AR using Human Pose and Actions in Resource-Constrained Web Environments \- UCSC Digital Library, consulté le décembre 20, 2025, [https://dl.ucsc.cmb.ac.lk/jspui/bitstream/123456789/4944/1/20000545%20-%20S%20R%20Galappaththy%20-%20Sandul%20Renuja.pdf](https://dl.ucsc.cmb.ac.lk/jspui/bitstream/123456789/4944/1/20000545%20-%20S%20R%20Galappaththy%20-%20Sandul%20Renuja.pdf)  
22. RGB Face Tracking and Reconstruction on GPU using CUDA \- GitHub, consulté le décembre 20, 2025, [https://github.com/isikmustafa/face-tracking](https://github.com/isikmustafa/face-tracking)  
23. IFacialMocap for PC? : r/vtubertech \- Reddit, consulté le décembre 20, 2025, [https://www.reddit.com/r/vtubertech/comments/18drc3e/ifacialmocap\_for\_pc/](https://www.reddit.com/r/vtubertech/comments/18drc3e/ifacialmocap_for_pc/)  
24. Android, 3D model, VSeeFace \+ Meowface alternative : r/vtubertech \- Reddit, consulté le décembre 20, 2025, [https://www.reddit.com/r/vtubertech/comments/1gwnxo3/android\_3d\_model\_vseeface\_meowface\_alternative/](https://www.reddit.com/r/vtubertech/comments/1gwnxo3/android_3d_model_vseeface_meowface_alternative/)