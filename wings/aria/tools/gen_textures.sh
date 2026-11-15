#!/usr/bin/env bash
# Art-pass textures: raw generations into wings/aria/textures_raw/, then PBR sets / plain maps into textures/.
#   wings/aria/tools/gen_textures.sh
set -uo pipefail
cd "$(dirname "$0")/../../.."
R=wings/aria/textures_raw
G=tools/gen_image.sh
T="Seamless square tileable texture, top-down orthographic, flat even light, no shadows, no perspective, no text:"
gen() { [[ -f "$R/$1.png" ]] || $G "$R/$1.png" "$2"; }
gen marble_teal "$T polished deep teal-green verde antico marble with fine ivory and gold veins, subtle cloudy depth, large slab, tile edges not visible." &
gen damask_ox "$T oxblood crimson silk damask wallpaper, a repeating baroque pomegranate and acanthus pattern woven tone-on-tone with a slight sheen, fine weave visible." &
gen boards "$T old dark oak stage floorboards running vertically, 12 cm wide planks, worn varnish, nail holes, scuffed by decades of performances." &
gen ornament "$T a band of carved baroque acanthus scroll ornament in gilded wood, deep relief, continuous horizontal frieze filling the whole square, tileable left to right and top to bottom." &
gen backdrop "A painted theatre backdrop canvas, flat front view filling the image: a stormy sea with towering waves under a moonlit teal sky and a distant drowned opera house on a rock, painted in broad 19th-century scenic-art brushwork in teal, oxblood and gold, canvas texture, no frame, no text." &
gen ceiling "A circular baroque ceiling fresco seen straight up from below, centred and filling the square: singers and muses in billowing robes floating among teal-green clouds around a radiant golden centre, sheets of music swirling, painted in the style of Tiepolo, deep teal and oxblood with gilt highlights, black outside the circle, no text." &
gen score "A single aged page of a handwritten opera score, flat scan filling the image: ink staves and notes, pencil markings, foxed cream paper, slightly torn edges, no title text legible." &
wait
ls -la "$R"
