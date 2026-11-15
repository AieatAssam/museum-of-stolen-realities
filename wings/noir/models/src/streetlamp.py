"""Cast-iron streetlamp, 5.2 m. Origin at the foot of the pole. Lantern glass is material 'glass'
(Godot makes it emissive white at runtime). Pole and base carry convex collision."""
import math

import kit


def build(args):
    parts = []
    base = kit.lathe("base", [(0.0, 0.0), (0.26, 0.0), (0.24, 0.08), (0.17, 0.2), (0.13, 0.32), (0.0, 0.34)], 20, mat="iron")
    shaft = kit.lathe("shaft", [(0.11, 0.3), (0.085, 1.5), (0.07, 3.6), (0.09, 3.8), (0.075, 4.1), (0.0, 4.1)], 14, mat="iron")
    collar = kit.torus("collar", 0.1, 0.03, 24, 6, mat="iron", loc=(0, 0, 4.05))
    parts += [base, shaft, collar]
    # scroll arm reaching over the pavement (+X)
    arm = kit.tube("arm", [(0, 0, 4.25), (0.35, 0, 4.55), (0.75, 0, 4.6), (1.0, 0, 4.5)], 0.04, 8, mat="iron")
    parts.append(arm)
    # lantern: a glass drum on a flared iron cradle, capped by a cone
    cradle = kit.lathe("cradle", [(0.0, 4.35), (0.2, 4.36), (0.24, 4.42), (0.16, 4.45), (0.0, 4.45)], 16, mat="iron")
    glass = kit.lathe("lantern-glass", [(0.0, 4.45), (0.2, 4.45), (0.23, 4.7), (0.23, 4.92), (0.2, 5.0), (0.0, 5.0)], 16, mat="glass", smooth_angle=None)
    cap = kit.lathe("cap", [(0.0, 5.0), (0.3, 5.0), (0.27, 5.08), (0.08, 5.2), (0.0, 5.22)], 16, mat="iron")
    finial = kit.lathe("finial", [(0.0, 5.2), (0.05, 5.22), (0.03, 5.32), (0.0, 5.34)], 8, mat="iron")
    parts += [cradle, glass, cap, finial]
    for i in range(6):
        a = 2 * math.pi * i / 6
        bar = kit.box("cage", (0.012, 0.012, 0.8), (0.225 * math.cos(a), 0.225 * math.sin(a), 4.72), mat="iron")
        parts.append(bar)
    kit.join("streetlamp", parts)
    kit.box("pole-convcolonly", (0.3, 0.3, 4.2), (0, 0, 2.1))
