extends MovementMode
## Vesper while The Drowned Aria is playing. Ground movement with inertia and air drag, plus the
## singing-gravity field summed from every sounding Instrument at her position. The wing's gravity
## vector is never changed here, so the body never rolls; only her velocity is bent by the field.
## Primary = strike the instrument you are aiming at. Secondary = hold the note you struck nearby
## (breath-limited; releasing refills the breath).

const Instrument := preload("res://wings/aria/instrument.gd")

var walk_speed: float = 4.2
var ground_accel: float = 12.0
var air_accel: float = 2.6
var jump_speed: float = 4.6
var air_drag: float = 1.1          # 1/s, applied to horizontal and vertical velocity in the air
var breath_max: float = 6.0
var breath: float = 6.0
var last_struck: Node3D
var _holding: bool = false
var _jump_pressed: bool = false
var _since_floor: float = 0.0


func enter(_from: MovementMode) -> void:
	breath = breath_max


func exit(_to: MovementMode) -> void:
	_release_hold()


func physics(delta: float) -> void:
	var p := player
	var up := p.up_direction
	var on_floor := p.is_on_floor()
	_since_floor = 0.0 if on_floor else _since_floor + delta
	_update_hold(delta)

	var wish := p.wish_dir() * walk_speed
	var vertical := up * p.velocity.dot(up)
	var horizontal := p.velocity - vertical
	var rate := ground_accel if on_floor else air_accel
	horizontal = horizontal.lerp(wish, 1.0 - exp(-rate * delta))

	if on_floor and vertical.dot(up) <= 0.0:
		vertical = Vector3.ZERO
	if not on_floor:
		var drag := exp(-air_drag * delta)
		horizontal *= drag
		vertical *= drag
	# the singing-gravity field is acceleration on top of the constant wing gravity
	vertical += (p.gravity_vector + up * _field_at(p.global_position)) * delta

	if _jump_pressed and (on_floor or _since_floor < 0.1):
		vertical = up * jump_speed
		_jump_pressed = false
		p.jumped.emit()
	p.velocity = horizontal + vertical
	if on_floor and horizontal.length() > 0.1:
		p.try_step_up(horizontal * delta, 0.38)
	p.move_and_slide()


func _field_at(pos: Vector3) -> float:
	var total := 0.0
	for inst: Node in player.get_tree().get_nodes_in_group(Instrument.GROUP):
		total += (inst as Node3D).field_at(pos)
	return total


func on_verb(verb: StringName, pressed: bool) -> bool:
	match verb:
		&"primary":
			if pressed:
				var target := _aimed()
				if target:
					target.strike()
					last_struck = target
			return true
		&"secondary":
			_holding = pressed
			return true
		&"jump":
			if pressed:
				_jump_pressed = true
			return true
		_:
			return false


func _aimed() -> Node3D:
	var cam := player.camera
	var fwd := -cam.global_basis.z
	var best: Node3D = null
	var best_score := 0.9
	for inst: Node in player.get_tree().get_nodes_in_group(Instrument.GROUP):
		var n := inst as Node3D
		var to := n.global_position + Vector3.UP * 1.5 - cam.global_position
		var dist := to.length()
		if dist > 14.0 or dist < 0.5:
			continue
		var score := fwd.dot(to / dist) - dist * 0.004
		if score > best_score:
			best_score = score
			best = n
	return best


func _update_hold(delta: float) -> void:
	# one held note: the struck instrument nearest Vesper stays sustained while breath lasts
	var holding_now := _holding and breath > 0.0
	if holding_now:
		breath = maxf(breath - delta, 0.0)
	else:
		breath = minf(breath + delta * 1.5, breath_max)
	var target: Node3D = null
	if holding_now and last_struck and is_instance_valid(last_struck):
		if last_struck.global_position.distance_to(player.global_position) < 9.0:
			target = last_struck
	for inst: Node in player.get_tree().get_nodes_in_group(Instrument.GROUP):
		(inst as Node3D).held = inst == target


func _release_hold() -> void:
	_holding = false
	if player == null or not player.is_inside_tree():
		return
	for inst: Node in player.get_tree().get_nodes_in_group(Instrument.GROUP):
		(inst as Node3D).held = false


func bob_scale() -> float:
	return 0.6
