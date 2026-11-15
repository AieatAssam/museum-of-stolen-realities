extends Wing
## The Chitin Court (Acquisition No. 340). Rule: Silkspinning (silk_mode.gd, strand.gd).
## Greybox: geometry is built here as flat-coloured boxes under Areas/<Area>/. Colours by function:
## walkable 6b7f8a, structure 39424a, interactive e0c040, hazard c0392b, goal 2ecc71.
##
## Route (x east, y up, z south):
##   OuterGate (y 0) -> one swing -> SilkDistricts (y -3): usher (pluck), light-well (tightrope),
##   moth (pluck calls an anchor, swing to the perch) -> HiveShaft: the gate course's three-swing
##   chain to a balcony (y -7), a zip woven mid-fall to the foundry (y -28) -> Foundry: clockwork
##   anchor over a channel (y -31), the guild door and the vault (resonance locks) -> TapestryGallery
##   -> GeneralArena (three phrases, y -31 to -42) -> processional stair -> CoronationHall at the
##   shaft's base (y -70): the reveal, the dais lock, the fragment -> heist: lifts and a cut line
##   up the shaft to the rim (y -3) -> finish().
## Every swing gap copies the gate course's offsets (tests/swing_course.gd): anchor 6 m past the
## edge and 10 m up; a single swing lands 13 m+ out and 3 m down, a chain of n anchors 13 m apart
## lands 13(n-1)+9 m+ out and 4 m down.

const SilkMode := preload("res://wings/chitin/silk_mode.gd")
const Strand := preload("res://wings/chitin/strand.gd")
const AUDIO := "res://wings/chitin/audio/"
const ACQ := "Acq. No. 340"
const HZ := 120.0

const C_WALK := Color("6b7f8a")
const C_WALL := Color("39424a")
const C_INTERACT := Color("e0c040")
const C_HAZARD := Color("c0392b")
const C_GOAL := Color("2ecc71")
const C_AMBER := Color("ffb03a")

const GUILD_STANDARD := 8.0
const QUEENS_SPAN := 6.0
const LOCK_TOL := 0.5
const PHRASE_SECS := [12.0, 16.0, 20.0]
const KEY_TICKS := 60          # on the key's line this long turns it (0.5 s)
const CUT_ON_TICKS := 540      # heist: the courtiers' cut line, 4.5 s up ...
const CUT_OFF_TICKS := 180     # ... 1.5 s cut
const BLINK_EVERY := 9.0

var silk: MovementMode
var _mat := {}
var _sfx := {}

# districts
var _usher: Node3D
var _usher_home := Vector3(27.0, -1.9, 0.0)
var _usher_away_t := 0.0
var _harp_usher: Node
var _harp_moth: Node
var _moth: Node3D
# foundry
var _clock_anchor: Node3D
var _clock_t := 0.0
var _guild_door: Node3D
var _guild_pegs: Array[Node3D] = []
var _vault_door: Node3D
var _vault_pegs: Array[Node3D] = []
# arena
var _arena_segs: Array = []           # Array of Array[Node3D], one per phrase
var _keys: Array[Node3D] = []
var _islands: Array[AABB] = []
var _arena_on := false
var _phrase := -1
var _phrase_tick := 0
var _key_ticks := 0
var _key_turned := [false, false, false]
var _gallery_gate: Node3D
var _dais_gate: Node3D
var _general: Node3D
# hall
var _curtain: Node3D
var _dome_mat: StandardMaterial3D
var _revealed := false
var _blink_t := 0.0
var _court_figs: Array[Node3D] = []
var _hall_pegs: Array[Node3D] = []
var _cage: Node3D
var _fragment: Pickup
var _fragment_spot: Node3D
# heist
var _heist_on := false
var _lifts: Array[Dictionary] = []    # {"node", "path", "speed", "i", "run"}
var _cut_anchor: Node3D
var _cut_tick := 0
var _falling := false


# --- contract ------------------------------------------------------------------------------

func objectives() -> Array[Dictionary]:
	return [
		{"id": "gate", "title": "Cross the molted gate", "steps": [{"id": "swing", "title": "Swing over the gate's ditch"}],
			"hint": "Aim at a hook and press primary to fire a line. Press it again near the top of the swing to let go."},
		{"id": "districts", "title": "Pass through the silk districts",
			"steps": [{"id": "usher", "title": "Get past the usher"}, {"id": "tightrope", "title": "Cross the light-well"}],
			"hint": "Secondary at one peg, then another, weaves a line. Secondary at a line plucks it."},
		{"id": "shaft", "title": "Descend the hive shaft",
			"steps": [{"id": "chain", "title": "Swing down to the balcony"}, {"id": "zip", "title": "Reach the foundry"}],
			"hint": "A line woven on a slope can be caught while falling, and ridden down."},
		{"id": "foundry", "title": "Open the locksmiths' guild",
			"steps": [{"id": "clockwork", "title": "Cross the foundry channel"}, {"id": "door", "title": "Open the guild door"}],
			"hint": "Guild locks answer a plucked line of the right length."},
		{"id": "general", "title": "Out-swing the Locksmith General",
			"steps": [{"id": "key1", "title": "Turn the first key"}, {"id": "key2", "title": "Turn the second key"}, {"id": "key3", "title": "Turn the third key"}],
			"hint": "Hang from each key she offers and swing on it before the space closes."},
		{"id": "court", "title": "Attend the coronation",
			"steps": [{"id": "hall", "title": "Enter the coronation hall"}, {"id": "dais", "title": "Open the dais case"}]},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "bell", "name": "A moth's finger-bell", "line": "Rung once, it calls a moth. The moth has not come since the bell left the court."},
		{"id": "guild_key", "name": "A guild key, cut to six metres", "line": "Cut to the queen's span, which only her tailors ever wrote down."},
		{"id": "tapestry", "name": "A strip of ancestor tapestry", "line": "A hem from an ancestor who was always this way, according to the court."},
	]


func fragment() -> Dictionary:
	return {"name": "A fragment of the Chitin Court", "line": "Taken from the coronation dais while the court was still pretending. They have stopped."}


func register_modes(player: Player) -> void:
	silk = SilkMode.new()
	player.add_mode(&"silk", silk)
	silk.connect(&"fired", func(a: Node3D) -> void: Audio.sfx(_sfx["fire"], a.global_position, -4.0))
	silk.connect(&"released", func(top: bool) -> void: Audio.sfx(_sfx["release"], null, -6.0 if not top else -2.0, 0.0, 1.25 if top else 1.0))
	silk.connect(&"woven", func(s: Node) -> void: Audio.sfx(_sfx["fire"], s.global_position, -6.0, 0.2, 0.8))
	silk.connect(&"plucked", _on_plucked)


func on_enter(first_time: bool) -> void:
	if first_time:
		await Cinematics.play([{"card": "The Chitin Court", "sub": "Acquisition No. 340", "t": 3.0, "style": "display"}])
		toast("The court is at rest. Visitors travel by line.")


func on_exit() -> void:
	_arena_on = false
	_heist_on = false


func save_state() -> Dictionary:
	return {"moth": _moth != null and _moth.is_in_group(&"silk_anchors"), "vault": _vault_door != null and not _vault_door.visible}


func load_state(_state: Dictionary) -> void:
	pass  # read back through recall() in _ready


# --- build ---------------------------------------------------------------------------------

func _ready() -> void:
	_sfx = {"fire": load(AUDIO + "line_fire.ogg"), "release": load(AUDIO + "swing_release.ogg"), "pluck": load(AUDIO + "pluck.ogg"),
		"blink": load(AUDIO + "eye_blink.ogg"), "stinger": load(AUDIO + "stinger_eye.ogg")}
	_mat = {"walk": _flat(C_WALK), "wall": _flat(C_WALL), "int": _flat(C_INTERACT), "haz": _flat(C_HAZARD), "goal": _flat(C_GOAL),
		"hi": _glow(Color(1.0, 0.85, 0.4, 0.55), 3.0, true), "membrane": _glow(Color("6a2a10"), 0.4, false)}
	_build_environment()
	var areas := _group(self, "Areas")
	_build_gate(_group(areas, "OuterGate"))
	_build_districts(_group(areas, "SilkDistricts"))
	_build_shaft(_group(areas, "HiveShaft"))
	_build_foundry(_group(areas, "Foundry"))
	_build_gallery(_group(areas, "TapestryGallery"))
	_build_arena(_group(areas, "GeneralArena"))
	_build_hall(_group(areas, "CoronationHall"))
	_build_heist(_group(areas, "Heist"))
	_build_checkpoints()
	_build_marks()
	_restore()


func _build_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("1a0d04")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("8a5a2a")
	env.ambient_light_energy = 0.55
	env.fog_enabled = true
	env.fog_light_color = Color("3a2210")
	env.fog_density = 0.006
	env.glow_enabled = true
	env.glow_bloom = 0.15
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	Quality.apply(env)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.light_color = Color("ffc070")
	sun.light_energy = 0.6
	sun.rotation_degrees = Vector3(-70, 20, 0)
	add_child(sun)


# --- Outer gate: arrival, the molted gate, the first swing -----------------------------------

func _build_gate(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	_ledge(geo, Vector3(-26, -1, -10), Vector3(0, 0, 10), _mat["walk"])
	_ledge(geo, Vector3(-27, -1, -10), Vector3(-26, 6, 10), _mat["wall"])
	_ledge(geo, Vector3(-26, -1, -11), Vector3(0, 6, -10), _mat["wall"])
	_ledge(geo, Vector3(-26, -1, 10), Vector3(0, 6, 11), _mat["wall"])
	# the molted gate: the shed shell of the first doorkeeper, two halves and a lintel
	_ledge(geo, Vector3(-13, 0, -6), Vector3(-11, 7, -3), _mat["membrane"])
	_ledge(geo, Vector3(-13, 0, 3), Vector3(-11, 7, 6), _mat["membrane"])
	_ledge(geo, Vector3(-13, 7, -6), Vector3(-11, 9, 6), _mat["membrane"])
	_anchor(area, Vector3(6, 10, 0))
	_abyss(area, Vector3(0, -14, -16), Vector3(13, -10, 16))
	_zone(area, Vector3(13, -3, -14), Vector3(28, 0, 14), func() -> void: complete_step(&"gate", &"swing"))
	_placard(area, Vector3(-11.9, 1.4, -2.7), Vector3(0, 0, 1), "The molted gate", "Shed in the present reign", "Chitin, one hinge",
		"The court's outer gate is the skin its first doorkeeper grew out of. He was promoted inside it. Visitors pass through him. The hinge is original. His whereabouts are not recorded.")
	_placard(area, Vector3(-2, 1.4, -9.9), Vector3(0, 0, 1), "Silkspinning", "Customary", "Wrist spinneret, silk",
		"Courtiers travel by line. One line swings, two lines make a road, and a plucked line is a word. Letting go at the top of a swing is good manners. Falling is considered nothing at all.")


# --- Silk districts: the usher, the light-well tightrope, the moth and the perch ---------------

func _build_districts(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	var wall: Material = _mat["wall"]
	_ledge(geo, Vector3(13, -4, -14), Vector3(40, -3, 14), walk)
	_ledge(geo, Vector3(52, -4, -14), Vector3(80, -3, 14), walk)
	for z: float in [-14.0, 14.0]:
		_ledge(geo, Vector3(13, -3, z - 0.5 if z < 0 else z), Vector3(80, 6, z if z < 0 else z + 0.5), wall)
	# the usher's wall at x 28, a door 3 m wide and 3 m tall
	_ledge(geo, Vector3(27.5, -3, -14), Vector3(28.5, 6, -1.5), wall)
	_ledge(geo, Vector3(27.5, -3, 1.5), Vector3(28.5, 6, 14), wall)
	_ledge(geo, Vector3(27.5, 0, -1.5), Vector3(28.5, 6, 1.5), wall)
	_usher = _box(area, Vector3(1.2, 2.2, 3.0), _usher_home, _mat["haz"])
	_usher.name = "Usher"
	_harp_usher = Strand.create(area, Vector3(18, -1.2, 13.3), Vector3(26, -1.2, 13.3))
	_harp_usher.name = "UsherHarp"
	_zone(area, Vector3(29, -3, -3), Vector3(32, 0, 3), func() -> void: complete_step(&"districts", &"usher"))
	# light-well W1 (x 40..52): pegs on both lips, a line woven between them is the only way over
	_peg(area, Vector3(40.3, -2.95, 0))
	_peg(area, Vector3(51.7, -2.95, 0))
	_abyss(area, Vector3(40, -12, -14), Vector3(52, -8, 14))
	_zone(area, Vector3(53, -3, -14), Vector3(56, 0, 14), func() -> void: complete_step(&"districts", &"tightrope"))
	# the moth: a pre-strung line on the south wall calls it; it hangs above the perch approach
	_harp_moth = Strand.create(area, Vector3(56, -1.2, -13.3), Vector3(64, -1.2, -13.3))
	_harp_moth.name = "MothHarp"
	_moth = _anchor(area, Vector3(66, 9, -6), false)
	_moth.name = "Moth"
	_ledge(geo, Vector3(74, -4, -10), Vector3(79, 0, -2), walk)  # the high perch, 3 m up
	_provenance(area, "bell", Vector3(77.5, 0, -8.5))
	_placard(area, Vector3(16, -1.6, -13.4), Vector3(0, 0, 1), "The tailors' quarter", "Working district", "Silk, wax, tape",
		"Every garment at court is cut to the queen's span, which the tailors record as six metres, wrist to wrist. No garment has been delivered. The tailors are confident she will grow into them.")
	_placard(area, Vector3(26.9, -1.6, -3.5), Vector3(-1, 0, 0), "The usher", "In post", "Beetle, livery",
		"The usher admits no one without an appointment and keeps no appointment book. He is susceptible to music. Any line plucked nearby is, to him, the queen calling. He has never once checked.")
	_placard(area, Vector3(38, -1.6, -13.4), Vector3(0, 0, 1), "Light-wells", "Structural", "Absence",
		"The districts are lit by wells that open onto lesser hive shafts. Residents cross on lines woven between the pegs. The pegs are counted every morning. The residents are counted when convenient.")
	_placard(area, Vector3(54, -1.6, -13.4), Vector3(0, 0, 1), "Court moths", "Domesticated", "Moth, brass",
		"A moth answers a plucked line and holds still in the air for anyone who needs to hang from something. Each wears a finger-bell. One bell was lost on a high perch.")


# --- Hive shaft: the gate course chain, the balcony, the zip woven mid-fall ---------------------

func _build_shaft(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var wall: Material = _mat["wall"]
	# the shaft: x 80..150, z -30..14, from the hall floor (y -70) open to the amber sky
	_ledge(geo, Vector3(79.5, -70, -30), Vector3(80.5, -4, -13.5), wall)
	_ledge(geo, Vector3(79.5, -66.5, -13.5), Vector3(80.5, -4, -10.5), wall)
	_ledge(geo, Vector3(79.5, -70, -10.5), Vector3(80.5, -4, 14), wall)
	_ledge(geo, Vector3(150, -70, -40), Vector3(151, 20, 40), wall)
	_ledge(geo, Vector3(80, -70, -31), Vector3(150, -4, -30), wall)
	_ledge(geo, Vector3(80, -70, 14), Vector3(95, -28, 15), wall)
	# the chain: the gate course offset to the district rim (x 80, y -3)
	for x: float in [86.0, 99.0, 112.0]:
		_anchor(area, Vector3(x, 7, 0))
	_ledge(geo, Vector3(115, -8, -8), Vector3(130, -7, 8), _mat["walk"])  # the balcony
	_zone(area, Vector3(115, -7, -8), Vector3(130, -4, 8), func() -> void: complete_step(&"shaft", &"chain"))
	# the zip: two hooks off the balcony's east lip, a 22 m line sloping down to the foundry
	_anchor(area, Vector3(132, -10.5, 0))
	_anchor(area, Vector3(131.6, -24, 19))
	# the net: below every descent route, above the hall
	_abyss(area, Vector3(80, -44, -30), Vector3(150, -40, 14))
	# the sky: an amber dome over the shaft (it is an eye)
	var dome := MeshInstance3D.new()
	dome.name = "AmberSky"
	var sm := SphereMesh.new()
	sm.radius = 60.0
	sm.height = 60.0
	sm.is_hemisphere = true
	sm.radial_segments = 48
	sm.rings = 16
	dome.mesh = sm
	_dome_mat = _glow(C_AMBER, 1.6, false)
	_dome_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	dome.material_override = _dome_mat
	dome.position = Vector3(115, 20, -8)
	area.add_child(dome)
	_placard(area, Vector3(78.5, -1.6, 13.4), Vector3(0, 0, -1), "The abyssal hive shaft", "Unmeasured", "Air, amber light",
		"The shaft falls from the districts to the coronation hall. Its depth was last surveyed by a courier who swung three times without touching anything. Court records describe the light above as the sky.")


# --- Foundry: the clockwork anchor, the guild door, the vault ------------------------------------

func _build_foundry(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	var wall: Material = _mat["wall"]
	_ledge(geo, Vector3(95, -70, 14), Vector3(160, -28, 50), walk)  # also the shaft's north wall
	_ledge(geo, Vector3(95, -32, 63), Vector3(160, -31, 100), walk)
	_zone(area, Vector3(95, -28, 14), Vector3(160, -25, 48), func() -> void: complete_step(&"shaft", &"zip"))
	_ledge(geo, Vector3(94, -32, 50), Vector3(95, -10, 88), wall)
	_ledge(geo, Vector3(94, -32, 94), Vector3(95, -10, 100), wall)
	_ledge(geo, Vector3(160, -32, 14), Vector3(161, -10, 100), wall)
	# the channel z 50..63 and the clockwork anchor travelling its track at y -18, z 56
	_abyss(area, Vector3(95, -50, 50), Vector3(160, -46, 63))
	var track := MeshInstance3D.new()
	var tm := BoxMesh.new()
	tm.size = Vector3(30, 0.3, 0.3)
	track.mesh = tm
	track.material_override = wall
	track.position = Vector3(130, -16.5, 56)
	area.add_child(track)
	_clock_anchor = _anchor(area, Vector3(130, -18, 56))
	_clock_anchor.name = "ClockworkAnchor"
	_zone(area, Vector3(95, -31, 63), Vector3(160, -28, 72), func() -> void: complete_step(&"foundry", &"clockwork"))
	# the guild wall at z 80, its door x 126..134
	_ledge(geo, Vector3(95, -31, 80), Vector3(126, -10, 81), wall)
	_ledge(geo, Vector3(134, -31, 80), Vector3(160, -10, 81), wall)
	_ledge(geo, Vector3(126, -26, 80), Vector3(134, -10, 81), wall)
	_guild_door = _box(area, Vector3(8, 5, 0.6), Vector3(130, -28.5, 80.5), _mat["int"])
	_guild_door.name = "GuildDoor"
	for p: Vector3 in [Vector3(110, -30.95, 74), Vector3(114, -30.95, 77), Vector3(118, -30.95, 74), Vector3(122, -30.95, 77)]:
		_guild_pegs.append(_peg(area, p))
	# the vault: x 95..105, z 64..74, door in its north wall x 98..102
	_ledge(geo, Vector3(95, -31, 63.5), Vector3(105, -26, 64), wall)
	_ledge(geo, Vector3(104.5, -31, 64), Vector3(105, -26, 74), wall)
	_ledge(geo, Vector3(95, -31, 73.5), Vector3(98, -26, 74), wall)
	_ledge(geo, Vector3(102, -31, 73.5), Vector3(105, -26, 74), wall)
	_ledge(geo, Vector3(95, -26, 63.5), Vector3(105, -25.5, 74), wall)
	_vault_door = _box(area, Vector3(4, 5, 0.4), Vector3(100, -28.5, 73.8), _mat["int"])
	_vault_door.name = "VaultDoor"
	for p: Vector3 in [Vector3(97, -30.95, 77), Vector3(100, -30.95, 79.5), Vector3(103, -30.95, 77), Vector3(107, -30.95, 79.5)]:
		_vault_pegs.append(_peg(area, p))
	_provenance(area, "guild_key", Vector3(99, -31, 67))
	_placard(area, Vector3(140, -26.6, 49), Vector3(0, 0, -1), "The clockwork foundry", "Running", "Brass, tallow, escapements",
		"Anchors here travel on tracks, so that no one can hang from the same place twice. The founders considered this a security measure. The workers consider it a commute.")
	_placard(area, Vector3(136, -29.6, 79.4), Vector3(0, 0, -1), "The locksmiths' guild", "Chartered", "Resonant brass",
		"Guild doors open to a plucked line of the guild standard, eight metres. Shorter lines sing higher and are refused. Members are asked not to hum near the doors. The Locksmith General is a member.")
	_placard(area, Vector3(103.5, -29.6, 74.3), Vector3(0, 0, 1), "The vault", "Private", "Resonant brass",
		"Tuned to the queen's span.")


# --- Tapestry gallery: the ancestors; no gaps, no falls -----------------------------------------

func _build_gallery(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	var wall: Material = _mat["wall"]
	# the guild hall's west wall (x 95) opens z 88..94 into the gallery, x 60..95, z 82..100
	_ledge(geo, Vector3(60, -32, 81), Vector3(95, -31, 100), walk)
	_ledge(geo, Vector3(60, -31, 80.5), Vector3(95, -22, 81.5), wall)
	_ledge(geo, Vector3(60, -31, 100), Vector3(95, -22, 101), wall)
	# hanging ancestors: membranes on both long walls
	for x: float in [64.0, 70.0, 76.0, 82.0, 88.0]:
		_ledge(geo, Vector3(x, -29.5, 81.5), Vector3(x + 3.0, -23, 81.7), _mat["membrane"])
		_ledge(geo, Vector3(x, -29.5, 99.3), Vector3(x + 3.0, -23, 99.5), _mat["membrane"])
	# a winding post under a ceiling hook: no-fail practice for wraps
	var post := _box(area, Vector3(0.6, 6.0, 0.6), Vector3(84, -28, 91), wall)
	post.add_to_group(&"silk_posts")
	_anchor(area, Vector3(84, -22, 86))
	_provenance(area, "tapestry", Vector3(66, -31, 98))
	_placard(area, Vector3(73, -29.6, 81.6), Vector3(0, 0, 1), "Tapestry-membranes", "Ancestral", "Silk, wing membrane",
		"The tapestries are not pictures of the court's ancestors. They are the ancestors, pressed flat and hung at eye level so that they may continue to attend. They are dusted on feast days.")
	_placard(area, Vector3(67.5, -29.6, 99.2), Vector3(0, 0, -1), "Ancestor, unlabelled", "Before the present reign", "Membrane",
		"This ancestor is missing a strip along the hem. The court maintains that she was always this way. She is consulted on matters of succession and has not yet answered.")


# --- The Locksmith General: three phrases, each a key and a closing space -----------------------

func _build_arena(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	# corridor from the gallery's west wall (x 60, opening z 96..104) to the arena ledge
	_ledge(geo, Vector3(59.5, -31, 81), Vector3(60.5, -22, 96), _mat["wall"])
	_ledge(geo, Vector3(50, -32, 96), Vector3(60, -31, 104), walk)
	_gallery_gate = _box(area, Vector3(0.6, 6, 8), Vector3(50.3, -28, 100), _mat["haz"])
	_gallery_gate.name = "ArenaGate"
	# the arena runs south (-z) from its ledge (z 96..106) to the General's dais
	_ledge(geo, Vector3(30, -32, 96), Vector3(50, -31, 106), walk)
	_islands = [AABB(Vector3(28, -35, 68), Vector3(24, 3, 15)), AABB(Vector3(28, -39, 30), Vector3(24, 3, 16)), AABB(Vector3(25, -43, -20), Vector3(30, 3, 15))]
	_ledge(geo, Vector3(28, -35, 68), Vector3(52, -34, 83), walk)
	_ledge(geo, Vector3(28, -39, 30), Vector3(52, -38, 46), walk)
	_ledge(geo, Vector3(25, -43, -20), Vector3(55, -42, -5), walk)
	_abyss(area, Vector3(15, -60, -25), Vector3(54.5, -52, 96))
	var segs := [[Vector3(40, -21, 90)], [Vector3(40, -24, 62), Vector3(40, -24, 49)], [Vector3(40, -28, 24), Vector3(40, -28, 11), Vector3(40, -28, -2)]]
	for s: Array in segs:
		var seg: Array[Node3D] = []
		for p: Vector3 in s:
			seg.append(_anchor(area, p, false))
		_arena_segs.append(seg)
		var key: Node3D = seg[-1]
		key.name = "Key%d" % _arena_segs.size()
		var bow := MeshInstance3D.new()
		var tm := TorusMesh.new()
		tm.inner_radius = 0.45
		tm.outer_radius = 0.8
		bow.mesh = tm
		bow.material_override = _mat["goal"]
		bow.rotation_degrees.x = 90.0
		bow.name = "Bow"
		key.add_child(bow)
		var shaft := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.25, 4.0, 0.25)
		shaft.mesh = bm
		shaft.material_override = _mat["goal"]
		shaft.position.y = 2.6
		key.add_child(shaft)
		_keys.append(key)
	_zone(area, Vector3(30, -31, 96), Vector3(50, -28, 99.5), _arena_start, false)
	# the General on her dais, and the wall that keeps the stair shut until she is locked
	_general = _group(area, "LocksmithGeneral")
	_general.position = Vector3(40, -42, -16)
	var body := MeshInstance3D.new()
	var cap := CapsuleMesh.new()
	cap.radius = 1.2
	cap.height = 7.0
	body.mesh = cap
	body.material_override = _mat["haz"]
	body.position.y = 3.5
	_general.add_child(body)
	for side: float in [-1.0, 1.0]:
		var limb := MeshInstance3D.new()
		var lm := BoxMesh.new()
		lm.size = Vector3(0.4, 0.4, 5.0)
		limb.mesh = lm
		limb.material_override = _mat["goal"]
		limb.position = Vector3(side * 1.6, 5.0, 2.5)
		limb.name = "Forelimb"
		_general.add_child(limb)
	_dais_gate = _box(area, Vector3(0.6, 4, 3.4), Vector3(55.3, -40, -12), _mat["haz"])
	_dais_gate.name = "StairGate"
	_placard(area, Vector3(32, -29.6, 105.9), Vector3(0, 0, -1), "The Locksmith General", "In service", "Mantis, key forelimbs",
		"The General duels in ritual phrases. Each phrase locks part of the hall, and a lock, once turned, stays turned. Her forelimbs are keys. She has never imagined anyone turning them for her.")


# --- Processional stair and the coronation hall at the shaft's base ------------------------------

func _build_hall(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	var wall: Material = _mat["wall"]
	# the stair: x 55..80, z -13.5..-10.5, from the dais (y -42) down to the hall (y -70); 80 risers
	# of 0.35 m on 0.3125 m treads, a ceiling 3.5 m over each step: low, narrow, one amber thread
	var stair := _group(area, "ProcessionalStair")
	var n := 80
	for i: int in n:
		var top := -42.0 - 0.35 * (i + 1)
		var x0 := 55.0 + 0.3125 * i
		_ledge(stair, Vector3(x0, -71, -13.5), Vector3(x0 + 0.3125, top, -10.5), walk)
		_ledge(stair, Vector3(x0, top + 3.5, -14), Vector3(x0 + 0.3125, top + 4.2, -10))
	_ledge(stair, Vector3(55, -72, -14), Vector3(80, -38, -13.5), wall)
	_ledge(stair, Vector3(55, -72, -10.5), Vector3(80, -38, -10), wall)
	var thread := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.03
	cm.bottom_radius = 0.03
	cm.height = sqrt(25.0 * 25.0 + 28.0 * 28.0)
	thread.mesh = cm
	thread.material_override = _glow(C_AMBER, 3.0, false)
	thread.position = Vector3(67.5, -55.0 + 1.0, -13.4)
	thread.rotation.z = atan2(25.0, 28.0)
	stair.add_child(thread)
	# the curtain: a dark membrane across the stair's foot that parts after a held breath
	_curtain = _box(area, Vector3(0.3, 3.6, 3.0), Vector3(80.2, -68.2, -12), _mat["membrane"])
	_curtain.name = "Curtain"
	_zone(area, Vector3(75, -70, -13.5), Vector3(79.8, -66, -10.5), _reveal)
	# the hall floor: the shaft's base, x 80..150, z -30..14
	_ledge(geo, Vector3(80, -71, -30), Vector3(150, -70, 14), walk)
	# the dais and its case (resonance-locked: weave the two pegs, pluck the line)
	_ledge(geo, Vector3(109, -70, -14), Vector3(121, -69.7, -2), _mat["int"])
	for p: Vector3 in [Vector3(111, -69.65, -14), Vector3(119, -69.65, -14)]:
		_hall_pegs.append(_peg(area, p))
	_fragment_spot = _group(area, "FragmentSpot")
	_fragment_spot.position = Vector3(115, -69.7, -8)
	var shard := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.5, 0.7, 0.3)
	shard.mesh = pm
	shard.material_override = _mat["goal"]
	shard.position.y = 1.0
	_fragment_spot.add_child(shard)
	_cage = _box(area, Vector3(1.6, 2.2, 1.6), Vector3(115, -68.6, -8), _glow(Color(1.0, 0.7, 0.2, 0.35), 0.8, true))
	_cage.name = "DaisCase"
	_fragment = Pickup.new()
	_fragment.kind = &"fragment"
	_fragment.prompt = "Take the fragment"
	_fragment.enabled = false
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.6
	cs.shape = sph
	_fragment.add_child(cs)
	_fragment.position.y = 1.0
	_fragment_spot.add_child(_fragment)
	_fragment.visual = shard
	_fragment.picked.connect(_start_heist)
	# the court, kneeling to the dais in shifts
	for i: int in 10:
		var a := TAU * i / 10.0
		var fig := _group(area, "Courtier%d" % i)
		fig.position = Vector3(115 + sin(a) * 9.0, -70, -8 + cos(a) * 9.0)
		var b := MeshInstance3D.new()
		var cap := CapsuleMesh.new()
		cap.radius = 0.4
		cap.height = 1.3
		b.mesh = cap
		b.material_override = wall
		b.position.y = 0.65
		fig.add_child(b)
		var head := MeshInstance3D.new()
		var hs := SphereMesh.new()
		hs.radius = 0.3
		hs.height = 0.6
		head.mesh = hs
		head.material_override = _mat["int"]
		head.position = Vector3(0, 1.4, -0.25)
		fig.add_child(head)
		fig.look_at(Vector3(115, -70, -8), Vector3.UP)
		_court_figs.append(fig)
	# the pin: through the specimen, up into the sky
	var pin := MeshInstance3D.new()
	var pc := CylinderMesh.new()
	pc.top_radius = 0.9
	pc.bottom_radius = 0.9
	pc.height = 130.0
	pin.mesh = pc
	pin.material_override = _mat["int"]
	pin.position = Vector3(138, -5, 4)
	area.add_child(pin)
	_placard(area, Vector3(108.6, -68.6, -8), Vector3(-1, 0, 0), "Queen (type specimen)", "Collected", "Specimen under dome",
		"Pinned for the collection as the reference for her species. Her court reports that she is resting, and asks visitors to lower their voices. The sky over this hall was not part of the acquisition.")
	_placard(area, Vector3(86, -68.6, -16.5), Vector3(0, 0, 1), "The court at rest", "Ongoing", "Courtiers, kneeling",
		"The court kneels toward the dais in shifts. Nobody has said aloud that the queen is pinned. Pretending is a salaried office, the most senior post after Locksmith General.")


# --- Heist: lifts and a cut line up the shaft to the rim -------------------------------------

func _build_heist(area: Node3D) -> void:
	var geo := _group(area, "Geometry")
	var walk: Material = _mat["walk"]
	# H1: west-wall balcony; H2: a lower ledge across; R: the rim balcony outside the south wall
	_ledge(geo, Vector3(82, -36, -28), Vector3(96, -35, -16), walk)
	_ledge(geo, Vector3(109, -39, -28), Vector3(124, -38, -16), walk)
	_ledge(geo, Vector3(105, -4, -40), Vector3(130, -3, -30), walk)
	_ledge(geo, Vector3(104, -4, -41), Vector3(131, 4, -40), _mat["wall"])
	_lifts.append(_lift(area, [Vector3(100, -58, -22), Vector3(100, -20, -22), Vector3(89, -20, -22), Vector3(89, -24, -22)], 4.0))
	_lifts.append(_lift(area, [Vector3(118, -27, -22), Vector3(118, 10, -22), Vector3(118, 10, -35), Vector3(118, 7.5, -35)], 4.0))
	_cut_anchor = _anchor(area, Vector3(102, -25, -22), false)
	_cut_anchor.name = "CutLine"
	_zone(area, Vector3(105, -3, -40), Vector3(130, 1, -30), _on_rim, false)
	_placard(area, Vector3(108, -1.6, -39.9), Vector3(0, 0, 1), "The rim", "Exit", "Chitin lip",
		"Visitors leaving with an object are asked to declare it. No visitor has declared anything. The court has stopped pretending, which it records in the minutes as an emergency.")


func _lift(area: Node3D, path: Array, speed: float) -> Dictionary:
	var a := _anchor(area, path[0], false)
	a.name = "Lift%d" % (_lifts.size() + 1)
	a.set_meta(&"lift", true)
	var cog := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.9
	cm.bottom_radius = 0.9
	cm.height = 0.3
	cog.mesh = cm
	cog.material_override = _mat["int"]
	cog.position.y = 0.4
	a.add_child(cog)
	return {"node": a, "path": path, "speed": speed, "i": 0, "run": false}


func _build_checkpoints() -> void:
	_checkpoint(&"start", Vector3(-22, 0, 0), -90.0)
	_checkpoint(&"districts", Vector3(17, -3, 0), -90.0)
	_checkpoint(&"rim", Vector3(70, -3, 6), -90.0)
	_checkpoint(&"balcony", Vector3(118, -7, 0), -90.0)
	_checkpoint(&"foundry", Vector3(135, -28, 25), 180.0)
	_checkpoint(&"guild", Vector3(130, -31, 66), 180.0)
	_checkpoint(&"gallery", Vector3(90, -31, 91), 90.0)
	_checkpoint(&"general", Vector3(40, -31, 103), 0.0)
	_checkpoint(&"hall", Vector3(86, -70, -12), -90.0)
	var h := _checkpoint(&"heist", Vector3(115, -69.7, -4), 0.0)
	h.radius = 0.0


func _checkpoint(id: StringName, pos: Vector3, yaw_deg: float) -> Checkpoint:
	var cp := Checkpoint.new()
	cp.id = id
	cp.position = pos
	cp.rotation_degrees.y = yaw_deg
	add_child(cp)
	return cp


## Twelve camera marks: Marker3Ds under ShotMarks (shots.gd looks down each one's -Z), also in
## group shot_marks.
func _build_marks() -> void:
	var holder := _group(self, "ShotMarks")
	var marks := [
		["gate", Vector3(-20, 2.0, 6), Vector3(6, 6, 0)],
		["first_swing", Vector3(-2, 3, 8), Vector3(10, 4, -2)],
		["usher", Vector3(20, -1, 6), Vector3(28, -2, 0)],
		["light_well", Vector3(37, -1, 5), Vector3(52, -3, 0)],
		["perch", Vector3(60, -1, 4), Vector3(76, 1, -6)],
		["shaft_rim", Vector3(76, -1, 2), Vector3(110, 5, 0)],
		["shaft_down", Vector3(128, -6, -4), Vector3(131, -24, 19)],
		["foundry", Vector3(130, -26, 45), Vector3(130, -18, 60)],
		["guild_door", Vector3(118, -29, 70), Vector3(130, -29, 80)],
		["gallery", Vector3(92, -29.5, 91), Vector3(62, -27, 91)],
		["arena", Vector3(40, -29, 105), Vector3(40, -32, 60)],
		["eye_reveal", Vector3(84, -68.3, -12), Vector3(118, 30, -8)],
	]
	for m: Array in marks:
		var mk := Marker3D.new()
		mk.name = m[0]
		var pos: Vector3 = m[1]
		mk.transform = Transform3D(Basis.looking_at((m[2] as Vector3) - pos, Vector3.UP), pos)
		mk.add_to_group(&"shot_marks")
		holder.add_child(mk)


## Resuming: beats already done stay done.
func _restore() -> void:
	if Quest.is_done(&"districts") or Quest.is_step_done(&"districts", &"usher"):
		_usher.position = _usher_home + Vector3(-2, 0, 4.5)
	if recall("moth", false):
		_set_active(_moth, true)
	if Quest.is_step_done(&"foundry", &"door"):
		_open(_guild_door)
	if recall("vault", false):
		_open(_vault_door)
	if Quest.is_done(&"general"):
		for seg: Array in _arena_segs:
			for a: Node3D in seg:
				_set_active(a, true)
		for k: Node3D in _keys:
			k.rotation_degrees.z = 90.0
		_open(_dais_gate)
	_open(_gallery_gate)
	if Quest.is_step_done(&"court", &"hall"):
		_open(_curtain)
		_revealed = true
	if Quest.is_step_done(&"court", &"dais"):
		_open(_cage)
	_update_fragment()


# --- runtime -----------------------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	var dt := delta * Game.world_time_scale
	# the clockwork anchor: 20 m of track, 20 s a round trip
	_clock_t += dt
	_clock_anchor.position.x = 130.0 + 10.0 * sin(_clock_t * TAU / 20.0)
	# the usher returns to his door once the music has been gone a while
	if _usher_away_t > 0.0:
		_usher_away_t -= dt
		if _usher_away_t <= 0.0 and not Quest.is_step_done(&"districts", &"usher"):
			create_tween().tween_property(_usher, "position", _usher_home, 1.0)
	_tick_arena()
	_tick_lifts(dt)
	if _heist_on:
		_cut_tick += 1
		var cyc := _cut_tick % (CUT_ON_TICKS + CUT_OFF_TICKS)
		_set_active(_cut_anchor, cyc < CUT_ON_TICKS)
		if Game.player:
			for f: Node3D in _court_figs:
				var t := Game.player.global_position
				t.y = f.global_position.y
				if t.distance_to(f.global_position) > 0.5:
					f.look_at(t, Vector3.UP)
	if _revealed:
		_blink_t += dt
		if _blink_t > BLINK_EVERY:
			_blink_t = 0.0
			_blink()


func _on_plucked(s: Node) -> void:
	var pitch: float = s.call("pitch")
	Audio.sfx(_sfx["pluck"], s.global_position, -2.0, 0.3, pitch)
	var mid: Vector3 = s.global_position
	if mid.distance_to(_usher.global_position) < 18.0 and not Quest.is_step_done(&"districts", &"usher"):
		_usher_away_t = 20.0
		create_tween().tween_property(_usher, "position", _usher_home + Vector3(-2, 0, 4.5), 1.0)
		toast("The usher hears the queen calling, and steps aside to listen.")
	if s == _harp_moth and not _moth.is_in_group(&"silk_anchors"):
		_moth.position = Vector3(66, 24, -6)
		_set_active(_moth, true)
		create_tween().tween_property(_moth, "position", Vector3(66, 9, -6), 2.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		toast("A court moth answers the line, and holds still above you.")
	var ends: Array = s.get_meta(&"ends", [])
	var length: float = s.get("length")
	if _ends_in(ends, _guild_pegs) and _guild_door.visible:
		if absf(length - GUILD_STANDARD) < LOCK_TOL:
			_open(_guild_door)
			s.queue_free()  # the lock keeps the line it heard; nothing left to trip over
			complete_step(&"foundry", &"door")
			toast("The guild door hears its standard, and opens.")
		else:
			toast("The guild door does not care for that note. It sounds %s." % ("too high" if length < GUILD_STANDARD else "too low"))
	if _ends_in(ends, _vault_pegs) and _vault_door.visible and absf(length - QUEENS_SPAN) < LOCK_TOL:
		_open(_vault_door)
		s.queue_free()
		store("vault", true)
		toast("The vault recognises the queen's span.")
	if _ends_in(ends, _hall_pegs) and _cage.visible:
		_open(_cage)
		s.queue_free()
		complete_step(&"court", &"dais")
		_update_fragment()
		toast("The case over the dais answers the court's standard and lifts away.")


func _ends_in(ends: Array, pegs: Array[Node3D]) -> bool:
	return ends.size() == 2 and ends[0] in pegs and ends[1] in pegs


## A fall: back to the last ledge stood on within a second; in the arena and the heist, back to
## that sequence's checkpoint with its state reset.
func _fall() -> void:
	if _falling or Game.player == null:
		return
	if silk.get("state") == SilkMode.ROPE and is_instance_valid(silk.get("anchor_node")) and (silk.get("anchor_node") as Node).has_meta(&"lift"):
		return  # a lift is hauling her through the net
	_falling = true
	var p := Game.player
	if _arena_on:
		_arena_reset()
		toast("The General resumes her first phrase.", "The Locksmith General")
		await Game.respawn()
	elif _heist_on:
		_reset_lifts()
		await Game.respawn()
	elif silk.get("has_safe"):
		p.input_enabled = false
		await Post.fade_to(1.0, 0.25)
		if is_instance_valid(p) and Game.player == p:
			p.teleport(silk.get("last_safe"))
			p.velocity = Vector3.ZERO
			silk.call("reset")
			p.input_enabled = true
			await Post.fade_to(0.0, 0.35)
	else:
		await Game.respawn()
	_falling = false


# --- arena ---------------------------------------------------------------------------------------

func _arena_start() -> void:
	if _arena_on or Quest.is_done(&"general"):
		return
	_arena_on = true
	_gallery_gate.visible = true
	_set_solid(_gallery_gate, true)
	Audio.set_intensity(0.6)
	_begin_phrase(0)


const PHRASES := [
	"First phrase: the shutting of the outer door. The General offers her first key.",
	"Second phrase: the folding of the galleries. Two holds, then the second key.",
	"Third phrase: the sealing of the court. Three holds, then the last key.",
]


func _begin_phrase(k: int) -> void:
	_phrase = k
	_phrase_tick = 0
	_key_ticks = 0
	for a: Node3D in _arena_segs[k]:
		_set_active(a, true)
	toast(PHRASES[k], "The Locksmith General")
	Audio.sfx(_sfx["blink"], _keys[k].global_position, 0.0, 0.4, 0.6)


func _tick_arena() -> void:
	if not _arena_on or _phrase < 0:
		return
	_phrase_tick += 1
	var seg: Array = _arena_segs[_phrase]
	var total := int(PHRASE_SECS[_phrase] * HZ)
	# the space closes: each hold in the phrase locks at its share of the phrase
	for i: int in seg.size():
		var a: Node3D = seg[i]
		var turned_key: bool = a == _keys[_phrase] and _key_turned[_phrase]
		if not turned_key and a.is_in_group(&"silk_anchors") and _phrase_tick >= total * (i + 1) / seg.size():
			_set_active(a, false)
	if silk.get("state") == SilkMode.ROPE and silk.get("anchor_node") == _keys[_phrase] and not _key_turned[_phrase]:
		_key_ticks += 1
		if _key_ticks >= KEY_TICKS:
			_key_turned[_phrase] = true
			create_tween().tween_property(_keys[_phrase], "rotation_degrees:z", 90.0, 0.5)
			Audio.sfx(_sfx["pluck"], _keys[_phrase].global_position, 2.0, 0.5, 0.5)
	var p := Game.player
	if _key_turned[_phrase] and p and p.is_on_floor() and silk.get("state") == SilkMode.GROUND and _islands[_phrase].has_point(p.global_position + Vector3.UP * 0.5):
		for a: Node3D in seg:
			_set_active(a, false)
		if _phrase < 2:
			_begin_phrase(_phrase + 1)
		else:
			_arena_won()


func _arena_won() -> void:
	_arena_on = false
	_phrase = -1
	for s: StringName in [&"key1", &"key2", &"key3"]:
		complete_step(&"general", s)
	_open(_dais_gate)
	_open(_gallery_gate)
	for limb: Node in _general.find_children("*Forelimb*", "", false, false):
		(limb as Node3D).rotation_degrees.x = 60.0
	Audio.set_intensity(0.2)
	toast("Her own keys hold her. The General stands very still, as if this were a phrase she knew.", "The Locksmith General")


func _arena_reset() -> void:
	_arena_on = false
	_phrase = -1
	_key_turned = [false, false, false]
	for seg: Array in _arena_segs:
		for a: Node3D in seg:
			_set_active(a, false)
	for k: Node3D in _keys:
		k.rotation_degrees.z = 0.0
	_open(_gallery_gate)
	Audio.set_intensity(0.0)


# --- hall ----------------------------------------------------------------------------------------

## The reveal: compress (the stair), occlude (the curtain, a held breath of near-silence), release
## into the shaft's base under the amber sky, stinger, then the sky blinks.
func _reveal() -> void:
	if _revealed:
		return
	_revealed = true
	_blink_t = -60.0  # the scripted first blink below; the cycle starts after it
	Audio.reveal(_sfx["stinger"], 3.5)
	await get_tree().create_timer(2.5).timeout
	_open(_curtain)
	await get_tree().create_timer(3.5).timeout
	_blink()
	complete_step(&"court", &"hall")
	_blink_t = 0.0


func _blink() -> void:
	Audio.sfx(_sfx["blink"], null, -2.0, 0.6, 0.5)
	var t := create_tween()
	t.tween_property(_dome_mat, "emission_energy_multiplier", 0.02, 0.18)
	t.parallel().tween_property(_dome_mat, "albedo_color", Color("150a02"), 0.18)
	t.tween_interval(0.12)
	t.tween_property(_dome_mat, "emission_energy_multiplier", 1.6, 0.45)
	t.parallel().tween_property(_dome_mat, "albedo_color", C_AMBER, 0.45)


func _update_fragment() -> void:
	if not is_instance_valid(_fragment):
		return
	var ready := Quest.is_step_done(&"court", &"dais") and not Quest.has_fragment(wing_id)
	_fragment.enabled = ready
	_fragment_spot.visible = not Quest.has_fragment(wing_id)


# --- heist ---------------------------------------------------------------------------------------

func _start_heist() -> void:
	_heist_on = true
	_fragment_spot.visible = false
	Game.set_checkpoint(&"heist")
	for l: Dictionary in _lifts:
		_set_active(l["node"], true)
	Audio.set_intensity(1.0)
	toast("The court stops pretending. Every head turns. The lifts are still running; the courtiers are cutting lines.", "The Heist")


func _tick_lifts(dt: float) -> void:
	for l: Dictionary in _lifts:
		var a: Node3D = l["node"]
		if not l["run"]:
			if silk.get("state") == SilkMode.ROPE and silk.get("anchor_node") == a and int(l["i"]) == 0:
				l["run"] = true
			continue
		var path: Array = l["path"]
		var i: int = l["i"]
		if i + 1 >= path.size():
			continue
		var to: Vector3 = path[i + 1]
		a.position = a.position.move_toward(to, float(l["speed"]) * dt)
		if a.position.distance_to(to) < 0.01:
			l["i"] = i + 1


func _reset_lifts() -> void:
	for l: Dictionary in _lifts:
		(l["node"] as Node3D).position = (l["path"] as Array)[0]
		l["i"] = 0
		l["run"] = false


func _on_rim() -> void:
	if not Quest.has_fragment(wing_id) or not _heist_on:
		return
	_heist_on = false
	Audio.set_intensity(0.3)
	finish()


# --- test accessors (read-only) ----------------------------------------------------------------

func arena_phrase() -> int:
	return _phrase


func key_turned(k: int) -> bool:
	return _key_turned[k]


func phrase_anchors(k: int) -> Array:
	return _arena_segs[k].duplicate()


func lift(k: int) -> Node3D:
	return _lifts[k]["node"]


func lift_done(k: int) -> bool:
	return int(_lifts[k]["i"]) + 1 >= (_lifts[k]["path"] as Array).size()


# --- helpers -------------------------------------------------------------------------------------

func _anchor(parent: Node3D, pos: Vector3, active: bool = true) -> Node3D:
	var a := Node3D.new()
	a.name = "Hook"
	a.position = pos
	parent.add_child(a)
	var m := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = 0.3
	s.height = 0.6
	m.mesh = s
	m.material_override = _mat["int"]
	a.add_child(m)
	var h := MeshInstance3D.new()
	h.name = "Highlight"
	var hs := SphereMesh.new()
	hs.radius = 0.75
	hs.height = 1.5
	h.mesh = hs
	h.material_override = _mat["hi"]
	h.visible = false
	a.add_child(h)
	_set_active(a, active)
	return a


## A peg: a low anchor on a lip, for weaving.
func _peg(parent: Node3D, pos: Vector3) -> Node3D:
	var a := _anchor(parent, pos)
	a.name = "Peg"
	(a.get_child(0) as Node3D).scale = Vector3.ONE * 0.5
	(a.get_node(^"Highlight") as Node3D).scale = Vector3.ONE * 0.6
	return a


func _set_active(a: Node3D, on: bool) -> void:
	a.visible = on
	if on:
		a.add_to_group(&"silk_anchors")
	elif a.is_in_group(&"silk_anchors"):
		a.remove_from_group(&"silk_anchors")


func _open(n: Node3D) -> void:
	n.visible = false
	_set_solid(n, false)


func _set_solid(n: Node3D, on: bool) -> void:
	for c: Node in n.find_children("*", "CollisionShape3D", true, false):
		(c as CollisionShape3D).set_deferred(&"disabled", not on)


func _abyss(parent: Node3D, mn: Vector3, mx: Vector3) -> void:
	var tz := TriggerZone.make_box(mx - mn, false)
	tz.name = "Abyss"
	tz.position = (mn + mx) * 0.5
	tz.triggered.connect(func(_p: Player) -> void: _fall())
	parent.add_child(tz)


func _zone(parent: Node3D, mn: Vector3, mx: Vector3, fn: Callable, once: bool = true) -> void:
	var tz := TriggerZone.make_box(mx - mn, once)
	tz.position = (mn + mx) * 0.5
	tz.triggered.connect(func(_p: Player) -> void: fn.call())
	parent.add_child(tz)


func _provenance(parent: Node3D, id: String, pos: Vector3) -> void:
	if Quest.has_provenance(wing_id, StringName(id)):
		return
	var p := {}
	for d: Dictionary in provenances():
		if d["id"] == id:
			p = d
	var marker := Node3D.new()
	marker.name = "Provenance_" + id
	marker.position = pos
	parent.add_child(marker)
	var mesh := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(0.25, 0.3, 0.25)
	mesh.mesh = pm
	mesh.material_override = _mat["int"]
	mesh.position.y = 0.4
	marker.add_child(mesh)
	var pick := Pickup.new()
	pick.kind = &"provenance"
	pick.item_id = StringName(id)
	pick.prompt = "Take: " + String(p["name"])
	pick.visual = mesh
	pick.position.y = 0.4
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.4
	cs.shape = sph
	pick.add_child(cs)
	marker.add_child(pick)


## A museum tombstone facing `face` (its text faces local +Z).
func _placard(parent: Node3D, pos: Vector3, face: Vector3, title: String, date: String, medium: String, body: String) -> void:
	var pl := Placard.new()
	pl.position = pos
	pl.rotation.y = atan2(face.x, face.z)
	parent.add_child(pl)
	pl.set_label(Placard.fields(title, date, medium, ACQ, body), false)


func _group(parent: Node, name_: String) -> Node3D:
	var n := Node3D.new()
	n.name = name_
	parent.add_child(n)
	return n


func _flat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 1.0
	return m


func _glow(c: Color, energy: float, transparent: bool) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = Color(c.r, c.g, c.b)
	m.emission_energy_multiplier = energy
	if transparent:
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return m


## A static box from its AABB corners (mesh + collision).
func _ledge(parent: Node3D, mn: Vector3, mx: Vector3, mat: Material = null) -> StaticBody3D:
	return _box(parent, mx - mn, (mn + mx) * 0.5, mat if mat else _mat["wall"])


func _box(parent: Node3D, size: Vector3, pos: Vector3, mat: Material) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	parent.add_child(body)
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
	return body
