extends Node3D
## The Long Shadow's art pass: models over the code-built solids, the lighting recipe per area, wet
## ground, steam and rain, the mono pass and per-area exposure. Gameplay stays in noir.gd: colliders,
## the lights in `shadow_lights` (the only light the ShadowField counts) and every interactable keep
## their positions. Everything here is visual; decorative lights are kept out of `shadow_lights`, dim,
## and placed where the rule already says "lit" or where the pool is too faint to read as light.
##
## Lighting recipe (key / practicals / fog / reflections / exposure):
##   alley     moon raking down the west wall; the back door's caged bulb; neon EAT spill from the street
##   street    two street lamps (gameplay) with volumetric cones; diner window glow; neon blade sign
##   roofs     moon key from behind the far roof; the train lamp (gameplay); lit skyline through fog
##   plaza     one hard spot on the figures (gameplay); bar neon on the east wall; cobble reflections
##   precinct  desk + swing lamps (gameplay); moonlight striped through the blinds (projector)
##   cinema    three searchlights with volumetric beams (gameplay); the screen's glow; marquee bulbs
##   booth     the projector beams through fog; the frame on its lightbox
## Fog: one volumetric field for the whole city (light shafts) plus depth fog for the grey distance.
## Reflections: SSR plus one box reflection probe per area, captured once.

const MODELS := "res://wings/noir/models/"
const MATS := "res://wings/noir/materials/"
## Tonemap exposure per area, set from the current camera (tuned against shot_check.py).
const EXPOSURE := {"alley": 3.8, "street": 2.6, "roofs": 3.4, "plaza": 3.7, "precinct": 3.7, "cinema": 3.4, "booth": 4.6}
## Volumetric fog density per area: thick outdoors for the cones, thinner in rooms so they keep contrast.
## depth fog per area: indoors it is cut so the blacks stay black
const DEPTH_FOG := {"alley": 0.016, "street": 0.016, "roofs": 0.005, "plaza": 0.016, "precinct": 0.0, "cinema": 0.012, "booth": 0.006}
const FOG := {"alley": 0.03, "street": 0.03, "roofs": 0.014, "plaza": 0.03, "precinct": 0.006, "cinema": 0.016, "booth": 0.018}

var wing: Node3D
var env: Environment
var mono: ShaderMaterial
var _rain: GPUParticles3D
var _fan: Node3D
var _dirs: Array = []
var _beams: Array = []  # [light, cone] pairs, Compatibility only
var _compat := false  # WebGL 2 / gl_compatibility: no volumetric fog, so the exposure is lifted to compensate


## MSAA costs several ms at 1440p with this many lights; SMAA keeps edges clean for a fraction.
## The fog froxel grid drops from 64^3 to 48^3: the cones stay soft and it saves ~1.5 ms at 1440p.
static func enter_quality(vp: Viewport) -> void:
	if vp.msaa_3d != Viewport.MSAA_DISABLED:
		vp.msaa_3d = Viewport.MSAA_DISABLED
		vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_SMAA
	RenderingServer.environment_set_volumetric_fog_volume_size(48, 48)


static func exit_quality() -> void:
	RenderingServer.environment_set_volumetric_fog_volume_size(
		int(ProjectSettings.get_setting("rendering/environment/volumetric_fog/volume_size", 64)),
		int(ProjectSettings.get_setting("rendering/environment/volumetric_fog/volume_depth", 64)))


func build(w: Node3D) -> void:
	wing = w
	name = "Dressing"
	_dirs = [MATS.trim_suffix("/"), MaterialLib.CORE_DIR]
	w.add_child(self)
	_environment()
	_alley()
	_street()
	_plaza()
	_roofs()
	_precinct()
	_cinema()
	_booth()
	_sound()
	_skyline()
	_probes()
	_compat_beams()


# ---------- helpers ----------

func mat(n: String) -> Material:
	return load(MATS + n + ".tres")


func model(parent: Node, n: String, pos: Vector3, yaw := 0.0, scl := Vector3.ONE) -> Node3D:
	var node: Node3D = (load(MODELS + n + ".glb") as PackedScene).instantiate()
	MaterialLib.apply(node, _dirs)
	node.position = pos
	node.rotation_degrees.y = yaw
	node.scale = scl
	parent.add_child(node)
	return node


func mesh_of(n: String) -> Mesh:
	var node: Node3D = (load(MODELS + n + ".glb") as PackedScene).instantiate()
	var found := node.find_children("*", "MeshInstance3D", true, false)
	var mesh: Mesh = (found[0] as MeshInstance3D).mesh.duplicate() if not found.is_empty() else null
	node.free()
	if mesh:
		for i in mesh.get_surface_count():
			var sm := mesh.surface_get_material(i)
			var m := MaterialLib.lookup(sm.resource_name, _dirs) if sm else null
			if m:
				mesh.surface_set_material(i, m)
	return mesh


static func xf(pos: Vector3, yaw := 0.0, scl := Vector3.ONE) -> Transform3D:
	return Transform3D(Basis(Vector3.UP, deg_to_rad(yaw)) * Basis.from_scale(scl), pos)


## Repeats of one model as a MultiMesh: one draw per surface for every copy.
func mm(n: String, xforms: Array) -> MultiMeshInstance3D:
	var mesh := mesh_of(n)
	if mesh == null or xforms.is_empty():
		return null
	var m := MultiMesh.new()
	m.transform_format = MultiMesh.TRANSFORM_3D
	m.mesh = mesh
	m.instance_count = xforms.size()
	for i in xforms.size():
		m.set_instance_transform(i, xforms[i])
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = m
	add_child(mi)
	return mi


## A visual box (no collider): building masses behind facades, ceilings, roof surfaces.
func mass(a: Vector3, b: Vector3, m: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = (b - a).abs()
	mi.mesh = bm
	mi.position = (a + b) * 0.5
	mi.material_override = mat(m)
	add_child(mi)
	return mi


## A thin visual slab whose top is at y (roof membranes, pavements, the ground under the gap).
func surface(x0: float, x1: float, z0: float, z1: float, y: float, m: String) -> MeshInstance3D:
	return mass(Vector3(x0, y - 0.05, z0), Vector3(x1, y, z1), m)


## A solid's visual box, found by its collider's centre: hidden when a model replaces it.
func box_at(area: String, at: Vector3) -> MeshInstance3D:
	for b: Node in (wing.get("_areas") as Node).get_node(area).get_children():
		if b is StaticBody3D and (b as Node3D).position.distance_to(at) < 0.05:
			for c: Node in b.get_children():
				if c is MeshInstance3D:
					return c
	return null


func hide_box(area: String, at: Vector3) -> void:
	var mi := box_at(area, at)
	if mi:
		mi.visible = false


func _shadow_box(at: Vector3, size: Vector3, m: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	mi.position = at
	add_child(mi)


## Decorative light: never in `shadow_lights`, so it is never "lit" to the rule.
func omni(pos: Vector3, col: Color, energy: float, rng: float, shadows := false) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = col
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.6
	l.shadow_enabled = shadows
	l.light_volumetric_fog_energy = 0.6
	add_child(l)
	return l


func spot(from: Vector3, to: Vector3, col: Color, energy: float, angle: float, rng: float, shadows := true) -> SpotLight3D:
	var s := SpotLight3D.new()
	s.light_color = col
	s.light_energy = energy
	s.spot_angle = angle
	s.spot_range = rng
	s.spot_attenuation = 0.8
	s.shadow_enabled = shadows
	s.light_volumetric_fog_energy = 2.0
	add_child(s)
	s.look_at_from_position(from, to, Vector3.UP if absf(from.direction_to(to).y) < 0.98 else Vector3.FORWARD)
	return s


## Bays of a facade along a wall face. `face` is the outward normal (into the walkable space).
func facade_run(z0: float, z1: float, x: float, face: float, y := 0.0, kinds := ["facade_a", "facade_c", "facade_b"]) -> void:
	var by_kind := {}
	var n := int(round(absf(z1 - z0) / 3.0))
	for i in n:
		var z := minf(z0, z1) + 1.5 + i * 3.0
		var k: String = kinds[(i * 7 + int(absf(x)) * 3) % kinds.size()]
		by_kind.get_or_add(k, []).append(xf(Vector3(x, y, z), 90.0 * face))
	for k: String in by_kind:
		mm(k, by_kind[k])


## Bays along a face running in X (north/south faces). `face` +1 faces +Z, -1 faces -Z.
func facade_run_x(x0: float, x1: float, z: float, face: float, y := 0.0, kinds := ["facade_a", "facade_b", "facade_c"]) -> void:
	var by_kind := {}
	var n := int(round(absf(x1 - x0) / 3.0))
	for i in n:
		var x := minf(x0, x1) + 1.5 + i * 3.0
		var k: String = kinds[(i * 5 + int(absf(z))) % kinds.size()]
		by_kind.get_or_add(k, []).append(xf(Vector3(x, y, z), 0.0 if face > 0 else 180.0))
	for k: String in by_kind:
		mm(k, by_kind[k])


## Steam rising from a grate: soft billboards, unshaded and faint so they read in the lamp light.
func steam(pos: Vector3, amount := 18, rise := 1.0) -> void:
	var p := GPUParticles3D.new()
	p.position = pos
	p.amount = amount
	p.lifetime = 5.0
	p.preprocess = 5.0
	p.visibility_aabb = AABB(Vector3(-3, 0, -3), Vector3(6, 7, 6))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.3
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 18.0
	pm.initial_velocity_min = 0.35 * rise
	pm.initial_velocity_max = 0.7 * rise
	pm.gravity = Vector3(0.12, 0.05, 0)
	pm.angle_min = -180.0
	pm.angle_max = 180.0
	pm.scale_min = 1.0
	pm.scale_max = 1.6
	var sc := CurveTexture.new()
	var c := Curve.new()
	c.add_point(Vector2(0, 0.4))
	c.add_point(Vector2(1, 1.6))
	sc.curve = c
	pm.scale_curve = sc
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 0))
	g.set_color(1, Color(1, 1, 1, 0))
	g.add_point(0.2, Color(1, 1, 1, 1))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	pm.color_ramp = gt
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(1.6, 1.6)
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_color = Color(0.62, 0.63, 0.66, 0.07)
	var tex := GradientTexture2D.new()
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	var tg := Gradient.new()
	tg.set_color(0, Color(1, 1, 1, 1))
	tg.set_color(1, Color(1, 1, 1, 0))
	tex.gradient = tg
	m.albedo_texture = tex
	m.proximity_fade_enabled = true
	m.proximity_fade_distance = 0.8
	q.material = m
	p.draw_pass_1 = q
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)


# ---------- environment ----------

func _environment() -> void:
	env = (wing.get_node("WorldEnvironment") as WorldEnvironment).environment
	_compat = RenderingServer.get_current_rendering_method() == "gl_compatibility"
	# the sky: black overhead, the city's glow on the low cloud at the horizon, so roofs and towers stand as silhouettes
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.025, 0.026, 0.03)
	sky_mat.sky_horizon_color = Color(0.3, 0.3, 0.32)
	sky_mat.sky_curve = 0.3
	sky_mat.ground_horizon_color = Color(0.3, 0.3, 0.32)
	sky_mat.ground_bottom_color = Color(0.05, 0.05, 0.055)
	sky_mat.sun_angle_max = 0.0
	sky_mat.sky_energy_multiplier = 1.0
	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.process_mode = Sky.PROCESS_MODE_QUALITY  # static: the radiance map is built once
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	env.sky = sky
	env.background_mode = Environment.BG_SKY
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.5, 0.52, 0.58)
	env.ambient_light_energy = 0.08
	env.reflected_light_source = Environment.REFLECTION_SOURCE_BG
	# Filmic is per channel: a pure red tube stays red where AgX would bleach it toward pink-white
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_white = 6.0
	env.tonemap_exposure = 1.2
	env.ssr_enabled = true
	env.ssr_max_steps = 32
	env.ssr_fade_in = 0.08
	env.ssr_fade_out = 1.5
	env.ssr_depth_tolerance = 0.4
	env.ssao_enabled = false
	env.glow_enabled = true
	env.glow_intensity = 0.6
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 1.2
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.set_glow_level(0, 0.0)
	env.set_glow_level(1, 0.3)
	env.set_glow_level(2, 1.0)
	env.set_glow_level(3, 0.7)
	env.set_glow_level(4, 0.4)
	# depth fog: the far city goes grey, as in the plates
	env.fog_enabled = true
	env.fog_light_color = Color(0.3, 0.31, 0.34)
	env.fog_light_energy = 1.0
	env.fog_density = 0.016
	env.fog_sky_affect = 0.35
	env.fog_aerial_perspective = 0.0
	# volumetric fog: the lamps' cones and the searchlight beams
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.022
	env.volumetric_fog_albedo = Color(0.8, 0.8, 0.82)
	env.volumetric_fog_emission = Color(0.004, 0.004, 0.005)
	env.volumetric_fog_anisotropy = 0.55
	env.volumetric_fog_length = 48.0
	env.volumetric_fog_detail_spread = 1.6
	env.volumetric_fog_ambient_inject = 0.0
	env.volumetric_fog_sky_affect = 0.0
	# moon: a cool, dim key from the south-west, high enough to rake facades and throw long shadows
	var moon := DirectionalLight3D.new()
	moon.name = "Moon"
	moon.light_color = Color(0.78, 0.84, 1.0)
	moon.light_energy = 0.75
	moon.shadow_enabled = true
	moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	moon.directional_shadow_max_distance = 45.0
	moon.light_volumetric_fog_energy = 0.5
	add_child(moon)
	moon.look_at_from_position(Vector3.ZERO, Vector3(0.55, -0.62, -0.56), Vector3.UP)
	# mono: everything to silver grey except saturated, bright light (neon, the frame)
	var layer := CanvasLayer.new()
	layer.layer = 49
	var rect := ColorRect.new()
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mono = ShaderMaterial.new()
	mono.shader = load("res://wings/noir/shaders/noir_mono.gdshader")
	rect.material = mono
	layer.add_child(rect)
	add_child(layer)
	# rain around the camera, outdoors only (see _process)
	_rain = GPUParticles3D.new()
	_rain.amount = 1800
	_rain.lifetime = 1.0
	_rain.preprocess = 1.0
	_rain.local_coords = false
	_rain.visibility_aabb = AABB(Vector3(-14, -14, -14), Vector3(28, 28, 28))
	var rp := ParticleProcessMaterial.new()
	rp.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	rp.emission_box_extents = Vector3(12, 0.5, 12)
	rp.direction = Vector3(0.05, -1, 0)
	rp.spread = 2.0
	rp.initial_velocity_min = 13.0
	rp.initial_velocity_max = 16.0
	rp.gravity = Vector3.ZERO
	_rain.process_material = rp
	var q := QuadMesh.new()
	q.size = Vector2(0.006, 0.3)
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.billboard_keep_scale = true
	# a streak, not a bar: alpha tapers to both ends, and drops near the lens (exposure runs 2.6-3.8 outside)
	m.albedo_color = Color(0.32, 0.33, 0.36, 0.1)
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.45, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 0), Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	gt.width = 4
	gt.height = 64
	m.albedo_texture = gt
	m.distance_fade_mode = BaseMaterial3D.DISTANCE_FADE_PIXEL_ALPHA
	m.distance_fade_min_distance = 0.6
	m.distance_fade_max_distance = 3.0
	q.material = m
	_rain.draw_pass_1 = q
	_rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_rain)


func _probes() -> void:
	for p: Array in [[Vector3(0, 4, -10), Vector3(10, 9, 23), false], [Vector3(0, 5, -36), Vector3(10, 11, 33), false],
			[Vector3(0, 4, -59), Vector3(12, 9, 15), false], [Vector3(9.25, 1.8, -59.5), Vector3(6.6, 3.6, 13.6), true],
			[Vector3(0, 4.5, -78), Vector3(12.5, 9.2, 24.5), true], [Vector3(0, 2, -95), Vector3(8.5, 4.1, 8.5), true],
			[Vector3(-19, 7, -29), Vector3(24, 14, 16), false]]:
		var rp := ReflectionProbe.new()
		rp.position = p[0]
		rp.size = p[1]
		rp.box_projection = true
		rp.interior = p[2]
		rp.update_mode = ReflectionProbe.UPDATE_ONCE
		rp.max_distance = 80.0
		add_child(rp)


## Compatibility has no volumetric fog, so a spot's fog cone is a faint additive mesh cone instead.
func _compat_beams() -> void:
	if not _compat:
		return
	# alpha falls off toward the far end and toward the rim (view-facing centre is brightest), so no hard edge
	var sh := Shader.new()
	sh.code = "shader_type spatial;\nrender_mode unshaded, blend_add, cull_disabled, depth_draw_never;\n" \
		+ "uniform vec3 tint : source_color = vec3(0.85, 0.85, 0.9);\nuniform float strength = 0.2;\nuniform float height = 1.0;\n" \
		+ "varying float along;\nvoid vertex() { along = VERTEX.y / height + 0.5; }\n" \
		+ "void fragment() {\n\tfloat centre = pow(abs(dot(normalize(NORMAL), normalize(VIEW))), 1.5);\n" \
		+ "\tfloat fade = pow(1.0 - clamp(along, 0.0, 1.0), 1.5);\n\tALBEDO = tint;\n\tALPHA = strength * centre * fade;\n}\n"
	for s: Node in wing.find_children("*", "SpotLight3D", true, false):
		var l := s as SpotLight3D
		if l.light_volumetric_fog_energy <= 0.0:
			continue
		var cm := CylinderMesh.new()
		cm.top_radius = l.spot_range * tan(deg_to_rad(l.spot_angle))  # wide end, far from the lamp
		cm.bottom_radius = 0.02
		cm.height = l.spot_range
		cm.cap_top = false
		cm.cap_bottom = false
		var m := ShaderMaterial.new()
		m.shader = sh
		m.set_shader_parameter("height", l.spot_range)
		var mi := MeshInstance3D.new()
		mi.mesh = cm
		mi.material_override = m
		mi.rotation_degrees.x = -90.0  # local +Y points down the spot's -Z
		mi.position = Vector3(0, 0, -l.spot_range * 0.5)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		l.add_child(mi)
		_beams.append([l, mi])


func area_of(at: Vector3) -> String:
	if at.z > -20.5:
		return "alley"
	if at.x < -4.6 and at.z > -45.0:
		return "roofs"
	if at.z > -52.0:
		return "street"
	if at.z > -66.0:
		return "precinct" if at.x > 5.0 else "plaza"
	return "cinema" if at.z > -90.6 else "booth"


func _process(delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	var at := cam.global_position
	var a := area_of(at)
	# Compatibility loses the volumetric haze and the reflections that lift the dark rooms, so it reads darker: lift it
	env.tonemap_exposure = move_toward(env.tonemap_exposure, EXPOSURE[a] * (1.5 if _compat else 1.0), delta * 2.0)
	env.volumetric_fog_density = move_toward(env.volumetric_fog_density, FOG[a], delta * 0.02)
	env.fog_density = move_toward(env.fog_density, DEPTH_FOG[a], delta * 0.02)
	if _fan:
		_fan.rotate_y(delta * 2.2)
	var outdoors := a in ["alley", "street", "plaza", "roofs"]
	_rain.emitting = outdoors
	_rain.visible = outdoors
	_rain.global_position = at + Vector3(0, 9, 0)
	for p: Array in _beams:  # a cone follows its light: off when the light is dimmed or off
		(p[1] as Node3D).visible = (p[0] as Light3D).is_visible_in_tree() and (p[0] as Light3D).light_energy > 0.0


# ---------- areas ----------

func _alley() -> void:
	# the end wall behind the entry: brick and a facade so the alley closes
	facade_run(0.5, -20.0, -4.0, 1.0, 0.0, ["facade_c", "facade_a", "facade_b"])
	facade_run(0.5, -20.0, 4.0, -1.0, 0.0, ["facade_b", "facade_c", "facade_a"])
	facade_run_x(-4.5, 4.5, 1.0, -1.0, 0.0, ["facade_low", "facade_a", "facade_low"])
	hide_box("Alley", Vector3(-4.5, 3, -10))
	hide_box("Alley", Vector3(4.5, 3, -10))
	# back wall (the latch face): a steel back door in stone, the dark face either side
	model(self, "back_door", Vector3(-2.6, 0, -20.5))
	omni(Vector3(-2.6, 2.9, -20.1), Color(1.0, 0.86, 0.62), 1.8, 3.6)
	model(self, "fire_escape", Vector3(-4.0, 0, -9.0), 90.0)
	model(self, "fire_escape", Vector3(4.0, 0, -15.5), -90.0)
	# the cover crate: two crates stacked to the collider's 1.2 x 0.8 x 1.2
	hide_box("Alley", Vector3(-3.2, 0.4, -12))
	model(self, "crate", Vector3(-3.2, 0, -12), 8.0, Vector3(0.8, 0.88, 0.8))
	model(self, "crate", Vector3(-3.55, 0, -13.25), -14.0, Vector3(0.6, 0.6, 0.6))
	mm("trash_can", [xf(Vector3(-3.55, 0, -18.6), 20.0), xf(Vector3(-3.5, 0, -17.8), -35.0), xf(Vector3(3.55, 0, -6.2), 60.0)])
	model(self, "manhole", Vector3(0.6, 0.01, -14.0))
	steam(Vector3(0.6, 0.05, -14.0))
	model(self, "lamp_bracket", Vector3(4.0, 3.6, -5.0), -90.0)
	omni(Vector3(3.15, 3.35, -5.0), Color(1.0, 0.9, 0.7), 2.4, 5.5)
	# a second bracket across from the cover crate: the crate stays in the dark, the cobbles shine
	model(self, "lamp_bracket", Vector3(4.0, 3.3, -10.0), -90.0)
	omni(Vector3(3.15, 3.05, -10.0), Color(1.0, 0.9, 0.7), 3.4, 6.0)


func _street() -> void:
	# east: the diner run with the upper storeys above it; west: brick bays around the ramp gap
	var dz := []
	for i in 7:
		dz.append(xf(Vector3(4.0, 0, -23.0 - i * 4.0), -90.0))
	mm("diner_front", dz)
	# the last 2.6 m before the plaza (past the diner's end) was open into the void behind the street
	model(self, "shopfront", Vector3(4.0, 0, -50.5), -90.0, Vector3(0.7, 1.0, 1.0))
	facade_run(-21.0, -51.0, 4.0, -1.0, 4.4)
	mass(Vector3(4.35, 4.4, -52.0), Vector3(14.0, 18.0, -20.5), "brick_dark")
	hide_box("DinerStreet", Vector3(4.5, 3, -36))
	facade_run(-20.0, -26.0, -4.0, 1.0)
	facade_run(-31.0, -52.0, -4.0, 1.0)
	hide_box("DinerStreet", Vector3(-4.5, 3, -23.25))
	hide_box("DinerStreet", Vector3(-4.5, 3, -41.25))
	# blocks behind the west bays, and over the stair passage: the el runs into this building
	mass(Vector3(-13.5, 0, -20.0), Vector3(-4.35, 16.0, -26.6), "brick_dark")
	mass(Vector3(-13.5, 0, -30.4), Vector3(-4.35, 13.6, -52.0), "brick_dark")
	mass(Vector3(-13.5, 13.9, -26.6), Vector3(-4.35, 16.0, -30.4), "brick_dark")
	mass(Vector3(-13.5, 8.6, -26.6), Vector3(-4.35, 9.0, -30.4), "brick_dark")
	mass(Vector3(-12.6, 9.0, -26.6), Vector3(-12.4, 13.9, -30.4), "black")
	# kerbs and pavements both sides; the road is cobbled asphalt
	var kerbs := []
	for i in 11:
		var z := -21.5 - i * 3.0
		kerbs.append(xf(Vector3(-2.7, 0, z), 90.0))
		kerbs.append(xf(Vector3(2.7, 0, z), -90.0))
	mm("curb", kerbs)
	surface(-4.0, -2.7, -20.5, -52.0, 0.02, "wet_pavement")
	surface(2.7, 4.0, -20.5, -52.0, 0.02, "wet_pavement")
	# the diner window: clear plate glass, the black figure behind it, the lit room behind that
	var glass: MeshInstance3D = (wing.get("_areas") as Node).get_node("DinerStreet").get_children().filter(func(n: Node) -> bool:
		return n is MeshInstance3D and (n as Node3D).position.is_equal_approx(Vector3(3.97, 2.3, -35.0)))[0]
	glass.material_override = mat("window_clear")
	glass.position.x = 4.02
	# the run's alley end is closed by a cased pier (z -21.0..-21.4); the glass and the lit room run up to it
	(glass.mesh as BoxMesh).size.z = 26.6
	glass.position.z = -34.7
	model(self, "diner_end", Vector3(4.0, 0, -21.2), -90.0)
	# the metre between the alley's last bay (z -20) and the pier was open onto the fogged void: a brick return closes it
	model(self, "alley_return", Vector3(4.02, 0, -20.5), -90.0)
	mass(Vector3(4.9, 1.0, -48.5), Vector3(4.95, 3.6, -21.3), "diner_glow")
	var sil: MeshInstance3D = wing.get("_silhouette")
	sil.mesh = mesh_of("figure_b")
	sil.material_override = mat("silhouette")
	sil.position = Vector3(4.45, 0.0, sil.position.z)
	sil.rotation_degrees.y = -90.0
	omni(Vector3(3.2, 2.4, -30.0), Color(1.0, 0.86, 0.64), 0.6, 5.0)
	omni(Vector3(3.2, 2.4, -42.0), Color(1.0, 0.86, 0.64), 0.6, 5.0)
	# the eleven-second figure: a man in a coat; his shadow (the caster) walks eleven seconds ahead
	var caster: DelayedCaster = wing.get("_caster")
	var fig := mesh_of("figure")
	var ghost := caster.ghost as MeshInstance3D
	ghost.mesh = fig
	ghost.material_override = null
	ghost.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	caster.ghost_offset = Vector3(0, -0.9, 0)
	for c: Node in caster.get_children():
		if c is MeshInstance3D:
			(c as MeshInstance3D).mesh = fig
			(c as MeshInstance3D).position = Vector3(0, -0.9, 0)
	# street covers (2.2 x 3 x 1.4): a shuttered newsstand, then crates and barrels off a delivery, stacked high
	var stacks := []
	for i in 4:
		var z := -26.0 - i * 6.0
		var x := -1.8 if i % 2 == 0 else 1.8
		hide_box("DinerStreet", Vector3(x, 1.5, z))
		if i == 0:
			model(self, "newsstand", Vector3(x, 0, z), 180.0, Vector3(1.1, 1.25, 1.17))
			continue
		stacks.append(xf(Vector3(x, 0, z), 180.0 * (i % 2) + 4.0 * i, Vector3(1.3, 1.0, 1.05)))
		stacks.append(xf(Vector3(x + 0.15 * (1 - i % 2 * 2), 1.6, z + 0.05), 180.0 * ((i + 1) % 2) - 6.0, Vector3(1.15, 0.86, 1.0)))
	mm("crate_stack", stacks)
	# signage on the upper storeys: a vertical hotel blade and a painted ghost sign, both readable down the street
	var hotel := Label3D.new()
	hotel.text = "H\nO\nT\nE\nL"
	hotel.font_size = 96
	hotel.pixel_size = 0.009
	hotel.line_spacing = -8.0
	hotel.modulate = Color(2.4, 2.35, 2.2)
	hotel.position = Vector3(-3.7, 8.6, -44.0)
	hotel.rotation_degrees.y = 90.0
	add_child(hotel)
	model(self, "lamp_bracket", Vector3(-3.9, 11.2, -44.0), -90.0)
	var ghost_sign := Label3D.new()
	ghost_sign.text = "KESSLER & SONS\nFIREPROOF STORAGE"
	ghost_sign.font_size = 96
	ghost_sign.pixel_size = 0.007
	ghost_sign.modulate = Color(0.6, 0.6, 0.56, 0.35)
	ghost_sign.position = Vector3(4.33, 10.2, -40.0)
	ghost_sign.rotation_degrees.y = -90.0
	add_child(ghost_sign)
	# the neon blade over the diner, and its spill on the wet street
	model(self, "neon_eat", Vector3(4.0, 3.2, -23.2), -90.0)
	spot(Vector3(3.4, 4.6, -23.2), Vector3(-2.0, 0.0, -24.5), Color(1.0, 0.03, 0.05), 6.0, 55.0, 10.0, false)
	model(self, "hydrant", Vector3(-3.4, 0, -37.0), 30.0)
	mm("trash_can", [xf(Vector3(-3.5, 0, -33.0), 10.0), xf(Vector3(-3.45, 0, -45.5), -40.0)])
	model(self, "manhole", Vector3(0.2, 0.01, -35.0))
	steam(Vector3(0.2, 0.05, -35.0), 22, 1.2)
	steam(Vector3(-0.4, 0.05, -49.5), 14, 0.8)
	model(self, "streetlamp", Vector3(-3.8, 0, -32.0))  # the third lamp: its light is not in the print
	# street lamp cones in the fog
	for l: Node in (wing.get("_areas") as Node).get_node("DinerStreet").get_children():
		if l is SpotLight3D:
			(l as SpotLight3D).light_volumetric_fog_energy = 2.5
			(l as SpotLight3D).light_color = Color(1.0, 0.94, 0.84)
			(l as SpotLight3D).light_energy = 16.0


func _plaza() -> void:
	facade_run(-52.0, -66.0, -5.0, 1.0, 0.0, ["facade_a", "facade_b"])
	hide_box("DinerStreet", Vector3(-5.5, 3, -59))
	# east: the bar on the precinct's corner, shuttered, with its neon
	model(self, "shopfront", Vector3(5.0, 0, -53.6), -90.0)
	model(self, "door_frame", Vector3(5.0, 0, -57.0), -90.0)
	model(self, "shopfront", Vector3(5.0, 0, -62.5), -90.0)
	facade_run(-52.0, -66.0, 5.0, -1.0, 4.4, ["facade_low", "facade_a"])
	model(self, "neon_eat", Vector3(5.0, 3.4, -61.0), -90.0)
	spot(Vector3(4.4, 4.2, -61.0), Vector3(-1.5, 0.0, -61.5), Color(1.0, 0.03, 0.05), 5.0, 55.0, 9.0, false)  # aimed away from the precinct wall
	model(self, "bench", Vector3(-3.6, 0, -62.0), 90.0)
	# the matchbook rests on a crate by the bar
	model(self, "crate", Vector3(4.2, 0, -63.0), 12.0, Vector3(0.5, 0.6, 0.5))
	model(self, "manhole", Vector3(1.8, 0.01, -61.0))
	steam(Vector3(1.8, 0.05, -61.0), 16, 0.9)
	# the cinema's marquee over the gate, bulbs lit
	model(self, "marquee", Vector3(0, 5.6, -65.6))
	omni(Vector3(0, 4.6, -64.8), Color(1.0, 0.9, 0.7), 1.2, 6.0)
	facade_run_x(-6.0, 6.0, -65.6, 1.0, 6.0, ["facade_low"])
	mass(Vector3(-6.0, 6.0, -90.0), Vector3(6.0, 13.2, -65.9), "brick_dark")
	# hanging signs on scroll brackets over the plaza and the street
	mm("sign_bracket", [xf(Vector3(-5.0, 3.6, -57.5), 90.0), xf(Vector3(-4.0, 3.4, -42.5), 90.0),
		xf(Vector3(4.0, 5.4, -36.5), -90.0), xf(Vector3(-4.5, 7.0, -65.6), 0.0)])
	for l: Node in (wing.get("_areas") as Node).get_node("DinerStreet").get_children():
		if l is SpotLight3D and (l as Node3D).position.z < -55.0:
			(l as SpotLight3D).light_volumetric_fog_energy = 3.0
			(l as SpotLight3D).light_energy = 50.0


func _roofs() -> void:
	var e := "ElevatedLine"
	hide_box(e, Vector3(-19.0, 8.0, -29.0))
	for n: Node in (wing.get("_areas") as Node).get_node(e).get_children():
		if n is MeshInstance3D and (n as MeshInstance3D).mesh is BoxMesh and ((n as MeshInstance3D).mesh as BoxMesh).size.x > 50.0:
			(n as MeshInstance3D).visible = false
	# roof membranes on the two buildings, parapets where you can't fall (never on the gap edges)
	surface(-19.6, -13.0, -33.0, -25.0, 5.01, "wet_roof")
	surface(-30.0, -22.5, -33.0, -25.0, 7.01, "wet_roof")
	var para := []
	for x in [-18.1, -15.1]:
		para.append(xf(Vector3(x, 5.0, -25.15), 0.0))
		para.append(xf(Vector3(x, 5.0, -32.85), 180.0))
	for x in [-28.5, -25.5, -23.0]:
		para.append(xf(Vector3(x, 7.0, -25.15), 0.0))
		para.append(xf(Vector3(x, 7.0, -32.85), 180.0))
	mm("parapet", para)
	# the far roof's east face is the latch face: dark windows across the gap
	facade_run(-33.0, -24.0, -22.5, 1.0, 0.0, ["facade_low", "facade_low"])
	mm("chimney", [xf(Vector3(-18.6, 5.0, -32.0), 0.0), xf(Vector3(-29.0, 7.0, -26.2), 90.0)])
	model(self, "roof_vent", Vector3(-14.4, 5.0, -26.2))
	model(self, "roof_hatch", Vector3(-17.2, 5.0, -26.0))
	model(self, "water_tower", Vector3(-28.0, 7.0, -31.0), 20.0)
	steam(Vector3(-18.6, 7.7, -32.0), 10, 0.6)
	# under the gap: the yard far below, wet
	surface(-30.0, -4.5, -45.0, -15.0, 0.0, "wet_cobble")
	# buildings around the roofs (north and south of them, and the west portal the el comes out of)
	mass(Vector3(-30.0, 0, -24.9), Vector3(-13.5, 10.0, -18.0), "brick_dark")
	facade_run_x(-30.0, -13.5, -24.9, -1.0, -3.6, ["facade_a", "facade_b", "facade_a"])
	mass(Vector3(-30.0, 0, -40.0), Vector3(-13.5, 8.0, -33.1), "brick_dark")
	facade_run_x(-30.0, -13.5, -33.1, 1.0, -5.6, ["facade_a", "facade_a", "facade_b"])
	mass(Vector3(-52.0, 0, -40.0), Vector3(-39.0, 8.6, -18.0), "brick_dark")
	mass(Vector3(-52.0, 8.6, -40.0), Vector3(-39.0, 18.0, -30.4), "brick_dark")
	mass(Vector3(-52.0, 8.6, -26.6), Vector3(-39.0, 18.0, -18.0), "brick_dark")
	mass(Vector3(-52.0, 13.9, -30.4), Vector3(-39.0, 18.0, -26.6), "brick_dark")
	mass(Vector3(-40.2, 8.6, -30.4), Vector3(-40.0, 13.9, -26.6), "black")
	facade_run(-40.0, -30.4, -39.0, 1.0, 4.4, ["facade_a", "facade_b"])
	facade_run(-26.6, -18.0, -39.0, 1.0, 4.4, ["facade_b", "facade_a"])
	# the el: deck and bents from portal to portal, high enough to stand under on the far roof
	var spans := []
	var bents := []
	for i in 5:
		spans.append(xf(Vector3(-36.0 + i * 6.0, 9.4, -29.0)))
		bents.append(xf(Vector3(-39.0 + i * 6.0, 9.4, -29.0), 0.0, Vector3(1, 9.4 / 7.85, 1)))
	mm("el_span", spans)
	mm("el_bent", bents)
	var car := model(wing.get("_train"), "el_car", Vector3(0, 1.1, 0))
	for c: Node in (wing.get("_train") as Node3D).get_children():
		if c is MeshInstance3D:
			(c as MeshInstance3D).visible = false
	car.name = "Car"
	var head := SpotLight3D.new()
	head.position = Vector3(5.3, 2.2, 0)
	head.rotation_degrees = Vector3(0, -90, 0)
	head.light_color = Color(1.0, 0.95, 0.85)
	head.light_energy = 3.0
	head.spot_range = 22.0
	head.spot_angle = 18.0
	head.light_volumetric_fog_energy = 3.0
	(wing.get("_train") as Node3D).add_child(head)
	for c: Node in (wing.get("_train") as Node3D).get_children():
		if c is SpotLight3D and c != head:
			(c as SpotLight3D).light_volumetric_fog_energy = 2.0
	model(self, "lamp_bracket", Vector3(-13.5, 10.6, -31.0), 90.0)
	var spill := OmniLight3D.new()  # the lit car throws its windows onto the deck and the roofs below
	spill.position = Vector3(0, 2.6, 0)
	spill.light_color = Color(1.0, 0.9, 0.72)
	spill.light_energy = 2.2
	spill.omni_range = 7.0
	(wing.get("_train") as Node3D).add_child(spill)
	# the back light: a cold key behind the water tower rims the chimneys, the tower and the el, and lays a
	# bright wet path across the near roof toward the gap
	var back := spot(Vector3(-30.0, 17.0, -16.0), Vector3(-18.0, 5.0, -30.0), Color(0.78, 0.84, 1.0), 16.0, 22.0, 40.0)
	back.light_volumetric_fog_energy = 0.5
	omni(Vector3(-17.2, 6.0, -26.0), Color(1.0, 0.9, 0.7), 1.2, 3.0)  # the bulb over the roof hatch


func _precinct() -> void:
	var p := "Precinct"
	# the room is closed: a ceiling at 3.6, a wainscot, the desk, cabinets and the blind window
	mass(Vector3(6.0, 3.6, -66.0), Vector3(12.0, 3.8, -53.0), "plaster")
	var ws := []
	for i in 6:
		ws.append(xf(Vector3(12.0, 0, -54.0 - i * 2.0), -90.0))
	for i in 3:
		ws.append(xf(Vector3(7.0 + i * 2.0, 0, -53.0), 0.0))
		ws.append(xf(Vector3(7.0 + i * 2.0, 0, -66.0), 180.0))
	mm("wainscot", ws)
	for i in 5:
		hide_box(p, Vector3(11.9, 2.4, -53.2 - i * 0.4))
	var bw := model(self, "blind_window", Vector3(12.0, 0.9, -54.2), -90.0)
	for gi: Node in bw.find_children("*", "GeometryInstance3D", true, false):
		(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF  # the shadow slats do the work
	# moonlight through the blinds, cast for real: a shadowed spot outside, the east wall's mesh casts no shadow,
	# a shadow-only mask leaves the window opening, and the slats in it rule the floor and the far wall in bars
	var east := box_at(p, Vector3(12.5, 3, -59))
	if east:
		east.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var occ := StandardMaterial3D.new()
	for b: Array in [[Vector3(12.05, 0.45, -59.5), Vector3(0.05, 0.9, 13.0)], [Vector3(12.05, 4.5, -57.0), Vector3(0.05, 3.2, 18.0)],
			[Vector3(12.05, 1.9, -51.2), Vector3(0.05, 2.0, 4.4)], [Vector3(12.05, 1.9, -60.5), Vector3(0.05, 2.0, 11.0)]]:
		_shadow_box(b[0], b[1], occ)
	for i in 15:
		_shadow_box(Vector3(11.97, 0.98 + i * 0.13, -54.2), Vector3(0.03, 0.065, 1.6), occ)
	var bl := spot(Vector3(16.5, 4.4, -54.3), Vector3(8.0, 0.0, -57.6), Color(0.8, 0.86, 1.0), 260.0, 19.0, 18.0)
	bl.shadow_blur = 0.15
	bl.light_volumetric_fog_energy = 0.0
	var desk := model(self, "desk", Vector3(9.4, 0, -55.8), 180.0)
	desk.name = "Desk"
	model(self, "desk_lamp", Vector3(9.8, 0.78, -55.6), 160.0)
	omni(Vector3(9.8, 1.05, -55.6), Color(0.9, 1.0, 0.85), 0.5, 1.8)
	model(self, "chair", Vector3(9.3, 0, -54.9), 170.0)
	mm("file_cabinet", [xf(Vector3(6.6, 0, -53.4), 0.0), xf(Vector3(7.1, 0, -53.4), 0.0), xf(Vector3(11.6, 0, -65.6), 180.0), xf(Vector3(11.1, 0, -65.6), 180.0)])
	model(self, "hanging_lamp", Vector3(8.0, 3.6, -57.0))
	(wing.get("_desk_lamp") as SpotLight3D).light_energy = 0.0 if Quest.is_step_done(&"heist", &"dim_lamp") else 28.0
	(wing.get("_desk_lamp") as SpotLight3D).light_volumetric_fog_energy = 0.8
	var piv: Node3D = wing.get("_swing_pivot")
	model(piv, "hanging_lamp", Vector3(0, 0.9, 0))
	for c: Node in piv.get_children():
		if c is SpotLight3D:
			(c as SpotLight3D).light_energy = 32.0
	hide_box(p, Vector3(5.5, 3, -53.5))  # outer faces are dressed from the plaza side
	hide_box(p, Vector3(5.5, 3, -62.5))
	model(self, "locker", Vector3(6.5, 0, -63.0))
	model(self, "locker", Vector3(7.55, 0, -63.6))
	model(self, "switch_box", Vector3(5.25, 1.2, -58.95), 0.0)
	model(self, "detective_seated", Vector3(11.2, 0, -59.0), -90.0)
	# the squad room: a second desk with the typewriter and phone, the coat stand, clock, pinboard, frosted door
	model(self, "desk", Vector3(10.9, 0, -62.6), 90.0)
	model(self, "chair", Vector3(11.7, 0, -62.6), 80.0)
	model(self, "typewriter", Vector3(10.9, 0.78, -62.9), 90.0)
	model(self, "telephone", Vector3(10.8, 0.78, -62.0), 70.0)
	model(self, "telephone", Vector3(8.9, 0.78, -55.4), 200.0)
	model(self, "coat_stand", Vector3(11.55, 0, -53.6), 30.0)
	model(self, "wall_clock", Vector3(7.6, 2.6, -53.0))
	model(self, "pinboard", Vector3(9.4, 1.55, -66.0), 180.0)
	model(self, "frosted_door", Vector3(10.3, 0, -53.0))
	var sign := Label3D.new()  # painted for the corridor, so it reads backwards from inside
	sign.text = "HOMICIDE\nLt. M. KESSLER"
	sign.font_size = 64
	sign.pixel_size = 0.0022
	sign.modulate = Color(0.08, 0.08, 0.08)
	sign.outline_size = 0
	sign.position = Vector3(10.3, 1.7, -53.08)
	add_child(sign)
	# the west wall from inside: plaster over the bar's shopfront backs, wainscot, a lintel over the doorway
	mass(Vector3(5.97, 0.0, -55.0), Vector3(6.02, 3.6, -52.5), "plaster")
	mass(Vector3(5.97, 0.0, -66.0), Vector3(6.02, 3.6, -59.0), "plaster")
	mass(Vector3(5.97, 2.6, -59.0), Vector3(6.02, 3.6, -55.0), "plaster")
	mm("wainscot", [xf(Vector3(6.02, 0, -54.0), 90.0), xf(Vector3(6.02, 0, -60.0), 90.0), xf(Vector3(6.02, 0, -62.0), 90.0), xf(Vector3(6.02, 0, -64.0), 90.0)])
	# the plaster box dressed: a crown and picture rail round the walls, two cased beams across the ceiling
	var cr := []
	for x in [7.0, 9.0, 11.0]:
		cr.append(xf(Vector3(x, 3.6, -53.0), 0.0))
		cr.append(xf(Vector3(x, 3.6, -66.0), 180.0))
	for z in [-54.0, -56.0, -58.0, -60.0, -62.0, -64.0, -65.0]:
		cr.append(xf(Vector3(12.0, 3.6, z), -90.0))
		cr.append(xf(Vector3(6.02, 3.6, z), 90.0))
	mm("crown", cr)
	mm("ceiling_beam", [xf(Vector3(9.0, 3.6, -55.0), 0.0, Vector3(6.0, 1, 1)), xf(Vector3(9.0, 3.6, -62.5), 0.0, Vector3(6.0, 1, 1))])
	# the interview: a hard chair in the lamp's circle, facing the desk; the squad room's clutter
	model(self, "chair", Vector3(9.5, 0, -56.8), -10.0)
	mm("file_cabinet", [xf(Vector3(7.6, 0, -53.4), 0.0), xf(Vector3(8.1, 0, -53.4), 0.0)])
	model(self, "crate_stack", Vector3(7.6, 0, -65.3), 8.0, Vector3(0.6, 0.6, 0.6))
	model(self, "trash_can", Vector3(8.5, 0, -53.6), 0.0, Vector3(0.7, 0.7, 0.7))
	model(self, "bench", Vector3(11.6, 0, -60.9), -90.0)
	model(self, "ceiling_fan", Vector3(9.0, 3.6, -59.5))
	_fan = model(self, "ceiling_fan_blades", Vector3(9.0, 3.08, -59.5))
	# a ceiling light above the blades: the fan's shadow turns slowly over the floor
	spot(Vector3(9.0, 3.5, -59.5), Vector3(9.0, 0.0, -59.6), Color(0.95, 0.9, 0.8), 3.5, 45.0, 4.5).light_volumetric_fog_energy = 0.0


func _cinema() -> void:
	# the gate: a collapsible scissor gate over the collider
	(wing.get("_gate_mesh") as MeshInstance3D).mesh = mesh_of("cinema_gate")
	(wing.get("_gate_mesh") as MeshInstance3D).material_override = null
	# the house: proscenium and screen on the back wall over the booth door, seats over the covers
	model(self, "proscenium", Vector3(0, 0, -89.95))
	mass(Vector3(-3.8, 2.7, -90.0), Vector3(3.8, 6.6, -89.9), "black")
	# the picture: a 4:3 still, glowing on its own (dark albedo so the beams don't wash it)
	var film := StandardMaterial3D.new()
	film.albedo_color = Color(0.02, 0.02, 0.02)
	film.emission_enabled = true
	film.emission_texture = load("res://wings/noir/textures/screen_still.png")
	film.emission_energy_multiplier = 0.8
	var still := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(5.2, 3.9)
	still.mesh = q
	still.material_override = film
	still.position = Vector3(0, 4.65, -89.88)
	still.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(still)
	mass(Vector3(-1.0, 2.6, -90.9), Vector3(1.0, 6.0, -90.0), "black")
	model(self, "curtain", Vector3(-4.7, 0, -89.6), 0.0, Vector3(0.7, 1, 1))
	model(self, "curtain", Vector3(4.7, 0, -89.6), 0.0, Vector3(-0.7, 1, 1))
	var seats := []
	for row in 6:
		for col in 3:
			var at := Vector3(-3.0 + col * 3.0, 0.4, -69.0 - row * 3.0)
			hide_box("Cinema", at)
			seats.append(xf(Vector3(at.x, 0, at.z), 180.0))
	mm("seat_block", seats)
	var pil := []
	for i in 6:
		pil.append(xf(Vector3(-6.0, 0, -68.0 - i * 4.0), 90.0))
		pil.append(xf(Vector3(6.0, 0, -68.0 - i * 4.0), -90.0))
	mm("pilaster", pil)
	model(self, "balcony", Vector3(-5.6, 3.6, -78.0), 90.0)
	model(self, "balcony", Vector3(5.6, 3.6, -82.0), -90.0)
	# walls up to the ceiling at 9.2 (the colliders stop at 6)
	mass(Vector3(-7.0, 6.0, -90.5), Vector3(-6.0, 9.2, -66.0), "plaster")
	mass(Vector3(6.0, 6.0, -90.5), Vector3(7.0, 9.2, -66.0), "plaster")
	mass(Vector3(-7.0, 9.2, -90.5), Vector3(7.0, 9.4, -66.0), "plaster")
	mass(Vector3(-7.0, 6.0, -66.4), Vector3(7.0, 9.2, -66.0), "plaster")
	mass(Vector3(-6.0, 6.0, -91.0), Vector3(6.0, 9.2, -90.4), "plaster")
	# the house ceiling: crown round the walls, cased beams across every 4 m over the pilasters
	var cr := []
	for i in 12:
		cr.append(xf(Vector3(-6.0, 9.2, -67.4 - i * 2.0), 90.0))
		cr.append(xf(Vector3(6.0, 9.2, -67.4 - i * 2.0), -90.0))
	for x in [-5.0, -3.0, -1.0, 1.0, 3.0, 5.0]:
		cr.append(xf(Vector3(x, 9.2, -90.4), 0.0))
		cr.append(xf(Vector3(x, 9.2, -66.4), 180.0))
	mm("crown", cr)
	var bm := []
	for i in 6:
		bm.append(xf(Vector3(0, 9.2, -68.0 - i * 4.0), 0.0, Vector3(12.0, 1, 1)))
	mm("ceiling_beam", bm)
	model(self, "pedestal_reel", Vector3(0, 0, -86.0))
	omni(Vector3(0, 6.0, -88.5), Color(0.8, 0.85, 0.95), 2.2, 11.0)
	omni(Vector3(0, 7.5, -72.0), Color(0.8, 0.85, 0.95), 1.6, 10.0)  # house lights at half
	# searchlights cast shadows: the seats stripe the floor as the beams sweep
	for s: Node in get_tree().get_nodes_in_group(&"searchlights"):
		(s as SpotLight3D).shadow_enabled = true
		(s as SpotLight3D).light_volumetric_fog_energy = 4.0
		(s as SpotLight3D).light_energy = 34.0


func _sound() -> void:
	# a radio in the diner carries the jazz into the street; the city hums from the far end
	var radio := Node3D.new()
	radio.position = Vector3(5.5, 1.6, -36.0)
	add_child(radio)
	Audio.emitter(load("res://wings/noir/audio/jazz_bed.ogg"), radio, -6.0, 6.0).max_distance = 25.0
	var city := Node3D.new()
	city.position = Vector3(0, 6.0, -50.0)
	add_child(city)
	Audio.emitter(load("res://wings/noir/audio/city_night.ogg"), city, -12.0, 20.0)


func _booth() -> void:
	mass(Vector3(-4.5, 4.0, -99.5), Vector3(4.5, 4.2, -91.0), "brick_dark")
	model(self, "projector", Vector3(-2.4, 0, -97.4))
	model(self, "projector", Vector3(2.4, 0, -97.4))
	mm("port_window", [xf(Vector3(-2.4, 1.95, -91.0), 180.0), xf(Vector3(2.4, 1.95, -91.0), 180.0)])
	mm("film_shelf", [xf(Vector3(-4.0, 0, -94.5), 90.0), xf(Vector3(4.0, 0, -95.5), -90.0)])
	model(self, "hanging_lamp", Vector3(0, 4.0, -94.0))
	omni(Vector3(0, 3.0, -94.0), Color(1.0, 0.92, 0.78), 1.3, 6.0)
	spot(Vector3(0, 3.7, -95.0), Vector3(0, 0.8, -97.6), Color(1.0, 0.92, 0.78), 24.0, 24.0, 6.0, false)  # a tight pool on the desk and the frame
	# the beams: from each lens out through the port toward the screen's back
	for x in [-2.4, 2.4]:
		spot(Vector3(x, 1.95, -96.6), Vector3(x * 0.8, 2.2, -88.0), Color(1, 0.97, 0.9), 14.0, 9.0, 9.0, false).light_volumetric_fog_energy = 0.7
	model(self, "desk", Vector3(0, 0, -97.6))


func _skyline() -> void:
	var t := []
	for s: Array in [[Vector3(-70, 0, -12), 0.0, 1.0], [Vector3(-85, 0, -45), 25.0, 1.3], [Vector3(-60, 0, -80), -10.0, 0.9],
			[Vector3(40, 0, -18), 15.0, 1.1], [Vector3(55, 0, -55), -20.0, 1.4], [Vector3(30, 0, -100), 5.0, 1.0],
			[Vector3(-25, 0, -125), 40.0, 1.2], [Vector3(20, 0, 40), 0.0, 1.0], [Vector3(-35, 0, 45), 30.0, 1.25]]:
		t.append(xf(s[0], s[1], Vector3.ONE * s[2]))
	mm("skyline_block", t)
