#!/usr/bin/env bash
# Build every paint nature model headless from wings/paint/models/src/nature.py (parallel).
#   wings/paint/tools/build_nature.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/paint/models/src/nature.py
OUT=wings/paint/models
LOG=${TMPDIR:-/tmp}/paint_nature
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "tree_a:tree a" "tree_b:tree b" "tree_c:tree c"
  "tree_a_lod:tree a lod" "tree_b_lod:tree b lod" "tree_c_lod:tree c lod"
  "rock_a:rock a" "rock_b:rock b" "bush:bush" "tuft:tuft" "foliage_seg:foliage_seg" "knot:knot"
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
