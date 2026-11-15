# Credits: The Drowned Aria (wings/aria)

No third-party assets are used. Nothing was downloaded; `tools/fetch_cc.sh` was not run.

## Audio
- All 19 OGG files in `audio/` are synthesized by `tools/gen_aria_audio.py` (original code, no samples).
  They are original works made for this project.

## Textures
- `textures/fresco`, `textures/velvet`, `textures/verdigris` are generated with `tools/gen_image.sh`
  and converted to PBR sets with `tools/make_pbr.py`. Original works made for this project.

## Models
- All `models/*.glb` are built from `models/src/*.py` (Blender headless, `tools/blender_build.sh`).
  Original geometry made for this project.

## Shared core
- Materials `gilt`, `marble_ivory`, `brass`, `ebony`, `glass` are from `assets/materials` (this project's core).
