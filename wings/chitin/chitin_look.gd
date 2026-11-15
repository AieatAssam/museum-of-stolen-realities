extends Node3D
## The Chitin Court's look: materials on the gameplay boxes (which stay the colliders, untouched),
## modelled dressing generated from those same boxes (lips on every walkable edge, carapace ribs on
## walls, vault ribs over the streets), scattered practicals (fungus, comb, cocoons, lamps), the
## lighting recipe and per-area exposure, and the player's own swing line.
## Visual only: adds no collision and moves no gameplay node.

const MODELS := "res://wings/chitin/models/"
const MATS := "res://wings/chitin/materials"

## Per area: wall material, ribs on walls, prop density, practical colour, exposure.
## The light arc: warm honey at the gate and districts, cold and dark down the shaft, hot foundry,
## hushed gallery, a black arena under rim light, then the amber blaze of the hall.
const AREAS := {
	"OuterGate": {"wall": "carapace", "fungus": 6, "comb": 4, "lamp": Color(1.0, 0.72, 0.38), "exp": 2.4},
	"SilkDistricts": {"wall": "comb", "fungus": 14, "comb": 0, "lamp": Color(1.0, 0.7, 0.35), "exp": 1.35},
	"HiveShaft": {"wall": "carapace", "fungus": 4, "comb": 10, "lamp": Color(0.55, 1.0, 0.85), "exp": 3.3},
	"Foundry": {"wall": "comb_dim", "fungus": 14, "comb": 8, "lamp": Color(1.0, 0.55, 0.22), "exp": 1.9},
	"TapestryGallery": {"wall": "comb_dim", "fungus": 8, "comb": 0, "lamp": Color(0.6, 1.0, 0.88), "exp": 2.3},
	"GeneralArena": {"wall": "comb_dim", "fungus": 18, "comb": 0, "lamp": Color(1.0, 0.7, 0.35), "exp": 2.8},
	"CoronationHall": {"wall": "carapace", "fungus": 12, "comb": 6, "lamp": Color(1.0, 0.65, 0.3), "exp": 3.0},
	"Heist": {"wall": "carapace", "fungus": 4, "comb": 0, "lamp": Color(1.0, 0.65, 0.3), "exp": 1.8},
}

var wing: Node3D
var env: Environment
var sun: DirectionalLight3D
var _rng := RandomNumberGenerator.new()
var _xf := {}                      # model name -> Array[Transform3D]
var _lights := 0
var _rope: Array[MeshInstance3D] = []
var _rope_mat: Material
var _exp := -1.0


func dress(w: Node3D, environment: Environment, key: DirectionalLight3D) -> void:
	wing = w
	env = environment
	sun = key
	_rng.seed = 340
	name = "Look"
	_rope_mat = load("res://wings/chitin/materials/silk_line.tres")
	var areas := w.get_node("Areas")
	for area: Node in areas.get_children():
		_dress_area(area as Node3D, AREAS.get(String(area.name), AREAS["OuterGate"]))
	for m: String in _xf:
		_mm(m, _xf[m])
	_xf.clear()


# --- generic dressing from the gameplay boxes ----------------------------------------------------

func _dress_area(area: Node3D, cfg: Dictionary) -> void:
	var walls: Array[AABB] = []
	var floors: Array[AABB] = []
	for body: Node in area.find_children("*", "StaticBody3D", true, false):
		if body.get_script() != null:
			continue  # strands
		var mi := body.get_child(0) as MeshInstance3D if body.get_child_count() > 0 else null
		if mi == null or not (mi.mesh is BoxMesh) or not mi.visible:
			continue
		var size: Vector3 = (mi.mesh as BoxMesh).size
		var box := AABB((body as Node3D).global_position - size * 0.5, size)
		var col: Color = (mi.material_override as StandardMaterial3D).albedo_color if mi.material_override is StandardMaterial3D else Color.BLACK
		if col.is_equal_approx(Color("6b7f8a")):
			mi.material_override = _mat("floor")
			if size.x > 0.5:  # stair treads keep their own trim
				floors.append(box)
		elif col.is_equal_approx(Color("39424a")):
			var thin := minf(size.x, size.z) < 1.2 and size.y < 1.0  # stair ceilings
			mi.material_override = _mat("carapace_dull" if thin else cfg["wall"])
			if not thin:
				walls.append(box)
	for f: AABB in floors:
		_lips(f)
		_scatter_floor(f, cfg)
	for wb: AABB in walls:
		_ribs(wb, cfg)


## A modelled lip along every edge of a walkable top, so no ledge reads as a box.
func _lips(b: AABB) -> void:
	var top := b.end.y
	var mid := b.get_center()
	for e: Array in [[Vector3(mid.x, top, b.position.z), b.size.x, PI], [Vector3(mid.x, top, b.end.z), b.size.x, 0.0],
			[Vector3(b.position.x, top, mid.z), b.size.z, -PI / 2.0], [Vector3(b.end.x, top, mid.z), b.size.z, PI / 2.0]]:
		var length: float = e[1]
		if length < 1.5:
			continue
		# lip.glb overhangs toward its front (+Z in Godot): face outward from the ledge
		var basis := Basis(Vector3.UP, e[2]) * Basis.from_scale(Vector3(length, 1.0, 1.0))
		_add("lip", Transform3D(basis, e[0]))


## Carapace ribs up both broad faces of a wall every ~4 m, with comb and fungus between some.
func _ribs(b: AABB, cfg: Dictionary) -> void:
	var h := b.size.y
	if h < 2.5:
		return
	var along_x := b.size.x >= b.size.z
	var length := b.size.x if along_x else b.size.z
	if length < 3.0:
		return
	var n := int(length / 4.0)
	for side: float in [-1.0, 1.0]:
		for i: int in n + 1:
			var u := (float(i) / maxf(n, 1)) * (length - 1.0) + 0.5
			var p: Vector3
			var yaw: float
			if along_x:
				p = Vector3(b.position.x + u, b.position.y, b.position.z if side < 0 else b.end.z)
				yaw = 0.0 if side > 0 else PI
			else:
				p = Vector3(b.position.x if side < 0 else b.end.x, b.position.y, b.position.z + u)
				yaw = PI / 2.0 if side > 0 else -PI / 2.0
			var basis := Basis(Vector3.UP, yaw)
			_add("rib", Transform3D(basis * Basis.from_scale(Vector3(1.0, h, 1.0)), p))
			if i < n and h > 4.0:
				var mid_u := u + length / maxf(n, 1) * 0.5
				var q := p + (Vector3(mid_u - u, 0, 0) if along_x else Vector3(0, 0, mid_u - u))
				var roll := _rng.randf()
				var y := q.y + clampf(_rng.randf_range(1.5, h - 2.0), 1.0, 6.0)
				if roll < float(cfg["comb"]) / 40.0:
					_add("comb", Transform3D(basis.rotated(Vector3.UP, 0.0) * Basis.from_scale(Vector3.ONE * _rng.randf_range(0.8, 1.4)), Vector3(q.x, y, q.z)))
				elif roll < 0.45:
					_add("fungus_shelf", Transform3D(basis * Basis.from_scale(Vector3.ONE * _rng.randf_range(0.7, 1.3)), Vector3(q.x, q.y + _rng.randf_range(0.8, 3.0), q.z)))


## Fungus clusters along a floor's edges; some carry a practical light.
func _scatter_floor(b: AABB, cfg: Dictionary) -> void:
	var count := int(cfg["fungus"] * clampf(b.size.x * b.size.z / 400.0, 0.25, 1.0))
	for i: int in count:
		var edge := _rng.randi() % 4
		var t := _rng.randf()
		var inset := 0.9
		var p := Vector3(lerpf(b.position.x + inset, b.end.x - inset, t), b.end.y, lerpf(b.position.z + inset, b.end.z - inset, t))
		match edge:
			0: p.z = b.position.z + inset
			1: p.z = b.end.z - inset
			2: p.x = b.position.x + inset
			3: p.x = b.end.x - inset
		var s := _rng.randf_range(0.7, 1.5)
		_add("fungus_cap", Transform3D(Basis(Vector3.UP, _rng.randf() * TAU) * Basis.from_scale(Vector3.ONE * s), p))
		if i % 3 == 0:
			light(p + Vector3.UP * 1.2, cfg["lamp"], 0.9, 7.0, 0.0)  # no fog cost for the scatter


# --- instancing --------------------------------------------------------------------------------

func _add(model: String, xf: Transform3D) -> void:
	if not _xf.has(model):
		_xf[model] = []
	_xf[model].append(xf)


func _mat(n: String) -> Material:
	return MaterialLib.lookup(n, [MATS, MaterialLib.CORE_DIR])


## A model instance with the wing's materials, or null when it is missing.
static func model(n: String) -> Node3D:
	var path := MODELS + n + ".glb"
	if not ResourceLoader.exists(path):
		return null
	var node: Node3D = (load(path) as PackedScene).instantiate()
	MaterialLib.apply(node, [MATS, MaterialLib.CORE_DIR])
	return node


func _mm(n: String, xforms: Array) -> void:
	var src := model(n)
	if src == null or xforms.is_empty():
		return
	var found := src.find_children("*", "MeshInstance3D", true, false)
	if found.is_empty():
		src.free()
		return
	var smi := found[0] as MeshInstance3D
	var mesh: Mesh = smi.mesh.duplicate()
	for i in mesh.get_surface_count():
		var m := smi.get_surface_override_material(i)
		if m:
			mesh.surface_set_material(i, m)
	src.free()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = xforms.size()
	for i in xforms.size():
		mm.set_instance_transform(i, xforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.name = "MM_" + n
	mmi.multimesh = mm
	add_child(mmi)


## Place a model at a transform (one-offs).
func put(n: String, xf: Transform3D, parent: Node3D = null) -> Node3D:
	var m := model(n)
	if m:
		m.transform = xf
		(parent if parent else self).add_child(m)
	return m


func light(pos: Vector3, col: Color, energy: float, rng: float, fog: float = 1.0) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = col
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.6
	l.light_volumetric_fog_energy = fog
	l.distance_fade_enabled = true
	l.distance_fade_begin = 45.0
	l.distance_fade_length = 15.0
	add_child(l)
	_lights += 1
	return l


# --- the player's swing line ----------------------------------------------------------------------

func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		_expose(cam.global_position)
	var silk: Object = wing.get("silk")
	var pts: PackedVector3Array = silk.call("line_points") if silk else PackedVector3Array()
	var need := maxi(pts.size() - 1, 0)
	while _rope.size() < need:
		var mi := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.035
		cm.bottom_radius = 0.035
		cm.height = 1.0
		cm.radial_segments = 8
		cm.rings = 24
		mi.mesh = cm
		mi.material_override = _rope_mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		_rope.append(mi)
	for i: int in _rope.size():
		var mi := _rope[i]
		mi.visible = i < need
		if i >= need:
			continue
		var a := pts[i]
		var b := pts[i + 1]
		if i == need - 1:
			b += Vector3.DOWN * 0.15  # into the wrist, not the eye
		var d := b - a
		var l := maxf(d.length(), 0.01)
		var y := d / l
		var x := y.cross(Vector3.FORWARD if absf(y.z) < 0.9 else Vector3.RIGHT).normalized()
		var z := x.cross(y)
		mi.global_transform = Transform3D(Basis(x, y * l, z), (a + b) * 0.5)
		mi.set_instance_shader_parameter(&"len", 1.0)
		mi.set_instance_shader_parameter(&"beads", l * 1.5)


## The eye adapts to each area (camera driven, so shots and play agree).
func _expose(c: Vector3) -> void:
	var e: float = AREAS["OuterGate"]["exp"]
	if c.y < -45.0 and c.x > 54.0:
		e = AREAS["CoronationHall"]["exp"]
	elif c.x < 60.0 and c.z > -25.0 and c.y < -20.0:
		e = AREAS["GeneralArena"]["exp"]
	elif c.z > 80.5 and c.x < 95.0:
		e = AREAS["TapestryGallery"]["exp"]
	elif c.z > 14.0 and c.x > 94.0:
		e = AREAS["Foundry"]["exp"]
	elif c.x > 80.0:
		e = AREAS["HiveShaft"]["exp"]
	elif c.x > 13.0:
		e = AREAS["SilkDistricts"]["exp"]
	_exp = e if _exp < 0.0 else lerpf(_exp, e, 0.05)
	env.tonemap_exposure = _exp
