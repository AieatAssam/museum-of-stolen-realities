"""Upper storey of one atrium bay (sits on the giant columns, z 16.9 -> 31). Faces -Y.
Entablature (architrave, gilt frieze, dentilled cornice), a balustraded gallery, and a three-arch
arcade whose openings fall away into darkness. Back plane at y=0 is the wall line."""
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

W = 12.9
T15 = math.tan(math.radians(15))


def slab(name, z0, h, d0, d1, mat, bevel=0.02):
    """Box from y=-d0 (back) to y=-d1 (front), mitred so neighbouring bays meet at 30 degrees."""
    bm = bmesh.new()
    vs = []
    for y in (-d0, -d1):
        hw = W / 2 - (-y) * T15
        for z in (z0, z0 + h):
            vs.append([bm.verts.new((-hw, y, z)), bm.verts.new((hw, y, z))])
    (b0, b1), (t0, t1) = (vs[0], vs[1]), (vs[2], vs[3])
    faces = [(b0[0], b0[1], b1[1], b1[0]), (t0[0], t1[0], t1[1], t0[1]), (b0[0], t0[0], t0[1], b0[1]),
             (b1[0], b1[1], t1[1], t1[0]), (b0[0], b1[0], t1[0], t0[0]), (b0[1], t0[1], t1[1], b1[1])]
    for f in faces:
        bm.faces.new(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 30.0)


def build(args):
    p = []
    p.append(slab("architrave", 16.9, 0.9, 0.0, 2.8, "marble_ivory"))
    p.append(slab("arch_fascia", 17.55, 0.08, 0.0, 2.86, "gilt"))
    p.append(slab("frieze", 17.8, 1.0, 0.0, 2.65, "marble_black"))
    p.append(slab("frieze_band", 18.1, 0.4, 0.0, 2.7, "gilt"))
    p.append(slab("cornice_a", 18.8, 0.18, 0.0, 3.0, "gilt"))
    p.append(slab("cornice_b", 18.98, 0.5, 0.0, 3.35, "marble_ivory"))
    for i in range(30):  # dentils
        x = -W / 2 + 3.0 * T15 + (i + 0.5) * (W - 6.0 * T15) / 30
        p.append(kit.box("dent%d" % i, (0.18, 0.2, 0.22), (x, -3.05, 18.85), mat="marble_ivory"))
    # balustrade
    p.append(slab("bal_base", 19.48, 0.15, 2.7, 3.25, "marble_ivory"))
    p.append(slab("bal_rail", 20.55, 0.14, 2.65, 3.3, "gilt"))
    hw = W / 2 - 3.0 * T15
    n = 22
    for i in range(n):
        x = -hw + (i + 0.5) * 2 * hw / n
        b = kit.lathe("bal%d" % i, [(0.11, 0.0), (0.11, 0.06), (0.07, 0.12), (0.13, 0.35), (0.07, 0.62), (0.05, 0.7), (0.09, 0.78), (0.09, 0.92), (0.0, 0.92)], 10, mat="marble_ivory")
        kit.place(b, (x, -2.97, 19.63))
        p.append(b)
    # gallery floor/back wall
    p.append(slab("gal_floor", 19.3, 0.2, 0.0, 2.7, "marble_black"))
    p.append(kit.box("back", (W, 0.4, 12.0), (0, 0.2, 25.0), mat="damask"))
    # arcade: three openings (dark recess), gilt archivolts, ivory piers
    for k, x in enumerate((-4.0, 0.0, 4.0)):
        r, spring = 1.35, 24.8
        # dark opening: semicircle-headed plane just in front of the wall
        bm = bmesh.new()
        ring = [bm.verts.new((x - r, -0.02, 19.5)), bm.verts.new((x + r, -0.02, 19.5))]
        for j in range(17):
            a = math.pi * j / 16
            ring.append(bm.verts.new((x + r * math.cos(a), -0.02, spring + r * math.sin(a))))
        bm.faces.new(ring[:1] + ring[1:2] + ring[2:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = kit._obj("void%d" % k, bm, "void", None)
        p.append(ob)
        pts = [(x + r + 0.12, -0.15, 19.5), (x + r + 0.12, -0.15, spring)]
        pts += [(x + (r + 0.12) * math.cos(math.pi * j / 20), -0.15, spring + (r + 0.12) * math.sin(math.pi * j / 20)) for j in range(1, 20)]
        pts += [(x - r - 0.12, -0.15, spring), (x - r - 0.12, -0.15, 19.5)]
        p.append(orn.taper("archivolt%d" % k, pts, [0.14] * len(pts), 8, "gilt"))
        p.append(kit.box("key%d" % k, (0.4, 0.35, 0.6), (x, -0.2, spring + r + 0.2), mat="marble_ivory", bevel=0.03))
    for k, x in enumerate((-6.0, -2.0, 2.0, 6.0)):
        p.append(kit.box("pier%d" % k, (0.9 if abs(x) < 5 else 0.6, 0.5, 9.5), (x, -0.25, 24.25), mat="marble_ivory", bevel=0.03))
        p.append(kit.box("piercap%d" % k, (1.1 if abs(x) < 5 else 0.75, 0.62, 0.3), (x, -0.3, 29.0), mat="gilt", bevel=0.03))
    p.append(slab("top_cornice", 29.15, 0.6, 0.0, 1.2, "marble_ivory"))
    p.append(slab("top_band", 29.75, 0.15, 0.0, 1.35, "gilt"))
    kit.join("gallery", p)
