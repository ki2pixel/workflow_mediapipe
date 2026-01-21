# Matrice de Traçabilité Documentation ↔ Code

| Fonctionnalité / Domaine | Documentation(s) de référence | Implémentation(s) de référence |
| --- | --- | --- |
| Timeline Connectée (Phases 1-3) | `docs/workflow/core/ARCHITECTURE_COMPLETE_FR.md` (§ Interface Utilisateur), `docs/workflow/core/GUIDE_DEMARRAGE_RAPIDE.md` (§ Timeline) | `templates/index_new.html`, `static/css/components/steps.css`, `static/stepDetailsPanel.js`, `static/uiUpdater.js`, `tests/frontend/test_step_details_panel.mjs` |
| Logs Panel Phase 2 (overlay + header contextuel) | `docs/workflow/admin/UPDATE_DOCUMENTATION_SUMMARY.md` (section « Audit Logs Panel — Phase 2 ») | `templates/index_new.html`, `static/css/components/logs.css`, `static/domElements.js`, `static/uiUpdater.js`, `tests/frontend/test_timeline_logs_phase2.mjs` |
| Historique téléchargements SQLite | `docs/workflow/technical/CSV_DOWNLOADS_MANAGEMENT.md`, `docs/workflow/core/ARCHITECTURE_COMPLETE_FR.md` (§ Historique SQLite) | `services/download_history_repository.py`, `services/csv_service.py`, `scripts/migrate_download_history_to_sqlite.py` |
| Cinematic Log Mode | `docs/workflow/core/GUIDE_DEMARRAGE_RAPIDE.md` (§ Monitoring des Logs), `docs/workflow/core/ARCHITECTURE_COMPLETE_FR.md` (§ Cinematic Log Mode) | `static/cinematicLogMode.js`, `templates/index_new.html`, `static/css/components/logs.css` |
| STEP5 InsightFace / Maxine (GPU-only) | `docs/workflow/pipeline/STEP5_SUIVI_VIDEO.md` (§ Moteurs 7-8), `docs/workflow/core/GUIDE_DEMARRAGE_RAPIDE.md` (§ STEP5 env) | `workflow_scripts/step5/face_engines.py`, `workflow_scripts/step5/run_tracking_manager.py`, `config/settings.py` |
| STEP4 Lemonfox (variables + fallback) | `docs/workflow/pipeline/STEP4_ANALYSE_AUDIO.md` (§ Synthèse `LEMONFOX_*`) | `workflow_scripts/step4/run_audio_analysis_lemonfox.py`, `services/lemonfox_audio_service.py`, `config/settings.py` |
| Threads de polling (`app_new.py` + `start_workflow.sh`) | `docs/workflow/core/GUIDE_DEMARRAGE_RAPIDE.md` (§ Comprendre `start_workflow.sh` vs `app_new.py`), `docs/workflow/core/ARCHITECTURE_COMPLETE_FR.md` (§ WorkflowService/WorkflowState) | `app_new.py` (`init_app()` + threads), `start_workflow.sh`, `services/workflow_service.py` |
| Smart Upload (legacy) | `docs/workflow/README.md` (renvoi archive), `docs/workflow/admin/UPDATE_DOCUMENTATION_SUMMARY.md` (§ legacy) | `docs/workflow/legacy/SMART_UPLOAD_FEATURE.md` (archive), `memory-bank/decisionLog.md` (entrée 2026-01-18) |

> Cette matrice doit être complétée à chaque nouvelle fonctionnalité majeure : ajouter la documentation primaire, les fichiers de code maîtres et les tests associés.
