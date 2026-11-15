class_name PostGrade
extends Resource
## Full-screen grade applied by the Post autoload on top of the Environment's own adjustments.
## A wing sets one as `Wing.grade`; Post tweens between grades on wing entry.

@export var tint: Color = Color(1, 1, 1)
@export_range(0.0, 2.0) var saturation: float = 1.0
@export_range(0.5, 2.0) var contrast: float = 1.0
## Added to the shadows, e.g. a blue-black lift.
@export var lift: Color = Color(0, 0, 0)
@export_range(0.0, 0.3) var grain: float = 0.045
@export_range(0.0, 3.0) var aberration: float = 0.6
@export_range(0.0, 1.5) var vignette: float = 0.55
## 0 = smooth; >0 posterises time-steps for the grain (12 for claymation).
@export var grain_fps: float = 24.0
