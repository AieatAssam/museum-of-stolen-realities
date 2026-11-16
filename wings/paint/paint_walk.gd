extends WalkMode
## Vesper on foot in the Unfinished Wing (registered as &"paint", the wing's start mode).
## Walking, plus:
##  - the magnet: stepping onto, or falling within MAGNET m of, a wet stroke boards it (&"surf").
##  - carried momentum: thrown or jumped off a stroke she keeps her speed through the air (no air
##    drag pulling it to walking pace), so jump arcs read the same every time.
##  - green foliage: inside a climb column, forward climbs.

const MAGNET := 1.25
const MAGNET_DY_AIR := Vector2(-0.7, 1.6)    # feet minus stroke top, while descending
const MAGNET_DY_FLOOR := Vector2(-0.45, 1.3) # while walking (step down onto a lower stroke)
const AIR_CONTROL := 3.0
const CLIMB := 4.0

var surf                    # surf_mode.gd (untyped: preload cycles)
## Callable(feet: Vector3, radius: float) -> Array [stroke, s, dist] or [].
var find_rail: Callable
## Callable(pos: Vector3) -> float: climb column top height, or NAN when not in foliage.
var climb_top: Callable
var momentum: bool = false
var climbing: bool = false
var _ignore: Node3D
var _ignore_ticks: int = 0
var _ignore_far: bool = false


func _init() -> void:
	walk_speed = 4.4
	sprint_speed = 7.2
	coyote_time = 0.12


func enter(from: MovementMode) -> void:
	if from == surf and surf:
		momentum = true
		_ignore = surf.last_left
		_ignore_far = surf.last_leave_tick < 0   # crouched off: ignore until she is clear of it
		_ignore_ticks = 36


func physics(delta: float) -> void:
	var p := player
	var up := p.up_direction
	if _ignore_ticks > 0:
		_ignore_ticks -= 1
	# foliage
	var top: float = climb_top.call(p.global_position) if climb_top.is_valid() else NAN
	climbing = not is_nan(top) and p.move_input().y < -0.2 and p.global_position.y < top
	if climbing:
		momentum = false
		p.velocity = up * CLIMB   # straight up: drifting would walk her out of the column
		if p.global_position.y > top - 0.3:
			var fwd := (-p.head.global_basis.z).slide(up).normalized()
			p.velocity = up * 4.5 + fwd * 4.5   # over the lip, clear of the column's hole
		p.move_and_slide()
		return
	# magnet
	var vy := p.velocity.dot(up)
	if find_rail.is_valid() and (vy < 0.5 or p.is_on_floor()):
		var hit: Array = find_rail.call(p.global_position, MAGNET)
		if not hit.is_empty() and _may_board(hit, p.is_on_floor()):
			surf.pending = [hit[0], hit[1]]
			momentum = false
			p.set_mode(&"surf")
			return
	if _ignore_far and is_instance_valid(_ignore):
		var c: Array = _ignore.closest(p.global_position)
		if float(c[1]) > 2.5:
			_ignore = null
			_ignore_far = false
	# carried momentum through the air (is_on_floor is stale here: surf moves her without sliding)
	if momentum:
		var vert := up * vy + p.gravity_vector * delta
		var hor := p.velocity - up * vy
		hor += p.wish_dir() * AIR_CONTROL * delta
		p.velocity = hor + vert
		p.move_and_slide()
		if p.is_on_floor():
			momentum = false
		return
	momentum = false
	super.physics(delta)


## The wing's verb, taught where it can be used: a wet stroke ahead, until she has ridden one.
func prompt() -> Dictionary:
	var p := player
	if surf == null or surf.metres > 0.0 or not find_rail.is_valid() or not p.is_on_floor():
		return {}
	var fwd := (-p.head.global_basis.z).slide(p.up_direction).normalized()
	if (find_rail.call(p.global_position + fwd * 4.0, 4.0) as Array).is_empty():
		return {}
	return {"action": &"move_forward", "text": "walk onto the wet paint to ride it"}


func _may_board(hit: Array, on_floor: bool) -> bool:
	var st: Node3D = hit[0]
	if st == _ignore and (_ignore_ticks > 0 or _ignore_far):
		return false
	var top: Vector3 = st.sample(float(hit[1]))
	var dy := player.global_position.y - top.y
	var r := MAGNET_DY_FLOOR if on_floor else MAGNET_DY_AIR
	return dy >= r.x and dy <= r.y
