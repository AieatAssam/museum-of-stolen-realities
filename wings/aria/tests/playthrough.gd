extends Node
## Plays The Drowned Aria with the wing's own mechanics: strikes via the primary verb, the lift
## column under a sounding horn, the chord, the cadence on the glass, a held note on secondary,
## the provenances via interact, and the fragment. Positions are set with debug_teleport and aim
## is set by facing the instrument, so every mechanic is exercised by real verbs.
## Run:  Godot --headless --path . wings/aria/tests/playthrough.tscn

const Instrument := preload("res://wings/aria/instrument.gd")

var _fails: int = 0


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "PlaythroughRunner"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://aria_playthrough_save.json"
	_run.call_deferred()


func check(cond: bool, what: String) -> void:
	if cond:
		print("  ok   ", what)
	else:
		_fails += 1
		push_error("PLAYTHROUGH FAIL: " + what)
		print("  FAIL ", what)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


func _tap(action: StringName) -> void:
	_send(action, true)
	_send.call_deferred(action, false)


## Verbs arrive as input events (Player._unhandled_input), so send real action events.
func _send(action: StringName, pressed: bool) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = pressed
	Input.parse_input_event(ev)


## Stand at `at` (eye height 1.5 m) and face `target`, then wait for the camera to settle.
func _stand(at: Vector3, target: Vector3) -> void:
	Game.debug_teleport(at, target)
	await frames(8)


func _instrument(name_: String) -> Node3D:
	return Game.wing.get_node("Instruments/" + name_) as Node3D


func _run() -> void:
	print("[aria] boot, new game")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	Game.new_game()
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 30.0)
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing and not Transitions.busy, 15.0)

	print("[aria] enter the wing")
	await Game.debug_goto(&"aria")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"aria" and not Transitions.busy, 30.0)
	check(Game.wing != null and Game.wing.wing_id == &"aria", "aria wing loads")
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	check(Quest.provenances.size() == 3, "aria declares 3 provenances")
	Game.player.set_mode(&"song")
	await frames(4)
	check(Game.player.mode_name() == &"song", "song mode active")

	print("[aria] objective one: strike the horns, lift under one")
	# stand 0.8 m off the west horn's axis and aim at it: inside the column, the lift beats gravity
	var horns: Array[Node3D] = []
	for n: Node in Game.wing.get_node("Instruments").get_children():
		var inst := n as Instrument
		if inst and inst.note_id == &"note_horn":
			horns.append(inst)
	check(horns.size() == 3, "three horns in the hall")
	var y0 := Game.player.global_position.y
	await _stand(horns[0].global_position + Vector3(0, 0, 0.8), horns[0].global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	var y_max := y0
	var t_end := Time.get_ticks_msec() + 1600
	while Time.get_ticks_msec() < t_end:
		await frames(1)
		y_max = maxf(y_max, Game.player.global_position.y)
	check(Quest.is_step_done(&"brass", &"horn_a"), "striking the west horn completes its step")
	check(y_max - y0 > 1.0, "the horn lifts her (%.2f m)" % (y_max - y0))
	for i: int in [1, 2]:
		var h := horns[i]
		await _stand(h.global_position + Vector3(0, 0, 0.8), h.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(10)
	check(Quest.is_done(&"brass"), "objective 'Wake the brass' done")

	print("[aria] objective two: strike the three pipes within one sounding window")
	var pipes := ["Instrument_organ_c", "Instrument_organ_e", "Instrument_organ_g"]
	for pipe: String in pipes:
		var pn := _instrument(pipe)
		await _stand(pn.global_position + Vector3(0, 0, 2.2), pn.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(4)
	await _until(func() -> bool: return Quest.is_done(&"chord"), 3.0)
	check(Quest.is_done(&"chord"), "the chord step completes on three sounding pipes")

	print("[aria] objective three: G, E, C on the glass, then a held note")
	var glass := {"g": "Instrument_g", "e": "Instrument_e", "c": "Instrument_c"}
	for note: String in ["g", "e", "c"]:
		var gn := _instrument(glass[note])
		await _stand(gn.global_position + Vector3(0, 0, 2.0), gn.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(10)
	check(Quest.is_done(&"cadence"), "the cadence G, E, C completes the objective")

	# held note: secondary sustains the struck note nearby; breath should drop while held
	var song: MovementMode = Game.player.modes[&"song"]
	var gn0 := _instrument(glass["c"])
	await _stand(gn0.global_position + Vector3(0, 0, 1.5), gn0.global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	await frames(3)
	var breath0: float = song.get("breath")
	_send(&"secondary", true)
	await seconds(1.0)
	_send(&"secondary", false)
	var breath1: float = song.get("breath")
	check(breath1 < breath0 - 0.5, "holding a note spends breath (%.2f -> %.2f)" % [breath0, breath1])

	print("[aria] provenances by interact")
	var pickups: Array[Node] = Game.wing.find_children("*", "Pickup", true, false)
	for pk: Node in pickups:
		var pick := pk as Pickup
		if pick.kind != &"provenance":
			continue
		await _stand(pick.global_position + Vector3(0, 0, 1.2), pick.global_position)
		_tap(&"interact")
		await seconds(2.5)
	check(_count_provs() == 3, "three provenances recorded")

	print("[aria] fragment")
	var frag: Node3D = Game.wing.get_node("FragmentSpot")
	check(frag.visible, "fragment appears once the objectives are done")
	await _stand(frag.global_position + Vector3(0, -1.0, 1.6), frag.global_position)
	_tap(&"interact")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 30.0)
	check(Quest.has_fragment(&"aria"), "aria fragment recorded")
	check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "finish() returned to the atrium")

	print("[aria] done, %d failure(s)" % _fails)
	get_tree().quit(1 if _fails > 0 else 0)


func _count_provs() -> int:
	var n := 0
	for p: Dictionary in Quest.provenances:
		if Quest.has_provenance(&"aria", StringName(p["id"])):
			n += 1
	return n
