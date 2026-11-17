#!/usr/bin/env bash
# Build the paint landscape models headless from wings/paint/models/src/land.py (parallel).
#   wings/paint/tools/build_land.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/paint/models/src/land.py
OUT=wings/paint/models
LOG=/private/tmp/claude-501/-Users-aieat--claude-spares-spare-oxJofr/788ae2ca-fb42-43d8-942d-e0b8cc7ce803/scratchpad/paint_land
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "orchard_tree_a:orchard_tree_a" "orchard_tree_b:orchard_tree_b"
  "orchard_tree_a_lod:orchard_tree_a_lod" "orchard_tree_b_lod:orchard_tree_b_lod"
  "cypress:cypress" "hedge:hedge" "reeds:reeds"
  "house_a:house_a" "house_b:house_b" "house_c:house_c" "church:church"
  "hill_a:hill_a" "hill_b:hill_b" "hill_c:hill_c" "bank:bank"
  "torn_mass:torn_mass" "stretcher_deck:stretcher_deck" "course_land:course_land"
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
