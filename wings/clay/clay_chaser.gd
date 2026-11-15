class_name ClayChaser
extends Node3D
## The Unfinished One: a half-made figure that follows the player across the clay ground.
## It only moves on the world beat, one step at a time, and cannot climb a wall taller than
## MAX_STEP, so pulling a wall between you and it is a real escape. It gives up after a while.

signal caught

const STRIDE := 0.42
const MAX_STEP := 0.45
const CATCH_DIST := 1.35
const GIVE_UP_BEATS := 300  # about 25 s of world time

var terrain: ClayTerrain
var state: StringName = &"waiting"  # waiting | chase | idle | done
var _chase_beats: int = 0


func setup(t: ClayTerrain, model: Node3D) -> void:
	terrain = t
	add_child(model)


func start_chase() -> void:
	if state == &"waiting":
		state = &"chase"
		_chase_beats = 0


func beat(player_pos: Vector3) -> void:
	if state != &"chase":
		return
	_chase_beats += 1
	var here := global_position
	var to := Vector3(player_pos.x - here.x, 0.0, player_pos.z - here.z)
	var dist := to.length()
	if dist < CATCH_DIST:
		state = &"idle"
		caught.emit()
		return
	if _chase_beats > GIVE_UP_BEATS:
		state = &"idle"
		return
	var dir := to / dist
	var nxt := here + dir * STRIDE
	var rise := terrain.height_at(nxt.x, nxt.z) - terrain.height_at(here.x, here.z)
	if rise <= MAX_STEP:
		global_position = Vector3(nxt.x, terrain.height_at(nxt.x, nxt.z), nxt.z)
		rotation.y = atan2(-dir.x, -dir.z)
	else:
		# blocked by a wall: try the two diagonals
		for ang in [0.7, -0.7]:
			var d2: Vector3 = dir.rotated(Vector3.UP, ang)
			var n2 := here + d2 * STRIDE
			if terrain.height_at(n2.x, n2.z) - terrain.height_at(here.x, here.z) <= MAX_STEP:
				global_position = Vector3(n2.x, terrain.height_at(n2.x, n2.z), n2.z)
				rotation.y = atan2(-d2.x, -d2.z)
				return
	global_position.y = terrain.height_at(global_position.x, global_position.z)


## Put it on the ground at a point (used at setup and when loading a save).
func place(x: float, z: float) -> void:
	global_position = Vector3(x, terrain.height_at(x, z), z)
