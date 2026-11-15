extends CanvasLayer
## Cinematics autoload. `await Cinematics.play(steps)` runs a list of steps in order:
##   {"card": "Text", "sub": "SMALL CAPS", "t": 5.0, "style": "light"|"display"|"body"}  timed text card
##   {"cam": [Transform3D, ...], "t": 8.0, "fov": 60.0, "async": true}  camera path (Catmull-Rom); async = don't wait
##   {"wait": 2.0}
##   {"fade": 1.0, "t": 1.5}            3D view to ink (1) or back (0) — via Post
##   {"call": Callable, "always": true} always = still runs when skipped (state setup)
## Hold jump/interact/pause for 1.2 s to skip. Letterbox bars slide in for the duration.
## Camera transforms can come from Marker3D nodes: `Cinematics.marks([$A, $B])`.
##
## Lifetime: a cinematic belongs to the scene that started it. Any scene change (Transitions, or
## the scene leaving the tree) calls `abort()`: remaining steps are dropped (even "always" ones),
## a `call` step that is still awaiting is abandoned, tweens are killed, the cinematic camera is
## dropped, the previous camera restored, bars and skip label cleared, and `play()` returns true.
## A second `play()` while one runs waits for it to end (and returns at once if its scene is gone).

signal finished(skipped: bool)

const SKIP_HOLD := 1.2

var playing: bool = false
var skipped: bool = false
var _aborted: bool = false
var _scene: Node
var _bar_tween: Tween
var _card_tween: Tween
var _skip_t: float = 0.0
var _bars: Array[ColorRect] = []
var _card_box: VBoxContainer
var _card_sub: Label
var _card_main: Label
var _skip_label: Label
var _cam: Camera3D
var _cam_tween: Tween
var _prev_cam: Camera3D


func _ready() -> void:
	layer = 70
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in 2:
		var b := ColorRect.new()
		b.color = Color(0.008, 0.007, 0.005)
		b.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.anchor_right = 1.0
		if i == 1:
			b.anchor_top = 1.0
			b.anchor_bottom = 1.0
		add_child(b)
		_bars.append(b)
	_set_bars(0.0)
	var c := CenterContainer.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(c)
	_card_box = VBoxContainer.new()
	_card_box.custom_minimum_size.x = 1100
	_card_box.add_theme_constant_override(&"separation", 18)
	_card_box.modulate.a = 0.0
	c.add_child(_card_box)
	_card_sub = Style.catalog("", 18, Style.GOLD, HORIZONTAL_ALIGNMENT_CENTER)
	_card_main = Style.label("", Style.LIGHT, 54, Style.IVORY, HORIZONTAL_ALIGNMENT_CENTER)
	_card_main.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_card_main.add_theme_constant_override(&"line_spacing", 6)
	for l: Label in [_card_sub, _card_main]:  # cards sit over bright scenes; a soft shadow keeps them legible
		l.add_theme_color_override(&"font_shadow_color", Color(0, 0, 0, 0.85))
		l.add_theme_constant_override(&"shadow_outline_size", 14)
		l.add_theme_constant_override(&"shadow_offset_x", 0)
		l.add_theme_constant_override(&"shadow_offset_y", 2)
	_card_box.add_child(_card_sub)
	_card_box.add_child(_card_main)
	_skip_label = Style.catalog("Hold to skip", 14, Style.GOLD_DIM, HORIZONTAL_ALIGNMENT_RIGHT)
	_skip_label.anchor_left = 1.0
	_skip_label.anchor_right = 1.0
	_skip_label.anchor_top = 1.0
	_skip_label.anchor_bottom = 1.0
	_skip_label.offset_left = -360
	_skip_label.offset_right = -48
	_skip_label.offset_top = -64
	_skip_label.offset_bottom = -40
	_skip_label.modulate.a = 0.0
	add_child(_skip_label)


func _set_bars(frac: float) -> void:
	var h := frac * 1080.0
	_bars[0].offset_bottom = h
	_bars[1].offset_top = -h


## Slide the bars in/out. One tween at a time: a fast on->off must not let the "on" finish last.
func letterbox(on: bool, seconds: float = 1.2) -> void:
	if _bar_tween:
		_bar_tween.kill()
	_bar_tween = null
	if seconds <= 0.0:
		_set_bars(0.11 if on else 0.0)
		return
	_bar_tween = create_tween()
	_bar_tween.tween_method(_set_bars, _bars[0].offset_bottom / 1080.0, 0.11 if on else 0.0, seconds).set_trans(Tween.TRANS_SINE)


## True while any letterbox bar or the skip label is visible (tests assert this clears).
func overlay_visible() -> bool:
	return _bars[0].offset_bottom > 0.5 or _skip_label.modulate.a > 0.01 or _card_box.modulate.a > 0.01


static func marks(nodes: Array) -> Array[Transform3D]:
	var out: Array[Transform3D] = []
	for n: Node3D in nodes:
		out.append(n.global_transform)
	return out


func play(steps: Array) -> bool:
	var scene := get_tree().current_scene
	while playing:
		await finished
	if get_tree().current_scene != scene or not is_instance_valid(scene):
		return true  # queued behind a cinematic whose scene was torn down; ours is gone too
	playing = true
	skipped = false
	_aborted = false
	_skip_t = 0.0
	_scene = scene
	if _scene and not _scene.tree_exiting.is_connected(abort):
		_scene.tree_exiting.connect(abort, CONNECT_ONE_SHOT)
	_prev_cam = get_viewport().get_camera_3d()
	letterbox(true)
	if Game.player:
		Game.player.input_enabled = false
		Game.player.look_enabled = false
	for s: Dictionary in steps:
		if _aborted:
			break
		if skipped and not s.get("always", false):
			continue
		if s.has("card"):
			await _card(s)
		elif s.has("cam"):
			_camera(s)
			if not s.get("async", false):
				await _wait(float(s["t"]))
		elif s.has("wait"):
			await _wait(float(s["wait"]))
		elif s.has("fade"):
			if skipped:
				Post.fade_to(float(s["fade"]), 0.0)
			else:
				await Post.fade_to(float(s["fade"]), float(s.get("t", 1.0)))
		elif s.has("call"):
			var c: Callable = s["call"]
			if c.is_valid():
				await _call(c)
			else:
				push_warning("Cinematics: skipped call step on a freed object (%s)" % c.get_method())
	_end()
	return skipped


## Stop now: the scene is changing. Safe to call any time; no-op when nothing plays.
func abort() -> void:
	if not playing or _aborted:
		return
	_aborted = true
	skipped = true
	_kill_cam()


## Run a step's callable, but stop waiting for it if we abort (its object may be freed mid-await,
## which would otherwise leave play() suspended forever with the bars down).
func _call(c: Callable) -> void:
	var st := {"done": false}
	_call_into(c, st)
	while not st["done"] and not _aborted:
		await get_tree().process_frame


func _call_into(c: Callable, st: Dictionary) -> void:
	await c.call()
	st["done"] = true


func _kill_cam() -> void:
	if _cam_tween:
		_cam_tween.kill()
	_cam_tween = null
	if is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null


func _end() -> void:
	_kill_cam()
	var p := Game.player
	if not _aborted and is_instance_valid(p) and p.is_inside_tree():
		p.camera.make_current()
		p.input_enabled = true
		p.look_enabled = true
	elif is_instance_valid(_prev_cam) and _prev_cam.is_inside_tree() and not _prev_cam.is_queued_for_deletion():
		_prev_cam.make_current()
	_prev_cam = null
	if is_instance_valid(_scene) and _scene.tree_exiting.is_connected(abort):
		_scene.tree_exiting.disconnect(abort)
	_scene = null
	if _card_tween:
		_card_tween.kill()
	_card_box.modulate.a = 0.0
	_skip_label.modulate.a = 0.0
	_skip_t = 0.0
	letterbox(false, 0.0 if _aborted else 1.2)
	playing = false
	finished.emit(skipped)


func _wait(t: float) -> void:
	var end := Time.get_ticks_msec() + int(t * 1000.0)
	while Time.get_ticks_msec() < end and not skipped:
		await get_tree().process_frame


func _card(s: Dictionary) -> void:
	_card_sub.text = String(s.get("sub", "")).to_upper()
	_card_sub.visible = _card_sub.text != ""
	_card_main.text = s["card"]
	match String(s.get("style", "light")):
		"display":
			_card_main.add_theme_font_override(&"font", Style.DISPLAY)
			_card_main.add_theme_font_size_override(&"font_size", 64)
		"body":
			_card_main.add_theme_font_override(&"font", Style.ITALIC)
			_card_main.add_theme_font_size_override(&"font_size", 40)
		_:
			_card_main.add_theme_font_override(&"font", Style.LIGHT)
			_card_main.add_theme_font_size_override(&"font_size", 54)
	var t := float(s.get("t", 5.0))
	if _card_tween:
		_card_tween.kill()
	_card_tween = create_tween()
	_card_tween.tween_property(_card_box, "modulate:a", 1.0, minf(1.4, t * 0.3))
	await _wait(t - 1.2)
	_card_tween.kill()
	_card_tween = create_tween()
	_card_tween.tween_property(_card_box, "modulate:a", 0.0, 0.25 if skipped else 1.2)
	await _wait(1.2)


func _camera(s: Dictionary) -> void:
	var path: Array = s["cam"]
	if path.is_empty() or _scene == null or _aborted:
		return
	if _cam == null:
		_cam = Camera3D.new()
		_cam.name = "CinematicCamera"
		_cam.far = 800.0
		_scene.add_child(_cam)  # freed with the scene; abort() drops our ref before that happens
	_cam.fov = float(s.get("fov", 60.0))
	_cam.make_current()
	_cam.global_transform = path[0]
	if _cam_tween:
		_cam_tween.kill()
	var cam := _cam
	_cam_tween = create_tween()
	_cam_tween.tween_method(func(u: float) -> void: cam.global_transform = _sample(path, u),
		0.0, 1.0, float(s["t"])).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


static func _sample(path: Array, u: float) -> Transform3D:
	var n := path.size()
	if n == 1:
		return path[0]
	var f := u * float(n - 1)
	var i := mini(int(f), n - 2)
	var t := f - float(i)
	var p0: Vector3 = (path[maxi(i - 1, 0)] as Transform3D).origin
	var p1: Vector3 = (path[i] as Transform3D).origin
	var p2: Vector3 = (path[i + 1] as Transform3D).origin
	var p3: Vector3 = (path[mini(i + 2, n - 1)] as Transform3D).origin
	var pos := p1.cubic_interpolate(p2, p0, p3, t)
	var q := (path[i] as Transform3D).basis.get_rotation_quaternion().slerp((path[i + 1] as Transform3D).basis.get_rotation_quaternion(), t)
	return Transform3D(Basis(q), pos)


func _process(delta: float) -> void:
	if not playing:
		return
	var held := Input.is_action_pressed(&"jump") or Input.is_action_pressed(&"interact") or Input.is_action_pressed(&"pause")
	_skip_t = _skip_t + delta if held else maxf(_skip_t - delta * 2.0, 0.0)
	_skip_label.modulate.a = lerpf(_skip_label.modulate.a, 1.0 if held or _skip_t > 0.0 else 0.35, 1.0 - exp(-6.0 * delta))
	_skip_label.text = "HOLD TO SKIP  " + "·".repeat(int(_skip_t / SKIP_HOLD * 8.0))
	if _skip_t >= SKIP_HOLD and not skipped:
		skip()


func skip() -> void:
	if not playing:
		return
	skipped = true
	if _cam_tween:
		_cam_tween.custom_step(9999.0)
