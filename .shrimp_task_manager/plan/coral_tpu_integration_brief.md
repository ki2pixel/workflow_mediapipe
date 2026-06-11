# Brief : Intégration Google Coral Edge TPU (PCIe M.2)

## 1. Contexte
Suite à la validation matérielle (TPU M.2 B+M Key reconnu sous `/dev/apex_0`, GRUB configuré avec `pcie_aspm=off pci=noaer`, driver `feranick/gasket-driver` installé), la mission est d'intégrer le support logiciel du TPU Coral dans Workflow MediaPipe.

## 2. Architecture & Exigences
- **Caractère Optionnel** : Le recours au TPU Coral doit être piloté dynamiquement via la variable `ENABLE_CORAL_TPU_ACCELERATION=true` dans le fichier `.env`. Par défaut, le pipeline doit exécuter l'architecture classique (GPU/CPU).
- **Isolation Environnementale** : Création d'un environnement virtuel dédié `coral_env/` (Python 3.10) sans polluer les environnements existants (`tracking_env_slim`, etc.).
- **Dépendances Spécifiques** : L'environnement `coral_env` doit isoler les wheels pré-compilés communautaires (`tflite_runtime` et `pycoral`), évitant tout conflit de dépendances.
- **Adaptations Modélisations (Pipeline) - La Roadmap PCIe M.2** :
  - **STEP 3** : Remplacement de TransNetV2 par un réseau siamois basé sur MobileNetV2 INT8 (calcul de distance cosinus sur CPU).
  - **STEP 4** : Remplacement de Pyannote par YAMNet INT8 pour le VAD, couplé à un CNN Speaker Extractor (clustering sur CPU).
  - **STEP 5** : Remplacement de InsightFace/MediaPipe par une cascade pure TFLite (BlazeFace -> FaceMesh INT8 sans half_pixel_centers -> Face Blendshapes).
  - Implémentation d'un système de **Batch Processing asynchrone** (traitement par micro-lots) et co-compilation pour contourner la limite critique de 8 Mo de SRAM de l'ASIC et gérer le chargement des 3 étapes.
- **Sécurité et Permissions** : Déploiement automatisé d'un sous-script Bash d'installation pour la gestion des permissions et l'accès au noeud `/dev/apex_0`.

## 3. Dépendances de Tâches
- Le matériel est déjà opérationnel (Phase 0).
- Configuration de base (`coral_env`, auto-script d'installation système `install_coral_udev.sh`).
- L'orchestration (Batch processing) en tâche de fond.
- Implémentations techniques pour STEP 3, STEP 4 et STEP 5 avec les alternatives 100% compatibles TPU.
