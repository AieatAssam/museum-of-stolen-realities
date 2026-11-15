#!/usr/bin/env bash
# Concept targets for the noir art pass: one frame per area into wings/noir/_concept/. Targets only,
# never used in game.   wings/noir/tools/gen_concept.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/noir/_concept
G=tools/gen_image.sh
S="first-person in-game screenshot at eye height, 1940s film-noir American city at night, near-monochrome black and white with deep blacks that still hold detail, wet asphalt and cobbles with real mirror reflections of lights, hard key lights and very long cast shadows, drifting steam and low fog, light film grain, a single neon sign as the only colour accent, cinematic, premium game art, no text, no people unless stated."
gen() { [[ -f "$C/$1.png" ]] || $G "$C/$1.png" "$S $2"; }
mkdir -p "$C"
gen alley "A narrow brick alley after rain: fire escapes zig-zag up both walls, steam from a manhole, trash cans and wooden crates, one bare bulb over a back door throwing a cone of light, a dark brick back wall at the end, the exit to a lit street glowing beyond on the right, puddles mirror the bulb." &
gen street "A diner street: on the right a long diner window glowing warm white with venetian-blind stripes thrown across the wet pavement, a red neon tube sign (no letters legible), cast-iron streetlamps making hard pools, a parked 1940s sedan, a man in a fedora walking away while his long shadow on the pavement is somewhere else, ahead of him, as if it left eleven seconds early." &
gen rooftops "On tar-paper rooftops at night beside an elevated railway on steel trestles; a lit train with a bright headlamp crossing above, water towers and chimneys silhouetted against a hazy sky glow, a gap between two buildings with a taller dark brick wall across it, wet roof gravel reflecting the train." &
gen plaza "A small cobbled square: one streetlamp throws a single hard pool of light; two figures in trench coats and hats stand under it facing each other, but their two shadows on the cobbles stand apart, one shadow walking away; shuttered shops, a bar matchbook on a bench, mist." &
gen precinct "Inside a 1940s police precinct office at night: venetian blinds slicing moonlight into hard stripes across a wooden desk with a green-shaded desk lamp, filing cabinets, a steel evidence locker, a swinging bare bulb on a cord, wired glass door with blank lettering, cigarette smoke in the light beams." &
gen cinema "Inside a derelict picture palace: rows of velvet seats, ornate plaster proscenium, three carbon-arc searchlights sweeping hard beams through smoke across the auditorium, a film reel on a pedestal in the aisle, the screen glowing faintly; the beams are the only bright shapes." &
gen booth "A cramped projection booth: two big carbon-arc projectors with film reels, a beam of light shooting through a small port window into smoke, film cans on shelves, one film frame on a stand glowing in faint colour, the only colour in the image." &
wait
ls -la "$C"
