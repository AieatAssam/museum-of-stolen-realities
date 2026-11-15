# Design rules

Binding for the hub and every wing. Distilled from research on loops, feel,
reward and atmosphere. Numbers are starting values to tune by playtest; most
are practitioner defaults, not measured findings.

## 1. Wing structure (target 30–45 min; length follows beats, never padding)

| Min | Beat | Must contain |
|---|---|---|
| 0–3 | Arrival | Hook image. One safe, wordless demo of the wing's rule. First landmark pulling forward. |
| 3–10 | Introduce | The rule in one controlled space. Objective 1. Provenance A visible but not yet reachable. |
| 10–18 | Develop | 2–3 escalating uses of the rule. Objective 2. Provenance B needs the rule plus a piece of knowledge. |
| 18–21 | Rest | No fail states. Environmental story, placards, a view. Provenance C can live here. |
| 21–28 | Twist | The set-piece: the rule inverted or turned on the player, light time pressure. No HP-sponge combat. |
| 28–34 | Recombine | Objective 3 returns to an earlier area with knowledge gained since. Lock-and-key payoff. |
| 34–40 | Heist | Take the Fragment; escape with the rule under pressure; one clear exit. |
| 40–44 | Resolution | One-take return to the atrium. The hub visibly changes. |

- One verb per wing, fully explored. The twist recombines the rule; it never adds a new mechanic.
- Teach by room, not by text. No tutorial popups, no waypoint arrows, no quest markers.
- Navigate by landmark, light, contrast and leading lines. The intended path is the brightest or most saturated thing in view.
- The impossible rule stays consistent so the player can model it, then is broken exactly once.
- At least one wing-wide puzzle is gated by knowledge, not by an unlock.
- Let the player choose the order of objectives where the space allows.
- A failure never costs more than ~2 minutes. Checkpoint before every set-piece.
- No vast flat empty areas. Every space has a focal point and repeated small-scale motifs.

## 2. Reward cadence

- Every state-changing action: acknowledged in under 1 s (sound + light + small motion).
- Every 60–120 s: something changes (a clue, a room state, a new sightline).
- Every 10–20 min: an objective closes. Every wing: 3 Provenances, 1 Fragment.
- Each objective keeps two open questions alive, each answerable within minutes.
- Show a reward before it can be reached, then reveal the route.
- Progress is world state, never points, scores, percentages or tally popups.
- No variable-ratio rewards, streaks, fake scarcity, or fanfare longer than ~10 s. Repeated ceremonies shorten after the third.
- Spend the budget on the last minute of a wing: one clear peak using a mastered skill, then a quiet image.

**Provenance pickup:** stinger + 0.2 s world-audio duck → object lifts, camera holds ~1 s, no popup → one in-world placard line → later placed in the hub alcove, with one visible hub change.

**Fragment:** ambience drops 2 s → fragment revealed → carried out → the Exhibit 0 sphere fills with new light and sound (the peak) → quiet closing image that poses a new question.

## 3. Feel

- Input to motion within one frame. Curved acceleration: fast attack, longer release.
- Coyote time ~100 ms. Jump buffer ~100 ms. Corner and ledge correction.
- Interaction feedback is layered: 60–120 ms anticipation → impact → reaction → settle.
- Shake uses the trauma model (displacement = trauma², decay ~0.5/s). Light hits barely shake.
- Pickup and landing squash ≤ 10–15%. Strafe roll 1–3° on a spring. Default FOV ~90.
- UI motion 200–300 ms decelerate; 400–500 ms for emphasised moments.
- Camera is never locked longer than necessary; the player can look around during set-pieces.
- Head bob, FOV kick, shake and roll are separately adjustable, with a Reduced Motion preset. A motion effect is never the only signal.

Per verb:
- **Lightwalking:** beams read as solid — snap onto the surface, generous edge forgiveness, a hum that rises in pitch on contact.
- **Reshaping:** smooth deformation falloff, a 2–4 frame hitch at the peak of a pull, sound lands on the peak.
- **Shadowstepping:** fast and flat; speed effects in short bursts only.
- **Singing gravity:** gravity shifts ease in like tides, never snap; lean into swim direction, roll under 5°.
- **Silkspinning:** physical pull that keeps momentum; lines wrap around posts; release at the top of the arc is rewarded.
- **Wet paint:** speed builds on entry and bleeds slowly; tight jump arcs off rails.

## 4. Wonder

Reveal recipe, used for every jaw-drop:
1. Decide the single conclusion the player should reach.
2. Compress: low, narrow approach, one leading line, destination hidden.
3. Occlude the view entirely for a few seconds (door, fog, corner).
4. Release into the vast space with a human-scale object beside the enormous thing.
5. Near-silence for 3–5 s, then the stinger. Camera stays free.
6. One focal point, one readable placard, 5–8 s before anything forces movement.

- Colour is scripted by value first, then hue; each wing has a light–dark arc.
- Story is assembled from the scene ("what happened here?"), not told.
- Mysteries share one thread and are resolved; no dangling threads for their own sake.

## 5. Placards (the Curator's only voice)

- One idea, 40 words or fewer.
- Institutional and deadpan. Never a villain's speech.
- Provenance and condition, not moral.
- One deliberate gap or contradiction for the player to notice.
- Same format everywhere: title, catalogue number, date.
- The tone shifts slightly with each wing's medium.

## 6. Audio

- Vertical stems per area (drone, texture, motif) driven by proximity and discovery.
- Horizontal changes only at transitions, on bar boundaries.
- One leitmotif per wing, re-orchestrated as the wing progresses.
- Stingers are for true discoveries only.
- Strip music 3–5 s before every reveal. Silence is a tool.
- Reverb decay scales with room size.
- Prefer real Creative Commons recordings and music over synthesis. CC0 or CC-BY only; every file is logged in `CREDITS.md` (path, title, author, URL, licence) when added, and CC-BY items appear in the in-game credits.
