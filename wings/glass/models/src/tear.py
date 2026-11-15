"""The Rose Widow's tear and its dais. Arg:
  tear  a cut violet glass teardrop (flat facets) held in a four-claw brass cradle on a slender stem
        rising from the dais; origin at the dais top (floor), the drop's centre 1.2 m up.
  dais  the round dais it stands on: 3.9 m radius, 0.4 m deep, moulded edge, brass and lead rings;
        origin at its top centre (the collider stays the code-built cylinder)."""
import math

import kit


def tear():
    p = []
    # the drop: 12 facets around, pointed top, rounded belly
    prof = [(0.0, 0.74), (0.2, 0.8), (0.33, 0.93), (0.38, 1.1), (0.33, 1.25), (0.2, 1.42), (0.08, 1.55), (0.0, 1.66)]
    p.append(kit.lathe("drop", prof, 12, mat="tear", smooth_angle=None))
    # cradle: a cup ring and four claws up the belly
    p.append(kit.torus("cup", 0.24, 0.025, 32, 8, mat="brass", loc=(0, 0, 0.86)))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        p.append(kit.tube("claw%d" % k, [(c * 0.22, s * 0.22, 0.84), (c * 0.33, s * 0.33, 0.95), (c * 0.37, s * 0.37, 1.08), (c * 0.3, s * 0.3, 1.18)], 0.018, 6, mat="brass"))
    # stem: baluster with a knop, on a stepped foot
    stem = [(0.0, 0.0), (0.42, 0.0), (0.42, 0.05), (0.3, 0.09), (0.26, 0.14), (0.09, 0.2), (0.06, 0.34), (0.11, 0.42), (0.11, 0.48),
            (0.05, 0.56), (0.05, 0.74), (0.14, 0.8), (0.2, 0.84), (0.0, 0.84)]
    p.append(kit.lathe("stem", stem, 32, mat="brass"))
    p.append(kit.torus("knop_ring", 0.11, 0.015, 24, 6, mat="lead", loc=(0, 0, 0.45)))
    kit.join("rose_tear", p)


def dais():
    prof = [(0.0, -0.4), (3.75, -0.4), (3.9, -0.34), (3.95, -0.24), (3.86, -0.16), (3.9, -0.06), (3.85, 0.0), (0.0, 0.0)]
    p = [kit.lathe("dais", prof, 96, mat="glass_red_m")]
    p.append(kit.torus("edge_brass", 3.9, 0.035, 96, 8, mat="brass", loc=(0, 0, -0.02)))
    p.append(kit.torus("ring_lead", 2.6, 0.03, 96, 6, mat="lead", loc=(0, 0, 0.0)))
    p.append(kit.torus("ring_lead2", 1.3, 0.03, 64, 6, mat="lead", loc=(0, 0, 0.0)))
    for k in range(16):  # lead spokes: the dais is a small rose of its own
        a = k * math.pi / 8
        p.append(kit.tube("spoke%d" % k, [(math.cos(a) * 0.5, math.sin(a) * 0.5, 0.005), (math.cos(a) * 3.8, math.sin(a) * 3.8, 0.005)], 0.025, 6, mat="lead"))
    kit.join("rose_dais", p)


def build(args):
    dais() if args and args[0] == "dais" else tear()
