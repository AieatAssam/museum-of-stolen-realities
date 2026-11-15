#!/usr/bin/env bash
# Headless import that survives iCloud conflict copies ("title 2.gd"): imports, then removes the
# copies from .godot/global_script_class_cache.cfg so the real scripts own their class_names.
# Usage: tools/godot_import.sh        (tests/run_smoke.sh calls it when .godot/ is missing)
set -uo pipefail
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
"$GODOT" --headless --path . --import 2>&1
code=${PIPESTATUS[0]}
python3 tools/strip_conflict_copies.py .
exit $code
