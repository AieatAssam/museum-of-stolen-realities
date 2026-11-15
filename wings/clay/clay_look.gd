class_name ClayLook
extends Node3D
## Lighting for the Pinched Forest, as a miniature set is lit: a soft key (the sun lamp), a cool fill
## from the other side, warm bounce from SDFGI off the plasticine, a little haze, far depth of field.
## The light-dark arc is one function of where the camera stands along the set (z): morning over the
## meadow, late morning at the river, low gold at the hill, dusk over the village, night at the
## workbench, where an anglepoise lamp takes over as key. The burrow is its own dark room.
## Keyed off the current camera, so shot marks and play agree; no temporal smoothing.

const BURROW := Vector3(28.5, 0.0, -11.0)
const LAMP_HEAD := Vector3(-4.6, 10.4, -42.6)
const LAMP_AIM := Vector3(-0.6, 2.6, -40.0)

# z, sun colour, sun energy, sun pitch, sun yaw, ambient colour, ambient energy, fog colour, fog density,
# sky zenith, sky horizon, stars, exposure, fill energy, lamp energy, window glow
const STOPS: Array = [
	[34.0, Color(1.0, 0.93, 0.78), 2.1, -48.0, 35.0, Color(0.62, 0.74, 0.92), 0.55, Color(0.70, 0.80, 0.95), 0.006,
		Color(0.26, 0.52, 0.92), Color(0.78, 0.88, 0.98), 0.0, 0.72, 0.45, 0.0, 0.0],
	[6.0, Color(1.0, 0.89, 0.70), 2.0, -40.0, 20.0, Color(0.60, 0.70, 0.88), 0.5, Color(0.74, 0.80, 0.92), 0.007,
		Color(0.28, 0.50, 0.88), Color(0.86, 0.88, 0.92), 0.0, 0.6, 0.4, 0.0, 0.0],
	[-12.0, Color(1.0, 0.72, 0.42), 2.0, -18.0, 70.0, Color(0.62, 0.55, 0.70), 0.45, Color(0.95, 0.72, 0.52), 0.009,
		Color(0.32, 0.42, 0.78), Color(1.0, 0.72, 0.46), 0.0, 0.7, 0.35, 0.0, 0.4],
	[-24.0, Color(1.0, 0.50, 0.36), 1.25, -9.0, 80.0, Color(0.46, 0.38, 0.66), 0.5, Color(0.55, 0.40, 0.62), 0.011,
		Color(0.20, 0.16, 0.42), Color(0.98, 0.46, 0.40), 0.25, 0.9, 0.35, 4.0, 1.0],
	[-38.0, Color(0.55, 0.62, 1.0), 0.35, -35.0, 120.0, Color(0.22, 0.24, 0.42), 0.4, Color(0.18, 0.16, 0.26), 0.012,
		Color(0.03, 0.04, 0.11), Color(0.12, 0.10, 0.22), 1.0, 1.6, 0.2, 14.0, 1.0],
]

var env: Environment
var sky_mat: ShaderMaterial
var sun: DirectionalLight3D
var fill: DirectionalLight3D
var lamp: SpotLight3D
var burrow_light: SpotLight3D
var window_mats: Array[ShaderMaterial] = []
var _attrs: CameraAttributesPractical
var _last := Vector3.INF


func build(wing: Wing) -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://wings/clay/shaders/backdrop_sky.gdshader")
	sky_mat.set_shader_parameter(&"canvas", load("res://wings/clay/textures/clay_canvas_albedo.png"))
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 6.0
	# bounce: the plasticine throws its colour onto its neighbours, as on a real set
	env.sdfgi_enabled = true
	env.sdfgi_cascades = 3
	env.sdfgi_min_cell_size = 0.4
	env.sdfgi_use_occlusion = true
	env.sdfgi_energy = 1.1
	env.sdfgi_read_sky_light = true
	env.ssao_enabled = true
	env.ssao_radius = 0.8
	env.ssao_intensity = 1.6
	env.ssao_power = 1.4
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 1.2
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_sky_affect = 0.0
	env.fog_aerial_perspective = 0.4
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	# miniature-set depth of field: the far set softens, never the near (first person)
	_attrs = CameraAttributesPractical.new()
	_attrs.dof_blur_far_enabled = true
	_attrs.dof_blur_far_distance = 24.0
	_attrs.dof_blur_far_transition = 22.0
	_attrs.dof_blur_amount = 0.07
	we.camera_attributes = _attrs
	add_child(we)

	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.shadow_blur = 2.5          # a big soft studio key, not a hard sun
	sun.directional_shadow_max_distance = 55.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun)
	fill = DirectionalLight3D.new()
	fill.name = "Fill"
	fill.light_color = Color(0.62, 0.72, 1.0)
	fill.shadow_enabled = false
	fill.light_specular = 0.1
	fill.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	add_child(fill)

	lamp = SpotLight3D.new()
	lamp.name = "Anglepoise"
	lamp.light_color = Color(1.0, 0.78, 0.5)
	lamp.spot_range = 22.0
	lamp.spot_angle = 38.0
	lamp.spot_angle_attenuation = 1.6
	lamp.spot_attenuation = 0.6
	lamp.shadow_enabled = true
	lamp.shadow_blur = 1.5
	add_child(lamp)
	lamp.look_at_from_position(LAMP_HEAD, LAMP_AIM, Vector3.UP)

	burrow_light = SpotLight3D.new()
	burrow_light.name = "BurrowShaft"
	burrow_light.light_color = Color(1.0, 0.8, 0.55)
	burrow_light.light_energy = 6.0
	burrow_light.spot_range = 6.0
	burrow_light.spot_angle = 22.0
	burrow_light.shadow_enabled = false
	add_child(burrow_light)
	burrow_light.look_at_from_position(BURROW + Vector3(0.8, 4.2, 0.0), BURROW + Vector3(1.6, 0.0, 0.0), Vector3.FORWARD)

	wing.grade = PostGrade.new()
	wing.grade.tint = Color(1.02, 1.0, 0.97)
	wing.grade.saturation = 1.12
	wing.grade.contrast = 1.06
	wing.grade.lift = Color(0.01, 0.006, 0.004)
	wing.grade.grain = 0.035
	wing.grade.grain_fps = 12.0
	wing.grade.aberration = 0.0
	wing.grade.vignette = 0.5
	update_for(Vector3(0, 1.7, 34))


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	# only on a real move: every parameter write re-renders the sky radiance
	if cam and cam.global_position.distance_to(_last) > 0.25:
		_last = cam.global_position
		update_for(_last)


func _stop(z: float) -> Array:
	if z >= STOPS[0][0]:
		return STOPS[0]
	for i in STOPS.size() - 1:
		var a: Array = STOPS[i]
		var b: Array = STOPS[i + 1]
		if z <= a[0] and z >= b[0]:
			var t := smoothstep(0.0, 1.0, (a[0] - z) / (a[0] - b[0]))
			var out := []
			for k in a.size():
				out.append(lerp(a[k], b[k], t))
			return out
	return STOPS[-1]


func update_for(c: Vector3) -> void:
	var s := _stop(c.z)
	sun.light_color = s[1]
	sun.light_energy = s[2]
	sun.rotation_degrees = Vector3(s[3], s[4], 0.0)
	fill.rotation_degrees = Vector3(-25.0, s[4] + 180.0, 0.0)
	fill.light_energy = s[13]
	env.ambient_light_color = s[5]
	env.ambient_light_energy = s[6]
	env.fog_light_color = s[7]
	env.fog_density = s[8]
	sky_mat.set_shader_parameter(&"zenith", s[9])
	sky_mat.set_shader_parameter(&"horizon", s[10])
	sky_mat.set_shader_parameter(&"sun_col", s[1])
	sky_mat.set_shader_parameter(&"stars", s[11])
	sky_mat.set_shader_parameter(&"below", (s[5] as Color) * 0.3)
	env.tonemap_exposure = s[12]
	lamp.light_energy = s[14]
	lamp.visible = s[14] > 0.05
	for m in window_mats:
		m.set_shader_parameter(&"emission_gain", 3.0 * float(s[15]))
	# the burrow: a dark room lit by one shaft through a hole in its roof; the eye adapts
	var din := Vector2(c.x - BURROW.x, c.z - BURROW.z).length()
	var inside := 1.0 - smoothstep(2.6, 4.2, din)
	burrow_light.visible = din < 14.0
	if inside > 0.0:
		env.ambient_light_energy = lerpf(s[6], 0.12, inside)
		env.tonemap_exposure = lerpf(s[12], 2.2, inside)
		sun.light_energy = lerpf(s[2], s[2] * 0.6, inside)
	_attrs.dof_blur_far_distance = lerpf(24.0, 9.0, inside)
