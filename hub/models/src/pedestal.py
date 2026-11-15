"""THE THIEF, ACQUIRED. A round stepped plinth (top at 0.42 m) carrying an empty, person-sized
vitrine (1.2 x 1.2 x 2.35 m, brass-framed glass) with a headless brass display stand inside, and a
small brass lectern in front (top at 1.15 m, at y = -1.2) for the sketch and the label."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

TOP = 0.42
CASE = (1.2, 1.2, 2.35)


def build(args):
    p = []
    p.append(kit.lathe("plinth", [(1.15, 0.0), (1.15, 0.16), (1.08, 0.2), (0.98, 0.2), (0.98, 0.36), (0.92, 0.4), (0.92, TOP), (0.0, TOP)], 64, mat="marble_black", smooth_angle=30.0))
    p.append(kit.torus("band", 1.12, 0.025, 96, 6, mat="gilt", loc=(0, 0, 0.18)))
    p.append(kit.torus("band2", 0.95, 0.02, 96, 6, mat="gilt", loc=(0, 0, 0.38)))
    # brass case frame
    hx, hy, h = CASE[0] / 2, CASE[1] / 2, CASE[2]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(kit.box("post%d%d" % (sx, sy), (0.05, 0.05, h), (sx * hx, sy * hy, TOP + h / 2), mat="brass", bevel=0.006, segments=1))
    for z in (TOP + 0.03, TOP + h):
        p.append(kit.box("rx%d" % int(z * 10), (CASE[0] + 0.06, 0.05, 0.05), (0, -hy, z), mat="brass", bevel=0.006, segments=1))
        p.append(kit.box("rx2%d" % int(z * 10), (CASE[0] + 0.06, 0.05, 0.05), (0, hy, z), mat="brass", bevel=0.006, segments=1))
        p.append(kit.box("ry%d" % int(z * 10), (0.05, CASE[1] + 0.06, 0.05), (-hx, 0, z), mat="brass", bevel=0.006, segments=1))
        p.append(kit.box("ry2%d" % int(z * 10), (0.05, CASE[1] + 0.06, 0.05), (hx, 0, z), mat="brass", bevel=0.006, segments=1))
    p.append(kit.box("lid", (CASE[0] + 0.12, CASE[1] + 0.12, 0.08), (0, 0, TOP + h + 0.06), mat="ebony", bevel=0.01))
    p.append(kit.lathe("finial", [(0.0, 0.0), (0.08, 0.0), (0.05, 0.08), (0.07, 0.16), (0.0, 0.26)], 16, mat="gilt"))
    p[-1].location = (0, 0, TOP + h + 0.1)
    # the stand inside: a headless brass armature at human height, shoulders and nothing else
    p.append(kit.lathe("stand_base", [(0.28, 0.0), (0.28, 0.04), (0.06, 0.08), (0.0, 0.08)], 24, mat="brass"))
    p[-1].location = (0, 0, TOP)
    p.append(kit.tube("rod", [(0, 0, TOP + 0.05), (0, 0, TOP + 1.42)], 0.018, 8, mat="brass"))
    p.append(orn.taper("shoulders", [(-0.24, 0, TOP + 1.38), (-0.12, 0, TOP + 1.44), (0, 0, TOP + 1.46), (0.12, 0, TOP + 1.44), (0.24, 0, TOP + 1.38)], [0.02, 0.03, 0.035, 0.03, 0.02], 8, "brass"))
    p.append(kit.tube("neck", [(0, 0, TOP + 1.46), (0, 0, TOP + 1.6)], 0.02, 8, mat="brass"))
    p.append(kit.lathe("collar", [(0.0, 0.0), (0.05, 0.0), (0.04, 0.03), (0.0, 0.04)], 16, mat="brass"))
    p[-1].location = (0, 0, TOP + 1.6)
    kit.join("pedestal", p)
    kit.box("glass_front", (CASE[0], 0.01, h - 0.05), (0, -hy, TOP + h / 2), mat="glass")
    kit.box("glass_back", (CASE[0], 0.01, h - 0.05), (0, hy, TOP + h / 2), mat="glass")
    kit.box("glass_l", (0.01, CASE[1], h - 0.05), (-hx, 0, TOP + h / 2), mat="glass")
    kit.box("glass_r", (0.01, CASE[1], h - 0.05), (hx, 0, TOP + h / 2), mat="glass")
    # lectern for the sketch and the plate
    lec = [kit.lathe("lec", [(0.22, 0.0), (0.22, 0.03), (0.05, 0.06), (0.03, 0.1), (0.03, 1.02), (0.06, 1.06), (0.0, 1.07)], 16, mat="brass")]
    top = kit.box("lec_top", (0.5, 0.36, 0.03), (0, 0, 1.12), mat="ebony", bevel=0.006, segments=1)
    top.rotation_euler = (math.radians(14), 0, 0)
    lec.append(top)
    lj = kit.join("lectern", lec)
    lj.location = (0, -1.2, 0)
    kit.box("pedestal-convcolonly", (2.3, 2.3, 2.9), (0, 0, 1.45))
    kit.box("lectern-convcolonly", (0.5, 0.4, 1.15), (0, -1.2, 0.57))
