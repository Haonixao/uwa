import asyncio
import json
import re
import sys
import websockets
import subprocess
import time
import http.client
import os

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
                if item.get('type') == 'page' and 'url' in item:
                    print(f"[*] Found page: {item.get('title')} (ID: {item.get('id')})")
                    return item.get('id')
        return None
    except Exception as e:
        print(f"Error fetching page ID: {e}")
        return None

async def get_page_text(websocket):
    """Возвращает весь текст страницы"""
    await websocket.send(json.dumps({
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {'expression': 'document.body.innerText', 'returnByValue': True}
    }))
    response = await websocket.recv()
    return json.loads(response).get('result', {}).get('result', {}).get('value', '')

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
            timeout=60
        )
        output = result.stdout if result.stdout else ""
        if result.stderr:
            output += "\nError:\n" + result.stderr
        return output.strip()
    except Exception as e:
        return f"Execution Error: {str(e)}"

patched_files = {}  # path -> True (для защиты от двойного патча)
read_counter = 0

def execute_file_tool(tool_data):
    """Выполняет файловые операции через filetool.py на основе JSON данных"""
    print(f"  > Executing File Tool: {tool_data.get('path')} ({tool_data.get('action', 'symbols')})")
    global read_counter

    try:
        # Подготовка данных для filetool.py
        data = {
            "path": tool_data.get("path"),
            "action": tool_data.get("action", "symbols"),
            "start": tool_data.get("start"),
            "end": tool_data.get("end"),
            "old_text": tool_data.get("old_text"),
            "new_text": tool_data.get("new_text"),
            "replace_all": tool_data.get("replace_all")
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
                return f"Error: Double patch with strings range detected for {path} without read/symbols in between. This can lead to incorrect changes. Do read and then patch with strings range again. Or use patch with old_text + new_text (no double patch problem in this case)"
            patched_files[path] = True
        elif action in ["read", "symbols"]:
            if path in patched_files:
                del patched_files[path]
            if action == "read":
                read_counter += 1

        script_dir = os.path.dirname(os.path.abspath(__file__))
        filetool_path = os.path.join(script_dir, "filetool.py")

        process = subprocess.Popen(
            [sys.executable, filetool_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8"
        )

        stdout, stderr = process.communicate(input=json.dumps(data))
        output = stdout.strip()
        if stderr:
            output += "\nError:\n" + stderr

        print(f"    [+] File Tool Output: {output[:50]}...")
        return output

    except Exception as e:
        return f"File Tool Error: {str(e)}"

def extract_json_blocks(text):
    """Находит все JSON-блоки, содержащие uwa_msg_id, с учетом вложенных скобок"""
    blocks = []
    # Ищем все вхождения "uwa_msg_id"
    for match in re.finditer(r'"uwa_msg_id"\s*:', text):
        start_idx = text.rfind('{', 0, match.start())
        if start_idx == -1:
            continue
            
        # Считаем баланс скобок
        brace_count = 0
        end_idx = -1
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx != -1:
            blocks.append(text[start_idx:end_idx])
    return blocks

async def main_loop():
    page_id = get_dynamic_page_id()
    if not page_id:
        print("Error: Could not find page. Check if Chrome is open with --remote-debugging-port=9222")
        return

    uri = f'ws://localhost:9222/devtools/page/{page_id}'
    output_file = "out.json"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"--- JSON-based Agent Executor (Output to {output_file}) ---")
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
                        pr_block_str = re.sub(r'[\u200b-\u200d\ufeff]', '', json_blocks[-2])
                        pr_data = json.loads(pr_block_str)
                        pr_msgid = pr_data.get("uwa_msg_id")
                    except:
                        pass
                
                try:
                    # Очистка текста от возможных невидимых символов перед парсингом
                    clean_json_str = re.sub(r'[\u200b-\u200d\ufeff]', '', last_block_str)
                    request_data = json.loads(clean_json_str)
                    
                    current_msgid = request_data.get("uwa_msg_id")
                    
                    if current_msgid and current_msgid != last_processed_msgid:
                        # Защита от множественных блоков (как было раньше)
                        if pr_msgid is not None and last_processed_msgid is not None and pr_msgid != last_processed_msgid:
                            error_response = {
                                "uwa_msg_id": current_msgid,
                                "error": (
                                    "Error: Multiple JSON tool blocks were detected.\n"
                                    f"Previous unprocessed ID: {pr_msgid}\n"
                                    "Only one JSON block per message is allowed."
                                )
                            }
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(error_response, f, ensure_ascii=False, indent=2)
                            print(f"\n[!] Multiple blocks detected. Error written to {output_file}")
                            last_processed_msgid = current_msgid
                            continue

                        print(f"\n[!] New JSON request detected (ID: {current_msgid})")
                        
                        tools = request_data.get("tools", [])
                        if not tools:
                            print(f"  > No tools found in request {current_msgid}. Skipping.")
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
                                    result_item["result"] = "Error: Missing command for terminal tool."
                            
                            elif tool_type == "file":
                                res = execute_file_tool(tool)
                                result_item["result"] = res
                                for field in ["new_text", "old_text"]:
                                    if field in result_item and isinstance(result_item[field], str) and len(result_item[field]) > 50:
                                        result_item[field] = result_item[field][:50] + "..."
                            else:
                                result_item["result"] = f"Error: Unknown tool type '{tool_type}'."
                            
                            results.append(result_item)

                        # Формируем итоговый ответ
                        response = {
                            "uwa_msg_id": current_msgid,
                            "tools": results
                        }
                        
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(response, f, ensure_ascii=False, indent=2)
                        
                        print(f"  > Result written to {output_file}. Please copy it manually.")
                        last_processed_msgid = current_msgid
                
                except json.JSONDecodeError as e:
                    # Если это не валидный JSON, но содержит uwa_msg_id, попробуем сообщить об ошибке
                    # Но только если мы можем вытащить ID
                    id_match = re.search(r'"uwa_msg_id"\s*:\s*"(.*?)"', last_block_str)
                    if id_match:
                        error_id = id_match.group(1)
                        if error_id != last_processed_msgid:
                            error_response = {
                                "uwa_msg_id": error_id,
                                "error": f"JSON Decode Error: {str(e)}"
                            }
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(error_response, f, ensure_ascii=False, indent=2)
                            print(f"  > Error written to {output_file}")
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
