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
	canvas.burned.connect(func(_id: String) -> void: _sfx("burn", null, -2.0))
	canvas.refused.connect(func(_w: String) -> void: _sfx("refuse", null, -10.0))
	canvas._refresh()


## Overridden by the world builder further down; kept separate so the course exists alone.
func _build_world() -> void:
	pass


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


func _on_blended(_a: Node3D, _b: Node3D, _c: String) -> void:
	_sfx("blend", null, -3.0)


func _on_surf(ev: String, data: Variant) -> void:
	match ev:
		"board":
			_sfx("board", Game.player.global_position, -6.0, 0.9 + 0.05 * surf.chain)
			if surf.chain >= 2:
				_nudge_mood(0.006 * minf(surf.chain, 5))
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


## Per-area logic; the world builder overrides it.
func _tick(_delta: float) -> void:
	pass


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
		_last_safe = surf.stroke.sample(surf.s)
		_last_safe_stroke = surf.stroke
		_last_safe_yaw = p.yaw
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


## Where a fall returns her (the set-piece and heist override this to their checkpoints).
func _respawn_point() -> Transform3D:
	return _safe_point()


func _on_respawned() -> void:
	pass


func _apply_progress() -> void:
	pass
