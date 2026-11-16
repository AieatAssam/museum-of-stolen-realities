class_name Wing
extends Node3D
## THE WING CONTRACT — every wing's root scene script extends this.
##
## A wing is a self-contained stolen reality living entirely in `res://wings/<id>/`.
## Copy `wings/_template/` to start; it exercises every feature below.
##
## 1. METADATA. Set `wing_id` (export) to your id. Title, numeral, acquisition no., origin, rule,
##    palette and scene path live in `res://core/wings.tres` (owned by core, read via `info()`).
##    Your root scene must be `res://wings/<id>/<id>.tscn` — the hub finds it there; until it
##    exists the hub shows the frame as "Gallery under restoration".
##
## 2. OBJECTIVES. Override `objectives()` -> Array[Dictionary], ordered:
##      {"id": "wake_suns", "title": "Wake the three suns", "hint": "optional journal hint",
##       "steps": [{"id": "east", "title": "The eastern sun"}, ...], "optional": false}
##    optional == true makes a side objective. Complete via `complete_step(obj, step)` (an objective
##    auto-completes when all its steps are done) or `complete_objective(obj)`. Progress persists
##    immediately; re-entering resumes where the player left off. Read with `Quest.is_done(...)`.
##
## 3. PROVENANCES. Override `provenances()` -> exactly 3 x {"id", "name", "line"} — hidden
##    collectibles; `line` is the placard text shown in the hub's Private Collection. Collect with
##    a `Pickup` with kind = &"provenance" (plays the shared Ceremony), or
##    `await Ceremony.provenance(node, id)`, or silently `find_provenance(id)`.
##
## 4. FRAGMENT. Override `fragment()` -> {"name", "line"}. When the wing is finished call
##    `finish()` (or a Pickup with kind = &"fragment" then `finish()`): it records the fragment,
##    plays the toast and returns to the atrium, which rebuilds Exhibit 0 by one shard.
##
## 5. LOOK. Put a WorldEnvironment in your scene (author at full quality; `Quality.apply()` switches
##    expensive features off per preset). Set `grade` (PostGrade) for the full-screen grade/grain/
##    aberration/vignette. Lights/LOD/budgets: see tools/README.md.
##
## 6. SOUND. `music_layers` = stems that loop in sync (0 = base); `music_intensity` 0..1 or call
##    `Audio.set_intensity()`. `ambience` loops. Footstep surfaces: set meta "surface" on colliders
##    (or a glTF extra "surface"); register new sets with `Audio.register_footsteps()`.
##
## 7. CHECKPOINTS. Add `Checkpoint` (Marker3D) nodes; `spawn_checkpoint` names the first one.
##    Falling below `void_height` (along up) respawns at the last checkpoint, and so does leaving
##    `bounds` in any direction (empty = the wing's solid geometry, padded; see `play_bounds()`);
##    override `on_out_of_bounds()` for a wing's own fall. Save custom puzzle
##    state by overriding `save_state()` / `load_state()` — called on every checkpoint/exit/resume.
##
## 8. PHYSICS & TIME. `gravity` (vector incl. strength) applies to the player; change it at runtime
##    with `set_gravity()`. `world_time_scale` (read `Game.world_time_scale` in your animated nodes)
##    and `player_time_scale` are independent — e.g. clay animates the world at 12 fps while
##    Vesper stays smooth.
##
## 9. MOVEMENT MODES. Override `register_modes(player)` and call
##    `player.add_mode(&"name", YourMode.new())` (extend MovementMode, see core/modes/). Built-ins:
##    walk, swim, silhouette, rail, grapple, seated. `start_mode` picks the initial one.
##    Verbs: connect `player.primary` / `player.secondary`, or handle `on_verb` in your mode.
##    Anything that holds the player (rope, pendulum, rail, ladder, ledge) extends ConstrainedMode
##    (core/modes/constrained_mode.gd): write `attach()` and `step(delta)`; jump lets go for you.
##    Demo: the zipline in wings/_template (RailMode on a Path3D, grabbed with interact).
##    Stairs need no ramp: the player steps up risers up to Player.STEP_HEIGHT (0.4 m).
##
## 10. HOOKS. `on_enter(first_time)` after the player is placed and state restored (start your
##    intro cinematic here with `Cinematics.play`), `on_exit()` before leaving.
##    Curator's placards use the museum tombstone: build a label with
##    `Placard.fields(title, date, medium, acquisition, body)` and pass it to `toast(label)` (lower-
##    left card, queued) or `Placards.read(label)` (reading view); `toast("text")` still works.
##    In-world plaques are `Placard` nodes: `$Placard.set_label(label)`. Sentence case, no dots or
##    dashes as ornament. Voice: one idea, <= 40 words, institutional deadpan, one deliberate gap.
##    Before a big reveal: `await Audio.reveal(stinger)` (music to near-silence, then stinger).
##    Camera shake: `Game.player.add_trauma(0..1)` (respects accessibility settings).
##
## 11. TESTS & CREDITS. Write `wings/<id>/tests/playthrough.gd` (extends Playthrough, ~100 lines,
##    real input only; see the template's) and run `tests/run_playthrough.sh <id>`. Add a
##    `ShotMarks` node of Marker3Ds for `tests/shots.tscn -- --wing=<id>`. Third-party files go in
##    `wings/<id>/CREDITS.md` (tools/fetch_cc.sh writes it); the end credits merge it automatically.
##    Pitfalls (freed coroutines, quitting, iCloud copies, .import files): tools/README.md §7.
##
## NEVER: edit files outside `wings/<id>/`; add autoloads; change project.godot, the input map,
## physics layer names, audio buses or core/; instance the Player yourself; call
## get_tree().change_scene*() (use `exit_to_hub()`/`finish()`); use Engine.time_scale; write to
## Save.data directly. If you need a core change, ask for it.

@export var wing_id: StringName = &""
@export var spawn_checkpoint: StringName = &"start"
@export var start_mode: StringName = &"walk"
@export var grade: PostGrade
@export var music_layers: Array[AudioStream] = []
@export_range(0.0, 1.0) var music_intensity: float = 0.0
@export var ambience: AudioStream
@export var gravity: Vector3 = Vector3(0, -15.0, 0)
@export var world_time_scale: float = 1.0
@export var player_time_scale: float = 1.0
## Respawn when the player's height along `up` drops below this.
@export var void_height: float = -40.0
## The playable volume; outside it (above, sideways, below) the player respawns. Empty: computed
## once on entry from every solid collider in the wing, padded by BOUNDS_PAD.
@export var bounds: AABB = AABB()

const BOUNDS_PAD := 15.0


# --- overridables -------------------------------------------------------------------

func objectives() -> Array[Dictionary]:
	return []


func provenances() -> Array[Dictionary]:
	return []


func fragment() -> Dictionary:
	return {}


func register_modes(_player: Player) -> void:
	pass


func on_enter(_first_time: bool) -> void:
	pass


func on_exit() -> void:
	pass


func save_state() -> Dictionary:
	return {}


func load_state(_state: Dictionary) -> void:
	pass


## Called (every physics tick, until it ends) while the player is below `void_height` or outside
## `play_bounds()`. Default: the shared fade-and-respawn at the last checkpoint.
func on_out_of_bounds() -> void:
	Game.respawn()


# --- helpers ---------------------------------------------------------------------------

## `bounds`, or (when empty) the merged box of every solid body's shapes, padded on every side.
func play_bounds() -> AABB:
	if bounds.has_volume():
		return bounds
	var box := AABB()
	var first := true
	for b: Node in find_children("*", "PhysicsBody3D", true, false):
		if not ((b as CollisionObject3D).collision_layer & 1):
			continue
		for cs: Node in b.get_children():
			if not (cs is CollisionShape3D and (cs as CollisionShape3D).shape):
				continue
			var a := (cs as CollisionShape3D).global_transform * (cs as CollisionShape3D).shape.get_debug_mesh().get_aabb()
			box = a if first else box.merge(a)
			first = false
	return box.grow(BOUNDS_PAD) if not first else AABB()


## The HUD's verb prompt (MovementMode.prompt format). Defaults to the active movement mode's;
## override for a verb that lives in the wing itself.
func verb_prompt() -> Dictionary:
	var p := Game.player
	return p.mode.prompt() if p and p.mode else {}


func info() -> WingInfo:
	return Game.registry.get_info(wing_id)


func complete_step(objective_id: StringName, step_id: StringName) -> void:
	Quest.complete_step(objective_id, step_id)


func complete_objective(objective_id: StringName) -> void:
	Quest.complete_objective(objective_id)


func find_provenance(provenance_id: StringName) -> void:
	Quest.find_provenance(provenance_id)


## Record the fragment (if a Ceremony/Pickup hasn't already) and return to the atrium.
func finish() -> void:
	Quest.collect_fragment()
	var f := fragment()
	toast(String(f.get("line", "A fragment of Exhibit 0 has been recovered.")), String(f.get("name", "Fragment")))
	await get_tree().create_timer(3.0).timeout
	if Game.wing == self and not Transitions.busy:  # the player may already have left by a door
		exit_to_hub()


func exit_to_hub() -> void:
	Game.return_to_hub()


## A placard toast: `toast("text")`, `toast("text", "Title")` or `toast(Placard.fields(...))`.
func toast(text_or_label: Variant, heading: String = "") -> void:
	Placards.toast(text_or_label, heading)


func set_gravity(g: Vector3) -> void:
	gravity = g
	if Game.player:
		Game.player.gravity_vector = g


## Persist a key in this wing's custom state (survives quitting).
func store(key: String, value: Variant) -> void:
	(Save.wing_data(wing_id)["state"] as Dictionary)[key] = value


func recall(key: String, default: Variant = null) -> Variant:
	return (Save.wing_data(wing_id)["state"] as Dictionary).get(key, default)


func find_checkpoint(id: StringName) -> Checkpoint:
	for c: Checkpoint in get_tree().get_nodes_in_group(&"checkpoints"):
		if c.id == id and is_ancestor_of(c):
			return c
	return null


func environment() -> Environment:
	var we := find_children("*", "WorldEnvironment", true, false)
	return (we[0] as WorldEnvironment).environment if not we.is_empty() else null
# Note: Game detects the Wing via SceneTree.node_added, so overriding _ready()/_process() is safe
# without calling super.