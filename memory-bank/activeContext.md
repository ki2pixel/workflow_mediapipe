# Contexte Actif (Active Context)

## Tâche en Cours
Aucune tâche active.

## Objectifs
- [2026-02-01 18:10:00] **Post-production — Priorité Basse AE (COMPLET)** : Ajout `tracking_analytics` et `expression_summary` dans STEP6 (gated), pondération par `confidence` dans le script AE `Analyse-Écart-X` (configurable), et tests unitaires STEP6 associés.
- [2026-01-30 14:43:00] **Embeddings locuteurs STEP4 (COMPLET)** : Implémentation des embeddings locuteurs dans STEP4 (Pyannote + Lemonfox) avec flag `AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=1`, format JSON compact, préservation STEP6, tests unitaires et documentation. Les embeddings sont désormais disponibles pour After Effects via `*_audio.json` ou `*_tracking.json` après STEP6.
- [2026-01-30 13:33:00] **Documentation Scripts After Effects (COMPLET)** : Analyse complète des scripts JSX de post-production MediaPipe. Document créé dans `docs/workflow/post_production/AFTER_EFFECTS_SCRIPTS_ANALYSIS.md` avec évaluation de la cohérence STEP4/5, identification des améliorations potentielles et recommandations d'usage.
- [2026-01-30 02:36:00] **Post-production — Stabilisation AE via STEP6 + streaming STEP5 (COMPLET)** : Implémentation des points Priorité Haute : STEP6 reducer enrichi (tracking `*_tracking.json`, champs essentiels + `temporal_alignment`), script AE `Analyse-Écart-X` priorise STEP6 et utilise un parsing streaming sur STEP5 pour éviter les crashs mémoire. Tests unitaires STEP6 ajoutés et exécutés.
- [2026-01-24 15:25:00] **Frontend — Auto-ouverture logs paramétrable (COMPLET)** : Ajout du toggle "📟 Auto-ouverture des logs" dans Settings, synchronisation AppState/localStorage, conditionnement de `openLogPanelUI`/`sequenceManager` pour respecter la préférence utilisateur.
- [2026-01-21 20:05:00] **Frontend — Suppression toggles obsolètes (COMPLET)** : Nettoyage des contrôles "Logs Cinématiques" et "📜 Défilement Auto" devenus redondants avec Timeline Connectée (auto-scroll structurel). Fichiers impactés : `templates/index_new.html`, `static/main.js`, `static/eventHandlers.js`, `static/domElements.js`, suppression de `static/cinematicLogMode.js` et `static/css/features/cinematic-logs.css`. Tests UI non requis, vérification visuelle planifiée.
- [2026-01-21 14:36:00] **Audit Backend — init_app() pour threads de polling (COMPLET)** : Déplacement des threads `RemoteWorkflowPoller` et `CSVMonitorService` dans `init_app()` (logging + verrou/idempotence) afin d'éviter les doubles démarrages lors des imports/WSGI. Tests : `python3 -m py_compile app_new.py`.
- [2026-01-21 14:24:00] **Audit Backend — Simplification injection ENV Step5 (COMPLET)** : Refactor du gestionnaire STEP5 (`workflow_scripts/step5/run_tracking_manager.py`) pour centraliser la lecture des variables d'environnement via `_EnvConfig`, normaliser la sélection des moteurs/GPU et encapsuler l'injection `LD_LIBRARY_PATH` dans un helper dédié.
- [2026-01-21 13:38:00] **Audit Backend — Cache root configurable + ouverture explorateur désactivée en prod/headless (COMPLET)** : Ajout de `CACHE_ROOT_DIR` dans `config.settings.config`, remplacement du `/mnt/cache` en dur dans `services/filesystem_service.py`, et garde-fous `DISABLE_EXPLORER_OPEN` / `ENABLE_EXPLORER_OPEN` + détection headless (DISPLAY/WAYLAND_DISPLAY) pour empêcher l'ouverture explorateur côté serveur. Tests : `pytest -q tests/unit/test_filesystem_service.py`.

## Décisions Récentes
- [2026-02-03 01:34:00] **STEP5 — Simplification moteurs tracking (Phase 2)** : Finalisation de la simplification STEP5 : suppression réelle (git rm) des assets/scripts/tests legacy OpenSeeFace/OpenCV/EOS, nettoyage `face_engines.py` (ne garde que `InsightFaceEngine` + factory), retrait env vars legacy dans `config/settings.py`/`.env.example`, mise à jour docs (pipeline/architecture/guides) et scripts GPU (`validate_gpu_prerequisites.sh`). Tests unitaires alignés et validés (`pytest` ciblé OK). Architecture STEP5 désormais : MediaPipe CPU par défaut + InsightFace GPU-only.
- [2026-01-30 14:43:00] **Embeddings locuteurs STEP4** : Implémentation complète des embeddings locuteurs dans STEP4 avec activation par `AUDIO_INCLUDE_SPEAKER_EMBEDDINGS=1`. Support Pyannote et Lemonfox, format JSON compact normalisé, préservation par STEP6 reducer, tests unitaires (4 STEP4 + 2 STEP6) et documentation mise à jour. Robustesse garantie avec fallbacks silencieux et compatibilité streaming JSON.
- [2026-01-30 13:33:00] **Documentation Scripts After Effects** : Création de la documentation complète analysant les scripts JSX de post-production. Conclusion : scripts fonctionnels et cohérents avec les données STEP4/5, mais avec des améliorations possibles pour exploiter pleinement la richesse des données du pipeline. Le script `Analyse-Écart-X` est particulièrement pertinent pour la post-production créative.
- [2026-01-21 14:36:00] **Audit Backend — init_app() pour threads de polling** : Finalisation de la recommandation d'audit en déplaçant l'initialisation des threads de polling (`RemoteWorkflowPoller`, `CSVMonitorService`) dans `init_app()` avec verrou/globals idempotents. Le bloc `__main__` appelle désormais `init_app()` puis `APP_FLASK.run(...)`, évitant la création multiple de threads sous Gunicorn/tests.

## Questions Ouvertes
Aucune question ouverte.

## Prochaines Étapes
Aucune tâche prévue.
