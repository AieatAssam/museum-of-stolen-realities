extends CanvasLayer
## Post autoload: one full-screen grade/grain/aberration/vignette pass under the UI (layer 50).
## Wings don't call this directly — set `Wing.grade` and Wing applies it.

var _rect: ColorRect
var _mat: ShaderMaterial
var _tween: Tween
var _fade_tween: Tween


func _ready() -> void:
	layer = 50
	process_mode = Node.PROCESS_MODE_ALWAYS
	_rect = ColorRect.new()
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_mat = ShaderMaterial.new()
	_mat.shader = preload("res://core/post/post.gdshader")
	_rect.material = _mat
	add_child(_rect)
	_mat.set_shader_parameter("fade", 0.0)
	apply(PostGrade.new(), 0.0)


func apply(g: PostGrade, seconds: float = 1.5) -> void:
	if _tween:
		_tween.kill()
	var target := {
		"tint": g.tint, "saturation": g.saturation, "contrast": g.contrast, "lift": g.lift,
		"grain": g.grain, "aberration": g.aberration, "vignette": g.vignette,
	}
	_mat.set_shader_parameter("grain_fps", g.grain_fps)
	if seconds <= 0.0:
		for k: String in target:
			_mat.set_shader_parameter(k, target[k])
		return
	_tween = create_tween().set_parallel().set_trans(Tween.TRANS_SINE)
	for k: String in target:
		_tween.tween_method(func(v: Variant) -> void: _mat.set_shader_parameter(k, v),
			_mat.get_shader_parameter(k), target[k], seconds)


## Fade the 3D view to ink (1) or back (0). UI above layer 50 stays visible.
## A newer fade (or a scene change, which resets to 0) cancels a running one; its await returns.
func fade_to(amount: float, seconds: float) -> void:
	if _fade_tween:
		_fade_tween.kill()
	_fade_tween = null
	if seconds <= 0.0:
		_mat.set_shader_parameter("fade", amount)
		return
	var t := create_tween()
	_fade_tween = t
	t.tween_method(func(v: float) -> void: _mat.set_shader_parameter("fade", v),
		float(_mat.get_shader_parameter("fade")), amount, seconds)
	while t.is_valid() and t.is_running():  # not `await t.finished`: a killed tween never emits it
		await get_tree().process_frame
