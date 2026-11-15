class_name SwimMode
extends MovementMode
## Swim / float: free 3D movement along the camera's look, buoyancy against gravity, heavy drag.
## jump = rise, crouch = sink. `buoyancy` 1.0 cancels gravity exactly.

var speed: float = 4.5
var accel: float = 3.0
var drag: float = 1.6
var buoyancy: float = 0.92


func physics(delta: float) -> void:
	var p := player
	var mi := p.move_input()
	var cam := p.camera.global_basis
	var wish := (cam * Vector3(mi.x, 0.0, mi.y))
	if p.action_held(&"jump"):
		wish += p.up_direction
	if p.action_held(&"crouch"):
		wish -= p.up_direction
	wish = wish.limit_length(1.0) * speed
	p.velocity = p.velocity.lerp(wish, 1.0 - exp(-accel * delta))
	p.velocity += p.gravity_vector * (1.0 - buoyancy) * delta
	p.velocity *= exp(-drag * delta * 0.25)
	p.move_and_slide()


func on_verb(verb: StringName, _pressed: bool) -> bool:
	return verb == &"jump" or verb == &"crouch"


func bob_scale() -> float:
	return 0.0
