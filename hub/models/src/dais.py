"""Exhibit 0's circular dais (3 steps, r = 5.5 m) with a brass inlay ring + the armillary rings
(separate objects ring_a/b/c so Godot can turn them)."""
import math
import kit


def build(args):
    prof = [(5.5, 0.0), (5.5, 0.16), (5.42, 0.18), (4.7, 0.18), (4.7, 0.34), (4.62, 0.36), (3.9, 0.36), (3.9, 0.52), (3.82, 0.54), (0.0, 0.54)]
    d = kit.lathe("dais-col", prof, 96, mat="marble_black", smooth_angle=30.0)
    for i, r in enumerate((5.46, 4.66, 3.86)):
        kit.torus("inlay%d" % i, r, 0.035, 128, 6, mat="brass", loc=(0, 0, 0.16 + i * 0.18))
    # central stand: a slender gilt stem that the sphere hovers above
    kit.lathe("stem", [(0.6, 0.54), (0.55, 0.7), (0.3, 0.8), (0.16, 1.2), (0.12, 2.3), (0.24, 2.45), (0.34, 2.6), (0.0, 2.62)], 32, mat="gilt")
    # armillary rings (origin at sphere centre z=5.2)
    kit.torus("ring_a", 2.75, 0.045, 160, 10, mat="brass", loc=(0, 0, 0))
    kit.torus("ring_b", 2.95, 0.04, 160, 10, mat="brass", loc=(0, 0, 0), rot=(math.radians(90), 0, 0))
    kit.torus("ring_c", 3.15, 0.035, 160, 10, mat="gilt", loc=(0, 0, 0), rot=(math.radians(66), math.radians(20), 0))
