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


## Layout limits (in the 1920x1080 canvas; stretch mode scales it to any resolution).
const TOAST_MAX_W := 880.0     ## body text width cap
const TOAST_TOP_FRAC := 0.64   ## a card's top never rises above this fraction of the screen
const TOAST_BOTTOM := 72.0     ## gap to the screen bottom (more while letterbox bars are down)
const BODY_PX := 27


func _next() -> void:
	if _queue.is_empty():
		_busy = false
		return
	_busy = true
	var item: Dictionary = _queue.pop_front()
	while is_reading():  # one card at a time: wait for the reader to close
		await get_tree().process_frame
	_layout_card(String(item["heading"]), String(item["body"]))
	toast_shown.emit(item["body"])
	Audio.sfx(Audio.stream("placard"), null, -8.0)
	_card.visible = true
	_card.modulate.a = 0.0
	await get_tree().process_frame  # let the container settle its size
	var vs := get_viewport().get_visible_rect().size
	var rest_y := vs.y - _card.size.y - maxf(TOAST_BOTTOM, Cinematics._bars[0].offset_bottom + 24.0)
	_card.position = Vector2((vs.x - _card.size.x) * 0.5, rest_y + 24.0)
	var t := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_property(_card, "modulate:a", 1.0, 0.9)
	t.parallel().tween_property(_card, "position:y", rest_y, 1.2)
	await t.finished
	# hold; time spent with the reader open doesn't count, and the card hides under it
	var hold := clampf(2.5 + String(item["body"]).split(" ").size() * 0.32, 4.5, 11.0)
	if _queue.size() > 1:
		hold *= 0.7  # a backlog drains faster
	while hold > 0.0:
		await get_tree().process_frame
		_card.visible = not is_reading()
		if _card.visible:
			hold -= get_process_delta_time()
	t = create_tween()
	t.tween_property(_card, "modulate:a", 0.0, 1.2)
	await t.finished
	_card.visible = false
	_next()


## Size the card to its text: one line for short text, wider (to TOAST_MAX_W) for long text, and
## a smaller face if it would still rise past TOAST_TOP_FRAC.
func _layout_card(heading: String, body: String) -> void:
	_card_head.text = heading.to_upper()
	_card_body.text = body
	var vs := get_viewport().get_visible_rect().size
	var max_h := vs.y * (1.0 - TOAST_TOP_FRAC) - TOAST_BOTTOM
	for px: int in [BODY_PX, 24, 21, 18]:
		var one_line := Style.ITALIC.get_string_size(body, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x
		var lines := ceili(one_line / TOAST_MAX_W)
		var w := clampf(one_line / lines + px * 2.0, 420.0, TOAST_MAX_W + px * 2.0)
		_card_body.add_theme_font_size_override(&"font_size", px)
		_card_body.custom_minimum_size.x = w
		var est_h := (lines + 1) * px * 1.3 + 15 * 1.4 + 19 + 16 + 48  # body (+1 slack line), head, rule, gaps, margins
		if est_h <= max_h:
			break
	_card.reset_size()


## True while a toast card is on screen (tests).
func toast_visible() -> bool:
	return _card.visible and _card.modulate.a > 0.01


func toast_rect() -> Rect2:
	return _card.get_rect()


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
		close_reader()
		Audio.ui(&"back")


## Close the reading view (Transitions calls this before a scene change).
func close_reader() -> void:
	if not _reader.visible:
		return
	_reader.visible = false
	get_tree().paused = false
