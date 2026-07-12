# Repository Guidelines

Flask + native-JS pipeline that turns raw video archives into After Effects-ready
artifacts through eight sequential steps (extraction → conversion → scene
detection → audio diarization → tracking → JSON reduction → AE preprocessing →
finalization). Each step runs in its own Python virtualenv so incompatible
dependencies (PyTorch, MediaPipe, InsightFace, Coral TPU) coexist. Docs are
French (`docs/workflow/`); commits and PRs are English.

## Project Structure & Module Organization

- `./app_new.py` — Flask entrypoint wiring blueprints, services, and
  `WorkflowState`.
- `./services/` — pure business logic. Singletons via `get_workflow_state()`,
  `FilesystemService`, `CSVService`, `WorkflowService`; all Coral TPU calls
  queue through `services/coral_tpu_orchestrator.py`.
- `./routes/` — thin Flask blueprints; only validation + service call,
  decorated with `@measure_api`.
- `./config/` — `settings.py`, `workflow_commands.py`, `security.py`,
  `step3_transnet.json`, `step3_tpu.json`. No hardcoded paths or secrets.
- `./workflow_scripts/step{1..8}/` — per-step executables. Venvs live at
  `${VENV_BASE_DIR:-.}/{env,transnet_env,audio_env,tracking_env_slim,insightface_env,tracking_cv5_env,transnet_cv5_env,coral_env}`.
- `./static/utils/` — `DOMBatcher.js`, `AppState.js`, `PollingManager.js`,
  `DOMDiff.js`, `WorkerManager.js`, `PerformanceMonitor.js`.
- `./scripts/after_effects/MediaSolution-CEP/` — ES3 ExtendScript panel;
  Python bridge via `system.callSystem()`.
- `./memory-bank/` — accessed **only** through `fast-filesystem` MCP tools
  (`.agents/rules/memorybankprotocol.md`).
- `./tests/{unit,integration,frontend,legacy}` — pytest suites plus Node ESM
  frontend tests; `tests/legacy/` is deprecated MySQL coverage.

## Build, Test, and Development Commands

```bash
./start_workflow.sh                                  # runs app_new.py on :5003
python -m venv env && source env/bin/activate && pip install -r requirements_env.txt
pytest tests/unit tests/integration                  # backend default
npm run test:frontend                                # Node ESM frontend
./scripts/run_tests.sh                               # full coverage
PYTHONPATH=transnet_env ./scripts/run_step3_tests.sh # step-3 only
./scripts/run_step5_tests.sh                         # step-5 only
./scripts/diagnose_tests.sh                          # drift diagnostics
python scripts/validate_startup.py                   # blocks prod on default secrets
```

## Coding Style & Naming Conventions

Authoritative rules: `./.agents/rules/codingstandards.md` (mirrored in
`.clinerules/`, `.windsurf/rules/`).

- Routes are paper-thin; logic lives in `services/`. `WorkflowState` is a
  thread-safe singleton guarded by `RLock`; no `PROCESS_INFO` globals.
- All I/O via `FilesystemService.open_path_in_explorer()` with locks; logs are
  raw `progress_text` plus streamed JSON.
- OpenCV 5.0 workers must use `multiprocessing.get_context("spawn")` and
  `cv2.setNumThreads(1)` (STEP 3 stays sequential — spawn cost too high).
- Frontend is immutable: `appState.setState()` shallow-diff, mutations through
  `DOMBatcher.scheduleUpdate()`, polling only via `PollingManager`. Dynamic
  HTML must pass through `DOMUpdateUtils.escapeHtml()`.
- Large JSON via `ijson` / `StreamingJSONOutput` — never `json.load()`. Coral
  TPU inferences must queue through `coral_tpu_orchestrator.py`.
- Secrets and runtime config flow `.env` → `config/settings.py`; the startup
  validator refuses to boot in production with default tokens.
- After Effects scripts stay ES3 (`var`, classic `for`, no arrow, IIFE wrap);
  batch timeline mutations in `app.beginUndoGroup`/`endUndoGroup`.

## Testing Guidelines

- `pytest.ini` restricts default discovery to `tests/unit` and
  `tests/integration`; excluded files (`test_step3_transnet.py`,
  `test_step5_*.py`, `test_tracking_optimizations_*.py`) run via their
  dedicated scripts with the matching venv on `PYTHONPATH`.
- Frontend tests live in `tests/frontend/*.test.{js,mjs}` and import
  `./tests/frontend/setup.mjs`.
- Each test carries `// Given / When / Then` markers. Aim for ≥ failure-case
  parity with normal cases; target 100% branch coverage on critical paths
  (`process_video_worker`, `CSVService._normalize_url`, `WorkflowService`).
- CI exports `DRY_RUN_DOWNLOADS=true`, `ENABLE_GPU_MONITORING=false`,
  `FLASK_ENV=testing`. Manual validation scripts under `tests/validation/`
  are intentionally not auto-collected.

## Commit & Pull Request Guidelines

- Conventional Commits, English. `<Prefix>(scope)?: <imperative ≤50 chars>`
  then `- ` bullets, optional `Refs: #N` / `BREAKING CHANGE:`. Allowed
  prefixes: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`,
  `chore`, `style`, `revert`. Always derive messages from `git diff`.
- PR title mirrors the commit prefix; body must include `## Overview` and
  `## Changes`, plus `## Technical Details`, `## Test Content`, and
  `## Related Issues` (`./.agents/rules/pr-message-format.md`).

## Agent Skills and Workflows

Project-local skills under `./.agents/skills/` (mirrored to `.clinerules/`,
`.windsurf/`, `.cline/`) override global behavior. Stack order from
`codingstandards.md`: `workflow-operator` → debug/local skills → these rules →
docs → global skills. Standard workflows (commit, docs-updater,
repomix-bundle, enhance, end) live in `./.agents/workflows/`.
