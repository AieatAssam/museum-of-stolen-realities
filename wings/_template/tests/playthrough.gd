extends Playthrough
## The Conservation Studio, start to finish, by real input only (no debug_complete_*):
## three lamps, the stairs, the zipline, leave by the door and come back (progress persists), the sprint-jump
## gap, the hold-to-wind clock, all three provenances (one mid-air in the float zone), the fragment.
## Run: tests/run_playthrough.sh _template

const W := &"_template"

var w: Wing


func run() -> void:
	await enter(W)
	w = Game.wing

	# --- lamps: walk up to each and press interact ---
	var stands := {"lamp_a": Vector3(0, 0, 1.6), "lamp_b": Vector3(0, 0, 1.6), "lamp_c": Vector3(-1.4, 0, 1.0)}
	for id: String in stands:
		var lamp: Node3D = w.get_node("Lamps/" + id)
		await walk_to(lamp.global_position + stands[id])
		await use(lamp)
		check(Quest.is_step_done(&"lamps", StringName(id)), "%s lit by interact" % id)
	check(Quest.is_done(&"lamps"), "lamps objective completes from its steps")

	# --- stairs (0.18 m and 0.35 m risers) up to the top landing and back down ---
	await walk_to(Vector3(0.5, 0, -4.5))  # round the back of the staircase to its foot
	await walk_to(Vector3(0.5, 0, 2.2))
	await walk_to(Vector3(2.5, 0, 2.2), 8.0, 0.3)
	await walk_to(Vector3(2.5, 0, -2.6), 8.0, 0.3)
	check(Game.player.global_position.y > 1.7, "climbed the stairs without jumping (y=%.2f)" % Game.player.global_position.y)
	await walk_to(Vector3(2.5, 0, 2.0), 8.0, 0.3)
	check(Game.player.global_position.y < 0.1, "walked back down the stairs")

	# --- the zipline (a ConstrainedMode): grab, ride to the end, drop back into walk ---
	await walk_to(Vector3(-4, 0, 3.0))
	await walk_to(Vector3(-9.3, 0, 3.4), 10.0, 0.3)
	await use(w.get_node("Handle"))
	check(Game.player.mode_name() == &"rail", "interact grabs the zipline")
	await until(func() -> bool: return Game.player.mode_name() == &"walk", 6.0, "zipline lets go at its end")
	check(Game.player.global_position.z < -2.5, "rode the zipline (z=%.1f)" % Game.player.global_position.z)

	# --- provenance 1 on the stepped landing ---
	await walk_to(Vector3(7, 0, 1.5))  # in front of the 0.3 m steps, then up them
	await _take_provenance(0, Vector3(7, 0, -3.5))

	# --- leave by the door, come back: progress persists ---
	await walk_to(Vector3(0, 0, 8.5), 15.0)
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 15.0, "exit door returns to the atrium")
	await enter(W)
	w = Game.wing
	check(Quest.is_done(&"lamps"), "lamps still lit after leaving and re-entering")

	# --- the gap: sprint and jump ---
	await walk_to(Vector3(1.5, 0, -6))  # x=1.5 clears lamp_b on the centre line
	var ok := await jump_across(Vector3(1.5, 0, -12), Vector3(1.5, 0, -17))
	check(ok and Game.player.global_position.y > -0.5, "sprint-jumped the gap")
	await until(func() -> bool: return Quest.is_step_done(&"cross", &"far_side"), 3.0, "far side reached")

	# --- the clock: hold to wind ---
	var clock: Node3D = w.get_node("Clock")
	await walk_to(clock.global_position + Vector3(0, 0, 1.6))
	await use(clock, 1.6)
	check(Quest.is_step_done(&"cross", &"wind"), "holding interact winds the clock")
	check(Quest.main_objectives_done(), "main objectives done by play")

	# --- provenance 2 on the far floor, provenance 3 mid-air in the float zone ---
	await _take_provenance(1, Vector3(-8, 0, -22.5))
	await _float_provenance()

	# --- the fragment ---
	var frag: Node3D = w.get_node("FragmentSpot")
	check(frag.visible, "fragment appears once the objectives are done")
	await walk_to(frag.global_position + Vector3(0, 0, 1.6))
	await use(frag)
	await until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0, "finish() returns to the atrium")
	check(Quest.has_fragment(W), "fragment recorded")
	check(Save.data["provenances"].get(String(W), []).size() == 3, "all three provenances recorded")


func _pickup(i: int) -> Pickup:
	var m: Node = w.get_node("Provenances").get_child(i)
	for c in m.get_children():
		if c is Pickup:
			return c
	return null


func _take_provenance(i: int, stand: Vector3) -> void:
	var pick := _pickup(i)
	await walk_to(stand, 15.0, 0.4)
	await use(pick)
	await until(func() -> bool: return Save.data["provenances"].get(String(W), []).size() >= i + 1, 4.0,
		"provenance %d taken by interact" % (i + 1))


## p3 floats 5.5 m up over the float pad: walk onto the pad (low gravity + float mode), jump, and
## press interact as it passes under the crosshair.
func _float_provenance() -> void:
	var pick := _pickup(2)
	var target := pick.global_position
	await walk_to(Vector3(-7, 0, -16.6), 15.0, 0.3)
	check(Game.player.mode_name() == &"float", "float pad switches to the float mode")
	await tap(&"jump")
	var end := Time.get_ticks_msec() + 4000
	while Time.get_ticks_msec() < end and is_instance_valid(pick) and pick.enabled:
		Game.player.look_at_point(target)  # aim only; the climb is the jump
		if Interaction.target == pick:
			await tap(&"interact")
		await frames(1)
	await until(func() -> bool: return Save.data["provenances"].get(String(W), []).size() == 3, 4.0,
		"provenance 3 taken mid-air")
	await walk_to(Vector3(-3, 0, -20))  # off the pad: normal gravity again
