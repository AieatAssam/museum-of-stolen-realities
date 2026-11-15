#!/usr/bin/env bash
# Headless smoke test. Exit 0 only if the test passes AND the log has no script/engine errors.
set -uo pipefail
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
LOG="$(mktemp)"
"$GODOT" --headless --path . tests/smoke.tscn 2>&1 | tee "$LOG"
code=${PIPESTATUS[0]}
# "resources still in use at exit" is engine shutdown noise, not a script error
errs=$(grep -E "SCRIPT ERROR|Parse Error|^ERROR:" "$LOG" | grep -v "resources still in use at exit" | grep -v "ObjectDB instances leaked" || true)
if [[ -n "$errs" ]]; then
  echo "---- errors in log ----"; echo "$errs"; code=1
fi
echo "smoke exit: $code"
exit $code
