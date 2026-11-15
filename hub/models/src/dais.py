"""Exhibit 0's stepped dais: five black-marble steps (r 7.6 -> 3.4 m) with gilt nosings and brass
inlay, a fluted gilt cradle that holds the sphere, and the armillary rings (separate objects
ring_a/b/c so Godot can turn them; their origin is the sphere centre, built at z=0)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

STEPS = [(7.6, 0.18), (6.7, 0.36), (5.8, 0.54), (4.8, 0.72), (3.7, 0.9)]


def build(args):
    prof = [(STEPS[0][0], 0.0)]
    for i, (r, z) in enumerate(STEPS):
        prof += [(r, z - 0.02), (r - 0.06, z)]
        nxt = STEPS[i + 1][0] if i + 1 < len(STEPS) else 0.0
        if nxt > 0:
            prof.append((nxt + 0.0001, z))
    prof.append((0.0, STEPS[-1][1]))
    kit.lathe("dais-col", prof, 96, mat="marble_black", smooth_angle=30.0)
    for i, (r, z) in enumerate(STEPS):
        kit.torus("nosing%d" % i, r - 0.02, 0.03, 128, 6, mat="gilt", loc=(0, 0, z - 0.02))
        kit.torus("inlay%d" % i, r - 0.45, 0.018, 128, 4, mat="brass", loc=(0, 0, z + 0.002))
    # cradle: fluted stem rising into a gilt cup of acanthus that holds the sphere from below
    top = STEPS[-1][1]
    stem = kit.lathe("stem", [(1.1, top), (1.0, top + 0.15), (0.6, top + 0.3), (0.42, top + 0.5), (0.3, top + 1.1), (0.26, top + 2.0), (0.34, top + 2.1), (0.5, top + 2.25), (0.0, top + 2.3)], 32, mat="gilt")
    parts = [stem]
    for k in range(10):
        a = 2 * math.pi * k / 10
        d = (math.cos(a), math.sin(a), 0)
        parts.append(orn.leaf("cup%d" % k, (d[0] * 0.4, d[1] * 0.4, top + 2.15), (d[0] * 0.8, d[1] * 0.8, 1), 1.1, 0.26, curl=1.2, lift=d, n=12))
        parts.append(orn.leaf("foot%d" % k, (d[0] * 1.0, d[1] * 1.0, top + 0.1), (d[0], d[1], 0.9), 0.55, 0.2, curl=1.0, lift=d, n=10))
    kit.join("stem", parts)
    kit.torus("ring_a", 3.6, 0.06, 160, 10, mat="brass", loc=(0, 0, 0))
    kit.torus("ring_b", 3.85, 0.05, 160, 10, mat="gilt", loc=(0, 0, 0), rot=(math.radians(90), 0, 0))
    kit.torus("ring_c", 4.1, 0.045, 160, 10, mat="gilt", loc=(0, 0, 0), rot=(math.radians(66), math.radians(20), 0))
