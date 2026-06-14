# Rapport d'Arbitrage : Intégration du Google Coral AI Edge TPU

Ce document présente l'analyse technique et l'arbitrage concernant l'intégration de l'accélérateur matériel **Google Coral USB Edge TPU** au sein du pipeline **Workflow MediaPipe v4.x**, fonctionnant sous Ubuntu 22.04 et Python 3.10.

L'étude s'appuie sur le rapport technique communautaire (fork "Feranick", gestion des dépendances udev/INT8) et les standards architecturaux actuels du projet (`memory-bank`, isolation stricte des environnements virtuels).

---

## 1. Évaluation par Étape du Pipeline

L'architecture matérielle du Coral TPU impose une **quantification INT8 stricte**. Toute opération mathématique non supportée par le jeu d'instructions de l'ASIC entraîne un repli (*fallback*) vers le processeur central (CPU), ce qui génère un goulot d'étranglement majeur sur le bus USB 3.0.

### 🔴 STEP 3 : Scene Detection (TransNetV2)
**Verdict : Non Éligible**
- **Incompatibilité Architecturale** : TransNetV2 utilise de manière intensive des convolutions 3D (Conv3D) pour analyser les séquences temporelles d'images. Le compilateur Edge TPU offre un support très limité, voire inexistant, pour les opérations 3D complexes, forçant un repli CPU destructeur pour les performances.
- **Perte de Précision** : La quantification INT8 asymétrique d'un modèle aussi sensible aux variations colorimétriques temporelles entraînera inévitablement une perte de précision (faux positifs/négatifs lors des transitions douces).
- **Paradigme de Calcul** : L'étape 3 actuelle tire parti d'une inférence par lot (`batch_size=8`) sur GPU. Le Coral est optimisé pour une latence ultra-faible avec un batch size de 1, ce qui détériore le débit (*throughput*) global par rapport à la solution actuelle.

### 🔴 STEP 4 : Audio Analysis (Pyannote / Lemonfox)
**Verdict : Non Éligible**
- **Verrouillage Technologique** : L'écosystème Pyannote repose sur des graphes computationnels PyTorch complexes (modèles de langage, clustering dynamique, embeddings vocaux).
- **Impossibilité de Conversion** : Transformer la pipeline Pyannote en un modèle TFLite entièrement quantifié en INT8 est aujourd'hui techniquement irréalisable. Les opérations de clustering et de traitement du signal ne sont pas prises en charge par le Delegate Coral.

### 🟡 STEP 5 : Video Tracking (MediaPipe / InsightFace)
**Verdict : Partiellement Éligible (MediaPipe uniquement) / Non Éligible (InsightFace)**
- **InsightFace (GPU ONNX)** : Modèles de reconnaissance faciale lourds (AntelopeV2, Buffalo_l). La conversion d'ONNX vers TFLite INT8 est un cauchemar d'ingénierie (opérations non supportées systématiques). *No-Go absolu.*
- **MediaPipe (CPU)** : Certains modèles légers de MediaPipe (ex: Face Detection) disposent de variantes TFLite officiellement optimisées pour Edge TPU.
  - *Le problème* : L'architecture actuelle du `tracking_env_slim` repose sur le module Python `multiprocessing` (`TRACKING_CPU_WORKERS`) pour saturer les cœurs CPU. Le bus USB et le TPU physique représentent une ressource unique (*single-point-of-bottleneck*). Pour l'exploiter avec plusieurs workers, il faudrait implémenter un verrou (Lock) complexe ou disposer de plusieurs clés USB Coral, réduisant l'intérêt du parallélisme.

---

## 2. Analyse Comparative des Plateformes Hôtes

### Scénario A : Système actuel avec GPU dédié (RTX / CUDA)
> **Statut : NO-GO DÉFINITIF**

- **Performances** : Une carte graphique dédiée surpasse de plusieurs ordres de grandeur les 4 TOPS du Coral, en particulier sur l'inférence par lot en précision FP16/FP32 (utilisée en STEP 3 et STEP 5).
- **Dette Technique** : Maintenir les binaires communautaires ("Feranick") recompilés pour la glibc 2.35 d'Ubuntu 22.04 et isoler le runtime `libedgetpu` / règles `udev` introduit une complexité disproportionnée pour un gain de performance nul (voire négatif).

### Scénario B : Déploiement "Edge" / Basse Consommation (ex: Raspberry Pi 4 / NUC sans GPU)
> **Statut : GO CONDITIONNEL (Sous réserve de pivot architectural)**

- **Gains attendus** : En l'absence de GPU, le Coral TPU apporte une accélération phénoménale (réduction drastique de la charge CPU et de la consommation électrique).
- **Les Conditions du Go** :
  1. **Abandon de TransNetV2 et InsightFace** : Ces modèles devront être remplacés par des alternatives natives TFLite INT8 (ex: architectures MobileNet).
  2. **Refonte du STEP 5** : Abandonner le `multiprocessing` CPU intensif au profit d'une file d'attente asynchrone (*asyncio*) alimentant séquentiellement l'ASIC TPU.

---

## 3. Alternatives Technologiques Validées (Post-Deep Search)

Suite à une recherche approfondie ("Deep Search"), des alternatives *Edge-ready* (100% compatibles TPU sans fallback CPU) ont été identifiées. Elles impliquent cependant une **réécriture complète de l'architecture logicielle** :

- **STEP 3 (Détection de Scènes)** : Remplacement de TransNetV2 par un réseau siamois basé sur **MobileNetV2 INT8**. La distance cosinus est calculée sur le CPU pour détecter les transitions. *Score de viabilité : 8.5/10 (Nécessite un lissage temporel personnalisé).*
- **STEP 4 (Audio & Diarisation)** : Remplacement de Pyannote par **YAMNet INT8** (modèle `097` du PINTO_model_zoo) pour le VAD, couplé à un CNN Speaker Extractor pour générer des *d-vectors*. Le regroupement spectral (clustering) reste sur le CPU. *Score de viabilité : 9.5/10 pour le VAD.*
- **STEP 5 (Tracking & Blendshapes)** : Remplacement de InsightFace/MediaPipe CPU par une cascade TFLite pure : **BlazeFace** ➔ **FaceMesh** (avec désactivation du `half_pixel_centers` pour éviter le rejet TPU) ➔ **Face Blendshapes Model**. *Score de viabilité : 8.5/10 (Nécessite l'implémentation de Filtres de Kalman sur le CPU pour lisser le bruit de jittering introduit par la quantification INT8).*

> [!WARNING] 
> **Le problème de l'Éviction de Cache (SRAM Bottleneck)**
> La SRAM du Coral ne fait que 8 Mo. Charger séquentiellement MobileNetV2 (STEP 3), YAMNet (STEP 4) et FaceMesh (STEP 5) en boucle à chaque frame provoquera une **éviction de cache constante** sur le bus USB, ruinant les 4 TOPS de performance. **Solution obligatoire** : Mettre en place un traitement par micro-lots (*Batch Processing* asynchrone) et la **Co-compilation** des modèles pour partager la RAM de l'ASIC.

---

## 4. Matrice d'Aide à la Décision

| Critère | Maintien Architecture Actuelle (GPU/CPU) | Intégration Google Coral Edge TPU |
| :--- | :--- | :--- |
| **Précision des Modèles** | Maximale (FP32 / FP16 / AMP) | Dégradée (Quantification INT8) |
| **Compatibilité Pipeline** | 100% (TransNetV2, InsightFace, Pyannote) | Très Faible (Modèles incompatibles) |
| **Complexité d'Intégration** | Stable (Venvs isolés, standards fixés) | Très Élevée (Fork Feranick, Wheels cp310, Udev) |
| **Coût / Énergie** | Élevé (Consommation GPU) | Très Faible (~2 Watts) |
| **Throughput (Inférence Batch)**| Excellent (Optimisé par lot STEP 3) | Faible (Optimisé pour Latence Batch=1) |

---

## 5. Recommandation d'Architecture et Stratégie d'Adaptation

> [!CAUTION]
> **Décision Finale : Maintien strict de l'architecture actuelle.**
> L'architecture actuelle de Workflow MediaPipe, construite autour de modèles de Deep Learning complexes (TransNetV2, InsightFace, Pyannote), est stable et opérationnelle. Ces modèles actuels **devront impérativement rester en place** pour les charges de travail standards.

Si ce projet expérimental Edge TPU venait à être mis en place dans le futur, il ne s'agirait **pas d'un projet de migration, mais d'une adaptation optionnelle**. L'intégration de la solution Google Coral AI Edge TPU s'effectuerait sous les conditions structurelles suivantes :

1. **Activation Optionnelle via `.env`** : Le recours au TPU Coral sera piloté dynamiquement (ex: `ENABLE_CORAL_TPU_ACCELERATION=true` dans le fichier `.env`). Par défaut, le pipeline exécutera l'architecture classique éprouvée (GPU/CPU).
2. **Isolation dans un nouveau Venv dédié** : Les environnements existants (`tracking_env_slim`, `insightface_env`, `transnet_env`, `audio_env`) ne doivent **absolument pas être modifiés ou pollués**. Un nouvel environnement étanche, par exemple **`coral_env/`** (Python 3.10), sera instancié.
3. **Dépendances Spécifiques (Feranick)** : L'environnement `coral_env` isolera les *wheels* pré-compilés communautaires (`tflite_runtime-2.16.1-cp310-...whl` et `pycoral`), évitant tout conflit de dépendances (`Dependency Hell`) avec l'hôte Ubuntu 22.04.
4. **Règles Udev & Sécurité** : Déploiement d'un sous-script Bash d'installation optionnel pour la création du groupe `plugdev` et la gestion de la double énumération USB (`1a6e` -> `18d1`), sans impacter les utilisateurs n'exploitant pas le Coral.

---

## 6. Intégration Matérielle PCIe M.2 (Architecture Gigabyte X399)

L'exploration du format **Google Coral M.2 PCIe** sur une carte mère HEDT comme la Gigabyte X399 AORUS Gaming 7 (AMD Threadripper) lève plusieurs limitations du modèle USB (bande passante, latence), mais introduit des défis d'ingénierie système critiques :

1. **Le Piège du "Dual Edge TPU"** : Bien qu'attrayant pour doubler la puissance (8 TOPS), le modèle à deux puces (Dual TPU E-Key) nécessite un commutateur de paquets PCIe (Packet Switch). Sur les plateformes AMD, ce commutateur génère une instabilité sévère (Gels système, Kernel Lockups). **Recommandation matérielle absolue : Acquérir uniquement la version M.2 B+M Key (Single TPU, G650-04686-01)** qui s'insérera nativement dans un port SSD NVMe classique sans conflit.
2. **Éradication de la Latence USB** : En se connectant directement aux lignes PCIe du processeur Threadripper (qui possède 64 lignes), le goulot d'étranglement USB disparaît. De plus, les lourds dissipateurs thermiques (Thermal Guards) de la carte mère X399 empêchent physiquement le composant de surchauffer (*Thermal Throttling*).
3. **Catastrophe ASPM et Déluge d'Erreurs AER** : Le contrôleur PCIe d'AMD est en conflit avec la gestion d'énergie (ASPM) de l'ASIC Google. Sans intervention, le noyau Linux sera inondé d'erreurs PCIe (AER) jusqu'au crash de la machine. **Il est impératif d'éditer le bootloader (GRUB/Syslinux)** pour injecter les paramètres noyau : `pcie_aspm=off pci=noaer`.
4. **Obsolescence du Pilote Officiel (Kernel Linux > 6.5)** : Le paquet officiel `gasket-dkms` fourni par Google est abandonné et ne compile plus sur les noyaux récents (ex: Ubuntu 22.04 HWE Kernel 6.8). **Solution validée** : L'utilisation du paquet patché communautaire (fork `feranick/gasket-driver`) via un fichier `.deb` a permis de compiler avec succès les modules `gasket` et `apex`.
5. **Anomalie MSI-X et Virtualisation (IOMMU)** : Le contrôleur Coral viole le standard PCIe sur l'alignement mémoire (MSI-X). Sous Linux bare-metal (Ubuntu), le noyau "pardonne" l'erreur. Dans un environnement virtualisé (ex: Proxmox/Docker), l'excellente isolation IOMMU de la carte X399 permet un transfert *PCIe Passthrough* (VFIO) propre, à condition de désactiver les modules `gasket` et `apex` sur l'hôte.
6. **Scalabilité Multi-TPU (Data Parallelism & Pipelining)** : L'architecture Threadripper offrant 64 lignes PCIe sans partage (Lane Sharing), la carte X399 permet d'installer nativement jusqu'à **3 modules Coral M.2 B+M Key** simultanément sur les ports `M2M_32G`, `M2Q_32G` et `M2P_32G`. En cas de besoin, l'ajout d'adaptateurs passifs `PCIe x1 vers M.2` sur les ports GPU libres permet de démultiplier ce nombre. Cette topologie Multi-TPU offre la possibilité d'exécuter de multiples réseaux de neurones en parallèle (Data Parallelism) ou de fragmenter un modèle lourd entre plusieurs puces (Pipelining) pour contourner la limite critique de 8 Mo de SRAM.

**Conclusion** : Le format PCIe M.2 est techniquement supérieur à l'USB pour une station de travail. Néanmoins, il valide le point précédent : cette solution doit rester une **adaptation expérimentale**, car elle exige des modifications profondes au niveau du chargeur d'amorçage (GRUB) et l'installation de pilotes communautaires hors dépôts officiels.
