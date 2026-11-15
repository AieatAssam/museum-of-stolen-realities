extends AnimatableBody3D
## One brushstroke of the Unfinished Wing. A polyline of TOP-SURFACE centre points (local space),
## swept into a ridged ribbon (child "Visual") with one oriented box collider per segment
## (children "Col_<n>": collision is kept separate from the mesh for the art pass).
## Wet strokes are rails (surf_mode.gd samples them by arc length). `upright` strokes are walls:
## their points are the base line and the ribbon stands `width` metres tall.
## The plain-JSON record `rec` is what canvas.gd saves for strokes the player lays.

const RIDGE := 0.12
const KICK_H := 0.55
## Greybox function colours. Paint keeps its own hue (it IS the function in this wing).
const COLOURS := {
	"blue": Color("2a4fd6"), "red": Color("e2452b"), "yellow": Color("f2c230"),
	"green": Color("3c9a3a"), "violet": Color("6b34a8"), "orange": Color("f08a1c"),
	"umber": Color("5a3a24"), "fury": Color("3a0d12"), "pencil": Color("4a4a50"),
	"white": Color("f4efe4"), "dry": Color("a99c86"),
}
const HOT := ["red", "orange"]
const LIGHT := ["yellow", "orange"]

static var _mats: Dictionary = {}

var sid: String = ""
var rec: Dictionary = {}
var pts := PackedVector3Array()
var lens := PackedFloat32Array()
var length: float = 0.0
var width: float = 2.0
var thick: float = 0.5
var colour: String = "blue"
var upright: bool = false
## "" | "well" (infinite source) | "pencil" (underdrawing, needs light) | "seal" (Pentimento layer)
## | "fixed" (cannot be scraped) | "trunk" (never a rail)
var kind: String = ""
var wet: bool = true
var laid: bool = false
var kicks := PackedFloat32Array()   # arc positions of impasto ridges (jump here for height)
var under: Array = []                # stroke ids revealed when this one is scraped away
var enabled: bool = true
var dry: float = 0.0                 # 0 wet .. 1 hardened (heist)
var visual: MeshInstance3D
var _cols: Array[CollisionShape3D] = []
var _own_mat: ShaderMaterial


## Art palette: [body, ridge highlight, groove, glow, rim]. Separated by VALUE as well as hue so
## each colour reads at 30 m: yellow brightest, then white, red, green, blue, violet, umber, fury.
const PALETTE := {
	"blue": [Color(0.05, 0.13, 0.78), Color(0.55, 0.74, 1.0), Color(0.02, 0.04, 0.32), 0.0, 0.7],
	"red": [Color(0.92, 0.12, 0.05), Color(1.0, 0.58, 0.28), Color(0.45, 0.02, 0.03), 0.0, 0.6],
	"yellow": [Color(1.0, 0.78, 0.08), Color(1.0, 0.96, 0.62), Color(0.82, 0.48, 0.04), 0.55, 0.5],
	"green": [Color(0.12, 0.58, 0.20), Color(0.62, 0.88, 0.32), Color(0.02, 0.24, 0.14), 0.0, 0.6],
	"violet": [Color(0.40, 0.14, 0.70), Color(0.78, 0.56, 0.98), Color(0.16, 0.03, 0.34), 0.0, 0.6],
	"orange": [Color(1.0, 0.42, 0.04), Color(1.0, 0.82, 0.42), Color(0.62, 0.14, 0.02), 0.4, 0.5],
	"umber": [Color(0.34, 0.19, 0.09), Color(0.68, 0.44, 0.26), Color(0.13, 0.06, 0.04), 0.0, 0.35],
	"fury": [Color(0.38, 0.03, 0.07), Color(0.78, 0.16, 0.14), Color(0.10, 0.0, 0.02), 0.0, 0.5],
	"pencil": [Color(0.32, 0.32, 0.36), Color(0.62, 0.62, 0.66), Color(0.14, 0.14, 0.17), 0.0, 0.15],
	"white": [Color(0.96, 0.93, 0.86), Color(1.0, 1.0, 1.0), Color(0.70, 0.66, 0.78), 0.0, 0.3],
}
const WET_SHADER := "res://wings/paint/shaders/wet_stroke.gdshader"
const STROKE_N := "res://wings/paint/textures/paint_stroke_normal.png"
const STROKE_A := "res://wings/paint/textures/paint_stroke_albedo.png"


static func mat_for(c: String) -> ShaderMaterial:
	if _mats.has(c):
		return _mats[c]
	var m := ShaderMaterial.new()
	m.shader = load(WET_SHADER)
	m.set_shader_parameter(&"stroke_normal", load(STROKE_N))
	m.set_shader_parameter(&"stroke_albedo", load(STROKE_A))
	_paint(m, c)
	_mats[c] = m
	return m


static func _paint(m: ShaderMaterial, c: String) -> void:
	var p: Array = PALETTE.get(c, PALETTE["white"])
	m.set_shader_parameter(&"colour", p[0])
	m.set_shader_parameter(&"hi", p[1])
	m.set_shader_parameter(&"lo", p[2])
	m.set_shader_parameter(&"glow", p[3])
	m.set_shader_parameter(&"rim", p[4])
	m.set_shader_parameter(&"flow", 0.0 if c == "pencil" else 0.04)


## The rider's wake, pressed into every wet colour (and any drying copy) at once.
static func set_rider(pos: Vector3, strength: float, extra: Material = null) -> void:
	var v := Vector4(pos.x, pos.y, pos.z, strength)
	for m: ShaderMaterial in _mats.values():
		m.set_shader_parameter(&"rider", v)
	if extra is ShaderMaterial and not _mats.values().has(extra):
		(extra as ShaderMaterial).set_shader_parameter(&"rider", v)


static func pack(v: PackedVector3Array) -> Array:
	var out: Array = []
	for p in v:
		out.append_array([snappedf(p.x, 0.001), snappedf(p.y, 0.001), snappedf(p.z, 0.001)])
	return out


static func unpack(flat: Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	for i in range(0, flat.size() - 2, 3):
		out.append(Vector3(flat[i], flat[i + 1], flat[i + 2]))
	return out


## Record helper. `p` world points (the stroke is added under a parent at the origin).
static func make(id: String, p: Array, c: String, w: float = 2.0, extra: Dictionary = {}) -> Dictionary:
	var v := PackedVector3Array()
	for q: Vector3 in p:
		v.append(q)
	var r := {"id": id, "p": pack(v), "c": c, "w": w}
	r.merge(extra, true)
	return r


static func is_hot(c: String) -> bool:
	return c in HOT


static func is_light(c: String) -> bool:
	return c in LIGHT


func _init() -> void:
	sync_to_physics = false
	collision_layer = 1
	collision_mask = 0


func setup(r: Dictionary) -> Node3D:
	rec = r
	sid = String(r["id"])
	name = sid.validate_node_name()
	pts = unpack(r["p"])
	width = float(r.get("w", 2.0))
	thick = float(r.get("t", 0.5))
	colour = String(r.get("c", "blue"))
	upright = bool(r.get("up", false))
	kind = String(r.get("k", ""))
	laid = bool(r.get("laid", false))
	under = r.get("under", [])
	kicks = PackedFloat32Array(r.get("kicks", []))
	wet = kind != "pencil" and kind != "trunk" and not upright
	set_meta(&"stroke", true)
	set_meta(&"surface", "paint")
	_measure()
	_build()
	return self


func _measure() -> void:
	lens = PackedFloat32Array([0.0])
	for i in range(1, pts.size()):
		lens.append(lens[i - 1] + pts[i].distance_to(pts[i - 1]))
	length = lens[lens.size() - 1]


func _frame(i: int) -> Array:
	var n := pts.size()
	var t := (pts[mini(i + 1, n - 1)] - pts[maxi(i - 1, 0)]).normalized()
	var side := Vector3.UP.cross(t)
	if side.length() < 0.2:
		side = Vector3.RIGHT
	side = side.normalized()
	var nrm := t.cross(side).normalized()
	if upright:
		return [t, Vector3.UP, -side]  # tangent, across (up the wall), wall normal
	return [t, side, nrm]


func _kick_bump(s: float) -> float:
	var b := 0.0
	for k in kicks:
		b = maxf(b, 1.0 - absf(s - k) / 1.2)
	return b * KICK_H


## A deterministic 0..1 hash for this stroke (edge raggedness, drips, bristle phase).
func _h(x: float) -> float:
	return fposmod(sin(x * 12.9898 + float(sid.hash() % 1000) * 0.731) * 43758.5453, 1.0)


## Visual only: the stroke is swept as a closed body of paint along the centreline, resampled every
## half metre. Its top is a ridged profile with bristle grooves (UV.x runs along in widths, UV.y
## across the top 0..1), the head is loaded and round, the tail drags thin, and wet strokes drip
## off their edges. Collision stays one box per authored segment (Col_<n>), exactly as before.
func _build() -> void:
	for c in _cols:
		c.queue_free()
	_cols.clear()
	if visual:
		visual.queue_free()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var ss := PackedFloat32Array()
	for i in pts.size() - 1:
		var seg := lens[i + 1] - lens[i]
		var k := maxi(int(ceil(seg / 0.5)), 1)
		for j in k:
			ss.append(lens[i] + seg * float(j) / k)
	ss.append(length)
	const TOP := 16
	var ring := 0
	var vs := PackedVector3Array()
	var phase := _h(1.0) * TAU
	for s in ss:
		var t := (local_at(s + 0.25) - local_at(s - 0.25)).normalized()
		var side := Vector3.UP.cross(t)
		side = side.normalized() if side.length() > 0.2 else Vector3.RIGHT
		var across := Vector3.UP if upright else side
		var nrm := t.cross(across).normalized()
		var p := local_at(s)
		var head := clampf(s / 0.6, 0.0, 1.0)
		var tail := clampf((length - s) / 1.6, 0.0, 1.0)
		var taper := 0.3 + 0.7 * sqrt(minf(head, tail))
		var load := 1.0 + 0.08 * (1.0 - clampf(s / 2.0, 0.0, 1.0))
		var bump := _kick_bump(s)
		var rag := 0.05 * sin(s * 2.3 + phase) + 0.04 * sin(s * 5.7 + phase * 2.0)
		var prof: Array = []   # [across offset, normal offset, v]
		for k in TOP + 1:
			var u := float(k) / TOP
			var groove := 0.022 * sin(u * PI * 13.0 + s * 0.4 + phase) * sin(PI * u)
			if upright:
				var h := thick * 0.5 + (RIDGE * 0.6) * sin(PI * u) + groove
				prof.append([u * width, h, u])
			else:
				var hh := ((RIDGE + bump) * pow(sin(PI * u), 0.6) + groove) * taper
				prof.append([(u - 0.5) * width * taper * load * (1.0 + rag * (1.0 if u > 0.5 else -1.0) * 0.6), hh, u])
		if upright:
			prof.append([width + 0.06, 0.0, 1.0])
			for k in range(TOP, -1, -1):
				var u := float(k) / TOP
				prof.append([u * width, -(thick * 0.5 + RIDGE * 0.6 * sin(PI * u)), u])
			prof.append([-0.04, 0.0, 0.0])
		else:
			var hw := width * 0.5 * taper * load
			prof.append([hw * 0.98, -thick * 0.45, 1.0])
			prof.append([hw * 0.9, -thick, 1.0])
			prof.append([-hw * 0.9, -thick, 0.0])
			prof.append([-hw * 0.98, -thick * 0.45, 0.0])
		for q: Array in prof:
			var o: Vector3 = p + across * float(q[0]) + nrm * float(q[1])
			st.set_uv(Vector2(s / maxf(width, 0.1), q[2]))
			st.add_vertex(o)
			vs.append(o)
		ring = prof.size()
	var rows := ss.size()
	for i in rows - 1:
		for k in ring:
			var a := i * ring + k
			var b := i * ring + (k + 1) % ring
			st.add_index(a); st.add_index(a + ring); st.add_index(b)
			st.add_index(b); st.add_index(a + ring); st.add_index(b + ring)
	# end caps (fans to the ring centre)
	for e in 2:
		var base := 0 if e == 0 else (rows - 1) * ring
		var c := Vector3.ZERO
		for k in ring:
			c += vs[base + k]
		st.set_uv(Vector2(0.0 if e == 0 else length / maxf(width, 0.1), 0.5))
		st.add_vertex(c / ring)
		var ci := rows * ring + e
		for k in ring:
			var a := base + k
			var b := base + (k + 1) % ring
			if e == 0:
				st.add_index(ci); st.add_index(b); st.add_index(a)
			else:
				st.add_index(ci); st.add_index(a); st.add_index(b)
	if not upright and wet and length > 3.0:
		_drips(st, rows * ring + 2)
	st.generate_normals()
	st.generate_tangents()
	visual = MeshInstance3D.new()
	visual.name = "Visual"
	visual.mesh = st.commit()
	visual.material_override = _mat()
	add_child(visual)
	for i in pts.size() - 1:
		var cs := CollisionShape3D.new()
		cs.name = "Col_%d" % i
		var bs := BoxShape3D.new()
		bs.size = _seg_size(i)
		cs.shape = bs
		cs.transform = _seg_xform(i)
		add_child(cs)
		_cols.append(cs)
	_apply_enabled()


## Drips running off the stroke's edges: short tapering tongues with a bulb, every few metres.
func _drips(st: SurfaceTool, first: int) -> void:
	const SIDES := 6
	const STEPS := 5
	var idx := first
	var n := int(length / 3.5)
	for d in n:
		var s := (float(d) + 0.3 + 0.4 * _h(d + 3.0)) * length / n
		var t := (local_at(s + 0.25) - local_at(s - 0.25)).normalized()
		var side := Vector3.UP.cross(t)
		side = side.normalized() if side.length() > 0.2 else Vector3.RIGHT
		var sgn := 1.0 if _h(d + 7.0) > 0.5 else -1.0
		var top := local_at(s) + side * sgn * width * 0.44 - t.cross(side).normalized() * thick * 0.5
		var drop := 0.25 + 0.6 * _h(d + 11.0)
		var r0 := 0.07 + 0.05 * _h(d + 13.0)
		for j in STEPS + 1:
			var f := float(j) / STEPS
			var c := top + Vector3.DOWN * drop * f + side * sgn * 0.04 * f
			var r := r0 * lerpf(1.0, 0.45, f) + (0.05 if j == STEPS - 1 else 0.0)
			if j == STEPS:
				r = 0.0
			for k in SIDES:
				var a := -TAU * k / SIDES
				st.set_uv(Vector2(s / maxf(width, 0.1) + float(k) * 0.05, 0.02))
				st.add_vertex(c + (t * cos(a) + side * sin(a)) * r)
		for j in STEPS:
			for k in SIDES:
				var a := idx + j * SIDES + k
				var b := idx + j * SIDES + (k + 1) % SIDES
				st.add_index(a); st.add_index(b); st.add_index(a + SIDES)
				st.add_index(b); st.add_index(b + SIDES); st.add_index(a + SIDES)
		idx += (STEPS + 1) * SIDES


func _seg_size(i: int) -> Vector3:
	var l := pts[i].distance_to(pts[i + 1]) + 0.12
	return Vector3(thick, width, l) if upright else Vector3(width * 0.92, thick, l)


func _seg_xform(i: int) -> Transform3D:
	var a := pts[i]
	var b := pts[i + 1]
	var z := (b - a).normalized()
	var x := Vector3.UP.cross(z)
	if x.length() < 0.2:
		x = Vector3.RIGHT.cross(z)
	x = x.normalized()
	var y := z.cross(x).normalized()
	var mid := (a + b) * 0.5
	if upright:
		return Transform3D(Basis(x, y, z), mid + Vector3.UP * (width * 0.5))
	return Transform3D(Basis(x, y, z), mid - y * (thick * 0.5))


func _mat() -> Material:
	if _own_mat:
		return _own_mat
	return mat_for(colour)


# --- state ----------------------------------------------------------------------------------

func set_colour(c: String) -> void:
	colour = c
	rec["c"] = c
	if _own_mat:
		_paint(_own_mat, c)
	elif visual:
		visual.material_override = _mat()


func set_enabled(on: bool) -> void:
	enabled = on
	_apply_enabled()


func _apply_enabled() -> void:
	visible = enabled
	collision_layer = 1 if enabled else 0


## Heist drying: 0 wet, 1 hardened (no longer a rail), 2 cracked (falls away).
func set_dry(v: float) -> void:
	if is_equal_approx(v, dry):
		return
	dry = v
	if _own_mat == null:
		_own_mat = mat_for(colour).duplicate()
		visual.material_override = _own_mat
	_own_mat.set_shader_parameter(&"dry", clampf(v, 0.0, 1.0))
	if v >= 2.0:
		set_enabled(false)


func surfable() -> bool:
	return enabled and wet and dry < 1.0 and kind != "pencil" and kind != "seal" and kind != "well" and colour != "green"


# --- geometry queries (global space) -----------------------------------------------------------

func _idx(s: float) -> int:
	var lo := 0
	var hi := lens.size() - 1
	while hi - lo > 1:
		var m := (lo + hi) >> 1
		if lens[m] <= s:
			lo = m
		else:
			hi = m
	return lo


func local_at(s: float) -> Vector3:
	s = clampf(s, 0.0, length)
	var i := _idx(s)
	if i >= pts.size() - 1:
		return pts[pts.size() - 1]
	var seg := lens[i + 1] - lens[i]
	return pts[i].lerp(pts[i + 1], (s - lens[i]) / maxf(seg, 0.0001))


func sample(s: float) -> Vector3:
	return global_transform * local_at(s)


func tangent(s: float) -> Vector3:
	var i := mini(_idx(clampf(s, 0.0, length)), pts.size() - 2)
	return (global_transform.basis * (pts[i + 1] - pts[i])).normalized()


## Closest arc position to a global point. Returns [s, distance, global point].
func closest(p: Vector3) -> Array:
	var lp := global_transform.affine_inverse() * p
	var best_s := 0.0
	var best_d := INF
	for i in pts.size() - 1:
		var a := pts[i]
		var ab := pts[i + 1] - a
		var t := clampf((lp - a).dot(ab) / maxf(ab.length_squared(), 0.0001), 0.0, 1.0)
		var d := (a + ab * t).distance_to(lp)
		if d < best_d:
			best_d = d
			best_s = lens[i] + ab.length() * t
	return [best_s, best_d, sample(best_s)]


func kick_near(s: float) -> bool:
	for k in kicks:
		if absf(s - k) < 1.6:
			return true
	return false


func end_point(at_start: bool) -> Vector3:
	return sample(0.0 if at_start else length)


func centre() -> Vector3:
	return sample(length * 0.5)


var _bb := AABB()
var _bb_xf := Transform3D(Basis.IDENTITY * 0.0, Vector3.INF)


## Global AABB of the centreline (cached until the stroke moves).
func bounds() -> AABB:
	var xf := global_transform
	if xf != _bb_xf:
		_bb_xf = xf
		_bb = AABB(xf * pts[0], Vector3.ZERO)
		for p in pts:
			_bb = _bb.expand(xf * p)
		if upright:
			_bb = _bb.expand(_bb.end + Vector3.UP * width)
	return _bb
