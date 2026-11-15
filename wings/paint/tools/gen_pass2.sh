#!/usr/bin/env bash
# Art pass 2 image sources into wings/paint/_raw/ (Codex image generation, never shipped raw):
# the Pentimento portrait and the earlier compositions under it, the linen-and-pencil void, the
# gallery parquet. Then the gallery's other wings, taken from their own concepts.
#   wings/paint/tools/gen_pass2.sh       (skips files that already exist)
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/paint/_raw
G=tools/gen_image.sh
gen() { [[ -f "$1" ]] || $G "$1" "$2"; }
mkdir -p "$R"
O="An oil painting photographed flat and square-on, filling the whole frame, no frame, no wall, no text."
gen $R/portrait.png "$O A half-scraped oil portrait: head and shoulders of a seated young woman in three-quarter view, confident academic draughtsmanship, warm umber underpainting with grey-green dead colour and touches of flesh tone in the face and hands, the background and edges scraped back with a palette knife so bare canvas and fragments of earlier coloured layers show through, unfinished, luminous, Sargent and Zorn." &
gen $R/earlier_harbour.png "$O An earlier painting abandoned and half scraped away: a harbour with moored fishing boats and a stone quay in faded blues and ochres, palette-knife scrapes cutting across it, bare canvas showing, loose." &
gen $R/earlier_house.png "$O An earlier painting abandoned and half scraped away: a red-roofed farmhouse among green hills under a yellow sky, thick strokes partly scraped back to canvas with knife marks, loose and sketchy." &
gen $R/earlier_still.png "$O An earlier painting abandoned and half scraped away: a still life of a jug, lemons and a white cloth on a table in violet and lemon, scraped back in broad knife sweeps to the canvas, loose." &
T="seamless square texture, top-down orthographic, flat even light, no shadows, no perspective, no text, edge to edge."
gen $R/linen_pencil.png "$T Raw unprimed linen canvas weave, warm beige-grey, with loose graphite pencil underdrawing lines over it: contour lines of hills, a winding path, the outline of trees, construction lines and hatching, faint, sketchy." &
gen $R/parquet.png "$T Polished antique oak parquet floor in a herringbone pattern, warm honey and brown planks, satin varnish, subtle grain." &
wait
# the other five wings hang in the gallery as themselves (from their own concepts)
P=tools/.venv/bin/python
for pair in aria:auditorium chitin:2_districts clay:village glass:cloister noir:street paint:shore; do
  w=${pair%%:*}; f=${pair#*:}
  [[ -f wings/paint/textures/gallery_$w.jpg ]] || $P -c "
from PIL import Image; im=Image.open('wings/$w/_concept/$f.png').convert('RGB'); im.thumbnail((1024,1024)); im.save('wings/paint/textures/gallery_$w.jpg', quality=88)"
done
ls -la "$R" wings/paint/textures/gallery_*
