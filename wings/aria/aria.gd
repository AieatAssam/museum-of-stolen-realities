extends Wing
## The Drowned Aria (Acquisition No. 003). Rule: Singing Gravity. The wing's gravity is constant;
## sounding instruments add acceleration on top of it (see instrument.gd, song_mode.gd).
## Greybox: geometry is placeholder boxes, grouped as Areas/<AreaName>/Geometry and Areas/<AreaName>/...
## Areas: Foyer (ramp to gallery), Auditorium (horns, chord, cadence, La Sirena's duet, sink well),
## OrchestraPit (two pipes make a gantry reachable only by a chord), ScoredCorridor (gravity flips
## on the downbeat over a gap), FlyLoft (tuning-fork statue), Dome (chandelier fall, heist exit).

const SongMode := preload("res://wings/aria/song_mode.gd")
const Art := preload("res://wings/aria/art.gd")
const Instrument := preload("res://wings/aria/instrument.gd")
const MODELS := "res://wings/aria/models/"
const AUDIO := "res://wings/aria/audio/"
const MAT_DIRS := ["res://wings/aria/materials", MaterialLib.CORE_DIR]
const CHORD_NOTES := [&"organ_c", &"organ_e", &"organ_g"]
const CADENCE := [&"g", &"e", &"c"]
const FLIP_PERIOD := 6.0  # seconds between downbeats (world time)
const FLIP_WINDOW := 3.0  # seconds gravity stays reversed each downbeat (the 10 m ceiling takes about 2.5 s to walk)
const GANTRY_TOP := 1.0   # world Y of the pit gantry; tuned so one pipe cannot reach it, two can

# La Sirena: each phrase is sung note by note, then answered within the window. dyn: cres pulls her
# down while she sings, whisp lets her drift up. Rounds rise in length and in window tightness.
const DUET_ROUNDS := [
	[{"notes": [&"g"], "dyn": &"cres"}, {"notes": [&"c"], "dyn": &"whisp"}],
	[{"notes": [&"e", &"g"], "dyn": &"cres"}, {"notes": [&"c"], "dyn": &"whisp"}, {"notes": [&"g", &"c"], "dyn": &"cres"}],
	[{"notes": [&"e", &"g"], "dyn": &"whisp"}, {"notes": [&"g", &"c", &"e"], "dyn": &"cres"}, {"notes": [&"c", &"e"], "dyn": &"whisp"}, {"notes": [&"g", &"c", &"e"], "dyn": &"cres"}],
]
const DUET_WINDOW := [5.0, 4.5, 4.0]
const DUET_PITCH := {&"c": 1.0, &"e": 1.26, &"g": 1.5}
const SING_NOTE := 0.9        # seconds per sung note
const FALL_TIME := 90.0       # the silent chandelier fall, in seconds
const CHANDELIER_TOP := 15.0
const CHANDELIER_LOW := 4.0
const DOME_CENTRE := Vector3(0, 0, -50)

var _strikes: Array[StringName] = []
var _fragment: Pickup
var _fragment_spot: Node3D
var _chord_done: bool = false
var _flip_clock: float = 0.0
var _duet_box := AABB(Vector3(-15, -2, -31), Vector3(30, 14, 11))
var _duet_on: bool = false
var _duet_round: int = 0
var _duet_open: bool = false
var _duet_left: float = 0.0
var _duet_expect: Array = []
var _duet_idx: int = 0
var _duet_wrong: bool = false
var _sung: AudioStream
var _fall_on: bool = false
var _chandelier: Node3D
var _heads: Array[Node3D] = []
var art: Art


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
			"hint": "Hold secondary to sustain the last note you struck. It travels with you. Breath runs out, and returns when you let go."},
		{"id": "duet", "title": "Answer La Sirena",
			"steps": [{"id": "round1", "title": "Round one"}, {"id": "round2", "title": "Round two"}, {"id": "round3", "title": "Round three"}],
			"hint": "She sings a phrase. Strike the same notes on the stage bowls, in order, before the window closes. A wrong or late answer repeats the round."},
		{"id": "fall", "title": "The silent fall",
			"steps": [{"id": "fall", "title": "Let the chandelier come down"}],
			"hint": "The music stops. The chandelier takes ninety seconds. You are free to walk."},
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
	art.on_enter()
	if first_time:
		await Cinematics.play([
			{"card": "The Drowned Aria", "sub": "Acquisition No. 003", "t": 3.0, "style": "display"},
		])
		toast("The foyer is open. The auditorium is flooded to the second row.")
	# resuming: a finished fall stays finished; a duet already won resumes its fall
	if Quest.is_done(&"fall"):
		_chandelier.position.y = CHANDELIER_LOW
	elif Quest.is_done(&"duet"):
		_begin_fall(false)


func on_exit() -> void:
	art.on_exit()
	SongMode.flipping = false
	SongMode.duet_box = AABB()
	SongMode.duet_accel = 0.0
	if Game.player:
		Game.player.gravity_vector = gravity


func save_state() -> Dictionary:
	return {"strikes": _strikes.map(func(s: StringName) -> String: return String(s))}


func load_state(state: Dictionary) -> void:
	_strikes.clear()
	for s: Variant in state.get("strikes", []):
		_strikes.append(StringName(s))


func _ready() -> void:
	var areas := Node3D.new()
	areas.name = "Areas"
	add_child(areas)
	_build_foyer(areas)
	_build_auditorium(areas)
	_build_pit(areas)
	_build_corridor(areas)
	_build_fly_loft(areas)
	_build_dome(areas)
	_build_checkpoints()
	_build_fragment()
	_build_marks()
	art = Art.new()
	art.name = "Art"
	add_child(art)
	art.build(self)
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
	if _duet_open:
		_duet_left -= delta
	if _fall_on:
		for h: Node3D in _heads:
			h.look_at(_chandelier.global_position, Vector3.UP)


# --- Foyer: entrance hall, grand ramp, gallery landing -----------------------------------

func _build_foyer(areas: Node3D) -> void:
	var foyer := _group(areas, "Foyer")
	var geo := _group(foyer, "Geometry")
	var walk := _mat("marble_teal")
	var wall := _mat("damask_ox")
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
	ramp_body.name = "FoyerRamp"
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
	_placard(foyer, Vector3(-8, 1.4, 25), 0.0, "I", "The Foyer", "Acq. No. 003\nEntrance",
		"Visitors are asked to leave their umbrellas at the door. The door has been gone since 1961. The umbrellas were never recovered, and the foyer still smells of rain.")
	_placard(foyer, Vector3(-14.9, 1.6, 33), 90.0, "II", "The Gallery Ramp", "Acq. No. 003\nGallery",
		"The ramp was built for a procession that was never scheduled. Its handrail was removed for conservation. Conservators have not agreed what conservation required, or who signed the form.")


# --- Auditorium: the flooded hall, the brass, the chord, the cadence, La Sirena, the sink well -

func _build_auditorium(areas: Node3D) -> void:
	var aud := _group(areas, "Auditorium")
	var geo := _group(aud, "Geometry")
	var walk := _mat("marble_teal")
	var wall := _mat("damask_ox")
	# floor, 30 m wide, from z = 16 (the foyer threshold) to z = -30 (the stage)
	_box(geo, Vector3(30, 1, 46), Vector3(0, -0.5, -7), walk)
	# west wall, with the opening to the orchestra pit at z -14..-6
	_box(geo, Vector3(1, 14, 16), Vector3(-15.5, 7, -22), wall)
	_box(geo, Vector3(1, 14, 22), Vector3(-15.5, 7, 5), wall)
	_box(geo, Vector3(1, 14, 46), Vector3(15.5, 7, -7), wall)
	# the back wall, opened in the middle: the passage to the dome is x -3..3, up to y 9
	_box(geo, Vector3(12, 14, 1), Vector3(-9, 7, -30.5), wall)
	_box(geo, Vector3(12, 14, 1), Vector3(9, 7, -30.5), wall)
	_box(geo, Vector3(6, 5, 1), Vector3(0, 11.5, -30.5), wall)
	# the stage lip: a low step the player can walk over
	_box(geo, Vector3(30, 0.6, 2), Vector3(0, 0.3, -22), walk)
	_build_instruments(aud)
	_build_duet(aud)
	_placard(aud, Vector3(-12, 1.4, 12), 90.0, "III", "The Flooded Auditorium", "Acq. No. 003\nHall",
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
	# a sink well under the glass: draws you down through its footprint (a flavour trap, off the route)
	var well := _instrument("", "note_cello", &"sink_low", &"sink", Vector3(0, 0, -15))
	well.radius = 3.0
	well.height = 3.0
	well.strength = 14.0
	root.add_child(well)


## La Sirena's stage: three bowls (G, E, C) to answer with, the duet cue, the duet checkpoint.
func _build_duet(aud: Node3D) -> void:
	var stage := _group(aud, "Stage")
	var duet_bowls := [[Vector3(-9, 0, -24), &"g"], [Vector3(9, 0, -24), &"e"], [Vector3(0, 0, -28.5), &"c"]]
	for d: Array in duet_bowls:
		var b := _instrument("glass_bowls", "note_glass", d[1], &"lift", d[0])
		b.name = "Duet_" + String(d[1])
		b.pitch = DUET_PITCH[d[1]]
		b.strength = 22.0
		stage.add_child(b)
		b.struck.connect(func(_n: Node3D) -> void: _duet_answer(d[1]))
	_sung = load(AUDIO + "note_sirena.ogg")
	var cue := TriggerZone.make_box(Vector3(30, 3, 3), false)
	cue.position = Vector3(0, 1.5, -19)
	cue.triggered.connect(_duet_cue)
	stage.add_child(cue)
	_placard(stage, Vector3(-13, 1.4, -27), 90.0, "IX", "La Sirena", "Acq. No. 003\nStage",
		"She sang the chorus from this stage and was never paid for it. The score records two dynamics only, loud and soft, and the orchestra played both as a single note.")


# --- Orchestra pit: down the ramp at the west wall. Two pipes lift you onto the gantry together ---

func _build_pit(areas: Node3D) -> void:
	var pit := _group(areas, "OrchestraPit")
	var geo := _group(pit, "Geometry")
	var walk := _mat("boards")
	var wall := _mat("ebony")
	# pit floor, 3 m below the auditorium, x -32..-16, z -20..0
	_box(geo, Vector3(16, 1, 20), Vector3(-24, -3.5, -10), walk)
	_box(geo, Vector3(1, 14, 20), Vector3(-32.5, 4, -10), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(-24, 4, -20.5), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(-24, 4, 0.5), wall)
	# the ramp down from the auditorium floor: 6.7 m long, 3 m drop, 8 m wide
	var len_ := sqrt(36.0 + 9.0)
	var a := atan2(3.0, 6.0)
	var ramp_body := StaticBody3D.new()
	ramp_body.name = "PitRamp"
	ramp_body.position = Vector3(-18.5 + 0.2 * sin(a), -1.5 - 0.2 * cos(a), -10)
	ramp_body.rotation.z = a
	geo.add_child(ramp_body)
	_slab(ramp_body, Vector3(len_, 0.4, 8), walk)
	# the loft's west edge over the pit of the corridor's end: walls where the floor is open
	_box(geo, Vector3(1, 14, 8), Vector3(45.5, 7, 33), wall)
	_box(geo, Vector3(1, 14, 4), Vector3(45.5, 7, 44), wall)
	# the gantry: a platform reached only by lifting on both pipes at once
	# kept clear of the ramp (z -14..-6): the ramp would otherwise pass through the block
	_box(geo, Vector3(8, GANTRY_TOP + 3, 5), Vector3(-22, (GANTRY_TOP - 3) * 0.5, -17), walk).name = "Gantry"
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
	_placard(pit, Vector3(-22, -1.16, -0.12), 180.0, "IV", "The Orchestra Pit", "Acq. No. 003\nUnder-stage",
		"Musicians descended here before each performance. The records show the pit was dry for the entire run, although the flood reports list it as the first room to fill.")
	_placard(pit, Vector3(-31.87, -1.16, -14.0), 90.0, "V", "The Gantry", "Acq. No. 003\nTechnical",
		"Technicians reached the gantry by lifting with the pipes. The pipes are documented as silent during the period. The source of the sound is listed as unknown, which is listed as a finding.")


# --- Scored corridor: the gap, the ceiling it flips onto, and the downbeat -------------

func _build_corridor(areas: Node3D) -> void:
	var cor := _group(areas, "ScoredCorridor")
	var geo := _group(cor, "Geometry")
	var walk := _mat("boards")
	var wall := _mat("damask_ox")
	var haz := _mat("ebony")
	# x 15..46, z 36..42, floor at 2.8 m (the gallery height); a 6 m gap sits at x 24..30
	_box(geo, Vector3(9, 2.8, 6), Vector3(19.5, 1.4, 39), walk)
	_box(geo, Vector3(16, 2.8, 6), Vector3(38, 1.4, 39), walk)
	_box(geo, Vector3(31, 14, 1), Vector3(30.5, 7, 35.5), wall)
	_box(geo, Vector3(31, 14, 1), Vector3(30.5, 7, 42.5), wall)
	# the ceiling the player rides upside down during a downbeat, over the gap and its approach
	_box(geo, Vector3(10, 0.4, 6), Vector3(27, 6.0, 39), wall).name = "FlipCeiling"
	# the drop into the gap: hazard floor and a trigger that sends her back to the corridor checkpoint
	_box(geo, Vector3(8, 1, 6), Vector3(27, -2.5, 39), haz).name = "GapFloor"
	var drop := TriggerZone.make_box(Vector3(8, 2, 6), false)
	drop.position = Vector3(27, -1, 39)
	drop.triggered.connect(func(_p: Player) -> void: Game.respawn())
	cor.add_child(drop)
	SongMode.flip_box = AABB(Vector3(22, 0, 36), Vector3(10, 8, 6))
	_placard(cor, Vector3(18, 4.2, 36.05), 0.0, "VI", "The Scored Corridor", "Acq. No. 003\nPassage",
		"Gravity here reverses on the downbeat, as composed. The score marks each reversal with a rest, which is the only part of the score the audience is said to remember.")


# --- Fly-loft: the tuning-fork statue and a loft organ, reached through the corridor ----------

func _build_fly_loft(areas: Node3D) -> void:
	var loft := _group(areas, "FlyLoft")
	var geo := _group(loft, "Geometry")
	var walk := _mat("boards")
	var wall := _mat("ebony")
	_box(geo, Vector3(16, 2.8, 16), Vector3(54, 1.4, 38), walk)
	_box(geo, Vector3(1, 14, 18), Vector3(62.5, 7, 38), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(54, 7, 46.5), wall)
	_box(geo, Vector3(16, 14, 1), Vector3(54, 7, 29.5), wall)
	var root := _group(loft, "Instruments")
	# the statue: a tall column that rings a fork note when struck
	var statue := _instrument("", "fork_strike", &"fork", &"lift", Vector3(56, 2.8, 40))
	statue.name = "TuningForkStatue"
	statue.add_child(_model("fork_statue", Vector3.ZERO))
	root.add_child(statue)
	# the loft organ: a lift that sounds on its own note
	var organ := _instrument("pipes", "note_organ_g", &"loft_organ", &"lift", Vector3(48, 2.8, 32))
	root.add_child(organ)
	_provenance(loft, "tuning_fork", Vector3(61, 2.8, 31))
	_placard(loft, Vector3(52, 4.2, 30.6), 0.0, "VII", "The Fly-Loft", "Acq. No. 003\nRigging",
		"Stagehands stored the flown scenery here until it was sold. The inventory lists four drops. Three were found, and the fourth is said to have been requested by the chorus.")
	_placard(loft, Vector3(56, 4.2, 41.4), 180.0, "VIII", "The Tuning Fork", "Acq. No. 003\nStatue",
		"A fork sets the pitch for the whole orchestra. The statue beside it is inscribed with the note A. The inscription has been corrected twice, and the correction was signed by the statue.")


# --- Dome: the rotunda, the audience, the chandelier, and the heist's chord route out ---------

func _build_dome(areas: Node3D) -> void:
	var dome := _group(areas, "Dome")
	var geo := _group(dome, "Geometry")
	var walk := _mat("marble_teal")
	var wall := _mat("damask_ox")
	var c := DOME_CENTRE
	# rotunda floor, x -12..12, z -62..-30, level with the auditorium floor
	_box(geo, Vector3(24, 1, 32), Vector3(c.x, -0.5, -46), walk)
	_box(geo, Vector3(1, 16, 32), Vector3(-12.5, 8, -46), wall)
	_box(geo, Vector3(1, 16, 32), Vector3(12.5, 8, -46), wall)
	_box(geo, Vector3(26, 16, 1), Vector3(0, 8, -62.5), wall)
	_box(geo, Vector3(24, 0.5, 32), Vector3(0, 16.25, -46), wall).name = "Lid"
	# the audience: twelve seated figures ringed around the chandelier, heads free to turn
	var audience := _group(dome, "Audience")
	for i: int in 12:
		var a := deg_to_rad(15.0 + 30.0 * i)
		var fig := Node3D.new()
		fig.name = "Figure%02d" % i
		fig.position = c + Vector3(sin(a) * 8.0, 0.0, cos(a) * 8.0)
		fig.rotation.y = a + PI  # the model faces +Z; turn it to the centre
		audience.add_child(fig)
		var body := _model("figure", Vector3.ZERO)
		body.add_child(_model("seat", Vector3.ZERO))
		fig.add_child(body)
		var head := Node3D.new()
		head.position.y = 1.55
		fig.add_child(head)
		# look_at aims -Z; the modelled face looks +Z, so it is turned within the pivot
		var skull := _model("figure_head", Vector3.ZERO)
		skull.rotation.y = PI
		head.add_child(skull)
		_heads.append(head)
	# the cathedral chandelier: a ring of light hung from the dome, lowered during the silent fall
	_chandelier = Node3D.new()
	_chandelier.name = "Chandelier"
	_chandelier.position = Vector3(c.x, CHANDELIER_TOP, c.z)
	dome.add_child(_chandelier)
	_chandelier.add_child(_model("chandelier", Vector3(0, 5.0, 0)))
	_chandelier.add_child(_model("chain", Vector3(0, 31.0, 0)))
	var glow := OmniLight3D.new()
	glow.position = Vector3(0, 2.6, 0)
	glow.light_color = Color("ffc98a")
	glow.light_energy = 6.0
	glow.omni_range = 18.0
	glow.omni_attenuation = 1.4
	glow.light_volumetric_fog_energy = 2.0
	glow.shadow_enabled = false  # an omni shadow re-renders the whole rotunda six times; the crystals read without it
	_chandelier.add_child(glow)
	# the heist's chord route: two pipes that must sound together, a sink between them, and a ledge
	var root := _group(dome, "Instruments")
	for p: Array in [[Vector3(-2, 0, -56), &"heist_a", "note_organ_c"], [Vector3(2, 0, -56), &"heist_b", "note_organ_g"]]:
		var col := _instrument("pipes", p[2], p[1], &"lift", p[0])
		col.name = "Heist_" + String(p[1])
		col.radius = 2.6
		col.height = 8.0
		col.strength = 26.0
		root.add_child(col)
	var sink := _instrument("", "note_cello", &"dome_sink", &"sink", Vector3(0, 0, -54))
	sink.radius = 2.2
	sink.height = 3.0
	sink.strength = 14.0
	root.add_child(sink)
	_box(geo, Vector3(6, 1, 4), Vector3(0, 7.5, -60), walk).name = "Ledge"
	# tall enough to catch the chord's lift, which carries her to about y 14 before gravity is gone
	var exit_zone := TriggerZone.make_box(Vector3(6, 10, 4), false)
	exit_zone.position = Vector3(0, 12, -60)
	exit_zone.triggered.connect(_on_exit_zone)
	dome.add_child(exit_zone)
	_placard(dome, Vector3(-10, 1.4, -40), 0.0, "X", "The Dome", "Acq. No. 003\nRotunda",
		"The rotunda was built to hold the audience after the performance. The chandelier was hung for the applause, which was cancelled. Its rigging was never inspected by anyone.")
	_placard(dome, Vector3(-10.5, 1.4, -52), 90.0, "XI", "The Audience", "Acq. No. 003\nSeating",
		"Twelve figures were seated for the fall. Their heads are fixed in the direction of the chandelier, as the catalogue records, and they have not been moved since. None were identified.")
	_placard(dome, Vector3(-6, 1.4, -61.2), 0.0, "XII", "The Exit", "Acq. No. 003\nLedge",
		"The only exit is a ledge, and the ledge is reached by the chord. Visitors who reached it were asked to sign the book. The book was lost in the flood.")


func _build_checkpoints() -> void:
	_checkpoint(&"start", Vector3(0, 0.5, 26))
	_checkpoint(&"gallery", Vector3(0, 3.3, 37))
	_checkpoint(&"auditorium", Vector3(0, 0.5, 10))
	_checkpoint(&"pit", Vector3(-26, -2.5, -5))
	_checkpoint(&"corridor", Vector3(17, 3.3, 39))
	_checkpoint(&"flyloft", Vector3(50, 3.3, 36))
	_checkpoint(&"stage", Vector3(0, 0.5, -10))
	_checkpoint(&"duet", Vector3(0, 0.9, -19))


func _checkpoint(id: StringName, pos: Vector3) -> void:
	var cp := Checkpoint.new()
	cp.id = id
	cp.position = pos
	add_child(cp)


## Camera marks for capture (tests/shots.tscn): twelve Marker3D under ShotMarks, in group shot_marks,
## each looking down its -Z. Two per area, three in the auditorium, one in the fly-loft.
func _build_marks() -> void:
	var holder := _group(self, "ShotMarks")
	var marks := [
		["foyer_stair", Vector3(6, 1.7, 17.5), Vector3(-2, 3.6, 34)],
		["foyer_gallery", Vector3(-10, 4.7, 40), Vector3(5, 2.0, 18)],
		["auditorium_hall", Vector3(0, 2.2, 13), Vector3(0, 5.5, -21)],
		["auditorium_tiers", Vector3(10, 1.8, -10), Vector3(-15, 7.0, 4)],
		["auditorium_stage", Vector3(5, 2.0, -16.5), Vector3(0, 4.5, -27)],
		["pit_gantry", Vector3(-17, -1.2, -2), Vector3(-26, -1.0, -16)],
		["pit_pipes", Vector3(-18, -0.8, -16), Vector3(-30, -1.5, -6)],
		["corridor_gap", Vector3(17, 4.5, 39), Vector3(40, 4.0, 39)],
		["corridor_ceiling", Vector3(19, 3.4, 39), Vector3(28, 6.2, 39)],
		["flyloft", Vector3(49, 3.6, 32), Vector3(56, 9.0, 44)],
		["dome_ring", Vector3(0, 3.5, -33), Vector3(0, 6.0, -50)],
		["dome_chandelier", Vector3(6, 1.6, -42), Vector3(-1, 11.0, -48)],
	]
	for m: Array in marks:
		var mk := Marker3D.new()
		mk.name = m[0]
		mk.add_to_group(&"shot_marks")
		holder.add_child(mk)
		mk.look_at_from_position(m[1], m[2], Vector3.UP)


func _build_fragment() -> void:
	_fragment_spot = Node3D.new()
	_fragment_spot.name = "FragmentSpot"
	_fragment_spot.position = Vector3(0, 0.6, -26)
	find_child("Auditorium", true, false).add_child(_fragment_spot)
	var shard := _model("fragment", Vector3.ZERO)
	_fragment_spot.add_child(shard)
	var halo := OmniLight3D.new()
	halo.light_color = Color("7fffe0")
	halo.light_energy = 2.5
	halo.omni_range = 5.0
	shard.add_child(halo)
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
	_fragment.picked.connect(_start_heist)
	_update_fragment()


## The fragment waits on the stage from the moment La Sirena's last note ends.
func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.is_done(&"duet") and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_fragment_spot.visible = ready


func _on_struck(note: StringName) -> void:
	_strikes.append(note)
	if _strikes.size() > 3:
		_strikes.remove_at(0)
	if _strikes == [&"g", &"e", &"c"] and not Quest.is_done(&"cadence"):
		complete_step(&"cadence", &"cadence")


# --- La Sirena's duet ---------------------------------------------------------------------

func _duet_cue(_p: Player) -> void:
	if _duet_on or Quest.is_done(&"duet") or not Quest.is_done(&"cadence"):
		return
	_run_duet()


func _run_duet() -> void:
	_duet_on = true
	toast("La Sirena takes the stage. Answer her in the order she sings.", "The Duet")
	for r: int in DUET_ROUNDS.size():
		_duet_round = r
		var ok := false
		while not ok:
			ok = await _duet_play(r)
			if not ok:
				toast("She stops, and the round begins again.", "The Duet")
				await get_tree().create_timer(2.0).timeout
		complete_step(&"duet", StringName("round%d" % (r + 1)))
	_duet_on = false
	_begin_fall(true)


## One round: each phrase sung, then answered inside its window. Returns false on a wrong or late note.
func _duet_play(r: int) -> bool:
	for phrase: Dictionary in DUET_ROUNDS[r]:
		var notes: Array = phrase["notes"]
		SongMode.duet_accel = -22.0 if phrase["dyn"] == &"cres" else 9.8
		SongMode.duet_box = _duet_box
		for n: StringName in notes:
			Audio.sfx(_sung, Vector3(0, 2.5, -26), -6.0, 0.4, DUET_PITCH[n])
			await get_tree().create_timer(SING_NOTE).timeout
		SongMode.duet_accel = 0.0
		SongMode.duet_box = AABB()
		_duet_expect = notes
		_duet_idx = 0
		_duet_wrong = false
		_duet_left = DUET_WINDOW[r]
		_duet_open = true
		while _duet_left > 0.0 and _duet_idx < notes.size() and not _duet_wrong:
			await get_tree().process_frame
		_duet_open = false
		if _duet_wrong or _duet_idx < notes.size():
			return false
	return true


## Called by the stage bowls. Only counts while a window is open.
func _duet_answer(note: StringName) -> void:
	if not _duet_open:
		return
	if _duet_idx < _duet_expect.size() and note == _duet_expect[_duet_idx]:
		_duet_idx += 1
	else:
		_duet_wrong = true


## The silent chandelier fall: music cut, instruments silent, heads turning, the player free to move.
func _begin_fall(announce: bool) -> void:
	_fall_on = true
	Audio.stop_music(2.0)
	for inst: Node in get_tree().get_nodes_in_group(Instrument.GROUP):
		(inst as Instrument).timer = 0.0
	SongMode.duet_box = AABB()
	SongMode.duet_accel = 0.0
	_update_fragment()
	if announce:
		toast("The music stops. The chandelier begins its ninety seconds.", "The Dome")
	var t := create_tween()
	t.tween_property(_chandelier, "position:y", CHANDELIER_LOW, FALL_TIME).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	t.finished.connect(func() -> void:
		_fall_on = false
		complete_step(&"fall", &"fall"))


# --- The heist: the fragment is taken, the hall lets go of her, she climbs out on the chord ----

func _start_heist() -> void:
	# gravity lets go in stages: half for three seconds, then none; the chord lifts carry her out
	Game.player.gravity_vector = Vector3(0, gravity.y * 0.5, 0)
	toast("The last note has gone and the hall lets go of her.", "The Heist")
	await get_tree().create_timer(3.0).timeout
	Game.player.gravity_vector = Vector3.ZERO


func _on_exit_zone(_p: Player) -> void:
	if not Quest.has_fragment(wing_id):
		return
	if not Quest.is_done(&"fall"):
		toast("The chandelier is still coming down. The exit waits for the hall to go quiet.", "The Exit")
		return
	finish()


# --- test accessors (read-only) -----------------------------------------------------------

func duet_round() -> int:
	return _duet_round


func duet_window_open() -> bool:
	return _duet_open


func duet_expected() -> Array:
	return _duet_expect.duplicate()


func fall_running() -> bool:
	return _fall_on


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
	var mesh := _model({"score": "prov_score", "baton": "prov_baton", "tuning_fork": "prov_fork"}[id], Vector3.ZERO)
	var lamp := OmniLight3D.new()  # a small warm vitrine light, so the eye finds it
	lamp.position = Vector3(0, 1.2, 0.3)
	lamp.light_color = Color("ffd6a0")
	lamp.light_energy = 1.2
	lamp.omni_range = 2.5
	mesh.add_child(lamp)
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
	pl.set_label(Placard.fields_from_legacy(title, catalog, body), false)  # catalog: "Acq. No. 003\nEntrance"
	pl.position = pos
	pl.rotation_degrees.y = yaw_deg
	parent.add_child(pl)


func _group(parent: Node3D, name_: String) -> Node3D:
	var n := Node3D.new()
	n.name = name_
	parent.add_child(n)
	return n


func _mat(name_: String) -> Material:
	return MaterialLib.lookup(name_, MAT_DIRS)


func _instrument(model: String, sound_name: String, note: StringName, kind_: StringName, pos: Vector3) -> Instrument:
	var inst := Instrument.new()
	inst.name = "Instrument_" + String(note)
	inst.note_id = note
	inst.kind = kind_
	inst.position = pos
	inst.sound = load(AUDIO + sound_name + ".ogg")
	if model != "":
		inst.add_child(_model(model, Vector3.ZERO))
	return inst


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	parent.add_child(body)
	_slab(body, size, mat)
	return body


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
