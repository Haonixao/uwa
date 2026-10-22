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


async def set_page_input(websocket, text, attempts=10, delay=3):
    """
    Пытается вставить текст вместо $UWA_INPUT.
    Каждая попытка: сценарий 1 — поиск элемента по тегу; при успехе путь к
    элементу сохраняется в last_input_path. Сценарий 2 — вставка в элемент
    по сохранённому пути, без поиска по тегу.
    """
    global last_input_path
    safe_text = json.dumps(text)

    js_find = f"""
    (function() {{
        function buildPath(el) {{
            if (el.id) return '#' + CSS.escape(el.id);
            const parts = [];
            let cur = el;
            while (cur && cur.nodeType === 1 && cur !== document.body) {{
                let sel = cur.tagName.toLowerCase();
                if (cur.parentNode) {{
                    const sibs = Array.from(cur.parentNode.children).filter(
                        c => c.tagName === cur.tagName
                    );
                    if (sibs.length > 1) sel += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
                }}
                parts.unshift(sel);
                cur = cur.parentNode;
            }}
            return parts.join(' > ');
        }}

        const inputs = Array.from(document.querySelectorAll('textarea, [contenteditable="true"]'));
        for (let i = inputs.length - 1; i >= 0; i--) {{
            let el = inputs[i];
            if (el.hasAttribute('readonly') || el.getAttribute('aria-readonly') === 'true') continue;

            let isTextarea = el.tagName === 'TEXTAREA';
            let content = isTextarea ? el.value : el.innerText;

            if (content.includes('$UWA_INPUT')) {{
                el.focus();

                if (!isTextarea) {{
                    const selection = window.getSelection();
                    const range = document.createRange();

                    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while(node = walker.nextNode()) {{
                        let index = node.textContent.indexOf('$UWA_INPUT');
                        if (index !== -1) {{
                            range.setStart(node, index);
                            range.setEnd(node, index + '$UWA_INPUT'.length);
                            selection.removeAllRanges();
                            selection.addRange(range);
                            break;
                        }}
                    }}
                }} else {{
                    let start = el.value.indexOf('$UWA_INPUT');
                    el.setSelectionRange(start, start + '$UWA_INPUT'.length);
                }}

                const success = document.execCommand('insertText', false, {safe_text});

                if (!success) {{
                    if (isTextarea) {{
                        el.value = el.value.replace('$UWA_INPUT', {safe_text});
                    }} else {{
                        el.innerText = el.innerText.replace('$UWA_INPUT', {safe_text});
                    }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}

                return JSON.stringify({{ ok: true, path: buildPath(el) }});
            }}
        }}
        return JSON.stringify({{ ok: false }});
    }})()
    """

    js_by_path_template = """
    (function() {
        let el = null;
        try { el = document.querySelector(__PATH__); } catch (e) {
            return JSON.stringify({ ok: false, stale: true });
        }
        if (!el) return JSON.stringify({ ok: false, stale: true });
        if (el.hasAttribute('readonly') || el.getAttribute('aria-readonly') === 'true')
            return JSON.stringify({ ok: false });

        let isTextarea = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT';

        el.focus();

        if (isTextarea) {
            el.setSelectionRange(el.value.length, el.value.length);
        } else {
            const selection = window.getSelection();
            if (selection) {
                const range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }

        const success = document.execCommand('insertText', false, __SAFE_TEXT__);
        if (!success) {
            if (isTextarea) {
                el.value = el.value.replace('$UWA_INPUT', __SAFE_TEXT__);
            } else {
                el.innerText = el.innerText.replace('$UWA_INPUT', __SAFE_TEXT__);
            }
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }

        return JSON.stringify({ ok: true });
    })()
    """

    def make_js_by_path(path):
        return js_by_path_template.replace("__PATH__", json.dumps(path)).replace(
            "__SAFE_TEXT__", safe_text
        )

    async def eval_js(expr, call_id):
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

    print("  [*] Waiting for $UWA_INPUT tag on page...")

    for i in range(attempts):
        data = await eval_js(js_find, 100 + i)
        if data.get("ok"):
            print(f"  [+] $UWA_INPUT filled on attempt {i + 1} (search).")
            p = data.get("path")
            if p:
                last_input_path = p
            return True

        if last_input_path:
            data2 = await eval_js(make_js_by_path(last_input_path), 200 + i)
            if data2.get("ok"):
                print(f"  [+] $UWA_INPUT filled on attempt {i + 1} (saved path).")
                return True
            if data2.get("stale"):
                print("  [*] Saved path is stale, clearing it.")
                last_input_path = None

        if i < attempts - 1:
            await asyncio.sleep(delay)

    print("  [!] $UWA_INPUT not found after all attempts. Skipping autofill.")
    return False


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

# CSS-путь к элементу с $UWA_INPUT из последней успешной вставки (сценарий 1)
last_input_path = None


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


async def main_loop():
    page_id = get_dynamic_page_id()
    if not page_id:
        print(
            "Error: Could not find page. Check if Chrome is open with --remote-debugging-port=9222"
        )
        return

    uri = f"ws://localhost:9222/devtools/page/{page_id}"
    output_file = "out.json"

    try:
        async with websockets.connect(uri) as websocket:  # pyright: ignore[reportAttributeAccessIssue]
            print(f"[*] Connected to Page: {page_id}")
            print("[*] Monitoring for JSON blocks with 'uwa_msg_id'...")

            last_processed_msgid = None

            while True:
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
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(
                                    error_response, f, ensure_ascii=False, indent=2
                                )
                            print(
                                f"\n[!] Multiple blocks detected. Error written to {output_file}"
                            )

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
                                        and len(result_item[field]) > 50
                                    ):
                                        result_item[field] = (
                                            result_item[field][:50] + "..."
                                        )
                            else:
                                result_item["result"] = (
                                    f"Error: Unknown tool type '{tool_type}'."
                                )

                            results.append(result_item)

                        # Формируем итоговый ответ
                        response = {"uwa_msg_id": current_msgid, "tools": results}

                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(response, f, ensure_ascii=False, indent=2)

                        print(
                            f"  > Result written to {output_file}. Please copy it manually."
                        )
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
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(
                                    error_response, f, ensure_ascii=False, indent=2
                                )
                            print(f"  > Error written to {output_file}")

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
