---
paths:
  - "**/*.md"
---

# Git Pull Request Description Format Rules

This rule is a guideline for PR descriptions that applies to all pull requests.

## Position of This Rule

- This rule is a PR description convention based on Conventional Commits.
- While adhering to basic formats like `Prefix` from Conventional Commits, it adds guidelines specific to this repository such as structured body sections.
- When reusing in other projects, adjust the sections according to each project's policy.

## Language Specification

- In this rule file, `language` is used as a logical name representing the language used in PR descriptions.
- `language = "en"`
- All sections should be written in the language specified by `language` as a rule.

## Basic Format (Required)

```
<Prefix>: <Summary (imperative/concise)>

## Overview
Brief description of the changes and their purpose.

## Changes
- Change 1 (bullet point)
- Change 2 (bullet point)
- ...

## Testing
Description of testing performed and results.

Closes: #<Issue number> (optional)
```

## Prefix (Leading Prefix)

Prefix corresponds to `type` in Conventional Commits and uses lowercase English words.

- feat: Add new feature
- fix: Bug fix
- refactor: Refactoring (no behavior change)
- perf: Performance improvement
- test: Add/modify tests
- docs: Documentation update
- build: Build/dependency changes
- ci: CI-related changes
- chore: Miscellaneous tasks (tool settings/scripts, etc.)
- style: Style-only changes (unrelated to code logic)
- revert: Revert

As with Conventional Commits, the format `<Prefix>(scope):` is also allowed as needed (e.g., `fix(translation): ...`).
- For detailed specifications, also refer to the official [Conventional Commits](https://www.conventionalcommits.org/) documentation.

## Summary (First Line)

- Write concisely in the language specified by `language`. No period at the end.
- Briefly express what and why (if necessary).
- Aim for approximately 50 characters or less.

## Overview Section

- Provide a brief description of the changes and their purpose.
- Explain the problem being solved or the feature being added.
- Write in paragraph form, 2-3 sentences maximum.

## Changes Section (Bullet Points)

- List the specific changes made as bullet points starting with "- ".
- Be specific about what files were changed and what was modified.
- Include any breaking changes or migration notes if applicable.
- Write in the same language as the summary.

## Testing Section

- Describe what testing was performed.
- Include unit tests, integration tests, manual testing, etc.
- Mention test results and any edge cases covered.
- If no tests were added, explain why.

## Footer (Optional)

- Closes: Specify related Issues with `Closes: #123`.
- BREAKING CHANGE: If there are backward-incompatible changes, clearly state the content.

## Examples

```
fix: Resolve user authentication timeout issue

## Overview
Fixes the issue where users were being logged out prematurely due to session timeout being set too low.

## Changes
- Increased session timeout from 30 minutes to 2 hours in config/settings.py
- Updated logout warning to appear 15 minutes before timeout
- Added session refresh on user activity

## Testing
- Ran unit tests for session management (all pass)
- Manual testing with different timeout scenarios
- Verified backward compatibility with existing sessions

Closes: #456
```

```
feat: Add user profile customization

## Overview
Allows users to customize their profile with avatar, bio, and theme preferences.

## Changes
- Added Profile model with avatar, bio, theme fields
- Created profile edit form and validation
- Updated user dashboard to display profile info
- Added API endpoints for profile CRUD operations

## Testing
- Added comprehensive unit tests for Profile model
- Integration tests for profile API endpoints
- Manual testing of profile editing flow
- Verified data persistence and validation
```

## Prohibited

- Writing summary only in a language different from that specified by `language`
- Vague or incomplete descriptions that don't explain the purpose
- Changes section with only high-level descriptions without specifics
- Missing testing section or inadequate testing description
- Using the PR description as a commit message (they serve different purposes)