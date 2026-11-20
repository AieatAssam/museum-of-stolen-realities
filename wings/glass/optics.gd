class_name GlassOptics
extends Node3D
## LIGHTWALKING — the Vitrine Kingdom's one rule, as physics.
##
## Every physics tick each light Source is ray-traced through the optics layer: Mirrors reflect,
## Filters tint (light AND glass), Prisms split light into its colours, Lenses add colours together
## (one tick late), and Receptors (saints' panes, gates, reliquaries, the east window) record the
## exact colour that reaches them. Every traced segment becomes a SOLID, walkable slab of light
## (StaticBody3D on the wing_solid layer — a re-aimed beam never flings you, wider than it looks: generous edge forgiveness).
## Light steeper than WALK_SLOPE cannot be stood on; it is a shaft, not a bridge.
##
## Colours are 3-bit masks: RED | GOLD | BLUE. GOLD|BLUE = green, RED|BLUE = violet, all = white.

const RED := 1
const GOLD := 2
const BLUE := 4
const WHITE := 7
const OPTICS_LAYER := 1 << 6
const BEAM_LAYER := 1 << 4
const RAY_MASK := 1 | OPTICS_LAYER
const MAX_LEN := 95.0
const MAX_DEPTH := 10
const WALK_SLOPE := 47.0
const BEAM_W := 1.35        # collider width (visual is ~0.5 m): edge forgiveness
const BEAM_T := 0.45
const BEAM_LIFT := 0.06     # walk surface sits just above the light's axis

const COLORS := {
	0: Color(0, 0, 0),
	1: Color("d0283f"),
	2: Color("f2bd52"),
	4: Color("3563e0"),
	3: Color("f0742e"),
	5: Color("8a3fd1"),
	6: Color("1f9a73"),
	7: Color("fff1d2"),
}
const NAMES := {0: "dark", 1: "red", 2: "gold", 4: "blue", 3: "orange", 5: "violet", 6: "green", 7: "white"}

signal traced

var sources: Array = []
var elements: Array = []
var lenses: Array = []
var _segs: Array = []
var _used: int = 0
var _beam_shader: Shader = preload("res://wings/glass/shaders/beam.gdshader")
var _beam_mesh: Mesh
var _skin_mesh: PlaneMesh   # the walkable skin: unit length, stretched to each segment's collider
var _pool_mesh: PlaneMesh   # the soft pool where a walkable beam lands
var _mote_mesh: QuadMesh
var _flare_mat: Material


static func compat() -> bool:
	return RenderingServer.get_current_rendering_method() == "gl_compatibility"


static func color(mask: int) -> Color:
	return COLORS.get(mask, Color.WHITE)


static func dir_yaw(deg: float, pitch_deg: float = 0.0) -> Vector3:
	var y := deg_to_rad(deg)
	var p := deg_to_rad(pitch_deg)
	return Vector3(sin(y) * cos(p), sin(p), -cos(y) * cos(p))


## Normal a mirror at `pos` needs to send light arriving from `from` on to `to`.
static func mirror_normal(pos: Vector3, from: Vector3, to: Vector3) -> Vector3:
	var a := from.direction_to(pos)
	var b := pos.direction_to(to)
	return (b - a).normalized()


func _ready() -> void:
	var cm := CylinderMesh.new()
	cm.top_radius = 0.26
	cm.bottom_radius = 0.26
	cm.height = 1.0
	cm.radial_segments = 14
	cm.rings = 1
	cm.cap_top = false
	cm.cap_bottom = false
	_beam_mesh = cm
	var m := ShaderMaterial.new()
	m.shader = _beam_shader
	_beam_mesh.surface_set_material(0, m)
	_skin_mesh = PlaneMesh.new()
	_skin_mesh.size = Vector2(BEAM_W, 1.0)
	_skin_mesh.subdivide_depth = 0
	var skin_mat := ShaderMaterial.new()
	skin_mat.shader = preload("res://wings/glass/shaders/beam_walk.gdshader")
	skin_mat.set_shader_parameter(&"half_w", BEAM_W * 0.5)
	_skin_mesh.material = skin_mat
	_pool_mesh = PlaneMesh.new()
	_pool_mesh.size = Vector2(2.6, 2.6)
	var pool_mat := ShaderMaterial.new()
	pool_mat.shader = preload("res://wings/glass/shaders/beam_pool.gdshader")
	_pool_mesh.material = pool_mat
	var grad := Gradient.new()
	grad.colors = PackedColorArray([Color(1, 1, 1, 1), Color(0, 0, 0, 1)])  # additive: the fade is to black
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	var mm := StandardMaterial3D.new()
	mm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mm.vertex_color_use_as_albedo = true
	mm.albedo_texture = tex
	mm.disable_receive_shadows = true
	_mote_mesh = QuadMesh.new()
	_mote_mesh.size = Vector2(0.09, 0.09)
	_mote_mesh.material = mm


# --- registry -------------------------------------------------------------------------------

func add_source(s: Source) -> Source:
	sources.append(s)
	return s


func add_element(e: Element) -> Element:
	elements.append(e)
	if e is Lens:
		lenses.append(e)
	return e


# --- tracing ----------------------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	for e: Element in elements:
		e.acc = 0
	_used = 0
	for s: Source in sources:
		if s.on and s.mask != 0 and s.is_inside_tree():
			_trace(s.origin(), s.dir, s.mask, 0, s.exclude())
	for l: Lens in lenses:
		if l.prev != 0 and l.is_inside_tree():
			_trace(l.out_origin(), l.out_dir, l.prev, 0, [l.body.get_rid()])
	for e: Element in elements:
		e.settle(delta)
	for i in range(_used, _segs.size()):
		(_segs[i] as Segment).hide_seg()
	traced.emit()


func _trace(from: Vector3, dir: Vector3, mask: int, depth: int, exclude: Array) -> void:
	if depth > MAX_DEPTH or mask == 0:
		return
	var to := from + dir * MAX_LEN
	var q := PhysicsRayQueryParameters3D.create(from, to, RAY_MASK, exclude)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	var end: Vector3 = hit["position"] if hit else to
	_segment(from, end, mask)
	if not hit:
		return
	var col: Object = hit["collider"]
	if col == null or not col.has_meta(&"optic"):
		return
	var e: Element = col.get_meta(&"optic")
	e.receive(self, end, dir, mask, hit["normal"], depth)


## Elements call this to continue light.
func emit_ray(from: Vector3, dir: Vector3, mask: int, depth: int, exclude: Array) -> void:
	_trace(from, dir, mask, depth + 1, exclude)


func _segment(a: Vector3, b: Vector3, mask: int) -> void:
	if a.distance_to(b) < 0.05:
		return
	var s: Segment
	if _used < _segs.size():
		s = _segs[_used]
	else:
		s = Segment.new()
		s.setup(_beam_mesh, _skin_mesh, _pool_mesh, _mote_mesh)
		add_child(s)
		_segs.append(s)
	_used += 1
	s.set_seg(a, b, mask)


## Is a world point standing on (or within `r` of) any live beam of `mask` (0 = any)?
func beam_near(p: Vector3, r: float = 0.8, mask: int = 0) -> bool:
	for i in _used:
		var s: Segment = _segs[i]
		if mask != 0 and s.mask != mask:
			continue
		var c := Geometry3D.get_closest_point_to_segment(p, s.a, s.b)
		if c.distance_to(p) < r:
			return true
	return false


func live_segments() -> Array:
	return _segs.slice(0, _used)


# =============================================================================================
class Segment extends Node3D:
	var a: Vector3
	var b: Vector3
	var mask: int = 0
	var body: StaticBody3D
	var shape: ConvexPolygonShape3D
	var _shape_l := -1.0
	var col: CollisionShape3D
	var vis: MeshInstance3D
	var flare: OmniLight3D
	var _shown := true

	var skin: MeshInstance3D   # the walkable skin of light: exactly the collider's top face
	var pool: MeshInstance3D
	var motes: GPUParticles3D    # dust drifting in the shaft
	var skaters: GPUParticles3D  # motes that settle onto the skin and skate along it
	var _motes_pm: ParticleProcessMaterial
	var _skate_pm: ParticleProcessMaterial

	func setup(mesh: Mesh, skin_mesh: Mesh, pool_mesh: Mesh, mote_mesh: Mesh) -> void:
		skin = MeshInstance3D.new()
		skin.mesh = skin_mesh
		skin.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		skin.position.y = GlassOptics.BEAM_LIFT + 0.004
		add_child(skin)
		pool = MeshInstance3D.new()
		pool.mesh = pool_mesh
		pool.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(pool)
		motes = _particles(mote_mesh, 28, 5.0)
		_motes_pm = motes.process_material
		_motes_pm.direction = Vector3(0, 1, -0.3)
		_motes_pm.spread = 40.0
		_motes_pm.initial_velocity_min = 0.03
		_motes_pm.initial_velocity_max = 0.14
		skaters = _particles(mote_mesh, 16, 4.0)
		_skate_pm = skaters.process_material
		_skate_pm.direction = Vector3(0, 0.05, -1)
		_skate_pm.spread = 8.0
		_skate_pm.initial_velocity_min = 0.12
		_skate_pm.initial_velocity_max = 0.3
		_skate_pm.scale_min = 0.4
		_skate_pm.scale_max = 0.9

		vis = MeshInstance3D.new()
		vis.mesh = mesh
		if GlassOptics.compat():
			# Compatibility has no instance uniforms: each shaft carries its own material
			vis.material_override = ShaderMaterial.new()
			(vis.material_override as ShaderMaterial).shader = preload("res://wings/glass/shaders/beam_compat.gdshader")
		vis.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		vis.rotation.x = -PI / 2  # cylinder Y axis -> -Z
		var pivot := Node3D.new()
		pivot.name = "Vis"
		add_child(pivot)
		pivot.add_child(vis)
		body = StaticBody3D.new()
		body.collision_layer = GlassOptics.BEAM_LAYER
		body.collision_mask = 0
		body.set_meta(&"beam", true)
		body.set_meta(&"surface", "glass")
		col = CollisionShape3D.new()
		shape = ConvexPolygonShape3D.new()
		col.shape = shape
		body.add_child(col)
		add_child(body)
		flare = OmniLight3D.new()
		flare.omni_range = 4.5
		flare.light_energy = 1.6
		flare.light_volumetric_fog_energy = 0.0
		flare.shadow_enabled = false
		add_child(flare)

	func _particles(mote_mesh: Mesh, amount: int, life: float) -> GPUParticles3D:
		var g := GPUParticles3D.new()
		g.amount = amount
		g.lifetime = life
		g.local_coords = true
		g.draw_pass_1 = mote_mesh
		g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var pm := ParticleProcessMaterial.new()
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		pm.gravity = Vector3.ZERO
		pm.scale_min = 0.5
		pm.scale_max = 1.3
		var fade := Gradient.new()
		fade.colors = PackedColorArray([Color(0, 0, 0, 1), Color(1, 1, 1, 1), Color(0, 0, 0, 1)])
		fade.offsets = PackedFloat32Array([0.0, 0.3, 1.0])
		var ft := GradientTexture1D.new()
		ft.gradient = fade
		pm.color_ramp = ft
		g.process_material = pm
		add_child(g)
		return g

	## The light answers her weight: the skin's shader spreads a ripple from her feet.
	func _process(_delta: float) -> void:
		if not _shown or not skin.visible:
			return
		var p: Node3D = Game.player
		skin.set_instance_shader_parameter(&"foot", p.global_position if p else Vector3(0, -1000, 0))

	func _beam_param(p: StringName, v: Variant) -> void:
		if vis.material_override:
			(vis.material_override as ShaderMaterial).set_shader_parameter(p, v)
		else:
			vis.set_instance_shader_parameter(p, v)

	func set_seg(na: Vector3, nb: Vector3, nmask: int) -> void:
		if not _shown:
			_shown = true
			visible = true
		if na.is_equal_approx(a) and nb.is_equal_approx(b) and nmask == mask and body.collision_layer != 0:
			return
		var changed_shape := absf(na.distance_to(nb) - a.distance_to(b)) > 0.001
		a = na
		b = nb
		var colr := GlassOptics.color(nmask)
		if nmask != mask:
			mask = nmask
			_beam_param(&"beam_color", colr)
			flare.light_color = colr
		var d := a.direction_to(b)
		var length := a.distance_to(b)
		var up := Vector3.UP if absf(d.y) < 0.98 else Vector3.FORWARD
		var basis := Basis.looking_at(d, up)
		global_transform = Transform3D(basis, (a + b) * 0.5)
		var vis_pivot := get_node("Vis") as Node3D
		vis_pivot.scale = Vector3(1, 1, length)
		_beam_param(&"beam_len", length)
		flare.global_position = b - d * 0.4
		var slope := rad_to_deg(asin(clampf(absf(d.y), 0.0, 1.0)))
		var solid := slope < GlassOptics.WALK_SLOPE
		body.collision_layer = GlassOptics.BEAM_LAYER if solid else 0
		col.disabled = not solid
		skin.visible = solid
		pool.visible = solid
		motes.emitting = solid
		skaters.emitting = solid
		# a walkable beam is a fatter shaft (its own width), the skin laid across it; a steep shaft stays slim
		vis_pivot.scale = Vector3(2.3, 1.25, length) if solid else Vector3(1, 1, length)
		if solid:
			# trim the ends a little so the slab never pokes into the mirror/source it leaves
			var l := maxf(length - 0.3, 0.1)
			if changed_shape or absf(_shape_l - l) > 0.001:
				_set_shape(l)
			body.transform = Transform3D(Basis.IDENTITY, Vector3(0, GlassOptics.BEAM_LIFT - GlassOptics.BEAM_T * 0.5, 0))
			# the skin is the collider's top face: same width, same trimmed length, same height
			skin.scale = Vector3(1, 1, l)
			skin.set_instance_shader_parameter(&"beam_color", colr)
			skin.set_instance_shader_parameter(&"walk_len", l)
			pool.set_instance_shader_parameter(&"beam_color", colr)
			pool.position = Vector3(0, GlassOptics.BEAM_LIFT + 0.01, -length * 0.5 + 0.1)
			var tint := colr.lerp(Color.WHITE, 0.25)
			_motes_pm.emission_box_extents = Vector3(GlassOptics.BEAM_W * 0.4, 0.3, l * 0.5)
			_motes_pm.color = tint
			motes.visibility_aabb = AABB(Vector3(-1, -0.6, -l * 0.5 - 0.5), Vector3(2, 1.6, l + 1.0))
			motes.position = Vector3(0, 0.25, 0)
			_skate_pm.emission_box_extents = Vector3(GlassOptics.BEAM_W * 0.4, 0.01, l * 0.5)
			_skate_pm.color = tint
			skaters.visibility_aabb = AABB(Vector3(-1, -0.2, -l * 0.5 - 0.5), Vector3(2, 0.6, l + 1.0))
			skaters.position = Vector3(0, GlassOptics.BEAM_LIFT + 0.04, 0)
		body.set_meta(&"beam_a", a)
		body.set_meta(&"beam_b", b)
		body.set_meta(&"beam_mask", mask)

	## A flat walking top on a wider foot: all four sides slope at ~28 degrees, so a beam lying across
	## a floor can be walked onto from the side instead of being a 16 cm kerb the step-up won't take.
	func _set_shape(l: float) -> void:
		_shape_l = l
		var hw := GlassOptics.BEAM_W * 0.5
		var ht := GlassOptics.BEAM_T * 0.5
		var foot := hw + GlassOptics.BEAM_T / tan(deg_to_rad(28.0))
		var pts := PackedVector3Array()
		var run := foot - hw
		for sz: float in [-1.0, 1.0]:
			var zt := sz * l * 0.5
			var zb := sz * (l * 0.5 + run)
			pts.append_array([Vector3(-hw, ht, zt), Vector3(hw, ht, zt), Vector3(-foot, -ht, zb), Vector3(foot, -ht, zb)])
		shape.points = pts

	func hide_seg() -> void:
		if not _shown:
			return
		_shown = false
		visible = false
		body.collision_layer = 0
		col.disabled = true
		mask = -1
		a = Vector3.INF


# =============================================================================================
class Source extends Node3D:
	## A light: the sun through a window, a heliostat dial, a restored saint. Global position is
	## where the light leaves; `dir` is world space.
	var dir: Vector3 = Vector3.FORWARD
	var mask: int = GlassOptics.WHITE
	var on: bool = true
	var exclude_rids: Array = []

	func origin() -> Vector3:
		return global_position

	func exclude() -> Array:
		return exclude_rids


# =============================================================================================
class Element extends Node3D:
	## Anything light can strike. Owns a StaticBody3D on the optics layer (never collides with
	## Vesper). `lit` is the exact colour mask that reached it last tick.
	signal lit_changed(mask: int)
	var body: StaticBody3D
	var acc: int = 0
	var lit: int = 0

	func make_body(size: Vector3, offset: Vector3 = Vector3.ZERO, parent: Node3D = null) -> void:
		body = StaticBody3D.new()
		body.collision_layer = GlassOptics.OPTICS_LAYER
		body.collision_mask = 0
		body.set_meta(&"optic", self)
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = size
		cs.shape = bs
		cs.position = offset
		body.add_child(cs)
		(parent if parent else self).add_child(body)

	func receive(_o: Node, _at: Vector3, _dir: Vector3, mask: int, _n: Vector3, _depth: int) -> void:
		acc |= mask

	func settle(_delta: float) -> void:
		if acc != lit:
			lit = acc
			lit_changed.emit(lit)


class Mirror extends Element:
	## Polished silver on a gimbal. `normals` are the orientations it can be turned through.
	var normals: Array = []
	var index: int = 0
	var normal: Vector3 = Vector3.BACK
	var head: Node3D
	var _tw: Tween

	var _hit: MeshInstance3D

	func setup(face_size: Vector2 = Vector2(1.5, 1.5)) -> void:
		head = Node3D.new()
		head.name = "Head"
		add_child(head)
		make_body(Vector3(face_size.x, face_size.y, 0.12), Vector3.ZERO, head)
		# the glow over the face: lit only while light reaches it, so a struck mirror reads at a glance
		_hit = MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2.ONE * face_size.x * 1.5
		_hit.mesh = q
		_hit.material_override = ShaderMaterial.new()
		(_hit.material_override as ShaderMaterial).shader = preload("res://wings/glass/shaders/hit_glow.gdshader")
		_hit.position = Vector3(0, 0, 0.07)
		_hit.visible = false
		head.add_child(_hit)
		normal = normals[index]
		_orient(normal)

	func _orient(n: Vector3) -> void:
		normal = n.normalized()
		var up := Vector3.UP if absf(normal.y) < 0.97 else Vector3.FORWARD
		head.global_basis = Basis.looking_at(-normal, up)

	func settle(delta: float) -> void:
		super.settle(delta)
		var lit_now := lit != 0
		_hit.visible = lit_now
		if lit_now:
			var hm := _hit.material_override as ShaderMaterial
			hm.set_shader_parameter(&"glow_color", GlassOptics.color(lit))
			hm.set_shader_parameter(&"strength", 1.2)

	func turn() -> void:
		set_index((index + 1) % normals.size())

	func set_index(i: int, instant: bool = false) -> void:
		index = i
		var from := normal
		var to: Vector3 = normals[i]
		if _tw:
			_tw.kill()
		if instant or not is_inside_tree():
			_orient(to)
			return
		_tw = create_tween()
		_tw.tween_method(func(u: float) -> void: _orient(from.slerp(to, u)), 0.0, 1.0, 0.6) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

	func receive(o: Node, at: Vector3, dir: Vector3, mask: int, _n: Vector3, depth: int) -> void:
		acc |= mask
		if dir.dot(normal) >= 0.0:
			return  # struck from behind: the lead backing swallows it
		var r := dir - 2.0 * normal * dir.dot(normal)
		o.emit_ray(at, r.normalized(), mask, depth, [body.get_rid()])


class Filter extends Element:
	## A coloured pane: light passes through and leaves as (light AND glass).
	var glass: int = GlassOptics.RED

	func receive(o: Node, at: Vector3, dir: Vector3, mask: int, _n: Vector3, depth: int) -> void:
		acc |= mask
		var m := mask & glass
		if m != 0:
			o.emit_ray(at + dir * 0.02, dir, m, depth, [body.get_rid()])


class Prism extends Element:
	## Splits whatever reaches it into its colours: red fans left, gold straight on, blue right.
	var yaws: Array = [0.0]
	var index: int = 0
	var yaw: float = 0.0
	var spread: float = 35.0
	var head: Node3D
	var _tw: Tween

	func setup() -> void:
		head = Node3D.new()
		head.name = "Head"
		add_child(head)
		make_body(Vector3(1.3, 0.7, 1.3), Vector3.ZERO, self)
		yaw = yaws[index]
		head.rotation.y = -deg_to_rad(yaw)

	func out_dir(bit: int) -> Vector3:
		var off := -spread if bit == GlassOptics.RED else (spread if bit == GlassOptics.BLUE else 0.0)
		return GlassOptics.dir_yaw(yaw + off)

	func turn() -> void:
		set_index((index + 1) % yaws.size())

	func set_index(i: int, instant: bool = false) -> void:
		index = i
		var from := yaw
		var to: float = yaws[i]
		while to - from > 180.0:
			to -= 360.0
		while to - from < -180.0:
			to += 360.0
		if _tw:
			_tw.kill()
		if instant or not is_inside_tree():
			yaw = to
			head.rotation.y = -deg_to_rad(yaw)
			return
		_tw = create_tween()
		_tw.tween_method(func(v: float) -> void:
			yaw = v
			head.rotation.y = -deg_to_rad(v), from, to, 0.7).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

	func receive(o: Node, _at: Vector3, _dir: Vector3, mask: int, _n: Vector3, depth: int) -> void:
		acc |= mask
		for bit: int in [GlassOptics.RED, GlassOptics.GOLD, GlassOptics.BLUE]:
			if mask & bit:
				var d := out_dir(bit)
				o.emit_ray(global_position + d * 0.75, d, bit, depth, [body.get_rid()])


class Lens extends Element:
	## The bishop's lens: every colour that strikes it this tick leaves, added together, next tick.
	var out_dir: Vector3 = Vector3.FORWARD
	var prev: int = 0

	func out_origin() -> Vector3:
		return global_position + out_dir * 0.7

	func settle(delta: float) -> void:
		prev = acc
		super.settle(delta)


class Receptor extends Element:
	## Records the exact colour that reaches it; `satisfied` fires once after `want` has held for
	## `hold` seconds (want = -1: any light).
	signal satisfied
	var want: int = GlassOptics.WHITE
	var hold: float = 0.8
	var done: bool = false
	var held: float = 0.0

	func settle(delta: float) -> void:
		super.settle(delta)
		if done:
			return
		var ok := lit != 0 and (want < 0 or lit == want)
		held = held + delta if ok else 0.0
		if held >= hold:
			done = true
			satisfied.emit()

	func matches() -> bool:
		return lit != 0 and (want < 0 or lit == want)
