class_name ShadowstepMode
extends SilhouetteMode
## SHADOWSTEP, the noir rule. The player moves low and flat and may only stand where no light
## reaches the head. Stepping into light ejects them to the last dark point they occupied.
## Secondary latches onto a dark surface in front (gravity follows its normal); secondary again
## lets go and restores the wing's gravity.

signal latched_changed(on: bool)
signal ejected

const LATCH_RANGE := 5.0
const LATCH_GRAVITY := 15.0
const EDGE := 0.6  # how far inside the latched face's edges the climb stops

var last_dark: Vector3 = Vector3.ZERO
var has_dark: bool = false
var latched: bool = false
## The ray hit of the last latch (collider, normal, position), read by the wing when latched_changed fires.
var hit: Dictionary = {}


func enter(_from: MovementMode) -> void:
	latched = false


func reset() -> void:
	if latched:
		release()
	has_dark = false  # the last dark point belongs to the place she left


func exit(_to: MovementMode) -> void:
	if latched:
		release()


func physics(delta: float) -> void:
	var p := player
	# a respawn (or anything else) that restored the wing's gravity has ended the latch
	if latched and p.gravity_vector != Vector3.ZERO and not p.gravity_vector.is_equal_approx(-(hit["normal"] as Vector3) * LATCH_GRAVITY):
		latched = false
		latched_changed.emit(false)
	var before := p.global_position
	var off_before := _off_face(before)
	super.physics(delta)
	# once on the face, a move that takes her further off it (past its top or a side edge) is undone
	if off_before >= 0 and _off_face(p.global_position) > off_before:
		p.global_position = before
		p.velocity = Vector3.ZERO
	if _lit_here():
		if has_dark:
			p.global_position = last_dark
			p.velocity = Vector3.ZERO
			ejected.emit()
		return
	last_dark = p.global_position
	has_dark = true


func on_verb(verb: StringName, pressed: bool) -> bool:
	if verb != &"secondary" or not pressed:
		return false
	if latched:
		release()
	else:
		try_latch()
	return true


## Shown while a dark wall is in latch reach (and how to let go once latched).
func prompt() -> Dictionary:
	if latched:
		return {"action": &"secondary", "text": "let go (the wall ends at its top)"}
	var p := player
	if p.camera == null:
		return {}
	var ex: Array[RID] = [p.get_rid()]
	var from := p.head.global_position
	var q := PhysicsRayQueryParameters3D.create(from, from - p.camera.global_basis.z * LATCH_RANGE, 1, ex)
	var res := p.get_world_3d().direct_space_state.intersect_ray(q)
	if res.is_empty() or (res["normal"] as Vector3).dot(p.up_direction) > 0.7:
		return {}  # floors are no use to cling to
	if ShadowField.lit(p, (res["position"] as Vector3) + (res["normal"] as Vector3) * 0.2, ex):
		return {}
	return {"action": &"secondary", "text": "cling to the dark wall"}


func try_latch() -> bool:
	var p := player
	var ex: Array[RID] = [p.get_rid()]
	var from := p.head.global_position
	# along the view (pitch included): `head` only yaws, so a level ray could not reach down across the
	# gap to the lower near roof. The wing checks which body was hit (`hit`), so the view down at the
	# roof underfoot is an ordinary latch, never a crossing.
	var to := from + (-p.camera.global_basis.z) * LATCH_RANGE
	var q := PhysicsRayQueryParameters3D.create(from, to, 1, ex)
	var res := p.get_world_3d().direct_space_state.intersect_ray(q)
	if res.is_empty():
		return false
	var n: Vector3 = res["normal"]
	var at: Vector3 = res["position"]
	if ShadowField.lit(p, at + n * 0.2, ex):
		return false
	latched = true
	hit = res
	p.gravity_vector = -n * LATCH_GRAVITY
	latched_changed.emit(true)
	return true


func release() -> void:
	latched = false
	player.gravity_vector = Game.wing.gravity
	latched_changed.emit(false)


## While latched and standing on the face: how many of five probes (the body's centre and EDGE
## round it, along the face) are not over the latched body along gravity; -1 when not applicable.
## The climb may never raise it, so she stops short of the top and of the side edges, and lets go
## into the alley rather than onto the wall's top. Zero gravity is a scripted traversal (the roof gap).
func _off_face(pos: Vector3) -> int:
	var p := player
	if not latched or p.gravity_vector == Vector3.ZERO or not p.is_on_floor():
		return -1
	var down := p.gravity_vector.normalized()
	var side := (p.global_basis.x - down * p.global_basis.x.dot(down)).normalized()
	var along := side.cross(down)
	var n := 0
	for o: Vector3 in [Vector3.ZERO, side * EDGE, -side * EDGE, along * EDGE, -along * EDGE]:
		var from := pos + o - down * 0.5
		var q := PhysicsRayQueryParameters3D.create(from, from + down * 1.5, 1, [p.get_rid()] as Array[RID])
		var res := p.get_world_3d().direct_space_state.intersect_ray(q)
		if res.is_empty() or res["collider"] != hit.get("collider"):
			n += 1
	return n


func _lit_here() -> bool:
	var ex: Array[RID] = [player.get_rid()]
	return ShadowField.lit(player, player.head.global_position, ex)
