extends WalkMode
## Example custom movement mode owned by a wing: floaty low-gravity walking with a tall jump.
## Registered in template.gd via player.add_mode(&"float", FloatMode.new()).


func _init() -> void:
	jump_speed = 7.5
	air_accel = 5.0
	walk_speed = 3.6


func physics(delta: float) -> void:
	# Gravity is set by the wing (set_gravity); this mode just adds a gentle hover at the apex.
	if not player.is_on_floor() and player.velocity.dot(player.up_direction) < 0.0:
		player.velocity -= player.gravity_vector * delta * 0.5
	super.physics(delta)


func bob_scale() -> float:
	return 0.4
