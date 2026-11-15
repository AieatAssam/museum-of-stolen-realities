"""Colossal fluted column, 40 m (top vanishes into darkness). Origin at floor centre."""
import math
import bmesh
import kit

H = 40.0


def build(args):
    base = kit.lathe("base", [(1.5, 0.0), (1.5, 0.55), (1.38, 0.6), (1.38, 0.68), (1.3, 0.75), (1.32, 0.86), (1.18, 0.95), (1.12, 1.05), (1.06, 1.1), (0.0, 1.1)], 48, mat="gilt")
    plinth = kit.box("plinth", (3.1, 3.1, 0.5), (0, 0, 0.25), mat="marble_black", bevel=0.03)
    # fluted shaft
    flutes, seg_a, rings = 24, 24 * 4, 18
    bm = bmesh.new()
    vs = []
    for j in range(rings + 1):
        z = 1.1 + (H - 1.1) * j / rings
        r0 = 1.02 - 0.12 * (j / rings)
        row = []
        for i in range(seg_a):
            a = 2 * math.pi * i / seg_a
            k = (i % 4)
            dent = [0.0, 0.055, 0.07, 0.055][k]
            r = r0 - dent
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        vs.append(row)
    for j in range(rings):
        for i in range(seg_a):
            bm.faces.new((vs[j][i], vs[j][(i + 1) % seg_a], vs[j + 1][(i + 1) % seg_a], vs[j + 1][i]))
    shaft = kit._obj("shaft", bm, "marble_ivory", 50.0)
    ring = kit.torus("collar", 1.02, 0.07, 64, 10, mat="gilt", loc=(0, 0, 9.0))
    ring2 = kit.torus("collar2", 1.0, 0.05, 64, 10, mat="gilt", loc=(0, 0, 9.25))
    kit.join("column", [plinth, base, shaft, ring, ring2])
    kit.box("column-convcolonly", (2.2, 2.2, 12.0), (0, 0, 6.0))
