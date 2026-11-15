extends WalkMode
## SILKSPINNING, the Chitin Court's rule. A wrist spinneret.
##
## Primary fires a line at the best anchor in a soft aim cone (nodes in group `silk_anchors`; the
## targeted one shows its `Highlight` child) and the player swings on a real pendulum about the
## anchor, or about the last post the line has wrapped round (group `silk_posts`). Forward/back reel
## the line in and out (angular momentum is kept, so reeling in at the bottom speeds the swing).
## Primary again, or jump, releases with momentum. Releasing near the top of the arc (slow, high)
## is a "top release": the spinneret flicks her up and onward.
##
## The spinneret governs each swing into a band: in the lower arc it pays out or takes in energy
## so the forward apex always lies between BAND_MIN_DEG and BAND_MAX_DEG from vertical. That band
## is what makes the levels designable: `envelope()` below gives the closed-form release and
## landing range for any rope length, and every gap in the wing is sized from it.
##
## Secondary at one anchor then another weaves a taut strand between them (strand.gd): walk it as
## a tightrope, catch it mid-fall as a zip-membrane if it slopes, or aim at it and press secondary
## to pluck it (the wing hears plucks through `plucked`).
##
## Forgiveness: aim cone, mantle onto ledges up to MANTLE m above the feet, a magnet toward a ledge
## just ahead when falling short, walk-mode coyote time, and `last_safe` (the last ledge stood on)
## for the wing's fast fall respawn.

const Strand := preload("res://wings/chitin/strand.gd")

enum { GROUND, ROPE, AIR, ZIP }

const GRIP := 1.0              # pendulum point above the feet (the wrist)
const EYE := 1.62
const AIM_HALF_DEG := 14.0     # soft aim-assist cone, either side of the crosshair
const AIM_RANGE := 32.0
const MIN_ROPE := 3.0
const MAX_ROPE := 32.0
const REEL := 5.0
const ROPE_STEER := 3.0
const BAND_MIN_DEG := 55.0
const BAND_MAX_DEG := 78.0
const GOVERN_ARC_DEG := 50.0   # the governor only acts within this angle of the bottom
const GOVERN := 16.0           # m/s² the spinneret may add or take
const FLICK_UP := 5.0
const FLICK_FWD := 3.0
const FLICK_SPEED := 3.5       # release slower than this ...
const FLICK_MIN_DEG := 30.0    # ... and higher than this from vertical = top release
const PLANE_DAMP := 3.0       # 1/s, sideways speed bled off while swinging
const PLANE_PULL := 2.0       # 1/s², pull back to the plane through the anchor
const HOP := 4.0               # a line fired from the ground lifts her off it
const AIR_STEER := 4.0
const MANTLE := 1.4
const MAX_STRANDS := 4
const WEAVE_RANGE := 26.0
const PLUCK_RANGE := 16.0
const PLUCK_RADIUS := 0.9
const ZIP_CATCH := 1.2
const ZIP_MIN_SLOPE := 6.0

signal fired(anchor: Node3D)
signal released(top: bool)
signal touched_down
signal woven(strand: Node)
signal plucked(strand: Node)
signal wove_first(anchor: Node3D)

var state: int = GROUND
var anchor_node: Node3D
var pivots: Array[Vector3] = []
var chain_len: float = 0.0
var rope_len: float = 0.0
var target: Node3D
var weave_from: Node3D
var strands: Array[Node] = []
var last_safe: Transform3D
var has_safe: bool = false
## Telemetry the wing and tests read.
var swings: int = 0
var top_releases: int = 0
var mantles: int = 0
var air_chain: int = 0          # lines fired since the feet last touched ground
var best_air_chain: int = 0

var _rope_t: float = 0.0
var _rope_air: bool = false
var _seed: Vector3 = Vector3.ZERO
var _ground_t: float = 0.0
var _last_pos: Vector3 = Vector3.ZERO
var _zip: Node
var _zip_s: float = 0.0
var _zip_cool: float = 0.0
var _no_zip: Node
var _lit: Array[Node3D] = []


func enter(_from: MovementMode) -> void:
	state = GROUND
	_last_pos = player.global_position


func exit(_to: MovementMode) -> void:
	_drop_line()
	state = GROUND
	_set_lit([])


func reset() -> void:
	_drop_line()
	_zip = null
	state = GROUND
	air_chain = 0
	weave_from = null


func physics(delta: float) -> void:
	var p := player
	if _last_pos.distance_to(p.global_position) > 4.0:
		reset()  # teleported: a respawn, a cinematic or a test
	_zip_cool = maxf(_zip_cool - delta, 0.0)
	target = best_anchor()
	var lit: Array[Node3D] = []
	if target:
		lit.append(target)
	if is_instance_valid(weave_from):
		lit.append(weave_from)
	_set_lit(lit)
	match state:
		GROUND:
			_ground(delta)
		ROPE:
			_rope(delta)
		AIR:
			_air(delta)
		ZIP:
			_zipping(delta)
	_last_pos = p.global_position


func on_verb(verb: StringName, pressed: bool) -> bool:
	if verb == &"primary":
		if pressed:
			if state == ROPE:
				release()
			else:
				fire()
		return true
	if verb == &"secondary":
		if pressed:
			secondary()
		return true
	if verb == &"jump" and pressed:
		if state == ROPE:
			release()
			return true
		if state == ZIP:
			_leave_zip(Vector3.UP * 3.0)
			return true
	return super.on_verb(verb, pressed)


func bob_scale() -> float:
	return 1.0 if state == GROUND else 0.0


# --- aim ---------------------------------------------------------------------------------------

## Aim from yaw/pitch directly: head/pitch nodes only update in _process, which can lag physics.
func aim_dir() -> Vector3:
	return player.global_basis * (Basis(Vector3.UP, player.yaw) * Basis(Vector3.RIGHT, player.pitch) * Vector3.FORWARD)


func eye() -> Vector3:
	return player.global_position + player.up_direction * EYE


func grip() -> Vector3:
	return player.global_position + player.up_direction * GRIP


func best_anchor() -> Node3D:
	var o := eye()
	var d := aim_dir()
	var min_cos := cos(deg_to_rad(AIM_HALF_DEG))
	var cands: Array = []
	for n: Node in player.get_tree().get_nodes_in_group(&"silk_anchors"):
		var a := n as Node3D
		if a == null or not a.is_visible_in_tree() or a == anchor_node and state == ROPE:
			continue
		var to := a.global_position - o
		var dist := to.length()
		if dist > AIM_RANGE or dist < 1.0:
			continue
		var c := d.dot(to / dist)
		if c < min_cos:
			continue
		cands.append([c - dist / AIM_RANGE * 0.02, a])
	cands.sort_custom(func(x: Array, y: Array) -> bool: return x[0] > y[0])
	for i: int in mini(cands.size(), 4):
		var a: Node3D = cands[i][1]
		if _clear(o, a.global_position):
			return a
	return null


func _clear(from: Vector3, to: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1)
	q.exclude = [player.get_rid()]
	var hit := player.get_world_3d().direct_space_state.intersect_ray(q)
	return hit.is_empty() or (hit.position as Vector3).distance_to(to) < 0.8 or hit.collider is Strand


func _set_lit(lit: Array[Node3D]) -> void:
	for n: Node3D in _lit:
		if is_instance_valid(n) and not n in lit:
			var h := n.get_node_or_null(^"Highlight") as Node3D
			if h:
				h.visible = false
	for n: Node3D in lit:
		var h := n.get_node_or_null(^"Highlight") as Node3D
		if h:
			h.visible = true
	_lit = lit


# --- line --------------------------------------------------------------------------------------

func fire() -> bool:
	var n := target
	if n == null:
		return false
	var p := player
	var was_ground := state == GROUND and p.is_on_floor()
	if state == ZIP:
		_zip = null
	anchor_node = n
	pivots.clear()
	chain_len = 0.0
	rope_len = clampf(grip().distance_to(n.global_position), MIN_ROPE, MAX_ROPE)
	var up := p.up_direction
	if was_ground and p.velocity.dot(up) < HOP:
		p.velocity += up * (HOP - p.velocity.dot(up))
	else:
		air_chain += 1
		best_air_chain = maxi(best_air_chain, air_chain)
	# speed-preserving attach: outward speed is turned along the arc, not thrown away
	var r := grip() - n.global_position
	var rn := r.normalized()
	var vr := p.velocity.dot(rn)
	if vr > 0.0:
		var spd := p.velocity.length()
		var vt := p.velocity - rn * vr
		p.velocity = vt.normalized() * spd if vt.length() > 0.5 else vt
	# the swing plane: vertical, through the anchor and where she is (not where she aimed)
	var h := n.global_position - grip()
	h -= up * h.dot(up)
	if h.length() < 0.5:
		h = aim_dir() - up * aim_dir().dot(up)
	_seed = h.normalized() if h.length() > 0.05 else -p.global_basis.z
	state = ROPE
	_rope_t = 0.0
	_rope_air = not p.is_on_floor()
	weave_from = null
	swings += 1
	fired.emit(n)
	return true


func release() -> bool:
	if state != ROPE:
		return false
	var p := player
	var up := p.up_direction
	var r := grip() - pivot()
	var cos_t := -r.normalized().dot(up)
	var top := p.velocity.length() < FLICK_SPEED and cos_t < cos(deg_to_rad(FLICK_MIN_DEG)) and r.dot(up) < 0.0
	if top:
		var out := _seed if r.dot(_seed) >= 0.0 else -_seed
		p.velocity += up * FLICK_UP + out * FLICK_FWD
		top_releases += 1
	_drop_line()
	state = AIR
	released.emit(top)
	return true


func pivot() -> Vector3:
	if not pivots.is_empty():
		return pivots[-1]
	return anchor_node.global_position if is_instance_valid(anchor_node) else grip()


func line_points() -> PackedVector3Array:
	var pts := PackedVector3Array()
	if state != ROPE or not is_instance_valid(anchor_node):
		return pts
	pts.append(anchor_node.global_position)
	for q: Vector3 in pivots:
		pts.append(q)
	pts.append(grip())
	return pts


func _drop_line() -> void:
	anchor_node = null
	pivots.clear()
	chain_len = 0.0


func _anchor_ok() -> bool:
	return is_instance_valid(anchor_node) and anchor_node.is_inside_tree() and anchor_node.is_in_group(&"silk_anchors") and anchor_node.is_visible_in_tree()


func _rope(delta: float) -> void:
	if not _anchor_ok():
		_drop_line()
		state = AIR
		_air(delta)
		return
	var p := player
	var up := p.up_direction
	_rope_t += delta
	var mi := p.move_input()
	var free_before := rope_len - chain_len
	rope_len = clampf(rope_len + mi.y * REEL * delta, chain_len + MIN_ROPE, MAX_ROPE)
	p.velocity += p.gravity_vector * delta
	var side := p.head.global_basis.x
	p.velocity += (side - up * side.dot(up)) * mi.x * ROPE_STEER * delta
	if absf(mi.x) < 0.1 and pivots.is_empty():
		_keep_plane(delta)
	_update_wraps()
	var c := pivot()
	var free := rope_len - chain_len
	var r := grip() - c
	var d := r.length()
	var corr := Vector3.ZERO
	if d > 0.05:
		var n := r / d
		if d >= free - 0.03:
			var vr := p.velocity.dot(n)
			if vr > 0.0:
				p.velocity -= n * vr
			if free < free_before and free > 0.5:
				p.velocity *= minf(free_before / free, 1.05)  # angular momentum as the line shortens
			if not p.is_on_floor():
				_govern(delta, n, free)
			corr = -n * clampf(d - free, 0.0, 0.05) / delta
	p.velocity += corr
	p.move_and_slide()
	p.velocity -= corr
	# Before the pivot the line is still pulling her off the ledge she fired from (she slides over
	# its lip into the arc); only once past the pivot, or nearly stopped, does a ledge catch her.
	var rh := grip() - c
	rh -= up * rh.dot(up)
	var vh := p.velocity - up * p.velocity.dot(up)
	var past := rh.dot(vh) > 0.0 or vh.length() < 1.0
	if p.is_on_wall() and not p.is_on_floor() and past and _mantle():
		return
	if not p.is_on_floor():
		_rope_air = true
	elif (_rope_air and past and p.velocity.dot(up) <= 0.5) or (_rope_t > 1.5 and p.velocity.length() < 1.0):
		_touch_down()


## Hold the swing to its vertical plane: damp sideways speed and drift (a spherical pendulum would
## wander, which reads as the line being unreliable). Strafing or a wrap switches this off.
func _keep_plane(delta: float) -> void:
	var p := player
	var pn := p.up_direction.cross(_seed)
	if pn.length() < 0.1:
		return
	pn = pn.normalized()
	var lat := p.velocity.dot(pn)
	var off := (grip() - pivot()).dot(pn)
	p.velocity -= pn * (lat * minf(1.0, PLANE_DAMP * delta) + off * PLANE_PULL * delta)


## Keep the forward apex inside [BAND_MIN_DEG, BAND_MAX_DEG] by trimming speed in the lower arc.
func _govern(delta: float, n: Vector3, free: float) -> void:
	var p := player
	var up := p.up_direction
	var g := p.gravity_vector.length()
	var cos_t := -n.dot(up)
	if cos_t < cos(deg_to_rad(GOVERN_ARC_DEG)):
		return
	var h := free * (1.0 - cos_t)
	var spd := p.velocity.length()
	var e := 0.5 * spd * spd + g * h
	var e_min := g * free * (1.0 - cos(deg_to_rad(BAND_MIN_DEG)))
	var e_max := g * free * (1.0 - cos(deg_to_rad(BAND_MAX_DEG)))
	var want := spd
	if e < e_min:
		want = sqrt(maxf(2.0 * (e_min - g * h), 0.0))
	elif e > e_max:
		want = sqrt(maxf(2.0 * (e_max - g * h), 0.0))
	if is_equal_approx(want, spd):
		return
	var dir := p.velocity / spd if spd > 0.3 else (_seed - n * _seed.dot(n)).normalized()
	p.velocity = dir * move_toward(spd, want, GOVERN * delta)


## Wrap the line round posts it catches; unwrap when the previous point sees her again.
func _update_wraps() -> void:
	var g := grip()
	var c := pivot()
	if pivots.size() < 4:
		var hit := _post_hit(c, g)
		if not hit.is_empty():
			var pos: Vector3 = hit.position + (hit.normal as Vector3) * 0.15
			var seg := pos.distance_to(c)
			if seg > 0.3 and rope_len - chain_len - seg > MIN_ROPE:
				chain_len += seg
				pivots.append(pos)
				return
	if not pivots.is_empty():
		var prev := pivots[-2] if pivots.size() > 1 else anchor_node.global_position
		if _post_hit(prev, g).is_empty():
			chain_len -= (pivots[-1] - prev).length()
			pivots.pop_back()


func _post_hit(from: Vector3, to: Vector3) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1)
	q.exclude = [player.get_rid()]
	var r := player.get_world_3d().direct_space_state.intersect_ray(q)
	if r.is_empty() or not (r.collider as Node).is_in_group(&"silk_posts"):
		return {}
	return r


# --- ground, air, landing ----------------------------------------------------------------------

func _ground(delta: float) -> void:
	super.physics(delta)
	var p := player
	if p.is_on_floor():
		air_chain = 0
		var body := _floor_body()
		if body is Strand:
			_tightrope(body, delta)
			_ground_t = 0.0
		elif body != null and not body.is_in_group(&"silk_unsafe"):
			_ground_t += delta
			if _ground_t > 0.25:
				last_safe = Transform3D(Basis(p.up_direction, p.yaw), p.global_position)
				has_safe = true
	else:
		_ground_t = 0.0
		if p.is_on_wall():
			_mantle()
		_try_zip()


func _air(delta: float) -> void:
	var p := player
	var up := p.up_direction
	p.velocity += p.gravity_vector * delta
	var wish := p.wish_dir()
	if wish.length() > 0.01 and p.velocity.dot(wish) < 5.0:
		p.velocity += wish * AIR_STEER * delta
	_magnet(delta)
	p.move_and_slide()
	if p.is_on_wall() and not p.is_on_floor() and _mantle():
		return
	if _try_zip():
		return
	if p.is_on_floor() and p.velocity.dot(up) <= 0.5:
		_touch_down()


func _touch_down() -> void:
	_drop_line()
	state = GROUND
	touched_down.emit()


## Climb onto a ledge whose top is within MANTLE of the feet.
func _mantle() -> bool:
	var p := player
	var up := p.up_direction
	var n := p.get_wall_normal()
	var dir := -(n - up * n.dot(up))
	if dir.length() < 0.2:
		return false
	dir = dir.normalized()
	var before := p.global_position
	p.try_step_up(dir * 0.45, MANTLE)
	if p.global_position.distance_to(before) < 0.05:
		return false
	mantles += 1
	var h := p.velocity - up * p.velocity.dot(up)
	p.velocity = h * 0.4
	_touch_down()
	return true


## Falling just short of a ledge ahead: lean her onto it.
func _magnet(delta: float) -> void:
	var p := player
	var up := p.up_direction
	if p.velocity.dot(up) > 0.0:
		return
	var h := p.velocity - up * p.velocity.dot(up)
	if h.length() < 0.3:
		return
	var dir := h.normalized()
	if not _ray(p.global_position + up * 0.2, -up * 6.0).is_empty():
		return
	var ahead := _ray(p.global_position + dir * 1.2 + up * 0.2, -up * 3.0)
	if ahead.is_empty() or (ahead.normal as Vector3).dot(up) < 0.7:
		return
	p.velocity += dir * 6.0 * delta


func _ray(from: Vector3, by: Vector3) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, from + by, 1)
	q.exclude = [player.get_rid()]
	return player.get_world_3d().direct_space_state.intersect_ray(q)


func _floor_body() -> Node:
	var p := player
	for i: int in p.get_slide_collision_count():
		var c := p.get_slide_collision(i)
		if c.get_normal().dot(p.up_direction) > 0.7:
			return c.get_collider() as Node
	return null


func _tightrope(s: Node, delta: float) -> void:
	var p := player
	var q: Vector3 = s.call("closest", p.global_position)
	var off := p.global_position - q
	off -= p.up_direction * off.dot(p.up_direction)
	p.global_position -= off * minf(1.0, 8.0 * delta)


# --- weave, pluck, zip -------------------------------------------------------------------------

func secondary() -> void:
	if is_instance_valid(weave_from) and target and target != weave_from:
		weave(weave_from, target)
		return
	var s := aimed_strand()
	if s and (target == null or (s.call("ray_distance", eye(), aim_dir(), PLUCK_RANGE) as Array)[1] < eye().distance_to(target.global_position)):
		s.call("pluck")
		plucked.emit(s)
		return
	if target:
		weave_from = target
		wove_first.emit(target)


func aimed_strand() -> Node:
	var best: Node = null
	var best_d := PLUCK_RADIUS
	for s: Node in player.get_tree().get_nodes_in_group(&"silk_strands"):
		var rd: Array = s.call("ray_distance", eye(), aim_dir(), PLUCK_RANGE)
		if rd[0] < best_d and rd[1] > 0.5:
			best_d = rd[0]
			best = s
	return best


func weave(from: Node3D, to: Node3D) -> Node:
	weave_from = null
	var a := from.global_position
	var b := to.global_position
	if a.distance_to(b) > WEAVE_RANGE or a.distance_to(b) < 1.5:
		return null
	var q := PhysicsRayQueryParameters3D.create(a, b, 1)
	q.exclude = [player.get_rid()]
	var hit := player.get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty() and (hit.position as Vector3).distance_to(b) > 0.8 and (hit.position as Vector3).distance_to(a) > 0.8:
		return null
	var parent: Node = Game.wing if Game.wing else player.get_parent()
	var s := Strand.create(parent, a, b)
	s.set_meta(&"ends", [from, to])
	strands.append(s)
	while strands.size() > MAX_STRANDS:
		var old: Node = strands.pop_front()
		if is_instance_valid(old):
			old.queue_free()
	woven.emit(s)
	return s


func _try_zip() -> bool:
	if _zip_cool > 0.0:
		return false
	var p := player
	var g := grip()
	for s: Node in player.get_tree().get_nodes_in_group(&"silk_strands"):
		if s == _no_zip or float(s.call("slope_deg")) < ZIP_MIN_SLOPE:
			continue
		var q: Vector3 = s.call("closest", g + p.up_direction * 0.6)
		if q.distance_to(g + p.up_direction * 0.6) > ZIP_CATCH:
			continue
		var a: Vector3 = s.get("a")
		var b: Vector3 = s.get("b")
		var down := (b - a).normalized() if b.y < a.y else (a - b).normalized()
		_zip = s
		_zip_s = maxf(p.velocity.dot(down), 2.0)
		_drop_line()
		state = ZIP
		return true
	return false


func _zipping(delta: float) -> void:
	var p := player
	if not is_instance_valid(_zip):
		_leave_zip(Vector3.ZERO)
		return
	var a: Vector3 = _zip.get("a")
	var b: Vector3 = _zip.get("b")
	var low := b if b.y < a.y else a
	var down := (low - (a if low == b else b)).normalized()
	_zip_s += p.gravity_vector.dot(down) * delta
	_zip_s = minf(_zip_s * (1.0 - 0.15 * delta), 22.0)
	var hang: Vector3 = _zip.call("closest", grip() + p.up_direction * 0.6)
	var want := hang - p.up_direction * (GRIP + 0.6)
	p.velocity = down * _zip_s + (want - p.global_position) * 12.0
	p.move_and_slide()
	if hang.distance_to(low) < 0.4:
		_leave_zip(p.up_direction * 2.5)
	elif p.is_on_floor():
		_zip = null
		_touch_down()


func _leave_zip(kick: Vector3) -> void:
	var p := player
	_no_zip = _zip
	_zip_cool = 0.5
	if is_instance_valid(_zip):
		var a: Vector3 = _zip.get("a")
		var b: Vector3 = _zip.get("b")
		var down := (b - a).normalized() if b.y < a.y else (a - b).normalized()
		p.velocity = down * _zip_s + kick
	_zip = null
	state = AIR


# --- design model ------------------------------------------------------------------------------

## Closed-form release model for one governed swing, in the swing plane (x forward from the pivot,
## y up from the pivot). For each release offset (physics ticks from the forward apex, negative =
## before) it returns the release point and velocity (with the top-release flick applied) and the
## landing x at height `land_y` (relative to the pivot, measured at the grip). Used to size ledges.
static func envelope(rope: float, apex_deg: float, g: float, land_y: float, ticks: PackedInt32Array, hz: float = 120.0) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var th := deg_to_rad(apex_deg)
	for k: int in ticks:
		# integrate the pendulum from the apex (at rest) |k| ticks; before the apex it is moving forward
		var phi := th
		var w := 0.0
		var dt := 1.0 / hz
		for _i: int in absi(k):
			w -= g / rope * sin(phi) * dt
			phi += w * dt
		var spd := absf(w) * rope
		var fwd := 1.0 if k < 0 else -1.0  # before the apex she still moves forward and up
		var pos := Vector2(rope * sin(phi), -rope * cos(phi))
		var vel := Vector2(cos(phi), sin(phi)) * spd * fwd
		var top := spd < FLICK_SPEED and phi > deg_to_rad(FLICK_MIN_DEG)
		if top:
			vel += Vector2(FLICK_FWD, FLICK_UP)
		var disc := vel.y * vel.y + 2.0 * g * (pos.y - land_y)
		var t := (vel.y + sqrt(maxf(disc, 0.0))) / g
		out.append({"ticks": k, "phi": rad_to_deg(phi), "pos": pos, "vel": vel, "top": top, "land_x": pos.x + vel.x * t, "flight": t})
	return out
