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
const SPHERE_Y := 6.2
const WING_ORDER: Array[StringName] = [&"glass", &"clay", &"noir", &"aria", &"chitin", &"paint"]
const FRAME_BAYS: Array[int] = [1, 3, 5, 7, 9, 11]
const DOOR_BAY := 4
const THIEF_BAY := 2
const ALCOVE_BAY := 6
const MATS: Array = ["res://hub/materials", MaterialLib.CORE_DIR]
## The hub theme ("Immersed", Kevin MacLeod, CC-BY): seven band layers of one recording, 64 bpm 4/4.
## Layer 0 (the low band) plays from the start; each returned Fragment brings back the next band, so
## the music grows clearer as your world does. Changes wait for a bar line.
const THEME_BAR := 3.75

const MEDIUM := {
	&"glass": "Stained glass, lead, a standing sun",
	&"clay": "Plasticine, thumbprints, twelve frames a second",
	&"noir": "Silver nitrate, rain, a confession",
	&"aria": "Seawater, pressure, a held note",
	&"chitin": "Silk, wax, the consent of the hive",
	&"paint": "Oil, turpentine, unfinished",
}
## Tombstone dates (in-fiction acquisition years).
const DATE := {
	&"glass": "Acquired 1904", &"clay": "Acquired 1958", &"noir": "Acquired 1947",
	&"aria": "Acquired 1912", &"chitin": "Acquired 1979", &"paint": "Acquired, unfinished",
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
var _chips: Array[Dictionary] = []  # {node, r, a, y, speed, spin}
var _docents: Array[Dictionary] = []  # {root, head, next_sketch}
var _thief: Node3D
var _thief_fig: Dictionary = {}  # {body, head, arm, arm_rest}: the figure on the pedestal, idling
var _plaques: Dictionary = {}    # name -> Placard
var _skin: ShaderMaterial
var _weather: Dictionary = {}    # wing id -> 0..1, that wing's inner weather in Exhibit 0
var _thief_stage: int = 0
var _relics: Array[Dictionary] = []  # {wing, title, node} per filled vitrine
var _shafts: Array[SpotLight3D] = []
var _probe: ReflectionProbe
var _distant_t: float = 25.0
var _choice: CanvasLayer
var _finale_running: bool = false
var _t: float = 0.0


func objectives() -> Array[Dictionary]:
	var steps: Array = []
	for id in WING_ORDER:
		var winfo := Game.registry.get_info(id)
		steps.append({"id": String(id), "title": "%s. %s" % [winfo.numeral, winfo.title]})
	return [{"id": "exhibit0", "title": "Recover the six fragments of Exhibit 0", "steps": steps,
		"hint": "Walk into a frame."}]


func _ready() -> void:
	music_intensity = Quest.fragment_count() / 6.0  # read by Game.register_wing when it starts the bed
	var steps: Array[AudioStream] = []
	for i in range(1, 9):
		steps.append(_cc("step_marble_hall_%d" % i))
	Audio.register_footsteps(&"marble_hall", steps)
	_build_floor()
	_build_bays()
	_build_columns()
	_build_dais_and_sphere()
	_build_frames()
	_build_door()
	_build_alcove()
	_build_thief()
	_build_docents()
	_build_bench(Vector3(-3.6, 0, 10.5))  # beside the entrance axis: the first walk to the sphere is clear
	_build_atmosphere()
	_build_placards()
	_build_shot_marks()


func on_enter(_first_time: bool) -> void:
	for id in WING_ORDER:
		if Quest.has_fragment(id) and not Quest.is_step_done(&"exhibit0", id):
			Quest.complete_step(&"exhibit0", id)
	if Game.arrival != &"" and _frames.has(Game.arrival):
		_spawn_facing(entry_point(Game.arrival), 3.2)
	elif Game.arrival == &"_template":
		_spawn_facing(entry_point(&"_template"), 3.0)
	Game.arrival = &""
	Audio.music_bar = THEME_BAR
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


## What the hub currently shows for one wing (tests read this to check that a return changed it).
func debug_state(id: StringName) -> Dictionary:
	var shard_on := false
	for s: Dictionary in _shards:
		if s["wing"] == id and (s["node"] as MeshInstance3D).visible:
			shard_on = true
	var titles: Array = []
	for r: Dictionary in _relics:
		if r["wing"] == id:
			titles.append(r["title"])
	var f: Dictionary = _frames[id]
	return {
		"placed": _is_placed(id),
		"shard_visible": shard_on,
		"weather": float(_weather.get(id, 0.0)),
		"relics": titles,
		"frame_body": (f["placard"] as Placard).body,
		"thief_stage": _thief_stage,
	}


# --- layout helpers --------------------------------------------------------------------------

func _bay_xform(bay: int, r: float) -> Transform3D:
	var a := float(bay) * TAU / 12.0
	var dir := Vector3(sin(a), 0, cos(a))
	# local +Z faces the centre
	return Transform3D(Basis(Vector3.UP, a + PI), dir * r)


func _model(name_: String, xf: Transform3D, parent: Node = self) -> Node3D:
	var n := MaterialLib.instance("res://hub/models/%s.glb" % name_, MATS)
	n.transform = xf
	parent.add_child(n)
	return n


func _mat(path: String) -> Material:
	return load(path)


func _aim(from: Vector3, to: Vector3) -> Transform3D:
	return Transform3D(Basis.looking_at(to - from, Vector3.UP), from)


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
	sb.set_meta(&"surface", &"marble_hall")
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(76, 1, 76)
	cs.shape = sh
	cs.position.y = -0.5
	sb.add_child(cs)
	add_child(sb)


func _build_bays() -> void:
	var xfs: Array[Transform3D] = []
	for bay in 12:
		xfs.append(_bay_xform(bay, APOTHEM + 0.4))
	_multimesh("gallery", xfs)  # high and out of reach: no collision, no shadows, one draw per surface
	for bay in 12:
		if bay == ALCOVE_BAY:
			continue
		_model("wall", _bay_xform(bay, APOTHEM + 0.4))
	var dome := _model("dome", Transform3D.IDENTITY)
	for mi: MeshInstance3D in dome.find_children("*", "MeshInstance3D", true, false):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


## Every mesh of a hub model instanced at each transform (MaterialLib names remapped).
func _multimesh(name_: String, xfs: Array[Transform3D]) -> void:
	var src := (load("res://hub/models/%s.glb" % name_) as PackedScene).instantiate()
	for mi: MeshInstance3D in src.find_children("*", "MeshInstance3D", true, false):
		var mesh := mi.mesh.duplicate() as ArrayMesh
		for i in mesh.get_surface_count():
			var m := mesh.surface_get_material(i)
			var lib := MaterialLib.lookup(m.resource_name, MATS) if m else null
			if lib is StandardMaterial3D:
				# far overhead: matte, so SSR skips these pixels (saves ~3 ms at 1440p)
				var matte := (lib as StandardMaterial3D).duplicate() as StandardMaterial3D
				matte.roughness_texture = null
				matte.roughness = 0.9
				mesh.surface_set_material(i, matte)
			elif lib:
				mesh.surface_set_material(i, lib)
		var local: Transform3D = mi.transform
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = xfs.size()
		for i in xfs.size():
			mm.set_instance_transform(i, xfs[i] * local)
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "%s_%s" % [name_, mi.name]
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mmi)
	src.free()


## Twelve 40 m columns at the vertices, drawn as one MultiMesh (one draw call per surface).
func _build_columns() -> void:
	var src := (load("res://hub/models/column.glb") as PackedScene).instantiate()
	var col_mi: MeshInstance3D = src.find_child("column", true, false)
	var mesh := col_mi.mesh.duplicate() as ArrayMesh
	for i in mesh.get_surface_count():
		var m := mesh.surface_get_material(i)
		var lib := MaterialLib.lookup(m.resource_name, MATS) if m else null
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
			_rings.append(pivot)
	_sphere = _model("sphere", Transform3D(Basis(), Vector3(0, SPHERE_Y, 0)))
	var skin := ShaderMaterial.new()
	skin.shader = load("res://hub/shaders/exhibit_skin.gdshader")
	_skin = skin
	var core := ShaderMaterial.new()
	core.shader = load("res://hub/shaders/exhibit_core.gdshader")
	var world := ShaderMaterial.new()
	world.shader = load("res://hub/shaders/exhibit_world.gdshader")
	for mi: MeshInstance3D in _sphere.find_children("*", "MeshInstance3D", true, false):
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var nm := src.resource_name if src else ""
			var glass := skin if not String(mi.name).begins_with("chip_") else _chip_skin(skin)
			mi.set_surface_override_material(i, glass if nm == "exhibit_skin" else (world if nm == "exhibit_world" else core))
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if String(mi.name) == "world":
			continue
		if String(mi.name).begins_with("chip_"):
			_chips.append({"node": mi, "r": randf_range(2.9, 4.6), "a": randf() * TAU, "y": randf_range(-1.6, 1.6),
				"speed": randf_range(0.05, 0.16) * (1.0 if randf() > 0.25 else -1.0), "spin": Vector3(randf(), randf(), randf()).normalized()})
			continue
		var c := mi.get_aabb().get_center()
		var wing := &""
		var nm2 := String(mi.name)
		if nm2.begins_with("frag_"):
			wing = StringName(nm2.split("_")[1])
		_shards.append({"node": mi, "dir": c.normalized(), "phase": randf() * TAU, "wing": wing})
		mi.visible = wing == &"" or _is_placed(wing)
	for id in WING_ORDER:
		_weather[id] = 1.0 if _is_placed(id) else 0.0
		skin.set_shader_parameter("w_" + String(id), _weather[id])
	_sphere_light = OmniLight3D.new()
	_sphere_light.light_color = _sphere_tint()
	_sphere_light.omni_range = 17.0  # the brightest pool in the hall: the floor glows round the dais
	_sphere_light.light_energy = 3.4
	_sphere_light.shadow_enabled = false
	_sphere_light.light_volumetric_fog_energy = 0.6  # a halo, not milk
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
		var winfo := Game.registry.get_info(id)
		var root := Node3D.new()
		root.name = "Frame_" + String(id)
		root.transform = _bay_xform(FRAME_BAYS[i], APOTHEM - 0.46)
		add_child(root)
		_round_frame_posts(_model("frame", Transform3D.IDENTITY, root))
		var portal := MeshInstance3D.new()
		var qm := QuadMesh.new()
		qm.size = Vector2(4.6, 7.2)
		portal.mesh = qm
		portal.position = Vector3(0, 3.6, -0.45)
		var pm := ShaderMaterial.new()
		pm.shader = load("res://hub/shaders/frame_portal.gdshader")
		pm.set_shader_parameter("medium", winfo.portal_medium)
		pm.set_shader_parameter("art", load("res://hub/textures/portal_%s.png" % id))
		pm.set_shader_parameter("c0", winfo.palette[0])
		pm.set_shader_parameter("c1", winfo.palette[1])
		pm.set_shader_parameter("c2", winfo.palette[2])
		pm.set_shader_parameter("restoration", 0.0 if winfo.scene_exists() else 1.0)
		portal.material_override = pm
		root.add_child(portal)
		# colour spilling out of the frame onto the marble
		var spill := SpotLight3D.new()
		spill.light_color = winfo.palette[0].lerp(Color.WHITE, 0.35)
		spill.light_energy = 7.0 if winfo.scene_exists() else 3.5
		spill.spot_range = 22.0
		spill.spot_angle = 48.0
		spill.spot_attenuation = 0.9
		spill.light_volumetric_fog_energy = 0.0
		spill.light_projector = pm.get_shader_parameter("art")
		spill.position = Vector3(0, 6.2, -0.9)
		spill.rotation = Vector3(deg_to_rad(-28), PI, 0)
		root.add_child(spill)
		# gallery picture light: rakes the gilt from above and in front so the carving reads
		var pic := SpotLight3D.new()
		pic.light_color = Color(1.0, 0.8, 0.52)
		pic.light_energy = 6.0
		pic.spot_range = 18.0
		pic.spot_angle = 30.0
		pic.spot_attenuation = 0.6
		pic.light_volumetric_fog_energy = 0.0
		pic.light_specular = 1.6
		pic.transform = _aim(Vector3(0, 13.5, 5.5), Vector3(0, 6.5, 0))
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
		plq.position = Vector3(4.5, 1.55, 1.42)
		plq.size = Vector2(1.2, 0.83)  # readable from a couple of metres; E opens the reader
		root.add_child(plq)
		_frames[id] = {"node": root, "portal": pm, "light": spill, "spill_col": spill.light_color, "trigger": trig, "placard": plq, "info": winfo}


## The frame's square post colliders snag a player coming in at an angle and leave a pocket by the
## hall column. Each post becomes a round inner edge (the opening stays 4.6 m) and a box out to the
## column, so a glancing approach slides into the opening.
func _round_frame_posts(fm: Node3D) -> void:
	for n: String in ["post_l", "post_r"]:
		var body := fm.find_child(n, true, false) as StaticBody3D
		var s := -1.0 if n == "post_l" else 1.0
		var cs := body.get_child(0) as CollisionShape3D
		var cyl := CylinderShape3D.new()
		cyl.radius = 0.7
		cyl.height = 8.2
		cs.shape = cyl
		cs.position = Vector3(s * 3.0, 3.6, 0.0)
		var fill := CollisionShape3D.new()
		var bx := BoxShape3D.new()
		bx.size = Vector3(2.0, 8.2, 1.3)
		fill.shape = bx
		fill.position = Vector3(s * 4.0, 3.6, 0.05)
		body.add_child(fill)


func _build_door() -> void:
	var root := Node3D.new()
	root.name = "ConservationDoor"
	root.transform = _bay_xform(DOOR_BAY, APOTHEM)
	add_child(root)
	_model("door", Transform3D.IDENTITY, root)
	var key := SpotLight3D.new()  # rakes the architrave and pediment so the door reads from the hall
	key.light_color = Color(1.0, 0.82, 0.6)
	key.light_energy = 6.0
	key.spot_range = 12.0
	key.spot_angle = 28.0
	key.light_volumetric_fog_energy = 0.0
	key.transform = _aim(Vector3(0, 8.0, 4.5), Vector3(0, 3.6, 0))
	root.add_child(key)
	# a crack of work-light under the door
	var under := OmniLight3D.new()
	under.light_color = Color(1.0, 0.9, 0.75)
	under.light_energy = 0.8
	under.omni_range = 3.0
	under.light_volumetric_fog_energy = 0.0
	under.position = Vector3(0, 0.15, 0.4)
	root.add_child(under)
	var sign := Label3D.new()
	sign.text = "Conservation, staff only"
	sign.font = Style.CATALOG
	sign.font_size = 64
	sign.pixel_size = 0.0022
	sign.modulate = Style.GOLD
	sign.shaded = false
	sign.position = Vector3(0, 3.4, 0.16)
	root.add_child(sign)
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
	var depth := 8.5
	_model("wall", Transform3D(Basis(), Vector3(0, 0, -depth - 0.6)), root)
	for s: float in [-1.0, 1.0]:  # side walls: the hall's wall bay, narrowed; an unseen box collides
		_box(Vector3(0.6, 17.0, depth + 0.6), Transform3D(Basis(), Vector3(s * 6.4, 8.5, -depth * 0.5)), damask, true, root).visible = false
		var side := Basis(Vector3.UP, -s * PI * 0.5) * Basis.from_scale(Vector3((depth + 0.6) / 12.9, 1.0, 1.0))
		_model("wall", Transform3D(side, Vector3(s * 6.1, 0, 0.3 - (depth + 0.6) * 0.5)), root)
	_model("alcove", Transform3D.IDENTITY, root)
	var key := SpotLight3D.new()  # lights the proscenium and cartouche from the hall
	key.light_color = Color(1.0, 0.82, 0.6)
	key.light_energy = 8.0
	key.spot_range = 20.0
	key.spot_angle = 32.0
	key.light_volumetric_fog_energy = 0.0
	key.transform = _aim(Vector3(0, 11.0, 8.0), Vector3(0, 7.2, 0))
	root.add_child(key)
	_model("wall", Transform3D(Basis.from_scale(Vector3(1.0, 10.1 / 17.0, 1.0)), Vector3(0, 6.9, -0.4)), root)  # header
	# 18 vitrines, 3 rows of 6; row = provenance index, column = wing
	for wi in WING_ORDER.size():
		for row in 3:
			var p := Vector3(-4.5 + wi * 1.8, 0, -1.8 - row * 2.2)
			_model("plinth", Transform3D(Basis(), p), root)
			_build_vitrine(root, WING_ORDER[wi], row, p)
	var lamp := SpotLight3D.new()
	lamp.light_color = Color(1.0, 0.86, 0.66)
	lamp.light_energy = 55.0
	lamp.spot_range = 12.0
	lamp.spot_angle = 78.0
	lamp.shadow_enabled = true
	lamp.light_volumetric_fog_energy = 0.0
	lamp.position = Vector3(0, 5.9, -4.0)
	lamp.rotation.x = -PI * 0.5
	root.add_child(lamp)
	var wash := SpotLight3D.new()  # warm wash on the back damask so the recess has a back
	wash.light_color = Color(1.0, 0.72, 0.45)
	wash.light_energy = 24.0
	wash.spot_range = 14.0
	wash.spot_angle = 55.0
	wash.light_volumetric_fog_energy = 0.0
	wash.transform = _aim(Vector3(0, 5.8, -0.5), Vector3(0, 2.6, -8.5))
	root.add_child(wash)
	var coffer := OmniLight3D.new()  # (6) the coffered ceiling catches the lamp's bounce
	coffer.light_color = Color(1.0, 0.76, 0.5)
	coffer.light_energy = 3.0
	coffer.omni_range = 9.0
	coffer.light_volumetric_fog_energy = 0.0
	coffer.position = Vector3(0, 4.2, -4.0)
	root.add_child(coffer)
	for s: float in [-1.0, 1.0]:  # floor practicals between the plinth rows: the marble aisle reads
		var low := OmniLight3D.new()
		low.light_color = Color(1.0, 0.78, 0.52)
		low.light_energy = 3.2
		low.omni_range = 7.5
		low.light_volumetric_fog_energy = 0.0
		low.light_specular = 0.3
		low.position = Vector3(s * 2.7, 1.0, -3.6)
		root.add_child(low)
	var plq := Placard.new()
	plq.position = Vector3(-4.6, 1.55, 0.8)
	plq.size = Vector2(1.0, 0.69)  # the house plate, a touch smaller: the alcove is narrow
	root.add_child(plq)
	_plaques["alcove"] = plq


## One vitrine: the wing's `row`-th recovered provenance (in the order found), modelled
## (hub/models/provenance_relics.glb, `relic_<wing>_<id>`; the generic relics for unknown ids) with a
## tombstone on the plinth front. Empty vitrines carry a dim "awaiting" label.
func _build_vitrine(root: Node3D, wid: StringName, row: int, p: Vector3) -> void:
	var winfo := Game.registry.get_info(wid)
	var list: Array = (Save.data["provenances"] as Dictionary).get(String(wid), [])
	var plq := Placard.new()
	plq.size = Vector2(0.46, 0.32)
	plq.position = p + Vector3(0, 0.66, 0.3)  # clear of the plinth cornice
	plq.rotation.x = deg_to_rad(-12)
	var acq := "Acq. no. %s.%d" % [winfo.acquisition_no, row + 1]
	if row >= list.size():
		plq.readable = false
		plq.set_label(Placard.fields("Awaiting acquisition", "", winfo.title, acq, ""), false)
		root.add_child(plq)
		return
	var pid := String(list[row])
	var meta: Dictionary = ((Save.data.get("provenance_info", {}) as Dictionary).get(String(wid), {}) as Dictionary).get(pid, {})
	var title := String(meta.get("name", "Provenance, %s" % winfo.title))
	plq.set_label(Placard.fields(title, DATE[wid], "From %s" % winfo.title, acq, String(meta.get("line", ""))), false)
	root.add_child(plq)
	var tint := StandardMaterial3D.new()
	tint.albedo_color = winfo.palette[row % 3]
	tint.metallic = 0.3
	tint.roughness = 0.2
	tint.emission_enabled = true
	tint.emission = winfo.palette[row % 3]
	tint.emission_energy_multiplier = 0.6
	var xf := Transform3D(Basis(Vector3.UP, 0.3 - 0.3 * row), p + Vector3(0, 1.05, 0))
	var want := "relic_%s_%s" % [wid, pid]
	var relic := _model("provenance_relics", xf, root)
	if relic.find_child(want, false, false) == null:
		relic.free()
		relic = _model("relics", xf, root)
		want = "relic_%d" % row
	for c: Node in relic.get_children():
		if c.name != want:
			c.free()
	relic.name = "Relic_%s_%d" % [wid, row]
	for mi: MeshInstance3D in relic.find_children("*", "MeshInstance3D", true, false):
		for si in mi.mesh.get_surface_count():
			var sm := mi.mesh.surface_get_material(si)
			if sm and sm.resource_name == "relic_tint":
				mi.set_surface_override_material(si, tint)
	_relics.append({"wing": wid, "title": title, "node": relic})
	var pin := SpotLight3D.new()  # each relic gets its own pin light from the vitrine lid
	pin.light_color = Color(1.0, 0.9, 0.74)
	pin.light_energy = 3.0
	pin.spot_range = 1.2
	pin.spot_angle = 30.0
	pin.light_volumetric_fog_energy = 0.0
	pin.position = p + Vector3(0, 1.52, 0.12)
	pin.rotation.x = -PI * 0.5
	root.add_child(pin)


## THE THIEF, ACQUIRED: a pedestal waiting for you. One stage per fragment returned.
func _build_thief() -> void:
	_thief = Node3D.new()
	_thief.name = "Thief"
	_thief.transform = _bay_xform(THIEF_BAY, 14.5)
	add_child(_thief)
	var n := Quest.fragment_count()
	_thief_stage = n
	_model("pedestal", Transform3D.IDENTITY, _thief)
	# the thief herself, in plaster, caught mid-reach on the pedestal top (faces the sphere)
	var fig := _model("thief", Transform3D(Basis(), Vector3(0, 0.42, 0)), _thief)
	var arm: Node3D = fig.find_child("thief_arm", true, false)
	_thief_fig = {"body": fig.find_child("thief", true, false), "head": fig.find_child("thief_head", true, false),
		"arm": arm, "arm_rest": arm.rotation if arm else Vector3.ZERO}
	var plate := Label3D.new()
	plate.font = Style.CATALOG
	plate.font_size = 48
	plate.modulate = Style.GOLD
	plate.text = "Reserved" if n < 3 else "The thief, acquired"
	plate.pixel_size = 0.0011
	plate.position = Vector3(0, 0.28, 1.0)
	_thief.add_child(plate)
	# a cold white pin-spot that has always been waiting: the one light in the hall that is not gold
	var cold := SpotLight3D.new()
	cold.light_color = Color(0.82, 0.9, 1.0)
	cold.light_energy = 10.0 if n < 4 else 4.0
	cold.spot_range = 22.0
	cold.spot_angle = 8.0
	cold.spot_attenuation = 0.5
	cold.light_volumetric_fog_energy = 6.0
	cold.transform = _aim(Vector3(0.0, 19.0, 1.5), Vector3(0, 0, 0))
	_thief.add_child(cold)
	var inside := OmniLight3D.new()
	inside.light_color = Color(0.8, 0.9, 1.0)
	inside.light_energy = 0.9
	inside.omni_range = 2.4
	inside.light_volumetric_fog_energy = 0.0
	inside.position = Vector3(0, 2.5, 0)
	_thief.add_child(inside)
	if n >= 1:  # stage 1: a sketch of the hands, pinned up
		var easel := _model("easel", Transform3D(Basis(), Vector3(0, 1.12, 1.2)), _thief)
		var card: MeshInstance3D = easel.find_child("card", true, false)
		if card:  # the sketch is drawn on the easel's own card
			var sketch := StandardMaterial3D.new()
			sketch.albedo_texture = load("res://assets/ui/vesper_sketch.png" if n >= 6 else "res://assets/ui/hands_sketch.png")
			sketch.roughness = 0.9
			card.material_override = sketch
	if n >= 2:  # stage 2: the velvet rope
		for k in 4:
			var a := float(k) * TAU / 4.0 + PI / 4.0
			var p := Vector3(sin(a), 0, cos(a)) * 2.25
			var st := _model("stanchion", Transform3D(Basis(Vector3.UP, a + PI * 0.5), p), _thief)
			st.scale = Vector3(1.59, 1, 1)
	if n >= 3:  # stage 3: a printed placard
		var plq := Placard.new()
		plq.position = Vector3(2.5, 1.2, 1.9)
		plq.rotation.x = deg_to_rad(-20)
		plq.size = Vector2(0.8, 0.56)
		plq.set_label(Placard.fields("The thief, acquired", "Acquired this week", "Flesh, grief, intent", "Acq. no. 007",
			"Acquired in the act. Displayed in the round. The subject appears to be looking for something it lost; the Curator has declined to say what. Please do not feed the exhibit."), false)
		_thief.add_child(plq)
	if n >= 4:  # stage 4: gallery lighting
		var spot := SpotLight3D.new()
		spot.light_color = Color(1.0, 0.92, 0.8)
		spot.light_energy = 24.0
		spot.spot_range = 18.0
		spot.spot_angle = 13.0
		spot.shadow_enabled = true
		spot.light_volumetric_fog_energy = 3.0
		spot.position = Vector3(0, 14, 0)
		spot.rotation.x = -PI * 0.5
		_thief.add_child(spot)


## Docent-constructs: faceless plaster figures with sketchboards. They turn to watch you. One is
## here from the start; another arrives with each fragment (max 5).
func _build_docents() -> void:
	var spots: Array[Transform3D] = [
		_bay_xform(9, 16.0).translated_local(Vector3(3.2, 0, 0)),  # off the chitin frame's axis
		Transform3D(Basis(Vector3.UP, deg_to_rad(60) + PI * 1.9), _bay_xform(THIEF_BAY, 11.0).origin + Vector3(-2.5, 0, 1.0)),
		_bay_xform(7, 15.5).translated_local(Vector3(-3.2, 0, 0)),  # off the aria frame's axis
		Transform3D(Basis(Vector3.UP, deg_to_rad(60) + PI * 0.1), _bay_xform(THIEF_BAY, 12.0).origin + Vector3(3.0, 0, -3.2)),
		_bay_xform(10, 13.0),
	]
	var count := clampi(1 + Quest.fragment_count(), 1, spots.size())
	for i in count:
		var xf: Transform3D = spots[i]
		var d := _model("docent", xf)
		var head: Node3D = d.find_child("head", true, false)
		var key := SpotLight3D.new()  # a soft key from above and in front: the dark robe reads as a figure
		key.light_color = Color(1.0, 0.86, 0.68)
		key.light_energy = 9.0
		key.spot_range = 9.0
		key.spot_angle = 40.0  # wide enough to pool on the floor round the docent
		key.light_volumetric_fog_energy = 0.0
		key.light_specular = 0.4
		key.transform = _aim(Vector3(0.6, 4.6, 2.4), Vector3(0, 1.5, 0))
		d.add_child(key)
		_docents.append({"root": d, "head": head, "next": 4.0 + randf() * 6.0, "phase": float(i) * 1.7,
			"arms": [d.find_child("arm_L", true, false), d.find_child("arm_R", true, false)],
			"pencil": d.find_child("pencil", true, false)})


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
	# volumetric shafts falling through the oculus; dust drifts only inside them
	var shafts := [[Vector3(-2, 48, 3), Vector3(-6, 0, 7), 9.0], [Vector3(2.5, 48, -2.5), Vector3(9, 0, -4), 7.0], [Vector3(-1.5, 48, -2), Vector3(-10, 0, -9), 6.0]]
	var dust := _dust_mesh()
	for sh: Array in shafts:
		var top: Vector3 = sh[0]
		var bot: Vector3 = sh[1]
		var lo := bot.lerp(top, 0.03)
		var hi := bot.lerp(top, 0.4)
		_dust_column(dust, lo, hi, 1.6 if sh == shafts[0] else 1.1, 70 if sh == shafts[0] else 40)
	_dust_column(dust, Vector3(0, 0.5, 0), Vector3(0, 3.5, 0), 4.0, 30)  # around Exhibit 0's light
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
	# LIGHTING RECIPE (the hall's light-dark arc, read from the entrance):
	#   1 entrance + foreground floor: a dim warm pool, enough to read the marble inlay (gallery key)
	#   2 the hall falls darker between pools; columns rim-lit from their feet
	#   3 the centre: Exhibit 0 is the brightest thing, its omni pooling on the dais and floor
	#   4 the frames: each a coloured window spilling its world onto the floor
	#   5 the dome: a warm cove wash from the cornice up into the coffers, peaking at the oculus shaft
	#   6 the Private Collection: a warm, close, lamp-lit room at the end of the arc
	#   7 the thief: the one cold light
	# low warm fill so the hall reads as a room, not a void
	var fill := OmniLight3D.new()
	fill.light_color = Color(1.0, 0.78, 0.5)
	fill.light_energy = 1.4
	fill.omni_range = 40.0
	fill.omni_attenuation = 1.6
	fill.light_volumetric_fog_energy = 0.0
	fill.position = Vector3(0, 3.0, 0)
	add_child(fill)
	# upper glow: the gallery and the dome ribs catch a warm haze from below
	var high := OmniLight3D.new()
	high.light_color = Color(1.0, 0.7, 0.42)
	high.light_energy = 1.4
	high.omni_range = 34.0
	high.omni_attenuation = 1.2
	high.light_volumetric_fog_energy = 0.0
	high.light_specular = 0.4
	high.position = Vector3(0, 21.0, 0)
	add_child(high)
	# uplights at the column feet: flutes and capitals rim-lit, receding into the haze
	var r := APOTHEM / cos(PI / 12.0) - 0.9
	for i in 12:
		var a := (float(i) + 0.5) * TAU / 12.0
		var dir := Vector3(sin(a), 0, cos(a))
		var up := SpotLight3D.new()
		up.light_color = Color(1.0, 0.76, 0.48)
		up.light_energy = 7.0
		up.spot_range = 19.0
		up.spot_angle = 11.0
		up.spot_attenuation = 0.8
		up.light_volumetric_fog_energy = 0.0
		up.light_specular = 0.8
		up.transform = _aim(dir * (r - 2.4) + Vector3(0, 0.2, 0), dir * (r - 0.6) + Vector3(0, 16.0, 0))
		add_child(up)
	# (5) cove wash: six spots on the cornice, aimed across and up into the far side of the dome
	for i in 6:
		var a := (float(i) + 0.25) * TAU / 6.0
		var cove := SpotLight3D.new()
		cove.light_color = Color(1.0, 0.74, 0.46)
		cove.light_energy = 70.0
		cove.spot_range = 50.0
		cove.spot_angle = 40.0
		cove.spot_attenuation = 0.7
		cove.light_volumetric_fog_energy = 0.0
		cove.light_specular = 0.3
		cove.transform = _aim(Vector3(sin(a), 0, cos(a)) * (APOTHEM - 2.0) + Vector3(0, 18.5, 0),
			Vector3(-sin(a), 0, -cos(a)) * 6.0 + Vector3(0, 36.0, 0))
		add_child(cove)
	# (2) wall washers: one wide spot per bay under the gallery soffit, grazing the damask from above so
	# the green pattern reads between the columns (dimmer than any pool); a low fill under the gallery
	# lifts the dado and the floor margin it reflects in
	for i in 12:
		if i == ALCOVE_BAY:
			continue
		var a := float(i) * TAU / 12.0
		var dir := Vector3(sin(a), 0, cos(a))
		var wash := SpotLight3D.new()
		wash.light_color = Color(1.0, 0.8, 0.58)
		wash.light_energy = 16.0
		wash.spot_range = 16.0
		wash.spot_angle = 58.0
		wash.spot_attenuation = 0.5
		wash.light_volumetric_fog_energy = 0.0
		wash.light_specular = 0.15
		wash.transform = _aim(dir * (APOTHEM - 2.2) + Vector3(0, 11.5, 0), dir * (APOTHEM + 0.4) + Vector3(0, 3.0, 0))
		add_child(wash)
		var under := OmniLight3D.new()
		under.light_color = Color(1.0, 0.76, 0.52)
		under.light_energy = 2.4
		under.omni_range = 9.0
		under.omni_attenuation = 1.2
		under.light_volumetric_fog_energy = 0.0
		under.light_specular = 0.25
		under.position = dir * (APOTHEM - 4.0) + Vector3(0, 2.2, 0)
		add_child(under)
	# (1) foreground key: from the gallery over the entrance, a soft pool on the near floor
	var near := SpotLight3D.new()
	near.light_color = Color(1.0, 0.8, 0.56)
	near.light_energy = 12.0
	near.spot_range = 34.0
	near.spot_angle = 30.0
	near.spot_attenuation = 1.2
	near.light_volumetric_fog_energy = 0.4
	near.transform = _aim(Vector3(0, 21.0, 3.0), Vector3(0, 0, 13.0))
	add_child(near)
	# ponytail: no ReflectionProbe (cost ~1.5 ms at 1440p); SSR carries the floor reflections


## Re-capture the reflection probe (after the intro wakes the frames, so the floor mirrors them).
func _recapture() -> void:
	if _probe:
		_probe.update_mode = ReflectionProbe.UPDATE_ALWAYS
		await get_tree().process_frame
		await get_tree().process_frame
		if _probe:
			_probe.update_mode = ReflectionProbe.UPDATE_ONCE


func _dust_mesh() -> QuadMesh:
	var qm := QuadMesh.new()
	qm.size = Vector2(0.05, 0.05)
	var mm := StandardMaterial3D.new()
	mm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mm.vertex_color_use_as_albedo = true
	mm.albedo_color = Color(1.0, 0.82, 0.55)
	mm.albedo_texture = _dot_texture()
	mm.roughness = 1.0
	mm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	mm.disable_ambient_light = true
	mm.emission_enabled = true
	mm.emission = Color(1.0, 0.75, 0.4)
	mm.emission_energy_multiplier = 0.15
	qm.material = mm
	return qm


## A few dozen motes drifting along a light column from `lo` to `hi`: lit (not glowing), so they
## only sparkle where the shaft actually is, with sizes spread for depth.
func _dust_column(mesh: QuadMesh, lo: Vector3, hi: Vector3, radius: float, amount: int) -> void:
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = 18.0
	p.preprocess = 18.0
	p.local_coords = false
	var axis := (hi - lo)
	p.transform = Transform3D(Basis(Quaternion(Vector3.UP, axis.normalized())), (lo + hi) * 0.5)
	p.visibility_aabb = AABB(Vector3(-radius - 2, -axis.length() * 0.5 - 2, -radius - 2), Vector3(radius * 2 + 4, axis.length() + 4, radius * 2 + 4))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_RING
	pm.emission_ring_axis = Vector3(0, 1, 0)
	pm.emission_ring_height = axis.length()
	pm.emission_ring_radius = radius
	pm.emission_ring_inner_radius = 0.0
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 180.0
	pm.initial_velocity_min = 0.01
	pm.initial_velocity_max = 0.06
	pm.gravity = Vector3(0, -0.004, 0)
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.25
	pm.turbulence_noise_scale = 4.0
	pm.turbulence_noise_speed_random = 0.2
	pm.scale_min = 0.35
	pm.scale_max = 2.2
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 0))
	fade.add_point(0.25, Color(1, 1, 1, 1))
	fade.add_point(0.75, Color(1, 1, 1, 1))
	fade.set_color(fade.get_point_count() - 1, Color(1, 1, 1, 0))
	var gt := GradientTexture1D.new()
	gt.gradient = fade
	pm.color_ramp = gt
	p.process_material = pm
	p.draw_pass_1 = mesh
	add_child(p)


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
	entrance.size = Vector2(1.2, 0.83)
	add_child(entrance)
	_plaques["entrance"] = entrance
	var dais := Placard.new()
	dais.transform = Transform3D(Basis(Vector3.UP, 0.0), Vector3(0, 0.95, 8.1))
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
		var winfo: WingInfo = f["info"]
		var medium: String = MEDIUM[id]
		var body: String = BODY[id]
		if Quest.has_fragment(id):
			body = "You went in and came back with a piece of yourself. This label has been amended in your hand. The Curator has not yet noticed the handwriting."
		elif not winfo.scene_exists():
			medium = "Gallery closed for restoration"
		# tombstone order: title / date / medium / acquisition no. / one short paragraph
		(f["placard"] as Placard).set_label(Placard.fields(winfo.title, DATE[id], medium, "Acq. no. %s" % winfo.acquisition_no, body), anim)
	var e: String = ["Closed for the duration of your stay.",
		"Closed for the duration of your stay. Your stay has been extended.",
		"Closed for the duration of your stay. You have stopped trying it. Thank you.",
		"You could leave now. The door has noticed."][0 if n == 0 else (1 if n < 3 else (2 if n < 6 else 3))]
	(_plaques["entrance"] as Placard).set_label(Placard.fields("Entrance", "Date of your arrival", "Oak, brass, a lock. Way out, not in use.", "", e), anim)
	var d: String = ["A world, damaged in transit. Six pieces are missing. They are on display elsewhere in the building, which is the same thing as being safe.",
		"A world, damaged in transit. Someone is repairing it without permission. The Curator is aware.",
		"A world, damaged in transit. You are repairing it without permission. Please continue; it is the most interesting thing in the building.",
		"Complete. You did this. The Curator would like a word, and has prepared two."][0 if n == 0 else (1 if n < 3 else (2 if n < 6 else 3))]
	(_plaques["dais"] as Placard).set_label(Placard.fields("Exhibit 0", "Acquired the night you were taken", "Everything you had", "Acq. no. 000", d), anim)
	var provs := 0
	for k: String in Save.data["provenances"]:
		provs += (Save.data["provenances"][k] as Array).size()
	var a := "Not on public view. You are not the public." if provs == 0 else \
		"Items recovered by you, held by us. %d of 18. The arrangement is temporary on one side." % provs
	(_plaques["alcove"] as Placard).set_label(Placard.fields("The private collection", "Ongoing", "Things you brought back. By appointment.", "", a), anim)


## Camera marks for tests/shots.tscn (`-- --wing=atrium`): every surface the player judges the hall by.
func _build_shot_marks() -> void:
	var marks := Node3D.new()
	marks.name = "ShotMarks"
	add_child(marks)
	var add := func(n: String, at: Vector3, look: Vector3) -> void:
		var m := Marker3D.new()
		m.name = n
		m.transform = _aim(at, look)
		marks.add_child(m)
	add.call("01_entrance", Vector3(0.0, 1.7, 19.0), Vector3(0.0, 5.0, 0.0))
	add.call("02_sphere", Vector3(3.4, 4.0, 5.6), Vector3(0.0, 6.2, 0.0))
	add.call("03_sphere_low", Vector3(-2.2, 1.6, 6.8), Vector3(0.0, 6.0, 0.0))
	add.call("04_dome", Vector3(2.0, 1.7, 12.0), Vector3(0.0, 34.0, -6.0))
	add.call("05_floor", Vector3(6.0, 0.9, 16.5), Vector3(-4.0, 2.0, 0.0))
	for i in WING_ORDER.size():
		var a := float(FRAME_BAYS[i]) * TAU / 12.0
		var f := Vector3(sin(a), 0, cos(a)) * (APOTHEM - 0.5) + Vector3(0, 3.6, 0)
		var at := Vector3(sin(a + 0.22), 0, cos(a + 0.22)) * 14.0 + Vector3(0, 1.7, 0)
		add.call("1%d_frame_%s" % [i, WING_ORDER[i]], at, f)
	add.call("20_alcove", Vector3(1.5, 1.7, -16.5), Vector3(0.0, 1.4, -28.0))
	add.call("21_relics", Vector3(1.6, 1.6, -23.6), Vector3(-0.6, 1.15, -27.0))
	var ta := float(THIEF_BAY) * TAU / 12.0
	add.call("30_thief", Vector3(sin(ta + 0.2), 0, cos(ta + 0.2)) * 10.0 + Vector3(0, 1.7, 0), Vector3(sin(ta), 0, cos(ta)) * 14.5 + Vector3(0, 1.5, 0))
	add.call("31_docent", Vector3(-12.5, 1.6, 2.0), Vector3(-16.0, 1.8, 0.0))


# --- per frame --------------------------------------------------------------------------------

func _process(delta: float) -> void:
	_t += delta * Game.world_time_scale
	var dt := delta * Game.world_time_scale
	if _sphere:
		_sphere.rotate_y(dt * 0.05)
		_skin.set_shader_parameter("centre", _sphere.global_position)
		_sphere.position.y = SPHERE_Y + sin(_t * 0.4) * 0.08
		for s: Dictionary in _shards:
			if s.get("fly", false):
				continue
			var mi: MeshInstance3D = s["node"]
			mi.position = (s["dir"] as Vector3) * (_shard_gap + sin(_t * 0.6 + float(s["phase"])) * _shard_gap * 0.25)
		var spread := 1.0 + _shard_gap * 2.0
		for c: Dictionary in _chips:
			var a := float(c["a"]) + _t * float(c["speed"])
			var r := float(c["r"]) * spread
			var mi: MeshInstance3D = c["node"]
			mi.position = Vector3(cos(a) * r, float(c["y"]) + sin(_t * 0.3 + a) * 0.25, sin(a) * r)
			mi.rotate(c["spin"], dt * 0.4)
	for i in _rings.size():
		var r := _rings[i]
		r.rotate(Vector3(0.3 * i, 1.0, 0.2 * (2 - i)).normalized(), dt * (0.03 + 0.02 * i) * (-1.0 if i == 1 else 1.0))
	for id: StringName in _frames:  # each window's spill breathes in its own medium's rhythm
		var f: Dictionary = _frames[id]
		var k := 1.0
		match int((f["info"] as WingInfo).portal_medium):
			0: k = 0.85 + 0.25 * pow(0.5 + 0.5 * sin(_t * 0.19), 6.0)  # glass: a beam sweeps by
			1: k = 0.93 + 0.035 * float(int(_t * 12.0) % 3)          # clay: 12 fps boil
			2: k = 0.55 if fmod(_t * 9.0, 23.0) < 1.0 else 0.9       # noir: the lamp stutters
			3: k = 0.8 + 0.2 * sin(_t * 1.3) * sin(_t * 0.7 + 1.0)    # aria: caustic swell
			4: k = 0.8 + 0.25 * (0.5 + 0.5 * sin(_t * 0.9))          # chitin: the hive pulses
			5: k = 0.9 + 0.1 * sin(_t * 0.31)                        # paint: slow wet sheen
		(f["light"] as SpotLight3D).light_color = (f["spill_col"] as Color) * k
	var p := Game.player
	if p:
		for d: Dictionary in _docents:
			var head: Node3D = d["head"]
			var root: Node3D = d["root"]
			if head == null:
				continue
			var local := root.to_local(p.global_position)
			var want := clampf(atan2(local.x, local.z), -1.3, 1.3) if local.length() < 18.0 else 0.0  # models face +Z
			head.rotation.y = lerp_angle(head.rotation.y, want, 1.0 - exp(-2.5 * delta))
			d["next"] = float(d["next"]) - delta
			if float(d["next"]) <= 0.0:
				d["next"] = 6.0 + randf() * 8.0
				if local.length() < 12.0:
					Audio.sfx(Audio.stream("sketch"), root.global_position + Vector3(0, 1.2, 0), -10.0, 0.4, randf_range(0.9, 1.1))
			var ph: float = d["phase"]
			for arm: Node3D in d["arms"]:  # breathing: a slow lift of the shoulders
				if arm:
					arm.rotation.x = 0.03 * sin(_t * 1.1 + ph)
			var pencil: Node3D = d["pencil"]
			if pencil:  # sketching: small quick strokes while you are near, still otherwise
				var near := 1.0 if local.length() < 12.0 else 0.0
				pencil.rotation.z = near * 0.12 * sin(_t * 7.0) * maxf(0.0, sin(_t * 0.9 + ph))
		_animate_thief(p, delta)
	_distant_t -= delta
	if _distant_t <= 0.0:
		_distant_t = randf_range(45.0, 90.0)
		var a := randf() * TAU
		var far: AudioStream = [Audio.stream("distant_movement"), _cc("distant_stone_drag"), _cc("distant_stone_door")].pick_random()
		Audio.sfx(far, Vector3(sin(a) * 40.0, 30.0, cos(a) * 40.0), -8.0, 1.0, randf_range(0.7, 0.85))
	var touch: Interactable = _sphere.get_node_or_null("SphereTouch") if _sphere else null
	if touch:
		touch.enabled = finale_available() and not _finale_running


## The thief idles: breath in the chest, the reaching arm drifting, the head following you once
## you are close enough to be the thing she lost.
func _animate_thief(p: Node3D, delta: float) -> void:
	var head: Node3D = _thief_fig.get("head")
	var arm: Node3D = _thief_fig.get("arm")
	var body: Node3D = _thief_fig.get("body")
	if body:
		body.position.y = 0.006 * sin(_t * 1.25)
	if arm:
		var rest: Vector3 = _thief_fig["arm_rest"]
		arm.rotation = rest + Vector3(0.05 * sin(_t * 0.43), 0.0, 0.03 * sin(_t * 0.31 + 1.0))
	if head:
		var local := head.get_parent_node_3d().to_local(p.global_position + Vector3(0, 1.5, 0)) - head.position
		var near := local.length() < 9.0
		var yaw := clampf(atan2(local.x, local.z), -1.0, 1.0) if near else 0.25 * sin(_t * 0.17)
		var pitch := clampf(atan2(-local.y, Vector2(local.x, local.z).length()), -0.4, 0.4) if near else 0.0
		var k := 1.0 - exp(-1.6 * delta)
		head.rotation.y = lerp_angle(head.rotation.y, yaw, k)
		head.rotation.x = lerp_angle(head.rotation.x, pitch, k)


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
		{"card": "%d of 6" % Quest.fragment_count(), "sub": "Exhibit 0, restored without permission", "t": 3.2, "style": "display"},
		{"call": _mark_placed.bind(pending), "always": true},
	])


func _stinger_quiet() -> void:
	Audio.reveal(_cc("sting_cellos"), 2.0)


## CC0 recordings fetched with tools/fetch_cc.sh (see CREDITS.md).
func _cc(name: String) -> AudioStream:
	return load("res://assets/audio/cc/%s.ogg" % name)


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
	Audio.set_intensity(Quest.fragment_count() / 6.0, 6.0)  # one more band of the theme, on the bar
	for id in pending:  # the returned weather pours in over a few seconds
		_weather[id] = 1.0
		_tween_param(create_tween(), _skin, "w_" + String(id), 1.0, 4.0).set_trans(Tween.TRANS_SINE)
	create_tween().tween_property(_sphere_light, "light_color", _sphere_tint(), 4.0)


## The sphere's light: warm gold, taking on a little of each returned world's key colour.
func _sphere_tint() -> Color:
	var c := Color(1.0, 0.72, 0.38)
	var acc := Color(0, 0, 0)
	var n := 0
	for id in WING_ORDER:
		if _is_placed(id):
			acc += Game.registry.get_info(id).palette[0]
			n += 1
	return c if n == 0 else c.lerp(acc / float(n), 0.08 * n).lerp(Color.WHITE, 0.15)


# --- intro --------------------------------------------------------------------------------

## Premise cards, then the reveal recipe: dark compressed approach with the view occluded by a
## column, release into the hall with a human-scale object (the bench) in frame, near-silence,
## stinger, camera freed.
func _intro() -> void:
	# DESIGN_RULES §4. Conclusion: the broken world is the heart of an enormous house.
	# Compress (a low, narrow look along the brass meridian, the sphere out of frame) -> occlude
	# (black) -> release at eye level, the bench and placard for scale -> near-silence, then the sting.
	var c0 := Transform3D(Basis.looking_at(Vector3(0.0, -0.2, -1.0).normalized(), Vector3.UP), Vector3(0.35, 0.45, 21.5))
	var c1 := Transform3D(Basis.looking_at(Vector3(0.05, -0.16, -1.0).normalized(), Vector3.UP), Vector3(0.2, 0.55, 18.6))
	var c2p := Vector3(-0.6, 1.65, 16.2)
	var c2 := Transform3D(Basis.looking_at(Vector3(0, SPHERE_Y - 0.6, 0) - c2p, Vector3.UP), c2p)
	var c3p := Vector3(1.4, 1.7, 13.4)
	var c3 := Transform3D(Basis.looking_at(Vector3(0, SPHERE_Y - 0.2, 0) - c3p, Vector3.UP), c3p)
	Game.player.teleport(find_checkpoint(&"start").global_transform)  # stand her where the camera lands
	await get_tree().physics_frame
	var eye := Game.player.camera.global_transform
	await Cinematics.play([
		{"fade": 1.0, "t": 0.0},
		{"call": _intro_dark},
		{"card": "The Curator collects worlds.", "sub": "A museum of stolen realities", "t": 6.0},
		{"card": "Not paintings of worlds. The worlds themselves, cut from their skies and hung at eye level.", "t": 7.5, "style": "body"},
		{"card": "Six were acquired this century. Each one was someone's home.", "t": 6.5, "style": "body"},
		{"card": "The seventh was yours. It arrived broken. It is catalogued as Exhibit 0.", "t": 7.0, "style": "body"},
		{"card": "You came to take it back.", "t": 5.0},
		{"card": "You were caught in the act. You have been catalogued too.", "t": 6.0, "style": "body"},
		{"cam": [c0, c1], "t": 9.0, "fov": 38.0, "async": true},
		{"fade": 0.0, "t": 3.0},
		{"wait": 3.5},
		{"fade": 1.0, "t": 1.5},
		{"wait": 1.5},
		{"call": _intro_release},
		{"cam": [c2, c3], "t": 11.0, "fov": 64.0, "async": true},
		{"fade": 0.0, "t": 2.5},
		{"wait": 7.5},
		{"card": "The thief, acquired.", "sub": "Exhibit pending", "t": 5.0, "style": "display"},
		# handover: glide from the last shot into Vesper's own eye, field of view easing to hers
		{"cam": [c3, c3.interpolate_with(eye, 0.45), eye], "t": 4.0, "fov": 64.0, "fov_to": Game.player.base_fov},
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
	Audio.reveal(_cc("sting_swell"), 4.0)  # not awaited: 4 s of near-silence, then the sting
	_awaken(1.0, 4.0)


func _intro_done() -> void:
	_awaken(1.0, 0.0)
	_recapture()
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
	box.add_child(Style.catalog("Exhibit 0, complete", 18, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
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
	(box.get_child(2) as Button).grab_focus()  # keyboard and pad choose too
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
	return Credits.cards()



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


## The loose splinters share the vessel's glass but sit outside it: no interior to march.
var _chip_mat: ShaderMaterial
func _chip_skin(skin: ShaderMaterial) -> ShaderMaterial:
	if _chip_mat == null:
		_chip_mat = skin.duplicate() as ShaderMaterial
		_chip_mat.set_shader_parameter("volume", 0.0)
	return _chip_mat


## Tween a shader uniform via set_shader_parameter (property paths fail when the renderer has
## not reflected the uniforms, e.g. headless).
func _tween_param(tw: Tween, mat: ShaderMaterial, param: String, to: float, t: float) -> MethodTweener:
	var from: Variant = mat.get_shader_parameter(param)
	if from == null:
		from = 1.0
	return tw.tween_method(func(v: float) -> void: mat.set_shader_parameter(param, v), float(from), to, t)

