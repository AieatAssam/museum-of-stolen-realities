extends Node
## Windowed screenshots + frame times for The Drowned Aria (needs a display, not --headless).
##   Godot --path . --resolution 2560x1440 wings/aria/tests/capture.tscn
## PNGs go to CAPTURE_OUT (outside the repo). Frame-time stats print as [perf] lines.

const CAPTURE_OUT := "/private/tmp/claude-501/-Users-aieat--claude-spares-spare-oxJofr/788ae2ca-fb42-43d8-942d-e0b8cc7ce803/scratchpad/aria_shots"

## Named camera marks: [position, look-at target]
const MARKS := {
	"01_entrance": [Vector3(0, 2.0, 14.0), Vector3(0, 3.0, -20.0)],
	"02_horns": [Vector3(-6.0, 1.7, 1.0), Vector3(-8.0, 2.5, -4.0)],
	"03_pipes": [Vector3(0, 1.7, -12.0), Vector3(0, 2.5, -19.0)],
	"04_glass": [Vector3(0, 1.7, 0.5), Vector3(0, 1.2, -7.0)],
	"05_stage": [Vector3(-8.0, 2.0, -16.0), Vector3(0, 4.0, -30.0)],
	"06_fragment": [Vector3(3.0, 1.6, -22.0), Vector3(0, 1.0, -26.0)],
	"07_wide_side": [Vector3(13.0, 5.0, 9.0), Vector3(-6.0, 3.0, -20.0)],
	"08_floor": [Vector3(-2.0, 0.8, 4.0), Vector3(0, 0.0, -8.0)],
}

var _cam: Camera3D
var _frame_ms: PackedFloat32Array = []
var _recording: bool = false


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "CaptureRunner"
		get_tree().root.add_child.call_deferred(runner)
		return
	Save.save_path = "user://aria_capture_save.json"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	DirAccess.make_dir_recursive_absolute(CAPTURE_OUT)
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _process(delta: float) -> void:
	if _recording:
		_frame_ms.append(delta * 1000.0)


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


func shot(name_: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(CAPTURE_OUT + "/" + name_ + ".png")
	print("[shot] ", name_, " ", img.get_size())


func mark(name_: String) -> void:
	var m: Array = MARKS[name_]
	if _cam == null or not is_instance_valid(_cam):
		_cam = Camera3D.new()
		_cam.fov = 70.0
		_cam.far = 400.0
		get_tree().current_scene.add_child(_cam)
	_cam.global_position = m[0]
	_cam.look_at(m[1], Vector3.UP)
	_cam.make_current()
	await seconds(0.6)
	await shot(name_)


func measure(label: String, secs: float = 5.0) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await seconds(1.0)
	_frame_ms.clear()
	_recording = true
	await seconds(secs)
	_recording = false
	var f := Array(_frame_ms)
	f.sort()
	var avg := 0.0
	for v: float in f:
		avg += v
	avg /= maxf(1.0, f.size())
	print("[perf] %s @ %s frames=%d avg=%.2f ms (%.0f fps) p95=%.2f ms p99=%.2f ms max=%.2f ms" % [
		label, get_viewport().size, f.size(), avg, 1000.0 / avg,
		f[int(f.size() * 0.95)], f[int(f.size() * 0.99)], f[-1]])


func _run() -> void:
	Game.new_game()
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == Game.HUB_ID, 30.0)
	await seconds(0.5)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing and not Transitions.busy, 15.0)
	await Game.debug_goto(&"aria")
	await _until(func() -> bool: return Game.wing != null and Game.wing.wing_id == &"aria" and not Transitions.busy, 30.0)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing, 10.0)
	await seconds(1.5)
	await shot("00_player_start")
	for name_: String in MARKS.keys():
		await mark(name_)
	# free camera back to the player and measure the hall as played
	_cam.clear_current()
	Game.player.camera.make_current()
	await seconds(1.0)
	await measure("aria hall, player view")
	# a lift in progress: strike a horn from under it and catch her rising
	Game.debug_teleport(Vector3(-8, 0.5, -2.8), Vector3(-8, 2.0, -4))
	await seconds(0.6)
	var ev := InputEventAction.new()
	ev.action = &"primary"
	ev.pressed = true
	Input.parse_input_event(ev)
	await seconds(0.9)
	await shot("09_lift_rising")
	await measure("aria hall, horn sounding", 4.0)
	print("[shot] done")
	get_tree().quit(0)
