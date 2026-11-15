extends Node
## Noir playthrough. Real input for walking and pressing; teleports only to puzzle positions
## (a latch face, an interactable's approach, a pickup, the reel pedestal). Never calls debug_complete_*.
## Run:  Godot --headless --path . wings/noir/tests/playthrough.tscn

var _fails := 0


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "NoirPlaythrough"
		get_tree().root.add_child.call_deferred(runner)
		queue_free()
		return
	Save.save_path = "user://noir_playthrough.json"
	_run.call_deferred()


func check(cond: bool, what: String) -> void:
	if cond:
		print("  ok   ", what)
	else:
		_fails += 1
		push_error("NOIR FAIL: " + what)
		print("  FAIL ", what)


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _tap(action: StringName) -> void:
	var down := InputEventAction.new()
	down.action = action
	down.pressed = true
	Input.parse_input_event(down)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


func _tp(pos: Vector3, look: Vector3) -> void:
	Game.debug_teleport(pos, look)
	await frames(2)
	Game.player.look_at_point(look)
	await frames(2)


func _cinema_try(pos: Vector3, look: Vector3, hold: float, done: Callable) -> void:
	for attempt in 12:
		await _until(func() -> bool: return not Transitions.busy, 10.0)
		if done.call():
			return
		await _tp(pos, look)
		if hold > 0.0:
			var down := InputEventAction.new()
			down.action = &"interact"
			down.pressed = true
			Input.parse_input_event(down)
			await seconds(hold)
			var up := InputEventAction.new()
			up.action = &"interact"
			up.pressed = false
			Input.parse_input_event(up)
		else:
			_tap(&"interact")
		await _until(done, 3.0)
		if not done.call():
			print("  beam caught the attempt, retrying")


func _hold_on(action: StringName, t: float) -> void:
	var down := InputEventAction.new()
	down.action = action
	down.pressed = true
	Input.parse_input_event(down)
	await seconds(t)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event(up)


func _walk_to(target: Vector3, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	while Time.get_ticks_msec() < end and Game.player and Game.player.global_position.distance_to(target) > 0.8:
		var p := Game.player
		if p == null:
			break
		var to := target - p.global_position
		to.y = 0
		var want_yaw := atan2(-to.x, -to.z)
		var err := wrapf(want_yaw - p.yaw, -PI, PI)
		var mm := InputEventMouseMotion.new()
		mm.relative = Vector2(-err / deg_to_rad(float(Save.settings["mouse_sensitivity"])) * 0.5, 0)
		mm.screen_relative = mm.relative
		Input.parse_input_event(mm)
		if absf(err) < 0.5:
			Input.action_press(&"move_forward")
		else:
			Input.action_release(&"move_forward")
		await get_tree().physics_frame
	Input.action_release(&"move_forward")


func _in_noir() -> bool:
	return Game.wing != null and Game.wing.wing_id == &"noir"


## x of the elevated train, read from the wing (0 when the wing is not loaded)
func _train_x() -> float:
	var t: Node3D = Game.wing.get("_train") if Game.wing else null
	return t.position.x if t else 0.0


## true while the train's lamp reaches the gap midpoint
func _gap_lit() -> bool:
	var ex: Array[RID] = [Game.player.get_rid()]
	return ShadowField.lit(Game.player, Vector3(-21.0, 6.0, -29.0), ex)


var _sampling := false
var _t0 := 0.0


## Once a second: position, mode, and whether the head is lit. Logs are the evidence for stuck and ejected steps.
func _sampler() -> void:
	while _sampling:
		await seconds(1.0)
		var p := Game.player
		if p == null or not _in_noir():
			continue
		var ex: Array[RID] = [p.get_rid()]
		var lit := ShadowField.lit(p, p.head.global_position, ex)
		var v := p.global_position
		print("  t=%5.1f pos=(%.2f, %.2f, %.2f) mode=%s head_lit=%s" % [Time.get_ticks_msec() / 1000.0 - _t0, v.x, v.y, v.z, p.mode_name(), lit])


func _run() -> void:
	print("[noir] new game, real input to the Gallery of Stolen Realities")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(1.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	await seconds(0.5)
	_tap(&"ui_accept")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)

	var hub := Game.wing
	await _walk_to(hub.call("entry_point", &"noir"), 40.0)
	await _until(_in_noir, 20.0)
	await _until(func() -> bool: return not Transitions.busy, 15.0)
	check(_in_noir(), "walking into the noir door enters The Long Shadow")
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	var w := Game.wing
	check(Quest.provenances.size() == 3, "noir declares 3 provenances")
	check(Quest.objectives.size() == 3, "noir declares 3 objectives")
	check(Game.player.mode_name() == &"shadowstep", "player starts in shadowstep")
	var placards := w.find_children("*", "Placard", true, false)
	check(placards.size() <= 12, "placards: %d (limit 12)" % placards.size())

	_t0 = Time.get_ticks_msec() / 1000.0
	_sampling = true
	_sampler()
	print("[noir] alley: walk into the shade, latch onto the dark wall")
	await _walk_to(Vector3(0, 0.05, -7), 15.0)
	await frames(4)
	check(Quest.is_step_done(&"learn_dark", &"enter_shade"), "walking into the alley completes enter_shade")
	await _tp(Vector3(-1.0, 0.05, -18.0), Vector3(-1.0, 1.2, -21.0))
	await frames(10)
	_tap(&"secondary")
	await frames(6)
	check(Quest.is_step_done(&"learn_dark", &"latch_wall"), "latching onto the dark wall completes latch_wall")
	_tap(&"secondary")
	await frames(4)

	print("[noir] pawn ticket")
	await _tp(Vector3(-1.0, 0.05, -12.0), Vector3(-3.2, 1.1, -12.0))  # clear of the crate top; eye height is 0.55 in shadowstep
	await frames(4)
	_tap(&"interact")
	await _until(func() -> bool: return Quest.has_provenance(&"noir", &"pawn"), 4.0)
	check(Quest.has_provenance(&"noir", &"pawn"), "the pawn ticket is recorded")

	print("[noir] diner window: the silhouette shows where the shade will be")
	await _walk_to(Vector3(3.2, 0.05, -15.0), 15.0)
	await _walk_to(Vector3(3.2, 0.05, -30.0), 15.0)
	await frames(4)
	var sil: MeshInstance3D = w.get("_silhouette")
	var caster: DelayedCaster = w.get("_caster")
	var agreed := true
	for i in 30:
		await frames(2)
		if absf(sil.position.z - caster.position.z) > 0.05:
			agreed = false
	check(agreed, "the window silhouette tracks the caster's position eleven seconds ahead")

	print("[noir] the roof: walk up the fire-stair ramp, latch across the gap between trains")
	await _walk_to(Vector3(-2.0, 0.05, -28.5), 15.0)
	# set off just after the train wraps, so its lamp is at the far end while we climb
	await _until(func() -> bool: return _train_x() < -40.0, 14.0)
	var f0 := Engine.get_physics_frames()
	await _walk_to(Vector3(-15.0, 5.05, -28.5), 12.0)
	var climb := (Engine.get_physics_frames() - f0) / float(Engine.physics_ticks_per_second)
	var at := Game.player.global_position
	check(at.x < -13.5 and at.y > 4.8, "walking up the ramp reaches the roof (at %s)" % at)
	check(climb < 6.0, "the ramp climb takes %.1f s of physics (limit 6)" % climb)
	await _walk_to(Vector3(-18.0, 5.05, -29.0), 10.0)
	var m := Game.player.mode as ShadowstepMode
	# looking down at the roof underfoot is a latch on this roof, never the crossing
	await _until(func() -> bool: return not _gap_lit(), 14.0)
	await _tp(Vector3(-18.0, 5.05, -29.0), Vector3(-16.5, 5.0, -29.0))
	await frames(10)
	m.hit = {}
	_tap(&"secondary")
	await frames(30)
	check(m.hit.get("collider") == w.get("_near_roof"), "the downward latch ray hits the near roof")
	check(not Quest.is_step_done(&"cross_lit", &"latch_gap"), "latching the roof underfoot does not count as the crossing")
	check(Game.player.global_position.x > -19.0 and not m.latched, "latching the roof underfoot leaves the player there, unlatched (at %.2f)" % Game.player.global_position.x)
	# the train's lamp cuts the shadow path while it is over the gap; the latch only carries you while the gap is dark
	await _until(func() -> bool: return not _gap_lit(), 14.0)
	await _tp(Vector3(-19.0, 5.05, -29.0), Vector3(-22.5, 5.55, -29.0))
	await frames(10)
	_tap(&"secondary")
	await _until(func() -> bool: return Game.player.global_position.x < -21.0, 5.0)
	check(Quest.is_step_done(&"cross_lit", &"latch_gap"), "latching across the rooftop gap completes latch_gap")
	check(Game.player.global_position.x < -21.0, "the latch carries the player to the far roof (at %.2f)" % Game.player.global_position.x)
	# x < -21 is reached mid-traversal; a press before the 1.2 s tween ends lets go instead of latching
	await _until(func() -> bool: return not m.latched, 3.0)
	# back across: from the far roof's east edge, latch the near roof below across the gap
	await _tp(Vector3(-22.8, 7.05, -29.0), Vector3(-18.8, 5.0, -29.0))
	await frames(10)
	await _until(func() -> bool: return not _gap_lit(), 14.0)
	_tap(&"secondary")
	await _until(func() -> bool: return Game.player.global_position.x > -18.0, 5.0)
	check(Game.player.global_position.x > -18.0, "the latch carries the player back to the near roof (at %.2f)" % Game.player.global_position.x)
	await _until(func() -> bool: return not m.latched, 3.0)
	await _until(func() -> bool: return _train_x() < -40.0, 14.0)
	await _walk_to(Vector3(-13.5, 5.05, -29.0), 10.0)
	await _walk_to(Vector3(-2.5, 0.05, -28.5), 12.0)
	at = Game.player.global_position
	check(at.x > -4.5 and at.y < 0.1, "walking down the ramp returns to the street (at %s)" % at)
	await _walk_to(Vector3(3.2, 0.05, -28.5), 15.0)
	print("  at ", Game.player.global_position)

	print("[noir] the lit street")
	await _walk_to(Vector3(3.2, 0.05, -24.0), 15.0)
	print("  at ", Game.player.global_position)
	await _walk_to(Vector3(3.5, 0.05, -51.0), 45.0)
	print("  at ", Game.player.global_position)
	await frames(10)
	check(Quest.is_step_done(&"cross_lit", &"cross_street"), "crossing the street completes cross_street")

	print("[noir] the Better Half")
	await _tp(Vector3(0, 0.05, -55.5), Vector3(-1.4, 0.9, -58.0))
	await frames(6)
	_tap(&"interact")
	await frames(10)
	check(Quest.is_step_done(&"cross_lit", &"better_half"), "reuniting the figures completes better_half")

	print("[noir] matchbook")
	await _tp(Vector3(3.6, 0.05, -61.0), Vector3(4.2, 0.6, -63.0))
	await frames(4)
	_tap(&"interact")
	await _until(func() -> bool: return Quest.has_provenance(&"noir", &"matchbook"), 4.0)
	check(Quest.has_provenance(&"noir", &"matchbook"), "the matchbook is recorded")

	print("[noir] precinct: desk lamp off, swing lamp away, locker")
	await _tp(Vector3(3.2, 0.05, -57.8), Vector3(4.8, 1.2, -57.8))
	await frames(4)
	_tap(&"interact")
	await frames(6)
	check(Quest.is_step_done(&"heist", &"dim_lamp"), "switching off the desk lamp completes dim_lamp")
	await _tp(Vector3(7.2, 0.05, -59.6), Vector3(6.4, 1.2, -60.2))
	await frames(4)
	_tap(&"interact")
	await frames(6)
	await _tp(Vector3(7.2, 0.05, -61.5), Vector3(6.5, 0.8, -63.0))
	await frames(4)
	await _hold_on(&"interact", 1.4)
	await _until(func() -> bool: return Quest.is_step_done(&"heist", &"get_key"), 4.0)
	check(Quest.is_step_done(&"heist", &"get_key"), "holding interact at the locker completes get_key")

	print("[noir] the cinema and the reel")
	await _walk_to(Vector3(4.5, 0.05, -57.0), 15.0)
	await _walk_to(Vector3(3.5, 0.05, -64.5), 15.0)
	await _walk_to(Vector3(3.5, 0.05, -68.0), 15.0)
	await frames(6)
	check(Quest.is_step_done(&"heist", &"enter_cinema"), "entering the cinema completes enter_cinema")
	# the searchlights sweep the room; a beam that catches the player sends her back, so each take
	# retries from the puzzle position until the beam is off her
	await _cinema_try(Vector3(1.5, 0.05, -86.0), Vector3(0, 0.6, -86.0), 2.0,
		func() -> bool: return Quest.is_step_done(&"heist", &"steal_reel"))
	check(Quest.is_step_done(&"heist", &"steal_reel"), "holding interact takes the reel")
	await _cinema_try(Vector3(1.5, 0.05, -84.0), Vector3(3.0, 1.1, -84.0), 0.0,
		func() -> bool: return Quest.has_provenance(&"noir", &"stub"))
	check(Quest.has_provenance(&"noir", &"stub"), "the cinema stub is recorded")

	print("[noir] the booth")
	for attempt in 12:
		if Quest.is_step_done(&"heist", &"reach_projection"):
			break
		await _until(func() -> bool: return not Transitions.busy, 10.0)
		await _walk_to(Vector3(1.5, 0.05, -88.0), 10.0)
		await _walk_to(Vector3(0, 0.05, -89.0), 10.0)
		await _walk_to(Vector3(0, 0.05, -95.0), 15.0)
	await frames(6)
	check(Quest.is_step_done(&"heist", &"reach_projection"), "reaching the booth completes reach_projection")
	check(Quest.main_objectives_done(), "all three objectives are done")
	await _tp(Vector3(0, 0.05, -95.5), Vector3(0, 1.2, -97.0))
	await frames(6)
	_tap(&"interact")
	var t0 := Time.get_ticks_msec()
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 40.0)
	var back_after := (Time.get_ticks_msec() - t0) / 1000.0
	check(Quest.has_fragment(&"noir"), "the fragment is recorded")
	check(back_after >= 11.0, "the colour reveal holds for eleven seconds (%.1f s)" % back_after)
	check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "finish() returns to the atrium")

	_sampling = false
	print("[noir] done, %d failure(s)" % _fails)
	Game.quit(1 if _fails > 0 else 0)
