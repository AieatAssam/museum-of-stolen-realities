#!/usr/bin/env bash
# Seamless source images for the noir PBR sets into wings/noir/_raw/ (gitignored), then make_pbr into
# wings/noir/textures/.   wings/noir/tools/gen_textures.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/noir/_raw
T=wings/noir/textures
G=tools/gen_image.sh
PY="${PY:-tools/.venv/bin/python}"
B="Seamless square tileable texture, top-down orthographic, flat even diffuse light, no shadows, no perspective, no text, no vignette:"
gen() { [[ -f "$R/$1.png" ]] || $G "$R/$1.png" "$B $2"; }
mkdir -p "$R" "$T"
gen brick "old soot-stained city brick wall in running bond, dark weathered bricks with varied tone, deeply recessed crumbling mortar, efflorescence streaks, about 14 courses across" &
gen asphalt "old city street asphalt, fine aggregate, cracks sealed with tar strips, worn patches, oil stains, slightly darker damp areas" &
gen cobble "granite sett cobblestones laid in tight rows, rounded worn tops, dark gaps between stones, about 10 stones across" &
gen pavement "concrete sidewalk slabs with expansion joints, chewing-gum spots, hairline cracks and grime, about 3 slabs across" &
gen roof "flat tar-paper roof with embedded fine gravel and bitumen seams, patched, dusty" &
gen floorboards "worn oak floorboards, narrow planks with nail holes, scuffs and dark gaps, institutional 1940s office floor" &
gen steel "black painted riveted steel plate with rows of round rivet heads, chipped paint, rust bloom, grime" &
gen carpet "1930s art deco cinema carpet, geometric fan pattern in two tones, worn" &
gen plaster "painted plaster wall, scuffed, faint water stains, hairline cracks, institutional" &
wait
for n in brick asphalt cobble pavement roof floorboards steel carpet plaster; do
  [[ -f "$T/${n}_albedo.png" ]] || "$PY" tools/make_pbr.py "$R/$n.png" "$T" "$n" --size 1024
done
ls "$T"
