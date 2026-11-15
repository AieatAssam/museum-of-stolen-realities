extends Node3D
## The canvas: every stroke in the wing, the painter's knife, and what paint does to paint.
##  - scrape (secondary, aimed, KNIFE_REACH m): lifts a stroke off the world onto the knife. The
##    knife carries ONE load: that colour, that many metres (capped at MAX_LOAD). Wells refill
##    without being used up; seals (the Pentimento) crumble instead of loading.
##  - lay (primary): lays the load where she looks. Looking up past WALL_PITCH plants a WALL across
##    her view; otherwise a BRIDGE/RAMP from just ahead of her feet to the aimed point, clamped to
##    the load's length and to MAX_SLOPE. Real collision; wet, so it is a rail.
##  - colour: blue floats on water and holds it (a blue wall across a dam slot raises the water);
##    red/orange are hot (fast rails, and a hot stroke laid into varnish burns it away);
##    yellow/orange give light (pencil underdrawing within LIGHT_R becomes solid and visible).
##  - wet-on-wet: a laid stroke crossing another blends both: blue+yellow green (grows a climbable
##    column), red+blue violet (heavy: both sink), red+yellow orange.
##  - layers: scraping a stroke reveals the strokes listed in its "under".
## Everything she moves is recorded (state()/restore()) and survives leaving the wing.

signal scraped(stroke: Node3D, world: bool)
signal laid(stroke: Node3D)
signal blended(a: Node3D, b: Node3D, colour: String)
signal sank(stroke: Node3D)
signal burned(id: String)
signal refused(why: String)
signal seal_scraped(stroke: Node3D)

const Stroke := preload("res://wings/paint/stroke.gd")
const Art := preload("res://wings/paint/paint_art.gd")
const KNIFE_REACH := 7.0
const MAX_LOAD := 18.0
const WALL_PITCH := 0.45
const MAX_SLOPE := 0.55   # rad (~31 deg)
const LIGHT_R := 11.0
const SINK := 3.5

var strokes: Dictionary = {}     # sid -> stroke
var has_knife: bool = false
var load: Dictionary = {}        # {"c": colour, "len": metres}
var removed: Dictionary = {}     # world sid -> true
var laid_recs: Array = []
var blends: Dictionary = {}      # world sid -> colour
var sunk: Dictionary = {}        # sid -> true
var burned_ids: Dictionary = {}
var foliage: Array = []          # [x, y, z, top]
var waters: Array = []           # {id, rect: Rect2(x,z), base, raised, level, slot: Rect2, mesh}
var varnish: Dictionary = {}     # id -> StaticBody3D
var laid_n: int = 0
var _foliage_nodes: Array = []
var _lights: Dictionary = {}     # sid -> OmniLight3D


# --- building --------------------------------------------------------------------------------

func add(r: Dictionary, parent: Node3D = null) -> Node3D:
	var st: Node3D = Stroke.new().setup(r)
	(parent if parent else self).add_child(st)
	strokes[st.sid] = st
	if bool(r.get("hidden", false)) or st.kind == "pencil":
		st.set_enabled(false)
	if st.is_light(st.colour):
		_light_for(st)
	return st


func add_water(id: String, rect: Rect2, base: float, raised: float = NAN, slot: Rect2 = Rect2(), parent: Node3D = null) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = "Water_" + id
	var pm := PlaneMesh.new()
	pm.size = rect.size
	mi.mesh = pm
	var m := ShaderMaterial.new()   # opaque wet ultramarine, laid in creeping strokes
	m.shader = load("res://wings/paint/shaders/paint_water.gdshader")
	m.set_shader_parameter(&"stroke_normal", load(Stroke.STROKE_N))
	m.set_shader_parameter(&"stroke_albedo", load(Stroke.STROKE_A))
	mi.material_override = m
	mi.position = Vector3(rect.get_center().x, base, rect.get_center().y)
	(parent if parent else self).add_child(mi)
	waters.append({"id": id, "rect": rect, "base": base, "raised": raised, "level": base, "slot": slot, "mesh": mi})
	return mi


func add_varnish(id: String, a: Vector3, b: Vector3, parent: Node3D = null) -> StaticBody3D:
	var sb := StaticBody3D.new()
	sb.name = "Varnish_" + id
	sb.set_meta(&"varnish", id)
	var size := (b - a).abs()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	sb.add_child(cs)
	var fm := Art.model("torn_mass")   # a torn, crusted mass stretched over the box, never a slab
	fm.name = "Visual"
	fm.scale = size
	for g: MeshInstance3D in fm.find_children("*", "MeshInstance3D", true, false):
		g.material_override = Art.mat("g_varnish")  # hazard/blocker: yellowed, cracked varnish
	sb.add_child(fm)
	sb.position = (a + b) * 0.5
	(parent if parent else self).add_child(sb)
	varnish[id] = sb
	return sb


func _light_for(st: Node3D) -> void:
	if _lights.has(st.sid):
		return
	var l := OmniLight3D.new()
	l.light_color = Color("ffd76a")
	l.light_energy = 1.6
	l.omni_range = LIGHT_R
	l.position = st.local_at(st.length * 0.5) + Vector3.UP * 1.0
	st.add_child(l)
	_lights[st.sid] = l


# --- queries ----------------------------------------------------------------------------------

func get_stroke(sid: String) -> Node3D:
	return strokes.get(sid)


## Nearest wet stroke within `r` (horizontal) of the feet: [stroke, s, dist] or [].
func find_rail(feet: Vector3, r: float) -> Array:
	var best: Array = []
	var bd := r
	for st: Node3D in strokes.values():
		if not st.surfable():
			continue
		if not st.bounds().grow(r + 1.7).has_point(feet):
			continue
		var c: Array = st.closest(feet)
		var q: Vector3 = c[2]
		var hd := Vector2(q.x - feet.x, q.z - feet.z).length()
		if hd < bd and absf(st.tangent(float(c[0])).y) < 0.8:
			bd = hd
			best = [st, c[0], hd]
	return best


## The stroke that continues from `st`'s end (start if at_start): [next, s, dir] or [].
func connect_at(st: Node3D, at_start: bool, look: Vector3) -> Array:
	var end: Vector3 = st.end_point(at_start)
	var travel: Vector3 = st.tangent(0.0) * -1.0 if at_start else st.tangent(st.length)
	var best: Array = []
	var score := -INF
	var flat := Vector3(look.x, 0, look.z).normalized()
	for o: Node3D in strokes.values():
		if o == st or not o.surfable():
			continue
		for from_start: bool in [true, false]:
			if o.end_point(from_start).distance_to(end) > 1.6:
				continue
			var d := 1.0 if from_start else -1.0
			var s0: float = 0.0 if from_start else o.length
			var t: Vector3 = o.tangent(s0) * d
			var sc := flat.dot(Vector3(t.x, 0, t.z).normalized())
			if sc > score:
				score = sc
				best = [o, s0, d]
	return best


func climb_top(pos: Vector3) -> float:
	for f: Array in foliage:
		if Vector2(pos.x - f[0], pos.z - f[2]).length() < 1.4 and pos.y > float(f[1]) - 0.6 and pos.y < float(f[3]) + 0.2:
			return float(f[3])
	return NAN


func water_at(p: Vector3) -> Dictionary:
	for w: Dictionary in waters:
		if (w["rect"] as Rect2).has_point(Vector2(p.x, p.z)):
			return w
	return {}


func water_level(id: String) -> float:
	for w: Dictionary in waters:
		if w["id"] == id:
			return w["level"]
	return NAN


# --- the knife ---------------------------------------------------------------------------------

func _ray(from: Vector3, to: Vector3) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1)
	return get_world_3d().direct_space_state.intersect_ray(q)


func aimed_stroke(cam: Camera3D, reach: float = KNIFE_REACH) -> Node3D:
	var o := cam.global_position
	var hit := _ray(o, o - cam.global_basis.z * reach)
	if hit.is_empty():
		return null
	var c: Object = hit["collider"]
	return c if c != null and c.has_meta(&"stroke") else null


func scrape(cam: Camera3D) -> String:
	if not has_knife:
		return "no_knife"
	var st := aimed_stroke(cam)
	if st == null:
		refused.emit("nothing")
		return "nothing"
	if st.kind == "seal":
		st.set_enabled(false)
		removed[st.sid] = true
		seal_scraped.emit(st)
		return "seal"
	if st.kind in ["fixed", "pencil", "trunk"]:
		refused.emit("fixed")
		return "fixed"
	if not load.is_empty():
		refused.emit("full")
		return "full"
	load = {"c": st.colour, "len": minf(st.length, MAX_LOAD)}
	if st.kind == "well":
		scraped.emit(st, false)
		return "well"
	_remove(st)
	scraped.emit(st, not st.laid)
	return "ok"


func _remove(st: Node3D) -> void:
	st.set_enabled(false)
	if st.laid:
		for i in laid_recs.size():
			if laid_recs[i]["id"] == st.sid:
				laid_recs.remove_at(i)
				break
		strokes.erase(st.sid)
		st.queue_free()
	else:
		removed[st.sid] = true
	for u in st.under:
		var us: Node3D = strokes.get(String(u))
		if us and not removed.has(us.sid):
			_reveal(us)
	_refresh()


func _reveal(us: Node3D) -> void:
	us.set_enabled(true)
	us.visual.scale = Vector3(1, 0.05, 1)   # the mesh only: Jolt refuses non-uniform body scale
	create_tween().tween_property(us.visual, "scale", Vector3.ONE, 0.8).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func _line(a: Vector3, b: Vector3) -> Array:
	var n := maxi(int(ceil(a.distance_to(b) / 1.5)), 1)
	var out: Array = []
	for i in n + 1:
		out.append(a.lerp(b, float(i) / n))
	return out


## Lay what the knife carries where she looks. Returns "ok", "sank", "empty", "short".
func lay(p: Player) -> String:
	if not has_knife:
		return "no_knife"
	if load.is_empty():
		refused.emit("empty")
		return "empty"
	var cam := p.camera
	var o := cam.global_position
	var d := -cam.global_basis.z
	var flat := Vector3(d.x, 0, d.z)
	flat = flat.normalized() if flat.length() > 0.01 else -p.global_basis.z
	var L := float(load["len"])
	var feet := p.global_position
	var extra := {"laid": true}
	var points: Array
	if asin(clampf(d.y, -1, 1)) > WALL_PITCH:
		var base := feet + flat * 2.2
		var g := _ray(base + Vector3.UP * 1.5, base + Vector3.DOWN * 6.0)
		base.y = (float(g["position"].y) if not g.is_empty() else feet.y) - 1.0
		var side := flat.cross(Vector3.UP).normalized()
		var half := minf(L, 6.0) * 0.5
		points = _line(base - side * half, base + side * half)
		extra.merge({"up": true, "w": 4.2, "t": 0.6})
	else:
		var a := feet + flat * 1.2
		a.y = feet.y + 0.02
		var hit := _ray(o, o + d * 40.0)
		var b: Vector3 = hit["position"] if not hit.is_empty() else a + d * L   # aimed at nothing: along the look, from her feet
		var h := Vector2(b.x - a.x, b.z - a.z).length()
		b.y = clampf(b.y, a.y - h * tan(MAX_SLOPE), a.y + h * tan(MAX_SLOPE))
		if a.distance_to(b) > L:
			b = a + a.direction_to(b) * L
		if a.distance_to(b) < 1.5:
			refused.emit("short")
			return "short"
		points = _line(a, b)
	laid_n += 1
	var colour := String(load["c"])
	var r: Dictionary = Stroke.make("laid_%d" % laid_n, points, colour, 2.0, extra)
	load = {}
	# water: blue floats on it, anything else sinks and is lost
	if not r.get("up", false):
		var mid: Vector3 = points[points.size() / 2]
		var w := water_at(mid)
		if not w.is_empty() and mid.y < float(w["level"]) + 2.5:
			if colour == "blue":
				var lvl := float(w["level"]) + 0.05
				var flt: Array = []
				for q: Vector3 in points:
					flt.append(Vector3(q.x, lvl, q.z))
				r["p"] = Stroke.pack(PackedVector3Array(flt))
				r["fl"] = w["id"]
				r["fl0"] = lvl
			else:
				var gone := add(r)
				strokes.erase(gone.sid)
				gone.collision_layer = 0
				var t := create_tween()
				t.tween_property(gone, "position:y", -3.0, 1.6).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
				t.tween_callback(gone.queue_free)
				sank.emit(gone)
				return "sank"
	var st := add(r)
	laid_recs.append(r)
	_after_lay(st)
	laid.emit(st)
	return "ok"


func _after_lay(st: Node3D) -> void:
	# wet-on-wet
	for o: Node3D in strokes.values().duplicate():
		if o == st or not o.enabled or o.kind in ["pencil", "seal", "well"]:
			continue
		var res := _mix(st.colour, o.colour)
		if res == "":
			continue
		var q := _crossing(st, o)
		if q.is_empty():
			continue
		_blend(st, o, res, q[0])
	# hot paint burns varnish
	if st.is_hot(st.colour):
		for id: String in varnish:
			if burned_ids.has(id):
				continue
			var vb: StaticBody3D = varnish[id]
			var box := AABB(vb.global_position - ((vb.get_child(0) as CollisionShape3D).shape as BoxShape3D).size * 0.5,
				((vb.get_child(0) as CollisionShape3D).shape as BoxShape3D).size).grow(0.8)
			var s := 0.0
			while s <= st.length:
				if box.has_point(st.sample(s)):
					_burn(id, false)
					break
				s += 0.4
	_refresh()


static func _mix(a: String, b: String) -> String:
	var k := [a, b]
	k.sort()
	match k:
		["blue", "yellow"]: return "green"
		["blue", "red"]: return "violet"
		["red", "yellow"]: return "orange"
	return ""


## Where two strokes cross (closest approach of any two segments): [point] or [].
func _crossing(a: Node3D, b: Node3D) -> Array:
	var reach: float = (a.width + b.width) * 0.45 + 0.35
	if not a.bounds().grow(reach + (a.width if a.upright else 0.0)).intersects(b.bounds().grow(reach + (b.width if b.upright else 0.0))):
		return []
	var best := INF
	var bp := Vector3.ZERO
	for i in a.pts.size() - 1:
		for j in b.pts.size() - 1:
			var r := _seg_seg(a.global_transform * a.pts[i], a.global_transform * a.pts[i + 1],
				b.global_transform * b.pts[j], b.global_transform * b.pts[j + 1])
			if r[0] < best:
				best = r[0]
				bp = r[1]
	return [bp] if best < reach else []


static func _seg_seg(p1: Vector3, q1: Vector3, p2: Vector3, q2: Vector3) -> Array:
	var d1 := q1 - p1
	var d2 := q2 - p2
	var r := p1 - p2
	var a := d1.dot(d1)
	var e := d2.dot(d2)
	var f := d2.dot(r)
	var s := 0.0
	var t := 0.0
	if a <= 1e-6 and e <= 1e-6:
		return [p1.distance_to(p2), p1]
	if a <= 1e-6:
		t = clampf(f / e, 0, 1)
	else:
		var c := d1.dot(r)
		if e <= 1e-6:
			s = clampf(-c / a, 0, 1)
		else:
			var b := d1.dot(d2)
			var den := a * e - b * b
			s = clampf((b * f - c * e) / den, 0, 1) if den > 1e-6 else 0.0
			t = (b * s + f) / e
			if t < 0.0:
				t = 0.0
				s = clampf(-c / a, 0, 1)
			elif t > 1.0:
				t = 1.0
				s = clampf((b - c) / a, 0, 1)
	var c1 := p1 + d1 * s
	var c2 := p2 + d2 * t
	return [c1.distance_to(c2), (c1 + c2) * 0.5]


func _blend(a: Node3D, b: Node3D, res: String, at: Vector3, instant: bool = false) -> void:
	# the two colours bleed where they cross: a daub of the mixture over the crossing
	var bleed := MeshInstance3D.new()
	bleed.name = "Bleed"
	bleed.mesh = Art.daub_mesh(1.6, 0.22, at.x + at.z)
	bleed.material_override = Stroke.mat_for(res)
	a.add_child(bleed)   # sinks, hides and goes with the stroke
	bleed.global_position = at + Vector3.UP * 0.05
	for st: Node3D in [a, b]:
		st.set_colour(res)
		if not st.laid:
			blends[st.sid] = res
	if res == "green":
		var grow := maxf(float(a.rec.get("grow", 0.0)), float(b.rec.get("grow", 0.0)))
		_grow(at, at.y + (grow if grow > 0.0 else 7.0), instant)
	elif res == "violet":
		for st: Node3D in [a, b]:
			_sink(st, instant)
	elif res == "orange":
		for st: Node3D in [a, b]:
			_light_for(st)
	if not instant:
		blended.emit(a, b, res)


func _grow(at: Vector3, top: float, instant: bool) -> void:
	foliage.append([at.x, at.y, at.z, top])
	# a column of leafy daubs, stacked in 2 m segments, each turned so the stack never repeats
	var col := Node3D.new()
	col.name = "Foliage_%d" % foliage.size()
	var h := top - at.y + 0.6
	for i in ceili(h / 2.0):
		var seg := Art.model("foliage_seg")
		seg.position = Vector3(0, i * 2.0, 0)
		seg.rotation.y = i * 2.4 + at.x
		seg.scale = Vector3.ONE * (1.0 - 0.25 * float(i * 2.0) / h)
		col.add_child(seg)
	col.position = at
	add_child(col)
	_foliage_nodes.append(col)
	if not instant:
		col.scale = Vector3(1, 0.02, 1)
		create_tween().tween_property(col, "scale", Vector3.ONE, 2.0).set_trans(Tween.TRANS_SINE)


func _sink(st: Node3D, instant: bool) -> void:
	if sunk.has(st.sid):
		return
	sunk[st.sid] = true
	if st.laid:
		st.rec["sunk"] = true
	var depth := float(st.rec.get("sink", SINK))
	if instant:
		st.position.y -= depth
	else:
		create_tween().tween_property(st, "position:y", st.position.y - depth, 2.4).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


func _burn(id: String, instant: bool) -> void:
	burned_ids[id] = true
	var vb: StaticBody3D = varnish[id]
	vb.collision_layer = 0
	if instant:
		vb.visible = false
	else:
		var t := create_tween()
		t.tween_property(vb, "scale", Vector3(1, 0.02, 1), 1.2).set_trans(Tween.TRANS_QUAD)
		t.tween_callback(func() -> void: vb.visible = false)
		burned.emit(id)


# --- derived state: light and water ----------------------------------------------------------

func _refresh() -> void:
	_update_light()
	_update_water_targets()


func _update_light() -> void:
	var lamps: Array = []
	for st: Node3D in strokes.values():
		if st.enabled and st.is_light(st.colour) and not st.kind in ["pencil", "well"]:
			for i in range(0, st.pts.size(), 2):
				lamps.append(st.global_transform * st.pts[i])
			lamps.append(st.sample(st.length))
	for st: Node3D in strokes.values():
		if st.kind != "pencil" or removed.has(st.sid):
			continue
		var lit := false
		for i in st.pts.size():
			var q: Vector3 = st.global_transform * st.pts[i]
			for l: Vector3 in lamps:
				if q.distance_to(l) < LIGHT_R:
					lit = true
					break
			if lit:
				break
		if lit != st.enabled:
			st.set_enabled(lit)


func _update_water_targets() -> void:
	for w: Dictionary in waters:
		var slot: Rect2 = w["slot"]
		var dammed := false
		if slot.has_area():
			for st: Node3D in strokes.values():
				if st.enabled and st.upright and st.colour == "blue":
					for q in st.pts:
						var g: Vector3 = st.global_transform * q
						if slot.has_point(Vector2(g.x, g.z)):
							dammed = true
		w["target"] = float(w["raised"]) if dammed else float(w["base"])


func _physics_process(delta: float) -> void:
	for w: Dictionary in waters:
		var tgt := float(w.get("target", w["base"]))
		var lvl := float(w["level"])
		if not is_equal_approx(lvl, tgt):
			lvl = move_toward(lvl, tgt, 1.2 * delta)
			w["level"] = lvl
			(w["mesh"] as Node3D).position.y = lvl
			_float_to(w)


func _float_to(w: Dictionary) -> void:
	for st: Node3D in strokes.values():
		if String(st.rec.get("fl", "")) == w["id"]:
			st.position.y = float(w["level"]) + 0.05 - float(st.rec.get("fl0", 0.0)) - (SINK if sunk.has(st.sid) else 0.0)


# --- persistence --------------------------------------------------------------------------------

func state() -> Dictionary:
	return {"removed": removed.keys(), "laid": laid_recs.duplicate(true), "blends": blends.duplicate(),
		"sunk": sunk.keys(), "burned": burned_ids.keys(), "foliage": foliage.duplicate(true),
		"load": load.duplicate(), "knife": has_knife, "n": laid_n}


func restore(st: Dictionary) -> void:
	has_knife = bool(st.get("knife", false))
	load = st.get("load", {})
	laid_n = int(st.get("n", 0))
	var rem: Array = st.get("removed", [])
	for sid: String in rem:
		var s: Node3D = strokes.get(sid)
		if s:
			for u in s.under:
				var us: Node3D = strokes.get(String(u))
				if us:
					us.set_enabled(true)
	for sid: String in rem:
		removed[sid] = true
		var s: Node3D = strokes.get(sid)
		if s:
			s.set_enabled(false)
	for r: Dictionary in st.get("laid", []):
		laid_recs.append(r)
		var s := add(r)
		if r.get("sunk", false):
			sunk[s.sid] = true
			s.position.y -= float(r.get("sink", SINK))
	var bl: Dictionary = st.get("blends", {})
	for sid: String in bl:
		var s: Node3D = strokes.get(sid)
		if s:
			s.set_colour(bl[sid])
			blends[sid] = bl[sid]
			if s.is_light(s.colour):
				_light_for(s)
	for sid: String in st.get("sunk", []):
		var s: Node3D = strokes.get(sid)
		if s and not sunk.has(sid):
			sunk[sid] = true
			s.position.y -= float(s.rec.get("sink", SINK))
	for id: String in st.get("burned", []):
		if varnish.has(id):
			_burn(id, true)
	for f: Array in st.get("foliage", []):
		_grow(Vector3(f[0], f[1], f[2]), f[3], true)
	_refresh()
	for w: Dictionary in waters:
		w["level"] = w["target"]
		(w["mesh"] as Node3D).position.y = w["level"]
		_float_to(w)
