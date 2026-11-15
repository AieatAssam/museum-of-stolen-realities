extends CanvasLayer
## Pause menu (Esc). Built by Game.open_menu(&"pause").

var _center: CenterContainer
var _main: VBoxContainer


func _ready() -> void:
	layer = 85
	process_mode = Node.PROCESS_MODE_ALWAYS
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.017, 0.012, 0.78)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_center = CenterContainer.new()
	_center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_center)
	_build_main()


func _build_main() -> void:
	for c in _center.get_children():
		c.queue_free()
	_main = VBoxContainer.new()
	_main.add_theme_constant_override(&"separation", 10)
	_main.alignment = BoxContainer.ALIGNMENT_CENTER
	_center.add_child(_main)
	var info := Game.registry.get_info(Game.wing.wing_id) if Game.wing else null
	_main.add_child(Style.catalog(info.numeral + "  ·  " + info.acquisition_no if info else "The Atrium", 16, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER))
	_main.add_child(Style.label(info.title if info else "Intermission", Style.DISPLAY, 56, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER))
	_main.add_child(Style.rule(240))
	var first := _btn("Resume", Game.resume)
	_btn("Journal", func() -> void:
		Game.resume()
		Game.open_menu(&"journal"))
	_btn("Settings", _show_settings)
	if Game.wing and Game.wing.wing_id != Game.HUB_ID:
		_btn("Return to the Atrium", func() -> void:
			get_tree().paused = false
			Game.return_to_hub())
	_btn("Quit to Title", func() -> void:
		get_tree().paused = false
		Game.quit_to_title())
	first.grab_focus.call_deferred()


func _btn(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(func() -> void:
		Audio.ui(&"select")
		cb.call())
	b.mouse_entered.connect(func() -> void: Audio.ui(&"hover"))
	b.focus_entered.connect(func() -> void: Audio.ui(&"hover", -6.0))
	_main.add_child(b)
	return b


func _show_settings() -> void:
	for c in _center.get_children():
		c.queue_free()
	var s := preload("res://ui/settings_panel.gd").new()
	s.closed.connect(_build_main)
	_center.add_child(s)
