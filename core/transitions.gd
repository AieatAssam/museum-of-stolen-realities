extends CanvasLayer
## Transitions autoload: one-take medium bleed between scenes, with threaded loading behind it.
##   await Transitions.change_scene(path, palette, medium)
## The current frame is frozen, the destination medium (palette + pattern) bleeds across it while
## the next scene loads on a thread, then the medium drains away to reveal the new scene.
## Never a hard cut, never a bare loading bar.

signal scene_swapped

const BLEED_TIME := 1.7
const REVEAL_TIME := 1.9

var busy: bool = false
var _rect: ColorRect
var _mat: ShaderMaterial


func _ready() -> void:
	layer = 95
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rect = ColorRect.new()
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mat = ShaderMaterial.new()
	_mat.shader = preload("res://core/shaders/transition.gdshader")
	_rect.material = _mat
	_rect.visible = false
	add_child(_rect)


## Returns false (and stays in the current scene) if `path` fails to load. A call made while
## another transition runs waits for it rather than being dropped.
## Teardown of the outgoing scene's presentation (cinematic, placard reader, 3D fade) happens here,
## before the swap: the incoming wing's on_enter may start its own straight away.
func change_scene(path: String, palette: PackedColorArray, medium: int, on_swapped: Callable = Callable()) -> bool:
	while busy:
		await get_tree().process_frame
	busy = true
	Cinematics.abort()
	Placards.close_reader()
	var snap := _snapshot()
	var vs := get_viewport().get_visible_rect().size
	_mat.set_shader_parameter("aspect", Vector2(vs.x / vs.y, 1.0))
	_mat.set_shader_parameter("snapshot", snap)
	_mat.set_shader_parameter("medium", medium)
	for i in 3:
		_mat.set_shader_parameter("c%d" % i, palette[i] if i < palette.size() else Color.BLACK)
	_mat.set_shader_parameter("stage", 0)
	_mat.set_shader_parameter("progress", 0.0)
	_rect.visible = true
	Audio.sfx(Audio.stream("transition"), null, -3.0)
	# Engine-side: any off-main-thread load in 4.7.2 leaves 2-3 ResourceLoader LoadTokens alive at
	# exit (shown as "Leaked instance: RefCounted ... Reference count: 0"; a main-thread load() does
	# not). Kept, because a frozen frame while a big wing loads is worse. run_smoke.sh tolerates
	# exactly that signature and nothing else.
	ResourceLoader.load_threaded_request(path, "PackedScene", true)
	var t := create_tween()
	t.tween_method(func(v: float) -> void: _mat.set_shader_parameter("progress", v), 0.0, 1.0, BLEED_TIME).set_trans(Tween.TRANS_SINE)
	await t.finished
	while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		await get_tree().process_frame
	var packed := ResourceLoader.load_threaded_get(path) as PackedScene
	if packed == null:
		push_error("Transitions: failed to load %s" % path)
		_rect.visible = false
		busy = false
		return false
	get_tree().paused = false
	Post.fade_to(0.0, 0.0)  # an aborted intro may have left the view inked; the new scene starts clear
	get_tree().change_scene_to_packed(packed)
	await get_tree().scene_changed
	if on_swapped.is_valid():
		on_swapped.call()
	scene_swapped.emit()
	# let the new scene compile its pipelines behind the veil
	for i in 6:
		await get_tree().process_frame
	_mat.set_shader_parameter("stage", 1)
	var r := create_tween()
	r.tween_method(func(v: float) -> void: _mat.set_shader_parameter("progress", v), 0.0, 1.0, REVEAL_TIME).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	await r.finished
	_rect.visible = false
	busy = false
	return true


func _snapshot() -> Texture2D:
	var img: Image = null
	if DisplayServer.get_name() != "headless":
		img = get_viewport().get_texture().get_image()
	if img == null or img.is_empty():
		img = Image.create(4, 4, false, Image.FORMAT_RGB8)
		img.fill(Color(0.02, 0.018, 0.015))
	return ImageTexture.create_from_image(img)
