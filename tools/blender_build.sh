#!/usr/bin/env bash
# Build one .glb from a Blender python build script, headless (never opens the GUI).
#   tools/blender_build.sh <build_script.py> <out.glb> [extra args passed to the script]
# The build script defines build(args) and creates objects in an empty scene; tools/blender/export.py
# applies transforms, checks the poly budget, unwraps missing UVs, and exports glTF (+Y up, metres).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${BLENDER:-/opt/homebrew/bin/blender}"
SCRIPT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUT="$(cd "$(dirname "$2")" 2>/dev/null && pwd || (mkdir -p "$(dirname "$2")" && cd "$(dirname "$2")" && pwd))/$(basename "$2")"
shift 2
"$BLENDER" --background --factory-startup --python-exit-code 1 \
  --python "$ROOT/tools/blender/export.py" -- "$SCRIPT" "$OUT" "$@"
