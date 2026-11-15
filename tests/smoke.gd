extends Node
## Headless smoke test. Run:  tests/run_smoke.sh   (wraps the command below and fails on any
## script error in the log)
##   Godot --headless --path . tests/smoke.tscn
## Boots, starts a new game (intro skipped), walks into the template wing with real input,
## completes it, returns, loads every existing wing and drives its objectives through the debug
## API, completes all six, runs both finales. Exits 1 on the first failed check.

var _fails: int = 0


func _ready() -> void:
	if get_tree().current_scene == self:
		# The current scene is freed on every scene change; run from a node parented to root.
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "SmokeRunner"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://smoke_save.json"
	_run.call_deferred()


func check(cond: bool, what: String) -> void:
	if cond:
		print("  ok   ", what)
	else:
		_fails += 1
		push_error("SMOKE FAIL: " + what)
		print("  FAIL ", what)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	print("[smoke] title -> New Game with ui_accept")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(1.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	await seconds(0.5)
	_tap(&"ui_accept")  # the focused first button is New Game when there is no save
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
	check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "new game lands in the atrium")
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	check(Save.data["hub"]["seen_intro"] == true, "intro cinematic ran and was recorded")
	check(Game.player != null and Game.player.is_inside_tree(), "player spawned in atrium")

	# --- real input: walk through the conservation door into the template wing ---
	print("[smoke] walk into the template wing with scripted input")
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	var hub := Game.wing
	var door: Vector3 = hub.call("entry_point", &"_template")
	await _walk_to(door, 25.0)
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"_template", 15.0)
	check(Game.wing != null and Game.wing.wing_id == &"_template", "walking through the studio door entered the template wing")
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)

	if Game.wing and Game.wing.wing_id == &"_template":
		var w := Game.wing
		check(Quest.objectives.size() == 3 and Quest.provenances.size() == 3, "template declared objectives and provenances")
		# walk forward a few metres with real input and check we actually moved
		var p0 := Game.player.global_position
		Input.action_press(&"move_forward")
		await seconds(1.0)
		Input.action_release(&"move_forward")
		check(Game.player.global_position.distance_to(p0) > 2.0, "forward input moves the player (%.2f m)" % Game.player.global_position.distance_to(p0))
		# interact with a lamp: face it, press E
		var lamp: Node3D = w.get_node("Lamps/lamp_b")
		Game.debug_teleport(lamp.global_position + Vector3(0, 0, 2.0), lamp.global_position + Vector3(0, 0.9, 0))
		await frames(6)
		_tap(&"interact")
		await frames(4)
		check(Quest.is_step_done(&"lamps", &"lamp_b"), "pressing interact on a lamp completes its step")
		Game.debug_complete_objective(&"_template", &"lamps")
		# void fall -> respawn
		Game.debug_teleport(Vector3(0, -30, -13.5))
		await seconds(2.0)
		check(Game.player.global_position.y > -1.0, "void fall respawns at checkpoint")
		Game.debug_complete_objective(&"_template", &"cross")
		await frames(4)
		check(Quest.main_objectives_done(), "template main objectives done")
		var frag: Node3D = w.get_node("FragmentSpot")
		check(frag.visible, "fragment appears when objectives are done")
		Game.debug_teleport(frag.global_position + Vector3(0, -1.3, 1.6), frag.global_position)
		await frames(6)
		_tap(&"interact")
		await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
		check(Quest.has_fragment(&"_template"), "template fragment recorded")
		check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "finish() returned to the atrium")
		check(Quest.fragment_count() == 0, "template fragment does not count towards Exhibit 0")

	# --- every wing in the registry ---
	for info: WingInfo in Game.registry.exhibits():
		if not info.scene_exists():
			var ok: bool = await Game.enter_wing(info.id)
			check(not ok and Game.wing.wing_id == Game.HUB_ID, "%s: missing scene shows 'under restoration' without crashing" % info.id)
			continue
		print("[smoke] wing ", info.id)
		await _until(func() -> bool: return not Transitions.busy, 10.0)
		await Game.debug_goto(info.id)
		check(Game.wing != null and Game.wing.wing_id == info.id, "%s loads" % info.id)
		if Cinematics.playing:
			Cinematics.skip()
		await _until(func() -> bool: return not Cinematics.playing, 10.0)
		check(Quest.provenances.size() == 3, "%s declares 3 provenances" % info.id)
		for o: Dictionary in Quest.objectives:
			Game.debug_complete_objective(info.id, StringName(o["id"]))
		check(Quest.main_objectives_done(), "%s objectives completable" % info.id)
		Game.debug_complete_wing(info.id)
		await Game.return_to_hub()

	# --- everything else done via debug, then the finale ---
	for info: WingInfo in Game.registry.exhibits():
		if not Quest.has_fragment(info.id):
			Game.debug_complete_wing(info.id)
	check(Quest.fragment_count() == 6, "all six fragments recovered")
	await Game.return_to_hub()
	await seconds(1.0)
	await _until(func() -> bool: return not Cinematics.playing, 30.0)
	hub = Game.wing
	check(hub.call("finale_available"), "finale available after six fragments")
	for choice: StringName in [&"restore", &"break"]:
		print("[smoke] finale ", choice)
		var done := {"ended": false}  # lambdas capture locals by value; mutate a dict instead
		var on_end := func(_c: StringName) -> void: done["ended"] = true
		hub.connect(&"finale_finished", on_end)
		hub.call("start_finale", choice)
		await seconds(1.0)
		while Cinematics.playing and not done["ended"]:
			Cinematics.skip()
			await seconds(0.5)
		await _until(func() -> bool: return done["ended"], 40.0)
		check(done["ended"] and Save.data["ending"] == String(choice), "finale '%s' plays to the end" % choice)
		if choice == &"restore":
			# back to a fresh atrium for the other branch
			await _until(func() -> bool: return Game.state == Game.State.TITLE, 30.0)
			check(Game.state == Game.State.TITLE, "restore ending returns to the title")
			await _until(func() -> bool: return not Transitions.busy, 10.0)
			Save.load_game()
			Save.data["ending"] = ""
			Save.save_game()
			await Game.continue_game()
			await _until(func() -> bool: return Game.wing != null, 20.0)
			await seconds(1.0)
			await _until(func() -> bool: return not Cinematics.playing, 30.0)
			hub = Game.wing
			check(hub != null, "continue after an ending reloads the atrium")
			if hub == null:
				break

	print("[smoke] done in %.1fs, %d failure(s)" % [(Time.get_ticks_msec() - t0) / 1000.0, _fails])
	DirAccess.remove_absolute(ProjectSettings.globalize_path("user://smoke_save.json"))
	get_tree().quit(1 if _fails > 0 else 0)


func _tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


## Steer with real move input (mouse-look via InputEventMouseMotion) toward a point until a scene
## change starts or we arrive.
func _walk_to(target: Vector3, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	while Time.get_ticks_msec() < end and Game.player and not Transitions.busy:
		var p := Game.player
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
	if Game.player and not Transitions.busy:
		print("  walk_to timed out at ", Game.player.global_position, " target ", target, " mode ", Game.player.mode_name(), " input ", Game.player.input_enabled)
