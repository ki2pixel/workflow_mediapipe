## Étapes du workflow

1. [Étape 1 - Extraction des archives](./pipeline/STEP1_EXTRACTION.md)
2. [Étape 2 - Conversion des vidéos](./pipeline/STEP2_CONVERSION.md)
3. [Étape 3 - Analyse des transitions](./pipeline/STEP3_DETECTION_SCENES.md)
4. [Étape 4 - Analyse audio](./pipeline/STEP4_ANALYSE_AUDIO.md)
5. [Étape 5 - Analyse du tracking](./pipeline/STEP5_SUIVI_VIDEO.md)
6. [Étape 6 - Réduction JSON](./pipeline/STEP6_REDUCTION_JSON.md)
7. [Étape 7 - Pré-traitement AE](./pipeline/STEP7_PRETRAITEMENT_AE.md)
8. [Étape 8 - Finalisation](./pipeline/STEP8_FINALISATION.md)

## Documents clés

### Services Critiques
- [Service CSV — Monitoring et Téléchargements](./features/CSV_SERVICE.md)
- [Service Lemonfox Audio — Integration STT/LLM](./features/LEMONFOX_AUDIO_SERVICE.md)
- [Service Workflow — Orchestrateur Central](./features/WORKFLOW_SERVICE.md)
- [Service Visualization — Métriques et Rapports](./features/VISUALIZATION_SERVICE.md)
- [Service Results Archiver — Archivage des Résultats](./features/RESULTS_ARCHIVER_SERVICE.md)

### Pipeline et Complexité
- [STEP5 Workers — Architecture Multiprocessing](./pipeline/STEP5_WORKERS_COMPLEXITY.md)
- [Analyse de Complexité — Points Chauds Radon](./complexity/COMPLEXITY_HOTSPOTS.md)
- [Architecture complète du système de workflow](./core/ARCHITECTURE_COMPLETE_FR.md)

Pour les badges de provenance (Projet vs Archives) affichés dans les rapports et l'intégration avec les archives, voir la section dédiée dans [ARCHITECTURE_COMPLETE_FR.md](./core/ARCHITECTURE_COMPLETE_FR.md).
