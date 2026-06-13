---
name: coral-tpu-hybrid-algorithms
description: Expert des algorithmes CPU (Filtre de Kalman, Clustering Spectral) mis en place pour compenser la perte de précision INT8 et les limites de l'ASIC Coral.
trigger: kalman, spectral, clustering, cosine, hybrid, jittering
---

# Coral TPU Hybrid Algorithms Skill

Ce skill encadre les heuristiques mathématiques déportées sur le CPU pour compenser la limitation matérielle (précision INT8, manque d'opérations complexes) du TPU Coral.

## 🎯 Rôle
Déboguer, profiler et optimiser les calculs lourds qui s'exécutent sur le CPU en complément des inférences TPU. Cela inclut le Filtre One-Euro (52 dimensions) par défaut pour réduire le jittering (avec le Filtre de Kalman vectorisé en secours), le Clustering Hiérarchique Agglomératif (AHC) et le Regroupement Spectral via `scikit-learn` pour l'audio, et les calculs de Distance Cosinus.

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
- **Action** : Valider que le filtre One-Euro (`OneEuroFilterND`) est activé par défaut. Ajuster ses paramètres `min_cutoff` (seuil de coupure minimum pour stabiliser à basse vitesse) et `beta` (sensibilité à la vitesse pour éviter la traînée/décalage). En cas de fallback sur le Filtre de Kalman vectorisé, ajuster les matrices de covariance de bruit de processus ($Q$) et de bruit de mesure ($R$) pour lisser le bruit quantique spécifique à l'INT8.

### Incident 2 : Le clustering audio (STEP4) est inexact ou engorge le CPU
- **Symptôme** : Division fictive des locuteurs ou lenteurs lors du regroupement des d-vectors ECAPA-TDNN.
- **Action** : Veiller à ce que l'Agglomerative Hierarchical Clustering (AHC) soit utilisé en production avec une métrique `cosine`, linkage `average` et un seuil de distance `distance_threshold=0.32`. S'assurer que le post-traitement réassigne les locuteurs mineurs (<7.0s de parole cumulée) aux centroïdes des locuteurs majeurs les plus proches. Si l'estimation adaptative du nombre de locuteurs par Spectral Clustering (Eigen-gap/Silhouette) est activée, paramétrer le solveur de `scikit-learn` (ex: `n_jobs=-1`) ou restreindre l'analyse aux `max_speakers` autorisés pour soulager le CPU.

## ⚠️ Séparation des Responsabilités
Se concentre purement sur la viabilité et la performance des algorithmes mathématiques CPU. Intervient "après" le TPU, là où l'ASIC s'arrête, sans se substituer aux orchestrateurs globaux de STEP4 ou STEP5.
