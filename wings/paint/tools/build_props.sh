#!/usr/bin/env bash
# Build every paint prop headless from wings/paint/models/src/props.py (parallel).
#   wings/paint/tools/build_props.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/paint/models/src/props.py
OUT=wings/paint/models
LOG=${TMPDIR:-/tmp}/paint_props
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "mill:mill" "boat:boat" "frame:frame" "stretcher:stretcher" "post:post"
  "easel:easel" "palette:palette" "tube:tube" "tube_blue:tube_blue"
)
want=" $* "
fail=0
for e in "${ALL[@]}"; do
  name="${e%%:*}"; args="${e#*:}"
  [[ $# -eq 0 || "$want" == *" $name "* ]] || continue
  ( tools/blender_build.sh "$SRC" "$OUT/$name.glb" $args > "$LOG/$name.log" 2>&1 \
      && echo "ok   $name $(grep TOTAL "$LOG/$name.log" | cut -d' ' -f2) tris" \
      || { echo "FAIL $name (see $LOG/$name.log)"; tail -5 "$LOG/$name.log"; } ) &
  while (( $(jobs -r | wc -l) >= 6 )); do sleep 0.2; done
done
wait
