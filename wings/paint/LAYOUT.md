# The Unfinished Wing: layout (greybox)

Acquisition No. 001. The world is built in code (`paint.gd`) under `Areas/<Area>/...`. Each block has a `Visual` and a separate `Collision`. Strokes come from `stroke.gd`: a ribbon `Visual` plus one `Col_<n>` box per segment. The proving course sits at x=600 (`Areas/Course`); the shipped wing never routes through it.

Rule: WET PAINT. Wet strokes are rails (`surf_mode.gd`). The knife scrapes a stroke (secondary) and re-lays it (primary) as a bridge, a ramp, or a wall when she looks up.

The minutes below are a first-time player's estimate, not measured. The test bot's real-time seconds are listed for scale only, because the bot never hesitates.

| # | Area | Plays | Minutes |
|---|---|---|---|
| 1 | Shore (`Shore`) | The primed ground, the first bough, the intro card. Home for the heist. | 2 |
| 2 | Orchard (`Orchard`) | Ride bough 1. Chain boughs 1→2→3 and kick off bough 3's impasto to the Crown. Take the knife. Scrape the stray bough and lay it as a bridge to the Windfall. | 6 |
| 3 | Windfall and the Unpainted (`Windfall`, `Unpainted`) | The Old Tree and its lookout (out of reach until later). Wells. Red on the sealed blue test strip opens the niche (**swatch**). Yellow lamps bring the pencil underdrawing up to the pedestal (**stub**). | 6 |
| 4 | River of ultramarine (`River`) | Blue laid on water floats; cross on it. A blue wall across the mill inlet drains the basin; walk the bed and up its ramp. Red burns through the varnish crust. Yellow lights the cave's pencil path to the Source, which shows the outflow rail. | 8 |
| 5 | Corrections (`Corrections`) | A resting studio. Scrape the hand and its earlier pose is a ramp to a ledge (**ferrule**). Yellow across the blue hedge teaches green (optional). Red into the fixed blue barrier makes violet; it sinks and the causeway opens. | 5 |
| 6 | Pentimento (`Pentimento`) | Set-piece (see below). | 4 |
| 7 | Kinder road, green, horizon (`Horizon`) | The kinder road rides back to the Windfall. The Old Tree is blue underneath now: yellow on it grows green, so climb to the lookout. Ride the three horizon strokes 200 m west to the edge. | 5 |
| 8 | Edge and museum wall (`Edge`, `MuseumWall`) | The tacking margin. Through the staples to a ledge: the wall of the museum, a frame for every wing, and the empty Vesper frame. Lift the first stroke. | 3 |
| 9 | Heist (`Heist`) | Ride the drying stroke home (see below). | 3 |
| | **Total** | | **about 42** |

## Provenances

- **The swatch**, Windfall niche. Knowledge-gated. The test strip is fixed blue: the knife refuses it, and nothing in the Windfall says what to do. Laying red into it makes violet, which sinks and opens the niche. The rule is stated on placard 001.10 (Corrections) and shown again at the barrier (001.11). Most players will learn it there and come back. A player who already guesses the colour rule can take it on the first pass (the test does this).
- **The stub**, the Unpainted. Two yellow lays from the lamp oil well light the pencil path to the pedestal.
- **The ferrule**, Corrections. Scraping the hand reveals the earlier pose as a ramp to HandLedge.

## Checkpoints

The ids are `start`, `windfall`, `terrace`, `corrections`, `pentimento` and `edge`. Falls are safe: below y=-9, or under water, she fades and is put back on the last stroke she surfed (facing along it) or her last safe floor, in about 1.4 s. In the arena and the heist, falls go to the set-piece's own start instead.

## Set-piece: Pentimento

There is no guidance and no comment. The `pentimento` checkpoint stands at the arena mouth.

1. Six hills ring a crack where a 60 m figure stands. They are one-way umber ramps, 16 m long, rising from the rim towards the figure. They sit between the spokes, so the causeway meets the rim between two of them. They heave more with each layer.
2. Layer 1: three of the hills carry a dark seal near the crest. Ride up a hill and scrape the seal in passing (secondary), then crouch off.
3. When all three seals are gone, the layer peels. The figure sinks 7 m, the ground warms towards green, the camera shakes, and the next layer's seals appear on the other hills.
4. If a layer is left half-scraped for 90 s, its seals regrow. Peeled layers are saved and never regrow.
5. After three layers, the hills settle. The Old Tree's trunk is blue underneath now, the kinder road appears (rim → Windfall), and so does the hidden pear well.
6. Failure is a fall into the crack or off a hill. She is back at the arena mouth in about 1.5 s with peeled layers kept, so the worst case (one regrowth) costs about 1.5 minutes.

## Heist: the drying stroke

1. At the museum wall she lifts the first stroke (fragment). Every stroke she rode cracks behind her.
2. Back through the passage, heist_0 is wet and leads off the plateau. Three seconds after she boards, a drying front follows her route at 9 m/s. A stroke it reaches hardens (no longer a rail) and then falls away.
3. A branch. **Red** (heist_red_1, then a 6.8 m jump to red_2) is short and fast. **Blue** (heist_blue_1) is longer, with two varnish knots to jump.
4. heist_final has one knot. Fail to jump a knot and it knocks her off.
5. Respawn after a fall: before the branch she goes back to the heist start; after it, 12 m before the junction on heist_0. The front resets.
6. heist_final ends on the shore. Home (`_on_home`), the fragment is recorded and `finish()` returns her to the atrium.

## Weather

Weather is the painter's mood, saved as `mood`. It drifts with play: scraping sours it, laying and long chained rides lift it, falls sour it, and each Pentimento layer clears it. Sky, sun, fog and grade follow it slowly (tau 20 s).

## Shot marks

There are 12 `Marker3D` in group `shot_marks` under `ShotMarks`: shore, bough, chain, crown, unpainted, river, basin, source, corrections, pentimento, horizon, museum_wall.
