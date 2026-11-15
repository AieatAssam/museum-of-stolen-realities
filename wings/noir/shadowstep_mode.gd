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

var last_dark: Vector3 = Vector3.ZERO
var has_dark: bool = false
var latched: bool = false
## The ray hit of the last latch (collider, normal, position), read by the wing when latched_changed fires.
var hit: Dictionary = {}


func enter(_from: MovementMode) -> void:
	latched = false


func exit(_to: MovementMode) -> void:
	if latched:
		release()


func physics(delta: float) -> void:
	super.physics(delta)
	var p := player
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


func _lit_here() -> bool:
	var ex: Array[RID] = [player.get_rid()]
	return ShadowField.lit(player, player.head.global_position, ex)
