# Contexte Actif (Active Context)

## Tâche en Cours
- Aucune tâche active.

## Dernière Session Clôturée
- [2026-09-27 20:55:00] Suppression de l'étape « 2. Conversion des vidéos » et renumérotation STEP1→STEP7 (COMPLET) :
  - **Décision** : la normalisation vidéo (MP4 / H.264 / yuv420p / 25 fps) portée par l'ancienne STEP2 est déplacée dans STEP1 (`utils/media_normalizer.py`) ; les clés d'étapes sont renumérotées en continu de STEP1 à STEP7 (transitions=2, audio=3, tracking=4, réduction JSON=5, pré-traitement AE=6, finalisation=7). Détail et alternatives rejetées dans `decisionLog.md`.
  - **Implémentation** : `workflow_scripts/step2/convert_videos.py` supprimé ; `extract_archives.py` normalise après chaque extraction (modes `--normalize-only` / `--normalize-only --force` pour le rattrapage) ; dossiers `workflow_scripts/stepN`, `logs/stepN`, `config/stepN_*.json`, fichiers de tests, `pytest.ini`, runners et documentation renommés en bloc ; timeline frontend à 7 tuiles et purge one-shot de `selectedStepsOrder` dans `AppState`.
  - **Garde-fou** : avertissement de framerate non conforme dans les trois entrées d'analyse des transitions (risque de désynchronisation frame/timecode en aval).
  - **Validation** : suite backend complète (unit + intégration) et suites frontend Node ESM au vert.

## Prochaine Action
- Rattraper les projets extraits avant la migration : `env/bin/python workflow_scripts/step1/extract_archives.py --normalize-only`.
- Lancer et monitorer le workflow complet (1→7) sur un projet de test.
