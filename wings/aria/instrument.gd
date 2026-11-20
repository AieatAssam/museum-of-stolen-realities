extends Node3D
## One sounding instrument of The Drowned Aria. Striking it (the player's primary verb, aimed) starts
## its note. While the note sounds it projects a field into the player's movement (see song_mode.gd):
##   kind &"lift": a column that lifts strongest at its foot and eases out toward its top.
##   kind &"sink": a well that draws the player down through its footprint.
## The field is ACCELERATION, not gravity. The envelope eases in and out like a tide, so nothing snaps.

signal struck(instrument: Node3D)

const SUSTAIN := 9.0   # seconds a struck note keeps sounding
const ATTACK := 1.4    # seconds for the envelope to reach full field
const RELEASE := 2.2   # seconds for it to die away
const GROUP := &"aria_instruments"

@export var note_id: StringName = &""
@export var kind: StringName = &"lift"
@export var radius: float = 2.2
@export var height: float = 8.0
## How near the player must be for a strike to be offered (prompt) and to work. The demo horn only
## lifts someone standing in its column, so it is not offered from across the foyer.
@export var strike_reach: float = 14.0
@export var strength: float = 26.0
@export var sound: AudioStream
@export var pitch: float = 1.0

var env: float = 0.0       # 0..1 eased envelope
var timer: float = 0.0     # sustain left (seconds)
var held: bool = false     # the player is holding this note with the secondary verb
var carry_to: Node3D       # while held, the field follows this node in x and z (a carried lift)
var _vol: MeshInstance3D   # the visible field: a column (lift) or a well (sink), fading with env
var _vol_mat: StandardMaterial3D


func _ready() -> void:
	add_to_group(GROUP)
	# Gravity direction made visible on every renderer: a teal column rises from the lift's foot, a
	# violet well is drawn down through the sink's footprint. Unshaded and translucent, so it works on
	# Compatibility too; it is alpha-scaled by env, so it swells in with the note and dies with it.
	var cm := CylinderMesh.new()
	cm.top_radius = radius
	cm.bottom_radius = radius
	cm.height = height + 0.6 if kind == &"lift" else height * 2.0
	cm.radial_segments = 32
	cm.rings = 1
	_vol_mat = StandardMaterial3D.new()
	_vol_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_vol_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_vol_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_vol_mat.albedo_color = Color(0.45, 1.0, 0.85, 0.0) if kind == &"lift" else Color(0.5, 0.25, 0.9, 0.0)
	_vol = MeshInstance3D.new()
	_vol.mesh = cm
	_vol.material_override = _vol_mat
	_vol.top_level = true
	_vol.visible = false
	add_child(_vol)


func strike() -> void:
	timer = SUSTAIN
	if sound:
		Audio.sfx(sound, global_position + Vector3.UP, 0.0, 0.35, pitch)
	struck.emit(self)


func sounding() -> bool:
	return env > 0.5 and timer > 0.0


func _physics_process(delta: float) -> void:
	if timer > 0.0 and not held:
		timer = maxf(timer - delta, 0.0)
	var target := 1.0 if timer > 0.0 else 0.0
	env = move_toward(env, target, delta / (ATTACK if target > env else RELEASE))
	_show_field()


## Places and fades the field volume to match the envelope and the (possibly carried) centre.
func _show_field() -> void:
	_vol.visible = env > 0.001
	_vol_mat.albedo_color.a = env * 0.16
	var c := global_position
	if carry_to:
		c.x = carry_to.global_position.x
		c.z = carry_to.global_position.z
	if kind == &"lift":
		_vol.global_position = Vector3(c.x, c.y + (height - 0.6) * 0.5, c.z)
	else:
		_vol.global_position = c


## Acceleration (m/s^2, world Y) this instrument adds at point p.
func field_at(p: Vector3) -> float:
	if env <= 0.001:
		return 0.0
	var c := global_position
	if carry_to:  # a carried note follows the player in x and z and keeps its own height
		c.x = carry_to.global_position.x
		c.z = carry_to.global_position.z
	var dx := p.x - c.x
	var dz := p.z - c.z
	var d2 := dx * dx + dz * dz
	if d2 >= radius * radius:
		return 0.0
	var h := p.y - c.y
	var rad := 1.0 - d2 / (radius * radius)
	var a := 0.0
	if kind == &"lift":
		if h < -0.6 or h > height:
			return 0.0
		var t := clampf(h / height, 0.0, 1.0)
		a = strength * (1.0 - t * t)
	else:
		# the well pulls anything within its height above or below its floor origin, so a jump
		# into its footprint sinks (a grounded player stands on solid floor and is not pulled)
		if h < -height or h > height:
			return 0.0
		a = -strength
	return a * rad * env
