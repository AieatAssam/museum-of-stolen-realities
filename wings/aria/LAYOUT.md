# The Drowned Aria: layout and timings

Greybox layout for Acquisition No. 003, "Singing Gravity". All areas sit under `Areas/` in the wing scene.

## Timings

Two columns, kept apart on purpose:

- **Scripted** is measured. It is the scripted playthrough's own wing time, read from physics ticks at 120 Hz (`wings/aria/tests/playthrough.gd`, section timer). A bot walks and strikes with no reading time, so these numbers are a floor, not a playtime.
- **Estimated player** is my estimate, not a measurement. It adds reading the placards, aiming, and repeating phrases. Nothing here has been timed with a human player.

| Area | Scripted (measured) | Estimated player (not measured) |
|---|---|---|
| Foyer (demo horn, grand ramp, gallery) | 11.3 s | 2 min |
| Auditorium: brass, chord, cadence | 3.5 s | 3 min |
| Auditorium: sink well | 2.1 s | 1 min |
| Auditorium: held and carried notes | 9.4 s | 2 min |
| Pit | 6.6 s | 2 min |
| Fly-loft (fork statue) | 1.7 s | 1 min |
| Corridor (flip crossing) | 18.9 s | 3 min |
| Provenances (three) | 7.7 s | 3 min |
| Duet, La Sirena (three rounds, no mistakes) | 21.6 s | 5 min |
| Silent chandelier fall | 90.0 s | 2 min |
| Dome heist and exit | 22.6 s | 4 min |
| **Whole wing** | **about 3.5 min** | **about 26 min** |

The estimated total sits below the brief's 30 to 45 minute target. Reading every placard and a wrong-answer repeat in the duet could bring it into range, but that is not measured. The duet's wrong-answer repeat is the least certain figure, because no human has timed it.

## Areas

- **Foyer, gallery, auditorium floor**: the demo horn lifts her; the grand ramp climbs to the gallery; the route returns through the auditorium.
- **Auditorium**: horns, chord pipes, the glass cadence, the sink well, and the carried note.
- **Pit**: a ramp down; one pipe cannot reach the gantry, two together can.
- **Fly-loft**: the tuning-fork statue rings and lifts her.
- **Corridor**: flips on the downbeat; a fall in the gap sends her back to the corridor checkpoint.
- **Duet stage**: La Sirena's three rounds on the auditorium stage, with a checkpoint at the duet start.
- **Dome**: the chandelier (top at y 15, lowered to y 4 over the 90 s fall), twelve audience figures, the heist columns, the ledge, and the one exit.

## Tested and not tested

Tested by the playthrough:
- the sink well drops her, and the carried note lifts her 15 m or more from the instrument
- the breath limit on a held note
- the pit gantry needs two pipes
- the fly-loft statue lifts her
- the corridor flip window and the checkpoint respawn
- three provenances
- the duet's correct path, and one wrong answer that repeats round one with the same phrase
- the 90 s fall: free movement, heads turn, chandelier ends at y 4.00
- the heist: fragment taken, gravity stages, the climb to y 8.0, and the one exit to the atrium
- 12 placards and 12 `shot_marks` markers

Not tested:
- a late duet answer (the timeout path); only the wrong-answer path is run
- the cost of a repeat in real time, and the 60 s cap, which is a design target
- human playtime; the estimates above are not measured
- CC audio, which is not built and is deferred to a later pass

## Deviations from the brief

- The auditorium and pit sink wells sit off the required route. The Dome sink is the one on a required chord route, and the heist uses it.
- The heist gravity stages are set on the player (`Game.player.gravity_vector`), not on the wing. Gravity goes to half and then to zero.
- The fragment appears on the stage as the duet's last note ends. The exit waits until the fall has finished.
- Carried-note breath is the limit on holding: 6.0 s, draining at 1 per second while held, refilling at 1.5 per second.
- The chord lifts her to about y 14, past the ledge. Gravity is gone by then, so the exit trigger is tall: y 7 to 17.
- CC audio is not built. It is deferred to a later pass.

## Camera marks and placards

- Twelve `Marker3D` nodes in group `shot_marks`, checked by the playthrough.
- Twelve placards (I to XII). Body text runs 28 to 33 words, under the 40-word limit; one is at 28.
