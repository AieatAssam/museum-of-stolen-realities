class_name WingRegistry
extends Resource
## The catalogue of every wing. Loaded by Game as `Game.registry`.

@export var wings: Array[WingInfo] = []


func get_info(id: StringName) -> WingInfo:
	for w in wings:
		if w.id == id:
			return w
	return null


func exhibits() -> Array[WingInfo]:
	return wings.filter(func(w: WingInfo) -> bool: return w.is_exhibit)
