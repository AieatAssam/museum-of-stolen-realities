#!/usr/bin/env bash
# Art pass: the nave's story lancets (each re-leaded with an empty museum pedestal) and the onlooker
# silhouette for the sky. Raw generations go to wings/glass/_raw/ (gitignored).
#   wings/glass/tools/gen_story.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/glass/_raw
G=tools/gen_image.sh
L="A single tall narrow Gothic lancet stained-glass window with a pointed arch top, filling the full image height and exactly the central third of the image width; everything outside the lancet is pure flat black. Medieval 13th-century stained glass in the style of Chartres: LARGE bold pieces of glass (each piece big and simple, about one twentieth of the window height), thick black lead came outlining every piece, grisaille brush-painted faces and drapery folds, deep saturated translucent cobalt blue, ruby red, gold and emerald glass as if strongly backlit by the sun. Flat frontal orthographic view, no frame, no wall, no text, no border. The figures are hieratic and stylised. Somewhere in the scene, conspicuously re-leaded in plain off-white glass, stands an ordinary modern museum display pedestal, empty."
gen() { [[ -f "$R/$1.png" ]] || $G "$R/$1.png" "$2"; }
mkdir -p "$R"
gen story_1 "$L Scene: glaziers on ladders raising a great golden sun on a tall pole above a small cathedral city made of glass; the empty white pedestal stands in the street below where a king should stand." &
gen story_2 "$L Scene: a young queen being crowned under three suns (gold, red, blue); courtiers kneel; the empty white pedestal stands beside her throne." &
gen story_3 "$L Scene: peasants carrying long beams of coloured light on their shoulders like timber across a river, walking on a bridge made of light; the empty white pedestal stands on the far bank." &
gen story_4 "$L Scene: the queen in a violet mourning veil weeping over an empty bier; mourners with violet veils; where the king's body should lie stands the empty white pedestal." &
gen story_5 "$L Scene: an enormous hand reaching down out of a starry blue sky holding a round magnifying loupe over tiny kneeling townspeople who look up in fear; the empty white pedestal stands among them." &
gen story_6 "$L Scene: saints being lifted out of their windows by giant tongs, leaving white pedestals in their places; a bishop points in alarm." &
gen story_7 "$L Scene: a sun-king in gold robes holding a blazing golden sun in both hands above his head, golden rays on a cobalt background; the empty white pedestal at his feet." &
gen story_8 "$L Scene: a ladder of light climbing through a tower of glass; small glaziers climb it carrying panes; the empty white pedestal at the top of the ladder." &
gen onlooker "Pure black silhouette on a pure white background, centred and filling most of the frame: a colossal human head seen in three-quarter profile, leaning down and forward as if peering into a display case, with one hand raised to the eye holding a round jeweller's loupe; the loupe lens is a clean white circle; shoulders visible at the bottom. Smooth soft edges, absolutely no interior detail, no text, no texture, just a flat black shape on flat white." &
wait
if [[ ${1:-} == cloister ]]; then
  gen cloister_1 "$L Scene: glass-blowers at a furnace blowing a glowing sun-coloured bubble of glass; apprentices carry panes; the empty white pedestal stands by the furnace." &
  gen cloister_2 "$L Scene: a glass orchard where gardeners pick fruit of coloured light from leaded trees; the empty white pedestal stands under the tallest tree." &
  gen cloister_3 "$L Scene: monks in a cloister copying light into books, each page a small pane; the empty white pedestal stands on the lectern." &
  gen cloister_4 "$L Scene: a queen and king walking hand in hand across a bridge of light over a dark river, small glass birds above; the empty white pedestal stands at the end of the bridge." &
  wait
fi
ls -la "$R"
