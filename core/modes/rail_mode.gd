class_name RailMode
extends ConstrainedMode
## Ride along a Path3D (paint strokes, light beams, wires, ziplines). Forward input accelerates
## along the rail's travel direction; jump leaves the rail with momentum, and so does reaching
## either end. Set `rail` before switching to this mode.

var rail: Path3D
var speed: float = 9.0
var max_speed: float = 18.0
var ride_height: float = 0.1
var offset: float = 0.0
var _speed: float = 0.0
var _dir: float = 1.0


func _init() -> void:
	release_jump = 5.0


func attach() -> bool:
	if rail == null:
		return false
	offset = rail.curve.get_closest_offset(rail.to_local(player.global_position))
	var tangent := _tangent()
	_dir = 1.0 if player.velocity.dot(tangent) >= 0.0 else -1.0
	var length := rail.curve.get_baked_length()
	if offset < 0.5:  # grabbed at an end: always ride into the rail, not straight off it
		_dir = 1.0
	elif offset > length - 0.5:
		_dir = -1.0
	_speed = maxf(absf(player.velocity.dot(tangent)), speed)
	return true


func _tangent() -> Vector3:
	var c := rail.curve
	var a := rail.to_global(c.sample_baked(maxf(offset - 0.1, 0.0)))
	var b := rail.to_global(c.sample_baked(minf(offset + 0.1, c.get_baked_length())))
	return (b - a).normalized()


func step(delta: float) -> void:
	var c := rail.curve
	_speed = clampf(_speed + (-player.move_input().y) * 6.0 * delta, 2.0, max_speed)
	offset += _speed * _dir * delta
	if offset <= 0.0 or offset >= c.get_baked_length():
		release(_tangent() * _dir * _speed)
		return
	var pos := rail.to_global(c.sample_baked(offset)) + player.up_direction * ride_height
	player.velocity = (pos - player.global_position) / maxf(delta, 0.0001)
	player.global_position = pos


func release_velocity() -> Vector3:
	return _tangent() * _dir * _speed + player.up_direction * release_jump
