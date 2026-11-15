extends Node
## Clay wing screenshots and frame timing. Windowed (rendering needed):
##   Godot --path . --resolution 2560x1440 wings/clay/tests/shots.tscn
## Writes PNGs to SHOT_DIR and prints FRAMETIME lines. Pass a folder as the first user arg to override.

const SHOT_DIR := "/private/tmp/claude-501/-Users-aieat--claude-spares-spare-oxJofr/788ae2ca-fb42-43d8-942d-e0b8cc7ce803/scratchpad/clay_shots"

var _w: Node


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "ClayShots"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://clay_shots_save.json"
	_run.call_deferred()


func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _until(cond: Callable, timeout: float) -> bool:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame
	return cond.call()


func _ground(x: float, z: float) -> float:
	return (_w.call("_ground_at", Vector3(x, 0.0, z)) as Vector3).y


func _shot(name_: String, feet: Vector3, look: Vector3) -> void:
	Game.debug_teleport(feet, look)
	await frames(30)
	var img := get_viewport().get_texture().get_image()
	var path := "%s/%s.png" % [SHOT_DIR, name_]
	img.save_png(path)
	print("SHOT ", path)


func _new_game() -> void:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await get_tree().create_timer(1.0, true, false, true).timeout
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	await get_tree().create_timer(0.5, true, false, true).timeout
	_tap(&"ui_accept")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 60.0)
	print("STATE hub wing=", Game.wing.wing_id if Game.wing else "none", " busy=", Transitions.busy, " cin=", Cinematics.playing)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	await _until(func() -> bool: return not Transitions.busy, 60.0)
	print("STATE before goto wing=", Game.wing.wing_id if Game.wing else "none", " busy=", Transitions.busy)
	await Game.debug_goto(&"clay")
	print("STATE after goto wing=", Game.wing.wing_id if Game.wing else "none", " busy=", Transitions.busy)
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"clay", 30.0)
	await _until(func() -> bool: return not Transitions.busy, 10.0)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	_w = Game.wing
	await frames(20)


func _tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(SHOT_DIR)
	await _new_game()

	# Frame timing at the spawn, after warm-up.
	await frames(60)
	var times: Array[float] = []
	for i in 300:
		await get_tree().process_frame
		times.append(get_process_delta_time())
	var total := 0.0
	var worst := 0.0
	for dt in times:
		total += dt
		worst = maxf(worst, dt)
	times.sort()
	print("FRAMETIME spawn frames=%d mean_ms=%.2f p95_ms=%.2f worst_ms=%.2f fps=%.1f" % [
		times.size(), total / times.size() * 1000.0, times[int(times.size() * 0.95)] * 1000.0,
		worst * 1000.0, times.size() / total])

	var sx := 0.0
	var sz := 34.0
	await _shot("01_spawn_meadow", Vector3(sx, _ground(sx, sz) + 0.2, sz), Vector3(0.0, 0.5, 0.0))
	await _shot("02_pit_dig", Vector3(-16.0, _ground(-16.0, 26.0) + 0.2, 26.0), Vector3(-16.0, 0.0, 22.0))
	await _shot("03_mound_raise", Vector3(6.0, _ground(6.0, 25.2) + 0.2, 25.2), Vector3(6.0, 2.0, 22.0))
	await _shot("04_knoll_view", Vector3(-9.0, _ground(-9.0, 13.0) + 1.0, 13.0), Vector3(-16.0, 0.0, 22.0))
	await _shot("05_boulder_trench", Vector3(4.0, _ground(4.0, 10.0) + 0.2, 10.0), Vector3(0.0, 0.0, 4.0))
	await _shot("06_plug_hill", Vector3(22.6, _ground(22.6, -11.0) + 0.2, -11.0), Vector3(26.1, 1.2, -11.0))
	await _shot("07_fence_gate", Vector3(0.0, _ground(0.0, -26.0) + 0.2, -26.0), Vector3(0.0, 1.5, -29.0))
	await _shot("08_ramp_workbench", Vector3(0.0, _ground(0.0, -30.0) + 0.2, -30.0), Vector3(0.0, 1.0, -41.0))
	await _shot("09_village_horse", Vector3(-12.0, _ground(-12.0, -22.5) + 0.2, -22.5), Vector3(-12.0, 0.4, -25.0))
	await _shot("10_hill_lookout", Vector3(12.0, _ground(12.0, -16.0) + 1.0, -16.0), Vector3(12.0, 3.0, -28.0))
	await _shot("11_burrow_film", Vector3(29.0, _ground(29.0, -11.0) + 0.2, -11.0), Vector3(30.2, 0.3, -11.0))
	await _shot("12_chase_corridor", Vector3(3.0, _ground(3.0, -18.0) + 0.2, -18.0), Vector3(3.0, 1.0, -25.0))
	await _shot("13_workbench_table", Vector3(0.0, _ground(0.0, -36.0) + 0.2, -36.0), Vector3(0.0, 2.6, -41.0))

	get_tree().quit(0)
