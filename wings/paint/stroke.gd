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
var _own_mat: StandardMaterial3D


static func mat_for(c: String) -> StandardMaterial3D:
	if _mats.has(c):
		return _mats[c]
	var m := StandardMaterial3D.new()
	m.albedo_color = COLOURS.get(c, Color.MAGENTA)
	m.roughness = 0.35 if c != "pencil" and c != "dry" else 0.9
	if c in LIGHT:
		m.emission_enabled = true
		m.emission = COLOURS[c]
		m.emission_energy_multiplier = 0.8
	_mats[c] = m
	return m


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


func _build() -> void:
	for c in _cols:
		c.queue_free()
	_cols.clear()
	if visual:
		visual.queue_free()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := pts.size()
	const ACROSS := 5
	for i in n:
		var f: Array = _frame(i)
		var across: Vector3 = f[1]
		var nrm: Vector3 = f[2]
		var taper := clampf(minf(lens[i], length - lens[i]) / 0.8 + 0.35, 0.35, 1.0)
		var bump := _kick_bump(lens[i])
		for k in ACROSS + 1:
			var u := float(k) / ACROSS
			var o: Vector3
			if upright:
				o = pts[i] + across * (u * width) + nrm * (thick * 0.5 + RIDGE * sin(PI * u))
			else:
				var ridge := (RIDGE + bump) * pow(sin(PI * u), 0.7) * taper
				o = pts[i] + across * ((u - 0.5) * width * taper) + nrm * ridge
			st.set_uv(Vector2(lens[i] / maxf(width, 0.1), u))
			st.add_vertex(o)
	for i in n - 1:
		for k in ACROSS:
			var a := i * (ACROSS + 1) + k
			st.add_index(a); st.add_index(a + ACROSS + 1); st.add_index(a + 1)
			st.add_index(a + 1); st.add_index(a + ACROSS + 1); st.add_index(a + ACROSS + 2)
	st.generate_normals()
	visual = MeshInstance3D.new()
	visual.name = "Visual"
	visual.mesh = st.commit()
	visual.material_override = _mat()
	# a thin underside slab so a stroke reads as a body of paint, not a sheet
	var body := MeshInstance3D.new()
	body.name = "Body"
	var bst := SurfaceTool.new()
	bst.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in n - 1:
		var bx := BoxMesh.new()
		bx.size = _seg_size(i)
		bst.append_from(bx, 0, _seg_xform(i))
	body.mesh = bst.commit()
	body.material_override = visual.material_override
	visual.add_child(body)
	add_child(visual)
	for i in n - 1:
		var cs := CollisionShape3D.new()
		cs.name = "Col_%d" % i
		var bs := BoxShape3D.new()
		bs.size = _seg_size(i)
		cs.shape = bs
		cs.transform = _seg_xform(i)
		add_child(cs)
		_cols.append(cs)
	_apply_enabled()


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
	return mat_for("dry" if dry >= 1.0 else colour)


# --- state ----------------------------------------------------------------------------------

func set_colour(c: String) -> void:
	colour = c
	rec["c"] = c
	if _own_mat:
		_own_mat.albedo_color = COLOURS.get(c, Color.MAGENTA)
	elif visual:
		visual.material_override = _mat()
		(visual.get_node("Body") as MeshInstance3D).material_override = visual.material_override


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
		_own_mat = (mat_for(colour) as StandardMaterial3D).duplicate()
		visual.material_override = _own_mat
		(visual.get_node("Body") as MeshInstance3D).material_override = _own_mat
	_own_mat.albedo_color = (COLOURS[colour] as Color).lerp(COLOURS["dry"], clampf(v, 0.0, 1.0))
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
