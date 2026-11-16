extends RefCounted
## Art helpers for the Unfinished Wing: generated paint geometry (knife-laid slabs, daubs), the
## wing's materials and its Blender models. Collision never comes from here; gameplay keeps its boxes.

const MAT_DIR := "res://wings/paint/materials"
const MODEL_DIR := "res://wings/paint/models/"

static var _noise: FastNoiseLite
static var _mats: Dictionary = {}
static var _scenes: Dictionary = {}


## Drop the caches when the wing goes (static vars outlive the scene and show up as leaks at exit).
static func clear() -> void:
	_noise = null
	_mats.clear()
	_scenes.clear()


static func noise() -> FastNoiseLite:
	if _noise == null:
		_noise = FastNoiseLite.new()
		_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		_noise.frequency = 0.35
		_noise.fractal_octaves = 3
	return _noise


static func mat(name: String) -> Material:
	if not _mats.has(name):
		_mats[name] = load("%s/%s.tres" % [MAT_DIR, name])
	return _mats[name]


## A Blender model with the wing's materials applied. LOD: pass a visibility range for repeats.
static func model(name: String) -> Node3D:
	if not _scenes.has(name):
		_scenes[name] = load(MODEL_DIR + name + ".glb")
	var n: Node3D = (_scenes[name] as PackedScene).instantiate()
	MaterialLib.apply(n, [MAT_DIR, MaterialLib.CORE_DIR])
	return n


## A slab of paint laid with a knife: the box's corners rounded off, its sides pushed in and out
## and dragged downward in streaks, its top lightly rippled. `at` (world centre) seeds the noise so
## neighbouring slabs differ. Visual only: the collider stays the exact box.
static func slab_mesh(size: Vector3, at: Vector3, radius: float = 0.45, side_amp: float = 0.16, top_amp: float = 0.035) -> ArrayMesh:
	var bm := BoxMesh.new()
	bm.size = size
	bm.subdivide_width = clampi(int(size.x / 1.1), 1, 48)
	bm.subdivide_height = clampi(int(size.y / 0.6), 1, 24)
	bm.subdivide_depth = clampi(int(size.z / 1.1), 1, 48)
	var arr := bm.get_mesh_arrays()
	var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var nm: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
	var half := size * 0.5
	var r := minf(radius, minf(half.x, minf(half.y, half.z)) * 0.95)
	var inner := half - Vector3.ONE * r
	var nz := noise()
	for i in v.size():
		var p := v[i]
		var q := p.clamp(-inner, inner)
		var d := p - q
		var n := nm[i]
		if d.length() > 0.0001:
			n = d.normalized()
			p = q + n * r
		var w := p + at
		var amp: float
		if n.y > 0.7:
			amp = top_amp * nz.get_noise_2d(w.x * 1.7, w.z * 1.7)
		else:
			# streaks dragged down the sides, and a ragged outline
			amp = side_amp * (0.6 * nz.get_noise_3d(w.x * 0.9, w.y * 0.25, w.z * 0.9) + 0.4 * nz.get_noise_2d(w.x * 3.1 + w.z * 3.1, w.y * 0.5))
		v[i] = p + n * amp
		nm[i] = n
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nm
	arr[Mesh.ARRAY_TANGENT] = null
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


## A painted field seen from afar: a rounded island whose top (y 0 at the origin) is gently
## hummocked and whose banks roll down to `drop` below it, with a ragged outline. Visual only.
static func mound_mesh(sx: float, sz: float, drop: float, at: Vector3) -> ArrayMesh:
	var nz := noise()
	var nx := clampi(int(sx / 1.4), 8, 44)
	var nzc := clampi(int(sz / 1.4), 8, 44)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for iz in nzc + 1:
		for ix in nx + 1:
			var u := float(ix) / nx * 2.0 - 1.0
			var w := float(iz) / nzc * 2.0 - 1.0
			var wx := at.x + u * sx * 0.5
			var wz := at.z + w * sz * 0.5
			var e := pow(pow(absf(u), 4.0) + pow(absf(w), 4.0), 0.25) * (1.0 + 0.12 * nz.get_noise_2d(wx * 0.3, wz * 0.3))
			var inner := 1.0 - smoothstep(0.8, 1.0, e)
			var y := -drop * (1.0 - sqrt(inner)) + inner * 0.35 * nz.get_noise_2d(wx * 0.15, wz * 0.15)
			st.set_uv(Vector2(u, w) * 0.5 + Vector2(0.5, 0.5))
			st.add_vertex(Vector3(u * sx * 0.5, y, w * sz * 0.5))
	for iz in nzc:
		for ix in nx:
			var a := iz * (nx + 1) + ix
			var b := a + nx + 1
			st.add_index(a)
			st.add_index(a + 1)
			st.add_index(b)
			st.add_index(a + 1)
			st.add_index(b + 1)
			st.add_index(b)
	st.generate_normals()
	return st.commit()


## A daub: a domed puddle of wet paint with a ragged outline (where strokes bleed into each other).
static func daub_mesh(radius: float, height: float, seed: float) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	const RINGS := 6
	const SEGS := 28
	var nz := noise()
	st.set_uv(Vector2(0.5, 0.5))
	st.add_vertex(Vector3(0, height, 0))
	for ri in range(1, RINGS + 1):
		var t := float(ri) / RINGS
		for si in SEGS:
			var a := TAU * si / SEGS
			var rr := radius * t * (1.0 + 0.28 * nz.get_noise_2d(cos(a) * 3.0 + seed, sin(a) * 3.0))
			var h := height * (1.0 - t * t) + 0.01
			st.set_uv(Vector2(rr * cos(a) / radius * 2.0, 0.5 + 0.5 * sin(a) * t))
			st.add_vertex(Vector3(cos(a) * rr, h, sin(a) * rr))
	for si in SEGS:
		st.add_index(0); st.add_index(1 + (si + 1) % SEGS); st.add_index(1 + si)
	for ri in range(RINGS - 1):
		var a0 := 1 + ri * SEGS
		var b0 := a0 + SEGS
		for si in SEGS:
			var s1 := (si + 1) % SEGS
			st.add_index(a0 + si); st.add_index(a0 + s1); st.add_index(b0 + si)
			st.add_index(a0 + s1); st.add_index(b0 + s1); st.add_index(b0 + si)
	st.generate_normals()
	st.generate_tangents()
	return st.commit()
