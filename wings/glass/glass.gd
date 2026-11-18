extends Wing
## THE VITRINE KINGDOM — Acq. No. 214, "For the Light Alone".
## A kingdom glazed entire. Its one rule is LIGHTWALKING (optics.gd): coloured light is solid.
##
## Route (−Z is east, toward the altar):
##   Cloister (spawn, one beam, one dial) → Nave (a clockwork dial and a mirror schedule light across
##   the abyss) → Choir → Crypt (a prism splits white; mirrors and a lens recombine it; colour-keyed
##   gates; three saints turned face-up) → glass passage → Tower stair → Roof (THE SKY IS ONE WINDOW,
##   and something leans in) → the Rose Widow's hall (set-piece) → north triforium → Choir lens →
##   the east window shatters (the wind never stops; the way home seals) → heist along dying beams.
##
## The whole level is built in code from the coordinates below so the optics line up by
## construction (receptors are placed along the prism's actual output directions).

const Dial := preload("res://wings/glass/dial.gd")
const LightwalkMode := preload("res://wings/glass/lightwalk_mode.gd")
const RoseWidow := preload("res://wings/glass/rose_widow.gd")
const MATS := "res://wings/glass/materials/"
const SND := "res://wings/glass/audio/"
const MODELS := "res://wings/glass/models/"

const HALL := Vector3(-60, 14, -95)
const PRISM_O := Vector3(0, -7.88, -92)
const LENS_POS := Vector3(0, 2.75, -100.7)
const EAST_AIM := Vector3(0, 6.22, -120.8)
const HEIST_DEADLINES := [9.0, 15.0, 21.0, 27.0]

var optics: GlassOptics
var geo: Node3D
var M: Dictionary = {}
## Test- and cinematic-facing handles: interactables and named points by id.
var uses: Dictionary = {}
var pts: Dictionary = {}
var dials: Dictionary = {}
var _walked_light := false  # she has stood on a beam once: the "walk on the light" prompt retires
var mirrors: Dictionary = {}
var receptors: Dictionary = {}
var srcs: Dictionary = {}
var windows: Dictionary = {}   # id -> ShaderMaterial
var prism: GlassOptics.Prism
var lens_crypt: GlassOptics.Lens
var lens_choir: GlassOptics.Lens
var rose: RoseWidow
var sky_mat: ShaderMaterial
var env: Environment
var shattered: bool = false
var heist_on: bool = false
var heist_t: float = 0.0
var lantern_carried: bool = false

var _gates: Dictionary = {}     # id -> Node3D (solid gate)
var _west_door: Node3D
var _fragment: Pickup
var _frag_spot: Node3D
var _hand_lantern: Node3D
var _lens_lantern: Node3D
var _rose_lights: Array = []
var _east_mesh: MeshInstance3D
var _wind_fx: GPUParticles3D
var _last_pos: Vector3 = Vector3.INF
var _music_now: StringName = &""
var _reliquary_lid: Node3D
var _prov_spots: Dictionary = {}
var _sconce_lights: Array = []
var _sun: DirectionalLight3D
var _rose_pane_mat: ShaderMaterial
var _lantern_glow: OmniLight3D
var _heist_dark: float = 0.0
var _onlooker: MeshInstance3D
var _eye_dir := Vector3(-0.39, 0.8, -0.92).normalized()
var _onlooker_mat: ShaderMaterial
var _reveal_t0: float = 0.0

const AMBIENT := 0.7


# =============================================================================================
# Wing contract

func objectives() -> Array[Dictionary]:
	return [
		{"id": "light", "title": "Let the light into the nave", "steps": [
			{"id": "cloister_dial", "title": "Bridge the cloister with the sun-dial"},
			{"id": "clockwork", "title": "Ride the clockwork across the nave"},
			{"id": "choir", "title": "Reach the choir"}],
			"hint": "Interact with a dial to turn its beam. A beam you can see is a beam you can stand on."},
		{"id": "saints", "title": "Turn the saints face-up", "steps": [
			{"id": "azure", "title": "Saint Azure (blue)"},
			{"id": "ruby", "title": "Saint Ruby (red, behind the gold gate)"},
			{"id": "verdance", "title": "Saint Verdance (green: gold and blue together)"}],
			"hint": "Under the choir grate a prism splits white light. Each face-down pane wants exactly its own colour."},
		{"id": "east", "title": "Unglaze the Curator's window", "steps": [
			{"id": "widow", "title": "Cross the Rose Widow's hall"},
			{"id": "lens", "title": "Set her lantern in the choir lens"},
			{"id": "shatter", "title": "Light the east window with every saint at once"}],
			"hint": "The roof is reached from the crypt passage. Ruby, Azure and Verdance together make white."},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "face", "name": "The face of St. Lumen, leaded out", "line": "Removed in the re-glazing. She is still smiling at the miracle she was cut from."},
		{"id": "veil", "name": "A thread of the Widow's veil", "line": "Violet. Kept in a reliquary that opens only to the colours of mourning."},
		{"id": "iron", "name": "A glazier's grozing iron", "line": "Left on the roof by whoever re-leaded the sky. The handle is worn to the shape of a much larger hand."},
	]


func fragment() -> Dictionary:
	return {"name": "The fourth sun", "line": "A pane of the sky. Where it was, the onlooker's loupe has nothing left to look through but the hole."}


func register_modes(player: Player) -> void:
	var lw := LightwalkMode.new()
	lw.wind = _wind_at
	player.add_mode(&"lightwalk", lw)
	var steps: Array[AudioStream] = []
	for i in range(1, 7):
		steps.append(load(SND + "step_glass_%d.ogg" % i))
	Audio.register_footsteps(&"glass", steps)


func save_state() -> Dictionary:
	return {"lantern": lantern_carried}


func on_exit() -> void:
	get_tree().root.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED  # the next wing's Quality.apply restores MSAA
	RenderingServer.gi_set_use_half_resolution(false)


func on_enter(first_time: bool) -> void:
	# MSAA cost ~4 ms at 1440p here; SMAA keeps the lead lines clean for a fraction of that.
	var vp := get_tree().root
	if vp.msaa_3d != Viewport.MSAA_DISABLED:
		vp.msaa_3d = Viewport.MSAA_DISABLED
		vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_SMAA
	# SDFGI budget: half-res GI, fewer rays, light re-lit over more frames (the light here is static)
	RenderingServer.gi_set_use_half_resolution(true)
	RenderingServer.environment_set_sdfgi_ray_count(RenderingServer.ENV_SDFGI_RAY_COUNT_16)
	RenderingServer.environment_set_sdfgi_frames_to_update_light(RenderingServer.ENV_SDFGI_UPDATE_LIGHT_IN_8_FRAMES)
	_apply_progress()
	_last_pos = Game.player.global_position
	_music_for(Game.player.global_position)
	if first_time:
		await Cinematics.play([
			{"card": "For the light alone", "sub": "The Vitrine Kingdom. Acq. no. 214", "t": 4.0, "style": "display"},
		])
		toast("Lightwalking: coloured light here is solid. Turn the sun-dial to lay a beam across the gap.", "The Vitrine Kingdom")


# =============================================================================================
# Build

func _ready() -> void:
	geo = Node3D.new()
	geo.name = "Geometry"
	add_child(geo)
	optics = GlassOptics.new()
	optics.name = "Optics"
	add_child(optics)
	for n: String in ["glass_wall", "glass_floor", "glass_quarry", "glass_crypt", "glass_gold", "glass_red", "lead", "silver", "brass", "museum_white", "ember", "glazed_nave", "glazed_cloister", "glazed_tower", "glazed_ruby", "crypt_floor"]:
		M[n] = load(MATS + n + ".tres")
	_build_environment()
	_build_shot_marks()
	_build_cloister()
	_build_nave()
	_build_choir()
	_build_crypt()
	_build_passage_and_tower()
	_build_roof()
	_build_rose()
	_build_east_and_heist()
	_build_provenances()
	_build_checkpoints()
	_merge_static()
	# one reflection probe per area, captured once: polished glass floors mirror the windows
	for p: Array in [[Vector3(0, 4, 0), Vector3(37, 12, 37), false], [Vector3(0, 10, -69), Vector3(32, 30, 104), true],
			[Vector3(0, -3, -102), Vector3(31, 11, 41), true], [HALL + Vector3(0, 8, 0), Vector3(58, 34, 58), false],
			[Vector3(-22, 5, -24), Vector3(13, 28, 13), true]]:
		var rp := ReflectionProbe.new()
		rp.position = p[0]
		rp.size = p[1]
		rp.box_projection = true
		rp.interior = p[2]
		rp.update_mode = ReflectionProbe.UPDATE_ONCE
		rp.max_distance = 120.0
		geo.add_child(rp)


## ~1000 code-built boxes would be ~1000 draw calls. Bake the ones nothing refers to into one mesh per
## material per 24 m cell (cells keep frustum culling useful). Colliders stay where they were.
func _merge_static() -> void:
	var keep := [_west_door, _reliquary_lid]
	keep.append_array(_gates.values())
	var groups := {}
	for n: Node in geo.get_children():
		var mi := n as MeshInstance3D
		if mi == null or not mi.mesh is BoxMesh or not mi.visible or mi in keep:
			continue
		var c := (mi.global_position / 24.0).floor()
		var key := [mi.material_override, c]
		if not groups.has(key):
			groups[key] = []
		groups[key].append(mi)
	for key: Array in groups:
		var st := SurfaceTool.new()
		for mi: MeshInstance3D in groups[key]:
			st.append_from(mi.mesh, 0, mi.global_transform)
			for ch: Node in mi.get_children():
				ch.reparent(geo)
			mi.queue_free()
		var out := MeshInstance3D.new()
		out.mesh = st.commit()
		out.material_override = key[0]
		geo.add_child(out)


func _build_environment() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://wings/glass/shaders/sky_window.gdshader")
	sky_mat.set_shader_parameter(&"dome", load("res://wings/glass/textures/sky_rose.png"))
	_onlooker = MeshInstance3D.new()
	var oq := QuadMesh.new()
	oq.size = Vector2(1.32, 1.0) * 200.0  # ~a third of the sky at 300 m
	_onlooker.mesh = oq
	_onlooker_mat = ShaderMaterial.new()
	_onlooker_mat.shader = load("res://wings/glass/shaders/onlooker.gdshader")
	_onlooker_mat.set_shader_parameter(&"face", load("res://wings/glass/textures/onlooker_face.png"))
	_onlooker.material_override = _onlooker_mat
	_onlooker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_onlooker.visible = false
	add_child(_onlooker)
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
	env.sky = sky
	# Value first: the interior is near-black; colour lives in the windows and the light they throw.
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.16, 0.2, 0.36)
	env.ambient_light_energy = AMBIENT
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 10.0
	env.tonemap_exposure = 2.1
	# window emission and the colour it throws fill the rooms (bounce); lead stays black
	env.sdfgi_enabled = true
	env.sdfgi_cascades = 3
	env.sdfgi_min_cell_size = 0.6
	env.sdfgi_use_occlusion = false
	env.sdfgi_energy = 1.4
	env.sdfgi_read_sky_light = false
	env.ssr_enabled = true
	env.ssr_max_steps = 32
	env.ssr_fade_in = 0.1
	env.ssr_fade_out = 2.0
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 1.6   # only windows, beams and suns bloom
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.set_glow_level(0, 0.0)
	env.set_glow_level(1, 0.0)
	env.set_glow_level(2, 1.0)
	env.set_glow_level(3, 0.6)
	env.set_glow_level(4, 0.4)
	env.ssao_enabled = false  # glass is lit from behind; SSAO cost ~13 ms at 1440p for no visible gain
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.009
	env.volumetric_fog_albedo = Color(0.6, 0.62, 0.7)
	env.volumetric_fog_emission = Color(0.002, 0.003, 0.01)
	env.volumetric_fog_anisotropy = 0.7
	env.volumetric_fog_length = 70.0
	env.volumetric_fog_ambient_inject = 0.0
	env.volumetric_fog_sky_affect = 0.15
	# grade: clean. No fringe, no grain: the glass is the texture.
	grade = PostGrade.new()
	grade.tint = Color(1.0, 0.99, 1.02)
	grade.lift = Color(0.004, 0.005, 0.014)
	grade.saturation = 1.3
	grade.contrast = 1.08
	grade.aberration = 0.0
	grade.vignette = 0.55
	grade.grain = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	# The sun only matters out on the roof and the heist: it is switched on there (see _process).
	_sun = DirectionalLight3D.new()
	_sun.name = "Sun"
	_sun.light_color = Color("ffe2a8")
	_sun.light_energy = 1.3
	_sun.shadow_enabled = true
	_sun.directional_shadow_max_distance = 50.0
	_sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	_sun.light_volumetric_fog_energy = 0.6
	add_child(_sun)
	_sun.look_at_from_position(Vector3.ZERO, Vector3(-0.35, -0.55, 0.76), Vector3.UP)


## Beauty-shot marks for tests/shots.tscn (--wing=glass). Stateful views (sky reveal, Rose phases,
## heist) are shot by wings/glass/tests/shots.tscn, which sets those states first.
func _build_shot_marks() -> void:
	var root := Node3D.new()
	root.name = "ShotMarks"
	add_child(root)
	for m: Array in [
			["cloister", Vector3(1.0, 1.7, 15.5), Vector3(14.2, 0.4, 0.0)],
			["nave", Vector3(0.0, 1.7, -21.0), Vector3(0.0, 4.0, -70.0)],
			["choir", Vector3(0.0, 4.2, -84.0), Vector3(0.0, 8.0, -110.0)],
			["crypt", Vector3(-6.0, -6.2, -86.0), Vector3(2.0, -7.6, -100.0)],
			["tower", Vector3(-17.2, 9.6, -19.0), Vector3(-26.0, 14.0, -26.0)],
			["rooftops", Vector3(-17.0, 17.6, -55.0), Vector3(-24.3, 18.0, -68.0)],
			["rose_hall", HALL + Vector3(25.5, 1.7, 0.0), HALL + Vector3(-27.0, 10.0, 0.0)],
			["east_window", Vector3(0.0, 3.4, -97.5), Vector3(0.0, 13.0, -121.0)]]:
		var mk := Marker3D.new()
		mk.name = m[0]
		root.add_child(mk)
		mk.look_at_from_position(m[1], m[2], Vector3.UP)


# --- primitives --------------------------------------------------------------------------------

func _block(a: Vector3, b: Vector3, mat: String, solid: bool = true, parent: Node3D = null) -> MeshInstance3D:
	var lo := a.min(b)
	var hi := a.max(b)
	var size := hi - lo
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = M[mat]
	mi.position = (lo + hi) * 0.5
	(parent if parent else geo).add_child(mi)
	if solid:
		_solid(mi, size)
	return mi


func _solid(mi: Node3D, size: Vector3) -> StaticBody3D:
	var sb := StaticBody3D.new()
	sb.collision_layer = 1
	sb.collision_mask = 0
	sb.set_meta(&"surface", "glass")
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	sb.add_child(cs)
	mi.add_child(sb)
	return sb


## A slab whose top centre-line runs from a to b.
func _ramp(a: Vector3, b: Vector3, w: float, mat: String, solid: bool = true) -> MeshInstance3D:
	var d := b - a
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(w, 0.4, d.length())
	mi.mesh = bm
	mi.material_override = M[mat]
	var basis := Basis.looking_at(d.normalized(), Vector3.UP)
	mi.transform = Transform3D(basis, (a + b) * 0.5 - basis.y * 0.2)
	geo.add_child(mi)
	if solid:
		_solid(mi, bm.size)
	return mi


func _light(pos: Vector3, col: Color, energy: float, rng: float, parent: Node3D = null) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.light_color = col
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.2
	l.position = pos
	(parent if parent else geo).add_child(l)
	return l


func _spot(from: Vector3, to: Vector3, col: Color, energy: float, angle: float, rng: float) -> SpotLight3D:
	var s := SpotLight3D.new()
	s.light_color = col
	s.light_energy = energy
	s.spot_angle = angle
	s.spot_range = rng
	s.light_volumetric_fog_energy = 3.0
	geo.add_child(s)
	s.look_at_from_position(from, to, Vector3.UP if absf(from.direction_to(to).y) < 0.98 else Vector3.FORWARD)
	return s


## A modelled lancet: pane (its own art, 1:3.5) in a moulded lead frame with saddle bars, `w` wide,
## plus a projector spot outside throwing the same art in through it as coloured light.
func _lancet(id: String, centre: Vector3, w: float, facing: Vector3, tex: String, edited: float = 0.0, throw: Vector3 = Vector3.INF, energy: float = 6.0) -> MeshInstance3D:
	var mi := _window(id, centre, Vector2(w, w * 3.5), facing, tex, edited, "lancet_pane")
	var fr := _model("lancet_frame")
	mi.add_child(fr)  # inherits the pane's scale
	if throw != Vector3.INF:
		var from := centre - facing * 6.0 + Vector3(0, 6.0, 0)
		var s := _spot(from, throw, Color.WHITE, energy, 24.0, from.distance_to(throw) * 1.6)
		s.light_projector = load("res://wings/glass/textures/%s.png" % tex)
		s.spot_attenuation = 0.6
		s.light_volumetric_fog_energy = 2.0
		s.light_specular = 0.6
	return mi


func _window(id: String, centre: Vector3, size: Vector2, facing: Vector3, tex: String, edited: float = 0.0, mesh: String = "") -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	if mesh != "":
		mi.mesh = _mesh_of(mesh)
		mi.scale = Vector3(size.x, size.x, size.x) if mesh == "lancet_pane" else Vector3(size.x, size.y, size.x) * 0.5
	else:
		var q := QuadMesh.new()
		q.size = size
		mi.mesh = q
	var m := ShaderMaterial.new()
	m.shader = load("res://wings/glass/shaders/window.gdshader")
	m.set_shader_parameter(&"window_tex", load("res://wings/glass/textures/%s.png" % tex))
	m.set_shader_parameter(&"edited", edited)
	m.set_shader_parameter(&"dark", 0.0)
	m.set_shader_parameter(&"crack", 0.0)
	m.set_shader_parameter(&"energy", 2.6 if id == "east" else 3.4)  # the rest read richer than the sunlit east
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var sc := mi.scale
	geo.add_child(mi)
	mi.global_transform = Transform3D(Basis.looking_at(-facing, Vector3.UP if absf(facing.y) < 0.9 else Vector3.FORWARD).scaled_local(sc), centre)
	windows[id] = m
	return mi


func _model_mat(name: String) -> ShaderMaterial:
	return load("res://wings/glass/materials/%s.tres" % name)


## Transforms for parapet.glb modules (1.3 m along local X) laid end to end from a to b (level).
func _parapet_run(a: Vector3, b: Vector3) -> Array:
	var d := b - a
	var n := maxi(1, roundi(d.length() / 1.3))
	var step := d.length() / n
	var x := d.normalized()
	var basis := Basis(x * (step / 1.3), Vector3.UP, x.cross(Vector3.UP))
	var out: Array = []
	for i in n:
		out.append(Transform3D(basis, a + x * step * (i + 0.5)))
	return out


func _model(name: String) -> Node3D:
	var path := MODELS + name + ".glb"
	if not ResourceLoader.exists(path):
		return null
	var n: Node3D = (load(path) as PackedScene).instantiate()
	MaterialLib.apply(n, ["res://wings/glass/materials", MaterialLib.CORE_DIR])
	return n


func _mesh_of(name: String) -> Mesh:
	var n := _model(name)
	if n == null:
		return null
	var found := n.find_children("*", "MeshInstance3D", true, false)
	var mesh: Mesh = (found[0] as MeshInstance3D).mesh if not found.is_empty() else null
	n.free()
	return mesh


## Repeats of a modelled part as one MultiMesh (one draw per surface for every instance).
## `swap` renames Blender materials (e.g. the gold shaft glazed red).
func _mm(name: String, xforms: Array, swap: Dictionary = {}) -> MultiMeshInstance3D:
	var src := _mesh_of(name)
	if src == null or xforms.is_empty():
		return null
	var mesh: Mesh = src.duplicate()
	for i in mesh.get_surface_count():
		var sm := mesh.surface_get_material(i)
		if sm:
			var m := MaterialLib.lookup(swap.get(sm.resource_name, sm.resource_name), [MATS.trim_suffix("/"), MaterialLib.CORE_DIR])
			if m:
				mesh.surface_set_material(i, m)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = xforms.size()
	for i in xforms.size():
		mm.set_instance_transform(i, xforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	geo.add_child(mmi)
	return mmi


## A modelled clustered pier from y0 to y1 (colliders stay the code boxes). Capitals at `caps`.
func _pier_xf(out: Dictionary, base: Vector3, top: float, caps: Array, s: float = 1.0) -> void:
	var y := base.y
	if base.y >= -0.01:
		out["pier_base"].append(Transform3D(Basis.from_scale(Vector3.ONE * s), base))
		y += 0.62 * s
	out["pier_shaft"].append(Transform3D(Basis.from_scale(Vector3(s, top - y, s)), Vector3(base.x, y, base.z)))
	for c: float in caps:
		out["pier_capital"].append(Transform3D(Basis.from_scale(Vector3.ONE * s), Vector3(base.x, c - 0.72 * s, base.z)))


func _use(id: String, pos: Vector3, size: Vector3, prompt: String, cb: Callable, hold: float = 0.0) -> Interactable:
	var it := Interactable.make_box(size, prompt)
	it.position = pos
	it.hold_time = hold
	it.interacted.connect(func(_p: Player) -> void: cb.call())
	geo.add_child(it)
	uses[id] = it
	return it


func _catch(a: Vector3, b: Vector3) -> void:
	var tz := TriggerZone.make_box((b - a).abs(), false)
	tz.position = (a + b) * 0.5
	tz.triggered.connect(func(_p: Player) -> void: Game.respawn())
	add_child(tz)


## Local haze filling a pit, thickest at the bottom, so looking or falling into it shows depth.
func _haze(a: Vector3, b: Vector3) -> void:
	var fv := FogVolume.new()
	fv.size = (b - a).abs()
	fv.position = (a + b) * 0.5
	var fm := FogMaterial.new()
	fm.density = 0.25
	fm.albedo = Color(0.32, 0.4, 0.62)
	fm.emission = Color(0.03, 0.045, 0.09)
	fm.edge_fade = 0.3
	fv.material = fm
	geo.add_child(fv)
	# a floor of the haze's own colour under it: the background never shows through as a flat void
	var fl := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(fv.size.x + 20.0, fv.size.z + 20.0)  # past the walls' feet
	fl.mesh = pm
	var um := StandardMaterial3D.new()
	um.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	um.albedo_color = Color(0.07, 0.09, 0.16)
	fl.material_override = um
	fl.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	fl.position = Vector3(fv.position.x, a.y + 1.8, fv.position.z)
	geo.add_child(fl)


## The first time a beam is within a stride, say what to do with it; silent once she has stood on one.
func verb_prompt() -> Dictionary:
	var m: MovementMode = Game.player.mode if Game.player else null
	if m is LightwalkMode and not _walked_light:
		if (m as LightwalkMode).on_beam:
			_walked_light = true
		elif optics and optics.beam_near(Game.player.global_position, 2.5):
			return {"action": &"move_forward", "text": "walk on the light"}
	return super()


func _zone(a: Vector3, b: Vector3, cb: Callable, once: bool = true) -> TriggerZone:
	var tz := TriggerZone.make_box((b - a).abs(), once)
	tz.position = (a + b) * 0.5
	tz.triggered.connect(func(_p: Player) -> void: cb.call())
	add_child(tz)
	return tz


## Tombstone label: title; date; medium and acquisition number; one short paragraph.
func _placard(pos: Vector3, facing: Vector3, title: String, date: String, medium: String, acq: String, body: String) -> Placard:
	var p := Placard.new()
	geo.add_child(p)
	p.global_transform = Transform3D(Basis.looking_at(-facing, Vector3.UP), pos)
	p.set_label(Placard.fields(title, date, medium, "Acq. no. %s" % acq, body), false)
	return p


func _dial(id: String, pos: Vector3, aims: Array, mask: int, prompt: String, cycle: Array = []) -> Node3D:
	var d: Dial = Dial.new()
	d.id = id
	d.aims = aims
	d.cycle = cycle
	d.position = pos
	var model := _model("dial")
	if model == null:
		model = Node3D.new()
		var base := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.45
		cm.bottom_radius = 0.6
		cm.height = 0.5
		base.mesh = cm
		base.material_override = M["brass"]
		base.position.y = -0.1
		model.add_child(base)
	d.setup(optics, mask, model, prompt)
	geo.add_child(d)
	var lensv := MeshInstance3D.new()
	var lm := CylinderMesh.new()
	lm.top_radius = 0.28
	lm.bottom_radius = 0.28
	lm.height = 0.12
	lensv.mesh = lm
	lensv.rotation.x = PI / 2
	lensv.position.z = -0.35
	var gm := StandardMaterial3D.new()
	gm.albedo_color = GlassOptics.color(mask)
	gm.emission_enabled = true
	gm.emission = GlassOptics.color(mask)
	gm.emission_energy_multiplier = 3.0
	lensv.material_override = gm
	d.head.add_child(lensv)
	dials[id] = d
	uses[id] = d.interact
	return d


func _mirror(id: String, pos: Vector3, from: Vector3, targets: Array, index: int = 0, face: float = 1.1) -> GlassOptics.Mirror:
	var m := GlassOptics.Mirror.new()
	for t: Vector3 in targets:
		m.normals.append(GlassOptics.mirror_normal(pos, from, t))
	m.index = index
	m.position = pos
	optics.add_child(m)
	m.setup(Vector2(face, face))
	optics.add_element(m)
	var head := _model("mirror_head")
	head.scale = Vector3.ONE * face / 1.1
	m.head.add_child(head)
	var collar := _model("mirror_collar")
	collar.position.y = -0.11
	collar.scale = Vector3.ONE * face / 1.1
	m.add_child(collar)
	mirrors[id] = m
	_use(id, pos + Vector3(0, 0.3, 0), Vector3(1.4, 1.6, 1.4), "Turn the mirror", func() -> void:
		m.turn()
		Audio.sfx(load(SND + "mirror_turn.ogg"), pos, -3.0, 0.4, randf_range(0.95, 1.05)))
	return m


func _receptor(id: String, pos: Vector3, want: int, size: Vector3, cb: Callable) -> GlassOptics.Receptor:
	var r := GlassOptics.Receptor.new()
	r.want = want
	r.position = pos
	optics.add_child(r)
	r.make_body(size)
	optics.add_element(r)
	r.satisfied.connect(cb)
	receptors[id] = r
	return r


func _source(id: String, pos: Vector3, target: Vector3, mask: int, on: bool = true) -> GlassOptics.Source:
	var s := GlassOptics.Source.new()
	s.position = pos
	s.dir = pos.direction_to(target)
	s.mask = mask
	s.on = on
	optics.add_child(s)
	optics.add_source(s)
	srcs[id] = s
	return s


func _icons(xforms: Array, tint: Color) -> void:
	# The kneeling congregation: hinged, hieratic glass icons — one MultiMesh, hundreds of saints.
	var mmi := _mm("icon_stand", xforms)
	var mm := mmi.multimesh
	var keep := []
	for i in mm.instance_count:
		keep.append(mm.get_instance_transform(i))
	mm.instance_count = 0
	mm.use_colors = true
	mm.instance_count = keep.size()
	var rng := RandomNumberGenerator.new()
	rng.seed = 214
	var pal := [Color("2b54c9"), Color("b22242"), Color("e8b54a"), Color("1a7a5e"), Color("8a3fd1")]
	for i in keep.size():
		mm.set_instance_transform(i, keep[i])
		mm.set_instance_color(i, (pal[rng.randi() % pal.size()] as Color).lerp(tint, 0.2))


# --- CLOISTER ------------------------------------------------------------------------------------

func _build_cloister() -> void:
	# Walks around a void garth, |x|,|z| in [11, 17.5]. The east walk is broken (z -5..5), the west
	# walk collapsed (no way round). Spawn on the south walk.
	_block(Vector3(-17.5, -1, 11), Vector3(17.5, 0, 17.5), "glass_floor")
	_block(Vector3(-17.5, -1, -17.5), Vector3(17.5, 0, -11), "glass_floor")
	_block(Vector3(11, -1, 5), Vector3(17.5, 0, 11), "glass_floor")
	_block(Vector3(11, -1, -11), Vector3(17.5, 0, -5), "glass_floor")
	_block(Vector3(-17.5, -1, 5), Vector3(-11, 0, 11), "glass_floor")
	_block(Vector3(-17.5, -1, -11), Vector3(-11, 0, -5), "glass_floor")
	# rubble of the collapsed west walk, hanging over nothing
	# (walk_rubble.glb: five shattered floor slabs falling away, chunk 0 centred here; not solid)
	var rubble := _model("walk_rubble")
	rubble.position = Vector3(-15.5, -2.15, -3.45)
	geo.add_child(rubble)
	# outer walls (the north wall is the nave's west front, with its door)
	_block(Vector3(-18.5, 0, 17.5), Vector3(18.5, 9, 18.5), "glazed_cloister")
	_block(Vector3(17.5, 0, -17.5), Vector3(18.5, 9, 17.5), "glazed_cloister")
	_block(Vector3(-18.5, 0, -17.5), Vector3(-17.5, 9, 17.5), "glazed_cloister")
	_block(Vector3(-18.5, 0, -18.5), Vector3(-2.5, 26, -17.5), "glass_wall")
	_block(Vector3(2.5, 0, -18.5), Vector3(18.5, 26, -17.5), "glass_wall")
	_block(Vector3(-2.5, 4.5, -18.5), Vector3(2.5, 26, -17.5), "glass_wall")
	_west_door = _block(Vector3(-2.5, 0, -18.2), Vector3(2.5, 4.5, -17.8), "lead")
	_west_door.visible = false
	(_west_door.get_child(0) as StaticBody3D).collision_layer = 0
	# the west front's cloister face (west_front.glb, visual only): portal, buttresses, string courses
	var front := _model("west_front")
	if front:
		front.position = Vector3(0, 0, -17.5)
		geo.add_child(front)
	# the outer walls' bays and the walk roof (cloister_*.glb, visual only): an engaged shaft, plinth and
	# cornice between each pair of the shader's lancets (centres on multiples of 3 m), a transverse rib from
	# each arcade pier onto its wall shaft, and a moulded kerb over the walk slabs' garth faces
	var cbay: Array = []
	var crib: Array = []
	for wall: Array in [[Vector3(0, 0, 17.5), Vector3.RIGHT, PI], [Vector3(17.5, 0, 0), Vector3.BACK, -PI / 2], [Vector3(-17.5, 0, 0), Vector3.BACK, PI / 2]]:
		var b := Basis(Vector3.UP, wall[2])
		for k in 12:
			var u := -16.5 + k * 3.0
			var at: Vector3 = wall[0] + wall[1] * u
			cbay.append(Transform3D(b, at))
			if absf(u) < 11.0 and (wall[1] == Vector3.RIGHT or absf(u) > 5.5):
				crib.append(Transform3D(b, at))
	for k in 8:  # the north walk's roof, ribbed onto the west front between its portal and buttresses
		var u := -10.5 + k * 3.0
		if absf(u) > 3.0:
			crib.append(Transform3D(Basis.IDENTITY, Vector3(u, 0, -17.5)))
	_mm("cloister_bay", cbay)
	_mm("cloister_rib", crib)
	var ckerb: Array = []
	for k in 22:  # south and north rims
		ckerb.append(Transform3D(Basis(Vector3.UP, PI), Vector3(-10.5 + k, 0, 11)))
		ckerb.append(Transform3D(Basis.IDENTITY, Vector3(-10.5 + k, 0, -11)))
	for k in 6:  # east and west rims, and the broken ends of those walks at |z| 5
		for s: float in [1.0, -1.0]:
			ckerb.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(11, 0, s * (5.5 + k))))
			ckerb.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-11, 0, s * (5.5 + k))))
			var end := Basis(Vector3.UP, PI if s > 0 else 0.0)
			ckerb.append(Transform3D(end, Vector3(11.5 + k * 1.083, 0, s * 5)))
			ckerb.append(Transform3D(end, Vector3(-11.5 - k * 1.083, 0, s * 5)))
	_mm("cloister_kerb", ckerb)
	# arcade around the garth: lead-framed glass piers, a glazed roof over the walks
	var cpier := {"pier_base": [], "pier_shaft": [], "pier_capital": []}
	var carch: Array = []
	for side in 4:
		for k in 8:
			var u := -10.5 + k * 3.0
			var p := Vector3(u, 0, 11) if side == 0 else (Vector3(u, 0, -11) if side == 1 else (Vector3(11, 0, u) if side == 2 else Vector3(-11, 0, u)))
			if side >= 2 and absf(u) < 5.5:
				continue
			# the pier stands on the walk's rim over the garth: a round collider lets a player
			# strafing along the edge slide past it instead of catching on a square corner
			var pc := _block(p + Vector3(-0.3, 0, -0.3), p + Vector3(0.3, 5.2, 0.3), "glass_gold")
			pc.visible = false
			var cyl := CylinderShape3D.new()
			cyl.radius = 0.3
			cyl.height = 5.2
			((pc.get_child(0) as StaticBody3D).get_child(0) as CollisionShape3D).shape = cyl
			_pier_xf(cpier, p, 5.2, [5.2], 0.5)
			# pointed arches between the piers, 3 m span (the nave arch scaled down)
			if k < 7 and not (side >= 2 and absf(u + 3.0) < 5.5):
				var b := Basis.IDENTITY if side < 2 else Basis(Vector3.UP, PI / 2)
				var mid := p + (Vector3(1.5, 5.2, 0) if side < 2 else Vector3(0, 5.2, 1.5))
				carch.append(Transform3D(b.scaled(Vector3.ONE * 0.3), mid))
	for part: String in cpier:
		_mm(part, cpier[part])
	_mm("arch_arcade", carch)
	_block(Vector3(-17.5, 7.2, 11), Vector3(17.5, 7.5, 17.5), "glass_quarry", false)
	_block(Vector3(-17.5, 7.2, -17.5), Vector3(17.5, 7.5, -11), "glass_quarry", false)
	_block(Vector3(11, 7.2, -11), Vector3(17.5, 7.5, 11), "glass_quarry", false)
	_block(Vector3(-17.5, 7.2, -11), Vector3(-11, 7.5, 11), "glass_quarry", false)
	# the garth is a light-well: a column of white falls into it forever
	var well := _spot(Vector3(0, 40, 0), Vector3(0, -20, 0), Color("fff1d2"), 16.0, 16.0, 70.0)
	well.light_volumetric_fog_energy = 4.0
	# a fall into the well (or the gap) ends in haze a few metres down, not a long drop to a flat void
	_haze(Vector3(-17.5, -16, -17.5), Vector3(17.5, -1.5, 17.5))
	_catch(Vector3(-17.5, -4.5, -17.5), Vector3(17.5, -3.5, 17.5))
	# four lancets in the outer walls tell the Kingdom's ordinary days and light the walks
	_lancet("c1", Vector3(17.45, 4.6, 8.5), 1.9, Vector3(-1, 0, 0), "cloister_1", 0.0, Vector3(13.5, 0, 6.0), 5.0)
	_lancet("c2", Vector3(17.45, 4.6, -8.5), 1.9, Vector3(-1, 0, 0), "cloister_2", 0.0, Vector3(13.5, 0, -6.0), 5.0)
	_lancet("c3", Vector3(-17.45, 4.6, 14.0), 1.9, Vector3(1, 0, 0), "cloister_3", 0.0, Vector3(-13.5, 0, 14.0), 5.0)
	_lancet("c4", Vector3(-8.0, 4.6, 17.45), 1.9, Vector3(0, 0, -1), "cloister_4", 0.0, Vector3(-6.0, 0, 13.5), 5.0)
	for id: String in ["c1", "c2", "c3", "c4"]:  # the glazed walls carry these lancets; keep only their throw
		for mi: Node in geo.get_children():
			if mi is MeshInstance3D and (mi as MeshInstance3D).material_override == windows[id]:
				mi.visible = false
	# the nave's west front over the garth: three lancets, the Kingdom's founding in the middle, each
	# throwing its colours onto the walk below. The first thing she sees is coloured light.
	for k: int in 3:
		var x := (k - 1) * 3.7
		_lancet("west_%d" % k, Vector3(x, 15.5 + (1.2 if k == 1 else 0.0), -17.45), 2.8, Vector3(0, 0, 1),
			["story_2", "win_history", "story_5"][k], 0.0, Vector3(x * 1.4, 0, 3.0), 6.0)
	# the first dial sits in a notch at the gap's edge, its lens at walking height
	_dial("d1", Vector3(14.2, -0.35, 4.7), [Vector3(8, -6, 1), Vector3(14.2, -0.07, -5.0)], GlassOptics.GOLD, "Turn the sun-dial")
	dials["d1"].turned.connect(func(i: int) -> void:
		if i == 1:
			toast("The gold beam is solid. Walk onto it from the gap's edge and follow its glow north to the far walk.", "The sun-dial"))
	# a threshold stone at each end of the gap, centred on the beam (visual only; the walk's collider is untouched)
	for sill: Array in [[Vector3(14.2, 0.0, 5.0), 0.0], [Vector3(14.2, 0.0, -5.0), PI]]:
		var stone := _model("sill")
		if stone:
			stone.position = sill[0]
			stone.rotation.y = sill[1]
			geo.add_child(stone)
	pts["d1_use"] = Vector3(14.2, 0, 6.5)
	pts["gap_south"] = Vector3(14.2, 0, 5.4)
	pts["gap_north"] = Vector3(14.2, 0, -6.5)
	_zone(Vector3(11, 0, -10), Vector3(17.5, 3, -6), func() -> void:
		complete_step(&"light", &"cloister_dial")
		toast("Across. The nave's door is the open arch in the middle of this north walk, 12 m west. Beyond it, straight ahead, stands the clockwork dial.", "The cloister"))
	# congregation along the south and north walks, facing east (−Z)
	var xf: Array = []
	for k in 5:
		xf.append(Transform3D(Basis(Vector3.UP, PI), Vector3(-15 + k * 2.6, 0, 16.9)))
		xf.append(Transform3D(Basis(Vector3.UP, PI), Vector3(-15 + k * 2.6, 0, -12.2)))
	_icons(xf, Color("8a3fd1"))
	_placard(Vector3(-3.5, 1.5, 17.4), Vector3(0, 0, -1), "For the light alone", "Undated, glazed continuously",
		"Leaded glass, light", "214",
		"A kingdom glazed entire. Its light is load-bearing. Visitors walk only on beams that are switched on. The museum accepts no liability for beams that have been switched off.")
	_placard(Vector3(8, 1.5, 17.4), Vector3(0, 0, -1), "Kneeling congregation", "In perpetuity", "Glass, lead", "214.1",
		"They kneel toward the east window. Their veils are violet: in the Kingdom the colour of mourning, in its schools the colour of knowledge. Conservators note these are the same colour.")


# --- NAVE --------------------------------------------------------------------------------------

func _build_nave() -> void:
	# west bay, then the abyss (z -34..-80), two islands, the choir beyond.
	_block(Vector3(-15.5, -1, -34), Vector3(15.5, 0, -17.5), "glass_floor")
	_block(Vector3(-4, -0.6, -48), Vector3(4, 0, -43), "glass_floor")    # P1
	_block(Vector3(-4, -0.6, -65), Vector3(4, 0, -59), "glass_floor")    # P2
	var isl := {"pier_shaft": [], "pier_capital": []}
	for p: Vector3 in [Vector3(0, -0.6, -45.5), Vector3(0, -0.6, -62)]:
		isl["pier_shaft"].append(Transform3D(Basis.from_scale(Vector3(2, 13.28, 2)), p + Vector3(0, -14, 0)))
		isl["pier_capital"].append(Transform3D(Basis.from_scale(Vector3(2, 1, 2)), p + Vector3(0, -0.72, 0)))
	for part: String in isl:
		_mm(part, isl[part])
	# walls and vault (the nave is roofed: its sky is hidden in haze until the roof)
	_block(Vector3(15.5, -12, -121), Vector3(16.5, 26, -17.5), "glazed_nave")
	_block(Vector3(-16.5, -3, -107.5), Vector3(-15.5, 26, -17.5), "glazed_nave")
	_block(Vector3(-16.5, -3, -121), Vector3(-15.5, 26, -111.5), "glazed_nave")
	_block(Vector3(-16.5, -3, -111.5), Vector3(-15.5, 8.9, -107.5), "glass_wall")
	_block(Vector3(-16.5, 12, -111.5), Vector3(-15.5, 26, -107.5), "glass_wall")
	_block(Vector3(-16.5, -12, -121), Vector3(-15.5, -3, -88), "glass_wall")
	_block(Vector3(-16.5, 25.5, -121), Vector3(16.5, 26.5, -17.5), "glass_quarry", false)
	# the glazed walls' bays (cloister_nave.glb, visual only): an engaged shaft between each pair of the
	# shader's lancets (5.5 m bays, divisions on the piers' 11 m and halfway), sill course, band between tiers
	var nbay: Array = []
	for k in 18:
		var z := -22.0 - k * 5.5
		nbay.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(15.5, 0, z)))
		if z > -106.0 or z < -113.0:  # north wall: not across the Rose hall door
			nbay.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-15.5, 0, z)))
	_mm("cloister_nave", nbay)
	# piers of the arcade
	# Modelled: clustered piers (capitals at the arcade and vault springs), pointed arcade arches,
	# a ribbed vault bay per bay. All MultiMesh; the code boxes stay as invisible colliders.
	var red := {"pier_base": [], "pier_shaft": [], "pier_capital": []}
	var gold := {"pier_base": [], "pier_shaft": [], "pier_capital": []}
	var arches: Array = []
	var bays: Array = []
	for k in 9:
		var z := -22.0 - k * 11.0
		var y0 := -12.0 if z < -34 and z > -80 else 0.0
		for x: float in [-9.5, 9.5]:
			_block(Vector3(x - 0.6, y0, z - 0.6), Vector3(x + 0.6, 25.5, z + 0.6), "glass_red", z > -34 or z < -80).visible = false
			_pier_xf(red if k % 2 == 0 else gold, Vector3(x, y0, z), 25.5, [8.0, 14.0])
			if k < 8:
				arches.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(x, 8.0, z - 5.5)))
		if k < 8:  # the apse bay stays open so no rib crosses the east window
			bays.append(Transform3D(Basis.IDENTITY, Vector3(0, 14.0, z)))
	for part: String in red:
		_mm(part, red[part], {"glass_gold_m": "glass_red_m"})
		_mm(part, gold[part])
	_mm("arch_arcade", arches)
	_mm("vault_bay", bays)
	# triforium: south gallery over the nave (Provenance A), north stub over the choir (the way back
	# from the Rose hall)
	_block(Vector3(12, 8.6, -80), Vector3(15.5, 9, -20), "glass_floor")
	_block(Vector3(12, 9, -80), Vector3(12.3, 10, -54), "glass_quarry")
	_block(Vector3(12, 9, -50), Vector3(12.3, 10, -20), "glass_quarry")
	_block(Vector3(-15.5, 8.6, -112), Vector3(-12, 9, -100), "glass_floor")
	# windows: the nave's history windows (go dark during the heist) and the gold window W_N
	# The story of the Kingdom in six clerestory lancets, each re-leaded round an empty pedestal. Each
	# throws its own picture into the nave as coloured light (projector spots), through the haze.
	var hist := 0
	for z: float in [-27.5, -38.5, -71.5]:
		for s: float in [-1.0, 1.0]:
			var land := Vector3(-4.0 * s, 0, z - 4.0) if z > -34 else Vector3(-6.0 * s, -6.0, z - 3.0)
			_lancet("hist_%d" % hist, Vector3(15.45 * s, 20.6, z), 2.6, Vector3(-s, 0, 0), "story_%d" % (hist + 1), 0.0, land, 7.0)
			hist += 1
	_lancet("w_n", Vector3(-15.45, 20.6, -58.5), 2.6, Vector3(1, 0, 0), "story_7", 0.0, Vector3(-2, 0, -63.8), 9.0)
	_source("w_n", Vector3(-15.0, 18, -58.5), Vector3(-2, 0.12, -63.8), GlassOptics.GOLD)
	# blind triforium arcade on both walls, between the main arcade and the clerestory
	var tri: Array = []
	for k in 9:
		var z := -27.5 - k * 11.0
		if z < -112.0:
			break
		tri.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(14.8, 12.0, z)))
		tri.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-14.8, 12.0, z)))
	# the same arcade dresses the flat west wall either side of the door (at the floor, and carried round
	# at the triforium's level) and the crypt's side walls (visual only; the code walls stay the colliders)
	for x: float in [-9.0, 9.0]:
		for y: float in [0.0, 12.0]:
			tri.append(Transform3D(Basis(Vector3.UP, PI), Vector3(x, y, -19.2)))
	for z: float in [-98.0, -113.5]:  # inside the ruby vestry (x -10..-15, z -90..-106), and past it
		tri.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-14.3, -8.0, z)))
	for z: float in [-86.0, -97.0, -108.0]:
		tri.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(14.3, -8.0, z)))
	_mm("triforium", tri)
	_light(Vector3(0, 4, -25), Color("ffd9a0"), 0.6, 10.0)
	# Escalation 1½: a clockwork dial — light on a timetable. A: bridge to P1. B: onto mirror M1.
	_dial("d2", Vector3(-4, -0.35, -34.3),
		[Vector3(-6, -12, -42), Vector3(-1.5, -0.07, -43.0), Vector3(2, 0.12, -46.5)], GlassOptics.GOLD,
		"Wind the clockwork dial", [[1, 7.0], [2, 9.0], [0, 2.5]])
	pts["d2_use"] = Vector3(-4, 0, -32.3)
	pts["lip"] = Vector3(-1.6, 0, -33.8)
	# M1 on P1: north (rest) / P2 / south
	_mirror("m1", Vector3(2, 0.12, -46.5), Vector3(-4, -0.07, -34.3),
		[Vector3(-15, 0.1, -52), Vector3(2.5, -0.07, -59.0), Vector3(15, 0.1, -50)], 0)
	pts["p1"] = Vector3(-1.5, 0, -45)
	pts["p1_far"] = Vector3(2.3, 0, -47.6)
	# M2 on P2 catches the gold window: abyss (rest) / choir / triforium (Provenance A)
	_mirror("m2", Vector3(-2, 0.12, -63.8), Vector3(-15, 18, -58.5),
		[Vector3(-2, -10, -75), Vector3(-1, 2.34, -80.0), Vector3(12, 8.86, -52)], 0)
	pts["p2"] = Vector3(2.5, 0, -60.5)
	pts["p2_m2"] = Vector3(-1.2, 0, -62.0)
	_zone(Vector3(-4, 0, -65), Vector3(4, 3, -59), func() -> void: complete_step(&"light", &"clockwork"))
	_catch(Vector3(-15.5, -4, -80), Vector3(15.5, -3, -34))
	_haze(Vector3(-15.5, -16, -80), Vector3(15.5, -1.5, -34))  # the abyss reads as depth, not a flat floor
	_placard(Vector3(7, 1.5, -18.2), Vector3(0, 0, -1), "Windows of the nave", "Re-leaded under the present administration", "Stained glass, lead", "214.2",
		"Each saint has been lifted out of her own miracle and replaced by a pedestal. The miracles proceed regardless. The pedestals are empty. This is described as an improvement.")


# --- CHOIR ---------------------------------------------------------------------------------------

func _build_choir() -> void:
	_block(Vector3(-15.5, 2.1, -110), Vector3(15.5, 2.5, -80), "glass_floor")
	_block(Vector3(-15.5, 2.1, -121), Vector3(15.5, 2.5, -114), "glass_floor")
	_block(Vector3(14, 2.1, -114), Vector3(15.5, 2.5, -110), "glass_floor")
	_block(Vector3(-15.5, -12, -80.4), Vector3(15.5, 2.1, -80), "glass_crypt")   # choir front face
	# crypt stair: one long ramp down the slot at the east end
	_ramp(Vector3(14, 2.5, -112), Vector3(-12, -8, -112), 3.0, "glass_floor")
	_block(Vector3(-3, 2.5, -103), Vector3(3, 2.6, -97), "glass_gold")       # lens dais
	pts["choir"] = Vector3(0, 2.5, -84)
	pts["ramp_top"] = Vector3(14.6, 2.5, -112)
	pts["ramp_bottom"] = Vector3(-13.5, -8, -112)
	_zone(Vector3(-15.5, 2.5, -88), Vector3(15.5, 5.5, -80.5), func() -> void: complete_step(&"light", &"choir"))
	# grate over the prism (decorative lead lattice)
	for k in 5:
		_block(Vector3(-1.2 + k * 0.6, 2.5, -93.2), Vector3(-1.15 + k * 0.6, 2.56, -90.8), "lead", false)
	# saint windows (edited until restored) and their mirrors
	_lancet("ruby", Vector3(15.45, 20.6, -92.5), 2.6, Vector3(-1, 0, 0), "lancet_ruby", 1.0, Vector3(6, 2.5, -95), 6.0)
	_lancet("azure", Vector3(-15.45, 20.6, -92.5), 2.6, Vector3(1, 0, 0), "lancet_azure", 1.0, Vector3(-5, 2.5, -95), 6.0)
	_lancet("verdance", Vector3(15.45, 20.6, -105.5), 2.6, Vector3(-1, 0, 0), "lancet_verdance", 1.0, Vector3(6, 2.5, -103), 6.0)
	var sr := Vector3(10.5, 2.75, -92.5)
	var sa := Vector3(-8.5, 2.75, -92.5)
	var sv := Vector3(10.5, 2.75, -105.5)
	_source("ruby", Vector3(15.0, 16.5, -92.5), sr, GlassOptics.RED, false)
	_source("azure", Vector3(-15.0, 16.5, -92.5), sa, GlassOptics.BLUE, false)
	_source("verdance", Vector3(15.0, 16.5, -105.5), sv, GlassOptics.GOLD | GlassOptics.BLUE, false)
	_mirror("s_r", sr, Vector3(15.0, 16.5, -92.5), [sr + Vector3(-1.5, -0.45, 0.6), LENS_POS], 0, 0.9)
	_mirror("s_a", sa, Vector3(-15.0, 16.5, -92.5), [sa + Vector3(1.5, -0.45, 0.6), LENS_POS], 0, 0.9)
	_mirror("s_v", sv, Vector3(15.0, 16.5, -105.5), [sv + Vector3(-1.5, -0.45, -0.6), LENS_POS], 0, 0.9)
	# the lens holder: a cradle, empty until the Widow's lantern is set in it
	lens_choir = GlassOptics.Lens.new()
	lens_choir.position = LENS_POS
	lens_choir.out_dir = LENS_POS.direction_to(EAST_AIM)
	optics.add_child(lens_choir)
	lens_choir.make_body(Vector3(0.9, 0.9, 0.9))
	lens_choir.body.collision_layer = 0
	optics.add_element(lens_choir)
	var cradle := _model("lens_cradle")
	cradle.position = LENS_POS
	geo.add_child(cradle)
	_use("lens_holder", LENS_POS, Vector3(1.2, 1.4, 1.2), "Set the Widow's lantern in the lens", _place_lantern)
	pts["lens"] = Vector3(0, 2.6, -99.0)
	_light(Vector3(0, 6, -100), Color("ffd9a0"), 0.8, 12.0)


# --- CRYPT ---------------------------------------------------------------------------------------

func _build_crypt() -> void:
	# floor (with the channel pit x 5..11, z -84..-104 — Saint Azure lies across it)
	_block(Vector3(-15, -9, -122), Vector3(5, -8, -82), "crypt_floor")
	_block(Vector3(5, -9, -122), Vector3(15, -8, -104), "crypt_floor")
	_block(Vector3(5, -9, -84), Vector3(15, -8, -82), "crypt_floor")
	_block(Vector3(11, -9, -104), Vector3(15, -8, -84), "crypt_floor")
	# the crypt's dead: ledger stones let into the floor, brass effigies, heads to the east
	var ledgers: Array = []
	for at: Vector2 in [Vector2(-7.5, -88.5), Vector2(-5.0, -88.5), Vector2(-2.5, -88.5), Vector2(-7.5, -116.5), Vector2(-4.5, -116.5),
			Vector2(-1.5, -116.5), Vector2(1.5, -116.5), Vector2(4.5, -116.5), Vector2(-6.5, -106.0), Vector2(13.0, -108.0)]:
		ledgers.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(at.x, -8.0, at.y)))
	_mm("ledger", ledgers, {"glass_red_m": "ledger_red"})
	_catch(Vector3(5, -12, -104), Vector3(11, -11, -84))
	# walls; west wall has the white gate (z -86..-83.6) to the passage
	_block(Vector3(15, -8, -122), Vector3(15.5, 2.1, -80.4), "glass_crypt")
	_block(Vector3(-15.5, -8, -122), Vector3(-15, 2.1, -86), "glass_crypt")
	_block(Vector3(-15.5, -8, -83.6), Vector3(-15, 2.1, -80.4), "glass_crypt")
	_block(Vector3(-15.5, -4.5, -86), Vector3(-15, 2.1, -83.6), "glass_crypt")
	_block(Vector3(-15.5, -8, -121.0), Vector3(15.5, 2.1, -120.95), "glass_crypt")  # in front of the east wall's foot
	_gates["white"] = _block(Vector3(-15.4, -8, -86), Vector3(-15.1, -4.5, -83.6), "glass_quarry")
	# the low ribbed vault: transverse ribs on engaged piers, a teal glass web between them with
	# diagonal ribs and a ring boss; the stair slot's bay stays open, the shaft drops through an eye
	var zs: Array[float] = [-80.6, -86.7, -92.29, -98.23, -104.17, -110.11, -116.06, -121.8]
	var ribs: Array = []
	var webs: Array = []
	for i in zs.size():
		ribs.append(Transform3D(Basis.IDENTITY, Vector3(0, 0, zs[i])))
		if i + 1 < zs.size() and i != 5:
			webs.append(Transform3D(Basis.IDENTITY.scaled(Vector3(1, 1, (zs[i] - zs[i + 1]) / 6.0)), Vector3(0, 0, zs[i])))
	_mm("crypt_rib", ribs)
	_mm("crypt_web", webs)
	# Ruby chapel x -15..-10, z -90..-106, behind the gold gate; a slit admits red at z -92.7
	_block(Vector3(-10.25, -8, -92.45), Vector3(-9.95, -3, -90), "glazed_ruby")
	_block(Vector3(-10.25, -8, -98.9), Vector3(-9.95, -3, -92.95), "glazed_ruby")
	_block(Vector3(-10.25, -8, -106), Vector3(-9.95, -3, -101.3), "glazed_ruby")
	_block(Vector3(-15, -8, -90.3), Vector3(-10, -3, -90), "glazed_ruby")
	_block(Vector3(-15, -8, -106), Vector3(-10, -3, -105.7), "glazed_ruby")
	_gates["gold"] = _block(Vector3(-10.2, -8, -101.3), Vector3(-10.0, -3, -98.9), "glass_gold")
	_light(Vector3(-12.5, -5, -98), Color("b22242"), 0.8, 6.0)
	_light(Vector3(0, -2, -100), Color("8a3fd1"), 0.9, 16.0)
	_light(Vector3(12, -5, -94), Color("2b54c9"), 0.8, 7.0)
	_light(Vector3(0, -5, -118), Color("1a7a5e"), 0.8, 8.0)
	_light(Vector3(3, -3.2, -112), Color("c8d8ff"), 5.5, 16.0)  # a cold lamp over the panes' floor, so the tiles read
	# White light falls through the choir grate onto the prism.
	_source("shaft", Vector3(0, 1.8, -92), PRISM_O, GlassOptics.WHITE)
	prism = GlassOptics.Prism.new()
	prism.yaws = [160.0, 45.0, -51.0, 0.0]
	prism.position = PRISM_O
	optics.add_child(prism)
	prism.setup()
	optics.add_element(prism)
	prism.head.add_child(_model("prism"))
	prism.head.add_child(_spectrum_fan())
	var stand := _model("prism_stand")
	stand.position = PRISM_O + Vector3(0, -0.02, 0)
	stand.scale.y = 0.33  # a low turntable: the beams leave the crystal at its centre
	geo.add_child(stand)
	_use("prism", PRISM_O + Vector3(0, 0.4, 0), Vector3(1.6, 1.6, 1.6), "Turn the prism", func() -> void:
		prism.turn()
		Audio.sfx(load(SND + "mirror_turn.ogg"), PRISM_O, 0.0, 0.5, 0.8))
	pts["prism"] = PRISM_O + Vector3(0, -0.12, 1.6)
	# Receptors are placed ON the prism's real output lines.
	var d_az := GlassOptics.dir_yaw(45.0 + 35.0)
	var d_gold := GlassOptics.dir_yaw(-51.0)
	var d_red := GlassOptics.dir_yaw(-51.0 - 35.0)
	var at_az := PRISM_O + d_az * ((12.8 - PRISM_O.x) / d_az.x)
	_receptor("azure", at_az, GlassOptics.BLUE, Vector3(1.2, 0.7, 1.2), func() -> void: _restore(&"azure"))
	_pane(at_az, "win_azure")
	var t_gate := (-10.1 - PRISM_O.x) / d_gold.x
	_receptor("gold_gate", PRISM_O + d_gold * t_gate, GlassOptics.GOLD, Vector3(0.4, 0.8, 2.2), _open_gold_gate)
	var t_slit := (-13.0 - PRISM_O.x) / d_red.x
	var m4 := PRISM_O + d_red * t_slit
	var bier := Vector3(-13, -7.88, -102.5)
	_mirror("m4", m4, PRISM_O, [Vector3(-15, -7.88, -87.5), bier], 0, 0.8)
	_receptor("ruby", bier, GlassOptics.RED, Vector3(1.2, 0.7, 1.2), func() -> void: _restore(&"ruby"))
	_pane(bier, "win_ruby")
	pts["chapel_in"] = Vector3(-11.5, -8, -100.1)
	pts["gate_out"] = Vector3(-8.5, -8, -100.1)
	pts["m4"] = m4 + Vector3(0.9, -0.12, -1.0)
	# yaw 0: gold straight on to the lens; blue +35 to M6; red -35 to the reliquary
	var d_b := GlassOptics.dir_yaw(35.0)
	var d_r := GlassOptics.dir_yaw(-35.0)
	var m6 := PRISM_O + d_b * 7.0
	var reliq := PRISM_O + d_r * 9.8
	lens_crypt = GlassOptics.Lens.new()
	lens_crypt.position = Vector3(0, -7.88, -108)
	lens_crypt.out_dir = Vector3(0, 0, -1)
	optics.add_child(lens_crypt)
	lens_crypt.make_body(Vector3(0.9, 0.9, 0.9))
	optics.add_element(lens_crypt)
	lens_crypt.add_child(_model("lens"))
	_mirror("m6", m6, PRISM_O, [Vector3(10, -7.88, m6.z - 1.0), lens_crypt.position, reliq], 0, 0.8)
	pts["m6"] = m6 + Vector3(-1.0, -0.12, 0.6)
	_receptor("verdance", Vector3(0, -7.88, -120.6), GlassOptics.GOLD | GlassOptics.BLUE, Vector3(1.6, 1.2, 0.6), func() -> void: _restore(&"verdance"))
	_pane(Vector3(0, -7.88, -120.5), "win_verdance", true)
	_receptor("reliquary", reliq, GlassOptics.RED | GlassOptics.BLUE, Vector3(1.3, 0.8, 1.3), _open_reliquary)
	_block(reliq + Vector3(-0.5, -0.12, -0.4), reliq + Vector3(0.5, 0.25, 0.4), "glass_gold", true).visible = false
	var chest := _model("reliquary")
	chest.position = reliq + Vector3(0, -0.12, 0)
	geo.add_child(chest)
	_reliquary_lid = _model("reliquary_lid")
	_reliquary_lid.position = reliq + Vector3(0, 0.25, 0)
	geo.add_child(_reliquary_lid)
	_prov_spots["veil"] = reliq + Vector3(0, 0.62, 0)
	pts["reliquary"] = reliq + Vector3(0.9, -0.12, 0.8)
	_placard(Vector3(-3, -6.5, -82.6), Vector3(0, 0, -1), "Original glazing, face-down", "Removed during re-leading", "Stained glass, stored per conservation guidance", "214.3",
		"Panes removed in the re-leading are kept face-down, which is how glass is stored and how saints are kept quiet. Light of a pane's own colour, applied from behind, will regrettably turn it over.")
	pts["white_gate"] = Vector3(-14, -8, -84.8)


## The prism's dispersion thrown on the floor: red at -35 degrees through gold to violet at +35 (the
## gameplay beams leave along -35, 0 and +35), soft at the edges, fading over 5 m.
func _spectrum_fan() -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 48
	var ring := func(k: int, r: float, a: float) -> void:
		var t := float(k) / n
		var yaw := deg_to_rad(lerpf(-42.0, 42.0, t))
		var c := Color.from_hsv(lerpf(0.0, 0.78, t), 0.95, 1.0)
		c.a = a * smoothstep(0.0, 0.12, t) * smoothstep(1.0, 0.88, t)
		st.set_color(c)
		st.add_vertex(Vector3(sin(yaw) * r, -0.105, -cos(yaw) * r))
	for k in n:
		for seg: Array in [[0.35, 0.9, 1.6, 0.85], [1.6, 0.85, 5.0, 0.0]]:
			ring.call(k, seg[0], seg[1]); ring.call(k + 1, seg[0], seg[1]); ring.call(k + 1, seg[2], seg[3])
			ring.call(k, seg[0], seg[1]); ring.call(k + 1, seg[2], seg[3]); ring.call(k, seg[2], seg[3])
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var m := ShaderMaterial.new()
	m.shader = load("res://wings/glass/shaders/spectrum.gdshader")
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


## A face-down saint's pane lying on a bier (or set in a niche): a quad of the saint's window, face
## to the floor; restoring it lifts it upright and lights it.
func _pane(pos: Vector3, tex: String, upright: bool = false) -> void:
	_block(pos + Vector3(-0.9, -0.12, -0.6), pos + Vector3(0.9, -0.07, 0.6), "lead", true)
	var id := tex.trim_prefix("win_")
	var mi := _window("pane_" + id, pos + Vector3(0, 0.14 if not upright else 1.1, 0), Vector2(1.6, 1.6) if not upright else Vector2(2.0, 2.0), Vector3.DOWN if not upright else Vector3(0, 0, 1), tex)
	(windows["pane_" + id] as ShaderMaterial).set_shader_parameter(&"dark", 0.85)
	mi.set_meta(&"pane_up", pos + Vector3(0, 1.1, 0))


# --- PASSAGE & TOWER --------------------------------------------------------------------------

func _build_passage_and_tower() -> void:
	# corridor west out of the crypt, then a glass tube south through the dark beside the nave
	_block(Vector3(-19, -9, -86), Vector3(-15.5, -8, -83.6), "glass_crypt")
	_block(Vector3(-19, -9, -86), Vector3(-16, -8, -30), "glass_floor")
	_block(Vector3(-19.4, -8, -86.4), Vector3(-19, -5, -30), "glass_quarry")
	_block(Vector3(-16, -8, -83.6), Vector3(-15.6, -5, -30), "glass_quarry")
	_block(Vector3(-19.4, -5, -86.4), Vector3(-15.5, -4.7, -30), "glass_quarry")
	_block(Vector3(-19.4, -8, -86.4), Vector3(-15.5, -4.7, -86), "glass_crypt")
	_catch(Vector3(-19.5, -4.6, -86), Vector3(-15.4, -3.6, -30))
	for k in 7:
		_light(Vector3(-17.5, -5.8, -80 + k * 8.0), Color("2b54c9") if k % 2 else Color("1a7a5e"), 0.9, 6.0)
	# the tube is lined with lead portal frames every 4 m, so its glass reads as panels between ribs
	var frames: Array = []
	for k in 14:
		frames.append(Transform3D(Basis.IDENTITY, Vector3(-17.5, -8.0, -84.0 + k * 4.0)))
	_mm("tube_frame", frames)
	# tower: x -28..-16, z -30..-18; ten switchback legs, -8 → 16
	_block(Vector3(-28, -9, -30), Vector3(-16, -8, -18), "glass_floor")
	_block(Vector3(-28.5, -8, -18), Vector3(-15.5, 19, -17.5), "glazed_tower")
	_block(Vector3(-28.5, -8, -30), Vector3(-28, 19, -18), "glazed_tower")
	_block(Vector3(-16, -8, -29.6), Vector3(-15.5, 19, -18), "glazed_tower")
	_block(Vector3(-28.5, -5, -30.5), Vector3(-16, 16, -30), "glazed_tower")
	_block(Vector3(-28.5, -8, -30.5), Vector3(-19.4, -5, -30), "glazed_tower")
	_block(Vector3(-28.5, 19, -30.5), Vector3(-15.5, 19.4, -17.5), "glass_quarry", false)
	_block(Vector3(-28.5, 16, -30.5), Vector3(-21.5, 19, -30), "glass_wall")
	_tower_masonry()
	var y := -8.0
	for leg in 10:
		var west := leg % 2 == 0
		var lane_z := -25.8 if west else -20.6
		var xa := -18.5 if west else -25.5
		var xb := -25.5 if west else -18.5
		# colliders stay the code ramp and slab; the modelled flight and landing are what you see
		_ramp(Vector3(xa, y, lane_z), Vector3(xb, y + 2.4, lane_z), 2.6, "glass_gold" if west else "glass_red").visible = false
		var fl := _model("tower_flight_gold" if west else "tower_flight_red")
		fl.transform = Transform3D(Basis(Vector3.UP, PI if west else 0.0), Vector3(xa, y, lane_z))
		geo.add_child(fl)
		y += 2.4
		var lx := Vector2(-28, -25.5) if west else Vector2(-18.5, -16)
		var lz := Vector2(-27.3, -19.1) if leg < 9 else Vector2(-30, -19.1)
		_block(Vector3(lx.x, y - 0.4, lz.x), Vector3(lx.y, y, lz.y), "glass_floor").visible = false
		var ld := _model("tower_landing")
		ld.transform = Transform3D(Basis.from_scale(Vector3(1, 1, (lz.y - lz.x) / 8.2)), Vector3((lx.x + lx.y) * 0.5, y, (lz.x + lz.y) * 0.5))
		geo.add_child(ld)
		if leg % 3 == 1:
			_light(Vector3((lx.x + lx.y) * 0.5, y + 1.6, -23), Color("e8b54a"), 2.2, 8.0)
		if leg % 2 == 1:  # a warm lamp hung in the well between the flights, so the stonework and soffits read
			_light(Vector3(-22.0, y + 1.0, -24.0), Color("ffd9a0"), 2.4, 9.0)
	_block(Vector3(-21.5, 15.6, -30.5), Vector3(-16, 16, -27.3), "glass_floor")
	pts["tower_in"] = Vector3(-17.5, -8, -28.5)
	pts["tower_top"] = Vector3(-17.5, 16, -26)
	_lancet("tower_w", Vector3(-27.95, 8, -24), 2.0, Vector3(1, 0, 0), "story_8", 0.0, Vector3(-21, -2, -24), 6.0)


## The tower shaft's masonry over the glazed walls, full height: a clustered pier between every pair of
## lancets, a sill course under the lower tier, a deep band of blind lancets between the tiers and a
## corbelled cornice under the roof. Visual only (the glazed boxes keep their colliders). Courses skip the
## passage door (south wall, x > -19.4, below -5) and the roof exit (south wall, x > -21.5, above 16).
func _tower_masonry() -> void:
	var parts := {"tower_pier": [], "tower_sill": [], "tower_band": [], "tower_cornice": []}
	# [face basis, point on the face at the shaft floor, course centres along the wall, pier centres]
	var n := Basis(Vector3.UP, PI)
	var s := Basis.IDENTITY
	var w := Basis(Vector3.UP, PI / 2)
	var e := Basis(Vector3.UP, -PI / 2)
	for wall: Array in [[n, "x", -18.0, [-26.0, -22.0, -18.0], [-26.0, -22.0, -18.0]],
			[s, "x", -30.0, [-26.0, -22.0, -18.0], [-26.0, -22.0]],
			[w, "z", -28.0, [-28.0, -24.0, -20.0], [-26.0, -22.0]],
			[e, "z", -16.0, [-28.0, -24.0, -20.0], [-26.0, -22.0]]]:
		var at := func(c: float) -> Vector3:
			return Vector3(c, -8.0, wall[2]) if wall[1] == "x" else Vector3(wall[2], -8.0, c)
		for c: float in wall[3]:
			var south: bool = wall[0] == s
			if not (south and c > -20.0):
				parts["tower_sill"].append(Transform3D(wall[0], at.call(c)))
			parts["tower_band"].append(Transform3D(wall[0], at.call(c)))
			if not (south and c > -24.0):
				parts["tower_cornice"].append(Transform3D(wall[0], at.call(c)))
		for c: float in wall[4]:
			parts["tower_pier"].append(Transform3D(wall[0], at.call(c)))
	for k: String in parts:
		_mm(k, parts[k])


# --- ROOF ---------------------------------------------------------------------------------------

func _build_roof() -> void:
	_block(Vector3(-21.5, 15.6, -100), Vector3(-16.5, 16, -30.5), "glass_floor")
	# parapet with gaps at the buttress ramp (z -60) and the bridge (z -95)
	# colliders stay the code slabs; what you see is a lead-and-glass arcaded parapet (parapet.glb, 1.3 m
	# modules stretched a little to fill each run)
	var rails: Array = []
	for seg: Vector2 in [Vector2(-58.8, -30.5), Vector2(-93.5, -61.2), Vector2(-100, -96.5)]:
		_block(Vector3(-21.8, 16, seg.x), Vector3(-21.5, 16.9, seg.y), "lead").visible = false
		rails.append_array(_parapet_run(Vector3(-21.65, 16, seg.x), Vector3(-21.65, 16, seg.y)))
	_block(Vector3(-21.8, 16, -100.3), Vector3(-16.5, 16.9, -100), "lead").visible = false
	rails.append_array(_parapet_run(Vector3(-21.8, 16, -100.15), Vector3(-16.5, 16, -100.15)))
	_mm("parapet", rails)
	# flying buttresses: outer pinnacles and arches leaning on the clerestory
	var tips: Array = []
	var butt: Array = []
	for k in 8:
		var z := -36.0 - k * 9.0
		_block(Vector3(-25, 0, z - 0.7), Vector3(-23.6, 23, z + 0.7), "glass_red", true).visible = false
		tips.append(Transform3D(Basis.IDENTITY, Vector3(-24.3, 23.6, z)))
		butt.append(Transform3D(Basis.IDENTITY, Vector3(-24.3, 0, z)))
	_mm("pinnacle", tips)
	_mm("buttress", butt)
	_mm("flyer", butt)
	# a glass icon on the walk, looking up: the human scale beside the thing in the sky
	_icons([Transform3D(Basis(Vector3.UP, -2.3) * Basis(Vector3.RIGHT, -0.25), Vector3(-20.6, 16.0, -45.0))], Color("8a3fd1"))
	# the hidden one: a fallen buttress you can climb, to a pinnacle niche (Provenance C)
	_ramp(Vector3(-20.5, 16, -60), Vector3(-23.6, 18.3, -60), 1.6, "glass_red").visible = false
	_block(Vector3(-25.2, 17.9, -61.2), Vector3(-23.6, 18.3, -58.8), "glass_floor").visible = false
	var ff := _model("fallen_flyer")  # modelled +X: turn it to climb toward -X
	ff.transform = Transform3D(Basis(Vector3.UP, PI), Vector3(-20.5, 16, -60))
	geo.add_child(ff)
	var niche := _model("pinnacle_niche")
	niche.position = Vector3(-24.4, 18.3, -60)
	geo.add_child(niche)
	_prov_spots["iron"] = Vector3(-24.3, 18.8, -60)
	pts["iron"] = Vector3(-22.5, 17.4, -60)
	# THE REVEAL: crest the stair and the sky is one window, and something leans in to look.
	_zone(Vector3(-21.5, 15.8, -34), Vector3(-16.5, 19, -31), _reveal_sky)
	# heliostat to the Rose hall
	_dial("d3", Vector3(-21.9, 15.65, -95), [Vector3(-26, 40, -95), Vector3(-32.0, 13.93, -95)], GlassOptics.RED | GlassOptics.BLUE, "Turn the heliostat")
	pts["d3_use"] = Vector3(-20.0, 16, -95)
	pts["roof_end"] = Vector3(-21.0, 16, -95)
	_placard(Vector3(-16.6, 17.2, -40), Vector3(-1, 0, 0), "The sky, glazed", "Cleaned once", "Firmament, lead, three suns", "214.4",
		"The heaven of the Vitrine Kingdom is a single window. It has been cleaned once. Whoever cleaned it is still looking in.")


# --- ROSE HALL ----------------------------------------------------------------------------------

func _build_rose() -> void:
	# the round hall: modelled 10-degree bays (blind arcade, blind lancet, shafts, courses)
	var bays: Array = []
	for i in 36:
		var a := TAU * i / 36.0
		var deg := rad_to_deg(wrapf(a, -PI, PI))
		if absf(deg) < 9.0 or (deg > -40.0 and deg < -24.0) or absf(deg) > 155.0:
			continue
		bays.append(Transform3D(Basis(Vector3.UP, -a), HALL))
	_mm("rotunda_bay", bays)
	_block(HALL + Vector3(-28.6, -11, -12.6), HALL + Vector3(-27.6, 27, 12.6), "glass_wall", false)  # flat bay behind the rose
	_block(HALL + Vector3(23.4, -0.4, -2), HALL + Vector3(28, 0, 2), "glass_floor")           # balcony
	_block(HALL + Vector3(-22, -0.4, -4), HALL + Vector3(-13, 0, 4), "glass_floor")           # dais
	_block(HALL + Vector3(18.2, -0.4, -18), HALL + Vector3(25.5, -0.01, -12.2), "glass_floor")      # exit landing
	# her dais (modelled; the collider stays a plain cylinder) and the tear she weeps, in its cradle
	var boss := _model("rose_dais")
	boss.position = HALL
	geo.add_child(boss)
	var sb := StaticBody3D.new()
	sb.set_meta(&"surface", "glass")
	sb.position = HALL + Vector3(0, -0.2, 0)
	var cs := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 3.9
	cyl.height = 0.4
	cs.shape = cyl
	sb.add_child(cs)
	geo.add_child(sb)
	var tear := _model("rose_tear")
	tear.position = HALL
	geo.add_child(tear)
	var glint := OmniLight3D.new()
	glint.light_color = Color("a66bff")
	glint.light_energy = 1.2
	glint.omni_range = 4.0
	glint.shadow_enabled = false
	glint.position = HALL + Vector3(0, 1.2, 0)
	geo.add_child(glint)
	# THE ROSE WIDOW: a 23 m rose of modelled tracery; her petals of panes light with her floor.
	var rw := _window("rose", HALL + Vector3(-27.4, 12, 0), Vector2(23, 23), Vector3(1, 0, 0), "win_rose", 0.0, "rose_pane")
	rw.scale = Vector3.ONE * 11.5  # the whole end wall: 23 m, floor to cornice
	_rose_pane_mat = windows["rose"]
	_rose_pane_mat.set_shader_parameter(&"figure_c", Vector2(0.5, 0.5))
	_rose_pane_mat.set_shader_parameter(&"rose", true)
	_rose_pane_mat.set_shader_parameter(&"energy", 3.2)
	var tr := _model("rose_tracery")
	rw.add_child(tr)
	tr.position = Vector3(0, 0, 0.004)
	# her light: one projector from behind her face down across the hall, and a warm key on the dais
	var key := _spot(HALL + Vector3(-34, 24, 0), HALL + Vector3(4, -2, 0), Color.WHITE, 14.0, 34.0, 70.0)
	key.light_projector = load("res://wings/glass/textures/win_rose.png")
	key.light_volumetric_fog_energy = 1.6
	_rose_lights.append(key)
	_rose_lights.append(_light(HALL + Vector3(-20, 4, 0), Color("c79bff"), 1.2, 9.0))
	rose = RoseWidow.new()
	rose.name = "RoseWidow"
	rose.path = PackedVector3Array([Vector3(-13.5, 0, 0), Vector3(-6, 0, -5), Vector3(5, 0, -1), Vector3(8, 0, -9), Vector3(14, 0, -11), Vector3(21, 0, -14)])
	rose.sconces = PackedVector3Array([Vector3(5, 0, -1), Vector3(14, 0, -11)])
	rose.bridge = PackedVector3Array([Vector3(24, 0, 0), Vector3(3.5, 0, 0)])
	rose.position = HALL
	add_child(rose)
	var tile := BoxMesh.new()
	tile.size = Vector3(1.47, 0.1, 1.47)
	rose.build(tile, load("res://wings/glass/shaders/rose_tile.gdshader"))
	for s: Vector3 in rose.sconces:
		var sl := _light(HALL + s + Vector3(0, 1.4, 0), Color("ffc27a"), 0.0, 5.0)
		_sconce_lights.append(sl)
		_block(HALL + s + Vector3(-0.15, -3, -0.15), HALL + s + Vector3(0.15, -0.3, 0.15), "lead", false)
	_catch(HALL + Vector3(-28, -8, -28), HALL + Vector3(28, -7, 28))
	_use("lantern", HALL + Vector3(-19, 1.0, 0), Vector3(1.4, 2.0, 1.4), "Take the Widow's lantern", _take_lantern)
	var lantern := _lantern_mesh()
	lantern.position = HALL + Vector3(-19, 1.1, 0)
	lantern.name = "WidowLantern"
	geo.add_child(lantern)
	pts["balcony"] = HALL + Vector3(25.5, 0, 0)
	pts["balcony_edge"] = HALL + Vector3(23.7, 0, 0)
	pts["dais"] = HALL + Vector3(-15, 0, 0)
	pts["lantern"] = HALL + Vector3(-17.2, 0, 0)
	pts["landing"] = HALL + Vector3(22.5, 0, -14.5)
	for p: Vector3 in rose.path:
		pts["path_%d" % pts.size()] = HALL + p
	_zone(HALL + Vector3(20, 0, -18), HALL + Vector3(25.5, 3, -11), _cross_rose)
	# exit corridor down to the north triforium and a drop into the choir
	_ramp(HALL + Vector3(25.5, 0, -14.5), Vector3(-15.5, 9, -109.5), 3.0, "glass_floor")
	_block(Vector3(-16.6, 9, -111.5), Vector3(-15.4, 12, -107.5), "glass_quarry", false)
	pts["corridor_end"] = Vector3(-14.5, 9, -109.5)
	pts["triforium_drop"] = Vector3(-10.5, 2.5, -106)
	_placard(HALL + Vector3(27.6, 1.5, 2.6), Vector3(-1, 0, 0), "The Rose Widow", "In mourning", "Rose window, six petals", "214.5",
		"She grieves in six colours, slowly. Her floor exists only where her light falls. Cross while she breathes out. Do not take her lantern. Visitors take her lantern.")


func _lantern_mesh() -> Node3D:
	var m := _model("lantern")
	if m:
		# the Widow's last light: warm, short, with real falloff and shadows (the only shadowed
		# light in her hall), so blind glass glints only where it reaches
		var l := _light(Vector3(0, 0.25, 0), Color("ffb768"), 2.4, 9.0, m)
		l.omni_attenuation = 1.6
		l.shadow_enabled = true
		l.light_volumetric_fog_energy = 2.5
		return m
	var n := Node3D.new()
	var body := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.12
	cm.bottom_radius = 0.16
	cm.height = 0.4
	body.mesh = cm
	body.material_override = M["ember"]
	n.add_child(body)
	var cap := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.36, 0.2, 0.36)
	cap.mesh = pm
	cap.material_override = M["lead"]
	cap.position.y = 0.3
	n.add_child(cap)
	_light(Vector3(0, 0.1, 0), Color("ffc27a"), 1.8, 5.0, n)
	return n


# --- EAST WINDOW & HEIST -------------------------------------------------------------------------

func _build_east_and_heist() -> void:
	# end wall with the east window (x -9..9, y 6.3..24.3) and a sill outward
	_block(Vector3(-16.5, -12, -122), Vector3(16.5, 6.3, -121), "glass_wall")
	_block(Vector3(-16.5, 6.3, -122), Vector3(-9, 26, -121), "glass_wall")
	_block(Vector3(9, 6.3, -122), Vector3(16.5, 26, -121), "glass_wall")
	_block(Vector3(-9, 24.3, -122), Vector3(9, 26, -121), "glass_wall")
	_block(Vector3(-2.5, 5.9, -124.5), Vector3(2.5, 6.3, -122), "glass_floor")
	_east_mesh = _window("east", Vector3(0, 15.3, -121.5), Vector2(13.5, 18), Vector3(0, 0, 1), "win_east")
	(windows["east"] as ShaderMaterial).set_shader_parameter(&"figure_r", Vector2(0.0, 0.0))
	_receptor("east", Vector3(0, 15.3, -121.2), GlassOptics.WHITE, Vector3(18, 20, 0.6), _shatter)
	var ek := _spot(Vector3(0, 22, -132), Vector3(0, 2.5, -98), Color.WHITE, 16.0, 26.0, 60.0)
	ek.light_projector = load("res://wings/glass/textures/win_east.png")
	ek.light_volumetric_fog_energy = 1.4
	# the side lancets' blue spills back across the east wall round the great window
	var wash := _spot(Vector3(0, 3, -100), Vector3(0, 14, -121.5), Color(0.3, 0.45, 1.0), 16.0, 50.0, 40.0)
	wash.light_volumetric_fog_energy = 0.0
	# the museum pedestal glazed into every scene, here for real, holding the fourth sun
	_frag_spot = Node3D.new()
	_frag_spot.position = Vector3(0, 6.3, -123.3)
	geo.add_child(_frag_spot)
	var ped := _model("pedestal")
	if ped == null:
		ped = _block(Vector3(-0.4, 0, -0.4), Vector3(0.4, 1.05, 0.4), "museum_white", false, _frag_spot)
	else:
		_frag_spot.add_child(ped)
	var shard := _model("fourth_sun")
	shard.position.y = 1.5
	shard.name = "Shard"
	_frag_spot.add_child(shard)
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the Fourth Sun"
	_fragment.visual = shard
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.7
	cs.shape = sph
	_fragment.add_child(cs)
	_fragment.position.y = 1.4
	_frag_spot.add_child(_fragment)
	_fragment.picked.connect(_start_heist)
	uses["fragment"] = _fragment
	pts["sill"] = Vector3(0, 6.3, -122.2)
	pts["fragment"] = Vector3(0, 6.3, -122.4)
	# escape platforms out in the sky, joined by heliostat beams that die one by one
	var plats := [Vector3(7, 5.5, -136), Vector3(2, 4.5, -150), Vector3(-6, 3.5, -163), Vector3(-8, 2.5, -178)]
	var prev := Vector3(0, 6.3, -124.5)
	var posts := {"pier_shaft": [], "pier_capital": []}
	for i in plats.size():
		var p: Vector3 = plats[i]
		_block(p + Vector3(-2, -0.5, -2), p + Vector3(2, 0, 2), "glass_floor" if i < 3 else "glass_gold")
		_pier_xf(posts, p + Vector3(0, -14, 0), p.y - 0.5, [p.y - 0.5], 1.2)
		var from := prev + Vector3(0, -0.07, -0.08)
		var to := p + Vector3(0.3 * signf(prev.x - p.x), -0.07, 2.0)
		_source("h%d" % i, from, to, GlassOptics.GOLD if i % 2 == 0 else GlassOptics.RED, false)
		pts["h%d" % i] = p
		prev = p + Vector3(0, 0, -2.0)
	_mm("pier_shaft", posts["pier_shaft"], {"glass_gold_m": "glass_red_m"})
	_mm("pier_capital", posts["pier_capital"])
	var ex: Vector3 = plats[3]
	var frame := _model("frame_exit")
	if frame == null and ResourceLoader.exists("res://hub/models/frame.glb"):
		frame = MaterialLib.instance("res://hub/models/frame.glb")
	if frame:
		frame.position = ex + Vector3(0, 0, -1.5)
		geo.add_child(frame)
	_light(ex + Vector3(0, 2, 0), Color("ffd98a"), 2.0, 8.0)
	_zone(ex + Vector3(-2, 0, -2), ex + Vector3(2, 3, 1), func() -> void:
		if heist_on:
			heist_on = false
			Audio.sfx(load(SND + "pane_restore.ogg"), null, 0.0)
			finish())
	_catch(Vector3(-20, -6, -190), Vector3(20, -5, -124))
	_placard(Vector3(4.2, 4.0, -120.4), Vector3(0, 0, 1), "The east window", "Recent", "Stained glass, the Curator's own glazing", "214.6",
		"A procession around an empty pedestal. It admits only the light of every saint at once, which the Curator considered impossible to arrange.")


# --- PROVENANCES & CHECKPOINTS -------------------------------------------------------------------

func _build_provenances() -> void:
	_prov_spots["face"] = Vector3(14.2, 9.6, -50)
	pts["face"] = Vector3(13.5, 9, -51.5)
	pts["triforium_face"] = Vector3(12.6, 9, -52)


func _spawn_provenance(id: String) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var at: Vector3 = _prov_spots[id]
	var mesh := _model("prov_" + id)
	mesh.scale = Vector3.ONE * 1.6  # hand-sized, but readable from a few metres
	mesh.position = at
	geo.add_child(mesh)
	var spin := mesh.create_tween().set_loops()
	spin.tween_property(mesh, "rotation:y", TAU, 4.0).as_relative()
	var pick := Pickup.new()
	pick.kind = &"provenance"
	pick.item_id = StringName(id)
	pick.prompt = "Take: " + String((provenances().filter(func(p: Dictionary) -> bool: return p["id"] == id)[0] as Dictionary)["name"])
	pick.visual = mesh
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.5
	cs.shape = sph
	pick.add_child(cs)
	pick.position = at
	geo.add_child(pick)
	uses["prov_" + id] = pick
	_light(at + Vector3(0, 0.4, 0), Color("e8b54a"), 0.8, 3.0)


func _build_checkpoints() -> void:
	var cps := {
		"start": [Vector3(0, 0.05, 14), Vector3(0, 0, 0)],
		"cloister_gap": [Vector3(14.2, 0.05, -8.5), Vector3(0, 0, -14)],
		"nave": [Vector3(0, 0.05, -24), Vector3(0, 0, -40)],
		"lip": [Vector3(-1, 0.05, -31.5), Vector3(-1.5, 0, -45)],
		"p1": [Vector3(-1.5, 0.05, -45.5), Vector3(2.5, 0, -60)],
		"p2": [Vector3(2.5, 0.05, -61), Vector3(0, 2.5, -85)],
		"choir": [Vector3(0, 2.55, -84), Vector3(0, 2.5, -100)],
		"crypt": [Vector3(-11, -7.95, -114), Vector3(0, -8, -92)],
		"passage": [Vector3(-17.5, -7.95, -80), Vector3(-17.5, -8, -40)],
		"tower": [Vector3(-17.5, -7.95, -28.5), Vector3(-25, -8, -26)],
		"roof": [Vector3(-19, 16.05, -36), Vector3(-19, 16, -80)],
		"rose_balcony": [HALL + Vector3(25.8, 0.05, 0), HALL],
		"rose_dais": [HALL + Vector3(-16.5, 0.05, 0), HALL],
		"triforium": [Vector3(-14, 9.05, -106), Vector3(0, 2.5, -100)],
		"heist": [Vector3(0, 6.35, -122.2), Vector3(7, 5.5, -136)],
	}
	var node := Node3D.new()
	node.name = "Checkpoints"
	add_child(node)
	for id: String in cps:
		var c := Checkpoint.new()
		c.id = StringName(id)
		c.name = id
		var at: Vector3 = cps[id][0]
		var look: Vector3 = cps[id][1]
		var f := Vector3(look.x - at.x, 0, look.z - at.z).normalized()
		c.transform = Transform3D(Basis.looking_at(f, Vector3.UP), at)
		c.radius = 2.0
		node.add_child(c)
	(node.get_node("crypt") as Checkpoint).toast = "Below the choir, the original glazing waits face-down."
	(node.get_node("roof") as Checkpoint).radius = 3.0


# --- MUSIC (follows position twice a second; zones would double up at seams) -------------------

func _music_for(p: Vector3) -> void:
	var want: StringName
	if heist_on:
		want = &"heist"
	elif p.y < -3.0:
		want = &"crypt"
	elif p.distance_to(HALL) < 32.0:
		want = &"rose"
	elif p.x < -16.0 and p.y > 10.0:
		want = &"roof"
	else:
		want = &"nave"
	if want == _music_now:
		return
	_music_now = want
	var stems: Array[AudioStream] = []
	match want:
		&"nave":
			for n: String in ["nave_0", "nave_1", "nave_2"]:
				stems.append(load(SND + n + ".ogg"))
			Audio.play_music(stems, 4.0, 0.2 + 0.4 * float(Quest.is_done(&"light")))
			Audio.play_ambience(load(SND + "amb_glass.ogg"))
		&"crypt":
			for n: String in ["crypt_0", "crypt_1"]:
				stems.append(load(SND + n + ".ogg"))
			Audio.play_music(stems, 4.0, 0.3)
			Audio.play_ambience(load(SND + "amb_crypt.ogg"))
		&"roof":
			for n: String in ["nave_0", "nave_2"]:
				stems.append(load(SND + n + ".ogg"))
			Audio.play_music(stems, 6.0, 0.6)
			Audio.play_ambience(load(SND + "wind_loop.ogg"), 3.0, -10.0)
		&"rose":
			for n: String in ["rose_0", "rose_1"]:
				stems.append(load(SND + n + ".ogg"))
			Audio.play_music(stems, 5.0, 0.0)
			Audio.play_ambience(load(SND + "amb_glass.ogg"))
		&"heist":
			for n: String in ["heist_0", "heist_1"]:
				stems.append(load(SND + n + ".ogg"))
			Audio.play_music(stems, 0.5, 1.0)


# =============================================================================================
# Progress

func _apply_progress() -> void:
	for id: StringName in [&"azure", &"ruby", &"verdance"]:
		if Quest.is_step_done(&"saints", id):
			_restore(id, true)
	if recall("gold_gate", false) or Quest.is_step_done(&"saints", &"ruby"):
		_open_gold_gate(true)
	if Quest.is_done(&"saints"):
		_open_white_gate(true)
	if Quest.has_provenance(wing_id, &"veil") or recall("reliquary", false):
		_open_reliquary(true)
	_spawn_provenance("face")
	_spawn_provenance("iron")
	lantern_carried = bool(recall("lantern", false)) and not Quest.is_step_done(&"east", &"lens")
	if recall("sky", false):
		sky_mat.set_shader_parameter(&"haze", 0.0)
		_onlooker_mat.set_shader_parameter(&"reveal", 1.0)
	if Quest.is_step_done(&"east", &"widow"):
		rose.set_phase(3)
		_rose_dark(true)
	elif lantern_carried:
		rose.set_phase(2)
		_rose_dark(true)
	if lantern_carried:
		_hold_lantern(true)
	if Quest.is_step_done(&"east", &"lens"):
		_place_lantern(true)
	if Quest.is_step_done(&"east", &"shatter"):
		_shatter(true)
	_update_fragment()
	(uses["lens_holder"] as Interactable).enabled = lantern_carried
	(uses["lantern"] as Interactable).enabled = not lantern_carried and not Quest.is_step_done(&"east", &"widow")


func _restore(id: StringName, instant: bool = false) -> void:
	var sid := String(id)
	if not instant:
		if Quest.is_step_done(&"saints", id):
			return
		complete_step(&"saints", id)
		Audio.sfx(load(SND + "pane_restore.ogg"), null, -2.0, 0.6)
		toast({"azure": "Saint Azure is face-up. High in the choir, her window remembers her.",
			"ruby": "Saint Ruby is face-up. Her window above the choir is hers again.",
			"verdance": "Saint Verdance is face-up. Green, which is gold and blue agreeing."}[sid], "Restored")
	var pm: ShaderMaterial = windows["pane_" + sid]
	var t := create_tween().set_parallel()
	t.tween_property(pm, "shader_parameter/dark", 0.0, 0.1 if instant else 2.0)
	var wm: ShaderMaterial = windows[sid]
	t.tween_property(wm, "shader_parameter/edited", 0.0, 0.1 if instant else 4.0)
	(srcs[sid] as GlassOptics.Source).on = true
	if not instant:
		_light(receptors[sid].global_position + Vector3(0, 1.5, 0), GlassOptics.color((receptors[sid] as GlassOptics.Receptor).want), 2.0, 6.0)
	if Quest.is_done(&"saints"):
		_open_white_gate(instant)


func _open_gold_gate(instant: bool = false) -> void:
	store("gold_gate", true)
	_open_gate("gold", instant)
	if not instant:
		toast("The gold gate admits gold. It was always going to.", "Colour-keyed")


func _open_white_gate(instant: bool = false) -> void:
	_open_gate("white", instant)
	if not instant:
		toast("All three saints face-up: the white gate in the crypt's west wall has opened.", "Restored")


func _open_gate(id: String, instant: bool) -> void:
	var g: MeshInstance3D = _gates[id]
	if not g.visible:
		return
	(g.get_child(0) as StaticBody3D).collision_layer = 0
	if instant:
		g.visible = false
		return
	Audio.sfx(load(SND + "gate_open.ogg"), g.global_position, 0.0, 0.5)
	var t := create_tween()
	t.tween_property(g, "position:y", g.position.y - 3.6, 2.0).set_trans(Tween.TRANS_SINE)
	t.tween_callback(func() -> void: g.visible = false)


func _open_reliquary(instant: bool = false) -> void:
	store("reliquary", true)
	if is_instance_valid(_reliquary_lid):
		if instant:
			_reliquary_lid.visible = false
		else:
			Audio.sfx(load(SND + "gate_open.ogg"), _reliquary_lid.global_position, -3.0, 0.5, 1.3)
			create_tween().tween_property(_reliquary_lid, "position:y", _reliquary_lid.position.y + 1.6, 1.5)
			toast("Violet: red and blue together. The reliquary of the veil opens to mourning.", "Reliquary")
	if not uses.has("prov_veil"):
		_spawn_provenance("veil")


# --- the jaw-drop ---------------------------------------------------------------------------------

func _reveal_sky() -> void:
	if recall("sky", false):
		return
	store("sky", true)
	_reveal_t0 = Time.get_ticks_msec() / 1000.0
	Audio.reveal(load(SND + "sky_reveal.ogg"), 2.2)
	var t := create_tween()
	t.tween_interval(2.0)
	t.tween_method(func(v: float) -> void: sky_mat.set_shader_parameter(&"haze", v), 1.0, 0.0, 3.5).set_trans(Tween.TRANS_SINE)
	t.tween_method(func(v: float) -> void: _onlooker_mat.set_shader_parameter(&"reveal", v), 0.0, 1.0, 5.0).set_trans(Tween.TRANS_SINE)
	t.tween_callback(func() -> void:
		Game.player.add_trauma(0.25)
		toast("The sky is one window. Something on the other side of it is looking in.", "The sky, glazed"))


# --- the Rose Widow -------------------------------------------------------------------------------

func _take_lantern() -> void:
	if lantern_carried:
		return
	lantern_carried = true
	store("lantern", true)
	(uses["lantern"] as Interactable).enabled = false
	Audio.sfx(load(SND + "going_dark.ogg"), null, 0.0, 0.6)
	rose.set_phase(2)
	_rose_dark(false)
	_hold_lantern(false)
	toast("She has gone dark. Only the old processional path remains, and only near her lantern.", "The Rose Widow")


func _rose_dark(instant: bool) -> void:
	var wm: ShaderMaterial = windows["rose"]
	var t := create_tween().set_parallel()
	t.tween_property(wm, "shader_parameter/dark", 0.9, 0.1 if instant else 3.0)
	for l: Light3D in _rose_lights:
		t.tween_property(l, "light_energy", 0.0, 0.1 if instant else 2.5)


func _hold_lantern(_instant: bool) -> void:
	var wl := geo.get_node_or_null("WidowLantern")
	if wl:
		wl.visible = false
	if _hand_lantern == null:
		_hand_lantern = _lantern_mesh()
		_hand_lantern.position = Vector3(0.32, -0.42, -0.6)
		_hand_lantern.scale = Vector3.ONE * 0.6
		Game.player.camera.add_child(_hand_lantern)
	_hand_lantern.visible = true
	(uses["lens_holder"] as Interactable).enabled = true


func _cross_rose() -> void:
	if Quest.is_step_done(&"east", &"widow") or rose.phase != 2:
		return
	rose.set_phase(3)
	complete_step(&"east", &"widow")
	Audio.sfx(load(SND + "pane_restore.ogg"), null, -2.0, 0.6)
	toast("Crossed. The path stays lit behind you, faintly, the way grief does.", "The Rose Widow")


func _place_lantern(instant: bool = false) -> void:
	if not instant:
		if not lantern_carried:
			toast("The cradle is empty. It is shaped for a lantern.", "The choir lens")
			return
		complete_step(&"east", &"lens")
		Audio.sfx(load(SND + "gate_open.ogg"), LENS_POS, 0.0, 0.5, 0.8)
		toast("The lantern sits in the lens. Turn the saints' mirrors toward it.", "The choir lens")
	lantern_carried = false
	store("lantern", false)
	if _hand_lantern:
		_hand_lantern.visible = false
	(uses["lens_holder"] as Interactable).enabled = false
	lens_choir.body.collision_layer = GlassOptics.OPTICS_LAYER
	if _lens_lantern == null:
		_lens_lantern = _lantern_mesh()
		_lens_lantern.position = LENS_POS
		geo.add_child(_lens_lantern)


# --- Escalation 3: the shatter --------------------------------------------------------------------

func _shatter(instant: bool = false) -> void:
	if shattered:
		return
	shattered = true
	(receptors["east"] as GlassOptics.Receptor).body.collision_layer = 0
	_west_door.visible = true
	(_west_door.get_child(0) as StaticBody3D).collision_layer = 1
	dials["d2"].jammed = true
	if not instant:
		complete_step(&"east", &"shatter")
		var wm: ShaderMaterial = windows["east"]
		var t := create_tween()
		t.tween_method(func(v: float) -> void: wm.set_shader_parameter(&"crack", v), 0.0, 1.0, 1.6)
		t.tween_callback(func() -> void:
			_east_mesh.visible = false
			_burst(Vector3(0, 15, -121.4))
			Audio.sfx(load(SND + "shatter.ogg"), Vector3(0, 12, -118), 3.0, 0.7)
			Game.player.add_trauma(0.6)
			toast("The east window is open. The wind through the hole will not stop. Behind you, the west door has sealed.", "The east window"))
	else:
		_east_mesh.visible = false
	_start_wind()
	_update_fragment()


func _burst(at: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.amount = 900
	p.lifetime = 3.5
	p.one_shot = true
	p.explosiveness = 0.95
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(8, 8, 0.2)
	pm.direction = Vector3(0, 0.2, 1)
	pm.spread = 50.0
	pm.initial_velocity_min = 4.0
	pm.initial_velocity_max = 14.0
	pm.gravity = Vector3(0, -12, 0)
	pm.angular_velocity_min = -720
	pm.angular_velocity_max = 720
	pm.scale_min = 0.6
	pm.scale_max = 1.8
	var grad := Gradient.new()
	grad.colors = PackedColorArray([Color("b22242"), Color("2b54c9"), Color("e8b54a"), Color("1a7a5e")])
	grad.offsets = PackedFloat32Array([0.0, 0.33, 0.66, 1.0])
	var gt := GradientTexture1D.new()
	gt.gradient = grad
	pm.color_initial_ramp = gt
	p.process_material = pm
	var q := PrismMesh.new()  # a thin triangular shard of coloured glass, not a square card
	q.size = Vector3(0.3, 0.32, 0.008)
	q.left_to_right = 0.3
	var qm := StandardMaterial3D.new()
	qm.vertex_color_use_as_albedo = true
	qm.emission_enabled = true
	qm.emission_energy_multiplier = 2.0
	qm.cull_mode = BaseMaterial3D.CULL_DISABLED
	qm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	q.material = qm
	p.draw_pass_1 = q
	p.position = at
	geo.add_child(p)
	p.emitting = true
	get_tree().create_timer(5.0).timeout.connect(p.queue_free)


func _start_wind() -> void:
	var holder := Node3D.new()
	holder.position = Vector3(0, 8, -118)
	geo.add_child(holder)
	Audio.emitter(load(SND + "wind_loop.ogg"), holder, 2.0, 30.0)
	_wind_fx = GPUParticles3D.new()
	_wind_fx.amount = 260
	_wind_fx.lifetime = 6.0
	_wind_fx.visibility_aabb = AABB(Vector3(-16, -10, -10), Vector3(32, 30, 110))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(8, 8, 1)
	pm.direction = Vector3(0, -0.05, 1)
	pm.spread = 8.0
	pm.initial_velocity_min = 10.0
	pm.initial_velocity_max = 18.0
	pm.gravity = Vector3.ZERO
	pm.scale_min = 0.6
	pm.scale_max = 1.4
	_wind_fx.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(0.03, 0.9)
	var qm := StandardMaterial3D.new()
	qm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	qm.albedo_color = Color(0.85, 0.9, 1.0, 0.18)
	qm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	qm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	var g := Gradient.new()  # a streak, not a bar: alpha feathers across and tapers to both ends
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(0.5, 0.0)
	gt.width = 8
	gt.height = 64
	qm.albedo_texture = gt
	q.material = qm
	_wind_fx.draw_pass_1 = q
	_wind_fx.position = Vector3(0, 12, -119)
	geo.add_child(_wind_fx)


func _wind_at(p: Vector3) -> Vector3:
	if not shattered:
		return Vector3.ZERO
	if absf(p.x) < 15.5 and p.z < -17.5 and p.z > -124.0 and p.y > -1.0:
		return Vector3(0, 0, 1.2)
	return Vector3.ZERO


# --- the heist ---------------------------------------------------------------------------------

func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.main_objectives_done() and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_frag_spot.visible = shattered or ready


func _start_heist() -> void:
	heist_on = true
	heist_t = 0.0
	for i in 4:
		(srcs["h%d" % i] as GlassOptics.Source).on = true
	_music_now = &""
	toast("Run. The suns are going out behind you, window by window.", "The heist")


func _heist_tick(dt: float) -> void:
	var before := heist_t
	heist_t += dt
	for i in 4:
		var dl: float = HEIST_DEADLINES[i]
		if before < dl and heist_t >= dl:
			(srcs["h%d" % i] as GlassOptics.Source).on = false
			Audio.sfx(load(SND + "going_dark.ogg"), null, -4.0, 0.5, 1.0 + i * 0.08)
			for k in 2:
				var id := "hist_%d" % (i * 2 + k) if i < 3 else ("w_n" if k == 0 else "ruby")
				if windows.has(id):
					create_tween().tween_property(windows[id], "shader_parameter/dark", 1.0, 1.2)
	_heist_dark = clampf(heist_t / 30.0, 0.0, 0.8)


func _heist_reset() -> void:
	heist_t = 0.0
	for i in 4:
		(srcs["h%d" % i] as GlassOptics.Source).on = true
	_heist_dark = 0.0


# =============================================================================================
# Per-frame

func _physics_process(delta: float) -> void:
	var p := Game.player
	if p == null:
		return
	var pos := p.global_position
	if _last_pos != Vector3.INF and pos.distance_to(_last_pos) > 6.0:
		_on_respawned()
	_last_pos = pos
	var dt := delta * Game.world_time_scale
	if heist_on:
		_heist_tick(dt)
	if rose.phase == 2:
		var lp := rose.to_local(pos)
		rose.lantern_pos = Vector3(lp.x, 0, lp.z)
		for i in rose.sconces.size():
			var on: bool = Vector2(lp.x - rose.sconces[i].x, lp.z - rose.sconces[i].z).length() < 2.4
			if on:
				(_sconce_lights[i] as OmniLight3D).light_energy = 2.5
	rose.set_active(pos.distance_to(HALL) < 45.0)


func _process(_delta: float) -> void:
	if Game.player and Engine.get_process_frames() % 30 == 0:
		_music_for(Game.player.global_position)
	_look_for(get_viewport().get_camera_3d())
	if is_instance_valid(_frag_spot) and _frag_spot.visible:
		var s := _frag_spot.get_node_or_null("Shard")
		if s:
			s.rotate_y(_delta * 0.8)


## Look follows the camera (not the player, so shots and cinematics agree): the sun exists only out of
## doors; the Widow's hall is truly black while she is dark; the onlooker sways and its shadow passes
## over the sun.
func _look_for(cam: Camera3D) -> void:
	if cam == null:
		return
	var c := cam.global_position
	var outdoors := (c.y > 14.5 and c.x < -16.2 and c.distance_to(HALL) > 30.0) or c.z < -121.6
	_sun.visible = outdoors
	var in_hall := c.distance_to(HALL) < 31.0
	var black := in_hall and rose.phase == 2
	env.ambient_light_energy = 0.0 if black else AMBIENT
	env.volumetric_fog_density = 0.004 if black or c.y < -2.0 else 0.009  # the crypt stays clear and dark
	# the eye adapts: the crypt, the cloister and the tower stair are lit only by their own glass
	var ex := 2.1
	if c.y < -2.0:
		ex = 2.8
	elif c.z > -17.5:
		ex = 2.3
	elif c.x < -16.2 and c.y < 14.5 and not in_hall:
		ex = 4.3
	env.tonemap_exposure = ex
	sky_mat.set_shader_parameter(&"dark", 0.97 if black else _heist_dark)
	(_model_mat("glass_wall_uv")).set_shader_parameter(&"dark", 1.0 if black else 0.0)
	if _rose_pane_mat:
		_rose_pane_mat.set_shader_parameter(&"rose_t", rose.t)
	if bool(recall("sky", false)):
		# it leans over the roof walk, then drifts across the suns and back (period 50 s)
		var t := Time.get_ticks_msec() / 1000.0 - _reveal_t0
		var sway := 0.5 - 0.5 * cos(t * TAU / 50.0)
		var e := Vector3(-0.39, 0.8 + 0.06 * sin(t * TAU / 23.0), -0.92).rotated(Vector3.UP, -0.78 * sway).normalized()
		_eye_dir = e
		_onlooker.visible = not black
		_onlooker.global_transform = Transform3D(Basis.looking_at(e), c + e * 300.0)
		# its shadow: when the head passes before the sun, the whole Kingdom dims
		var sun_dir := _sun.global_basis.z
		var cover := smoothstep(0.82, 0.97, e.dot(sun_dir.normalized()))
		_sun.light_energy = lerpf(1.3, 0.15, cover)


func _on_respawned() -> void:
	if heist_on:
		_heist_reset()
	if rose.phase == 2:
		rose.lantern_age = 0.0
