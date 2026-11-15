extends ConstrainedMode
## WET PAINT: Vesper surfs a wet stroke like a rail (registered as &"surf"; paint_walk.gd boards it).
## Feel (DESIGN_RULES §3 "speed builds on entry and bleeds slowly; tight jump arcs off rails"):
##  - entry: speed jumps to max(carried speed along the stroke, BASE) + ENTRY; red/orange shove more.
##  - chaining: boarding within CHAIN_TICKS of leaving another stroke adds CHAIN per link (capped).
##  - riding: forward input builds toward the colour's cap; no input bleeds BLEED m/s per second;
##    downhill adds, uphill takes (gravity along the stroke, halved); back input brakes.
##  - jump: tight and fixed (JUMP up, all the speed carried forward); at an impasto ridge, +KICK up.
##  - crouch: step off sideways without jumping.
##  - the end of a stroke: if another stroke starts there, she flows onto it (the branch nearest the
##    look direction); otherwise she is thrown off its end with her speed.
## Primary/secondary are NOT consumed: the painter's knife works mid-ride.

const BASE := 8.0
const ENTRY := 2.0
const SHOVE := 4.0          # extra entry speed on hot (red/orange) paint
const CHAIN := 1.5
const CHAIN_TICKS := 150    # 1.25 s at 120 Hz
const CAP := 15.0
const HOT_CAP := 22.0
const ACCEL := 5.0
const BLEED := 0.6
const OVERCAP_BLEED := 0.8  # 1/s, the boost above the cap fades slowly
const BRAKE := 8.0
const MIN_SPEED := 3.0
const JUMP := 5.5
const KICK := 5.0
const LAUNCH_UP := 1.0

var stroke: Node3D          # stroke.gd
var s: float = 0.0
var dir: float = 1.0
var speed: float = 0.0
var chain: int = 0
var last_leave_tick: int = -100000
var last_left: Node3D
var pending: Array = []     # [stroke, s] set by paint_walk before set_mode(&"surf")
## Callable(stroke, at_start: bool, look: Vector3) -> Array [next_stroke, s, dir] or [].
var connect_at: Callable
## Callable(event: String, data: Variant) for the wing (weather, sound, tests).
var on_event: Callable
var metres: float = 0.0     # surfed in total (tests and weather read it)
var kicked: bool = false


func _init() -> void:
	exit_mode = &"paint"
	release_verbs = []


func _cap() -> float:
	return HOT_CAP if stroke.is_hot(stroke.colour) else CAP


func _emit(ev: String, data: Variant = null) -> void:
	if on_event.is_valid():
		on_event.call(ev, data)


func attach() -> bool:
	if pending.is_empty() or not is_instance_valid(pending[0]):
		return false
	stroke = pending[0]
	s = float(pending[1])
	pending = []
	var p := player
	var t: Vector3 = stroke.tangent(s)
	var hv := p.velocity - p.up_direction * p.velocity.dot(p.up_direction)
	if hv.length() > 1.0:
		dir = 1.0 if hv.dot(t) >= 0.0 else -1.0
	else:
		var look := -p.head.global_basis.z
		dir = 1.0 if look.dot(t) >= 0.0 else -1.0
	if s < 0.6:
		dir = 1.0
	elif s > stroke.length - 0.6:
		dir = -1.0
	var now := Engine.get_physics_frames()
	if now - last_leave_tick <= CHAIN_TICKS and last_left != stroke:
		chain += 1
	else:
		chain = 1
	speed = maxf(absf(hv.dot(t)), BASE) + ENTRY + (SHOVE if stroke.is_hot(stroke.colour) else 0.0)
	speed += CHAIN * minf(chain - 1, 4)
	_emit("board", stroke)
	return true


func step(delta: float) -> void:
	var p := player
	if not is_instance_valid(stroke) or not stroke.surfable():
		_leave(p.velocity, false)
		return
	var t: Vector3 = stroke.tangent(s) * dir
	var cap := _cap()
	speed += p.gravity_vector.dot(t) * 0.5 * delta
	var fwd := -p.move_input().y
	if fwd > 0.2:
		speed += ACCEL * delta * maxf(1.0 - speed / cap, 0.0)
	else:
		speed -= BLEED * delta
	if fwd < -0.2:
		speed -= BRAKE * delta
	if speed > cap:
		speed -= (speed - cap) * OVERCAP_BLEED * delta
	speed = maxf(speed, MIN_SPEED)
	s += speed * dir * delta
	metres += speed * delta
	if s < 0.0 or s > stroke.length:
		var at_start := s < 0.0
		var nxt: Array = connect_at.call(stroke, at_start, -p.head.global_basis.z) if connect_at.is_valid() else []
		if not nxt.is_empty():
			var over := absf(s - (0.0 if at_start else stroke.length))
			stroke = nxt[0]
			dir = float(nxt[2])
			s = float(nxt[1]) + over * dir
			_emit("flow", stroke)
		else:
			s = clampf(s, 0.0, stroke.length)
			_leave(t * speed + p.up_direction * LAUNCH_UP, true)
			return
	var pos: Vector3 = stroke.sample(s) + p.up_direction * 0.03
	p.velocity = (pos - p.global_position) / maxf(delta, 0.0001)
	p.global_position = pos


func _leave(v: Vector3, chainable: bool) -> void:
	last_left = stroke
	last_leave_tick = Engine.get_physics_frames() if chainable else -100000
	_emit("leave", stroke)
	release(v)


func on_verb(verb: StringName, pressed: bool) -> bool:
	if not pressed or not is_instance_valid(stroke):
		return false
	if verb == &"jump":
		var t: Vector3 = stroke.tangent(s) * dir
		kicked = stroke.kick_near(s)
		var up := JUMP + (KICK if kicked else 0.0)
		if kicked:
			_emit("kick", stroke)
		player.jumped.emit()
		_leave(t * speed + player.up_direction * up, true)
		return true
	if verb == &"crouch":
		_leave(player.velocity * 0.5, false)
		return true
	return false


func bob_scale() -> float:
	return 0.0
