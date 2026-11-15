extends Node
## Runner for wing playthrough tests:  tests/run_playthrough.sh <wing_id>
## (= tests/run_smoke.sh tests/playthrough.tscn --wing=<id>). Loads
## res://wings/<id>/tests/playthrough.gd (extends Playthrough) and runs it from the root.


func _ready() -> void:
	var id := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--wing="):
			id = a.trim_prefix("--wing=")
	var path := "res://wings/%s/tests/playthrough.gd" % id
	if id == "" or not ResourceLoader.exists(path):
		push_error("playthrough: no test at %s (pass -- --wing=<id>)" % path)
		get_tree().quit(2)
		return
	var s := load(path) as GDScript
	if s == null or not s.can_instantiate():
		push_error("playthrough: %s failed to compile (run --import once if Playthrough is unknown)" % path)
		get_tree().quit(2)
		return
	var n: Node = s.new()
	n.name = "Playthrough_" + id
	get_tree().root.add_child.call_deferred(n)
