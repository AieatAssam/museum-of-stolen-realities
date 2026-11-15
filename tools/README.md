# Asset pipeline and test harness

Godot 4.7 (Forward+). Paths are from the repo root. Godot binary on macOS:
`G=/Applications/Godot.app/Contents/MacOS/Godot`.

One-time setup:

```sh
python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt
brew install vorbis-tools   # oggenc, for gen_audio.py
```

## 1. Images (Codex image generation)

```sh
tools/gen_image.sh assets/_raw/gilt.png "Seamless square texture, top-down, even light: antique water-gilded gold leaf over gesso, fine craquelure, tiny leaf seams, no shadows, no perspective"
```

This runs `codex exec --skip-git-repo-check -s read-only -C <tmp> --json "<brief>"`. It reads the
thread id from the JSON stream and copies `~/.codex/generated_images/<thread_id>/*.png`. Each run
takes about 45 s and returns a 1254x1254 PNG. Runs are independent, so start several with `&` and
`wait`.

- Raw generations go in `assets/_raw/` (it has a `.gdignore`, so Godot never imports them).
- **Texture briefs:** "seamless, top-down, flat even light, no shadows, no perspective, no text".
- **UI / title briefs:** state the composition and where the empty space for text goes.

## 2. Seamless PBR sets

```sh
tools/.venv/bin/python tools/make_pbr.py assets/_raw/gilt.png assets/textures/gilt gilt --size 1024
tools/.venv/bin/python tools/make_pbr.py noise:7 assets/textures/plaster plaster --tint e9e3d3
```

- **Output:** `<name>_albedo/_normal/_roughness/_height.png`. Normals use the OpenGL convention
  (+Y), which is what Godot expects.
- **How it tiles:** a four-way, variance-preserving offset blend. Check for seams by tiling the
  albedo 2x2 in any viewer.
- **Knobs:** `--normal-strength`, `--height-highpass` (removes baked lighting), `--rough-min`/`--rough-max`, `--rough-invert`.
- **Materials** live in `assets/materials/<name>.tres` (StandardMaterial3D, world triplanar by
  default). A wing's own materials live in `wings/<id>/materials/`.

## 3. Import conventions

After adding PNGs:

```sh
$G --headless --path . --import          # creates .import files
python3 tools/fix_imports.py             # applies the rules below, deletes stale imports
$G --headless --path . --import          # re-imports with the rules
```

| File | Import |
|---|---|
| `*_albedo`, `*_roughness`, `*_height`, anything under `textures/` | VRAM compressed, mipmaps |
| `*_normal` | VRAM compressed as a normal map (RGTC), mipmaps |
| `ui/`, fonts | Lossless, no mipmaps |

## 4. Models (Blender, headless only)

Never open the Blender GUI for project work. Many people build in parallel and every build must be
reproducible from a script.

```sh
tools/blender_build.sh hub/models/src/frame.py hub/models/frame.glb
# = blender --background --factory-startup --python-exit-code 1 \
#     --python tools/blender/export.py -- hub/models/src/frame.py hub/models/frame.glb
```

**Writing a build script.** It defines `build(args)` and creates objects into an empty scene.
Helpers in `tools/blender/kit.py`: `material`, `box`, `lathe`, `sweep_closed`, `torus`, `tube`,
`join`, `duplicate`, `collision_box`.

**What the export does.** It applies modifiers and transforms, cube-projects missing UVs (1 UV unit
= 1 m), prints the triangle count per object and exports GLB (+Y up). It fails if the total goes
over `MOSR_MAX_TRIS` (default 60000).

**Units and facing.** 1 unit = 1 m, +Z up in Blender. An object that faces −Y in Blender faces +Z in
Godot.

**Node-name suffixes** (Godot import hints):

| Suffix | Result |
|---|---|
| `-convcolonly` | Invisible convex collider (preferred for props) |
| `-colonly` | Invisible trimesh collider |
| `-col` | Mesh plus trimesh collider |
| `-convcol` | Mesh plus convex collider |

**Material names are the contract.** Blender shading is ignored. `MaterialLib.instance(path)`
swaps each surface for `assets/materials/<name>.tres`. A wing can override this by passing its own
directory first: `MaterialLib.apply(node, ["res://wings/<id>/materials", MaterialLib.CORE_DIR])`.

**Custom properties** export as glTF extras, so they arrive as node meta. For example,
`obj["surface"] = "carpet"` drives footsteps.

### Texel density and budgets

| | Target |
|---|---|
| Architecture (walls, floor, columns) | 256–512 px/m (marble floor: 2048 px over 8.3 m ≈ 250 px/m; triplanar materials at `uv1_scale` 0.35 with 1024 px ≈ 360 px/m) |
| Hero props seen within 1 m (placards, frames, plinths) | ~1024 px/m |
| Texture size | 1024 by default; 2048 only for large hero surfaces (the atrium floor) |
| Triangles per model | ≤ 60k, enforced. The atrium kit is 0.5k–16k per model |
| Triangles per wing on screen | ≤ 1.5M |
| Dynamic lights | 1–2 shadowed lights per view. Use volumetric fog energy on lights instead of extra geometry |
| Frame time | 60 fps at 1440p on the default (`high`) preset. Measure with `tests/shots.gd`, which reports it |

## 5. Audio

`tools/.venv/bin/python tools/gen_audio.py` synthesises the core and hub set (beds, ambience,
stingers, UI, footsteps `step_<surface>_N.ogg`) into `assets/audio/`. Music beds are vertical stems
that loop in sync (`Audio.play_music([...])`, with `set_intensity` fading upper stems in).

## 6. Sourcing CC assets (sounds and music first)

The owner's rule:

- Use Creative Commons material where it beats synthesis, especially sound and music.
- **CC0 and CC-BY only.** No NC, no SA, no ND, no "free for personal use".
- **Every downloaded file gets a row in `/CREDITS.md`.**
- CC-BY rows are shown automatically on the in-game credits card. The atrium reads `CREDITS.md`
  at the end of the game.

Good sources:

| Source | What to use |
|---|---|
| freesound.org | Filter licence to CC0 / Attribution |
| opengameart.org | Check each file's licence |
| Free Music Archive | CC-BY tracks only |
| incompetech | Kevin MacLeod, CC-BY |
| Sonniss GDC bundles | Royalty-free. Not CC, so these also need a CREDITS row and the owner's OK |

Download with the helper. It refuses other licences and writes the CREDITS row:

```sh
tools/fetch_cc.sh <direct file url> assets/audio/cc/<name>.ogg "<title>" "<author>" "<source page url>" CC-BY-4.0
python3 tools/fix_imports.py && $G --headless --path . --import
```

- **Format:** convert to `.ogg` (`ffmpeg -i in.wav -c:a libvorbis -q:a 5 out.ogg`) before
  committing.
- **Keep the source page URL** so the licence can be re-checked later.

## 7. Tests

```sh
tests/run_smoke.sh                                   # headless; exit 1 on any failed check or script error
$G --path . --resolution 2560x1440 tests/shots.tscn  # windowed real render; PNGs to shots/, frame times to stdout
```

**`smoke`** covers:

- New game, then the intro, which it skips.
- Walking into the Conservation door with real input.
- The template wing: a lamp via E, a void respawn, the fragment, then back.
- Each exhibit wing via the debug API. A missing scene must fail gracefully.
- All six fragments, then both finales.

**`shots`** covers:

- The title, the full intro, and the atrium at named camera marks (`MARKS` in `tests/shots.gd`;
  add yours there).
- The fragment-fill ceremony, THE THIEF stages, the alcove and the template wing.
- Frame times, measured with vsync off: average, p95, p99, max and GPU ms (`[perf]` lines).

Look at every PNG before calling visual work done.

### Debug API (console, tests)

| Call | What it does |
|---|---|
| `Game.debug_goto(id)` | Go to a wing |
| `Game.debug_complete_objective(wing, obj)` | Complete one objective |
| `Game.debug_complete_wing(wing)` | Completes objectives, provenances and the fragment |
| `Game.debug_teleport(pos, look_at)` | Move the player |
| `atrium.start_finale(&"restore" \| &"break")` | Start an ending |
