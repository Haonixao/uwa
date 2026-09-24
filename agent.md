# UWA Tools Documentation

This document describes the interface for agent interaction with the execution environment. The interaction occurs via a browser (monitoring page text) and the file system (writing results to `out.json`).

## Request Format

The agent must send a message containing a JSON block. Only **one** JSON block is allowed per message.

### JSON Structure

```json
{
  "uwa_msg_id": "unique_msgid_string",
  "tools": [
    {
      "type": "terminal",
      "command": "command to execute"
    },
    {
      "type": "file",
      "path": "path/to/file",
      "action": "symbols|read|patch",
      "start": 1,
      "end": 100,
      "old_text": "text to find",
      "new_text": "replacement text",
      "replace_all": false
    }
  ]
}
```

## Tools

### 1. TERMINAL Tool

**Purpose:** Execute system commands.

- **type**: `terminal`
- **command**: The command string. Executed cross-platform via the system shell (`/bin/sh` or `cmd.exe`).
- **Features:** Supports command chaining via `&&`. Execution timeout is 180 seconds.

### 2. FILE Tool

**Purpose:** Read and modify files.

- **type**: `file`
- **path**: Absolute path to the file.
- **action**:
  - `symbols` (default): Extracts file structure (functions, classes, headers). Recommended for initial file exploration.
  - `read`: Reads file content.
  - `patch`: Modifies the file.

#### FILE Tool Parameters:

- **read**: Requires `start` and `end` (line numbers, starting from 1).
- **patch (search mode)**: Requires `old_text` and `new_text`.
  - `replace_all` (bool): If `true`, replaces all occurrences of `old_text`. Defaults to `false`.
- **patch (line mode)**: Requires `start`, `end`, and `new_text`. Replaces the specified line range. This mode is very useful when the text to be replaced is very complex and errors occur in **patch (search mode)**.

## Output Format (out.json)

Execution results are written to `out.json`. You must manually copy the contents of this file and paste it into the browser chat to continue.

### Success Response

```json
{
  "uwa_msg_id": "id_from_request",
  "tools": [
    {
      "type": "terminal",
      "command": "...",
      "result": "...terminal output..."
    },
    {
      "type": "file",
      "path": "...",
      "result": "...content or ok status..."
    }
  ]
}
```

### Important: Result Truncation

To keep the context clean, the executor truncates `new_text` and `old_text` fields in the **response** JSON to 50 characters if they are longer. This is a display-only truncation in `out.json`; the actual file operations are performed with the full text you provided.

### General Error

If the JSON is invalid or rules are violated (e.g., multiple blocks), the response will be:

```json
{
  "uwa_msg_id": "id_from_request",
  "error": "Error message text"
}
```

## Rules and Constraints

1. **Execution Order:** Tools in the `tools` array are executed strictly sequentially (top to bottom).
1. **ID Uniqueness:** Every new message must have a unique `uwa_msg_id`. The script ignores messages with an already processed ID.
1. **One Block Per Message:** If two unprocessed JSON blocks with different IDs are found on the page, the script will return an error, requiring them to be sent one at a time.
1. **Text Cleaning:** The environment automatically removes invisible Unicode characters (Zero Width Space, etc.) before parsing your JSON.
1. **Context Compression Protocol Recovery:** After each context session compression, the agent **must** explicitly note in the compression summary that `agent.md` needs to be re-read and the UWA Tools communication protocol must be restored in the context before continuing with further work.
1. **Skills System Integration:** The agent **must** always consult `skills.json` at the start of each session to discover available skills and their triggers. During user interactions, continuously analyze user requests against skill triggers to automatically recognize and apply relevant skills. Skills extend agent capabilities and should be leveraged opportunistically throughout the workflow.
1. **User Overview Awareness:** Before beginning core session tasks, the agent **must** explicitly check for and read its own `user-overview/[model-name].md` diary (if it exists) to incorporate prior observations about the user’s preferences, competencies, and communication style. If the diary does not exist, the agent should note this and plan to create it at session end. This step ensures consistent, personalized, and protocol-aware behavior aligned with the user’s expectations.

## Context Recovery Request

This is the exact request to restore context after compression.

```json
{
  "uwa_msg_id": "restore_context_protocol_001",
  "tools": [
    {
      "type": "file",
      "path": "agent.md",
      "action": "read",
      "start": 1,
      "end": 1000
    },
    {
      "type": "file",
      "path": "skills.json",
      "action": "read",
      "start": 1,
      "end": 1000
    }
  ]
}
```
