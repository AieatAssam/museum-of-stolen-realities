#!/usr/bin/env bash
# Generate one image with Codex's built-in image generation and write it to OUT.png.
#   tools/gen_image.sh <out.png> "<prompt>"
# Safe to run many in parallel (each run gets its own codex thread id).
# Codex stores the image under ~/.codex/generated_images/<thread_id>/; we copy it
# ourselves instead of trusting the model to.
set -euo pipefail
OUT="$1"; PROMPT="$2"
CODEX="${CODEX:-/opt/homebrew/bin/codex}"
WORK="$(mktemp -d)"
mkdir -p "$(dirname "$OUT")"
LOG="$WORK/run.jsonl"
"$CODEX" exec --skip-git-repo-check -s read-only -C "$WORK" --json \
  "Use your image generation tool to generate exactly one image. Do not run shell commands. Do not write files. Image brief: $PROMPT" \
  </dev/null >"$LOG" 2>&1 || true
TID="$(head -c 4000 "$LOG" | grep -o '"thread_id":"[^"]*"' | head -1 | cut -d'"' -f4)"
SRC="$(ls -t "$HOME/.codex/generated_images/$TID"/*.png 2>/dev/null | head -1 || true)"
if [[ -z "$TID" || -z "$SRC" ]]; then
  echo "gen_image: no image produced (thread '$TID'). Log: $LOG" >&2
  tail -c 2000 "$LOG" >&2
  exit 1
fi
cp "$SRC" "$OUT"
rm -rf "$WORK"
echo "$OUT"
