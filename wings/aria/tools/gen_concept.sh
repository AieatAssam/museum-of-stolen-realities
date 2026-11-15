#!/usr/bin/env bash
# Concept targets for the art pass: one frame per area into wings/aria/_concept/ (never shipped in-game).
#   wings/aria/tools/gen_concept.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/aria/_concept
G=tools/gen_image.sh
S="first-person in-game screenshot, Unreal-quality real-time render: a baroque opera house drowned in luminous teal haze where gravity is sung; deep teal and oxblood palette with warm gilt highlights, red velvet, carved gilt mouldings, floating sheet music and small debris drifting in the air, faint concentric standing-wave patterns (cymatics) in the dust and water, volumetric light shafts, readable midtones, cinematic, no people, no text, no UI."
gen() { [[ -f "$C/$1.png" ]] || $G "$C/$1.png" "$S $2"; }
mkdir -p "$C"
gen foyer "The grand foyer: a wide marble ramp-stair climbing to a gallery landing with a gilt balustrade, marble pilasters and gilt-framed panels on oxblood damask walls, two warm crystal chandeliers, at the ramp foot a bronze caryatid holding a glowing brass horn on a plinth, sheet music hanging in the air above it." &
gen auditorium "The flooded auditorium from the stalls: a horseshoe of three tiers of opera boxes with curved gilt balustrades and oxblood velvet interiors, a huge gilt proscenium arch with a heavy oxblood curtain swagged open, the floor drowned in still dark water to the second row with velvet seats half submerged, concentric ripple rings radiating from brass organ pipes and glass bowls standing in the water, a crystal chandelier hanging above, shafts of teal light." &
gen pit "The orchestra pit under the stage: low dark room of black-lacquered wood and brass, abandoned music stands and a cello on its side, two tall brass organ pipes on a wooden wind-chest, a steel gantry above, puddles reflecting teal light from a grate, circular cymatic patterns traced in dust on the floor, a few lamps glowing amber." &
gen corridor "The scored corridor: a long gilt-panelled backstage passage with five brass stave lines running along both walls like a musical staff, a broken gap in the floor dropping into darkness, chairs and music stands stuck to the ceiling as if gravity flipped, pages of a score drifting in mid-air, mirrors in gilt frames, rhythmic amber wall sconces." &
gen flyloft "The fly-loft high above the stage: a timber gridiron and catwalks, hundreds of hemp ropes and sandbags, enormous painted backdrop canvases of a seascape hanging in the dark, a tall verdigris bronze tuning-fork statue on a pedestal glowing faintly, a small loft organ, a single warm work lamp, dust motes." &
gen dome "The rotunda under a painted baroque dome fresco of clouds and singers: a colossal crystal-and-gilt chandelier hangs at the centre, a ring of twelve pale drowned audience figures seated in velvet chairs looking up at it, gilt ribbed walls with organ pipes rising behind, concentric rings of standing-wave light on the marble floor, a high ledge as the only exit." &
wait
ls -la "$C"
