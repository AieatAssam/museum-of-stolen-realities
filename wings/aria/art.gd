extends Node3D
## The Drowned Aria, art pass. Modelled architecture laid over the gameplay boxes, the flooded stalls
## and the cymatics, drifting score pages and dust, the lighting recipe per area and the per-area look
## (driven by the camera, so shots and cinematics agree with play). aria.gd keeps the gameplay; nothing
## here adds a collider, and every collider the boxes had is still there (only their meshes are hidden
## where a model now stands in for them).
##
## Lighting recipe (key / practicals / haze / GI / exposure), the arc runs warm-mid, bright, dark,
## mid, dark, climax:
##   Foyer       key: two foyer chandeliers (warm omni, no shadows); practicals: wall sconces (emissive);
##               haze: teal volumetric fog 0.02; SDFGI bounce off marble; exposure 1.9
##   Auditorium  key: the great chandelier (warm omni, shadowed); practicals: tier sconces, footlights
##               (warm spot up the proscenium), La Sirena's own teal glow; haze 0.024; SSR on the
##               flooded stalls; exposure 1.7
##   Pit         key: two amber stand lamps (short omni); fill: teal spill down the stair; haze 0.03
##               (thick, close); exposure 2.6
##   Corridor    key: cool top spots along the stave; practicals: sconces, mirrors catch them; haze 0.02;
##               exposure 2.1
##   Fly-loft    key: moonlight down a skylight (cold spot, shadowed) onto the fork; practical: a warm
##               work lamp; haze 0.035 so the shaft reads; exposure 2.6
##   Dome        key: the cathedral chandelier (aria.gd, shadowed) over a ring of warm tier lamps;
##               cymatic rings on the floor; haze 0.026; exposure 1.8

const Instrument := preload("res://wings/aria/instrument.gd")
const MODELS := "res://wings/aria/models/"
const MAT_DIRS := ["res://wings/aria/materials", MaterialLib.CORE_DIR]
const SHADERS := "res://wings/aria/shaders/"
const AUDIO := "res://wings/aria/audio/"

## per area: exposure, fog density, fog albedo, ambient energy
const LOOK := {
	&"foyer": [5.0, 0.018, Color(0.55, 0.62, 0.6), 1.2],
	&"auditorium": [4.2, 0.02, Color(0.5, 0.66, 0.62), 1.0],
	&"pit": [6.0, 0.022, Color(0.45, 0.55, 0.52), 1.2],
	&"corridor": [4.6, 0.014, Color(0.5, 0.6, 0.6), 1.2],
	&"flyloft": [6.0, 0.012, Color(0.55, 0.62, 0.66), 1.0],
	&"dome": [4.2, 0.012, Color(0.55, 0.62, 0.6), 1.0],
}

var wing: Node3D
var env: Environment
var _water: ShaderMaterial
var _discs: Array = []  # [ShaderMaterial, centre Vector3, radius, base level]
var _area: StringName = &""
var _music_now: StringName = &""


func build(w: Node3D) -> void:
	wing = w
	_environment()
	_foyer()
	_auditorium()
	_pit()
	_corridor()
	_fly_loft()
	_dome()
	_particles()
	_probes()


func on_enter() -> void:
	var vp := get_tree().root
	if vp.msaa_3d != Viewport.MSAA_DISABLED:
		vp.msaa_3d = Viewport.MSAA_DISABLED
		vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_SMAA
	vp.use_debanding = true  # dark teal fog gradients band badly in 8-bit output without it
	RenderingServer.gi_set_use_half_resolution(true)
	RenderingServer.environment_set_sdfgi_ray_count(RenderingServer.ENV_SDFGI_RAY_COUNT_16)
	RenderingServer.environment_set_sdfgi_frames_to_update_light(RenderingServer.ENV_SDFGI_UPDATE_LIGHT_IN_8_FRAMES)
	_music_now = &""
	if Game.player:
		_music_for(_area_of(Game.player.global_position))


func on_exit() -> void:
	get_tree().root.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED  # the next wing's Quality.apply restores MSAA
	get_tree().root.use_debanding = false
	RenderingServer.gi_set_use_half_resolution(false)


func _process(delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		_look_for(cam.global_position, delta)
	if Game.player and Engine.get_process_frames() % 30 == 0:
		_music_for(_area_of(Game.player.global_position))
	_feed_cymatics()


# =============================================================================================
# Environment

func _environment() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.004, 0.022, 0.024)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.1, 0.26, 0.25)
	env.ambient_light_energy = 0.5
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 10.0
	env.tonemap_exposure = 1.9
	env.sdfgi_enabled = true
	env.sdfgi_cascades = 3
	env.sdfgi_min_cell_size = 0.5
	env.sdfgi_use_occlusion = false
	env.sdfgi_energy = 1.2
	env.sdfgi_read_sky_light = false
	env.ssr_enabled = true
	env.ssr_max_steps = 16
	env.ssr_fade_in = 0.1
	env.ssr_fade_out = 2.0
	env.ssao_enabled = false  # cost ~13 ms at 1440p in glass; SDFGI occlusion reads well enough here
	env.glow_enabled = true
	env.glow_intensity = 0.8
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 1.4
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.set_glow_level(0, 0.0)
	env.set_glow_level(1, 0.0)
	env.set_glow_level(2, 1.0)
	env.set_glow_level(3, 0.7)
	env.set_glow_level(4, 0.5)
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.02
	env.volumetric_fog_albedo = Color(0.55, 0.62, 0.6)
	env.volumetric_fog_emission = Color(0.006, 0.032, 0.03)
	env.volumetric_fog_emission_energy = 1.0
	env.volumetric_fog_anisotropy = 0.6
	env.volumetric_fog_length = 64.0
	env.volumetric_fog_ambient_inject = 0.15
	var grade := PostGrade.new()
	grade.tint = Color(1.0, 0.98, 0.95)
	grade.lift = Color(0.0, 0.012, 0.014)  # teal shadows
	grade.saturation = 1.2
	grade.contrast = 1.08
	grade.aberration = 0.15
	grade.vignette = 0.6
	grade.grain = 0.012
	wing.grade = grade
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _area_of(p: Vector3) -> StringName:
	if p.z < -30.5:
		return &"dome"
	if p.x < -15.6:
		return &"pit"
	if p.x > 45.8:
		return &"flyloft"
	if p.x > 15.2 and p.z > 30.0:
		return &"corridor"
	if p.z > 16.0:
		return &"foyer"
	return &"auditorium"


func _look_for(c: Vector3, delta: float) -> void:
	var a := _area_of(c)
	var l: Array = LOOK[a]
	var k := 1.0 if a != _area else clampf(delta * 2.0, 0.0, 1.0)  # cut on a jump, ease when walking
	if _area == &"":
		k = 1.0
	_area = a
	env.tonemap_exposure = lerpf(env.tonemap_exposure, l[0], k)
	env.volumetric_fog_density = lerpf(env.volumetric_fog_density, l[1], k)
	env.volumetric_fog_albedo = env.volumetric_fog_albedo.lerp(l[2], k)
	env.ambient_light_energy = lerpf(env.ambient_light_energy, l[3], k)


# =============================================================================================
# Placement helpers

## A model, no colliders (the gameplay boxes collide), placed by position, yaw and scale.
func _put(model: String, pos: Vector3, yaw_deg: float = 0.0, scale_: Vector3 = Vector3.ONE, parent: Node = self) -> Node3D:
	var n := MaterialLib.instance(MODELS + model + ".glb", MAT_DIRS)
	for b: Node in n.find_children("*", "CollisionObject3D", true, false):
		b.queue_free()
	n.position = pos
	n.rotation_degrees.y = yaw_deg
	n.scale = scale_
	parent.add_child(n)
	return n


## Run a 4 m bay model along a wall: centres from `a` to `b` in steps of 4 m.
func _bays(model: String, a: Vector3, b: Vector3, yaw: float, swap: Dictionary = {}) -> void:
	var n := int(round(a.distance_to(b) / 4.0))
	for i: int in n + 1:
		var p := a.lerp(b, float(i) / maxf(n, 1))
		var m := _put(model, p, yaw)
		if not swap.is_empty():
			_swap(m, swap)


## Swap materials by name on an instanced model (e.g. the pit's darker panelling).
func _swap(root: Node, map: Dictionary) -> void:
	for mi: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		for i: int in mi.mesh.get_surface_count():
			var m := mi.get_active_material(i)
			if m and map.has(m.resource_name):
				mi.set_surface_override_material(i, MaterialLib.lookup(map[m.resource_name], MAT_DIRS))


## Many copies of one single-mesh model as one MultiMesh (seats, balusters, staves).
func _multi(model: String, xforms: Array[Transform3D]) -> MultiMeshInstance3D:
	var src := MaterialLib.instance(MODELS + model + ".glb", MAT_DIRS)
	var mi := src.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	var mesh := mi.mesh.duplicate() as Mesh
	for i: int in mesh.get_surface_count():
		mesh.surface_set_material(i, mi.get_active_material(i))
	src.free()
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = xforms.size()
	for i: int in xforms.size():
		mm.set_instance_transform(i, xforms[i])
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	add_child(mmi)
	return mmi


## Pieces of a 2.5 m balustrade from a to b, sheared so the balusters stay plumb on a slope.
func _balustrade(a: Vector3, b: Vector3, out: Array[Transform3D]) -> void:
	var d := b - a
	var n := maxi(1, int(ceil(Vector3(d.x, 0, d.z).length() / 2.5)))
	var x := d / float(n) / 2.5
	var flat := Vector3(d.x, 0, d.z).normalized()
	var z := flat.cross(Vector3.UP).normalized()  # right-handed, so faces keep their winding
	for i: int in n:
		var basis := Basis(x, Vector3.UP, z)
		out.append(Transform3D(basis, a + d * ((float(i) + 0.5) / float(n))))


func _hide_mesh(body_name: String) -> void:
	var b := wing.find_child(body_name, true, false)
	for mi: Node in b.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).visible = false


func _omni(pos: Vector3, col: Color, energy: float, range_: float, shadow: bool = false, fog: float = 0.0) -> OmniLight3D:  # fills stay out of the fog (GPU)
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = col
	l.light_energy = energy
	l.omni_range = range_
	l.omni_attenuation = 1.2
	l.shadow_enabled = shadow
	l.light_volumetric_fog_energy = fog
	add_child(l)
	return l


func _spot(pos: Vector3, at: Vector3, col: Color, energy: float, range_: float, angle: float, shadow: bool = false, fog: float = 1.0) -> SpotLight3D:
	var l := SpotLight3D.new()
	l.light_color = col
	l.light_energy = energy
	l.spot_range = range_
	l.spot_angle = angle
	l.spot_attenuation = 0.8
	l.shadow_enabled = shadow
	l.light_volumetric_fog_energy = fog
	add_child(l)
	l.look_at_from_position(pos, at, Vector3.UP if absf((at - pos).normalized().y) < 0.99 else Vector3.FORWARD)
	return l


## A Chladni disc of light lying on the floor (or water), fed by the instruments near it.
func _disc(centre: Vector3, radius: float, tint: Color, base: float, n_: float, m_: float) -> void:
	var q := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(radius, radius) * 2.0
	q.mesh = pm
	q.position = centre
	q.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var m := ShaderMaterial.new()
	m.shader = load(SHADERS + "cymatics.gdshader")
	m.set_shader_parameter(&"tint", tint)
	m.set_shader_parameter(&"level", base)
	m.set_shader_parameter(&"n_mode", n_)
	m.set_shader_parameter(&"m_mode", m_)
	q.material_override = m
	add_child(q)
	_discs.append([m, centre, radius + 3.0, base])


# =============================================================================================
# Areas

func _foyer() -> void:
	# walls: panelled bays (damask, gilt frames, pilasters, lunettes) on three sides
	_bays("panel_bay", Vector3(-15, 0, 18), Vector3(-15, 0, 38), 90.0)
	_put("panel_bay", Vector3(-15, 0, 41), 90.0, Vector3(0.5, 1, 1))
	_bays("panel_bay", Vector3(15, 0, 18), Vector3(15, 0, 34), -90.0)
	_bays("panel_bay", Vector3(-12, 0, 42), Vector3(12, 0, 42), 180.0)
	for x: float in [-14.5, 14.5]:
		_put("panel_bay", Vector3(x, 0, 42), 180.0, Vector3(0.25, 1, 1))
	# the grand stair over the ramp collider (treads straddle the slope), balustrades, the landing rail
	_hide_mesh("FoyerRamp")
	_put("stair", Vector3(0, -0.14, 30))
	var rail: Array[Transform3D] = []
	for sx: float in [-1.0, 1.0]:
		_balustrade(Vector3(sx * 6.3, 0.05, 30.0), Vector3(sx * 6.3, 2.85, 37.0), rail)
		_balustrade(Vector3(sx * 6.3, 2.8, 37.1), Vector3(sx * 14.8, 2.8, 37.1), rail)
	_multi("balustrade", rail)
	# the colonnade between the foyer and the stalls, a coffered ceiling with its fresco, chandeliers
	_put("screen", Vector3(0, 0, 16))
	_put("ceiling", Vector3(0, 14.6, 29.25), 0.0, Vector3(1, 1, 26.5 / 46.0))
	for z: float in [22.0, 34.0]:
		_put("chandelier", Vector3(0, 14.4, z), 0.0, Vector3.ONE * 0.6)
		_omni(Vector3(0, 11.4, z), Color("ffe2bc"), 7.0, 18.0, false, 1.0)
	_omni(Vector3(0, 6, 40), Color("ffd2a0"), 1.5, 12.0)  # gallery wash, so the stair's head reads
	_spot(Vector3(0, 12, 17), Vector3(0, 0.5, 19.5), Color("ffe0b0"), 6.0, 16.0, 18.0)  # the demo horn


func _auditorium() -> void:
	# the horseshoe: three tiers of boxes down both sides; the pit opening framed by a portal
	_bays("tier_bay", Vector3(-15, 0, 14), Vector3(-15, 0, -2), 90.0)
	_put("portal", Vector3(-15, 0, -10), 90.0)
	_bays("tier_bay", Vector3(-15, 0, -16), Vector3(-15, 0, -20), 90.0)
	_bays("tier_bay", Vector3(15, 0, 14), Vector3(15, 0, -18), -90.0)
	for sx: float in [-1.0, 1.0]:
		_bays("panel_bay", Vector3(sx * 15, 0, -24), Vector3(sx * 15, 0, -28), sx * -90.0, {"damask_ox": "velvet"})
	_put("proscenium", Vector3(0, 0, -22.6))
	for sx: float in [-1.0, 1.0]:
		_put("organ_case", Vector3(sx * 8.6, 0, -30), 0.0, Vector3.ONE * 0.68)
	_put("ceiling", Vector3(0, 15.0, -7))
	_put("chandelier", Vector3(0, 15.0, -4))
	_omni(Vector3(0, 10.5, -4), Color("ffe2bc"), 9.0, 30.0, false, 1.5)
	# warm boxes: a lamp in each tier run, low energy, no shadows
	for sx: float in [-1.0, 1.0]:
		for z: float in [8.0, -14.0]:
			_omni(Vector3(sx * 13.2, 7.5, z), Color("ffd6a6"), 2.0, 9.0)
	# footlights up the proscenium and a cold top light on the stage
	_spot(Vector3(0, 0.6, -19.5), Vector3(0, 9, -23), Color("ffe2bc"), 6.0, 18.0, 55.0, false, 0.6)
	_spot(Vector3(0, 13.5, -24), Vector3(0, 0, -26.5), Color("8ff5e0"), 5.0, 18.0, 28.0, true, 2.0)
	# La Sirena hangs over the stage in her own light
	_put("sirena", Vector3(0, 2.6, -27.6), 0.0, Vector3.ONE * 0.66)
	_omni(Vector3(0, 6, -26.5), Color("6fffe0"), 2.4, 10.0, false, 1.0)
	for sx: float in [-1.0, 1.0]:  # stage wings: warm working light either side of the opening
		_omni(Vector3(sx * 10.0, 5.0, -25.5), Color("ffd6a6"), 4.0, 11.0, false, 1.0)
	# the flooded stalls: black water to the stage lip, seats sunk to the cushions
	var water := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(30, 37)
	pm.subdivide_width = 2
	pm.subdivide_depth = 2
	water.mesh = pm
	water.position = Vector3(0, 0.22, -2.5)
	_water = ShaderMaterial.new()
	_water.shader = load(SHADERS + "water.gdshader")
	if compat():  # no SSR on the web build, so the mirror is missing: lift the basin so it reads as water, not void
		_water.set_shader_parameter(&"deep", Vector3(0.02, 0.1, 0.1))
	water.material_override = _water
	water.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(water)
	# the stalls: two banks of eight rows (the fifth row left out as the cross aisle) of 11 seats, a standard at each row end,
	# raised to the floor so they read from the aisle; one collider box per row, the centre and cross aisles stay open
	var seats: Array[Transform3D] = []
	var ends: Array[Transform3D] = []
	for r: int in 9:
		if r == 4:
			continue
		var z := 3.4 + 1.15 * r
		for sx: float in [-1.0, 1.0]:
			for i: int in 11:
				var x := sx * (2.6 + 0.78 * i)
				seats.append(Transform3D(Basis(Vector3.UP, PI + sx * 0.012 * i), Vector3(x, 0.0, z)))
			ends.append(Transform3D(Basis(Vector3.UP, 0.0 if sx < 0.0 else PI), Vector3(sx * 2.21, 0.0, z)))
			ends.append(Transform3D(Basis(Vector3.UP, PI if sx < 0.0 else 0.0), Vector3(sx * 10.79, 0.0, z)))
			var body := StaticBody3D.new()
			body.position = Vector3(sx * 6.5, 0.5, z)
			var cs := CollisionShape3D.new()
			var box := BoxShape3D.new()
			box.size = Vector3(8.6, 1.0, 0.6)
			cs.shape = box
			body.add_child(cs)
			add_child(body)
	_multi("stall_seat", seats)
	_multi("stall_end", ends)
	# a low warm wash over the stalls so the velvet and gilt read from the aisle
	for sx: float in [-1.0, 1.0]:
		_omni(Vector3(sx * 6.5, 2.4, 5.5), Color("ffcf9a"), 3.0, 8.0)
		_omni(Vector3(sx * 6.5, 2.4, 11.0), Color("ffcf9a"), 3.0, 8.0)


func _pit() -> void:
	# the pit's own panelling: oak wainscot, ebony fields, whole ebony pilasters (no marble stubs)
	_bays("pit_bay", Vector3(-32, -3, -2), Vector3(-32, -3, -18), 90.0)
	_bays("pit_bay", Vector3(-18, -3, -20), Vector3(-30, -3, -20), 0.0)
	_bays("pit_bay", Vector3(-18, -3, 0), Vector3(-30, -3, 0), 180.0)
	# the upper fields are under-stage timberwork: the fly loft's oak framing over the boarding
	var frame: Array[Transform3D] = []
	for i: int in 5:
		frame.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-31.9, -0.2, -2.0 - 4.0 * i)))
	for i: int in 4:
		frame.append(Transform3D(Basis.IDENTITY, Vector3(-18.0 - 4.0 * i, -0.2, -19.9)))
		frame.append(Transform3D(Basis(Vector3.UP, PI), Vector3(-18.0 - 4.0 * i, -0.2, -0.1)))
	_multi("loft_wall", frame)
	_hide_mesh("Gantry")
	_put("wind_chest", Vector3(-22, -4, -17))
	# warm fills on the organ case's two pipe flats (west and front), so it reads as gilt and tin, not a block
	_omni(Vector3(-28.5, -0.5, -17.0), Color("ffd6a6"), 2.2, 6.0)
	_omni(Vector3(-20.5, -0.5, -12.0), Color("ffd6a6"), 1.6, 5.5)
	_hide_mesh("PitRamp")
	_swap(_put("stair_pit", Vector3(-21.5, -3.13, -10), 90.0), {"marble_ivory": "boards", "marble_teal": "ebony"})
	# the band's chairs and stands, left as they stood; a cello down on its side
	for p: Array in [[Vector3(-21.5, -3, -4.2), 200.0], [Vector3(-24.0, -3, -3.4), 175.0], [Vector3(-26.6, -3, -4.0), 150.0],
			[Vector3(-25.2, -3, -7.6), 130.0], [Vector3(-19.6, -3, -6.8), 240.0]]:
		_put("stand", p[0], p[1])
		_put("seat", p[0] + Vector3(0, 0, 0.9).rotated(Vector3.UP, deg_to_rad(p[1])), p[1] + 180.0)
	var cello := _put("cello", Vector3(-23.0, -2.85, -2.2), 70.0)
	cello.rotation_degrees.x = 90.0
	# the well's cymatics, amber stand lamps, the teal spill down the stair
	_disc(Vector3(-22, -2.97, -2), 2.4, Color(1.0, 0.7, 0.35), 0.18, 4.0, 5.0)
	_omni(Vector3(-24.2, -1.4, -4.0), Color("ffd6a6"), 5.0, 9.0, false, 2.0)
	_omni(Vector3(-28.5, -0.8, -12.0), Color("ffd6a6"), 4.5, 9.0, false, 2.0)
	_omni(Vector3(-22.0, 3.5, -17.0), Color("ffd6a6"), 3.0, 10.0, false, 1.0)  # over the wind-chest deck
	_spot(Vector3(-15.5, 5.0, -10), Vector3(-22, -3, -10), Color("6fd8c8"), 4.0, 16.0, 30.0, false, 1.5)


func _corridor() -> void:
	_bays("panel_bay", Vector3(17, 2.8, 36), Vector3(41, 2.8, 36), 0.0)
	_put("panel_bay", Vector3(44.35, 2.8, 36), 0.0, Vector3(0.7, 1, 1))  # its end pilaster stays inside the corridor mouth (x < 46), not loose in the loft
	_bays("panel_bay", Vector3(17, 2.8, 42), Vector3(41, 2.8, 42), 180.0)
	_put("panel_bay", Vector3(44.35, 2.8, 42), 180.0, Vector3(0.7, 1, 1))
	# the flip ceiling, coffered on its underside; chairs bolted to it as if it were the floor
	_hide_mesh("FlipCeiling")
	_put("coffer_panel", Vector3(27, 5.8, 39))
	for x: float in [20.2, 30.5, 40.8]:  # the corridor's own coffered ceiling, high above
		_put("coffer_panel", Vector3(x, 14.0, 39), 0.0, Vector3(1.03, 1, 1))
	for x: float in [23.5, 25.5, 28.5, 30.5]:
		for z: float in [36.8, 41.2]:
			var s := _put("seat", Vector3(x, 5.8, z), 90.0 if z < 39.0 else -90.0)
			s.rotation_degrees.z = 180.0
	# the gap: black water far below
	_hide_mesh("GapFloor")
	var gap := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(8, 6)
	gap.mesh = pm
	gap.position = Vector3(27, -1.2, 39)
	gap.material_override = _water
	gap.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(gap)
	# the score: two staves overhead the length of the corridor
	var staves: Array[Transform3D] = []
	for z: float in [37.4, 40.6]:
		for i: int in 8:
			staves.append(Transform3D(Basis(Vector3.UP, PI if z > 39.0 else 0.0), Vector3(16.5 + 4.0 * i + 2.0, 8.4, z)))
	_multi("stave", staves)
	# pier mirrors facing each other across the corridor
	for x: float in [19.0, 35.0, 39.0]:
		_put("mirror", Vector3(x, 4.0, 36.25), 0.0)
		_put("mirror", Vector3(x + 2.0, 4.0, 41.75), 180.0)
	for x: float in [19.0, 27.0, 35.0, 43.0]:
		_spot(Vector3(x, 11.5, 39), Vector3(x, 2.8, 39), Color("9ff0e0"), 4.0, 12.0, 26.0, false, 1.2)
	_omni(Vector3(17, 5.0, 39), Color("ffe2bc"), 2.0, 8.0)
	_omni(Vector3(43, 5.0, 39), Color("ffe2bc"), 2.0, 8.0)
	# sconce wash: warm light pooled on the oxblood damask between the piers
	for x: float in [21.0, 29.0, 37.0]:
		_omni(Vector3(x, 3.6, 37.0), Color("ffd6a6"), 2.0, 5.0, false, 0.5)
		_omni(Vector3(x + 2.0, 3.6, 41.0), Color("ffd6a6"), 2.0, 5.0, false, 0.5)


func _fly_loft() -> void:
	# the fly tower's brick skin: piers every 4 m, string courses, a corbel table, pin-rail brackets and rope
	# cleats on the piers (visual only; walls and colliders unchanged)
	var brick: Array[Transform3D] = []
	var hi: Array[Transform3D] = []  # loading galleries high on the north and south walls
	for i: int in 4:
		brick.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(62, 2.8, 32.0 + 4.0 * i)))
		brick.append(Transform3D(Basis(Vector3.UP, PI), Vector3(48.0 + 4.0 * i, 2.8, 46)))
		brick.append(Transform3D(Basis.IDENTITY, Vector3(48.0 + 4.0 * i, 2.8, 30)))
		hi.append(Transform3D(Basis(Vector3.UP, PI), Vector3(48.0 + 4.0 * i, 12.2, 46)))
		hi.append(Transform3D(Basis.IDENTITY, Vector3(48.0 + 4.0 * i, 12.2, 30)))
	for z: float in [31.0, 35.0, 44.0]:  # the west wall either side of the corridor's mouth (z 37..42)
		brick.append(Transform3D(Basis(Vector3.UP, PI / 2), Vector3(46, 2.8, z)))
	_multi("loft_brick", brick)
	var fly: Array[Transform3D] = []  # the fly gallery on the east wall carries the catwalk rail
	for i: int in 4:
		fly.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(62, 9.0, 32.0 + 4.0 * i)))
	_multi("loft_gallery", fly + hi)
	# the lines hang 0.3 m off the brick, clear of the piers, onto the pin rail on its brackets
	_bays("rigging", Vector3(61.7, 2.8, 32), Vector3(61.7, 2.8, 44), -90.0)
	_bays("rigging", Vector3(48, 2.8, 45.7), Vector3(60, 2.8, 45.7), 180.0)
	_bays("rigging", Vector3(48, 2.8, 30.3), Vector3(60, 2.8, 30.3), 0.0)
	# a painted seascape flown out, hem at 7.6 m, and a second drop further up
	_put("backdrop", Vector3(54.5, 14.2, 43.6), 180.0)
	_spot(Vector3(54.5, 3.6, 36.0), Vector3(54.5, 8.5, 43.6), Color("ffd9a8"), 1.6, 14.0, 40.0, false, 0.3)  # footlight on the drop
	_put("backdrop", Vector3(54.0, 18.5, 33.0), 0.0, Vector3(1.0, 1.0, 1.0))
	var walk: Array[Transform3D] = []
	for i: int in 4:
		walk.append(Transform3D(Basis(Vector3.UP, -PI / 2), Vector3(60.7, 9.0, 32.0 + 4.0 * i)))  # on the gallery's front edge
		walk.append(Transform3D(Basis(Vector3.UP, PI), Vector3(48.0 + 4.0 * i, 12.2, 44.7)))
		walk.append(Transform3D(Basis.IDENTITY, Vector3(48.0 + 4.0 * i, 12.2, 31.3)))
	_multi("catwalk", walk)
	# moonlight down the skylight onto the fork; a warm work lamp on the floor
	_spot(Vector3(52, 22, 36), Vector3(56, 2.8, 40), Color("bfe8ff"), 7.0, 30.0, 12.0, true, 0.8)
	if compat():
		shaft(self, Vector3(52, 22, 36), Vector3(56, 2.8, 40), Color("bfe8ff"), 12.0)
	_omni(Vector3(54, 11, 38), Color("ffcf9a"), 2.0, 14.0, false, 0.3)  # grid lamp: the rigging and drops
	_omni(Vector3(49.5, 4.2, 33.5), Color("ffd6a6"), 2.5, 8.0, false, 1.5)
	_omni(Vector3(56, 5.0, 40), Color("8ff0d8"), 1.0, 5.0)
	# rope-lamps along the rigging walls: warm pools on the pin rails and sandbags
	for p: Vector3 in [Vector3(51, 4.0, 31.0), Vector3(58, 4.0, 31.0), Vector3(61.0, 4.0, 38), Vector3(51, 4.0, 45.0), Vector3(58, 4.0, 45.0)]:
		_omni(p, Color("ffd6a6"), 3.0, 6.0, false, 0.4)


func _dome() -> void:
	_bays("tier_bay", Vector3(-12, 0, -32), Vector3(-12, 0, -60), 90.0)
	_bays("tier_bay", Vector3(12, 0, -32), Vector3(12, 0, -60), -90.0)
	_put("organ_case", Vector3(0, 0, -62), 0.0, Vector3.ONE * 1.1)
	_hide_mesh("Ledge")
	_put("royal_box", Vector3(0, 8, -60))
	# the lid keeps its collider; the eye goes up into a painted dome
	_hide_mesh("Lid")
	_put("dome_shell", Vector3(0, 16, -46), 0.0, Vector3(0.86, 1.0, 1.14))
	_disc(Vector3(0, 0.03, -46), 7.0, Color(0.55, 1.0, 0.85), 0.35, 6.0, 8.0)
	for i: int in 6:
		var a := TAU * (float(i) + 0.5) / 6.0
		_omni(Vector3(sin(a) * 10.0, 8.0, -46 + cos(a) * 12.0), Color("ffd6a6"), 1.8, 8.0)
	_spot(Vector3(0, 28, -46), Vector3(0, 0, -46), Color("8ff5e0"), 4.0, 34.0, 20.0, false, 0.6)
	for p: Vector3 in [Vector3(-9, 14.5, -46), Vector3(9, 14.5, -46), Vector3(0, 14.5, -35), Vector3(0, 14.5, -57)]:
		_omni(p, Color("ffd6a6"), 0.8, 12.0, false, 0.4)  # cornice uplights wash the painted dome


# =============================================================================================
# Particles: drifting score pages and dust in the haze

func _particles() -> void:
	for spec: Array in [[Vector3(0, 7, 28), Vector3(13, 6, 11), 24], [Vector3(0, 7, -6), Vector3(13, 6, 18), 40],
			[Vector3(0, 8, -46), Vector3(10, 7, 14), 30], [Vector3(31, 6, 39), Vector3(14, 3, 2.5), 14]]:
		_pages(spec[0], spec[1], spec[2])
	for spec: Array in [[Vector3(0, 6, 28), Vector3(15, 6, 13)], [Vector3(0, 7, -7), Vector3(15, 7, 23)], [Vector3(-24, 2, -10), Vector3(8, 5, 10)],
			[Vector3(31, 6, 39), Vector3(15, 4, 3)], [Vector3(54, 8, 38), Vector3(8, 7, 8)], [Vector3(0, 8, -46), Vector3(12, 8, 16)]]:
		_dust(spec[0], spec[1])


func _pages(centre: Vector3, extents: Vector3, count: int) -> void:
	var p := GPUParticles3D.new()
	p.position = centre
	p.amount = count
	p.lifetime = 24.0
	p.preprocess = 24.0
	p.visibility_aabb = AABB(-extents - Vector3.ONE * 3.0, (extents + Vector3.ONE * 3.0) * 2.0)
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = extents
	pm.gravity = Vector3(0, -0.05, 0)
	pm.initial_velocity_min = 0.05
	pm.initial_velocity_max = 0.25
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 180.0
	pm.angular_velocity_min = -25.0
	pm.angular_velocity_max = 25.0
	pm.angle_min = 0.0
	pm.angle_max = 360.0
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.6
	pm.turbulence_noise_scale = 6.0
	pm.turbulence_influence_min = 0.05
	pm.turbulence_influence_max = 0.15
	pm.particle_flag_rotate_y = true
	var fade := Curve.new()
	fade.add_point(Vector2(0.0, 0.0))
	fade.add_point(Vector2(0.1, 1.0))
	fade.add_point(Vector2(0.9, 1.0))
	fade.add_point(Vector2(1.0, 0.0))
	var ct := CurveTexture.new()
	ct.curve = fade
	pm.scale_curve = ct
	p.process_material = pm
	pm.scale_min = 0.6  # loose pages of several sizes
	pm.scale_max = 1.5
	var src := (load(MODELS + "page.glb") as PackedScene).instantiate()
	var q := ((src.find_children("*", "MeshInstance3D", true, false)[0]) as MeshInstance3D).mesh.duplicate() as Mesh
	src.free()
	q.surface_set_material(0, MaterialLib.lookup("score_paper", MAT_DIRS))
	p.draw_pass_1 = q
	p.transform_align = GPUParticles3D.TRANSFORM_ALIGN_DISABLED
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)


func _dust(centre: Vector3, extents: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.position = centre
	p.amount = 220
	p.lifetime = 14.0
	p.preprocess = 14.0
	p.visibility_aabb = AABB(-extents - Vector3.ONE, (extents + Vector3.ONE) * 2.0)
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = extents
	pm.gravity = Vector3(0, 0.02, 0)
	pm.initial_velocity_min = 0.0
	pm.initial_velocity_max = 0.08
	pm.spread = 180.0
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.3
	pm.turbulence_noise_scale = 3.0
	pm.scale_min = 0.5
	pm.scale_max = 1.4
	var fade := Curve.new()
	fade.add_point(Vector2(0.0, 0.0))
	fade.add_point(Vector2(0.2, 1.0))
	fade.add_point(Vector2(0.8, 1.0))
	fade.add_point(Vector2(1.0, 0.0))
	var ct := CurveTexture.new()
	ct.curve = fade
	pm.scale_curve = ct
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(0.04, 0.04)  # the soft dot's core is about half of this
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.albedo_color = Color(1.0, 0.8, 0.55, 0.3)
	mat.albedo_texture = _soft_dot()  # a round mote with a feathered edge, never a square
	q.material = mat
	p.draw_pass_1 = q
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)


## Compatibility (the web build) has no volumetric fog, so a fogged light draws no shaft there.
static func compat() -> bool:
	return RenderingServer.get_current_rendering_method() == "gl_compatibility"


## A faint additive cone standing in for a volumetric light shaft from `from` (narrow) to `to` (wide).
static func shaft(parent: Node3D, from: Vector3, to: Vector3, col: Color, spread_deg: float) -> void:
	var d := to - from
	var len := d.length()
	var cm := CylinderMesh.new()
	cm.top_radius = len * tan(deg_to_rad(spread_deg))
	cm.bottom_radius = 0.05
	cm.height = len
	cm.radial_segments = 24
	cm.rings = 1
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.albedo_color = Color(col.r, col.g, col.b, 0.07)
	var mi := MeshInstance3D.new()
	mi.mesh = cm
	mi.material_override = mat
	mi.transform = Transform3D(Basis(Quaternion(Vector3.UP, d / len)), (from + to) * 0.5)
	parent.add_child(mi)


static func _soft_dot() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 1))
	g.set_color(1, Color(1, 1, 1, 0))
	g.add_point(0.35, Color(1, 1, 1, 0.45))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(0.5, 0.0)
	gt.width = 32
	gt.height = 32
	return gt


func _probes() -> void:
	for p: Array in [[Vector3(0, 7, 29), Vector3(31, 15, 27)], [Vector3(0, 7.5, -7), Vector3(31, 16, 47)], [Vector3(-24, 3, -10), Vector3(17, 13, 21)],
			[Vector3(31, 7, 39), Vector3(31, 12, 7)], [Vector3(54, 8, 38), Vector3(17, 14, 17)], [Vector3(0, 8, -46), Vector3(25, 17, 33)]]:
		var rp := ReflectionProbe.new()
		rp.position = p[0]
		rp.size = p[1]
		rp.box_projection = true
		rp.interior = true
		rp.update_mode = ReflectionProbe.UPDATE_ONCE
		rp.max_distance = 60.0
		rp.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
		add_child(rp)


# =============================================================================================
# Cymatics: the water and the discs answer whatever is sounding near them

func _feed_cymatics() -> void:
	var srcs: Array = []
	for n: Node in get_tree().get_nodes_in_group(Instrument.GROUP):
		var inst := n as Instrument
		if inst.env > 0.01:
			srcs.append(inst)
	srcs.sort_custom(func(a: Instrument, b: Instrument) -> bool: return a.env > b.env)
	var packed: Array[Vector4] = []
	for inst: Instrument in srcs:
		if packed.size() == 8:
			break
		var p := inst.global_position
		var k := 3.0 * inst.pitch + (2.0 if inst.kind == &"sink" else 0.0)
		packed.append(Vector4(p.x, p.z, inst.env, k))
	var count := packed.size()
	while packed.size() < 8:
		packed.append(Vector4.ZERO)
	_water.set_shader_parameter(&"src", packed)
	_water.set_shader_parameter(&"src_count", count)
	for d: Array in _discs:
		var lvl: float = d[3]
		for inst: Instrument in srcs:
			if inst.global_position.distance_to(d[1]) < d[2]:
				lvl = maxf(lvl, inst.env)
		(d[0] as ShaderMaterial).set_shader_parameter(&"level", lvl)


# =============================================================================================
# Music: one leitmotif (G, E, C, the cadence) re-voiced per area, as vertical stems

## Per area: stem intensity (0 bed, .33 + strings, .66 + the sung motif, 1 + choir), ambience, its dB.
const SCORE := {
	&"foyer": [0.2, "amb_hall", -4.0],
	&"auditorium": [0.62, "amb_hall", -2.0],
	&"pit": [0.4, "amb_drips", -3.0],
	&"corridor": [0.45, "amb_water", -6.0],
	&"flyloft": [0.3, "amb_rigging", -3.0],
	&"dome": [1.0, "amb_crystal", -3.0],
}


func _music_for(area: StringName) -> void:
	if area == _music_now:
		return
	_music_now = area
	var s: Array = SCORE[area]
	Audio.play_ambience(load(AUDIO + s[1] + ".ogg"), 3.0, s[2])
	if not (wing.get(&"_fall_on") or Quest.is_done(&"fall")):  # the fall silences the score for good
		Audio.set_intensity(s[0], 4.0)
