extends Node
## Vitrine Kingdom screenshot + frame-time harness (windowed, real render; not --headless):
##   Godot --path . --resolution 2560x1440 res://wings/glass/tests/shots.tscn
## PNGs go to wings/glass/_shots/ (gitignored). States (sky reveal, Rose phases, shatter, heist) are
## set directly: this is a camera rig, the playthrough is the proof of play.

const OUT := "res://wings/glass/_shots"
const H := Vector3(-60, 14, -95)

## name: [camera position, look-at, state]
const MARKS := [
	["01_cloister", Vector3(1.0, 1.7, 15.5), Vector3(14.2, 0.4, 0.0), ""],
	["02_cloister_beam", Vector3(16.6, 1.8, 7.5), Vector3(13.0, -0.4, -7.0), "d1"],
	["03_nave", Vector3(0.0, 1.7, -21.0), Vector3(0.0, 4.0, -70.0), ""],
	["04_nave_clockwork", Vector3(-6.0, 3.0, -30.0), Vector3(1.0, -0.5, -50.0), "d2"],
	["05_choir_saints", Vector3(0.0, 4.2, -84.0), Vector3(0.0, 8.0, -110.0), ""],
	["06_crypt_prism", Vector3(-6.0, -6.2, -86.0), Vector3(2.0, -7.6, -100.0), "prism"],
	["07_crypt_panes", Vector3(5.0, -6.5, -112.0), Vector3(0.0, -7.2, -121.0), "prism3"],
	["08_tower", Vector3(-17.2, 9.6, -19.0), Vector3(-26.0, 14.0, -26.0), ""],
	["09_roof_reveal", Vector3(-19.0, 17.7, -33.0), Vector3(-30.0, 26.0, -60.0), "sky"],
	["10_buttresses", Vector3(-17.0, 17.6, -55.0), Vector3(-24.3, 18.0, -68.0), "sky"],
	["11_rose_phase1", H + Vector3(25.5, 1.7, 0.0), H + Vector3(-27.0, 10.0, 0.0), "rose1"],
	["12_rose_dark", H + Vector3(-15.0, 1.7, 0.0), H + Vector3(5.0, -0.5, -4.0), "rose2"],
	["13_east_window", Vector3(0.0, 3.4, -97.5), Vector3(0.0, 13.0, -121.0), "lens"],
	["14_shattered", Vector3(0.0, 4.0, -104.0), Vector3(0.0, 8.0, -122.0), "shatter"],
	["14b_fourth_sun", Vector3(1.3, 8.1, -121.6), Vector3(0.0, 7.75, -123.3), ""],
	["15_heist", Vector3(1.6, 8.0, -124.3), Vector3(-1.0, 4.0, -150.0), "heist"],
]

var _cam: Camera3D
var _w: Node
var _frame_ms: PackedFloat32Array = []
var _gpu_ms: PackedFloat32Array = []
var _recording := false


func _ready() -> void:
	if get_tree().current_scene == self:
		var r: Node = (get_script() as GDScript).new()
		r.name = "GlassShots"
		get_tree().root.add_child.call_deferred(r)
		return
	Save.save_path = "user://glass_shots.json"
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


func secs(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func _state(s: String) -> void:
	match s:
		"d1":
			_w.dials["d1"].set_index(1, true)
		"d2":
			_w.dials["d2"].set_index(2, true)
			_w.mirrors["m1"].set_index(1, true)
		"prism":
			_w.prism.set_index(1, true)
		"prism3":
			_w.prism.set_index(3, true)
			_w.mirrors["m6"].set_index(1, true)
		"sky":
			_w._reveal_sky()
		"rose1":
			_w.rose.set_active(true)
			_w.rose.t = 2.0
		"rose2":
			_w._take_lantern()
		"lens":
			_w.lantern_carried = true
			_w._place_lantern()
			for id: String in ["ruby", "azure"]:
				_w._restore(StringName(id), true)
				_w.mirrors["s_" + id.substr(0, 1)].set_index(1, true)
		"shatter":
			_w._restore(&"verdance", true)
			_w.mirrors["s_v"].set_index(1, true)
			await _until(func() -> bool: return _w.shattered, 6.0)
			await secs(2.5)
		"heist":
			_w._start_heist()


func _until(cond: Callable, timeout: float) -> void:
	var end := Time.get_ticks_msec() + int(timeout * 1000)
	while not cond.call() and Time.get_ticks_msec() < end:
		await get_tree().process_frame


func measure(label: String, s: float = 4.0) -> void:
	_frame_ms.clear()
	_gpu_ms.clear()
	_recording = true
	await secs(s)
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
	print("[perf]   cpu process=%.2f ms physics=%.2f ms draws=%d objects=%d prims=%d" % [Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0, Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)])
	print("[perf] %-18s avg=%.2f ms (%.0f fps) p95=%.2f ms max=%.2f ms | gpu avg=%.2f p95=%.2f" % [
		label, avg, 1000.0 / avg, f[int(f.size() * 0.95)], f[-1], gavg, g[int(g.size() * 0.95)]])


func _perf_diag() -> void:
	_cam = Camera3D.new()
	get_tree().current_scene.add_child(_cam)
	_cam.global_position = Vector3(0.0, 1.7, -21.0)
	_cam.look_at(Vector3(0.0, 4.0, -70.0), Vector3.UP)
	_cam.make_current()
	var env: Environment = _w.env
	await secs(1.0)
	await measure("all on")
	env.volumetric_fog_enabled = false
	await measure("fog off")
	env.ssao_enabled = false
	await measure("+ssao off")
	get_viewport().msaa_3d = Viewport.MSAA_DISABLED
	await measure("+msaa off")
	(_w.get_node("Sun") as DirectionalLight3D).shadow_enabled = false
	await measure("+sun shadow off")
	for l: Light3D in _w.find_children("*", "Light3D", true, false):
		if not l is DirectionalLight3D:
			l.visible = false
	await measure("+local lights off")
	var cats := {"beams": [], "windows": [], "glass": [], "multimesh": [], "other": []}
	for gi: GeometryInstance3D in _w.find_children("*", "GeometryInstance3D", true, false):
		var m: Material = gi.material_override
		var sh := ""
		if m is ShaderMaterial and (m as ShaderMaterial).shader:
			sh = (m as ShaderMaterial).shader.resource_path.get_file()
		if gi is MultiMeshInstance3D:
			cats["multimesh"].append(gi)
		elif sh == "beam.gdshader":
			cats["beams"].append(gi)
		elif sh == "window.gdshader":
			cats["windows"].append(gi)
		elif sh == "leaded_glass.gdshader":
			cats["glass"].append(gi)
		else:
			cats["other"].append(gi)
	for k: String in cats:
		for gi: GeometryInstance3D in cats[k]:
			gi.visible = false
		await measure("+%s off (%d)" % [k, cats[k].size()])


func _run() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	if OS.has_environment("GLASS_PERF_HUB"):
		await Game.enter_wing(Game.HUB_ID)
		await secs(3.0)
		await measure("atrium baseline")
		get_tree().quit()
		return
	await Game.enter_wing(&"glass")
	_w = Game.wing
	await secs(1.0)
	if Cinematics.playing:
		Cinematics.skip()
	await _until(func() -> bool: return not Cinematics.playing and not Transitions.busy, 15.0)
	Game.player.input_enabled = false
	Game.player.visible = false
	DisplayServer.window_move_to_foreground()
	if OS.has_environment("GLASS_PERF_DIAG"):
		await _perf_diag()
		get_tree().quit()
		return
	var only := OS.get_environment("GLASS_SHOTS")  # e.g. "03_nave,04" to re-shoot a few
	for m: Array in MARKS:
		await _state(m[3])
		if only != "" and not Array(only.split(",")).any(func(o: String) -> bool: return (m[0] as String).begins_with(o)):
			continue
		if _cam == null or not is_instance_valid(_cam):
			_cam = Camera3D.new()
			_cam.fov = 75.0
			_cam.far = 800.0
			get_tree().current_scene.add_child(_cam)
		_cam.global_position = m[1]
		_cam.look_at(m[2], Vector3.UP)
		_cam.make_current()
		await secs(1.2)
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var path := ProjectSettings.globalize_path("%s/%s.png" % [OUT, m[0]])
		img.save_png(path)
		print("[shots] ", path, "  ", img.get_size())
		await measure(m[0], 2.0)
	get_tree().quit()
