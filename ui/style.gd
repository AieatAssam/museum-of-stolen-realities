class_name Style
## Museum typography + palette (docs/DESIGN_RULES.md §7). Two families, one weight each:
##   DISPLAY  Newsreader (opsz 72, 400)  headings and titles: one face, one weight, one colour
##   TEXT     Libre Franklin (400)        everything else: labels, buttons, body, tombstone lines
## Sentence case, default tracking, roman. No shadows/outlines on text: legibility comes from
## `backing()`. Sizes are in the 1920x1080 canvas and never below 16 (SIZE_MIN).
## LIGHT / BODY / ITALIC / CATALOG are kept as aliases so older call sites still compile; they all
## map onto the two families above.

const GOLD := Color("c8a35a")       ## accent only: one rule, the focused button, one key number
const GOLD_DIM := Color("a08550")   ## 5.5:1 on INK
const INK := Color("0e0c09")
const IVORY := Color("ece6d6")      ## 15:1 on INK
const IVORY_DIM := Color("bdb5a3")  ## 9.5:1 on INK

const SIZE_TITLE := 88
const SIZE_HEADING := 40
const SIZE_SUBHEADING := 28
const SIZE_BODY := 22
const SIZE_META := 20
const SIZE_MIN := 18

static var DISPLAY: Font = _axes(preload("res://assets/fonts/Newsreader-Variable.ttf"), {"wght": 400, "opsz": 72})
static var TEXT: Font = _axes(preload("res://assets/fonts/LibreFranklin-Variable.ttf"), {"wght": 400})
static var LIGHT: Font = DISPLAY
static var BODY: Font = TEXT
static var ITALIC: Font = TEXT
static var CATALOG: Font = TEXT


static func _axes(f: Font, axes: Dictionary) -> FontVariation:
	var v := FontVariation.new()
	v.base_font = f
	var d := {}
	for k: String in axes:
		d[TextServerManager.get_primary_interface().name_to_tag(k)] = axes[k]
	v.variation_opentype = d
	return v


## Install the fonts into the project theme (ui/theme.tres holds colours/boxes only; see its header).
static func apply_theme() -> void:
	var th := ThemeDB.get_project_theme()
	if th == null:
		return
	th.default_font = TEXT
	th.default_font_size = SIZE_BODY
	for type: StringName in [&"Label", &"Button", &"CheckButton", &"OptionButton", &"PopupMenu"]:
		th.set_font(&"font", type, TEXT)
	th.set_font(&"normal_font", &"RichTextLabel", TEXT)


## Kept for old call sites: tracking is not changed (sentence case, default spacing).
static func spaced(base: Font, _spacing: int = 0) -> Font:
	return base


## Remove the decorations §7 forbids from legacy strings: middle-dot separators become line breaks
## (`joiner`), a lone dash heading becomes empty.
static func clean(text: String, joiner: String = "\n") -> String:
	var t := text.strip_edges()
	if t in ["—", "-", "–"]:
		return ""
	for sep: String in ["  ·  ", " · ", "·"]:
		t = t.replace(sep, joiner)
	return t


static func label(text: String, font: Font, size: int, color: Color = IVORY, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override(&"font", font)
	l.add_theme_font_size_override(&"font_size", maxi(size, SIZE_MIN))
	l.add_theme_color_override(&"font_color", color)
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## A small sentence-case label in the text face (was: letter-spaced small caps).
static func catalog(text: String, size: int = SIZE_META, color: Color = IVORY_DIM, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	return label(clean(text, ", "), TEXT, size, IVORY_DIM if color == GOLD or color == GOLD_DIM else color, align)


## A plain hairline rule (no ornament).
static func rule(width: float = 220.0, color: Color = GOLD_DIM) -> Control:
	var c := ColorRect.new()
	c.color = color
	c.custom_minimum_size = Vector2(width, 1)
	c.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


## Solid backing for text over the 3D view.
static func backing(alpha: float = 0.84, margin: int = 28) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(INK, alpha)
	sb.set_content_margin_all(margin)
	return sb
