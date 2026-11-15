class_name ClayDressing
extends Node3D
## Set dressing for the Pinched Forest, all MultiMesh: trees, bushes, flowers, tufts, toadstools, pebbles
## and bulrushes, scattered by a seeded hand so every run is the same set. The ground is clay the player
## reshapes, so after every flush the dressing re-seats on the new height, and anything on ground the
## player has worked (mark > 0.3) is squashed away (scale 0), as a model-maker would pick it off.
## Gameplay ground (pit, mound, knoll, trench, ramp strip, bench, chase corridor, path) is kept clear.

const MODEL_DIR := "res://wings/clay/models/"

var terrain: ClayTerrain
var _sets: Array[Dictionary] = []   # {mm: MultiMesh, pts: Array[Vector3], basis: Array[Basis], sink: float}
var _keep_out: Array = []           # [Vector2 centre, radius] or [Rect2]


func build(t: ClayTerrain, keep_out: Array) -> void:
	terrain = t
	_keep_out = keep_out
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 88
	# perimeter woods: three rings of trees just inside the edge, and clumps along the sides
	var trees: Array[Vector3] = []
	for ring in [37.0, 33.5]:
		var n := int(ring * 0.42)
		for i in n:
			var a := TAU * (i + rnd.randf_range(-0.3, 0.3)) / n
			var tp := Vector3(cos(a) * ring, 0, sin(a) * ring) + Vector3(rnd.randf_range(-1.5, 1.5), 0, rnd.randf_range(-1.5, 1.5))
			if not _blocked(tp, 1.0):
				trees.append(tp)
	trees += _scatter(rnd, 26, Rect2(-30, -30, 60, 64), 4.5)
	var split := [[], [], []]
	for i in trees.size():
		split[i % 3].append(trees[i])
	for k in 3:
		_add("tree_%s.glb" % ["a", "b", "c"][k], split[k], rnd, Vector2(0.85, 1.25), 0.25, true)
	_add("bush.glb", _scatter(rnd, 60, Rect2(-36, -36, 72, 72), 1.6), rnd, Vector2(0.8, 1.6), 0.1, true)
	var flower_cols := ["pink", "yellow", "purple", "ivory"]
	for c in flower_cols:
		_add("flower_%s.glb" % c, _clusters(rnd, 14, 7, Rect2(-34, -30, 68, 66), 1.4), rnd, Vector2(1.4, 2.4), 0.0, false)
	_add("tuft.glb", _clusters(rnd, 40, 6, Rect2(-36, -36, 72, 72), 1.2), rnd, Vector2(1.0, 2.0), 0.02, false)
	# the village green: walk-through drifts of flowers and grass on the square (no big things there)
	var green := Rect2(-22, -29, 35, 11.5)
	for c in ["yellow", "ivory", "pink"]:
		_add("flower_%s.glb" % c, _clusters(rnd, 7, 8, green, 1.6, true), rnd, Vector2(1.3, 2.2), 0.0, false)
	_add("tuft.glb", _clusters(rnd, 18, 7, green, 1.4, true), rnd, Vector2(1.0, 2.0), 0.02, false)
	_add("toadstool.glb", _clusters(rnd, 9, 4, Rect2(-34, -30, 68, 66), 0.9), rnd, Vector2(0.8, 2.6), 0.02, false)
	_add("pebble.glb", _scatter(rnd, 70, Rect2(-36, -36, 72, 72), 0.8), rnd, Vector2(0.6, 1.8), 0.08, false)
	# bulrushes along both banks of the trench (the banks are steep: they stand at the lip)
	var reeds: Array[Vector3] = []
	for side in [-1.0, 1.0]:
		var x := -38.0
		while x < 38.0:
			x += rnd.randf_range(0.5, 2.2)
			if absf(x) < 1.8:
				continue
			reeds.append(Vector3(x, 0, -4.5 + side * rnd.randf_range(2.35, 2.9)))
	_add("reed.glb", reeds, rnd, Vector2(0.8, 1.3), 0.05, false, true)
	terrain_changed()


## Points kept off gameplay ground, at least `gap` apart.
func _scatter(rnd: RandomNumberGenerator, n: int, area: Rect2, gap: float, small: bool = false) -> Array[Vector3]:
	var out: Array[Vector3] = []
	var tries := 0
	while out.size() < n and tries < n * 40:
		tries += 1
		var p := Vector3(rnd.randf_range(area.position.x, area.end.x), 0, rnd.randf_range(area.position.y, area.end.y))
		if _blocked(p, 0.6, small):
			continue
		var ok := true
		for q in out:
			if Vector2(q.x - p.x, q.z - p.z).length() < gap:
				ok = false
				break
		if ok:
			out.append(p)
	return out


## Drifts of small things, the way a set dresser presses a handful in at once.
func _clusters(rnd: RandomNumberGenerator, n: int, per: int, area: Rect2, spread: float, small_centres: bool = false) -> Array[Vector3]:
	var out: Array[Vector3] = []
	for c in _scatter(rnd, n, area, 3.0, small_centres):
		for i in per:
			var p := c + Vector3(rnd.randf_range(-spread, spread), 0, rnd.randf_range(-spread, spread))
			if not _blocked(p, 0.2, true):
				out.append(p)
	return out


## `small`: flowers, tufts and pebbles may go where only big things are kept out (entries marked "big").
func _blocked(p: Vector3, pad: float, small: bool = false) -> bool:
	if absf(p.x) > 39.0 or absf(p.z) > 39.0:
		return true
	for k: Array in _keep_out:
		if small and k.size() > 2 and k[2] == "big":
			continue
		if k[0] is Rect2:
			if (k[0] as Rect2).grow(pad).has_point(Vector2(p.x, p.z)):
				return true
		elif Vector2(p.x, p.z).distance_to(k[0]) < float(k[1]) + pad:
			return true
	# the path down the middle of the set (same curve as the ground shader)
	var px := absf(p.x - 1.6 * sin(p.z * 0.14) - 0.6 * sin(p.z * 0.41))
	return px < 1.8 + pad and p.z < 34.0 and p.z > -35.0


func _add(file: String, pts: Array, rnd: RandomNumberGenerator, scale_range: Vector2, sink: float, shadows: bool, upright: bool = false) -> void:
	if pts.is_empty():
		return
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh_of(file)
	mm.instance_count = pts.size()
	var bases: Array[Basis] = []
	var pp: Array[Vector3] = []
	for p in pts:
		var s := rnd.randf_range(scale_range.x, scale_range.y)
		var b := Basis(Vector3.UP, rnd.randf_range(0.0, TAU))
		if not upright:
			b = Basis(Vector3(rnd.randf_range(-1, 1), 0, rnd.randf_range(-1, 1)).normalized(), rnd.randf_range(0.0, 0.12)) * b
		bases.append(b.scaled(Vector3.ONE * s))
		pp.append(p)
	var mi := MultiMeshInstance3D.new()
	mi.name = file.get_basename()
	mi.multimesh = mm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.visibility_range_end = 70.0 if shadows else 34.0
	mi.visibility_range_end_margin = 6.0
	mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	add_child(mi)
	_sets.append({"mm": mm, "pts": pp, "basis": bases, "sink": sink})


## Re-seat everything on the current ground. Called after the terrain flushes.
func terrain_changed() -> void:
	for st in _sets:
		var mm: MultiMesh = st["mm"]
		var pts: Array = st["pts"]
		var bases: Array = st["basis"]
		for i in pts.size():
			var p: Vector3 = pts[i]
			var worked := _mark_at(p.x, p.z) > 0.3
			var b: Basis = bases[i] if not worked else Basis().scaled(Vector3.ONE * 0.001)
			mm.set_instance_transform(i, Transform3D(b, Vector3(p.x, terrain.height_at(p.x, p.z) - float(st["sink"]), p.z)))


func _mark_at(x: float, z: float) -> float:
	var ix := clampi(roundi(x + ClayTerrain.HALF), 0, ClayTerrain.N - 1)
	var iz := clampi(roundi(z + ClayTerrain.HALF), 0, ClayTerrain.N - 1)
	return terrain.mark[iz * ClayTerrain.N + ix]


## The first mesh of a model, with the wing's materials baked onto its surfaces (MultiMesh ignores the
## per-instance overrides MaterialLib.apply sets).
static func mesh_of(file: String) -> Mesh:
	var n := (load(MODEL_DIR + file) as PackedScene).instantiate()
	var mi: MeshInstance3D = n if n is MeshInstance3D else n.find_children("*", "MeshInstance3D", true, false)[0]
	var m := mi.mesh.duplicate() as ArrayMesh
	for i in m.get_surface_count():
		var src := m.surface_get_material(i)
		if src:
			var mat := MaterialLib.lookup(src.resource_name, ["res://wings/clay/materials", MaterialLib.CORE_DIR])
			if mat:
				m.surface_set_material(i, mat)
	n.free()
	return m
