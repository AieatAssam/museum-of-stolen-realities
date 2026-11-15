extends Node
## Game autoload: run state, scene flow (title / atrium / wings), player spawning, checkpoints,
## pause/journal, and the debug API used by tests.

signal wing_entered(wing_id: StringName)
signal wing_left(wing_id: StringName)
signal state_changed(state: State)

enum State { TITLE, PLAYING, PAUSED, CINEMATIC, TRANSITION }

const HUB_ID := &"atrium"
const HUB_SCENE := "res://hub/atrium.tscn"
const TITLE_SCENE := "res://ui/title.tscn"
var MUSEUM_PALETTE := PackedColorArray([Color("c8a35a"), Color("3a2c18"), Color("0e0c09")])
const MUSEUM_MEDIUM := 6

var registry: WingRegistry = preload("res://core/wings.tres")
var state: State = State.TITLE
var player: Player
var wing: Wing
var checkpoint_id: StringName = &""
var world_time_scale: float = 1.0
var player_time_scale: float = 1.0
## Where the player arrives in the atrium next time (frame id they came back through).
var arrival: StringName = &""

var _hud: CanvasLayer
var _menu: CanvasLayer


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Style.apply_theme()
	get_tree().auto_accept_quit = false  # window close goes through quit() (clean audio shutdown)
	get_tree().node_added.connect(_on_node_added)
	Quest.fragment_collected.connect(func(_w: StringName) -> void: Save.save_game())


func _on_node_added(n: Node) -> void:
	if n is Wing and n.get_parent() == get_tree().root:
		register_wing.call_deferred(n)


func set_state(s: State) -> void:
	state = s
	var capture := s == State.PLAYING and not DisplayServer.get_name() == "headless"
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if capture else Input.MOUSE_MODE_VISIBLE
	state_changed.emit(s)


# --- flow ----------------------------------------------------------------------------

## All scene flow below returns true once the player stands in the destination, false if it could
## not get there (missing/broken scene). Calls made during a transition wait for it to finish and
## then run (a repeat request for the scene that transition just reached returns true at once).
func new_game() -> bool:
	await _idle()
	Save.new_game()
	arrival = &""
	return await _go(HUB_SCENE, MUSEUM_PALETTE, MUSEUM_MEDIUM)


func continue_game() -> bool:
	await _idle()
	if not Save.load_game():
		return await new_game()
	var cp: Dictionary = Save.data["checkpoint"]
	var path := String(cp.get("scene", ""))
	if path == "" or not ResourceLoader.exists(path):
		path = HUB_SCENE
	var info := _info_for_scene(path)
	return await _go(path, info.palette if info else MUSEUM_PALETTE, info.portal_medium if info else MUSEUM_MEDIUM)


func enter_wing(id: StringName) -> bool:
	var info := registry.get_info(id)
	if info == null or not info.scene_exists():
		Placards.toast("This gallery is under restoration. The Curator asks for your patience; it has a great deal of it.", "Gallery closed")
		return false
	if await _idle() and _at(info.scene_path):
		return true
	arrival = id
	Save.data["checkpoint"] = {"scene": info.scene_path, "id": ""}
	return await _go(info.scene_path, info.palette, info.portal_medium)


func return_to_hub() -> bool:
	if await _idle() and _at(HUB_SCENE):
		return true  # dedupe: e.g. the exit door firing during finish()'s own return to the hub
	if wing:
		arrival = wing.wing_id
	Save.data["checkpoint"] = {"scene": HUB_SCENE, "id": ""}
	return await _go(HUB_SCENE, MUSEUM_PALETTE, MUSEUM_MEDIUM)


## Wait out a running transition. Returns true if it had to wait.
func _idle() -> bool:
	var waited := Transitions.busy
	while Transitions.busy:
		await get_tree().process_frame
	return waited


func _at(path: String) -> bool:
	return wing != null and wing.scene_file_path == path


func quit_to_title() -> void:
	await _idle()
	_save_wing_state()
	Save.save_game()
	_close_menu()
	set_state(State.TRANSITION)
	player = null
	wing = null
	await Transitions.change_scene(TITLE_SCENE, MUSEUM_PALETTE, MUSEUM_MEDIUM, _free_hud)
	Audio.stop_music()
	set_state(State.TITLE)


func _go(path: String, palette: PackedColorArray, medium: int) -> bool:
	await _idle()
	if not ResourceLoader.exists(path):
		push_error("Game: no scene at %s" % path)
		return false
	_close_menu()
	var old_wing := wing
	var old_player := player
	if wing:
		_save_wing_state()
		wing.on_exit()
		wing_left.emit(wing.wing_id)
	Save.save_game()
	var old_state := state
	set_state(State.TRANSITION)
	if player:
		player.input_enabled = false
	player = null
	wing = null
	if not await Transitions.change_scene(path, palette, medium):
		# broken scene (parse error etc.): stay where we were
		wing = old_wing
		player = old_player
		if is_instance_valid(player):
			player.input_enabled = true
		set_state(old_state)
		return false
	# register_wing runs (deferred) as the scene enters the tree; wait for it.
	while wing == null and get_tree().current_scene is Wing:
		await get_tree().process_frame
	return wing != null and wing.scene_file_path == path


func _info_for_scene(path: String) -> WingInfo:
	for w in registry.wings:
		if w.scene_path == path:
			return w
	return null


# --- wing registration ------------------------------------------------------------------

func register_wing(w: Wing) -> void:
	wing = w
	var id := w.wing_id
	var first: bool = not Save.data["wings"].has(String(id))
	Save.wing_data(id)
	Quest.begin(id, w.objectives(), w.provenances(), w.fragment())
	world_time_scale = w.world_time_scale
	player_time_scale = w.player_time_scale

	player = Player.new()
	w.add_child(player)
	player.gravity_vector = w.gravity
	w.register_modes(player)
	player.set_mode(w.start_mode)

	var resume_cp := StringName(Save.data["checkpoint"].get("id", ""))
	if Save.data["checkpoint"].get("scene", "") != w.scene_file_path:
		resume_cp = &""
	checkpoint_id = resume_cp if resume_cp != &"" else w.spawn_checkpoint
	var cp := w.find_checkpoint(checkpoint_id)
	if cp == null:
		cp = w.find_checkpoint(w.spawn_checkpoint)
	if cp:
		player.teleport(cp.global_transform)
	w.load_state((Save.wing_data(id)["state"] as Dictionary).duplicate(true))

	var env := w.environment()
	Quality.apply(env)
	if not Save.settings_changed.is_connected(_reapply_quality):
		Save.settings_changed.connect(_reapply_quality)
	Post.apply(w.grade if w.grade else PostGrade.new(), 0.0)
	if not w.music_layers.is_empty():
		Audio.play_music(w.music_layers, 4.0, w.music_intensity)
	Audio.play_ambience(w.ambience)

	_ensure_hud()
	set_state(State.PLAYING)
	wing_entered.emit(id)
	w.on_enter(first)


func _reapply_quality() -> void:
	if wing:
		Quality.apply(wing.environment())


# --- checkpoints & respawn ------------------------------------------------------------------

func set_checkpoint(id: StringName) -> void:
	checkpoint_id = id
	if wing == null:
		return
	Save.data["checkpoint"] = {"scene": wing.scene_file_path, "id": String(id)}
	_save_wing_state()
	Save.save_game()


func _save_wing_state() -> void:
	if wing:
		var st: Dictionary = Save.wing_data(wing.wing_id)["state"]
		st.merge(wing.save_state(), true)


var _respawning: bool = false

func respawn() -> void:
	if _respawning or wing == null or player == null:
		return
	_respawning = true
	var w := wing
	var p := player
	p.input_enabled = false
	await Post.fade_to(1.0, 0.5)
	if wing != w or player != p or not is_instance_valid(p):
		_respawning = false  # the scene changed under us; Transitions resets the fade
		return
	var cp := w.find_checkpoint(checkpoint_id)
	if cp == null:
		cp = w.find_checkpoint(w.spawn_checkpoint)
	p.set_mode(w.start_mode)
	p.teleport(cp.global_transform if cp else Transform3D.IDENTITY)
	p.gravity_vector = w.gravity
	await get_tree().create_timer(0.25).timeout
	if player == p and is_instance_valid(p):
		p.input_enabled = true
		await Post.fade_to(0.0, 0.8)
	_respawning = false


func _physics_process(_delta: float) -> void:
	if state == State.PLAYING and wing and player and not Transitions.busy:
		if player.global_position.dot(-wing.gravity.normalized()) < wing.void_height:
			respawn()
	if state == State.PLAYING:
		Save.data["play_seconds"] = float(Save.data["play_seconds"]) + _delta


# --- HUD & menus ------------------------------------------------------------------------------

func _ensure_hud() -> void:
	if _hud == null or not is_instance_valid(_hud):
		_hud = preload("res://ui/hud.gd").new()
		add_child(_hud)
	_hud.visible = true


func _free_hud() -> void:
	if _hud and is_instance_valid(_hud):
		_hud.queue_free()
	_hud = null
	Post.fade_to(0.0, 0.0)  # endings fade the 3D view to ink; the title must not inherit it


func open_menu(kind: StringName) -> void:
	if state != State.PLAYING or Cinematics.playing or Placards.is_reading():
		return
	_close_menu()
	_menu = (preload("res://ui/pause_menu.gd").new() if kind == &"pause" else preload("res://ui/journal.gd").new())
	add_child(_menu)
	get_tree().paused = true
	set_state(State.PAUSED)
	Audio.ui(&"open")


func _close_menu() -> void:
	if _menu and is_instance_valid(_menu):
		_menu.queue_free()
	_menu = null
	if state == State.PAUSED:
		get_tree().paused = false


func resume() -> void:
	_close_menu()
	get_tree().paused = false
	set_state(State.PLAYING)
	Audio.ui(&"back")


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause"):
		if state == State.PLAYING and not Cinematics.playing:
			open_menu(&"pause")
			get_viewport().set_input_as_handled()
		elif state == State.PAUSED:
			resume()
			get_viewport().set_input_as_handled()
	elif event.is_action_pressed(&"journal"):
		if state == State.PLAYING and not Cinematics.playing:
			open_menu(&"journal")
			get_viewport().set_input_as_handled()
		elif state == State.PAUSED and _menu and _menu.get_script() == preload("res://ui/journal.gd"):
			resume()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed and state == State.PLAYING \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and state == State.PLAYING and OS.has_feature("release"):
		open_menu(&"pause")
	elif what == NOTIFICATION_WM_CLOSE_REQUEST:
		quit()


## Quit cleanly. Use this instead of get_tree().quit(): stopping every audio player and letting
## the mixer drop its playbacks first is what avoids "ObjectDB instances leaked" /
## "resources still in use" (AudioStreamPlayback*, OggPacketSequence*) at exit.
func quit(exit_code: int = 0) -> void:
	for n in get_tree().root.find_children("*", "", true, false):
		if n is AudioStreamPlayer or n is AudioStreamPlayer3D or n is AudioStreamPlayer2D:
			n.stop()
	await get_tree().create_timer(0.15, true, false, true).timeout
	get_tree().quit(exit_code)


# --- debug API (tests, console) -------------------------------------------------------------

## Go to a wing (or &"atrium"). Waits out a running transition instead of dropping the request;
## returns true when the player is standing in `id`.
func debug_goto(id: StringName) -> bool:
	var ok: bool
	if id == HUB_ID:
		ok = await return_to_hub()
	else:
		ok = await enter_wing(id)
	return ok and wing != null and wing.wing_id == id


func debug_complete_objective(wing_id: StringName, objective_id: StringName) -> void:
	if Quest.wing_id == wing_id:
		Quest.complete_objective(objective_id)
	else:
		var objs: Dictionary = Save.wing_data(wing_id)["objectives"]
		objs[String(objective_id)] = {"done": true, "steps": []}
		Save.save_game()


## Marks everything in a wing done: objectives (if loaded), 3 provenances, the fragment.
func debug_complete_wing(wing_id: StringName) -> void:
	if Quest.wing_id == wing_id:
		for o in Quest.objectives:
			Quest.complete_objective(StringName(o["id"]))
		for p in Quest.provenances:
			Quest.find_provenance(StringName(p["id"]))
		Quest.collect_fragment()
		return
	var provs: Array = []
	for i in 3:
		provs.append("debug_%d" % i)
	(Save.data["provenances"] as Dictionary)[String(wing_id)] = provs
	if not String(wing_id) in Save.data["fragments"]:
		(Save.data["fragments"] as Array).append(String(wing_id))
	Save.wing_data(wing_id)
	Save.save_game()
	Quest.fragment_collected.emit(wing_id)


func debug_teleport(pos: Vector3, look_at_pos: Variant = null) -> void:
	if player == null:
		return
	player.global_position = pos
	player.velocity = Vector3.ZERO
	if look_at_pos is Vector3:
		player.look_at_point(look_at_pos)
