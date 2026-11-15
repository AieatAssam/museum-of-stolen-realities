#!/usr/bin/env python3
"""Drop iCloud conflict copies ("title 2.gd", "wing 3.gd") from Godot's global class cache.

iCloud's copies keep the original `class_name`, and on import Godot may register the copy instead
of the real script. The copies themselves are left alone (never delete them; they may hold work).
Usage: tools/strip_conflict_copies.py [project_dir]     (tools/godot_import.sh runs it for you)
Self-check: tools/strip_conflict_copies.py --test
"""
import re
import sys
from pathlib import Path

COPY = re.compile(r" [2-9]\d*(\.[A-Za-z0-9]+)?$")  # "name 2.gd", "name 2"


def is_copy(path: str) -> bool:
    stem = path.rsplit("/", 1)[-1]
    return bool(COPY.search(stem)) or any(COPY.search(p) for p in path.split("/")[:-1])


def strip(text: str) -> tuple[str, list[str]]:
    head, sep, body = text.partition("list=[")
    if not sep:
        return text, []
    body, end = body.rsplit("]", 1)
    entries = [e for e in re.split(r"(?<=\}), (?=\{)", body.strip()) if e.strip()]
    keep, dropped = [], []
    for e in entries:
        m = re.search(r'"path": "([^"]*)"', e)
        if m and is_copy(m.group(1)):
            dropped.append(m.group(1))
        else:
            keep.append(e)
    return head + sep + ", ".join(keep) + "]" + end, dropped


def main() -> int:
    if sys.argv[1:] == ["--test"]:
        assert is_copy("res://ui/title 2.gd") and is_copy("res://wings/glass 2/x.gd")
        assert not is_copy("res://ui/title.gd") and not is_copy("res://wings/aria/act2.gd")
        src = 'list=[{\n"class": &"A",\n"path": "res://a.gd"\n}, {\n"class": &"A",\n"path": "res://a 2.gd"\n}]\n'
        out, dropped = strip(src)
        assert dropped == ["res://a 2.gd"] and "a 2.gd" not in out and "res://a.gd" in out, out
        print("ok")
        return 0
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    cache = root / ".godot" / "global_script_class_cache.cfg"
    if not cache.exists():
        return 0
    out, dropped = strip(cache.read_text())
    if dropped:
        cache.write_text(out)
        for d in dropped:
            print(f"strip_conflict_copies: ignored iCloud copy {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
