#!/usr/bin/env bash
# Rebuild the noir art-pass models headless:  wings/noir/tools/build_models.sh [part ...]
# Each part is "<script>:<part>" from wings/noir/models/src/; with no args, builds everything.
set -uo pipefail
cd "$(dirname "$0")/../../.."
SRC=wings/noir/models/src
OUT=wings/noir/models
ALL=(
  city:facade_a city:facade_b city:facade_c city:facade_low city:back_door city:fire_escape city:diner_front city:neon_eat
  city:trash_can city:crate city:manhole city:hydrant city:bench city:shopfront city:curb city:lamp_bracket
  city:newsstand city:crate_stack
  el:el_bent el:el_span el:el_car el:water_tower el:chimney el:roof_vent el:roof_hatch el:parapet el:skyline_block
  interior:desk interior:desk_lamp interior:chair interior:file_cabinet interior:locker interior:blind_window
  interior:hanging_lamp interior:switch_box interior:wainscot interior:door_frame
  interior:seat_block interior:proscenium interior:curtain interior:pilaster interior:balcony interior:pedestal_reel interior:cinema_gate
  interior:projector interior:film_shelf interior:port_window
  interior:pawn_ticket interior:matchbook interior:stub interior:frame_stand
  interior:typewriter interior:telephone interior:coat_stand interior:wall_clock interior:pinboard
  interior:frosted_door interior:ceiling_fan interior:ceiling_fan_blades
  figure:figure figure:figure_b figure:figure_woman figure:detective_seated
)
PARTS=("${@:-${ALL[@]}}")
fail=0
for pp in "${PARTS[@]}"; do
  s="${pp%%:*}"; part="${pp#*:}"
  if ! tools/blender_build.sh "$SRC/$s.py" "$OUT/$part.glb" "$part" > "/tmp/noir_build_$part.log" 2>&1; then
    echo "FAIL $pp"; tail -15 "/tmp/noir_build_$part.log"; fail=1
  else
    echo "ok   $pp  $(grep TOTAL "/tmp/noir_build_$part.log" | cut -d' ' -f2) tris"
  fi
done
exit $fail
