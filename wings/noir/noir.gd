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
var _traverse: Tween
var _near_roof: StaticBody3D
var _far_roof: StaticBody3D
var _dress: Node3D


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
		if _player.global_position.y > 4.0:
			_cross_gap(m)
		else:
			complete_step(&"learn_dark", &"latch_wall"))
	m.ejected.connect(func() -> void:
		# a train lamp that catches the traversal drops the player back to the last dark point
		if _traverse and _traverse.is_running():
			_traverse.kill()
			m.release()
		if _in_cinema:
			Game.respawn())
	player.add_mode(&"shadowstep", m)


## Latching the far roof's dark face carries the player across the gap. The train's lamp cuts the path:
## the traversal is refused while the gap is lit, and a lamp that catches it mid-air drops the player back.
## Only the roof across the gap carries you: from the near roof, the far roof's dark east face; from
## the far roof, the near roof. A latch on the roof underfoot (or anything else up here) lets go.
func _cross_gap(m: ShadowstepMode) -> void:
	var near_side := _player.global_position.x > -21.0
	var body: Object = m.hit.get("collider")
	var n: Vector3 = m.hit.get("normal", Vector3.ZERO)
	if not ((near_side and body == _far_roof and n.x > 0.7) or (not near_side and body == _near_roof)):
		m.release()
		return
	var ex: Array[RID] = [_player.get_rid()]
	if ShadowField.lit(_player, Vector3(-21.0, 6.0, -29.0), ex):
		m.release()
		toast("The train's lamp is across the gap. Wait for it to pass.", "Elevated line")
		return
	complete_step(&"cross_lit", &"latch_gap")
	# from the near roof the latch carries you to the far roof; from the far roof, back to the near one
	var to := Vector3(-25.2, 7.05, -29.0) if near_side else Vector3(-16.6, 5.05, -29.0)
	_player.gravity_vector = Vector3.ZERO
	_player.velocity = Vector3.ZERO
	_traverse = create_tween()
	_traverse.tween_property(_player, "global_position", to, 1.2).set_trans(Tween.TRANS_SINE)
	_traverse.tween_callback(m.release)


func save_state() -> Dictionary:
	return {"reel": _reel_taken, "better": _better_mode}


func load_state(state: Dictionary) -> void:
	_reel_taken = bool(state.get("reel", false))
	_better_mode = String(state.get("better", ""))


func on_exit() -> void:
	get_tree().root.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED  # the next wing's Quality.apply restores MSAA
	_dress.exit_quality()


func on_enter(first_time: bool) -> void:
	_dress.enter_quality(get_tree().root)
	$Placard.set_label(Placard.fields("The Long Shadow", "", "Untitled (City at Night)", "Acquisition No. 501",
		"Light is a room you can stand in only once. Keep to the dark. Anything lit will put you back where you last hid."), false)
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
	var steps: Array[AudioStream] = []
	for i in [1, 2, 3]:
		steps.append(load("res://wings/noir/audio/step_wet_%d.ogg" % i))
	Audio.register_footsteps(&"wet", steps)
	_dress = preload("res://wings/noir/noir_dress.gd").new()
	_dress.build(self)
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


## A noir material (wings/noir/materials/<key>.tres) when one exists, else a flat colour.
func _surface(key: String, col: Color) -> Material:
	var path := "res://wings/noir/materials/%s.tres" % key
	return load(path) if ResourceLoader.exists(path) else _mat(key, col)


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
	mi.material_override = _surface(key, col)
	body.add_child(mi)
	if key.begins_with("wet_"):
		body.set_meta(&"surface", &"wet" if key != "wet_floorboards" and key != "wet_carpet" else (&"wood" if key == "wet_floorboards" else &"carpet"))
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
		MaterialLib.apply(n, ["res://wings/noir/materials", MaterialLib.CORE_DIR])
		parent.add_child(n)
		return n
	return null


func _provenance(parent: Node, id: String, at: Vector3) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var props := {"pawn": "pawn_ticket", "matchbook": "matchbook", "stub": "stub"}
	var mesh := _model(parent, "res://wings/noir/models/%s.glb" % props[id], at)
	mesh.scale = Vector3.ONE * 2.2
	var glint := OmniLight3D.new()
	glint.light_color = Color(1.0, 0.92, 0.8)
	glint.light_energy = 0.35
	glint.omni_range = 0.9
	mesh.add_child(glint)
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


func _plaque(parent: Node, at: Vector3, yaw: float, medium: String, title: String, acq: String, body: String) -> void:
	var p := Placard.new()
	p.size = Vector2(1.3, 0.9)  # bigger than the house plate: read at 2 m through the fog
	parent.add_child(p)
	p.position = at
	p.rotation_degrees.y = yaw
	p.set_label(Placard.fields(title, "", medium, acq, body), false)
	# a hooded picture light over the plate: the room stays dark, the label does not
	var lamp := SpotLight3D.new()
	lamp.position = Vector3(0, 0.75, 0.55)
	lamp.light_color = Color(1.0, 0.93, 0.8)
	lamp.light_energy = 1.6
	lamp.spot_range = 2.0
	lamp.spot_angle = 40.0
	lamp.light_volumetric_fog_energy = 0.0
	p.add_child(lamp)
	lamp.look_at(p.global_position + Vector3.DOWN * 0.15, Vector3.UP)


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
	_solid(a, Vector3(0, -0.5, -10), Vector3(9, 1, 22), "wet_cobble", Color("111113"))
	_solid(a, Vector3(-4.5, 3, -10), Vector3(1, 6, 22), "brick_dark")
	_solid(a, Vector3(4.5, 3, -10), Vector3(1, 6, 22), "brick_dark")
	# north end: the alley is closed behind the entry
	_solid(a, Vector3(0, 3, 1.5), Vector3(9, 6, 1), "brick_dark")
	# back wall: the dark face the latch targets; the passage to the street is the gap on the east side
	_solid(a, Vector3(-1.0, 3, -21), Vector3(7.0, 6, 1), "brick")
	_solid(a, Vector3(-3.2, 0.4, -12), Vector3(1.2, 0.8, 1.2), "cover", Color("5c5c5c"))
	_provenance(a, "pawn", Vector3(-3.2, 1.1, -12))
	_plaque(a, Vector3(-3.95, 1.6, -16.0), 90.0, "Gelatin silver print, 1938", "The alley, after rain", "Acquisition No. 501.1",
		"Taken from the fire escape, though no fire escape appears in the frame. The negative was retouched once, by hand. The retoucher is not recorded. Water stain, lower left.")
	_zone(a, Vector3(0, 1.5, -5), Vector3(8, 3, 2), func(_p: Player) -> void:
		complete_step(&"learn_dark", &"enter_shade"))
	_checkpoint_at("alley", Vector3(0, 0.05, -2))


func _build_diner_street() -> void:
	var s := _area("DinerStreet")
	_solid(s, Vector3(0, -0.5, -36), Vector3(9, 1, 32), "wet_asphalt", Color("111113"))
	_solid(s, Vector3(4.5, 3, -36), Vector3(1, 6, 32), "brick_dark")
	# west wall with a 4 m opening where the elevated ramp comes down
	_solid(s, Vector3(-4.5, 3, -23.25), Vector3(1, 6, 6.5), "brick_dark")
	_solid(s, Vector3(-4.5, 3, -41.25), Vector3(1, 6, 21.5), "brick_dark")
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
	_solid(s, Vector3(0, -0.5, -59), Vector3(10, 1, 14), "wet_cobble", Color("111113"))
	_solid(s, Vector3(-5.5, 3, -59), Vector3(1, 6, 14), "brick_dark")
	# one pool of light over the two figures; the approach stays in shade
	_spot(s, Vector3(0, 5, -59), 7.0, 9.0, 20.0)
	_model(s, PATH_FIGURE, Vector3(-1.4, 0, -58), 90.0)
	_model(s, "res://wings/noir/models/figure_woman.glb", Vector3(1.4, 0, -58), -90.0)
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
	# fire-stair ramp up from the street's west wall to the roof. Its top surface runs straight from the
	# street floor's edge (x -4.5, y 0) to the roof's edge (x -13, y 5); the 11 m slab ends flush at the
	# roof edge and runs on 1.1 m under the street floor, so neither end has a slot or a lip (the old
	# 30-degree slab left a 0.57 m slot under the wall gap at the foot and a 0.42 m lip at the roof edge).
	var slope := atan2(5.0, 8.5)
	var down := Vector3(cos(slope), -sin(slope), 0)
	var up_n := Vector3(sin(slope), cos(slope), 0)
	var ramp := _solid(e, Vector3(-13, 5, -28.5) + down * 5.5 - up_n * 0.2, Vector3(11, 0.4, 3.4), "iron", Color("3d3d40"))
	ramp.rotation.z = -slope
	# threshold under the wall gap, and the stair's side rails (no walking off into the yard)
	_solid(e, Vector3(-5.0, -0.5, -28.4), Vector3(1.0, 1.0, 4.2), "wet_asphalt", Color("111113"))
	for zr in [-26.75, -30.25]:
		var rail := _solid(e, Vector3(-8.75, 2.5, zr) + up_n * 0.5, Vector3(9.9, 1.0, 0.1), "iron", Color("3d3d40"))
		rail.rotation.z = -slope
	_near_roof = _solid(e, Vector3(-16.3, 2.5, -29.0), Vector3(6.6, 5, 8), "brick_dark", Color("2a2a2c"))
	# the far roof: its east face is the dark wall across the gap, taller than the roof we stand on
	_far_roof = _solid(e, Vector3(-26.25, 3.5, -29.0), Vector3(7.5, 7, 8), "brick", Color("2a2a2c"))
	_checkpoint_at("roof", Vector3(-14.5, 5.05, -29.0))
	_checkpoint_at("ramp_foot", Vector3(-2.0, 0.05, -28.5))
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
	_solid(p, Vector3(5.5, 3, -53.5), Vector3(1, 6, 3), "plaster")
	_solid(p, Vector3(5.5, 3, -62.5), Vector3(1, 6, 7), "plaster")
	_solid(p, Vector3(9.25, -0.5, -59), Vector3(6.5, 1, 14), "wet_floorboards", Color("111113"))
	# threshold floor under the wall line: without it the 4 m opening drops the player out of the wing
	_solid(p, Vector3(5.5, -0.5, -59), Vector3(1, 1, 14), "wet_floorboards", Color("111113"))
	_checkpoint_at("precinct", Vector3(8.5, 0.05, -60))
	_solid(p, Vector3(12.5, 3, -59), Vector3(1, 6, 14), "plaster")
	_solid(p, Vector3(9.25, 3, -52.5), Vector3(6.5, 6, 1), "plaster")
	_solid(p, Vector3(9.25, 3, -66.5), Vector3(6.5, 6, 1), "plaster")
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
	lamp_switch.position = Vector3(5.5, 1.2, -58.8)  # on the doorway's south jamb, outside the room
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
	_solid(c, Vector3(0, -0.5, -78), Vector3(12, 1, 24), "wet_carpet", Color("111113"))
	_solid(c, Vector3(-6.5, 3, -78), Vector3(1, 6, 24), "velvet")
	_solid(c, Vector3(6.5, 3, -78), Vector3(1, 6, 24), "velvet")
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
	_solid(c, Vector3(-3.5, 3, -90.5), Vector3(5, 6, 1), "plaster")
	_solid(c, Vector3(3.5, 3, -90.5), Vector3(5, 6, 1), "plaster")
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
	_solid(b, Vector3(0, -0.5, -95), Vector3(8, 1, 8), "wet_floorboards", Color("111113"))
	_solid(b, Vector3(-4.5, 2, -95), Vector3(1, 4, 8), "brick_dark")
	_solid(b, Vector3(4.5, 2, -95), Vector3(1, 4, 8), "brick_dark")
	_solid(b, Vector3(0, 2, -99.5), Vector3(10, 4, 1), "brick_dark")
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
	var shard := _model(spot, "res://wings/noir/models/frame_stand.glb", Vector3(0, -0.06, 0))
	var glow := OmniLight3D.new()
	glow.position = Vector3(0, 0.1, 0.3)
	glow.light_color = Color(1.0, 0.85, 0.6)
	glow.light_energy = 0.8
	glow.omni_range = 2.0
	shard.add_child(glow)
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
	var mono: ShaderMaterial = _dress.get("mono")
	create_tween().tween_method(func(v: float) -> void: mono.set_shader_parameter(&"amount", v), 1.0, 0.0, 0.8)
	await get_tree().create_timer(11.0).timeout
	mono.set_shader_parameter(&"amount", 1.0)
	Post.apply(grade, 0.0)
	finish()


func _build_shot_marks() -> void:
	# one camera mark per area view worth a screenshot: [name, position, look-at]
	var root := Node3D.new()
	root.name = "ShotMarks"
	add_child(root)
	var marks := [
		["alley_entry", Vector3(0.6, 1.7, -1.0), Vector3(0.0, 2.2, -20.0)], ["alley_latch", Vector3(0.5, 1.5, -14.5), Vector3(-2.0, 2.0, -20.5)],
		["alley_crate", Vector3(-1.4, 1.4, -15.8), Vector3(-2.6, 0.8, -10.5)], ["street_lamps", Vector3(1.6, 1.7, -21.5), Vector3(-1.2, 1.6, -46.0)],
		["diner_window", Vector3(-2.2, 1.6, -29.0), Vector3(3.8, 2.0, -37.0)], ["roof_gap", Vector3(-14.5, 6.4, -30.5), Vector3(-25.0, 7.6, -28.5)],
		["roof_train", Vector3(-14.2, 6.3, -26.2), Vector3(-28.0, 9.0, -31.0)], ["plaza_figures", Vector3(-1.5, 1.7, -51.0), Vector3(0.3, 1.1, -59.0)],
		["precinct_desk", Vector3(6.6, 1.6, -60.5), Vector3(10.0, 0.9, -55.5)], ["precinct_locker", Vector3(10.6, 1.6, -58.0), Vector3(6.8, 1.0, -63.2)],
		["cinema_lattice", Vector3(-2.0, 2.4, -67.5), Vector3(0.5, 2.6, -89.0)], ["booth_frame", Vector3(2.6, 1.6, -92.5), Vector3(0.0, 1.0, -97.4)],
	]
	for m: Array in marks:
		var mk := Marker3D.new()
		mk.name = m[0]
		root.add_child(mk)
		mk.look_at_from_position(m[1], m[2], Vector3.UP)
		mk.add_to_group(&"shot_marks")
