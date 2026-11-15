extends Wing
## The Pinched Forest (Acquisition No. 088). Stop-motion world on twos at 12 fps; Vesper is smooth.
## Rule: Reshaping. Hold primary to pull clay up (or scoop it out of the pit), secondary to press
## it down. Clay comes from a pouch of limited size: pulling spends it, pressing and scooping refill it.
## Edits and creatures only move on the world beat, never on render frames.

const WORLD_FPS := 12.0
const STEP := 1.0 / WORLD_FPS
const PULL_RATE := 0.9        # m of height per second at the brush centre
const BRUSH_R := 1.25
const POUCH_START := 4.0
const POUCH_MAX := 9.0
const TOOL_POUCH_BONUS := 3.0
const PRESS_FLOOR := 0.0      # pressing never takes clay below the meadow
const DIG_CENTRE := Vector3(-16.0, 0.0, 22.0)
const DIG_R := 3.4
const DIG_FLOOR := -2.2
const MOUND := Vector3(6.0, 0.0, 22.0)
const MOUND_DONE := 0.3
const KNOLL := Vector3(-9.0, 0.0, 13.0)
const HILL := Vector3(12.0, 0.0, -20.0)
const TABLE := Vector3(0.0, 0.0, -41.0)
const TABLE_TOP := 2.6
const REACH := 9.0
const GATE_TIME := 1.6
const PLUG_TIME := 2.4
const FENCE_Z := -29.0
const FENCE_MODULES := 20
const FENCE_W := 4.0
const RAMP_Z := -34.5
const MODEL_DIR := "res://wings/clay/models/"
const AUDIO_DIR := "res://wings/clay/audio/"

signal beat(dt: float)

var world_fps: float = WORLD_FPS
var pouch: float = POUCH_START
var terrain: ClayTerrain
var _beat_acc: float = 0.0
var _tick: int = 0
var _saved: Dictionary = {}
var _aim_kind: StringName = &""
var _aim: Vector3 = Vector3.INF
var _scooped: bool = false
var _pulled: bool = false
var _tool: bool = false
var _choice: StringName = &""
var _choice_shown: bool = false
var _plug: StaticBody3D
var _plug_press: float = 0.0
var _gate_press: float = 0.0
var _gate_down: bool = false
var _fence: Array[Node3D] = []
var _boulder: ClayBoulder
var _chaser: ClayChaser
var _fragment: Pickup
var _reveal_started: bool = false
var _reveal_done: bool = false
var _bench_nag: float = -10.0
var _villagers: MultiMeshInstance3D
var _crumbs: GPUParticles3D
var _chase_started: bool = false


func objectives() -> Array[Dictionary]:
	return [
		{"id": "raise", "title": "Pull the first step out of the moss",
			"steps": [{"id": "pull_step", "title": "Pull a step up from the moss"},
				{"id": "ledge", "title": "Climb onto the ledge"},
				{"id": "mound", "title": "Press the mound flat"}]},
		{"id": "cross", "title": "Cross the cling-film river",
			"steps": [{"id": "carry", "title": "Fill the pouch from the pit"},
				{"id": "boulder", "title": "Roll the boulder into the gap and flatten it"},
				{"id": "doorway", "title": "Thumb open the hill"}]},
		{"id": "way_up", "title": "Build a way up to the workbench",
			"steps": [{"id": "gate", "title": "Lower the wire gate"},
				{"id": "ramp", "title": "Pull a ramp to the workbench foot"}]},
		{"id": "lookout", "title": "Look over the armature village", "optional": true,
			"steps": [{"id": "view", "title": "Stand on the hill and look down"}]},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "thumb", "name": "A thumbprint, larger than a hand", "line": "Found in the moss on the morning the forest was lifted. The print is still warm to the touch."},
		{"id": "horse", "name": "A wire horse, one leg bent back", "line": "The armature was never covered. The horse was meant to be carried in someone's pocket."},
		{"id": "film", "name": "A scrap of cling film, fingerprinted", "line": "It covered the river, then the river's cover. The Curator has not decided which of them is the exhibit."},
	]


func fragment() -> Dictionary:
	return {"name": "A pinch of the Pinched Forest",
		"line": "A fragment of Exhibit 0. The clay still holds the shape of a thumb. The thumb is not in the catalogue."}


func save_state() -> Dictionary:
	var out := {
		"pouch": pouch,
		"choice": String(_choice),
		"tool": _tool,
		"gate_down": _gate_down,
		"plug_open": _plug == null,
		"scooped": _scooped,
		"pulled": _pulled,
		"reveal_done": _reveal_done,
		"boulder": [_boulder.global_position.x, _boulder.global_position.y, _boulder.global_position.z],
		"boulder_flat": _boulder.flat,
	}
	if terrain:
		var hs: Array = []
		var ms: Array = []
		hs.resize(terrain.h.size())
		ms.resize(terrain.mark.size())
		for i in terrain.h.size():
			hs[i] = snappedf(terrain.h[i], 0.01)
			ms[i] = snappedf(terrain.mark[i], 0.01)
		out["heights"] = hs
		out["marks"] = ms
	return out


func load_state(state: Dictionary) -> void:
	_saved = state
	if terrain:
		_apply_saved()


func _ready() -> void:
	beat.connect(_on_beat)
	terrain = ClayTerrain.new()
	terrain.name = "Ground"
	add_child(terrain)
	terrain.setup(Callable(self, "base_height"))
	terrain.collider().set_meta("surface", "clay")
	var steps: Array[AudioStream] = []
	for i in [1, 2, 3]:
		steps.append(_stream("step_clay_%d" % i))
	Audio.register_footsteps(&"clay", steps)
	_build_checkpoints()
	_build_meadow()
	_build_river()
	_build_hill()
	_build_village()
	_build_table()
	_build_fence()
	_build_burrow()
	_build_start_note()
	_crumbs = _make_crumbs()
	add_child(_crumbs)
	if _saved.is_empty():
		terrain.flush()
	else:
		_apply_saved()


func on_enter(first_time: bool) -> void:
	if first_time:
		await Cinematics.play([
			{"card": "Handmade.", "sub": "The Pinched Forest\nAcquisition No. 088", "t": 3.0, "style": "display"},
		])
	toast("You are in the Pinched Forest. The clay is still soft, and so is everything else.")


func _process(delta: float) -> void:
	# World ticker: nothing in the wing advances on render frames, only on beats.
	if world_fps <= 0.0:
		_beat_acc = 0.0
		return
	_beat_acc += delta
	var step := 1.0 / world_fps
	while _beat_acc >= step:
		_beat_acc -= step
		_tick += 1
		beat.emit(step)


func _physics_process(_delta: float) -> void:
	_aim_kind = &""
	var p := Game.player
	if p == null or p.camera == null or not p.is_inside_tree():
		return
	var cam := p.camera
	var from := cam.global_position
	var to := from - cam.global_basis.z * REACH
	var q := PhysicsRayQueryParameters3D.create(from, to, 1 | (1 << 4))
	q.exclude = [p.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return
	_aim = hit["position"]
	var col: Object = hit["collider"]
	if col == terrain.collider():
		_aim_kind = &"terrain"
	elif col == _boulder:
		_aim_kind = &"boulder"
	elif col is StaticBody3D and col.has_meta("clay_press"):
		_aim_kind = StringName(col.get_meta("clay_press"))


# --- the ground as a function of place (the undeformed clay) ---------------------------------

func base_height(x: float, z: float) -> float:
	var h := 0.10 * sin(x * 0.13) * cos(z * 0.11)
	h += _plateau(x, z, KNOLL.x, KNOLL.z, 5.0, 3.0, 1.2, 0.6)
	h += _plateau(x, z, TABLE.x, TABLE.z, 6.0, 5.0, TABLE_TOP, 0.5)
	h += _hump(x, z, MOUND.x, MOUND.z, 2.6, 1.6)
	h += _hump(x, z, HILL.x, HILL.z, 8.0, 3.2)
	h += _hump(x, z, DIG_CENTRE.x, DIG_CENTRE.z, DIG_R, -0.9)
	# The trench the boulder falls into: a dip with a bank that slopes down towards it.
	var dz := absf(z + 4.5)
	h -= 1.6 * (1.0 - smoothstep(1.5, 2.2, dz))
	h += 0.28 * clampf(z + 2.2, 0.0, 5.2) * (1.0 - smoothstep(-2.2, 5.0, absf(x) - 6.0))
	return h


func _plateau(x: float, z: float, cx: float, cz: float, hx: float, hz: float, height: float, soft: float) -> float:
	var d := maxf(absf(x - cx) - hx, absf(z - cz) - hz)
	return height * (1.0 - smoothstep(0.0, soft, d))


func _hump(x: float, z: float, cx: float, cz: float, r: float, height: float) -> float:
	var d := Vector2(x - cx, z - cz).length() / r
	return height * maxf(0.0, 1.0 - d) * maxf(0.0, 1.0 - d)


# --- building the wing -----------------------------------------------------------------------

func _model(file: String) -> Node3D:
	var ps := load(MODEL_DIR + file) as PackedScene
	var n := ps.instantiate() as Node3D
	MaterialLib.apply(n, ["res://wings/clay/materials", MaterialLib.CORE_DIR])
	return n


func _stream(file: String) -> AudioStream:
	return load(AUDIO_DIR + file + ".ogg") as AudioStream


func _ground_at(p: Vector3) -> Vector3:
	return Vector3(p.x, terrain.height_at(p.x, p.z), p.z)


func _placard(node_name: String, at: Vector3, yaw: float, heading: String, title: String, catalog: String, body: String) -> void:
	var pl := Placard.new()
	pl.name = node_name
	add_child(pl)
	pl.position = _ground_at(at) + Vector3(0, 1.1, 0)
	pl.rotation.y = yaw
	pl.set_label(Placard.fields_from_legacy(title, catalog, body), false)


func _build_checkpoints() -> void:
	var holder := get_node_or_null("Checkpoints")
	if holder == null:
		return
	var start := holder.get_node_or_null("start") as Node3D
	if start:
		start.global_position = _ground_at(Vector3(0, 0, 34))
	var list := {"river": Vector3(0, 0, 1.0), "village": Vector3(-4, 0, -19.0), "ramp": Vector3(0, 0, -31.5)}
	for id in list:
		var c := Checkpoint.new()
		c.id = StringName(id)
		c.radius = 2.5
		holder.add_child(c)
		c.global_position = _ground_at(list[id]) + Vector3(0, 0.05, 0)


func _build_meadow() -> void:
	_provenance(&"thumb", _model("thumb.glb"), Vector3(14, 0, 27))
	# Ledge: stand on the knoll's plateau to finish the climb step.
	var ledge := TriggerZone.make_box(Vector3(7.0, 2.6, 7.0))
	ledge.position = _ground_at(KNOLL) + Vector3(0, 1.3, 0)
	ledge.triggered.connect(func(_p: Player) -> void: complete_step(&"raise", &"ledge"))
	add_child(ledge)
	# Pit: aim at it and hold primary to scoop clay back into the pouch.
	_placard("PitNote", Vector3(-12, 0, 27), PI, "I", "The Pit", "Acquisition No. 088\nSource material",
		"The clay was dug from here, and it was dug again. It is the only part of the forest that is still empty.")


func _build_start_note() -> void:
	_placard("StartNote", Vector3(-4, 0, 30), 0.0, "0", "The Pinched Forest", "Acquisition No. 088\nHandmade",
		"Everything here was made by hand and then made again. The ground is the first exhibit. Please do not sit on it, though it will not object.")


func _build_river() -> void:
	# A boulder on the bank. The bank slopes down into the trench, so it rolls in by itself.
	_boulder = ClayBoulder.new()
	_boulder.name = "Boulder"
	_boulder.setup(_model("boulder.glb"))
	add_child(_boulder)
	_boulder.position = _ground_at(Vector3(0.0, 0.0, 3.0)) + Vector3(0, 1.6, 0)
	_boulder.flattened.connect(func() -> void: complete_step(&"cross", &"boulder"))
	# Cling-film river: a sheet laid over the trench.
	var sheet := _model("river.glb")
	sheet.position = Vector3(0, -0.2, -4.5)
	add_child(sheet)
	_placard("RiverNote", Vector3(-4, 0, 1.4), 0.0, "II", "The River", "Acquisition No. 088\nCling film",
		"The river is cling film over a trench. The Curator has not decided whether it is water. A stone is the recommended crossing, and the clay does the rest.")


func _build_hill() -> void:
	var top := TriggerZone.make_box(Vector3(5.0, 2.0, 5.0))
	top.position = _ground_at(HILL) + Vector3(0, 2.6, 0)
	top.triggered.connect(func(_p: Player) -> void: complete_objective(&"lookout"))
	add_child(top)
	_placard("HillNote", Vector3(HILL.x + 9.0, 0, HILL.z), -PI / 2.0, "III", "The Hill", "Acquisition No. 088\nThumbed",
		"The hill was pushed up by a thumb, from the inside. Its door is kept shut with a plug of the same clay. The door is not locked. Nothing here is locked.")


func _build_village() -> void:
	# Villagers in wire, all in one MultiMesh, praying to the workbench.
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	var villager := _model("villager.glb")
	mm.mesh = _first_mesh(villager)
	villager.free()  # only its mesh is used; the orphan node leaked at exit
	var spots := [Vector3(-16, 0, -23), Vector3(-12, 0, -26), Vector3(-7, 0, -23), Vector3(-3, 0, -26),
		Vector3(3, 0, -23), Vector3(7, 0, -26), Vector3(11, 0, -23), Vector3(-19, 0, -27), Vector3(-9, 0, -20), Vector3(5, 0, -19)]
	mm.instance_count = spots.size()
	for i in spots.size():
		var s: Vector3 = _ground_at(spots[i])
		var dir := TABLE - s
		mm.set_instance_transform(i, Transform3D(Basis(Vector3.UP, atan2(-dir.x, -dir.z)), s))
	_villagers = MultiMeshInstance3D.new()
	_villagers.name = "Villagers"
	_villagers.multimesh = mm
	add_child(_villagers)
	# The Unfinished One.
	_chaser = ClayChaser.new()
	_chaser.name = "UnfinishedOne"
	add_child(_chaser)
	_chaser.setup(terrain, _model("unfinished.glb"))
	_chaser.place(3.0, -25.0)
	_chaser.caught.connect(_show_choice)
	# Horse in the village.
	_provenance(&"horse", _model("horse.glb"), Vector3(-12, 0, -25))
	# Chase starts when the player crosses the village entrance.
	var entrance := TriggerZone.make_box(Vector3(84.0, 6.0, 2.0))
	entrance.position = Vector3(0, 3.0, -21.5)
	entrance.triggered.connect(func(_p: Player) -> void:
		if not _chase_started:
			_chase_started = true
			_chaser.start_chase())
	add_child(entrance)
	_placard("VillageNote", Vector3(-22, 0, -17), PI / 2.0, "IV", "The Armature Village", "Acquisition No. 088\nWire and hope",
		"The figures were never covered. Their wire shows, and their hands are open. They face the workbench. They have been praying for the workbench for some time.")


func _build_table() -> void:
	var bench := _model("bench.glb")
	bench.position = Vector3(0.0, TABLE_TOP, TABLE.z)
	add_child(bench)
	var lamp := OmniLight3D.new()
	lamp.light_color = Color("ffd59a")
	lamp.omni_range = 7.0
	lamp.light_energy = 2.2
	lamp.position = Vector3(0, TABLE_TOP + 2.2, TABLE.z + 1.5)
	add_child(lamp)
	# The fragment on the bench top appears once the reveal is done.
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the fragment"
	_fragment.hold_time = 0.8
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.7
	cs.shape = sph
	_fragment.add_child(cs)
	_fragment.position = Vector3(-0.6, TABLE_TOP + 1.25, TABLE.z - 0.4)
	var frag_visual := _model("fragment.glb")
	_fragment.visual = frag_visual
	_fragment.add_child(frag_visual)
	_fragment.picked.connect(_on_fragment_taken)
	_fragment.enabled = false
	_fragment.visible = false
	add_child(_fragment)
	# Bench-top trigger: reaching the top with the objectives done starts the reveal.
	var top := TriggerZone.make_box(Vector3(10.0, 1.6, 8.0), false)
	top.position = Vector3(0, TABLE_TOP + 1.2, TABLE.z)
	top.triggered.connect(_on_bench_top)
	add_child(top)
	_placard("BenchNote", Vector3(3.2, TABLE_TOP, TABLE.z + 1.6), PI / 2.0 + PI, "V", "The Workbench", "Acquisition No. 088\nTools",
		"The workbench is the exhibit's most charming feature. The scissors are open. The jar of eyes has not been closed. The figures below have been waiting for it to be finished.")


func _build_fence() -> void:
	# Wire fence across the village. Pressing a module lowers it; the Unfinished One's choice lowers it too.
	for i in FENCE_MODULES:
		var root := StaticBody3D.new()
		root.name = "Fence%02d" % i
		root.set_meta("clay_press", "gate")
		root.collision_layer = 1 << 4
		root.collision_mask = 0
		root.add_child(_model("gate.glb"))
		var cs := CollisionShape3D.new()
		var bx := BoxShape3D.new()
		bx.size = Vector3(FENCE_W, 2.4, 0.2)
		cs.shape = bx
		cs.position = Vector3(0, 1.2, 0)
		root.add_child(cs)
		root.position = Vector3(-FENCE_MODULES * FENCE_W * 0.5 + (i + 0.5) * FENCE_W, terrain.height_at(0, FENCE_Z), FENCE_Z)
		add_child(root)
		_fence.append(root)


func _build_burrow() -> void:
	# The chamber behind a plug in the hill's west face. The film is inside.
	var room := _model("burrow.glb")
	room.position = Vector3(28.5, 0.0, -11.0)
	add_child(room)
	_provenance(&"film", _model("film.glb"), Vector3(30.2, 0.2, -11.0))
	if not bool(_saved.get("plug_open", false)):
		_plug = StaticBody3D.new()
		_plug.name = "Plug"
		_plug.collision_layer = 1 << 4
		_plug.collision_mask = 0
		_plug.set_meta("clay_press", "plug")
		_plug.add_child(_model("plug.glb"))
		var cs := CollisionShape3D.new()
		var bx := BoxShape3D.new()
		bx.size = Vector3(0.9, 2.4, 4.0)
		cs.shape = bx
		cs.position = Vector3(0, 1.2, 0)
		_plug.add_child(cs)
		_plug.position = Vector3(26.1, 0.0, -11.0)
		add_child(_plug)
	_placard("BurrowNote", Vector3(23.6, 0, -11.0), -PI / 2.0, "VI", "The Chamber", "Acquisition No. 088\nClosed",
		"A chamber in the hill, closed with a plug. The plug has a thumbprint on it the size of a door. The Curator would like it noted that the door was never locked.")


func _make_crumbs() -> GPUParticles3D:
	var g := GPUParticles3D.new()
	g.name = "Crumbs"
	g.amount = 24
	g.lifetime = 0.7
	g.fixed_fps = 12
	g.emitting = false
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 60.0
	pm.initial_velocity_min = 0.6
	pm.initial_velocity_max = 1.6
	pm.gravity = Vector3(0, -9.0, 0)
	pm.scale_min = 0.03
	pm.scale_max = 0.06
	g.process_material = pm
	var mesh := SphereMesh.new()
	mesh.radius = 0.5
	mesh.height = 1.0
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.56, 0.34, 0.20)
	mesh.material = mat
	g.draw_pass_1 = mesh
	return g


func _provenance(id: StringName, model: Node3D, at: Vector3) -> void:
	if Quest.has_provenance(wing_id, id):
		model.free()
		return
	var marker := Node3D.new()
	marker.name = "Prov_" + String(id)
	add_child(marker)
	marker.position = _ground_at(at) + Vector3(0, 0.25, 0)
	var pick := Pickup.new()
	pick.kind = &"provenance"
	pick.item_id = id
	for p: Dictionary in provenances():
		if StringName(p["id"]) == id:
			pick.prompt = "Take: " + String(p["name"])
	pick.visual = model
	pick.add_child(model)
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.7
	cs.shape = sph
	pick.add_child(cs)
	marker.add_child(pick)


func _first_mesh(n: Node) -> Mesh:
	if n is MeshInstance3D:
		return (n as MeshInstance3D).mesh
	for c in n.get_children():
		var m := _first_mesh(c)
		if m:
			return m
	return null


# --- restoring saved state -------------------------------------------------------------------

func _apply_saved() -> void:
	var st := _saved
	if st.has("heights") and (st["heights"] as Array).size() == terrain.h.size():
		var hs: Array = st["heights"]
		for i in hs.size():
			terrain.h[i] = float(hs[i])
		var ms: Array = st.get("marks", [])
		for i in mini(ms.size(), terrain.mark.size()):
			terrain.mark[i] = float(ms[i])
		terrain.dirty = true
		terrain.flush()
	pouch = float(st.get("pouch", POUCH_START))
	_tool = bool(st.get("tool", false))
	_scooped = bool(st.get("scooped", false))
	_pulled = bool(st.get("pulled", false))
	_reveal_done = bool(st.get("reveal_done", false))
	_gate_down = bool(st.get("gate_down", false))
	_choice = StringName(st.get("choice", ""))
	if _choice != &"":
		_choice_shown = true
		_chaser.state = &"done"
		_chaser.scale = Vector3.ONE * (0.6 if _choice == &"keep" else 1.0)
	_set_fence_down(false, _gate_down)
	if st.has("boulder") and (st["boulder"] as Array).size() == 3:
		var bp: Array = st["boulder"]
		_boulder.global_position = Vector3(bp[0], bp[1], bp[2])
		if bool(st.get("boulder_flat", false)):
			_boulder.freeze = true
			_boulder.visual.scale = Vector3(1.0, ClayBoulder.FLAT_Y, 1.0)
			_boulder.flat = true
	if _plug and bool(st.get("plug_open", false)):
		_plug.queue_free()
		_plug = null
	if _reveal_done:
		_fragment.visible = true
		_fragment.enabled = true


# --- beats, aiming and verbs -------------------------------------------------------------------

func _on_beat(_dt: float) -> void:
	if terrain == null or Game.player == null:
		return
	var p := Game.player
	var keep := p.global_position
	var primary := p.action_held(&"primary")
	var secondary := p.action_held(&"secondary")
	var working := false
	if _aim_kind == &"terrain":
		if primary:
			working = true
			if _in_pit(_aim):
				_scoop(keep)
			else:
				_pull(keep)
		if secondary:
			working = true
			_press_ground(keep)
	elif _aim_kind == &"boulder" and secondary and _boulder:
		working = true
		_boulder.press(STEP)
	elif _aim_kind == &"gate" and secondary and not _gate_down:
		working = true
		_gate_press += STEP
		if _gate_press >= GATE_TIME:
			_lower_fence()
	elif _aim_kind == &"plug" and secondary and _plug:
		working = true
		_plug_press += STEP
		if _plug_press >= PLUG_TIME:
			_open_plug()
	if _aim_kind != &"gate":
		_gate_press = maxf(0.0, _gate_press - STEP * 0.5)
	if _aim_kind != &"plug":
		_plug_press = maxf(0.0, _plug_press - STEP * 0.5)
	_crumbs.emitting = working and _aim_kind == &"terrain"
	if _crumbs.emitting:
		_crumbs.global_position = _aim
	terrain.flush()
	if _chase_started and _choice == &"":
		_chaser.beat(p.global_position)
		_check_choice_proximity(p.global_position)
	_check_objectives()
	_animate_villagers()


func _pull(keep: Vector3) -> void:
	var dh := PULL_RATE * STEP
	var w := terrain.weight_sum(_aim, BRUSH_R, keep)
	if w <= 0.0 or pouch <= 0.01:
		return
	if dh * w > pouch:
		dh *= pouch / (dh * w)
	var moved := terrain.brush(_aim, BRUSH_R, dh, keep)
	if moved > 0.0:
		_pulled = true
		pouch = clampf(pouch - moved, 0.0, _pouch_cap())
		Audio.sfx(_stream("pull"), _aim, -6.0, 0.0, randf_range(0.9, 1.1))


func _scoop(keep: Vector3) -> void:
	var dh := -PULL_RATE * STEP * 1.2
	var moved := terrain.brush(_aim, BRUSH_R, dh, keep, DIG_FLOOR)
	if moved < 0.0:
		pouch = clampf(pouch - moved, 0.0, _pouch_cap())
		Audio.sfx(_stream("pull"), _aim, -10.0, 0.0, 0.7)
		if pouch >= _pouch_cap() - 0.05:
			_scooped = true


func _press_ground(keep: Vector3) -> void:
	var dh := -PULL_RATE * STEP * (2.0 if _tool else 1.0)
	var moved := terrain.brush(_aim, BRUSH_R, dh, keep, PRESS_FLOOR)
	if moved < 0.0:
		pouch = clampf(pouch - moved, 0.0, _pouch_cap())
		Audio.sfx(_stream("press"), _aim, -4.0, 0.0, randf_range(0.9, 1.1))


func _pouch_cap() -> float:
	return POUCH_MAX + (TOOL_POUCH_BONUS if _tool else 0.0)


func _in_pit(p: Vector3) -> bool:
	return Vector2(p.x - DIG_CENTRE.x, p.z - DIG_CENTRE.z).length() < DIG_R


func _check_objectives() -> void:
	if not Quest.is_step_done(&"raise", &"pull_step") and _pulled:
		complete_step(&"raise", &"pull_step")
	if not Quest.is_step_done(&"raise", &"mound") and terrain.height_at(MOUND.x, MOUND.z) <= MOUND_DONE:
		complete_step(&"raise", &"mound")
	if not Quest.is_step_done(&"cross", &"carry") and _scooped:
		complete_step(&"cross", &"carry")
	if not Quest.is_step_done(&"way_up", &"ramp") and terrain.max_in(-1.5, 1.5, RAMP_Z - 1.0, RAMP_Z + 1.0) >= 2.0:
		complete_step(&"way_up", &"ramp")


func _show_choice() -> void:
	if _choice != &"" or _choice_shown:
		return
	_choice_shown = true
	var kneel := Interactable.make_box(Vector3(1.2, 1.6, 1.2), "Kneel and finish it")
	kneel.hold_time = 1.4
	kneel.once = true
	kneel.position = Vector3(-1.0, 0.8, 0.0)
	kneel.interacted.connect(func(_p: Player) -> void: _choose(&"kneel"))
	_chaser.add_child(kneel)
	var keep_it := Interactable.make_box(Vector3(1.2, 1.6, 1.2), "Take the tool")
	keep_it.once = true
	keep_it.position = Vector3(1.0, 0.8, 0.0)
	keep_it.interacted.connect(func(_p: Player) -> void: _choose(&"keep"))
	_chaser.add_child(keep_it)
	_chaser.state = &"idle"


func _check_choice_proximity(p: Vector3) -> void:
	if _choice != &"" or _choice_shown or _chaser.state != &"idle":
		return
	if Vector2(p.x - _chaser.global_position.x, p.z - _chaser.global_position.z).length() < 4.0:
		_show_choice()


func _choose(c: StringName) -> void:
	if _choice != &"":
		return
	_choice = c
	_chaser.state = &"done"
	for child in _chaser.get_children():
		if child is Interactable:
			child.queue_free()
	if c == &"keep":
		_tool = true
		_chaser.create_tween().tween_property(_chaser, "scale", Vector3.ONE * 0.6, 1.6)
		toast("The tool is yours now. The pouch is larger and the press is firmer.", "Addendum to the catalogue")
	else:
		_chaser.create_tween().tween_property(_chaser, "rotation:y", _chaser.rotation.y + TAU, 1.4)
		_lower_fence()
		toast("The figure is finished. It has turned to face the workbench, and the fence has come down for it.", "Addendum to the catalogue")


func _lower_fence() -> void:
	if _gate_down:
		return
	_gate_down = true
	_set_fence_down(true, true)
	complete_step(&"way_up", &"gate")


func _set_fence_down(animate: bool, down: bool) -> void:
	if not down:
		return
	for f in _fence:
		if animate:
			f.create_tween().tween_property(f, "rotation:x", -PI / 2.0, 1.2).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		else:
			f.rotation.x = -PI / 2.0


func _open_plug() -> void:
	if _plug == null:
		return
	var p := _plug
	_plug = null
	complete_step(&"cross", &"doorway")
	var t := p.create_tween()
	t.tween_property(p, "position:y", p.position.y + 2.6, 0.8)
	t.tween_callback(p.queue_free)


func _on_bench_top(_p: Player) -> void:
	if _reveal_done or _reveal_started:
		return
	if not Quest.main_objectives_done():
		var now := Time.get_ticks_msec() / 1000.0
		if now - _bench_nag > 8.0:
			_bench_nag = now
			toast("The bench is not ready. Something below it is still waiting for the rest of the forest.", "Addendum to the catalogue")
		return
	_reveal()


func _reveal() -> void:
	_reveal_started = true
	var p := Game.player
	p.input_enabled = false
	await Audio.reveal(_stream("reveal"), 1.2)
	for f in [8.0, 6.0, 2.0]:
		world_fps = f
		await get_tree().create_timer(0.9, true, false, true).timeout
	world_fps = 0.0
	await get_tree().create_timer(1.0, true, false, true).timeout
	toast("The forest has stopped. It is the first time it has waited for anyone.", "Addendum to the catalogue")
	await get_tree().create_timer(1.4, true, false, true).timeout
	world_fps = WORLD_FPS
	p.input_enabled = true
	_reveal_done = true
	_fragment.visible = true
	_fragment.enabled = true


func _on_fragment_taken() -> void:
	finish()


func _animate_villagers() -> void:
	# Stepped prayer: each figure nods on the beat.
	var mm := _villagers.multimesh
	for i in mm.instance_count:
		var t := mm.get_instance_transform(i)
		var nod := sin(float(_tick) * 0.9 + float(i)) * 0.03
		t.basis = t.basis.orthonormalized().rotated(t.basis.x.normalized(), nod)
		mm.set_instance_transform(i, t)
