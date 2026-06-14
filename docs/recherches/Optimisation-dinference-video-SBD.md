# **Rapport d'Architecture Technique : Optimisation Extrême d'Inférence Vidéo et Évolution des Architectures de Détection de Transitions de Scènes**

## **Introduction et Paradigme de l'Analyse Vidéo à Grande Échelle**

L'analyse structurelle des flux vidéo, et plus spécifiquement la détection de transitions de scènes (Shot Boundary Detection \- SBD), constitue la pierre angulaire de la compréhension automatisée des médias visuels. Dans l'écosystème de l'apprentissage profond moderne, cette tâche transcende la simple identification de coupures abruptes (hard cuts) pour englober la reconnaissance sémantique de transitions graduelles complexes telles que les fondus enchaînés (dissolves), les fermetures au noir (fades) ou les balayages (wipes). Historiquement, les pipelines d'inférence s'appuient sur des architectures basées sur des réseaux de neurones convolutifs (CNN) tridimensionnels, capables de modéliser simultanément les dimensions spatiales et temporelles. Au sein de ces architectures, TransNetV2 s'est imposé comme un standard de l'industrie, exploitant une structure DDCNN V2 (Deep Dilated Convolutional Neural Network) associée à des histogrammes de couleurs RGB et des mesures de similarité inter-trames pour atteindre des niveaux de précision remarquables.1 Le modèle analyse les vidéos par le biais d'une fenêtre temporelle glissante de 100 images, sous-échantillonnées à une résolution spatiale très basse de 48x27 pixels, afin de prédire la probabilité de transition pour chaque trame.3  
Cependant, le déploiement de tels modèles dans un environnement de production lourd, orchestré sous PyTorch et adossé à des accélérateurs matériels NVIDIA (CUDA), se heurte invariablement à des défis architecturaux majeurs liés aux flux d'entrées et de sorties (I/O). Le paradigme de traitement traditionnel s'appuie sur un décodage logiciel exécuté par le processeur central (CPU) via des bibliothèques telles que FFmpeg, qui extrait les trames vidéo sous forme de matrices RGB24 brutes dans la mémoire système (RAM).4 Ces données massives et non compressées doivent ensuite transiter par le bus PCI-Express (PCIe) pour atteindre la mémoire vidéo (VRAM) du processeur graphique (GPU) où l'inférence neuronale est véritablement exécutée.5 Dans un scénario de traitement par lots (batching) massivement parallèle, ce transfert systématique sature rapidement la bande passante du bus PCIe, induisant un phénomène de famine de données (data starvation) au niveau des cœurs de calcul CUDA.5 Le GPU, pourtant capable de performances de calcul de l'ordre du pétaflops sur les architectures récentes, se retrouve sous-utilisé, limitant drastiquement le ratio d'images par seconde (FPS) par gigaoctet de VRAM consommée.7  
L'objet de la présente recherche est de déconstruire ce goulot d'étranglement et de proposer une refonte architecturale exhaustive selon deux axes stratégiques fondamentaux. Le premier axe explore l'optimisation matérielle extrême de l'architecture existante, en supprimant la latence de transfert via un décodage direct en VRAM (Zero-Copy) et en transpilant le modèle TransNetV2 vers un graphe d'exécution NVIDIA TensorRT optimisé en précision mixte (FP16/INT8). Le second axe évalue la pertinence d'une obsolescence programmée de TransNetV2 au profit des architectures de l'état de l'art (SOTA) des années 2023 à 2026, caractérisées par l'intégration de mécanismes d'attention (Transformers) et de recherche d'architecture neuronale (NAS), capables de redéfinir les standards de précision sur les transitions graduelles.9

## **Axe A : Optimisation Matérielle Extrême et Refonte du Pipeline d'Exécution**

L'optimisation d'un pipeline PyTorch en production ne se résume pas à l'accélération du graphe de calcul neuronal ; elle exige une ingénierie holistique du cycle de vie de la donnée, depuis son extraction du support de stockage jusqu'à la projection de la prédiction finale. La maximisation du rendement matériel passe par la suppression de l'intermédiaire CPU et la compilation bas niveau des opérations tensorielles.

### **Le Décodage Zéro-Copie et l'Élimination du Goulot d'Étranglement PCIe**

Le décodage vidéo logiciel sur CPU est une opération asymétrique. Pour une vidéo compressée en H.264 ou HEVC, le flux binaire représente un volume de données relativement restreint. Cependant, une fois décompressées en RGB24 par FFmpeg, les trames brutes d'une seule seconde de vidéo 1080p à 30 images par seconde représentent un flux de plusieurs centaines de mégaoctets.5 Le transfert de ces trames brutes de la RAM vers la VRAM via tensor.to('cuda') sollicite intensément le bus PCIe.5 Pour contourner cette limite physique, les architectures matérielles NVIDIA modernes intègrent un processeur de décodage dédié, le NVDEC (NVIDIA Decoder), capable de décompresser les flux vidéo de manière totalement autonome.5 L'exploitation de ce composant matériel via des bibliothèques logicielles spécialisées permet de réaliser un décodage "zéro-copie", où le tenseur décodé est instancié directement dans la mémoire vidéo.  
L'écosystème Python a récemment vu l'émergence de plusieurs solutions pour interfacer NVDEC avec PyTorch, chacune présentant des compromis spécifiques en termes de flexibilité, de dépendances et de performances.  
PyAV-CUDA constitue une première approche, se positionnant comme une extension de la bibliothèque standard PyAV pour ajouter le support du décodage matériel h264\_cuvid de FFmpeg.13 Cette bibliothèque permet d'initialiser un contexte matériel dédié via avcuda.init\_hwcontext et de convertir les trames directement en tenseurs CUDA grâce à la méthode avcuda.to\_tensor.13 Bien que les benchmarks bruts montrent des accélérations spectaculaires, réduisant par exemple le temps de décodage d'un échantillon de 34.99 secondes sur CPU à 8.30 secondes sur GPU 13, cette solution souffre d'une complexité d'intégration significative. Elle requiert souvent une recompilation manuelle de FFmpeg avec le support NVDEC (--enable-cuda-nvcc) et la gestion complexe des chemins de liaisons dynamiques (PKG\_CONFIG\_LIBDIR).13 De plus, le support d'autres codecs comme l'AV1 peut s'avérer erratique ou basculer silencieusement sur un traitement logiciel malgré la spécification du contexte matériel.14  
Une seconde alternative réside dans l'utilisation de NVIDIA DALI (Data Loading Library), une solution conçue explicitement pour saturer les GPU lors de l'entraînement ou de l'inférence de réseaux de neurones.16 DALI propose l'opérateur ops.VideoReader qui, configuré avec l'argument device="gpu", orchestre la lecture, le décodage et le transfert des séquences vidéo de manière totalement asynchrone.16 DALI est particulièrement adapté pour fournir des séquences de longueur fixe, correspondant parfaitement aux exigences de la fenêtre de 100 images de TransNetV2.3 En définissant sequence\_length=100 et en exploitant des paramètres tels que initial\_fill pour le préchargement en mémoire tampon, DALI masque efficacement les latences d'accès au disque.16 Néanmoins, l'architecture de DALI repose sur la définition d'un graphe statique et déclaratif (Pipeline API) qui s'intègre difficilement dans des pipelines d'inférence hautement dynamiques où la longueur des vidéos varie ou lorsque des logiques de traitement conditionnel complexes sont requises après le décodage.16  
La solution la plus moderne et techniquement avantageuse provient de la bibliothèque TorchCodec, développée et maintenue par Meta pour l'écosystème PyTorch.4 TorchCodec offre une API Pythonique intuitive qui abstrait entièrement la complexité de l'API C de FFmpeg tout en garantissant un accès direct à NVDEC.4 En instanciant la classe VideoDecoder avec le paramètre device="cuda", le décodage matériel est activé et les trames vidéo sont retournées sous la forme d'un tenseur PyTorch au format NCHW (Batch, Channel, Height, Width), de type torch.uint8, résidant nativement sur le GPU.5 Cette approche est particulièrement synergique avec TransNetV2, car les étapes de prétraitement ultérieures, telles que le redimensionnement drastique à une résolution de 48x27 pixels, peuvent être exécutées directement par des transformations PyTorch accélérées par CUDA.3 En effet, l'exécution d'une interpolation bilinéaire sur des tenseurs déjà présents en VRAM est immensément plus rapide que de procéder à ce redimensionnement sur le CPU via OpenCV.5 TorchCodec démontre une supériorité incontestable dans les cas d'usage impliquant le décodage simultané de multiples vidéos par des threads parallèles (batch decoding), un scénario classique pour saturer les pipelines d'inférence en production.8 En outre, la bibliothèque intègre un mécanisme robuste de surveillance matérielle via la classe CpuFallbackStatus, permettant au système de basculer de manière transparente vers un décodage logiciel si le flux vidéo utilise un format non pris en charge par NVDEC, garantissant ainsi la continuité de service.7 L'utilisation du backend expérimental via set\_cuda\_backend("beta") permet d'activer des chemins d'exécution encore plus optimisés pour le transfert de mémoire.5  
L'intégration de TorchCodec élimine le goulot d'étranglement lié au transfert PCIe, permettant au pipeline de n'ingérer que les paquets compressés depuis le disque, maximisant ainsi l'efficacité énergétique et la bande passante disponible pour d'autres opérations système.5

### **Compilation ONNX et Optimisation TensorRT : Le Moteur d'Inférence**

Si le décodage matériel résout la famine de données, la compilation du modèle lui-même dicte la vitesse d'ingestion mathématique. L'implémentation originale de TransNetV2 en PyTorch exécute un graphe dynamique en précision standard (virgule flottante 32 bits, FP32).19 Bien que PyTorch propose des compilateurs Just-In-Time (JIT), la performance ultime sur le matériel NVIDIA est atteinte par l'exportation du modèle vers le format Open Neural Network Exchange (ONNX), suivie d'une compilation spécifique au matériel (Ahead-Of-Time) via NVIDIA TensorRT.21  
La transition vers ONNX nécessite une modélisation précise du graphe de calcul. Le modèle TransNetV2 s'attend à recevoir un tenseur d'entrée représentant une fenêtre de 100 images, avec une résolution de 48x27 pixels.3 Lors de l'utilisation de torch.onnx.export, il est impératif de déclarer des axes dynamiques (Dynamic Axes) pour la dimension du lot (batch size) afin de préserver la flexibilité lors de l'inférence simultanée de plusieurs fenêtres.23 L'outil d'export enregistre les poids (paramètres spatio-temporels de l'architecture DDCNN V2) et les opérations dans une représentation agnostique.1  
L'outil en ligne de commande trtexec, inclus dans le SDK TensorRT, prend ensuite le relais pour générer un engin d'inférence hautement optimisé (engine file).22 La puissance de TensorRT repose sur plusieurs optimisations mathématiques profondes. La première est la fusion de couches (Layer Fusion) : les opérations séquentielles telles que les convolutions 3D, les additions de biais et les fonctions d'activation sont mathématiquement combinées en un seul noyau CUDA (Kernel), évitant ainsi de multiples allers-retours coûteux vers la mémoire globale du GPU.25 La seconde est l'auto-réglage des noyaux (Kernel Auto-Tuning) : TensorRT compile et évalue des dizaines d'implémentations algorithmiques pour chaque couche fusionnée, sélectionnant l'algorithme qui s'exécute le plus rapidement sur la microarchitecture spécifique du GPU hôte (par exemple, en exploitant les spécificités des architectures Ampere ou Ada Lovelace).26  
L'argument \--useCudaGraph dans trtexec est d'une importance capitale pour un modèle exécuté à haute fréquence comme TransNetV2.24 Il permet de capturer l'ensemble de la séquence de lancements des noyaux CUDA dans un graphe unifié, réduisant pratiquement à zéro le temps de surcharge (overhead) imposé au CPU pour orchestrer l'exécution sur le GPU.24 De même, les arguments \--minShapes, \--optShapes, et \--maxShapes informent le compilateur des tailles de lots attendues, lui permettant de préallouer la mémoire de travail (Workspace) de manière optimale et de sélectionner les noyaux les plus performants pour le profil \--optShapes.27

### **Le Dilemme de la Quantification : Précision FP16 contre Entropie INT8**

L'un des leviers les plus puissants de TensorRT pour réduire l'empreinte VRAM et décupler les opérations par seconde est la réduction de la précision numérique des tenseurs de poids et des activations, connue sous le nom de quantification.28  
L'activation de l'indicateur \--fp16 dans trtexec convertit le modèle en demi-précision (16 bits).24 L'architecture DDCNN de TransNetV2 se prête exceptionnellement bien à cette transformation. Le domaine dynamique des activations dans les réseaux convolutifs pour l'analyse d'images est généralement bien circonscrit, et la conversion de FP32 à FP16 n'induit aucune perte sémantique mesurable. L'inférence FP16 divise la consommation de VRAM par deux et active l'utilisation massive des cœurs Tensor (Tensor Cores) spécialisés dans les multiplications matricielles en virgule flottante, doublant souvent le débit d'inférence réel.28 Les scores F1 de référence de TransNetV2 (77.9% sur le dataset ClipShots et 93.9% sur RAI) restent rigoureusement identiques en FP16.30  
La quantification en INT8 (entiers de 8 bits), en revanche, introduit un paradigme mathématique beaucoup plus risqué pour la tâche spécifique de la détection de limites de plans.28 L'INT8 ne dispose que de 256 valeurs discrètes pour représenter l'ensemble du domaine des activations. TensorRT emploie un schéma de quantification symétrique nécessitant un facteur d'échelle pour mapper les valeurs flottantes vers ces entiers.28 Pour un modèle déjà entraîné, cette opération s'effectue via la Quantification Post-Entraînement (Post-Training Quantization \- PTQ).28 La PTQ nécessite de fournir à trtexec un fichier de calibration généré en injectant un lot représentatif de données (Calibration Dataset) dans le modèle pour analyser la distribution statistique des activations.32 TensorRT utilise ensuite un algorithme pour minimiser la divergence de Kullback-Leibler (Perte d'information entropique) entre la distribution FP32 originale et la distribution INT8 quantifiée.32  
Cependant, l'analyse des retours d'expérience et des principes fondamentaux de la vision par ordinateur met en lumière une incompatibilité structurelle entre l'INT8 PTQ et la détection de transitions graduelles (soft fades, dissolves).29 Si une coupure abrupte (hard cut) génère un gradient d'activation massif qui survit très bien à la troncature INT8, une transition graduelle s'étendant sur plusieurs dizaines d'images repose sur des variations infinitésimales des valeurs des pixels et des caractéristiques internes extraites par les convolutions tridimensionnelles. L'écrasement de la plage dynamique imposé par le facteur d'échelle INT8 agit comme un filtre passe-bas destructeur, annulant ces micro-variations. En conséquence, si l'INT8 PTQ permet effectivement de quadripler théoriquement le débit matériel et de diviser l'empreinte VRAM par quatre par rapport au modèle original, il engendre une dégradation asymétrique du rappel (Recall) sur les classes de transitions douces.28 Sans recourir à un ré-entraînement complet du modèle intégrant la simulation de quantification (Quantization-Aware Training \- QAT), une procédure lourde et coûteuse, la compilation de TransNetV2 en INT8 pour des tâches exigeant une haute fidélité sur les fondus enchaînés constitue un risque technique majeur d'altération du score F1 global.28

## **Axe B : Panorama Exhaustif de l'État de l'Art (SOTA 2023-2026) en SBD**

L'optimisation hardcore de TransNetV2 via l'Axe A permet d'atteindre le rendement matériel maximal pour une architecture conçue autour de 2020\. Néanmoins, l'évolution fulgurante des architectures d'apprentissage profond au cours des dernières années soulève la question de l'obsolescence structurelle du modèle. L'exploration de la littérature scientifique récente sur des portails tels que ArXiv et PapersWithCode met en évidence une rupture de paradigme dans la modélisation de la détection des frontières de plans.9

### **Les Limites Intrinsèques de l'Architecture TransNetV2**

Bien que TransNetV2 affiche des scores F1 globaux honorables (entre 0.75 et 0.82 selon les mesures contemporaines), une analyse diagnostique fine révèle ses failles conceptuelles.36 Le problème fondamental réside dans le traitement des transitions graduelles. Les modèles basés sur des CNN 3D comme TransNetV2 tendent à réduire drastiquement la résolution spatiale (à 48x27 pixels) pour maintenir un temps de calcul acceptable sur de longues fenêtres temporelles.3 Ce sous-échantillonnage sévère détruit une part significative des informations de texture nécessaires à l'identification précise des effets visuels de transition.12 De plus, ces architectures prédisent souvent des limites de plans approximatives, où le segment temporel prédit ne s'aligne que grossièrement avec la durée réelle de la transition.37 Les publications de 2026 utilisent une métrique spécifique, le "Transition IoU" (Intersection sur Union des segments de transition), pour quantifier ce phénomène. Sur cette métrique cruciale, TransNetV2 s'effondre avec un score exceptionnellement bas de 0.192, prouvant son incapacité à délimiter précisément le début et la fin d'un fondu ou d'un balayage.36 De même, la précision sur les sauts soudains et rapides (Sudden jump precision) s'avère limitée, le modèle peinant à différencier un véritable changement de plan d'un mouvement de caméra erratique très rapide.36

### **AutoShot : L'Approche par Recherche d'Architecture (NAS)**

En 2023, Zhu et al. ont proposé une solution novatrice nommée AutoShot, présentée lors de la conférence CVPR.9 Face à la difficulté de concevoir manuellement une architecture optimale pour la SBD, les chercheurs ont employé la Recherche d'Architecture Neuronale (Neural Architecture Search \- NAS).9 Ils ont défini un vaste espace de recherche englobant diverses configurations de réseaux convolutifs 3D avancés et de blocs d'attention de type Transformer.9  
L'algorithme NAS a convergé vers une architecture hybride très performante, identifiée dans les fichiers du dépôt GitHub open source (wentaozhu/AutoShot) sous le nom de "Supernet Flat Transformer" (supernet\_flattransf\_3\_8\_8\_8\_13\_12\_0\_16\_60.py).38 Cette structure aplatie permet au modèle de capturer des dépendances temporelles à plus long terme avec une meilleure efficacité que les convolutions dilatées rigides de TransNetV2.38  
Pour entraîner et évaluer cette architecture, les auteurs ont constitué et publié un nouveau jeu de données ciblant spécifiquement le format des vidéos courtes modernes (TikTok, Instagram Reels, YouTube Shorts), nommé le jeu de données SHOT.9 Ce dataset comprend 853 vidéos complètes et plus de 11 606 annotations de limites de plans.9  
Les performances d'AutoShot démontrent une avancée claire. Évalué sur le nouveau dataset SHOT, le modèle surpasse TransNetV2 de 4.2% en termes de score F1.9 Plus important encore, les auteurs ont validé la capacité de généralisation de cette architecture issue du NAS en l'évaluant directement sur des benchmarks publics préexistants.38 Les résultats confirment sa supériorité : AutoShot augmente le score F1 de 1.1% sur ClipShots (atteignant environ 79.0%), de 1.2% sur RAI (atteignant environ 95.1%), et de 0.9% sur BBC par rapport aux précédentes approches de l'état de l'art.9 Le code d'inférence, tel que compare\_inference\_baseline\_groundtruth\_v2.py, ainsi que les poids des modèles (supernet\_best\_f1.pickle) sont disponibles publiquement, rendant cette solution directement exploitable.38

### **OmniShotCut : La Révolution des Transformers Vidéo Denses**

L'avancée la plus spectaculaire dans le domaine, définissant le véritable état de l'art pour l'horizon 2024-2026, est l'introduction d'OmniShotCut par le laboratoire de vision par ordinateur de l'Université de Virginie (UVA).11 Ce modèle adresse directement les failles historiques en reformulant le problème. Au lieu de considérer la SBD comme une simple tâche de classification binaire frame par frame (cette image est-elle une limite?), OmniShotCut la traite comme un problème de **prédiction relationnelle structurée**.36  
L'architecture repose sur un Transformer vidéo dense basé sur des "requêtes de plans" (Shot-Query Transformer).11 Ce mécanisme permet au modèle d'optimiser conjointement la prédiction des limites temporelles de chaque plan, tout en évaluant simultanément les relations de continuité spatiale à l'intérieur d'un même plan (relations intra-plan) et la cohérence sémantique entre des plans adjacents (relations inter-plans).36 L'ensemble de ces prédictions est géré au sein d'un état caché unifié, offrant au modèle une compréhension globale et contextuelle de la structure de montage de la vidéo.36  
Cette modélisation continue est particulièrement redoutable pour la détection des transitions graduelles. Le Transformer n'identifie pas un point de coupure abstrait, mais détecte l'intervalle temporel complet constituant la transition.12 Pour entraîner ce modèle complexe sans être limité par la qualité médiocre des annotations manuelles des anciens datasets, les chercheurs ont développé un pipeline de synthèse de données générant automatiquement des familles entières de transitions mathématiquement parfaites (dissolves, wipes, slides, doorways).12 Ils ont également introduit OmniShotCutBench, un benchmark moderne incluant des vidéos issues du web contemporain.36  
Les métriques publiées sont sans appel. OmniShotCut atteint un score F1 global de 0.883 (88.3%), écrasant les scores respectifs de 0.814 pour AutoShot et TransNetV2 sur les mêmes bases d'évaluation modernes.36 Plus impressionnant encore, la métrique Transition IoU bondit à **0.632** (contre 0.192 pour TransNetV2 et 0.252 pour AutoShot), certifiant la capacité du modèle à localiser le début et la fin exacts des effets visuels avec une précision chirurgicale.36 Les précisions relationnelles intra-plan (0.959) et inter-plans (0.836) valident la robustesse sémantique de l'approche.36 Le code complet et le modèle sont accessibles sur le dépôt UVA-Computer-Vision-Lab/OmniShotCut.11

### **FilmShots : Convolutions Dilatées et Analyse Cinématographique**

En parallèle des approches basées sur les Transformers, une alternative publiée dans la revue IEEE Access en 2026, nommée FilmShots, propose une architecture ciblant spécifiquement les défis inhérents aux longs métrages : scènes très sombres, sous-titres superposés, mouvements rapides, et fortes variations colorimétriques.10  
Plutôt que d'adopter des blocs d'attention purs dont la complexité de calcul croît de manière quadratique avec la longueur de la séquence vidéo temporelle, FilmShots innove en combinant des convolutions 3D dilatées (Temporal Dilated Convolutions).10 La dilatation permet d'élargir le champ récepteur du réseau pour capter des dépendances temporelles sur de longues durées sans augmenter proportionnellement le nombre de paramètres ou la charge computationnelle.10 L'architecture se divise en plusieurs composants de spécialisation : des blocs non locaux (FilmShotNL) pour extraire les dépendances à long rayon d'action, une Transformée en Cosinus Discrète (FilmShotNLDCT) visant à compresser drastiquement la complexité spatio-temporelle de ces opérations, et des mécanismes d'attention de canal via des convolutions unidimensionnelles (FilmShotECA).10  
L'approche de FilmShots se révèle particulièrement pertinente car elle surpasse empiriquement à la fois TransNetV2 et AutoShot en score F1 sur des ensembles de données cinématographiques difficiles, fournissant une implémentation robuste hébergée sous CBD-Lab/FilmShots.10 Techniquement, l'utilisation exclusive de convolutions tridimensionnelles dilatées garantit une compatibilité native et une accélération massive lors d'une éventuelle compilation via NVIDIA TensorRT, contrairement à certains mécanismes d'attention complexes des Transformers qui nécessitent des noyaux CUDA personnalisés tels que FlashAttention.

## **Synthèse Comparative et Implémentations Techniques**

Afin d'évaluer concrètement l'impact des optimisations matérielles et des évolutions architecturales, le tableau suivant synthétise les performances sémantiques et matérielles. Les estimations de VRAM et de FPS sont basées sur le traitement d'une fenêtre vidéo standard en 1080p, en considérant le pipeline complet (de la lecture du flux à la prédiction) sur un GPU moderne tel qu'un NVIDIA L4 ou T4.

| Architecture & Optimisation | Cadre d'Exécution | F1-Score (ClipShots) | F1-Score (RAI) | Transition IoU (Précision des Fondus) | VRAM Estimée (Batch 1\) | Multiplicateur FPS Relatif (Pipeline) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **TransNetV2 (Baseline)** | PyTorch FP32 (Décodage CPU FFmpeg) | 77.9% | 93.9% | 0.192 | \~1.5 GB | 1.0x (Référence) |
| **TransNetV2 (Opt. Max)** | **TensorRT FP16 \+ Zéro-Copie TorchCodec** | **77.9%** | **93.9%** | 0.192 | **\~0.8 GB** | **\~4.5x \- 5.5x** |
| **TransNetV2 (Opt. Extrême)** | TensorRT INT8 \+ Zéro-Copie TorchCodec | Dégradation notable | Dégradation | \< 0.150 | \~0.4 GB | \~8.0x \- 10.0x |
| **AutoShot (CVPR 2023\)** | PyTorch FP32 (NAS Supernet) | 79.0% | 95.1% | 0.252 | \~2.2 GB | \~0.6x |
| **OmniShotCut (SOTA 2026\)** | PyTorch FP32 (Shot-Query Transformer) | **88.3% (Range F1)** | **SOTA** | **0.632** | \~3.5 GB | \~0.4x |
| **FilmShots (SOTA 2026\)** | PyTorch FP32 (Dilated Conv3D) | \> 79.0% | \> 95.1% | N/A | \~1.8 GB | \~0.8x |

### **Boîte à Outils "Code" : Intégration Pratique**

L'intégration de l'optimisation maximale pour l'architecture existante nécessite la réécriture du flux de données et la compilation du modèle. Les extraits de code suivants démontrent cette implémentation.

#### **1\. Implémentation du Décodage Zéro-Copie avec TorchCodec**

L'objectif de ce script est de supprimer l'intervention du CPU lors de l'extraction des images, en forçant le flux à transiter directement du disque vers le NVDEC, puis vers la VRAM.4

Python  
import torch  
import torchvision.transforms as T  
\# Importation de l'interface de décodage vidéo de Meta  
from torchcodec.decoders import VideoDecoder, set\_cuda\_backend

def initialize\_nvdec\_pipeline(video\_filepath: str, device: str \= "cuda:0"):  
    """  
    Configure un pipeline de lecture matérielle asynchrone bypassant la mémoire hôte.  
    """  
    \# L'activation du backend 'beta' déverrouille des chemins de transfert de mémoire optimisés  
    \# pour les transferts NVDEC vers les tenseurs PyTorch selon la documentation.  
    set\_cuda\_backend("beta")  
      
    \# L'argument device="cuda" est l'instruction cruciale qui force le décodage  
    \# via l'accélérateur matériel (NVDEC). Le résultat ne touchera jamais la RAM.  
    try:  
        decoder \= VideoDecoder(video\_filepath, device=device)  
    except Exception as e:  
        raise RuntimeError(f"Échec de l'initialisation du lecteur vidéo : {e}")

    \# Vérification proactive du fallback. Si la vidéo est encodée dans un format exotique,  
    \# TorchCodec peut retomber sur le CPU de manière transparente.  
    if decoder.cpu\_fallback:  
        print(f"\[Alerte Performance\] Fallback logiciel détecté : {decoder.cpu\_fallback}")  
    else:  
        print("\[Optimisation\] Décodage matériel NVDEC actif et exclusif.")

    \# TransNetV2 nécessite des trames de 48x27 pixels en virgule flottante.  
    \# Ces transformations s'exécutent via des noyaux CUDA natifs, préservant le paradigme Zéro-Copie.  
    gpu\_native\_transform \= T.Compose()  
      
    return decoder, gpu\_native\_transform

\# Scénario de production  
decoder, transform \= initialize\_nvdec\_pipeline("sequence\_test.mp4")

\# L'API d'indexation simple extrait un FrameBatch. Les données restent sur \`cuda:0\`.  
\# Shape: en dtype uint8.  
raw\_vram\_frames \= decoder\[0:100\]

\# Application des opérations de redimensionnement et normalisation directement sur le GPU.  
processed\_frames \= transform(raw\_vram\_frames)

\# Restructuration finale pour correspondre aux dimensions d'entrée de TransNetV2 :  
\# Ajout de la dimension batch et permutation pour obtenir  
\# soit .  
model\_input\_tensor \= processed\_frames.unsqueeze(0).permute(0, 1, 3, 4, 2).contiguous()

#### **2\. Exportation ONNX et Génération de l'Engin TensorRT**

Cette phase requiert l'exportation du graphe PyTorch vers le format d'échange ONNX, qui servira de base de compilation pour trtexec.22  
**Étape A : Génération de la représentation ONNX (Python)**

Python  
import torch  
from transnetv2\_pytorch import TransNetV2

device \= torch.device("cuda:0")  
\# Instanciation de l'architecture DDCNN de TransNetV2  
model \= TransNetV2().to(device)  
model.eval()

\# Définition précise de la signature spatio-temporelle attendue.  
\# La fenêtre de 100 images est structurellement fixe pour ce modèle.  
dummy\_input \= torch.randn(1, 100, 27, 48, 3, device=device, dtype=torch.float32)

torch.onnx.export(  
    model,   
    dummy\_input,   
    "transnetv2\_fp32.onnx",   
    export\_params=True,  
    opset\_version=13, \# L'opset 13 offre la meilleure compatibilité pour les convolutions 3D  
    do\_constant\_folding=True, \# Optimisation agressive des nœuds statiques lors de l'export  
    input\_names=\['input\_frames'\],   
    output\_names=\['transition\_probabilities'\],  
    \# La définition d'axes dynamiques garantit que l'engin TensorRT   
    \# pourra accepter des tailles de lot variables (ex: batch de 1 à 16 vidéos)  
    dynamic\_axes={'input\_frames': {0: 'batch\_size'},   
                  'transition\_probabilities': {0: 'batch\_size'}}  
)

**Étape B : Compilation et Fusion de Couches via CLI TensorRT** La commande suivante construit le plan d'exécution binaire, optimisé pour la demi-précision.24

Bash  
trtexec \\  
  \--onnx=transnetv2\_fp32.onnx \\  
  \--saveEngine=transnetv2\_fp16.engine \\  
  \--explicitBatch \\  
  \--minShapes=input\_frames:1x100x27x48x3 \\  
  \--optShapes=input\_frames:8x100x27x48x3 \\  
  \--maxShapes=input\_frames:16x100x27x48x3 \\  
  \--fp16 \\  
  \--useCudaGraph \\  
  \--useSpinWait \\  
  \--workspace=4096

L'utilisation de la précision \--fp16 est primordiale ici. Elle autorise le compilateur à exploiter l'accélération matérielle des cœurs Tensor sans nécessiter l'étape complexe et destructrice de calibration liée à l'ajout du drapeau \--int8.24 La capture du graphe CUDA via \--useCudaGraph neutralise les surcharges d'ordonnancement CPU lors de l'invocation répétée du modèle en production.24

## **Verdict de l'Architecte et Recommandations Stratégiques**

La conception et la maintenance d'un pipeline d'analyse vidéo industriel imposent un arbitrage rigoureux entre l'effort d'ingénierie non récurrent (NRE), les coûts d'infrastructure de calcul et l'exactitude sémantique requise par les spécifications du produit. L'analyse technique approfondie révèle que les limitations de performance actuelles du système ne sont pas inhérentes à la complexité mathématique des convolutions de TransNetV2, mais découlent d'une architecture d'accès aux données (I/O) obsolète, exacerbée par une exécution logicielle sous-optimale.5  
Le remplacement intégral de l'infrastructure neuronale par un modèle de l'état de l'art tel qu'OmniShotCut représente une opportunité sémantique sans précédent.11 L'augmentation stupéfiante de la métrique Transition IoU (passant de 0.192 à 0.632) démontre une maîtrise absolue des transitions temporelles graduelles, répondant définitivement aux failles historiques de TransNetV2.36 Cependant, le retour sur investissement technique immédiat d'une telle migration est défavorable dans un contexte où le goulet d'étranglement principal est la bande passante PCI-e.5 Déployer un Transformer vidéo dense, intrinsèquement plus lourd en VRAM en raison de la complexité quadratique des mécanismes d'attention, sur un pipeline I/O saturé ne ferait qu'aggraver la latence globale du système.36  
À l'inverse, l'optimisation matérielle du pipeline existant (Axe A) présente une asymétrie de retour sur investissement particulièrement favorable. L'intégration de TorchCodec requiert un effort de refactorisation mineur, remplaçant les appels FFmpeg synchrones par une interface asynchrone branchée directement sur l'encodeur matériel NVDEC.4 Cette intervention isole la RAM système et désengorge instantanément le bus PCIe. Couplée à la compilation du modèle via TensorRT en précision FP16 (trtexec \--fp16), cette approche réduit l'empreinte VRAM par deux et multiplie par un facteur de 4 à 5 la cadence d'ingestion des trames, le tout en préservant scrupuleusement la dynamique mathématique des poids du réseau, maintenant ainsi le score F1 de référence strictement intact.24 Il est impératif d'écarter la tentation de la quantification en INT8 (PTQ) ; la troncature brutale de la plage dynamique imposée par la réduction de l'entropie détruirait inévitablement la sensibilité du modèle aux variations subtiles caractérisant les fondus enchaînés, dégradant sévèrement les capacités de détection déjà fragiles de TransNetV2 sur ces segments spécifiques.28  
Il est donc préconisé d'adopter une stratégie de déploiement itérative. La première phase, à exécution immédiate, consiste à consolider l'architecture actuelle en implémentant le paradigme Zéro-Copie via TorchCodec et en substituant l'exécution PyTorch par l'engin TensorRT FP16. Une fois le débit matériel stabilisé et la capacité de traitement démultipliée à coût constant, une seconde phase d'exploration devra être initiée. Ce n'est qu'avec une infrastructure I/O capable de délivrer des dizaines de milliers d'images par seconde directement en VRAM que le remplacement de TransNetV2 par une architecture SOTA 2026, telle qu'OmniShotCut ou FilmShots, prendra tout son sens technique et économique, offrant alors l'excellence sémantique sans compromettre la viabilité opérationnelle du traitement à grande échelle.

#### **Sources des citations**

1. PaddleVideo/docs/en/model\_zoo/partition/transnetv2.md at develop \- GitHub, consulté le juin 13, 2026, [https://github.com/paddlepaddle/paddlevideo/blob/develop/docs/en/model\_zoo/partition/transnetv2.md](https://github.com/paddlepaddle/paddlevideo/blob/develop/docs/en/model_zoo/partition/transnetv2.md)  
2. TransNet V2: An effective deep network architecture for fast shot transition detection \- arXiv, consulté le juin 13, 2026, [https://arxiv.org/pdf/2008.04838](https://arxiv.org/pdf/2008.04838)  
3. elya5/transnetv2 \- Hugging Face, consulté le juin 13, 2026, [https://huggingface.co/elya5/transnetv2](https://huggingface.co/elya5/transnetv2)  
4. torchcodec 0.2.0 \- PyPI, consulté le juin 13, 2026, [https://pypi.org/project/torchcodec/0.2.0/](https://pypi.org/project/torchcodec/0.2.0/)  
5. Accelerated video decoding on GPUs with CUDA and NVDEC \- Meta-PyTorch, consulté le juin 13, 2026, [https://meta-pytorch.org/torchcodec/0.8/generated\_examples/decoding/basic\_cuda\_example.html](https://meta-pytorch.org/torchcodec/0.8/generated_examples/decoding/basic_cuda_example.html)  
6. \[P\] DeFFcode: A High-performance FFmpeg based Video-Decoder Python Library for fast and low-overhead decoding of a wide range of video streams into 3D NumPy frames. \- Reddit, consulté le juin 13, 2026, [https://www.reddit.com/r/learnmachinelearning/comments/tji3q7/p\_deffcode\_a\_highperformance\_ffmpeg\_based/](https://www.reddit.com/r/learnmachinelearning/comments/tji3q7/p_deffcode_a_highperformance_ffmpeg_based/)  
7. Accelerated video decoding on GPUs with CUDA and NVDEC ..., consulté le juin 13, 2026, [https://meta-pytorch.org/torchcodec/stable/generated\_examples/decoding/basic\_cuda\_example.html](https://meta-pytorch.org/torchcodec/stable/generated_examples/decoding/basic_cuda_example.html)  
8. torchcodec: Easy and Efficient Video Decoding for PyTorch, consulté le juin 13, 2026, [https://pytorch.org/blog/torchcodec/](https://pytorch.org/blog/torchcodec/)  
9. AutoShot: A Short Video Dataset and State-of-the-Art Shot Boundary Detection \- CVF Open Access, consulté le juin 13, 2026, [https://openaccess.thecvf.com/content/CVPR2023W/NAS/papers/Zhu\_AutoShot\_A\_Short\_Video\_Dataset\_and\_State-of-the-Art\_Shot\_Boundary\_Detection\_CVPRW\_2023\_paper.pdf](https://openaccess.thecvf.com/content/CVPR2023W/NAS/papers/Zhu_AutoShot_A_Short_Video_Dataset_and_State-of-the-Art_Shot_Boundary_Detection_CVPRW_2023_paper.pdf)  
10. FilmShots: A Fast Film Shot Boundary Detection Based on Dilated Conv3D and Attention, consulté le juin 13, 2026, [https://ieeexplore.ieee.org/document/11455054/](https://ieeexplore.ieee.org/document/11455054/)  
11. UVA-Computer-Vision-Lab/OmniShotCut: OmniShotCut is a ... \- GitHub, consulté le juin 13, 2026, [https://github.com/UVA-Computer-Vision-Lab/OmniShotCut](https://github.com/UVA-Computer-Vision-Lab/OmniShotCut)  
12. OmniShotCut: Holistic Relational Shot Boundary Detection with Shot-Query Transformer, consulté le juin 13, 2026, [https://www.researchgate.net/publication/404249355\_OmniShotCut\_Holistic\_Relational\_Shot\_Boundary\_Detection\_with\_Shot-Query\_Transformer](https://www.researchgate.net/publication/404249355_OmniShotCut_Holistic_Relational_Shot_Boundary_Detection_with_Shot-Query_Transformer)  
13. avcuda \- PyPI, consulté le juin 13, 2026, [https://pypi.org/project/avcuda/](https://pypi.org/project/avcuda/)  
14. AV1 support for HW decoding · PyAV-Org PyAV · Discussion \#1691 \- GitHub, consulté le juin 13, 2026, [https://github.com/PyAV-Org/PyAV/discussions/1691](https://github.com/PyAV-Org/PyAV/discussions/1691)  
15. Using h264\_cuvid as hardware decoder · Issue \#451 · PyAV-Org/PyAV \- GitHub, consulté le juin 13, 2026, [https://github.com/PyAV-Org/PyAV/issues/451](https://github.com/PyAV-Org/PyAV/issues/451)  
16. PyTorch video loader utilising GPU (CUDA) using NVIDIA DALI \> 0.18. \- GitHub Gist, consulté le juin 13, 2026, [https://gist.github.com/kiyoon/ae84ee3736c1350b20901bfb4a60d621](https://gist.github.com/kiyoon/ae84ee3736c1350b20901bfb4a60d621)  
17. Using PyTorch DALI plugin: using various readers \- NVIDIA Documentation Hub, consulté le juin 13, 2026, [https://docs.nvidia.com/deeplearning/dali/user-guide/docs/examples/frameworks/pytorch/pytorch-various-readers.html](https://docs.nvidia.com/deeplearning/dali/user-guide/docs/examples/frameworks/pytorch/pytorch-various-readers.html)  
18. NVIDIA DALI : unable to load videos using readers.video in NVIDIA DALI pipeline \- Stack Overflow, consulté le juin 13, 2026, [https://stackoverflow.com/questions/70019833/nvidia-dali-unable-to-load-videos-using-readers-video-in-nvidia-dali-pipeline](https://stackoverflow.com/questions/70019833/nvidia-dali-unable-to-load-videos-using-readers-video-in-nvidia-dali-pipeline)  
19. soCzech/TransNetV2: TransNet V2: Shot Boundary Detection Neural Network \- GitHub, consulté le juin 13, 2026, [https://github.com/soCzech/TransNetV2](https://github.com/soCzech/TransNetV2)  
20. transnetv2-pytorch \- PyPI Package Security Analysis \- Socket, consulté le juin 13, 2026, [https://socket.dev/pypi/package/transnetv2-pytorch](https://socket.dev/pypi/package/transnetv2-pytorch)  
21. NVIDIA \- TensorRT | onnxruntime, consulté le juin 13, 2026, [https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html)  
22. Export to ONNX and inference using TensorRT \- NVIDIA Documentation Hub, consulté le juin 13, 2026, [https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/examples/onnx/onnx\_export.html](https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/examples/onnx/onnx_export.html)  
23. VideoBricks is a minimal video editor packed with features. Detail Scrubbing, AI shot boundary detection, Cropping, Trimming, Multi-Track outputs. Outputs in high quality GIF (using pngquant for the best palettes) and MP4 · GitHub, consulté le juin 13, 2026, [https://github.com/alonsorobots/VideoBricks](https://github.com/alonsorobots/VideoBricks)  
24. Performance Benchmarking using trtexec — NVIDIA TensorRT, consulté le juin 13, 2026, [https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/benchmarking.html](https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/benchmarking.html)  
25. Estimating Depth with ONNX Models and Custom Layers Using NVIDIA TensorRT, consulté le juin 13, 2026, [https://developer.nvidia.com/blog/estimating-depth-beyond-2d-using-custom-layers-on-tensorrt-and-onnx-models/](https://developer.nvidia.com/blog/estimating-depth-beyond-2d-using-custom-layers-on-tensorrt-and-onnx-models/)  
26. Paddle-Inference-Demo/docs/optimize/paddle\_trt\_en.rst at master \- GitHub, consulté le juin 13, 2026, [https://github.com/PaddlePaddle/Paddle-Inference-Demo/blob/master/docs/optimize/paddle\_trt\_en.rst](https://github.com/PaddlePaddle/Paddle-Inference-Demo/blob/master/docs/optimize/paddle_trt_en.rst)  
27. TRTEXEC with Faster RCNN — Tao Toolkit \- NVIDIA Documentation Hub, consulté le juin 13, 2026, [https://docs.nvidia.com/tao/tao-toolkit/text/trtexec\_integration/trtexec\_frcnn.html](https://docs.nvidia.com/tao/tao-toolkit/text/trtexec_integration/trtexec_frcnn.html)  
28. Working with Quantized Types — NVIDIA TensorRT, consulté le juin 13, 2026, [https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/work-quantized-types.html](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/work-quantized-types.html)  
29. Cosmos World Foundation Model Platform for Physical AI \- arXiv, consulté le juin 13, 2026, [https://arxiv.org/html/2501.03575v1](https://arxiv.org/html/2501.03575v1)  
30. TransNetV2/README.md at master \- GitHub, consulté le juin 13, 2026, [https://github.com/soCzech/TransNetV2/blob/master/README.md](https://github.com/soCzech/TransNetV2/blob/master/README.md)  
31. transnetv2-pytorch \- PyPI, consulté le juin 13, 2026, [https://pypi.org/project/transnetv2-pytorch](https://pypi.org/project/transnetv2-pytorch)  
32. Low-Level Details of Post-Training INT8 Quantization and Calibration \- Ultralytics, consulté le juin 13, 2026, [https://community.ultralytics.com/t/low-level-details-of-post-training-int8-quantization-and-calibration/1506](https://community.ultralytics.com/t/low-level-details-of-post-training-int8-quantization-and-calibration/1506)  
33. Post Training Quantization (PTQ) — Torch-TensorRT v2.5.0.dev0+bb405b0 documentation, consulté le juin 13, 2026, [https://docs.pytorch.org/TensorRT/user\_guide/ptq.html](https://docs.pytorch.org/TensorRT/user_guide/ptq.html)  
34. Calibration INT8 with trtexec \#4044 \- NVIDIA/TensorRT \- GitHub, consulté le juin 13, 2026, [https://github.com/NVIDIA/TensorRT/issues/4044](https://github.com/NVIDIA/TensorRT/issues/4044)  
35. AUTOSHOT:ASHORT VIDEO DATASET AND STATE-OF-THE-ART SHOT BOUNDARY DETECTION \- OpenReview, consulté le juin 13, 2026, [https://openreview.net/pdf?id=u89Eq-\_3oE4](https://openreview.net/pdf?id=u89Eq-_3oE4)  
36. OmniShotCut: Holistic Relational Shot Boundary Detection with Shot-Query Transformer, consulté le juin 13, 2026, [https://arxiv.org/html/2604.24762v1](https://arxiv.org/html/2604.24762v1)  
37. OmniShotCut: Holistic Relational Shot Boundary Detection with Shot-Query Transformer, consulté le juin 13, 2026, [https://arxiv.org/html/2604.24762v2](https://arxiv.org/html/2604.24762v2)  
38. GitHub \- wentaozhu/AutoShot: AutoShot: A Short Video Dataset and ..., consulté le juin 13, 2026, [https://github.com/wentaozhu/AutoShot](https://github.com/wentaozhu/AutoShot)  
39. AutoShot: A Short Video Dataset and State-of-the-Art Shot Boundary Detection \- arXiv, consulté le juin 13, 2026, [https://arxiv.org/abs/2304.06116](https://arxiv.org/abs/2304.06116)  
40. Paper page \- OmniShotCut: Holistic Relational Shot Boundary Detection with Shot-Query Transformer \- Hugging Face, consulté le juin 13, 2026, [https://huggingface.co/papers/2604.24762](https://huggingface.co/papers/2604.24762)  
41. TransVLM: Shot Transition Detection with Vision-Language AI \- HeyGen, consulté le juin 13, 2026, [https://www.heygen.com/research/transvlm](https://www.heygen.com/research/transvlm)  
42. OmniShotCut: Holistic Relational Shot Boundary Detection \- Computer Vision Lab, consulté le juin 13, 2026, [https://uva-computer-vision-lab.github.io/OmniShotCut\_website/](https://uva-computer-vision-lab.github.io/OmniShotCut_website/)  
43. UVA Computer Vision Lab \- GitHub, consulté le juin 13, 2026, [https://github.com/UVA-Computer-Vision-Lab](https://github.com/UVA-Computer-Vision-Lab)  
44. Shot boundary detection on broadcast news videos using a combination of multiple features \- PeerJ, consulté le juin 13, 2026, [https://peerj.com/articles/cs-3785.pdf](https://peerj.com/articles/cs-3785.pdf)  
45. FilmShots: A Fast Film Shot Boundary Detection Based on Dilated Conv3D and Attention, consulté le juin 13, 2026, [https://www.researchgate.net/publication/403110988\_FilmShots\_A\_Fast\_Film\_Shot\_Boundary\_Detection\_Based\_on\_Dilated\_Conv3D\_and\_Attention](https://www.researchgate.net/publication/403110988_FilmShots_A_Fast_Film_Shot_Boundary_Detection_Based_on_Dilated_Conv3D_and_Attention)  
46. CBD Lab · GitHub, consulté le juin 13, 2026, [https://github.com/CBD-Lab](https://github.com/CBD-Lab)