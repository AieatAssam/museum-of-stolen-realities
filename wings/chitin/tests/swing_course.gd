extends Node3D
## Swing gate: a three-anchor chain over an abyss, flown TRIALS times by real primary taps with
## varied release timing (physics ticks from the forward apex), mid-air fire delay and aim jitter.
## Passes when at least 9 in 10 chains land on the far ledge without touching ground between.
## Run:  Godot --headless --path . wings/chitin/tests/swing_course.tscn
## Geometry comes from COURSE, which the wing's hive-shaft chain copies (chitin.gd, SHAFT_CHAIN).

const SilkMode := preload("res://wings/chitin/silk_mode.gd")
var TRIALS := int(OS.get_environment("SWING_TRIALS")) if OS.has_environment("SWING_TRIALS") else 40
## anchor positions and ledges, x forward. Sized from SilkMode.envelope() (printed at start).
const COURSE := {
	"start": [Vector3(-8, -1, -4), Vector3(0, 0, 4)],      # AABB min/max of the start ledge
	"anchors": [Vector3(6, 10, 0), Vector3(19, 10, 0), Vector3(32, 10, 0)],
	"land": [Vector3(35, -4, -8), Vector3(50, -3, 8)],
}
# Each of the three releases independently draws: an offset in ticks from the forward apex
# (RELEASE, uniform; -48 ticks = 0.4 s early, outside the top-release window), a fire delay after
# the release (DELAY ticks) and aim jitter (JITTER degrees). Start position also varies.
var RELEASE := Vector2i(-48, 36) if not OS.has_environment("SWING_WIDE") else Vector2i(-90, 60)
const DELAY := Vector2i(4, 40)
const JITTER := 10.0
var SEED := int(OS.get_environment("SWING_SEED")) if OS.has_environment("SWING_SEED") else 340

var rng := RandomNumberGenerator.new()

var player: Player
var silk: MovementMode
var _anchors: Array[Node3D] = []


func _ready() -> void:
	_build()
	player = Player.new()
	add_child(player)
	player.gravity_vector = Vector3(0, -15, 0)
	silk = SilkMode.new()
	player.add_mode(&"silk", silk)
	player.set_mode(&"silk")
	_run.call_deferred()


func _build() -> void:
	var ledge_mat := StandardMaterial3D.new()
	ledge_mat.albedo_color = Color("6b7f8a")
	for k: String in ["start", "land"]:
		var bb: Array = COURSE[k]
		var size: Vector3 = bb[1] - bb[0]
		var body := StaticBody3D.new()
		body.position = (bb[0] + bb[1]) * 0.5
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = size
		cs.shape = bs
		body.add_child(cs)
		add_child(body)
	for p: Vector3 in COURSE["anchors"]:
		var a := Node3D.new()
		a.position = p
		a.add_to_group(&"silk_anchors")
		add_child(a)
		_anchors.append(a)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _tap(action: StringName) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = action
	up.pressed = false
	Input.parse_input_event.call_deferred(up)


func _aim(p: Vector3, jitter_deg: float) -> void:
	player.look_at_point(p)
	player.yaw += deg_to_rad(jitter_deg)
	player.pitch += deg_to_rad(jitter_deg * 0.5)


## Ticks until the forward apex of the current swing, by integrating the pendulum from her state.
## Returns -1 while not on an upswing.
func _ticks_to_apex() -> int:
	if silk.state != SilkMode.ROPE:
		return -1
	var up := Vector3.UP
	var c: Vector3 = silk.pivot()
	var r: Vector3 = silk.grip() - c
	var L := r.length()
	var rn := r / L
	var phi := acos(clampf(-rn.dot(up), -1.0, 1.0))
	var t_up := up - rn * rn.dot(up)
	if t_up.length() < 0.01:
		return -1
	var w := player.velocity.dot(t_up.normalized()) / L
	if w <= 0.0 or phi < deg_to_rad(15.0) or r.x < 0.0:
		return -1
	var g := 15.0
	var dt := 1.0 / Engine.physics_ticks_per_second
	var n := 0
	while w > 0.0 and n < 600:
		w -= g / L * sin(phi) * dt
		phi += w * dt
		n += 1
	return n


func _run() -> void:
	rng.seed = SEED
	await frames(5)
	print("[swing] model: release envelope per rope length (landing x from the pivot at grip height -9)")
	for L: float in [8.0, 10.0, 12.0]:
		for apex: float in [SilkMode.BAND_MIN_DEG, SilkMode.BAND_MAX_DEG]:
			var env := SilkMode.envelope(L, apex, 15.0, -9.0, PackedInt32Array([-30, -24, -12, 0, 12, 24]))
			var xs := env.map(func(e: Dictionary) -> String: return "%+d:%.1f%s" % [e["ticks"], e["land_x"], "*" if e["top"] else ""])
			print("  L %4.1f apex %2d deg  %s" % [L, apex, " ".join(xs)])
	var landed := 0
	var lines: Array[String] = []
	for i: int in TRIALS:
		var res: Dictionary = await _trial(i)
		if res["ok"]:
			landed += 1
		lines.append("  trial %2d  release %s  delay %s  jitter %s  -> %s  (air chain %d, top releases %d, mantles %d, land x %.1f y %.1f z %.1f state %d, %.2f s)" % [
			i, res["offset"], res["delay"], res["jitter"], "LANDED" if res["ok"] else "FELL", res["chain"], res["tops"], res["mantles"], res["x"], res["y"], res["z"], res["state"], res["secs"]])
	for l: String in lines:
		print(l)
	var rate := float(landed) / TRIALS
	print("[swing] chained three-swing landings: %d / %d (%.0f%%)" % [landed, TRIALS, rate * 100.0])
	Game.quit(0 if rate >= 0.9 else 1)


func _trial(_i: int) -> Dictionary:
	var offsets: Array[int] = []
	var delays: Array[int] = []
	var jitters: Array[float] = []
	for k: int in 3:
		offsets.append(rng.randi_range(RELEASE.x, RELEASE.y))
		delays.append(rng.randi_range(DELAY.x, DELAY.y))
		jitters.append(rng.randf_range(-JITTER, JITTER))
	var start := Vector3(rng.randf_range(-2.5, -0.4), 0.0, rng.randf_range(-1.0, 1.0))
	player.teleport(Transform3D(Basis.IDENTITY, start))
	silk.call("reset")
	await frames(6)
	var t0 := Engine.get_physics_frames()
	var tops0: int = silk.top_releases
	var mantles0: int = silk.mantles
	var chain := 0
	for k: int in _anchors.size():
		var offset := offsets[k]
		var delay := delays[k]
		_aim(_anchors[k].global_position, jitters[k])
		await frames(1)
		_tap(&"primary")
		await frames(2)
		if silk.state != SilkMode.ROPE:
			await frames(2)
		if silk.state != SilkMode.ROPE:
			break
		chain = maxi(chain, silk.air_chain)
		# wait for the release moment: `offset` ticks from the forward apex
		var guard := 0
		var seen_up := false
		while guard < 600 and silk.state == SilkMode.ROPE:
			guard += 1
			var n := _ticks_to_apex()
			if n >= 0:
				seen_up = true
			if offset < 0 and n >= 0 and n <= -offset:
				break
			if offset >= 0 and seen_up and n <= 1:
				await frames(offset)
				break
			await frames(1)
		if silk.state == SilkMode.ROPE:
			_tap(&"primary")
			await frames(1)
		if OS.has_environment("SWING_DEBUG"):
			print("    swing %d released at %s v %s state %d" % [k, player.global_position, player.velocity, silk.state])
		if k < _anchors.size() - 1:
			await frames(delay)
	var guard2 := 0
	while guard2 < 600 and silk.state != SilkMode.GROUND and player.global_position.y > -25.0:
		guard2 += 1
		if OS.has_environment("SWING_DEBUG") and guard2 % 6 == 0:
			print("      t%d pos %s v %s state %d" % [guard2, player.global_position, player.velocity, silk.state])
		await frames(1)
	var pos := player.global_position
	var bb: Array = COURSE["land"]
	var ok: bool = silk.state == SilkMode.GROUND and pos.y > (bb[1] as Vector3).y - 0.5 and pos.x >= (bb[0] as Vector3).x - 0.5 and pos.x <= (bb[1] as Vector3).x
	return {"ok": ok, "offset": offsets, "delay": delays, "jitter": jitters.map(func(j: float) -> String: return "%+.0f" % j), "chain": chain,
		"tops": silk.top_releases - tops0, "mantles": silk.mantles - mantles0, "x": pos.x, "y": pos.y, "z": pos.z, "state": silk.state,
		"secs": float(Engine.get_physics_frames() - t0) / Engine.physics_ticks_per_second}


