class_name ClayBoulder
extends RigidBody3D
## A lump of clay that rolls on the heightfield. Pulling the ground behind it tilts it into the
## trench. Pressing it squashes it over a few seconds; once flat enough it freezes into a bridge.

signal flattened

const FLAT_Y := 0.32
const LONG := 2.2  # the flattened stone stretches along the trench to span it
const SQUASH_TIME := 1.6
const TRENCH_Z := -4.5  # the middle of the trench: a flat stone lies across it here

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
	visual.scale = Vector3(1.0, lerpf(1.0, FLAT_Y, _squash), lerpf(1.0, LONG, _squash))
	if _squash >= 1.0:
		become_bridge()


## Freeze the stone into a slab across the middle of the trench. `announce` is false when a saved
## game restores it (the step is already done then).
func become_bridge(announce: bool = true) -> void:
	flat = true
	var cs := get_node("Ball") as CollisionShape3D
	var bx := BoxShape3D.new()
	bx.size = Vector3(2.3, FLAT_Y * 2.0, 2.3 * LONG)
	cs.shape = bx
	cs.position = Vector3(0, 0.0, 0)
	# it may have rolled in: lay it flat across the trench, level, and stop it spinning
	global_transform = Transform3D(Basis.IDENTITY, Vector3(global_position.x, global_position.y, TRENCH_Z))
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	visual.scale = Vector3(1.0, FLAT_Y, LONG)
	freeze = true
	sleeping = true
	if announce:
		flattened.emit()
