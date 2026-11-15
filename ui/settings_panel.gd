extends VBoxContainer
## Settings controls bound to Save.settings. Used by the title screen and the pause menu.

signal closed


func _ready() -> void:
	add_theme_constant_override(&"separation", 14)
	custom_minimum_size.x = 620
	add_child(Style.label("Settings", Style.DISPLAY, Style.SIZE_HEADING, Style.IVORY))
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override(&"h_separation", 32)
	grid.add_theme_constant_override(&"v_separation", 12)
	add_child(grid)

	var q := OptionButton.new()
	for p: String in Quality.PRESETS:
		q.add_item(p.capitalize().left(1) + p.capitalize().substr(1).to_lower())
	q.selected = Quality.level()
	q.item_selected.connect(func(i: int) -> void: Save.set_setting("quality", Quality.PRESETS[i]))
	_row(grid, "Quality", q)
	_row(grid, "Resolution scale", _slider("render_scale", 0.5, 1.0, 0.05))
	_row(grid, "Field of view", _slider("fov", 70.0, 110.0, 1.0))
	_row(grid, "Mouse sensitivity", _slider("mouse_sensitivity", 0.03, 0.4, 0.01))
	_row(grid, "Invert look", _check("invert_y"))
	_row(grid, "Reduced motion", _check("reduced_motion"))
	_row(grid, "Head bob", _slider("head_bob", 0.0, 1.0, 0.05))
	_row(grid, "Sprint FOV kick", _slider("fov_kick", 0.0, 1.0, 0.05))
	_row(grid, "Camera shake", _slider("camera_shake", 0.0, 1.0, 0.05))
	_row(grid, "Strafe roll", _slider("strafe_roll", 0.0, 1.0, 0.05))
	_row(grid, "Fullscreen", _check("fullscreen"))
	_row(grid, "Vertical sync", _check("vsync"))
	_row(grid, "Master", _slider("vol_master", 0.0, 1.0, 0.05))
	_row(grid, "Music", _slider("vol_music", 0.0, 1.0, 0.05))
	_row(grid, "Effects", _slider("vol_sfx", 0.0, 1.0, 0.05))
	_row(grid, "Ambience", _slider("vol_ambience", 0.0, 1.0, 0.05))

	var back := Button.new()
	back.text = "Return"
	back.pressed.connect(func() -> void:
		Audio.ui(&"back")
		closed.emit())
	back.mouse_entered.connect(func() -> void: Audio.ui(&"hover"))
	add_child(back)
	back.grab_focus.call_deferred()


func _row(grid: GridContainer, text: String, ctl: Control) -> void:
	grid.add_child(Style.label(text, Style.TEXT, Style.SIZE_META, Style.IVORY))
	ctl.custom_minimum_size.x = 300
	ctl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	grid.add_child(ctl)


func _slider(key: String, lo: float, hi: float, step: float) -> HSlider:
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = float(Save.settings[key])
	s.value_changed.connect(func(v: float) -> void: Save.set_setting(key, v))
	return s


func _check(key: String) -> CheckButton:
	var c := CheckButton.new()
	c.button_pressed = bool(Save.settings[key])
	c.toggled.connect(func(v: bool) -> void: Save.set_setting(key, v))
	return c
