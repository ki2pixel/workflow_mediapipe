# Tests de Référence (docs/workflow/tests)

## Couverture des tests unitaires récents

- **`tests/unit/test_step5_export_verbose_fields.py`** : vérifie la réduction contrôlée des exports JSON STEP5 (`STEP5_EXPORT_VERBOSE_FIELDS`) et les profils de filtrage des blendshapes. À exécuter après toute modification de `utils/tracking_optimizations.py`, des moteurs STEP5 ou de la configuration des exports.
- **`tests/unit/test_object_detector_registry.py`** : garantit la résolution correcte des modèles du registry STEP5 (`workflow_scripts/step5/object_detector_registry.py`) ainsi que les chemins overrides via l'environnement. À exécuter dès qu'un nouveau modèle est ajouté ou qu'une logique de fallback est modifiée.

> Pensez à consigner l'exécution de ces tests lors des mises à jour de documentation ou d'architecture afin d'assurer la traçabilité qualité.
