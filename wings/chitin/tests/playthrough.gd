extends Playthrough
## The Chitin Court, start to finish, by real input: mouse-motion aim, primary to fire and let go,
## secondary to weave and pluck, move keys to walk tightropes, interact for pickups. No teleports.
## Release timing: the line is let go at the forward apex, predicted by integrating the pendulum
## from her state every physics tick (as the swing gate does).

const SilkMode := preload("res://wings/chitin/silk_mode.gd")

var w: Node
var silk: Object
var _section_t := 0


func run() -> void:
	if not await enter(&"chitin"):
		return
	w = Game.wing
	silk = Game.player.modes[&"silk"]
	check(Game.player.mode_name() == &"silk", "silk is the start mode")
	_deliverables()
	await _section("fall", _fall_test)
	await _section("gate", _gate)
	await _section("districts", _districts)
	await _section("shaft", _shaft)
	await _section("foundry", _foundry)
	await _section("gallery", _gallery)
	await _section("general", _general)
	await _section("hall", _hall)
	await _section("heist", _heist)
	for id: StringName in [&"bell", &"guild_key", &"tapestry"]:
		check(Quest.has_provenance(&"chitin", id), "provenance held at the end: %s" % id)


func _section(name_: String, fn: Callable) -> void:
	if fails > 0:
		return
	var t0 := Engine.get_physics_frames()
	await fn.call()
	print("[section] %s  %.1f s game time" % [name_, (Engine.get_physics_frames() - t0) / 120.0])


func _deliverables() -> void:
	var placards := w.find_children("*", "Placard", true, false)
	check(placards.size() >= 12, "at least 12 placards (%d)" % placards.size())
	var long := 0
	for pl: Node in placards:
		if String(pl.get("body")).split(" ", false).size() > 40:
			long += 1
	check(long == 0, "every placard body is 40 words or fewer")
	var marks := w.get_node("ShotMarks").get_children()
	check(marks.size() == 12 and marks.all(func(m: Node) -> bool: return m is Marker3D and m.is_in_group(&"shot_marks")), "12 shot marks in ShotMarks and group shot_marks")
	check(w.provenances().size() == 3, "three provenances")


# --- input helpers -------------------------------------------------------------------------

## Turn the view onto `point` with one mouse-motion event, then let physics see it.
func aim(point: Vector3) -> void:
	var p := Game.player
	var s := deg_to_rad(float(Save.settings["mouse_sensitivity"]))
	var inv := -1.0 if Save.settings["invert_y"] else 1.0
	var d := (point - silk.call("eye")).normalized() as Vector3
	var ey := wrapf(atan2(-d.x, -d.z) - p.yaw, -PI, PI)
	var ep := asin(clampf(d.y, -1.0, 1.0)) - p.pitch
	var mm := InputEventMouseMotion.new()
	mm.relative = Vector2(-ey / s, -ep / s * inv)
	mm.screen_relative = mm.relative
	Input.parse_input_event(mm)
	await frames(2)


## Press and release in one go (the release lands next frame); does not wait.
func press(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


## Aim at an anchor and press `verb` once the cone has picked it.
func aim_and(node: Node3D, verb: StringName, what: String) -> bool:
	for i in 4:
		await aim(node.global_position)
		if silk.get("target") == node:
			break
	if not check(silk.get("target") == node, "aim picks " + what):
		var t: Node3D = silk.get("target")
		print("    aim miss: at %s v %s, wanted %s, target %s, state %d" % [Game.player.global_position, Game.player.velocity, node.global_position if node else null, t.global_position if t else null, silk.get("state")])
		return false
	press(verb)
	await frames(3)
	return true


## Ticks to the apex of the current upswing heading along `fwd`; -1 when not on one.
func ticks_to_apex(fwd: Vector3) -> int:
	if silk.get("state") != SilkMode.ROPE:
		return -1
	var up := Vector3.UP
	var c: Vector3 = silk.call("pivot")
	var r: Vector3 = silk.call("grip") - c
	var L := r.length()
	var rn := r / L
	var phi := acos(clampf(-rn.dot(up), -1.0, 1.0))
	var t_up := up - rn * rn.dot(up)
	if t_up.length() < 0.01 or r.dot(fwd) < 0.0:
		return -1
	var wv := Game.player.velocity.dot(t_up.normalized()) / L
	if wv <= 0.0 or phi < deg_to_rad(15.0):
		return -1
	var n := 0
	while wv > 0.0 and n < 600:
		wv -= 15.0 / L * sin(phi) * (1.0 / 120.0)
		phi += wv * (1.0 / 120.0)
		n += 1
	return n


## Fire at each anchor in turn (the first from the ground), letting go at each forward apex;
## then wait for the landing. Returns true if she lands with her feet up at `land_y` or above.
func swing_chain(anchors: Array, fwd: Vector3, land_y: float, what: String) -> bool:
	var chain := 0
	for k: int in anchors.size():
		if not await aim_and(anchors[k], &"primary", "%s hook %d" % [what, k + 1]):
			return false
		if not check(silk.get("state") == SilkMode.ROPE, "%s: line %d holds" % [what, k + 1]):
			return false
		chain = maxi(chain, int(silk.get("air_chain")))
		if OS.has_environment("CHITIN_DEBUG"):
			print("      %s k%d fired: rope %.2f dist %.2f pivot %s floor %s" % [what, k, silk.get("rope_len"), (silk.call("grip") as Vector3).distance_to(anchors[k].global_position), silk.call("pivot"), Game.player.is_on_floor()])
		var guard := 0
		while guard < 900 and silk.get("state") == SilkMode.ROPE:
			guard += 1
			if guard % 12 == 0 and OS.has_environment("CHITIN_DEBUG"):
				print("      %s k%d t%d pos %s v %s apex %d" % [what, k, guard, Game.player.global_position, Game.player.velocity, ticks_to_apex(fwd)])
			var n := ticks_to_apex(fwd)
			if n >= 0 and n <= 1:
				break
			await frames(1)
		if silk.get("state") == SilkMode.ROPE:
			press(&"primary")
			await frames(1)
		if k < anchors.size() - 1:
			await frames(10)
	var g := 0
	while g < 720 and silk.get("state") != SilkMode.GROUND:
		g += 1
		await frames(1)
	var y := Game.player.global_position.y
	print("    %s: landed at %s, air chain %d, top releases %d" % [what, Game.player.global_position, chain, silk.get("top_releases")])
	return check(silk.get("state") == SilkMode.GROUND and y > land_y - 0.3, "%s: lands (y %.1f)" % [what, y])


# --- sections ------------------------------------------------------------------------------

func _gate() -> void:
	await walk_to(Vector3(-1.2, 0, 0), 20.0, 0.4)
	await swing_chain([_hook(Vector3(6, 10, 0))], Vector3.RIGHT, -3.0, "first swing")
	check(Quest.is_step_done(&"gate", &"swing"), "gate step done")


## A deliberate fall: walk off the gate's lip into the abyss. She must be back on the gate ledge
## (the last ledge stood on) within two seconds of dropping below the lip.
func _fall_test() -> void:
	await walk_to(Vector3(-2, 0, 0), 20.0, 0.4)
	await frames(40)
	Input.action_press(&"move_forward")
	var t0 := -1
	var low := 99.0
	var back := false
	for i in 1200:
		await frames(1)
		var y := Game.player.global_position.y
		low = minf(low, y)
		if t0 < 0 and y < -1.0:
			t0 = Engine.get_physics_frames()
			Input.action_release(&"move_forward")
		if t0 >= 0 and y > -0.5 and Game.player.global_position.x < 0.5:
			back = true
			break
	var secs := (Engine.get_physics_frames() - t0) / 120.0 if t0 >= 0 else -1.0
	print("    fall test: lowest y %.1f, now at %s" % [low, Game.player.global_position])
	check(t0 >= 0, "fall test: she fell")
	check(back and secs < 2.0, "fall test: back on the gate ledge in %.2f s" % secs)
	await frames(60)


## Pluck at a point on a strand (aim at it, secondary). Returns the strand plucked, if any.
func pluck_at(point: Vector3, what: String) -> bool:
	var got: Array = []
	var cb := func(st: Node) -> void: got.append(st)
	silk.connect(&"plucked", cb)
	await aim(point)
	press(&"secondary")
	await frames(3)
	silk.disconnect(&"plucked", cb)
	return check(not got.is_empty(), "pluck: " + what)


## Weave a line between two pegs: secondary at each.
func weave(a: Node3D, b: Node3D, what: String) -> Node:
	var before: int = (silk.get("strands") as Array).size()
	await aim_and(a, &"secondary", what + " first peg")
	await aim_and(b, &"secondary", what + " second peg")
	var strands: Array = silk.get("strands")
	check(strands.size() > before or strands.size() == SilkMode.MAX_STRANDS, "weave: " + what)
	return strands[-1] if not strands.is_empty() else null


func _districts() -> void:
	# the usher blocks the door until a nearby line is plucked
	await walk_to(Vector3(22, -3, 9), 15.0)
	await pluck_at(Vector3(22, -1.2, 13.3), "the usher's harp line")
	await until(func() -> bool: return (w.get("_usher") as Node3D).position.z > 3.0, 3.0, "the usher steps aside")
	await walk_to(Vector3(26, -3, 0), 10.0, 0.4)
	await walk_to(Vector3(33, -3, 0), 10.0, 0.4)
	check(Quest.is_step_done(&"districts", &"usher"), "past the usher")
	# the light-well: weave a tightrope between its pegs and walk it
	await walk_to(Vector3(38.6, -3, 0), 10.0, 0.3)
	var s := await weave(_hook(Vector3(40.3, -2.95, 0)), _hook(Vector3(51.7, -2.95, 0)), "the light-well tightrope")
	check(s != null and absf(float(s.get("length")) - 11.4) < 0.2, "tightrope is 11.4 m")
	await walk_to(Vector3(55, -3, 0), 15.0, 0.4)
	check(Game.player.global_position.y > -3.3 and Quest.is_step_done(&"districts", &"tightrope"), "walked the tightrope over the well")
	# the moth: pluck its line, it comes down to hang above; swing up to the perch
	await walk_to(Vector3(60, -3, -10), 10.0)
	await pluck_at(Vector3(60, -1.2, -13.3), "the moth's harp line")
	var moth: Node3D = w.get("_moth")
	await until(func() -> bool: return moth.is_in_group(&"silk_anchors") and moth.position.y < 9.2, 4.0, "a moth answers and hangs above")
	await walk_to(Vector3(60, -3, -6), 10.0, 0.3)
	await frames(30)
	await aim_and(moth, &"primary", "the moth")
	var g := 0
	while g < 1200 and not (silk.get("state") == SilkMode.GROUND and Game.player.global_position.y > -0.5):
		g += 1
		if g % 12 == 0 and OS.has_environment("CHITIN_DEBUG"):
			print("      perch t%d st %d pos %s v %s" % [g, silk.get("state"), Game.player.global_position, Game.player.velocity])
		if silk.get("state") == SilkMode.ROPE and ticks_to_apex(Vector3.RIGHT) in [0, 1] and Game.player.global_position.x > 72.0:
			press(&"primary")
		await frames(1)
	check(Game.player.global_position.y > -0.5, "up on the high perch (mantles %d)" % silk.get("mantles"))
	await walk_to(Vector3(77.5, 0, -8), 10.0, 0.5)
	await use(w.find_child("Provenance_bell", true, false) as Node3D)
	await until(func() -> bool: return Quest.has_provenance(&"chitin", &"bell"), 8.0, "provenance: the finger-bell")


func _shaft() -> void:
	# off the perch, to the district rim; the gate course's chain, offset to the rim
	await walk_to(Vector3(72, -3, -4), 10.0)
	await walk_to(Vector3(78.6, -3, 0), 10.0, 0.3)
	await frames(30)
	var chain := [_hook(Vector3(86, 7, 0)), _hook(Vector3(99, 7, 0)), _hook(Vector3(112, 7, 0))]
	var ok := await swing_chain(chain, Vector3.RIGHT, -7.0, "shaft chain")
	check(ok and int(silk.get("best_air_chain")) >= 2 and Quest.is_step_done(&"shaft", &"chain"), "three swings chained without touching ground (air chain %d)" % silk.get("best_air_chain"))
	# step off the balcony's east lip; weave the two hooks while falling and ride the line down
	# the top hook is picked from the lip; the line is finished mid-fall
	await walk_to(Vector3(129.6, -7, 0), 10.0, 0.2)
	await aim_and(_hook(Vector3(132, -10.5, 0)), &"secondary", "zip top hook (from the lip)")
	await look_at(Vector3(140, -9, 0))
	Input.action_press(&"move_forward")
	await until(func() -> bool: return not Game.player.is_on_floor(), 3.0)
	Input.action_release(&"move_forward")
	var fell_at: Vector3 = Game.player.global_position
	await aim_and(_hook(Vector3(131.6, -24, 19)), &"secondary", "zip low hook (mid-fall)")
	if OS.has_environment("CHITIN_DEBUG"):
		print("    zip: left lip at %s, woven at %s state %d" % [fell_at, Game.player.global_position, silk.get("state")])
	var zipped := false
	var g := 0
	while g < 900 and not (silk.get("state") == SilkMode.GROUND and Game.player.global_position.y > -28.5 and Game.player.global_position.y < -20.0 and Game.player.is_on_floor()):
		g += 1
		zipped = zipped or silk.get("state") == SilkMode.ZIP
		if OS.has_environment("CHITIN_DEBUG") and g % 10 == 0 and g < 120:
			print("    zip t%d %s v %s state %d" % [g, Game.player.global_position, Game.player.velocity, silk.get("state")])
		await frames(1)
	check(zipped, "caught the woven line mid-fall and zipped")
	check(Quest.is_step_done(&"shaft", &"zip"), "down the zip to the foundry (at %s)" % Game.player.global_position)


func _foundry() -> void:
	# the clockwork anchor rides a track over the channel; fire as it turns at the east end
	await walk_to(Vector3(139, -28, 49.5), 15.0, 0.3)
	await look_at(Vector3(139, -24, 60))
	var clock: Node3D = w.get("_clock_anchor")
	await until(func() -> bool: return clock.global_position.x > 139.6, 25.0, "the clockwork anchor comes round")
	await swing_chain([clock], Vector3(0, 0, 1), -31.0, "clockwork swing")
	check(Quest.is_step_done(&"foundry", &"clockwork"), "across the channel on a moving anchor")
	# the vault: a six-metre line (the tailors' span) between its pegs, plucked
	await walk_to(Vector3(100, -31, 79.3), 20.0, 0.4)
	await weave(_hook(Vector3(97, -30.95, 77)), _hook(Vector3(103, -30.95, 77)), "the vault's six-metre line")
	await pluck_at(Vector3(100, -30.95, 77), "the vault line")
	await until(func() -> bool: return not (w.get("_vault_door") as Node3D).visible, 3.0, "the vault opens to the queen's span")
	await walk_to(Vector3(100, -31, 72), 10.0, 0.4)
	await walk_to(Vector3(99, -31, 68.5), 10.0, 0.4)
	await use(w.find_child("Provenance_guild_key", true, false) as Node3D)
	await until(func() -> bool: return Quest.has_provenance(&"chitin", &"guild_key"), 8.0, "provenance: the guild key")
	await walk_to(Vector3(100, -31, 76), 10.0, 0.4)
	# the guild door: the eight-metre standard
	await walk_to(Vector3(114, -31, 70), 15.0, 0.4)
	await weave(_hook(Vector3(110, -30.95, 74)), _hook(Vector3(118, -30.95, 74)), "the guild's eight-metre line")
	await pluck_at(Vector3(114, -30.95, 74), "the guild line")
	await until(func() -> bool: return Quest.is_step_done(&"foundry", &"door"), 3.0, "the guild door opens")
	await walk_to(Vector3(130, -31, 78), 15.0, 0.5)
	await walk_to(Vector3(130, -31, 84), 10.0, 0.5)


func _gallery() -> void:
	await walk_to(Vector3(100, -31, 91), 20.0, 0.5)
	await walk_to(Vector3(90, -31, 91), 10.0, 0.5)
	await walk_to(Vector3(67, -31, 96.5), 20.0, 0.5)
	await use(w.find_child("Provenance_tapestry", true, false) as Node3D)
	await until(func() -> bool: return Quest.has_provenance(&"chitin", &"tapestry"), 8.0, "provenance: the tapestry hem")


## The Locksmith General: three phrases, swung south over the arena's pit, one key per phrase.
func _general() -> void:
	await walk_to(Vector3(40, -31, 98), 20.0, 0.5)
	await until(func() -> bool: return int(w.call("arena_phrase")) == 0, 3.0, "the first phrase begins")
	var fwd := Vector3(0, 0, -1)
	await walk_to(Vector3(40, -31, 96.6), 10.0, 0.25)
	await look_at(Vector3(40, -25, 88))
	await swing_chain([w.get("_keys")[0]], fwd, -34.0, "phrase 1")
	await until(func() -> bool: return int(w.call("arena_phrase")) == 1, 3.0, "key 1 turned, the second phrase begins")
	var segs: Array = w.get("_arena_segs")
	await walk_to(Vector3(40, -34, 68.6), 10.0, 0.25)
	await look_at(Vector3(40, -28, 60))
	await swing_chain(segs[1], fwd, -38.0, "phrase 2")
	await until(func() -> bool: return int(w.call("arena_phrase")) == 2, 3.0, "key 2 turned, the third phrase begins")
	await walk_to(Vector3(40, -38, 30.6), 10.0, 0.25)
	await look_at(Vector3(40, -32, 22))
	await swing_chain(segs[2], fwd, -42.0, "phrase 3")
	await until(func() -> bool: return Quest.is_done(&"general"), 3.0, "the General is held by her own keys")


## Down the processional stair, through the curtain, under the eye; open the case, take the fragment.
func _hall() -> void:
	await walk_to(Vector3(50, -42, -12), 15.0, 0.5)
	await walk_to(Vector3(57, -42, -12), 10.0, 0.4)
	await walk_to(Vector3(78, -70, -12), 30.0, 0.4)
	await until(func() -> bool: return Quest.is_step_done(&"court", &"hall"), 10.0, "the curtain parts and the sky blinks")
	await walk_to(Vector3(100, -70, -18), 20.0, 0.5)
	await walk_to(Vector3(115, -70, -17), 10.0, 0.3)
	await weave(_hook(Vector3(111, -69.65, -14)), _hook(Vector3(119, -69.65, -14)), "the case's standard line")
	await pluck_at(Vector3(115, -69.65, -14), "the case line")
	await until(func() -> bool: return Quest.is_step_done(&"court", &"dais"), 3.0, "the case lifts away")
	await walk_to(Vector3(115, -69.7, -10.5), 10.0, 0.4)
	await use(w.get("_fragment") as Node3D)
	await until(func() -> bool: return bool(w.get("_heist_on")), 10.0, "the fragment is taken and the court stops pretending")
	await skip_cinematics()


## Up the shaft: a lift to the first ledge, the courtiers' cut line, a lift to the rim.
func _heist() -> void:
	await walk_to(Vector3(100, -70, -21), 15.0, 0.4)
	await _ride(0, Vector3(89, -35, -22), "lift 1")
	await walk_to(Vector3(95.4, -35, -22), 10.0, 0.25)
	await look_at(Vector3(102, -25, -22))
	var cut: Node3D = w.get("_cut_anchor")
	await until(func() -> bool: return not cut.is_in_group(&"silk_anchors"), 8.0)
	await until(func() -> bool: return cut.is_in_group(&"silk_anchors"), 3.0, "the cut line is spun again")
	await swing_chain([cut], Vector3.RIGHT, -38.0, "cut line")
	await walk_to(Vector3(118, -38, -21), 10.0, 0.4)
	await _ride(1, Vector3(118, -3, -35), "lift 2")
	await until(func() -> bool: return Quest.has_fragment(&"chitin"), 6.0, "out on the rim with the fragment")


## Fire at lift k from below, ride it to the end of its path, let go over `over`.
func _ride(k: int, over: Vector3, what: String) -> void:
	var l: Node3D = w.call("lift", k)
	if not await aim_and(l, &"primary", what):
		return
	await until(func() -> bool: return bool(w.call("lift_done", k)), 25.0, what + " reaches the top of its run")
	await frames(30)
	if silk.get("state") == SilkMode.ROPE:
		press(&"primary")
	await until(func() -> bool: return silk.get("state") == SilkMode.GROUND, 5.0)
	var at: Vector3 = Game.player.global_position
	check(absf(at.y - over.y) < 0.5, "%s: set down on its ledge (at %s)" % [what, at])


# --- lookups -------------------------------------------------------------------------------

func _hook(pos: Vector3) -> Node3D:
	var best: Node3D = null
	for n: Node in get_tree().get_nodes_in_group(&"silk_anchors"):
		if (n as Node3D).global_position.distance_to(pos) < 0.6:
			best = n
	for n: Node in w.find_children("Hook*", "Node3D", true, false) + w.find_children("Peg*", "Node3D", true, false):
		if best == null and (n as Node3D).global_position.distance_to(pos) < 0.6:
			best = n
	return best
