extends Wing
## The Drowned Aria (Acquisition No. 003). Rule: Singing Gravity. The wing's gravity is constant;
## sounding instruments add acceleration on top of it (see instrument.gd, song_mode.gd).
## Greybox: geometry is placeholder boxes, grouped as Areas/<AreaName>/Geometry and Areas/<AreaName>/...
## Areas so far: Foyer (grand staircase, gallery), Auditorium (the flooded hall: horns, pipes,
## glass, sink well, provenances, fragment). Still to build: pit, fly-loft, dome, duet, chandelier, heist.

const SongMode := preload("res://wings/aria/song_mode.gd")
const Instrument := preload("res://wings/aria/instrument.gd")
const MODELS := "res://wings/aria/models/"
const AUDIO := "res://wings/aria/audio/"
const MAT_DIRS := ["res://wings/aria/materials", MaterialLib.CORE_DIR]
const CHORD_NOTES := [&"organ_c", &"organ_e", &"organ_g"]
const CADENCE := [&"g", &"e", &"c"]

# placeholder colours, one per function
const C_WALK := Color("6b7f8a")  # walkable
const C_WALL := Color("39424a")  # structure
const C_INTERACT := Color("e0c040")  # interactive
const C_HAZARD := Color("c0392b")  # hazard
const C_GOAL := Color("2ecc71")  # goal

var _strikes: Array[StringName] = []
var _fragment: Pickup
var _fragment_spot: Node3D
var _chord_done: bool = false


func objectives() -> Array[Dictionary]:
	return [
		{"id": "brass", "title": "Wake the brass",
			"steps": [{"id": "horn_a", "title": "The west horn"}, {"id": "horn_b", "title": "The east horn"}, {"id": "horn_c", "title": "The gallery horn"}],
			"hint": "Aim at an instrument and press primary to strike it. While it sounds it lifts you."},
		{"id": "chord", "title": "Play the chord",
			"steps": [{"id": "chord", "title": "Have all three pipes sounding at once"}],
			"hint": "Each pipe sounds for nine seconds. Strike all three before the first one fades."},
		{"id": "cadence", "title": "Carry the cadence",
			"steps": [{"id": "cadence", "title": "Strike G, E, C in order on the glass"}],
			"hint": "Hold secondary near a struck note to sustain it. Breath runs out, and returns when you let go."},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "score", "name": "A pencilled score, page nine", "line": "The last page was left blank so that the audience could sing it."},
		{"id": "baton", "name": "A conductor's baton, ash", "line": "Restored to the orchestra by a clerk who was not authorised to restore anything."},
		{"id": "tuning_fork", "name": "A tuning fork, A-440", "line": "Struck once, it still tells the room what is true."},
	]


func fragment() -> Dictionary:
	return {"name": "A fragment of the Drowned Aria", "line": "The chorus was never recorded. Only the silence between its verses was kept."}


func register_modes(player: Player) -> void:
	player.add_mode(&"song", SongMode.new())


func on_enter(first_time: bool) -> void:
	if first_time:
		await Cinematics.play([
			{"card": "The Drowned Aria", "sub": "Acquisition No. 003", "t": 3.0, "style": "display"},
		])
	toast("The foyer is open. The auditorium is flooded to the second row.")


func save_state() -> Dictionary:
	return {"strikes": _strikes.map(func(s: StringName) -> String: return String(s))}


func load_state(state: Dictionary) -> void:
	_strikes.clear()
	for s: Variant in state.get("strikes", []):
		_strikes.append(StringName(s))


func _ready() -> void:
	_build_environment()
	var areas := Node3D.new()
	areas.name = "Areas"
	add_child(areas)
	_build_foyer(areas)
	_build_auditorium(areas)
	_build_checkpoints()
	_build_fragment()
	Quest.objective_completed.connect(func(_w: StringName, _o: StringName) -> void: _update_fragment())


func _process(delta: float) -> void:
	if not _chord_done and not Quest.is_step_done(&"chord", &"chord"):
		var sounding := 0
		for id: StringName in CHORD_NOTES:
			for n: Node in get_tree().get_nodes_in_group(Instrument.GROUP):
				var inst := n as Instrument
				if inst.note_id == id and inst.sounding():
					sounding += 1
					break
		if sounding == CHORD_NOTES.size():
			_chord_done = true
			complete_step(&"chord", &"chord")
			toast("The pipes hold the chord. The hall answers.")
	# world time, not Engine.time_scale
	_fragment_spot.rotate_y(delta * Game.world_time_scale * 0.6)


func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("04201f")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("0f4d48")
	env.ambient_light_energy = 0.5
	env.fog_enabled = true
	env.fog_light_color = Color("0f4d48")
	env.fog_density = 0.025
	env.glow_enabled = true
	env.glow_bloom = 0.12
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	Quality.apply(env)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.light_color = Color("c9e8df")
	sun.light_energy = 0.35
	sun.rotation_degrees = Vector3(-55, 30, 0)
	add_child(sun)


# --- Foyer: entrance hall, grand staircase, gallery landing --------------------------------

func _build_foyer(areas: Node3D) -> void:
	var foyer := _group(areas, "Foyer")
	var geo := _group(foyer, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	# entrance floor, z 16 (the auditorium threshold) to 30 (the stair foot)
	_box(geo, Vector3(30, 1, 14), Vector3(0, -0.5, 23), walk)
	_box(geo, Vector3(1, 14, 26), Vector3(-15.5, 7, 29), wall)
	_box(geo, Vector3(1, 14, 26), Vector3(15.5, 7, 29), wall)
	_box(geo, Vector3(30, 14, 1), Vector3(0, 7, 42.5), wall)
	# grand staircase: a 12 m wide ramp rising 2.8 m over 7 m (about 22 degrees). Treads of 0.35 m
	# are too high for the capsule's step-up, so the stair is a slope the floor handling walks.
	var stairs := _group(foyer, "GrandStaircase")
	var ramp := Vector3(12, 0.4, 7.54)
	var angle := atan2(2.8, 7.0)
	var ramp_body := StaticBody3D.new()
	ramp_body.position = Vector3(0, 1.4 - 0.2 * cos(angle), 33.5 + 0.2 * sin(angle))
	ramp_body.rotation.x = -angle
	stairs.add_child(ramp_body)
	var ramp_mi := MeshInstance3D.new()
	var ramp_mesh := BoxMesh.new()
	ramp_mesh.size = ramp
	ramp_mi.mesh = ramp_mesh
	ramp_mi.material_override = walk
	ramp_body.add_child(ramp_mi)
	var ramp_cs := CollisionShape3D.new()
	var ramp_shape := BoxShape3D.new()
	ramp_shape.size = ramp
	ramp_cs.shape = ramp_shape
	ramp_body.add_child(ramp_cs)
	# gallery landing at the top of the ramp, 2.8 m up
	_box(geo, Vector3(30, 2.8, 4), Vector3(0, 1.4, 39.0), walk)
	# the wordless demonstration horn at the stair foot: a lift the player learns on
	var demo := _instrument("horn", "note_horn", &"note_horn", &"lift", Vector3(0, 0, 19))
	demo.name = "DemoHorn"
	demo.strength = 26.0
	foyer.add_child(demo)


# --- Auditorium: the flooded hall, the brass, the chord, the cadence, the sink well -------

func _build_auditorium(areas: Node3D) -> void:
	var aud := _group(areas, "Auditorium")
	var geo := _group(aud, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	# floor, 30 m wide, from z = 16 (the foyer threshold) to z = -30 (the stage)
	_box(geo, Vector3(30, 1, 46), Vector3(0, -0.5, -7), walk)
	_box(geo, Vector3(1, 14, 46), Vector3(-15.5, 7, -7), wall)
	_box(geo, Vector3(1, 14, 46), Vector3(15.5, 7, -7), wall)
	_box(geo, Vector3(30, 14, 1), Vector3(0, 7, -30.5), wall)
	# the stage lip: a low step the player can walk over
	_box(geo, Vector3(30, 0.6, 2), Vector3(0, 0.3, -22), walk)
	_build_instruments(aud)
	_build_provenances(aud)


func _build_instruments(aud: Node3D) -> void:
	var root := _group(aud, "Instruments")
	# the brass: three lift columns, objective one
	var horns := [Vector3(-8, 0, -4), Vector3(8, 0, -4), Vector3(0, 0, -12)]
	var horn_steps := ["horn_a", "horn_b", "horn_c"]
	for i: int in 3:
		var h := _instrument("horn", "note_horn", &"note_horn", &"lift", horns[i])
		h.strength = 26.0
		root.add_child(h)
		h.struck.connect(func(_n: Node3D) -> void: complete_step(&"brass", StringName(horn_steps[i])))
	# the chord: three pipes on C, E, G, all lifts
	var pipes := [[Vector3(-7, 0, -18), &"organ_c", "note_organ_c"], [Vector3(0, 0, -20), &"organ_e", "note_organ_e"], [Vector3(7, 0, -18), &"organ_g", "note_organ_g"]]
	for p: Array in pipes:
		root.add_child(_instrument("pipes", p[2], p[1], &"lift", p[0]))
	# the cadence: three glass bowls, G, E, C
	var glass := [[Vector3(-9, 0, -8), &"g"], [Vector3(9, 0, -8), &"e"], [Vector3(0, 0, -6), &"c"]]
	for g: Array in glass:
		var b := _instrument("glass_bowls", "note_glass", g[1], &"lift", g[0])
		b.strength = 22.0
		root.add_child(b)
		b.struck.connect(func(_n: Node3D) -> void: _on_struck(g[1]))
	# a sink well under the glass: draws you down through its footprint
	var well := _instrument("", "note_cello", &"sink_low", &"sink", Vector3(0, 0, -15))
	well.radius = 3.0
	well.height = 3.0
	well.strength = 14.0
	root.add_child(well)


func _build_provenances(aud: Node3D) -> void:
	var spots := [Vector3(-13, 0.4, 6), Vector3(13, 0.4, -26), Vector3(-6, 0.4, -29)]
	var provs := provenances()
	var root := _group(aud, "Provenances")
	for i: int in provs.size():
		var p: Dictionary = provs[i]
		if Quest.has_provenance(wing_id, StringName(p["id"])):
			continue
		var marker := Node3D.new()
		marker.position = spots[i]
		root.add_child(marker)
		var mesh := MeshInstance3D.new()
		var pm := PrismMesh.new()
		pm.size = Vector3(0.25, 0.3, 0.25)
		mesh.mesh = pm
		mesh.material_override = _flat(C_INTERACT)
		mesh.position.y = 0.4
		marker.add_child(mesh)
		var pick := Pickup.new()
		pick.kind = &"provenance"
		pick.item_id = StringName(p["id"])
		pick.prompt = "Take: " + String(p["name"])
		pick.visual = mesh
		var cs := CollisionShape3D.new()
		var sph := SphereShape3D.new()
		sph.radius = 0.4
		cs.shape = sph
		pick.add_child(cs)
		marker.add_child(pick)


func _build_checkpoints() -> void:
	_checkpoint(&"start", Vector3(0, 0.5, 26))
	_checkpoint(&"gallery", Vector3(0, 3.3, 37))
	_checkpoint(&"auditorium", Vector3(0, 0.5, 10))
	_checkpoint(&"stage", Vector3(0, 0.5, -10))


func _checkpoint(id: StringName, pos: Vector3) -> void:
	var cp := Checkpoint.new()
	cp.id = id
	cp.position = pos
	add_child(cp)


func _build_fragment() -> void:
	_fragment_spot = Node3D.new()
	_fragment_spot.name = "FragmentSpot"
	_fragment_spot.position = Vector3(0, 0.6, -26)
	find_child("Auditorium", true, false).add_child(_fragment_spot)
	var shard := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.5, 0.7, 0.3)
	shard.mesh = pm
	shard.material_override = _flat(C_GOAL)
	_fragment_spot.add_child(shard)
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the fragment"
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.6
	cs.shape = sph
	_fragment.add_child(cs)
	_fragment_spot.add_child(_fragment)
	_fragment.visual = shard
	_fragment.picked.connect(finish)
	_update_fragment()


func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.main_objectives_done() and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_fragment_spot.visible = ready


func _on_struck(note: StringName) -> void:
	_strikes.append(note)
	if _strikes.size() > 3:
		_strikes = _strikes.slice(_strikes.size() - 3)
	if _strikes == [&"g", &"e", &"c"] and not Quest.is_done(&"cadence"):
		complete_step(&"cadence", &"cadence")


# --- helpers -----------------------------------------------------------------------

func _group(parent: Node3D, name_: String) -> Node3D:
	var n := Node3D.new()
	n.name = name_
	parent.add_child(n)
	return n


func _flat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 1.0
	return m


func _instrument(model: String, sound_name: String, note: StringName, kind_: StringName, pos: Vector3) -> Instrument:
	var inst := Instrument.new()
	inst.name = "Instrument_" + String(note)
	inst.note_id = note
	inst.kind = kind_
	inst.position = pos
	inst.sound = load(AUDIO + sound_name + ".ogg")
	if model != "":
		var node := _model(model, Vector3.ZERO)
		for mi: Node in node.find_children("*", "MeshInstance3D", true, false):
			(mi as MeshInstance3D).material_override = _flat(C_INTERACT)
		inst.add_child(node)
	return inst


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> void:
	var body := StaticBody3D.new()
	body.position = pos
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	body.add_child(mi)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	body.add_child(cs)
	parent.add_child(body)


func _model(name_: String, pos: Vector3) -> Node3D:
	var node := MaterialLib.instance(MODELS + name_ + ".glb", MAT_DIRS)
	node.position = pos
	return node
