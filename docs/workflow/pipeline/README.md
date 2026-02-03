# 🔄 Pipeline Workflow

> **Metrics Snapshot** (cloc 2026-01-26) – 115 source files, 106 991 LOC (code only). Python leads (54 files / 15 043 LOC), followed by JavaScript (24 / 5 641 LOC) and CSS (17 / 3 594 LOC). Complexity hotspots (Radon) identified in CSV ingestion (Score F) and STEP5 workers (Score F); see [COMPLEXITY_ANALYSIS.md](../core/COMPLEXITY_ANALYSIS.md) for detailed analysis.

## Overview

This directory contains the complete technical documentation for the 8‑step MediaPipe video processing pipeline. Each step follows a **uniform template**:

- **Purpose & Pipeline Role** – What the step does and its position in the workflow
- **Inputs & Outputs** – Expected artifacts and generated results
- **Command & Environment** – `WorkflowCommandsConfig` command and virtual environment used
- **Dependencies** – Key libraries and external services
- **Configuration** – Relevant environment variables and tuning knobs
- **Known Hotspots** – References to high‑complexity backend modules (from Radon analysis)
- **Metrics & Monitoring** – Performance indicators and logging patterns
- **Failure & Recovery** – Common error modes and remediation steps
- **Related Documentation** – Cross‑links to technical guides and audit reports

## Étapes du Pipeline

1. **[STEP1_EXTRACTION.md](STEP1_EXTRACTION.md)** — Extraction d'archives
2. **[STEP2_CONVERSION.md](STEP2_CONVERSION.md)** — Conversion vidéo
3. **[STEP3_DETECTION_SCENES.md](STEP3_DETECTION_SCENES.md)** — Détection de scènes
4. **[STEP4_ANALYSE_AUDIO.md](STEP4_ANALYSE_AUDIO.md)** — Analyse audio
5. **[STEP5_SUIVI_VIDEO.md](STEP5_SUIVI_VIDEO.md)** — Suivi vidéo et blendshapes
6. **[STEP6_REDUCTION_JSON.md](STEP6_REDUCTION_JSON.md)** — Réduction JSON
7. **[STEP7_PRETRAITEMENT_AE.md](STEP7_PRETRAITEMENT_AE.md)** — Pré-traitement AE (JSON optimisé)
8. **[STEP8_FINALISATION.md](STEP8_FINALISATION.md)** — Finalisation et archivage

## Development & Operations

- **Scripts Location**: Each step has its own script in `workflow_scripts/step{N}/`
- **Configuration**: Centralized in `WorkflowCommandsConfig` (see `config/settings.py`)
- **State Management**: All steps interact via `WorkflowState` (thread‑safe RLock)
- **Complexity Context**: Backend hotspots (CSV/STEP5 workers) are flagged in individual step docs
- **Testing**: Refer to `technical/TESTING_STRATEGY.md` for test coverage and environment isolation

### Current Radon Hotspots (Jan 25 2026)

| Severity | Module / Function | Impacted Docs |
| --- | --- | --- |
| F | `services/csv_service.py::_check_csv_for_downloads`, `_normalize_url` | STEP4 (webhook ingestion prerequisites)
| F | `workflow_scripts/step4/run_audio_analysis.py::main` | STEP4_ANALYSE_AUDIO.md (Pyannote/Lemonfox runner)
| F | `workflow_scripts/step5/process_video_worker.py::main`, `workflow_scripts/step5/process_video_worker_multiprocessing.py::{init_worker_process, process_frame_chunk}` | STEP5_SUIVI_VIDEO.md (tracking workers)
| F | `workflow_scripts/step5/run_tracking_manager.py::main` | STEP5_SUIVI_VIDEO.md (manager orchestration)
| F | `services/report_service.py::generate_monthly_archive_report` | `../features/REPORTS_ARCHITECTURE.md`

Hotspots with severity ≥ C must be documented and kept under watch. Update the referenced docs whenever the underlying implementation changes or when Radon surfaces new blocks with score ≥ 10.

---

*Generated with Code-Doc protocol (tree, cloc, radon) – see `../cloc_stats.json` and `../complexity_report.txt`.*
