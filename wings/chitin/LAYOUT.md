# The Chitin Court: layout

Acquisition No. 340. Rule: **Silkspinning**. Primary (fire/let go) swings on a line; secondary
weaves a line between two anchors (tightrope or zip) or plucks one (signal, distract, call a moth,
open a resonance lock). Everything is built in `chitin.gd` `_ready()` under `Areas/<Area>`.
Axes: x east, y up. Gravity 15 m/s². Physics 120 Hz.

## Minutes (honest)

"Bot" is measured game time of `tests/playthrough.gd` (it knows the answers and never misses).
"Player" is an estimate for a first visit, reading placards; nobody has played it by hand yet.

| Area | Bot | Player (est.) | What happens |
|---|---|---|---|
| Molted outer gate | 5.5 s | 2 min | First swing over a 13 m gap. A walk-off fall returns her to the ledge in 1.07 s. |
| Silk districts | 22.9 s | 5 min | Pluck to move the usher; weave and walk the light-well tightrope; pluck the harp to call a moth, swing up to the perch (Provenance: finger-bell). |
| Abyssal hive shaft | 18.7 s | 4 min | Three chained swings without touching ground to the balcony; pick the top hook, step off, weave the zip mid-fall and ride it to the foundry. |
| Clockwork foundry / locksmiths' guild | 35.8 s | 7 min | Swing from a clockwork anchor on a 20 s track; vault opens to a 6 m line (Provenance: guild key, knowledge-gated); guild door to an 8 m line. |
| Tapestry gallery | 16.2 s | 3 min | No-fail wrap practice post; Provenance: tapestry hem. |
| Locksmith General | 30.5 s | 5 min | Set-piece (below). |
| Coronation hall | 29.4 s | 4 min | Processional stair, curtain, the eye reveal, case opened by the court standard, fragment. |
| Heist | 42.1 s | 4 min | Lift, cut line, lift to the rim (below). |
| **Total** | **3.4 min** | **~34 min** | |

## Provenances

1. **bell**: the finger-bell, on the high perch in the districts (77.5, 0, -8.5). Reached by calling a moth.
2. **guild_key**: inside the vault (99, -31, 67). Knowledge-gated: the vault placard says only
   "Tuned to the queen's span."; the six-metre span is on the tailors' quarter placard in the districts.
   Weave 6 m between the vault pegs (1 to 3) and pluck. Wrong lengths do nothing.
3. **tapestry**: the gallery's far corner (66, -31, 98).

## Checkpoints

start (gate), districts, rim (district edge of the shaft), balcony, foundry, guild, gallery,
general (arena ledge, before the set-piece), hall (foot of the stair), heist (the dais; set on taking
the fragment). Ordinary falls skip checkpoints: `_fall()` fades 0.25 s and puts her back on the last
ledge she stood on (`silk.last_safe`). In the arena and heist a fall resets that sequence.

## Set-piece: the Locksmith General

1. Walk onto the arena ledge (z 96..99.5). The gallery gate shuts behind her; intensity 0.6.
2. **Phrase 1** (12 s): one anchor, key 1 (40, -21, 90). Hold the key's line 0.5 s to turn it; land on island 1.
3. **Phrase 2** (16 s): anchor A2 then key 2. Holds lock at half the phrase each; land on island 2.
4. **Phrase 3** (20 s): A3a, A3b, key 3, landing on the General's dais (a three-swing chain).
5. Win: all keys turned, the General's forelimbs lock, the stair gate and gallery gate open.
6. Failure: a fall resets the arena and respawns at checkpoint `general`, a few metres from the start zone.
   The whole duel is 48 s of phrases, so a failure costs under a minute.

## Jaw-drop: the amber sky blinks

Built with the reveal recipe: compress (80-riser processional stair, 3.5 m ceiling, one amber thread),
occlude (curtain; `Audio.reveal` ducks to near-silence), release into the 70 m shaft base under the amber
hemisphere, stinger, then 3.5 s later the sky blinks: it is the empress's compound eye. It blinks every
9 s after. She is pinned under a dome labelled "Queen (type specimen)"; the court stands "at rest".

## Heist beat by beat

1. Weave the hall pegs (8 m, the court standard), pluck: the case lifts. Take the fragment.
2. Courtiers turn to face her; intensity 1.0; checkpoint heist.
3. Fire at lift 1 (100, -58, -22), hanging west of the dais. It hauls her up 38 m and over to ledge H1; let go.
4. The courtiers' cut line (102, -25, -22) is up 4.5 s, cut 1.5 s. Swing it to H2.
5. Fire at lift 2: up through the shaft to y 10, over to the rim; let go on the rim. `finish()`.
6. A fall resets both lifts and respawns at the dais.

## Swing numbers (silk_mode.gd)

Analytic pendulum, gravity 15, grip 1.0 m above the feet. Aim cone 14° half-angle, 32 m range, visible
highlight on the picked anchor. Reel 5 m/s (angular momentum kept). Band governor keeps the apex
55..78° (acts within 50° of the bottom, 16 m/s²). Top-release flick +5 up, +3 along when slow near
the apex. Hop 4 m/s on a ground fire; a ground fire starts taut and never longer than the floor allows.
Mantle up to 1.4 m, ledge magnet 6 m/s², walk-mode coyote time. Wraps on `silk_posts`. Zip catch
1.2 m from feet to above the grip, on lines sloped over 6°. Max 4 woven lines, weave range 26 m,
pluck radius 0.9 m within 16 m, pitch 8/length. Locks keep (remove) the line they open to.

Gate (`tests/swing_course.tscn`, three chained swings then a landing, randomised release and delay
jitter): 159/160 across seeds 340, 1, 2, 3 at fixed 120 fps; earlier 40/40 in real time.

## Audio

One leitmotif (congusbongus, "Cathedral in the forest", CC0) in three stems that loop in sync; all
sources and licences in CREDITS.md. Derived with:

```bash
#!/usr/bin/env bash
# derive_audio.sh <dir with downloaded sources> <swishes dir>; ffmpeg filters, oggenc encode
set -euo pipefail
A="$1"; SW="$2"
cd "$A"
T="$(mktemp -d)"
mk() {  # mk <in> <filter or -> <out.ogg>
	if [[ "$2" == "-" ]]; then ffmpeg -v error -y -i "$1" -ar 44100 "$T/x.wav"
	else ffmpeg -v error -y -i "$1" -af "$2" -ar 44100 "$T/x.wav"; fi
	oggenc -Q -q 4 -o "$3" "$T/x.wav"
}
mk src_cathedral_in_the_forest.ogg "lowpass=f=500,volume=1.4" chitin_stem_bed.ogg
mk src_cathedral_in_the_forest.ogg "highpass=f=900,volume=1.6" chitin_stem_motif.ogg
mk src_cathedral_in_the_forest.ogg "bandpass=f=300:width_type=o:w=1.5,tremolo=f=2:d=0.8,volume=1.8" chitin_stem_pulse.ogg
mk src_meadow_thoughts.ogg "atrim=0:7,afade=t=in:d=0.05,afade=t=out:st=4.5:d=2.5,aecho=0.8:0.7:120|300:0.4|0.25" stinger_eye.ogg
mk src_guitar_strum.ogg "atrim=0:1.6,afade=t=out:st=1.0:d=0.6" pluck.ogg
mk "$SW/swish-3.wav" - line_fire.ogg
mk "$SW/swish-9.wav" - swing_release.ogg
mk "$SW/swish-12.wav" "asetrate=44100*0.4,aresample=44100,volume=2" eye_blink.ogg
rm -rf "$T"
```

Intensity: 0 outside, 0.6 in the General's duel, 0.2 after, 1.0 in the heist.
