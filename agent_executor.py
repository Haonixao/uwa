import asyncio
import http.client
import json
import os
import re
import subprocess
import sys

import websockets

# Настройка окружения для корректной работы UTF-8
os.environ["PYTHONIOENCODING"] = "utf-8"


def get_dynamic_page_id():
    """Автоматически находит ID первой подходящей страницы через HTTP API Chrome"""
    try:
        conn = http.client.HTTPConnection("localhost", 9222)
        conn.request("GET", "/json")
        response = conn.getresponse()
        if response.status == 200:
            data = json.loads(response.read())
            for item in data:
                if item.get("type") == "page" and "url" in item:
                    print(f"[*] Found page: {item.get('title')} (ID: {item.get('id')})")
                    return item.get("id")
        return None
    except Exception as e:
        print(f"Error fetching page ID: {e}")
        return None


async def get_page_text(websocket):
    """Возвращает весь текст страницы"""
    async with ws_lock:
        await websocket.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": "document.body.innerText",
                        "returnByValue": True,
                    },
                }
            )
        )
        response = await websocket.recv()
    return json.loads(response).get("result", {}).get("result", {}).get("value", "")


async def set_page_input(websocket, text, attempts=10, delay=1):
    """
    Вставляет текст в поле ввода, путь к которому сохранён в dataset.inputPath панели.
    Если путь не захвачен, возвращает False.
    """
    safe_text = json.dumps(text)

    js_insert = f"""
    (function() {{
        const panel = document.getElementById('uwa-control-panel');
        if (!panel || !panel.dataset.inputPath) {{
            return JSON.stringify({{ ok: false, reason: 'no_path' }});
        }}

        let el = null;
        try {{
            el = document.querySelector(panel.dataset.inputPath);
        }} catch (e) {{
            return JSON.stringify({{ ok: false, reason: 'invalid_path' }});
        }}

        if (!el) {{
            return JSON.stringify({{ ok: false, reason: 'element_not_found' }});
        }}

        if (el.hasAttribute('readonly') || el.getAttribute('aria-readonly') === 'true') {{
            return JSON.stringify({{ ok: false, reason: 'readonly' }});
        }}

        let isTextarea = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT';

        el.focus();

        if (isTextarea) {{
            el.setSelectionRange(el.value.length, el.value.length);
        }} else {{
            const selection = window.getSelection();
            if (selection) {{
                const range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);
                selection.removeAllRanges();
                selection.addRange(range);
            }}
        }}

        const success = document.execCommand('insertText', false, {safe_text});
        if (!success) {{
            if (isTextarea) {{
                el.value = {safe_text};
            }} else {{
                el.innerText = {safe_text};
            }}
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        return JSON.stringify({{ ok: true }});
    }})()
    """

    async def eval_js(expr, call_id):
        async with ws_lock:
            await websocket.send(
                json.dumps(
                    {
                        "id": call_id,
                        "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True},
                    }
                )
            )
            response = await websocket.recv()
        raw = json.loads(response).get("result", {}).get("result", {}).get("value", "")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {}

    print("  [*] Attempting to insert text into captured field...")

    for i in range(attempts):
        data = await eval_js(js_insert, 100 + i)
        if data.get("ok"):
            print(f"  [+] Text inserted on attempt {i + 1}.")
            return True

        reason = data.get("reason", "unknown")
        if reason == "no_path":
            print("  [!] Field not captured. Click '📍 Capture field' on the panel.")
            await show_result_modal(websocket, text)
            return False
        else:
            print(f"  [!] Attempt {i + 1}: Failed ({reason}).")

        if i < attempts - 1:
            await asyncio.sleep(delay)

    print("  [!] Could not insert text after all attempts. Showing result modal.")
    await show_result_modal(websocket, text)
    return False


async def show_result_modal(websocket, text):
    """
    Показывает модальное окно с результатом, если не удалось вставить текст в поле ввода.
    Окно можно закрыть и перетаскивать. Тема автоматически подстраивается под панель управления.
    """
    safe_text = json.dumps(text)

    js_modal = f"""
    (function() {{
        // Удаляем предыдущее модальное окно, если оно есть
        const existing = document.getElementById('uwa-result-modal');
        if (existing) existing.remove();

        // Определяем тему из панели управления
        const panel = document.getElementById('uwa-control-panel');
        let theme = panel ? (panel.dataset.theme || 'auto') : 'auto';
        let isDark;
        if (theme === 'auto') {{
            isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        }} else {{
            isDark = theme === 'dark';
        }}

        // Цвета в зависимости от темы
        const bgColor = isDark ? '#1e1e1e' : '#eff1f5';
        const textColor = isDark ? '#eff1f5' : '#4c4f69';
        const headerBg = isDark ? '#1e1e1e' : '#eff1f5';
        const textareaBg = isDark ? '#1e1e1e' : '#eff1f5';
        const textareaColor = isDark ? '#eff1f5' : '#4c4f69';
        const borderColor = isDark ? '#7287fd' : '#7287fd';

        // Создаём модальное окно
        const modal = document.createElement('div');
        modal.id = 'uwa-result-modal';
        modal.style.cssText = `position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 2147483647; background: ${{bgColor}}; color: ${{textColor}}; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); font-family: system-ui, sans-serif; min-width: 500px; max-width: 80vw; max-height: 80vh; display: flex; flex-direction: column; border: 2px solid ${{borderColor}};`;

        // Заголовок
        const header = document.createElement('div');
        header.style.cssText = `display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: ${{headerBg}}; border-radius: 12px 12px 0 0; cursor: move; user-select: none; border-bottom: 2px solid ${{borderColor}};`;

        const title = document.createElement('span');
        title.style.cssText = 'font-weight: 600; font-size: 14px;';
        title.textContent = '⚠️ Result (could not insert automatically)';
        header.appendChild(title);

        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `background: transparent; color: ${{textColor}}; border: none; font-family: system-ui, sans-serif; font-size: 14px; cursor: pointer; padding: 0 4px; line-height: 1;`;
        closeBtn.addEventListener('click', () => modal.remove());
        header.appendChild(closeBtn);

        modal.appendChild(header);

        // Текстовое поле с результатом
        const textarea = document.createElement('textarea');
        textarea.value = {safe_text};
        textarea.readOnly = true;
        textarea.style.cssText = `flex: 1; min-height: 300px; padding: 12px; background: ${{textareaBg}}; color: ${{textareaColor}}; border: none; font-family: system-ui, sans-serif; font-size: 14px; resize: none; outline: none;`;
        modal.appendChild(textarea);

        document.body.appendChild(modal);

        // Drag-логика
        let isDragging = false;
        let offsetX = 0, offsetY = 0;

        header.addEventListener('mousedown', (e) => {{
            if (e.target === closeBtn) return;
            isDragging = true;
            const rect = modal.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            modal.style.transform = 'none';
            e.preventDefault();
        }});

        document.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            modal.style.left = (e.clientX - offsetX) + 'px';
            modal.style.top = (e.clientY - offsetY) + 'px';
        }});

        document.addEventListener('mouseup', () => {{
            isDragging = false;
        }});

        // Фокусируемся на textarea для удобного копирования
        textarea.focus();
        textarea.select();

        return JSON.stringify({{ ok: true }});
    }})()
    """

    async with ws_lock:
        await websocket.send(
            json.dumps(
                {
                    "id": 9999,
                    "method": "Runtime.evaluate",
                    "params": {"expression": js_modal, "returnByValue": True},
                }
            )
        )
        await websocket.recv()


def execute_command(cmd):
    """Выполняет команду в терминале кроссплатформенно"""
    print(f"  > Executing Terminal: {cmd}")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=script_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        output = result.stdout if result.stdout else ""
        if result.stderr:
            output += "\nError:\n" + result.stderr
        return output.strip()
    except Exception as e:
        return f"Execution Error: {e!s}"


patched_files = {}  # path -> True (для защиты от двойного патча)

# Глобальное состояние управления выполнением (running, paused, stopped)
uwa_control_state = "running"

# Lock для защиты WebSocket от конкурентных вызовов send/recv
ws_lock = asyncio.Lock()


def execute_file_tool(tool_data):
    """Выполняет файловые операции через filetool.py на основе JSON данных"""
    print(
        f"  > Executing File Tool: {tool_data.get('path')} ({tool_data.get('action')})"
    )

    try:
        # Подготовка данных для filetool.py
        data = {
            "path": tool_data.get("path"),
            "action": tool_data.get("action"),
            "start": tool_data.get("start"),
            "end": tool_data.get("end"),
            "old_text": tool_data.get("old_text"),
            "new_text": tool_data.get("new_text"),
            "replace_all": tool_data.get("replace_all"),
        }

        # Очистка None значений
        data = {k: v for k, v in data.items() if v is not None}

        action = data.get("action")
        path = data.get("path")

        # Проверки перед вызовом
        if action == "patch" and data.get("new_text") is None:
            return "Error: action == patch, but new_text is missing."

        # === Защита от двойного патча (только для start-end режима) ===
        if action == "patch" and data.get("old_text") is None:
            if path in patched_files:
                return f"Error: Double patch with strings range detected for {path} without read in between. This can lead to incorrect changes. Do read and then patch with strings range again. Or use patch with old_text + new_text (no double patch problem in this case)"
            patched_files[path] = True
        elif action in ["read"]:
            patched_files.pop(path, None)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        filetool_path = os.path.join(script_dir, "filetool.py")

        process = subprocess.Popen(
            [sys.executable, filetool_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        stdout, stderr = process.communicate(input=json.dumps(data))
        output = stdout.strip()
        if stderr:
            output += "\nError:\n" + stderr

        print(f"    [+] File Tool Output: {output[:50]}...")
        return output

    except Exception as e:
        return f"File Tool Error: {e!s}"


def execute_around_tool(tool_data):
    """Выполняет around-поиск через around.py: контекст вокруг needle"""
    p = tool_data.get("path")
    n = tool_data.get("needle")
    print(f"  > Executing Around Tool: {p} (needle: {n})")
    try:
        data = {
            "path": p,
            "needle": n,
            "before": tool_data.get("before"),
            "after": tool_data.get("after"),
            "max_matches": tool_data.get("max_matches"),
            "include": tool_data.get("include"),
            "exclude": tool_data.get("exclude"),
        }
        data = {k: v for k, v in data.items() if v is not None}

        if not data.get("path"):
            return "Error: path is required for around tool."
        if not data.get("needle"):
            return "Error: needle is required for around tool."

        script_dir = os.path.dirname(os.path.abspath(__file__))
        around_path = os.path.join(script_dir, "around.py")

        process = subprocess.Popen(
            [sys.executable, around_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        stdout, stderr = process.communicate(input=json.dumps(data))
        output = stdout.strip()
        if stderr:
            output += "\nError:\n" + stderr
        return output
    except Exception as e:
        return f"Around Tool Error: {e!s}"


def extract_json_blocks(text):
    """Находит все валидные JSON-блоки, содержащие uwa_msg_id, с учетом вложенности"""
    blocks = []
    for match in re.finditer(r"\{", text):
        start_idx = match.start()

        msg_match = re.search(r'"uwa_msg_id"\s*:', text[start_idx:])
        if not msg_match:
            continue

        brace_count = 0
        in_string = False
        escaped = False
        end_idx = -1

        for i in range(start_idx, len(text)):
            ch = text[i]

            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        if end_idx != -1:
            candidate = text[start_idx:end_idx]

            # 1. Заменяем неразрывные пробелы (NBSP) на обычные пробелы
            clean_candidate = candidate.replace("\xa0", " ")

            # 2. Удаляем остальные невидимые Unicode-символы форматирования
            clean_candidate = re.sub(
                r"[\u200b-\u200f\u2028-\u202e\ufeff]", "", clean_candidate
            )

            try:
                data = json.loads(clean_candidate)
                if "uwa_msg_id" in data:
                    blocks.append(clean_candidate)
            except json.JSONDecodeError:
                # Ошибки парсинга JS-кода страницы или мусорных блоков теперь можно не логировать,
                # чтобы не засорять консоль, либо оставить для отладки:
                # print(f"  [DEBUG] JSON Decode Error: {e}")
                continue

    return blocks


async def monitor_ui_state(websocket):
    """Периодически проверяет и обеспечивает наличие UI-панели управления, обновляя глобальное состояние."""
    global uwa_control_state
    js_ui_check = """
    (function() {
        let panel = document.getElementById('uwa-control-panel');

        const applyTheme = (p) => {
            let theme = p.dataset.theme || 'auto';
            let isDark;
            if (theme === 'auto') {
                isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            } else {
                isDark = theme === 'dark';
            }
            p.style.background = isDark ? '#1e1e1e' : '#eff1f5';
            p.style.color = isDark ? '#eff1f5' : '#4c4f69';
            p.style.border = isDark ? '2px solid #7287fd' : '2px solid #7287fd';
            const header = p.querySelector('.uwa-header');
            if (header) header.style.borderBottom = isDark ? '2px solid #7287fd' : '2px solid #7287fd';
            const themeBtn = p.querySelector('.uwa-theme-btn');
            if (themeBtn) {
                themeBtn.style.background = isDark ? '#1e1e1e' : '#eff1f5';
                themeBtn.style.color = isDark ? '#eff1f5' : '#4c4f69';
            }
        };

        const syncButtons = (p) => {
            const state = p.dataset.state;
            p.querySelectorAll('.uwa-ctrl-btn').forEach(b => {
                const isActive = b.dataset.targetState === state;
                b.disabled = isActive;
                b.style.opacity = isActive ? '0.5' : '1';
                b.style.cursor = isActive ? 'not-allowed' : 'pointer';
            });
        };

        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'uwa-control-panel';
            panel.dataset.state = 'running';
            panel.dataset.theme = 'auto';
            panel.style.cssText = 'position: fixed; top: 10px; right: 10px; z-index: 2147483647; padding: 0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: system-ui, sans-serif; font-size: 14px; min-width: 220px;';

            const header = document.createElement('div');
            header.className = 'uwa-header';
            header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; cursor: move; user-select: none; border-radius: 8px 8px 0 0;';

            const title = document.createElement('span');
            title.style.cssText = 'font-weight: 600; font-family: system-ui, sans-serif; font-size: 14px;';
            title.textContent = 'UWA Control';
            header.appendChild(title);

            const themeBtn = document.createElement('button');
            themeBtn.className = 'uwa-theme-btn';
            themeBtn.title = 'Toggle theme (auto/dark/light)';
            themeBtn.style.cssText = 'border: none; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-family: system-ui, sans-serif; font-size: 14px; line-height: 1;';
            themeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const p = document.getElementById('uwa-control-panel');
                const current = p.dataset.theme || 'auto';
                const next = current === 'auto' ? 'dark' : current === 'dark' ? 'light' : 'auto';
                p.dataset.theme = next;
                updateThemeIcon();
                applyTheme(p);
            });
            header.appendChild(themeBtn);
            panel.appendChild(header);

            const btns = document.createElement('div');
            btns.style.cssText = 'display: flex; gap: 6px; padding: 8px 10px;';

            const createBtn = (text, state, color) => {
                const b = document.createElement('button');
                b.className = 'uwa-ctrl-btn';
                b.textContent = text;
                b.dataset.targetState = state;
                b.style.cssText = `background: ${color}; color: #eff1f5; border: none; padding: 5px 10px; border-radius: 4px; font-weight: 600; font-family: system-ui, sans-serif; font-size: 14px; transition: opacity 0.15s;`;
                b.addEventListener('click', function() {
                    const p = document.getElementById('uwa-control-panel');
                    if (p) {
                        p.dataset.state = this.dataset.targetState;
                        syncButtons(p);
                    }
                });
                return b;
            };

            btns.appendChild(createBtn('▶ Run', 'running', '#40a02b'));
            btns.appendChild(createBtn('⏸ Pause', 'paused', '#fe640b'));
            btns.appendChild(createBtn('⏹ Stop', 'stopped', '#d20f39'));
            panel.appendChild(btns);

            // Кнопка захвата поля ввода
            const captureBtn = document.createElement('button');
            captureBtn.className = 'uwa-capture-btn';
            captureBtn.textContent = '📍 Capture field';
            captureBtn.style.cssText = 'width: 95%; background: #04a5e5; color: #eff1f5; border: none; padding: 6px 10px; border-radius: 4px; font-weight: 600; font-family: system-ui, sans-serif; font-size: 14px; cursor: pointer; margin: 6px; transition: background 0.2s;';

            // Запоминаем последний валидный элемент ввода
            let lastValidInput = null;
            document.addEventListener('focusin', (e) => {
                const el = e.target;
                if (el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' || el.getAttribute('contenteditable') === 'true')) {
                    if (!el.hasAttribute('readonly') && el.getAttribute('aria-readonly') !== 'true') {
                        lastValidInput = el;
                    }
                }
            });

            // Вычисление CSS-пути к элементу
            function buildPath(el) {
                if (!el || el === document.body) return 'body';
                if (el.id) return '#' + CSS.escape(el.id);

                const parts = [];
                let cur = el;
                while (cur && cur.nodeType === 1 && cur !== document.body) {
                    let sel = cur.tagName.toLowerCase();
                    if (cur.id) {
                        parts.unshift('#' + CSS.escape(cur.id));
                        break;
                    }
                    if (cur.parentNode) {
                        const siblings = Array.from(cur.parentNode.children);
                        const idx = siblings.indexOf(cur) + 1;
                        sel += ':nth-child(' + idx + ')';
                    }
                    parts.unshift(sel);
                    cur = cur.parentNode;
                }
                return parts.join(' > ');
            }

            // preventDefault на mousedown, чтобы фокус не уходил из поля чата
            captureBtn.addEventListener('mousedown', (e) => {
                e.preventDefault();
            });

            captureBtn.addEventListener('click', () => {
                const target = lastValidInput || document.activeElement;
                if (!target || target === document.body || target === captureBtn) {
                    captureBtn.textContent = '❌ No field focused';
                    setTimeout(() => { captureBtn.textContent = '📍 Capture field'; }, 2000);
                    return;
                }

                const path = buildPath(target);
                const panel = document.getElementById('uwa-control-panel');
                if (panel) {
                    panel.dataset.inputPath = path;
                }

                captureBtn.textContent = '✅ Field captured';
                captureBtn.style.background = '#04a5e5';

                setTimeout(() => {
                    captureBtn.textContent = '📍 Capture field';
                    captureBtn.style.background = '#04a5e5';
                }, 10000);
            });

            panel.appendChild(captureBtn);

            document.body.appendChild(panel);

            let isDragging = false;
            let offsetX = 0, offsetY = 0;
            header.addEventListener('mousedown', (e) => {
                if (e.target === themeBtn) return;
                isDragging = true;
                const rect = panel.getBoundingClientRect();
                offsetX = e.clientX - rect.left;
                offsetY = e.clientY - rect.top;
                e.preventDefault();
            });
            document.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                panel.style.left = (e.clientX - offsetX) + 'px';
                panel.style.top = (e.clientY - offsetY) + 'px';
                panel.style.right = 'auto';
            });
            document.addEventListener('mouseup', () => { isDragging = false; });

            const updateThemeIcon = () => {
                const p = document.getElementById('uwa-control-panel');
                const t = p.dataset.theme || 'auto';
                themeBtn.textContent = t === 'auto' ? '◐' : t === 'dark' ? '🌙' : '☀';
            };
            updateThemeIcon();
        }

        syncButtons(panel);
        applyTheme(panel);

        return panel.dataset.state;
    })()
    """
    call_id = 9000
    while True:
        try:
            async with ws_lock:
                await websocket.send(
                    json.dumps(
                        {
                            "id": call_id,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": js_ui_check,
                                "returnByValue": True,
                            },
                        }
                    )
                )
                response = await websocket.recv()
            res_data = (
                json.loads(response)
                .get("result", {})
                .get("result", {})
                .get("value", "")
            )
            if res_data in ["running", "paused", "stopped"]:
                if uwa_control_state != res_data:
                    print(f"  [*] UI Control State changed to: {res_data.upper()}")
                uwa_control_state = res_data
            call_id += 1
        except Exception as e:
            print(f"  [!] UI Monitor Error: {e}")

        await asyncio.sleep(2)


async def main_loop():
    page_id = get_dynamic_page_id()
    if not page_id:
        print(
            "Error: Could not find page. Check if Chrome is open with --remote-debugging-port=9222"
        )
        return

    uri = f"ws://localhost:9222/devtools/page/{page_id}"

    try:
        async with websockets.connect(uri) as websocket:  # pyright: ignore[reportAttributeAccessIssue]
            print(f"[*] Connected to Page: {page_id}")
            print("[*] Monitoring for JSON blocks with 'uwa_msg_id'...")

            # Запуск монитора UI-состояния в фоновой задаче
            ui_monitor_task = asyncio.create_task(monitor_ui_state(websocket))

            last_processed_msgid = None

            while True:
                # Проверка состояния управления перед обработкой
                if uwa_control_state == "stopped":
                    print("[!] Stop command received. Shutting down gracefully.")
                    ui_monitor_task.cancel()
                    break

                if uwa_control_state == "paused":
                    last_processed_msgid = None  # очистка при паузе т.к. во время паузы могли пройти новые блоки
                    await asyncio.sleep(2)
                    continue

                full_text = await get_page_text(websocket)

                # Ищем все JSON-подобные блоки в тексте страницы с учетом вложенности
                json_blocks = extract_json_blocks(full_text)

                if not json_blocks:
                    await asyncio.sleep(2)
                    continue

                # Извлекаем данные последнего и предпоследнего блоков для проверки
                last_block_str = json_blocks[-1]
                pr_msgid = None

                if len(json_blocks) >= 2:
                    try:
                        pr_block_str = re.sub(
                            r"[\u200b-\u200d\ufeff]", "", json_blocks[-2]
                        )
                        pr_data = json.loads(pr_block_str)
                        pr_msgid = pr_data.get("uwa_msg_id")
                    except:
                        pass

                try:
                    # Очистка текста от возможных невидимых символов перед парсингом
                    clean_json_str = re.sub(
                        r"[\u200b-\u200d\ufeff]", "", last_block_str
                    )
                    request_data = json.loads(clean_json_str)

                    current_msgid = request_data.get("uwa_msg_id")

                    if current_msgid and current_msgid != last_processed_msgid:
                        # Защита от множественных блоков (как было раньше)
                        if (
                            pr_msgid is not None
                            and last_processed_msgid is not None
                            and pr_msgid != last_processed_msgid
                        ):
                            error_response = {
                                "uwa_msg_id": current_msgid,
                                "error": (
                                    "Error: Multiple JSON tool blocks were detected.\n"
                                    f"Previous unprocessed ID: {pr_msgid}\n"
                                    "Only one JSON block per message is allowed."
                                ),
                            }
                            print("\n[!] Multiple blocks detected.")

                            result_text = json.dumps(
                                error_response, ensure_ascii=False, indent=2
                            )
                            await set_page_input(websocket, result_text)

                            last_processed_msgid = current_msgid
                            continue

                        print(f"\n[!] New JSON request detected (ID: {current_msgid})")

                        tools = request_data.get("tools", [])
                        if not tools:
                            print(
                                f"  > No tools found in request {current_msgid}. Skipping."
                            )
                            last_processed_msgid = current_msgid
                            continue

                        print(f"  > Processing {len(tools)} tool(s)...")
                        results = []

                        for tool in tools:
                            tool_type = tool.get("type")
                            result_item = tool.copy()

                            if tool_type == "terminal":
                                command = tool.get("command")
                                if command:
                                    res = execute_command(command)
                                    result_item["result"] = res
                                else:
                                    result_item["result"] = (
                                        "Error: Missing command for terminal tool."
                                    )

                            elif tool_type == "file":
                                res = execute_file_tool(tool)
                                result_item["result"] = res

                            elif tool_type == "around":
                                res = execute_around_tool(tool)
                                result_item["result"] = res
                                for field in ["new_text", "old_text"]:
                                    if (
                                        field in result_item
                                        and isinstance(result_item[field], str)
                                        and len(result_item[field]) > 15
                                    ):
                                        result_item[field] = (
                                            result_item[field][:15] + "..."
                                        )
                            else:
                                result_item["result"] = (
                                    f"Error: Unknown tool type '{tool_type}'."
                                )

                            results.append(result_item)

                        # Формируем итоговый ответ
                        response = {"uwa_msg_id": current_msgid, "tools": results}

                        last_processed_msgid = current_msgid

                        result_text = json.dumps(response, ensure_ascii=False, indent=2)
                        await set_page_input(websocket, result_text)

                except json.JSONDecodeError as e:
                    # Если это не валидный JSON, но содержит uwa_msg_id, попробуем сообщить об ошибке
                    # Но только если мы можем вытащить ID
                    id_match = re.search(r'"uwa_msg_id"\s*:\s*"(.*?)"', last_block_str)
                    if id_match:
                        error_id = id_match.group(1)
                        if error_id != last_processed_msgid:
                            error_response = {
                                "uwa_msg_id": error_id,
                                "error": f"JSON Decode Error: {e!s}",
                            }

                            result_text = json.dumps(
                                error_response, ensure_ascii=False, indent=2
                            )
                            await set_page_input(websocket, result_text)

                            last_processed_msgid = error_id

                await asyncio.sleep(2)

    except Exception as e:
        print(f"\nPipeline Error: {e}")
        print("Attempting to reconnect in 5 seconds...")
        await asyncio.sleep(5)
        await main_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[!] Shutdown requested by user. Exiting...")
        sys.exit(0)
