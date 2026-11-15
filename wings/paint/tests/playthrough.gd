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

func on_floor() -> bool:
	return _p().is_on_floor() and _mode() == &"paint"


## Scrape the stroke at `at` (looking at it from where she stands).
func scrape(at: Vector3, what: String) -> void:
	await look_at(at)
	await tap(&"secondary")
	check(not w.canvas.load.is_empty(), what)


func lay(at: Vector3, what: String) -> void:
	await look_at(at)
	var n: int = w.canvas.laid_n
	await tap(&"primary")
	check(w.canvas.laid_n > n, what)


## Ride/walk toward `target` holding forward until on the ground past `cond`.
func go(target: Vector3, cond: Callable, n: int = 2400) -> bool:
	return await steer(target, n, func() -> bool: return cond.call() and on_floor())


func _wing() -> void:
	var from := OS.get_environment("PAINT_FROM")   # dev only: resume a later section
	_audit()
	if from == "":
		await _orchard()
		await _windfall()
		await _unpainted()
	if from in ["", "river"]:
		if from != "":
			await _jump_to("windfall", Vector3(0, 0.5, -170))
		await _river()
		await _corrections()
	if from in ["", "pent"]:
		if from != "":
			await _jump_to("pentimento", w.pts["rim"])
		await _pentimento()
	if from in ["", "pent", "green"]:
		if from != "":
			w.pent = 3
			w._apply_pent(true)
			await _jump_to("pentimento", Vector3(6, 0, -351))
		await _green_and_horizon()
	if from in ["", "pent", "green", "edge"]:
		if from != "":
			await _jump_to("edge", Vector3(-214, 21.6, -171.5))
		await _edge_and_heist()


func _jump_to(cp: String, pos: Vector3) -> void:
	w.canvas.has_knife = true
	await teleport(pos, pos + Vector3(0, 0, -5))


func _orchard() -> void:
	await teleport(w.pts["start"], Vector3(0, 0, -30))
	await go(Vector3(0, 0, -50), func() -> bool: return _p().global_position.z < -44.0)
	check(Quest.is_step_done(&"orchard", &"ride"), "rode the shore bough over the first void")
	await steer(Vector3(0, -2, -140), 2400, func() -> bool: return surfing("bough_3") and w.surf.s > 16.2)
	check(Quest.is_step_done(&"orchard", &"chain"), "chained three boughs")
	await tap(&"jump")
	await ticks(480, on_floor)
	check(Quest.is_step_done(&"orchard", &"crown"), "kicked off the impasto to the crown (%s)" % _p().global_position)
	await walk_to(Vector3(0.5, 0.5, -145), 10.0, 0.4)
	await use(w.uses["knife"])
	check(w.canvas.has_knife, "took the painter's knife")
	await scrape(w.canvas.get_stroke("stray_bough").centre() + Vector3(0, 0.7, 0), "scraped the stray bough")
	await walk_to(w.pts["crown_edge"], 10.0, 0.3)
	await lay(w.pts["windfall_near"], "laid it across the gap")
	await go(Vector3(0, 0.5, -166), func() -> bool: return _p().global_position.z < -160.0)
	check(Quest.is_done(&"orchard"), "orchard objective done by play")


func _windfall() -> void:
	# the test strip: sealed blue; red across it makes violet, which sinks (Provenance: swatch)
	await walk_to(Vector3(10.5, 0.5, -183.5), 15.0, 0.4)
	await scrape(Vector3(10.5, 0.62, -186), "scraped red from the tube")
	await walk_to(w.pts["strip_stand"], 10.0, 0.3)
	await lay(Vector3(17.5, 1.0, -183), "laid red across the blue test strip")
	await ticks(360)
	var strip: Node3D = w.canvas.get_stroke("test_strip")
	check(strip.colour == "violet" and strip.position.y < -3.0, "violet: the strip sank")
	await walk_to(Vector3(20.2, 0.5, -183), 10.0, 0.4)
	await use(w.uses["swatch"].get_parent())
	await ticks(420, func() -> bool: return Quest.has_provenance(W, &"swatch"))
	check(Quest.has_provenance(W, &"swatch"), "Provenance: the dried swatch")


func _unpainted() -> void:
	for i in 2:
		await walk_to(Vector3(-12, 0.5, -169.2), 20.0, 0.4)
		await scrape(w.pts["lamp_oil"], "took yellow from the lamp oil (%d)" % i)
		var stand: Vector3 = w.pts["unpainted_edge"] if i == 0 else w.pts["pencil_1_end"]
		await go(stand, func() -> bool: return absf(_p().global_position.x - stand.x) < 0.8, 2400)
		await lay(stand + Vector3(-8, 1.62, 0), "laid light into the dark (%d)" % i)
		await ticks(30)
	check(w.canvas.get_stroke("pencil_2").enabled, "the underdrawing is solid in the light")
	await go(w.pts["pedestal"], func() -> bool: return _p().global_position.x < -56.0)
	await use(w.uses["stub"].get_parent())
	await ticks(420, func() -> bool: return Quest.has_provenance(W, &"stub"))
	check(Quest.has_provenance(W, &"stub"), "Provenance: the pencil stub")
	# back to the windfall, over her own light
	await go(Vector3(-5, 0.5, -172), func() -> bool: return _p().global_position.x > -12.0)


func _river() -> void:
	# float: blue laid on water floats; ride it across
	await walk_to(Vector3(-17, 0.5, -183.6), 20.0, 0.4)
	await scrape(w.pts["bank_well"], "took ultramarine from the bank")
	await walk_to(w.pts["bank"], 15.0, 0.3)
	await lay(w.pts["beach"], "laid blue on the river")
	var raft: Node3D = w.canvas.get_stroke("laid_%d" % w.canvas.laid_n)
	check(raft != null and raft.rec.has("fl"), "the blue floats")
	await go(w.pts["terrace"], func() -> bool: return _p().global_position.z < -207.0)
	check(Quest.is_step_done(&"river", &"float"), "crossed the river on floating paint")
	# dam: a blue wall across the inlet; the basin drains to its bed
	await walk_to(Vector3(18, 0, -230.6), 20.0, 0.4)
	await scrape(Vector3(18, 0.12, -234), "took blue from the terrace well")
	await walk_to(w.pts["dam_stand"], 15.0, 0.3)
	await lay(Vector3(40, 12, -228), "planted a blue wall in the inlet")
	await ticks(900, func() -> bool: return Quest.is_step_done(&"river", &"dam"))
	check(Quest.is_step_done(&"river", &"dam"), "the wall holds the water back; the basin drains")
	await walk_to(Vector3(24, 0, -236), 10.0, 0.6)   # round the end of her own wall
	await walk_to(Vector3(40, -3, -228), 15.0, 0.6)
	await walk_to(w.pts["bed"], 15.0, 0.6)
	await go(Vector3(76, 0, -228), func() -> bool: return _p().global_position.x > 71.0)
	check(_p().global_position.y > -0.5, "up the ramp out of the drained basin")
	# burn: red laid into the varnish burns through it
	await walk_to(Vector3(72, 0, -238.6), 15.0, 0.4)
	await scrape(w.pts["cinnabar"], "took red from the cinnabar")
	await walk_to(w.pts["varnish_stand"], 15.0, 0.3)
	await lay(Vector3(80, 1, -228), "laid red into the varnish")
	await ticks(240)
	check(Quest.is_step_done(&"river", &"burn"), "hot paint burned through the varnish")
	# light: yellow makes the cave's underdrawing solid
	await walk_to(Vector3(92.5, 0, -241.6), 20.0, 0.4)
	await scrape(w.pts["cave_lamp"], "took yellow in the cave")
	await walk_to(w.pts["cave_edge"], 15.0, 0.3)
	await lay(Vector3(110, 1.62, -228), "laid light at the cave's edge")
	check(w.canvas.get_stroke("cave_pencil").enabled, "the underdrawing holds in the light")
	await go(Vector3(127, 0, -228), func() -> bool: return _p().global_position.x > 126.0)   # the pencil is 2 m wide: keep to it
	check(Quest.is_done(&"river"), "river objective done by play")
	# the outflow carries her to the Corrections
	await walk_to(Vector3(132, 0, -234), 10.0, 0.5)
	await steer(Vector3(132, 0.25, -250), 900, func() -> bool: return surfing("outflow"))
	check(surfing("outflow"), "boarded the outflow")
	await go(Vector3(4, 0, -285), func() -> bool: return _p().global_position.z < -272.0, 4800)
	check(_p().global_position.z < -272.0 and _p().global_position.y > -0.5, "rode the outflow down to the Corrections")


func _corrections() -> void:
	# scraping the hand reveals its earlier pose: a ramp to a ledge (Provenance: the ferrule)
	await walk_to(w.pts["hand_stand"], 15.0, 0.4)
	await scrape(Vector3(16, 3, -287), "scraped the half-finished hand")
	check(w.canvas.get_stroke("figure_hand_early").enabled, "an earlier pose shows through")
	await lay(Vector3(16, 0, -275), "set the umber down")
	await walk_to(Vector3(12, 0, -288.2), 15.0, 0.4)
	await go(Vector3(24, 3, -299), func() -> bool: return _p().global_position.y > 2.8)
	await walk_to(Vector3(25.5, 3, -301), 10.0, 0.6)
	await use(w.uses["ferrule"].get_parent())
	await ticks(420, func() -> bool: return Quest.has_provenance(W, &"ferrule"))
	check(Quest.has_provenance(W, &"ferrule"), "Provenance: the ferrule")
	# violet: red into the fixed blue barrier, and it sinks
	await walk_to(Vector3(18, 0, -308), 15.0, 0.6)
	await walk_to(Vector3(10, 0, -319.6), 20.0, 0.4)
	await scrape(w.pts["corr_red"], "took red in the Corrections")
	await walk_to(w.pts["barrier_stand"], 15.0, 0.3)
	await lay(Vector3(0, 1, -336), "laid red into the blue barrier")
	await ticks(360)
	check(w.canvas.get_stroke("barrier").position.y < -3.0, "violet: the barrier sank")
	await walk_to(w.pts["rim"], 15.0, 0.5)


func _arena(angle: float, r: float) -> Vector3:
	return w.PENT_C + Vector3(sin(angle), 0, cos(angle)) * r


## Walk the arena by its free inner ring (inside the hills' raised ends, outside the crack), then
## out along a clear spoke, then along the rim onto hill k's foot.
func _to_hill(k: int) -> void:
	var a: float = w.hill_angle(k)
	var d: Vector3 = _p().global_position - w.PENT_C
	var ang := atan2(d.x, d.z)
	if Vector2(d.x, d.z).length() > 14.0:
		await walk_to(_arena(ang, 11.0), 20.0, 1.0)
	var spoke := a - TAU / 12.0 if absf(wrapf(a - TAU / 12.0 - ang, -PI, PI)) < absf(wrapf(a + TAU / 12.0 - ang, -PI, PI)) else a + TAU / 12.0
	var left := wrapf(spoke - ang, -PI, PI)
	while absf(left) > 0.05:
		var step := clampf(left, -0.5, 0.5)
		ang += step
		left -= step
		await walk_to(_arena(ang, 11.0), 10.0, 1.0)
	await walk_to(_arena(spoke, 31.5), 20.0, 1.0)
	await steer(_arena(a, 33.4), 900, func() -> bool: return surfing())


func _pentimento() -> void:
	var tries := 0
	var t0 := Engine.get_physics_frames()
	while w.pent < 3 and tries < 24 and _p():
		tries += 1
		var layer: int = w.pent
		var target: Node3D = null
		for sd: Node3D in w.seals[layer]:
			if sd.enabled:
				target = sd
				break
		if target == null:
			await ticks(30)
			continue
		var k := int(String(target.sid).get_slice("_", 2))
		var hid := "hill_%d" % k
		if not surfing():
			await _to_hill(k)
		if not surfing(hid):
			print("  missed hill %d at %s (%s)" % [k, _p().global_position, _mode()])
			if surfing():
				await tap(&"crouch")
			await ticks(240, on_floor)
			continue
		await steer(w.PENT_C, 900, func() -> bool: return not surfing(hid) or w.surf.s > 10.5)
		if surfing(hid):
			await look_at(target.centre() + Vector3(0, 0.75, 0), 30)
			await tap(&"secondary")
			check(not target.enabled, "scraped a seal riding the buckling hill (layer %d)" % layer)
		# ride on: the hill throws her off its raised end onto the inner ring
		await ticks(600, func() -> bool: return on_floor() and not w._respawning)
	var mins := (Engine.get_physics_frames() - t0) / 120.0 / 60.0
	check(w.pent == 3, "three layers removed: the first composition (%d tries, %.1f min)" % [tries, mins])
	check(Quest.is_step_done(&"edge", &"pentimento"), "pentimento step done by play")
	check(w.canvas.get_stroke("kinder_road").enabled, "a kinder road appears")


func _green_and_horizon() -> void:
	await walk_to(Vector3(6, 0, -352.5), 20.0, 0.5)
	await go(Vector3(4, 1, -170), func() -> bool: return _p().global_position.z > -190.0, 4800)
	check(_p().global_position.z > -190.0, "rode the kinder road back to the Old Tree")
	check(w.canvas.get_stroke("old_tree").colour == "blue", "the Old Tree is blue again underneath")
	await walk_to(Vector3(-2, 0.5, -178.6), 15.0, 0.4)
	await scrape(Vector3(-2, 0.62, -181), "took yellow from the pear")
	check(w.canvas.load.get("c", "") == "yellow", "the pear is yellow")
	await walk_to(Vector3(8, 0.5, -171.2), 15.0, 0.3)
	await lay(Vector3(12, 1.2, -171.2), "laid yellow across the blue trunk")
	check(Quest.is_step_done(&"edge", &"green"), "the Old Tree grows green")
	await walk_to(Vector3(10.6, 0.5, -171.2), 6.0, 0.5)   # into the column: forward climbs
	await steer(Vector3(16, 25, -171.2), 1800, func() -> bool: return _p().global_position.y > 23.5 and on_floor())
	check(_p().global_position.y > 23.5, "climbed the green to the lookout (y=%.1f)" % _p().global_position.y)
	await walk_to(Vector3(13, 24.4, -164.5), 10.0, 0.5)
	await walk_to(Vector3(9.5, 24.4, -164.5), 10.0, 0.5)
	await walk_to(Vector3(9.5, 24.4, -171.5), 10.0, 0.4)
	await go(Vector3(-212, 22, -171.5), func() -> bool: return _p().global_position.x < -206.0, 4800)
	check(_p().global_position.x < -206.0, "rode the horizon to the edge")
	check(Quest.is_done(&"edge"), "edge objective done by play")


func _edge_and_heist() -> void:
	for q: Vector3 in w.pts["passage"]:
		await walk_to(q, 15.0, 0.4)
	await walk_to(w.pts["ledge"], 10.0, 0.5)
	check(w.revealed, "through the passage: the museum wall, thirty storeys")
	await walk_to(w.pts["fragment"] + Vector3(1.4, -0.8, 0), 10.0, 0.4)
	await use(w.uses["fragment"].get_parent())
	await ticks(600, func() -> bool: return w.heist and _p().input_enabled)
	check(Quest.has_fragment(W) and w.heist, "lifted the first stroke; the long stroke home is wet")
	var back: Array = w.pts["passage"].duplicate()
	back.reverse()
	for q: Vector3 in back:
		await walk_to(q, 15.0, 0.4)
	# the heist: board, take the red branch over its gap, jump the knot, home before it dries
	await steer(Vector3(-205, 21, -166), 1200, func() -> bool: return surfing("heist_0"))
	await steer(Vector3(-100, 12, -112), 2400, func() -> bool: return surfing("heist_red_2") or surfing("heist_final"))
	check(w.heist_ridden.has("heist_red_1"), "took the red branch")
	await steer(Vector3(-20, 3, -30), 2400, func() -> bool: return surfing("heist_final") and w.surf.s > 15.5)
	await tap(&"jump")
	check(w.surf.last_left != null and w.surf.last_left.sid == "heist_final", "jumped the varnish knot")
	await steer(Vector3(0, 0, 10), 2400, func() -> bool: return Game.wing == null or Game.wing.wing_id != W or not w.heist)
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0, "home on the shore: finish() returns to the atrium")
	check(Quest.has_fragment(W), "fragment recorded")
	check(Save.data["provenances"].get(String(W), []).size() == 3, "all three provenances recorded")


func _audit() -> void:
	var labels := 0
	var long := 0
	for pl: Placard in w.find_children("*", "Placard", true, false):
		if pl.acquisition.to_lower().begins_with("acq. no. 001"):
			labels += 1
			if pl.body.split(" ", false).size() > 40:
				long += 1
				print("  long placard: ", pl.title)
	check(labels >= 12 and long == 0, "%d museum labels in the wing, none over 40 words" % labels)
	check(w.get_node("ShotMarks").get_child_count() == 12 and get_tree().get_nodes_in_group(&"shot_marks").size() == 12, "12 shot marks")
	check(w.provenances().size() == 3, "three provenances declared")
