#!/usr/bin/env bash
# Concept targets for the Chitin Court art pass: one frame per area into wings/chitin/_concept/.
# Targets only; never used in game.   wings/chitin/tools/gen_concept.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/chitin/_concept
G=tools/gen_image.sh
S="first-person in-game screenshot from a premium 3D game, an insect royal court grown inside a colossal hive: architecture secreted and woven, never built; ribbed carapace vaults in deep green-black beetle shell with an iridescent blue-green-violet thin-film sheen, honeycomb wax galleries, translucent backlit amber and honey-gold wax, pale silk lines with sheen and dew, bioluminescent fungus as lamps, volumetric haze, rich readable midtones, cinematic, no people, no text."
gen() { [[ -f "$C/$1.png" ]] || $G "$C/$1.png" "$S $2"; }
mkdir -p "$C"
gen 1_gate "Arrival on a ledge before the molted outer gate: the split, hollow shed exoskeleton of a giant beetle doorkeeper stands as a two-leaf gate, translucent amber-brown husk lit from behind; beyond it a ditch 13 m wide and a single glinting silk hook hanging in warm light over the gap; honey glow ahead is the brightest point." &
gen 2_districts "A woven silk district street: walls of hexagonal wax cells glowing honey gold from within, silk awnings and hanging cocoons, a luminous light-well shaft dropping away in the floor with two brass-ringed pegs on its lips, a beetle usher in livery blocking a door, warm amber with pale silk." &
gen 3_shaft "Looking across a colossal vertical hive shaft: ribbed carapace walls fall away into darkness, three silk hooks hang in a line across the void, a balcony of chitin on the far side, high above a vast glowing amber hemisphere like a sky (an eye), dust motes, strong value contrast from bright top to black depths." &
gen 4_foundry "A clockwork foundry made of insect parts: giant gears built from mandibles and elytra, a brass track with a travelling hook over a dark channel, wax-sealed guild door with a resonant brass lock and four pegs, tallow fungus lamps, hot orange-amber key light, greenish-black shadows." &
gen 5_gallery "A long tapestry gallery: on both walls hang woven silk tapestries that are pressed flattened insect ancestors, pale silk with gold thread, iridescent wing-membrane panels, a carved chitin post wrapped in silk under a ceiling hook, soft bioluminescent fungus sconces, quiet and reverent." &
gen 6_general "A vast dark arena descending in floating chitin islands above an abyss; across it the Locksmith General, a towering armoured mantis whose forelimbs are giant ornate brass keys, stands on a dais; three glowing key-hooks hang over the void, iridescent green carapace, dramatic rim light." &
gen 7_hall "The coronation hall at the base of the shaft: a moulted empty throne on a wax dais inside an amber case, kneeling insect courtiers in a ring, an enormous pin driven through a pinned queen specimen under a glass dome, overhead a colossal amber compound eye fills the sky, golden god rays through haze." &
gen 8_heist "Escape up the hive shaft: hanging from a silk line hauled upward by a clockwork lift, the amber eye sky above now fully open and staring, courtiers below cutting lines, dramatic upward perspective, tension, warm amber over green-black." &
wait
ls -la "$C"
