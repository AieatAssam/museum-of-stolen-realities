extends CanvasLayer
## In-play HUD: a quiet objective card (top-left, fades when idle), crosshair, interaction prompt
## with hold ring. Created by Game; never instanced by wings.

var _obj_box: VBoxContainer
var _obj_wing: Label
var _obj_title: Label
var _obj_steps: Label
var _dot: Control
var _prompt: HBoxContainer
var _prompt_key: Label
var _prompt_text: Label
var _ring: Control
var _idle: float = 0.0


func _ready() -> void:
	layer = 60
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	_obj_box = VBoxContainer.new()
	_obj_box.position = Vector2(64, 56)
	_obj_box.add_theme_constant_override(&"separation", 4)
	root.add_child(_obj_box)
	_obj_wing = Style.catalog("", 14, Style.GOLD)
	_obj_title = Style.label("", Style.ITALIC, 26, Style.IVORY)
	_obj_steps = Style.label("", Style.BODY, 19, Style.IVORY_DIM)
	_obj_box.add_child(_obj_wing)
	_obj_box.add_child(_obj_title)
	_obj_box.add_child(_obj_steps)

	_dot = Control.new()
	_dot.set_anchors_preset(Control.PRESET_CENTER)
	_dot.draw.connect(func() -> void:
		var on := is_instance_valid(Interaction.target)
		var a := 0.9 if on else 0.35
		var r := 3.2 if on else 1.8
		_dot.draw_circle(Vector2.ZERO, r, Color(Style.IVORY, a), true, -1.0, true)
		if Interaction.hold_progress > 0.0:
			_dot.draw_arc(Vector2.ZERO, 16, -PI / 2, -PI / 2 + TAU * Interaction.hold_progress, 48, Style.GOLD, 2.0, true))
	root.add_child(_dot)

	_prompt = HBoxContainer.new()
	_prompt.set_anchors_preset(Control.PRESET_CENTER)
	_prompt.position = Vector2(-200, 34)
	_prompt.custom_minimum_size = Vector2(400, 0)
	_prompt.alignment = BoxContainer.ALIGNMENT_CENTER
	_prompt.add_theme_constant_override(&"separation", 12)
	root.add_child(_prompt)
	_prompt_key = Style.label("E", Style.CATALOG, 16, Style.INK, HORIZONTAL_ALIGNMENT_CENTER)
	var keybg := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(Style.GOLD, 0.92)
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 1
	sb.content_margin_bottom = 1
	keybg.add_theme_stylebox_override(&"panel", sb)
	keybg.add_child(_prompt_key)
	_prompt.add_child(keybg)
	_prompt_text = Style.catalog("", 17, Style.IVORY)
	_prompt.add_child(_prompt_text)
	_prompt.modulate.a = 0.0

	Quest.objectives_changed.connect(func(_w: StringName) -> void: _refresh(true))
	Quest.objective_completed.connect(_on_obj_done)
	_refresh(true)


func _on_obj_done(_w: StringName, obj: StringName) -> void:
	var o := Quest.get_objective(obj)
	if not o.is_empty():
		Audio.ui(&"select")
	_refresh(true)


func _refresh(wake: bool) -> void:
	var cur := Quest.current()
	var info := Game.registry.get_info(Quest.wing_id)
	_obj_wing.text = (info.numeral + "  ·  " + info.title).to_upper() if info else ""
	if cur.is_empty():
		_obj_title.text = ""
		_obj_steps.text = ""
	else:
		_obj_title.text = String(cur["title"])
		var lines: PackedStringArray = []
		for s: Dictionary in cur.get("steps", []):
			var done := Quest.is_step_done(StringName(cur["id"]), StringName(s["id"]))
			lines.append(("◆  " if done else "◇  ") + String(s["title"]))
		_obj_steps.text = "\n".join(lines)
	if wake:
		_idle = 0.0


func _process(delta: float) -> void:
	var playing := Game.state == Game.State.PLAYING and not Cinematics.playing and not Placards.is_reading()
	visible = Game.state != Game.State.TITLE
	_idle += delta
	var show_obj := playing and (_idle < 9.0 or Input.is_action_pressed(&"journal")) and _obj_title.text != ""
	_obj_box.modulate.a = lerpf(_obj_box.modulate.a, 1.0 if show_obj else 0.0, 1.0 - exp(-3.0 * delta))
	var t := Interaction.target if is_instance_valid(Interaction.target) else null
	if t:
		_prompt_text.text = t.prompt.to_upper() + ("  (HOLD)" if t.hold_time > 0.0 else "")
	_prompt.modulate.a = lerpf(_prompt.modulate.a, 1.0 if (t and playing) else 0.0, 1.0 - exp(-10.0 * delta))
	_dot.visible = playing
	_dot.queue_redraw()
