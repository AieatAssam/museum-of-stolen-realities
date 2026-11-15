class_name Checkpoint
extends Marker3D
## A respawn point. Place anywhere under the wing; -Z is the facing on respawn.
## Activated when the player comes within `radius`, or explicitly via Game.set_checkpoint(id).
## The wing's `spawn_checkpoint` is used on first entry.

@export var id: StringName = &"start"
@export var radius: float = 2.5
## Show a placard toast when reached ("" = silent).
@export var toast: String = ""


func _ready() -> void:
	add_to_group(&"checkpoints")


func _physics_process(_delta: float) -> void:
	var p := Game.player
	if p == null or Game.checkpoint_id == id:
		return
	if p.global_position.distance_to(global_position) < radius:
		Game.set_checkpoint(id)
		if toast != "":
			Placards.toast(toast)
