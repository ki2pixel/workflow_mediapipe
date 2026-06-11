---
name: coral-tpu-hybrid-algorithms
description: Expert des algorithmes CPU (Filtre de Kalman, Clustering Spectral) mis en place pour compenser la perte de précision INT8 et les limites de l'ASIC Coral.
trigger: kalman, spectral, clustering, cosine, hybrid, jittering
---

# Coral TPU Hybrid Algorithms Skill

Ce skill encadre les heuristiques mathématiques déportées sur le CPU pour compenser la limitation matérielle (précision INT8, manque d'opérations complexes) du TPU Coral.

## 🎯 Rôle
Déboguer, profiler et optimiser les calculs lourds qui s'exécutent sur le CPU en complément des inférences TPU. Cela inclut le Filtre de Kalman vectorisé (52 dimensions) pour réduire le jittering, le Regroupement Spectral via `scikit-learn` pour l'audio, et les calculs de Distance Cosinus.

## 📋 Checklist de Préparation
Avant d'optimiser le code algorithmique :
- [ ] Activer le profiler CPU Python (`cProfile`) pour identifier les goulots d'étranglement.
- [ ] S'assurer que les dépendances (`scikit-learn`, `numpy`, `scipy`) sont à jour dans le bon environnement.

## 🛠 Commandes Types
- Profiling d'un composant de clustering :
  ```bash
  python -m cProfile -s cumtime scripts/test_spectral_clustering.py
  ```

## 🚑 Checklist Diagnostique & Résolution

### Incident 1 : Jittering extrême (Tremblement) sur le Tracking (STEP5)
- **Symptôme** : Les points de repère faciaux générés par le modèle quantisé BlazeFace/FaceMesh tremblent fortement par rapport à la version FP32 CPU.
- **Action** : Ajuster les matrices de covariance de bruit de processus ($Q$) et de bruit de mesure ($R$) du Filtre de Kalman vectorisé pour lisser ce bruit quantique spécifique à l'INT8.

### Incident 2 : Le regroupement spectral (STEP4) engorge le CPU
- **Symptôme** : Bien que l'inférence audio YAMNet soit très rapide sur le TPU, l'étape de clustering prend un temps déraisonnable.
- **Action** : Paramétrer le solveur de `scikit-learn` (ex: `n_jobs=-1`) pour exploiter l'ensemble des cœurs de l'architecture Threadripper, ou procéder à une réduction de dimension préalable (PCA).

## ⚠️ Séparation des Responsabilités
Se concentre purement sur la viabilité et la performance des algorithmes mathématiques CPU. Intervient "après" le TPU, là où l'ASIC s'arrête, sans se substituer aux orchestrateurs globaux de STEP4 ou STEP5.
