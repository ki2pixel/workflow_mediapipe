# 🔄 Pipeline Workflow

Documentation détaillée des 7 étapes du pipeline MediaPipe.

## Étapes du Pipeline

1. **[STEP1_EXTRACTION.md](STEP1_EXTRACTION.md)** — Extraction d'archives
2. **[STEP2_CONVERSION.md](STEP2_CONVERSION.md)** — Conversion vidéo
3. **[STEP3_DETECTION_SCENES.md](STEP3_DETECTION_SCENES.md)** — Détection de scènes
4. **[STEP4_ANALYSE_AUDIO.md](STEP4_ANALYSE_AUDIO.md)** — Analyse audio
5. **[STEP5_SUIVI_VIDEO.md](STEP5_SUIVI_VIDEO.md)** — Suivi vidéo et blendshapes
6. **[STEP6_REDUCTION_JSON.md](STEP6_REDUCTION_JSON.md)** — Réduction JSON
7. **[STEP7_FINALISATION.md](STEP7_FINALISATION.md)** — Finalisation et archivage

## Développement

Chaque étape dispose de son propre script dans `workflow_scripts/step{N}/` et sa configuration dans `WorkflowCommandsConfig`.
