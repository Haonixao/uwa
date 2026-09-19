# go-packages-analyze

## Overview
Skill for analyzing Go packages directly from the local module cache to debug incorrect package usage without copying files to workspace. When a Go file fails to compile due to wrong struct fields, undefined symbols, or incorrect function signatures, inspecting the local Go module cache (`$HOME/go/pkg/mod`) provides accurate type information faster than web-based documentation.

## Purpose
To resolve Go package usage errors by examining actual package source code from the local module cache. This is more reliable than web searches because Go is strictly typed and documentation often lacks precise details about function signatures, struct fields, and interface definitions. Direct cache inspection eliminates unnecessary file copying and workspace clutter.

## When to Use
- Go compilation errors related to package usage (undefined symbols, wrong struct fields)
- Uncertain about correct function signatures or constructor names
- Need to verify interface implementations
- Package documentation is unclear or outdated
- Must understand exact type definitions in dependencies

## Prerequisites
- Go project with dependencies already downloaded (module cache exists at `$HOME/go/pkg/mod`)
- Import path and approximate package version known or discoverable
- Access to terminal for running ls/find/grep commands in cache directory
- Access to subagent via kilo for direct file reading from cache

## Workflow / Core Steps
1. **Locate Package in Cache** - Run terminal commands to find package in module cache
2. **Query Package Structure** - Use subagent to read specific .go files directly from cache
3. **Inspect Source Code** - Parse output from subagent to understand structs, functions, interfaces
4. **Verify Signatures** - Confirm exact function signatures, constructor names, struct fields from source
5. **Apply Fixes** - Update your code based on accurate information from source
6. **No Cleanup Needed** - No temporary files created in workspace

## Usage Examples

### Example 1: Fix Undefined Struct Field
**Scenario**: Compilation error: "undefined field X in struct SearchCriteria"

**Steps**:
```
1. terminal: find $HOME/go/pkg/mod -type d -name "*go-imap*"
2. subagent: Read the types.go or criteria.go file from cache, output SearchCriteria struct definition
3. Identify correct field names from subagent output
4. Fix your code with correct field names
```

### Example 2: Find Correct Constructor Function
**Scenario**: Not sure how to create a Criteria object for go-imap package

**Steps**:
```
1. subagent: Search $HOME/go/pkg/mod/github.com/emersion/go-imap@v1.2.1 for all functions starting with 'New'
2. subagent: Read the file containing NewSearchCriteria, output the function signature and docstring
3. Use correct constructor in your code based on signature
```

### Example 3: Verify Interface Implementation
**Scenario**: Need to understand what methods interface requires

**Steps**:
```
1. subagent: Read the interface definition from cache, find all methods in the interface
2. subagent: Output complete interface signature with all method names and parameters
3. Implement all required methods in your code
```

## Best Practices
- **Prefer Direct Reading** - Always read directly from cache via subagent, no copying needed
- **Use Targeted Queries** - Ask subagent for specific functions/structs, not entire files
- **Read Source Over Docs** - Prefer examining actual source over documentation
- **Prefer Local Over Web** - Never use web_search/web_fetch for Go package internals; use local cache
- **Document the Fix** - When fixing usage errors, note what was wrong and why
- **Version Matters** - Different package versions may have different signatures; verify correct version path
- **No Workspace Clutter** - No temp files, no cleanup needed - everything stays in cache

## Integration with UWA Tools

**Primary workflow (native tools)**:
1. Terminal: Find package path: `ls $HOME/go/pkg/mod/<import-path>@<version>` or `find $HOME/go/pkg/mod -type d -name <package-name>`
2. Terminal: Search for patterns: `grep -n "pattern" $HOME/go/pkg/mod/<path>/*.go`
3. File tool: Read specific .go files directly from cache: `read $HOME/go/pkg/mod/<import-path>@<version>/filename.go`
4. Main agent: Analyze source code and make decisions
5. File tool: Patch your code with fixes

**Subagent workflow (when appropriate)**:
- Use subagent only if terminal/file tools are problematic or inefficient
- Example: Complex glob patterns or systematic search across many files
- Subagent can batch operations that would require multiple terminal commands

**Typical sequence**:
```
1. terminal → find/ls to locate package path
2. terminal → grep or direct path lookup
3. file → read .go file directly from cache at full path
4. main agent → analyze source code output
5. file → patch your code with fixes
No subagent needed in most cases.
```

**Key principle**: Use native tools first (terminal + file). Direct cache access is available - no need to involve subagent unless there's a specific technical reason (tool failure, complex operations, etc.).