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
	"HiveShaft": {"wall": "carapace", "fungus": 4, "comb": 16, "lamp": Color(0.55, 1.0, 0.85), "exp": 3.3},
	"Foundry": {"wall": "carapace", "fungus": 14, "comb": 8, "lamp": Color(0.55, 1.0, 0.85), "exp": 1.9},
	"TapestryGallery": {"wall": "comb_dim", "fungus": 8, "comb": 0, "lamp": Color(0.6, 1.0, 0.88), "exp": 2.3},
	"GeneralArena": {"wall": "comb", "fungus": 18, "comb": 0, "lamp": Color(1.0, 0.7, 0.35), "exp": 2.8},
	"CoronationHall": {"wall": "carapace", "fungus": 12, "comb": 6, "lamp": Color(1.0, 0.65, 0.3), "exp": 3.0},
	"Heist": {"wall": "carapace", "fungus": 4, "comb": 12, "lamp": Color(1.0, 0.65, 0.3), "exp": 1.8},
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
var _meshes := {}                  # model name -> Mesh with the wing's materials baked in

const CHUNK := 16.0
const NEAR := 30.0                 # wall skins switch to flat stand-ins of the same material family past this
const FAR := {"comb_panel": "comb_dim", "plate_panel": "carapace"}
## Wall skins and small scatter cast no shadows: the walls behind them already do, and the key's
## cascades would otherwise redraw thousands of cells.
const NO_SHADOW := ["comb_panel", "plate_panel", "web", "shelf_edge", "lip", "fungus_cap", "fungus_shelf", "comb"]
const FADE := {"fungus_cap": 70.0, "web": 60.0, "fungus_shelf": 80.0}
## Per-model material swaps: comb panel caps use a dimmer, cell-varied amber.
const SWAP := {"comb_panel": {"amber": "amber_cell", "carapace_dull": "wax"}}  # open cells: old dim wax, not void


## Sculpted room shells and platform skins (models/src/shells.json) over the unchanged collision:
## the wall boxes they cover and the platform boxes they skin are hidden, collision stays.
const SHELLS := "res://wings/chitin/models/src/shells.json"
var _cover: Array[AABB] = []
var _skinned: Array[AABB] = []


func _shell(n: String) -> void:
	var m := put(n, Transform3D.IDENTITY)
	if m:
		for mi: MeshInstance3D in m.find_children("*", "MeshInstance3D", true, false):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF  # the eye's light falls through


## Amber light falling through the comb in the vault crown: narrow fogged spots, every ~18 m.
func _shafts(r: Dictionary) -> void:
	var a: Array = r["a"]
	var c: Array = r["c"]
	var n := maxi(1, int((float(a[1]) - float(a[0])) / 18.0))
	var mid := (float(c[0]) + float(c[1])) * 0.5
	var drop := float(r["peak"]) - float(r["floor"])
	for i: int in n:
		var u := lerpf(float(a[0]), float(a[1]), (i + 0.5) / n)
		var off := (float(c[1]) - float(c[0])) * 0.18 * (1.0 if i % 2 == 0 else -1.0)
		var top := Vector3(u, float(r["peak"]) - 1.0, mid + off) if r["axis"] == "x" else Vector3(mid + off, float(r["peak"]) - 1.0, u)
		_spot(top, top + Vector3(0.25 * signf(off), -1.0, 0.15), drop + 4.0, 15.0)


func _spot(from: Vector3, to: Vector3, rng: float, angle: float) -> void:
	var sp := SpotLight3D.new()
	sp.light_color = Color(1.0, 0.55, 0.16)
	sp.light_energy = 9.0
	sp.spot_range = rng
	sp.spot_angle = angle
	sp.spot_attenuation = 0.6
	sp.light_volumetric_fog_energy = 30.0  # froxels are ~27 px: beams under ~12° vanish
	sp.shadow_enabled = false
	add_child(sp)
	sp.look_at_from_position(from, to, Vector3.FORWARD)


## The throat walls carry comb clusters over their full height and webs slung across the corners.
func _throat_comb(r: Dictionary) -> void:
	var x0 := float(r["x"][0])
	var x1 := float(r["x"][1])
	var z0 := float(r["z"][0])
	var z1 := float(r["z"][1])
	var tops: Dictionary = r["tops"]
	# wall: [start, end, yaw (model front +Z faces into the shaft), top]
	for w: Array in [[Vector3(x0, 0, z0), Vector3(x0, 0, z1), PI / 2.0, tops["west"]],
			[Vector3(x1, 0, z0), Vector3(x1, 0, z1), -PI / 2.0, tops["east"]],
			[Vector3(x0, 0, z0), Vector3(x1, 0, z0), 0.0, tops["south"]],
			[Vector3(x0, 0, z1), Vector3(x1, 0, z1), PI, tops["north"]]]:
		var a: Vector3 = w[0]
		var b: Vector3 = w[1]
		var top := float(w[3]) - 2.0
		var n := int(a.distance_to(b) * (top + 68.0) / 55.0)
		for i: int in n:
			var p := a.lerp(b, _rng.randf_range(0.06, 0.94))
			p.y = _rng.randf_range(-67.0, top)
			if p.y < -64.0 and p.x < 84.0:
				continue  # keep the stair door clear
			_add("comb", Transform3D(Basis(Vector3.UP, float(w[2])).rotated(Vector3(0, 0, 1).rotated(Vector3.UP, float(w[2])), _rng.randf_range(-0.6, 0.6)) * Basis.from_scale(Vector3.ONE * _rng.randf_range(1.0, 1.8)), p))
	for c: Vector3 in [Vector3(x0, 0, z0), Vector3(x1, 0, z0), Vector3(x0, 0, z1), Vector3(x1, 0, z1)]:
		var yaw := atan2(-(c.x - (x0 + x1) * 0.5), -(c.z - (z0 + z1) * 0.5))
		for y: float in [-60.0, -44.0, -30.0]:
			var inward := Vector3(signf((x0 + x1) * 0.5 - c.x), 0, signf((z0 + z1) * 0.5 - c.z)) * 1.6
			_add("web", Transform3D(Basis(Vector3.UP, yaw) * Basis.from_scale(Vector3(1.6, 1.6, 1.0)), c + inward + Vector3(0, y + _rng.randf_range(-3, 3), 0)))


func _inside(list: Array[AABB], p: Vector3) -> bool:
	for b: AABB in list:
		if b.grow(0.01).has_point(p):
			return true
	return false


func dress(w: Node3D, environment: Environment, key: DirectionalLight3D) -> void:
	wing = w
	env = environment
	sun = key
	_rng.seed = 340
	name = "Look"
	_rope_mat = load("res://wings/chitin/materials/silk_line.tres")
	var spec: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SHELLS))
	for r: Dictionary in spec["partitions"]:
		_shell(r["name"])
		for c: Array in r["cover"]:
			_cover.append(AABB(Vector3(c[0], c[1], c[2]), Vector3(c[3] - c[0], c[4] - c[1], c[5] - c[2])))
	for r: Dictionary in spec["rooms"] + [spec["throat"]]:
		_shell(r["name"])
		_shell(r["name"] + "_comb")
		if r.has("axis"):
			_shafts(r)
			if r["name"] == "shell_arena":  # the walkway hangs over a pit; give it its own pools
				for z: float in [92.0, 76.0, 60.0]:
					_spot(Vector3(40, -8, z), Vector3(40.2, -9, z + 0.1), 30.0, 12.0)
		else:  # the throat: three long shafts of eye-light falling to the hall floor
			for t: Vector3 in [Vector3(98, 12, -16), Vector3(124, 12, 2), Vector3(116, 12, -24)]:
				_spot(t, t + Vector3(0.1, -1.0, 0.05), 92.0, 9.0)
			_throat_comb(r)
		for c: Array in r["cover"]:
			_cover.append(AABB(Vector3(c[0], c[1], c[2]), Vector3(c[3] - c[0], c[4] - c[1], c[5] - c[2])))
	for pl: Dictionary in spec["platforms"]:
		_shell(pl["name"])
		var q: Array = pl["rect"]
		_skinned.append(AABB(Vector3(q[0], float(pl["base"]) - 0.5, q[2]), Vector3(q[1] - q[0], float(pl["top"]) - float(pl["base"]) + 0.5, q[3] - q[2])))
	var areas := w.get_node("Areas")
	for area: Node in areas.get_children():
		_dress_area(area as Node3D, AREAS.get(String(area.name), AREAS["OuterGate"]))
	for m: String in _xf:
		# chunked so each MultiMesh frustum-culls and picks its own mesh LOD
		var chunks := {}
		for xf: Transform3D in _xf[m]:
			var c := Vector3i((xf.origin / CHUNK).floor())
			if not chunks.has(c):
				chunks[c] = []
			chunks[c].append(xf)
		for c: Vector3i in chunks:
			_mm(m, chunks[c])
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
		if col.is_equal_approx(Color("6b7f8a")) and _inside(_skinned, box.get_center()):
			mi.visible = false
		elif col.is_equal_approx(Color("39424a")) and _inside(_cover, box.get_center()):
			mi.visible = false
		elif col.is_equal_approx(Color("6b7f8a")):
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
		if f.size.x * f.size.z < 600.0:
			_underside(f)
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
		# layered chitin shelves hang under the edge, so a slab's side never reads as a box
		if b.size.y > 0.6:
			var n := maxi(1, roundi(length / 4.0))
			var dir := Basis(Vector3.UP, e[2]).x
			for i: int in n:
				var off := (i + 0.5) * length / n - length * 0.5
				var sb := Basis(Vector3.UP, e[2]) * Basis.from_scale(Vector3(length / n / 4.0, minf(1.0, b.size.y / 1.2), 1.0))
				_add("shelf_edge", Transform3D(sb, e[0] + dir * off + Vector3(0, -0.12, 0)))


## Ledges seen from below (the shaft, the heist): overlapping plates over the bottom face.
func _underside(b: AABB) -> void:
	var nx := maxi(1, roundi(b.size.x / 4.0))
	var nz := maxi(1, roundi(b.size.z / 4.0))
	# rotated so the plates' front (+Z) faces down; the panel's height then runs along +Z
	var basis := Basis(Vector3.RIGHT, PI / 2.0) * Basis.from_scale(Vector3(b.size.x / nx / 4.0, b.size.z / nz / 4.0, 0.6))
	for i: int in nx:
		for k: int in nz:
			_add("plate_panel", Transform3D(basis, Vector3(b.position.x + (i + 0.5) * b.size.x / nx, b.position.y, b.position.z + k * b.size.z / nz)))


## Every broad wall face is covered in modelled panels (deep comb cells or overlapping carapace
## plates), so no wall reads as a textured plane; ribs every ~8 m, secreted columns at the ends,
## silk webs strung between some ribs, and comb or fungus shelves on the panels.
func _ribs(b: AABB, cfg: Dictionary) -> void:
	var h := b.size.y
	if h < 2.5:
		return
	var along_x := b.size.x >= b.size.z
	var length := b.size.x if along_x else b.size.z
	if length < 3.0:
		return
	var comb_wall: bool = String(cfg["wall"]).begins_with("comb")
	var nx := maxi(1, roundi(length / 4.0))
	var nz := maxi(1, roundi(h / 4.0))
	var sx := length / nx / 4.0
	var sz := h / nz / 4.0
	for side: float in [-1.0, 1.0]:
		var yaw: float
		if along_x:
			yaw = 0.0 if side > 0 else PI
		else:
			yaw = PI / 2.0 if side > 0 else -PI / 2.0
		var basis := Basis(Vector3.UP, yaw)
		for i: int in nx:
			var u := (i + 0.5) * length / nx
			# a few carapace columns break up comb streets (the comb on carapace walls grows on the shells now)
			var stripe := _rng.randf()
			var lo := 0
			if not comb_wall and nz > 2:
				lo = _rng.randi_range(0, nz - 2)  # windows two panels tall, not floor-to-ceiling stripes
			for k: int in nz:
				var win := stripe < float(cfg.get("win", 0.0)) and (comb_wall or nz <= 2 or k == lo or k == lo + 1)
				var panel := "comb_panel" if (comb_wall and stripe > 0.15) or (not comb_wall and win) else "plate_panel"
				var p: Vector3
				if along_x:
					p = Vector3(b.position.x + u, b.position.y + k * h / nz, b.position.z if side < 0 else b.end.z)
				else:
					p = Vector3(b.position.x if side < 0 else b.end.x, b.position.y + k * h / nz, b.position.z + u)
				# model front is +Z (Godot); depth squashed so cells never reach far into the walk space
				_add(panel, Transform3D(basis * Basis.from_scale(Vector3(sx, sz, 0.6)), p))
		var n := maxi(1, int(length / 8.0))
		for i: int in n + 1:
			var u := (float(i) / n) * (length - 1.0) + 0.5
			var p: Vector3
			if along_x:
				p = Vector3(b.position.x + u, b.position.y, b.position.z if side < 0 else b.end.z)
			else:
				p = Vector3(b.position.x if side < 0 else b.end.x, b.position.y, b.position.z + u)
			_add("rib", Transform3D(basis * Basis.from_scale(Vector3(1.0, h, 1.0)), p))
			if i < n and h > 4.0:
				var step := (length - 1.0) / n
				var q := p + (Vector3(step * 0.5, 0, 0) if along_x else Vector3(0, 0, step * 0.5))
				var roll := _rng.randf()
				var y := q.y + clampf(_rng.randf_range(1.5, h - 2.0), 1.0, 6.0)
				if roll < float(cfg["comb"]) / 40.0:
					_add("comb", Transform3D(basis * Basis.from_scale(Vector3.ONE * _rng.randf_range(0.8, 1.4)), Vector3(q.x, y, q.z)))
				elif roll < 0.45:
					_add("fungus_shelf", Transform3D(basis * Basis.from_scale(Vector3.ONE * _rng.randf_range(0.7, 1.3)), Vector3(q.x, q.y + _rng.randf_range(0.8, 3.0), q.z)))
				elif roll < 0.7 and h > 7.0:
					# a web strung across the bay, standing off the panels
					var off := (Vector3(0, 0, side) if along_x else Vector3(side, 0, 0)) * 0.5
					var ws := step / 4.0
					_add("web", Transform3D(basis * Basis.from_scale(Vector3(ws, ws, 1.0)), Vector3(q.x, q.y + h - 4.5 * ws, q.z) + off))
	# secreted columns hide the wall's end faces
	if h > 5.0:
		var ends: Array[Vector3] = []
		if along_x:
			ends = [Vector3(b.position.x, b.position.y, b.get_center().z), Vector3(b.end.x, b.position.y, b.get_center().z)]
		else:
			ends = [Vector3(b.get_center().x, b.position.y, b.position.z), Vector3(b.get_center().x, b.position.y, b.end.z)]
		var thick := minf(b.size.x, b.size.z)
		for e: Vector3 in ends:
			var r := clampf(thick / 1.2, 0.8, 2.5)
			_add("column", Transform3D(Basis(Vector3.UP, _rng.randf() * TAU) * Basis.from_scale(Vector3(r, h / 8.0, r)), e))


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
	var mesh := _mesh(n, n)
	if mesh == null or xforms.is_empty():
		return
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = xforms.size()
	for i in xforms.size():
		mm.set_instance_transform(i, xforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.name = "MM_" + n
	mmi.multimesh = mm
	if NO_SHADOW.has(n):
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if FADE.has(n):
		mmi.visibility_range_end = FADE[n]
		mmi.visibility_range_end_margin = 8.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	add_child(mmi)
	if FAR.has(n):
		# HLOD: the modelled skin near the eye, a flat stand-in with the same material family beyond
		mmi.visibility_range_end = NEAR
		mmi.visibility_range_end_margin = 4.0
		var q: Mesh = _meshes.get(n + "_far")
		if q == null:
			var qm := QuadMesh.new()
			qm.size = Vector2(4.0, 4.0)
			qm.center_offset = Vector3(0, 2.0, 0.12)
			qm.material = _mat(FAR[n])
			q = qm
			_meshes[n + "_far"] = q
		_tier(n + "_far", q, xforms, NEAR, 0.0)


func _tier(n: String, mesh: Mesh, xforms: Array, begin: float, end: float) -> void:
	var fm := MultiMesh.new()
	fm.transform_format = MultiMesh.TRANSFORM_3D
	fm.mesh = mesh
	fm.instance_count = xforms.size()
	for i in xforms.size():
		fm.set_instance_transform(i, xforms[i])
	var fmi := MultiMeshInstance3D.new()
	fmi.name = "MM_" + n
	fmi.multimesh = fm
	fmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	fmi.visibility_range_begin = begin
	fmi.visibility_range_begin_margin = 4.0
	fmi.visibility_range_end = end
	fmi.visibility_range_end_margin = 4.0
	add_child(fmi)


## A model's first mesh with its materials baked in (and SWAP applied under the base name), cached.
func _mesh(n: String, base: String) -> Mesh:
	if _meshes.has(n):
		return _meshes[n]
	var src := model(n)
	if src == null:
		return null
	var found := src.find_children("*", "MeshInstance3D", true, false)
	var mesh: Mesh = null
	if not found.is_empty():
		var smi := found[0] as MeshInstance3D
		mesh = smi.mesh.duplicate()
		for i in mesh.get_surface_count():
			var m := smi.get_surface_override_material(i)
			if m and SWAP.has(base) and SWAP[base].has(m.resource_name):
				m = _mat(SWAP[base][m.resource_name])
			if m:
				mesh.surface_set_material(i, m)
	src.free()
	_meshes[n] = mesh
	return mesh


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
