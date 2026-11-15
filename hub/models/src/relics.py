"""Private Collection relics, one per provenance row (each sits on a plinth inside its vitrine,
origin at the vitrine floor): relic_0 a sealed reliquary orb on a claw stand, relic_1 a rolled
document with a wax seal and ribbon, relic_2 a medallion on a little easel. `relic_tint` surfaces
take the wing's colour in Godot."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402


def build(args):
    a = [kit.lathe("r0_base", [(0.09, 0.0), (0.09, 0.015), (0.05, 0.03), (0.02, 0.06), (0.03, 0.08), (0.0, 0.08)], 20, mat="gilt")]
    for k in range(4):
        t = k * math.pi / 2
        a.append(orn.taper("claw%d" % k, [(math.cos(t) * 0.02, math.sin(t) * 0.02, 0.07), (math.cos(t) * 0.07, math.sin(t) * 0.07, 0.12), (math.cos(t) * 0.06, math.sin(t) * 0.06, 0.18)], [0.01, 0.008, 0.004], 5, "gilt"))
    a.append(orn.ellipsoid("orb", (0, 0, 0.16), (0.14, 0.14, 0.14), "relic_tint", 20, 12))
    a.append(kit.torus("orb_band", 0.072, 0.006, 40, 5, mat="gilt", loc=(0, 0, 0.16), rot=(math.radians(90), 0, 0)))
    kit.join("relic_0", a)
    b = [kit.tube("scroll", [(-0.14, 0, 0.04), (0.14, 0, 0.04)], 0.035, 16, mat="sketch_paper")]
    for s in (-1, 1):
        b.append(kit.lathe("knob%d" % s, [(0.0, 0.0), (0.045, 0.0), (0.04, 0.015), (0.0, 0.02)], 12, mat="gilt"))
        b[-1].location = (s * 0.14, 0, 0.04)
        b[-1].rotation_euler = (0, math.radians(90 * s), 0)
    b.append(orn.taper("ribbon", [(0.02, -0.03, 0.06), (0.03, -0.05, 0.02), (0.05, -0.06, -0.0), (0.08, -0.08, 0.0)], [0.012, 0.012, 0.01, 0.006], 4, "relic_tint", flat=0.3))
    b.append(orn.ellipsoid("seal", (0.02, -0.037, 0.05), (0.04, 0.015, 0.04), "relic_tint", 12, 4))
    kit.join("relic_1", b)
    c = [kit.tube("e_l", [(-0.06, 0.03, 0.0), (0.0, 0.0, 0.22)], 0.004, 5, mat="brass"),
         kit.tube("e_r", [(0.06, 0.03, 0.0), (0.0, 0.0, 0.22)], 0.004, 5, mat="brass"),
         kit.tube("e_b", [(0.0, 0.09, 0.0), (0.0, 0.0, 0.2)], 0.004, 5, mat="brass")]
    med = kit.lathe("med", [(0.0, 0.0), (0.07, 0.0), (0.075, 0.008), (0.06, 0.016), (0.0, 0.02)], 28, mat="gilt")
    kit.place(med, (0, -0.01, 0.12), (math.radians(80), 0, 0))
    c.append(med)
    gem = orn.ellipsoid("gem", (0, -0.035, 0.12), (0.06, 0.03, 0.06), "relic_tint", 12, 6)
    c.append(gem)
    kit.join("relic_2", c)
