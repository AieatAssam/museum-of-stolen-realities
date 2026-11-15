class_name ConstrainedMode
extends MovementMode
## Base for modes that hold the player to something: a rope or pendulum (GrappleMode), a rail or
## zipline (RailMode), a ladder, a ledge. The base owns letting go; you write the constraint.
## Hooks (override what you need):
##   attach() -> bool        on enter. Return false when there is nothing to hold (bounces back to
##                           exit_mode next frame).
##   step(delta)             every physics tick while attached. Move the player (set velocity and
##                           move_and_slide(), or set global_position); call release(v) to let go.
##   release_velocity()      velocity when a release verb is pressed (default: keep velocity and
##                           add `release_jump` up).
## Set `exit_mode` (default walk) and `release_verbs` (default jump). `released` fires on let-go.
## Demo: the zipline in wings/_template (a RailMode on a Path3D, grabbed with interact).

signal released

var exit_mode: StringName = &"walk"
var release_verbs: Array[StringName] = [&"jump"]
var release_jump: float = 3.0


func attach() -> bool:
	return true


func step(_delta: float) -> void:
	pass


func release_velocity() -> Vector3:
	return player.velocity + player.up_direction * release_jump


## Let go with velocity `v` and switch to exit_mode.
func release(v: Vector3) -> void:
	player.velocity = v
	player.set_mode(exit_mode)
	released.emit()


func enter(_from: MovementMode) -> void:
	if not attach():
		player.set_mode.call_deferred(exit_mode)


func physics(delta: float) -> void:
	step(delta)


func on_verb(verb: StringName, pressed: bool) -> bool:
	if pressed and verb in release_verbs:
		release(release_velocity())
		return true
	return false


func bob_scale() -> float:
	return 0.0
