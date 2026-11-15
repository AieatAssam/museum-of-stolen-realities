class_name SeatedMode
extends MovementMode
## Sit on something (benches). Set `seat` (a Node3D whose -Z faces the view) before switching in.
## Any movement, jump or interact stands up again.

var seat: Node3D
var exit_mode: StringName = &"walk"
var _stand_from: Vector3
var _t: float = 0.0


func enter(_from: MovementMode) -> void:
	_stand_from = player.global_position
	_t = 0.0
	player.velocity = Vector3.ZERO
	player.collision_mask_world(false)
	Audio.sfx(Audio.stream("cloth"), player.global_position, -6.0)


func exit(_to: MovementMode) -> void:
	player.global_position = _stand_from
	player.collision_mask_world(true)


func physics(delta: float) -> void:
	_t += delta
	var target := seat.global_position
	player.global_position = player.global_position.lerp(target, 1.0 - exp(-6.0 * delta))
	if _t > 0.6 and (player.move_input().length() > 0.3):
		player.set_mode(exit_mode)


func on_verb(verb: StringName, pressed: bool) -> bool:
	if pressed and _t > 0.6 and verb == &"jump":
		player.set_mode(exit_mode)
	return true


func bob_scale() -> float:
	return 0.0


func eye_height() -> float:
	return 1.15
