extends Node
## Windowed, real-render screenshot + frame-time harness. Run (needs a display, not --headless):
##   Godot --path . --resolution 2560x1440 tests/shots.tscn
## Plays title -> new game (full intro) -> atrium marks -> 4 fragments returned (fill ceremony,
## THE THIEF stages, alcove) -> template wing. Saves PNGs to shots/ and prints frame-time stats
## (vsync off) for the atrium. Uses a throwaway save (user://shots_save.json).

const OUT := "res://shots"

## Named camera marks: [position, look-at target]
const MARKS := {
	"atrium_wide": [Vector3(3.5, 2.2, 21.0), Vector3(-1.0, 5.0, 0.0)],
	"frames": [Vector3(-6.0, 1.7, 6.0), Vector3(-20.0, 3.5, -6.0)],
	"sphere": [Vector3(4.2, 3.4, 6.8), Vector3(0.0, 5.4, 0.0)],
	"thief": [Vector3(9.5, 1.75, 4.0), Vector3(15.2, 1.2, 8.75)],
	"alcove": [Vector3(0.0, 1.8, -17.5), Vector3(0.0, 1.0, -28.0)],
	"docents": [Vector3(-4.0, 1.7, 2.0), Vector3(-14.0, 1.8, -9.0)],
	"floor_reflection": [Vector3(-2.0, 0.6, 9.0), Vector3(0.0, 4.0, -10.0)],
}

var _cam: Camera3D
var _frame_ms: PackedFloat32Array = []
var _gpu_ms: PackedFloat32Array = []
var _recording: bool = false


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "ShotsRunner"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://shots_save.json"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	FileAccess.open(OUT + "/.gdignore", FileAccess.WRITE)
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _process(delta: float) -> void:
	if _recording:
		_frame_ms.append(delta * 1000.0)
		_gpu_ms.append(RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()))


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func shot(name_: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := ProjectSettings.globalize_path("%s/%s.png" % [OUT, name_])
	img.save_png(path)
	print("[shots] ", path, "  ", img.get_size())


func mark(name_: String, settle: float = 0.6) -> void:
	var m: Array = MARKS[name_]
	if _cam == null or not is_instance_valid(_cam):
		_cam = Camera3D.new()
		_cam.fov = 70.0
		_cam.far = 600.0
		get_tree().current_scene.add_child(_cam)
	_cam.global_position = m[0]
	_cam.look_at(m[1], Vector3.UP)
	_cam.make_current()
	await seconds(settle)
	await shot(name_)


func measure(label: String, secs: float = 5.0) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	DisplayServer.window_move_to_foreground()
	await seconds(1.0)
	print("[perf] vsync mode ", DisplayServer.window_get_vsync_mode(), "  refresh ", DisplayServer.screen_get_refresh_rate(), " Hz  max_fps ", Engine.max_fps)
	_frame_ms.clear()
	_gpu_ms.clear()
	_recording = true
	await seconds(secs)
	_recording = false
	var f := Array(_frame_ms)
	f.sort()
	var g := Array(_gpu_ms)
	g.sort()
	var avg := 0.0
	for v: float in f:
		avg += v
	avg /= maxf(1.0, f.size())
	var gavg := 0.0
	for v: float in g:
		gavg += v
	gavg /= maxf(1.0, g.size())
	print("[perf] %s @ %s  frames=%d  avg=%.2f ms (%.0f fps)  p95=%.2f ms  p99=%.2f ms  max=%.2f ms  | gpu avg=%.2f ms p95=%.2f ms" % [
		label, get_viewport().size, f.size(), avg, 1000.0 / avg, f[int(f.size() * 0.95)], f[int(f.size() * 0.99)], f[-1], gavg, g[int(g.size() * 0.95)]])


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


func _run() -> void:
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	print("[shots] window ", DisplayServer.window_get_size(), " viewport ", get_viewport().size, " quality ", Save.settings["quality"])
	await seconds(3.5)
	await shot("01_title")
	Game.new_game()
	await _until(func() -> bool: return Game.wing != null and Cinematics.playing, 30.0)
	var t0 := Time.get_ticks_msec()
	await seconds(3.0)
	await shot("02_intro_card")
	await _until(func() -> bool: return Time.get_ticks_msec() - t0 > 43500, 70.0)
	await shot("03_intro_approach")
	await _until(func() -> bool: return Time.get_ticks_msec() - t0 > 56500, 70.0)
	await shot("04_intro_reveal")
	await _until(func() -> bool: return not Cinematics.playing, 40.0)
	await seconds(2.0)
	await shot("05_player_view")
	await measure("atrium player view")
	await mark("atrium_wide")
	await measure("atrium wide")
	await mark("frames")
	await mark("sphere")
	await mark("floor_reflection")

	# progression: four wings returned
	for id: StringName in [&"glass", &"clay", &"noir", &"aria"]:
		Game.debug_complete_wing(id)
	await Game.return_to_hub()
	await _until(func() -> bool: return Cinematics.playing, 10.0)
	await seconds(6.2)
	await shot("06_fragment_fill")
	await _until(func() -> bool: return not Cinematics.playing, 30.0)
	_cam = null
	await mark("thief", 1.5)
	await mark("alcove")
	await mark("docents")
	await mark("sphere", 0.8)
	await measure("atrium 4 fragments, sphere mark")

	await Game.debug_goto(&"_template")
	await seconds(1.0)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	await seconds(2.5)
	await shot("07_template")
	await measure("template wing")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	print("[shots] done")
	get_tree().quit(0)
