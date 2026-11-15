"""Windows of the Vitrine Kingdom. Arg = part (Blender X right, Z up, facing -Y = Godot +Z):
  lancet_pane    the glass of a lancet: 1 m wide, 3.5 m tall, origin at its centre; UV 0..1 over the
                 whole lancet so one image fills it (black outside the arch is lead).
  lancet_frame   moulded lead/brass frame round the lancet, plus horizontal saddle bars (ferramenta).
  rose_pane      a disc of radius 1, UV 0..1 (planar), centred.
  rose_tracery   radius 1: moulded outer ring, centre roundel ring, 16 spokes with cusped heads,
                 16 small roundels near the rim. All visual (no colliders)."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import pointed  # noqa: E402

H = 3.5
RISE = 0.866


def outline(n=20):
    """Closed lancet outline (x, z), counter-clockwise from the bottom-left."""
    spring = H / 2 - RISE
    arch = [(h, spring + y) for h, y in pointed(1.0, RISE, n)]  # left springer -> apex -> right
    return [(-0.5, -H / 2), (0.5, -H / 2)] + list(reversed(arch))


def lancet_pane():
    bm = bmesh.new()
    pts = outline(24)
    verts = [bm.verts.new((x, 0, z)) for x, z in pts]
    f = bm.faces.new(verts)
    uv = bm.loops.layers.uv.new("UVMap")
    for loop in f.loops:
        x, _, z = loop.vert.co
        loop[uv].uv = (x + 0.5, (z + H / 2) / H)
    bmesh.ops.triangulate(bm, faces=[f])
    f2 = [ff for ff in bm.faces]
    for ff in f2:
        if ff.normal.y > 0:
            ff.normal_flip()
    kit._obj("lancet_pane", bm, "window", None)


def lancet_frame():
    pts = [(x, 0.0, z) for x, z in outline(20)]
    p = [kit.sweep_closed("frame", [(-0.02, -0.07), (0.05, -0.09), (0.1, -0.06), (0.14, -0.02), (0.16, 0.05), (-0.02, 0.05)], pts, mat="lead", smooth_angle=50.0)]
    p.append(kit.sweep_closed("roll", [(0.03 + 0.025 * math.cos(a), -0.1 + 0.025 * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]], pts, mat="brass", smooth_angle=70.0))
    spring = H / 2 - RISE
    for k in range(1, 7):
        z = -H / 2 + k * 0.48
        if z > spring + 0.3:
            break
        p.append(kit.box("bar%d" % k, (1.0, 0.03, 0.022), (0, -0.03, z), mat="lead", bevel=0.006))
    # the central iron upright of the armature
    p.append(kit.box("upright", (0.022, 0.03, H - RISE * 0.6), (0, -0.03, -RISE * 0.3), mat="lead", bevel=0.006))
    kit.join("lancet_frame", p)


def _ring(name, r, w, d, mat, seg=96):
    ob = kit.lathe(name, [(r - w, -d), (r + w, -d), (r + w * 1.2, 0.0), (r + w, d), (r - w, d), (r - w * 1.2, 0.0), (r - w, -d)], seg, mat=mat, smooth_angle=50.0, cap=False)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    return ob


def rose_pane():
    bm = bmesh.new()
    n = 96
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((math.cos(2 * math.pi * i / n), 0, math.sin(2 * math.pi * i / n))) for i in range(n)]
    uv = bm.loops.layers.uv.new("UVMap")
    for i in range(n):
        f = bm.faces.new((c, ring[(i + 1) % n], ring[i]))
        for loop in f.loops:
            x, _, z = loop.vert.co
            loop[uv].uv = ((x + 1) / 2, (z + 1) / 2)
        if f.normal.y > 0:
            f.normal_flip()
    kit._obj("rose_pane", bm, "window", None)


def rose_tracery():
    p = [_ring("rim", 1.0, 0.035, 0.07, "lead"), _ring("rim_roll", 1.04, 0.012, 0.09, "brass")]
    p.append(_ring("hub", 0.39, 0.022, 0.06, "lead"))
    p.append(_ring("hub_roll", 0.41, 0.008, 0.075, "brass"))
    p.append(_ring("petal_ring", 0.83, 0.014, 0.05, "lead"))
    n = 16
    off = math.pi / 2 + math.pi / n
    for k in range(n):
        a = off + 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)
        bar = kit.box("spoke%d" % k, (0.44, 0.1, 0.028), (0, 0, 0), mat="lead", bevel=0.008)
        bar.location = (ca * 0.61, 0, sa * 0.61)
        bar.rotation_euler = (0, -a, 0)
        p.append(bar)
        # cusped head: a trefoil-ish arc joining this spoke to the next just inside the petal ring
        b = a + 2 * math.pi / n
        pts = []
        for i in range(13):
            t = i / 12
            ang = a + (b - a) * t
            r = 0.76 + 0.06 * math.sin(math.pi * t) - 0.025 * math.sin(3 * math.pi * t)
            pts.append((math.cos(ang) * r, -0.01, math.sin(ang) * r))
        p.append(kit.tube("cusp%d" % k, pts, 0.014, 6, mat="lead"))
        # rim roundels, centred on the petals
        m = (a + b) / 2
        rd = kit.torus("roundel%d" % k, 0.055, 0.011, 24, 6, mat="lead", loc=(math.cos(m) * 0.915, 0, math.sin(m) * 0.915), rot=(math.pi / 2, 0, 0))
        p.append(rd)
    kit.join("rose_tracery", p)


def build(args):
    {"lancet_pane": lancet_pane, "lancet_frame": lancet_frame, "rose_pane": rose_pane, "rose_tracery": rose_tracery}[args[0]]()
