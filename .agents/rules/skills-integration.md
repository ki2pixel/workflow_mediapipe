---
trigger: model_decision
description: Automatic skill detection and routing matrix for workflow_mediapipe based on pattern matching and priority hierarchy
globs: 
---

# Skills Integration Matrix

## Detection Patterns

| Pattern | Skill | Priority |
|---------|-------|----------|
| `bug`, `error`, `crash`, `performance`, `slow`, `optimize` | debugging-strategies | 1 |
| `feature`, `add`, `implement`, `create`, `build` | workflow-operator | 1 |
| `documentation`, `docs`, `README`, `guide` | documentation | 1 |
| `tâche`, `task`, `backlog`, `planification`, `roadmap` | shrimp-task-manager.md | 1 |
| `réflexion`, `think`, `logique`, `architecture`, `analyser` | sequentialthinking | 1 |
| `test`, `testing`, `coverage`, `pytest` | tests-suite-guardian | 2 |
| `pipeline`, `step4`, `audio`, `lemonfox`, `pyannote` | step4-audio-orchestrator | 2 |
| `tracking`, `step5`, `mediapipe`, `insightface`, `gpu` | step5-gpu-ops | 2 |
| `timeline`, `frontend`, `ui`, `logs`, `overlay` | frontend-timeline-designer | 2 |
| `logs`, `overlay`, `conductor` | logs-overlay-conductor | 2 |
| `coral`, `tpu`, `gasket`, `pcie`, `apex_0`, `orchestrator`, `sram` | coral-tpu-system-orchestration | 2 |
| `tflite`, `int8`, `quantization`, `compiler`, `edgetpu`, `half_pixel_centers` | coral-tpu-model-compiler | 2 |
| `kalman`, `spectral`, `clustering`, `hybrid`, `jittering`, `cosine` | coral-tpu-hybrid-algorithms | 2 |
| `gros fichier`, `massive file`, `chirurgical`, `edit block` | fast-filesystem | 2 |
| `json`, `path`, `structure`, `inspect`, `valeur`, `clé` | json-query | 2 |
| `diagnostics`, `health`, `env`, `validation` | pipeline-diagnostics | 3 |
| `after`, `effects`, `ae`, `jsx`, `script` | after-effects-scripts | 3 |
| `cep`, `panel`, `extension`, `adobe` | after-effects-cep-panel | 3 |
| `csv`, `monitoring`, `download`, `webhook` | csv-monitoring-sme | 3 |
| `docs`, `update`, `workflow`, `updater` | workflow-docs-updater-plus | 3 |

## Auto-Loading Logic

When patterns detected, automatically load:
```
fast_read_file(".agents/skills/[SKILL_NAME]/SKILL.md")
```

## Multi-Skill Support

For complex requests, combine multiple skills based on pattern detection priority.

## Skills Usage Policy

- **Local Skills** (`.agents/skills/`) : workflow-operator, debugging-strategies, documentation, tests-suite-guardian, step4-audio-orchestrator, step5-gpu-ops, frontend-timeline-designer, logs-overlay-conductor, coral-tpu-system-orchestration, coral-tpu-model-compiler, coral-tpu-hybrid-algorithms, pipeline-diagnostics, after-effects-scripts, after-effects-cep-panel, csv-monitoring-sme, workflow-docs-updater-plus, shrimp-task-manager, sequentialthinking, fast-filesystem, json-query
- **Global Skills** : Only if no local equivalent
- **Detection** : Automatic via pattern matching above
- **Priority** : Local skills first, then global fallback
- **Hierarchy** : workflow-operator > Skills locales > Règles coding standards > Docs > Skills globales