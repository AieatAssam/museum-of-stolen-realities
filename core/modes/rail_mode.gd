class_name RailMode
extends MovementMode
## Ride along a Path3D (paint strokes, light beams, wires). Forward input accelerates along the
## rail's travel direction; jump leaves the rail with momentum and returns to `exit_mode`.
## Set `rail` before switching to this mode.

var rail: Path3D
var exit_mode: StringName = &"walk"
var speed: float = 9.0
var max_speed: float = 18.0
var ride_height: float = 0.1
var offset: float = 0.0
var _speed: float = 0.0
var _dir: float = 1.0


func enter(_from: MovementMode) -> void:
	if rail == null:
		player.set_mode.call_deferred(exit_mode)
		return
	var local := rail.to_local(player.global_position)
	offset = rail.curve.get_closest_offset(local)
	var tangent := _tangent()
	_dir = 1.0 if player.velocity.dot(tangent) >= 0.0 else -1.0
	_speed = maxf(absf(player.velocity.dot(tangent)), speed)


func _tangent() -> Vector3:
	var c := rail.curve
	var a := rail.to_global(c.sample_baked(maxf(offset - 0.1, 0.0)))
	var b := rail.to_global(c.sample_baked(minf(offset + 0.1, c.get_baked_length())))
	return (b - a).normalized()


func physics(delta: float) -> void:
	var c := rail.curve
	_speed = clampf(_speed + (-player.move_input().y) * 6.0 * delta, 2.0, max_speed)
	offset += _speed * _dir * delta
	var t := _tangent() * _dir
	if offset <= 0.0 or offset >= c.get_baked_length():
		player.velocity = t * _speed
		player.set_mode(exit_mode)
		return
	var pos := rail.to_global(c.sample_baked(offset)) + player.up_direction * ride_height
	player.velocity = (pos - player.global_position) / maxf(delta, 0.0001)
	player.global_position = pos


func on_verb(verb: StringName, pressed: bool) -> bool:
	if verb == &"jump" and pressed:
		player.velocity = _tangent() * _dir * _speed + player.up_direction * 5.0
		player.set_mode(exit_mode)
		return true
	return false


func bob_scale() -> float:
	return 0.0
