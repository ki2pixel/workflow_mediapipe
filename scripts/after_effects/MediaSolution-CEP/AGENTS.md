# Repository Guidelines

Adobe CEP panel extension for After Effects (Media Solution v12.0). Adapts a standalone ExtendScript batch-processing script into a hosted HTML/JS panel with optional Python bridges for auto-recentering and CSV cuts parsing. Part of the Workflow MediaPipe v4.1 pipeline. No build system, no package manager — files are deployed as-is into the CEP extensions folder.

## Project Structure & Module Organization

Two-side CEP architecture with a vendored Adobe library:

- **`.\CSXS\manifest.xml`** — CEP manifest targeting `AEFT` (After Effects) `[13.0,99.9]`, CSXS 5.0. Enables `--enable-nodejs` and `--mixed-context` so the client can use Node.js APIs.
- **`.\client\`** — Panel UI (HTML/CSS/JS loaded in the CEF browser inside AE). `.\client\main.js` holds all client logic: event binding, config persistence (localStorage), bridge health monitoring, named-pipe IPC via Node.js `net`/`child_process`, and **batch orchestration via pipe** (optional "Batch Pipe" mode, see below). `.\client\CSInterface.js` is Adobe's vendored CEP library — do not edit.
- **`.\host\MediaSolution.jsx`** — ~3300-line ExtendScript (ES3) IIFE containing all After Effects business logic: folder selection, batch processing, diagnostics, cuts application, Python bridge calls. Functions are exported to CEP via `$.global.<name> = <ref>` at the bottom of the file. Since 07/08/2026, Step3.2 (import → prepare → cuts) is factored into per-step primitives (`step3_2_importImages`, `step3_2_prepareLayer`, `step3_2_applyCuts`) plus string-based wrappers exported for client-driven orchestration (`step3_2ImportImagesForFolder`, `step3_2PrepareLayerByComp`, `step3_2ApplyCutsByComp`, `batchPipe*`).

**Communication pattern:** Client→Host via `csInterface.evalScript("fnName(args)")`. Host→Client via `CSXSEvent` dispatched through `PlugPlugExternalObject` on event type `com.workflowmediapipe.mediasolution.hostMessage`, payload is a JSON string. The host uses a private `myJSON` polyfill (not native `JSON`) to avoid global prototype pollution from third-party AE plugins.

**Python bridge (dual transport):** Mailbox mode writes/reads `cep_to_py.json` / `py_to_cep.json` files polled with `$.sleep`. Pipe mode (client-side Node.js) connects to `\\.\pipe\mediasolution` — a **self-hosted named pipe served by `bridge_daemon.py`** (ctypes `CreateNamedPipeW`, stdlib pure, runs in the daemon's main thread; added 07/08/2026). Single-instance locking uses a Windows Kernel Named Mutex (`Local\PyShiftBridge_Daemon_SingleInstance_Mutex`) + OS file lock (`msvcrt.locking`) since 20/08/2026, eliminating stale PID recycling lockups. The client probes the pipe at health-check time and auto-switches pipe ↔ mailbox, re-testing a few seconds after spawning the daemon. Note: PyShiftAE (v0.1.1 and v1.0.1 alike) implements **no** CEPy named-pipe transport — the `CreatePipe` in the v1.0.1 `.aex` is an anonymous stdout-redirection pipe, and the real v1.0.1 IPC is `boost::message_queue` (`PyC21`/`PyR21`, non-JSON, unusable from Node); see `docs/confirmation_diagnostic.md`. The installed version is **PyShiftAE v1.0.1** (migrated 14/07/2026, see `PyShiftBridge/tools/migrate_to_1.0.1.py`); Mailbox remains the fallback transport. The client can spawn a detached Python daemon (`bridge_daemon.py`) when health pings fail. Standalone daemon `RuntimeError` is expected — ExtendScript fallback handles all AE API calls natively.

**Batch orchestration via pipe (optional mode):** The multi-folder batch is normally driven by the host (`startBatchQueue`/`processBatch`, mailbox transport). Since 07/08/2026, the client can instead orchestrate the batch step by step (button "Batch Pipe" in `client/index.html`): it loops over folders/projects with sequential `evalScript` calls to `batchPipe*` host functions, and routes **only pure computations** through the pipe — `mediasolution_apply_cuts_active_layer` (segments) and `mediasolution_apply_auto_recentering` (center/label). Import, layer-prepare and project-open stay host-native because the daemon returns `status:"fallback"` for those entrypoints (they need the AE DOM). The client never relies on `app.project.activeItem` (null in batch, no viewer open): project context (matching CSV, tracking JSON, comp/layer info, bridge config) is resolved host-side by `batchPipeGetProjectContext`, and segments/coordinates are applied via `applyComputedCutsToLayerByComp`/`applyAutoRecenteringCoords`. Pipe calls are strictly serialized (the daemon serves one connection at a time in its main thread) and `sendCommandToPythonPipe` retries ENOENT a few times, because `_pipe_serve_one` closes and recreates the pipe handle after each served connection. Full fallback to the host batch when the pipe is unavailable. See `docs/BATCH_PIPE_ORCHESTRATION.md`.

## Build, Test, and Development Commands

No build step. To develop:

1. Copy/symlink the extension folder to `%APPDATA%\Adobe\CEP\extensions\` (Windows) or `~/Library/Application Support/Adobe/CEP/extensions/` (macOS).
2. In After Effects: `Help > Enable Debugging`, then restart.
3. Open via `Window > Extensions > Media Solution v12.0`.
4. After edits, reload with `Window > Extensions > Reload Extensions` or restart AE.

Debug tools: F12 inside the panel for CEP Chromium DevTools; ExtendScript Toolkit / AE console for host-side `$.writeln` logs.

No test suite exists.

## Coding Style & Naming Conventions

No linter or formatter is configured. Conventions are enforced by the ExtendScript (ES3) runtime constraints:

- **Never shadow built-ins** (`JSON`, `Math`, `String`) with local `var` declarations — ES3 silently ignores the shadowing. Use unique names (e.g. `myJSON`).
- **Always `var`-declare every temporary variable** (`i`, `k`, `v`, `partial`) inside recursive functions to prevent cross-recursion memory overwrite.
- Host functions that need CEP access must be exported on `$.global` at the bottom of `.\host\MediaSolution.jsx`.
- Client code uses an IIFE with `'use strict'`; state lives in a single `state` object.
- JSON files on disk are written atomically (temp file + rename) to avoid Windows file-lock corruption.
