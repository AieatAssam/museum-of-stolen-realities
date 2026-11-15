extends Node
## Full legitimate playthrough of the Vitrine Kingdom with real input only: move_forward / sprint /
## jump / interact actions and mouse-motion look. No teleports, no debug_complete_*. Every beam is
## really walked on; every receptor is really lit by traced light.
##   Godot --headless --path . --fixed-fps 60 res://wings/glass/tests/playthrough.tscn
## Exit 0 = pass. Uses a throwaway save.

const RoseWidow := preload("res://wings/glass/rose_widow.gd")

var _fails: int = 0
var _w: Node
var _frames: int = 0


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "GlassPlaythrough"
		get_tree().root.add_child.call_deferred(runner)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	Save.save_path = "user://glass_playthrough.json"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	_run.call_deferred()


func check(cond: bool, what: String) -> bool:
	if cond:
		print("  ok   ", what)
	else:
		_fails += 1
		push_error("PLAYTHROUGH FAIL: " + what)
		print("  FAIL ", what, "   at ", Game.player.global_position if Game.player else Vector3.ZERO)
		# every later step depends on this one: stop rather than cascade
		print("[glass] stopped after first failure (%.1fs game)" % (_frames / float(Engine.physics_ticks_per_second)))
		get_tree().quit(1)
	return cond


func _physics_process(_d: float) -> void:
	_frames += 1


# --- input ---------------------------------------------------------------------------------

func _tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await get_tree().physics_frame
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event(up)
	await get_tree().physics_frame


func _mouse(dx: float, dy: float) -> void:
	var mm := InputEventMouseMotion.new()
	mm.relative = Vector2(dx, dy)
	mm.screen_relative = mm.relative
	Input.parse_input_event(mm)


func _sens() -> float:
	return deg_to_rad(float(Save.settings["mouse_sensitivity"]))


func _yaw_err(target: Vector3) -> float:
	var p := Game.player
	var to := target - p.global_position
	return wrapf(atan2(-to.x, -to.z) - p.yaw, -PI, PI)


func _frames_wait(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _secs(s: float) -> void:
	await _frames_wait(int(s * Engine.physics_ticks_per_second))


func _release_all() -> void:
	for a: StringName in [&"move_forward", &"sprint", &"jump"]:
		Input.action_release(a)


## Walk with real input toward `target` (horizontal) until within `r`. Returns true on arrival.
func walk(target: Vector3, max_s: float = 30.0, r: float = 0.55, sprint: bool = false) -> bool:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	var n := int(max_s * Engine.physics_ticks_per_second)
	for i in n:
		var p := Game.player
		var d := Vector2(target.x - p.global_position.x, target.z - p.global_position.z).length()
		if d < r:
			_release_all()
			return true
		var err := _yaw_err(target)
		if OS.has_environment("GLASS_DEBUG") and i % 120 == 0:
			print("    dbg pos=", p.global_position, " yaw=", p.yaw, " err=", err, " in=", p.input_enabled, " vel=", p.velocity, " mode=", p.mode_name())
		_mouse(-err / _sens() * 0.6, 0)
		if absf(err) < 0.35:
			Input.action_press(&"move_forward")
			if sprint:
				Input.action_press(&"sprint")
		else:
			_release_all()
		await get_tree().physics_frame
	_release_all()
	print("  walk timed out at ", Game.player.global_position, " -> ", target)
	var c := KinematicCollision3D.new()
	var to := target - pos()
	if Game.player.test_move(Game.player.global_transform, Vector3(to.x, 0, to.z).normalized() * 0.5, c):
		var o: Node = c.get_collider()
		print("    blocked by ", o.get_parent().name, " at ", c.get_position(), " n=", c.get_normal(), " beam=", o.has_meta(&"beam"), " ", o.get_meta(&"beam_a", null), " -> ", o.get_meta(&"beam_b", null))
	return false


func route(points: Array, max_s: float = 40.0, sprint: bool = false) -> bool:
	for p: Vector3 in points:
		if not await walk(p, max_s, 0.55, sprint):
			return false
	return true


func look(at: Vector3) -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	var inv := -1.0 if Save.settings["invert_y"] else 1.0
	for i in 20:
		var p := Game.player
		var d := p.camera.global_position.direction_to(at)
		var ey := wrapf(atan2(-d.x, -d.z) - p.yaw, -PI, PI)
		var ep := asin(clampf(d.y, -1, 1)) - p.pitch
		if absf(ey) < 0.01 and absf(ep) < 0.01:
			break
		_mouse(-ey / _sens() * 0.7, -ep / (_sens() * inv) * 0.7)
		await get_tree().physics_frame


## Look at an interactable and press interact. Returns true if it was targeted.
func use(id: String) -> bool:
	var it: Interactable = _w.uses[id]
	await look(it.global_position)
	for i in 30:
		if Interaction.target == it:
			break
		await get_tree().physics_frame
	if not check(Interaction.target == it, "can target '%s'" % id):
		return false
	await _tap(&"interact")
	await _frames_wait(4)
	return true


func until(cond: Callable, max_s: float) -> bool:
	for i in int(max_s * Engine.physics_ticks_per_second):
		if cond.call():
			return true
		await get_tree().physics_frame
	return false


func pos() -> Vector3:
	return Game.player.global_position


# --- the run -----------------------------------------------------------------------------------

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	print("[glass] enter")
	await Game.enter_wing(&"glass")
	_w = Game.wing
	check(_w != null and _w.wing_id == &"glass", "glass loads")
	await _frames_wait(10)
	if Cinematics.playing:
		Cinematics.skip()
	await until(func() -> bool: return not Cinematics.playing and not Transitions.busy, 15.0)
	await _secs(0.5)
	check(Game.player.mode_name() == &"lightwalk", "start mode is lightwalk")
	_check_placards()

	print("[glass] 1 cloister: one beam, one dial")
	await route([Vector3(14.2, 0, 14), _w.pts["d1_use"]])
	await use("d1")
	await _secs(1.0)
	check(_w.optics.beam_near(Vector3(14.2, 0, 0)), "the sun-dial lays a beam across the gap")
	await walk(Vector3(14.2, 0, 3.0))
	var was_on_beam := false
	for i in 300:
		Input.action_press(&"move_forward")
		var err := _yaw_err(_w.pts["gap_north"])
		_mouse(-err / _sens() * 0.6, 0)
		if (Game.player.mode as Object).get("on_beam"):
			was_on_beam = true
		if pos().z < -6.0:
			break
		await get_tree().physics_frame
	_release_all()
	check(was_on_beam, "Vesper stood on the beam (lightwalk on_beam)")
	await walk(_w.pts["gap_north"])
	check(Quest.is_step_done(&"light", &"cloister_dial"), "crossed the cloister gap on light")

	print("[glass] 2 nave: clockwork")
	await route([Vector3(14.2, 0, -14), Vector3(0, 0, -14), Vector3(0, 0, -22), _w.pts["d2_use"]])
	await use("d2")
	await until(func() -> bool: return _w.dials["d2"].index == 1, 3.0)
	await _secs(0.9)
	var ok_p1 := await walk(_w.pts["p1"], 8.0, 0.6, true)
	check(ok_p1 and pos().y > -0.5, "rode clockwork beam A to the first island")
	await walk(Vector3(3.4, 0, -45.6))
	await use("m1")
	check(_w.mirrors["m1"].index == 1, "M1 turned toward the second island")
	# wait off the beam's path for the dial's timetable to swing light onto the mirror
	await until(func() -> bool: return _w.dials["d2"].index == 2, 20.0)
	await _secs(0.6)
	if not _w.optics.beam_near(Vector3(2.4, 0, -53)):
		print("    d2=", _w.dials["d2"].index, " m1=", _w.mirrors["m1"].index)
		for sg in _w.optics.live_segments():
			print("    seg ", sg.a, " -> ", sg.b)
	check(_w.optics.beam_near(Vector3(2.4, 0, -53)), "clockwork beam B reflects off M1 toward P2")
	await route([Vector3(3.3, 0, -47.5), Vector3(2.0, 0, -47.75)], 4.0)
	await walk(Vector3(2.95, 0, -57.8), 6.0, 0.4, true)
	var ok_p2 := await walk(_w.pts["p2"], 8.0, 0.6, true)
	check(ok_p2 and pos().y > -0.5 and Quest.is_step_done(&"light", &"clockwork"), "rode the scheduled reflection to the second island")

	print("[glass] 3 provenance A: up the gold beam to the triforium")
	await walk(Vector3(0.5, 0, -63.6))
	await use("m2")
	await use("m2")
	check(_w.mirrors["m2"].index == 2, "M2 aimed at the triforium")
	await _secs(0.8)
	# step up onto its low end from the side, then climb
	await walk(Vector3(-0.9, 0, -64.5))
	await walk(Vector3(-1.75, 0, -63.5), 4.0, 0.3)
	await walk(Vector3(12.0, 9, -51.97), 12.0, 0.5)
	await walk(_w.pts["triforium_face"], 3.0, 0.4)
	check(pos().y > 8.5, "climbed a 25-degree beam to the triforium")
	await walk(Vector3(13.6, 9, -50.6))
	await use("prov_face")
	await until(func() -> bool: return Quest.has_provenance(&"glass", &"face"), 6.0)
	check(Quest.has_provenance(&"glass", &"face"), "Provenance A: the face of St. Lumen")
	await _secs(1.0)
	await walk(Vector3(12.6, 9, -52.2))
	await walk(Vector3(-1.3, 0, -63.2), 12.0)
	check(pos().y > -0.5 and pos().y < 1.0, "walked back down the beam to P2")
	await use("m2")
	await use("m2")
	check(_w.mirrors["m2"].index == 1, "M2 aimed at the choir")
	await _secs(0.8)
	await walk(Vector3(-2.06, 0, -62.6))
	await walk(_w.pts["choir"], 15.0)
	check(Quest.is_step_done(&"light", &"choir") and pos().y > 2.0, "reached the choir along reflected gold")
	check(Quest.is_done(&"light"), "objective 1 complete")

	print("[glass] 4 crypt: prism, mirrors, lens")
	await route([Vector3(12.5, 2.5, -93), Vector3(12.8, 2.5, -108), _w.pts["ramp_top"]])
	await walk(_w.pts["ramp_bottom"], 20.0)
	check(pos().y < -7.0, "descended into the crypt")
	await route([Vector3(-6, -8, -110), _w.pts["prism"]])
	await use("prism")
	await until(func() -> bool: return Quest.is_step_done(&"saints", &"azure"), 4.0)
	check(Quest.is_step_done(&"saints", &"azure"), "blue split from white turned Saint Azure face-up")
	await use("prism")
	await until(func() -> bool: return bool(_w.recall("gold_gate", false)), 4.0)
	check(_w.recall("gold_gate", false), "gold opened the colour-keyed gate")
	await _secs(2.2)
	await route([_w.pts["gate_out"], _w.pts["chapel_in"], _w.pts["m4"]])
	await use("m4")
	await until(func() -> bool: return Quest.is_step_done(&"saints", &"ruby"), 4.0)
	check(Quest.is_step_done(&"saints", &"ruby"), "red through the slit, off M4, turned Saint Ruby face-up")
	await route([_w.pts["chapel_in"], _w.pts["gate_out"], Vector3(-3, -8, -95), _w.pts["prism"]])
	await use("prism")
	check(_w.prism.index == 3, "prism turned to split straight on")
	await walk(_w.pts["m6"])
	await use("m6")
	await until(func() -> bool: return Quest.is_step_done(&"saints", &"verdance"), 4.0)
	check(Quest.is_step_done(&"saints", &"verdance"), "gold + blue combined in the lens made green for Saint Verdance")
	check(Quest.is_done(&"saints"), "objective 2 complete")
	await use("m6")
	await until(func() -> bool: return _w.uses.has("prov_veil"), 4.0)
	check(_w.uses.has("prov_veil"), "red + blue (violet) opened the reliquary")
	await walk(_w.pts["reliquary"])
	await use("prov_veil")
	await until(func() -> bool: return Quest.has_provenance(&"glass", &"veil"), 6.0)
	check(Quest.has_provenance(&"glass", &"veil"), "Provenance B: the Widow's veil thread")
	await _secs(1.0)

	print("[glass] 5 passage, tower, roof")
	await route([Vector3(-8, -8, -86), _w.pts["white_gate"], Vector3(-17.5, -8, -84.8), Vector3(-17.5, -8, -32), _w.pts["tower_in"], Vector3(-17.5, -8, -25.8)], 60.0, true)
	var west := true
	for leg in 10:
		if west:
			await walk(Vector3(-26.7, 0, -25.8), 20.0)
			if leg < 9:
				await walk(Vector3(-26.7, 0, -20.6), 10.0)
		else:
			await walk(Vector3(-17.2, 0, -20.6), 20.0)
			if leg < 9:
				await walk(Vector3(-17.2, 0, -25.8), 10.0)
		west = not west
	check(pos().y > 15.5, "climbed the tower (%.1f m)" % pos().y)
	await walk(Vector3(-19, 16, -36), 10.0)
	check(_w.recall("sky", false), "the jaw-drop fired on cresting the stair")
	await _secs(4.0)
	await route([Vector3(-19, 16, -60), _w.pts["iron"], Vector3(-23.8, 18.3, -60)], 20.0)
	await use("prov_iron")
	await until(func() -> bool: return Quest.has_provenance(&"glass", &"iron"), 6.0)
	check(Quest.has_provenance(&"glass", &"iron"), "Provenance C: the grozing iron on the pinnacle")
	await _secs(1.0)
	await route([Vector3(-19, 16, -60), _w.pts["d3_use"]], 30.0)
	await use("d3")
	await _secs(1.0)
	await walk(_w.pts["balcony"], 12.0)
	check(pos().y > 13.5 and pos().x < -33.0, "crossed to the Rose hall on the heliostat beam")

	print("[glass] 6 the Rose Widow")
	var crossed := false
	for attempt in 4:
		crossed = await _rose_phase1()
		if crossed:
			break
		print("  (fell; retrying from the balcony)")
		await until(func() -> bool: return not Game._respawning and pos().distance_to(_w.pts["balcony"]) < 4.0, 6.0)
		await _secs(1.0)
	check(crossed, "rode her petals balcony -> tear -> dais")
	await walk(_w.pts["lantern"])
	await use("lantern")
	check(_w.rose.phase == 2 and _w.lantern_carried, "took the lantern; she went dark")
	await _secs(0.5)
	var path_ok := true
	for p: Vector3 in _w.rose.path:
		if not await walk(_w.HALL + p, 15.0, 0.6):
			path_ok = false
		print("    path ", p, " -> at ", pos() - _w.HALL, " lantern_r ", _w.rose.lantern_r)
	await walk(_w.pts["landing"], 8.0)
	check(path_ok and Quest.is_step_done(&"east", &"widow"), "crossed in the dark by lantern light")
	await walk(_w.pts["corridor_end"], 20.0)
	await walk(_w.pts["triforium_drop"], 10.0)
	await until(func() -> bool: return Game.player.is_on_floor() and pos().y < 3.0, 5.0)
	check(pos().y > 2.0 and pos().y < 3.0, "dropped from the triforium into the choir")

	print("[glass] 7 the lens and the East Window")
	await walk(_w.pts["lens"])
	await use("lens_holder")
	check(Quest.is_step_done(&"east", &"lens"), "lantern set in the choir lens")
	await walk(Vector3(9.3, 2.5, -93.6))
	await use("s_r")
	await walk(Vector3(-7.4, 2.5, -93.6))
	await use("s_a")
	await route([Vector3(5, 2.5, -95.5), Vector3(11.3, 2.5, -97.2), Vector3(11.3, 2.5, -101), Vector3(9.3, 2.5, -104.6)])
	await use("s_v")
	await until(func() -> bool: return _w.shattered, 6.0)
	check(_w.shattered and Quest.is_step_done(&"east", &"shatter"), "red + blue + green in the lens made white; the East Window shattered")
	check(Quest.main_objectives_done(), "all three objectives complete")
	await _secs(2.5)
	await route([Vector3(11.3, 2.5, -101), Vector3(11.3, 2.5, -97.2), Vector3(0, 2.6, -98.0), Vector3(0, 2.6, -99.6)])
	var up_ok := await walk(_w.pts["sill"], 20.0, 0.6)
	check(up_ok and pos().y > 6.0, "walked the white beam up into the wind to the sill")

	print("[glass] 8 heist")
	await use("fragment")
	await until(func() -> bool: return _w.heist_on, 8.0)
	check(_w.heist_on and Quest.has_fragment(&"glass"), "took the Fourth Sun; the heist begins")
	var prev := Vector3(0, 6.3, -124.4)
	var hops := 0
	for i in 4:
		var p: Vector3 = _w.pts["h%d" % i]
		if await walk(prev + Vector3(0, 0, -0.3), 6.0, 0.4, true) and await walk(p, 8.0, 0.8, true):
			hops += 1
		prev = p + Vector3(0, 0, -1.8)
		if Transitions.busy:
			break
	await until(func() -> bool: return Transitions.busy or (Game.wing and Game.wing.wing_id == Game.HUB_ID), 10.0)
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 15.0)
	check(hops == 4, "escaped along the dying beams (%d/4 hops)" % hops)
	check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "finish() returned to the atrium")
	var provs := 0
	for id: StringName in [&"face", &"veil", &"iron"]:
		provs += int(Quest.has_provenance(&"glass", id))
	check(provs == 3, "all three provenances collected")
	check(Quest.has_fragment(&"glass"), "fragment recorded")

	print("[glass] done in %.1fs real, %.1fs game, %d failure(s)" % [(Time.get_ticks_msec() - t0) / 1000.0, _frames / float(Engine.physics_ticks_per_second), _fails])
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	get_tree().quit(1 if _fails > 0 else 0)


## Phase 1: board a petal when one points at the balcony at full exhale, ride it in to the tear,
## wait one breath, ride the opposite petal out to the dais. Steering only reads what a player sees
## (where the petals are, how far she has breathed out) via the same function the floor uses.
func _rose_phase1() -> bool:
	var rose: Node3D = _w.rose
	var H: Vector3 = _w.HALL
	var P: float = RoseWidow.breath_period()
	await walk(_w.pts["balcony"], 6.0, 0.4)
	var t0: float = ceil((rose.t + 1.0) / P) * P
	await until(func() -> bool: return rose.t >= t0 - 0.45, P + 2.0)
	if not await _ride(H, func(t: float) -> float: return RoseWidow.OMEGA * (t - t0), -1.0, 3.2):
		return false
	await walk(H + Vector3(-2.8, 0, 0), 6.0, 0.3)
	var t1: float = ceil((rose.t + 1.0) / P) * P
	await until(func() -> bool: return rose.t >= t1 - 0.7, P + 2.0)
	if not await _ride(H, func(t: float) -> float: return PI + RoseWidow.OMEGA * (t - t1), 1.0, 14.5):
		return false
	return true


func _ride(H: Vector3, theta: Callable, dir: float, goal_r: float) -> bool:
	var rose: Node3D = _w.rose
	for i in 2400:
		var lp := pos() - H
		var r := Vector2(lp.x, lp.z).length()
		if (dir < 0 and r < goal_r) or (dir > 0 and r > goal_r):
			_release_all()
			return true
		if pos().y < H.y - 1.0:
			_release_all()
			return false
		var th: float = theta.call(rose.t + 0.25)
		var rt := maxf(r + dir * 3.0, 0.0)
		var target := H + Vector3(cos(th) * rt, 0, sin(th) * rt)
		var err := _yaw_err(target)
		_mouse(-err / _sens() * 0.8, 0)
		Input.action_press(&"move_forward")
		Input.action_press(&"sprint")
		await get_tree().physics_frame
	_release_all()
	return false


func _check_placards() -> void:
	var n := 0
	var worst := 0
	for p: Node in _w.find_children("*", "Placard", true, false):
		var words := String((p as Placard).body).split(" ", false).size()
		worst = maxi(worst, words)
		n += 1
	check(n >= 6 and worst <= 40, "%d placards, longest body %d words (<= 40)" % [n, worst])
