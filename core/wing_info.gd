class_name WingInfo
extends Resource
## One row of the museum catalogue. Lives in res://core/wings.tres (owned by core; wings never edit it).

@export var id: StringName
@export var numeral: String = "I"
@export var title: String = ""
@export var acquisition_no: String = ""
## One line, catalog voice: where and when it was taken.
@export var origin: String = ""
## The wing's rule, shown in small caps on the placard.
@export var rule: String = ""
## [0] dominant, [1] secondary, [2] accent. Used by the hub frame, floor spill and the entry transition.
@export var palette: PackedColorArray = PackedColorArray([Color.WHITE, Color.GRAY, Color.BLACK])
@export_file("*.tscn") var scene_path: String = ""
## Index into hub/shaders/frame_portal.gdshader's medium switch.
@export var portal_medium: int = 0
## Template/staff wings: reachable from the hub but not counted towards the six fragments.
@export var is_exhibit: bool = true


func scene_exists() -> bool:
	return scene_path != "" and ResourceLoader.exists(scene_path)
