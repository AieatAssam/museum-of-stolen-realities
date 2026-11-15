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

## Set by the wing: during a downbeat, fields inside flip_box invert for the flip's duration.
static var flip_active: bool = false
static var flip_box: AABB = AABB()

@export var note_id: StringName = &""
@export var kind: StringName = &"lift"
@export var radius: float = 2.2
@export var height: float = 8.0
@export var strength: float = 26.0
@export var sound: AudioStream
@export var pitch: float = 1.0

var env: float = 0.0       # 0..1 eased envelope
var timer: float = 0.0     # sustain left (seconds)
var held: bool = false     # the player is holding this note with the secondary verb


func _ready() -> void:
	add_to_group(GROUP)


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


## Acceleration (m/s^2, world Y) this instrument adds at point p.
func field_at(p: Vector3) -> float:
	if env <= 0.001:
		return 0.0
	var dx := p.x - global_position.x
	var dz := p.z - global_position.z
	var d2 := dx * dx + dz * dz
	if d2 >= radius * radius:
		return 0.0
	var h := p.y - global_position.y
	var rad := 1.0 - d2 / (radius * radius)
	var a := 0.0
	if kind == &"lift":
		if h < -0.6 or h > height:
			return 0.0
		var t := clampf(h / height, 0.0, 1.0)
		a = strength * (1.0 - t * t)
	else:
		if h < -height or h > 0.6:
			return 0.0
		a = -strength
	var sgn := -1.0 if (flip_active and flip_box.has_point(p)) else 1.0
	return a * rad * env * sgn
