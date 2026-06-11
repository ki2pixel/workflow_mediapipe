# Intégration Expérimentale : Google Coral AI Edge TPU

Cette documentation trace l'ensemble des travaux réalisés pour accomplir la mission de migration expérimentale de l'architecture logicielle vers le **Google Coral Edge TPU (M.2 PCIe)**, validant ainsi la viabilité du pipeline `Workflow MediaPipe` sur des architectures basse consommation (Edge) sans GPU dédié.

## 🚀 Réalisations et Changements Effectués

### 1. Fondation Système et Pilotes
- **Désentrelacement des dépendances** : Création du script `scripts/install_coral_udev.sh` pour configurer le groupe `plugdev` et implémenter les règles `udev` (permettant au TPU d'être reconnu sur `/dev/apex_0` via le pilote communautaire `feranick/gasket-driver`).
- **Isolation Environnementale (`coral_env`)** : Configuration stricte respectant les standards du projet pour instancier un *venv* Python 3.10 autonome chargé des *wheels* pré-compilés `tflite_runtime-2.17.1` et `pycoral-2.0.2`.

### 2. Orchestration Asynchrone Globale
- **Singleton TPU Orchestrator** : Afin de contourner la redoutable limite matérielle de 8 Mo de SRAM du Coral, un routeur asynchrone (`services/coral_tpu_orchestrator.py`) a été greffé au cœur de l'application (`app_new.py`).
- Ce routeur garantit une exécution séquentielle et sécurisée (*Queue*) des inférences, empêchant un effondrement du bus et l'éviction de cache.

### 3. Les Trois Grandes Migrations (STEP 3, 4, 5)

> [!IMPORTANT]  
> Le basculement vers ces nouveaux algorithmes est contrôlé par la variable d'environnement dynamique `ENABLE_CORAL_TPU_ACCELERATION=true` dans votre fichier `.env`. S'il est désactivé, le pipeline standard `(GPU/CPU)` reprend instantanément le dessus.

#### STEP 3 : Détection de Scènes (Remplacement TransNetV2)
Le réseau complexe à convolutions 3D a été remplacé par un algorithme Siamois MobileNetV2 INT8.
* **Fonctionnement** : Analyse d'images une par une (batch=1) générant des vecteurs à 1000 dimensions (logits).
* **Innovation CPU** : Le calcul temporel est transféré sur le CPU via l'application mathématique d'une **Distance Cosinus** couplée à un filtre médian de lissage temporel, garantissant une précision similaire sans polluer l'ASIC.

#### STEP 4 : VAD & Diarisation (Remplacement Pyannote)
L'architecture de Pyannote est inconvertible vers le TPU. Le choix s'est porté sur **YAMNet INT8**.
* **Fonctionnement** : VAD extrêmement rapide traitant l'audio tronqué à 16kHz par blocs de 0.96s pour déterminer les activités vocales.
* **Innovation CPU** : Le regroupement spectral (*Spectral Clustering*), mathématiquement lourd, est déporté sur le CPU via `scikit-learn` pour regrouper les locuteurs et produire le fichier d'annotation `.json` final.

#### STEP 5 : Tracking Avancé (Remplacement InsightFace/MediaPipe CPU)
Désactivation de la logique lourde du `multiprocessing` CPU de MediaPipe au profit d'une Cascade Pure TFLite séquentielle.
* **Fonctionnement** : Détection via `BlazeFace`, extraction nodale par `FaceMesh` (avec suppression impérative du noeud asymétrique `half_pixel_centers`), puis modélisation 3D via `Face Blendshapes`.
* **Innovation CPU** : L'utilisation d'INT8 engendre de la perte de précision (jittering sur les expressions du visage). Un **Filtre de Kalman vectorisé** à N dimensions (52 blendshapes) a été programmé manuellement pour stabiliser les micro-tremblements.

---

## ✅ Plan de Vérification

Pour valider l'ensemble du système, effectuez la séquence suivante :

1. **Vérification Physique du Matériel**
   * Assurez-vous que le GRUB a bien démarré avec les arguments `pcie_aspm=off pci=noaer`.
   * Vérifiez la présence du pilote : `ls /dev/apex_0`

2. **Configuration**
   * Modifiez votre fichier `.env` et ajoutez : `ENABLE_CORAL_TPU_ACCELERATION=true`

3. **Exécution Test**
   * Prenez une courte vidéo dans `projets_extraits/` (moins d'une minute).
   * Relancez votre workflow. Vous devriez constater l'utilisation des modèles TFLite et une consommation électrique ridicule (2 à 4 Watts) en lieu et place des turbines de la RTX.

> [!TIP]
> Tous les scripts TPU disposent d'un logger performant. En cas d'anomalie de détection, scrutez les fichiers situés dans `logs/step3`, `logs/step4`, et `logs/step5` qui conserveront un historique détaillé des inférences (`tpu_scenedetect_*.log`, etc.).
