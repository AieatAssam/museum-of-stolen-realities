#!/usr/bin/env bash
# Art-pass targets for the Unfinished Wing: one concept frame per area into wings/paint/_concept/
# (never shipped), plus raw texture sources into wings/paint/_raw/ for tools/make_pbr.py.
#   wings/paint/tools/gen_concept.sh          (skips files that already exist)
set -uo pipefail
cd "$(dirname "$0")/../../.."
C=wings/paint/_concept
R=wings/paint/_raw
G=tools/gen_image.sh
S="first-person in-game screenshot of a 3D world that is the inside of an unfinished oil painting, everything made of thick oil paint: heavy impasto ridges with visible bristle tracks, wet glossy strokes catching highlights, palette-knife slabs, translucent glazes, shadows that shift hue to violet and blue rather than grey, painterly like Van Gogh and Sorolla, rich saturated midtones, cinematic, no people, no text, no UI."
gen() { [[ -f "$1" ]] || $G "$1" "$2"; }
mkdir -p "$C" "$R"
gen $C/shore.png "$S A luminous painted seashore at morning: a broad plateau of creamy lead-white primed ground in thick knife strokes, a single huge ribbon of wet ultramarine paint (a brushstroke as thick as a log) runs from the foreground out over a void into the picture, sky of swirling warm cream and cerulean strokes, sea of dashed blue strokes below." &
gen $C/orchard.png "$S An orchard where every tree is a single sweeping brushstroke: twisted umber trunks of ridged paint, crowns of dabbed viridian, sap and yellow daubs; three wet ultramarine ribbons of paint arc away over a dark linen void like rails, each a step lower; blossoms flicked in white; warm afternoon." &
gen $C/windfall.png "$S A golden knoll under an ancient tree painted in heavy umber over an earlier blue, a small sealed niche of fixed blue paint in a wall of dry gesso, small glossy puddles of pure red, yellow and blue paint like wells on the ground, warm late light." &
gen $C/unpainted.png "$S The unpainted part of the canvas: bare raw linen weave in dim shadow, loose graphite pencil underdrawing lines of trees and a path floating in the air, lit only by a warm pool of yellow lamplight from a glowing puddle of cadmium yellow paint, everything outside the light a deep umber gloom." &
gen $C/river.png "$S A river of pure wet ultramarine paint, swirling glossy horizontal strokes with white highlights, a little rowing boat painted in broad strokes, a terrace of cream knife-laid paint, a wooden watermill painted loosely on the far bank, sky of high blue and apricot strokes." &
gen $C/source.png "$S A low cave of dark raw canvas and charcoal smudges, a varnish crust of cracked amber resin across the way, a single glowing pencil-line path leading to a radiant well of pure blue pigment at the back, warm lamplight from a yellow paint puddle." &
gen $C/corrections.png "$S A painter's abandoned studio inside the painting: half-scraped figures in umber with earlier white poses showing through scraped paint, a giant painted hand, a blue hedge stroke, a barrier of blue paint across a causeway, easel and palette, placards on posts, soft north light, quiet resting mood." &
gen $C/pentimento.png "$S A vast circular arena where several layers of old paintings show through scraped paint, six ramps of umber paint rising toward a 60 metre ghostly standing figure painted in flesh tones and grey that sinks into a crack, dark red seals on the ramps, dramatic stormy sky of swirling grey and violet strokes, hints of green showing through." &
gen $C/horizon.png "$S High above the painted world on three long horizontal ribbons of wet blue paint that form the horizon line, stretching far into the distance under a vast sky of thick swirling cloud strokes in cream, peach and cobalt; below, the orchard, river and fields as dabs of colour." &
gen $C/museum_wall.png "$S Seen from inside a painting, looking out past the gilded edge of its frame and the canvas tacking margin with staples: an enormous dim museum gallery wall in dark plaster with huge gilt frames hanging, one frame empty; the painted world ends in a ragged edge of brushstrokes and bare canvas, the museum in cool grey shadow." &
gen $C/heist.png "$S Racing along a long ribbon of wet blue paint that dries and cracks to grey behind, a red branch splitting off, amber varnish knots on the stroke ahead, the luminous shore far below at golden hour, the sky darkening with the painter's mood into violet strokes." &
# texture sources (seamless, flat, no perspective)
T="seamless square texture, top-down orthographic, flat even light, no shadows, no perspective, no text, edge to edge."
gen $R/impasto.png "$T Thick oil paint impasto in a single warm white, dense overlapping short directional brushstrokes all running roughly left to right with deep bristle grooves and raised ridges, like a Van Gogh surface, neutral colour so it can be tinted." &
gen $R/stroke.png "$T One long horizontal band of thick wet oil paint dragged by a wide bristle brush, parallel bristle grooves running exactly left to right across the whole image, glossy ridges, neutral pale grey so it can be tinted, no gaps." &
gen $R/knife.png "$T Palette-knife painted oil surface, broad flat smeared slabs of thick paint with sharp ridged edges where the knife lifted, neutral off-white." &
gen $R/canvas.png "$T Raw unprimed linen canvas weave, close-up, fine regular warp and weft threads, warm beige with slight slubs, flat." &
gen $R/gesso.png "$T Lead white gesso primer brushed onto canvas, faint brush marks and canvas weave showing through, creamy warm white." &
gen $R/varnish.png "$T Old yellowed amber picture varnish with fine craquelure crack network, glossy resin, warm honey colour with darker cracks." &
gen $R/pencil.png "$T Graphite pencil hatching and loose sketch lines on raw canvas, beige ground, grey diagonal hatches." &
gen $R/gilt.png "$T Antique water-gilded gold leaf on a carved frame surface, fine craquelure, worn red bole showing at the edges of leaf squares." &
gen $R/plaster.png "$T Old painted museum wall plaster, warm grey-green distemper, very subtle trowel marks." &
gen $R/sky.png "A wide oil painting of a sky only, no land, no horizon: swirling impasto cloud strokes in cream, peach, apricot and cobalt blue, thick visible brushstrokes, Van Gogh and Constable cloud studies, luminous, flat lighting, no text, fills the frame." &
gen $R/sky_storm.png "A wide oil painting of a stormy sky only, no land: swirling heavy grey, violet and slate brushstrokes with streaks of dirty ochre light, thick impasto, angry painter's mood, no text, fills the frame." &
wait
ls -la "$C" "$R"
