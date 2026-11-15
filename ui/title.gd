extends Control
## Title screen: the real atrium, rendered live behind the menu (DESIGN_RULES §7), with a slow
## camera drift. The atrium is a child of this scene (not of root), so Game does not register it
## as the current wing: no player, no quest, no intro. The menu sits on the dark left side, on a
## soft backing, in a CanvasLayer above Post so text gets no grain or aberration.

const DRIFT_SECS := 70.0
const CAM_A := Vector3(5.5, 2.1, 20.0)
const CAM_B := Vector3(1.5, 2.6, 17.0)
const LOOK := Vector3(-3.5, 4.4, 0.0)  # left of the sphere, so the sphere sits right of centre

var _menu: VBoxContainer
var _panel_host: Control
var _left: VBoxContainer
var _cam: Camera3D
var _t: float = 0.0


func _ready() -> void:
	Game.set_state(Game.State.TITLE)
	Post.apply(PostGrade.new(), 0.0)
	Post.fade_to(0.0, 0.0)
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var black := ColorRect.new()  # shown only if the atrium fails to load
	black.color = Style.INK
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(black)

	var atrium_scene := load(Game.HUB_SCENE) as PackedScene
	if atrium_scene:
		var atrium := atrium_scene.instantiate()
		add_child(atrium)
		if atrium is Wing:
			Quality.apply((atrium as Wing).environment())
		black.visible = false
	_cam = Camera3D.new()
	_cam.fov = 62.0
	_cam.far = 600.0
	add_child(_cam)
	_cam.make_current()
	_place_camera()

	var ui := CanvasLayer.new()
	ui.layer = 65
	add_child(ui)
	var shade := TextureRect.new()  # backing: ink fading out to the right
	var g := Gradient.new()
	g.set_color(0, Color(Style.INK, 0.88))
	g.set_color(1, Color(Style.INK, 0.0))
	g.add_point(0.55, Color(Style.INK, 0.7))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.width = 256
	gt.height = 4
	shade.texture = gt
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.anchor_bottom = 1.0
	shade.offset_right = 1000
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(shade)

	_left = VBoxContainer.new()
	_left.anchor_top = 0.5
	_left.anchor_bottom = 0.5
	_left.offset_left = 150
	_left.offset_top = -240
	_left.add_theme_constant_override(&"separation", 40)
	ui.add_child(_left)
	var t := Style.label("Museum of Stolen Realities", Style.DISPLAY, Style.SIZE_TITLE, Style.IVORY)
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.custom_minimum_size.x = 640
	_left.add_child(t)
	_menu = VBoxContainer.new()
	_menu.add_theme_constant_override(&"separation", 4)
	_left.add_child(_menu)

	_panel_host = PanelContainer.new()
	_panel_host.add_theme_stylebox_override(&"panel", Style.backing(0.9, 40))
	_panel_host.anchor_top = 0.5
	_panel_host.anchor_bottom = 0.5
	_panel_host.offset_left = 150
	_panel_host.grow_vertical = Control.GROW_DIRECTION_BOTH
	_panel_host.visible = false
	ui.add_child(_panel_host)

	_build_menu()
	_left.modulate.a = 0.0
	create_tween().tween_property(_left, "modulate:a", 1.0, 2.0).set_trans(Tween.TRANS_SINE)
	# the hub theme, half its bands: the atrium picks up the same playback (no restart) on New Game
	var theme: Array[AudioStream] = []
	for i in 7:
		theme.append(Audio.stream("hub_theme_%d" % i))
	Audio.play_music(theme, 4.0, 0.5)
	Audio.play_ambience(Audio.stream("amb_hub"), 4.0, -6.0)


func _build_menu() -> void:
	for c in _menu.get_children():
		c.queue_free()
	var first: Button = null
	if Save.has_save():
		first = _btn("Continue", func() -> void: Game.continue_game())
	var ng := _btn("New game", func() -> void: Game.new_game())
	_btn("Settings", _show_settings)
	_btn("Quit", func() -> void: Game.quit())
	(first if first else ng).grab_focus.call_deferred()


func _btn(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.add_theme_font_size_override(&"font_size", Style.SIZE_SUBHEADING)
	b.pressed.connect(func() -> void:
		if Transitions.busy:
			return
		Audio.ui(&"select")
		cb.call())
	b.mouse_entered.connect(func() -> void:
		Audio.ui(&"hover")
		b.grab_focus())
	_menu.add_child(b)
	return b


func _show_settings() -> void:
	_left.visible = false
	_panel_host.visible = true
	var s := preload("res://ui/settings_panel.gd").new()
	_panel_host.add_child(s)
	s.closed.connect(func() -> void:
		s.queue_free()
		_panel_host.visible = false
		_left.visible = true
		_build_menu())


func _place_camera() -> void:
	var u := 0.5 - 0.5 * cos(_t / DRIFT_SECS * TAU)  # ping-pong A..B, eased at the ends
	_cam.position = CAM_A.lerp(CAM_B, u)
	_cam.look_at(LOOK + Vector3(0, 0.3 * sin(_t * 0.05), 0), Vector3.UP)


func _process(delta: float) -> void:
	_t += delta
	_place_camera()
