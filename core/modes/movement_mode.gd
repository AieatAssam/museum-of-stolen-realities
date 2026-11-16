class_name MovementMode
extends RefCounted
## Base class for a player movement mode. The Player owns exactly one active mode and calls
## `physics(delta)` every physics tick with delta already scaled by Game.player_time_scale.
## A mode must set `player.velocity` and call `player.move_and_slide()` (or move the player itself).
##
## Register from a wing (no core edits needed):
##     player.add_mode(&"lightwalk", preload("res://wings/glass/lightwalk_mode.gd").new())
##     player.set_mode(&"lightwalk")
## Read input through the player helpers (`move_input()`, `wish_dir()`, `action_*`) so scripted
## test input and the void-respawn/seat logic keep working.

var player: Player
var name: StringName


## Called when the mode becomes active. `from` is the previous mode (may be null).
func enter(_from: MovementMode) -> void:
	pass


func exit(_to: MovementMode) -> void:
	pass


func physics(_delta: float) -> void:
	pass


## Called for verbs while this mode is active: &"primary", &"secondary", &"jump", &"crouch".
## Return true to consume (the Player then won't emit its generic verb signal).
func on_verb(_verb: StringName, _pressed: bool) -> bool:
	return false


## The verb prompt the HUD shows in the interaction prompt's place when no Interactable is under the
## crosshair, e.g. {"action": &"primary", "text": "spin a line"} (+ "hold": true), or {} for none.
## Teach the wing's verb where it can be used; never as a popup.
func prompt() -> Dictionary:
	return {}


## 0..1 multiplier on head bob / footsteps.
func bob_scale() -> float:
	return 1.0


## Eye height above the feet, metres.
func eye_height() -> float:
	return 1.62
