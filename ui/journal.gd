extends CanvasLayer
## The journal (Tab): the catalogue of wings, the current wing's objectives, provenances and the
## Curator's addenda. Built by Game.open_menu(&"journal").


func _ready() -> void:
	layer = 85
	process_mode = Node.PROCESS_MODE_ALWAYS
	var bg := ColorRect.new()
	bg.color = Color(0.03, 0.025, 0.018, 0.93)
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

	# left: catalogue
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_theme_constant_override(&"separation", 10)
	cols.add_child(left)
	left.add_child(Style.catalog("The Catalogue", 16))
	left.add_child(Style.label("Journal of a Thief", Style.DISPLAY, 50, Style.IVORY))
	left.add_child(Style.rule(220))
	for w: WingInfo in Game.registry.exhibits():
		var row := VBoxContainer.new()
		row.add_theme_constant_override(&"separation", 0)
		var done := Quest.has_fragment(w.id)
		var provs: int = (Save.data["provenances"] as Dictionary).get(String(w.id), []).size()
		row.add_child(Style.catalog("%s  ·  No. %s%s" % [w.numeral, w.acquisition_no, "  ·  Fragment recovered" if done else ""], 13, Style.GOLD if done else Style.GOLD_DIM))
		var t := Style.label(w.title, Style.DISPLAY, 28, Style.IVORY if w.scene_exists() else Style.IVORY_DIM)
		row.add_child(t)
		var sub := w.rule + "   —   provenances %d / 3" % provs if w.scene_exists() else "Gallery under restoration"
		row.add_child(Style.label(sub, Style.ITALIC, 19, Style.IVORY_DIM))
		left.add_child(row)

	# right: current wing + addenda
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_theme_constant_override(&"separation", 10)
	cols.add_child(right)
	var info := Game.registry.get_info(Quest.wing_id)
	right.add_child(Style.catalog("Present gallery", 16))
	right.add_child(Style.label(info.title if info else "The Atrium", Style.DISPLAY, 40, Style.IVORY))
	right.add_child(Style.rule(180))
	if Quest.objectives.is_empty():
		right.add_child(Style.label("Six frames. One pedestal. The Curator is patient.", Style.ITALIC, 22, Style.IVORY_DIM))
	for o: Dictionary in Quest.objectives:
		var oid := StringName(o["id"])
		var done := Quest.is_done(oid)
		var l := Style.label(("◆  " if done else "◇  ") + String(o["title"]) + ("   (optional)" if o.get("optional", false) else ""),
			Style.BODY, 24, Style.IVORY_DIM if done else Style.IVORY)
		right.add_child(l)
		if not done:
			for s: Dictionary in o.get("steps", []):
				var sd := Quest.is_step_done(oid, StringName(s["id"]))
				right.add_child(Style.label("        " + ("·  " if not sd else "—  ") + String(s["title"]), Style.ITALIC, 20, Style.IVORY_DIM if sd else Color(Style.IVORY, 0.8)))
			if o.has("hint"):
				right.add_child(Style.label("        " + String(o["hint"]), Style.ITALIC, 18, Style.GOLD_DIM))
	if not Quest.provenances.is_empty():
		right.add_child(Control.new())
		right.add_child(Style.catalog("Provenances", 14))
		for p: Dictionary in Quest.provenances:
			var found := Quest.has_provenance(Quest.wing_id, StringName(p["id"]))
			right.add_child(Style.label(String(p["name"]) if found else "—  undiscovered  —", Style.BODY, 21, Style.IVORY if found else Style.IVORY_DIM))
	right.add_child(Control.new())
	right.add_child(Style.catalog("Latest addenda", 14))
	var hist := Placards.history.slice(maxi(Placards.history.size() - 4, 0))
	hist.reverse()
	for h: String in hist:
		var l := Style.label("“" + h + "”", Style.ITALIC, 19, Style.IVORY_DIM)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		right.add_child(l)
	var hint := Style.catalog("Tab to close", 13, Style.GOLD_DIM, HORIZONTAL_ALIGNMENT_RIGHT)
	hint.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	hint.position = Vector2(-260, -50)
	add_child(hint)
