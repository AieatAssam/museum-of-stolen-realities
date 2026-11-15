extends Wing
## The Drowned Aria (Acquisition No. 003). Rule: Singing Gravity. The wing's gravity is constant;
## sounding instruments add acceleration on top of it (see instrument.gd, song_mode.gd).
## Greybox: geometry is placeholder boxes, grouped as Areas/<AreaName>/Geometry and Areas/<AreaName>/...
## Areas: Foyer (ramp to gallery), Auditorium (horns, chord, cadence, sink well, fragment),
## OrchestraPit (two pipes make a gantry reachable only by a chord), ScoredCorridor (gravity flips
## on the downbeat over a gap), FlyLoft (tuning-fork statue). The dome is not built yet.

const SongMode := preload("res://wings/aria/song_mode.gd")
const Instrument := preload("res://wings/aria/instrument.gd")
const MODELS := "res://wings/aria/models/"
const AUDIO := "res://wings/aria/audio/"
const MAT_DIRS := ["res://wings/aria/materials", MaterialLib.CORE_DIR]
const CHORD_NOTES := [&"organ_c", &"organ_e", &"organ_g"]
const CADENCE := [&"g", &"e", &"c"]
const FLIP_PERIOD := 6.0  # seconds between downbeats (world time)
const FLIP_WINDOW := 3.0  # seconds gravity stays reversed each downbeat (the 10 m ceiling takes about 2.5 s to walk)
const GANTRY_TOP := 1.0   # world Y of the pit gantry; tuned so one pipe cannot reach it, two can

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
var _flip_clock: float = 0.0


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


func on_exit() -> void:
	SongMode.flipping = false


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
	_build_pit(areas)
	_build_corridor(areas)
	_build_fly_loft(areas)
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
	# downbeats: world time, not Engine.time_scale
	_flip_clock += delta * Game.world_time_scale
	var flipping := fposmod(_flip_clock, FLIP_PERIOD) < FLIP_WINDOW
	if flipping and not SongMode.flipping:
		Audio.sfx(load(AUDIO + "gravity_release.ogg"), Vector3(27, 4, 39), 0.0, 0.2, 1.0)
	SongMode.flipping = flipping
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


# --- Foyer: entrance hall, grand ramp, gallery landing -----------------------------------

func _build_foyer(areas: Node3D) -> void:
	var foyer := _group(areas, "Foyer")
	var geo := _group(foyer, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	# entrance floor, z 16 (the auditorium threshold) to 30 (the ramp foot)
	_box(geo, Vector3(30, 1, 14), Vector3(0, -0.5, 23), walk)
	_box(geo, Vector3(1, 14, 26), Vector3(-15.5, 7, 29), wall)
	# east wall stops at z 36: the corridor opens to the gallery there
	_box(geo, Vector3(1, 14, 20), Vector3(15.5, 7, 26), wall)
	_box(geo, Vector3(30, 14, 1), Vector3(0, 7, 42.5), wall)
	# grand ramp: 12 m wide, rising 2.8 m over 7 m (about 22 degrees), walked by the floor handling
	var stairs := _group(foyer, "GrandStaircase")
	var ramp := Vector3(12, 0.4, 7.54)
	var angle := atan2(2.8, 7.0)
	var ramp_body := StaticBody3D.new()
	ramp_body.position = Vector3(0, 1.4 - 0.2 * cos(angle), 33.5 + 0.2 * sin(angle))
	ramp_body.rotation.x = -angle
	stairs.add_child(ramp_body)
	_slab(ramp_body, ramp, walk)
	# gallery landing at the top of the ramp, 2.8 m up
	_box(geo, Vector3(30, 2.8, 4), Vector3(0, 1.4, 39.0), walk)
	# the wordless demonstration horn at the ramp foot: a lift the player learns on
	var demo := _instrument("horn", "note_horn", &"note_horn", &"lift", Vector3(0, 0, 19))
	demo.name = "DemoHorn"
	foyer.add_child(demo)
	_provenance(foyer, "score", Vector3(-13, 2.8, 39))
	_placard(foyer, Vector3(-8, 1.4, 25), 0.0, "I", "The Foyer", "Acq. No. 003  ·  Entrance",
		"Visitors are asked to leave their umbrellas at the door. The door has been gone since 1961. The umbrellas were never recovered, and the foyer still smells of rain.")
	_placard(foyer, Vector3(-14.9, 1.6, 33), 90.0, "II", "The Gallery Ramp", "Acq. No. 003  ·  Gallery",
		"The ramp was built for a procession that was never scheduled. Its handrail was removed for conservation. Conservators have not agreed what conservation required, or who signed the form.")


# --- Auditorium: the flooded hall, the brass, the chord, the cadence, the sink well -------

func _build_auditorium(areas: Node3D) -> void:
	var aud := _group(areas, "Auditorium")
	var geo := _group(aud, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	# floor, 30 m wide, from z = 16 (the foyer threshold) to z = -30 (the stage)
	_box(geo, Vector3(30, 1, 46), Vector3(0, -0.5, -7), walk)
	# west wall, with the opening to the orchestra pit at z -14..-6
	_box(geo, Vector3(1, 14, 16), Vector3(-15.5, 7, -22), wall)
	_box(geo, Vector3(1, 14, 22), Vector3(-15.5, 7, 5), wall)
	_box(geo, Vector3(1, 14, 46), Vector3(15.5, 7, -7), wall)
	_box(geo, Vector3(30, 14, 1), Vector3(0, 7, -30.5), wall)
	# the stage lip: a low step the player can walk over
	_box(geo, Vector3(30, 0.6, 2), Vector3(0, 0.3, -22), walk)
	_build_instruments(aud)
	_placard(aud, Vector3(-12, 1.4, 12), 90.0, "III", "The Flooded Auditorium", "Acq. No. 003  ·  Hall",
		"Water reached the second row in the spring. Seats in the first row were never counted, so that loss is recorded as nil. The horns are kept operational for educational purposes only.")


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


# --- Orchestra pit: down the ramp at the west wall. Two pipes lift you onto the gantry together ---

func _build_pit(areas: Node3D) -> void:
	var pit := _group(areas, "OrchestraPit")
	var geo := _group(pit, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	# pit floor, 3 m below the auditorium, x -32..-16, z -20..0
	_box(geo, Vector3(16, 1, 20), Vector3(-24, -3.5, -10), walk)
	_box(geo, Vector3(1, 14, 20), Vector3(-32.5, 4, -10), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(-24, 4, -20.5), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(-24, 4, 0.5), wall)
	# the ramp down from the auditorium floor: 6.7 m long, 3 m drop, 8 m wide
	var len_ := sqrt(36.0 + 9.0)
	var a := atan2(3.0, 6.0)
	var ramp_body := StaticBody3D.new()
	ramp_body.position = Vector3(-18.5 + 0.2 * sin(a), -1.5 - 0.2 * cos(a), -10)
	ramp_body.rotation.z = a
	geo.add_child(ramp_body)
	_slab(ramp_body, Vector3(len_, 0.4, 8), walk)
	# the gantry: a platform reached only by lifting on both pipes at once
	# kept clear of the ramp (z -14..-6): the ramp would otherwise pass through the block
	_box(geo, Vector3(8, GANTRY_TOP + 3, 5), Vector3(-22, (GANTRY_TOP - 3) * 0.5, -17), walk)
	# under-stage machinery: two lift pipes that must sound together, and a sink well
	var root := _group(pit, "Instruments")
	for p: Array in [[Vector3(-28, -3, -13), &"pit_a", "note_organ_c"], [Vector3(-28, -3, -11), &"pit_b", "note_organ_e"]]:
		var inst := _instrument("pipes", p[2], p[1], &"lift", p[0])
		inst.strength = 26.0
		root.add_child(inst)
	var well := _instrument("", "note_cello", &"pit_well", &"sink", Vector3(-22, -3, -2))
	well.radius = 2.2
	well.height = 3.0
	well.strength = 14.0
	root.add_child(well)
	_provenance(pit, "baton", Vector3(-30.5, -3, -3))
	_placard(pit, Vector3(-20, -1.6, -4), 0.0, "IV", "The Orchestra Pit", "Acq. No. 003  ·  Under-stage",
		"Musicians descended here before each performance. The records show the pit was dry for the entire run, although the flood reports list it as the first room to fill.")
	_placard(pit, Vector3(-30, -1.6, -15), 90.0, "V", "The Gantry", "Acq. No. 003  ·  Technical",
		"Technicians reached the gantry by lifting with the pipes. The pipes are documented as silent during the period. The source of the sound is listed as unknown, which is listed as a finding.")


# --- Scored corridor: the gap, the ceiling it flips onto, and the downbeat -------------

func _build_corridor(areas: Node3D) -> void:
	var cor := _group(areas, "ScoredCorridor")
	var geo := _group(cor, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	var haz := _flat(C_HAZARD)
	# x 15..46, z 36..42, floor at 2.8 m (the gallery height); a 6 m gap sits at x 24..30
	_box(geo, Vector3(9, 2.8, 6), Vector3(19.5, 1.4, 39), walk)
	_box(geo, Vector3(16, 2.8, 6), Vector3(38, 1.4, 39), walk)
	_box(geo, Vector3(31, 14, 1), Vector3(30.5, 7, 35.5), wall)
	_box(geo, Vector3(31, 14, 1), Vector3(30.5, 7, 42.5), wall)
	# the ceiling the player rides upside down during a downbeat, over the gap and its approach
	_box(geo, Vector3(10, 0.4, 6), Vector3(27, 6.0, 39), wall)
	# the drop into the gap: hazard floor and a trigger that sends her back to the corridor checkpoint
	_box(geo, Vector3(8, 1, 6), Vector3(27, -2.5, 39), haz)
	var drop := TriggerZone.make_box(Vector3(8, 2, 6), false)
	drop.position = Vector3(27, -1, 39)
	drop.triggered.connect(func(_p: Player) -> void: Game.respawn())
	cor.add_child(drop)
	SongMode.flip_box = AABB(Vector3(22, 0, 36), Vector3(10, 8, 6))
	_placard(cor, Vector3(18, 4.2, 36.05), 0.0, "VI", "The Scored Corridor", "Acq. No. 003  ·  Passage",
		"Gravity here reverses on the downbeat, as composed. The score marks each reversal with a rest, which is the only part of the score the audience is said to remember.")


# --- Fly-loft: the tuning-fork statue and a loft organ, reached through the corridor ----------

func _build_fly_loft(areas: Node3D) -> void:
	var loft := _group(areas, "FlyLoft")
	var geo := _group(loft, "Geometry")
	var walk := _flat(C_WALK)
	var wall := _flat(C_WALL)
	_box(geo, Vector3(16, 2.8, 16), Vector3(54, 1.4, 38), walk)
	_box(geo, Vector3(1, 14, 18), Vector3(62.5, 7, 38), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(54, 7, 46.5), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(54, 7, 29.5), wall)
	var root := _group(loft, "Instruments")
	# the statue: a tall column that rings a fork note when struck
	var statue := _instrument("", "fork_strike", &"fork", &"lift", Vector3(56, 2.8, 40))
	statue.name = "TuningForkStatue"
	var column := MeshInstance3D.new()
	var cm := BoxMesh.new()
	cm.size = Vector3(0.6, 3.0, 0.6)
	column.mesh = cm
	column.material_override = _flat(C_INTERACT)
	column.position.y = 1.5
	statue.add_child(column)
	root.add_child(statue)
	# the loft organ: a lift that sounds on its own note
	var organ := _instrument("pipes", "note_organ_g", &"loft_organ", &"lift", Vector3(48, 2.8, 32))
	root.add_child(organ)
	_provenance(loft, "tuning_fork", Vector3(61, 2.8, 31))
	_placard(loft, Vector3(52, 4.2, 30.6), 0.0, "VII", "The Fly-Loft", "Acq. No. 003  ·  Rigging",
		"Stagehands stored the flown scenery here until it was sold. The inventory lists four drops. Three were found, and the fourth is said to have been requested by the chorus.")
	_placard(loft, Vector3(56, 4.2, 41.4), 180.0, "VIII", "The Tuning Fork", "Acq. No. 003  ·  Statue",
		"A fork sets the pitch for the whole orchestra. The statue beside it is inscribed with the note A. The inscription has been corrected twice, and the correction was signed by the statue.")


func _build_checkpoints() -> void:
	_checkpoint(&"start", Vector3(0, 0.5, 26))
	_checkpoint(&"gallery", Vector3(0, 3.3, 37))
	_checkpoint(&"auditorium", Vector3(0, 0.5, 10))
	_checkpoint(&"pit", Vector3(-26, -2.5, -5))
	_checkpoint(&"corridor", Vector3(17, 3.3, 39))
	_checkpoint(&"flyloft", Vector3(50, 3.3, 36))
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
		_strikes.remove_at(0)
	if _strikes == [&"g", &"e", &"c"] and not Quest.is_done(&"cadence"):
		complete_step(&"cadence", &"cadence")


# --- helpers -----------------------------------------------------------------------

func _provenance(parent: Node3D, id: String, pos: Vector3) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var p := {}
	for d: Dictionary in provenances():
		if d["id"] == id:
			p = d
	var marker := Node3D.new()
	marker.position = pos
	var holder := parent.find_child("Provenances", false, false) as Node3D
	if holder == null:
		holder = _group(parent, "Provenances")
	holder.add_child(marker)
	var mesh := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.25, 0.3, 0.25)
	mesh.mesh = pm
	mesh.material_override = _flat(C_INTERACT)
	mesh.position.y = 0.4
	marker.add_child(mesh)
	var pick := Pickup.new()
	pick.kind = &"provenance"
	pick.item_id = StringName(id)
	pick.prompt = "Take: " + String(p["name"])
	pick.visual = mesh
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.4
	cs.shape = sph
	pick.add_child(cs)
	marker.add_child(pick)


func _placard(parent: Node3D, pos: Vector3, yaw_deg: float, heading: String, title: String, catalog: String, body: String) -> void:
	var pl := Placard.new()
	pl.heading = heading
	pl.title = title
	pl.catalog_line = catalog
	pl.body = body
	pl.position = pos
	pl.rotation_degrees.y = yaw_deg
	parent.add_child(pl)


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
	parent.add_child(body)
	_slab(body, size, mat)


## A box mesh and collision on an existing body, centred on the body's origin.
func _slab(body: Node3D, size: Vector3, mat: Material) -> void:
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


func _model(name_: String, pos: Vector3) -> Node3D:
	var node := MaterialLib.instance(MODELS + name_ + ".glb", MAT_DIRS)
	node.position = pos
	return node
