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
		var guard := 0
		while guard < 900 and silk.get("state") == SilkMode.ROPE:
			guard += 1
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
