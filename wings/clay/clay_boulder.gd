class_name ClayBoulder
extends RigidBody3D
## A lump of clay that rolls on the heightfield. Pulling the ground behind it tilts it into the
## trench. Pressing it squashes it over a few seconds; once flat enough it freezes into a bridge.

signal flattened

const FLAT_Y := 0.32
const SQUASH_TIME := 1.6

var visual: Node3D
var _squash: float = 0.0
var flat: bool = false


func _init() -> void:
	mass = 35.0
	linear_damp = 0.25
	angular_damp = 0.6
	collision_layer = 1 << 4
	collision_mask = 1 | (1 << 1) | (1 << 4)
	continuous_cd = true


func setup(model: Node3D) -> void:
	visual = model
	add_child(model)
	var cs := CollisionShape3D.new()
	cs.name = "Ball"
	var sph := SphereShape3D.new()
	sph.radius = 1.15
	cs.shape = sph
	add_child(cs)


func in_trench() -> bool:
	return not flat and global_position.z < -2.6 and global_position.z > -6.4 and global_position.y < 0.2


## Called on the world beat while the player holds secondary on it.
func press(dt: float) -> void:
	if flat or not in_trench():
		return
	_squash = minf(_squash + dt / SQUASH_TIME, 1.0)
	visual.scale = Vector3(1.0, lerpf(1.0, FLAT_Y, _squash), 1.0)
	if _squash >= 1.0:
		_become_bridge()


func _become_bridge() -> void:
	flat = true
	var cs := get_node("Ball") as CollisionShape3D
	var bx := BoxShape3D.new()
	bx.size = Vector3(2.3, FLAT_Y * 2.0, 2.4)
	cs.shape = bx
	cs.position = Vector3(0, 0.0, 0)
	freeze = true
	sleeping = true
	flattened.emit()
