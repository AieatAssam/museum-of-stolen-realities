extends StaticBody3D
## A taut silk line between two points. Walkable as a tightrope (a narrow box collider on the
## world layer), caught as a zip-membrane when sloped, and plucked like a harp string: its pitch
## follows its length (f ∝ 1/L at constant tension), which is what resonance locks listen for.
## Built by silk_mode.gd (secondary at two anchors) or by the wing for pre-strung harp lines.

const WIDTH := 0.5
const REF_LENGTH := 8.0  # the length that plucks at pitch 1.0

var a: Vector3
var b: Vector3
var length: float = 0.0
var _mesh: MeshInstance3D
var _pluck_t: float = 0.0


static func create(parent: Node, pa: Vector3, pb: Vector3, mat: Material = null) -> Node:
	var s: Node = (load("res://wings/chitin/strand.gd") as GDScript).new()
	s.name = "Strand"
	parent.add_child(s)
	s.call("setup", pa, pb, mat)
	return s


func setup(pa: Vector3, pb: Vector3, mat: Material) -> void:
	a = pa
	b = pb
	length = a.distance_to(b)
	add_to_group(&"silk_strands")
	set_meta(&"surface", "silk")
	var mid := (a + b) * 0.5
	var dir := (b - a) / maxf(length, 0.001)
	var side := dir.cross(Vector3.UP)
	if side.length() < 0.01:
		side = Vector3.RIGHT
	side = side.normalized()
	var upv := side.cross(dir).normalized()
	global_transform = Transform3D(Basis(side, upv, -dir), mid)
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(WIDTH, 0.12, length)
	cs.shape = box
	add_child(cs)
	_mesh = MeshInstance3D.new()
	_mesh.name = "SilkLine"
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.03
	cyl.bottom_radius = 0.03
	cyl.height = length
	cyl.radial_segments = 8
	cyl.rings = clampi(int(length * 3.0), 8, 96)  # enough rings to bend for the sag and the shiver
	_mesh.mesh = cyl
	_mesh.rotation_degrees.x = 90.0
	if mat == null:
		mat = _silk_mat()
	_mesh.material_override = mat
	_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# a walkable line sags a hand's width at most, so her feet stay on it; harps sag a little more
	_mesh.set_instance_shader_parameter(&"len", length)
	_mesh.set_instance_shader_parameter(&"sag", minf(0.006 * length, 0.07))
	_mesh.set_instance_shader_parameter(&"pitch", pitch())
	_mesh.set_instance_shader_parameter(&"beads", length * 1.6)
	add_child(_mesh)


## Pitch of a pluck: 1.0 at REF_LENGTH, higher for shorter lines.
func pitch() -> float:
	return clampf(REF_LENGTH / maxf(length, 0.5), 0.3, 4.0)


func slope_deg() -> float:
	var d := (b - a).normalized()
	return rad_to_deg(asin(clampf(absf(d.y), 0.0, 1.0)))


func closest(p: Vector3) -> Vector3:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 0.0001), 0.0, 1.0)
	return a + ab * t


## Distance from a ray (origin, unit dir, max range) to this segment; returns [distance, along_ray].
func ray_distance(o: Vector3, d: Vector3, rng: float) -> Array:
	var best := INF
	var along := INF
	for i: int in 17:
		var q := a.lerp(b, float(i) / 16.0)
		var t := clampf((q - o).dot(d), 0.0, rng)
		var dist := (o + d * t).distance_to(q)
		if dist < best:
			best = dist
			along = t
	return [best, along]


func pluck() -> void:
	_pluck_t = 0.6


static func _silk_mat() -> Material:
	return load("res://wings/chitin/materials/silk_line.tres")


func _process(delta: float) -> void:
	if _pluck_t > 0.0:
		_pluck_t = maxf(_pluck_t - delta, 0.0)
		_mesh.set_instance_shader_parameter(&"pluck", _pluck_t / 0.6)
