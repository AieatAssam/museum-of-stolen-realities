class_name Player
extends CharacterBody3D
## Vesper. First-person body spawned by Game into every wing (wings never instance it).
##
## Wing-facing API:
##   gravity_vector            — world gravity for the player (Wing sets it on entry; tween it freely).
##   add_mode(name, mode)      — register a MovementMode; set_mode(name) switches.
##   signals primary/secondary(pressed), jumped, landed(impact_speed), footstep(surface)
##   input_enabled / look_enabled — cinematics flip these.
##   teleport(xform)           — move + face, zeroes velocity.
## Built-in modes: &"walk", &"swim", &"silhouette", &"rail", &"grapple", &"seated".

signal primary(pressed: bool)
signal secondary(pressed: bool)
signal jumped
signal landed(impact_speed: float)
signal footstep(surface: StringName)
signal mode_changed(mode_name: StringName)

const RADIUS := 0.32
const HEIGHT := 1.8
const CROUCH_HEIGHT := 1.15
## Tallest riser walked up without jumping (and snapped down when walking off). Stairs need no ramp.
const STEP_HEIGHT := 0.4

var gravity_vector: Vector3 = Vector3(0, -15.0, 0)
var modes: Dictionary = {}  # StringName -> MovementMode
var mode: MovementMode
var input_enabled: bool = true
var look_enabled: bool = true
var base_fov: float = 90.0
## Screenshake "trauma" 0..1; displacement = trauma² × smooth noise; decays ~0.5/s.
var trauma: float = 0.0

var head: Node3D
var pitch_node: Node3D
var camera: Camera3D
var feet_ray: RayCast3D
var _shape: CylinderShape3D
var _col: CollisionShape3D

var yaw: float = 0.0
var pitch: float = 0.0
var _bob_phase: float = 0.0
var _bob_amount: float = 0.0
var _dip: float = 0.0
var _dip_vel: float = 0.0
var _eye: float = 1.62
var _was_on_floor: bool = true
var _fov_kick: float = 0.0
var _last_step_sign: float = 1.0
var _look_lag: Vector2 = Vector2.ZERO
var _crouched: bool = false
var _roll: float = 0.0
var _roll_vel: float = 0.0
var _noise := FastNoiseLite.new()
var _shake_t: float = 0.0
## Camera lag that hides a step-up/step-down pop: set to -dy on a step, decays to 0.
var _step_offset: float = 0.0
var _teleported: bool = false


func _init() -> void:
	name = "Player"
	collision_layer = 1 << 1
	collision_mask = 1 | (1 << 4)
	floor_max_angle = deg_to_rad(48.0)
	floor_snap_length = STEP_HEIGHT + 0.05
	floor_constant_speed = true
	floor_block_on_wall = true
	safe_margin = 0.02
	# Flat-bottomed cylinder, not a capsule: a capsule's round bottom meets a riser edge on its
	# curve, so step-up lands it on the corner at a too-steep normal and it slides back off.
	_shape = CylinderShape3D.new()
	_shape.radius = RADIUS
	_shape.height = HEIGHT
	_col = CollisionShape3D.new()
	_col.shape = _shape
	_col.position.y = HEIGHT * 0.5
	add_child(_col)
	head = Node3D.new()
	head.name = "Head"
	head.position.y = _eye
	add_child(head)
	pitch_node = Node3D.new()
	head.add_child(pitch_node)
	camera = Camera3D.new()
	camera.name = "Camera"
	camera.near = 0.05
	camera.far = 600.0
	pitch_node.add_child(camera)
	feet_ray = RayCast3D.new()
	feet_ray.position.y = 0.2
	feet_ray.target_position = Vector3(0, -0.6, 0)
	feet_ray.collision_mask = 1 | (1 << 4)
	add_child(feet_ray)
	add_mode(&"walk", WalkMode.new())
	add_mode(&"swim", SwimMode.new())
	add_mode(&"silhouette", SilhouetteMode.new())
	add_mode(&"rail", RailMode.new())
	add_mode(&"grapple", GrappleMode.new())
	add_mode(&"seated", SeatedMode.new())


func _ready() -> void:
	add_to_group(&"player")
	set_mode(&"walk")
	camera.make_current()
	_apply_settings()
	Save.settings_changed.connect(_apply_settings)


func _apply_settings() -> void:
	base_fov = float(Save.settings["fov"])


# --- modes ---------------------------------------------------------------------

func add_mode(mode_name: StringName, m: MovementMode) -> void:
	m.player = self
	m.name = mode_name
	modes[mode_name] = m


func set_mode(mode_name: StringName) -> void:
	var next: MovementMode = modes.get(mode_name)
	if next == null:
		push_error("Player: unknown movement mode %s" % mode_name)
		return
	if next == mode:
		return
	var prev := mode
	if prev:
		prev.exit(next)
	mode = next
	next.enter(prev)
	mode_changed.emit(mode_name)


func mode_name() -> StringName:
	return mode.name if mode else &""


# --- input helpers (modes use these) ---------------------------------------------

func move_input() -> Vector2:
	if not input_enabled:
		return Vector2.ZERO
	return Input.get_vector(&"move_left", &"move_right", &"move_forward", &"move_back")


## Camera-yaw-relative horizontal wish direction (length 0..1), perpendicular to up.
func wish_dir() -> Vector3:
	var mi := move_input()
	var v := head.global_basis * Vector3(mi.x, 0.0, mi.y)
	v -= up_direction * v.dot(up_direction)
	return v.limit_length(1.0) if v.length() > 0.001 else Vector3.ZERO


func action_held(action: StringName) -> bool:
	return input_enabled and Input.is_action_pressed(action)


func can_stand() -> bool:
	return not test_move(global_transform, up_direction * (HEIGHT - CROUCH_HEIGHT))


func set_crouched(c: bool) -> void:
	if c == _crouched:
		return
	_crouched = c
	_shape.height = CROUCH_HEIGHT if c else HEIGHT
	_col.position.y = _shape.height * 0.5


func collision_mask_world(on: bool) -> void:
	collision_mask = (1 | (1 << 4)) if on else 0


## Step-up: if a ledge up to `height` blocks horizontal motion, lift onto it. The camera height
## is smoothed separately (see _physics_process), so stairs read as a glide, not a pop.
func try_step_up(motion: Vector3, height: float) -> void:
	# probe a little further than this tick's motion: pressed against a riser, the per-tick motion
	# is millimetres (velocity was zeroed by the wall) and can sit inside the safe margin
	var probe := motion.normalized() * maxf(motion.length(), 0.06)
	var col := KinematicCollision3D.new()
	if not test_move(global_transform, probe, col):
		return
	if col.get_normal().dot(up_direction) > 0.7:
		return  # it's a slope, move_and_slide handles it
	var up := up_direction * height
	var head_hit := KinematicCollision3D.new()
	if test_move(global_transform, up, head_hit):
		up = head_hit.get_travel()  # low ceiling: try whatever headroom there is
	var raised := global_transform.translated(up)
	if test_move(raised, probe):
		return
	var down := KinematicCollision3D.new()
	if not test_move(raised.translated(probe), -up, down) or down.get_normal().dot(up_direction) < 0.7:
		return
	var climb := (up + down.get_travel()).dot(up_direction)
	if climb > 0.005:
		global_position += up_direction * climb + motion


## Jump clipping a ceiling edge: nudge sideways so the head slides past instead of bonking.
func try_corner_correct(motion_up: Vector3, nudge: float) -> void:
	if not test_move(global_transform, motion_up):
		return
	for side: Vector3 in [global_basis.x, -global_basis.x, -head.global_basis.z, head.global_basis.z]:
		var shifted := global_transform.translated(side * nudge)
		if not test_move(global_transform, side * nudge) and not test_move(shifted, motion_up):
			global_position = shifted.origin
			return


## Add camera-shake trauma (0..1). Landing, impacts and reveals call this.
func add_trauma(amount: float) -> void:
	trauma = clampf(trauma + amount, 0.0, 1.0)


func teleport(xform: Transform3D) -> void:
	global_position = xform.origin
	velocity = Vector3.ZERO
	var f := -xform.basis.z
	yaw = atan2(-f.x, -f.z)
	pitch = 0.0
	head.rotation = Vector3(0, yaw, 0)
	pitch_node.rotation = Vector3.ZERO
	_was_on_floor = true
	_teleported = true
	_step_offset = 0.0


## Point the view at a world position (used by cinematics/tests).
func look_at_point(p: Vector3) -> void:
	var d := head.global_position.direction_to(p)
	yaw = atan2(-d.x, -d.z)
	pitch = asin(clampf(d.y, -1, 1))


# --- input ------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and look_enabled and (Input.mouse_mode == Input.MOUSE_MODE_CAPTURED or DisplayServer.get_name() == "headless"):
		var s := deg_to_rad(float(Save.settings["mouse_sensitivity"]))
		var inv := -1.0 if Save.settings["invert_y"] else 1.0
		var rel: Vector2 = (event as InputEventMouseMotion).screen_relative
		yaw -= rel.x * s
		pitch = clampf(pitch - rel.y * s * inv, deg_to_rad(-88), deg_to_rad(88))
		_look_lag += rel * 0.0015
	if not input_enabled:
		return
	for verb: StringName in [&"primary", &"secondary", &"jump", &"crouch"]:
		if event.is_action_pressed(verb) or event.is_action_released(verb):
			var pressed := event.is_action_pressed(verb)
			if mode and mode.on_verb(verb, pressed):
				continue
			if verb == &"primary":
				primary.emit(pressed)
			elif verb == &"secondary":
				secondary.emit(pressed)


func _physics_process(delta: float) -> void:
	var d := delta * Game.player_time_scale
	_align_to_gravity(d)
	var pre_vel := velocity
	var pre_pos := global_position
	if mode:
		mode.physics(d)
	var on_floor := is_on_floor()
	# a grounded vertical jump this tick is a step up/down (or floor snap): let the eye catch up
	var dy := (global_position - pre_pos).dot(up_direction)
	if on_floor and _was_on_floor and not _teleported and absf(dy) > 0.05 and absf(dy) <= STEP_HEIGHT + 0.1:
		_step_offset = clampf(_step_offset - dy, -1.0, 1.0)  # room for 2-3 quick risers; a tighter clamp snaps the excess
		head.position.y -= dy  # now, not next _process: no frame shows the body jump uncompensated
	_teleported = false
	if on_floor and not _was_on_floor:
		var impact := maxf(-pre_vel.dot(up_direction), 0.0)
		if impact > 1.5:
			_dip_vel -= minf(impact * 0.045, 0.5) * maxf(Save.motion("head_bob"), 0.35)
			if impact > 7.0:
				add_trauma(clampf((impact - 7.0) * 0.06, 0.0, 0.5))
			landed.emit(impact)
			Audio.footstep(surface(), global_position, clampf(impact / 6.0, 0.6, 1.4))
	_was_on_floor = on_floor


func _align_to_gravity(delta: float) -> void:
	if gravity_vector.length_squared() < 0.0001:
		return
	var want := -gravity_vector.normalized()
	up_direction = want
	var cur := global_basis.y
	if cur.dot(want) > 0.9999:
		return
	var axis := cur.cross(want)
	if axis.length_squared() < 1e-8:
		axis = global_basis.x
	var ang := cur.angle_to(want)
	var step := minf(ang, 4.0 * delta + ang * 6.0 * delta)
	global_basis = Basis(axis.normalized(), step) * global_basis
	global_basis = global_basis.orthonormalized()


func _process(delta: float) -> void:
	var d := delta * Game.player_time_scale
	# gamepad look
	if look_enabled and input_enabled:
		var g := Input.get_vector(&"look_left", &"look_right", &"look_up", &"look_down")
		if g.length() > 0.0:
			var sp := deg_to_rad(float(Save.settings["mouse_sensitivity"])) * 1400.0 * d
			var inv := -1.0 if Save.settings["invert_y"] else 1.0
			yaw -= g.x * sp * absf(g.x)
			pitch = clampf(pitch - g.y * sp * absf(g.y) * inv, deg_to_rad(-88), deg_to_rad(88))
	head.rotation = Vector3(0, yaw, 0)
	pitch_node.rotation = Vector3(pitch, 0, 0)

	# eye height / crouch
	var target_eye := mode.eye_height() if mode else 1.62
	_eye = lerpf(_eye, target_eye, 1.0 - exp(-10.0 * d))

	# head bob + footsteps
	var horiz := velocity - up_direction * velocity.dot(up_direction)
	var spd := horiz.length()
	var grounded := is_on_floor()
	var bob_target := clampf(spd / 6.0, 0.0, 1.2) * (mode.bob_scale() if mode else 1.0) * (1.0 if grounded else 0.0)
	_bob_amount = lerpf(_bob_amount, bob_target, 1.0 - exp(-8.0 * d))
	if grounded and spd > 0.4:
		_bob_phase += d * (5.0 + spd * 0.95)
	var s := sin(_bob_phase * 2.0)
	if grounded and spd > 0.8 and (mode == null or mode.bob_scale() > 0.0) and signf(s) != _last_step_sign and s < 0.0:
		var surf := surface()
		footstep.emit(surf)
		Audio.footstep(surf, global_position, clampf(spd / 5.0, 0.4, 1.3))
	_last_step_sign = signf(s)

	# landing dip spring
	_dip_vel += (-_dip * 60.0 - _dip_vel * 11.0) * d
	_dip += _dip_vel * d

	_step_offset *= exp(-14.0 * d)
	var bob := Save.motion("head_bob")
	head.position.y = _eye + _dip + _step_offset
	camera.position = Vector3(cos(_bob_phase) * 0.03, -absf(s) * 0.035 + 0.015, 0.0) * _bob_amount * bob
	_look_lag = _look_lag.lerp(Vector2.ZERO, 1.0 - exp(-8.0 * d))

	# strafe roll: spring-damper towards 1.5° per unit of sideways speed fraction
	var side_speed := horiz.dot(head.global_basis.x) / 6.0
	var roll_target := -clampf(side_speed, -1.0, 1.0) * deg_to_rad(1.8) * Save.motion("strafe_roll")
	_roll_vel += ((roll_target - _roll) * 90.0 - _roll_vel * 14.0) * d
	_roll += _roll_vel * d

	# trauma shake (trauma² × smooth noise), decays 0.5/s
	trauma = maxf(trauma - 0.5 * d, 0.0)
	_shake_t += d * 30.0
	var shake := trauma * trauma * Save.motion("camera_shake")
	camera.rotation = Vector3(
		deg_to_rad(2.5) * shake * _noise.get_noise_2d(_shake_t, 0.0),
		deg_to_rad(2.5) * shake * _noise.get_noise_2d(0.0, _shake_t),
		_roll - _look_lag.x * 0.2 * Save.motion("strafe_roll") + deg_to_rad(4.0) * shake * _noise.get_noise_2d(_shake_t, 50.0))

	# FOV kick
	var sprinting := action_held(&"sprint") and spd > 5.0
	_fov_kick = lerpf(_fov_kick, 6.0 * Save.motion("fov_kick") if sprinting else 0.0, 1.0 - exp(-4.0 * d))
	camera.fov = base_fov + _fov_kick


## Surface under the feet: collider meta "surface", else glTF extras {"surface": ...}, else "marble".
func surface() -> StringName:
	feet_ray.force_raycast_update()
	var c := feet_ray.get_collider()
	if c == null:
		return &"marble"
	for n: Node in [c, c.get_parent()]:
		if n == null:
			continue
		if n.has_meta(&"surface"):
			return StringName(n.get_meta(&"surface"))
		if n.has_meta(&"extras") and (n.get_meta(&"extras") as Dictionary).has("surface"):
			return StringName(n.get_meta(&"extras")["surface"])
	return &"marble"
