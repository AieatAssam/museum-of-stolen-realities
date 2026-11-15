extends Node3D
## A heliostat sun-dial: catches the standing sun and throws it as a beam toward one of a few
## fixed aims. [interact] turns it to the next aim (the beam sweeps there). A clockwork dial, once
## wound, turns itself through `cycle` ([aim index, seconds], ...) forever — light on a timetable.

signal turned(index: int)

var id: String = ""
var aims: Array = []          # world target points
var index: int = 0
var cycle: Array = []         # clockwork: [[index, seconds], ...]
var wound: bool = false
var jammed: bool = false
var source: GlassOptics.Source
var interact: Interactable
var head: Node3D
var lens_light: OmniLight3D
var _tw: Tween
var _cycle_i: int = 0
var _cycle_t: float = 0.0


func setup(optics: GlassOptics, mask: int, model: Node3D, prompt: String) -> void:
	head = Node3D.new()
	head.name = "Head"
	head.position.y = 0.28
	add_child(head)
	if model:
		add_child(model)
	source = GlassOptics.Source.new()
	source.mask = mask
	head.add_child(source)
	optics.add_source(source)
	source.dir = global_position.direction_to(aims[index]) if is_inside_tree() else Vector3.FORWARD
	lens_light = OmniLight3D.new()
	lens_light.light_color = GlassOptics.color(mask)
	lens_light.light_energy = 1.2
	lens_light.omni_range = 3.0
	lens_light.position.y = 0.5
	add_child(lens_light)
	interact = Interactable.make_box(Vector3(1.6, 1.8, 1.6), prompt)
	interact.position.y = 0.9
	interact.interacted.connect(func(_p: Player) -> void: _use())
	add_child(interact)


func _ready() -> void:
	_aim(aims[index], true)


func aim_point() -> Vector3:
	return aims[index]


func _use() -> void:
	if jammed:
		Audio.sfx(load("res://wings/glass/audio/gate_close.ogg"), global_position, -6.0)
		return
	if not cycle.is_empty():
		if not wound:
			wound = true
			_cycle_i = 0
			_cycle_t = 0.0
			set_index(int(cycle[0][0]))
		return
	set_index((index + 1) % aims.size())


func set_index(i: int, instant: bool = false) -> void:
	index = i
	_aim(aims[i], instant)
	if not instant:
		Audio.sfx(load("res://wings/glass/audio/dial_turn.ogg"), global_position, -2.0, 0.4, randf_range(0.96, 1.04))
		var t := create_tween()
		t.tween_property(lens_light, "light_energy", 5.0, 0.08)
		t.tween_property(lens_light, "light_energy", 1.2, 0.6)
	turned.emit(i)


func _aim(target: Vector3, instant: bool) -> void:
	var to := source.global_position.direction_to(target) if is_inside_tree() else Vector3.FORWARD
	if _tw:
		_tw.kill()
	if instant or not is_inside_tree():
		_set_dir(to)
		return
	var from := source.dir
	_tw = create_tween()
	_tw.tween_method(func(u: float) -> void: _set_dir(from.slerp(to, u).normalized()), 0.0, 1.0, 0.75) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)


func _set_dir(d: Vector3) -> void:
	source.dir = d
	var up := Vector3.UP if absf(d.y) < 0.97 else Vector3.FORWARD
	head.global_basis = Basis.looking_at(d, up)


func _process(delta: float) -> void:
	if cycle.is_empty() or not wound or jammed:
		return
	_cycle_t += delta * Game.world_time_scale
	if _cycle_t >= float(cycle[_cycle_i][1]):
		_cycle_t = 0.0
		_cycle_i = (_cycle_i + 1) % cycle.size()
		set_index(int(cycle[_cycle_i][0]))


## Seconds until the clockwork next turns (tests and the HUD-less player read the dial by eye).
func time_left() -> float:
	if cycle.is_empty() or not wound:
		return INF
	return float(cycle[_cycle_i][1]) - _cycle_t
