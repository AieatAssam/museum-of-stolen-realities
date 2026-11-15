extends Node
## Screenshot every UI surface (windowed, real render; not --headless):
##   Godot --path . --resolution 1920x1080 tests/ui_shots.tscn -- --out=after_1080
## PNGs land in shots/ui_<out>/: title, title settings, HUD + toast, interaction prompt, in-world
## plaque, placard reader, cinematic card, pause, pause settings, journal, atrium plaque, credits.

var _out := "res://shots/ui_default"


func _ready() -> void:
	if get_tree().current_scene == self:
		var r: Node = (get_script() as GDScript).new()
		r.name = "UiShotsRunner"
		get_tree().root.add_child.call_deferred(r)
		return
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = "res://shots/ui_" + a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(_out))
	FileAccess.open("res://shots/.gdignore", FileAccess.WRITE)
	Save.save_path = "user://ui_shots_save.json"
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	Save.load_game()
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func seconds(t: float) -> void:
	await get_tree().create_timer(t, true, false, true).timeout


func shot(n: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path("%s/%s.png" % [_out, n]))
	print("[ui_shots] ", n, " ", img.get_size())


func _skip() -> void:
	await seconds(0.3)
	while Cinematics.playing:
		Cinematics.skip()
		await seconds(0.2)


func _run() -> void:
	get_tree().change_scene_to_file(Game.TITLE_SCENE)
	await seconds(4.0)
	await shot("01_title")
	var title := get_tree().current_scene
	title.call(&"_show_settings")
	await seconds(0.5)
	await shot("02_title_settings")

	await Game.debug_goto(&"_template")
	await _skip()
	await seconds(2.5)
	# a worst-case (40-word) tombstone toast, queued behind the wing's own
	Placards.toast(Placard.fields("A note on the lamps", "Undated", "Lamp oil on brass", "Acq. No. 000-T",
		"Staff are reminded that the lamps in this studio are original to the collection and must be lit in order. Visitors who light them out of order will be thanked and asked, politely, to begin again from the very first."))
	while Placards.history.size() < 2 or not Placards.toast_visible() or Placards._card_parts[0].text != "A note on the lamps":
		await get_tree().process_frame
	await seconds(1.0)
	await shot("03_hud_toast")
	Game.debug_teleport(Vector3(-5, 0, -5.4), Vector3(-5, 0.6, -7))
	await seconds(0.8)
	await shot("04_prompt")
	Game.debug_teleport(Vector3(-3, 0, 6.6), Vector3(-3, 1.6, 7.9))
	await seconds(0.8)
	await shot("05_plaque_template")
	var plaque: Node = Game.wing.get_node("Placard")
	for c in plaque.get_children():
		if c is Interactable:
			(c as Interactable).interacted.emit(Game.player)
	await seconds(0.8)
	await shot("06_reader")
	Placards.close_reader()
	Cinematics.play([{"card": "Staff only.", "sub": "The Conservation Studio", "t": 4.0, "style": "display"}])
	await seconds(2.0)
	await shot("07_cinematic_card")
	await _skip()
	Game.open_menu(&"pause")
	await seconds(0.6)
	await shot("08_pause")
	Game._menu.call(&"_show_settings")
	await seconds(0.5)
	await shot("09_pause_settings")
	Game.resume()
	Game.open_menu(&"journal")
	await seconds(0.6)
	await shot("10_journal")
	Game.resume()

	await Game.return_to_hub()
	await _skip()
	Game.debug_teleport(Vector3(0, 0, 8.4), Vector3(0, 0.95, 6.3))
	await seconds(1.5)
	await shot("11_plaque_atrium")
	if Game.wing.has_method(&"_credits"):
		Cinematics.play(Game.wing.call(&"_credits"))
		await seconds(2.5)
		await shot("12_credits_a")
		await seconds(6.0)
		await shot("13_credits_b")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Save.save_path))
	print("[ui_shots] done")
	Game.quit(0)
