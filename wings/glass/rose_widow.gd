extends Node3D
## THE ROSE WIDOW — the set-piece. Lightwalking turned on the player.
##
## Phase 1 (her light): the hall has no floor. Six petals of coloured light turn slowly around her
## tear (the central boss) and breathe in and out with her grief. A leaded floor tile exists only
## while her colour falls on its centre — `lit()` is the single source of truth, evaluated the same
## way here (collision) and in rose_tile.gdshader (what you see).
## Phase 2 (dark): she goes out. Vesper carries the last of her light in a lantern; only tiles of the
## old processional path, and only within the lantern's shrinking radius, are real. Sconces relight it.
## Phase 3 (done): the path stays, faintly, as the way she was crossed.

signal reached_dais
signal crossed
signal phase_changed(phase: int)

const TILE := 1.5
const PETALS := 6
const HALF_WIDTH := 0.31
const EDGE := 0.035
const OMEGA := 0.11
const R_IN := 4.0
const R_MAX := 23.2
const R_MIN := 11.5
const LANTERN_MAX := 4.6
const LANTERN_MIN := 1.7
const LANTERN_FADE := 75.0
const PETAL_COLORS := [Color("b22242"), Color("e8b54a"), Color("2b54c9"), Color("1a7a5e"), Color("8a3fd1"), Color("e8b54a")]

var phase: int = 1
var t: float = 0.0
var lantern_pos: Vector3 = Vector3(1e5, 0, 1e5)
var lantern_r: float = LANTERN_MAX
var lantern_age: float = 0.0
var path: PackedVector3Array = PackedVector3Array()   # local, y = 0
var sconces: PackedVector3Array = PackedVector3Array()  # local
var bridge: PackedVector3Array = PackedVector3Array()  # local, phase-3 link from the balcony

var _tiles: PackedVector3Array = PackedVector3Array()  # local centres
var _kind: PackedByteArray = PackedByteArray()          # 1 = path, 2 = bridge
var _solid: PackedByteArray = PackedByteArray()
var _shapes: Array[CollisionShape3D] = []
var _mm: MultiMeshInstance3D
var mat: ShaderMaterial
var _active: bool = true


static func breath_period() -> float:
	return 2.0 * (TAU / PETALS) / OMEGA


static func r_out_at(time: float) -> float:
	return R_MIN + (R_MAX - R_MIN) * (0.5 + 0.5 * cos(TAU * time / breath_period()))


## 0..1 how strongly her light falls on local floor point `p` at `time` (phase 1).
static func lit_at(p: Vector3, time: float) -> float:
	var r := Vector2(p.x, p.z).length()
	if r < R_IN:
		return 1.0
	var a := atan2(p.z, p.x) - OMEGA * time
	var seg := TAU / PETALS
	a = fposmod(a + seg * 0.5, seg) - seg * 0.5
	var ang := smoothstep(HALF_WIDTH + EDGE, HALF_WIDTH - EDGE, absf(a))
	var rad := smoothstep(r_out_at(time) + 0.6, r_out_at(time) - 0.6, r)
	return ang * rad


static func petal_index(p: Vector3, time: float) -> int:
	var a := atan2(p.z, p.x) - OMEGA * time
	return posmod(int(round(a / (TAU / PETALS))), PETALS)


func build(tile_mesh: Mesh, shader: Shader) -> void:
	var body := StaticBody3D.new()
	body.name = "Tiles"
	body.collision_layer = 1 << 4
	body.collision_mask = 0
	body.set_meta(&"surface", "glass")
	add_child(body)
	var box := BoxShape3D.new()
	box.size = Vector3(TILE * 0.98, 0.4, TILE * 0.98)
	var n := int(ceil(R_MAX / TILE)) + 1
	for ix in range(-n, n + 1):
		for iz in range(-n, n + 1):
			var c := Vector3(ix * TILE, 0, iz * TILE)
			var r := Vector2(c.x, c.z).length()
			if r < R_IN - 0.2 or r > R_MAX + 0.4:
				continue
			_tiles.append(c)
			_kind.append(_path_kind(c))
			_solid.append(0)
			var cs := CollisionShape3D.new()
			cs.shape = box
			cs.position = c - Vector3(0, 0.2, 0)
			cs.disabled = true
			body.add_child(cs)
			_shapes.append(cs)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = tile_mesh
	mm.instance_count = _tiles.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = 214
	for i in _tiles.size():
		mm.set_instance_transform(i, Transform3D(Basis.IDENTITY, _tiles[i]))
		mm.set_instance_custom_data(i, Color(float(_kind[i]), rng.randf(), rng.randf(), 0))
	_mm = MultiMeshInstance3D.new()
	_mm.multimesh = mm
	_mm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mat = ShaderMaterial.new()
	mat.shader = shader
	_mm.material_override = mat
	add_child(_mm)
	_push_uniforms()


func _path_kind(c: Vector3) -> int:
	for i in path.size() - 1:
		if Geometry3D.get_closest_point_to_segment(c, path[i], path[i + 1]).distance_to(c) < 1.15:
			return 1
	for i in bridge.size() - 1:
		if Geometry3D.get_closest_point_to_segment(c, bridge[i], bridge[i + 1]).distance_to(c) < 0.9:
			return 2
	return 0


func set_phase(p: int) -> void:
	phase = p
	if p == 2:
		lantern_r = LANTERN_MAX
		lantern_age = 0.0
	_push_uniforms()
	phase_changed.emit(p)


func set_active(on: bool) -> void:
	_active = on
	_mm.visible = on


func solid_at_local(p: Vector3) -> bool:
	match phase:
		1:
			return lit_at(p, t) >= 0.5
		2:
			return _nearest_kind(p) == 1 and Vector2(p.x - lantern_pos.x, p.z - lantern_pos.z).length() < lantern_r
		3:
			return _nearest_kind(p) != 0
	return false


func _nearest_kind(p: Vector3) -> int:
	var ix := roundi(p.x / TILE)
	var iz := roundi(p.z / TILE)
	var c := Vector3(ix * TILE, 0, iz * TILE)
	var i := _tiles.find(c)
	return _kind[i] if i >= 0 else 0


func _tile_solid(i: int) -> bool:
	var c := _tiles[i]
	match phase:
		1:
			return lit_at(c, t) >= 0.5
		2:
			return _kind[i] == 1 and Vector2(c.x - lantern_pos.x, c.z - lantern_pos.z).length() < lantern_r
		3:
			return _kind[i] != 0
	return false


func _physics_process(delta: float) -> void:
	if not _active:
		return
	var dt := delta * Game.world_time_scale
	if phase == 1:
		t += dt
	elif phase == 2:
		lantern_age += dt
		lantern_r = lerpf(LANTERN_MAX, LANTERN_MIN, clampf(lantern_age / LANTERN_FADE, 0.0, 1.0))
		for s in sconces:
			if lantern_pos.distance_to(s) < 2.2 and lantern_age > 1.0:
				lantern_age = 0.0
				Audio.sfx(load("res://wings/glass/audio/beam_touch.ogg"), to_global(s), 0.0, 0.5, 0.7)
	for i in _tiles.size():
		var on := 1 if _tile_solid(i) else 0
		if on != _solid[i]:
			_solid[i] = on
			_shapes[i].disabled = on == 0
	_push_uniforms()


func _push_uniforms() -> void:
	if mat == null:
		return
	mat.set_shader_parameter(&"rose_t", t)
	mat.set_shader_parameter(&"phase", phase)
	mat.set_shader_parameter(&"lantern_pos", lantern_pos)
	mat.set_shader_parameter(&"lantern_r", lantern_r)
	mat.set_shader_parameter(&"centre", global_position)
	mat.set_shader_parameter(&"petals", float(PETALS))
	mat.set_shader_parameter(&"half_width", HALF_WIDTH)
	mat.set_shader_parameter(&"edge", EDGE)
	mat.set_shader_parameter(&"omega", OMEGA)
	mat.set_shader_parameter(&"r_in", R_IN)
	mat.set_shader_parameter(&"r_out", r_out_at(t))


## Seconds from `time` until a petal next lies across `angle` (radians, world-local) while she is
## exhaled to at least `need_r`. Tests use it; so could a patient player.
static func next_window(time: float, angle: float, need_r: float) -> float:
	var step := 0.05
	var s := 0.0
	while s < 60.0:
		var tt := time + s
		var a := angle - OMEGA * tt
		var seg := TAU / PETALS
		a = fposmod(a + seg * 0.5, seg) - seg * 0.5
		if absf(a) < HALF_WIDTH * 0.35 and r_out_at(tt) >= need_r:
			return s
		s += step
	return -1.0
