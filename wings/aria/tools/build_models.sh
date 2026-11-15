#!/usr/bin/env bash
# Build every art-pass model from wings/aria/models/src/opera.py (parallel). Optional args: kinds to build.
#   wings/aria/tools/build_models.sh [kind ...]
set -uo pipefail
cd "$(dirname "$0")/../../.."
KINDS=("$@")
[[ ${#KINDS[@]} -gt 0 ]] || KINDS=(tier_bay panel_bay proscenium organ_case ceiling seat figure figure_head horn pipes glass_bowls fork_statue chandelier stair stair_pit balustrade wind_chest royal_box coffer_panel stave mirror stand cello backdrop rigging catwalk fragment prov_score prov_baton prov_fork)
mkdir -p wings/aria/_tmp
for k in "${KINDS[@]}"; do
  ( tools/blender_build.sh wings/aria/models/src/opera.py "wings/aria/models/$k.glb" "$k" > "wings/aria/_tmp/build_$k.log" 2>&1 || { echo "FAIL $k"; grep -E "Error|error|Traceback|line [0-9]+" "wings/aria/_tmp/build_$k.log" | tail -6; } ) &
  while [[ $(jobs -r | wc -l) -ge 8 ]]; do sleep 0.5; done
done
wait
for k in "${KINDS[@]}"; do grep -h "^TOTAL" "wings/aria/_tmp/build_$k.log" || echo "no output: $k"; done
