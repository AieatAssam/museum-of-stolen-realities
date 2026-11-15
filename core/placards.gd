extends CanvasLayer
## Placards autoload — the Curator's only voice.
##   toast(body, heading)  — a small museum card rises at the bottom of the screen, queued.
##   read(title, sub, body)— full-screen reading view of a placard (pauses play; any key closes).
## In-world plaques are the `Placard` node (core/placard.gd).

signal toast_shown(body: String)

var _queue: Array[Dictionary] = []
var _busy: bool = false
var _card: PanelContainer
var _card_head: Label
var _card_body: Label
var _reader: Control
var _reader_title: Label
var _reader_sub: Label
var _reader_body: Label
## Every toast ever shown this session (tests and journal read this).
var history: Array[String] = []


func _ready() -> void:
	layer = 80
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_card()
	_build_reader()


func toast(body: String, heading: String = "Addendum to the catalogue") -> void:
	history.append(body)
	_queue.append({"body": body, "heading": heading})
	if not _busy:
		_next()


func _next() -> void:
	if _queue.is_empty():
		_busy = false
		return
	_busy = true
	var item: Dictionary = _queue.pop_front()
	_card_head.text = String(item["heading"]).to_upper()
	_card_body.text = item["body"]
	toast_shown.emit(item["body"])
	Audio.sfx(Audio.stream("placard"), null, -8.0)
	_card.visible = true
	_card.modulate.a = 0.0
	await get_tree().process_frame
	var rest_y := get_viewport().get_visible_rect().size.y - _card.size.y - 72.0
	_card.position = Vector2((get_viewport().get_visible_rect().size.x - _card.size.x) * 0.5, rest_y + 24.0)
	var hold := clampf(2.5 + String(item["body"]).split(" ").size() * 0.32, 4.5, 11.0)
	var t := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_property(_card, "modulate:a", 1.0, 0.9)
	t.parallel().tween_property(_card, "position:y", rest_y, 1.2)
	t.tween_interval(hold)
	t.tween_property(_card, "modulate:a", 0.0, 1.2)
	await t.finished
	_card.visible = false
	_next()


func clear() -> void:
	_queue.clear()


func _build_card() -> void:
	_card = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.043, 0.037, 0.028, 0.9)
	sb.border_color = Color(Style.GOLD, 0.5)
	sb.set_border_width_all(1)
	sb.content_margin_left = 44
	sb.content_margin_right = 44
	sb.content_margin_top = 22
	sb.content_margin_bottom = 26
	sb.shadow_color = Color(0, 0, 0, 0.5)
	sb.shadow_size = 30
	_card.add_theme_stylebox_override(&"panel", sb)
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := VBoxContainer.new()
	v.add_theme_constant_override(&"separation", 8)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	_card.add_child(v)
	_card_head = Style.catalog("", 15, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(_card_head)
	v.add_child(Style.rule(160))
	_card_body = Style.label("", Style.ITALIC, 27, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER)
	_card_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_card_body.custom_minimum_size.x = 640
	v.add_child(_card_body)
	_card.visible = false
	add_child(_card)


func _build_reader() -> void:
	_reader = Control.new()
	_reader.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reader.visible = false
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.017, 0.012, 0.86)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reader.add_child(bg)
	var c := CenterContainer.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reader.add_child(c)
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 760
	v.add_theme_constant_override(&"separation", 14)
	c.add_child(v)
	_reader_sub = Style.catalog("", 18, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	_reader_title = Style.label("", Style.DISPLAY, 60, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER)
	_reader_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_reader_body = Style.label("", Style.BODY, 30, Color(Style.IVORY, 0.92), HORIZONTAL_ALIGNMENT_CENTER)
	_reader_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_reader_sub)
	v.add_child(_reader_title)
	v.add_child(Style.rule(260))
	v.add_child(_reader_body)
	var hint := Style.catalog("Any key to return", 14, Style.GOLD_DIM, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(Control.new())
	v.add_child(hint)
	add_child(_reader)


func is_reading() -> bool:
	return _reader.visible


func read(title: String, sub: String, body: String) -> void:
	_reader_title.text = title
	_reader_sub.text = sub.to_upper()
	_reader_body.text = body
	_reader.visible = true
	_reader.modulate.a = 0.0
	create_tween().tween_property(_reader, "modulate:a", 1.0, 0.35)
	Audio.ui(&"open")
	get_tree().paused = true


func _input(event: InputEvent) -> void:
	if not _reader.visible:
		return
	var close: bool = (event is InputEventKey and event.pressed and not event.echo) \
		or (event is InputEventMouseButton and event.pressed) \
		or (event is InputEventJoypadButton and event.pressed)
	if close:
		get_viewport().set_input_as_handled()
		_reader.visible = false
		get_tree().paused = false
		Audio.ui(&"back")
