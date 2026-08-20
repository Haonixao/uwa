# UWA (Universal Web Agent)

**Local Autonomous Agent for Web AI Chats**

A local automation tool that turns your Web AI chat into agent with direct access to your computer's terminal and file system.
It connects to Chrome via the Chrome DevTools Protocol, monitors the chat, parses model tool calls, executes them on your system, and automatically pastes the results into `out.json`.

It effectively gives the AI persistent, real-world execution capabilities.

## Features

- **Terminal Execution** — Run any commands with full output capture
- **File Operations** — Safe read/patch/symbols (with ctags and Markdown support)
- **Autonomous & Safe** — Continuous monitoring with Double Patch Protection
- **Chrome Integration** — Automatically finds the active tab via DevTools Protocol

## Web AI chats tested

- **grok.com**
- **work.trae.ai**
- **perplexity.ai**
- **app.kilo.ai**
- **duck.ai**
- **gemini.google.com**
- **chat.deepseek.com**
- **chat.qwen.ai**
- **claude.ai**
- **chatgpt.com**
- **alice.yandex.ru**
- **Most likely, it can work on many others without modifications**

## Files

| File | Purpose |
| ------------------- | ------------------------------------------------------- |
| `agent_executor.py` | Main autonomous loop (core) |
| `filetool.py` | Safe file read/patch operations |
| `agent.md` | Communication protocol specification (Send it to model) |
| `README.md` | This documentation |

## Quick Start

1. **Launch Chrome with debugging enabled (`--remote-debugging-port=9222`)**

2. **Install dependencies:**

```bash
pip install websockets
```

For Windows:

```bash
choco install universal-ctags -y
```

For Linux:

```bash
sudo snap install universal-ctags --classic
```

3. **Run the agent:**

```bash
python agent_executor.py
```

The agent is now ready. Results in `out.json` are automatically cleaned (large `new_text`/`old_text` blocks are truncated to 50 chars) to keep the chat history concise.

## Safety Notes

- The agent only executes commands you explicitly request through tool calls
- Use with trusted AI models only

______________________________________________________________________

**Disclaimer**: This project is in the early MVP stage. You are fully responsible for the commands you allow the agent to execute and any consequences that may result.
