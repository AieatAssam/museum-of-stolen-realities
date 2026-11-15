"""Fluted giant-order column, 16.9 m to the top of the abacus, carrying the gallery entablature.
Black marble plinth, gilt Attic base, ivory fluted shaft, gilt Corinthian capital (two rows of
acanthus, corner volutes). Origin at floor centre."""
import math
import os
import sys

import bmesh
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

SHAFT_TOP = 15.0


def build(args):
    parts = []
    parts.append(kit.box("plinth", (3.1, 3.1, 0.5), (0, 0, 0.25), mat="marble_black", bevel=0.03))
    parts.append(kit.lathe("base", [(1.5, 0.5), (1.5, 0.6), (1.38, 0.66), (1.38, 0.72), (1.3, 0.78), (1.34, 0.88), (1.2, 0.96), (1.12, 1.04), (1.06, 1.1), (0.0, 1.1)], 48, mat="gilt"))
    flutes, seg_a, rings = 24, 24 * 4, 10
    bm = bmesh.new()
    vs = []
    for j in range(rings + 1):
        z = 1.1 + (SHAFT_TOP - 1.1) * j / rings
        r0 = 1.02 - 0.1 * (j / rings)
        row = []
        for i in range(seg_a):
            a = 2 * math.pi * i / seg_a
            r = r0 - [0.0, 0.055, 0.07, 0.055][i % 4]
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        vs.append(row)
    for j in range(rings):
        for i in range(seg_a):
            bm.faces.new((vs[j][i], vs[j][(i + 1) % seg_a], vs[j + 1][(i + 1) % seg_a], vs[j + 1][i]))
    parts.append(kit._obj("shaft", bm, "marble_ivory", 50.0))
    parts.append(kit.torus("astragal", 0.94, 0.07, 48, 8, mat="gilt", loc=(0, 0, SHAFT_TOP + 0.02)))
    # capital bell
    z0 = SHAFT_TOP + 0.08
    parts.append(kit.lathe("bell", [(0.9, z0), (0.92, z0 + 0.5), (1.0, z0 + 1.0), (1.18, z0 + 1.35), (0.0, z0 + 1.35)], 32, mat="gilt"))
    for row, (h, ln, n) in enumerate([(0.05, 0.75, 8), (0.45, 0.8, 8)]):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * row) / n
            d = (math.cos(a), math.sin(a), 0)
            base = (0.9 * d[0], 0.9 * d[1], z0 + h)
            parts.append(orn.leaf("ac%d_%d" % (row, k), base, (d[0] * 0.25, d[1] * 0.25, 1), ln, 0.24, curl=1.1, lift=d, n=12))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        m = Matrix.Translation((math.cos(a) * 1.15, math.sin(a) * 1.15, z0 + 1.15)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        parts.append(orn.scroll("vol%d" % k, m, 0.3, 0.05, 1.3, 0.1, 0.03, n=20, sides=8))
    parts.append(kit.box("abacus", (2.9, 2.9, 0.4), (0, 0, z0 + 1.55), mat="marble_ivory", bevel=0.04))
    parts.append(kit.box("abacus_g", (2.98, 2.98, 0.08), (0, 0, z0 + 1.37), mat="gilt", bevel=0.02))
    kit.join("column", parts)
    kit.box("column-convcolonly", (2.2, 2.2, 12.0), (0, 0, 6.0))
