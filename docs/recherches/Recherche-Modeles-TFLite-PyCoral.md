# **Optimisation Stratégique des Architectures TensorFlow Lite pour Google Coral Edge TPU : Ingénierie du Post-Traitement et Gestion des Tenseurs Quantifiés**

L'émergence de l'intelligence artificielle en périphérie de réseau, communément appelée Edge AI, a fondamentalement redéfini les paradigmes de traitement de la vision par ordinateur. Dans ce contexte, l'accélérateur Google Coral Edge TPU (Tensor Processing Unit) s'est imposé comme une solution matérielle de référence, offrant des capacités de calcul asymétriques atteignant quatre billions d'opérations par seconde (4 TOPS) pour une enveloppe thermique et énergétique exceptionnellement basse, typiquement mesurée autour de 2 watts1. Cependant, l'exploitation maximale de cette architecture de circuit intégré spécifique à une application (ASIC) requiert une adéquation algorithmique d'une rigueur absolue. L'architecture ne pardonne aucune déviation par rapport à ses contraintes structurelles : les modèles de réseaux de neurones doivent être intégralement quantifiés en nombres entiers (généralement sur 8 bits, int8 ou uint8), leurs dimensions tensorielles doivent être statiques lors de la compilation, et les opérations mathématiques sous-jacentes doivent figurer dans le registre d'instructions supporté par le matériel3.  
Le déploiement de modèles de détection d'objets, tels que les architectures Single Shot MultiBox Detector (SSD) ou EfficientDet, met en exergue une problématique d'ingénierie complexe : la gestion du post-traitement algorithmique. Ce rapport d'expertise technique propose une analyse exhaustive des écosystèmes de modèles pré-compilés, évaluant spécifiquement les alternatives permettant de restreindre le volume de détections générées tout en préservant le format d'entrée optimal en uint8. En explorant les mécaniques internes du nœud TFLite\_Detection\_PostProcess, la sérialisation des schémas FlatBuffers et FlexBuffers, ainsi que les coûts computationnels relatifs aux conversions de types de données, cette étude apporte une réponse définitive quant à l'existence et à la pertinence de modèles alternatifs capables de satisfaire des contraintes de flux vidéo en temps réel.

## **Évaluation Exhaustive des Écosystèmes de Modèles Pré-compilés**

Le processus de détection d'objets sur un accélérateur Edge TPU ne se limite pas à la simple propagation avant (forward pass) à travers les couches convolutionnelles. Il englobe également le décodage des ancres (anchor decoding) et la suppression des non-maxima (Non-Maximum Suppression, NMS). Le choix du modèle pré-compilé détermine intrinsèquement la répartition de cette charge de travail entre le coprocesseur TPU et le processeur central (CPU) de l'hôte.

### **Analyse des Modèles Standard de la Fondation Google Coral**

Les investigations initiales sur les modèles disponibles mettent en évidence des disparités majeures dans la structure des graphes d'inférence. Le modèle efficientdet\_lite1.tflite, quantifié en uint8, constitue souvent le point de départ des développements grâce à sa compatibilité immédiate avec les environnements d'exécution tels que l'API PyCoral5. Ce modèle intègre nativement le nœud TFLite\_Detection\_PostProcess, lequel encapsule l'algorithme NMS et limite les prédictions à un maximum de 25 objets spatiaux.  
Néanmoins, d'autres itérations de la même famille, à l'instar de efficientdet\_lite0.tflite ou de ssd\_mobilenet\_v3.tflite dans leurs versions brutes, sont distribuées sans ce nœud de post-traitement6. Ces architectures renvoient des tenseurs bruts (souvent des milliers de propositions de boîtes englobantes), déléguant l'intégralité du traitement géométrique à l'application logicielle en aval. Sur des dispositifs embarqués comme le Raspberry Pi, l'implémentation d'un algorithme NMS en Python pur ou via des appels NumPy asynchrones induit une pénalité de latence inacceptable, fragmentant le pipeline d'inférence.  
Une exploration approfondie des dépôts de développement de Google Coral, et plus spécifiquement du répertoire test\_data hébergé sur les forges logicielles officielles, révèle l'existence de plusieurs modèles alternatifs pré-compilés et optimisés qui n'apparaissent pas toujours dans la vitrine principale du Model Zoo8. Parmi ces spécimens, le modèle ssd\_mobilenet\_v2\_coco\_quant\_postprocess\_edgetpu.tflite se distingue comme un standard de facto pour de nombreuses applications de vidéosurveillance intégrées, telles que le projet Frigate NVR9. Ce modèle accepte des tenseurs d'entrée en uint8, dispose de l'opérateur de post-traitement intégré, mais plafonne généralement son vecteur de sortie à 20 ou 25 détections, selon le processus exact d'exportation de l'API TensorFlow Object Detection.  
Un autre candidat de très haute performance découvert dans ces dépôts est le modèle ssdlite\_mobiledet\_coco\_qat\_postprocess\_edgetpu.tflite13. Construit sur l'architecture MobileDet, ce réseau a fait l'objet d'un entraînement conscient de la quantification (Quantization-Aware Training, QAT), offrant un rapport précision-vitesse exceptionnel. Sur des processeurs ARM accompagnés de l'Edge TPU, ce modèle peut soutenir des cadences de traitement atteignant 50 trames par seconde17. Toutefois, à l'instar de ses homologues, sa configuration interne fixe un nombre de détections génériques (souvent 10 ou 20\) sans offrir de granularité fine pour une limitation matérielle à 3 ou 5 objets.

### **Les Modèles PINTO : Une Fausse Bonne Idée pour l'Inférence à Haute Vitesse**

Face à l'absence de modèles Google configurés pour renvoyer un très faible nombre d'objets, la communauté se tourne fréquemment vers le répertoire de modèles PINTO. L'inspection de la topologie de ces modèles, notamment les variantes ssdlite\_mobilenet\_v2\_coco\_300\_integer\_quant\_with\_postprocess.tflite, confirme l'inclusion salvatrice du nœud TFLite\_Detection\_PostProcess et révèle une configuration interne limitant les sorties à 10 détections (max\_detections=10)18.  
Cependant, ces modèles présentent un défaut structurel majeur qui compromet irrémédiablement leur viabilité dans un pipeline de traitement vidéo à faible latence : l'exigence d'un tenseur d'entrée de type virgule flottante 32 bits (float32)20.  
La littérature scientifique traitant des benchmarks d'intelligence artificielle en périphérie documente rigoureusement l'impact de ces choix architecturaux4. Les flux vidéo extraits de périphériques Video4Linux (V4L2) ou traités par des bibliothèques de décodage matériel telles que GStreamer fournissent des matrices d'images non signées sur 8 bits (uint8). Imposer un modèle exigeant du float32 contraint le processeur hôte (CPU) à allouer dynamiquement un nouveau tampon mémoire, multipliant l'empreinte mémoire par quatre, puis à itérer sur des centaines de milliers de pixels pour appliquer une opération de normalisation arithmétique (généralement une soustraction de la moyenne suivie d'une division par la déviation standard)22.

| Modèle de Détection Pré-compilé | Source du Dépôt | Format d'Entrée Exigé | Statut du Nœud NMS | Limite Typique de Détections | Performance Théorique Globale |
| :---- | :---- | :---- | :---- | :---- | :---- |
| efficientdet\_lite1 | Coral Zoo | uint8 | Intégré | 25 | Optimale (Pipeline natif 8-bits) |
| ssd\_mobilenet\_v3 | Coral Zoo | uint8 | Absent | N/A (Tenseurs bruts) | Mauvaise (Post-traitement asynchrone) |
| ssd\_mobilenet\_v2\_coco\_quant\_postprocess\_edgetpu | Coral test\_data | uint8 | Intégré | 20 / 25 | Optimale (Standard industriel) |
| ssdlite\_mobiledet\_coco\_qat\_postprocess\_edgetpu | Coral test\_data | uint8 | Intégré | 10 / 20 | Excellente (Optimisation QAT) |
| ssdlite\_mobilenet\_v2\_coco\_300 | PINTO Zoo | float32 | Intégré | 10 | Médiocre (Goulot CPU pré-traitement) |

Cette conversion de type (casting) et cette normalisation, exécutées de manière séquentielle sur un processeur ARM Cortex-A embarqué, introduisent une pénalité de latence allant de 2 à 10 millisecondes par trame2. Considérant que le temps d'inférence pur du Coral Edge TPU pour une architecture SSD MobileNet avoisine les 8 à 12 millisecondes9, l'ajout d'une telle charge sur le CPU anéantit le bénéfice matériel de l'accélérateur. L'utilisation des modèles PINTO, bien qu'ils restreignent le nombre d'objets à 10, est donc une solution paradoxale qui dégrade l'efficacité énergétique et temporelle du système.

### **Réponse Analytique au Besoin Spécifique**

L'analyse de l'infrastructure globale permet de répondre de manière définitive à l'interrogation concernant l'existence de modèles pré-compilés alternatifs qui accepteraient nativement du uint8 tout en plafonnant spécifiquement les détections à une poignée d'objets (3 ou 5). **Il n'existe, dans les dépôts publics officiels ou communautaires de référence, aucun modèle de détection pré-compilé répondant exactement à cette combinatoire.** Les architectes de modèles standardisent les sorties à 10, 20, 25 ou 100 objets afin de maximiser le rappel (recall) sur les jeux de données complexes comme COCO5. Restreindre artificiellement le graphe pré-compilé à 3 objets réduit l'utilisabilité générale du modèle pour la communauté, justifiant ainsi l'absence de tels binaires "prêts à l'emploi".  
Dès lors, l'optimisation doit se faire par le biais d'un arbitrage entre l'adaptation du code applicatif et la rétro-ingénierie du graphe d'inférence.

## **Mécanique Computationnelle : Le Faux Avantage de la Limitation NMS Interne**

Pour justifier le choix de l'architecture logicielle, il est fondamental de déconstruire le mythe selon lequel limiter un modèle TensorFlow Lite à 5 détections via son nœud interne accélérerait significativement le traitement par rapport à un modèle configuré pour 25 détections, filtré ensuite en Python.

### **La Charge de Calcul de TFLite\_Detection\_PostProcess**

L'opération TFLite\_Detection\_PostProcess est une routine d'une immense complexité algorithmique. Contrairement aux couches convolutionnelles qui sont projetées sur la matrice systolique de l'Edge TPU, cet opérateur est catégoriquement refusé par le compilateur Edge TPU et systématiquement relégué au processeur central de la machine hôte24. Le compilateur génère un graphe hybride où le bloc edgetpu-custom-op exécute le réseau de neurones sur l'ASIC, puis les tenseurs résultants sont rapatriés dans la mémoire RAM principale pour que le CPU exécute le post-traitement3.  
L'algorithme NMS opère en plusieurs phases intensives :

1. **Décodage spatial** : Les vecteurs de sortie bruts du réseau (parfois plus de 10 000 prédictions pour des modèles comme EfficientDet)7 sont mathématiquement traduits en coordonnées cartésiennes absolues à l'aide des boîtes d'ancrage préalablement définies.  
2. **Filtrage par seuil de confiance** : Toutes les boîtes dont la probabilité d'appartenir à une classe est inférieure à un paramètre score\_threshold (souvent très bas, de l'ordre de 0.01 ou ![][image1]) sont écartées18.  
3. **Tri heuristique** : Les boîtes restantes sont triées par ordre décroissant de confiance. Cette opération de tri présente une complexité temporelle de ![][image2].  
4. **Suppression spatiale (IoU)** : L'algorithme itère sur la boîte la plus confiante, calcule l'Intersection sur Union (IoU) géométrique avec toutes les boîtes superposées, et supprime celles qui excèdent le iou\_threshold18. L'opération est répétée jusqu'à épuisement des candidats ou jusqu'à l'atteinte du paramètre max\_detections.

### **Évaluation du Coût de Slicing vs NMS**

L'hypothèse selon laquelle abaisser max\_detections de 25 à 5 réduirait considérablement le travail du CPU est erronée. La quasi-totalité du temps d'exécution de l'algorithme NMS est accaparée par les étapes 1, 2 et 37. L'étape de suppression spatiale (étape 4\) s'arrêtera certes plus tôt si le plafond est fixé à 5, mais sur un vecteur déjà trié, cette économie se chiffre en microsecondes.  
En contrepartie, si l'on utilise un modèle pré-compilé générant 25 objets, le code Python de l'application reçoit une liste de 25 éléments. Appliquer une troncature via l'opération de slicing objs\[:5\] est une manipulation de pointeurs en mémoire dont la complexité algorithmique est ![][image3] par rapport à la taille originale de la liste. Cette opération ne requiert aucun calcul arithmétique flottant et s'exécute en quelques nanosecondes.  
La conclusion analytique est implacable : l'utilisation du filtrage Python objs\[:max\_results\] combinée à un modèle natif en uint8 tel que efficientdet\_lite1.tflite ou ssd\_mobilenet\_v2\_coco\_quant\_postprocess\_edgetpu.tflite représente l'optimum absolu en matière de performance, d'efficacité énergétique et de simplicité d'intégration logicielle.

## **Ingénierie Inverse et Modification des Paramètres Internes (FlatBuffers & FlexBuffers)**

Bien que la recommandation stratégique s'oriente vers le filtrage logiciel, certaines architectures logicielles embarquées (particulièrement celles développées en C/C++ strict sous des contraintes de mémoire statique) requièrent impérativement un modèle dont le graphe d'inférence ne produit qu'un nombre restreint de tenseurs de sortie. Dans ce cas de figure, modifier les modèles existants sans avoir à les ré-entraîner de zéro devient nécessaire. Le framework TensorFlow Lite repose sur une architecture de sérialisation complexe impliquant les technologies FlatBuffers et FlexBuffers.

### **L'Architecture de Sérialisation FlatBuffers**

Les fichiers .tflite ne sont pas des archives ou des structures de données dynamiques, mais des représentations binaires hautement alignées générées par le compilateur FlatBuffers27. Contrairement aux Protocol Buffers (Protobuf) historiquement utilisés par TensorFlow (.pb), FlatBuffers permet au runtime d'accéder directement aux poids et aux métadonnées des nœuds en lisant la mémoire sans aucune étape d'allocation, de parsing ou de désérialisation préalable28.  
Cette sérialisation est régie par un schéma explicite nommé schema.fbs19. Pour les opérations mathématiques intégrées au standard (les Builtin Operators comme les convolutions ou le MaxPool), le schéma définit de manière stricte les paramètres associés, permettant au compilateur de générer un code C++ d'accès direct très optimisé28.

### **L'Enigme des Custom Options et FlexBuffers**

Le défi technique réside dans le fait que TFLite\_Detection\_PostProcess n'est pas un opérateur intégré standard, mais un "Custom Operator" (opérateur personnalisé)29. Étant donné qu'un opérateur personnalisé peut nécessiter des paramètres arbitraires inconnus lors de la conception du schéma principal de TensorFlow Lite, ses options ne sont pas encodées sous forme de champs statiques28.  
À la place, les paramètres tels que max\_detections, max\_classes\_per\_detection, ou nms\_score\_threshold sont sérialisés dans un champ générique nommé custom\_options32. Pour structurer ces paramètres à l'intérieur de ce tableau d'octets opaque, TensorFlow Lite utilise une technologie secondaire appelée **FlexBuffers**29.  
FlexBuffers est une variante "sans schéma" (schema-less) de FlatBuffers. Il fonctionne de manière conceptuellement similaire au format JSON, permettant de stocker des dictionnaires de paires clé-valeur avec une empreinte binaire ultra-compacte33. Le code source C++ qui initialise l'opérateur de post-traitement illustre cette mécanique d'extraction :

C++  
void\* Init(TfLiteOpaqueContext\* context, const char\* buffer, size\_t length) {  
    auto\* op\_data \= new OpData;  
    const uint8\_t\* buffer\_t \= reinterpret\_cast\<const uint8\_t\*\>(buffer);  
    const flexbuffers::Map& m \= flexbuffers::GetRoot(buffer\_t, length).AsMap();  
    op\_data-\>max\_detections \= m\["max\_detections"\].AsInt32();  
    op\_data-\>max\_classes\_per\_detection \= m\["max\_classes\_per\_detection"\].AsInt32();  
    // ...  
}

29

### **Procédure de Rétro-ingénierie et de Modification Binaire**

La modification directe de la valeur max\_detections au sein d'un modèle .tflite pré-compilé exige la déconstruction de ces deux couches de sérialisation superposées. La méthodologie repose sur l'utilisation du compilateur flatc19.

1. **Compilation de l'Outil Flatc** : L'environnement de développement doit compiler la version exacte de flatc correspondant à la version de TensorFlow Lite ciblée, afin d'éviter les décalages de schéma19.  
2. **Extraction du Modèle en JSON** : Le modèle binaire detect.tflite est converti en une représentation textuelle JSON.  
   Bash  
   ./flatc \-t \--strict-json \--defaults-json \-o . schema.fbs \-- detect.tflite

   \[cite: 19\]  
3. **Analyse du Graphe et Identification du Nœud** : Le fichier JSON généré contient un tableau "subgraphs". L'opérateur de post-traitement doit être localisé, généralement identifié par son "opcode\_index" pointant vers la définition de l'opérateur personnalisé19.  
4. **Manipulation du FlexBuffer** : Sous cet opérateur, le champ "custom\_options" se présente comme un tableau d'entiers représentant les octets du FlexBuffer (par exemple : \[1, 0, 0, 0, 2, 0, 0, 0...\])19. Modifier le paramètre max\_detections implique de trouver la valeur hexadécimale exacte encodant ce paramètre dans la structure FlexBuffers et de la remplacer par la nouvelle valeur (par exemple, remplacer l'octet représentant 25 par l'octet représentant 5).  
5. **Re-sérialisation** : Une fois la valeur modifiée, le fichier JSON est recompilé en binaire .tflite via flatc19.

Cette procédure est d'une complexité notable et présente des risques de corruption de la structure binaire, notamment si la nouvelle valeur nécessite une altération de l'alignement des bits (bit-width) imposée par les contraintes d'efficacité de FlexBuffers33. Bien qu'elle permette de manipuler des modèles pré-compilés inaccessibles par d'autres moyens, elle doit être réservée à des cas de force majeure en ingénierie inverse.

## **Recompilation Orthodose via l'API TensorFlow Object Detection et Model Maker**

Face aux risques inhérents à l'altération binaire, l'approche préconisée par l'industrie de l'intelligence artificielle pour ajuster la topologie de sortie d'un modèle implique la recompilation canonique du graphe, préalable à la délégation Edge TPU.

### **Re-Génération par Scripts d'Exportation TensorFlow**

L'architecture historique de la TensorFlow Object Detection API repose sur la conversion d'un point de sauvegarde d'entraînement (checkpoint) en un graphe figé (frozen graph), puis en un modèle quantifié20. Les poids du réseau demeurent inchangés ; seule la structure du post-traitement est redéfinie.  
Le script export\_tflite\_ssd\_graph.py (ou son équivalent TF2) expose explicitement les variables conditionnant le nœud NMS. En modifiant l'argument de ligne de commande \--max\_detections, le développeur instruit l'interface de programmation d'encoder directement la nouvelle limite dans le dictionnaire FlexBuffers généré18.

Bash  
python3 object\_detection/export\_tflite\_ssd\_graph.py \\  
    \--pipeline\_config\_path=pipeline.config \\  
    \--trained\_checkpoint\_prefix=model.ckpt \\  
    \--output\_directory=output\_dir \\  
    \--add\_postprocessing\_op=true \\  
    \--max\_detections=5

18  
Le graphe résultant doit ensuite subir la conversion finale vers le format TFLite via le convertisseur TOCO, en appliquant les paramètres stricts de quantification (--inference\_type=QUANTIZED\_UINT8 ou équivalents) et en stipulant les opérations personnalisées via le flag \--allow\_custom\_ops20. Finalement, l'invocation du compilateur edgetpu\_compiler générera un binaire matériellement accéléré.

### **Utilisation Moderne de TensorFlow Lite Model Maker**

Pour la gamme des réseaux EfficientDet-Lite, Google a significativement modernisé cette chaîne d'outils via la bibliothèque **TensorFlow Lite Model Maker**5. Cette librairie abstraite la complexité des scripts d'exportation historiques en offrant une interface de programmation orientée objet en Python.  
Model Maker permet de redéfinir les paramètres du graphe, y compris la limite des détections, tout en gérant automatiquement le processus de quantification post-entraînement (PTQ) pour assurer la compatibilité matérielle5. La configuration de la limite s'effectue directement sur l'objet de spécification du modèle :

Python  
from tflite\_model\_maker import model\_spec  
from tflite\_model\_maker import object\_detector

\# Instanciation de la spécification de l'architecture  
spec \= model\_spec.get('efficientdet\_lite1')

\# Redéfinition du paramètre NMS contrôlant la sérialisation FlexBuffers  
spec.config.max\_output\_size \= 5

\# Dans certaines itérations de l'API, la redéfinition globale est exigée  
\# spec \= object\_detector.EfficientDetLite1Spec(..., tflite\_max\_detections=5)

\# L'exportation gère de manière transparente la quantification int8/uint8  
model.export(export\_dir='/tmp/')

43  
L'approche Model Maker présente l'immense avantage de garantir la conformité typologique du tenseur d'entrée (qui demeure optimalement orienté vers une ingestion d'image non signée en 8 bits) et d'automatiser l'insertion du nœud TFLite\_Detection\_PostProcess avec des paramètres validés.

## **L'Impact Mémoire des Tenseurs de Sortie**

Il est pertinent d'analyser l'impact réel de la réduction du paramètre max\_detections sur les allocations de la mémoire statique de l'accélérateur et de l'hôte. Lors de la phase d'initialisation de l'interpréteur TensorFlow Lite (Interpreter::AllocateTensors()), le moteur d'exécution réserve des blocs de mémoire (le Tensor Arena) pour accueillir les vecteurs de sortie28.  
Les modèles incluant le nœud NMS produisent généralement quatre tenseurs de sortie structurellement définis par le paramètre ![][image4] (représentant max\_detections)6 :

* **Boîtes englobantes** : Tenseur dimensionné à \[1, N, 4\] de type float32.  
* **Identifiants de classes** : Tenseur dimensionné à \[1, N\] de type float32.  
* **Scores de confiance** : Tenseur dimensionné à \[1, N\] de type float32.  
* **Compteur de détections valides** : Scalaire dimensionné à \[1\] de type float32.

Réduire ![][image4] de 25 à 5 divise mécaniquement par cinq la taille de ces matrices. Pour les coordonnées des boîtes (![][image5] octets au lieu de ![][image6] octets), la mémoire vive économisée se chiffre à environ 320 octets de RAM17. Sur des architectures de microcontrôleurs à mémoire statique très limitée (SRAM de quelques centaines de kilo-octets) exploitant des frameworks embarqués, cette économie peut s'avérer cruciale28. Cependant, dans l'immense majorité des cas d'utilisation impliquant un accélération via USB Coral ou PCIe (opérant sur des architectures ARM ou x86 pourvues de plusieurs gigaoctets de mémoire DDR4), cette allocation est virtuellement infinitésimale et n'impacte en rien la vélocité du cache du processeur central.

## **Synthèse et Recommandations Finales**

Les impératifs d'optimisation d'un pipeline de détection d'objets sur le Google Coral Edge TPU nécessitent une compréhension granulaire des architectures tensorielles et des contraintes inhérentes au post-traitement asynchrone. L'analyse détaillée des dépôts de modèles, des processus de sérialisation et des coûts computationnels autorise l'énonciation des recommandations suivantes :

1. **Rejet des architectures exigeant une conversion flottante** : L'utilisation de modèles pré-compilés exigeant un tenseur d'entrée float32 (tels que certaines variantes du PINTO Model Zoo) est catégoriquement déconseillée pour des performances en temps réel20. La charge de normalisation imposée au CPU hôte crée un goulot d'étranglement sévère qui neutralise l'accélération fournie par l'Edge TPU, dégradant la latence globale du système4. L'ingestion directe de trames vidéo en uint8 doit demeurer le standard non négociable.  
2. **Inexistence de modèles pré-compilés répondant à des contraintes de niche** : La recherche exhaustive au sein des ressources communautaires et des dépôts officiels (google-coral/test\_data) certifie l'absence de modèles pré-compilés combinant nativement une entrée uint8, l'intégration du nœud NMS, et une limite dure fixée à un volume d'objets marginal (3 ou 5). Les standards de l'industrie fixent ces paramètres à des valeurs de rappel maximal (10, 20 ou 25 objets)5.  
3. **Optimalité du filtrage logiciel** : La tentative de réduire la valeur max\_detections au sein du nœud d'inférence afin d'alléger la charge de travail du CPU est fondée sur un postulat mathématique erroné. L'opérateur TFLite\_Detection\_PostProcess exécute la majorité de son tri heuristique en amont de la coupure de la boucle spatiale20. Par conséquent, exploiter un modèle natif en uint8 générant 25 détections (tel que efficientdet\_lite1.tflite ou ssd\_mobilenet\_v2\_coco\_quant\_postprocess\_edgetpu.tflite) et limiter les résultats via un découpage de pointeurs en Python (objs\[:5\]) est la stratégie offrant le meilleur ratio performance-complexité d'implémentation.  
4. **Recompilation ciblée pour des contraintes matérielles strictes** : Si l'architecture logicielle de l'hôte (par exemple, des routines C++ aux tampons mémoire rigides) interdit formellement le tri logiciel a posteriori, la recompilation du modèle s'impose. L'altération des structures FlatBuffers/FlexBuffers par ingénierie inverse via l'outil flatc19 demeure une solution techniquement fascinante mais fragile. La méthodologie préconisée repose sur l'utilisation du framework TensorFlow Lite Model Maker, permettant de ré-exporter proprement l'architecture EfficientDet-Lite avec des spécifications de post-traitement rigoureuses tout en maintenant l'intégrité de la quantification nécessaire au processeur TPU43.

#### **Sources des citations**

1. Optimize AI inference with Google Coral Edge TPU \- Viam Codelabs, [https://codelabs.viam.com/guide/coral/index.html?index=..%2F..index](https://codelabs.viam.com/guide/coral/index.html?index=../..index)  
2. Google Coral TPU: Accelerating AI Projects on Raspberry Pi \- Zbotic, [https://zbotic.in/google-coral-tpu-accelerating-ai-projects-on-raspberry-pi/](https://zbotic.in/google-coral-tpu-accelerating-ai-projects-on-raspberry-pi/)  
3. Efficient Edge Deployment Demonstrated on YOLOv5 and Coral Edge TPU \- ResearchGate, [https://www.researchgate.net/publication/362253028\_Efficient\_Edge\_Deployment\_Demonstrated\_on\_YOLOv5\_and\_Coral\_Edge\_TPU](https://www.researchgate.net/publication/362253028_Efficient_Edge_Deployment_Demonstrated_on_YOLOv5_and_Coral_Edge_TPU)  
4. Benchmarking Machine Learning on Avnet's MaaXBoard \- element14 Community, [https://community.element14.com/products/devtools/single-board-computers/b/blog/posts/benchmarking-machine-learning-on-avnet-s-maaxboard](https://community.element14.com/products/devtools/single-board-computers/b/blog/posts/benchmarking-machine-learning-on-avnet-s-maaxboard)  
5. Object Detection with TensorFlow Lite Model Maker | Google AI Edge, [https://developers.google.com/edge/litert/libraries/modify/object\_detection](https://developers.google.com/edge/litert/libraries/modify/object_detection)  
6. TFLite\_Detection\_PostProcess produces invalid bounding box coordinates \#53713 \- GitHub, [https://github.com/tensorflow/tensorflow/issues/53713](https://github.com/tensorflow/tensorflow/issues/53713)  
7. Understanding Post-processing Operation for Compiled Models · Issue \#560 · google-coral/edgetpu \- GitHub, [https://github.com/google-coral/edgetpu/issues/560](https://github.com/google-coral/edgetpu/issues/560)  
8. GitHub \- google-coral/test\_data: Trained and compiled TF Lite models, and other testing data for Coral devices, [https://github.com/google-coral/test\_data](https://github.com/google-coral/test_data)  
9. Coral TPU \- Poor confidence % for detecting : r/frigate\_nvr \- Reddit, [https://www.reddit.com/r/frigate\_nvr/comments/1iovcmk/coral\_tpu\_poor\_confidence\_for\_detecting/](https://www.reddit.com/r/frigate_nvr/comments/1iovcmk/coral_tpu_poor_confidence_for_detecting/)  
10. Update stop sign detector to run without EdgeTPU · Issue \#953 · autorope/donkeycar, [https://github.com/autorope/donkeycar/issues/953](https://github.com/autorope/donkeycar/issues/953)  
11. Frigate decided my tree is a dog today : r/homeassistant \- Reddit, [https://www.reddit.com/r/homeassistant/comments/1almmn5/frigate\_decided\_my\_tree\_is\_a\_dog\_today/](https://www.reddit.com/r/homeassistant/comments/1almmn5/frigate_decided_my_tree_is_a_dog_today/)  
12. pycoral/examples/detect\_image.py at master \- GitHub, [https://github.com/google-coral/pycoral/blob/master/examples/detect\_image.py](https://github.com/google-coral/pycoral/blob/master/examples/detect_image.py)  
13. test\_data/ssdlite\_mobiledet\_coco\_qat\_postprocess\_edgetpu.tflite at master \- GitHub, [https://github.com/google-coral/test\_data/blob/master/ssdlite\_mobiledet\_coco\_qat\_postprocess\_edgetpu.tflite](https://github.com/google-coral/test_data/blob/master/ssdlite_mobiledet_coco_qat_postprocess_edgetpu.tflite)  
14. Tensorflow Recipe — Object Detection Module documentation \- CrossControl, [https://crosscontrol.com/manual/Object%20Detection%20Documentation/content/tensorflow-recipe.html](https://crosscontrol.com/manual/Object%20Detection%20Documentation/content/tensorflow-recipe.html)  
15. TensorFlow model used in Frigate · blakeblackshear frigate · Discussion \#16225 \- GitHub, [https://github.com/blakeblackshear/frigate/discussions/16225](https://github.com/blakeblackshear/frigate/discussions/16225)  
16. AUR (en) \- zmeventnotification \- Arch Linux, [https://aur.archlinux.org/packages/zmeventnotification?all\_deps=1](https://aur.archlinux.org/packages/zmeventnotification?all_deps=1)  
17. Features — Object Detection Module documentation \- CrossControl, [https://crosscontrol.com/manual/Object%20Detection%20Documentation/content/features.html](https://crosscontrol.com/manual/Object%20Detection%20Documentation/content/features.html)  
18. mobilenetv2 tflite not expected output size with python3 \- Stack Overflow, [https://stackoverflow.com/questions/54864071/mobilenetv2-tflite-not-expected-output-size-with-python3](https://stackoverflow.com/questions/54864071/mobilenetv2-tflite-not-expected-output-size-with-python3)  
19. How to Regenerate a TFLite Model by Deconverting It to JSON, Replacing Custom Operations with Standard Ops, and Reconverting It \- Zenn, [https://zenn.dev/pinto0309/articles/9d316860f8d418?locale=en](https://zenn.dev/pinto0309/articles/9d316860f8d418?locale=en)  
20. Deploying Pretrained TF Object Detection Models on Android \- Medium, [https://medium.com/data-science/deploying-pretrained-tf-object-detection-models-on-android-25c3de92caab](https://medium.com/data-science/deploying-pretrained-tf-object-detection-models-on-android-25c3de92caab)  
21. Benchmarking Deep Learning Models for Object Detection on Edge Computing Devices \- arXiv, [https://arxiv.org/html/2409.16808v1](https://arxiv.org/html/2409.16808v1)  
22. tflite-server with custom model? \- ModalAI Forum, [https://forum.modalai.com/topic/3748/tflite-server-with-custom-model](https://forum.modalai.com/topic/3748/tflite-server-with-custom-model)  
23. arXiv:2409.16808v1 \[cs.CV\] 25 Sep 2024, [https://arxiv.org/pdf/2409.16808](https://arxiv.org/pdf/2409.16808)  
24. Does the TFLite\_Detection\_PostProcess Op runs on the TPU or the CPU · Issue \#515 · google-coral/edgetpu \- GitHub, [https://github.com/google-coral/edgetpu/issues/515](https://github.com/google-coral/edgetpu/issues/515)  
25. CUSTOM : Operation is working on an unsupported data type EDGETPU \- Stack Overflow, [https://stackoverflow.com/questions/66653597/custom-operation-is-working-on-an-unsupported-data-type-edgetpu](https://stackoverflow.com/questions/66653597/custom-operation-is-working-on-an-unsupported-data-type-edgetpu)  
26. TI Deep Learning Product User Guide: TFLite Runtime, [https://software-dl.ti.com/jacinto7/esd/processor-sdk-rtos-j721s2/09\_02\_00\_05/exports/docs/c7x-mma-tidl/ti\_dl/docs/user\_guide\_html/md\_tidl\_osr\_tflrt\_tidl.html](https://software-dl.ti.com/jacinto7/esd/processor-sdk-rtos-j721s2/09_02_00_05/exports/docs/c7x-mma-tidl/ti_dl/docs/user_guide_html/md_tidl_osr_tflrt_tidl.html)  
27. Flatbuffer Converter Tool \- Developer Docs \- Silicon Labs, [https://docs.silabs.com/machine-learning/latest/aiml-developers-guide/flatbuffer-conversion](https://docs.silabs.com/machine-learning/latest/aiml-developers-guide/flatbuffer-conversion)  
28. In-depth: TensorFlow Lite for Microcontrollers \- Part 2 \- Hackster.io, [https://www.hackster.io/theevildoof/in-depth-tensorflow-lite-for-microcontrollers-part-2-f0d170](https://www.hackster.io/theevildoof/in-depth-tensorflow-lite-for-microcontrollers-part-2-f0d170)  
29. Google Edge TPUで TensorFlow Liteを使った時に 何をやっているのかを妄想してみる 2 「エッジAIモダン計測制御の世界」オフ会＠東京 \- Slideshare, [https://www.slideshare.net/slideshow/google-edge-tpu-tensorflow-lite-2-ai-155538767/155538767](https://www.slideshare.net/slideshow/google-edge-tpu-tensorflow-lite-2-ai-155538767/155538767)  
30. Tflite Detection Postprocess Explanation \- tensorflow \- Stack Overflow, [https://stackoverflow.com/questions/79451236/tflite-detection-postprocess-explanation](https://stackoverflow.com/questions/79451236/tflite-detection-postprocess-explanation)  
31. OE 35\. TFLite support · opencv/opencv Wiki \- GitHub, [https://github.com/opencv/opencv/wiki/OE-35.-TFLite-support](https://github.com/opencv/opencv/wiki/OE-35.-TFLite-support)  
32. Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers, [https://kolegite.com/EE\_library/books\_and\_lectures/%D0%9F%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%B8%D1%80%D0%B0%D0%BD%D0%B5/TinyML%20Machine%20Learning%20with%20TensorFlow%20Lite%20on%20Arduino%20and%20Ultra-Low-Power%20Microcontrollers%20%28Pete%20Warden%2C%20Daniel%20Situnayake%29%20%28Z-Library%29.pdf](https://kolegite.com/EE_library/books_and_lectures/%D0%9F%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%B8%D1%80%D0%B0%D0%BD%D0%B5/TinyML%20Machine%20Learning%20with%20TensorFlow%20Lite%20on%20Arduino%20and%20Ultra-Low-Power%20Microcontrollers%20%28Pete%20Warden%2C%20Daniel%20Situnayake%29%20%28Z-Library%29.pdf)  
33. FlexBuffers (Schema-less version) \- FlatBuffers Docs, [https://flatbuffers.dev/flexbuffers/](https://flatbuffers.dev/flexbuffers/)  
34. Custom Operation入りのtfliteを逆コンバートしてJSON化し標準OPへ置き換えたうえでtfliteを再生成する方法 \- Zenn, [https://zenn.dev/pinto0309/articles/9d316860f8d418](https://zenn.dev/pinto0309/articles/9d316860f8d418)  
35. Custom operators | Google AI Edge, [https://developers.google.com/edge/litert/conversion/tensorflow/ops\_custom](https://developers.google.com/edge/litert/conversion/tensorflow/ops_custom)  
36. TensorFlow Lite Flatbuffer Manipulation Example \- Colab \- Google, [https://colab.research.google.com/drive/11R9hd\_0zvW0y3mesitNtF8dCjf27xP9T?usp=sharing](https://colab.research.google.com/drive/11R9hd_0zvW0y3mesitNtF8dCjf27xP9T?usp=sharing)  
37. Google\_Colab\_Notebooks/Hand\_Tracking\_Model\_TFLite\_Conversion.ipynb at main \- GitHub, [https://github.com/shubham0204/Google\_Colab\_Notebooks/blob/main/Hand\_Tracking\_Model\_TFLite\_Conversion.ipynb](https://github.com/shubham0204/Google_Colab_Notebooks/blob/main/Hand_Tracking_Model_TFLite_Conversion.ipynb)  
38. Creating a Cattle Counter app for the Parrot Anafi \- RIIS LLC, [https://www.riis.com/blog/creating-a-cattle-counter-app-for-the-parrot-anafi](https://www.riis.com/blog/creating-a-cattle-counter-app-for-the-parrot-anafi)  
39. TF Lite object detection only returning 10 detections \- Stack Overflow, [https://stackoverflow.com/questions/58052869/tf-lite-object-detection-only-returning-10-detections](https://stackoverflow.com/questions/58052869/tf-lite-object-detection-only-returning-10-detections)  
40. Convert your Tensorflow Object Detection model to Tensorflow Lite. \- Gilbert Tanner, [https://gilberttanner.com/blog/convert-your-tensorflow-object-detection-model-to-tensorflow-lite/](https://gilberttanner.com/blog/convert-your-tensorflow-object-detection-model-to-tensorflow-lite/)  
41. Tensorflow \- conversion from frozen .pb to .tflite \- Stack Overflow, [https://stackoverflow.com/questions/57927688/tensorflow-conversion-from-frozen-pb-to-tflite](https://stackoverflow.com/questions/57927688/tensorflow-conversion-from-frozen-pb-to-tflite)  
42. TensorFlow Lite Model Maker | Google AI Edge, [https://developers.google.com/edge/litert/libraries/modify](https://developers.google.com/edge/litert/libraries/modify)  
43. Modify tflite model input/output shapes for faster inference? \- Google AI Developers Forum, [https://discuss.ai.google.dev/t/modify-tflite-model-input-output-shapes-for-faster-inference/25127](https://discuss.ai.google.dev/t/modify-tflite-model-input-output-shapes-for-faster-inference/25127)  
44. TFlite Model-Maker maximum detection is always 25 (Android) how can I increase this number? : r/tensorflow \- Reddit, [https://www.reddit.com/r/tensorflow/comments/y0ibox/tflite\_modelmaker\_maximum\_detection\_is\_always\_25/](https://www.reddit.com/r/tensorflow/comments/y0ibox/tflite_modelmaker_maximum_detection_is_always_25/)  
45. Increase number of detections on Tensorflow Lite's Model Maker (Android) \- Stack Overflow, [https://stackoverflow.com/questions/74019381/increase-number-of-detections-on-tensorflow-lites-model-maker-android](https://stackoverflow.com/questions/74019381/increase-number-of-detections-on-tensorflow-lites-model-maker-android)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEsAAAAZCAYAAAB5CNMWAAACm0lEQVR4Xu2XW4hNURzG/4Qi1BRmUm6jRGiShymXiESReHEp5ZIHlyYjeeHBJN4kj27FkxRFLrkUkhBKnuSBFw8SiQm5jPB9/dc59vq399l7bXMcD+tXv5r9rT3n7Plm77XWFolEIr3PaHgUHoAn4RhvNOJxAg5yP4+C5xJjhfkfGh5rgwQr4SN4B96Hi/zhwvAzlrifR8IzibGasOEZ8AK8ZMb+Ff3hRHgQfjBjFZbCz3CCO54GP8I51TOKswn+hMdF77JWfzidzfANvAx/SGPKmgrfid4pL+Enf7jKU3jEZKfhXZMVoQnehG/ha9juD+fzVRpTVpKrkl7WZPgLdpi8y+XN7piP1r4aDnXnXRed5IfDs6L/pCBCy2qD422YgBc2z4Y5ZJW1RrSUtSbf7vKFJq8FH3cWVKEPfAJHJLJcQssaBx9I+vM+GN6As+1ADlll7RQtZbXJt7p8g8lrMUS0nIHumNfK7w0itCzCx+Ox+CsYL4K3+eJEVpSssvaIlrLK5JxzmW8zeR4L4EV4WHSfNckbLUCZssh00cK4BA8Q/YwV3hnFySqrS3q3rL+GZXFVLMNM+BCeh+v8oSBYFrcHlqzHcIvLN5q87rCsKzYsSD/RpfiZ6LJcFpb1xYaiJbGU9SavTPBlN6elYVnBEx3oC0/BTjgX3hKdRMvA7+d1WLiCsZQdJt/v8haT1x1e5DUb5sBll7vg3YmMyzg/p7LahMCyvtnQwU3pMZPxreOeyeoOHyNe5G07kMMhuNeGYLnoH8LXmBC43eiR9N/j6043nOKO+Yr2Hc6qnlFnuLy/gO9Fb2fK7f9zyZ97lok+BllwntllwxSGiX7fK/lzDXw/ZGbnIq6GXHm5v+MdNd8fjkQikUgkEmk4vwGIpo+aq/NNrAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGcAAAAaCAYAAACq/ULmAAAFKUlEQVR4Xu2Zd6gkRRCHyzPnnBVPBRWzqJg5MwYOwQiKglnEnAP+YwADiggGRBQDyGFAxJwOIyrmDKYzI5hRzOH3XXXf9tabmd073u5bcD748barJvRMd1dXzTNraWlpaWlgYelBacXo+B+zhPSYtGR0DJv7pEOicRzZTzpfukZaJ/hGmT2lR6S5o2NYHG4+QwYJ93he+lfavts18twunRONc8Iy0rnSk9Kj0lPSS9J50nzFcRlsn0pToyOxmPSe9KX5i/3BfLmXXCX9Zu7/U3q72z0L7jERg3OP9IH5vf+Rdux224HSj+Z+9IW0QeHfSvpWWqSwzTbHSl9Jp0gLFPZVpTekl6XFCzvsbX7OpGCPnCZ9ZN75s4MP1pPeteb4TIiYiMGBzazT/4eDDwhbTNINoyPxlnRCNPbDXNJ10s/S5sGX2dq8Y1cG+23SncFWxUPSFtIf5qsorsJ9pQuCLbKbTdzgMKFYIe+Y96FcGbCsebSpg/d7fzT2w4XmNzwsOgrmkf6SZgT7+9LpwRZhIF5Iv28xv9ehHfdM2Oi3C7ZI3eAQZqab70mvS5dJC3Yd4RODEP20eQQguaAvRIQTi+PqIMQzALwj+nBzt9v2Nw/9dfC8hL7ZSgw2lf42X3asoDoIc3Tql8JGDCUG71XYqthBuiL9ZsZxHfaV8n68sHmLdhVVg7OPeTwnLAIT4S7zwWJCwUrST9Kpqb2c+XPQPrOw18GzP5d+c31WPhFg5VlHmF0vbVm0I9uY931ysDcyzfykXvEwh7UPC9vqyTalsFVxkbR70SbEcd4eqb2adG/HXUscnEWl72xsqF3L/LjjUvuk1GYiZl6V3izaTewiXVK0zzK/3qWF7RVrXhXr29g+NMLMJXvipLWDL3Kx+XHEzszGybZRYauCUEKRmiEMcd4TqX20dHzHXUscHEIJ7aPyAQVEg2fSb67Pcdt23DPDHwPUDwzCzkWbpIiVyLtjgvDuWK1NrGLeh12jow7iMieguEGXLCR9Y76UmZUZBqXX4JB9VdVApOd5Jt1tvScHxME5ObXj/gWk5p+k36TuhKLLU5sQ+LtVn1cFIa3MXoFrcW9CIlGHCdBEHhyeoW+YAewb80dHARssFz4j2EmxsU8J9hKyMOqmyAHm595hvin3QxwcvhrQzuErw0TjmUgQgEnI6r1RetH8ZVPU9gP7U1XqzMtmspI+8wVgjW73GHJYo+bpm1vNT9opOhJ8kuFB86wrYUVxblNCULdREp9z3XBD8NUR6xxWJaHl6nxAglqD46itgPBLITknkD6zx1SRM08K1F7khGDN6GiCTGaGeRXPBp9Z3rxyZ8Nt+mb2sdWn0itIn5vH5SrYZ+gwq6gfmAQcX8ZtQhMDtElqEwFILkjdc6imH7+a11FkZ/T3SGnd5K+D80lemBRV5Mzz2uioIKfSTRlxJUubrwwG6FnzYmq6+UPETy2Rm2xsEbqU+bWI63SeAa4aQFYeewH37wVZJekv16NYJkRlyPqoYV4z/8rABl4mIKTohDPOjaK+qoIBJuRzDAMbnzFDYdkUOTIkUoS/ocKs5wVPio5xhhWR78Hfpj0yQvh5wDqfnjifgjKnxBSog4Y68phoHDQUeoS2qdExQnxtvndUQRZ6UDSOMyQB35t/BB46R5h/3hhV2GuoafJXBGAf5LPVZzb4l8a/DOqSiqFABw6OxhGCgvVx88KUVJqKnk9K/ItkkJBMsI/nT0kTArUEcb39N3UHkikK8EFPgJaWlpZR5z8oUSVmsJPFbAAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAACT0lEQVR4Xu2XS6hNYRiGP3cHuXTU6Yg6UhgQJYPDwOCUlKRMjCiHgQwMFInMDJRIRmYGlJShWy6JkgkTGShEBs7EPXK/vK9v//n227/X/p3OMtpPPZP3+/fa317rv6xt1qHDiDMZXoK9WqhgOrwGZ2ihbs7DzRoG+jRosBZegWO0UBdbze+QMg4uhEfhW6lFzsB9GpYwE+6HN+FVeAvehQfg+DAuwew5XCf5YvgK3jGvf2guN9FvPnaKFqrYAYfgLjgx5HPgfXgPTgs52WD+mdGSRy5bdbPkAdypYY5R8IT5BZdLLbEC/oLHJD8Nz0mmlDTL77+gYY6D5o0MaiEwFn6HzyR/BHdLppQ0uwW+szYLbRn8Yf4YeIdbwWnBH/QxZJxjP+H6kOUoaXal+fX7JG/irPmgdvMlTYMnIZvbyFaFLEdJs4vMr8Wbl4V3klsKBy2QmnLIfBznVmJpI1sSshxsNj6RHLPNr7VaC4ku8wE0ty0lJsGX8CucH3I2WdrsJw2F1OwaLUTem8+7CVoIHDa/0B7JuaWVToPPGgppGnDPbckp80EDWmjAI5Q/5ogWzO84P1uywL5oKKQFNk8LkVnm29FD8wWT6IHH4WurPvOfWvut6zr8Zn78tiJtXVU70h+6ze8cG75tftTeMG+Cb0ZVnLT8ocBj+zF8YX/XBRczs9y85MLlC02tbDRvqOq4LYH7/HYNRxqebJwK+iLzL3BRvYFTtVAH28zf0IYLXxH3algn/MJNGhbAl2+uEz6h/wYPmIs2vL81XIwdOrTjN3TxfIaISbdBAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAABDElEQVR4XmNgGAXDFzgD8S0gfg/E/4H4IKo0GJwF4n8MEPlvQDwbVRoTbAHiewwQDZZociCQDcTLgJgJXQIdsALxGSCOYIAYthZVGgymMEB8QRDYAPFkIGYG4vtA/BeIVVBUQCxjRxPDChqB2A/KzmWAuG4aQppBCoi3I/HxggNAzAtlcwHxGwZIQItAxeKBuAjKxgv4GCCGIYMmBojr6qD85UCsi5DGDfyBuB5NTBSIvwPxKyDmBuLLqNK4ASiWrNEFgWA6A8R1c4B4EZocTnAOiFnQBRkgsQmKVZCBMWhyWIEdEJ9GF0QCoPQGMkwCXQIZuAHxAwZEFnkCxPbICqDAnAGSlUbBKBhQAADIFjDhxd8YOAAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAZCAYAAABJhMI3AAAC4UlEQVR4Xu2XSchOURjHHzMZMpSQzBZYUKaE+pAkC0TGBQsLCikWoiRDwkZYIPOCBfm+JCHDAhkylIiUUjIkSaYk0//fc+/3nff57nDuu3jfhfOrX937nFv3nOec89xzRQKBQCBg6Q/XwEGwNewFV8Dj7kNV4BxcZoMVZjR8a4NJTIJ/jd/hZPehCjNNtB/LbUMFaQLvwA+2IYka0QdfwufwCBzotFeaFvCpVD+Ji+Af8UzieHjUBqvIatGJrGYS28Hb8Ip4JnGclJ/EoaI1NY0OcKINZtAV3hStRb5J7AQn2KADt+UMG8xhG5wrWpe9kjgWnoX74WX4RHQ1+NBXtG70sw2is8mZ5Er35YBoLR4h/klsBS+K1tEkdot+OH3hmJgH4p3EMfCd6NeZdIfv4cb4gRyGwAewjxNrAy9J+sCSGAbPRNdFkkjaw+twqolvh1tNLI/TcHh07Z3EttJ4JR2DP2A3E0+DL2Uie8CWoi+fU/JEPkz6gOi6aBJJZ9FdURPdb4B76lv9YFk47Nx7JzGJzaKDWGAbMmBZuAvr4OLSplxmw53OfTlJJKyp9+BeeEi0HvrSFN6Q0oXjnURug/uwmRPjLHIQRWpJc3gVPhMt9r7wgM8vIT9CMeUmkWyBX+BI25DDUrjWxLySyMT9gp9F61jMDtFBLHRiWXAWT8BVotvpmmid8oGD/SRal2M/ir6f/eJ9vM3z4B/OKdG/Lk7M4NLmTGpFvwVuP36KnhV5va/h0cawlo0ysQvwK+xi4klwyxyE653YFNEvpjsxReD2LroSeTjmyuFhnfSGtyT7CJbHY/FYiWS66Ms7Rvez4G+4pP6JbHbBTTYIZooeneJBFWGeaBJX2oYU2OfzoqXBhX9eTGRPE/eFpYm7wgt2+hF8BR+KdsoHHmKzjhDz4TobzICnhBfwmzT8w/Penh5ceCTjIkhb9TyCnbTBHLgwXov2gb6JYoFAIBAIBAL/A/8A9guaHbYJHAMAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAZCAYAAABeplL+AAADgElEQVR4Xu2YWahOURTHl3keuyGha8wUiWRIbuaSuUxFXsSTuRQviBSRZCpSPJDMMo9XyBQPMmV+kBRSImT8/1vnuvss3z3Tw3eT/atf9ztrn3u/c9ZZe+91rojH4/F4/kVGwDvwY/BzOqwQOkNkJhwOC2At2AcehL3dk/JMHfgKdrADeWYB3GODuRgEb8PGsC7cCH/B5e5J4FIQdz0Gq7on5ZnVotfR2Q7kkSbwA9xnB3JxFfZ3jivBp/AnbO7Ei+FD+BJehjNgRWc837SFn6X8k71dNFexyWZif8BnsJ4T3yp6E0xoCedgoXNc3hyCO6V8k91DdPng8hubbFbme9ELbuPE1wSxuU7srGRP9lgbMAyBNW0wgqFws+hamTTZXWFrG3TgEjrABmMoKcBEySbd4GATOy16E278DJwNT8Cb8Dhs74xHsRKusMGA8XC/6CxLQmV4RXSjTpPslvA6bGUHQG3RxPWzAxFMltJ9LXGyLS3gN3hPwmvyKbjWifGL2Ak0/XNGNJvgMhMbCU/C6iYexSwpnXFpkk06iTYDhU6shmhxsdNKCmfhNdGujGRO9i7R3bWLiXeUcPJZKbzRdU4sCraSO+DC4Jiz5oJoVSWloeiGXiU4Tpts0l004SwSdlJHRWdXGpbCqc5xpmRPgZ9gkYnngtOeN/rIDkTA39kL14t2NPXDw7FskHAFZkk26QtviG6y08JDsbBDK5bwe0jqZHMDeSu5NwneIKvdVgBbHn5RGtjX84HOtwMxcAlgFbpkTTbX/fOirWwDMxYHZ759kUuVbE7PB3CYEyuCE4LPS0RvanHJoOi6xdhjJxZHT9HNtZno2+fE8HAk8+A7+NqRN8lrYJHwzTcJXAqZsDmi98iljG+iSXkj4WugvIYvwWd3efkLTm12FuNMnOvSqODzaHhYwh1DL9EvYaeRBO4Bt0QTTaqJVio3yaxwWUlT2Zz62yRcNGwjuflzo8xCgeg1JKrsVaLT+m4gu5An8KvopkhYDVxj+T8UwrX2IrwvyaqinWhFF5o4ZwdbyoEmnpQtojdqN/Oy4GZuOyIyBh6R0o03DXxd5zUcsAMWPk2emEuux25L1gjuFn0QfGVnhfCpJoEVnKu/JXxY7N35UpGUSfA5/C56rXwxY5cSBWdnWb0+4d9cZIMx8Du5tPEa+Cb+QvTveDwej8fj8Xj+X34DyEXFZQat660AAAAASUVORK5CYII=>