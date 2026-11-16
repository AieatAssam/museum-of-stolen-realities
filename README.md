# Museum of Stolen Realities

A first-person game in Godot 4.7 (Forward+). The player is Vesper, a Reality Thief recovering
fragments of her own world from a museum outside time. The Curator never speaks; it comments only
through museum placards.

## Structure

The game starts in the title screen (`ui/title.tscn`) and then enters the hub, the atrium
(`hub/atrium.tscn`). The atrium is a rotunda of six frames, one per wing. Each wing is a
self-contained world in one art medium, built around one physics rule. Finishing a wing recovers
a fragment for Exhibit 0, and the hub changes as wings are recovered.

| Wing | Title | Rule | Verb |
|---|---|---|---|
| `wings/glass` | The Vitrine Kingdom | Lightwalking | Aim a heliostat so its beam reaches the target. |
| `wings/clay` | The Pinched Forest | Reshaping | Pull, press and scoop clay to reshape the terrain. |
| `wings/noir` | The Long Shadow | Shadowstepping | Move only where no light reaches the head. |
| `wings/aria` | The Drowned Aria | Singing Gravity | Sound instruments to add acceleration to gravity. |
| `wings/paint` | The Unfinished Wing | Wet Paint | Scrape paint from the world, lay it as bridges and walls. |
| `wings/chitin` | The Chitin Court | Silkspinning | Pluck and swing on silk strands. |

Wing ids, titles and rules are listed in `core/wings.tres`. The registry is `core/wing_registry.gd`.
A wing is a `Wing` node (`core/wing.gd`) with its own scene; `wings/_template/` is a worked
example of every contract feature.

Core systems live in `core/`: scene flow and checkpoints (`game.gd`), scene transitions
(`transitions.gd`), audio (`audio.gd`), placards and cinematics, quests and ceremonies, save data
(`save.gd`), and the player and movement modes (`core/player/`, `core/modes/`). Hub code is in
`hub/`, and menus and HUD in `ui/`.

## Running

Requires Godot 4.7.2 (the project is set up for the macOS editor at
`/Applications/Godot.app`).

```sh
/Applications/Godot.app/Contents/MacOS/Godot --path .
```

To import assets and refresh the script class cache without running the game, use:

```sh
tools/godot_import.sh
```

This is a headless import that also removes iCloud conflict copies (such as `foo 2.gd`) from the
class cache. Prefer it over a bare `--import`.

## Tests

- `tests/run_smoke.sh` runs the whole-game smoke test (`tests/smoke.tscn`). It exits 0 only if the
  test passes and the log has no script errors or unexpected leaks.
- `tests/run_playthrough.sh <wing>` runs a scripted playthrough of one wing, for example
  `tests/run_playthrough.sh glass`. Each wing's playthrough is in `wings/<wing>/tests/`.
- `res://tests/e2e.tscn` is the end-to-end test. Run it with
  `Godot --headless --verbose --path . res://tests/e2e.tscn`.
- Screenshots and frame timings: `Godot --path . --resolution 2560x1440 tests/shots.tscn -- --wing=<id>`.
  The UI is hidden unless `--ui` is passed. Shots accept `--off=` toggles (fog, ssr, ssao, glow,
  msaa, sphere, shadows) for performance comparisons. `tests/ui_shots.tscn` captures the interface.

## Tools

The asset pipeline is documented in `tools/README.md`.

- `tools/blender_build.sh` builds a `.glb` from a Blender Python build script, headless.
- `tools/gen_image.sh` generates an image from a prompt into a PNG (raw output goes to
  `assets/_raw/`, which Godot does not import).
- `tools/godot_import.sh` runs the headless import described above.

Python helpers for textures, audio and the Blender build live in `tools/` as well, with their
requirements in `tools/requirements.txt`.

## Godot AI addon

`addons/godot_ai` is enabled in `project.godot`. It connects the editor to an external assistant
over a local server. The plugin is disabled in headless mode.

## Credits and design

- `CREDITS.md` lists the third-party assets and their licences. Each wing keeps its own
  `CREDITS.md` for the files it uses.
- `docs/DESIGN_RULES.md` holds the rules for wing structure, reward, feel and text that the hub and
  every wing follow.
