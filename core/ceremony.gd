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
	Audio.duck(-12.0, 0.2)
	Audio.sfx(Audio.stream("provenance"), node.global_position, 0.0, 0.6)
	var p := Game.player
	if p and is_instance_valid(node):
		# anticipation (squash) -> lift toward the eye -> hold -> settle away
		var eye := p.camera.global_position - p.camera.global_basis.z * 0.9 - p.camera.global_basis.y * 0.08
		var s0 := node.scale
		var t := node.create_tween()
		t.tween_property(node, "scale", s0 * Vector3(1.12, 0.88, 1.12), 0.08)
		t.tween_property(node, "scale", s0 * Vector3(0.94, 1.1, 0.94), 0.1)
		t.parallel().tween_property(node, "global_position", eye, 0.45).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		t.tween_property(node, "scale", s0, 0.15)
		t.tween_interval(0.4 if short else 1.0)
		t.tween_property(node, "scale", Vector3.ONE * 0.001, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		await t.finished
	Quest.find_provenance(id)
	if not entry.is_empty():
		Placards.toast(String(entry["line"]), String(entry["name"]))


static func fragment(node: Node3D) -> void:
	var p := Game.player
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
			if p:
				p.add_trauma(0.25))
		t.tween_property(node, "scale", Vector3.ONE * 0.001, 0.8).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		await t.finished
	Quest.collect_fragment()
	if p and is_instance_valid(p):
		p.input_enabled = true
