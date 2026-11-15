extends Wing
## The Long Shadow (Acquisition No. 501, "Untitled (City at Night)").
## Shadowstep: stay out of light. Light that reaches your head ejects you to the last dark point.
## Geometry and checkpoints are built here so they exist before the Game registers the wing.

const PATH_LAMP := "res://wings/noir/models/streetlamp.glb"
const PATH_SEARCH := "res://wings/noir/models/searchlight.glb"
const PATH_SEDAN := "res://wings/noir/models/sedan.glb"
const PATH_FIGURE := "res://wings/noir/models/figure.glb"

var _player: Player
var _mats: Dictionary = {}
var _world: Node3D
var _fragment: Pickup
var _clock := 0.0
var _sweeps: Array[Node3D] = []
var _better_items: Array[Interactable] = []
var _better_mode := ""
var _reel_taken := false
var _in_cinema := false


func objectives() -> Array[Dictionary]:
	return [
		{"id": "learn_dark", "title": "Learn the dark", "steps": [
			{"id": "enter_shade", "title": "Walk into the alley"},
			{"id": "latch_wall", "title": "Latch onto a dark wall"}]},
		{"id": "cross_lit", "title": "Cross the lit street", "steps": [
			{"id": "cross_street", "title": "Cross the street in shade"},
			{"id": "better_half", "title": "Decide about The Better Half"}]},
		{"id": "heist", "title": "Take the reel", "steps": [
			{"id": "enter_cinema", "title": "Get into the cinema unseen"},
			{"id": "steal_reel", "title": "Take the reel"},
			{"id": "reach_projection", "title": "Reach the projection booth"}]},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "pawn", "name": "A pawn ticket for a camera", "line": "Redeemable until the thing it bought is no longer worth keeping."},
		{"id": "matchbook", "name": "A matchbook from a bar that closed", "line": "One match for two cigarettes. Only one of them came back."},
		{"id": "stub", "name": "A cinema stub, row G", "line": "Admitted once. The usher never checked who was left in the seat."},
	]


func fragment() -> Dictionary:
	return {"name": "The Long Shadow, frame 3", "line": "A reel of what the city kept in the dark. Colour, for eleven seconds."}


func register_modes(player: Player) -> void:
	_player = player
	var m := ShadowstepMode.new()
	m.latched_changed.connect(func(on: bool) -> void:
		if on:
			complete_step(&"learn_dark", &"latch_wall"))
	m.ejected.connect(func() -> void:
		if _in_cinema:
			Game.respawn())
	player.add_mode(&"shadowstep", m)


func save_state() -> Dictionary:
	return {"reel": _reel_taken, "better": _better_mode}


func load_state(state: Dictionary) -> void:
	_reel_taken = bool(state.get("reel", false))
	_better_mode = String(state.get("better", ""))


func on_enter(first_time: bool) -> void:
	$Placard.set_text("No. 501", "The Long Shadow", "Acquisition No. 501  ·  Untitled (City at Night)",
		"Light is a room you can stand in only once. Keep to the dark. Anything lit will put you back where you last hid.", false)
	if first_time:
		await Cinematics.play([
			{"card": "Keep to the dark.", "sub": "Untitled (City at Night)", "t": 3.0, "style": "display"},
		])
	toast("Stay out of the light.")
	_update_fragment()


func _ready() -> void:
	_world = Node3D.new()
	add_child(_world)
	_build_alley()
	_build_street()
	_build_plaza()
	_build_cinema()
	_build_booth()
	Quest.objective_completed.connect(func(_w: StringName, _o: StringName) -> void: _update_fragment())


func _physics_process(delta: float) -> void:
	_clock += delta * Game.world_time_scale
	for i in _sweeps.size():
		_sweeps[i].rotation.y = (-0.5 if i % 2 == 0 else 0.5) + sin(_clock * 0.35 + i * 1.7) * 0.7
	if _player:
		_in_cinema = _player.global_position.z < -66.0 and _player.global_position.z > -91.0


func _process(delta: float) -> void:
	if is_instance_valid(_fragment):
		_fragment.get_parent().rotate_y(delta * Game.world_time_scale * 0.8)


# ---------- helpers ----------

func _mat(key: String, col: Color, rough := 0.9, glow := false) -> StandardMaterial3D:
	if not _mats.has(key):
		var m := StandardMaterial3D.new()
		m.albedo_color = col
		m.roughness = rough
		if glow:
			m.emission_enabled = true
			m.emission = col
			m.emission_energy_multiplier = 1.5
		_mats[key] = m
	return _mats[key]


func _box(parent: Node, pos: Vector3, size: Vector3, key := "wall", col := Color("242426")) -> CSGBox3D:
	var b := CSGBox3D.new()
	b.size = size
	b.position = pos
	b.use_collision = true
	b.material = _mat(key, col)
	parent.add_child(b)
	return b


func _zone(pos: Vector3, size: Vector3, cb: Callable) -> void:
	var tz := TriggerZone.make_box(size)
	tz.position = pos
	tz.triggered.connect(cb)
	add_child(tz)


func _lamp(pos: Vector3, energy: float, range_: float, angle := 55.0) -> void:
	var s := SpotLight3D.new()
	s.position = pos
	s.rotation_degrees = Vector3(-90, 0, 0)
	s.light_color = Color("ffe2b0")
	s.light_energy = energy
	s.spot_range = range_
	s.spot_angle = angle
	s.shadow_enabled = true
	s.add_to_group(&"shadow_lights")
	_world.add_child(s)


func _model(path: String, pos: Vector3, yaw_deg := 0.0) -> Node3D:
	var res := load(path)
	if res is PackedScene:
		var n := (res as PackedScene).instantiate() as Node3D
		n.position = pos
		n.rotation_degrees.y = yaw_deg
		_world.add_child(n)
		return n
	return null


func _provenance(id: String, at: Vector3) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var mesh := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.25, 0.3, 0.25)
	mesh.mesh = pm
	mesh.material_override = _mat("glint", Color("f2f2f2"), 0.3, true)
	mesh.position = at
	_world.add_child(mesh)
	var pick := Pickup.new()
	pick.kind = &"provenance"
	pick.item_id = StringName(id)
	pick.prompt = "Take: " + _prov_name(id)
	pick.visual = mesh
	pick.position = at
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.4
	cs.shape = sph
	pick.add_child(cs)
	_world.add_child(pick)


func _prov_name(id: String) -> String:
	for p: Dictionary in provenances():
		if p["id"] == id:
			return p["name"]
	return id


func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.main_objectives_done() and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_fragment.get_parent().visible = ready


# ---------- areas ----------

func _build_alley() -> void:
	_box(_world, Vector3(0, -0.5, -10), Vector3(9, 1, 22), "floor", Color("111113"))
	_box(_world, Vector3(-4.5, 3, -10), Vector3(1, 6, 22))
	_box(_world, Vector3(4.5, 3, -10), Vector3(1, 6, 22))
	# back wall: the dark face the latch targets; the passage to the street is the dark gap on the east side
	_box(_world, Vector3(-1.0, 3, -21), Vector3(7.0, 6, 1))
	# crate with the pawn ticket
	_box(_world, Vector3(-3.2, 0.4, -12), Vector3(1.2, 0.8, 1.2), "cover", Color("5c5c5c"))
	_provenance("pawn", Vector3(-3.2, 1.1, -12))
	_zone(Vector3(0, 1.5, -5), Vector3(8, 3, 2), func(_p: Player) -> void:
		complete_step(&"learn_dark", &"enter_shade"))
	_checkpoint_at("alley", Vector3(0, 0.05, -2))


func _build_street() -> void:
	_box(_world, Vector3(0, -0.5, -36), Vector3(9, 1, 32), "floor", Color("111113"))
	_box(_world, Vector3(-4.5, 3, -36), Vector3(1, 6, 32))
	_box(_world, Vector3(4.5, 3, -36), Vector3(1, 6, 32))
	# covers: alternate sides so the lit gaps and shadows form a route
	for i in 4:
		var z := -26.0 - i * 6.0
		var x := -1.8 if i % 2 == 0 else 1.8
		_box(_world, Vector3(x, 1.5, z), Vector3(2.2, 3, 1.4), "cover", Color("5c5c5c"))
	for z in [-24.0, -36.0, -48.0]:
		_lamp(Vector3(-3.2, 4.5, z), 9.0, 14.0)
		_model(PATH_LAMP, Vector3(-3.8, 0, z))
	# the eleven-second caster: its shadow is cast from where it will be eleven seconds from now
	var ghost := Node3D.new()
	var gbox := _box(ghost, Vector3.ZERO, Vector3(0.6, 1.8, 0.6), "figure", Color("a8a8a8"))
	gbox.use_collision = false
	_world.add_child(ghost)
	var caster := DelayedCaster.new()
	caster.a = Vector3(-0.6, 0.9, -22.0)
	caster.b = Vector3(-0.6, 0.9, -46.0)
	caster.period = 14.0
	caster.lead = 11.0
	caster.ghost = ghost
	_world.add_child(caster)
	_zone(Vector3(0, 1.5, -50.5), Vector3(8, 3, 1), func(_p: Player) -> void:
		complete_step(&"cross_lit", &"cross_street"))
	_checkpoint_at("street", Vector3(0, 0.05, -22))


func _build_plaza() -> void:
	_box(_world, Vector3(0, -0.5, -59), Vector3(10, 1, 14), "floor", Color("111113"))
	_box(_world, Vector3(-5.5, 3, -59), Vector3(1, 6, 14))
	_box(_world, Vector3(5.5, 3, -59), Vector3(1, 6, 14))
	# one pool of light over the two figures; the approach stays in shade
	_lamp(Vector3(0, 5, -59), 7.0, 9.0, 20.0)  # narrow pool: the figures are lit, the approach and the east edge are not
	var left := _model(PATH_FIGURE, Vector3(-1.4, 0, -58), 90.0)
	var right := _model(PATH_FIGURE, Vector3(1.4, 0, -58), -90.0)
	if left == null:
		_box(_world, Vector3(-1.4, 0.9, -58), Vector3(0.6, 1.8, 0.6), "figure", Color("a8a8a8"))
		_box(_world, Vector3(1.4, 0.9, -58), Vector3(0.6, 1.8, 0.6), "figure", Color("a8a8a8"))
	_better_items.clear()
	for spec in [[Vector3(-1.4, 0.9, -58), "Reunite them", "reunite"], [Vector3(1.4, 0.9, -58), "Release them", "release"]]:
		var it := Interactable.make_box(Vector3(1.2, 1.8, 1.2), spec[1])
		it.position = spec[0]
		it.once = true
		var how: String = spec[2]
		it.interacted.connect(func(_p: Player) -> void: _resolve_better(how))
		_world.add_child(it)
		_better_items.append(it)
	_provenance("matchbook", Vector3(4.2, 0.6, -63))
	_checkpoint_at("plaza", Vector3(0, 0.05, -55))


func _resolve_better(how: String) -> void:
	if _better_mode != "":
		return
	_better_mode = how
	for it in _better_items:
		it.enabled = false
	complete_step(&"cross_lit", &"better_half")
	if how == "reunite":
		toast("The two figures walk on together, back into the dark.", "The Better Half")
	else:
		toast("One figure steps into the light and is not seen again.", "The Better Half")


func _build_cinema() -> void:
	_box(_world, Vector3(0, -0.5, -78), Vector3(12, 1, 24), "floor", Color("111113"))
	_box(_world, Vector3(-6.5, 3, -78), Vector3(1, 6, 24))
	_box(_world, Vector3(6.5, 3, -78), Vector3(1, 6, 24))
	# back wall with a doorway into the booth
	_box(_world, Vector3(-3.5, 3, -90.5), Vector3(5, 6, 1))
	_box(_world, Vector3(3.5, 3, -90.5), Vector3(5, 6, 1))
	for row in 6:
		for col in 3:
			_box(_world, Vector3(-3.0 + col * 3.0, 0.4, -69.0 - row * 3.0), Vector3(1.6, 0.8, 1.6), "cover", Color("5c5c5c"))
	# three searchlights, each on a sweeping pivot
	for p in [Vector3(-5.5, 5.5, -72), Vector3(5.5, 5.5, -79), Vector3(-5.5, 5.5, -86)]:
		var pivot := Node3D.new()
		pivot.position = p
		_world.add_child(pivot)
		var s := SpotLight3D.new()
		s.rotation_degrees = Vector3(-70, 0, 0)
		s.light_color = Color("fff8e8")
		s.light_energy = 12.0
		s.spot_range = 18.0
		s.spot_angle = 20.0
		s.add_to_group(&"shadow_lights")
		s.add_to_group(&"searchlights")
		pivot.add_child(s)
		_model(PATH_SEARCH, p)
		_sweeps.append(pivot)
	_zone(Vector3(0, 1.5, -66.5), Vector3(8, 3, 1), func(_p: Player) -> void:
		complete_step(&"heist", &"enter_cinema"))
	var pedestal := Interactable.make_box(Vector3(0.9, 1.2, 0.9), "Take the reel")
	pedestal.position = Vector3(0, 0.6, -86)
	pedestal.hold_time = 1.5
	pedestal.once = true
	pedestal.enabled = not _reel_taken
	pedestal.interacted.connect(func(_p: Player) -> void:
		_reel_taken = true
		complete_step(&"heist", &"steal_reel"))
	_world.add_child(pedestal)
	_provenance("stub", Vector3(3.0, 1.1, -84.0))  # on top of the cover, reached through the gap at x 1.5
	_checkpoint_at("cinema", Vector3(0, 0.05, -68))


func _build_booth() -> void:
	_box(_world, Vector3(0, -0.5, -95), Vector3(8, 1, 8), "floor", Color("111113"))
	_box(_world, Vector3(-4.5, 2, -95), Vector3(1, 4, 8))
	_box(_world, Vector3(4.5, 2, -95), Vector3(1, 4, 8))
	_box(_world, Vector3(0, 2, -99.5), Vector3(10, 4, 1))
	_zone(Vector3(0, 1.5, -94), Vector3(6, 3, 2), func(_p: Player) -> void:
		complete_step(&"heist", &"reach_projection"))
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the reel frame"
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.6
	cs.shape = sph
	_fragment.add_child(cs)
	var spot := Node3D.new()
	spot.position = Vector3(0, 1.2, -97)
	_world.add_child(spot)
	spot.add_child(_fragment)
	var shard := CSGBox3D.new()
	shard.size = Vector3(0.5, 0.7, 0.1)
	shard.material = _mat("glint", Color("f2f2f2"), 0.3, true)
	spot.add_child(shard)
	_fragment.visual = shard
	_fragment.picked.connect(_on_fragment)
	_checkpoint_at("booth", Vector3(0, 0.05, -93))


func _on_fragment() -> void:
	_fragment.enabled = false
	var colour := grade.duplicate() as PostGrade
	colour.saturation = 1.6
	colour.aberration = 0.0
	Post.apply(colour, 0.5)
	await get_tree().create_timer(11.0).timeout
	Post.apply(grade, 0.0)
	finish()


func _checkpoint_at(id: String, at: Vector3) -> void:
	var cp := Checkpoint.new()
	cp.id = StringName(id)
	cp.position = at
	add_child(cp)
