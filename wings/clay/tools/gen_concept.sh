#!/usr/bin/env bash
# Concept targets for the clay art pass: one frame per area into wings/clay/_concept/ (targets only,
# never shipped as scenery). Skips frames that already exist.
#   wings/clay/tools/gen_concept.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/clay/_concept
G=tools/gen_image.sh
S="first-person in-game screenshot of a hand-made stop-motion claymation miniature set (Aardman / Laika quality), everything sculpted from rich saturated plasticine with visible fingerprints, thumb smears and modelling-tool marks, slightly irregular hand-built forms, soft studio key light, warm bounce, subtle shallow depth of field, cinematic, no people in the foreground, no text."
gen() { [[ -f "$C/$1.png" ]] || $G "$C/$1.png" "$S $2"; }
mkdir -p "$C"
gen meadow "Bright morning. A rolling meadow of lumpy green plasticine moss dotted with clay flowers and toadstools, a scooped-out pit of raw orange clay on the left, a small terraced knoll, a soft round mound, puffy cotton-wool clouds against a painted sky-blue backdrop flat that curves around the set; plasticine trees with ball canopies at the edges." &
gen river "Late morning. A trench across the meadow covered by a sheet of crinkled cling film that plays the river, glinting, with blue plasticine underneath; a big lumpy clay boulder on the sloping bank above it, reeds made of rolled clay snakes, a little clay footbridge stump." &
gen hill "A big lumpy plasticine hill pushed up from inside, its west face closed by a round clay plug door bearing a thumbprint the size of a door; inside, glimpsed through the opening, a dark warm domed chamber lit by one shaft of light, a crumpled scrap of cling film on the floor. Low sun, long shadows." &
gen village "Dusk. A village of unfinished clay figures whose wire armatures show through, standing in rows with open hands all facing one way, little clay cottages with warm lit windows, a wire fence across the path; violet-teal shadows and warm window light, a single taller unfinished figure holding a wooden modelling tool." &
gen workbench "Night in the animation studio. A colossal wooden workbench looming over the miniature set like a cliff, lit by one warm anglepoise lamp: open steel scissors, a glass jar full of ivory eyeballs, modelling tools, rolls of plasticine; a ramp of clay leads up to its edge; the rest of the studio falls into deep warm darkness." &
wait
ls -la "$C"
