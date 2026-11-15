extends Node
## Quest autoload — objective book-keeping for the active wing, persisted through Save.
##
## A wing declares (see core/wing.gd):
##   objectives  — ordered; each {id, title, steps: [{id, title}], optional: bool, hint: String}
##                 optional == true => side objective (never blocks the wing).
##   provenances — exactly three hidden collectibles {id, name, line}; `line` is the placard text.
##   fragment    — {name, line}: the Fragment of Exhibit 0 that ends the wing.
## Steps/objectives can be completed in any order; the HUD shows the first unfinished main objective.

signal objectives_changed(wing_id: StringName)
signal step_completed(wing_id: StringName, objective_id: StringName, step_id: StringName)
signal objective_completed(wing_id: StringName, objective_id: StringName)
signal provenance_found(wing_id: StringName, provenance_id: StringName)
signal fragment_collected(wing_id: StringName)

var wing_id: StringName = &""
var objectives: Array[Dictionary] = []
var provenances: Array[Dictionary] = []
var fragment: Dictionary = {}


func begin(id: StringName, objs: Array[Dictionary], provs: Array[Dictionary], frag: Dictionary) -> void:
	wing_id = id
	objectives = objs
	provenances = provs
	fragment = frag
	for p in provs:
		assert(p.has("id") and p.has("name") and p.has("line"), "Provenance needs id, name, line")
	objectives_changed.emit(wing_id)


func clear() -> void:
	begin(&"", [] as Array[Dictionary], [] as Array[Dictionary], {})


func _rec(obj_id: StringName) -> Dictionary:
	var objs: Dictionary = Save.wing_data(wing_id)["objectives"]
	if not objs.has(String(obj_id)):
		objs[String(obj_id)] = {"done": false, "steps": []}
	return objs[String(obj_id)]


func get_objective(obj_id: StringName) -> Dictionary:
	for o in objectives:
		if StringName(o["id"]) == obj_id:
			return o
	return {}


func is_done(obj_id: StringName) -> bool:
	return bool(_rec(obj_id)["done"])


func is_step_done(obj_id: StringName, step_id: StringName) -> bool:
	return String(step_id) in _rec(obj_id)["steps"]


func complete_step(obj_id: StringName, step_id: StringName) -> void:
	var r := _rec(obj_id)
	if String(step_id) in r["steps"]:
		return
	(r["steps"] as Array).append(String(step_id))
	step_completed.emit(wing_id, obj_id, step_id)
	var o := get_objective(obj_id)
	var steps: Array = o.get("steps", [])
	if not steps.is_empty() and steps.all(func(s: Dictionary) -> bool: return String(s["id"]) in r["steps"]):
		complete_objective(obj_id)
	else:
		Save.save_game()
		objectives_changed.emit(wing_id)


func complete_objective(obj_id: StringName) -> void:
	var r := _rec(obj_id)
	if r["done"]:
		return
	r["done"] = true
	for s: Dictionary in get_objective(obj_id).get("steps", []):
		if not String(s["id"]) in r["steps"]:
			(r["steps"] as Array).append(String(s["id"]))
	Save.save_game()
	objective_completed.emit(wing_id, obj_id)
	objectives_changed.emit(wing_id)


## First unfinished main objective, or {} when all main objectives are done.
func current() -> Dictionary:
	for o in objectives:
		if not o.get("optional", false) and not is_done(StringName(o["id"])):
			return o
	return {}


func main_objectives_done() -> bool:
	return current().is_empty()


func find_provenance(prov_id: StringName) -> void:
	var all: Dictionary = Save.data["provenances"]
	var list: Array = all.get(String(wing_id), [])
	if String(prov_id) in list:
		return
	list.append(String(prov_id))
	all[String(wing_id)] = list
	for p in provenances:  # name and line travel with it: the hub labels its vitrine from these
		if StringName(p["id"]) == prov_id:
			var info: Dictionary = Save.data["provenance_info"]
			var w: Dictionary = info.get(String(wing_id), {})
			w[String(prov_id)] = {"name": String(p.get("name", "")), "line": String(p.get("line", ""))}
			info[String(wing_id)] = w
	Save.save_game()
	provenance_found.emit(wing_id, prov_id)


func has_provenance(w: StringName, prov_id: StringName) -> bool:
	return String(prov_id) in (Save.data["provenances"] as Dictionary).get(String(w), [])


func collect_fragment() -> void:
	var frags: Array = Save.data["fragments"]
	if String(wing_id) in frags:
		return
	frags.append(String(wing_id))
	Save.save_game()
	fragment_collected.emit(wing_id)


func has_fragment(w: StringName) -> bool:
	return String(w) in Save.data["fragments"]


## Fragments from exhibit wings only (the template/staff wing never counts).
func fragment_count() -> int:
	return (Save.data["fragments"] as Array).filter(func(id: String) -> bool:
		var info: WingInfo = Game.registry.get_info(StringName(id))
		return info != null and info.is_exhibit).size()
