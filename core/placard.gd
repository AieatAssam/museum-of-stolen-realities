class_name Placard
extends Node3D
## An in-world museum label ("tombstone"): ink plate in a brass bezel, left-aligned:
##   title / date / medium / acquisition number / one short paragraph (<= 40 words)
## The same format is used by the reading view (`Placards.read`) and toasts (`Placards.toast`);
## all three take a label Dictionary made by `Placard.fields(...)`. [interact] opens the reader.
## The text faces local +Z.
##
##   $Plaque.set_label(Placard.fields("The Conservation Studio", "Undated", "Staff only",
##       "Acq. No. 000-T", "Every rule of a gallery, in miniature."))
##
## Old API, still accepted: `heading`, `catalog_line` and `set_text(heading, title, catalog, body)`.
## The catalog line is split on "·" into the tombstone lines ("Acq…" -> acquisition,
## "Medium: …" -> medium, anything else -> date line); a dash or numeral heading is dropped.

@export var title: String = "Untitled"
@export var date: String = ""
@export var medium: String = ""
@export var acquisition: String = ""
@export_multiline var body: String = ""
## Plate size, metres. The default reads from a couple of metres; [interact] opens the reader.
@export var size: Vector2 = Vector2(1.2, 0.83)
@export var readable: bool = true
## Legacy fields (see the header). Setting them re-derives date/medium/acquisition.
@export var heading: String = ""
@export var catalog_line: String = "":
	set(v):
		catalog_line = v
		if v != "":
			var f := fields_from_legacy(title, v, body)
			date = f["date"]
			medium = f["medium"]
			acquisition = f["acquisition"]

var _l_title: Label3D
var _l_meta: Label3D
var _l_body: Label3D
var _built: bool = false

static var _plate_mat: StandardMaterial3D
static var _bezel_mat: StandardMaterial3D
static var _back_mat: StandardMaterial3D

const PX_TITLE := 64
const PX_META := 40
const PX_BODY := 44


## A label Dictionary for any placard surface. Empty lines are skipped when shown.
static func fields(t: String, date_: String = "", medium_: String = "", acquisition_: String = "", body_: String = "") -> Dictionary:
	return {"title": t, "date": date_, "medium": medium_, "acquisition": acquisition_, "body": body_}


## Old (title, "Acq. No. 002  ·  Medium: oil, regret", body) strings -> a label Dictionary.
static func fields_from_legacy(t: String, catalog: String, body_: String) -> Dictionary:
	var f := fields(Style.clean(t, ", "), "", "", "", body_)
	var rest: PackedStringArray = []
	for part in Style.clean(catalog).split("\n", false):
		var p := part.strip_edges()
		if p.begins_with("Acq"):
			f["acquisition"] = p
		elif p.to_lower().begins_with("medium:"):
			var m := p.substr(7).strip_edges()
			f["medium"] = m.left(1).to_upper() + m.substr(1)
		elif p != "":
			rest.append(p.left(1).to_upper() + p.substr(1))
	f["date"] = ", ".join(rest)
	return f


## date, medium, acquisition: the non-empty ones, in order.
static func meta_lines(f: Dictionary) -> PackedStringArray:
	var out: PackedStringArray = []
	for k: String in ["date", "medium", "acquisition"]:
		if String(f.get(k, "")) != "":
			out.append(String(f[k]))
	return out


## True when the text (as Label3D lays it out) sits inside the plate. Tests call this.
func text_fits() -> bool:
	var bottom := _l_body.position.y + _l_body.get_aabb().position.y if body != "" else _l_meta.position.y + _l_meta.get_aabb().position.y
	var right := 0.0
	for l: Label3D in [_l_title, _l_meta, _l_body]:
		right = maxf(right, l.position.x + l.get_aabb().end.x)
	return bottom >= -size.y * 0.5 and right <= size.x * 0.5


func get_label() -> Dictionary:
	return fields(title, date, medium, acquisition, body)


func _ready() -> void:
	_build()
	_refresh()


func set_label(f: Dictionary, animate: bool = true) -> void:
	title = String(f.get("title", ""))
	date = String(f.get("date", ""))
	medium = String(f.get("medium", ""))
	acquisition = String(f.get("acquisition", ""))
	body = String(f.get("body", ""))
	if not _built:
		return
	if not animate:
		_refresh()
		return
	var labels: Array[Label3D] = [_l_title, _l_meta, _l_body]
	var t := create_tween()
	for l in labels:
		t.parallel().tween_property(l, "modulate:a", 0.0, 1.2)
	t.tween_callback(_refresh)
	for l in labels:
		t.parallel().tween_property(l, "modulate:a", 1.0, 2.0)


## Legacy: (heading, title, catalog line, body). The heading is not shown (tombstone format).
func set_text(new_heading: String, new_title: String, new_catalog: String, new_body: String, animate: bool = true) -> void:
	heading = new_heading
	set_label(fields_from_legacy(new_title, new_catalog, new_body), animate)


func _refresh() -> void:
	_l_title.text = title
	_l_meta.text = "\n".join(meta_lines(get_label()))
	_l_body.text = body
	# fit: the largest text size (up to 2x the old fixed size) at which the three blocks, wrapped to
	# the plate width at that size, fit the plate's height; measured at the final wrap, so it never spills
	var cap := 0.0011 * size.x / 0.9
	var ps := cap
	var w := int(size.x * 0.86 / ps)
	while ps > cap * 0.2 and _stack_px(w) * ps + 0.034 > size.y - 0.1:
		ps *= 0.95
		w = int(size.x * 0.86 / ps)
	for l: Label3D in [_l_title, _l_meta, _l_body]:
		l.pixel_size = ps
		l.width = w
	# stack the three blocks from the top edge
	var y := size.y * 0.5 - 0.05
	_l_title.position.y = y
	y -= Style.DISPLAY.get_multiline_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, w, PX_TITLE).y * ps + 0.012
	_l_meta.position.y = y
	if _l_meta.text != "":
		y -= Style.TEXT.get_multiline_string_size(_l_meta.text, HORIZONTAL_ALIGNMENT_LEFT, w, PX_META).y * ps + 0.022
	_l_body.position.y = y


## Height in label pixels of title + meta + body wrapped at `w` pixels.
func _stack_px(w: int) -> float:
	var h := Style.DISPLAY.get_multiline_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, w, PX_TITLE).y
	if _l_meta.text != "":
		h += Style.TEXT.get_multiline_string_size(_l_meta.text, HORIZONTAL_ALIGNMENT_LEFT, w, PX_META).y
	if body != "":
		h += Style.TEXT.get_multiline_string_size(body, HORIZONTAL_ALIGNMENT_LEFT, w, PX_BODY).y
	return h


func _mk_label(font: Font, px: int, color: Color, width_px: int) -> Label3D:
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
	l.position = Vector3(-size.x * 0.43, 0, 0.012)  # left-aligned text starts at the origin
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	l.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.width = width_px
	add_child(l)
	return l


## A brass moulding round the plate: a stepped, bevelled profile swept round the rectangle with
## mitred corners, plus a back. Profile = (outward offset from the plate edge, height off the wall).
const BEZEL_PROFILE: Array[Vector2] = [Vector2(-0.002, 0.0095), Vector2(0.004, 0.013), Vector2(0.008, 0.016),
	Vector2(0.014, 0.017), Vector2(0.019, 0.014), Vector2(0.023, 0.009), Vector2(0.026, 0.004), Vector2(0.026, 0.0)]
static var _bezels: Dictionary = {}


## Two surfaces: 0 the moulding, swept on both faces (the back a shallower copy, so a free-standing
## placard has a framed back), 1 the recessed back panel with four domed screw heads. On a wall the
## back half sits inside the wall and is never seen.
const BACK_DEPTH := 0.7  # back moulding height as a fraction of the front's
static func _bezel_mesh(plate: Vector2) -> ArrayMesh:
	if _bezels.has(plate):
		return _bezels[plate]
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var h := plate * 0.5
	var corners: Array[Vector2] = [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]
	for face: float in [1.0, -BACK_DEPTH]:
		var order: Array = [0, 2, 1, 0, 3, 2] if face > 0.0 else [0, 1, 2, 0, 2, 3]
		for c in 4:
			var s0 := corners[c]
			var s1 := corners[(c + 1) % 4]
			for j in BEZEL_PROFILE.size() - 1:
				var a := BEZEL_PROFILE[j]
				var b := BEZEL_PROFILE[j + 1]
				var p := [Vector3(s0.x * (h.x + a.x), s0.y * (h.y + a.x), a.y * face), Vector3(s1.x * (h.x + a.x), s1.y * (h.y + a.x), a.y * face),
					Vector3(s1.x * (h.x + b.x), s1.y * (h.y + b.x), b.y * face), Vector3(s0.x * (h.x + b.x), s0.y * (h.y + b.x), b.y * face)]
				for i: int in order:
					st.add_vertex(p[i])
	st.generate_normals()
	var m := st.commit()
	# the back panel, recessed inside the back moulding, and its screws
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var o := h + Vector2.ONE * BEZEL_PROFILE[0].x
	var z := -BEZEL_PROFILE[0].y * BACK_DEPTH + 0.002
	for v: Vector3 in [Vector3(-o.x, -o.y, z), Vector3(o.x, o.y, z), Vector3(o.x, -o.y, z), Vector3(-o.x, -o.y, z), Vector3(-o.x, o.y, z), Vector3(o.x, o.y, z)]:
		st.add_vertex(v)
	for c in corners:
		var at := Vector3(c.x * (h.x - 0.045), c.y * (h.y - 0.045), z)
		var ring: Array[Vector3] = []
		for k in 8:
			var ang := TAU * k / 8.0
			ring.append(at + Vector3(cos(ang) * 0.011, sin(ang) * 0.011, -0.002))
		var tip := at + Vector3(0, 0, -0.0055)
		for k in 8:
			for v: Vector3 in [tip, ring[(k + 1) % 8], ring[k]]:
				st.add_vertex(v)
	st.generate_normals()
	st.commit(m)
	_bezels[plate] = m
	return m


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
		_bezel_mat.uv1_triplanar = true  # the swept moulding has no UVs
		_bezel_mat.uv1_scale = Vector3(6, 6, 6)
		_back_mat = _bezel_mat.duplicate() as StandardMaterial3D  # the same brass, darkened: aged bronze
		_back_mat.albedo_color = Color(0.36, 0.27, 0.17)
		_back_mat.metallic = 0.75
		_back_mat.roughness = 0.6
		_back_mat.cull_mode = BaseMaterial3D.CULL_DISABLED  # the back panel shows from behind too, never an empty frame
	var bezel := MeshInstance3D.new()
	bezel.mesh = _bezel_mesh(size)
	bezel.set_surface_override_material(0, _bezel_mat)
	bezel.set_surface_override_material(1, _back_mat)
	add_child(bezel)
	var plate := MeshInstance3D.new()
	var pm := QuadMesh.new()
	pm.size = size
	plate.mesh = pm
	plate.material_override = _plate_mat
	plate.position.z = 0.0085
	add_child(plate)
	var w := int(size.x * 0.86 / (0.0011 * size.x / 0.9 * 0.5))
	_l_title = _mk_label(Style.DISPLAY, PX_TITLE, Style.IVORY, w)
	_l_meta = _mk_label(Style.TEXT, PX_META, Style.IVORY_DIM, w)
	_l_body = _mk_label(Style.TEXT, PX_BODY, Color(Style.IVORY, 0.92), w)
	if readable:
		var it := Interactable.make_box(Vector3(size.x, size.y, 0.3), "Read")
		it.max_distance = 3.5
		it.interacted.connect(func(_p: Player) -> void: Placards.read(get_label()))
		add_child(it)
