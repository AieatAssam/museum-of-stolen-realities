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
	var dir := "%s/%s%s" % [OUT, id, ("_f" + String(_args["fragments"])) if _args.has("fragments") else ""]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	FileAccess.open(OUT + "/.gdignore", FileAccess.WRITE)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	if id == &"atrium" and _args.has("fragments"):  # --fragments=N: the hall after N wings came home
		Save.data["hub"]["seen_intro"] = true
		var placed: Array = []
		for w: WingInfo in Game.registry.exhibits().slice(0, int(_args["fragments"])):
			Game.debug_complete_wing(w.id)
			placed.append(String(w.id))
		Save.data["hub"]["flags"]["placed"] = placed
	var ok: bool = await Game.debug_goto(Game.HUB_ID if id == &"atrium" else id)
	if not ok:
		push_error("shots: could not enter %s" % id)
		get_tree().quit(1)
		return
	await _settle_cinematics()
	_switch_off(String(_args.get("off", "")).split(",", false))
	print("[shots] %s  window %s  quality %s  3d scale %.2f mode %d  off %s  load %s" % [id, DisplayServer.window_get_size(),
		Save.settings["quality"], get_viewport().scaling_3d_scale, get_viewport().scaling_3d_mode, _args.get("off", "-"), _loadavg()])
	if not _args.has("ui"):
		for n: String in ["/root/Placards", "/root/Cinematics"]:
			(get_node(n) as CanvasLayer).visible = false
		if Game._hud:  # the HUD re-shows itself every frame while playing: stop it, then hide
			Game._hud.process_mode = Node.PROCESS_MODE_DISABLED
			Game._hud.visible = false
	if _args.has("ab"):
		await _run_ab(String(_args["ab"]), String(_args.get("marks", "")).split(",", false))
		Game.quit(0)
		return
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


func _loadavg() -> String:
	var out: Array = []
	OS.execute("sysctl", ["-n", "vm.loadavg"], out)
	return String(out[0]).strip_edges() if out.size() > 0 else "?"


## --off=fog,ssr,ssao,glow,msaa,sphere,shadows: switch features off to find where the GPU time goes.
func _switch_off(what: PackedStringArray) -> void:
	var we := get_tree().root.find_children("*", "WorldEnvironment", true, false)
	var env: Environment = (we[0] as WorldEnvironment).environment if not we.is_empty() else Environment.new()
	for w in what:
		match w:
			"fog": env.volumetric_fog_enabled = false
			"ssr": env.ssr_enabled = false
			"ssao": env.ssao_enabled = false
			"glow": env.glow_enabled = false
			"msaa": get_viewport().msaa_3d = Viewport.MSAA_DISABLED
			"shadows":
				for l: Light3D in get_tree().root.find_children("*", "Light3D", true, false):
					l.shadow_enabled = false
			"sphere":
				var skin: ShaderMaterial = Game.wing.get("_skin")
				if skin:
					skin.set_shader_parameter("volume", 0.0)


## --ab=lever [--marks=a,b] [--rounds=3]: interleaved A/B at each mark (A,B,A,B,...) in one process, so
## load and thermals hit both sides alike. Prints mean frame ms per side. Levers: see _lever().
func _run_ab(lever: String, only: PackedStringArray) -> void:
	print("[ab] defaults: ssr half %s  ssao q %s half %s" % [ProjectSettings.get_setting("rendering/environment/screen_space_reflection/half_size", "?"),
		ProjectSettings.get_setting("rendering/environment/ssao/quality"), ProjectSettings.get_setting("rendering/environment/ssao/half_size")])
	var cam := Camera3D.new()
	cam.fov = 70.0
	cam.far = 600.0
	Game.wing.add_child(cam)
	var views: Array = []  # [name, Transform3D]
	var marks := Game.wing.get_node_or_null("ShotMarks")
	if marks:
		for m: Node in marks.get_children():
			if m is Node3D:
				views.append([String(m.name), (m as Node3D).global_transform])
	else:
		for n: String in ATRIUM_MARKS:
			views.append([n, Transform3D.IDENTITY.translated(ATRIUM_MARKS[n][0]).looking_at(ATRIUM_MARKS[n][1])])
	cam.make_current()
	if _args.has("base"):  # --base=fsr77: held on for both sides, so the lever's marginal cost shows
		_lever(String(_args["base"]), true)
	for v: Array in views:
		if not only.is_empty() and not only.has(v[0]):
			continue
		cam.global_transform = v[1]
		var sums := [0.0, 0.0]
		var runs := [[], []]
		for r in int(_args.get("rounds", "3")):
			for side in 2:
				_lever(lever, side == 1)
				await get_tree().create_timer(0.6).timeout
				for x in _rec:
					x.clear()
				_recording = true
				await get_tree().create_timer(float(_args["secs"])).timeout
				_recording = false
				var avg := 0.0
				for f: float in _rec[0]:
					avg += f
				avg /= maxi(_rec[0].size(), 1)
				runs[side].append("%.1f" % avg)
				sums[side] += avg
		var n := float(runs[0].size())
		print("[ab] %-6s %-14s A %.2f  B %.2f  delta %+.2f ms   A%s B%s  load %s" % [lever, v[0], sums[0] / n, sums[1] / n,
			(sums[1] - sums[0]) / n, runs[0], runs[1], _loadavg()])
	_lever(lever, false)


func _lever(lever: String, on: bool) -> void:
	if "+" in lever:  # a package: msaa+fsr77
		for l in lever.split("+"):
			_lever(l, on)
		return
	var vp := get_viewport()
	if lever.begins_with("fsr") or lever.begins_with("bil"):  # fsr77, bil85: 3D scale 0.77 / 0.85
		vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if lever.begins_with("fsr") and on else Viewport.SCALING_3D_MODE_BILINEAR
		vp.scaling_3d_scale = float(lever.substr(3)) / 100.0 if on else 1.0
		return
	var env: Environment = Game.wing.environment() if Game.wing else null
	match lever:
		"none": pass
		"newq":  # B: the shipped "high" preset + auto scale; A: the pre-2026-11 high (MSAA 2x + FXAA, fog 96^3, native)
			if on:  # mirrors Quality.apply at high (not called: it would undo chitin's SSR step clamp)
				vp.msaa_3d = Viewport.MSAA_DISABLED
				vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_SMAA
				RenderingServer.environment_set_volumetric_fog_volume_size(64, 64)
				Save._apply_render_scale()
			else:
				vp.msaa_3d = Viewport.MSAA_2X
				vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
				RenderingServer.environment_set_volumetric_fog_volume_size(96, 96)
				vp.scaling_3d_scale = 1.0
				vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
		"fog64": RenderingServer.environment_set_volumetric_fog_volume_size(64 if on else 96, 64 if on else 96)
		"fog64x48": RenderingServer.environment_set_volumetric_fog_volume_size(64 if on else 96, 48 if on else 96)
		"fogfilter": RenderingServer.environment_set_volumetric_fog_filter_active(not on)
		"fogoff": env.volumetric_fog_enabled = not on
		"msaa": vp.msaa_3d = Viewport.MSAA_DISABLED if on else Viewport.MSAA_2X
		"ssroff": env.ssr_enabled = not on
		"ssrrough": RenderingServer.environment_set_ssr_roughness_quality(
			RenderingServer.ENV_SSR_ROUGHNESS_QUALITY_LOW if on else ProjectSettings.get_setting("rendering/environment/screen_space_reflection/roughness_quality"))
		"ssaooff": env.ssao_enabled = not on
		"ssaolow": RenderingServer.environment_set_ssao_quality(
			RenderingServer.ENV_SSAO_QUALITY_LOW if on else ProjectSettings.get_setting("rendering/environment/ssao/quality"),
			ProjectSettings.get_setting("rendering/environment/ssao/half_size"), 0.5, 2, 50.0, 300.0)
		"glowoff": env.glow_enabled = not on
		"glowbicubic": RenderingServer.environment_glow_set_use_bicubic_upscale(not on)
		"softshadow":
			RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW if on else RenderingServer.SHADOW_QUALITY_SOFT_MEDIUM)
			RenderingServer.positional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW if on else RenderingServer.SHADOW_QUALITY_SOFT_MEDIUM)
		"atlas2k":
			RenderingServer.directional_shadow_atlas_set_size(2048 if on else 4096, true)
			vp.positional_shadow_atlas_size = 2048 if on else 4096
		"ssrhalf": RenderingServer.environment_set_ssr_half_size(on != bool(
			ProjectSettings.get_setting("rendering/environment/screen_space_reflection/half_size", true)))  # flips the default
		_: push_error("unknown lever " + lever)


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
