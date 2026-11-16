extends CanvasLayer
## The journal (Tab): the catalogue of wings, the current wing's objectives and steps, provenances
## and the Curator's latest placards. Everything the one-line HUD leaves out lives here.
## Built by Game.open_menu(&"journal").

var _scroll: ScrollContainer
var _more: Label


func _input(e: InputEvent) -> void:
	for a: StringName in [&"ui_down", &"ui_up", &"move_back", &"move_forward"]:
		if e.is_action_pressed(a, true):
			_scroll.scroll_vertical += 90 if a in [&"ui_down", &"move_back"] else -90


func _ready() -> void:
	layer = 85
	process_mode = Node.PROCESS_MODE_ALWAYS
	var bg := ColorRect.new()
	bg.color = Color(Style.INK, 0.94)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var m := MarginContainer.new()
	m.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side: String in ["left", "right"]:
		m.add_theme_constant_override("margin_" + side, 140)
	m.add_theme_constant_override(&"margin_top", 90)
	m.add_theme_constant_override(&"margin_bottom", 80)
	add_child(m)
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override(&"separation", 90)
	m.add_child(cols)

	# left: the catalogue
	var left := _col(cols)
	left.add_child(Style.label("Journal", Style.DISPLAY, Style.SIZE_HEADING + 8, Style.IVORY))
	for w: WingInfo in Game.registry.exhibits():
		var row := VBoxContainer.new()
		row.add_theme_constant_override(&"separation", 2)
		var open := w.scene_exists()
		row.add_child(Style.label(w.title, Style.DISPLAY, Style.SIZE_SUBHEADING, Style.IVORY if open else Style.IVORY_DIM))
		var provs: int = (Save.data["provenances"] as Dictionary).get(String(w.id), []).size()
		var meta := "Acq. No. %s" % w.acquisition_no
		if not open:
			meta += ", gallery under restoration"
		else:
			meta += ", provenances %d of 3" % provs
			if Quest.has_fragment(w.id):
				meta += ", fragment recovered"
		row.add_child(Style.label(meta, Style.TEXT, Style.SIZE_META, Style.IVORY_DIM))
		left.add_child(row)

	# right: the present gallery. It scrolls inside the page when a wing's objectives and placards
	# outgrow it, with a visible bar and a cue under it while there is more below.
	var side := VBoxContainer.new()
	side.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	side.add_theme_constant_override(&"separation", 8)
	cols.add_child(side)
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var bar := _scroll.get_v_scroll_bar()
	var track := StyleBoxFlat.new()
	track.bg_color = Color(Style.IVORY, 0.12)
	track.content_margin_left = 6
	track.content_margin_right = 6
	var grab := StyleBoxFlat.new()
	grab.bg_color = Style.IVORY_DIM
	bar.add_theme_stylebox_override(&"scroll", track)
	for st: StringName in [&"grabber", &"grabber_highlight", &"grabber_pressed"]:
		bar.add_theme_stylebox_override(st, grab)
	side.add_child(_scroll)
	_more = Style.label("More below: scroll, or press S", Style.TEXT, Style.SIZE_BODY, Style.IVORY_DIM)
	_more.modulate.a = 0.0
	side.add_child(_more)
	var right := _col(_scroll)
	var info := Game.registry.get_info(Quest.wing_id)
	right.add_child(Style.label(info.title if info else "The Atrium", Style.DISPLAY, Style.SIZE_HEADING, Style.IVORY))
	if Quest.objectives.is_empty():
		right.add_child(_wrap("Six frames. One pedestal. The Curator is patient.", Style.IVORY_DIM))
	for o: Dictionary in Quest.objectives:
		var oid := StringName(o["id"])
		var done := Quest.is_done(oid)
		var t := String(o["title"]) + (" (optional)" if o.get("optional", false) else "") + (" (done)" if done else "")
		right.add_child(_wrap(t, Style.IVORY_DIM if done else Style.IVORY, Style.SIZE_BODY + 2))
		if done:
			continue
		for s: Dictionary in o.get("steps", []):
			var sd := Quest.is_step_done(oid, StringName(s["id"]))
			var l := _wrap(String(s["title"]) + (" (done)" if sd else ""), Style.IVORY_DIM if sd else Style.IVORY)
			var indent := MarginContainer.new()
			indent.add_theme_constant_override(&"margin_left", 24)
			indent.add_child(l)
			right.add_child(indent)
		if o.has("hint"):
			var h := MarginContainer.new()
			h.add_theme_constant_override(&"margin_left", 24)
			h.add_child(_wrap("Hint: " + String(o["hint"]), Style.IVORY_DIM))
			right.add_child(h)
	if not Quest.provenances.is_empty():
		right.add_child(Style.label("Provenances", Style.DISPLAY, Style.SIZE_SUBHEADING, Style.IVORY))
		for p: Dictionary in Quest.provenances:
			var found := Quest.has_provenance(Quest.wing_id, StringName(p["id"]))
			right.add_child(_wrap(String(p["name"]) if found else "Not yet found", Style.IVORY if found else Style.IVORY_DIM))
	var hist := Placards.history.slice(maxi(Placards.history.size() - 3, 0))
	if not hist.is_empty():
		right.add_child(Style.label("Latest placards", Style.DISPLAY, Style.SIZE_SUBHEADING, Style.IVORY))
		hist.reverse()
		for h: String in hist:
			right.add_child(_wrap(h, Style.IVORY_DIM))
	var hint := Style.label("Tab to close", Style.TEXT, Style.SIZE_BODY, Style.IVORY_DIM, HORIZONTAL_ALIGNMENT_RIGHT)
	hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	hint.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	hint.position += Vector2(-140, -30)
	add_child(hint)


func _process(_delta: float) -> void:
	var bar := _scroll.get_v_scroll_bar()
	_more.modulate.a = 1.0 if bar.max_value - bar.page > 1.0 and _scroll.scroll_vertical < bar.max_value - bar.page - 4.0 else 0.0


func _col(parent: Control) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override(&"separation", 16)
	parent.add_child(v)
	return v


## Journal body text: wrapped to the column, at the body size (never under SIZE_MIN).
func _wrap(text: String, color: Color, size: int = Style.SIZE_BODY) -> Label:
	var l := Style.label(text, Style.TEXT, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l
