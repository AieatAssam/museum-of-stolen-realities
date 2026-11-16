extends Node
## Audio autoload.
##   play_music(layers)      — a "bed" of stems that loop in sync; set_intensity(0..1) fades upper stems in.
##   play_ambience(stream)   — one looping room tone, crossfaded.
##   sfx(stream, pos)        — one-shot, positional if pos is a Vector3; `reverb` sends a copy to the hall reverb.
##   ui(&"name")             — res://assets/audio/ui_<name>.ogg on the UI bus.
##   footstep(surface, pos)  — random variation of a surface set; wings add sets with register_footsteps().
##   emitter(stream, parent) — looping positional source attached to a node.

const DIR := "res://assets/audio/"

var _beds: Array[AudioStreamPlayer] = []
var _bed_streams: Array[AudioStream] = []
var _intensity: float = 0.0
var _ambience: AudioStreamPlayer
var _cache: Dictionary = {}
var _footsteps: Dictionary = {}  # surface -> Array[AudioStream]
var _last_step: Dictionary = {}
## Set by Game.quit(): no new players start while the tree is shutting down (a footstep or a late
## reveal stinger started after the stop pass is a playback still alive at exit, i.e. a leak).
var closing: bool = false
## Seconds per bar of the current bed (0 = unknown). When set, intensity changes wait for the next
## bar line (DESIGN_RULES §6: musical changes land on bar boundaries). Reset by a new bed.
var music_bar: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for surface: String in ["marble", "carpet", "wood", "stone"]:
		var set: Array[AudioStream] = []
		for i in range(1, 7):
			var s := _load("%sstep_%s_%d.ogg" % [DIR, surface, i])
			if s:
				set.append(s)
		if not set.is_empty():
			_footsteps[surface] = set


func _load(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	var s: AudioStream = load(path) if ResourceLoader.exists(path) else null
	_cache[path] = s
	return s


func stream(name: String) -> AudioStream:
	return _load(DIR + name + ".ogg")


# --- music ----------------------------------------------------------------------

func play_music(layers: Array[AudioStream], fade: float = 3.0, intensity: float = 0.0) -> void:
	if layers == _bed_streams:
		set_intensity(intensity)
		return
	for p in _beds:
		var t := create_tween()
		t.tween_property(p, "volume_db", -60.0, fade)
		t.tween_callback(p.queue_free)
	_beds.clear()
	_bed_streams = layers
	music_bar = 0.0
	_intensity = intensity
	for i in layers.size():
		if layers[i] == null:
			continue
		_set_loop(layers[i])
		var p := AudioStreamPlayer.new()
		p.stream = layers[i]
		p.bus = &"Music"
		p.volume_db = -60.0
		add_child(p)
		p.play()
		_beds.append(p)
		create_tween().tween_property(p, "volume_db", _layer_db(i), fade)


func stop_music(fade: float = 3.0) -> void:
	play_music([] as Array[AudioStream], fade)


## 0 = only the base stem; 1 = all stems.
func set_intensity(v: float, seconds: float = 2.5) -> void:
	_intensity = clampf(v, 0.0, 1.0)
	var wait := to_next_bar()
	for i in _beds.size():
		var t := create_tween()
		if wait > 0.0:
			t.tween_interval(wait)
		t.tween_property(_beds[i], "volume_db", _layer_db(i), seconds)


## Seconds until the bed's next bar line (0 when no bar length is known or nothing plays).
func to_next_bar() -> float:
	if music_bar <= 0.0 or _beds.is_empty() or not _beds[0].playing:
		return 0.0
	var pos := _beds[0].get_playback_position() + AudioServer.get_time_since_last_mix()
	return music_bar - fmod(pos, music_bar)


func _layer_db(i: int) -> float:
	if i == 0 or _beds.size() <= 1:
		return 0.0
	var n := float(maxi(_bed_streams.size() - 1, 1))
	var w := clampf((_intensity - float(i - 1) / n) * n, 0.0, 1.0)
	return linear_to_db(maxf(w, 0.001))


# --- ambience ---------------------------------------------------------------------

func play_ambience(s: AudioStream, fade: float = 3.0, volume_db: float = 0.0) -> void:
	if _ambience and _ambience.stream == s:
		return
	if _ambience:
		var old := _ambience
		var t := create_tween()
		t.tween_property(old, "volume_db", -60.0, fade)
		t.tween_callback(old.queue_free)
		_ambience = null
	if s == null:
		return
	_set_loop(s)
	_ambience = AudioStreamPlayer.new()
	_ambience.stream = s
	_ambience.bus = &"Ambience"
	_ambience.volume_db = -60.0
	add_child(_ambience)
	_ambience.play()
	create_tween().tween_property(_ambience, "volume_db", volume_db, fade)


# --- one-shots ----------------------------------------------------------------------

func sfx(s: AudioStream, at: Variant = null, volume_db: float = 0.0, reverb: float = 0.0, pitch: float = 1.0) -> void:
	if s == null:
		return
	_one_shot(s, at, volume_db, &"SFX", pitch)
	if reverb > 0.0:
		_one_shot(s, at, volume_db + linear_to_db(reverb), &"Reverb", pitch)


func _one_shot(s: AudioStream, at: Variant, db: float, bus: StringName, pitch: float) -> void:
	if closing:
		return
	var p: Node
	if at is Vector3 and get_tree().current_scene is Node3D:
		var p3 := AudioStreamPlayer3D.new()
		p3.stream = s
		p3.bus = bus
		p3.volume_db = db
		p3.pitch_scale = pitch
		p3.unit_size = 6.0
		p3.max_distance = 80.0
		p3.attenuation_filter_cutoff_hz = 12000.0
		get_tree().current_scene.add_child(p3)
		p3.global_position = at
		p3.play()
		p = p3
	else:
		var p2 := AudioStreamPlayer.new()
		p2.stream = s
		p2.bus = bus
		p2.volume_db = db
		p2.pitch_scale = pitch
		add_child(p2)
		p2.play()
		p = p2
	p.connect(&"finished", p.queue_free)


func ui(name: StringName, volume_db: float = 0.0) -> void:
	var s := stream("ui_" + String(name))
	if s:
		_one_shot(s, null, volume_db, &"UI", randf_range(0.97, 1.03))


func register_footsteps(surface: StringName, streams: Array[AudioStream]) -> void:
	_footsteps[String(surface)] = streams


func footstep(surface: StringName, pos: Vector3, loudness: float = 1.0) -> void:
	var set: Array = _footsteps.get(String(surface), _footsteps.get("marble", []))
	if set.is_empty():
		return
	var i := randi() % set.size()
	if set.size() > 1 and i == _last_step.get(surface, -1):
		i = (i + 1) % set.size()
	_last_step[surface] = i
	sfx(set[i], pos, linear_to_db(loudness) - 4.0, 0.55, randf_range(0.93, 1.06))


func emitter(s: AudioStream, parent: Node3D, volume_db: float = 0.0, unit_size: float = 8.0) -> AudioStreamPlayer3D:
	_set_loop(s)
	var p := AudioStreamPlayer3D.new()
	p.autoplay = false
	p.stream = s
	p.bus = &"Ambience"
	p.volume_db = volume_db
	p.unit_size = unit_size
	p.max_distance = 120.0
	parent.add_child(p)
	if not closing:
		p.play()
	return p


func _set_loop(s: AudioStream) -> void:
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true
	elif s is AudioStreamWAV:
		(s as AudioStreamWAV).loop_mode = AudioStreamWAV.LOOP_FORWARD


# --- reveal helpers -----------------------------------------------------------------

## Briefly duck the world (music + ambience + sfx) by `db`, e.g. under a pickup stinger.
func duck(db: float = -10.0, hold: float = 0.2, release: float = 0.8) -> void:
	for bus_name: StringName in [&"Music", &"Ambience", &"SFX"]:
		var idx := AudioServer.get_bus_index(bus_name)
		var base := 0.0
		var t := create_tween()
		t.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(idx, v), base, db, 0.06)
		t.tween_interval(hold)
		t.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(idx, v), db, base, release)


## Strip the music (and ambience) to near-silence for `hold` seconds, then fire `stinger` and
## bring the bed back. Use before every big reveal: `await Audio.reveal(Audio.stream("fragment"))`.
func reveal(stinger: AudioStream, hold: float = 3.5, silence_db: float = -30.0) -> void:
	var music := AudioServer.get_bus_index(&"Music")
	var amb := AudioServer.get_bus_index(&"Ambience")
	var t := create_tween().set_parallel()
	t.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(music, v), 0.0, silence_db, 1.2)
	t.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(amb, v), 0.0, silence_db * 0.5, 1.2)
	await get_tree().create_timer(hold, true, false, true).timeout
	sfx(stinger, null, 0.0, 0.7)
	var back := create_tween().set_parallel()
	back.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(music, v), silence_db, 0.0, 5.0)
	back.tween_method(func(v: float) -> void: AudioServer.set_bus_volume_db(amb, v), silence_db * 0.5, 0.0, 5.0)
