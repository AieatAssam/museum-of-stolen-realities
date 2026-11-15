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
##    Falling below `void_height` (along up) respawns at the last checkpoint. Save custom puzzle
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
##
## 10. HOOKS. `on_enter(first_time)` after the player is placed and state restored (start your
##    intro cinematic here with `Cinematics.play`), `on_exit()` before leaving.
##    Use `toast(text)` for the Curator's placards; in-world plaques are `Placard` nodes.
##    Placard voice: one idea, <= 40 words, institutional deadpan, one deliberate gap.
##    Before a big reveal: `await Audio.reveal(stinger)` (music to near-silence, then stinger).
##    Camera shake: `Game.player.add_trauma(0..1)` (respects accessibility settings).
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


# --- helpers ---------------------------------------------------------------------------

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


func toast(text: String, heading: String = "Addendum to the catalogue") -> void:
	Placards.toast(text, heading)


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