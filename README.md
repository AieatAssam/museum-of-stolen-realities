# Museum of Stolen Realities — The Stained Glass Kingdom

A playable, high-fidelity vertical slice of one museum wing: a stolen
stained-glass cathedral reality. Third-person action-adventure in the
browser, built on Three.js with no build step.

Full six-wing concept document:
https://claude.ai/code/artifact/8511ed25-0da6-4913-9eda-c48ae3280205

## Run

```bash
npm install
python3 -m http.server 8642
# open http://localhost:8642            (Wing I — The Stained Glass Kingdom)
# open http://localhost:8642/?wing=noir  (Wing III — The Long Shadow)
# click the canvas to enter (pointer lock)
```

## Play

- **WASD** move · **mouse** look · **Space** jump (double jump in air)
- **Shift** dash · **Left click** attack · **E** interact

Objective: wake the three glass resonators, defeat the Rose Warden,
and restore the Heart Prism at the altar. Each resonator visibly
transforms the cathedral; the finale is a scripted cinematic.

## What's inside

| System | Detail |
|--------|--------|
| Environment | Procedural gothic nave: tiled stone floor with a real planar-mirror aisle (`Reflector`), colonnade with vault ribs and arches, contiguous lancet-window walls, pews, swaying banners, side chapel, west gallery reached by floating glass slabs, procedural rose window with lead tracery |
| Atmosphere | Soft-gradient god rays, fake caustic pools, 900-particle gold dust, 120 drifting glass shards (instanced), breathing window emissives, bloom postprocessing with an HDR clamp pass |
| Character | Vesper, a floating Reality Thief: layered lathe robes, luminous hem, gold circlet, vertex-waved ribbon scarf, crescent blade with anticipation/sweep swing, dash ghosts, landing squash, hover idle |
| Camera | Third-person pointer-lock orbit with wall/column occlusion clamping (`clampSegment`), FOV kicks on dash, screen shake, letterboxed cinematics, 7.5 s intro crane shot |
| Combat | The Rose Warden: instanced shard-cloud body that flares into wings when attacking, projectile volleys, dash sweeps, hit-stagger scatter, shatter death; hearts HUD, i-frames, knockback, damage vignette |
| Physics | AABB + cylinder colliders with substepped integration (no dash tunneling), raycast ground standing on any mesh (slabs, dais, ledges), void-fall respawn |
| Audio | WebAudio drone pad + synthesized chimes/hits (starts on first click) |

## Structure

```
index.html               HUD shell + import map (no bundler)
src/main.js              wing loader (?wing=glass|noir)
src/engine/core.js       renderer, composer, input, colliders, camera helpers
src/engine/flow.js       generic wing runner: intro, nodes, guardian, drops, relic, UI
src/engine/player.js     Vesper: movement, combat feel, procedural animation
src/engine/audio.js      WebAudio ambience and SFX
src/engine/textures.js   shared procedural texture factory
src/wings/glass/         Wing I — cathedral world, Rose Warden, story beats
src/wings/noir/          Wing III — noir city, the Better Half, color-flood climax
```

## Tests

```bash
SHOT_DIR=/tmp node smoke.mjs    # full flow: 3 resonators → warden → climax, fails on console errors
node physics.mjs                # wall clipping, dash tunneling, slab standing, camera occlusion, pew colliders
SHOT_DIR=/tmp node gallery.mjs  # screenshot gallery of every beat (glass)
SHOT_DIR=/tmp node noir-smoke.mjs  # full flow + screenshots for the noir wing
```

All drive headless Chrome (`puppeteer-core` + system Chrome) against the
dev server and use the `window.__game` debug hooks (`teleport`,
`activateAll`, `killWarden`, `stage`).
