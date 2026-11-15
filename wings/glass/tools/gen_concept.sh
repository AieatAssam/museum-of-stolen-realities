#!/usr/bin/env bash
# Concept targets for the art pass: one frame per area into wings/glass/_concept/ (gitignored via .gdignore-less
# raw folder; not shipped). Also the sky dome's wheel-window artwork into _raw/.
#   wings/glass/tools/gen_concept.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/glass/_concept
G=tools/gen_image.sh
S="first-person in-game screenshot, a gothic cathedral built entirely of stained glass, tall luminous figurative windows, jewel-coloured light pools thrown across a polished dark glass floor, coloured volumetric shafts in haze, black lead cames, rich readable midtones, cinematic, no people, no text."
gen() { [[ -f "$C/$1.png" ]] || $G "$C/$1.png" "$S $2"; }
mkdir -p "$C" wings/glass/_raw
gen cloister "A square cloister walk: pointed glass arcades on slender piers, four tall figurative lancets on the inner wall, a garth well lit by a single shaft from above, jewel-coloured window images printed across the glass floor." &
gen nave "Looking down a long nave: bays of tall figurative lancets on both side walls and a clerestory row above, windows filling a third of the frame, their images thrown as coloured pools across the mirror-like floor, ribbed vault in deep sapphire glass." &
gen crypt "A low crypt vault of smoky teal glass with heavy ribs, a crystal prism on a brass stand splitting a white beam into solid red and blue beams of light you could walk on, sparkles where they land." &
gen rooftops "Outside on the cathedral roof walk at dusk between glass buttresses and pinnacles; the whole sky above is one colossal leaded rose-window dome lit from outside; pressed against it, a vast soft silhouette of a human face and a hand holding a jeweller's loupe fills a third of the sky, its shadow crossing the rooftops; a small human-sized statue on the roof for scale." &
gen rose1 "A round hall whose entire far wall is one enormous rose window 16 metres across with deep stone-like tracery and individually glowing petals; her ruby, sapphire, emerald and gold petals project saturated coloured light with soft edges across the dark glass floor." &
gen rose2 "The same round hall gone completely dark; the rose window is black; the only light is a warm handheld brass lantern in the foreground casting a soft warm radius on the glass floor and small glints on the blind glass around." &
gen east "Standing before a huge east window of the choir, a figurative stained-glass scene with an empty white museum pedestal at its centre, solid beams of red and blue light converging toward it, the window's image thrown onto the floor." &
gen heist "Inside a glass reliquary chamber behind the shattered east window, dark night, a beam of golden light like a walkway stretches across a void toward an ornate empty frame on a plinth; above, the glazed sky dome with a huge looming face silhouette." &
[[ -f wings/glass/_raw/dome.png ]] || $G wings/glass/_raw/dome.png "A colossal circular medieval rose / wheel window seen straight-on, perfectly centred and filling the square image edge to edge, black background outside the circle. Radiating rings of tracery: a central boss medallion, 16 spokes, rings of pointed-lobed petals and roundels, outer ring of small trefoils. Thousands of pieces of hand-blown antique stained glass in deep cobalt, ruby, gold, emerald and violet with streaks, seeds and bubbles and uneven thickness, thick black lead cames and heavier black stone tracery, strongly backlit unevenly by sun, flat orthographic, no text." &
wait
ls -la "$C"
