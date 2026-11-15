class_name Interactable
extends Area3D
## Something the player can look at and use with [interact]. Put a CollisionShape3D child on it.
## It lives on physics layer 3 ("interactable"). Connect `interacted` or subclass `_on_interact`.
## hold_time > 0 makes it hold-to-interact (the HUD shows a ring).

signal interacted(player: Player)

@export var prompt: String = "Examine"
@export var hold_time: float = 0.0
@export var max_distance: float = 3.2
@export var enabled: bool = true
## One-shot interactables disable themselves after use.
@export var once: bool = false


func _init() -> void:
	collision_layer = 1 << 2
	collision_mask = 0
	monitoring = false
	input_ray_pickable = false


func interact(player: Player) -> void:
	if not enabled:
		return
	if once:
		enabled = false
	_on_interact(player)
	interacted.emit(player)


func _on_interact(_player: Player) -> void:
	pass


## Convenience: build a box-shaped interactable in code.
static func make_box(size: Vector3, text: String = "Examine") -> Interactable:
	var i := Interactable.new()
	i.prompt = text
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	i.add_child(cs)
	return i
