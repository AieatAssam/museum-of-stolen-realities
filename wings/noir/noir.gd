extends Wing
## The Long Shadow (Acquisition No. 501, "Untitled (City at Night)").
## Shadowstep: stay out of light. Light that reaches your head ejects you to the last dark point.
## Geometry is built in five areas under Areas/. Each solid is a StaticBody3D whose collision
## shape and visual mesh are separate children, so the art team can swap visuals without touching collision.

const PATH_LAMP := "res://wings/noir/models/streetlamp.glb"
const PATH_SEARCH := "res://wings/noir/models/searchlight.glb"
const PATH_FIGURE := "res://wings/noir/models/figure.glb"
const TRAIN_PERIOD := 12.0

var _player: Player
var _mats: Dictionary = {}
var _world: Node3D
var _areas: Node3D
var _fragment: Pickup
var _clock := 0.0
var _sweeps: Array[Node3D] = []
var _better_items: Array[Interactable] = []
var _better_mode := ""
var _reel_taken := false
var _in_cinema := false
var _gate: StaticBody3D
var _gate_shape: CollisionShape3D
var _gate_mesh: MeshInstance3D
var _desk_lamp: SpotLight3D
var _swing_pivot: Node3D
var _train: Node3D
var _caster: DelayedCaster
var _silhouette: MeshInstance3D


func objectives() -> Array[Dictionary]:
	return [
		{"id": "learn_dark", "title": "Learn the dark", "steps": [
			{"id": "enter_shade", "title": "Walk into the alley"},
			{"id": "latch_wall", "title": "Latch onto a dark wall"}]},
		{"id": "cross_lit", "title": "Cross the lit street", "steps": [
			{"id": "cross_street", "title": "Cross the street in shade"},
			{"id": "latch_gap", "title": "Latch across the rooftop gap"},
			{"id": "better_half", "title": "Decide about The Better Half"}]},
		{"id": "heist", "title": "Take the reel", "steps": [
			{"id": "dim_lamp", "title": "Switch off the precinct desk lamp"},
			{"id": "get_key", "title": "Open the evidence locker"},
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
		if not on:
			return
		# the roof face is the only latch above street height
		if _player.global_position.y > 4.0:
			complete_step(&"cross_lit", &"latch_gap")
		else:
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
	$Placard.set_text("No. 501", "The Long Shadow", "Acquisition No. 501, untitled (City at Night)",
		"Light is a room you can stand in only once. Keep to the dark. Anything lit will put you back where you last hid.", false)
	if first_time:
		await Cinematics.play([
			{"card": "Keep to the dark.", "sub": "Untitled (City at Night)", "t": 3.0, "style": "display"},
		])
	toast("Stay out of the light.")
	if Quest.is_step_done(&"heist", &"dim_lamp"):
		_desk_lamp.light_energy = 0.0
	_sync_gate()
	_update_fragment()


func _ready() -> void:
	_world = Node3D.new()
	add_child(_world)
	_areas = Node3D.new()
	_areas.name = "Areas"
	_world.add_child(_areas)
	_build_alley()
	_build_diner_street()
	_build_elevated_line()
	_build_precinct()
	_build_cinema()
	_build_booth()
	_build_shot_marks()
	Quest.objective_completed.connect(func(_w: StringName, _o: StringName) -> void: _update_fragment())


func _physics_process(delta: float) -> void:
	_clock += delta * Game.world_time_scale
	for i in _sweeps.size():
		_sweeps[i].rotation.y = (-0.5 if i % 2 == 0 else 0.5) + sin(_clock * 0.35 + i * 1.7) * 0.7
	if _train:
		_train.position = Vector3(lerpf(-44.0, -8.0, fposmod(_clock / TRAIN_PERIOD, 1.0)), 8.6, -29.0)
	if _caster and _silhouette:
		_silhouette.position.z = _caster.position.z
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


func _area(area_name: String) -> Node3D:
	var n := Node3D.new()
	n.name = area_name
	_areas.add_child(n)
	return n


## A solid box: StaticBody3D with a collision shape child and a separate visual mesh child.
func _solid(parent: Node, pos: Vector3, size: Vector3, key := "wall", col := Color("242426")) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	body.add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(key, col)
	body.add_child(mi)
	parent.add_child(body)
	return body


func _zone(parent: Node, pos: Vector3, size: Vector3, cb: Callable) -> void:
	var tz := TriggerZone.make_box(size)
	tz.position = pos
	tz.triggered.connect(cb)
	parent.add_child(tz)


func _spot(parent: Node, pos: Vector3, energy: float, range_: float, angle: float) -> SpotLight3D:
	var s := SpotLight3D.new()
	s.position = pos
	s.rotation_degrees = Vector3(-90, 0, 0)
	s.light_color = Color("ffe2b0")
	s.light_energy = energy
	s.spot_range = range_
	s.spot_angle = angle
	s.shadow_enabled = true
	s.add_to_group(&"shadow_lights")
	parent.add_child(s)
	return s


func _model(parent: Node, path: String, pos: Vector3, yaw_deg := 0.0) -> Node3D:
	var res := load(path)
	if res is PackedScene:
		var n := (res as PackedScene).instantiate() as Node3D
		n.position = pos
		n.rotation_degrees.y = yaw_deg
		parent.add_child(n)
		return n
	return null


func _provenance(parent: Node, id: String, at: Vector3) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var mesh := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.25, 0.3, 0.25)
	mesh.mesh = pm
	mesh.material_override = _mat("glint", Color("f2f2f2"), 0.3, true)
	mesh.position = at
	parent.add_child(mesh)
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
	parent.add_child(pick)


func _prov_name(id: String) -> String:
	for p: Dictionary in provenances():
		if p["id"] == id:
			return p["name"]
	return id


func _plaque(parent: Node, at: Vector3, yaw: float, heading: String, title: String, catalog: String, body: String) -> void:
	var p := Placard.new()
	parent.add_child(p)
	p.position = at
	p.rotation_degrees.y = yaw
	p.set_text(heading, title, catalog, body, false)


func _checkpoint_at(id: String, at: Vector3) -> void:
	var cp := Checkpoint.new()
	cp.id = StringName(id)
	cp.position = at
	add_child(cp)


func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.main_objectives_done() and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_fragment.get_parent().visible = ready


# ---------- areas ----------

func _build_alley() -> void:
	var a := _area("Alley")
	_solid(a, Vector3(0, -0.5, -10), Vector3(9, 1, 22), "floor", Color("111113"))
	_solid(a, Vector3(-4.5, 3, -10), Vector3(1, 6, 22))
	_solid(a, Vector3(4.5, 3, -10), Vector3(1, 6, 22))
	# back wall: the dark face the latch targets; the passage to the street is the gap on the east side
	_solid(a, Vector3(-1.0, 3, -21), Vector3(7.0, 6, 1))
	_solid(a, Vector3(-3.2, 0.4, -12), Vector3(1.2, 0.8, 1.2), "cover", Color("5c5c5c"))
	_provenance(a, "pawn", Vector3(-3.2, 1.1, -12))
	_plaque(a, Vector3(-3.95, 1.6, -16.0), 90.0, "Gelatin silver print, 1938", "The alley, after rain", "Acquisition No. 501.1",
		"Taken from the fire escape, though no fire escape appears in the frame. The negative was retouched once, by hand. The retoucher is not recorded. Water stain, lower left.")
	_zone(a, Vector3(0, 1.5, -5), Vector3(8, 3, 2), func(_p: Player) -> void:
		complete_step(&"learn_dark", &"enter_shade"))
	_checkpoint_at("alley", Vector3(0, 0.05, -2))


func _build_diner_street() -> void:
	var s := _area("DinerStreet")
	_solid(s, Vector3(0, -0.5, -36), Vector3(9, 1, 32), "floor", Color("111113"))
	_solid(s, Vector3(4.5, 3, -36), Vector3(1, 6, 32))
	# west wall with a 4 m opening where the elevated ramp comes down
	_solid(s, Vector3(-4.5, 3, -23.25), Vector3(1, 6, 6.5))
	_solid(s, Vector3(-4.5, 3, -41.25), Vector3(1, 6, 21.5))
	# covers: alternate sides so the lit gaps and shadows form a route
	for i in 4:
		var z := -26.0 - i * 6.0
		var x := -1.8 if i % 2 == 0 else 1.8
		_solid(s, Vector3(x, 1.5, z), Vector3(2.2, 3, 1.4), "cover", Color("5c5c5c"))
	# lamps sit well south of the ramp (z -27..-30) so the climb is in shade
	for z in [-40.0, -48.0]:
		_spot(s, Vector3(-3.2, 4.5, z), 9.0, 14.0, 55.0)
		_model(s, PATH_LAMP, Vector3(-3.8, 0, z))
	# the eleven-second caster: its shadow is the body, sampled eleven seconds ahead of the visible figure
	var ghost := MeshInstance3D.new()
	var gbm := BoxMesh.new()
	gbm.size = Vector3(0.6, 1.8, 0.6)
	ghost.mesh = gbm
	ghost.material_override = _mat("figure", Color("a8a8a8"))
	s.add_child(ghost)
	_caster = DelayedCaster.new()
	_caster.a = Vector3(-0.6, 0.9, -22.0)
	_caster.b = Vector3(-0.6, 0.9, -46.0)
	_caster.period = 14.0
	_caster.lead = 11.0
	_caster.ghost = ghost
	s.add_child(_caster)
	# the diner window: the silhouette in it is where the shade will be in eleven seconds
	var glass := MeshInstance3D.new()
	var glm := BoxMesh.new()
	glm.size = Vector3(0.04, 2.2, 26.0)
	glass.mesh = glm
	glass.material_override = _mat("glass", Color("ffb865"), 0.4, true)
	glass.position = Vector3(3.97, 2.3, -35.0)
	s.add_child(glass)
	_silhouette = MeshInstance3D.new()
	var sm := BoxMesh.new()
	sm.size = Vector3(0.05, 1.8, 0.5)
	_silhouette.mesh = sm
	_silhouette.material_override = _mat("silhouette", Color("141414"), 0.9)
	_silhouette.position = Vector3(4.0, 1.0, -22.0)
	s.add_child(_silhouette)
	_plaque(s, Vector3(-3.95, 1.6, -34.0), 90.0, "Gelatin silver print, 1941", "The diner window", "Acquisition No. 501.2",
		"The window shows the street eleven seconds before the street does. Figures inside are kept in place by a patrol that was never photographed. The diner's own record gives no date.")
	_plaque(s, Vector3(-3.95, 1.6, -44.0), 90.0, "Gelatin silver print, 1941", "Three lamps, one street", "Acquisition No. 501.3",
		"Three lamps were ordered as a set and installed as two. The third lamp appears in the frame, and its light does not. The crossing is the subject of the print.")
	_zone(s, Vector3(0, 1.5, -50.5), Vector3(8, 3, 1), func(_p: Player) -> void:
		complete_step(&"cross_lit", &"cross_street"))
	_checkpoint_at("street", Vector3(0, 0.05, -22))
	_build_plaza(s)


func _build_plaza(s: Node3D) -> void:
	_solid(s, Vector3(0, -0.5, -59), Vector3(10, 1, 14), "floor", Color("111113"))
	_solid(s, Vector3(-5.5, 3, -59), Vector3(1, 6, 14))
	# one pool of light over the two figures; the approach stays in shade
	_spot(s, Vector3(0, 5, -59), 7.0, 9.0, 20.0)
	_model(s, PATH_FIGURE, Vector3(-1.4, 0, -58), 90.0)
	_model(s, PATH_FIGURE, Vector3(1.4, 0, -58), -90.0)
	_better_items.clear()
	for spec in [[Vector3(-1.4, 0.9, -58), "Reunite them", "reunite"], [Vector3(1.4, 0.9, -58), "Release them", "release"]]:
		var it := Interactable.make_box(Vector3(1.2, 1.8, 1.2), spec[1])
		it.position = spec[0]
		it.once = true
		var how: String = spec[2]
		it.interacted.connect(func(_p: Player) -> void: _resolve_better(how))
		s.add_child(it)
		_better_items.append(it)
	_provenance(s, "matchbook", Vector3(4.2, 0.6, -63))
	_plaque(s, Vector3(-4.95, 1.6, -56.0), 90.0, "Gelatin silver print, 1947", "Two figures under one lamp", "Acquisition No. 501.5",
		"Two figures stand under one lamp. The catalogue lists them as a pair. The record does not say whether they were meant to stand together, or only lit together.")
	_plaque(s, Vector3(4.95, 1.6, -53.5), -90.0, "Printed card, 1951", "Matchbook, open", "Acquisition No. 501.6",
		"A bar matchbook, opened to the striker. The bar closed the year of the print. Two matches are missing from the cover, and one was returned, according to a note.")


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


func _build_elevated_line() -> void:
	var e := _area("ElevatedLine")
	# fire-escape ramp up from the street's west wall to the roof
	var ramp := _solid(e, Vector3(-8.85, 2.5, -28.5), Vector3(10, 0.4, 3), "metal", Color("3d3d40"))
	ramp.rotation_degrees.z = -30.0
	_solid(e, Vector3(-16.3, 2.5, -29.0), Vector3(6.6, 5, 8), "roof", Color("2a2a2c"))
	# the far roof: its east face is the dark wall across the gap, taller than the roof we stand on
	_solid(e, Vector3(-26.25, 3.5, -29.0), Vector3(7.5, 7, 8), "roof", Color("2a2a2c"))
	_checkpoint_at("roof", Vector3(-14.5, 5.05, -29.0))
	_plaque(e, Vector3(-16.3, 5.35, -32.6), 0.0, "Gelatin silver print, 1955", "Elevated line, last train", "Acquisition No. 501.4",
		"A train crosses the roofs every twelve seconds. Its lamp falls on the parapet and not the gap. Two photographs show the same parapet; one has been cropped at the edge.")
	# the train runs on a rail above the roofs; its lamp is the rhythm that cuts the shadow path
	var rail := MeshInstance3D.new()
	var rm := BoxMesh.new()
	rm.size = Vector3(54, 0.3, 1.4)
	rail.mesh = rm
	rail.material_override = _mat("rail", Color("1a1a1c"), 0.5)
	rail.position = Vector3(-19.0, 8.0, -29.0)
	e.add_child(rail)
	_train = Node3D.new()
	e.add_child(_train)
	var body := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(7, 1.2, 2.2)
	body.mesh = bm
	body.material_override = _mat("train", Color("2a3640"), 0.5)
	_train.add_child(body)
	_spot(_train, Vector3(0, -0.7, 0), 12.0, 14.0, 35.0)


func _build_precinct() -> void:
	var p := _area("Precinct")
	# plaza east wall with a 4 m opening into the precinct
	_solid(p, Vector3(5.5, 3, -53.5), Vector3(1, 6, 3))
	_solid(p, Vector3(5.5, 3, -62.5), Vector3(1, 6, 7))
	_solid(p, Vector3(9.25, -0.5, -59), Vector3(6.5, 1, 14), "floor", Color("111113"))
	_solid(p, Vector3(12.5, 3, -59), Vector3(1, 6, 14))
	_solid(p, Vector3(9.25, 3, -52.5), Vector3(6.5, 6, 1))
	_solid(p, Vector3(9.25, 3, -66.5), Vector3(6.5, 6, 1))
	# blinds hanging from the east wall
	for i in 5:
		_solid(p, Vector3(11.9, 2.4, -53.2 - i * 0.4), Vector3(0.1, 2.6, 0.12), "blind", Color("8a8a84"))
	# desk lamp over the entrance: lit until switched off from outside the room
	_desk_lamp = _spot(p, Vector3(8.0, 2.6, -57.0), 8.0, 4.0, 45.0)
	# swing lamp over the locker: the pool moves away when swung
	_swing_pivot = Node3D.new()
	_swing_pivot.position = Vector3(9.0, 2.8, -63.0)
	p.add_child(_swing_pivot)
	_spot(_swing_pivot, Vector3.ZERO, 8.0, 5.0, 40.0)
	var lamp_switch := Interactable.make_box(Vector3(0.4, 0.8, 0.4), "Switch off the desk lamp")
	lamp_switch.position = Vector3(4.8, 1.2, -57.8)
	lamp_switch.once = true
	lamp_switch.interacted.connect(func(_p: Player) -> void: _dim_lamp())
	p.add_child(lamp_switch)
	var swing := Interactable.make_box(Vector3(0.4, 0.8, 0.4), "Swing the spare lamp")
	swing.position = Vector3(6.4, 1.2, -60.2)
	swing.interacted.connect(func(_p: Player) -> void: _swing_pivot.rotation_degrees.z = 50.0 - _swing_pivot.rotation_degrees.z)
	p.add_child(swing)
	var locker := Interactable.make_box(Vector3(1.0, 1.6, 0.8), "Open the evidence locker")
	locker.position = Vector3(6.5, 0.8, -63.0)
	locker.hold_time = 1.0
	locker.once = true
	locker.interacted.connect(func(_p: Player) -> void: _get_key())
	p.add_child(locker)
	_plaque(p, Vector3(11.95, 1.6, -57.0), -90.0, "Desk lamp, enamelled steel, 1949", "Desk lamp, precinct", "Acquisition No. 501.7",
		"The lamp was switched on for every interview. Interviews were held in its circle of light. The switch is outside the room, where the sergeant could reach it without standing up.")
	_plaque(p, Vector3(6.05, 1.6, -65.2), 90.0, "Steel locker, 1950", "Evidence locker, precinct", "Acquisition No. 501.8",
		"Key held by the desk sergeant until his retirement. The lock was replaced twice. The file inside lists the matchbook as returned. The owner is not named.")
	_sync_precinct()


func _dim_lamp() -> void:
	_desk_lamp.light_energy = 0.0
	complete_step(&"heist", &"dim_lamp")
	toast("The desk lamp goes dark.", "Precinct")


func _sync_precinct() -> void:
	if Quest.is_step_done(&"heist", &"dim_lamp"):
		_desk_lamp.light_energy = 0.0


func _get_key() -> void:
	if Quest.is_step_done(&"heist", &"get_key"):
		return
	if not Quest.is_step_done(&"heist", &"dim_lamp"):
		toast("The desk lamp still reaches the locker. Switch it off first.", "Precinct")
		return
	complete_step(&"heist", &"get_key")
	_sync_gate()
	toast("The locker gives up its key.", "Precinct")


func _sync_gate() -> void:
	var open := Quest.is_step_done(&"heist", &"get_key")
	if _gate_shape:
		_gate_shape.set_deferred("disabled", open)
	if _gate_mesh:
		_gate_mesh.visible = not open


func _build_cinema() -> void:
	var c := _area("Cinema")
	_solid(c, Vector3(0, -0.5, -78), Vector3(12, 1, 24), "floor", Color("111113"))
	_solid(c, Vector3(-6.5, 3, -78), Vector3(1, 6, 24))
	_solid(c, Vector3(6.5, 3, -78), Vector3(1, 6, 24))
	# locked gate across the cinema mouth; the precinct key opens it
	_gate = StaticBody3D.new()
	_gate.position = Vector3(0, 2.0, -66.0)
	var gcs := CollisionShape3D.new()
	var gshape := BoxShape3D.new()
	gshape.size = Vector3(11.0, 4.0, 0.5)
	gcs.shape = gshape
	_gate.add_child(gcs)
	_gate_shape = gcs
	_gate_mesh = MeshInstance3D.new()
	var gmesh := BoxMesh.new()
	gmesh.size = gshape.size
	_gate_mesh.mesh = gmesh
	_gate_mesh.material_override = _mat("gate", Color("3a3a3c"), 0.6)
	_gate.add_child(_gate_mesh)
	c.add_child(_gate)
	_sync_gate()
	# back wall with a doorway into the booth
	_solid(c, Vector3(-3.5, 3, -90.5), Vector3(5, 6, 1))
	_solid(c, Vector3(3.5, 3, -90.5), Vector3(5, 6, 1))
	for row in 6:
		for col in 3:
			_solid(c, Vector3(-3.0 + col * 3.0, 0.4, -69.0 - row * 3.0), Vector3(1.6, 0.8, 1.6), "cover", Color("5c5c5c"))
	# three searchlights, each on a sweeping pivot
	for pv in [Vector3(-5.5, 5.5, -72), Vector3(5.5, 5.5, -79), Vector3(-5.5, 5.5, -86)]:
		var pivot := Node3D.new()
		pivot.position = pv
		c.add_child(pivot)
		var s := SpotLight3D.new()
		s.rotation_degrees = Vector3(-70, 0, 0)
		s.light_color = Color("fff8e8")
		s.light_energy = 12.0
		s.spot_range = 18.0
		s.spot_angle = 20.0
		s.add_to_group(&"shadow_lights")
		s.add_to_group(&"searchlights")
		pivot.add_child(s)
		_model(pivot, PATH_SEARCH, Vector3.ZERO)
		_sweeps.append(pivot)
	_zone(c, Vector3(0, 1.5, -66.5), Vector3(8, 3, 1), func(_p: Player) -> void:
		complete_step(&"heist", &"enter_cinema"))
	var pedestal := Interactable.make_box(Vector3(0.9, 1.2, 0.9), "Take the reel")
	pedestal.position = Vector3(0, 0.6, -86)
	pedestal.hold_time = 1.5
	pedestal.once = true
	pedestal.enabled = not _reel_taken
	pedestal.interacted.connect(func(_p: Player) -> void:
		_reel_taken = true
		complete_step(&"heist", &"steal_reel"))
	c.add_child(pedestal)
	_provenance(c, "stub", Vector3(3.0, 1.1, -84.0))  # on top of the cover, reached through the gap at x 1.5
	_plaque(c, Vector3(-5.9, 1.6, -74.0), 90.0, "Searchlight, carbon arc, 1939", "Searchlight, cinema house", "Acquisition No. 501.9",
		"A searchlight swept the house for the length of one feature. Patrons it found were asked to leave their seats. The register does not say the seats were refilled.")
	_plaque(c, Vector3(5.9, 1.6, -82.0), -90.0, "Printed ticket, 1943", "Cinema stub, row G", "Acquisition No. 501.10",
		"Admitted once. The usher never checked who was left in the seat. The stub is the only record of row G that survived the fire.")
	_checkpoint_at("cinema", Vector3(0, 0.05, -68))


func _build_booth() -> void:
	var b := _area("Booth")
	_solid(b, Vector3(0, -0.5, -95), Vector3(8, 1, 8), "floor", Color("111113"))
	_solid(b, Vector3(-4.5, 2, -95), Vector3(1, 4, 8))
	_solid(b, Vector3(4.5, 2, -95), Vector3(1, 4, 8))
	_solid(b, Vector3(0, 2, -99.5), Vector3(10, 4, 1))
	_zone(b, Vector3(0, 1.5, -94), Vector3(6, 3, 2), func(_p: Player) -> void:
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
	b.add_child(spot)
	spot.add_child(_fragment)
	var shard := CSGBox3D.new()
	shard.size = Vector3(0.5, 0.7, 0.1)
	shard.material = _mat("glint", Color("f2f2f2"), 0.3, true)
	spot.add_child(shard)
	_fragment.visual = shard
	_fragment.picked.connect(_on_fragment)
	_plaque(b, Vector3(0, 1.6, -98.9), 0.0, "Film reel frame, 1938, colour", "The Long Shadow, frame 3", "Acquisition No. 501.11",
		"The projection booth kept one frame in colour for eleven seconds. Whoever cut it did not log the length. The rest of the reel is grey, as expected for the city.")
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


func _build_shot_marks() -> void:
	# twelve camera marks for the art team, one per view worth a screenshot
	var marks := [
		["alley_entry", Vector3(0, 1.4, -2)], ["alley_latch", Vector3(-1.0, 1.4, -18)],
		["alley_crate", Vector3(-3.0, 1.2, -12)], ["street_lamps", Vector3(0, 1.4, -24)],
		["diner_window", Vector3(0, 1.4, -36)], ["roof_gap", Vector3(-19.0, 5.6, -29)],
		["roof_train", Vector3(-16.0, 5.6, -26)], ["plaza_figures", Vector3(0, 1.6, -52)],
		["precinct_desk", Vector3(7.0, 1.4, -56)], ["precinct_locker", Vector3(6.5, 1.4, -60)],
		["cinema_lattice", Vector3(0, 1.6, -72)], ["booth_frame", Vector3(0, 1.4, -92)],
	]
	for m: Array in marks:
		var mk := Marker3D.new()
		mk.name = m[0]
		mk.position = m[1]
		mk.add_to_group(&"shot_marks")
		_world.add_child(mk)
