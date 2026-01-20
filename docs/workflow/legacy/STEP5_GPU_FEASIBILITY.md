> **⚠️ DOCUMENT HISTORIQUE - ARCHIVÉ LE 13 JANVIER 2026**
> 
> Ce document a été archivé car son contenu est obsolète. La politique actuelle (depuis décembre 2025) restreint l'utilisation du GPU pour STEP5 au moteur InsightFace uniquement. Les autres moteurs (MediaPipe, OpenCV YuNet, OpenSeeFace, EOS) sont maintenant exécutés exclusivement en mode CPU pour des raisons de stabilité et de performance.
> 
> Pour la documentation actuelle sur l'utilisation GPU avec STEP5, voir : [STEP5_GPU_USAGE.md](../optimization/STEP5_GPU_USAGE.md)

---

# Rapport de Faisabilité : Support GPU pour les Moteurs STEP5

**Date** : 21 décembre 2025  
**Statut** : ANALYSE TECHNIQUE COMPLÈTE (OBSOLÈTE)  
**Auteur** : Analyse automatisée via workflow `/enhance`  
**Contexte** : Évaluation de la possibilité d'ajouter un mode GPU optionnel aux 4 moteurs STEP5 (mediapipe_landmarker, opencv_yunet_pyfeat, openseeface, eos) tout en préservant le mode CPU-only par défaut (v4.1).

---

## Sommaire Exécutif

**Verdict global** : ⚠️ **Partiellement faisable avec investissement modéré** (OBSOLÈTE)

- **MediaPipe Landmarker** : ✅ **Faisable** — nécessite installation TensorFlow Lite GPU delegate
- **OpenCV YuNet + PyFeat** : ✅ **Faisable** — nécessite migration vers `onnxruntime-gpu` + CUDA provider (détection YuNet reste CPU mais FaceMesh/py-feat profitent du GPU)
- **OpenSeeFace** : ✅ **Faisable** — même stack que YuNet (ONNX + CUDA)
- **EOS** : ⚠️ **Incertain** — bindings C++ natifs, investigation approfondie requise

**Risques majeurs identifiés** :
1. Contention VRAM avec STEP2 (conversion vidéo NVENC déjà active)
2. Complexité de maintenance multi-stack GPU
3. Incohérences potentielles entre moteurs GPU/CPU
4. Dépendances TensorFlow vs ONNX conflictuelles

**Recommandation finale (obsolète)** : Prioriser InsightFace GPU-only, maintenir autres moteurs en CPU pour stabilité.

---

## Note d'Archivage

Ce document a été conservé pour référence historique mais ne reflète plus la politique technique actuelle. La décision finale a été de restreindre le GPU STEP5 au moteur InsightFace uniquement pour simplifier l'architecture et garantir la stabilité du système.

**Politique actuelle** :
- `STEP5_ENABLE_GPU=1` + `STEP5_GPU_ENGINES="insightface"` : GPU activé uniquement pour InsightFace
- Autres moteurs : Force CPU-only, même avec flags GPU actifs
- Bascule automatique CPU si GPU indisponible (`STEP5_GPU_FALLBACK_AUTO=1`)
