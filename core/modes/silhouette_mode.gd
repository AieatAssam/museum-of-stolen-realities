class_name SilhouetteMode
extends WalkMode
## Fast, low, flat movement (noir SHADOWSTEPPING). `is_blocked` lets the wing veto positions
## (e.g. "light is a wall"): Callable(world_pos: Vector3) -> bool. Blocked moves are reverted.

var is_blocked: Callable = func(_pos: Vector3) -> bool: return false


func _init() -> void:
	walk_speed = 7.5
	sprint_speed = 11.0
	ground_accel = 18.0
	jump_speed = 0.0


func physics(delta: float) -> void:
	var before := player.global_position
	super.physics(delta)
	if is_blocked.call(player.global_position):
		player.global_position = before
		player.velocity = Vector3.ZERO


func eye_height() -> float:
	return 0.55


func bob_scale() -> float:
	return 0.2
