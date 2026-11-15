extends Node
## Interaction autoload: every physics tick, ray-casts from the active camera against layer 3
## and tracks the Interactable under the crosshair. The HUD reads `target`, `hold_progress`.

signal target_changed(target: Interactable)

var target: Interactable
var hold_progress: float = 0.0
var _holding: bool = false


func _physics_process(delta: float) -> void:
	var p := Game.player
	var cam := get_viewport().get_camera_3d()
	var found: Interactable = null
	if p and cam and p.input_enabled and Game.state == Game.State.PLAYING:
		var from := cam.global_position
		var q := PhysicsRayQueryParameters3D.create(from, from - cam.global_basis.z * 4.0, (1 << 2) | 1)
		q.collide_with_areas = true
		q.exclude = [p.get_rid()]
		var hit := p.get_world_3d().direct_space_state.intersect_ray(q)
		if hit and hit.collider is Interactable:
			var it := hit.collider as Interactable
			if it.enabled and from.distance_to(hit.position) <= it.max_distance:
				found = it
	if found != target:
		target = found
		hold_progress = 0.0
		target_changed.emit(target)
	if target and target.hold_time > 0.0 and _holding:
		hold_progress += delta / target.hold_time
		if hold_progress >= 1.0:
			_holding = false
			hold_progress = 0.0
			target.interact(Game.player)
	elif not _holding:
		hold_progress = move_toward(hold_progress, 0.0, delta * 3.0)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"interact"):
		_holding = true
		if target and target.hold_time <= 0.0:
			target.interact(Game.player)
			_holding = false
	elif event.is_action_released(&"interact"):
		_holding = false
