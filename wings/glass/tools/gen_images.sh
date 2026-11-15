#!/usr/bin/env bash
# Generates the Vitrine Kingdom's raw images (windows, rose, seamless glass) into wings/glass/_raw/.
#   wings/glass/tools/gen_images.sh [batch]   batch = windows | seamless | all (default all)
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/glass/_raw
G=tools/gen_image.sh
L="A single tall narrow Gothic lancet stained-glass window, pointed arch top, filling the full image height and only the central third of the width; everything outside the lancet is pure flat black. Medieval stained glass with thick black lead came outlining every piece, hand-painted grisaille detail on faces, rich translucent saturated colour as if strongly backlit by sunlight, flat frontal orthographic view, no frame, no wall, no text, no border."
S="Seamless tileable square texture, flat frontal orthographic, even flat light, no shadows, no perspective, no text, no border."
gen() { [[ -f "$R/$1.png" ]] || $G "$R/$1.png" "$2"; }
B="${1:-all}"
if [[ $B == windows || $B == all ]]; then
gen win_ruby "$L Subject: a hieratic standing female saint in deep ruby-red robes with a gold halo, hands raised lifting a small golden sun above a kneeling crowd of tiny glass figures; background of cobalt blue diamond quarries and gold stars." &
gen win_azure "$L Subject: a hieratic standing male saint in cobalt-blue robes with a gold halo, pouring a stream of light from a jug into a river where glass fish swim; background of ruby red and gold quarries with small emerald leaves." &
gen win_verdance "$L Subject: a hieratic standing female saint in emerald green robes with a gold halo, holding a sprouting vine that becomes a ladder of light; background of cobalt blue and ruby quarries with gold suns." &
gen win_east "A huge Gothic stained-glass east window: three tall pointed lancets under one large pointed arch with tracery roundels, flat frontal orthographic view, filling the whole image, pure black outside the window outline. Thick black lead came, richly saturated translucent glass in cobalt blue, ruby red, gold and emerald, backlit. Subject: a royal procession of hieratic haloed glass figures kneeling toward the centre where, conspicuously, an ordinary plain white modern museum pedestal stands empty beneath three suns. No text, no frame." &
gen win_rose "A circular Gothic rose stained-glass window, perfectly centred, filling the frame edge to edge, pure black outside the circle. Sixteen radiating petal panels and an outer ring of small roundels, thick black lead came, translucent saturated cobalt blue, ruby red, gold and emerald glass, strongly backlit. In the central roundel a hieratic grieving queen in a violet veil and gold crown, head bowed, hands over her face, tears of gold glass. Flat frontal orthographic view, no text." &
gen win_history "$L Subject: three hieratic crowned kings and queens with halos raising three suns (gold, red and blue discs) on tall poles over a cathedral city made of glass; deep blue background with gold stars." &
wait
fi
if [[ $B == seamless || $B == all ]]; then
gen glass_wall "$S Medieval stained glass: irregular small hand-cut pieces of translucent cobalt blue and deep indigo glass with occasional ruby and gold pieces, every piece outlined by thick matte black lead came, slight streaks and bubbles in the glass." &
gen glass_floor "$S Floor of thick antique glass tiles set in a grid of broad black lead came: square and diamond tiles of dark bottle-green, smoky blue and amber glass, worn and slightly frosted, small bubbles." &
gen glass_gold "$S Medieval stained glass: irregular hand-cut pieces of translucent amber, honey gold and pale straw glass with a few ruby pieces, thick matte black lead came between every piece, streaks and seeds in the glass." &
gen glass_quarry "$S Leaded diamond quarry glazing: a regular lattice of diamond-shaped panes of pale greenish clear antique glass with faint painted gold quatrefoil in each, thick black lead came lattice." &
gen glass_crypt "$S Medieval stained glass: irregular hand-cut pieces of very dark emerald green and midnight blue glass with a few violet pieces, thick matte black lead came between every piece, cloudy, dim." &
gen glass_red "$S Medieval stained glass: irregular hand-cut pieces of translucent ruby red and crimson glass with a few gold pieces, thick matte black lead came between every piece, streaks and bubbles." &
wait
fi
ls -la $R
