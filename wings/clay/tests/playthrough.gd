extends Node
## Clay wing playthrough. Run:
##   Godot --headless --path . wings/clay/tests/playthrough.tscn
## Two fresh games. Run A takes the keep branch, all three provenances, the reveal and the fragment.
## Run B takes the kneel branch. Pulls, presses, scoops and holds use the real action inputs (held
## primary/secondary/interact); walking between spots is teleport. Exits 1 on the first failed check.

var _fails: int = 0
var _w: Node
var _rates: Array[float] = []
var _watch_rates: bool = false


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "ClayPlaythrough"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://clay_playthrough_save.json"
	_run.call_deferred()


func _process(_delta: float) -> void:
	if _watch_rates and _w and is_instance_valid(_w):
		var f: float = _w.world_fps
		if _rates.is_empty() or _rates.back() != f:
			_rates.append(f)


func check(cond: bool, what: String) -> void:
	if cond:
		print("  ok   ", what)
	else:
		_fails += 1
		push_error("CLAY FAIL: " + what)
		print("  FAIL ", what)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func _tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func _until(cond: Callable, timeout: float) -> bool:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame
	return cond.call()


## Hold a real action until the condition holds or the timeout passes. Returns the condition.
func _hold_until(action: StringName, cond: Callable, timeout: float) -> bool:
	Input.action_press(action)
	var ok := await _until(cond, timeout)
	Input.action_release(action)
	await frames(2)
	return ok


func _hold(action: StringName, secs: float) -> void:
	Input.action_press(action)
	await seconds(secs)
	Input.action_release(action)
	await frames(2)


## Interactables listen for the press and release events (Interaction._unhandled_input), so the
## interact action is sent as events; a hold is a press, a wait, then a release.
func _press_event(action: StringName, secs: float) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await seconds(secs)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event(up)
	await frames(4)


func _ground(x: float, z: float) -> float:
	return (_w.call("_ground_at", Vector3(x, 0.0, z)) as Vector3).y


## Put the player's feet on the ground at (x, z) and look at a point.
func _stand(x: float, z: float, look: Vector3) -> void:
	Game.debug_teleport(Vector3(x, _ground(x, z) + 0.2, z), look)
	await frames(10)


func _new_game() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(1.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	await seconds(0.5)
	_tap(&"ui_accept")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	await Game.debug_goto(&"clay")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"clay", 20.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	_w = Game.wing
	await frames(10)


func _interactables(parent: Node) -> Array[Interactable]:
	var out: Array[Interactable] = []
	for c in parent.get_children():
		if c is Interactable:
			out.append(c)
	return out


func _run() -> void:
	print("[clay] run A: keep branch")
	await _new_game()
	check(_w != null and _w.wing_id == &"clay", "the debug route enters the clay wing")
	check(Quest.objectives.size() == 4 and Quest.provenances.size() == 3, "declares 4 objectives and 3 provenances")

	# --- objective 1: raise ---------------------------------------------------------------------
	var mx: float = _w.MOUND.x
	var mz: float = _w.MOUND.z
	var kx: float = _w.KNOLL.x
	var kz: float = _w.KNOLL.z
	# at the knoll's foot, looking level at it (not down): the prompt shows and the pull works
	# (hugging the wall, 1.3 m off, looking up at the sky: the live play-test's spot, which never pulled)
	var foot_z: float = kz + _w.KNOLL_HALF.y + 1.3
	kx -= 0.5
	await _stand(kx, foot_z, Vector3(kx, _ground(kx, foot_z) + 9.0, kz - 3.0))
	await frames(6)
	check(String(_w.verb_prompt().get("text", "")) == "pull the clay up", "looking level at the knoll from its foot shows the pull prompt (%s)" % _w.verb_prompt())
	check(not Quest.is_step_done(&"raise", &"ledge"), "standing at the knoll's foot does not tick the ledge step")
	await _hold(&"primary", 2.5)
	check(Quest.is_step_done(&"raise", &"pull_step"), "held primary at the knoll pulls a step (pull_step)")
	check(not Quest.is_step_done(&"raise", &"ledge"), "pulling the step does not tick the ledge step")
	# walk (real input, no jump) up the pulled step onto the knoll; against the wall the step is built
	# beside her, so she sidesteps first
	Input.action_press(&"move_right")
	await seconds(0.8)
	Input.action_release(&"move_right")
	Input.action_press(&"move_forward")
	await _until(func() -> bool: return Quest.is_step_done(&"raise", &"ledge"), 5.0)
	Input.action_release(&"move_forward")
	check(Quest.is_step_done(&"raise", &"ledge"), "walking up the pulled step onto the knoll completes the ledge step (at %s)" % Game.player.global_position)
	check(not Quest.is_done(&"raise"), "the raise objective stays open until the mound is pressed")
	await _stand(mx, mz + 3.2, Vector3(mx, _w.terrain.height_at(mx, mz), mz))
	# The eye sits near 2.7 m and the peak is 3.2 m, so a ray at the peak only grazes it.
	# Aim at lower points on the front face first; each press flattens clay under the aim.
	var mound_ok: bool = false
	# two sweeps: a single sweep ends within a few cm of MOUND_DONE, so beat timing decides it
	for i in 18:
		var zt: float = mz + maxf(0.0, 2.0 - 0.25 * float(i % 9))
		var ht: float = _w.terrain.height_at(mx, zt)
		await _stand(mx, mz + 3.2, Vector3(mx, ht, zt))
		await _hold(&"secondary", 1.2)
		if _w.terrain.height_at(mx, mz) <= 0.3:
			mound_ok = true
			break
	check(mound_ok and Quest.is_step_done(&"raise", &"mound"), "held secondary presses the mound flat")
	check(Quest.is_done(&"raise"), "objective raise is complete")

	# --- objective 2: cross ---------------------------------------------------------------------
	var dx: float = _w.DIG_CENTRE.x
	var dz: float = _w.DIG_CENTRE.z
	await _stand(dx, dz + 4.8, Vector3(dx, _w.terrain.height_at(dx, dz), dz))
	var scooped: bool = await _hold_until(&"primary", func() -> bool: return _w._scooped, 30.0)
	check(scooped and Quest.is_step_done(&"cross", &"carry"), "scooping the pit fills the pouch (carry)")

	var boulder_in: bool = await _until(func() -> bool: return _w._boulder.in_trench(), 30.0)
	check(boulder_in, "the boulder rolls into the trench on its own")
	var bp: Vector3 = _w._boulder.global_position
	await _stand(bp.x, bp.z + 2.6, bp)
	var flat_ok: bool = await _hold_until(&"secondary", func() -> bool: return Quest.is_step_done(&"cross", &"boulder"), 12.0)
	check(flat_ok, "pressing the boulder flattens it into the gap (boulder)")
	var bx: float = _w._boulder.global_position.x
	await _stand(bx, -1.0, Vector3(bx, 0.0, -8.0))
	await frames(5)
	var across: bool = await _hold_until(&"move_forward", func() -> bool: return Game.player.global_position.z < -6.2, 12.0)
	check(across and Game.player.global_position.y > -0.5, "the flattened stone carries the player across the trench")

	# the river: a fall in must not be a dead end. Walk the trench floor to the bank ramp and climb out.
	Game.debug_teleport(Vector3(-6.0, _ground(-6.0, -4.5) + 0.2, -4.5), Vector3(-12.0, 0.0, -4.5))
	await frames(10)
	var along: bool = await _hold_until(&"move_forward", func() -> bool: return Game.player.global_position.x < -11.0, 12.0)
	check(along, "the trench floor can be walked along to the bank ramp (river)")
	Game.debug_teleport(Vector3(-11.5, _ground(-11.5, -4.0) + 0.2, -4.0), Vector3(-11.5, 0.0, 0.0))
	await frames(10)
	var out: bool = await _hold_until(&"move_forward", func() -> bool: return Game.player.global_position.z > -2.0, 12.0)
	check(out and Game.player.is_on_floor(), "walking up the ramp gets the player out of the river (river)")

	await _stand(22.6, -11.0, Vector3(26.1, 1.2, -11.0))
	var plug_ok: bool = await _hold_until(&"secondary", func() -> bool: return _w._plug == null, 10.0)
	check(plug_ok and Quest.is_step_done(&"cross", &"doorway"), "pressing the plug opens the hill (doorway)")
	check(Quest.is_done(&"cross"), "objective cross is complete")

	# --- optional lookout -----------------------------------------------------------------------
	var hx: float = _w.HILL.x
	var hz: float = _w.HILL.z
	Game.debug_teleport(Vector3(hx, _ground(hx, hz) + 2.2, hz))
	await frames(14)
	check(Quest.is_done(&"lookout"), "standing on the hill completes the optional lookout")

	# --- objective 3: way up --------------------------------------------------------------------
	var mod: Node3D = _w._fence[10]
	var fz: float = _w.FENCE_Z - 2.6
	await _stand(mod.global_position.x, fz, mod.global_position + Vector3(0, 1.2, 0))
	var gate_ok: bool = await _hold_until(&"secondary", func() -> bool: return _w._gate_down, 6.0)
	check(gate_ok and Quest.is_step_done(&"way_up", &"gate"), "holding secondary on the wire gate lowers it")
	await _stand(0.0, _w.RAMP_Z + 3.2, Vector3(0.0, _w.terrain.height_at(0.0, _w.RAMP_Z), _w.RAMP_Z))
	var ramp_ok: bool = await _hold_until(&"primary", func() -> bool: return Quest.is_step_done(&"way_up", &"ramp"), 25.0)
	check(ramp_ok, "pulling a ramp to the workbench foot (ramp)")
	check(Quest.main_objectives_done(), "all three main objectives are done")

	# --- the Unfinished One: keep ---------------------------------------------------------------
	await _cross_village_entrance()
	var shown: bool = await _until(func() -> bool: return _w._choice_shown, 60.0)
	check(shown, "the Unfinished One catches the player and offers the choice")
	var ints := _interactables(_w._chaser)
	check(ints.size() == 2, "two choices are placed on the Unfinished One")
	if ints.size() == 2:
		var keep_it: Interactable = ints[1]
		var kp := keep_it.global_position
		Game.debug_teleport(kp + Vector3(0, -0.8, 2.2), kp)
		await frames(10)
		await _press_event(&"interact",0.3)
		await frames(6)
	check(_w._choice == &"keep" and _w._tool, "taking the tool records keep and grants the tool")
	check(String(_w.save_state()["choice"]) == "keep", "keep is saved to the wing state")

	# --- provenances ----------------------------------------------------------------------------
	var hgx := _ground(-12.0, -25.0)
	Game.debug_teleport(Vector3(-12.0, hgx + 0.2, -22.5), Vector3(-12.0, hgx + 0.4, -25.0))
	await frames(10)
	await _press_event(&"interact",1.5)
	var got_horse: bool = await _until(func() -> bool: return Quest.has_provenance(&"clay", &"horse"), 6.0)
	check(got_horse, "provenance: the wire horse is picked up")

	await _stand(14.0, 24.8, Vector3(14.0, _ground(14.0, 27.0) + 0.3, 27.0))
	await _press_event(&"interact",1.5)
	var got_thumb: bool = await _until(func() -> bool: return Quest.has_provenance(&"clay", &"thumb"), 6.0)
	check(got_thumb, "provenance: the thumbprint is picked up")

	var fx := 30.2
	var fg := _ground(fx, -11.0)
	await _stand(29.0, -11.0, Vector3(fx, fg + 0.3, -11.0))
	await _press_event(&"interact",1.5)
	var got_film: bool = await _until(func() -> bool: return Quest.has_provenance(&"clay", &"film"), 6.0)
	check(got_film, "provenance: the cling film is picked up")

	# --- reveal and fragment --------------------------------------------------------------------
	_watch_rates = true
	Game.debug_teleport(Vector3(_w.TABLE.x, _w.TABLE_TOP + 1.0, _w.TABLE.z))
	var revealed: bool = await _until(func() -> bool: return _w._reveal_done, 40.0)
	await _until(func() -> bool: return _w.world_fps >= 12.0, 10.0)
	_watch_rates = false
	check(revealed, "standing at the workbench starts the reveal and it finishes")
	print("  world_fps sequence: ", _rates)
	check(_seen_in_order(_rates, [8.0, 6.0, 2.0, 0.0]), "the frame rate drops 8, 6, 2, then holds at 0")
	check(_w.world_fps >= 12.0, "the frame rate recovers to 12 after the reveal")

	var frag: Node3D = _w._fragment
	check(frag.visible, "the fragment appears after the reveal")
	Game.debug_teleport(frag.global_position + Vector3(0.0, -1.25, 1.6), frag.global_position)
	await frames(10)
	await _press_event(&"interact",1.2)
	var home: bool = await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 20.0)
	check(home, "taking the fragment returns to the atrium")
	check(Quest.has_fragment(&"clay"), "the clay fragment is recorded")

	# --- run B: kneel ---------------------------------------------------------------------------
	print("[clay] run B: kneel branch")
	await _new_game()
	check(_w != null and _w.wing_id == &"clay", "a fresh game re-enters the clay wing")
	await _cross_village_entrance()
	var shown_b: bool = await _until(func() -> bool: return _w._choice_shown, 60.0)
	check(shown_b, "the Unfinished One offers the choice again")
	var ints_b := _interactables(_w._chaser)
	if ints_b.size() == 2:
		var kneel: Interactable = ints_b[0]
		var kp2 := kneel.global_position
		Game.debug_teleport(kp2 + Vector3(0, -0.8, 2.2), kp2)
		await frames(10)
		await _press_event(&"interact",2.2)
		await frames(6)
	check(_w._choice == &"kneel", "kneeling records kneel")
	check(not _w._tool, "kneeling does not grant the tool")
	check(_w._gate_down and Quest.is_step_done(&"way_up", &"gate"), "kneeling lowers the fence")
	check(String(_w.save_state()["choice"]) == "kneel", "kneel is saved to the wing state")

	print("[clay] %d failed check(s)" % _fails)
	Game.quit(1 if _fails > 0 else 0)


## The chase starts when the player crosses the village entrance (a long trigger at z -21.5).
func _cross_village_entrance() -> void:
	await _stand(3.0, -18.0, Vector3(3.0, _ground(3.0, -22.0) + 0.5, -22.0))
	await _stand(3.0, -21.5, Vector3(3.0, _ground(3.0, -25.0) + 0.5, -25.0))


func _seen_in_order(seq: Array[float], want: Array) -> bool:
	var i := 0
	for v in seq:
		if i < want.size() and is_equal_approx(v, float(want[i])):
			i += 1
	return i == want.size()
