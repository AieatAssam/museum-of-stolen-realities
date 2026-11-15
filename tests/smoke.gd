extends Playthrough
## Headless smoke test:  tests/run_smoke.sh   (fails on any failed check, script error or leak)
## Boots, starts a new game from the title with ui_accept, walks into the template wing with real
## input, plays it, runs the core regression checks (_hardening), loads every existing wing and
## drives its objectives through the debug API, completes all six, runs both finales.


func run() -> void:
	print("[smoke] title -> New Game with ui_accept")
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(1.5)
	await tap(&"ui_accept")  # the focused first button is New Game when there is no save
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
	check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "new game lands in the atrium")
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await until(func() -> bool: return not Cinematics.playing, 10.0)
	check(Save.data["hub"]["seen_intro"] == true, "intro cinematic ran and was recorded")
	check(Game.player != null and Game.player.is_inside_tree(), "player spawned in atrium")

	# --- real input: walk through the conservation door into the template wing ---
	print("[smoke] walk into the template wing with scripted input")
	var hub := Game.wing
	var door: Vector3 = hub.call("entry_point", &"_template")
	await until(func() -> bool: return not Transitions.busy, 10.0)  # the arrival fade is still running
	await walk_to(door, 25.0, 0.05)  # keep walking into the trigger
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"_template", 15.0)
	check(Game.wing != null and Game.wing.wing_id == &"_template", "walking through the studio door entered the template wing (player at %s, door %s)" % [Game.player.global_position if Game.player else Vector3.ZERO, door])
	if Cinematics.playing:
		Cinematics.skip()
	await until(func() -> bool: return not Cinematics.playing, 10.0)

	if Game.wing and Game.wing.wing_id == &"_template":
		var w := Game.wing
		check(Quest.objectives.size() == 3 and Quest.provenances.size() == 3, "template declared objectives and provenances")
		# walk forward a few metres with real input and check we actually moved
		var p0 := Game.player.global_position
		Input.action_press(&"move_forward")
		await frames(Engine.physics_ticks_per_second)  # one simulated second, however slow the machine
		Input.action_release(&"move_forward")
		check(Game.player.global_position.distance_to(p0) > 2.0, "forward input moves the player (%.2f m)" % Game.player.global_position.distance_to(p0))
		# interact with a lamp: face it, press E
		var lamp: Node3D = w.get_node("Lamps/lamp_b")
		Game.debug_teleport(lamp.global_position + Vector3(0, 0, 2.0), lamp.global_position + Vector3(0, 0.9, 0))
		await frames(6)
		await tap(&"interact")
		await frames(4)
		check(Quest.is_step_done(&"lamps", &"lamp_b"), "pressing interact on a lamp completes its step")
		Game.debug_complete_objective(&"_template", &"lamps")
		# void fall -> respawn
		Game.debug_teleport(Vector3(0, -30, -13.5))
		await until(func() -> bool: return Game.player.global_position.y > -1.0, 8.0)
		await until(func() -> bool: return not Transitions.busy, 5.0)  # the respawn fade
		await seconds(0.5)
		check(Game.player.global_position.y > -1.0, "void fall respawns at checkpoint")
		Game.debug_complete_objective(&"_template", &"cross")
		await frames(4)
		check(Quest.main_objectives_done(), "template main objectives done")
		var frag: Node3D = w.get_node("FragmentSpot")
		check(frag.visible, "fragment appears when objectives are done")
		Game.debug_teleport(frag.global_position + Vector3(0, -1.3, 1.6), frag.global_position)
		await frames(6)
		await tap(&"interact")
		await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
		check(Quest.has_fragment(&"_template"), "template fragment recorded")
		check(Game.wing != null and Game.wing.wing_id == Game.HUB_ID, "finish() returned to the atrium")
		check(Quest.fragment_count() == 0, "template fragment does not count towards Exhibit 0")

	await _hardening()

	# --- every wing in the registry ---
	for info: WingInfo in Game.registry.exhibits():
		if not info.scene_exists():
			var ok: bool = await Game.enter_wing(info.id)
			check(not ok and Game.wing.wing_id == Game.HUB_ID, "%s: missing scene shows 'under restoration' without crashing" % info.id)
			continue
		print("[smoke] wing ", info.id)
		await Game.debug_goto(info.id)
		check(Game.wing != null and Game.wing.wing_id == info.id, "%s loads" % info.id)
		if Cinematics.playing:
			Cinematics.skip()
		await until(func() -> bool: return not Cinematics.playing, 10.0)
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
	await until(func() -> bool: return not Cinematics.playing, 30.0)
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
		await until(func() -> bool: return done["ended"], 40.0)
		check(done["ended"] and Save.data["ending"] == String(choice), "finale '%s' plays to the end" % choice)
		if choice == &"restore":
			# back to a fresh atrium for the other branch
			await until(func() -> bool: return Game.state == Game.State.TITLE, 30.0)
			check(Game.state == Game.State.TITLE, "restore ending returns to the title")
			await until(func() -> bool: return not Transitions.busy, 10.0)
			Save.load_game()
			Save.data["ending"] = ""
			Save.save_game()
			await Game.continue_game()
			await until(func() -> bool: return Game.wing != null, 20.0)
			await seconds(1.0)
			await until(func() -> bool: return not Cinematics.playing, 30.0)
			hub = Game.wing
			check(hub != null, "continue after an ending reloads the atrium")
			if hub == null:
				break



## Regressions for the core hardening pass (each was a real bug).
func _hardening() -> void:
	print("[smoke] hardening regressions")
	# 1. a goto issued while a transition is running waits for it instead of being dropped
	Game.return_to_hub()  # not awaited: the transition is now busy
	await frames(1)
	var t0 := Time.get_ticks_msec()
	var ok: bool = await Game.debug_goto(&"_template")
	check(ok and Game.wing.wing_id == &"_template", "goto during a transition queues and arrives (%d ms)" % (Time.get_ticks_msec() - t0))
	await skip_cinematics()

	# 2. leaving mid-cinematic: no freed-callable call, bars/skip/card cleared, input back
	var w := Game.wing
	Cinematics.play([{"card": "Leaving mid-card.", "t": 6.0}, {"call": w.on_exit, "always": true}])
	await seconds(0.8)
	ok = await Game.debug_goto(Game.HUB_ID)
	await frames(3)
	check(ok and not Cinematics.playing, "a scene change aborts the running cinematic")
	check(not Cinematics.overlay_visible(), "letterbox, skip label and card cleared after the abort")
	check(Game.player.input_enabled and Game.player.look_enabled, "player input restored after the abort")

	# 3. placards: toast in the lower-left, clear of the centre, hidden under the reader
	ok = await Game.debug_goto(&"_template")
	await skip_cinematics()
	await until(func() -> bool: return not Placards.toast_visible(), 15.0)
	var forty := "word ".repeat(40).strip_edges()
	Placards.toast(Placard.fields("A forty-word placard", "Undated", "Words", "Acq. No. 000-T", forty))
	await until(func() -> bool: return Placards.toast_visible(), 5.0, "toast appears")
	await seconds(0.8)
	var vs := get_viewport().get_visible_rect().size
	var r := Placards.toast_rect()
	check(r.position.y >= vs.y * 0.6 and r.end.y <= vs.y and r.end.x < vs.x * 0.5,
		"40-word toast sits in the lower-left, clear of the centre (%s in %s)" % [r, vs])
	Placards.read(Placard.fields("Reader", "", "", "", "Text."))
	await frames(3)
	check(Placards.is_reading() and not Placards.toast_visible(), "toast hides under the reader")
	Placards.close_reader()
	Placards.clear()

	# 4. stairs: 0.18 m and 0.35 m risers climbed by walking, camera height smoothed
	Game.debug_teleport(Vector3(2.5, 0.05, 2.2), Vector3(2.5, 1.0, -10))
	await frames(4)
	var cam := Game.player.camera
	var last := cam.global_position.y
	var worst := 0.0  # camera vertical speed, m/s; counted in physics ticks so a slow machine walks as far
	Input.action_press(&"move_forward")
	var ticks := Engine.get_physics_frames() + 180
	var tick := Engine.get_physics_frames()
	# stop on the top landing (z -2.6): past it the player walks off the far edge and falls
	while Engine.get_physics_frames() < ticks and Game.player.global_position.z > -2.6:
		await get_tree().process_frame
		var n := Engine.get_physics_frames() - tick
		if n == 0:
			continue
		# over the longer of the frame's real time and its simulated ticks: a slow frame may move
		# the eye further (its smoothing step is longer), which is not a snap
		var dt := maxf(get_process_delta_time(), float(n) / Engine.physics_ticks_per_second)
		var rate := absf(cam.global_position.y - last) / dt
		worst = maxf(worst, rate)
		last = cam.global_position.y
		tick += n
	Input.action_release(&"move_forward")
	var pp := Game.player
	check(pp.global_position.y > 1.7, "walked up the stairs (at %s, state %d, input %s, mode %s)" % [pp.global_position, Game.state, pp.input_enabled, pp.mode_name()])
	check(worst < 15.0, "camera rises smoothly on steps (max %.1f m/s; a snapped 0.35 m riser reads %.0f)" % [worst, 0.35 * Engine.physics_ticks_per_second])
	ok = await Game.debug_goto(Game.HUB_ID)
	await skip_cinematics()
