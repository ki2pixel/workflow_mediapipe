# Skills Integration Rules

This rule defines how skills are automatically routed based on user requests and priority hierarchy.

## Automatic Skill Detection

Skills are specialized knowledge modules that activate based on pattern matching in user requests. The system automatically detects relevant skills and loads their instructions when triggered.

## Routing Matrix

| Skill Name | Trigger Patterns | Priority |
|------------|------------------|----------|
| after-effects-cep-panel | CEP panel, Adobe extension, JSX scripting | High |
| after-effects-scripts | ExtendScript, After Effects automation, JSX | High |
| csv-monitoring-sme | CSV monitoring, webhook ingestion, download_history | Medium |
| debugging-strategies | debug, crash, error analysis, troubleshooting | High |
| documentation | README, docs, documentation writing, technical writing | Medium |
| fast-filesystem-ops | file operations, batch processing, filesystem | Low |
| frontend-timeline-designer | Timeline UI, frontend design, connected timeline | Medium |
| json-mcp-expert | JSON processing, MCP server, data transformation | Low |
| logs-overlay-conductor | logs overlay, UI overlay, focus management | Medium |
| pipeline-diagnostics | pipeline validation, environment check, diagnostics | High |
| shrimp-task-manager | task management, planning, project breakdown | Low |
| step4-audio-orchestrator | audio processing, STEP4, audio analysis | Medium |
| step5-gpu-ops | tracking, STEP5, GPU operations, MediaPipe | Medium |
| tests-suite-guardian | testing, test suites, unit tests, integration | Medium |
| workflow-docs-updater-plus | workflow documentation, docs update, technical docs | Medium |
| workflow-operator | pipeline execution, STEP operations, workflow management | High |

## Priority Hierarchy

1. **workflow-operator** > All other skills
2. High priority skills (pipeline-diagnostics, debugging-strategies, etc.)
3. Medium priority skills
4. Low priority skills

## Skill Loading Rules

- **Single Skill Focus**: Only one skill loads at a time to avoid context conflicts
- **Pattern Matching**: Skills activate when request matches 70%+ of trigger patterns
- **Fallback to Local**: If no skill matches, use project-specific knowledge
- **Context Preservation**: Skills maintain project context and coding standards

## Integration Guidelines

- Skills supplement but don't override project rules
- Always combine skill knowledge with project-specific requirements
- Use skills for specialized tasks, general coding follows standard rules
- Skills can be invoked manually with `/skill-name` syntax

## Conflict Resolution

When multiple skills could apply:
1. Choose highest priority skill
2. If tie, choose most specific pattern match
3. If still tied, user chooses or combine approaches

## Skill Categories

- **Development**: coding standards, debugging, testing
- **Media Processing**: STEP4/5 operations, audio/video processing
- **Documentation**: technical writing, workflow docs
- **UI/UX**: frontend design, timeline management
- **System Integration**: MCP servers, external tools

## Best Practices

- Use skills for complex specialized tasks
- Verify skill recommendations against project constraints
- Combine multiple skills when task requires diverse expertise
- Document skill usage in commit messages when applicable