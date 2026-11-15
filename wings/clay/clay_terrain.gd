class_name ClayTerrain
extends Node3D
## Deformable clay ground: an 80 m square heightfield on 1 m cells, centred on the wing origin.
## Edits are queued while the player holds a verb and applied on the next world beat, so the
## ground only changes on twos. Collision (HeightMapShape3D) and the visible mesh rebuild together
## in flush(), and only when something changed.

const N := 81
const HALF := 40.0
const MIN_H := -2.4
const MAX_H := 4.2
const MATERIAL := preload("res://wings/clay/materials/ground.tres")

var h := PackedFloat32Array()     # index = iz * N + ix, world x = ix - HALF, z = iz - HALF
var mark := PackedFloat32Array()  # 0..1: shaped by the player (raw clay, fingerprints show)
var dirty: bool = false
var _mesh_inst: MeshInstance3D
var _body: StaticBody3D
var _shape: HeightMapShape3D


func setup(base_fn: Callable) -> void:
	h.resize(N * N)
	mark.resize(N * N)
	for iz in N:
		for ix in N:
			h[iz * N + ix] = float(base_fn.call(ix - HALF, iz - HALF))
	mark.fill(0.0)
	_mesh_inst = MeshInstance3D.new()
	_mesh_inst.material_override = MATERIAL
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
func brush(centre: Vector3, radius: float, dh: float, keep_out: Vector3, floor_h: float = MIN_H) -> float:
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
	return moved


## Largest-height value in a rectangle (used by objective checks).
func max_in(x0: float, x1: float, z0: float, z1: float) -> float:
	var best := -99.0
	for iz in range(int(z0 + HALF), int(z1 + HALF) + 1):
		for ix in range(int(x0 + HALF), int(x1 + HALF) + 1):
			if ix >= 0 and iz >= 0 and ix < N and iz < N:
				best = maxf(best, h[iz * N + ix])
	return best


## Apply queued changes: rebuild the mesh and the collision map. Called on the world beat.
func flush() -> void:
	if not dirty:
		return
	dirty = false
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var uvs := PackedVector2Array()
	var cols := PackedColorArray()
	verts.resize(N * N)
	norms.resize(N * N)
	uvs.resize(N * N)
	cols.resize(N * N)
	for iz in N:
		for ix in N:
			var i: int = iz * N + ix
			var hl := h[iz * N + maxi(ix - 1, 0)]
			var hr := h[iz * N + mini(ix + 1, N - 1)]
			var hd := h[maxi(iz - 1, 0) * N + ix]
			var hu := h[mini(iz + 1, N - 1) * N + ix]
			var wx := ix - HALF
			var wz := iz - HALF
			verts[i] = Vector3(wx, h[i], wz)
			norms[i] = Vector3(hl - hr, 2.0, hd - hu).normalized()
			uvs[i] = Vector2(wx, wz)
			cols[i] = Color(mark[i], 0.0, 0.0, 1.0)
	var idx := PackedInt32Array()
	idx.resize((N - 1) * (N - 1) * 6)
	var k := 0
	for iz in N - 1:
		for ix in N - 1:
			var a := iz * N + ix
			var b := a + 1
			var c := a + N
			var d := c + 1
			idx[k] = a; idx[k + 1] = b; idx[k + 2] = c
			idx[k + 3] = b; idx[k + 4] = d; idx[k + 5] = c
			k += 6
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_mesh_inst.mesh = mesh
	_shape.map_data = h


func _near(ix: int, iz: int, p: Vector3) -> bool:
	return p != Vector3.INF and Vector2(ix - HALF, iz - HALF).distance_to(Vector2(p.x, p.z)) < 0.9


func _range_x(c: Vector3, r: float) -> Array:
	return range(clampi(int(floor(c.x - r + HALF)), 0, N - 1), clampi(int(ceil(c.x + r + HALF)), 0, N - 1) + 1)


func _range_z(c: Vector3, r: float) -> Array:
	return range(clampi(int(floor(c.z - r + HALF)), 0, N - 1), clampi(int(ceil(c.z + r + HALF)), 0, N - 1) + 1)
