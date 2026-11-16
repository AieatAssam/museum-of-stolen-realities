class_name ClayTerrain
extends Node3D
## Deformable clay ground: an 80 m square heightfield on 1 m cells, centred on the wing origin.
## Edits are queued while the player holds a verb and applied on the next world beat, so the
## ground only changes on twos. Collision (HeightMapShape3D) and the visible ground update together
## in flush(), and only when something changed. The visible ground is a static grid RES times finer
## that the terrain shader lifts from a height texture with a Catmull-Rom patch: pulled clay gets
## rounded shoulders and eases into the moss instead of showing 1 m facets and a crease at its foot.

const N := 81
const HALF := 40.0
const MIN_H := -2.4
const MAX_H := 4.2
const MATERIAL := preload("res://wings/clay/materials/ground.tres")
const RES := 3  # render vertices per 1 m cell

var h := PackedFloat32Array()     # index = iz * N + ix, world x = ix - HALF, z = iz - HALF
var mark := PackedFloat32Array()  # 0..1: shaped by the player (raw clay, fingerprints show)
var dirty: bool = false
var _mesh_inst: MeshInstance3D
var _body: StaticBody3D
var _shape: HeightMapShape3D
var _tex: ImageTexture


func setup(base_fn: Callable) -> void:
	h.resize(N * N)
	mark.resize(N * N)
	for iz in N:
		for ix in N:
			h[iz * N + ix] = float(base_fn.call(ix - HALF, iz - HALF))
	mark.fill(0.0)
	_mesh_inst = MeshInstance3D.new()
	var mat := MATERIAL.duplicate() as ShaderMaterial
	mat.set_shader_parameter(&"half_size", HALF)
	_mesh_inst.material_override = mat
	_mesh_inst.mesh = _grid_mesh()
	add_child(_mesh_inst)
	_body = StaticBody3D.new()
	_body.collision_layer = 1
	_body.collision_mask = 0
	_shape = HeightMapShape3D.new()
	_shape.map_width = N
	_shape.map_depth = N
	var cs := CollisionShape3D.new()
	cs.shape = _shape
	_body.add_child(cs)
	add_child(_body)
	dirty = true
	flush()


func collider() -> StaticBody3D:
	return _body


func height_at(wx: float, wz: float) -> float:
	var fx := clampf(wx + HALF, 0.0, N - 1.001)
	var fz := clampf(wz + HALF, 0.0, N - 1.001)
	var ix := int(fx)
	var iz := int(fz)
	var tx := fx - ix
	var tz := fz - iz
	var a := lerpf(h[iz * N + ix], h[iz * N + ix + 1], tx)
	var b := lerpf(h[(iz + 1) * N + ix], h[(iz + 1) * N + ix + 1], tx)
	return lerpf(a, b, tz)


## Sum of brush weights (m^2) under a point, ignoring cells under `keep_out` (the player's feet).
func weight_sum(centre: Vector3, radius: float, keep_out: Vector3) -> float:
	var total := 0.0
	for iz in _range_z(centre, radius):
		for ix in _range_x(centre, radius):
			var d := Vector2(ix - HALF, iz - HALF).distance_to(Vector2(centre.x, centre.z))
			if d < radius and not _near(ix, iz, keep_out):
				total += 0.5 + 0.5 * cos(PI * d / radius)
	return total


## Raise (dh > 0) or lower (dh < 0) the ground under a point. Returns the volume moved (m^3, signed).
## `ceiling` (optional, Callable(x, z) -> float) caps how high a pull may raise each cell.
func brush(centre: Vector3, radius: float, dh: float, keep_out: Vector3, floor_h: float = MIN_H, ceiling: Callable = Callable()) -> float:
	var moved := 0.0
	for iz in _range_z(centre, radius):
		for ix in _range_x(centre, radius):
			var d := Vector2(ix - HALF, iz - HALF).distance_to(Vector2(centre.x, centre.z))
			if d >= radius or _near(ix, iz, keep_out):
				continue
			var i: int = iz * N + ix
			var wgt := 0.5 + 0.5 * cos(PI * d / radius)
			var before := h[i]
			var after := clampf(before + dh * wgt, minf(floor_h, before), MAX_H)
			if ceiling.is_valid():
				after = minf(after, maxf(before, float(ceiling.call(ix - HALF, iz - HALF))))
			if dh > 0.0 and after <= before:
				continue
			h[i] = after
			moved += after - before
			if dh > 0.0:
				mark[i] = maxf(mark[i], wgt)
			else:
				mark[i] = maxf(mark[i], wgt * 0.6)
	if absf(moved) > 0.0:
		dirty = true
	if moved > 0.0:
		# the raw clay frays out into the moss round a pulled column's foot, not a cut line at its base
		var outer := radius * 1.8
		for iz in _range_z(centre, outer):
			for ix in _range_x(centre, outer):
				var d := Vector2(ix - HALF, iz - HALF).distance_to(Vector2(centre.x, centre.z))
				if d < outer:
					var i: int = iz * N + ix
					mark[i] = maxf(mark[i], 0.45 * (0.5 + 0.5 * cos(PI * d / outer)))
	return moved


## Largest-height value in a rectangle (used by objective checks).
func max_in(x0: float, x1: float, z0: float, z1: float) -> float:
	var best := -99.0
	for iz in range(int(z0 + HALF), int(z1 + HALF) + 1):
		for ix in range(int(x0 + HALF), int(x1 + HALF) + 1):
			if ix >= 0 and iz >= 0 and ix < N and iz < N:
				best = maxf(best, h[iz * N + ix])
	return best


## Apply queued changes: upload the heights and marks for the shader and rebuild the collision
## map. Called on the world beat.
func flush() -> void:
	if not dirty:
		return
	dirty = false
	var hm := PackedFloat32Array()
	hm.resize(N * N * 2)
	for i in N * N:
		hm[i * 2] = h[i]
		hm[i * 2 + 1] = mark[i]
	var img := Image.create_from_data(N, N, false, Image.FORMAT_RGF, hm.to_byte_array())
	if _tex == null:
		_tex = ImageTexture.create_from_image(img)
		(_mesh_inst.material_override as ShaderMaterial).set_shader_parameter(&"heightmap", _tex)
	else:
		_tex.update(img)
	_shape.map_data = h


## The flat render grid (the shader lifts it), built once.
func _grid_mesh() -> ArrayMesh:
	var m := (N - 1) * RES + 1
	var verts := PackedVector3Array()
	verts.resize(m * m)
	for iz in m:
		for ix in m:
			verts[iz * m + ix] = Vector3(float(ix) / RES - HALF, 0.0, float(iz) / RES - HALF)
	var idx := PackedInt32Array()
	idx.resize((m - 1) * (m - 1) * 6)
	var k := 0
	for iz in m - 1:
		for ix in m - 1:
			var a := iz * m + ix
			idx[k] = a; idx[k + 1] = a + 1; idx[k + 2] = a + m
			idx[k + 3] = a + 1; idx[k + 4] = a + m + 1; idx[k + 5] = a + m
			k += 6
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.custom_aabb = AABB(Vector3(-HALF, MIN_H - 1.0, -HALF), Vector3(HALF * 2.0, MAX_H - MIN_H + 2.0, HALF * 2.0))
	return mesh


func _near(ix: int, iz: int, p: Vector3) -> bool:
	return p != Vector3.INF and Vector2(ix - HALF, iz - HALF).distance_to(Vector2(p.x, p.z)) < 0.9


func _range_x(c: Vector3, r: float) -> Array:
	return range(clampi(int(floor(c.x - r + HALF)), 0, N - 1), clampi(int(ceil(c.x + r + HALF)), 0, N - 1) + 1)


func _range_z(c: Vector3, r: float) -> Array:
	return range(clampi(int(floor(c.z - r + HALF)), 0, N - 1), clampi(int(ceil(c.z + r + HALF)), 0, N - 1) + 1)
