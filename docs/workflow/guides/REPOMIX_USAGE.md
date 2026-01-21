# Repomix Usage

## Quick Start

Generate an optimized bundle for LLMs:

```bash
npx repomix --config repomix.config.json
```

## Output

- File: `repomix-output.md`
- Target: External LLMs (Claude, ChatGPT, etc.)
- Content: Core code + essential docs, no large assets

## Configuration

- Edit `repomix.config.json` to adjust includes/ignores.
- Current config excludes: archives, models, logs, large docs.
- Token count: ~384k tokens (Jan 2026).

## Tips

- Use `removeComments: true` to reduce size further.
- For backend-only review, exclude `static/**` and `templates/**`.
- Re-run after code changes to keep bundle current.
