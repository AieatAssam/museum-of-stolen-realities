class_name GrappleMode
extends ConstrainedMode
## Pendulum swing from an anchor point (chitin SILKSPINNING). Set `anchor` (world position) before
## switching in. Forward/back reel in/out, strafe pumps the swing, jump or secondary releases.

var anchor: Vector3
var rope_length: float = 8.0
var reel_speed: float = 4.0
var pump: float = 6.0
var min_length: float = 1.5


func _init() -> void:
	release_verbs = [&"jump", &"secondary"]


func attach() -> bool:
	rope_length = maxf(player.global_position.distance_to(anchor), min_length)
	return true


func step(delta: float) -> void:
	var p := player
	var mi := p.move_input()
	rope_length = maxf(rope_length + mi.y * reel_speed * delta, min_length)
	p.velocity += p.gravity_vector * delta
	p.velocity += p.wish_dir() * Vector3(1, 0, 1) * pump * absf(mi.x) * delta
	var to_p := p.global_position - anchor
	var d := to_p.length()
	if d > rope_length:  # rope taut: remove outward velocity, pull back onto the sphere
		var n := to_p / d
		var outward := p.velocity.dot(n)
		if outward > 0.0:
			p.velocity -= n * outward
		p.global_position = anchor + n * rope_length
	p.move_and_slide()
