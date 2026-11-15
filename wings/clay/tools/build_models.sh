#!/usr/bin/env bash
# Build every clay model headless from wings/clay/models/src/props.py (parallel).
#   wings/clay/tools/build_models.sh [name ...]      (no names = all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/clay/models/src/props.py
OUT=wings/clay/models
LOG=${TMPDIR:-/tmp}/clay_models
mkdir -p "$LOG"
# out-name : builder args
ALL=(
  "villager_a:villager a" "villager_b:villager b" "villager_c:villager c" "villager_d:villager d" "villager_e:villager e" "unfinished:unfinished" "horse:horse" "thumb:thumb" "film:film" "fragment:fragment"
  "boulder:boulder" "river:river" "burrow:burrow" "plug:plug" "gate:gate" "bench:bench" "lamp:lamp" "apron:apron"
  "tree_a:tree 131" "tree_b:tree 137" "tree_c:tree 139"
  "flower_pink:flower pink 141" "flower_yellow:flower yellow 143" "flower_purple:flower purple 145" "flower_ivory:flower ivory 147"
  "tuft:tuft" "toadstool:toadstool" "pebble:pebble" "reed:reed" "cloud_a:cloud 191" "cloud_b:cloud 193"
  "cottage_a:cottage 201" "cottage_b:cottage 203" "backhills:backhills" "sign:sign" "plasticine:plasticine" "well:well" "cart:cart" "barrel:barrel" "washline:washline" "lantern:lantern" "hen:hen" "sunflower:sunflower" "bush:bush 231" "crumb:crumb"
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
