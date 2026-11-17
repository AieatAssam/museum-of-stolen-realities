"""The nave's west front as seen from the cloister: dressing for the flat glass_wall slab (glass.gd
_build_cloister, the wall at Godot z -18.5..-17.5 over x -18.5..18.5, y 0..26, with a 5 x 4.5 m doorway at
the bottom centre). Visual only: the slab and its colliders stay as they are.

Origin = the wall's cloister face at x 0, floor level (Godot (0, 0, -17.5)). Front is -Y (Godot +Z).
  - a moulded plinth along the foot of the wall (kept 0.12 m deep: people walk along it),
  - a portal round the doorway: three orders of shafts with capitals in each jamb,
    four-centred (Tudor) arches under a square label mould with gold-glass spandrels and roundels, and a
    leaded tympanum above the door head (all of it under the walk roof at 7.2 m),
  - four stepped buttresses from the cloister roof to the cornice, with set-offs and pinnacles,
  - string courses at the cloister roof and (outside the west lancets) at 13.4 m, and a cornice at the top.
"""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import roll, sweep  # noqa: E402

HALF = 17.5  # the cloister's side walls stand at |x| = 17.5
TOP = 26.0
DOOR_W, DOOR_H = 5.0, 4.5
BUTTRESS_X = (-12.0, -6.2, 6.2, 12.0)


def course(name, z, depth, height, mat, x0=-HALF, x1=HALF):
    """A string course: a chamfered moulding running along the wall face at height z."""
    sec = [(0.0, -height / 2), (depth * 0.6, -height / 2), (depth, -height * 0.1), (depth, height * 0.2),
           (depth * 0.8, height / 2), (0.0, height / 2)]
    path = [(x0, 0.0), (x1, 0.0)]
    # the path's in-plane normal is -Y, so section u runs out of the wall face; v is up
    return sweep(name, sec, path, mat,
                 place=lambda h, y, v: (h, y, z + v), smooth=40.0)


def shaft(name, x, depth, r, z0, z1, mat):
    s = kit.lathe(name, [(r * 1.5, 0.0), (r * 1.5, 0.12), (r, 0.2), (r, z1 - z0 - 0.3), (r * 1.6, z1 - z0 - 0.12),
                         (r * 1.6, z1 - z0)], 16, mat=mat)
    s.location = (x, -depth, z0)
    return s


def tudor(span, rise, n=28):
    """A four-centred arch centre-line (h, y) from the left springer to the right: steep haunches, a flat
    top meeting in a slight point."""
    out = []
    for i in range(n + 1):
        t = math.pi * i / n
        out.append((-span / 2 * math.cos(t), rise * (0.82 * math.sin(t) ** 0.55 + 0.18 * (1 - abs(math.cos(t))))))
    return out


def portal():
    p = []
    # jambs: three receding orders each side
    orders = [(DOOR_W / 2 + 0.18, 0.12, 0.11), (DOOR_W / 2 + 0.50, 0.24, 0.12), (DOOR_W / 2 + 0.82, 0.34, 0.13)]
    spring = DOOR_H + 0.15
    for s in (-1, 1):
        for i, (x, d, r) in enumerate(orders):
            p.append(shaft("jamb_shaft", s * x, d, r, 0.0, spring, "lead" if i % 2 == 0 else "brass"))
        block = kit.box("jamb", (1.1, 0.36, spring), (s * (DOOR_W / 2 + 0.55), -0.18, spring / 2), mat="glass_wall",
                        bevel=0.03)
        p.append(block)
    # arch orders: four-centred (Tudor) arches, low enough to stay under the cloister walk roof at 7.2 m
    for i, (x, d, r) in enumerate(orders):
        path = [(h, y + spring) for h, y in tudor(2 * x, 1.45 + 0.25 * i)]
        p.append(sweep("arch_roll", [(r * math.cos(a), -d + r * math.sin(a))
                                     for a in (2 * math.pi * k / 12 for k in range(12))], path,
                       "lead" if i % 2 == 0 else "brass", place=lambda h, y, v: (h, v, y), smooth=70.0))
    # square label (drip) mould over the arch, with returns and carved stops
    hx, top = orders[-1][0] + 0.32, spring + 2.25
    label = [(-hx, spring + 0.6), (-hx, top), (hx, top), (hx, spring + 0.6)]
    p.append(sweep("label", [(u, -0.44 + v) for u, v in roll(0.1, 10)], label, "brass",
                   place=lambda h, y, v: (h, v, y), smooth=70.0))
    for sx in (-1, 1):
        stop = kit.lathe("stop", [(0.0, -0.14), (0.12, -0.08), (0.14, 0.02), (0.08, 0.12), (0.0, 0.14)], 14, mat="brass")
        stop.location = (sx * hx, -0.44, spring + 0.5)
        p.append(stop)
    # spandrels between the arch and the label: leaded gold glass panels with a quatrefoil roundel each
    for sx in (-1, 1):
        bm = bmesh.new()
        outer = [(h, y + spring) for h, y in tudor(2 * orders[-1][0], 1.95)]
        half = [q for q in outer if sx * q[0] >= 0]
        pts = [(0.0, outer[len(outer) // 2][1])] + sorted(half, key=lambda q: abs(q[0]))[1:] + [(sx * hx, spring)] + [(sx * hx, top), (0.0, top)]
        vs = [bm.verts.new((h, -0.2, y)) for h, y in pts]
        bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        p.append(kit._obj("spandrel", bm, "glass_gold", 30.0))
        q = kit.torus("roundel", 0.32, 0.05, 24, 8, mat="lead")
        q.rotation_euler = (math.pi / 2, 0, 0)
        q.location = (sx * (hx - 0.75), -0.24, top - 0.5)
        p.append(q)
    # tympanum: a leaded gold glass panel filling the inner arch above the door head
    inner = 2 * orders[0][0]
    bm = bmesh.new()
    vs = [bm.verts.new((h, -0.06, max(y + spring, DOOR_H + 0.3))) for h, y in tudor(inner, 1.45, 20)]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    p.append(kit._obj("tympanum", bm, "glass_gold", 30.0))
    p.append(kit.box("lintel", (DOOR_W + 0.3, 0.2, 0.3), (0, -0.1, DOOR_H + 0.15), mat="lead", bevel=0.03))
    for k in (-1, 0, 1):  # tympanum mullions
        p.append(kit.box("mullion", (0.08, 0.1, 1.3 - 0.4 * abs(k)), (k * inner / 4, -0.08, spring + 0.65 - 0.2 * abs(k)),
                         mat="lead", bevel=0.01))
    return p


def buttress(x):
    p = []
    z0 = 7.5  # the cloister's walk roof hides the wall below
    steps = [(z0, 15.0, 1.3, 0.9), (15.0, 21.0, 1.1, 0.65), (21.0, TOP - 0.4, 0.9, 0.42)]
    for lo, hi, w, d in steps:
        p.append(kit.box("buttress", (w, d, hi - lo), (x, -d / 2, (lo + hi) / 2), mat="glass_wall", bevel=0.04))
        # set-off: a sloped weathering cap and a lead edge
        cap = kit.box("setoff", (w + 0.08, d + 0.08, 0.16), (x, -d / 2 - 0.02, hi), mat="lead", bevel=0.05)
        p.append(cap)
        for s in (-1, 1):  # corner shafts on each stage
            p.append(shaft("b_shaft", x + s * (w / 2 - 0.02), d - 0.02, 0.05, lo + 0.2, hi - 0.1, "brass"))
    pin = kit.lathe("pinnacle", [(0.32, 0.0), (0.32, 0.5), (0.24, 0.6), (0.12, 2.0), (0.0, 2.6)], 8, mat="lead")
    pin.location = (x, -0.25, TOP - 0.3)
    p.append(pin)
    return p


def build(args):
    p = []
    for x0, x1 in ((-HALF, -(DOOR_W / 2 + 1.1)), (DOOR_W / 2 + 1.1, HALF)):  # the doorway stays open
        p.append(course("plinth", 0.45, 0.12, 0.9, "lead", x0, x1))
    p.append(course("course_roof", 7.9, 0.22, 0.32, "brass"))
    for x0, x1 in ((-HALF, -6.2), (6.2, HALF)):  # stops at the inner buttresses: the west lancets lie between
        p.append(course("course_sill", 13.4, 0.2, 0.28, "lead", x0, x1))
    p.append(course("cornice", TOP - 0.35, 0.45, 0.7, "brass"))
    p += portal()
    for x in BUTTRESS_X:
        p += buttress(x)
    kit.join("west_front", p)
