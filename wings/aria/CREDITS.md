# Credits: The Drowned Aria (wings/aria)

No third-party assets are used. Nothing was downloaded; `tools/fetch_cc.sh` was not run.

## Audio
- All 19 OGG files in `audio/` are synthesized by `wings/aria/tools/gen_aria_audio.py` (original code, no samples).
  They are original works made for this project.

## Textures
- `textures/fresco`, `textures/velvet`, `textures/verdigris` are generated with the repo-root
  `tools/gen_image.sh` and converted to PBR sets with the repo-root `tools/make_pbr.py`. Original works made for this project.

## Models
- All `models/*.glb` are built from `wings/aria/models/src/*.py` (Blender headless, repo-root `tools/blender_build.sh`).
  Original geometry made for this project.

## Shared core
- Materials `gilt`, `marble_ivory`, `brass`, `ebony`, `glass` are from `assets/materials` (this project's core).
