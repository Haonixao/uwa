import sys
import json
import os

def get_symbols(path: str):
    """
    Вызывает ctags или парсит markdown.
    """
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        b_path = os.path.join(script_dir, path)
        if not os.path.exists(b_path):
            return f"Error: File not found: {path}"
        path = b_path

    ext = os.path.splitext(path)[1].lower()

    # === Markdown ===
    if ext == '.md':
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            symbols = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line.startswith('#'):
                    # Считаем уровень заголовка
                    level = 0
                    while level < len(line) and line[level] == '#':
                        level += 1
                    title = line[level:].strip()
                    if title:
                        symbols.append(f"{i:4d} - {i:4d} | heading{level:<2} | {title}")

            if not symbols:
                return "No headings found in markdown file."

            header = f"Headings in {os.path.basename(path)}:\n" + "-"*70
            return header + "\n" + "\n".join(symbols)

        except Exception as e:
            return f"Error parsing markdown: {str(e)}"

    # === Кодовые файлы (ctags) ===
    try:
        import subprocess
        import json

        result = subprocess.run(
            ['ctags', '--output-format=json', '--fields=+n+e', '--extras=+q', '-f', '-', path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            if "not recognized" in result.stderr or result.returncode == 127:
                return (
                    "Error: ctags not found.\n\n"
                    "Install: sudo snap install universal-ctags --classic or choco install universal-ctags -y"
                )
            return f"ctags error: {result.stderr.strip()}"

        symbols = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            try:
                tag = json.loads(line)
                if tag.get("_type") != "tag":
                    continue

                start = tag.get("line", "?")
                end = tag.get("end", "?")
                kind = tag.get("kind", "?")
                name = tag.get("name", "?")

                symbols.append(f"{start:4d} - {end:4d} | {kind:10s} | {name}")
            except:
                continue

        if not symbols:
            return f"No symbols found in {os.path.basename(path)}."

        header = f"Symbols in {os.path.basename(path)}:\n" + "-"*70
        return header + "\n" + "\n".join(symbols)

    except FileNotFoundError:
        return "Error: ctags not found.\nInstall: choco install universal-ctags -y"
    except Exception as e:
        return f"Error: {str(e)}"

def read_lines(path, start, end):
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        b_path = os.path.join(script_dir, path)
        if not os.path.exists(b_path):
            return f"Error: File not found: {path}"
        path = b_path
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 1-indexed slicing
        selected = lines[start-1:end]

        # Добавляем номера строк — это критично!
        numbered = []
        for i, line in enumerate(selected, start=start):
            numbered.append(f"{i:4d} | {line.rstrip()}")

        return "\n".join(numbered)

    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_patch(path, start, end, new_text):
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        b_path = os.path.join(script_dir, path)
        if not os.path.exists(b_path):
            return f"Error: File not found: {path}"
        path = b_path
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # new_text может приходить с \n или без — нормализуем
        new_lines = new_text.splitlines(keepends=True)

        # Если new_text не заканчивается переносом, а оригинал заканчивался — добавляем
        if new_lines and not new_lines[-1].endswith('\n') and (end <= len(lines) and lines[end-1].endswith('\n') if end > 0 else False):
            new_lines[-1] += '\n'

        # Применяем патч
        patched = lines[:start-1] + new_lines + lines[end:]

        with open(path, "w", encoding="utf-8", newline='') as f:
            f.writelines(patched)

        return "OK"
    except Exception as e:
        return f"Error patching file: {str(e)}"

def write_patch_with_old(path, old_text, new_text, replace_all=False):
    """
    Заменяет old_text на new_text в файле.
    Если replace_all=True — все вхождения, иначе — первое.
    Аналог Edit с old_string + replace_all.
    """
    if not os.path.exists(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        b_path = os.path.join(script_dir, path)
        if not os.path.exists(b_path):
            return f"Error: File not found: {path}"
        path = b_path
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_text not in content:
            return "Error: old_text not found in file. Note: old_text fully accounts for all spaces in all lines for search."

        if replace_all:
            new_content = content.replace(old_text, new_text)
            count = content.count(old_text)
        else:
            new_content = content.replace(old_text, new_text, 1)
            count = 1

        with open(path, "w", encoding="utf-8", newline='') as f:
            f.write(new_content)

        return f"OK: replaced {count} occurrence(s)"
    except Exception as e:
        return f"Error patching file: {str(e)}"

def main():
    try:
        # Read from stdin
        input_data = sys.stdin.read()
        if not input_data:
            print("Error: No input data")
            return

        data = json.loads(input_data)
        action = data.get("action")
        path = data.get("path")

        if action == "read":
            print(read_lines(path, int(data.get("start", 1)), int(data.get("end", 1000000))))
        elif action == "patch":
            old_text = data.get("old_text")
            if old_text is not None:
                print(write_patch_with_old(
                    path,
                    old_text,
                    data.get("new_text", ""),
                    replace_all=data.get("replace_all", False)
                ))
            else:
                print(write_patch(path, int(data.get("start")), int(data.get("end")), data.get("new_text", "")))
        elif action == "symbols":
            result = get_symbols(path)
            print(result)
        else:
            print(f"Error: Unknown action '{action}'")
    except Exception as e:
        print(f"Error in filetool: {str(e)}")

if __name__ == "__main__":
    main()
