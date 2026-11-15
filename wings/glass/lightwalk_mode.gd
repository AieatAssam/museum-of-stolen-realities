extends WalkMode
## Vesper in the Vitrine Kingdom. Walking, plus the feel of standing on light (DESIGN_RULES §3):
## beams snap underfoot (a gentle pull toward the beam's axis when drifting off its edge), a little
## extra coyote time leaving one, and a hum whose pitch rises the longer she stays on it.
## Also carries the wind that blows through a shattered window, forever.

var on_beam: bool = false
var beam_mask: int = 0
var beam_time: float = 0.0
## Callable(pos: Vector3) -> Vector3 horizontal wind velocity (m/s); set by the wing.
var wind: Callable
var hum: AudioStreamPlayer
var _hum_db: float = -60.0


func _init() -> void:
	walk_speed = 4.2
	coyote_time = 0.16
	jump_buffer = 0.12


func enter(_from: MovementMode) -> void:
	if hum == null and player:
		hum = AudioStreamPlayer.new()
		hum.stream = load("res://wings/glass/audio/beam_hum.ogg")
		hum.bus = &"SFX"
		hum.volume_db = -60.0
		if hum.stream is AudioStreamOggVorbis:
			(hum.stream as AudioStreamOggVorbis).loop = true
		player.add_child(hum)
		hum.play()


func physics(delta: float) -> void:
	var p := player
	p.feet_ray.force_raycast_update()
	var c := p.feet_ray.get_collider()
	var was := on_beam
	on_beam = c != null and c.has_meta(&"beam") and p.is_on_floor()
	if on_beam:
		beam_time += delta
		beam_mask = int(c.get_meta(&"beam_mask", 0))
		if not was:
			Audio.sfx(load("res://wings/glass/audio/beam_touch.ogg"), p.global_position, -8.0, 0.0, randf_range(0.95, 1.08))
		_magnet(c, delta)
	else:
		beam_time = maxf(beam_time - delta * 3.0, 0.0)
	if wind.is_valid():
		var w: Vector3 = wind.call(p.global_position)
		if w.length_squared() > 0.0001:
			p.velocity += w * delta * (3.0 if p.is_on_floor() else 1.2)
	super.physics(delta)
	_update_hum(delta)


func _magnet(c: Object, delta: float) -> void:
	# Pull toward the axis only when drifting outward past 0.3 m: forgiveness, not rails.
	var a: Vector3 = c.get_meta(&"beam_a")
	var b: Vector3 = c.get_meta(&"beam_b")
	var axis := a.direction_to(b)
	var flat := Vector3(axis.x, 0, axis.z)
	if flat.length_squared() < 0.01:
		return
	var side := flat.normalized().cross(Vector3.UP)
	var off := (player.global_position - a).dot(side)
	if absf(off) > 0.3:
		var pull := -signf(off) * (absf(off) - 0.3) * 9.0
		var lateral := player.velocity.dot(side)
		if signf(lateral) == signf(off) or absf(lateral) < 0.5:
			player.velocity += side * pull * delta * 6.0


func _update_hum(delta: float) -> void:
	if hum == null:
		return
	var target := -14.0 if on_beam else -60.0
	_hum_db = lerpf(_hum_db, target, 1.0 - exp(-(10.0 if on_beam else 4.0) * delta))
	hum.volume_db = _hum_db
	hum.pitch_scale = 0.85 + minf(beam_time, 6.0) * 0.09
