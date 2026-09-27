# Contexte Actif (Active Context)

## Tâche en Cours
- Aucune tâche active.

## Dernière Session Clôturée
- [2026-09-27 22:05:00] Renumérotation des variables d'environnement et des endpoints audio (COMPLET) :
  - **Décision** : les variables `STEPn_*` suivent désormais la numérotation actuelle du pipeline (STEP2_* transitions, STEP3_* audio, STEP4_* tracking, STEP5_* réduction JSON, STEP6_* pré-traitement AE) ; les endpoints audio passent de `/api/step4/*` à `/api/audio/*` en renommage sec. Détail et garde-fous dans `decisionLog.md`.
  - **Implémentation** : ~1300 occurrences renommées dans 73 fichiers ; `scripts/migrate_env_step_names.py` (passe unique, sauvegarde horodatée, marqueur `ENV_STEP_SCHEMA=2`) ; `.env` local migré (sauvegarde `.env.bak-*`) ; garde-fou `Config.check_step_env_schema()` — erreur en production, avertissement en développement — car le décalage est une permutation et un `.env` non migré change de sens silencieusement.
  - **Piège rencontré** : `utils/tracking_optimizations.py` lisait encore les anciens noms après le premier passage (répertoire absent des cibles) ; détecté par un contrôle de bijection « HEAD vs arbre courant » sur tous les fichiers suivis, puis corrigé.
  - **Validation** : suites backend et frontend au vert ; `/api/audio/lemonfox` → 401 sans token, `/api/step4/lemonfox_audio` → 404 ; `.env` migré chargé correctement (STEP4_TRACKING_ENGINE=insightface, USE_OPENCV5_STEP4=true).
- [2026-09-27 20:55:00] Suppression de l'étape « 2. Conversion des vidéos » et renumérotation STEP1→STEP7 (COMPLET) :
  - **Décision** : la normalisation vidéo (MP4 / H.264 / yuv420p / 25 fps) portée par l'ancienne STEP2 est déplacée dans STEP1 (`utils/media_normalizer.py`) ; les clés d'étapes sont renumérotées en continu de STEP1 à STEP7 (transitions=2, audio=3, tracking=4, réduction JSON=5, pré-traitement AE=6, finalisation=7). Détail et alternatives rejetées dans `decisionLog.md`.
  - **Implémentation** : `workflow_scripts/step2/convert_videos.py` supprimé ; `extract_archives.py` normalise après chaque extraction (modes `--normalize-only` / `--normalize-only --force` pour le rattrapage) ; dossiers `workflow_scripts/stepN`, `logs/stepN`, `config/stepN_*.json`, fichiers de tests, `pytest.ini`, runners et documentation renommés en bloc ; timeline frontend à 7 tuiles et purge one-shot de `selectedStepsOrder` dans `AppState`.
  - **Garde-fou** : avertissement de framerate non conforme dans les trois entrées d'analyse des transitions (risque de désynchronisation frame/timecode en aval).
  - **Validation** : suite backend complète (unit + intégration) et suites frontend Node ESM au vert.

## Prochaine Action
- Redémarrer l'application (le `.env` a été migré et le cache frontend doit être reconstruit).
- Rattraper les projets extraits avant la migration : `env/bin/python workflow_scripts/step1/extract_archives.py --normalize-only`.
- Lancer et monitorer le workflow complet (1→7) sur un projet de test.
- Mettre à jour les appels externes vers `/api/audio/lemonfox` et `/api/audio/deepinfra` (curl, n8n, règles de reverse-proxy).
