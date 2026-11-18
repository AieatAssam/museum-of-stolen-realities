"""A threshold stone for where a light bridge meets the walk. Visual only; the walk's own collider is untouched.
Origin on the walk at the gap's edge, centred on the beam; the stone lies on the walk toward Blender -Y (Godot +Z),
top at 0.025 (a hand's breadth proud of nothing: flush enough to step over). 1.9 m wide: the 1.35 m beam plus a
kerb stone either side. A brass nosing on the gap edge, a gold glass inlay between two brass studs, lead-lined joints."""
import math

import kit


def build(args):
    P = []
    # the stone: pale walk-stone, bevelled, a faint rise toward the gap so the edge reads
    P.append(kit.box("stone", (1.9, 0.7, 0.07), (0, -0.35, -0.01), mat="sill_stone", bevel=0.012))
    # a brass nosing at the gap edge, exactly the beam's 1.35 m wide
    P.append(kit.box("nosing", (1.35, 0.07, 0.04), (0, -0.035, 0.012), mat="brass", bevel=0.008))
    # the kerb stones either side of the beam: darker lead blocks that end the nosing
    for sx in (-1, 1):
        P.append(kit.box("kerb", (0.28, 0.7, 0.05), (sx * 0.81, -0.35, 0.01), mat="lead", bevel=0.01))
    # a gold-glass inlay (three lozenges), the beam's colour on the stone: the place to step
    for k, y in enumerate((-0.4,)):
        w = 0.3
        d = kit.box("lozenge", (w, w, 0.014), (0, y, 0.021), mat="brass", bevel=0.003)
        d.rotation_euler[2] = math.pi / 4
        P.append(d)
    for sx in (-1, 1):
        P.append(kit.lathe("stud", [(0.0, 0.0), (0.035, 0.0), (0.03, 0.012), (0.0, 0.016)], segments=10, mat="brass"))
        P[-1].location = (sx * 0.5, -0.4, 0.026)
    kit.join("sill", P)
