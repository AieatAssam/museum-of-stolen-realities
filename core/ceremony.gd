class_name Ceremony
## Reusable reward ceremonies. Wings call these instead of building their own popups.
## Progress is expressed as world state and placards — never points or tallies.
##
##   await Ceremony.provenance(node, "id")  — stinger + 0.2 s duck, object lifts toward the eye and
##        holds ~1 s (0.4 s after the third find), one placard line, recorded via Quest.
##   await Ceremony.fragment(node)          — the world goes quiet 2 s, the fragment rises and
##        brightens, it is recorded, then the wing's finish() carries it to the atrium where the
##        sphere fills (the peak of each wing happens in the hub).


static func _tree() -> SceneTree:
	return Engine.get_main_loop() as SceneTree


## What to squash and shrink: `node` itself, or, when it is a physics object (a Pickup with no
## separate visual), its visual children. Shapes under them are switched off first: Jolt cannot
## scale a body non-uniformly ("Failed to correctly scale body") and the object is leaving anyway.
static func _scale_targets(node: Node3D) -> Array[Node3D]:
	var out: Array[Node3D] = []
	if node is CollisionObject3D:
		for c in node.get_children():
			if c is Node3D and not (c is CollisionShape3D or c is CollisionObject3D):
				out.append(c)
	else:
		out.append(node)
	for t in out:
		for cs: Node in t.find_children("*", "CollisionShape3D", true, false):
			(cs as CollisionShape3D).set_deferred(&"disabled", true)
		for co: Node in t.find_children("*", "CollisionObject3D", true, false):
			(co as CollisionObject3D).set_deferred(&"process_mode", Node.PROCESS_MODE_DISABLED)
	return out


static func _scale_all(t: Tween, targets: Array[Node3D], s0: Array, k: Vector3, secs: float) -> PropertyTweener:
	var last: PropertyTweener
	for i in targets.size():
		var tw := t.parallel() if i > 0 else t
		last = tw.tween_property(targets[i], "scale", (s0[i] as Vector3) * k, secs)
	return last


static func _total_provenances() -> int:
	var n := 0
	for k: String in Save.data["provenances"]:
		n += (Save.data["provenances"][k] as Array).size()
	return n


static func provenance(node: Node3D, id: StringName) -> void:
	var entry: Dictionary = {}
	for p in Quest.provenances:
		if StringName(p["id"]) == id:
			entry = p
	var short := _total_provenances() >= 3
	Quest.find_provenance(id)  # record first: if `node` is freed mid-animation its tween never finishes
	Audio.duck(-12.0, 0.2)
	Audio.sfx(Audio.stream("provenance"), node.global_position, 0.0, 0.6)
	var p := Game.player
	if p and is_instance_valid(node):
		# anticipation (squash) -> lift toward the eye -> hold -> settle away
		var eye := p.camera.global_position - p.camera.global_basis.z * 0.9 - p.camera.global_basis.y * 0.08
		var targets := _scale_targets(node)
		var s0: Array = targets.map(func(n: Node3D) -> Vector3: return n.scale)
		var t := node.create_tween()
		_scale_all(t, targets, s0, Vector3(1.12, 0.88, 1.12), 0.08)
		_scale_all(t, targets, s0, Vector3(0.94, 1.1, 0.94), 0.1)
		t.parallel().tween_property(node, "global_position", eye, 0.45).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		_scale_all(t, targets, s0, Vector3.ONE, 0.15)
		t.tween_interval(0.4 if short else 1.0)
		var shrink := _scale_all(t, targets, s0, Vector3.ONE * 0.001, 0.3)
		if shrink:
			shrink.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		await t.finished
	if not entry.is_empty():
		Placards.toast(String(entry["line"]), String(entry["name"]))


static func fragment(node: Node3D) -> void:
	var p := Game.player
	Quest.collect_fragment()  # record first (see provenance)
	if p:
		p.input_enabled = false
	Audio.reveal(Audio.stream("fragment"), 2.0)  # runs alongside; its 2 s silence ends as the rise peaks
	if is_instance_valid(node):
		var light := OmniLight3D.new()
		light.light_color = Color("ffe2a8")
		light.light_energy = 0.0
		light.omni_range = 9.0
		node.add_child(light)
		var t := node.create_tween()
		t.tween_property(node, "position:y", node.position.y + 0.6, 2.0).set_trans(Tween.TRANS_SINE)
		t.parallel().tween_property(light, "light_energy", 6.0, 2.0)
		t.tween_callback(func() -> void:
			if is_instance_valid(p):
				p.add_trauma(0.25))
		var targets := _scale_targets(node)
		var s0: Array = targets.map(func(n: Node3D) -> Vector3: return n.scale)
		var shrink := _scale_all(t, targets, s0, Vector3.ONE * 0.001, 0.8)
		if shrink:
			shrink.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		await t.finished
	if is_instance_valid(p):
		p.input_enabled = true
