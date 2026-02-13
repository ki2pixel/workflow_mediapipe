---
description: documentation skill migrated from Windsurf as contextual rules
globs: 
  - "**/*.{py,js,md}"
alwaysApply: true
---

# Documentation & README Writing Guidelines

## Technical Article Structure (Deep Dive Articles)

When writing technical articles that explain a concept or pattern, use this structure:

### 1. TL;DR First

Start with a 1-2 sentence summary that a busy reader can skim. Bold the key insight.

```markdown
**TL;DR**: If you need to know what an API can do without running it, don't wrap definitions in functions. Use static objects for metadata, functions for execution.
```

### 2. Problem-First Opening

Drop the reader into a scenario where they feel pain. Don't start with definitions.

```markdown
❌ "Introspection is the ability to examine an API's capabilities at runtime..."
✅ "Introspection lets you discover available methods and inspect object state without executing code..."
```

### 3. Code Examples with Context

Always provide working examples that demonstrate the concept in context.

```markdown
// Before: Manual inspection
const obj = { /* ... */ };
console.log(Object.keys(obj)); // ["method1", "method2"]

// After: With introspection
const methods = Object.getOwnPropertyNames(obj);
console.log(methods); // ["method1", "method2", "method3"]
```

## README Structure

### Standard Sections
```markdown
# Project Name

## Quick Start
3-5 commands to get running

## Architecture
System overview with diagram

## Features
Key capabilities with examples

## Installation
Prerequisites and setup steps

## Usage
How to use with examples

## Configuration
Environment variables and options

## Contributing
Guidelines for contributors

## License
SPDX identifier
```

## Writing Guidelines

### 1. **Active Voice**
- Use present tense for current functionality
- Use imperative mood for instructions
- Be direct and concise

### 2. **Code Examples**
- Use syntax highlighting with language tags
- Provide complete, runnable examples
- Include error handling

### 3. **Technical Accuracy**
- Verify all commands and paths
- Test examples before publishing
- Include version compatibility information

### 4. **Cross-References**
- Link to related documentation
- Use consistent reference format
- Include anchor links for sections

### 5. **Visual Elements**
- Use diagrams for architecture
- Include screenshots for UI components
- Add badges for status/version

## Documentation Types

### API Documentation
```markdown
## Function Reference

### `functionName(param1, param2)`
**Description**: What the function does
**Parameters**: 
- `param1` (type): Description
- `param2` (type): Description

**Returns**: 
- `success` (object): Description on success
- `error` (Error): Description on failure

**Example**:
```javascript
const result = await functionName('value1', 'value2');
console.log(result);
```
```

### User Guides
```markdown
## How to [Task]

### Prerequisites
- Requirement 1
- Requirement 2

### Step-by-Step Instructions

1. **Step 1**: Description with code
2. **Step 2**: Description with code
3. **Step 3**: Description with code

### Common Issues

| Issue | Solution |
|---|---|
| Problem 1 | Solution 1 |
| Problem 2 | Solution 2 |

### Troubleshooting

#### Error Messages
- `Error: message` - Cause and solution
- `Warning: message` - When it occurs and what to do

## Quality Checklist

### Before Publishing
- [ ] All examples tested
- [ ] Links verified
- [ ] Spelling and grammar checked
- [ ] Code formatting consistent
- [ ] Technical accuracy verified

### Content Review
- [ ] Information is accurate and current
- [ ] Examples are complete and working
- [ ] Structure follows guidelines
- [ ] Cross-references are functional

## Punctuation Rules

### Commas
- Use Oxford comma for lists of three or more items
- No comma before "and" in simple lists
- Serial comma: "item1, item2, and item3"

### Semicolons
- Use semicolons to separate independent clauses
- Use semicolons in complex lists with internal commas

### Colons
- Use colons for introductions and explanations
- Use colons in ratios and proportions

### Hyphens
- Use hyphens for compound adjectives
- Use em dash (—) for emphasis in sentences
- Use hyphens in URL paths and file names

## Anti-Patterns

### What to Avoid
- Vague introductions ("In today's modern web development...")
- Overly complex sentences without clear purpose
- Passive voice when active is clearer
- Unnecessary jargon and buzzwords
- Inconsistent formatting

### Best Practices
- Start with the most important information
- Use simple, direct language
- Provide concrete examples
- Include troubleshooting sections
- Maintain consistent terminology

## Documentation Templates

### README Template
```markdown
# [Project Name]

[One-line description of the project]

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Contributing](#contributing)

## Installation

### Prerequisites
- Node.js 18+
- Python 3.10+
- [Other requirement]

### Quick Start
```bash
git clone https://github.com/user/repo.git
cd repo
npm install
npm start
```

## Usage

### Basic Example
```javascript
const library = require('project-name');

// Example usage
const result = library.method({
  parameter: 'value'
});
```

### Advanced Example
```javascript
const library = require('project-name');

// Advanced usage with options
const result = library.method({
  parameter: 'value',
  option1: true,
  option2: 'custom'
});
```

Utilisez ce prompt en tapant `/documentation` dans Continue.
