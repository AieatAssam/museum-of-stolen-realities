extends Playthrough
## Chitin, two checks, headless:  tests/run_smoke.sh wings/chitin/tests/resume_heist.tscn
##  1. A save with the fragment taken and the court's escape not done resumes mid-heist:
##     chitin.gd _restore() turns the heist on and every lift is live (visible, in silk_anchors).
##  2. A fall during the heist respawns her at the heist checkpoint, and the heist stays on.

const CHECKPOINT := Vector3(115, -69.7, -4)


func run() -> void:
	_seed_save()
	# Continue, the real resume path. enter() would reset the saved checkpoint to the wing's start.
	var loaded: bool = await Game.continue_game()
	_verdict(loaded and Game.wing != null and Game.wing.wing_id == &"chitin", "continue loads the chitin wing from the save")
	if not loaded or Game.wing == null:
		return
	await skip_cinematics()
	var w: Node = Game.wing
	await frames(2)

	# 1. resumed mid-heist
	_verdict(w.get("_heist_on") == true, "resumed mid-heist: _heist_on is true (got %s)" % str(w.get("_heist_on")))
	var lifts: Array = w.get("_lifts")
	var dead: Array = []
	for l: Dictionary in lifts:
		var n: Node3D = l["node"]
		if not (n.visible and n.is_in_group(&"silk_anchors")):
			dead.append(n.name)
	_verdict(lifts.size() == 2 and dead.is_empty(), "both lifts live after resume (%d lifts, not live: %s)" % [lifts.size(), str(dead)])

	# 2. heist fall reset
	if Game.player == null:
		_verdict(false, "heist fall: no player to drop")
		return
	Game.player.teleport(Transform3D(Basis.IDENTITY, Vector3(105, -200, -20)))
	var back := await until(func() -> bool: return Game.player != null and Game.player.global_position.distance_to(CHECKPOINT) < 3.0, 5.0)
	var at := Game.player.global_position if Game.player else Vector3.INF
	_verdict(back, "fall during heist respawns near heist checkpoint (at %s, want %s within 3 m)" % [str(at), str(CHECKPOINT)])
	_verdict(w.get("_heist_on") == true, "heist still on after the fall reset (got %s)" % str(w.get("_heist_on")))


## Set the run's state as a player who took the fragment (heist checkpoint saved) but did not escape.
## Written before the wing loads, so chitin.gd _restore() sees it.
func _seed_save() -> void:
	Save.data["fragments"] = ["chitin"]
	var objs: Dictionary = Save.wing_data(&"chitin")["objectives"]
	objs["court"] = {"done": false, "steps": ["hall", "dais"]}
	Save.data["checkpoint"] = {"scene": "res://wings/chitin/chitin.tscn", "id": "heist"}
	Save.save_game()  # Continue reads the file; Playthrough removed it at start


func _verdict(ok: bool, what: String) -> void:
	if ok:
		print("[resume_heist] PASS: %s" % what)
	else:
		fails += 1
		print("[resume_heist] FAIL: %s" % what)
