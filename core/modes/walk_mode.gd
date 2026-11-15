class_name WalkMode
extends MovementMode
## Default ground movement: smoothed acceleration, sprint, crouch, coyote time, jump buffer,
## step-up, slope handling. Subclass and tweak the exported-style vars for wing variants.

var walk_speed: float = 4.0
var sprint_speed: float = 6.8
var crouch_speed: float = 2.0
var ground_accel: float = 14.0   # fast attack (exponential approach rate, 1/s)
var ground_decel: float = 8.5    # longer release
var air_accel: float = 2.2
var jump_speed: float = 4.9
var coyote_time: float = 0.10
var jump_buffer: float = 0.10
var corner_nudge: float = 0.22   # sideways correction when a jump clips a ceiling edge
var step_height: float = Player.STEP_HEIGHT

var crouching: bool = false
var _since_floor: float = 0.0
var _since_jump_press: float = 99.0
var _jumped: bool = false


func physics(delta: float) -> void:
	var p := player
	var up := p.up_direction
	var on_floor := p.is_on_floor()
	_since_floor = 0.0 if on_floor else _since_floor + delta
	_since_jump_press += delta
	if on_floor:
		_jumped = false

	crouching = p.action_held(&"crouch") or (crouching and not p.can_stand())
	p.set_crouched(crouching)

	var speed := crouch_speed if crouching else (sprint_speed if p.action_held(&"sprint") and p.move_input().y < -0.2 else walk_speed)
	var wish := p.wish_dir() * speed
	var vertical := up * p.velocity.dot(up)
	var horizontal := p.velocity - vertical
	var rate := (ground_accel if wish.length() > 0.01 else ground_decel) if on_floor else air_accel
	horizontal = horizontal.lerp(wish, 1.0 - exp(-rate * delta))

	if on_floor:
		vertical = Vector3.ZERO
	vertical += p.gravity_vector * delta

	if _since_jump_press < jump_buffer and _since_floor < coyote_time and not _jumped:
		vertical = up * jump_speed
		_jumped = true
		_since_jump_press = 99.0
		_since_floor = 99.0
		p.jumped.emit()

	p.velocity = horizontal + vertical
	if on_floor and horizontal.length() > 0.1:
		p.try_step_up(horizontal * delta, step_height)
	if vertical.dot(up) > 0.5:
		p.try_corner_correct(vertical * delta, corner_nudge)
	p.move_and_slide()


func on_verb(verb: StringName, pressed: bool) -> bool:
	if verb == &"jump" and pressed:
		_since_jump_press = 0.0
		return true
	return false


func eye_height() -> float:
	return 1.05 if crouching else 1.62
