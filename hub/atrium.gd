extends Wing
## The Atrium: a dodecagonal hall, 48 m across, columns climbing into darkness. Exhibit 0 (your
## shattered world) turns over the central dais; six gilt frames on alternating bays are living
## windows into the wings. The even bays hold: 0 the sealed entrance, 2 THE THIEF, ACQUIRED,
## 4 the Conservation door (template wing), 6 the Private Collection alcove, 8/10 docents.
##
## Built in code from the Blender kit (hub/models/*.glb, materials by name) so the layout stays a
## few constants. Progression is read from Save on every entry; nothing here is scripted per visit
## except the intro (once) and the sphere-fill ceremony (once per returned fragment).

signal finale_finished(choice: StringName)

const APOTHEM := 24.0
const SPHERE_Y := 5.4
const WING_ORDER: Array[StringName] = [&"glass", &"clay", &"noir", &"aria", &"chitin", &"paint"]
const FRAME_BAYS: Array[int] = [1, 3, 5, 7, 9, 11]
const DOOR_BAY := 4
const THIEF_BAY := 2
const ALCOVE_BAY := 6

const MEDIUM := {
	&"glass": "Stained glass, lead, a standing sun",
	&"clay": "Plasticine, thumbprints, twelve frames a second",
	&"noir": "Silver nitrate, rain, a confession",
	&"aria": "Seawater, pressure, a held note",
	&"chitin": "Silk, wax, the consent of the hive",
	&"paint": "Oil, turpentine, unfinished",
}
const BODY := {
	&"glass": "A kingdom that lived inside its own windows. Its three suns were never permitted to set; the Curator considers this a kindness. Walk only where the light falls.",
	&"clay": "A forest made by hand, one frame at a time. The hand is no longer attached to anyone. The trees remember being squeezed and will take any shape you insist on.",
	&"noir": "A city that was only ever night. Its shadows are deeper than its streets; residents travel by them. The detective's file on the Curator is incomplete. Pages 4 to 9 are on loan.",
	&"aria": "An opera house that kept singing after the flood. Here a held note lifts and a low one sinks. The final aria has never been performed. The Curator holds the score.",
	&"chitin": "A royal court of insects, governed by thread. Every corridor was spun by someone who meant it. Visitors are asked to leave no silk of their own.",
	&"paint": "Acquired before it was finished. The painter has not been informed. Surfaces remain wet and will take a mark; the Curator would prefer they did not.",
}

var _frames: Dictionary = {}     # wing id -> {node, portal_mat, light, trigger, placard}
var _door_trigger: TriggerZone
var _sphere: Node3D
var _sphere_light: OmniLight3D
var _rings: Array[Node3D] = []
var _shards: Array[Dictionary] = []  # {node, dir, phase, wing}
var _shard_gap: float = 0.16
var _docents: Array[Dictionary] = []  # {root, head, next_sketch}
var _thief: Node3D
var _plaques: Dictionary = {}    # name -> Placard
var _shafts: Array[SpotLight3D] = []
var _distant_t: float = 25.0
var _choice: CanvasLayer
var _finale_running: bool = false
var _t: float = 0.0


func objectives() -> Array[Dictionary]:
	var steps: Array = []
	for id in WING_ORDER:
		var info := Game.registry.get_info(id)
		steps.append({"id": String(id), "title": "%s  ·  %s" % [info.numeral, info.title]})
	return [{"id": "exhibit0", "title": "Recover the six fragments of Exhibit 0", "steps": steps,
		"hint": "Walk into a frame."}]


func _ready() -> void:
	_build_floor()
	_build_bays()
	_build_columns()
	_build_dais_and_sphere()
	_build_frames()
	_build_door()
	_build_alcove()
	_build_thief()
	_build_docents()
	_build_bench(Vector3(0, 0, 11.5))
	_build_atmosphere()
	_build_placards()


func on_enter(_first_time: bool) -> void:
	for id in WING_ORDER:
		if Quest.has_fragment(id) and not Quest.is_step_done(&"exhibit0", id):
			Quest.complete_step(&"exhibit0", id)
	if Game.arrival != &"" and _frames.has(Game.arrival):
		_spawn_facing(entry_point(Game.arrival), 3.2)
	elif Game.arrival == &"_template":
		_spawn_facing(entry_point(&"_template"), 3.0)
	Game.arrival = &""
	Audio.emitter(Audio.stream("sphere_hum"), _sphere, -8.0, 6.0)
	var hub: Dictionary = Save.data["hub"]
	if not hub.get("seen_intro", false):
		await _intro()
	await _place_returned_fragments()
	_refresh_placards(true)


# --- public API (tests, debug) ---------------------------------------------------------

## Where to stand to enter a wing (frame) or the Conservation Studio (`&"_template"`).
func entry_point(id: StringName) -> Vector3:
	if id == &"_template":
		return _door_trigger.global_position * Vector3(1, 0, 1)
	return (_frames[id]["trigger"] as Node3D).global_position * Vector3(1, 0, 1)


func finale_available() -> bool:
	return Quest.fragment_count() >= 6 and String(Save.data.get("ending", "")) == ""


func start_finale(choice: StringName) -> void:
	if _finale_running:
		return
	_finale_running = true
	_close_choice()
	if choice == &"restore":
		await _ending_restore()
	else:
		await _ending_break()
	Save.data["ending"] = String(choice)
	Save.save_game()
	finale_finished.emit(choice)
	Game.quit_to_title()


# --- layout helpers --------------------------------------------------------------------------

func _bay_xform(bay: int, r: float) -> Transform3D:
	var a := float(bay) * TAU / 12.0
	var dir := Vector3(sin(a), 0, cos(a))
	# local +Z faces the centre
	return Transform3D(Basis(Vector3.UP, a + PI), dir * r)


func _model(name_: String, xf: Transform3D, parent: Node = self) -> Node3D:
	var n := MaterialLib.instance("res://hub/models/%s.glb" % name_)
	n.transform = xf
	parent.add_child(n)
	return n


func _mat(path: String) -> Material:
	return load(path)


func _spawn_facing(p: Vector3, out: float) -> void:
	var dir := (-p).normalized()
	var pos := p + dir * out + Vector3(0, 0.05, 0)
	Game.player.teleport(Transform3D(Basis.looking_at(dir, Vector3.UP), pos))


func _box(size: Vector3, xf: Transform3D, mat: Material, collide: bool = true, parent: Node = self) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.transform = xf
	parent.add_child(mi)
	if collide:
		var sb := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = size
		cs.shape = sh
		sb.add_child(cs)
		mi.add_child(sb)
	return mi


# --- architecture -----------------------------------------------------------------------------

func _build_floor() -> void:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(76, 76)
	pm.subdivide_width = 8
	pm.subdivide_depth = 8
	mi.mesh = pm
	var sm := ShaderMaterial.new()
	sm.shader = load("res://hub/shaders/floor.gdshader")
	sm.set_shader_parameter("marble_a", load("res://assets/textures/marble_black/marble_black_albedo.png"))
	sm.set_shader_parameter("marble_a_n", load("res://assets/textures/marble_black/marble_black_normal.png"))
	sm.set_shader_parameter("marble_b", load("res://assets/textures/marble_ivory/marble_ivory_albedo.png"))
	mi.material_override = sm
	add_child(mi)
	var sb := StaticBody3D.new()
	sb.set_meta(&"surface", &"marble")
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(76, 1, 76)
	cs.shape = sh
	cs.position.y = -0.5
	sb.add_child(cs)
	add_child(sb)


func _build_bays() -> void:
	for bay in 12:
		if bay == ALCOVE_BAY:
			continue
		_model("wall", _bay_xform(bay, APOTHEM + 0.4))


## Twelve 40 m columns at the vertices, drawn as one MultiMesh (one draw call per surface).
func _build_columns() -> void:
	var src := (load("res://hub/models/column.glb") as PackedScene).instantiate()
	var col_mi: MeshInstance3D = src.find_child("column", true, false)
	var mesh := col_mi.mesh.duplicate() as ArrayMesh
	for i in mesh.get_surface_count():
		var m := mesh.surface_get_material(i)
		var lib := MaterialLib.lookup(m.resource_name) if m else null
		if lib:
			mesh.surface_set_material(i, lib)
	src.free()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = 12
	var r := APOTHEM / cos(PI / 12.0) - 0.9
	for i in 12:
		var a := (float(i) + 0.5) * TAU / 12.0
		var p := Vector3(sin(a), 0, cos(a)) * r
		mm.set_instance_transform(i, Transform3D(Basis(Vector3.UP, a), p))
		var sb := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var cyl := CylinderShape3D.new()
		cyl.radius = 1.4
		cyl.height = 8.0
		cs.shape = cyl
		cs.position = p + Vector3(0, 4, 0)
		sb.add_child(cs)
		add_child(sb)
	var mmi := MultiMeshInstance3D.new()
	mmi.name = "Columns"
	mmi.multimesh = mm
	add_child(mmi)


func _build_dais_and_sphere() -> void:
	var dais := _model("dais", Transform3D.IDENTITY)
	for rn: String in ["ring_a", "ring_b", "ring_c"]:
		var ring: Node3D = dais.find_child(rn, true, false)
		if ring:
			var pivot := Node3D.new()
			pivot.position = Vector3(0, SPHERE_Y, 0)
			add_child(pivot)
			ring.reparent(pivot, false)
			ring.scale = Vector3.ONE * 1.12
			_rings.append(pivot)
	_sphere = _model("sphere", Transform3D(Basis(), Vector3(0, SPHERE_Y, 0)))
	var skin := ShaderMaterial.new()
	skin.shader = load("res://hub/shaders/exhibit_skin.gdshader")
	var core := ShaderMaterial.new()
	core.shader = load("res://hub/shaders/exhibit_core.gdshader")
	for mi: MeshInstance3D in _sphere.find_children("*", "MeshInstance3D", true, false):
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var nm := src.resource_name if src else ""
			mi.set_surface_override_material(i, skin if nm == "exhibit_skin" else core)
		var c := mi.get_aabb().get_center()
		var wing := &""
		var nm2 := String(mi.name)
		if nm2.begins_with("frag_"):
			wing = StringName(nm2.split("_")[1])
		_shards.append({"node": mi, "dir": c.normalized(), "phase": randf() * TAU, "wing": wing})
		mi.visible = wing == &"" or _is_placed(wing)
	_sphere_light = OmniLight3D.new()
	_sphere_light.light_color = Color(1.0, 0.72, 0.38)
	_sphere_light.omni_range = 9.0
	_sphere_light.light_energy = 2.0
	_sphere_light.shadow_enabled = false
	_sphere_light.light_volumetric_fog_energy = 2.5
	_sphere.add_child(_sphere_light)
	# finale interaction at the sphere
	var it := Interactable.make_box(Vector3(6.0, 6.0, 6.0), "Touch Exhibit 0")
	it.hold_time = 1.2
	it.max_distance = 7.0
	it.enabled = false
	it.name = "SphereTouch"
	it.interacted.connect(func(_p: Player) -> void: _open_choice())
	_sphere.add_child(it)


func _build_frames() -> void:
	for i in WING_ORDER.size():
		var id := WING_ORDER[i]
		var info := Game.registry.get_info(id)
		var root := Node3D.new()
		root.name = "Frame_" + String(id)
		root.transform = _bay_xform(FRAME_BAYS[i], APOTHEM - 0.46)
		add_child(root)
		_model("frame", Transform3D.IDENTITY, root)
		var portal := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(4.6, 7.2)
		portal.mesh = qm
		portal.position = Vector3(0, 3.6, -0.25)
		var pm := ShaderMaterial.new()
		pm.shader = load("res://hub/shaders/frame_portal.gdshader")
		pm.set_shader_parameter("medium", info.portal_medium)
		pm.set_shader_parameter("art", load("res://hub/textures/portal_%s.png" % id))
		pm.set_shader_parameter("c0", info.palette[0])
		pm.set_shader_parameter("c1", info.palette[1])
		pm.set_shader_parameter("c2", info.palette[2])
		pm.set_shader_parameter("restoration", 0.0 if info.scene_exists() else 1.0)
		portal.material_override = pm
		root.add_child(portal)
		# colour spilling out of the frame onto the marble
		var spill := SpotLight3D.new()
		spill.light_color = info.palette[0].lerp(Color.WHITE, 0.35)
		spill.light_energy = 7.0 if info.scene_exists() else 3.5
		spill.spot_range = 22.0
		spill.spot_angle = 48.0
		spill.spot_attenuation = 0.9
		spill.light_volumetric_fog_energy = 1.6
		spill.position = Vector3(0, 6.2, -0.6)
		spill.rotation = Vector3(deg_to_rad(-28), PI, 0)
		root.add_child(spill)
		# gallery picture light: grazes the gilt from above so the moulding reads
		var pic := SpotLight3D.new()
		pic.light_color = Color(1.0, 0.85, 0.62)
		pic.light_energy = 4.0
		pic.spot_range = 12.0
		pic.spot_angle = 32.0
		pic.light_volumetric_fog_energy = 0.0
		pic.position = Vector3(0, 10.5, 3.2)
		pic.rotation = Vector3(deg_to_rad(-72), 0, 0)
		root.add_child(pic)
		var trig := TriggerZone.make_box(Vector3(4.2, 3.0, 1.0), false)
		trig.position = Vector3(0, 1.5, 0.35)
		root.add_child(trig)
		var cooldown := [0.0]
		trig.triggered.connect(func(_p: Player) -> void:
			if Time.get_ticks_msec() < cooldown[0] or _finale_running:
				return
			cooldown[0] = Time.get_ticks_msec() + 5000.0
			Game.enter_wing(id))
		var plq := Placard.new()
		plq.position = Vector3(4.6, 1.55, 1.42)
		root.add_child(plq)
		_frames[id] = {"node": root, "portal": pm, "light": spill, "trigger": trig, "placard": plq, "info": info}


func _build_door() -> void:
	var root := Node3D.new()
	root.name = "ConservationDoor"
	root.transform = _bay_xform(DOOR_BAY, APOTHEM)
	add_child(root)
	var ebony := _mat("res://assets/materials/ebony.tres")
	var brass := _mat("res://assets/materials/brass.tres")
	_box(Vector3(0.35, 4.0, 0.5), Transform3D(Basis(), Vector3(-1.45, 2.0, 0.1)), ebony, true, root)
	_box(Vector3(0.35, 4.0, 0.5), Transform3D(Basis(), Vector3(1.45, 2.0, 0.1)), ebony, true, root)
	_box(Vector3(3.3, 0.45, 0.55), Transform3D(Basis(), Vector3(0, 4.2, 0.1)), ebony, true, root)
	var gap := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(2.6, 4.0)
	gap.mesh = qm
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.0, 0.0, 0.0)
	dark.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	gap.material_override = dark
	gap.position = Vector3(0, 2.0, 0.02)
	root.add_child(gap)
	# a crack of work-light under the door
	var under := OmniLight3D.new()
	under.light_color = Color(1.0, 0.9, 0.75)
	under.light_energy = 0.8
	under.omni_range = 3.0
	under.light_volumetric_fog_energy = 0.0
	under.position = Vector3(0, 0.15, 0.4)
	root.add_child(under)
	var sign := Label3D.new()
	sign.text = "CONSERVATION  ·  STAFF ONLY"
	sign.font = Style.spaced(Style.CATALOG, 8)
	sign.font_size = 64
	sign.pixel_size = 0.0022
	sign.modulate = Style.GOLD
	sign.shaded = false
	sign.position = Vector3(0, 4.75, 0.4)
	root.add_child(sign)
	_box(Vector3(2.0, 0.04, 0.02), Transform3D(Basis(), Vector3(0, 4.58, 0.39)), brass, false, root)
	_door_trigger = TriggerZone.make_box(Vector3(2.4, 3.0, 1.2), false)
	_door_trigger.position = Vector3(0, 1.5, 0.9)
	root.add_child(_door_trigger)
	var cooldown := [0.0]
	_door_trigger.triggered.connect(func(_p: Player) -> void:
		if Time.get_ticks_msec() < cooldown[0] or _finale_running:
			return
		cooldown[0] = Time.get_ticks_msec() + 5000.0
		Game.enter_wing(&"_template"))


## The Private Collection: a low, velvet-dark recess behind bay 6 with 18 vitrines (3 per wing).
func _build_alcove() -> void:
	var root := Node3D.new()
	root.name = "PrivateCollection"
	root.transform = _bay_xform(ALCOVE_BAY, APOTHEM)
	add_child(root)
	var damask := _mat("res://assets/materials/damask.tres")
	var ebony := _mat("res://assets/materials/ebony.tres")
	var gilt := _mat("res://assets/materials/gilt.tres")
	var depth := 8.5
	_model("wall", Transform3D(Basis(), Vector3(0, 0, -depth - 0.6)), root)
	for s: float in [-1.0, 1.0]:
		_box(Vector3(0.6, 22.0, depth + 0.6), Transform3D(Basis(), Vector3(s * 6.4, 11.0, -depth * 0.5)), damask, true, root)
	_box(Vector3(12.2, 0.5, depth), Transform3D(Basis(), Vector3(0, 6.4, -depth * 0.5)), ebony, false, root)
	_box(Vector3(12.9, 1.0, 0.8), Transform3D(Basis(), Vector3(0, 6.4, 0.1)), gilt, false, root)
	# 18 vitrines, 3 rows of 6; row = provenance index, column = wing
	var found: Dictionary = Save.data["provenances"]
	for wi in WING_ORDER.size():
		var wid := WING_ORDER[wi]
		var info := Game.registry.get_info(wid)
		var list: Array = found.get(String(wid), [])
		for row in 3:
			var p := Vector3(-4.5 + wi * 1.8, 0, -1.8 - row * 2.2)
			_model("plinth", Transform3D(Basis(), p), root)
			var card := Label3D.new()
			card.font = Style.spaced(Style.CATALOG, 4)
			card.font_size = 32
			card.pixel_size = 0.0012
			card.shaded = false
			card.position = p + Vector3(0, 0.98, 0.36)
			card.rotation.x = deg_to_rad(-30)
			root.add_child(card)
			if row < list.size():
				card.text = "%s  ·  NO. %d" % [info.numeral, row + 1]
				card.modulate = Style.GOLD
				var obj := MeshInstance3D.new()
				obj.mesh = [SphereMesh.new(), PrismMesh.new(), TorusMesh.new()][row]
				obj.scale = Vector3.ONE * 0.2
				obj.position = p + Vector3(0, 1.3, 0)
				var m := StandardMaterial3D.new()
				m.albedo_color = info.palette[row % 3].lerp(Style.GOLD, 0.4)
				m.metallic = 0.9
				m.roughness = 0.25
				m.emission_enabled = true
				m.emission = info.palette[row % 3]
				m.emission_energy_multiplier = 0.6
				obj.material_override = m
				obj.set_meta(&"spin", true)
				root.add_child(obj)
			else:
				card.text = "RESERVED"
				card.modulate = Color(Style.IVORY_DIM, 0.6)
	var lamp := SpotLight3D.new()
	lamp.light_color = Color(1.0, 0.86, 0.66)
	lamp.light_energy = 16.0
	lamp.spot_range = 12.0
	lamp.spot_angle = 70.0
	lamp.shadow_enabled = true
	lamp.light_volumetric_fog_energy = 0.0
	lamp.position = Vector3(0, 6.0, -4.0)
	lamp.rotation.x = -PI * 0.5
	root.add_child(lamp)
	for row in 3:  # a low glow along each row of vitrines
		var glow := OmniLight3D.new()
		glow.light_color = Color(1.0, 0.82, 0.6)
		glow.light_energy = 1.2
		glow.omni_range = 4.0
		glow.light_volumetric_fog_energy = 0.0
		glow.position = Vector3(0, 2.2, -1.8 - row * 2.2)
		root.add_child(glow)
	var plq := Placard.new()
	plq.position = Vector3(-4.7, 1.55, 0.8)
	root.add_child(plq)
	_plaques["alcove"] = plq


## THE THIEF, ACQUIRED: a pedestal waiting for you. One stage per fragment returned.
func _build_thief() -> void:
	_thief = Node3D.new()
	_thief.name = "Thief"
	_thief.transform = _bay_xform(THIEF_BAY, 17.5)
	add_child(_thief)
	var n := Quest.fragment_count()
	_model("pedestal", Transform3D.IDENTITY, _thief)
	var plate := Label3D.new()
	plate.font = Style.spaced(Style.CATALOG, 6)
	plate.font_size = 48
	plate.pixel_size = 0.0016
	plate.modulate = Style.GOLD
	plate.text = "RESERVED" if n < 3 else "THE THIEF, ACQUIRED"
	plate.position = Vector3(0, 0.95, 0.66)
	_thief.add_child(plate)
	if n >= 1:  # stage 1: a sketch of the hands, pinned up
		var easel := _model("easel", Transform3D(Basis(), Vector3(0, 1.15, 0)), _thief)
		var card: MeshInstance3D = easel.find_child("card", true, false)
		var sketch := StandardMaterial3D.new()
		sketch.albedo_texture = load("res://assets/ui/vesper_sketch.png" if n >= 6 else "res://assets/ui/hands_sketch.png")
		sketch.roughness = 0.9
		var q := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(0.27, 0.34)
		q.mesh = qm
		q.material_override = sketch
		q.position = Vector3(0, 1.15 + 0.29, 0.0)
		q.rotation.x = deg_to_rad(-14)
		_thief.add_child(q)
		if card:
			card.visible = false
	if n >= 2:  # stage 2: the velvet rope
		for k in 4:
			var a := float(k) * TAU / 4.0 + PI / 4.0
			var p := Vector3(sin(a), 0, cos(a)) * 1.5
			var st := _model("stanchion", Transform3D(Basis(Vector3.UP, a + PI * 0.5), p), _thief)
			st.scale = Vector3(1.06, 1, 1)
	if n >= 3:  # stage 3: a printed placard
		var plq := Placard.new()
		plq.position = Vector3(1.9, 1.2, 1.2)
		plq.rotation.x = deg_to_rad(-20)
		plq.size = Vector2(0.8, 0.56)
		plq.heading = "—"
		plq.title = "The Thief, Acquired"
		plq.catalog_line = "Medium: flesh, grief, intent"
		plq.body = "Acquired in the act. Displayed in the round. The subject appears to be looking for something it lost; the Curator has declined to say what. Please do not feed the exhibit."
		_thief.add_child(plq)
	if n >= 4:  # stage 4: gallery lighting
		var spot := SpotLight3D.new()
		spot.light_color = Color(1.0, 0.92, 0.8)
		spot.light_energy = 24.0
		spot.spot_range = 18.0
		spot.spot_angle = 15.0
		spot.shadow_enabled = true
		spot.light_volumetric_fog_energy = 3.0
		spot.position = Vector3(0, 14, 0)
		spot.rotation.x = -PI * 0.5
		_thief.add_child(spot)


## Docent-constructs: faceless plaster figures with sketchboards. They turn to watch you. One is
## here from the start; another arrives with each fragment (max 5).
func _build_docents() -> void:
	var spots: Array[Transform3D] = [
		_bay_xform(9, 16.0),
		Transform3D(Basis(Vector3.UP, deg_to_rad(60) + PI * 0.9), _bay_xform(THIEF_BAY, 14.0).origin + Vector3(-2.5, 0, 1.0)),
		_bay_xform(7, 15.5),
		Transform3D(Basis(Vector3.UP, deg_to_rad(60) + PI * 1.1), _bay_xform(THIEF_BAY, 14.5).origin + Vector3(2.0, 0, -2.4)),
		_bay_xform(10, 13.0),
	]
	var count := clampi(1 + Quest.fragment_count(), 1, spots.size())
	for i in count:
		var xf: Transform3D = spots[i]
		# models face -Z; the bay transform faces +Z inward, so turn round
		xf.basis = xf.basis * Basis(Vector3.UP, PI)
		var d := _model("docent", xf)
		var head: Node3D = d.find_child("head", true, false)
		_docents.append({"root": d, "head": head, "next": 4.0 + randf() * 6.0})


func _build_bench(p: Vector3) -> void:
	var b := _model("bench", Transform3D(Basis(), p))
	var seat := Marker3D.new()
	seat.position = Vector3(0, 0, 0)
	b.add_child(seat)
	var it := Interactable.make_box(Vector3(2.4, 0.9, 0.7), "Sit")
	it.position.y = 0.45
	it.interacted.connect(func(pl: Player) -> void:
		var m: SeatedMode = pl.modes[&"seated"]
		m.seat = seat
		pl.set_mode(&"seated"))
	b.add_child(it)


func _build_atmosphere() -> void:
	# gold motes
	var motes := GPUParticles3D.new()
	motes.amount = 1400
	motes.lifetime = 24.0
	motes.preprocess = 24.0
	motes.visibility_aabb = AABB(Vector3(-26, -1, -26), Vector3(52, 22, 52))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(23, 9, 23)
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 180.0
	pm.initial_velocity_min = 0.02
	pm.initial_velocity_max = 0.12
	pm.gravity = Vector3(0, 0.01, 0)
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.4
	pm.turbulence_noise_scale = 6.0
	pm.scale_min = 0.5
	pm.scale_max = 1.4
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 0))
	fade.add_point(0.2, Color(1, 1, 1, 1))
	fade.add_point(0.8, Color(1, 1, 1, 1))
	fade.set_color(fade.get_point_count() - 1, Color(1, 1, 1, 0))
	var gt := GradientTexture1D.new()
	gt.gradient = fade
	pm.color_ramp = gt
	motes.process_material = pm
	var qm := QuadMesh.new()
	qm.size = Vector2(0.035, 0.035)
	var mm := StandardMaterial3D.new()
	mm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mm.vertex_color_use_as_albedo = true
	mm.albedo_color = Color(1.0, 0.78, 0.42) * 2.2
	mm.albedo_texture = _dot_texture()
	qm.material = mm
	motes.draw_pass_1 = qm
	motes.position.y = 9.5
	add_child(motes)
	# volumetric shafts from the dark above
	var shafts := [[Vector3(-6, 42, 10), Vector3(0, 0, 0), 9.0], [Vector3(14, 42, -8), Vector3(9, 0, -4), 7.0], [Vector3(-12, 42, -12), Vector3(-10, 0, -9), 6.0]]
	for i in shafts.size():
		var s := SpotLight3D.new()
		s.light_color = Color(1.0, 0.88, 0.7)
		s.light_energy = shafts[i][2]
		s.spot_range = 60.0
		s.spot_angle = 7.0 if i > 0 else 9.0
		s.spot_attenuation = 0.4
		s.light_volumetric_fog_energy = 5.0
		s.shadow_enabled = i == 0
		s.position = shafts[i][0]
		add_child(s)
		s.look_at(shafts[i][1], Vector3.FORWARD)
		_shafts.append(s)
	# low warm fill so the hall reads as a room, not a void
	var fill := OmniLight3D.new()
	fill.light_color = Color(1.0, 0.8, 0.55)
	fill.light_energy = 0.25
	fill.omni_range = 27.0
	fill.omni_attenuation = 2.2
	fill.light_volumetric_fog_energy = 0.0
	fill.position = Vector3(0, 2.5, 0) # low, so the wall tops fall away into the dark
	add_child(fill)
	var probe := ReflectionProbe.new()
	probe.size = Vector3(52, 26, 52)
	probe.position = Vector3(0, 9, 0)
	probe.box_projection = true
	probe.interior = true
	probe.update_mode = ReflectionProbe.UPDATE_ONCE
	probe.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
	add_child(probe)


func _dot_texture() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(0.5, 0.0)
	gt.width = 32
	gt.height = 32
	return gt


func _build_placards() -> void:
	var entrance := Placard.new()
	entrance.transform = _bay_xform(0, APOTHEM - 0.05)
	entrance.position.y = 1.6
	add_child(entrance)
	_plaques["entrance"] = entrance
	var dais := Placard.new()
	dais.transform = Transform3D(Basis(Vector3.UP, 0.0), Vector3(0, 0.95, 6.3))
	dais.rotation.x = deg_to_rad(-25)
	dais.size = Vector2(1.1, 0.7)
	add_child(dais)
	_plaques["dais"] = dais
	_refresh_placards(false)


## Placards rewrite themselves as the visitor progresses: catalogue voice at first, then the
## second person. `animate` crossfades only the ones that changed since the last visit.
func _refresh_placards(animate: bool) -> void:
	var n := Quest.fragment_count()
	var flags: Dictionary = Save.data["hub"]["flags"]
	var seen := int(flags.get("placard_stage", -1))
	var anim := animate and seen != n
	flags["placard_stage"] = n
	for id: StringName in _frames:
		var f: Dictionary = _frames[id]
		var info: WingInfo = f["info"]
		var cat := "Acq. No. %s  ·  %s" % [info.acquisition_no, MEDIUM[id]]
		var body: String = BODY[id]
		if Quest.has_fragment(id):
			body = "You went in and came back with a piece of yourself. This label has been amended in your hand. The Curator has not yet noticed the handwriting."
		elif not info.scene_exists():
			cat = "Gallery closed for restoration"
		(f["placard"] as Placard).set_text(info.numeral, info.title, cat, body, anim)
	var e: String = ["Closed for the duration of your stay.",
		"Closed for the duration of your stay. Your stay has been extended.",
		"Closed for the duration of your stay. You have stopped trying it. Thank you.",
		"You could leave now. The door has noticed."][0 if n == 0 else (1 if n < 3 else (2 if n < 6 else 3))]
	(_plaques["entrance"] as Placard).set_text("—", "Entrance", "Way out  ·  not in use", e, anim)
	var d: String = ["A world, damaged in transit. Six pieces are missing. They are on display elsewhere in the building, which is the same thing as being safe.",
		"A world, damaged in transit. Someone is repairing it without permission. The Curator is aware.",
		"A world, damaged in transit. You are repairing it without permission. Please continue; it is the most interesting thing in the building.",
		"Complete. You did this. The Curator would like a word, and has prepared two."][0 if n == 0 else (1 if n < 3 else (2 if n < 6 else 3))]
	(_plaques["dais"] as Placard).set_text("0", "Exhibit 0", "Acq. No. 000  ·  Medium: everything you had", d, anim)
	var provs := 0
	for k: String in Save.data["provenances"]:
		provs += (Save.data["provenances"][k] as Array).size()
	var a := "Not on public view. You are not the public." if provs == 0 else \
		"Items recovered by you, held by us. %d of 18. The arrangement is temporary on one side." % provs
	(_plaques["alcove"] as Placard).set_text("—", "The Private Collection", "By appointment", a, anim)


# --- per frame --------------------------------------------------------------------------------

func _process(delta: float) -> void:
	_t += delta * Game.world_time_scale
	var dt := delta * Game.world_time_scale
	if _sphere:
		_sphere.rotate_y(dt * 0.05)
		_sphere.position.y = SPHERE_Y + sin(_t * 0.4) * 0.08
		for s: Dictionary in _shards:
			if s.get("fly", false):
				continue
			var mi: MeshInstance3D = s["node"]
			mi.position = (s["dir"] as Vector3) * (_shard_gap + sin(_t * 0.6 + float(s["phase"])) * _shard_gap * 0.25)
	for i in _rings.size():
		var r := _rings[i]
		r.rotate(Vector3(0.3 * i, 1.0, 0.2 * (2 - i)).normalized(), dt * (0.03 + 0.02 * i) * (-1.0 if i == 1 else 1.0))
	var p := Game.player
	if p:
		for d: Dictionary in _docents:
			var head: Node3D = d["head"]
			var root: Node3D = d["root"]
			if head == null:
				continue
			var local := root.to_local(p.global_position)
			var want := clampf(atan2(-local.x, -local.z), -1.3, 1.3) if local.length() < 18.0 else 0.0
			head.rotation.y = lerp_angle(head.rotation.y, want, 1.0 - exp(-2.5 * delta))
			d["next"] = float(d["next"]) - delta
			if float(d["next"]) <= 0.0:
				d["next"] = 6.0 + randf() * 8.0
				if local.length() < 12.0:
					Audio.sfx(Audio.stream("sketch"), root.global_position + Vector3(0, 1.2, 0), -10.0, 0.4, randf_range(0.9, 1.1))
	_distant_t -= delta
	if _distant_t <= 0.0:
		_distant_t = randf_range(45.0, 90.0)
		var a := randf() * TAU
		Audio.sfx(Audio.stream("distant_movement"), Vector3(sin(a) * 40.0, 30.0, cos(a) * 40.0), -2.0, 1.0, randf_range(0.85, 1.0))
	var touch: Interactable = _sphere.get_node_or_null("SphereTouch") if _sphere else null
	if touch:
		touch.enabled = finale_available() and not _finale_running


# --- placement of returned fragments (the hub half of the Fragment ceremony) ------------------

func _is_placed(wing: StringName) -> bool:
	return String(wing) in (Save.data["hub"]["flags"].get("placed", []) as Array)


func _orbit_view(dist: float, height: float, yaw_off: float) -> Transform3D:
	var p := Vector3(0, height, dist).rotated(Vector3.UP, Game.player.yaw + yaw_off)
	return Transform3D(Basis.looking_at(Vector3(0, SPHERE_Y, 0) - p, Vector3.UP), p)


func _place_returned_fragments() -> void:
	var pending: Array[StringName] = []
	for id in WING_ORDER:
		if Quest.has_fragment(id) and not _is_placed(id):
			pending.append(id)
	if pending.is_empty():
		return
	var flights: Array[Dictionary] = []
	for s: Dictionary in _shards:
		if s["wing"] in pending:
			var f: Node3D = _frames[s["wing"]]["node"]
			flights.append({"shard": s, "from": f.global_position + Vector3(0, 4.5, 0) + f.global_basis.z * 2.0})
	var view := _orbit_view(9.5, 2.2, 0.0)
	var close := _orbit_view(6.0, 3.6, 0.25)
	await Cinematics.play([
		{"call": _stinger_quiet},
		{"cam": [Game.player.camera.global_transform, view], "t": 2.5},
		{"cam": [view, close], "t": 6.0, "async": true},
		{"call": _fly_shards.bind(flights)},
		{"wait": 1.2},
		{"card": "%d of 6" % Quest.fragment_count(), "sub": "Exhibit 0  ·  restored without permission", "t": 3.2, "style": "display"},
		{"call": _mark_placed.bind(pending), "always": true},
	])


func _stinger_quiet() -> void:
	Audio.reveal(Audio.stream("placard"), 2.0)


func _fly_shards(flights: Array[Dictionary]) -> void:
	Audio.sfx(Audio.stream("transition"), null, -8.0, 0.6)
	for fl: Dictionary in flights:
		var s: Dictionary = fl["shard"]
		s["fly"] = true
		s["from"] = fl["from"]
		(s["node"] as MeshInstance3D).visible = true
	var tw := create_tween()
	tw.tween_method(_fly_step.bind(flights), 0.0, 1.0, 3.2)
	await tw.finished
	for fl: Dictionary in flights:
		(fl["shard"] as Dictionary)["fly"] = false
	Audio.sfx(Audio.stream("fragment"), _sphere.global_position, 0.0, 0.8)
	if Game.player:
		Game.player.add_trauma(0.35)
	var flash := create_tween()
	flash.tween_property(_sphere_light, "light_energy", 14.0, 0.15)
	flash.tween_property(_sphere_light, "light_energy", 2.0 + Quest.fragment_count() * 0.6, 2.5)


func _fly_step(u: float, flights: Array[Dictionary]) -> void:
	var e := ease(u, -2.2)
	for fl: Dictionary in flights:
		var s: Dictionary = fl["shard"]
		var home: Vector3 = (s["dir"] as Vector3) * _shard_gap
		var from_l := _sphere.to_local(fl["from"])
		(s["node"] as MeshInstance3D).position = from_l.lerp(home, e) + Vector3(0, sin(u * PI) * 3.0, 0)


func _mark_placed(pending: Array[StringName]) -> void:
	var placed: Array = Save.data["hub"]["flags"].get("placed", [])
	for id in pending:
		if not String(id) in placed:
			placed.append(String(id))
	Save.data["hub"]["flags"]["placed"] = placed
	Save.save_game()
	for s: Dictionary in _shards:
		s["fly"] = false
		(s["node"] as MeshInstance3D).visible = s["wing"] == &"" or _is_placed(s["wing"])
	_shard_gap = 0.16 - 0.02 * Quest.fragment_count()


# --- intro --------------------------------------------------------------------------------

## Premise cards, then the reveal recipe: dark compressed approach with the view occluded by a
## column, release into the hall with a human-scale object (the bench) in frame, near-silence,
## stinger, camera freed.
func _intro() -> void:
	var c0 := Transform3D(Basis.looking_at(Vector3(-1.0, 0.2, -1.0).normalized(), Vector3.UP), Vector3(9.2, 1.5, 21.2))
	var c1 := Transform3D(Basis.looking_at(Vector3(-0.55, 0.05, -1.0).normalized(), Vector3.UP), Vector3(7.0, 1.6, 20.0))
	var c2 := Transform3D(Basis.looking_at(Vector3(-0.25, 0.12, -1.0).normalized(), Vector3.UP), Vector3(3.0, 1.65, 18.8))
	var c3p := Vector3(0.4, 1.7, 17.0)
	var c3 := Transform3D(Basis.looking_at(Vector3(0, SPHERE_Y - 1.7, 0) - c3p, Vector3.UP), c3p)
	await Cinematics.play([
		{"fade": 1.0, "t": 0.0},
		{"call": _intro_dark},
		{"card": "The Curator collects worlds.", "sub": "A museum of stolen realities", "t": 6.0},
		{"card": "Not paintings of worlds. The worlds themselves, cut from their skies and hung at eye level.", "t": 7.5, "style": "body"},
		{"card": "Six were acquired this century. Each one was someone's home.", "t": 6.5, "style": "body"},
		{"card": "The seventh was yours. It arrived broken. It is catalogued as Exhibit 0.", "t": 7.0, "style": "body"},
		{"card": "You came to take it back.", "t": 5.0},
		{"card": "You were caught in the act. You have been catalogued too.", "t": 6.0, "style": "body"},
		{"cam": [c0, c1], "t": 9.0, "fov": 55.0, "async": true},
		{"fade": 0.0, "t": 4.0},
		{"wait": 4.0},
		{"call": _intro_release},
		{"cam": [c1, c2, c3], "t": 12.0, "fov": 62.0},
		{"wait": 2.0},
		{"card": "The Thief, Acquired.", "sub": "Exhibit pending", "t": 5.0, "style": "display"},
		{"call": _intro_done, "always": true},
	])


func _awaken(v: float, t: float) -> void:
	var tw := create_tween().set_parallel()
	for id: StringName in _frames:
		var f: Dictionary = _frames[id]
		var full := 7.0 if (f["info"] as WingInfo).scene_exists() else 3.5
		_tween_param(tw, f["portal"], "awaken", v, maxf(t, 0.01))
		tw.tween_property(f["light"], "light_energy", full * v, maxf(t, 0.01))
	for s in _shafts:
		tw.tween_property(s, "light_volumetric_fog_energy", 5.0 * v, maxf(t, 0.01))


func _intro_dark() -> void:
	_awaken(0.0, 0.0)
	Audio.set_intensity(0.0, 0.5)


func _intro_release() -> void:
	Audio.reveal(Audio.stream("fragment"), 3.0)
	_awaken(1.0, 6.0)


func _intro_done() -> void:
	_awaken(1.0, 0.0)
	Post.fade_to(0.0, 0.0)
	Audio.set_intensity(music_intensity, 4.0)
	Game.player.teleport(find_checkpoint(&"start").global_transform)
	Save.data["hub"]["seen_intro"] = true
	Save.save_game()


# --- finale ---------------------------------------------------------------------------------

func _open_choice() -> void:
	if not finale_available() or _choice:
		return
	_choice = CanvasLayer.new()
	_choice.layer = 85
	var bg := ColorRect.new()
	bg.color = Color(Style.INK, 0.72)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_choice.add_child(bg)
	var box := VBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_CENTER)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	box.add_theme_constant_override(&"separation", 18)
	box.grow_horizontal = Control.GROW_DIRECTION_BOTH
	box.grow_vertical = Control.GROW_DIRECTION_BOTH
	_choice.add_child(box)
	box.add_child(Style.catalog("Exhibit 0  ·  complete", 18, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
	box.add_child(Style.label("It is whole. It is yours. It is also the only thing holding the collection together.", Style.ITALIC, 30, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER))
	for pair: Array in [[&"restore", "Restore your world"], [&"break", "Break the collection"]]:
		var b := Button.new()
		b.text = pair[1]
		b.custom_minimum_size = Vector2(420, 56)
		b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		var choice: StringName = pair[0]
		b.pressed.connect(func() -> void: start_finale(choice))
		box.add_child(b)
	var back := Button.new()
	back.text = "Not yet"
	back.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	back.pressed.connect(_close_choice)
	box.add_child(back)
	add_child(_choice)
	Game.player.input_enabled = false
	Game.player.look_enabled = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	Audio.ui(&"open")


func _close_choice() -> void:
	if _choice:
		_choice.queue_free()
		_choice = null
		if Game.player:
			Game.player.input_enabled = true
			Game.player.look_enabled = true
		if Game.state == Game.State.PLAYING and not _finale_running:
			Game.set_state(Game.State.PLAYING)


func _orbit(radius: float, height: float, from_a: float, to_a: float, n: int = 6) -> Array[Transform3D]:
	var out: Array[Transform3D] = []
	var look := Vector3(0, SPHERE_Y, 0)
	for i in n:
		var a := lerpf(from_a, to_a, float(i) / float(n - 1))
		var p := Vector3(sin(a) * radius, height, cos(a) * radius)
		out.append(Transform3D(Basis.looking_at(look - p, Vector3.UP), p))
	return out


func _credits() -> Array:
	var cc: PackedStringArray = []
	var f := FileAccess.open("res://CREDITS.md", FileAccess.READ)
	if f:
		for line in f.get_as_text().split("\n"):
			var cols := line.split("|")
			if cols.size() >= 6 and cols[5].strip_edges().begins_with("CC-BY"):
				cc.append("%s — %s (%s)" % [cols[2].strip_edges(), cols[3].strip_edges(), cols[5].strip_edges()])
	var steps: Array = [
		{"card": "Museum of Stolen Realities", "sub": "Credits", "t": 4.0, "style": "display"},
		{"card": "Made with Godot Engine (MIT).\nType: Gloock, Italiana, Crimson Pro, Arsenal SC (SIL Open Font License).", "sub": "With thanks", "t": 5.0, "style": "body"},
	]
	if not cc.is_empty():
		steps.append({"card": "\n".join(cc), "sub": "Sound and music under Creative Commons Attribution", "t": 6.0, "style": "body"})
	return steps



func _ending_restore() -> void:
	var steps: Array = [
		{"call": _restore_begin},
		{"cam": _orbit(11.0, 3.0, Game.player.yaw, Game.player.yaw + 1.6), "t": 12.0, "fov": 55.0, "async": true},
		{"call": _restore_heal},
		{"wait": 9.0},
		{"fade": 1.0, "t": 2.5},
		{"card": "You put your world back together.", "t": 5.0},
		{"card": "It is small enough to carry. You carry it out through the door that had noticed.", "t": 6.5, "style": "body"},
		{"card": "Six worlds remain on the walls. The Curator has already written your placard.", "t": 6.5, "style": "body"},
	]
	steps.append_array(_credits())
	await Cinematics.play(steps)


func _restore_begin() -> void:
	Audio.stop_music(3.0)
	Audio.reveal(Audio.stream("ending_restore"), 2.5)


func _restore_heal() -> void:
	var tw := create_tween().set_parallel()
	tw.tween_property(self, "_shard_gap", 0.0, 6.0).set_trans(Tween.TRANS_SINE)
	tw.tween_property(_sphere_light, "light_energy", 18.0, 8.0)
	tw.tween_property(_sphere_light, "omni_range", 30.0, 8.0)
	var k := 0
	for id: StringName in _frames:
		_tween_param(tw, _frames[id]["portal"], "awaken", 0.0, 1.5).set_delay(2.0 + k * 0.9)
		tw.tween_property(_frames[id]["light"], "light_energy", 0.0, 1.5).set_delay(2.0 + k * 0.9)
		k += 1


func _ending_break() -> void:
	var steps: Array = [
		{"call": _break_begin},
		{"cam": _orbit(16.0, 2.0, Game.player.yaw, Game.player.yaw - 2.4, 8), "t": 13.0, "fov": 62.0, "async": true},
		{"call": _break_open},
		{"wait": 9.5},
		{"fade": 1.0, "t": 1.5},
		{"card": "You opened every frame.", "t": 4.5},
		{"card": "Seven worlds went home at once. Yours went with them, in pieces, and the pieces were glad.", "t": 7.0, "style": "body"},
		{"card": "The building is empty. Somewhere a placard is still describing you.", "t": 6.5, "style": "body"},
	]
	steps.append_array(_credits())
	await Cinematics.play(steps)


func _break_begin() -> void:
	Audio.stop_music(1.5)
	Audio.sfx(Audio.stream("ending_break"), null, 0.0, 0.8)


func _break_open() -> void:
	var tw := create_tween().set_parallel()
	for id: StringName in _frames:
		_tween_param(tw, _frames[id]["portal"], "brightness", 6.0, 6.0)
		tw.tween_property(_frames[id]["light"], "light_energy", 40.0, 6.0)
		tw.tween_property(_frames[id]["light"], "spot_range", 45.0, 6.0)
	tw.tween_property(self, "_shard_gap", 2.2, 8.0).set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_IN)
	tw.tween_method(_shake, 0.0, 0.05, 8.0)


func _shake(v: float) -> void:
	if Game.player:
		Game.player.add_trauma(v)


## Tween a shader uniform via set_shader_parameter (property paths fail when the renderer has
## not reflected the uniforms, e.g. headless).
func _tween_param(tw: Tween, mat: ShaderMaterial, param: String, to: float, t: float) -> MethodTweener:
	var from: Variant = mat.get_shader_parameter(param)
	if from == null:
		from = 1.0
	return tw.tween_method(func(v: float) -> void: mat.set_shader_parameter(param, v), float(from), to, t)
