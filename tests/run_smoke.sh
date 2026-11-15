#!/usr/bin/env bash
# Headless smoke test. Exit 0 only if the test passes AND the log has no script/engine errors and
# no shutdown leaks.
#   tests/run_smoke.sh                 the whole-game smoke (tests/smoke.tscn)
#   tests/run_smoke.sh <scene> [args]  any headless test scene, e.g. the playthrough runner
set -uo pipefail
cd "$(dirname "$0")/.."
GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
SCENE="${1:-tests/smoke.tscn}"
shift || true
LOG="$(mktemp)"
# --verbose so leaked objects are named; it adds ~700 lines of loader noise to the log.
"$GODOT" --headless --verbose --path . "$SCENE" "$@" 2>&1 | tee "$LOG"
code=${PIPESTATUS[0]}
errs=$(grep -E "SCRIPT ERROR|Parse Error|^ERROR:|^WARNING: .*leaked|Resource still in use" "$LOG" || true)
# Only tolerated leak: ResourceLoader LoadTokens from threaded scene loads (engine-side, see
# core/transitions.gd). Anything else leaked is ours.
bad_leaks=$(grep -E "^Leaked instance:" "$LOG" | grep -vE "^Leaked instance: RefCounted:[0-9]+ - Reference count: 0$" || true)
n_tokens=$(grep -cE "^Leaked instance: RefCounted:[0-9]+ - Reference count: 0$" "$LOG" || true)
errs=$(echo "$errs" | grep -vE "^WARNING: [0-9]+ ObjectDB instances were leaked" || true)
if [[ -n "$bad_leaks" ]]; then errs="$errs"$'\n'"$bad_leaks"; fi
if [[ "$n_tokens" -gt 6 ]]; then errs="$errs"$'\n'"too many leaked RefCounted ($n_tokens): not just LoadTokens"; fi
errs=$(echo "$errs" | sed '/^\s*$/d')
if [[ -n "$errs" ]]; then
  echo "---- errors in log ----"; echo "$errs"; code=1
fi
echo "smoke exit: $code"
exit $code
