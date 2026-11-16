extends Node
## Save autoload. Two JSON files in user://:
##   save.json      — the run: fragments, provenances, per-wing objective + custom state, hub state, checkpoint.
##   settings.json  — player settings (survive New Game).
## Wings never touch `data` directly; go through Quest (objectives) or Wing.save_state()/load_state().

signal settings_changed

const SAVE_PATH := "user://save.json"
const SETTINGS_PATH := "user://settings.json"
const VERSION := 1

var data: Dictionary = {}
var settings: Dictionary = {}
## Tests point this elsewhere so they never clobber a real save.
var save_path: String = SAVE_PATH

const DEFAULT_SETTINGS := {
	"quality": "high",          # low | medium | high | ultra
	"render_scale": 1.0,        # used when render_auto is off
	"render_auto": true,        # 3D scale from the window size (AUTO_PIXELS)
	"vol_master": 0.9, "vol_music": 0.8, "vol_sfx": 0.9, "vol_ambience": 0.8, "vol_ui": 0.7,
	"mouse_sensitivity": 0.12,  # degrees per pixel
	"invert_y": false,
	"fov": 90.0,
	"head_bob": 1.0,            # 0..1 accessibility scalers
	"fov_kick": 1.0,
	"camera_shake": 1.0,
	"strafe_roll": 1.0,
	"reduced_motion": false,    # forces the four above to 0
	"fullscreen": false,
	"vsync": true,
}


func _ready() -> void:
	settings = DEFAULT_SETTINGS.duplicate()
	var s: Variant = _read(SETTINGS_PATH)
	if s is Dictionary:
		settings.merge(s, true)
	data = fresh()
	apply_settings()


static func fresh() -> Dictionary:
	return {
		"version": VERSION,
		"fragments": [],          # wing ids whose Fragment of Exhibit 0 is recovered
		"provenances": {},        # wing id -> [provenance ids]
		"provenance_info": {},    # wing id -> {provenance id: {"name", "line"}} (the hub's vitrine labels)
		"wings": {},              # wing id -> {"objectives": {obj_id: {"done": bool, "steps": [step ids]}}, "state": {}}
		"hub": {"seen_intro": false, "flags": {}},
		"checkpoint": {"scene": "", "id": ""},
		"ending": "",
		"play_seconds": 0.0,
	}


func has_save() -> bool:
	return FileAccess.file_exists(save_path)


func new_game() -> void:
	data = fresh()
	save_game()


func load_game() -> bool:
	var d: Variant = _read(save_path)
	if not d is Dictionary:
		return false
	data = fresh()
	data.merge(d, true)
	return true


func save_game() -> void:
	_write(save_path, data)


func wing_data(wing_id: StringName) -> Dictionary:
	var w: Dictionary = data["wings"]
	if not w.has(String(wing_id)):
		w[String(wing_id)] = {"objectives": {}, "state": {}}
	return w[String(wing_id)]


# --- settings ---------------------------------------------------------------

## Effective motion-effect scale (0 when reduced motion is on).
func motion(key: String) -> float:
	return 0.0 if settings.get("reduced_motion", false) else float(settings.get(key, 1.0))


func set_setting(key: String, value: Variant) -> void:
	settings[key] = value
	_write(SETTINGS_PATH, settings)
	apply_settings()


func apply_settings() -> void:
	for pair: Array in [["Master", "vol_master"], ["Music", "vol_music"], ["SFX", "vol_sfx"],
			["Ambience", "vol_ambience"], ["UI", "vol_ui"]]:
		var idx := AudioServer.get_bus_index(pair[0])
		if idx >= 0:
			AudioServer.set_bus_volume_db(idx, linear_to_db(maxf(float(settings[pair[1]]), 0.0001)))
	var vp := get_tree().root
	_apply_render_scale()
	if not vp.size_changed.is_connected(_apply_render_scale):
		vp.size_changed.connect(_apply_render_scale)
	if not DisplayServer.get_name() == "headless":
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if settings["vsync"] else DisplayServer.VSYNC_DISABLED)
		var want_fs: bool = settings["fullscreen"]
		var is_fs := DisplayServer.window_get_mode() in [DisplayServer.WINDOW_MODE_FULLSCREEN, DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN]
		if want_fs != is_fs:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if want_fs else DisplayServer.WINDOW_MODE_WINDOWED)
	settings_changed.emit()


## Auto 3D scale never renders more 3D pixels than 1920x1080: 2560x1440 renders at 0.75 with FSR
## (with MSAA off, 6-10 ms saved on the heaviest chitin/atrium views, measured), 1080p and below stay native.
const AUTO_PIXELS := 1920 * 1080


func _apply_render_scale() -> void:
	var vp := get_tree().root
	var s := float(settings["render_scale"])
	if settings["render_auto"]:
		s = sqrt(AUTO_PIXELS / float(maxi(vp.size.x * vp.size.y, 1)))
	vp.scaling_3d_scale = clampf(s, 0.5, 1.0)
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if vp.scaling_3d_scale < 0.99 else Viewport.SCALING_3D_MODE_BILINEAR


# --- io -----------------------------------------------------------------------

func _read(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	var f := FileAccess.open(path, FileAccess.READ)
	return JSON.parse_string(f.get_as_text()) if f else null


func _write(path: String, d: Dictionary) -> void:
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("Save: cannot write %s" % tmp)
		return
	f.store_string(JSON.stringify(d, "\t"))
	f.close()
	DirAccess.rename_absolute(tmp, path)  # atomic-ish: never leave a half-written save
