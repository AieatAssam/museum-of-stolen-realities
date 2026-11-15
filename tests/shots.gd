extends Node
## Screenshots + frame timing for one wing, at named camera marks. Needs a window (not --headless):
##   Godot --path . --resolution 2560x1440 tests/shots.tscn -- --wing=_template [--ui] [--secs=4]
## --wing    a wing id or "atrium" (default atrium)
## --ui      keep the HUD, placards and cinematic overlays (hidden by default: clean frames)
## --secs    seconds measured at each mark (default 4)
## Marks: every Marker3D under the wing's `ShotMarks` node (the camera sits on the marker and looks
## down its -Z). A wing without ShotMarks is shot from the player's view only; the atrium falls back
## to ATRIUM_MARKS. Output: shots/<wing>/<mark>.png and one [perf] line per mark.
##
## What [perf] measures (vsync off, max_fps 0):
##   frame   wall time between frames (delta): what the player feels; includes GPU stalls.
##   cpu     render-thread CPU time to record the frame (viewport_get_measured_render_time_cpu).
##   gpu     GPU time from timestamp queries. Metal (macOS) returns 0 for these, so it prints
##           "n/a (driver)" there; read `frame` minus `cpu` as the GPU-bound share instead.
## Each as avg / p95 / p99 ms. Uses a throwaway save (user://shots_save.json).

const OUT := "res://shots"
const ATRIUM_MARKS := {  # [position, look-at]; hub/ has no ShotMarks node yet
	"atrium_wide": [Vector3(3.5, 2.2, 21.0), Vector3(-1.0, 5.0, 0.0)],
	"frames": [Vector3(-6.0, 1.7, 6.0), Vector3(-20.0, 3.5, -6.0)],
	"sphere": [Vector3(4.2, 3.4, 6.8), Vector3(0.0, 5.4, 0.0)],
	"alcove": [Vector3(0.0, 1.8, -17.5), Vector3(0.0, 1.0, -28.0)],
}

var _args := {"wing": "atrium", "secs": "4"}
var _rec: Array[PackedFloat32Array] = [PackedFloat32Array(), PackedFloat32Array(), PackedFloat32Array()]
var _recording := false


func _ready() -> void:
	if get_tree().current_scene == self:  # outlive the scene change
		var runner: Node = (get_script() as GDScript).new()
		get_tree().root.add_child.call_deferred(runner)
		return
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		_args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	Save.save_path = "user://shots_save.json"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _process(delta: float) -> void:
	if _recording:
		var rid := get_viewport().get_viewport_rid()
		_rec[0].append(delta * 1000.0)
		_rec[1].append(RenderingServer.viewport_get_measured_render_time_cpu(rid))
		_rec[2].append(RenderingServer.viewport_get_measured_render_time_gpu(rid))


func _run() -> void:
	var id := StringName(_args["wing"])
	var dir := "%s/%s" % [OUT, id]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	FileAccess.open(OUT + "/.gdignore", FileAccess.WRITE)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var ok: bool = await Game.debug_goto(Game.HUB_ID if id == &"atrium" else id)
	if not ok:
		push_error("shots: could not enter %s" % id)
		get_tree().quit(1)
		return
	await _settle_cinematics()
	print("[shots] %s  window %s  quality %s" % [id, DisplayServer.window_get_size(), Save.settings["quality"]])
	if not _args.has("ui"):
		for n: String in ["/root/Placards", "/root/Cinematics"]:
			(get_node(n) as CanvasLayer).visible = false
		if Game._hud:
			Game._hud.visible = false
	await _measure_at("player_view", dir, null)
	var cam := Camera3D.new()
	cam.fov = 70.0
	cam.far = 600.0
	Game.wing.add_child(cam)
	var marks := Game.wing.get_node_or_null("ShotMarks")
	if marks:
		for m: Node in marks.get_children():
			if m is Node3D:
				cam.global_transform = (m as Node3D).global_transform
				await _measure_at(m.name, dir, cam)
	elif id == &"atrium":
		for n: String in ATRIUM_MARKS:
			cam.global_position = ATRIUM_MARKS[n][0]
			cam.look_at(ATRIUM_MARKS[n][1])
			await _measure_at(n, dir, cam)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	print("[shots] done -> ", ProjectSettings.globalize_path(dir))
	Game.quit(0)


func _settle_cinematics() -> void:
	await get_tree().create_timer(0.5).timeout
	while Cinematics.playing:
		Cinematics.skip()
		await get_tree().create_timer(0.2).timeout
	await get_tree().create_timer(1.0).timeout


func _measure_at(mark: String, dir: String, cam: Camera3D) -> void:
	if cam:
		cam.make_current()
	await get_tree().create_timer(0.8).timeout  # let streaming, SDFGI and auto-exposure settle
	await RenderingServer.frame_post_draw
	var path := "%s/%s.png" % [dir, mark]
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(path))
	for r in _rec:
		r.clear()
	_recording = true
	await get_tree().create_timer(float(_args["secs"])).timeout
	_recording = false
	var gpu := _stats(_rec[2])
	print("[perf] %-16s frames=%d  frame %s  cpu %s  gpu %s" % [mark, _rec[0].size(), _stats(_rec[0]), _stats(_rec[1]),
		"n/a (driver)" if _rec[2].is_empty() or _sorted(_rec[2])[-1] == 0.0 else gpu])


func _sorted(a: PackedFloat32Array) -> Array:
	var s := Array(a)
	s.sort()
	return s


func _stats(a: PackedFloat32Array) -> String:
	if a.is_empty():
		return "-"
	var s := _sorted(a)
	var avg := 0.0
	for v: float in s:
		avg += v
	avg /= s.size()
	return "avg %.2f p95 %.2f p99 %.2f ms" % [avg, s[int(s.size() * 0.95)], s[mini(int(s.size() * 0.99), s.size() - 1)]]
