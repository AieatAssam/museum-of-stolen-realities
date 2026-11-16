class_name Pickup
extends Interactable
## An interactable that is collected: plays a sound, shrinks away, frees itself, emits `picked`.
## Use `kind` + `item_id` to route it: &"provenance" runs Ceremony.provenance (records it),
## &"fragment" runs Ceremony.fragment (records it; then call Wing.finish()),
## &"step" completes Quest step `item_id` = "objective/step".

signal picked

@export var kind: StringName = &"item"
@export var item_id: StringName = &""
## Optional visual to animate away (defaults to the parent's first MeshInstance3D sibling).
@export var visual: Node3D


func _init() -> void:
	super()
	prompt = "Take"
	once = true


func _on_interact(_player: Player) -> void:
	var v := visual if visual else self
	match kind:
		&"provenance":
			await Ceremony.provenance(v, item_id)
			picked.emit()
			queue_free()
			return
		&"fragment":
			await Ceremony.fragment(v)
			picked.emit()
			return
		&"step":
			var parts := String(item_id).split("/")
			Quest.complete_step(StringName(parts[0]), StringName(parts[1]))
			Audio.ui(&"select")
		_:
			Audio.ui(&"select")
	picked.emit()
	var t := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	for n in Ceremony._scale_targets(v):  # never scale a physics body (Jolt)
		t.parallel().tween_property(n, "scale", n.scale * 0.01, 0.45)
	t.chain().tween_callback(queue_free)
