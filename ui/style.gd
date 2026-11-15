class_name Style
## Museum typography + palette. Use these instead of ad-hoc colours/fonts.
##   DISPLAY  Gloock      — high-contrast display serif (titles, numerals)
##   LIGHT    Italiana    — thin display (big cinematic cards)
##   BODY     Crimson Pro — reading text, italic for the Curator's voice
##   CATALOG  Arsenal SC  — small-caps catalogue labels (letter-spaced)

const GOLD := Color("c8a35a")
const GOLD_DIM := Color("8a7040")
const INK := Color("0e0c09")
const IVORY := Color("e9e3d3")
const IVORY_DIM := Color("a39d8f")

static var DISPLAY: FontFile = preload("res://assets/fonts/Gloock-Regular.ttf")
static var LIGHT: FontFile = preload("res://assets/fonts/Italiana-Regular.ttf")
static var BODY: FontFile = preload("res://assets/fonts/CrimsonPro-Regular.ttf")
static var ITALIC: FontFile = preload("res://assets/fonts/CrimsonPro-Italic.ttf")
static var CATALOG: FontFile = preload("res://assets/fonts/ArsenalSC-Regular.ttf")


## Install the fonts into the project theme (ui/theme.tres holds colours/boxes only; see its header).
static func apply_theme() -> void:
	var th := ThemeDB.get_project_theme()
	if th == null:
		return
	th.default_font = BODY
	for type: StringName in [&"Label", &"CheckButton", &"OptionButton", &"PopupMenu"]:
		th.set_font(&"font", type, BODY)
	th.set_font(&"normal_font", &"RichTextLabel", BODY)
	th.set_font(&"font", &"Button", spaced(CATALOG, 3))


## A letter-spaced catalogue font variation (small caps labels).
static func spaced(base: Font, spacing: int) -> FontVariation:
	var v := FontVariation.new()
	v.base_font = base
	v.spacing_glyph = spacing
	return v


static func label(text: String, font: Font, size: int, color: Color = IVORY, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override(&"font", font)
	l.add_theme_font_size_override(&"font_size", size)
	l.add_theme_color_override(&"font_color", color)
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func catalog(text: String, size: int = 16, color: Color = GOLD, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	return label(text.to_upper(), spaced(CATALOG, 4), size, color, align)


static func rule(width: float = 220.0, color: Color = GOLD_DIM) -> Control:
	var c := TextureRect.new()
	c.texture = preload("res://assets/ui/divider.png")
	c.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	c.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	c.custom_minimum_size = Vector2(width, width * 0.12)
	c.modulate = color
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c
