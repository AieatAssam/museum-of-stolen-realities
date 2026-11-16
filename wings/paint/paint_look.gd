extends Node3D
## Light for the Unfinished Wing, as a painter keys each passage of the picture. One recipe per area
## (key sun, cool violet fill from the ambient so shadows change hue instead of greying, fog, sky
## tint, exposure), chosen by where the camera stands and eased between areas. The painter's mood
## (paint.gd `mood`) then modulates it: low mood brings the storm study into the sky, thickens the
## fog, lowers and greys the sun. No SDFGI (the world is 700 m across); SSAO and SSR for the gloss.

# load(), not preload(): resources preloaded under the threaded wing load leak their load tokens
const FAIR := "res://wings/paint/textures/paint_sky.png"
const STORM := "res://wings/paint/textures/paint_sky_storm.png"

# sun colour, sun energy, pitch, yaw, ambient colour, ambient energy, fog colour, fog density,
# exposure, sky tint, horizon haze, storm bias, saturation
const AREAS := {
	"shore": [Color(1.0, 0.90, 0.74), 2.3, -36.0, 30.0, Color(0.58, 0.58, 0.90), 0.62, Color(1.0, 0.87, 0.72), 0.0035,
		1.0, Color(1.0, 1.0, 1.0), Color(1.0, 0.86, 0.70), 0.0, 1.12],
	"orchard": [Color(1.0, 0.82, 0.56), 2.3, -30.0, 60.0, Color(0.50, 0.56, 0.90), 0.6, Color(0.98, 0.84, 0.64), 0.0045,
		1.0, Color(1.0, 0.96, 0.9), Color(1.0, 0.82, 0.62), 0.0, 1.15],
	"windfall": [Color(1.0, 0.72, 0.44), 2.2, -20.0, 80.0, Color(0.58, 0.48, 0.84), 0.58, Color(1.0, 0.76, 0.56), 0.0055,
		1.0, Color(1.05, 0.92, 0.82), Color(1.0, 0.72, 0.50), 0.0, 1.15],
	"unpainted": [Color(0.70, 0.55, 0.45), 0.3, -40.0, 60.0, Color(0.42, 0.33, 0.30), 0.35, Color(0.30, 0.23, 0.18), 0.012,
		1.35, Color(0.55, 0.48, 0.42), Color(0.40, 0.32, 0.24), 0.3, 1.0],
	"river": [Color(1.0, 0.94, 0.82), 2.5, -48.0, 20.0, Color(0.48, 0.58, 0.98), 0.62, Color(0.82, 0.86, 1.0), 0.0035,
		0.95, Color(0.95, 1.0, 1.08), Color(0.95, 0.88, 0.80), 0.0, 1.15],
	"source": [Color(0.55, 0.50, 0.70), 0.25, -40.0, 20.0, Color(0.28, 0.24, 0.45), 0.4, Color(0.16, 0.13, 0.28), 0.008,
		1.45, Color(0.5, 0.5, 0.6), Color(0.25, 0.22, 0.35), 0.4, 1.05],
	"corrections": [Color(0.92, 0.93, 1.0), 1.9, -44.0, -40.0, Color(0.70, 0.60, 0.84), 0.72, Color(0.92, 0.86, 0.90), 0.0045,
		1.0, Color(1.0, 0.95, 1.0), Color(0.96, 0.86, 0.86), 0.1, 1.08],
	"pentimento": [Color(1.0, 0.74, 0.58), 1.8, -16.0, 10.0, Color(0.46, 0.40, 0.70), 0.62, Color(0.62, 0.55, 0.72), 0.006,
		1.05, Color(0.95, 0.9, 1.0), Color(0.85, 0.66, 0.62), 0.55, 1.1],
	"horizon": [Color(1.0, 0.86, 0.70), 2.3, -24.0, 100.0, Color(0.55, 0.58, 0.92), 0.6, Color(1.0, 0.88, 0.76), 0.0022,
		1.0, Color(1.0, 1.0, 1.0), Color(1.0, 0.84, 0.70), 0.0, 1.12],
	"museum": [Color(0.96, 0.92, 0.86), 1.2, -58.0, -90.0, Color(0.62, 0.60, 0.60), 0.5, Color(0.36, 0.28, 0.24), 0.0008,
		1.6, Color(0.8, 0.82, 0.9), Color(0.6, 0.6, 0.66), 0.2, 0.92],
}

var env: Environment
var sun: DirectionalLight3D
var sky_mat: ShaderMaterial
var backdrop: ShaderMaterial   # the museum wall's inside face, painted out with the same sky
var grade: PostGrade
var area: String = "shore"
var _cur: Array = []
var _last_cam := Vector3.INF


func build(wing: Node) -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky_mat = ShaderMaterial.new()
	sky_mat.shader = load("res://wings/paint/shaders/paint_sky.gdshader")
	sky_mat.set_shader_parameter(&"fair", load(FAIR))
	sky_mat.set_shader_parameter(&"storm", load(STORM))
	sky.sky_material = sky_mat
	backdrop = ShaderMaterial.new()
	backdrop.shader = load("res://wings/paint/shaders/paint_backdrop.gdshader")
	backdrop.set_shader_parameter(&"fair", load(FAIR))
	backdrop.set_shader_parameter(&"storm", load(STORM))
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 5.0
	# AgX greys out bright paint; the picture is saturated oil, so put the chroma back after it
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.3
	env.adjustment_contrast = 1.05
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.4
	env.ssao_power = 1.3
	env.ssr_enabled = true
	env.ssr_max_steps = 24
	env.ssr_fade_in = 0.2
	env.ssr_depth_tolerance = 0.3
	env.glow_enabled = true
	env.glow_intensity = 0.45
	env.glow_bloom = 0.05
	env.glow_hdr_threshold = 1.1
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_sky_affect = 0.25
	env.fog_aerial_perspective = 0.3
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	wing.add_child(we)
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.shadow_blur = 1.5
	sun.directional_shadow_max_distance = 110.0
	wing.add_child(sun)
	grade = PostGrade.new()
	grade.contrast = 1.04
	grade.grain = 0.015
	grade.vignette = 0.28


static func area_at(p: Vector3) -> String:
	if p.x < -236.0:
		return "museum"
	if p.y > 15.0 and p.x < 20.0:
		return "horizon"
	if p.x > 82.0 and p.z < -200.0 and p.z > -254.0 and p.y < 8.0:
		return "source"
	if p.x < -14.0 and p.z < -156.0 and p.z > -184.0 and p.y < 8.0:
		return "unpainted"
	if p.z > -30.0:
		return "shore"
	if p.z > -155.0:
		return "orchard"
	if p.z > -192.0:
		return "windfall"
	if p.z > -266.0:
		return "river"
	if p.z > -338.0:
		return "corrections"
	return "pentimento"


## Called every physics tick with the painter's mood (0 grey smear .. 1 warm).
func update(cam_pos: Vector3, mood: float, delta: float) -> void:
	area = area_at(cam_pos)
	var tgt: Array = AREAS[area]
	var snap := _cur.is_empty() or _last_cam.distance_to(cam_pos) > 25.0
	_last_cam = cam_pos
	if snap:
		_cur = tgt.duplicate()
	else:
		var k := 1.0 - exp(-delta / 1.5)
		for i in _cur.size():
			_cur[i] = lerp(_cur[i], tgt[i], k)
	var m := clampf(mood, 0.0, 1.0)
	var r := _cur
	var grey := Color(0.72, 0.72, 0.74)
	sun.light_color = (r[0] as Color).lerp(grey, (1.0 - m) * 0.5)
	sun.light_energy = float(r[1]) * lerpf(0.55, 0.85, m)
	sun.rotation_degrees = Vector3(float(r[2]) + (1.0 - m) * 8.0, float(r[3]), 0.0)
	env.ambient_light_color = r[4]
	env.ambient_light_energy = r[5]
	env.fog_light_color = (r[6] as Color).lerp(Color(0.62, 0.62, 0.66), (1.0 - m) * 0.6)
	env.fog_density = float(r[7]) * lerpf(0.9, 0.35, m)
	env.tonemap_exposure = r[8]
	for sm: ShaderMaterial in [sky_mat, backdrop]:
		sm.set_shader_parameter(&"tint", r[9])
		sm.set_shader_parameter(&"haze", (r[10] as Color).lerp(Color(0.6, 0.6, 0.64), (1.0 - m) * 0.6))
		sm.set_shader_parameter(&"storm_amount", clampf(float(r[11]) + (0.55 - m) * 1.6, 0.0, 1.0))
	backdrop.set_shader_parameter(&"fog_colour", env.fog_light_color)
	grade.saturation = float(r[12]) * lerpf(0.9, 1.18, m)
	env.adjustment_saturation = 1.3 * float(r[12]) / 1.12   # the museum, outside the paint, is greyer
	# screen-space reflections only where something is glossy and large: the river and the parquet
	env.ssr_enabled = area == "river" or area == "museum"
