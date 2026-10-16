"""around.py — UWA tool: чтение контекста вокруг вхождений needle.

Принимает JSON через stdin:
  path        — файл или каталог для рекурсивного поиска
  needle      — искомая строка (литерал, не regex)
  before      — строк контекста до вхождения (по умолчанию 25)
  after       — строк контекста после вхождения (по умолчанию 25)
  max_matches — максимум показанных вхождений суммарно (0 или нет = без лимита)
  include     — glob-маска имени файла, например *.go (нет = все файлы)
  exclude     — glob-маска исключения, например *_test.go

Формат вывода (одна строка result):
  file: <путь>
  NNN |          обычная строка контекста
  NNN needle ->  строка с вхождением
  (skipped. no needle) — между непересекающимися окнами
  (truncated: max_matches reached) — обрезка внутри файла
В конце — сводка: показано/всего вхождений, файлы с матчами, пропуски.
"""

import fnmatch
import json
import os
import sys

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "__pycache__"}


def resolve_path(path):
    if os.path.exists(path):
        return path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    b_path = os.path.join(script_dir, path)
    if os.path.exists(b_path):
        return b_path
    return None


def match_mask(name, rel, mask):
    if not mask:
        return False
    masks = (
        mask
        if isinstance(mask, list)
        else [m.strip() for m in mask.split(",") if m.strip()]
    )
    return any(fnmatch.fnmatch(name, m) or fnmatch.fnmatch(rel, m) for m in masks)


def collect_files(root, include, exclude):
    if os.path.isfile(root):
        name = os.path.basename(root)
        if match_mask(name, name, exclude):
            return []
        if include and not match_mask(name, name, include):
            return []
        return [root]
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if match_mask(fn, rel, exclude):
                continue
            if include and not match_mask(fn, rel, include):
                continue
            files.append(os.path.join(dirpath, fn))
    return sorted(files)


def render_file(path, lines, match_idxs, before, after, limit_left):
    match_set = set(match_idxs)
    total = len(lines)
    covered = set()
    for i in match_idxs:
        covered.update(range(max(0, i - before), min(total, i + after + 1)))

    out = [f"file: {path}"]
    prev = None
    rendered = 0
    truncated = False

    for ln in sorted(covered):
        if ln in match_set and limit_left is not None and rendered >= limit_left:
            truncated = True
            break
        if prev is not None and ln != prev + 1:
            out.append("...(skipped. no needle)...")
        text = lines[ln].rstrip()
        if ln in match_set:
            out.append(f"{ln + 1:4d} needle ->|{text}")
            rendered += 1
        else:
            out.append(f"{ln + 1:4d}|{text}")
        prev = ln

    if truncated:
        out.append("...(truncated: max_matches reached)...")
    return out, rendered, truncated


def run(params):
    p = params.get("path") or ""
    if not p:
        return "Error: path is required"
    path = resolve_path(p)
    if path is None:
        return f"Error: path not found: {p}"

    needle = str(params.get("needle") or "")
    if not needle:
        return "Error: needle is required"

    before = int(params.get("before", 25))
    after = int(params.get("after", 25))
    max_matches = int(params.get("max_matches") or 0)
    limit_left = max_matches if max_matches > 0 else None

    files = collect_files(path, params.get("include"), params.get("exclude"))
    if not files:
        return f"No files matched include/exclude under: {p}"

    parts = []
    total_matches = 0
    rendered_total = 0
    files_with_matches = 0
    files_pending = []
    binary_skipped = 0
    unreadable = 0

    for fp in files:
        try:
            with open(fp, "rb") as f:
                raw = f.read()
        except OSError:
            unreadable += 1
            continue

        if b"\x00" in raw[:4096]:
            binary_skipped += 1
            continue

        lines = raw.decode("utf-8", errors="replace").splitlines()
        match_idxs = [i for i, line in enumerate(lines) if needle in line]
        if not match_idxs:
            continue

        files_with_matches += 1
        total_matches += len(match_idxs)

        if limit_left is not None and rendered_total >= limit_left:
            files_pending.append(fp)
            continue

        block, rendered, truncated = render_file(
            fp,
            lines,
            match_idxs,
            before,
            after,
            limit_left - rendered_total if limit_left is not None else None,
        )
        parts.append("\n".join(block))
        rendered_total += rendered
        if truncated:
            files_pending = []

    if not files_with_matches:
        notes = []
        if binary_skipped:
            notes.append(f"binary files skipped: {binary_skipped}")
        if unreadable:
            notes.append(f"unreadable files: {unreadable}")
        tail = f" ({'; '.join(notes)})" if notes else ""
        return (
            f"No matches for needle {needle!r} in {len(files)} file(s) under: {p}{tail}"
        )

    summary = [
        "---",
        f"matches: shown {rendered_total} of {total_matches}",
        f"files with matches: {files_with_matches}",
    ]
    if binary_skipped:
        summary.append(f"binary files skipped: {binary_skipped}")
    if unreadable:
        summary.append(f"unreadable files: {unreadable}")
    if files_pending:
        summary.append("matches in remaining files: " + ", ".join(files_pending))

    return "\n\n".join(parts) + "\n" + "\n".join(summary)


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print("Error: No input data")
            return
        data = json.loads(input_data)
        print(run(data))
    except Exception as e:
        print(f"Error in around tool: {e}")


if __name__ == "__main__":
    main()
