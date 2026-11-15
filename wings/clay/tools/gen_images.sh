#!/usr/bin/env bash
# Raw texture generations for the clay wing into wings/clay/_raw/ (not imported), then seamless PBR
# sets into wings/clay/textures/ via tools/make_pbr.py. Skips files that already exist.
#   wings/clay/tools/gen_images.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/clay/_raw
T=wings/clay/textures
G=tools/gen_image.sh
P="tools/.venv/bin/python tools/make_pbr.py"
F="Seamless square texture, top-down, flat even light, no shadows, no perspective, no text, no objects."
gen() { [[ -f "$R/$1.png" ]] || $G "$R/$1.png" "$F $2"; }
mkdir -p "$R" "$T"
gen moss "Close-up of soft green plasticine modelling clay pressed flat by hand: overlapping thumb smears, visible fingerprint whorls, small dabs and crumbs, tool scrapes, rich saturated grass green with slight lighter and darker kneaded streaks." &
gen terracotta "Close-up of raw orange-terracotta modelling clay smoothed by hand: fingerprint whorls, thumb smears, wire-tool drag lines and small gouges, slightly glossy, even saturated burnt orange." &
gen plasticine "Close-up of neutral mid-grey plasticine modelling clay worked by hand all over: dense fingerprint whorls, soft thumb smears, small modelling-tool marks, uniform colour so it can be tinted." &
gen wood "Worn pale beech workbench top seen from above: long straight grain, knife scores, pencil marks, dried blobs and smears of coloured plasticine and old paint drips, warm honey colour." &
gen film "Crinkled transparent cling film / plastic wrap laid over mid-grey card: dense random creases and wrinkles, tiny specular folds, uniform grey." &
gen canvas "A theatre backdrop flat painted in soft sky-blue scenic paint with broad visible brush strokes and soft cloud-like scumbling, uniform overall value, no clouds shapes, no horizon." &
wait
pbr() { [[ -f "$T/$2_albedo.png" ]] || $P "$R/$1.png" "$T" "$2" --size 1024 "${@:3}"; }
pbr moss clay_moss --normal-strength 3.0 --height-highpass 24
pbr terracotta clay_terracotta --normal-strength 3.0 --height-highpass 24
pbr plasticine clay_plasticine --normal-strength 3.5 --height-highpass 24
pbr wood clay_wood --normal-strength 1.5 --height-highpass 32
pbr film clay_film --normal-strength 4.0 --height-highpass 16
pbr canvas clay_canvas --normal-strength 1.0 --height-highpass 32
ls -la "$T"
