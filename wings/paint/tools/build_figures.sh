#!/usr/bin/env bash
# Build every paint-wing figure headless from wings/paint/models/src/figures.py (parallel).
#   wings/paint/tools/build_figures.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/paint/models/src/figures.py
OUT=wings/paint/models
LOG=${TMPDIR:-/tmp}/paint_figures
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "figure:figure" "hand:hand" "knife:knife" "swatch:swatch" "stub:stub" "ferrule:ferrule" "fragment:fragment" "study_0:study_0" "study_1:study_1" "study_2:study_2" "study_e:study_e"
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
