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
- **Features:** Supports command chaining via `&&`. Execution timeout is 60 seconds.

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
- **patch (line mode)**: Requires `start`, `end`, and `new_text`. Replaces the specified line range.
- **patch (search mode)**: Requires `old_text` and `new_text`.
  - `replace_all` (bool): If `true`, replaces all occurrences of `old_text`. Defaults to `false`.

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
1. **Double Patch Protection:** After using `patch` in line mode (`start`/`end`), you **must** perform a `read` or `symbols` on the same file before patching it by lines again. This prevents applying changes to shifted line numbers.
1. **ID Uniqueness:** Every new message must have a unique `uwa_msg_id`. The script ignores messages with an already processed ID.
1. **One Block Per Message:** If two unprocessed JSON blocks with different IDs are found on the page, the script will return an error, requiring them to be sent one at a time.
1. **Text Cleaning:** The environment automatically removes invisible Unicode characters (Zero Width Space, etc.) before parsing your JSON.

## Strategy: Line-Mode Priority

**Default Requirement:** You MUST prioritize `patch` in **line mode** (`start`, `end`, `new_text`) as your default editing strategy.

**Why?**

- **Token Conservation:** Line mode avoids duplicating source code in `old_text`, saving significant context space and reducing latency.
- **Deterministic Accuracy:** It bypasses common `old_text` matching failures caused by invisible characters or duplicate code blocks.
- **Safety:** The **Double Patch Protection** rule (mandatory `read` after each edit) ensures line numbers remain perfectly synchronized.

**Justification Policy:** You are allowed to use search mode (`old_text`) only if you can internally justify why it is more appropriate for a specific case (e.g., a global `replace_all` or a trivial one-word fix). Using search mode for multi-line blocks without a clear rationale is considered inefficient tool usage.

## Pro-Tips

- **Markdown Navigation**: Use `symbols` on `.md` files to get a structured list of headings. It's the fastest way to map out documentation.
- **Efficient Patching**: You can include a `read` tool *after* a `patch` tool for the same file in a single message. This immediately satisfies the **Double Patch Protection** rule, allowing you to perform another line-mode patch in your very next message without an extra round-trip.
