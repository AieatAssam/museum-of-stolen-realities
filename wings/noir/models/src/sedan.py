"""1938 sedan, 4.6 m long, 1.7 m tall. Faces +Y in Blender (-Z in Godot, the way the car drives).
Origin at the centre of the wheelbase on the road. Headlamps are material 'glass' and are lit
at runtime. Body and cabin use 'paint' (black lacquer), chrome parts 'chrome'."""
import math

import kit


def build(args):
    parts = []
    # lower body and bonnet
    parts.append(kit.box("body", (1.7, 4.6, 0.6), (0, 0, 0.55), mat="paint", bevel=0.12, segments=3))
    # cabin with a raked windscreen
    parts.append(kit.box("cabin", (1.5, 2.2, 0.55), (0, -0.35, 1.15), mat="paint", bevel=0.14, segments=3))
    parts.append(kit.box("glass_front", (1.36, 0.02, 0.42), (0, 0.78, 1.25), mat="glass"))
    parts.append(kit.box("glass_side_l", (0.02, 1.8, 0.36), (-0.76, -0.35, 1.25), mat="glass"))
    parts.append(kit.box("glass_side_r", (0.02, 1.8, 0.36), (0.76, -0.35, 1.25), mat="glass"))
    # running boards and bumpers
    parts.append(kit.box("bumper_f", (1.8, 0.1, 0.12), (0, 2.35, 0.36), mat="chrome"))
    parts.append(kit.box("bumper_r", (1.8, 0.1, 0.12), (0, -2.35, 0.36), mat="chrome"))
    # headlamps: glass on the chrome shells
    for x in (-0.6, 0.6):
        lamp = kit.lathe("headlamp", [(0.0, 0.0), (0.14, 0.0), (0.14, 0.12), (0.0, 0.12)], 14, mat="glass")
        kit.place(lamp, (x, 2.28, 0.9), rot=(math.radians(90), 0, 0))
        parts.append(lamp)
    # wheels: tyre + hub
    for x, y in ((-0.85, 1.4), (0.85, 1.4), (-0.85, -1.4), (0.85, -1.4)):
        tyre = kit.lathe("tyre", [(0.0, -0.13), (0.36, -0.13), (0.38, -0.08), (0.38, 0.08), (0.36, 0.13), (0.0, 0.13)], 20, mat="tyre")
        kit.place(tyre, (x, y, 0.38), rot=(0, math.radians(90), 0))
        hub = kit.lathe("hub", [(0.0, -0.14), (0.18, -0.14), (0.18, 0.14), (0.0, 0.14)], 16, mat="chrome")
        kit.place(hub, (x, y, 0.38), rot=(0, math.radians(90), 0))
        parts += [tyre, hub]
    kit.join("sedan", parts)
    kit.box("sedan-convcolonly", (1.8, 4.6, 1.5), (0, 0, 0.9))
