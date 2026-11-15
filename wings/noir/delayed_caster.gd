class_name DelayedCaster
extends AnimatableBody3D
## A shadow caster on layer 7 (1 << 6) that ping-pongs between `a` and `b`, one leg per `period`
## seconds. The physics body is sampled `lead` seconds ahead of the visible `ghost`, so its shadow
## arrives before the thing that casts it. That is the eleven-second rule: the shade is always the
## future. The player's mask excludes layer 7, so the body never blocks them.

@export var a: Vector3 = Vector3(0, 0.9, 0)
@export var b: Vector3 = Vector3(0, 0.9, -8)
@export var period: float = 12.0
@export var lead: float = 0.0
@export var box_size: Vector3 = Vector3(0.6, 1.8, 0.6)
## Visible body that trails the shadow. Positioned at pos_at(t) + ghost_offset.
@export var ghost: Node3D
@export var ghost_offset: Vector3 = Vector3.ZERO

var _t: float = 0.0


func _init() -> void:
	collision_layer = 1 << 6
	collision_mask = 0


func _ready() -> void:
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = box_size
	cs.shape = bs
	add_child(cs)
	# shadow-only mesh: the caster throws shade but is never drawn, so the shade arrives first
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = box_size
	mi.mesh = bm
	mi.cast_shadow = 3  # GeometryInstance3D.ShadowCastingSetting SHADOW_ONLY
	add_child(mi)
	_apply(0.0)


func _physics_process(delta: float) -> void:
	_t += delta * Game.world_time_scale
	_apply(_t)


func pos_at(t: float) -> Vector3:
	var u := fposmod(t / period, 2.0)
	if u > 1.0:
		u = 2.0 - u
	return a.lerp(b, u)


func _apply(t: float) -> void:
	position = pos_at(t + lead)
	if ghost:
		ghost.position = pos_at(t) + ghost_offset
