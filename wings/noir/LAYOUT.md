# The Long Shadow: greybox layout

Built in `wings/noir/noir.gd`. Each area is a node under `Areas/` with StaticBody3D collision children separate from visual mesh children. Lights are SpotLight3D in group `shadow_lights`. Coordinates are approximate world positions, in metres.

Play time: not yet met. The scripted playthrough (wings/noir/tests/playthrough.gd) takes about 110 s including the 20 s colour reveal, which is a bot route, not a player. No human playtest has been timed, so the 25-minute target is unmeasured.

## Areas in order

| # | Area | Position (z) | Teaches | Checkpoint | Provenance / pickup |
|---|------|--------------|---------|-----------|---------------------|
| 1 | Alley | -2 to -21 | Shadowstep, latching onto a dark wall | alley (0, 0.05, -2) | pawn ticket at (-3.2, 1.1, -12) |
| 2 | DinerStreet | -22 to -50 | Lit lamps, the eleven-second rule (diner window silhouette at x 3.97) | street (0, 0.05, -22) | none |
| 3 | ElevatedLine | roof at x -13 to -30, y 5 | Latching across the rooftop gap between trains; train lamp cuts the path | roof (-14.5, 5.05, -29) | none |
| 4 | Plaza (in DinerStreet) | -52 to -66 | The Better Half set-piece (two figures under one lamp) | none | matchbook at (4.2, 0.6, -63) |
| 5 | Precinct | x 5.5..12.5, z -52 to -66 | Desk lamp off, swing lamp away, evidence locker | none | none |
| 6 | Cinema | -66 to -90 | Gate (opens on the key), three sweeping searchlights, the reel | cinema (0, 0.05, -68) | stub at (3.0, 1.1, -84) |
| 7 | Booth | -92 to -99.5 | Reach the projection booth, take the frame | booth (0, 0.05, -93) | fragment frame at (0, 1.2, -97) |

## Beats and objectives

- learn_dark: enter_shade (alley zone), latch_wall (alley back wall).
- cross_lit: cross_street (diner street zone at z -50.5), latch_gap (roof, across to the dark east face of the far roof at x -22.5), better_half (Better Half interactables).
- heist: dim_lamp (precinct switch, outside the room at (4.8, 1.2, -57.8)), get_key (locker, needs dim_lamp first), enter_cinema (zone at z -66.5), steal_reel (pedestal, hold 1.5 s), reach_projection (booth zone).

Provenances: pawn (alley), matchbook (plaza), stub (cinema). Fragment: booth frame, which opens the colour reveal for eleven seconds.

## Mechanics in the greybox

- Eleven-second rule: DelayedCaster (`wings/noir/delayed_caster.gd`) is the shade, sampled eleven seconds ahead. The diner window silhouette is placed at the caster's z each frame, so reading the window tells the player where the caster will be.
- Roof gap: latching onto the far roof's dark east face completes latch_gap and carries the player across (tween, 1.2 s) to the far roof. The traversal is refused while the train's lamp lights the gap (about 1.3 m window around the train's x), and a lamp that catches the player mid-air drops them back to the last dark point. Latching the far roof again carries the player back to the near roof.
- Ramp: a 10 x 3.4 m slab at 30 degrees from the street's west wall gap (z -26.8..-30.2) up to the roof at y 5, with a continuous collider. Known defect: its low corner sits about 0.2 m below street level, so the player can sink in at the foot (seen in playthrough run 28, about 20 s stall). The street lamps sit at z -40 and -48 so the ramp stays in shade.
- Checkpoints: alley, street, roof, ramp_foot, precinct, cinema, booth. A void fall below y -20 respawns at the last one.
- Gate: StaticBody3D across the cinema mouth at z -66, removed when get_key completes.

## Placards (12 max)

Eleven placards are on the `_plaque` helper plus one in the wing scene (`$Placard`, on enter). Each has title, date/medium in the heading, a catalogue number (501.1 to 501.11) and one paragraph.

## Not built

- Sedan and fire-escape models from `wings/noir/models/` are not placed.
- Audio: no third-party audio added; `CREDITS.md` unchanged.
- Known gaps: the ramp foot defect above; the enter_cinema failure in run 27 was a precinct floor hole at x 5 to 6 (fixed; run 28 passes enter_cinema). The cause of the earlier cross_street failures is not proven; it passed in runs 27 and 28. Street lamp pools eject a shadowstep player to their last dark point, which can hold a walker at a lit edge; the bot route avoids it.
