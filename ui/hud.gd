extends CanvasLayer
## In-play HUD (DESIGN_RULES §7): one line, the current objective (top-left, fades when idle; the
## rest lives in the journal), the crosshair dot with its hold ring, and the interaction prompt
## below the centre of the view. Created by Game; never instanced by wings.

var _obj: PanelContainer
var _obj_label: Label
var _dot: Control
var _prompt: PanelContainer
var _prompt_text: Label
var _idle: float = 0.0


func _ready() -> void:
	layer = 60
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	_obj = PanelContainer.new()
	_obj.add_theme_stylebox_override(&"panel", Style.backing(0.7, 14))
	_obj.position = Vector2(48, 44)
	_obj.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_obj_label = Style.label("", Style.TEXT, Style.SIZE_BODY, Style.IVORY)
	_obj.add_child(_obj_label)
	root.add_child(_obj)

	_dot = Control.new()
	_dot.set_anchors_preset(Control.PRESET_CENTER)
	_dot.draw.connect(func() -> void:
		var on := is_instance_valid(Interaction.target)
		_dot.draw_circle(Vector2.ZERO, 3.2 if on else 1.8, Color(Style.IVORY, 0.9 if on else 0.35), true, -1.0, true)
		if Interaction.hold_progress > 0.0:
			_dot.draw_arc(Vector2.ZERO, 16, -PI / 2, -PI / 2 + TAU * Interaction.hold_progress, 48, Style.GOLD, 2.0, true))
	root.add_child(_dot)

	# Prompt: under the centre (at 70% height), never over it.
	_prompt = PanelContainer.new()
	_prompt.add_theme_stylebox_override(&"panel", Style.backing(0.7, 12))
	_prompt.anchor_left = 0.5
	_prompt.anchor_right = 0.5
	_prompt.anchor_top = 0.7
	_prompt.anchor_bottom = 0.7
	_prompt.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_prompt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_text = Style.label("", Style.TEXT, Style.SIZE_BODY, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER)
	_prompt.add_child(_prompt_text)
	_prompt.modulate.a = 0.0
	root.add_child(_prompt)

	Quest.objectives_changed.connect(func(_w: StringName) -> void: _refresh())
	Quest.objective_completed.connect(_on_obj_done)
	_refresh()


func _on_obj_done(_w: StringName, obj: StringName) -> void:
	if not Quest.get_objective(obj).is_empty():
		Audio.ui(&"select")
	_refresh()


## The objective line (tests read it).
func objective_text() -> String:
	return _obj_label.text


func _refresh() -> void:
	var cur := Quest.current()
	_obj_label.text = "" if cur.is_empty() else String(cur["title"])
	_idle = 0.0


func _process(delta: float) -> void:
	var playing := Game.state == Game.State.PLAYING and not Cinematics.playing and not Placards.is_reading()
	visible = Game.state != Game.State.TITLE
	_idle += delta
	var show_obj := playing and (_idle < 9.0 or Input.is_action_pressed(&"journal")) and _obj_label.text != ""
	_obj.modulate.a = lerpf(_obj.modulate.a, 1.0 if show_obj else 0.0, 1.0 - exp(-3.0 * delta))
	var t := Interaction.target if is_instance_valid(Interaction.target) else null
	if t:
		var key := _key_name(&"interact")
		_prompt_text.text = ("Hold %s: %s" if t.hold_time > 0.0 else "%s: %s") % [key, t.prompt.left(1).to_lower() + t.prompt.substr(1)]
	_prompt.modulate.a = lerpf(_prompt.modulate.a, 1.0 if (t and playing) else 0.0, 1.0 - exp(-10.0 * delta))
	_dot.visible = playing
	_dot.queue_redraw()


func _key_name(action: StringName) -> String:
	for e in InputMap.action_get_events(action):
		if e is InputEventKey:
			return (e as InputEventKey).as_text_physical_keycode().trim_suffix(" (Physical)")
	return "Interact"
