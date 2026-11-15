extends Control
## Title screen: the atrium matte painting breathing slowly behind museum typography.

var _bg: TextureRect
var _menu: VBoxContainer
var _panel_host: CenterContainer
var _left: VBoxContainer
var _t: float = 0.0


func _ready() -> void:
	Game.set_state(Game.State.TITLE)
	Post.apply(PostGrade.new(), 0.0)
	Post.fade_to(0.0, 0.0)
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var black := ColorRect.new()
	black.color = Style.INK
	black.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(black)

	_bg = TextureRect.new()
	_bg.texture = preload("res://assets/ui/title_art.png")
	_bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	var m := ShaderMaterial.new()
	m.shader = preload("res://ui/title_bg.gdshader")
	_bg.material = m
	add_child(_bg)

	var motes := GPUParticles2D.new()
	motes.amount = 90
	motes.lifetime = 14.0
	motes.preprocess = 14.0
	motes.position = Vector2(1200, 1100)
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(1100, 80, 0)
	pm.direction = Vector3(0.1, -1, 0)
	pm.spread = 25.0
	pm.initial_velocity_min = 18.0
	pm.initial_velocity_max = 55.0
	pm.gravity = Vector3.ZERO
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 3.0
	pm.turbulence_noise_scale = 4.0
	pm.scale_min = 0.6
	pm.scale_max = 2.4
	var ramp := Gradient.new()
	ramp.set_color(0, Color(1.0, 0.8, 0.45, 0.0))
	ramp.set_color(1, Color(1.0, 0.8, 0.45, 0.0))
	ramp.add_point(0.2, Color(1.0, 0.85, 0.5, 0.8))
	ramp.add_point(0.8, Color(1.0, 0.8, 0.45, 0.5))
	var gt := GradientTexture1D.new()
	gt.gradient = ramp
	pm.color_ramp = gt
	motes.process_material = pm
	motes.texture = _dot_texture()
	var add := CanvasItemMaterial.new()
	add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	motes.material = add
	add_child(motes)

	_left = VBoxContainer.new()
	_left.position = Vector2(150, 0)
	_left.anchor_top = 0.5
	_left.anchor_bottom = 0.5
	_left.offset_top = -330
	_left.add_theme_constant_override(&"separation", 6)
	add_child(_left)
	_left.add_child(Style.catalog("An exhibition in six acquisitions", 17, Style.GOLD))
	_left.add_child(Control.new())
	var l1 := Style.label("Museum of", Style.LIGHT, 64, Style.IVORY)
	_left.add_child(l1)
	var l2 := Style.label("Stolen Realities", Style.DISPLAY, 104, Style.IVORY)
	l2.add_theme_constant_override(&"outline_size", 0)
	_left.add_child(l2)
	var r := Style.rule(360, Style.GOLD)
	r.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_left.add_child(r)
	var spacer := Control.new()
	spacer.custom_minimum_size.y = 40
	_left.add_child(spacer)
	_menu = VBoxContainer.new()
	_menu.add_theme_constant_override(&"separation", 6)
	_left.add_child(_menu)

	var foot := Style.catalog("Acquisition No. 000  ·  The Thief  ·  Medium: flesh, grief, intent", 13, Style.GOLD_DIM)
	foot.anchor_top = 1.0
	foot.anchor_bottom = 1.0
	foot.position = Vector2(150, -70)
	add_child(foot)

	_panel_host = CenterContainer.new()
	_panel_host.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel_host.visible = false
	add_child(_panel_host)

	_build_menu()
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 2.5).set_trans(Tween.TRANS_SINE)
	Audio.play_music([Audio.stream("hub_bed_0"), Audio.stream("hub_bed_1")] as Array[AudioStream], 4.0, 1.0)
	Audio.play_ambience(Audio.stream("amb_hub"), 4.0, -6.0)


func _dot_texture() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(0.5, 0.0)
	t.width = 16
	t.height = 16
	return t


func _build_menu() -> void:
	for c in _menu.get_children():
		c.queue_free()
	var first: Button = null
	if Save.has_save():
		first = _btn("Continue", func() -> void: Game.continue_game())
	var ng := _btn("New Game", func() -> void: Game.new_game())
	_btn("Settings", _show_settings)
	_btn("Quit", func() -> void: Game.quit())
	(first if first else ng).grab_focus.call_deferred()


func _btn(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.add_theme_font_size_override(&"font_size", 26)
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
	var p := PanelContainer.new()
	var s := preload("res://ui/settings_panel.gd").new()
	p.add_child(s)
	_panel_host.add_child(p)
	s.closed.connect(func() -> void:
		p.queue_free()
		_panel_host.visible = false
		_left.visible = true
		_build_menu())


func _process(delta: float) -> void:
	_t += delta
	var z := 1.04 + 0.03 * sin(_t * 0.05)
	_bg.scale = Vector2(z, z)
	_bg.pivot_offset = size * Vector2(0.55, 0.4)
	var mp := get_viewport().get_mouse_position() / get_viewport_rect().size - Vector2(0.5, 0.5)
	_bg.position = _bg.position.lerp(-mp * 18.0, 1.0 - exp(-2.0 * delta))
