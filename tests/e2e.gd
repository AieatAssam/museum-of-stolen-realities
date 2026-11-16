extends Playthrough
## End-to-end run of the whole game in one process:  tests/run_smoke.sh tests/e2e.tscn
## New game from the title -> the intro plays out unskipped -> for each of the six wings in order:
## walk into its frame with real input, complete the wing with the documented debug completion
## (Game.debug_complete_wing while the wing is loaded, so its real provenance ids and names are
## recorded; each wing's full scripted playthrough runs separately via tests/run_playthrough.sh),
## return, let the hub's fragment ceremony play, and check the hub changed: the frame's label, the
## Exhibit 0 shard and inner weather, three named relics in the alcove, the thief's stage. Then both
## endings through the real sphere interaction and choice UI, and the credits cover every row.

const ORDER: Array[StringName] = [&"glass", &"clay", &"noir", &"aria", &"chitin", &"paint"]
const RING := 19.5  # clear of docents (r <= 16.8) and columns (inner edge 22.5)


func run() -> void:
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(1.5)
	await tap(&"ui_accept")
	await until(func() -> bool: return _in_hub(), 20.0, "new game lands in the atrium")
	await until(func() -> bool: return Cinematics.playing, 5.0, "the intro starts")
	var t0 := Time.get_ticks_msec()
	await until(func() -> bool: return not Cinematics.playing, 150.0, "the intro plays to its end")
	print("  intro ran %.1fs" % ((Time.get_ticks_msec() - t0) / 1000.0))
	check(Save.data["hub"]["seen_intro"] == true, "intro recorded")
	await until(func() -> bool: return not Transitions.busy and Game.player.input_enabled, 10.0, "control handed to the player")
	# a fresh player's first walk: straight down the entrance axis to the sphere's dais, nothing in the way
	_check_placards(&"atrium")
	var from := Game.player.global_position
	check(await walk_to(Vector3(0, 0, 8.0), 8.0, 0.5), "a straight walk from the hub spawn (%s) reaches the sphere dais" % from)

	for i in ORDER.size():
		var id := ORDER[i]
		print("[e2e] wing ", id)
		var before: Dictionary = Game.wing.call("debug_state", id)
		check(not before["placed"] and before["relics"].is_empty(), "%s: hub starts without it" % id)
		await _walk_into_frame(id)
		if not check(Game.wing != null and Game.wing.wing_id == id, "%s: walking into its frame entered it" % id):
			await Game.debug_goto(Game.HUB_ID)
			continue
		await skip_cinematics()
		check(Quest.provenances.size() == 3, "%s declares 3 provenances" % id)
		_check_placards(id)
		Game.debug_complete_wing(id)
		await Game.return_to_hub()
		await until(func() -> bool: return _in_hub(), 30.0, "%s: back in the atrium" % id)
		# the hub's fragment ceremony: let it play, it ends by marking the shard placed
		await until(func() -> bool: return Cinematics.playing, 6.0)
		await until(func() -> bool: return not Cinematics.playing, 40.0, "%s: fragment ceremony ends" % id)
		await seconds(0.5)
		var st: Dictionary = Game.wing.call("debug_state", id)
		check(st["placed"] and st["shard_visible"], "%s: shard placed and visible in Exhibit 0" % id)
		check(float(st["weather"]) > 0.5, "%s: its weather runs inside the sphere (%.2f)" % [id, st["weather"]])
		check((st["relics"] as Array).size() == 3, "%s: three relics in the alcove (%s)" % [id, st["relics"]])
		var named := true
		for t: String in st["relics"]:
			named = named and not t.begins_with("Provenance,")
		check(named, "%s: relic labels carry the provenance names" % id)
		check(st["frame_body"] != before["frame_body"], "%s: the frame's label was amended" % id)
		check(int(st["thief_stage"]) == i + 1, "%s: the thief's pedestal is at stage %d (%d)" % [id, i + 1, st["thief_stage"]])
		check(Quest.fragment_count() == i + 1, "%s: %d of 6 fragments" % [id, i + 1])

	_check_credits()
	for choice: StringName in [&"restore", &"break"]:
		await _ending(choice)


func _in_hub() -> bool:
	return Game.wing != null and Game.wing.wing_id == Game.HUB_ID and not Transitions.busy


## Walk round the hall on a ring (clear of the dais, docents and bench), then straight into the frame.
func _walk_into_frame(id: StringName) -> void:
	await until(func() -> bool: return _in_hub() and Game.player.input_enabled, 15.0)
	var entry: Vector3 = Game.wing.call("entry_point", id)
	var p := Game.player.global_position
	var a0 := atan2(p.x, p.z)
	var a1 := atan2(entry.x, entry.z)
	var da := wrapf(a1 - a0, -PI, PI)
	var steps := maxi(1, int(ceil(absf(da) / 0.4)))
	for k in steps + 1:
		var a := a0 + da * float(k) / float(steps)
		await walk_to(Vector3(sin(a), 0, cos(a)) * RING, 15.0, 0.8)
	await walk_to(entry, 15.0, 0.05)  # keeps walking until the trigger changes the scene
	await until(func() -> bool: return not Transitions.busy and Game.wing != null, 30.0)


## The real path: hold interact on Exhibit 0, choose with ui_accept / ui_down in the choice UI.
func _ending(choice: StringName) -> void:
	print("[e2e] ending ", choice)
	await until(func() -> bool: return _in_hub() and Game.player.input_enabled, 20.0)
	var hub := Game.wing
	if not check(hub.call("finale_available"), "%s: finale available with six fragments" % choice):
		return
	await walk_to(Vector3(0, 0, RING), 20.0, 0.8)
	await walk_to(Vector3(1.6, 0, 5.0), 20.0, 0.5)
	await look_at(Vector3(0, 6.2, 0))
	await frames(4)
	check(Interaction.target != null and Interaction.target.name == &"SphereTouch", "%s: the sphere is under the crosshair (%s)" % [choice, Interaction.target])
	await hold(&"interact", 1.6)
	await until(func() -> bool: return get_viewport().gui_get_focus_owner() is Button, 3.0, "%s: the choice opens with a focused button" % choice)
	if choice == &"break":
		await tap(&"ui_down")
	var b := get_viewport().gui_get_focus_owner() as Button
	check(b != null and b.text == ("Restore your world" if choice == &"restore" else "Break the collection"), "%s: focus on the right choice (%s)" % [choice, b.text if b else "none"])
	if b == null:
		return
	var done := {"ended": false}
	hub.connect(&"finale_finished", func(_c: StringName) -> void: done["ended"] = true)
	await tap(&"ui_accept")
	var cards := {"n": 0}
	var deadline := Time.get_ticks_msec() + 180000
	while not done["ended"] and is_instance_valid(hub) and Time.get_ticks_msec() < deadline:
		if Cinematics.playing:
			cards["n"] += 1
			Cinematics.skip()
		await seconds(0.3)
	check(done["ended"] and Save.data["ending"] == String(choice), "%s: the ending plays to its end" % choice)
	await until(func() -> bool: return Game.state == Game.State.TITLE and not Transitions.busy, 30.0, "%s: back to the title" % choice)
	if choice == &"restore":
		Save.data["ending"] = ""
		Save.save_game()
		await Game.continue_game()
		await until(func() -> bool: return _in_hub(), 20.0, "continue after the first ending reloads the atrium")
		await skip_cinematics()


## Every row of every CREDITS.md appears on a credits card (typefaces by title).
func _check_credits() -> void:
	var text := ""
	for s: Dictionary in Credits.cards():
		text += String(s.get("card", "")) + "\n"
	var missing: Array = []
	var n := 0
	for r in Credits.rows():
		n += 1
		var want := String(r["title"]) if String(r["licence"]).begins_with("OFL") else Credits.line_for(r)
		if not want in text:
			missing.append(r["path"])
	var wing_rows := Credits.rows().filter(func(r: Dictionary) -> bool: return String(r["file"]).begins_with("res://wings/")).size()
	check(missing.is_empty() and wing_rows > 0, "credits list all %d rows (%d from wings), missing %s" % [n, wing_rows, missing])


## Every in-world placard's text, as Label3D lays it out, sits inside its plate, and no solid geometry
## cuts through the plate's face (points 5 cm in front of its corners and edge midpoints).
func _check_placards(id: StringName) -> void:
	var bad: Array[String] = []
	var clipped: Array[String] = []
	var n := 0
	var space := Game.wing.get_world_3d().direct_space_state
	for pl: Placard in Game.wing.find_children("*", "Placard", true, false):
		n += 1
		if not pl.text_fits():
			bad.append(pl.title)
		for u: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1), Vector2(1, 1), Vector2(0, 1), Vector2(-1, 0), Vector2(1, 0)]:
			var q := PhysicsPointQueryParameters3D.new()
			q.position = pl.global_transform * Vector3(u.x * pl.size.x * 0.48, u.y * pl.size.y * 0.48, 0.05)
			q.collision_mask = 1
			if not space.intersect_point(q, 1).is_empty():
				clipped.append(pl.title)
				break
	check(bad.is_empty(), "%s: all %d placards' text fits the plate %s" % [id, n, bad])
	check(clipped.is_empty(), "%s: no placard plate is cut by geometry %s" % [id, clipped])
