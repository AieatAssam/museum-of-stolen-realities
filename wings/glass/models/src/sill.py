"""A threshold stone for where a beam of light lands on the walk. Visual only; the walk's own collider is untouched.
Origin on the walk at the gap's edge, centred on the beam; the stone lies on the walk toward Blender -Y (Godot +Z),
top at 0.013, flush enough to step over. 1.7 m wide, 0.55 deep, two brass studs; the light falls across it."""
import math

import kit


def build(args):
    P = []
    # one worn threshold slab, nearly flush with the walk: the light lands on it, it is not the start of a deck
    P.append(kit.box("stone", (1.7, 0.55, 0.05), (0, -0.275, -0.012), mat="sill_stone", bevel=0.01))
    for sx in (-1, 1):
        P.append(kit.lathe("stud", [(0.0, 0.0), (0.035, 0.0), (0.03, 0.012), (0.0, 0.016)], segments=10, mat="brass"))
        P[-1].location = (sx * 0.7, -0.3, 0.014)
    kit.join("sill", P)
