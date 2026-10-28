# UWA (Universal Web Agent)

**Local Autonomous Agent for Web AI Chats**

A local automation tool that turns your Web AI chat into agent with direct access to your computer's terminal and file system.
It connects to Chrome via the Chrome DevTools Protocol, monitors the chat, parses model tool calls, executes them on your system, and automatically pastes the results back into the chat input field.

It effectively gives the AI persistent, real-world execution capabilities.

## Features

- **Terminal Execution** — Run any commands with full output capture
- **File Operations** — Safe read/patch
- **Autonomous & Safe** — Continuous monitoring with Double Patch Protection
- **Auto-injection** — Automatically pastes results back into the captured chat input field
- **Chrome Integration** — Automatically finds the active tab via DevTools Protocol
- **In-Browser Runtime Control** — An automatically injected, draggable floating UI panel to Pause, Resume, or Stop the agent's execution loop, with theme support (Auto/Dark/Light).
- **Field Capture** — One-click calibration of the chat input field via the UI panel button.
- **Result Modal** — If auto-injection fails, a draggable modal window appears with the result for manual copying.

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

| File                | Purpose                                                 |
| ------------------- | ------------------------------------------------------- |
| `agent_executor.py` | Main autonomous loop (core)                             |
| `filetool.py`       | Safe file read/patch operations                         |
| `uwa`               | Executor                                                |
| `agent.md`          | Communication protocol specification (Send it to model) |
| `README.md`         | This documentation                                      |

## Quick Start

1. **Launch Chrome with debugging enabled (`--remote-debugging-port=9222`)**

2. **Install dependencies:**

```bash
pip install websockets
```

3. **Run the agent:**

```bash
./uwa
```

4. **Start the session:**
   Copy the content of `agent.md` and paste it into your Web AI chat. This initializes the communication protocol.

5. **Calibrate the input field:**
   Click into the chat's input field to focus it, then click the **"📍 Capture field"** button on the UWA Control panel. The button will show **"✅ Field captured"** for 10 seconds. The agent now knows where to paste results.

6. **Execution Loop:**
   When you want the agent to execute something, send your message to the AI. The agent will execute the requested tools and automatically paste the results into the captured field. No tags needed — just focus the field once and click the capture button.

> **Note**: If the chat interface re-renders its input field, the saved path may become stale. In that case, simply click into the field again and press **"📍 Capture field"** once more to re-calibrate.

7. **Fallback Modal:**
   If the agent cannot insert the result automatically (e.g., field not captured or path became invalid), a draggable modal window will appear in the center of the screen with the full result text. You can copy it manually and close the window.

## Safety Notes

- The agent only executes commands you explicitly request through tool calls
- Use with trusted AI models only

---

**Disclaimer**: This project is in the early MVP stage. You are fully responsible for the commands you allow the agent to execute and any consequences that may result.
