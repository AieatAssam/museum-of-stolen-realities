#!/usr/bin/env bash
# Build every paint gallery fitting headless from wings/paint/models/src/gallery.py (parallel).
#   wings/paint/tools/build_gallery.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/paint/models/src/gallery.py
OUT=wings/paint/models
LOG=${TMPDIR:-/tmp}/paint_gallery
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "bench:bench" "stanchion:stanchion" "rope:rope" "picture_light:picture_light"
  "cornice:cornice" "dado:dado" "skirting:skirting" "pedestal:pedestal"
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
