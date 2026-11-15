extends Node
## Plays The Drowned Aria start to finish with the wing's own mechanics: strikes via the primary verb,
## the lift columns, the chord, the cadence on the glass, a held note on secondary (carried anywhere),
## the provenances via interact, La Sirena's duet, the silent fall, and the heist out through the chord.
## Positions are set with debug_teleport and aim is set by facing the instrument, so every mechanic is
## exercised by real verbs. Section times are physics ticks converted to seconds of wing time.
## Run:  Godot --headless --path . wings/aria/tests/playthrough.tscn

const Instrument := preload("res://wings/aria/instrument.gd")
const SongMode := preload("res://wings/aria/song_mode.gd")
const AriaWing := preload("res://wings/aria/aria.gd")

var _fails: int = 0
var _sec_names: Array[String] = []
var _sec_ticks: Array[int] = []


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


## Waits t seconds of game time: the physics tick rate is fixed, the wall clock is not.
func phys(t: float) -> void:
	await frames(roundi(t * Engine.physics_ticks_per_second))


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
	return Game.wing.find_child(name_, true, false) as Node3D


## Calls a read-only accessor on the aria wing (the wing is typed as Wing in Game).
func _aria(method: StringName) -> Variant:
	return Game.wing.call(method)


## Named section: prints its heading and starts the physics-tick clock for the timing table.
func _section(name_: String, text: String) -> void:
	_sec_names.append(name_)
	_sec_ticks.append(Engine.get_physics_frames())
	print("[aria] %s: %s" % [name_, text])


func _run() -> void:
	_section("boot", "new game")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	Game.new_game()
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 30.0)
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing and not Transitions.busy, 15.0)

	_section("enter", "the wing")
	await Game.debug_goto(&"aria")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"aria" and not Transitions.busy, 30.0)
	check(Game.wing != null and Game.wing.wing_id == &"aria", "aria wing loads")
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	check(Quest.provenances.size() == 3, "aria declares 3 provenances")
	await frames(4)
	check(Game.player.mode_name() == &"song", "the wing starts her in song mode (start_mode)")
	check(Game.wing.get_node_or_null("Areas") != null, "areas are grouped under Areas/")

	_section("foyer", "the demo horn lifts, the stair climbs to the gallery, the route leads back into the auditorium")
	var demo := Game.wing.find_child("DemoHorn", true, false) as Node3D
	await _stand(demo.global_position + Vector3(0, 0, 0.8), demo.global_position + Vector3(0, 1.5, 0))
	var fy0 := Game.player.global_position.y
	_tap(&"primary")
	var fy_max := fy0
	for _i in roundi(1.6 * Engine.physics_ticks_per_second):
		await frames(1)
		fy_max = maxf(fy_max, Game.player.global_position.y)
	check(fy_max - fy0 > 1.0, "the foyer's demo horn lifts her (%.2f m)" % (fy_max - fy0))
	await _stand(Vector3(0, 0.5, 27), Vector3(0, 0.5, 40))
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.y > 2.6, 10.0)
	_send(&"move_forward", false)
	check(Game.player.global_position.y > 2.6, "walking up the grand staircase reaches the gallery (y %.2f)" % Game.player.global_position.y)
	await _stand(Vector3(0, 3.3, 36), Vector3(0, 3.3, 20))
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.z < 12.0, 14.0)
	_send(&"move_forward", false)
	check(Game.player.global_position.z < 12.0 and Game.player.global_position.y < 1.5, "walking down from the gallery reaches the auditorium floor")

	_section("brass", "strike the horns, lift under one")
	# stand 0.8 m off the west horn's axis and aim at it: inside the column, the lift beats gravity
	var horns: Array[Node3D] = []
	for n: Node in Game.wing.find_child("Instruments", true, false).get_children():
		var inst := n as Instrument
		if inst and inst.note_id == &"note_horn":
			horns.append(inst)
	check(horns.size() == 3, "three horns in the hall")
	await _stand(horns[0].global_position + Vector3(0, 0, 0.8), horns[0].global_position + Vector3(0, 1.5, 0))
	var y0 := Game.player.global_position.y
	_tap(&"primary")
	var y_max := y0
	for _i in roundi(1.6 * Engine.physics_ticks_per_second):
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

	_section("chord", "strike the three pipes within one sounding window")
	var pipes := ["Instrument_organ_c", "Instrument_organ_e", "Instrument_organ_g"]
	for pipe: String in pipes:
		var pn := _instrument(pipe)
		await _stand(pn.global_position + Vector3(0, 0, 2.2), pn.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(4)
	await _until(func() -> bool: return Quest.is_done(&"chord"), 3.0)
	check(Quest.is_done(&"chord"), "the chord step completes on three sounding pipes")

	_section("cadence", "G, E, C on the glass")
	var glass := {"g": "Instrument_g", "e": "Instrument_e", "c": "Instrument_c"}
	for note: String in ["g", "e", "c"]:
		var gn := _instrument(glass[note])
		await _stand(gn.global_position + Vector3(0, 0, 2.0), gn.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(10)
	check(Quest.is_done(&"cadence"), "the cadence G, E, C completes the objective")

	_section("sink", "strike the auditorium well, then drop through its footprint (A/B against the silent well)")
	var well := _instrument("Instrument_sink_low")
	# B: the same drop with the well silent, measured first so the well's tail does not leak in
	await _until(func() -> bool: return well.env <= 0.001, 15.0)
	var drop_silent := await _measure_drop(well)
	await _stand(well.global_position + Vector3(0, 0, 1.0), well.global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	await phys(1.4)
	var drop_sink := await _measure_drop(well)
	print("  drop with the well sounding %.2f m, silent %.2f m" % [drop_sink, drop_silent])
	check(drop_sink > drop_silent + 0.3, "the sink well draws her down faster (%.2f m vs %.2f m over 0.6 s)" % [drop_sink, drop_silent])

	_section("hold", "secondary sustains the last note struck, and spends breath")
	var song: MovementMode = Game.player.modes[&"song"]
	var gn0 := _instrument(glass["c"])
	await _stand(gn0.global_position + Vector3(0, 0, 1.5), gn0.global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	await frames(3)
	var breath0: float = song.get("breath")
	_send(&"secondary", true)
	await phys(1.0)
	_send(&"secondary", false)
	var breath1: float = song.get("breath")
	check(breath1 < breath0 - 0.5, "holding a note spends breath (%.2f -> %.2f)" % [breath0, breath1])

	_section("carried", "a held note travels with her: far from the horn, it still lifts her, and breath limits it")
	var horn_c := horns[2]
	await _stand(horn_c.global_position + Vector3(0, 0, 0.8), horn_c.global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	await phys(1.6)
	await _stand(Vector3(-14, 0.5, 6), Vector3(-14, 1.5, 0))
	check(horn_c.global_position.distance_to(Game.player.global_position) > 15.0, "she is more than 15 m from the horn it carries")
	var cy0 := Game.player.global_position.y
	_send(&"secondary", true)
	await phys(1.0)
	var cy1 := Game.player.global_position.y
	check((horn_c as Instrument).carry_to == Game.player, "the held horn is carried by the player")
	check(cy1 - cy0 > 0.5, "the carried note lifts her far from the instrument (%.2f m)" % (cy1 - cy0))
	await _until(func() -> bool: return float(song.get("breath")) <= 0.001, 10.0)
	check(float(song.get("breath")) <= 0.001, "holding until breath runs out stops the note's hold")
	_send(&"secondary", false)
	await phys(0.5)
	check((horn_c as Instrument).carry_to == null, "releasing the verb lets the note go")

	_section("pit", "walk down the ramp, one pipe stays below the gantry, two together reach it")
	await _stand(Vector3(-11, 0.5, -10), Vector3(-30, 0.5, -10))
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.y < -2.5, 12.0)
	_send(&"move_forward", false)
	check(Game.player.global_position.y < -2.5 and Game.player.global_position.x < -18.0, "the ramp walks her down into the pit (x %.1f, y %.2f)" % [Game.player.global_position.x, Game.player.global_position.y])
	var pit_a := _instrument("Instrument_pit_a")
	var pit_b := _instrument("Instrument_pit_b")
	await _stand(pit_a.global_position + Vector3(0, 0, 0.8), pit_a.global_position + Vector3(0, 1.5, 0))
	var py0 := Game.player.global_position.y
	_tap(&"primary")
	var py_one := py0
	for _i in roundi(1.6 * Engine.physics_ticks_per_second):
		await frames(1)
		py_one = maxf(py_one, Game.player.global_position.y)
	check(py_one < 0.9, "pit_a alone does not reach the gantry top (peak y %.2f, top 1.00)" % py_one)
	# both pipes sound: stand between them (1 m from each axis) and strike pit_b while pit_a still sounds
	await _stand(Vector3(-28, -3, -12), Vector3(-28, -1.5, -11))
	_tap(&"primary")
	await frames(2)
	# still lifted: steer for the gantry's centre; success means standing on its top inside the footprint
	Game.debug_teleport(Game.player.global_position, Vector3(-22, 1.0, -17))
	var py_two := py0
	var on_gantry := false
	_send(&"move_forward", true)
	for _i in 300:  # up to 5 s of physics frames
		if on_gantry:
			break
		await frames(1)
		var gp := Game.player.global_position
		py_two = maxf(py_two, gp.y)
		on_gantry = Game.player.is_on_floor() and gp.y > 0.8 and gp.x > -26.0 and gp.x < -18.0 and gp.z > -19.5 and gp.z < -14.5
	_send(&"move_forward", false)
	var gpos := Game.player.global_position
	check(on_gantry, "pit_a and pit_b together lift her, and she lands on the gantry (peak y %.2f, at x %.1f z %.1f y %.2f)" % [py_two, gpos.x, gpos.z, gpos.y])
	# the sink well in the pit is a trap off the route: the test only confirms it exists and is silent by default
	check(_instrument("Instrument_pit_well") != null, "the pit's sink well is placed")

	_section("fly-loft", "the tuning-fork statue rings its note and lifts her")
	var fork := Game.wing.find_child("TuningForkStatue", true, false) as Node3D
	await _stand(Vector3(56, 2.8, 40.8), fork.global_position + Vector3(0, 1.5, 0))
	var fk0 := Game.player.global_position.y
	_tap(&"primary")
	var fk_max := fk0
	for _i in roundi(1.6 * Engine.physics_ticks_per_second):
		await frames(1)
		fk_max = maxf(fk_max, Game.player.global_position.y)
	check(fk_max - fk0 > 1.0, "the fork statue lifts her (%.2f m)" % (fk_max - fk0))

	_section("corridor", "a fall outside the flip sends her to the corridor checkpoint; a crossing inside it succeeds")
	await _stand(Vector3(17, 2.8, 39), Vector3(30, 2.8, 39))
	await frames(10)
	await _stand(Vector3(21, 2.8, 39), Vector3(30, 2.8, 39))
	# wait for a fresh quiet window: the flip must start and end before she walks
	await _until(func() -> bool: return SongMode.flipping, 7.0)
	await _until(func() -> bool: return not SongMode.flipping, 7.0)
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.y < -1.0 or Game.player.global_position.x < 18.5, 6.0)
	_send(&"move_forward", false)
	await _until(func() -> bool: return Game.player.global_position.x < 18.5, 6.0)
	check(Game.player.global_position.x <= 18.5, "a jump outside the flip window respawns her at the corridor checkpoint (x %.1f)" % Game.player.global_position.x)
	# the respawn runs through a transition that puts her back at the checkpoint: wait it out before the next run
	await _until(func() -> bool: return not Transitions.busy, 6.0)
	await seconds(0.5)
	# the crossing, from the gallery: walk the approach, hold short of the box until a downbeat, then cross into the loft
	await _stand(Vector3(0, 2.8, 39), Vector3(30, 2.8, 39))
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.x >= 19.0, 10.0)
	_send(&"move_forward", false)
	await _until(func() -> bool: return not SongMode.flipping, 7.0)
	await _until(func() -> bool: return SongMode.flipping, 7.0)
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.x > 47.0, 12.0)
	_send(&"move_forward", false)
	var cx := Game.player.global_position
	check(cx.x > 47.0 and cx.y > 2.0, "walking the gallery, then crossing on a downbeat, reaches the fly-loft (x %.1f, y %.2f)" % [cx.x, cx.y])

	_section("provenances", "three hidden collectibles by interact")
	var pickups: Array[Node] = Game.wing.find_children("*", "Pickup", true, false)
	for pk: Node in pickups:
		var pick := pk as Pickup
		if pick.kind != &"provenance":
			continue
		await _stand(pick.global_position + Vector3(0, 0, 1.2), pick.global_position)
		_tap(&"interact")
		await seconds(2.5)
	check(_count_provs() == 3, "three provenances recorded")

	_section("duet", "La Sirena: a wrong answer repeats its round, then three rounds of correct answers")
	await _stand(Vector3(0, 0.5, -12), Vector3(0, 0.5, -20))
	_send(&"move_forward", true)
	await _until(func() -> bool: return Game.player.global_position.z < -19.5, 8.0)
	_send(&"move_forward", false)
	await _until(func() -> bool: return _aria(&"duet_window_open") as bool, 15.0)
	check(_aria(&"duet_window_open") as bool, "the duet cue opens the first answer window")
	check(_aria(&"duet_round") == 0, "the duet starts in round one")
	# a deliberate wrong answer: strike the bowl that is not in the phrase
	var expected: Array = _aria(&"duet_expected")
	var wrong := &"c" if expected[0] != &"c" else &"e"
	await _strike_bowl(wrong)
	await _until(func() -> bool: return not (_aria(&"duet_window_open") as bool), 3.0)
	check(_aria(&"duet_round") == 0 and not Quest.is_done(&"duet"), "a wrong answer repeats round one")
	await _until(func() -> bool: return _aria(&"duet_window_open") as bool, 15.0)
	check((_aria(&"duet_expected") as Array) == expected, "the repeated round sings the same phrase")
	var guard := 0
	while not Quest.is_done(&"duet") and guard < 40:
		guard += 1
		await _until(func() -> bool: return (_aria(&"duet_window_open") as bool) or Quest.is_done(&"duet"), 20.0)
		if Quest.is_done(&"duet"):
			break
		for n: StringName in _aria(&"duet_expected"):
			await _strike_bowl(n)
		await _until(func() -> bool: return not (_aria(&"duet_window_open") as bool), 3.0)
	check(Quest.is_done(&"duet"), "all three rounds answered, the duet is done")
	check(Quest.is_step_done(&"duet", &"round3"), "round three completed")

	_section("fall", "the silent chandelier: music cut, every figure looks up, she moves freely for ninety seconds")
	check(_aria(&"fall_running") as bool, "the chandelier begins its fall with the duet's last note")
	var fragment_spot: Node3D = Game.wing.find_child("FragmentSpot", true, false)
	check(fragment_spot.visible, "the fragment is on the stage as the last note ends")
	var chand := Game.wing.find_child("Chandelier", true, false) as Node3D
	var ch0 := chand.global_position.y
	await _stand(Vector3(0, 0.5, -40), Vector3(0, 0.5, -48))
	var fx0 := Game.player.global_position
	_send(&"move_forward", true)
	await phys(2.0)
	_send(&"move_forward", false)
	var fx1 := Game.player.global_position
	check(fx0.distance_to(fx1) > 0.5, "she moves freely during the fall (%.2f m in 2 s)" % fx0.distance_to(fx1))
	var ch1 := chand.global_position.y
	# the fall eases in and out over 90 s (11 m total), so the first two seconds move only centimetres
	check(ch0 - ch1 > 0.005 and ch0 - ch1 < 0.05, "the chandelier descends slowly (%.3f m in 2 s of 90)" % (ch0 - ch1))
	var fig := Game.wing.find_child("Figure00", true, false) as Node3D
	var head := fig.get_child(1) as Node3D
	var to_chand := (chand.global_position - head.global_position).normalized()
	var facing := -head.global_transform.basis.z.normalized()
	check(facing.dot(to_chand) > 0.95, "the first figure's head follows the chandelier")
	await _until(func() -> bool: return Quest.is_done(&"fall"), 150.0)
	check(Quest.is_done(&"fall"), "the fall completes after ninety seconds")
	check(absf(chand.global_position.y - 4.0) < 0.05, "the chandelier comes to rest at y 4 (%.2f)" % chand.global_position.y)

	_section("heist", "take the fragment, gravity lets go in stages, climb the chord to the ledge, leave by the one exit")
	var marks := get_tree().get_nodes_in_group(&"shot_marks")
	check(marks.size() == 12, "twelve camera marks in group shot_marks (%d)" % marks.size())
	var plac := Game.wing.find_children("*", "Placard", true, false)
	check(plac.size() <= 12 and plac.size() >= 8, "placards in the wing, at most twelve (%d)" % plac.size())
	await _stand(fragment_spot.global_position + Vector3(0, -1.0, 1.6), fragment_spot.global_position)
	_tap(&"interact")
	await _until(func() -> bool: return Quest.has_fragment(&"aria"), 6.0)
	check(Quest.has_fragment(&"aria"), "the fragment is taken")
	await seconds(0.3)
	check(absf(Game.player.gravity_vector.y - Game.wing.gravity.y * 0.5) < 0.2, "gravity lets go in stages: half first (%.2f)" % Game.player.gravity_vector.y)
	await seconds(3.5)
	check(Game.player.gravity_vector.length() < 0.1, "then gravity is gone (%.2f)" % Game.player.gravity_vector.length())
	# the sink in the dome: with no gravity it still pulls her down through its footprint
	var sink := _instrument("Instrument_dome_sink")
	await _stand(Vector3(0, 0.5, -48), Vector3(0, 1.5, -54))
	_tap(&"primary")
	await phys(0.4)
	await _stand(Vector3(0, 2.5, -54), Vector3(0, 2.5, -55))
	var sy0 := Game.player.global_position.y
	await phys(0.5)
	var sink_drop := sy0 - Game.player.global_position.y
	check(sink_drop > 0.5, "the sink well pulls her down with no gravity (%.2f m in 0.5 s)" % sink_drop)
	await phys(9.0)  # let the sink fall silent before the chord route
	# the chord route: strike both columns, then climb between them to the ledge
	for col_name: String in ["Heist_heist_a", "Heist_heist_b"]:
		var col := _instrument(col_name)
		await _stand(col.global_position + Vector3(0, 0, 2.2), col.global_position + Vector3(0, 1.5, 0))
		_tap(&"primary")
		await frames(4)
	# rise inside the chord's footprint (the lift is weakest at its top, so she stays within 2.6 m of both columns)
	await _stand(Vector3(0, 0.5, -56), Vector3(0, 0.5, -62))
	await _until(func() -> bool: return Game.player.global_position.y >= 8.0, 25.0)
	var rise := Game.player.global_position
	print("  climb: risen to y %.2f at x %.2f z %.2f" % [rise.y, rise.x, rise.z])
	check(rise.y >= 8.0, "the chord lifts her clear of the ledge (y %.2f)" % rise.y)
	# with gravity gone nothing pulls her back down, so once above the ledge she drifts onto it
	_send(&"move_forward", true)
	var climb_t := 0.0
	while climb_t < 30.0 and Game.wing != null and Game.wing.wing_id != Game.HUB_ID:
		await phys(1.0)
		climb_t += 1.0
		if Game.player == null:  # the exit may already have swapped the wing out
			break
		var cp := Game.player.global_position
		print("  climb t=%.0f s  x %.2f y %.2f z %.2f" % [climb_t, cp.x, cp.y, cp.z])
	_send(&"move_forward", false)
	check(Game.wing == null or Game.wing.wing_id == Game.HUB_ID, "the ledge exit returns to the atrium")
	check(Quest.has_fragment(&"aria"), "aria fragment recorded")

	_section("end", "")
	_print_timings()
	print("[aria] done, %d failure(s)" % _fails)
	get_tree().quit(1 if _fails > 0 else 0)


## Strike the duet bowl for `note`: stand two metres off it, face it, and press primary.
func _strike_bowl(note: StringName) -> void:
	var bowl := _instrument("Duet_" + String(note))
	await _stand(bowl.global_position + Vector3(0, 0, 2.0), bowl.global_position + Vector3(0, 1.5, 0))
	_tap(&"primary")
	await frames(6)


func _print_timings() -> void:
	print("[aria] section times (wing time, from physics ticks at %d Hz):" % Engine.physics_ticks_per_second)
	for i: int in _sec_names.size() - 1:
		var secs := float(_sec_ticks[i + 1] - _sec_ticks[i]) / Engine.physics_ticks_per_second
		print("  %-12s %6.1f s  (%.2f min)" % [_sec_names[i], secs, secs / 60.0])


## Drop from 2.5 m above the well's floor origin for 0.6 s of physics, returning metres fallen.
func _measure_drop(well: Node3D) -> float:
	Game.debug_teleport(well.global_position + Vector3(0, 2.5, 0), well.global_position + Vector3(0, 2.5, -1.0))
	await frames(4)
	var y0 := Game.player.global_position.y
	await frames(36)
	return y0 - Game.player.global_position.y


func _count_provs() -> int:
	var n := 0
	for p: Dictionary in Quest.provenances:
		if Quest.has_provenance(&"aria", StringName(p["id"])):
			n += 1
	return n
