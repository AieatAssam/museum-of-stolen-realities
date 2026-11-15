extends Wing
## The Pinched Forest (Acquisition No. 088). Stop-motion world on twos at 12 fps; Vesper is smooth.
## Rule: Reshaping. Hold primary to pull clay up, secondary to press it down.

const WORLD_FPS := 12.0

var world_fps: float = WORLD_FPS
var _beat_acc: float = 0.0
var _tick: int = 0
signal beat(dt: float)


func objectives() -> Array[Dictionary]:
	return [
		{"id": "raise", "title": "Pull the first step out of the moss",
			"steps": [{"id": "pull_step", "title": "Pull a step up from the moss"},
				{"id": "ledge", "title": "Climb onto the ledge"},
				{"id": "mound", "title": "Press the mound flat"}]},
		{"id": "cross", "title": "Cross the cling-film river",
			"steps": [{"id": "carry", "title": "Carry clay from the pit"},
				{"id": "boulder", "title": "Roll the boulder into the gap and flatten it"},
				{"id": "doorway", "title": "Thumb open the hill"}]},
		{"id": "way_up", "title": "Build a way up to the workbench",
			"steps": [{"id": "gate", "title": "Lower the wire gate"},
				{"id": "ramp", "title": "Pull a ramp to the workbench foot"}]},
		{"id": "lookout", "title": "Look over the armature village", "optional": true, "steps": []},
	]


func provenances() -> Array[Dictionary]:
	return [
		{"id": "thumb", "name": "A thumbprint, larger than a hand", "line": "Found in the moss on the morning the forest was lifted. The print is still warm to the touch."},
		{"id": "horse", "name": "A wire horse, one leg bent back", "line": "The armature was never covered. The horse was meant to be carried in someone's pocket."},
		{"id": "film", "name": "A scrap of cling film, fingerprinted", "line": "It was used to cover the river and then to cover the river's cover. The Curator has not decided which is the exhibit."},
	]


func fragment() -> Dictionary:
	return {"name": "A pinch of the Pinched Forest",
		"line": "A fragment of Exhibit 0. The clay still holds the shape of a thumb. The thumb is not in the catalogue."}


func on_enter(_first_time: bool) -> void:
	if not is_inside_tree():
		return
	toast("You are in the Pinched Forest. The clay is still soft.")


func _process(delta: float) -> void:
	# World ticker: animated world nodes advance only on beats, never on render frames.
	if world_fps <= 0.0:
		_beat_acc = 0.0
		return
	_beat_acc += delta
	var step := 1.0 / world_fps
	while _beat_acc >= step:
		_beat_acc -= step
		_tick += 1
		beat.emit(step)
