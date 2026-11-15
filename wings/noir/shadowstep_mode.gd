class_name ShadowstepMode
extends SilhouetteMode
## SHADOWSTEP, the noir rule. The player moves low and flat and may only stand where no light
## reaches the head. Stepping into light ejects them to the last dark point they occupied.
## Secondary latches onto a dark surface in front (gravity follows its normal); secondary again
## lets go and restores the wing's gravity.

signal latched_changed(on: bool)
signal ejected

const LATCH_RANGE := 4.0
const LATCH_GRAVITY := 15.0

var last_dark: Vector3 = Vector3.ZERO
var has_dark: bool = false
var latched: bool = false


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
	var to := from + (-p.head.global_basis.z) * LATCH_RANGE
	var q := PhysicsRayQueryParameters3D.create(from, to, 1, ex)
	var hit := p.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return false
	var n: Vector3 = hit["normal"]
	var at: Vector3 = hit["position"]
	if ShadowField.lit(p, at + n * 0.2, ex):
		return false
	latched = true
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
