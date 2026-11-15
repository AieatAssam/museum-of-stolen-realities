class_name TriggerZone
extends Area3D
## Fires `triggered(player)` when the player enters (layer 4 "trigger"). `once` = fire one time.

signal triggered(player: Player)
signal exited(player: Player)

@export var once: bool = true
var _fired: bool = false


func _init() -> void:
	collision_layer = 1 << 3
	collision_mask = 1 << 1
	monitorable = false
	body_entered.connect(_on_enter)
	body_exited.connect(func(b: Node3D) -> void: if b is Player: exited.emit(b))


func _on_enter(b: Node3D) -> void:
	if not b is Player or (once and _fired):
		return
	_fired = true
	triggered.emit(b)


## Convenience: a box trigger.
static func make_box(size: Vector3, fire_once: bool = true) -> TriggerZone:
	var t := TriggerZone.new()
	t.once = fire_once
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	t.add_child(cs)
	return t
