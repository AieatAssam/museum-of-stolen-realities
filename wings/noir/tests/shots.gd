extends Node
## Noir screenshot harness (windowed, not headless). Jumps to the noir wing, frames each mark
## with a camera teleport, saves PNGs, and prints frame-time stats.
## Run:  Godot --path . wings/noir/tests/shots.tscn

const OUT := "/private/tmp/claude-501/-Users-aieat--claude-spares-spare-oxJofr/788ae2ca-fb42-43d8-942d-e0b8cc7ce803/scratchpad/noir_shots"

# [file, position, look-at]
const MARKS := [
	["01_alley_entry", Vector3(0, 1.4, -3.0), Vector3(0, 1.2, -15.0)],
	["02_latch_wall", Vector3(0, 1.4, -18.0), Vector3(0, 1.6, -21.0)],
	["03_pawn_crate", Vector3(-2.0, 1.2, -10.0), Vector3(-3.2, 0.8, -12.0)],
	["04_lit_street", Vector3(0, 1.6, -22.0), Vector3(0, 0.5, -40.0)],
	["05_covers_caster", Vector3(0, 1.6, -36.0), Vector3(-0.6, 0.9, -44.0)],
	["06_plaza_figures", Vector3(0, 1.6, -54.0), Vector3(0, 1.2, -58.0)],
	["07_better_half", Vector3(-2.0, 1.6, -55.5), Vector3(-1.4, 1.0, -58.0)],
	["08_cinema_entry", Vector3(0, 1.6, -70.0), Vector3(0, 1.5, -84.0)],
	["09_searchlights", Vector3(0, 3.0, -82.0), Vector3(-5.0, 0.0, -76.0)],
	["10_reel_pedestal", Vector3(0, 1.6, -82.0), Vector3(0, 0.8, -86.0)],
	["11_booth_fragment", Vector3(0, 1.6, -95.5), Vector3(0, 1.2, -97.0)],
]


func _ready() -> void:
	if get_tree().current_scene == self:
		var runner: Node = (get_script() as GDScript).new()
		runner.name = "NoirShots"
		get_tree().root.add_child.call_deferred(runner)
		queue_free()
		return
	Save.save_path = "user://noir_shots.json"
	_run.call_deferred()


func _shot(file: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := OUT + "/" + file + ".png"
	img.save_png(path)
	print("SHOT ", path)


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(OUT)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	await Game.debug_goto(&"noir")
	for i in 120:
		await get_tree().process_frame
	await get_tree().create_timer(2.0, true, false, true).timeout
	if Cinematics.playing:
		Cinematics.skip()
	await get_tree().create_timer(0.5, true, false, true).timeout

	for mark in MARKS:
		Game.debug_teleport(mark[1], mark[2])
		for i in 20:
			await get_tree().process_frame
		await _shot(mark[0])

	# frame-time sample at the lit street, measured over 300 frames
	Game.debug_teleport(MARKS[3][1], MARKS[3][2])
	for i in 60:
		await get_tree().process_frame
	var samples: Array[float] = []
	var last := Time.get_ticks_usec()
	for i in 300:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		samples.append((now - last) / 1000.0)
		last = now
	samples.sort()
	var avg := 0.0
	for s in samples:
		avg += s
	avg /= samples.size()
	print("[perf] noir lit street frames=%d avg=%.2f ms p50=%.2f ms p95=%.2f ms worst=%.2f ms (%.0f fps avg)" % [
		samples.size(), avg, samples[samples.size() / 2], samples[int(samples.size() * 0.95)], samples[-1], 1000.0 / avg])

	get_tree().quit(0)
