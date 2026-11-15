extends Wing
## THE UNFINISHED WING, Acq. no. 001. A dying painter's last canvas; it has never dried.
## Rule, WET PAINT: Vesper surfs wet strokes (surf_mode.gd, boarded by paint_walk.gd's magnet),
## and with the painter's knife scrapes strokes off the world and lays them again (canvas.gd).
##
## GREYBOX. Everything is built in code from the coordinates below, grouped as Areas/<Area>/<piece>
## with a "Visual" mesh and a separate "Collision" body, coloured by function:
##   primed canvas (walkable) warm white, bare weave (void, falls) dark linen far below, paint in its
##   own hue (rails, the rule), varnish amber (blocker), pickups and frames gold, pencil graphite.
##
## Route (-Z is "into the painting"): PrimedShore -> Orchard (+ the Unpainted to its west) ->
## River of ultramarine (dam channel east, source cave far east) -> Corrections (rest) ->
## Pentimento (set-piece) -> the kinder road back to the Old Tree -> the horizon line west to the
## Edge -> the museum ledge (jaw-drop) -> heist along the long stroke back to the shore.
## See LAYOUT.md.

const Canvas := preload("res://wings/paint/canvas.gd")
const Stroke := preload("res://wings/paint/stroke.gd")
const SurfMode := preload("res://wings/paint/surf_mode.gd")
const PaintWalk := preload("res://wings/paint/paint_walk.gd")
const SND := "res://wings/paint/audio/"
const COURSE := Vector3(600, 0, 0)

const COL := {
	"primed": Color("efe9dc"), "weave": Color("3b352c"), "goal": Color("e0b43c"),
	"crust": Color("8c7a62"), "wall": Color("d8cfbd"), "frame": Color("b8913a"),
	"museum": Color("5d5246"), "figure": Color("c79f86"), "interact": Color("d23cc8"),
}

var canvas: Node3D
var areas: Node3D
var surf: SurfMode
var walker: PaintWalk
var pts: Dictionary = {}          # named points (tests, cinematics)
var uses: Dictionary = {}         # interactables by id
var mood: float = 0.5             # the painter, as weather: 0 grey smear .. 1 warm
var mood_shown: float = 0.5
var env: Environment
var sky_mat: ProceduralSkyMaterial
var sun: DirectionalLight3D
var _mats: Dictionary = {}
var _last_safe: Vector3 = Vector3.INF
var _last_safe_stroke: Node3D
var _last_safe_yaw: float = 0.0
var _respawning: bool = false
var _safe_tick: int = 0
var _surf_dist_acc: float = 0.0


# =============================================================================================
# Wing contract

func objectives() -> Array[Dictionary]:
	return [
		{"id": "orchard", "title": "Walk the orchard of single strokes", "steps": [
			{"id": "ride", "title": "Ride a bough across the first void"},
			{"id": "chain", "title": "Cross three boughs without touching the ground"},
			{"id": "crown", "title": "Kick off the impasto to the Old Tree's crown"},
			{"id": "bridge", "title": "Lay a stroke of your own across the gap"}]},
		{"id": "river", "title": "Follow the ultramarine to its source", "steps": [
			{"id": "float", "title": "Cross the river on paint that floats"},
			{"id": "dam", "title": "Hold the water back"},
			{"id": "burn", "title": "Burn through the varnish"},
			{"id": "light", "title": "Find the way in the unpainted dark"}]},
		{"id": "edge", "title": "Find the edge of the canvas", "steps": [
			{"id": "pentimento", "title": "The first composition"},
			{"id": "green", "title": "Grow the Old Tree green"},
			{"id": "horizon", "title": "Ride the horizon to the edge"}]},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "stub", "name": "A pencil stub", "line": "Sharpened with a knife, both ends. The underdrawing it made is still finding its way in the dark."},
		{"id": "swatch", "name": "A dried colour swatch", "line": "Violet, tested and kept. The only paint in the wing permitted to dry."},
		{"id": "ferrule", "name": "The palette knife's ferrule", "line": "Brass, from the painter's own knife. The knife you carry has a new one."},
	]


func fragment() -> Dictionary:
	return {"name": "The first stroke", "line": "Lifted from the edge, where the painter began. The canvas is now one stroke less finished than it was."}


func register_modes(player: Player) -> void:
	walker = PaintWalk.new()
	surf = SurfMode.new()
	walker.surf = surf
	walker.find_rail = canvas.find_rail
	walker.climb_top = canvas.climb_top
	surf.connect_at = canvas.connect_at
	surf.on_event = _on_surf
	player.add_mode(&"paint", walker)
	player.add_mode(&"surf", surf)
	player.primary.connect(func(pressed: bool) -> void:
		if pressed:
			_on_lay())
	player.secondary.connect(func(pressed: bool) -> void:
		if pressed:
			_on_scrape())


func save_state() -> Dictionary:
	return {"canvas": canvas.state(), "mood": mood}


func load_state(st: Dictionary) -> void:
	canvas.restore(st.get("canvas", {}))
	mood = float(st.get("mood", 0.5))
	mood_shown = mood
	_apply_mood(mood_shown)
	_apply_progress()


func on_enter(first_time: bool) -> void:
	_last_safe = Game.player.global_position
	if first_time:
		await Cinematics.play([
			{"card": "The Unfinished Wing", "sub": "Acquisition no. 001", "t": 4.0, "style": "display"},
		])


# =============================================================================================
# Build

func _ready() -> void:
	canvas = Canvas.new()
	canvas.name = "Canvas"
	add_child(canvas)
	areas = Node3D.new()
	areas.name = "Areas"
	add_child(areas)
	var marks := Node3D.new()
	marks.name = "ShotMarks"
	add_child(marks)
	_build_environment()
	_build_course()
	_build_world()
	canvas.scraped.connect(_on_scraped)
	canvas.laid.connect(_on_laid)
	canvas.blended.connect(_on_blended)
	canvas.sank.connect(func(_s: Node3D) -> void: _sfx("sink", null, -4.0); _nudge_mood(-0.01))
	canvas.burned.connect(func(_id: String) -> void:
		_sfx("burn", null, -2.0)
		complete_step(&"river", &"burn"))
	canvas.refused.connect(func(_w: String) -> void: _sfx("refuse", null, -10.0))
	canvas._refresh()


func _build_environment() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat = ProceduralSkyMaterial.new()
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.8
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true
	env.glow_bloom = 0.05
	env.fog_enabled = true
	env.fog_density = 0.002
	env.fog_sky_affect = 0.4
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	add_child(we)
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 120.0
	add_child(sun)
	sun.look_at_from_position(Vector3.ZERO, Vector3(0.4, -0.7, -0.5), Vector3.UP)
	grade = PostGrade.new()
	grade.saturation = 1.05
	grade.contrast = 1.02
	grade.grain = 0.02
	grade.vignette = 0.3


# --- primitives ---------------------------------------------------------------------------------

func _area(path: String) -> Node3D:
	var n := areas.get_node_or_null(path)
	if n:
		return n
	var parent := areas
	for part in path.split("/"):
		var c := parent.get_node_or_null(part)
		if c == null:
			c = Node3D.new()
			c.name = part
			parent.add_child(c)
		parent = c
	return parent


func _mat(key: String) -> StandardMaterial3D:
	if not _mats.has(key):
		var m := StandardMaterial3D.new()
		m.albedo_color = COL[key]
		m.roughness = 0.85
		if key == "goal":
			m.emission_enabled = true
			m.emission = COL[key]
			m.emission_energy_multiplier = 0.6
		_mats[key] = m
	return _mats[key]


## A named block: <name>/Visual (mesh) + <name>/Collision (static body), corners a and b.
func _block(area: String, name: String, a: Vector3, b: Vector3, mat: String = "primed", solid: bool = true) -> Node3D:
	var root := Node3D.new()
	root.name = name
	var lo := a.min(b)
	var hi := a.max(b)
	root.position = (lo + hi) * 0.5
	var size := hi - lo
	var mi := MeshInstance3D.new()
	mi.name = "Visual"
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(mat)
	root.add_child(mi)
	if solid:
		var sb := StaticBody3D.new()
		sb.name = "Collision"
		sb.set_meta(&"surface", "canvas")
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = size
		cs.shape = bs
		sb.add_child(cs)
		root.add_child(sb)
	_area(area).add_child(root)
	return root


## Ground slab whose TOP is at y (thickness 1 m).
func _ground(area: String, name: String, x0: float, z0: float, x1: float, z1: float, y: float = 0.0, mat: String = "primed") -> Node3D:
	return _block(area, name, Vector3(x0, y - 1.0, z0), Vector3(x1, y, z1), mat)


func _stroke(area: String, id: String, p: Array, c: String, w: float = 2.0, extra: Dictionary = {}) -> Node3D:
	return canvas.add(Stroke.make(id, p, c, w, extra), _area(area))


func _checkpoint(area: String, id: String, pos: Vector3, face: Vector3, radius: float = 3.0) -> Checkpoint:
	var c := Checkpoint.new()
	c.name = "Checkpoint_" + id
	c.id = StringName(id)
	c.radius = radius
	_area(area).add_child(c)
	c.global_transform = Transform3D(Basis.looking_at(face.normalized(), Vector3.UP), pos)
	return c


func _mark(name: String, pos: Vector3, look: Vector3) -> void:
	var m := Marker3D.new()
	m.name = name
	m.add_to_group(&"shot_marks")
	get_node("ShotMarks").add_child(m)
	m.global_transform = Transform3D(Basis.looking_at((look - pos).normalized(), Vector3.UP), pos)


func _placard(area: String, pos: Vector3, facing: Vector3, title: String, date: String, medium: String, acq: String, body: String) -> Placard:
	var p := Placard.new()
	p.name = "Placard_" + acq.replace(".", "_")
	_area(area).add_child(p)
	p.global_transform = Transform3D(Basis.looking_at(-facing.normalized(), Vector3.UP), pos)
	p.set_label(Placard.fields(title, date, medium, "Acq. no. " + acq, body), false)
	return p


func _zone(area: String, a: Vector3, b: Vector3, cb: Callable, once: bool = true) -> TriggerZone:
	var tz := TriggerZone.make_box((b - a).abs(), once)
	tz.position = (a + b) * 0.5
	tz.triggered.connect(func(_p: Player) -> void: cb.call())
	_area(area).add_child(tz)
	return tz


func _use(area: String, id: String, pos: Vector3, size: Vector3, prompt: String, cb: Callable) -> Interactable:
	var it := Interactable.make_box(size, prompt)
	it.name = "Use_" + id
	it.position = pos
	it.interacted.connect(func(_p: Player) -> void: cb.call())
	_area(area).add_child(it)
	uses[id] = it
	return it


func _prop(area: String, name: String, pos: Vector3, size: Vector3, mat: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(mat)
	mi.position = pos
	_area(area).add_child(mi)
	return mi


func _sfx(n: String, at: Variant = null, db: float = 0.0, pitch: float = 1.0) -> void:
	var path := SND + n + ".ogg"
	if ResourceLoader.exists(path):
		Audio.sfx(load(path), at, db, 0.2, pitch)


# =============================================================================================
# The test course (far east, x 600): proves surf, chain, bleed, kick, scrape and re-lay.

func _build_course() -> void:
	var O := COURSE
	var A := "TestCourse"
	_ground(A, "Pad0", O.x - 5, O.z + 5, O.x + 5, O.z - 3)
	_stroke(A, "course_a", [O + Vector3(0, 0.25, -1), O + Vector3(0, 0.25, -24)], "blue")
	_stroke(A, "course_b", [O + Vector3(0, -1.2, -29), O + Vector3(0, -1.2, -48)], "blue")
	_stroke(A, "course_c", [O + Vector3(0, -2.5, -53), O + Vector3(0, -2.5, -72)], "blue", 2.0, {"kicks": [17.0]})
	_ground(A, "Pad1", O.x - 5, O.z - 80, O.x + 5, O.z - 92, 0.5)
	_stroke(A, "course_red", [O + Vector3(4.5, 0.5, -82), O + Vector3(4.5, 0.5, -91)], "red", 1.5, {"up": true, "t": 0.4})
	_ground(A, "Pad2", O.x - 5, O.z - 98, O.x + 5, O.z - 110, 0.5)
	_checkpoint(A, "course", O + Vector3(0, 0, 3), Vector3(0, 0, -1), 1.0)
	pts["course_start"] = O + Vector3(0, 0, 3)
	pts["pad1"] = O + Vector3(0, 0.5, -86)
	pts["pad1_edge"] = O + Vector3(0, 0.5, -91.2)
	pts["pad2_near"] = O + Vector3(0, 0.5, -99)
	pts["pad2"] = O + Vector3(0, 0.5, -105)


# =============================================================================================
# Verbs, weather, falls

func _on_scrape() -> void:
	var r: String = canvas.scrape(Game.player.camera)
	if r in ["ok", "well", "seal"]:
		_sfx("scrape", Game.player.global_position, -2.0, randf_range(0.95, 1.05))


func _on_lay() -> void:
	var r: String = canvas.lay(Game.player)
	if r == "ok":
		_sfx("lay", Game.player.global_position, -2.0, randf_range(0.95, 1.05))


func _on_scraped(st: Node3D, world: bool) -> void:
	if world and st.kind != "well":
		_nudge_mood(-0.012)   # destruction is noticed


func _on_laid(_st: Node3D) -> void:
	_nudge_mood(0.01)


func _on_blended(a: Node3D, b: Node3D, c: String) -> void:
	_sfx("blend", null, -3.0)
	if c == "green" and (a.sid == "old_tree" or b.sid == "old_tree"):
		complete_step(&"edge", &"green")


func _on_surf(ev: String, data: Variant) -> void:
	match ev:
		"board":
			_sfx("board", Game.player.global_position, -6.0, 0.9 + 0.05 * surf.chain)
			if surf.chain >= 2:
				_nudge_mood(0.006 * minf(surf.chain, 5))
			if surf.chain >= 3 and String(data.sid).begins_with("bough_"):
				complete_step(&"orchard", &"chain")
			if data.rec.has("fl"):
				complete_step(&"river", &"float")
		"kick":
			_sfx("kick", Game.player.global_position, -4.0)


func _nudge_mood(d: float) -> void:
	mood = clampf(mood + d, 0.0, 1.0)


## The painter as weather: warm, high-key light when travelled well; a grey smear across the
## horizon (fog, desaturation, low sun) when the canvas is being damaged.
func _apply_mood(m: float) -> void:
	var grey := Color("8f8c88")
	sky_mat.sky_top_color = grey.lerp(Color("5f9ee8"), m)
	sky_mat.sky_horizon_color = grey.lerp(Color("ffc98a"), m)
	sky_mat.ground_horizon_color = sky_mat.sky_horizon_color
	sky_mat.ground_bottom_color = Color("3b352c")
	sun.light_color = Color("c9c6c0").lerp(Color("ffe0b0"), m)
	sun.light_energy = lerpf(0.7, 1.5, m)
	env.fog_light_color = grey.lerp(Color("ffd9a8"), m)
	env.fog_density = lerpf(0.009, 0.0015, m)
	if grade:
		grade.saturation = lerpf(0.55, 1.12, m)


func _physics_process(delta: float) -> void:
	var p := Game.player
	if p == null or Game.wing != self:
		return
	# weather follows the painter's mood over minutes, not seconds
	mood_shown = lerpf(mood_shown, mood, 1.0 - exp(-delta / 20.0))
	if Engine.get_physics_frames() % 30 == 0:
		_apply_mood(mood_shown)
		if grade:
			Post.apply(grade, 0.0)
	if surf and p.mode == surf:
		_surf_dist_acc += surf.speed * delta
		if _surf_dist_acc > 40.0:
			_surf_dist_acc = 0.0
			_nudge_mood(0.004)
	_track_safe(p)
	if not _respawning and p.global_position.y < _kill_y(p.global_position):
		_fall()
	_tick(delta)


func _kill_y(pos: Vector3) -> float:
	var w: Dictionary = canvas.water_at(pos)
	if not w.is_empty() and pos.y < float(w["level"]) - 0.4:
		return INF
	return -9.0


func _track_safe(p: Player) -> void:
	_safe_tick += 1
	if _safe_tick % 15 != 0:
		return
	if p.mode == surf and is_instance_valid(surf.stroke) and _stroke_is_safe(surf.stroke):
		_last_safe = surf.stroke.sample(surf.board_s)
		_last_safe_stroke = surf.stroke
		var t: Vector3 = surf.stroke.tangent(surf.board_s) * surf.dir
		_last_safe_yaw = atan2(-t.x, -t.z)
	elif p.is_on_floor() and p.mode == walker:
		var c := p.get_last_slide_collision()
		var col: Object = c.get_collider() if c else null
		if col != null and (not col.has_meta(&"stroke") or _stroke_is_safe(col)):
			_last_safe = p.global_position
			_last_safe_stroke = col as Node3D if col.has_meta(&"stroke") else null
			_last_safe_yaw = p.yaw


## Strokes that move (Pentimento hills, sinking violet, drying heist rails) are not respawn points.
func _stroke_is_safe(st: Node3D) -> bool:
	return st.enabled and not st.has_meta(&"unsafe") and not canvas.sunk.has(st.sid)


func _safe_point() -> Transform3D:
	if _last_safe != Vector3.INF and (_last_safe_stroke == null or (is_instance_valid(_last_safe_stroke) and _last_safe_stroke.enabled)):
		return Transform3D(Basis(Vector3.UP, _last_safe_yaw), _last_safe + Vector3.UP * 0.1)
	var cp := find_checkpoint(Game.checkpoint_id)
	return cp.global_transform if cp else Transform3D.IDENTITY


## A fall into the bare weave: back on the last stroke she stood on, within a second.
func _fall() -> void:
	_respawning = true
	var p := Game.player
	_nudge_mood(-0.04)
	_sfx("fall", null, -6.0)
	p.input_enabled = false
	await Post.fade_to(1.0, 0.2)
	if not is_instance_valid(p) or Game.wing != self:
		return
	var xf := _respawn_point()
	p.set_mode(&"paint")
	p.teleport(xf)
	walker.momentum = false
	_on_respawned()
	await get_tree().create_timer(0.15).timeout
	if is_instance_valid(p):
		p.input_enabled = true
	await Post.fade_to(0.0, 0.35)
	_respawning = false


# =============================================================================================
# THE WING. Coordinates in metres; ground tops given as y. See LAYOUT.md for the map.

const W_ID := &"paint"
const PENT_C := Vector3(0, 0, -385)
const PENT_R := 33.0
const LAYERS := 3
const REGROW := 45.0
const DRY_SPEED := 9.0
const DRY_GRACE := 3.0
const HEIST_IDS := ["heist_0", "heist_red_1", "heist_red_2", "heist_blue_1", "heist_final"]

var hills: Array = []            # [stroke, base Transform3D, k]
var seals: Array = []            # per layer: [stroke, stroke, stroke]
var pent: int = 0                # layers removed
var pent_t: float = 0.0
var _regrow: float = -1.0
var figure: Node3D
var arena_mat: StandardMaterial3D
var revealed: bool = false
var heist: bool = false          # the long stroke home is live
var heist_t: float = -1.0        # seconds since boarding it (-1: not started)
var heist_m0: float = 0.0
var heist_stage: int = 0         # 0 before the junction, 1 after
var heist_ridden: Dictionary = {}  # sid -> heist metres when boarded
var heist_nominal: Dictionary = {} # sid -> route metres for strokes she did not ride
var knots: Array = []            # [stroke, s, node]


func _build_world() -> void:
	_build_shore()
	_build_orchard()
	_build_windfall()
	_build_river()
	_build_corrections()
	_build_pentimento()
	_build_edge()
	_build_heist()
	_build_marks()
	# the bare weave: the void, far below, never solid
	_block("BareWeave", "Weave", Vector3(-420, -32, 80), Vector3(320, -31, -460), "weave", false)
	canvas.seal_scraped.connect(_on_seal)


func _post(area: String, pos: Vector3, facing: Vector3, title: String, date: String, medium: String, acq: String, body: String) -> void:
	_prop(area, "Post_" + acq.replace(".", "_"), pos + Vector3(0, 0.55, 0), Vector3(0.12, 1.1, 0.12), "museum")
	_placard(area, pos + Vector3(0, 1.25, 0), facing, title, date, medium, acq, body)


## A well: a puddle of paint that refills when scraped (so no dead end is permanent).
func _well(area: String, id: String, a: Vector3, b: Vector3, c: String, extra: Dictionary = {}) -> Node3D:
	var e := {"k": "well", "t": 0.3}
	e.merge(extra, true)
	return _stroke(area, id, [a + Vector3(0, 0.12, 0), b + Vector3(0, 0.12, 0)], c, 1.0, e)


# --- PrimedShore -------------------------------------------------------------------------------

func _build_shore() -> void:
	var A := "PrimedShore"
	_ground(A, "Shore", -14, 30, 14, -18)
	_checkpoint(A, "start", Vector3(0, 0, 6), Vector3(0, 0, -1))
	_stroke(A, "shore_bough", [Vector3(0, 0.25, -12), Vector3(0, 0.25, -26), Vector3(0, 0.25, -40)], "blue")
	_post(A, Vector3(-3, 0, 3), Vector3(0.5, 0, 1), "Primed ground", "Laid in a single morning", "Lead white on linen", "001.1",
		"The painter primed the canvas and died before the second coat. Visitors are asked to keep to the white. The white is not dry. Nothing in this wing has been allowed to dry.")
	_post(A, Vector3(3, 0, -9), Vector3(-0.3, 0, 1), "A single bough", "Undated", "Ultramarine, one stroke", "001.2",
		"Painted without lifting the brush. Conservators measured it twice and recorded two lengths. Both are on file. Visitors may stand on it. The museum does not recommend standing still.")
	_zone(A, Vector3(-14, -1, 4), Vector3(14, 5, 30), _on_home, false)
	pts["start"] = Vector3(0, 0, 6)


# --- Orchard: the chain of boughs, the kick to the crown, the knife, the first bridge ------------

func _build_orchard() -> void:
	var A := "Orchard"
	_ground(A, "Grove", -16, -36, 16, -61)
	_post(A, Vector3(-4, 0, -46), Vector3(0.6, 0, 1), "Orchard of single strokes", "Spring, year unrecorded", "Oil, wet", "001.3",
		"Each tree is one stroke and each stroke is a tree. The painter planned forty. Thirty nine are listed in the inventory. The inventory was taken by the painter.")
	_zone(A, Vector3(-16, -1, -38), Vector3(16, 4, -46), func() -> void: complete_step(&"orchard", &"ride"))
	# three boughs falling away over the void, the last with an impasto ridge
	_stroke(A, "bough_1", [Vector3(0, 0.25, -59), Vector3(0, 0.25, -82)], "blue")
	_stroke(A, "bough_2", [Vector3(0, -1.2, -87), Vector3(0, -1.2, -106)], "blue")
	_stroke(A, "bough_3", [Vector3(0, -2.5, -111), Vector3(0, -2.5, -130)], "blue", 2.0, {"kicks": [17.0]})
	_ground(A, "Crown", -6, -136, 6, -152, 0.5, "goal")
	_zone(A, Vector3(-6, 0, -136), Vector3(6, 4, -152), func() -> void: complete_step(&"orchard", &"crown"))
	_stroke(A, "stray_bough", [Vector3(-4.6, 0.5, -139), Vector3(-4.6, 0.5, -148)], "blue", 1.5, {"up": true, "t": 0.4})
	_prop(A, "Knife", Vector3(2, 0.62, -146), Vector3(0.12, 0.04, 0.5), "museum")
	_use(A, "knife", Vector3(2, 0.9, -146), Vector3(1.2, 1, 1.2), "Take the painter's knife", _take_knife)
	pts["grove"] = Vector3(0, 0, -50)
	pts["crown"] = Vector3(0, 0.5, -146)
	pts["crown_edge"] = Vector3(0, 0.5, -151.2)
	pts["windfall_near"] = Vector3(0, 0.5, -158.6)


func _take_knife() -> void:
	if canvas.has_knife:
		return
	canvas.has_knife = true
	var n := areas.get_node_or_null("Orchard/Knife")
	if n:
		n.queue_free()
	_sfx("lay", null, -4.0)
	toast(Placard.fields("Palette knife", "Before 1900", "Steel, walnut, brass ferrule (replaced)", "Acq. No. 001.4",
		"Used for mixing, for scraping and once, according to a letter we do not hold, for an argument. Lent to the visitor for the duration. Return is assumed."))


# --- Windfall: the Old Tree, the test strip, the edge of the Unpainted ---------------------------

func _build_windfall() -> void:
	var A := "Windfall"
	_ground(A, "Windfall", -16, -158, 24, -188, 0.5)
	_checkpoint(A, "windfall", Vector3(0, 0.5, -162), Vector3(0, 0, -1))
	_zone(A, Vector3(-16, 0, -158), Vector3(24, 4, -165), func() -> void: complete_step(&"orchard", &"bridge"))
	# the Old Tree: umber over an earlier blue (Pentimento restores the blue)
	_stroke(A, "old_tree", [Vector3(12, 0.5, -170), Vector3(12, 0.5, -172.5)], "umber", 9.0, {"up": true, "t": 0.8, "k": "trunk", "grow": 24.2})
	_post(A, Vector3(8, 0.5, -166), Vector3(-0.4, 0, 1), "The Old Tree", "Painted first, painted last", "Umber over an earlier blue", "001.5",
		"X radiography shows a green tree beneath. The painter's notebook calls the umber a correction. It does not say what was wrong with the tree.")
	# a U-shaped lookout around where the green will reach, and the horizon line from it
	_block(A, "LookoutEast", Vector3(13.6, 23.4, -166), Vector3(19, 24.4, -176.5))
	_block(A, "LookoutWest", Vector3(4.8, 23.4, -166), Vector3(10.0, 24.4, -176.5))   # the hole is the green column's, plus her shoulders
	_block(A, "LookoutNorth", Vector3(4.8, 23.4, -163), Vector3(19, 24.4, -166))
	_well(A, "lamp_oil", Vector3(-12, 0.5, -163), Vector3(-12, 0.5, -167), "yellow")
	_well(A, "ultramarine_bank", Vector3(-26, 0.5, -185.5), Vector3(-8, 0.5, -185.5), "blue")
	_well(A, "red_tube", Vector3(9, 0.5, -186), Vector3(12, 0.5, -186), "red")
	_well(A, "pear", Vector3(-4, 0.5, -181), Vector3(0, 0.5, -181), "yellow", {"hidden": true})
	# the test strip (Provenance: the dried swatch). Sealed blue; it will not lift, only sink.
	_block(A, "NicheBack", Vector3(23.5, 0.5, -179.5), Vector3(24, 3.2, -186.5), "wall")
	_block(A, "NicheN", Vector3(18, 0.5, -179.5), Vector3(24, 3.2, -180), "wall")
	_block(A, "NicheS", Vector3(18, 0.5, -186), Vector3(24, 3.2, -186.5), "wall")
	_block(A, "NicheRoof", Vector3(18, 3.2, -179.5), Vector3(24, 3.6, -186.5), "wall")
	_stroke(A, "test_strip", [Vector3(17.7, 0.5, -180), Vector3(17.7, 0.5, -186)], "blue", 2.7, {"up": true, "t": 0.4, "k": "fixed", "sink": 3.6})
	_pickup(A, "swatch", Vector3(21.5, 1.2, -183), Color("6b34a8"))
	# the Unpainted (Provenance: the pencil stub): underdrawing, solid only in yellow light
	var U := "Unpainted"
	_block(U, "Shade", Vector3(-16, 7, -158), Vector3(-68, 8, -182), "weave")
	_stroke(U, "pencil_1", [Vector3(-17, 0.5, -170), Vector3(-37, 0.5, -170)], "pencil", 2.0, {"k": "pencil"})
	_stroke(U, "pencil_2", [Vector3(-37, 0.5, -170), Vector3(-55, 0.5, -171)], "pencil", 2.0, {"k": "pencil"})
	_ground(U, "Pedestal", -55, -166, -63, -175, 0.5, "crust")
	_pickup(U, "stub", Vector3(-59, 1.2, -170.5), Color("4a4a50"))
	_post(U, Vector3(-13, 0.5, -175), Vector3(1, 0, 0.3), "The Unpainted", "Never begun", "Graphite underdrawing", "001.6",
		"Lines the painter drew and never covered. They can be seen only by lamplight. The museum has no record of a lamp. The museum has a record of the lines.")
	pts["windfall"] = Vector3(0, 0.5, -162)
	pts["lamp_oil"] = Vector3(-12, 0.62, -165)
	pts["unpainted_edge"] = Vector3(-14.6, 0.5, -170)
	pts["pencil_1_end"] = Vector3(-35.6, 0.5, -170)
	pts["pedestal"] = Vector3(-59, 0.5, -170.5)
	pts["strip_stand"] = Vector3(14, 0.5, -183)


func _pickup(area: String, id: String, pos: Vector3, c: Color) -> Pickup:
	var root := Node3D.new()
	root.name = "Provenance_" + id
	root.position = pos
	_area(area).add_child(root)
	var mi := MeshInstance3D.new()
	mi.name = "Visual"
	var bm := BoxMesh.new()
	bm.size = Vector3(0.35, 0.35, 0.35)
	mi.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = COL["goal"]
	m.emission_energy_multiplier = 0.4
	mi.material_override = m
	root.add_child(mi)
	var pk := Pickup.new()
	pk.name = "Pickup"
	pk.kind = &"provenance"
	pk.item_id = StringName(id)
	pk.visual = mi
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(1, 1, 1)
	cs.shape = sh
	pk.add_child(cs)
	root.add_child(pk)
	uses[id] = pk
	return pk


# --- River of ultramarine: float, dam, burn, light ----------------------------------------------

func _build_river() -> void:
	var A := "River"
	canvas.add_water("river", Rect2(-40, -204, 100, 16), -0.3, NAN, Rect2(), _area(A))
	_ground(A, "Beach", -30, -204, 26, -209, -0.35)
	_ground(A, "Terrace", -30, -209, 26, -252, 0.0)
	_checkpoint(A, "terrace", Vector3(0, 0, -212), Vector3(0, 0, -1))
	_post(A, Vector3(-6, 0.5, -184), Vector3(0, 0, 1), "River of ultramarine", "1891", "Ultramarine, cobalt, linseed", "001.7",
		"Ground lapis cost more than the canvas. The painter used it for water anyway. Blue rides on it. Other colours are absorbed and are not catalogued again.")
	# the mill basin: dam its inlet with a blue wall and it drains to the bed
	canvas.add_water("basin", Rect2(26, -250, 40, 44), -0.3, -6.0, Rect2(26, -250, 7, 44), _area(A))
	_ground(A, "BasinBed", 26, -206, 66, -250, -3.0, "crust")
	_stroke(A, "basin_ramp", [Vector3(60, -2.75, -228), Vector3(70, 0.25, -228)], "umber", 2.0, {"k": "fixed"})
	_post(A, Vector3(22, 0, -214), Vector3(-1, 0, 0.4), "Mill race", "1891, altered", "Oil, with a dam the painter did not paint", "001.8",
		"The water here rises and falls according to whatever stands in its way. Conservators have stopped standing in its way. The level shown is the level at the time of writing.")
	# the source bank: varnish, then the dark
	_ground(A, "SourceBank", 66, -206, 100, -250, 0.0)
	_well(A, "terrace_blue", Vector3(18, 0, -232), Vector3(18, 0, -236), "blue")
	_well(A, "cinnabar", Vector3(72, 0, -240), Vector3(72, 0, -245), "red")
	canvas.add_varnish("crust", Vector3(80, 0, -206), Vector3(82, 7, -250), _area(A))
	_well(A, "cave_lamp", Vector3(90, 0, -244), Vector3(95, 0, -244), "yellow")
	_block(A, "CaveRoof", Vector3(82, 6, -204), Vector3(142, 7, -252), "weave")
	_block(A, "CaveWallN", Vector3(82, 0, -204), Vector3(142, 6, -206), "weave")
	_block(A, "CaveWallS", Vector3(82, 0, -250), Vector3(130, 6, -252), "weave")
	_block(A, "CaveWallS2", Vector3(134, 0, -250), Vector3(142, 6, -252), "weave")   # the outflow's mouth
	_stroke(A, "cave_pencil", [Vector3(100, 0, -228), Vector3(125, 0, -228)], "pencil", 2.0, {"k": "pencil"})
	_ground(A, "Source", 125, -214, 140, -242, 0.0, "goal")
	_zone(A, Vector3(125, -1, -214), Vector3(140, 4, -242), _reach_source)
	_post(A, Vector3(136, 0, -222), Vector3(-1, 0, 0), "The source", "Date of first wetting unknown", "Pigment, unmixed", "001.9",
		"Every river in the painting begins here, in the dark, as a single drop of blue. Visitors who reach the source are asked how. Most say a lamp.")
	# the outflow: shown once she reaches the source, it carries her down to the Corrections
	_stroke(A, "outflow", [Vector3(132, 0.25, -238), Vector3(132, 0.25, -256), Vector3(60, 0.25, -262), Vector3(12, 0.25, -268), Vector3(4, 0.25, -277)],
		"blue", 2.0, {"hidden": true})
	pts["bank"] = Vector3(0, 0.5, -187.4)
	pts["bank_well"] = Vector3(-17, 0.62, -185.5)
	pts["beach"] = Vector3(0, -0.35, -205.2)
	pts["terrace"] = Vector3(0, 0, -212)
	pts["dam_stand"] = Vector3(25.2, 0, -228)
	pts["bed"] = Vector3(56, -3, -228)
	pts["cinnabar"] = Vector3(72, 0.12, -242.5)
	pts["varnish_stand"] = Vector3(75, 0, -228)
	pts["cave_lamp"] = Vector3(92.5, 0.12, -244)
	pts["cave_edge"] = Vector3(98.8, 0, -228)
	pts["source"] = Vector3(132, 0, -232)


func _reach_source() -> void:
	complete_step(&"river", &"light")
	var o: Node3D = canvas.get_stroke("outflow")
	if o and not o.enabled:
		canvas._reveal(o)


# --- Corrections: rest; earlier poses; the violet rule ---------------------------------------------

func _build_corrections() -> void:
	var A := "Corrections"
	_ground(A, "Studio", -30, -272, 30, -330)
	_checkpoint(A, "corrections", Vector3(0, 0, -282), Vector3(0, 0, -1))
	_post(A, Vector3(-4, 0, -284), Vector3(0.3, 0, 1), "Studies in correction", "Various sittings", "Oil, partially removed", "001.10",
		"Figures scraped back and begun again. Each earlier pose survives underneath. The test strip on the windfall is sealed in blue and will not lift. Sealed things in this wing tend to sink instead.")
	# half-scraped figures: scrape one and the earlier pose comes back
	for i in 3:
		var x := -22.0 + i * 7.0
		_stroke(A, "figure_%d" % i, [Vector3(x, 0, -296), Vector3(x + 2.5, 0, -298)], "umber", 5.0, {"up": true, "t": 0.5, "under": ["figure_%d_early" % i]})
		_stroke(A, "figure_%d_early" % i, [Vector3(x - 1, 0, -299), Vector3(x + 1.5, 0, -296)], "white", 4.0, {"up": true, "t": 0.5, "hidden": true})
	# the hand: its earlier pose is a ramp to a ledge (Provenance: the ferrule)
	_stroke(A, "figure_hand", [Vector3(13, 0, -287), Vector3(19, 0, -287)], "umber", 6.0, {"up": true, "t": 0.6, "under": ["figure_hand_early"]})
	_stroke(A, "figure_hand_early", [Vector3(12, 0.25, -290), Vector3(24, 3.25, -299)], "blue", 2.0, {"hidden": true})
	_ground(A, "HandLedge", 21.5, -296, 38, -306, 3.0, "crust")   # long: the pose is a wet rail and throws her
	_pickup(A, "ferrule", Vector3(26, 3.7, -302), Color("b8913a"))
	# the green, taught: yellow across this blue hedge grows a climbable column to a view
	_stroke(A, "hedge", [Vector3(-12, 0, -306), Vector3(-12, 0, -314)], "blue", 1.0, {"up": true, "t": 0.5, "k": "fixed", "grow": 7.0})
	_well(A, "corr_yellow", Vector3(-24, 0, -300), Vector3(-24, 0, -304), "yellow")
	_block(A, "View", Vector3(-19, 5.6, -305), Vector3(-13.2, 6.6, -315))
	# the way on is barred in fixed blue; red into it makes violet, and violet sinks
	_ground(A, "Causeway", -4, -330, 4, -352)
	_well(A, "corr_red", Vector3(8, 0, -322), Vector3(12, 0, -322), "red")
	_stroke(A, "barrier", [Vector3(-4.6, 0, -336), Vector3(4.6, 0, -336)], "blue", 3.2, {"up": true, "t": 0.6, "k": "fixed", "sink": 3.7})
	_post(A, Vector3(6, 0, -328), Vector3(-0.5, 0, 1), "The violet rule", "Late", "Cadmium red into ultramarine", "001.11",
		"The painter mixed red into blue only to put something away. Violet is heavy here. The barrier was blue at accession and is listed as violet in a condition report that predates it.")
	pts["corrections"] = Vector3(0, 0, -282)
	pts["hand_stand"] = Vector3(16, 0, -282)
	pts["ramp_start"] = Vector3(12, 0, -288.6)
	pts["hand_ledge"] = Vector3(26, 3, -302)
	pts["corr_red"] = Vector3(10, 0.12, -322)
	pts["barrier_stand"] = Vector3(0, 0, -331.5)


# --- Pentimento --------------------------------------------------------------------------------------

func _build_pentimento() -> void:
	var A := "Pentimento"
	var C := PENT_C
	_post(A, Vector3(-3, 0, -344), Vector3(0, 0, 1), "Pentimento", "Underneath everything", "Oil over oil over oil", "001.12",
		"From the Italian for repentance: a painter's change of mind, showing through. This one is large. The museum has not decided which version it acquired.")
	_checkpoint(A, "pentimento", Vector3(0, 0, -349), Vector3(0, 0, -1))
	# the ground around a crack where the figure stands
	arena_mat = (_mat("primed") as StandardMaterial3D).duplicate()
	var parts := [[-34, -351, 34, -380], [-34, -390, 34, -419], [-34, -380, -5, -390], [5, -380, 34, -390]]
	for i in parts.size():
		var b: Array = parts[i]
		var g := _ground(A, "Ground_%d" % i, b[0], b[1], b[2], b[3])
		(g.get_node("Visual") as MeshInstance3D).material_override = arena_mat
	figure = _block(A, "Figure", C + Vector3(-4, -40, 4), C + Vector3(4, 22, -4), "figure")
	# six hills, pivoting at the rim, heaving; the seals of the earlier layers ride on them
	for k in 6:
		var a := k * TAU / 6.0
		var rim := C + Vector3(sin(a), 0, cos(a)) * PENT_R
		var xf := Transform3D(Basis.looking_at((C - rim).normalized(), Vector3.UP), rim)
		var holder := _area(A + "/Hill_%d" % k)
		var st: Node3D = canvas.add(Stroke.make("hill_%d" % k, [Vector3(0, 0.25, 0), Vector3(0, 2.8, -11), Vector3(0, 5.5, -22)], "umber", 2.0, {"oneway": true}), holder)
		st.set_meta(&"unsafe", true)
		st.transform = xf
		hills.append([st, xf, k])
	for layer in LAYERS:
		var row: Array = []
		for j in 3:
			var k := (j * 2 + layer) % 6
			var h: Node3D = hills[k][0]
			var sd: Node3D = canvas.add(Stroke.make("seal_%d_%d" % [layer, k], [Vector3(2.4, 4.4, -19.4), Vector3(2.4, 4.4, -21.6)], "fury", 1.5,
				{"up": true, "t": 0.5, "k": "seal", "hidden": true}), h)
			row.append(sd)
		seals.append(row)
	pts["rim"] = Vector3(0, 0, -349)


func _hill_start(k: int) -> Vector3:
	var a := k * TAU / 6.0
	return PENT_C + Vector3(sin(a), 0, cos(a)) * (PENT_R + 0.6)


func _in_arena(p: Vector3) -> bool:
	return absf(p.x - PENT_C.x) < 36.0 and absf(p.z - PENT_C.z) < 36.0


func _pent_tick(delta: float) -> void:
	pent_t += delta
	var amp := 0.0 if pent >= LAYERS else 0.05 + 0.025 * pent
	for h: Array in hills:
		var st: Node3D = h[0]
		var th := amp * sin(pent_t * 0.6 + float(h[2]) * 1.1)
		st.transform = (h[1] as Transform3D) * Transform3D(Basis(Vector3.RIGHT, th), Vector3.ZERO)
	if _regrow > 0.0:
		_regrow -= delta
		if _regrow <= 0.0 and pent < LAYERS:
			for sd: Node3D in seals[pent]:   # an unfinished layer closes over again
				if not sd.enabled:
					canvas.removed.erase(sd.sid)
					canvas._reveal(sd)


func _show_layer() -> void:
	for layer in LAYERS:
		for sd: Node3D in seals[layer]:
			sd.set_enabled(layer == pent and not canvas.removed.has(sd.sid))


func _on_seal(_sd: Node3D) -> void:
	_sfx("seal", null, -2.0)
	if pent >= LAYERS:
		return
	var left := 0
	for sd: Node3D in seals[pent]:
		if sd.enabled:
			left += 1
	if left > 0:
		if _regrow <= 0.0:
			_regrow = REGROW
		return
	_regrow = -1.0
	pent += 1
	store("pent", pent)
	_nudge_mood(0.08)
	Game.player.add_trauma(0.45)
	_sfx("buckle", null, 0.0)
	_apply_pent(false)
	_show_layer()
	if pent >= LAYERS:
		complete_step(&"edge", &"pentimento")


## Each layer removed sinks the figure and warms the ground; the last restores the kinder world.
func _apply_pent(instant: bool) -> void:
	var y := -9.0 - float(pent) * 7.0
	var warm := Color("efe9dc").lerp(Color("cfe6b0"), float(pent) / LAYERS)
	if instant:
		figure.position.y = y
		arena_mat.albedo_color = warm
	else:
		var t := create_tween().set_parallel()
		t.tween_property(figure, "position:y", y, 3.0).set_trans(Tween.TRANS_SINE)
		t.tween_property(arena_mat, "albedo_color", warm, 3.0)
	if pent >= LAYERS:
		for id: String in ["kinder_road", "kinder_road_home", "pear"]:
			var st: Node3D = canvas.get_stroke(id)
			if st and not st.enabled:
				if instant:
					st.set_enabled(true)
				else:
					canvas._reveal(st)
		var tree: Node3D = canvas.get_stroke("old_tree")
		if tree and tree.colour == "umber":
			tree.set_colour("blue")


# --- The edge and the museum wall (the jaw-drop) -----------------------------------------------------

func _build_edge() -> void:
	var A := "Horizon"
	_stroke(A, "horizon_1", [Vector3(8, 24.65, -171.5), Vector3(-60, 24.65, -171.5)], "blue")
	_stroke(A, "horizon_2", [Vector3(-65, 23.35, -171.5), Vector3(-130, 23.35, -171.5)], "blue")
	_stroke(A, "horizon_3", [Vector3(-135, 22.05, -171.5), Vector3(-205, 22.05, -171.5)], "blue")
	# the kinder road (after the Pentimento): rim to the Old Tree, then on home to the grove
	_stroke(A, "kinder_road", [Vector3(6, 0.25, -349), Vector3(6, 3, -338), Vector3(6, 3, -200), Vector3(4, 1.0, -178)], "blue", 2.0, {"hidden": true})
	_stroke(A, "kinder_road_home", [Vector3(-8, 0.75, -160), Vector3(-8, 3, -150), Vector3(-8, 3, -62), Vector3(-8, 0.25, -50)], "blue", 2.0, {"hidden": true})
	var E := "CanvasEdge"
	_ground(E, "Plateau", -203, -150, -240, -190, 21.6)
	_checkpoint(E, "edge", Vector3(-214, 21.6, -171.5), Vector3(-1, 0, 0))
	_zone(E, Vector3(-203, 20, -150), Vector3(-240, 26, -190), func() -> void: complete_step(&"edge", &"horizon"))
	_post(E, Vector3(-222, 21.6, -165), Vector3(1, 0, 0), "The edge", "Present", "Tacking margin, unprimed", "001.13",
		"Where the painting stops and the canvas turns around the stretcher. Visitors are reminded that the edge is part of the work, and that the work ends at the edge.")
	# compression: a low, dark, turning passage over the stretcher bar
	var T := "CanvasEdge/Passage"
	_ground(T, "Floor1", -240, -168.7, -252.6, -171.3, 21.6, "crust")
	_ground(T, "Floor2", -250, -171.3, -252.6, -180, 21.6, "crust")
	_ground(T, "Floor3", -250, -177.4, -262, -180, 21.6, "crust")
	var walls := [
		[Vector3(-240, 21.6, -168.4), Vector3(-252.9, 24.2, -168.7)],
		[Vector3(-240, 21.6, -171.3), Vector3(-250, 24.2, -171.6)],
		[Vector3(-252.6, 21.6, -168.4), Vector3(-252.9, 24.2, -177.4)],
		[Vector3(-249.7, 21.6, -171.3), Vector3(-250, 24.2, -180.3)],
		[Vector3(-250, 21.6, -180), Vector3(-262, 24.2, -180.3)],
		[Vector3(-252.6, 21.6, -177.1), Vector3(-262, 24.2, -177.4)],
		[Vector3(-240, 24.2, -168.4), Vector3(-262, 24.6, -180.3)]]
	for i in walls.size():
		_block(T, "Wall_%d" % i, walls[i][0], walls[i][1], "weave")
	_block(T, "Stretcher", Vector3(-254, 24.6, -150), Vector3(-256, 26.6, -200), "crust")
	# the frame's gilt top edge and its staples, then the museum wall and a moulding ledge
	var M := "MuseumWall"
	for i in 6:
		_prop(M, "Staple_%d" % i, Vector3(-259.5, 21.65, -176.6 - i * 0.7), Vector3(0.6, 0.05, 0.08), "museum")
	_block(M, "GiltTop", Vector3(-261, 21.6, -150), Vector3(-262, 21.9, -205), "frame")
	_block(M, "WallNorth", Vector3(-262, -94, 0), Vector3(-264, 80, -177.4), "wall")
	_block(M, "WallSouth", Vector3(-262, -94, -180), Vector3(-264, 80, -400), "wall")
	_block(M, "WallBelow", Vector3(-262, -94, -177.4), Vector3(-264, 21.6, -180), "wall")
	_block(M, "WallAbove", Vector3(-262, 24.2, -177.4), Vector3(-264, 80, -180), "wall")
	_ground(M, "Ledge", -264, -170, -271, -187, 21.6, "museum")
	_block(M, "Floor", Vector3(-264, -96, 0), Vector3(-430, -94, -400), "museum", false)
	_block(M, "FarWall", Vector3(-350, -94, 0), Vector3(-352, 80, -400), "wall", false)
	_zone(M, Vector3(-264, 20, -170), Vector3(-271, 26, -187), _reveal_hall)
	_post(M, Vector3(-266, 21.6, -172), Vector3(-1, 0, 0), "Gallery wall, east", "Permanent collection", "Plaster, gilt, thirty storeys", "001.14",
		"Every acquisition hangs here. One frame is reserved. Its label was printed before the work was acquired, which is standard practice, and before the artist was born, which is not.")
	_build_frames(M)
	# the fragment: the first stroke, lifted from where the painter began
	var root := Node3D.new()
	root.name = "FragmentSpot"
	root.position = Vector3(-268.5, 22.4, -181)
	_area(M).add_child(root)
	var mi := MeshInstance3D.new()
	mi.name = "Visual"
	var bm := BoxMesh.new()
	bm.size = Vector3(0.25, 0.12, 0.9)
	mi.mesh = bm
	mi.material_override = Stroke.mat_for("red")
	root.add_child(mi)
	var pk := Pickup.new()
	pk.name = "Pickup"
	pk.kind = &"fragment"
	pk.item_id = W_ID
	pk.visual = mi
	pk.prompt = "Lift the first stroke"
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(1, 1, 1.4)
	cs.shape = sh
	pk.add_child(cs)
	root.add_child(pk)
	pk.picked.connect(_start_heist)
	uses["fragment"] = pk
	pts["lookout"] = Vector3(8, 24.4, -171.5)
	pts["plateau"] = Vector3(-214, 21.6, -171.5)
	pts["passage"] = [Vector3(-245, 21.6, -170), Vector3(-251.3, 21.6, -170), Vector3(-251.3, 21.6, -178.7), Vector3(-262.5, 21.6, -178.7)]
	pts["ledge"] = Vector3(-266.5, 21.6, -178.7)
	pts["fragment"] = root.position


## Every wing hangs on the far wall as a frame; one more frame is empty, and its label is hers.
func _build_frames(area: String) -> void:
	var ex: Array[WingInfo] = Game.registry.exhibits()
	var n := ex.size() + 1
	for i in n:
		var z := -178.0 + (float(i) - (n - 1) * 0.5) * 18.0
		var c := Vector3(-349.5, 18.0, z)
		var mine := i == ex.size()
		_prop(area, "Frame_%d" % i, c, Vector3(0.6, 13, 13), "frame")
		var pane := _prop(area, "Canvas_%d" % i, c + Vector3(0.4, 0, 0), Vector3(0.3, 11, 11), "wall")
		if not mine and ex[i].palette.size() > 0:
			var m := StandardMaterial3D.new()
			m.albedo_color = ex[i].palette[0]
			pane.material_override = m
		var pl: Placard
		if mine:
			pane.visible = false
			pl = _placard(area, c + Vector3(0.7, -8, 0), Vector3(1, 0, 0), "Vesper", "Not yet", "Mixed media", "Reserved",
				"Frame reserved. Work in progress. The museum is confident.")
		else:
			pl = _placard(area, c + Vector3(0.7, -8, 0), Vector3(1, 0, 0), ex[i].title, "", "", ex[i].acquisition_no, "")
		pl.scale = Vector3.ONE * 4.0


func _reveal_hall() -> void:
	if revealed:
		return
	revealed = true
	store("revealed", true)
	var path := SND + "reveal.ogg"
	if ResourceLoader.exists(path):
		Audio.reveal(load(path), 4.0)


# --- The heist: one long branching stroke home, drying behind her ----------------------------------

func _build_heist() -> void:
	var A := "Heist"
	var h := {"hidden": true}
	_stroke(A, "heist_0", [Vector3(-215, 21.85, -168), Vector3(-185, 19.5, -162), Vector3(-150, 15, -150)], "blue", 2.0, h)
	_stroke(A, "heist_red_1", [Vector3(-150, 15, -150), Vector3(-125, 13, -130), Vector3(-100, 12, -112)], "red", 2.0, h)
	_stroke(A, "heist_red_2", [Vector3(-94.5, 10.5, -108), Vector3(-70, 9, -88), Vector3(-40, 6, -62)], "red", 2.0, h)
	_stroke(A, "heist_blue_1", [Vector3(-150, 15, -150), Vector3(-120, 13.5, -152), Vector3(-90, 12, -140), Vector3(-70, 10, -115), Vector3(-55, 8, -90), Vector3(-40, 6, -62)], "blue", 2.0, h)
	_stroke(A, "heist_final", [Vector3(-40, 6, -62), Vector3(-20, 3.5, -30), Vector3(0, 1.5, -10), Vector3(0, 0.75, 2)], "blue", 2.0, h)
	for id: String in HEIST_IDS:
		(canvas.get_stroke(id) as Node3D).set_meta(&"unsafe", true)
	var L0: float = canvas.get_stroke("heist_0").length
	var L1: float = canvas.get_stroke("heist_red_1").length
	var L2: float = canvas.get_stroke("heist_red_2").length
	heist_nominal = {"heist_0": 0.0, "heist_red_1": L0, "heist_blue_1": L0, "heist_red_2": L0 + L1 + 7.0, "heist_final": L0 + L1 + 7.0 + L2}
	# varnish knots on the long blue way and on the last run: jump them
	for k: Array in [["heist_blue_1", 30.0], ["heist_blue_1", 75.0], ["heist_final", 20.0]]:
		var st: Node3D = canvas.get_stroke(k[0])
		var at: Vector3 = st.sample(k[1])
		var n := _prop(A, "Knot_%s_%d" % [k[0], int(k[1])], at + Vector3(0, 0.35, 0), Vector3(1.6, 0.7, 0.7), "crust")
		var m := StandardMaterial3D.new()
		m.albedo_color = Color("c98a1e")
		n.material_override = m
		n.visible = false
		knots.append([st, float(k[1]), n])
	_post("PrimedShore", Vector3(6, 0, 10), Vector3(-0.5, 0, -1), "The first stroke, removed", "Today", "Absence, in oil", "001.15",
		"The canvas is now one stroke less finished than it was. The painter's mood is recorded in the sky. The sky has been recorded.")
	pts["heist_start"] = Vector3(-213, 21.6, -168)


func _start_heist() -> void:
	store("heist", true)
	_open_heist()


func _open_heist() -> void:
	heist = true
	heist_t = -1.0
	heist_stage = 0
	heist_ridden.clear()
	for id: String in HEIST_IDS:
		var st: Node3D = canvas.get_stroke(id)
		st.set_dry(0.0)
		st.set_enabled(true)
	for k: Array in knots:
		(k[2] as Node3D).visible = true


func _heist_tick(delta: float) -> void:
	var p := Game.player
	var on: Node3D = surf.stroke if p.mode == surf and is_instance_valid(surf.stroke) else null
	if heist_t < 0.0:
		if on and on.sid in HEIST_IDS:
			heist_t = 0.0
			heist_m0 = surf.metres
		else:
			return
	heist_t += delta
	var me := surf.metres - heist_m0
	if on and on.sid in HEIST_IDS and not heist_ridden.has(on.sid):
		heist_ridden[on.sid] = me - (surf.s if surf.dir > 0.0 else on.length - surf.s)
		if on.sid != "heist_0":
			heist_stage = 1
	# the drying front follows her along the route at DRY_SPEED after a grace
	var front := (heist_t - DRY_GRACE) * DRY_SPEED
	for id: String in HEIST_IDS:
		var st: Node3D = canvas.get_stroke(id)
		var start: float = heist_ridden.get(id, heist_nominal[id])
		var v := clampf((front - start) / st.length, 0.0, 0.99)
		if front > start + st.length:
			v = 1.0 if front < start + st.length + 25.0 else 2.0
		if on == st and front > me:
			v = 1.0   # it caught her: the stroke hardens under her feet
		if v > st.dry:
			st.set_dry(v)
	# knots knock her off unless she jumps them
	if on:
		for k: Array in knots:
			if k[0] == on and absf(surf.s - float(k[1])) < 0.8:
				surf._leave(p.velocity * 0.2 + Vector3.UP * 2.0, false)
				_sfx("refuse", null, 0.0)
				break


func _heist_respawn() -> Transform3D:
	var stage := heist_stage
	_open_heist()
	if stage >= 1:
		var st: Node3D = canvas.get_stroke("heist_0")
		var s0: float = st.length - 12.0
		heist_stage = 1
		var t: Vector3 = st.tangent(s0)
		return Transform3D(Basis(Vector3.UP, atan2(-t.x, -t.z)), st.sample(s0) + Vector3.UP * 0.1)
	return Transform3D(Basis(Vector3.UP, PI * 0.5 - 0.2), pts["heist_start"] + Vector3.UP * 0.1)


func _on_home() -> void:
	if heist and Quest.has_fragment(W_ID):
		heist = false
		store("heist", false)
		finish()


# --- shot marks --------------------------------------------------------------------------------------

func _build_marks() -> void:
	_mark("01_shore", Vector3(4, 2.2, 10), Vector3(0, 0.5, -30))
	_mark("02_bough", Vector3(5, 3, -14), Vector3(0, 0, -40))
	_mark("03_chain", Vector3(8, 4, -60), Vector3(0, -2, -125))
	_mark("04_crown", Vector3(-8, 4, -128), Vector3(0, 0.5, -146))
	_mark("05_unpainted", Vector3(-12, 3, -172), Vector3(-50, 0, -170))
	_mark("06_river", Vector3(-10, 4, -184), Vector3(10, -0.3, -204))
	_mark("07_basin", Vector3(22, 5, -212), Vector3(50, -2, -235))
	_mark("08_source", Vector3(96, 2.5, -230), Vector3(132, 0, -228))
	_mark("09_corrections", Vector3(-25, 4, -276), Vector3(0, 2, -305))
	_mark("10_pentimento", Vector3(0, 6, -347), PENT_C + Vector3(0, 8, 0))
	_mark("11_horizon", Vector3(0, 27, -160), Vector3(-120, 22, -171.5))
	_mark("12_museum_wall", Vector3(-268, 23.2, -176), Vector3(-350, 10, -178))


# --- per-tick, falls, progress ----------------------------------------------------------------------

func _tick(delta: float) -> void:
	_pent_tick(delta)
	if heist:
		_heist_tick(delta)
	if canvas.water_level("basin") < -2.0 and not Quest.is_step_done(&"river", &"dam"):
		complete_step(&"river", &"dam")
	if Engine.get_physics_frames() % 240 == 0:
		Audio.set_intensity(clampf(mood_shown * 0.6 + float(pent) * 0.13, 0.0, 1.0), 4.0)


func _respawn_point() -> Transform3D:
	var p := Game.player.global_position
	if heist:
		return _heist_respawn()
	if pent < LAYERS and _in_arena(p):
		return find_checkpoint(&"pentimento").global_transform
	return _safe_point()


func _on_respawned() -> void:
	pass


func _apply_progress() -> void:
	pent = int(recall("pent", 0))
	revealed = bool(recall("revealed", false))
	_show_layer()
	_apply_pent(true)
	if Quest.is_step_done(&"river", &"light"):
		(canvas.get_stroke("outflow") as Node3D).set_enabled(true)
	if Quest.has_fragment(W_ID):
		var f := areas.get_node_or_null("MuseumWall/FragmentSpot")
		if f:
			f.queue_free()
		_open_heist()


