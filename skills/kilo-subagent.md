# kilo-subagent

## Overview
Subagent skill for delegating technical subtasks to auxiliary language models via the `kilo run --auto` command. Use when existing UWA Tools encounter limitations, when file operations are complex/error-prone, or when specialized code search/analysis is needed. Subagent handles pure technical work with minimal reasoning required.

## Purpose
To provide a controlled interface for leveraging lightweight, cost-efficient models for specific technical operations that are difficult or inefficient to accomplish with standard UWA Tools. Subagent excels at pattern matching, code search, file editing, and information gathering—never at analysis or decision-making.

## When to Use
- **Code search**: Finding function definitions, class implementations, interface usage across large projects
- **Complex file editing**: When patch operations are error-prone or deeply nested; when write operations are tedious
- **Information gathering**: Scanning project structure, extracting specific patterns, collecting metadata
- **Boilerplate generation**: Creating file templates, standardized code patterns, configuration files
- **Error recovery**: When file tool errors occur repeatedly and manual workaround is more efficient

## When NOT to Use
- Architecture decisions or design reviews
- Code quality analysis or technical recommendations
- Evaluating approaches or comparing solutions
- Understanding business logic or intent
- Any task requiring judgment, reasoning, or interpretation
- Tasks better handled by terminal or file tools (prefer those first)

## Prerequisites
- Clear, specific, technical task description (no ambiguity)
- Understanding of what you're searching for or what needs modification
- Knowledge of file paths or patterns to search within
- Availability of `kilo run --auto` command in execution environment

## Workflow / Core Steps
1. **Identify the Technical Bottleneck** - Recognize where existing tools fail/struggle
2. **Define the Specific Subtask** - Break down into concrete, unambiguous operation
3. **Write Technical Instructions** - Describe exactly WHAT to find/edit, WHERE, and HOW the output should be formatted
4. **Execute via Terminal** - Use `kilo run --auto "Your instructions"` in a terminal tool
5. **Collect Results** - Review output from the subagent execution
6. **Analyze & Decide** - You (main agent + user) interpret results and make decisions

## Usage Examples

### Example 1: Find Function Definition
**Scenario**: Need to locate a specific Go function signature across the project

**Instructions to subagent**:
```
Search the project for the function definition of 'UserRepository.FindByID'. 
Return the exact function signature, file path, and line number. 
Include 10 lines of context after the function declaration.
```

**Why subagent**: Faster pattern search than multiple file reads; exact coordinates needed.

### Example 2: Complex File Restructuring
**Scenario**: Need to reorganize imports and reorder methods in a large struct

**Instructions to subagent**:
```
In file src/models/user.go, reorganize the struct UserModel:
1. Move all private methods below public methods
2. Group related methods together
3. Sort public methods alphabetically
4. Keep the struct field order unchanged
Return the complete modified file content.
```

**Why subagent**: Complex nested edits; file tool patch operations would be tedious/error-prone.

### Example 3: Gather Codebase Metrics
**Scenario**: List all files implementing a specific interface

**Instructions to subagent**:
```
Find all Go files that implement the 'Repository' interface.
For each file, return: file path, struct name, function signatures.
Format as structured list with clear separators.
```

**Why subagent**: Systematic search across multiple files; main agent will analyze results.

## Best Practices
- **Be Brutally Specific** - Subagent should not guess; give exact coordinates, patterns, or formats
- **Reduce Reasoning Burden** - The more specific you are, the better the output. Avoid "find anything related to X"
- **Keep Tasks Single-Purpose** - Don't mix search + edit + analysis in one call; split into steps
- **Preserve Context Locally** - You keep the results; you make decisions based on results
- **Validate Output Format** - Specify exactly how results should be returned (JSON, markdown, raw code, etc.)
- **Use for Tedious Work** - Subagent shines at repetitive pattern matching, not creative problem-solving
- **Prefer Native Tools First** - Before calling subagent, verify existing tools won't work reasonably well

## Integration with UWA Tools

Subagent is invoked via `terminal` tool using the `kilo` command:

```json
{
  "type": "terminal",
  "command": "kilo run --auto \"Your specific technical instructions here\""
}
```

**Workflow**:
1. Prepare clear, technical instructions
2. Execute terminal tool with `kilo run --auto` command
3. Subagent processes and returns results
4. You read results, analyze, make decisions
5. Use other UWA Tools (file, terminal) to execute your decisions

**Example UWA sequence**:
```
1. terminal → kilo run --auto (search/gather)
2. read results from output
3. file tool → patch (make the edits you decided on)
4. terminal → validate changes
```

**Important**: Subagent output is raw data. You interpret it and determine next actions.