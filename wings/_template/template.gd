extends Wing
## The Conservation Studio — a minimal working wing that exercises every part of the Wing
## contract. Copy this folder to wings/<id>/, rename template.* to <id>.*, set wing_id.
##
## Demonstrates: objectives with steps + a side objective, 3 provenances, a fragment + finish(),
## grade/environment/music/ambience exports (see template.tscn), two checkpoints and void respawn,
## a custom movement mode (float) switched by a trigger volume with a gravity change, an
## Interactable, a hold-to-interact, Pickups, a Placard, a seat, persisted custom state, and the
## exit back to the atrium.

const FloatMode := preload("res://wings/_template/float_mode.gd")

var _lamps: Dictionary = {}  # step id -> OmniLight3D
var _fragment: Pickup


func objectives() -> Array[Dictionary]:
	return [
		{"id": "lamps", "title": "Light the three conservation lamps",
			"steps": [{"id": "lamp_a", "title": "The west lamp"}, {"id": "lamp_b", "title": "The centre lamp"}, {"id": "lamp_c", "title": "The east lamp"}]},
		{"id": "cross", "title": "Cross to the drying room",
			"steps": [{"id": "far_side", "title": "Reach the far side"}, {"id": "wind", "title": "Wind the humidity clock"}],
			"hint": "The gap is a jump. Sprint first."},
		{"id": "rest", "title": "Sit a while", "optional": true, "steps": []},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "brush", "name": "A sable brush, never cleaned", "line": "Whoever used it last meant to come back."},
		{"id": "ticket", "name": "A cloakroom ticket, No. 7", "line": "The coat was never collected. The Curator kept the coat."},
		{"id": "glove", "name": "One white cotton glove", "line": "Conservators wear them so as not to leave themselves on things."},
	]


func fragment() -> Dictionary:
	return {"name": "A test fragment", "line": "Staff note: the Studio's fragment is a rehearsal. It does not count."}


func register_modes(player: Player) -> void:
	player.add_mode(&"float", FloatMode.new())


func save_state() -> Dictionary:
	return {"visits": int(recall("visits", 0))}


func load_state(state: Dictionary) -> void:
	store("visits", int(state.get("visits", 0)) + 1)


func on_enter(first_time: bool) -> void:
	_build_lamps()
	_build_clock()
	_build_bench()
	_build_provenances()
	_build_float_zone()
	_build_exit()
	_build_fragment()
	$Placard.set_text("—", "The Conservation Studio", "Staff only  ·  Acq. No. 000-T",
		"Every rule of a gallery, in miniature. Light the lamps, cross the gap, wind the clock. Visits recorded: %d." % int(recall("visits", 1)), false)
	if first_time:
		await Cinematics.play([
			{"card": "Staff only.", "sub": "The Conservation Studio", "t": 3.0, "style": "display"},
		])
	toast("You are in the Studio. The Curator lets staff rehearse here.")


func _build_lamps() -> void:
	for id: String in ["lamp_a", "lamp_b", "lamp_c"]:
		var marker: Node3D = get_node("Lamps/" + id)
		var light := OmniLight3D.new()
		light.light_color = Color("ffd59a")
		light.omni_range = 6.0
		light.light_energy = 2.5 if Quest.is_step_done(&"lamps", StringName(id)) else 0.0
		light.position.y = 1.4
		marker.add_child(light)
		_lamps[id] = light
		var it := Interactable.make_box(Vector3(0.8, 1.6, 0.8), "Light the lamp")
		it.position.y = 0.8
		it.once = true
		it.enabled = not Quest.is_step_done(&"lamps", StringName(id))
		it.interacted.connect(func(_p: Player) -> void:
			create_tween().tween_property(light, "light_energy", 2.5, 1.0)
			complete_step(&"lamps", StringName(id)))
		marker.add_child(it)


func _build_clock() -> void:
	var it := Interactable.make_box(Vector3(0.8, 1.8, 0.6), "Wind the clock")
	it.hold_time = 1.2
	it.once = true
	it.enabled = not Quest.is_step_done(&"cross", &"wind")
	it.position.y = 0.9
	it.interacted.connect(func(_p: Player) -> void: complete_step(&"cross", &"wind"))
	$Clock.add_child(it)
	var tz := TriggerZone.make_box(Vector3(10, 4, 3))
	tz.position = Vector3(0, 2, -17)
	tz.triggered.connect(func(_p: Player) -> void: complete_step(&"cross", &"far_side"))
	add_child(tz)


func _build_bench() -> void:
	var it := Interactable.make_box(Vector3(2.0, 0.9, 0.8), "Sit")
	it.position.y = 0.45
	var seat := Marker3D.new()
	seat.position = Vector3(0, 0.0, 0)
	$Bench.add_child(seat)
	it.interacted.connect(func(p: Player) -> void:
		var m: SeatedMode = p.modes[&"seated"]
		m.seat = seat
		p.set_mode(&"seated")
		complete_objective(&"rest"))
	$Bench.add_child(it)


func _build_provenances() -> void:
	var i := 0
	for p: Dictionary in provenances():
		var id := StringName(p["id"])
		var marker: Node3D = get_node("Provenances").get_child(i)
		i += 1
		if Quest.has_provenance(wing_id, id):
			continue
		var mesh := MeshInstance3D.new()
		var pm := PrismMesh.new()
		pm.size = Vector3(0.25, 0.3, 0.25)
		mesh.mesh = pm
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color("c8a35a")
		mat.emission_enabled = true
		mat.emission = Color("c8a35a")
		mat.emission_energy_multiplier = 1.5
		mat.metallic = 1.0
		mesh.material_override = mat
		marker.add_child(mesh)
		var pick := Pickup.new()
		pick.kind = &"provenance"
		pick.item_id = id
		pick.prompt = "Take: " + String(p["name"])
		pick.visual = mesh
		var cs := CollisionShape3D.new()
		var sph := SphereShape3D.new()
		sph.radius = 0.4
		cs.shape = sph
		pick.add_child(cs)
		marker.add_child(pick)


func _build_float_zone() -> void:
	var zone := TriggerZone.make_box(Vector3(6, 8, 6), false)
	zone.position = $FloatZone.position + Vector3(0, 4, 0)
	zone.triggered.connect(func(p: Player) -> void:
		set_gravity(Vector3(0, -4.0, 0))
		p.set_mode(&"float"))
	zone.exited.connect(func(p: Player) -> void:
		set_gravity(Vector3(0, -15.0, 0))
		if p.mode_name() == &"float":
			p.set_mode(&"walk"))
	add_child(zone)


func _build_exit() -> void:
	var tz := TriggerZone.make_box(Vector3(3, 3, 1))
	tz.position = $Geometry/ExitDoor.position + Vector3(0, 1.5, 0)
	tz.triggered.connect(func(_p: Player) -> void: exit_to_hub())
	add_child(tz)


func _build_fragment() -> void:
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the fragment"
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.6
	cs.shape = sph
	_fragment.add_child(cs)
	$FragmentSpot.add_child(_fragment)
	_fragment.visual = $FragmentSpot/Shard
	_fragment.picked.connect(finish)
	_update_fragment()
	Quest.objective_completed.connect(func(_w: StringName, _o: StringName) -> void: _update_fragment())


func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.main_objectives_done() and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	$FragmentSpot.visible = ready


func _process(delta: float) -> void:
	# World time: animate with Game.world_time_scale, not Engine.time_scale.
	$FragmentSpot.rotate_y(delta * Game.world_time_scale * 0.8)
