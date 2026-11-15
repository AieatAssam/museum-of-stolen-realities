# Greybox pass (wing builders)

Your wing is now built in two stages. You do stage 1. A separate art team does stage 2 on top of
your work, so do not spend time on looks.

## Stage 1 — complete, playable greybox (you)

Goal: the WHOLE wing playable start to finish in simple untextured geometry, 30–45 minutes long,
with every mechanic real and every beat of docs/DESIGN_RULES.md §1 present.

First: `git merge main` (core fixes landed; if tests/smoke.gd conflicts, take main's version).

Build, in this order, verifying each with your playthrough test before starting the next:
1. Every area in the wing's brief, connected, at final scale and layout. Simple boxes/CSG/primitive
   meshes are correct here. Give every piece of geometry a clear node name and group it per area
   (`Areas/<AreaName>/...`) so artists can replace it. Keep collision separate from visuals.
2. The verb's three escalations, each taught by a room and then tested by a harder one.
3. All 3 objectives with sub-steps, wired to Quest. All 3 Provenances, hidden but fair.
4. The set-piece, fully scripted and playable (logic, timing, fail and retry), using placeholder shapes.
5. The Fragment heist and escape, then the return to the atrium.
6. Checkpoints before every hard part. No failure costs more than ~2 minutes.
7. Every placard written (≤40 words, institutional deadpan, one gap or contradiction each),
   at least 12 per wing, placed where the story needs them.
8. Audio: source real CC0/CC-BY music, ambience and SFX (the owner has authorised these downloads),
   wire them in, and list each in `wings/<id>/CREDITS.md`.
9. Named camera marks (Marker3D in group `shot_marks`) at the 12 best viewpoints, for the art team.

Mark placeholder visuals with flat, distinct colours per function (walkable, hazard, interactive,
goal) so the layout reads at a glance.

## Done means
- `wings/<id>/tests/playthrough.gd` completes the whole wing through real use of the mechanic,
  collects all 3 Provenances, and exits 0. Run it twice.
- `tests/run_smoke.sh` passes.
- `wings/<id>/LAYOUT.md`: a short map — areas in order, what the player does in each, minutes each
  takes, where the Provenances and checkpoints are, and what the set-piece and heist do beat by beat.
- Committed on your worktree branch. Not pushed.

## Report (under 300 words)
Minutes of play per area; what works by test; what does not; anything you could not build.
