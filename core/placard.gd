class_name Placard
extends Node3D
## An in-world museum plaque: ink plate in a brass bezel with gilt lettering. Readable at a glance
## from ~2 m; [interact] opens the full reading view. The text faces local +Z.
## `set_text()` rewrites it live (the atrium's placards rewrite themselves to address you).

@export var heading: String = "I"           ## Big line (numeral / name), display serif
@export var title: String = "Untitled"      ## Second line, display serif
@export var catalog_line: String = ""       ## Small caps line (acquisition no. etc.)
@export_multiline var body: String = ""     ## Reading text
@export var size: Vector2 = Vector2(0.9, 0.62)
@export var readable: bool = true

var _l_head: Label3D
var _l_title: Label3D
var _l_cat: Label3D
var _l_body: Label3D
var _built: bool = false

static var _plate_mat: StandardMaterial3D
static var _bezel_mat: StandardMaterial3D


func _ready() -> void:
	_build()
	_refresh()


func set_text(new_heading: String, new_title: String, new_catalog: String, new_body: String, animate: bool = true) -> void:
	heading = new_heading
	title = new_title
	catalog_line = new_catalog
	body = new_body
	if not _built:
		return
	if not animate:
		_refresh()
		return
	var labels: Array[Label3D] = [_l_head, _l_title, _l_cat, _l_body]
	var t := create_tween()
	for l in labels:
		t.parallel().tween_property(l, "modulate:a", 0.0, 1.2)
	t.tween_callback(_refresh)
	for l in labels:
		t.parallel().tween_property(l, "modulate:a", 1.0, 2.0)


func _refresh() -> void:
	_l_head.text = heading
	_l_title.text = title
	_l_cat.text = catalog_line.to_upper()
	_l_body.text = body


func _mk_label(font: Font, px: int, color: Color, y: float, width_px: int = 0) -> Label3D:
	var l := Label3D.new()
	l.font = font
	l.font_size = px
	l.pixel_size = 0.0011 * size.x / 0.9 * 0.5
	l.modulate = color
	l.outline_size = 0
	l.shaded = false
	l.double_sided = false
	l.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	l.alpha_cut = Label3D.ALPHA_CUT_DISABLED
	l.position = Vector3(0, y, 0.012)
	l.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	if width_px > 0:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.width = width_px
	add_child(l)
	return l


func _build() -> void:
	_built = true
	if _plate_mat == null:
		_plate_mat = StandardMaterial3D.new()
		_plate_mat.albedo_color = Color(0.03, 0.026, 0.02)
		_plate_mat.roughness = 0.35
		_plate_mat.metallic = 0.2
		_bezel_mat = StandardMaterial3D.new()
		_bezel_mat.albedo_texture = preload("res://assets/textures/brass/brass_albedo.png")
		_bezel_mat.roughness_texture = preload("res://assets/textures/brass/brass_roughness.png")
		_bezel_mat.metallic = 1.0
		_bezel_mat.albedo_color = Color(1.0, 0.86, 0.6)
	var bezel := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(size.x + 0.05, size.y + 0.05, 0.02)
	bezel.mesh = bm
	bezel.material_override = _bezel_mat
	bezel.position.z = -0.002
	add_child(bezel)
	var plate := MeshInstance3D.new()
	var pm := QuadMesh.new()
	pm.size = size
	plate.mesh = pm
	plate.material_override = _plate_mat
	plate.position.z = 0.0085
	add_child(plate)
	var top := size.y * 0.5 - 0.045
	var w := int(size.x * 0.84 / (0.0011 * size.x / 0.9 * 0.5))
	_l_cat = _mk_label(Style.spaced(Style.CATALOG, 6), 44, Style.GOLD, top)
	_l_head = _mk_label(Style.DISPLAY, 110, Color(Style.GOLD, 1.0) * Color(1.1, 1.1, 1.1), top - 0.05)
	_l_title = _mk_label(Style.DISPLAY, 70, Style.IVORY, top - 0.155, w)
	_l_body = _mk_label(Style.ITALIC, 46, Color(Style.IVORY, 0.85), top - 0.26, w)
	if readable:
		var it := Interactable.make_box(Vector3(size.x, size.y, 0.3), "Read")
		it.max_distance = 3.5
		it.interacted.connect(func(_p: Player) -> void: Placards.read(heading + "  ·  " + title, catalog_line, body))
		add_child(it)
