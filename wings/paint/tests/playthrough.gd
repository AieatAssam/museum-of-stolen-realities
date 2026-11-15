extends Playthrough
## The Unfinished Wing by real input only. Part 1 is the mechanic proof on the test course
## (x 600, reached by debug_teleport): surf, chain, bleed, kick, fall, scrape, re-lay, persistence.
## Run: tests/run_playthrough.sh paint
## Waits are counted in physics ticks (120 Hz), not wall time.

const W := &"paint"

var w: Wing


func run() -> void:
	await enter(W)
	w = Game.wing
	await _course()
	await _wing()


# --- helpers ----------------------------------------------------------------------------------

func _p() -> Player:
	return Game.player


## Wait up to `n` physics ticks for `cond`. With `what`, a timeout is a failed check.
func ticks(n: int, cond: Callable = Callable(), what: String = "") -> bool:
	for i in n:
		if cond.is_valid() and cond.call():
			break
		await get_tree().physics_frame
	var ok: bool = cond.call() if cond.is_valid() else true
	if what != "":
		check(ok, what)
	return ok


## Steer toward `target` holding forward (also while surfing) until `cond` or `n` ticks.
func steer(target: Vector3, n: int, cond: Callable, sprint: bool = false) -> bool:
	if sprint:
		Input.action_press(&"sprint")
	var ok := false
	for i in n:
		if cond.call():
			ok = true
			break
		var p := _p()
		if p == null:
			break
		var to := target - p.global_position
		var err := wrapf(atan2(-to.x, -to.z) - p.yaw, -PI, PI)
		var mm := InputEventMouseMotion.new()
		mm.relative = Vector2(-err / deg_to_rad(float(Save.settings["mouse_sensitivity"])) * 0.5, 0)
		mm.screen_relative = mm.relative
		Input.parse_input_event(mm)
		Input.action_press(&"move_forward")
		await get_tree().physics_frame
	Input.action_release(&"move_forward")
	Input.action_release(&"sprint")
	return ok or cond.call()


func surfing(sid: String = "") -> bool:
	var p := _p()
	if p == null or p.mode_name() != &"surf":
		return false
	return sid == "" or w.surf.stroke.sid == sid


func _mode() -> StringName:
	return _p().mode_name() if _p() else &""


func teleport(pos: Vector3, look: Vector3) -> void:
	if _mode() == &"surf":
		await tap(&"crouch")   # step off first, or the rail keeps her
	Game.debug_teleport(pos, look)
	await ticks(6)


# --- part 1: the test course --------------------------------------------------------------------

func _course() -> void:
	var O: Vector3 = w.COURSE
	var orig: Callable = w.surf.on_event
	w.surf.on_event = func(ev: String, d: Variant) -> void:
		print("    [surf] %s %s at %s v=%.1f chain=%d" % [ev, d.sid if d else "", _p().global_position, w.surf.speed, w.surf.chain])
		orig.call(ev, d)
	await teleport(w.pts["course_start"], O + Vector3(0, 1.5, -20))
	# board by walking onto the first stroke
	await steer(O + Vector3(0, 0, -20), 360, func() -> bool: return surfing("course_a"))
	check(surfing("course_a"), "walking onto a wet stroke boards it")
	var entry: float = w.surf.speed
	check(entry >= 9.5, "entry speed jumps on boarding (%.1f m/s)" % entry)
	# hands off: speed bleeds slowly
	Input.action_release(&"move_forward")
	var s0: float = w.surf.speed
	await ticks(120)
	var bled: float = s0 - w.surf.speed
	check(bled > 0.2 and bled < 1.5, "speed bleeds slowly with no input (%.2f m/s in 1 s)" % bled)
	# forward: chain onto B and C through the air
	await steer(O + Vector3(0, -2, -80), 900, func() -> bool: return surfing("course_c"))
	check(surfing("course_c"), "jumped the gaps from stroke to stroke without touching ground")
	check(w.surf.chain >= 3, "chain counts boarded strokes (chain %d)" % w.surf.chain)
	# kick off the impasto ridge (s 17) up to pad 1, which a plain launch cannot reach
	await steer(O + Vector3(0, -2, -80), 600, func() -> bool: return surfing("course_c") and w.surf.s > 16.2)
	await tap(&"jump")
	check(w.surf.kicked, "jumping at an impasto ridge kicks")
	await ticks(400, func() -> bool: return _p().is_on_floor() and _mode() == &"paint")
	var pos := _p().global_position
	check(pos.y > 0.3 and pos.z < O.z - 79.0, "the kick reaches the raised pad (%s)" % pos)

	# a fall from a stroke is caught: back on the last stroke within seconds
	await teleport(O + Vector3(0, -2.4, -60), O + Vector3(0, -2.4, -80))
	await ticks(60, func() -> bool: return surfing("course_c"))
	await steer(O + Vector3(0, -2, -90), 600, func() -> bool: return not surfing())
	var t0 := Engine.get_physics_frames()
	await ticks(600, func() -> bool: return _p().global_position.y < -9.0)
	await ticks(360, func() -> bool: return _p().global_position.y > -9.0 and _p().input_enabled)
	var dt := (Engine.get_physics_frames() - t0) / 120.0
	check(_p().global_position.y > -4.0 and dt < 4.0, "missed the pad, fell, respawned on the stroke in %.1f s" % dt)

	# the knife: scrape a stroke, carry it, lay it as a bridge
	w.canvas.has_knife = true   # fixture: in the wing it is taken from the Old Tree's crown
	await teleport(w.pts["pad1"], w.pts["pad2"])
	var red: Node3D = w.canvas.get_stroke("course_red")
	await look_at(red.centre())
	await tap(&"secondary")
	check(not red.enabled and w.canvas.load.get("c", "") == "red", "secondary scrapes the stroke onto the knife")
	await walk_to(w.pts["pad1_edge"], 10.0, 0.3)
	await look_at(w.pts["pad2_near"])
	await tap(&"primary")
	var laid: Node3D = w.canvas.get_stroke("laid_1")
	check(laid != null and w.canvas.load.is_empty(), "primary lays the carried paint where she looks")
	await steer(w.pts["pad2"], 600, func() -> bool:
		return _p().global_position.z < w.pts["pad2_near"].z - 1.0 and _p().is_on_floor())
	check(_p().global_position.y > 0.3 and _p().global_position.z < w.pts["pad2_near"].z, "crossed the gap on her own stroke")

	# moved paint stays moved
	await Game.debug_goto(Game.HUB_ID)
	await Game.debug_goto(W)
	await skip_cinematics()
	w = Game.wing
	var back: Node3D = w.canvas.get_stroke("laid_1")
	var gone: Node3D = w.canvas.get_stroke("course_red")
	check(back != null and back.enabled and gone != null and not gone.enabled, "scraped and laid strokes persist across leaving")


# --- part 2: the wing ------------------------------------------------------------------------

func _wing() -> void:
	pass
