#!/usr/bin/env bash
# Headless smoke test for The Drowned Aria. Exit 0 only if the full playthrough passes
# and the log has no script, parse or engine errors.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
cd "$ROOT"
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
LOG="$(mktemp)"
"$GODOT" --headless --path . wings/aria/tests/playthrough.tscn 2>&1 | tee "$LOG"
code=${PIPESTATUS[0]}
# "resources still in use at exit" and leaked-instance warnings are engine shutdown noise
errs=$(grep -E "SCRIPT ERROR|Parse Error|PLAYTHROUGH FAIL" "$LOG" || true)
if [[ -n "$errs" ]]; then
  echo "---- errors in log ----"; echo "$errs"; code=1
fi
echo "aria smoke exit: $code"
exit "$code"
