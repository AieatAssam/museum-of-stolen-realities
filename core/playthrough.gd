class_name Playthrough
extends Node
## Base for scripted, headless test runs (tests/smoke.gd and every wing's tests/playthrough.gd).
## Extend it, override `run()`, drive the game with REAL input, assert with `check()`:
##
##   extends Playthrough
##   func run() -> void:
##       await enter(&"glass")                                  # fresh save, load the wing, skip intro
##       await walk_to(Vector3(0, 0, -12))                      # steer with move/mouse input
##       await use($"/root/Glass/Prism")                        # aim at it, press interact
##       check(Quest.is_step_done(&"light", &"prism"), "prism lit by interact")
##       await until(func() -> bool: return Quest.has_fragment(&"glass"), 30.0, "fragment taken")
##
## Run:  tests/run_playthrough.sh <wing_id>   (headless; exit 1 on any failed check, script error,
##       or leak in the log). Wing tests live at res://wings/<id>/tests/playthrough.gd.
## The run always ends via `finish()`, which quits with the exit code; `run()` just returns.

var fails: int = 0
var _t0: int = 0


func _ready() -> void:
	if get_tree().current_scene == self:
		# The current scene is freed on every scene change; run from a node parented to root.
		var runner: Node = (get_script() as GDScript).new()
		runner.name = name + "Runner"
		get_tree().root.add_child.call_deferred(runner)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	Save.save_path = "user://test_%s.json" % (get_script() as GDScript).resource_path.get_file().get_basename()
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	_start.call_deferred()


func _start() -> void:
	_t0 = Time.get_ticks_msec()
	await run()
	finish()


## Override: the test body.
func run() -> void:
	pass


## Print a summary, delete the throwaway save and quit with 0 (all checks passed) or 1.
func finish() -> void:
	print("[test] done in %.1fs, %d failure(s)" % [(Time.get_ticks_msec() - _t0) / 1000.0, fails])
	Input.action_release(&"move_forward")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Game.quit(1 if fails > 0 else 0)


# --- assertions & waiting -------------------------------------------------------------------

func check(cond: bool, what: String) -> bool:
	if cond:
		print("  ok   ", what)
	else:
		fails += 1
		push_error("TEST FAIL: " + what)
		print("  FAIL ", what)
	return cond


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


## Wait until `cond` is true or `timeout` s pass. With `what`, a timeout is a failed check.
func until(cond: Callable, timeout: float, what: String = "") -> bool:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame
	var ok: bool = cond.call()
	if what != "":
		check(ok, what)
	return ok


# --- game flow --------------------------------------------------------------------------------

## Fresh save, go to the wing (waits out any transition) and skip its intro. Returns true if there.
func enter(wing_id: StringName) -> bool:
	var ok: bool = await Game.debug_goto(wing_id)
	check(ok, "%s loads" % wing_id)
	await skip_cinematics()
	return ok


## Skip whatever cinematic is playing (and any that start within `settle` s), then wait it out.
func skip_cinematics(settle: float = 0.3) -> void:
	await seconds(settle)
	while Cinematics.playing:
		Cinematics.skip()
		await seconds(0.2)


# --- input ------------------------------------------------------------------------------------

## Press and release an action (one event each way, like a key tap).
func tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await frames(2)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event(up)
	await frames(1)


## Hold an action for `secs` (hold-to-interact, charge verbs, sprint).
func hold(action: StringName, secs: float) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	await seconds(secs)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event(up)
	await frames(1)


## Turn the view with real mouse-motion events until it faces `point` (yaw and pitch).
func look_at(point: Vector3, max_frames: int = 90) -> void:
	var p := Game.player
	if p == null:
		return
	var s := deg_to_rad(float(Save.settings["mouse_sensitivity"]))
	var inv := -1.0 if Save.settings["invert_y"] else 1.0
	for i in max_frames:
		var d := p.camera.global_position.direction_to(point)
		var want_yaw := atan2(-d.x, -d.z)
		var want_pitch := asin(clampf(d.y, -1.0, 1.0))
		var ey := wrapf(want_yaw - p.yaw, -PI, PI)
		var ep := want_pitch - p.pitch
		if absf(ey) < 0.01 and absf(ep) < 0.01:
			return
		var mm := InputEventMouseMotion.new()
		mm.relative = Vector2(-ey / s, -ep / s * inv) * 0.6
		mm.screen_relative = mm.relative
		Input.parse_input_event(mm)
		await get_tree().process_frame


## Steer with move input (and mouse look) toward `target` until within `radius` (horizontal), a
## scene change starts, or `timeout`. Hold `sprint` for jumps. Returns true on arrival.
func walk_to(target: Vector3, timeout: float = 20.0, radius: float = 0.6, sprint: bool = false) -> bool:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	if sprint:
		Input.action_press(&"sprint")
	var arrived := false
	while Time.get_ticks_msec() < end and Game.player and not Transitions.busy:
		var p := Game.player
		var to := target - p.global_position
		to -= p.up_direction * to.dot(p.up_direction)
		if to.length() < radius:
			arrived = true
			break
		var want_yaw := atan2(-to.x, -to.z)
		var err := wrapf(want_yaw - p.yaw, -PI, PI)
		var mm := InputEventMouseMotion.new()
		mm.relative = Vector2(-err / deg_to_rad(float(Save.settings["mouse_sensitivity"])) * 0.5, 0)
		mm.screen_relative = mm.relative
		Input.parse_input_event(mm)
		if absf(err) < 0.5:
			Input.action_press(&"move_forward")
		else:
			Input.action_release(&"move_forward")
		await get_tree().physics_frame
	Input.action_release(&"move_forward")
	Input.action_release(&"sprint")
	if not arrived and Game.player and not Transitions.busy:
		print("  walk_to timed out at ", Game.player.global_position, " target ", target)
	return arrived


## Walk to a point and jump at the right moment: walks toward `target`, pressing jump when the
## player is `takeoff` m from `edge` (a point on the lip you jump from). Sprints.
func jump_across(edge: Vector3, target: Vector3, takeoff: float = 0.4, timeout: float = 10.0) -> bool:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	Input.action_press(&"sprint")
	var jumped := false
	while Time.get_ticks_msec() < end and Game.player and not Transitions.busy:
		var p := Game.player
		var to := target - p.global_position
		to.y = 0.0
		if to.length() < 0.6:
			break
		var err := wrapf(atan2(-to.x, -to.z) - p.yaw, -PI, PI)
		var mm := InputEventMouseMotion.new()
		mm.relative = Vector2(-err / deg_to_rad(float(Save.settings["mouse_sensitivity"])) * 0.5, 0)
		mm.screen_relative = mm.relative
		Input.parse_input_event(mm)
		Input.action_press(&"move_forward")
		var flat := p.global_position - edge
		flat.y = 0.0
		if not jumped and flat.length() < takeoff:
			jumped = true
			tap(&"jump")
		await get_tree().physics_frame
	Input.action_release(&"move_forward")
	Input.action_release(&"sprint")
	return Game.player != null and (target - Game.player.global_position).length() < 2.0


## Aim at `node` from where the player stands and press interact (or hold it `hold_secs`).
## Returns true if the crosshair found an Interactable at that moment.
func use(node: Node3D, hold_secs: float = 0.0) -> bool:
	await look_at(node.global_position)
	await frames(3)
	var had := is_instance_valid(Interaction.target)
	if hold_secs > 0.0:
		await hold(&"interact", hold_secs)
	else:
		await tap(&"interact")
	return had
