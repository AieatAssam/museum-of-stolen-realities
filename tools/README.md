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
tools/godot_import.sh                    # creates .import files (and strips iCloud copies, below)
python3 tools/fix_imports.py             # applies the rules below, deletes stale imports
tools/godot_import.sh                    # re-imports with the rules
```

Commit every `.import` file next to its asset (fonts included). A fresh clone without them fails to
parse any script that `preload`s the asset on its first import.

### iCloud conflict copies

The repo lives in an iCloud-synced folder. iCloud sometimes writes conflict copies such as
`title 2.gd` or `project 2.godot`. A copy of a script that declares `class_name` registers the same
class a second time, and Godot's global class cache (`.godot/global_script_class_cache.cfg`) can end
up pointing `Wing`, `Placard` and others at the stale copy. Symptoms: "Could not find base class",
or old behaviour after an edit.

**Always import with `tools/godot_import.sh` (not `$G --import`).** It runs the headless import,
then `tools/strip_conflict_copies.py`, which removes every cache entry whose file or folder name
ends in ` 2`, ` 3`, and so on. The copies are not deleted, because they may hold someone's work.
Compare them by hand, then remove them. `.gitignore` already ignores them.
`python3 tools/strip_conflict_copies.py --test` runs its self-check. `tests/run_smoke.sh` calls the
wrapper first.

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
- **Every downloaded file gets a row in a CREDITS table.** Shared assets go in `/CREDITS.md`. A
  wing's own files (`wings/<id>/...`) go in `wings/<id>/CREDITS.md`.
- `core/credits.gd` (`Credits.rows()` / `Credits.cards()`) merges every table. CC-BY rows and the
  typefaces appear on the in-game credits card at the end of the game.

Good sources:

| Source | What to use |
|---|---|
| freesound.org | Filter licence to CC0 / Attribution |
| opengameart.org | Check each file's licence |
| Free Music Archive | CC-BY tracks only |
| incompetech | Kevin MacLeod, CC-BY |
| Sonniss GDC bundles | Royalty-free. Not CC, so these also need a CREDITS row and the owner's OK |

Download with the helper. It refuses other licences and writes the CREDITS row in the right table:

```sh
tools/fetch_cc.sh <direct file url> assets/audio/cc/<name>.ogg "<title>" "<author>" "<source page url>" CC-BY-4.0
tools/fetch_cc.sh <direct file url> wings/<id>/audio/<name>.ogg "<title>" "<author>" "<source page url>" CC0-1.0
python3 tools/fix_imports.py && $G --headless --path . --import
```

- **Format:** convert to `.ogg` (`ffmpeg -i in.wav -c:a libvorbis -q:a 5 out.ogg`) before
  committing.
- **Keep the source page URL** so the licence can be re-checked later.

## 7. Tests

```sh
tests/run_smoke.sh                       # headless core regression; exit 1 on any failed check, script error or leak
tests/run_playthrough.sh <wing_id>       # headless: wings/<id>/tests/playthrough.gd played by real input
$G --path . --resolution 1920x1080 tests/shots.tscn -- --wing=<id> [--ui] [--secs=4]   # windowed
$G --path . --resolution 2560x1440 tests/ui_shots.tscn -- --out=<name>                  # windowed
```

**`smoke`** (`tests/smoke.gd`) covers:

- New game from the title, the intro skipped, then walking into the Conservation door with real
  input. Then the template wing: a lamp via E, a void respawn, the fragment, and back.
- **Hardening regressions:**
  - a goto during a transition queues;
  - leaving mid-cinematic clears the bars, card and skip label and restores input;
  - a 40-word toast sits in the lower left and hides under the reader;
  - the stairs (0.18 m and 0.35 m risers) are climbed by walking, with camera speed under 15 m/s (a snapped riser reads ~42).
- Each exhibit wing via the debug API. A missing scene must fail gracefully. Then all six
  fragments and both finales.

**Wing playthroughs.** Extend `Playthrough` (`core/playthrough.gd`) in
`wings/<id>/tests/playthrough.gd` and write `run()`. The helpers are:

- `enter`, `walk_to`, `jump_across`, `use(node, hold_secs)`, `look_at`, `tap`, `hold`;
- `until(cond, timeout, "what")`, `check`, `frames`, `seconds`, `skip_cinematics`.

They steer with real input events. The test gets a throwaway save. `wings/_template/tests/playthrough.gd`
is the example: about 100 lines that complete the whole wing.

**`shots`** (`tests/shots.gd`) works on one wing per run.

- **Marks.** Every `Marker3D` under the wing's `ShotMarks` node is a mark. The camera sits on the
  marker and looks down its -Z. The player's view is also shot.
- **UI.** The HUD, placards and cinematic overlays are hidden unless you pass `--ui`.
- **Output.** `shots/<wing>/<mark>.png`, and one `[perf]` line per mark with avg/p95/p99 ms of:
  - **frame**: wall time per frame, which is what the player feels;
  - **cpu**: render-thread CPU time to record the frame;
  - **gpu**: GPU time from timestamp queries.
- **Reading the numbers.** On macOS/Metal the GPU timestamps read 0, so `gpu` prints
  "n/a (driver)". Read `frame - cpu` as the GPU-bound share. Vsync is switched off, but the macOS
  compositor can still pace a windowed run to the display (~16.7 ms at 60 Hz). To find headroom,
  run fullscreen or compare marks.

**`ui_shots`** captures every UI surface (title, settings, HUD and toast, prompt, plaques, reader,
cinematic card, pause, journal, credits) to `shots/ui_<name>/`.

Look at every PNG before calling visual work done. `shots/` is git-ignored.

### Known pitfalls

- A coroutine whose node is freed never resumes. `await` on a wing node after a scene change
  silently drops the rest of the function. Don't keep core state in such a function.
- Never `get_tree().quit()` directly. Use `Game.quit(code)`, which waits out the transition and
  stops audio; otherwise you get "ObjectDB instances leaked".
- `Game.debug_goto`, `enter_wing` and `return_to_hub` queue behind a running transition and return
  `bool`. Use `await` and check the result.
- A newly added font or texture needs its `.import` committed (see §3).
- A stale class cache from iCloud copies causes "Could not find base class". Re-run
  `tools/godot_import.sh`.
- `Label3D` has no `centered`. Position it by its alignment instead (left/top hangs from the origin).
- Rails grabbed at an end always ride into the rail.
- In headless tests, frame pacing is uneven. Count physics ticks (`Engine.get_physics_frames()`)
  instead of wall time when a check depends on distance walked.

### Debug API (console, tests)

| Call | What it does |
|---|---|
| `Game.debug_goto(id)` | Go to a wing |
| `Game.debug_complete_objective(wing, obj)` | Complete one objective |
| `Game.debug_complete_wing(wing)` | Completes objectives, provenances and the fragment |
| `Game.debug_teleport(pos, look_at)` | Move the player |
| `atrium.start_finale(&"restore" \| &"break")` | Start an ending |
