extends CanvasLayer
## Placards autoload: the Curator's only voice. Every surface uses the museum tombstone format
## (title / date / medium / acquisition number / one paragraph of <= 40 words), left-aligned:
##   toast(label)  a small label slides in at the lower-left corner; queued, one at a time
##   read(label)   reading view (pauses play; any key closes), a column left of centre
## `label` is a Dictionary from `Placard.fields(title, date, medium, acquisition, body)`.
## Old calls still work: toast(body, heading) and read(title, catalog_line, body).
## In-world plaques are the `Placard` node (core/placard.gd).

signal toast_shown(body: String)

## Layout (1920x1080 canvas; stretch mode scales it). The toast never rises above TOAST_TOP_FRAC.
const TOAST_W := 520.0
const TOAST_MARGIN := 48.0
const TOAST_TOP_FRAC := 0.62
const READER_X := 160.0
const READER_W := 700.0

var _queue: Array[Dictionary] = []
var _busy: bool = false
var _showing: bool = false  # a toast is up; _process hides it while blocked
var _card: PanelContainer
var _card_parts: Array[Label] = []   # title, meta, body
var _reader: Control
var _reader_parts: Array[Label] = []
## Every toast body shown this session (tests and the journal read this).
var history: Array[String] = []


func _ready() -> void:
	layer = 80
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_card()
	_build_reader()


## Normalise the old and new call shapes into a label Dictionary.
func _as_label(a: Variant, b: String, c: String, legacy_catalog: bool) -> Dictionary:
	if a is Dictionary:
		return a
	if legacy_catalog:  # read(title, catalog_line, body)
		return Placard.fields_from_legacy(String(a), b, c)
	return Placard.fields(Style.clean(b, ", "), "", "", "", String(a))  # toast(body, heading)


func toast(body_or_label: Variant, heading: String = "") -> void:
	var l := _as_label(body_or_label, heading, "", false)
	history.append(String(l.get("body", "")))
	_queue.append(l)
	if not _busy:
		_next()


func _next() -> void:
	if _queue.is_empty():
		_busy = false
		return
	_busy = true
	var l: Dictionary = _queue.pop_front()
	while _blocked():  # one placard at a time, and never under a cinematic card or a menu
		await get_tree().process_frame
	_fill(_card_parts, l)
	toast_shown.emit(String(l.get("body", "")))
	Audio.sfx(Audio.stream("placard"), null, -8.0)
	_showing = true
	_card.modulate.a = 0.0
	_card.reset_size()
	await get_tree().process_frame  # let the container settle its size
	var vs := get_viewport().get_visible_rect().size
	var bottom := maxf(TOAST_MARGIN, Cinematics._bars[0].offset_bottom + 24.0)
	_card.position = Vector2(TOAST_MARGIN - 40.0, maxf(vs.y - _card.size.y - bottom, vs.y * TOAST_TOP_FRAC))
	var t := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_property(_card, "modulate:a", 1.0, 0.5)
	t.parallel().tween_property(_card, "position:x", TOAST_MARGIN, 0.6)
	await t.finished
	# hold; time with the reader open doesn't count, and the card hides under it
	var hold := clampf(2.5 + String(l.get("body", "")).split(" ").size() * 0.32, 4.5, 11.0)
	if not _queue.is_empty():
		hold *= 0.7  # a backlog drains faster
	while hold > 0.0:
		await get_tree().process_frame
		if _card.visible:
			hold -= get_process_delta_time()
	t = create_tween()
	t.tween_property(_card, "modulate:a", 0.0, 0.8)
	await t.finished
	_showing = false
	_next()


func _process(_d: float) -> void:
	_card.visible = _showing and not _blocked()


func _fill(parts: Array[Label], l: Dictionary) -> void:
	parts[0].text = String(l.get("title", ""))
	parts[1].text = "\n".join(Placard.meta_lines(l))
	parts[2].text = String(l.get("body", ""))
	for p in parts:
		p.visible = p.text != ""
	# a little air between the tombstone lines and the paragraph, only when both are shown
	parts[1].add_theme_constant_override(&"line_spacing", 2)
	var v := parts[0].get_parent() as VBoxContainer
	v.add_theme_constant_override(&"separation", 14 if (parts[0].visible or parts[1].visible) and parts[2].visible else 6)


## True while a toast is on screen (tests).
func toast_visible() -> bool:
	return _card.visible and _card.modulate.a > 0.01


func toast_rect() -> Rect2:
	return _card.get_rect()


func clear() -> void:
	_queue.clear()


func _column(parent: Control, width: float, sizes: Array[int], into: Array[Label]) -> void:
	var v := VBoxContainer.new()
	v.add_theme_constant_override(&"separation", 6)
	v.custom_minimum_size.x = width
	parent.add_child(v)
	var fonts: Array[Font] = [Style.DISPLAY, Style.TEXT, Style.TEXT]
	var cols: Array[Color] = [Style.IVORY, Style.IVORY_DIM, Style.IVORY]
	for i in 3:
		var l := Style.label("", fonts[i], sizes[i], cols[i])
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size.x = width
		v.add_child(l)
		into.append(l)


func _build_card() -> void:
	_card = PanelContainer.new()
	_card.add_theme_stylebox_override(&"panel", Style.backing(0.86, 24))
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_column(_card, TOAST_W - 48.0, [26, 18, 20], _card_parts)
	_card.visible = false
	add_child(_card)


func _build_reader() -> void:
	_reader = Control.new()
	_reader.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reader.visible = false
	var bg := ColorRect.new()
	bg.color = Color(Style.INK, 0.9)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_reader.add_child(bg)
	var v := VBoxContainer.new()
	v.anchor_top = 0.5
	v.anchor_bottom = 0.5
	v.position = Vector2(READER_X, 0)
	v.grow_vertical = Control.GROW_DIRECTION_BOTH
	v.add_theme_constant_override(&"separation", 28)
	_reader.add_child(v)
	_column(v, READER_W, [Style.SIZE_HEADING + 8, Style.SIZE_META + 2, Style.SIZE_BODY + 4], _reader_parts)
	v.add_child(Style.label("Press any key to return", Style.TEXT, Style.SIZE_MIN, Style.IVORY_DIM))
	add_child(_reader)


func _blocked() -> bool:
	return is_reading() or Cinematics.playing or get_tree().paused


func is_reading() -> bool:
	return _reader.visible


func read(title_or_label: Variant, catalog_line: String = "", body: String = "") -> void:
	_fill(_reader_parts, _as_label(title_or_label, catalog_line, body, true))
	_reader.visible = true  # no fade: a tween here stalled at alpha 0 under the pause
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
