# Credits: The Long Shadow (noir)

No third-party files are used. Everything in this wing was made for this project.

## Audio (synthesized, original)

| File | Source | Licence |
|---|---|---|
| `audio/noir_bed.ogg` | `audio_src/gen_audio.py` (pads and drone) | Project original |
| `audio/noir_pulse.ogg` | `audio_src/gen_audio.py` (heartbeat, thumps, brushed hats) | Project original |
| `audio/noir_strings.ogg` | `audio_src/gen_audio.py` (harmonic pads and melody) | Project original |
| `audio/noir_rain.ogg` | `audio_src/gen_audio.py` (filtered noise and droplets) | Project original |

Generator: `audio_src/gen_audio.py` (numpy synthesis, encoded to Ogg Vorbis with `oggenc -q 4`).

## Models (Blender, original)

| File | Source script |
|---|---|
| `models/streetlamp.glb` | `models/src/streetlamp.py` |
| `models/searchlight.glb` | `models/src/searchlight.py` |
| `models/sedan.glb` | `models/src/sedan.py` |
| `models/figure.glb` | `models/src/figure.py` |
| `models/detective_seated.glb` | `models/src/detective_seated.py` |
| `models/fire_escape.glb` | `models/src/fire_escape.py` |
| `models/marquee.glb` | `models/src/marquee.py` |

Built with the project kit at `tools/blender_build.sh`. Project original, no third-party meshes or textures.
