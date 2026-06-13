---
name: coral-tpu-model-compiler
description: Spécialiste de la préparation, conversion et compilation de modèles TFLite INT8 (BlazeFace, YAMNet, MobileNetV2) pour l'Edge TPU via edgetpu_compiler.
trigger: tflite, int8, quantization, compiler, edgetpu, half_pixel_centers, graph_surgeon
---

# Coral TPU Model Compiler Skill

Ce skill se concentre sur l'optimisation, la conversion TFLite, la quantisation INT8 et la compilation des réseaux de neurones pour assurer leur entière compatibilité avec le Google Coral Edge TPU.

## 🎯 Rôle
Piloter la compilation des modèles via `edgetpu_compiler`. Intervenir de façon chirurgicale sur la topologie des graphes pour maximiser le mapping des opérations sur l'ASIC et résoudre les incompatibilités d'opérations.

## 📋 Checklist de Préparation
Avant toute modification ou recompilation :
- [ ] Vérifier la version du compilateur : `edgetpu_compiler --version`
- [ ] Inspecter les types d'inputs/outputs du modèle cible (ils doivent impérativement être en `uint8` ou `int8` pour le Edge TPU).

## 🛠 Commandes Types
- Compilation standard d'un modèle TFLite quantisé :
  ```bash
  edgetpu_compiler -s model.tflite
  ```
- Co-compilation de plusieurs modèles (ex: BlazeFace + FaceMesh pour optimiser l'utilisation de la SRAM de 8 Mo et éviter le changement de contexte) :
  ```bash
  ./scripts/compile_coral_comodels.sh
  ```
- Analyse des opérations non supportées : Lire attentivement les logs du compilateur qui précisent quelles opérations sont déportées sur le CPU.

## 🚑 Checklist Diagnostique & Résolution

### Incident 1 : Déport d'opérations massives sur le CPU
- **Symptôme** : Le log indique que certaines opérations, comme `RESIZE_BILINEAR`, sont assignées au CPU, brisant le pipeline matériel et ralentissant l'inférence.
- **Action** : Analyser l'architecture source. Exemple : Remplacer l'argument `half_pixel_centers=True` par `False` dans le modèle originel (ex: FaceMesh) via un script de modification de graphe avant la conversion TFLite.

### Incident 2 : Perte drastique de précision après quantisation
- **Symptôme** : Le modèle compile à 100% sur le TPU mais produit des résultats aberrants.
- **Action** : Revoir le dataset représentatif utilisé lors du processus de "Post-Training Quantization" (PTQ). L'échantillon d'images/audios doit couvrir l'entièreté de la distribution réelle.

## ⚠️ Séparation des Responsabilités
Ce skill n'intervient pas dans l'exécution métier du pipeline (STEP3, 4 ou 5). Il agit en amont pour s'assurer que les modèles `.tflite` fournis sont syntaxiquement et matériellement compatibles avec le compilateur Coral. À noter : le modèle ECAPA-TDNN a été déporté vers ONNX Runtime CPU pour des raisons de performance et de stabilité de précision, et ne fait plus partie des cibles de compilation `edgetpu_compiler`.
