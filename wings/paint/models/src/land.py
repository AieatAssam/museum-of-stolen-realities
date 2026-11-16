"""Paint wing landscape: the inside of an oil painting, out of doors. Orchard trees, a flame cypress, a
hedgerow, reeds, three village houses, a church, distant hills and a river bank. Every form is paint:
brush strokes (elliptic sections, tapered like a lifted brush), knife-laid slabs (lattice boxes with a
lumpy, leaning skin) and cupped daubs. Headless bmesh, deterministic (seeded). One script, selected by
args[0]; wings/paint/tools/build_land.sh builds them all.
Blender: +Z up, 1 unit = 1 m, origin at the base centre on the ground (hedge and bank run along +X).
Material names are the contract (Godot swaps them)."""
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nature as N  # noqa: E402  (Parts container and the daub/ico helpers)

TAU = 2 * math.pi
Z = Vector((0, 0, 1))


# --- brush helpers ------------------------------------------------------------------------------

def stroke(P, mat, pts, widths, sides=6, thick=0.35, ref=None, jit=0.02, jit_z=True):
    """A brush stroke along pts: elliptic section, width per point (thickness = width * thick), fan-capped.
    ref is the plane the stroke lies in (a roof normal for roof courses); default flat, or upright."""
    n, bm, rings = len(pts), P.bm(mat), []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if ref is None:
            r = Z if abs(d.z) < 0.9 else Vector((1, 0, 0))
        else:
            r = ref
        w = d.cross(r).normalized()
        t = d.cross(w).normalized()
        a = max(widths[i], 0.01) * 0.5
        b = a * thick
        rings.append([bm.verts.new(p + w * (a * math.cos(th)) + t * (b * math.sin(th)) + P.jit(jit, jit_z))
                      for th in (TAU * k / sides for k in range(sides))])
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    for end in (0, n - 1):
        c = bm.verts.new(pts[end])
        for k in range(sides):
            bm.faces.new((rings[end][k], rings[end][(k + 1) % sides], c))


def taper(width, n):
    """Brush-lift taper: full width mid-stroke, thin at both ends."""
    return [max(0.02, width * math.sin(math.pi * k / (n - 1)) ** 0.5) for k in range(n)]


def blob(P, mat, c, radii, rng, detail=1, lump=0.15):
    """A lumpy ellipsoid of dabs (icosphere, every vertex nudged)."""
    base, faces = N._ico(detail)
    cos = []
    for u in base:
        f = 1 + rng.uniform(-lump, lump)
        cos.append(c + Vector((u.x * radii[0] * f, u.y * radii[1] * f, u.z * radii[2] * f)))
    P.add(mat, cos, faces)


def box(P, mat, lo, hi, n=3, lean=(0.0, 0.0), amp=0.03):
    """A knife-laid slab: a closed box from lo to hi, cut n times per side. The top is leaned by lean
    (m per m of height) and every lattice point nudged by amp, so no face is flat or ruler-straight."""
    seed, idx, cos = P.rng.randrange(1 << 30), {}, []

    def vid(i, j, k):
        if (i, j, k) not in idx:
            r = random.Random(seed * 1009 + i * 131 + j * 17 + k)
            h = (hi.z - lo.z) * k / n
            p = Vector((lo.x + (hi.x - lo.x) * i / n + lean[0] * h,
                        lo.y + (hi.y - lo.y) * j / n + lean[1] * h,
                        lo.z + (hi.z - lo.z) * k / n))
            dz = r.uniform(-amp, amp) if k > 0 else 0.0
            idx[(i, j, k)] = len(cos)
            cos.append(p + Vector((r.uniform(-amp, amp), r.uniform(-amp, amp), dz)))
        return idx[(i, j, k)]

    faces = []
    for axis in range(3):
        o = [a for a in range(3) if a != axis]
        for side in (0, n):
            for u in range(n):
                for v in range(n):
                    quad = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        c = [0, 0, 0]
                        c[axis], c[o[0]], c[o[1]] = side, u + du, v + dv
                        quad.append(vid(*c))
                    faces.append(tuple(quad))
    P.add(mat, cos, faces)


def gable_roof(P, mat, xc, yc, z0, w, d, rise, ov=0.4, K=4):
    """Two pitched planes of overlapping brush courses running along X, with ragged eaves."""
    rng, R = P.rng, d / 2 + ov
    L = math.hypot(R, rise)
    for s in (-1, 1):
        along = Vector((0, -s * R, rise)).normalized()  # eave to ridge
        nrm = Vector((0, s * rise, R)).normalized()     # outward, up
        for layer in (0, 1):
            for k in range(K):
                u = (k + 0.25 + 0.5 * layer) / K
                c = Vector((xc, yc + s * R, z0)) + along * (L * u) + nrm * 0.1
                hw = w / 2 + rng.uniform(0.15, 0.5)
                pts = [c + Vector((x, 0.0, 0.0)) for x in (-hw, 0.0, hw)]
                stroke(P, mat, pts, [L / K * 1.6] * 3, sides=6, thick=0.22, ref=nrm, jit=0.03)


def gable_end(P, mat, x0, x1, yc, z0, d, rise):
    """Plaster triangle closing a gable, from plane x0 to x1."""
    tri = [(yc - d / 2, z0), (yc + d / 2, z0), (yc, z0 + rise)]
    cos = [Vector((x, y, z)) + P.jit(0.03) for x in (x0, x1) for y, z in tri]
    P.add(mat, cos, [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])


def finish(P, name, recalc=True):
    if recalc:
        for bm in P.bms.values():
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return P.write(name)


# --- orchard tree -------------------------------------------------------------------------------

ORCHARD = {"a": dict(limbs=5, blossom=14), "b": dict(limbs=4, blossom=0)}


def orchard(P, v, lod):
    rng, cfg = P.rng, ORCHARD[v]
    segs, sides = (4, 5) if lod else (8, 8)
    split = rng.uniform(2.6, 3.0)
    tw = rng.uniform(0.9, 1.3) * rng.choice((-1, 1))
    for j in range(2):  # two bark strands twisting round each other: a 0.4 m trunk
        pts, widths = [], []
        for k in range(segs + 1):
            t = k / segs
            ang = j * math.pi + tw * t
            R = 0.085 * (1 - 0.3 * t)
            pts.append(Vector((R * math.cos(ang), R * math.sin(ang), split * t)))
            widths.append(0.26 * (1 + 0.9 * math.exp(-9 * t)) * (1 - 0.2 * t))
        stroke(P, "p_bark", pts, widths, sides=sides, thick=0.7, jit=0.012, jit_z=False)
    # limbs: splay out of the split and end in the canopy clumps
    tips = []
    nl = segs // 2 + 1
    ss = [i / (nl - 1) for i in range(nl)]
    for k in range(cfg["limbs"]):
        a = TAU * k / cfg["limbs"] + rng.uniform(-0.3, 0.3)
        el = rng.uniform(0.45, 0.9)
        L = rng.uniform(2.0, 2.6)
        start = Vector((0.05 * math.cos(a), 0.05 * math.sin(a), split - 0.1))
        dr = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        perp = Vector((-math.sin(a), math.cos(a), 0.0))
        bow = rng.uniform(-0.2, 0.2)
        pts = [start + dr * (L * s) + perp * (bow * math.sin(math.pi * s)) for s in ss]
        stroke(P, "p_bark", pts, [0.24 * (1 - s) ** 0.6 + 0.05 for s in ss], sides=sides, thick=0.75, jit=0.02)
        tips.append(start + dr * L)
    clumps = [tp + Vector((0, 0, 0.2)) for tp in tips] + [Vector((0, 0, split + 1.7))]
    if lod:
        for c in clumps:
            mat = "p_leaf_light" if rng.random() < 0.3 else "p_leaf"
            blob(P, mat, c, [rng.uniform(1.2, 1.6), rng.uniform(1.1, 1.5), rng.uniform(0.9, 1.2)], rng, detail=1)
        return
    # canopy: brush ribbons swirled in clumps around the limb tips
    for _ in range(92):
        c = clumps[rng.randrange(len(clumps))]
        p = c + Vector((rng.gauss(0, 0.7), rng.gauss(0, 0.7), rng.gauss(0, 0.45)))
        r = math.hypot(p.x, p.y)
        if r > 2.7:
            p = Vector((p.x * 2.7 / r, p.y * 2.7 / r, p.z))
        phi = rng.uniform(0, TAU)
        el = rng.gauss(0, 0.3)
        d = Vector((math.cos(phi) * math.cos(el), math.sin(phi) * math.cos(el), math.sin(el)))
        L = rng.uniform(0.8, 1.6)
        bow = rng.uniform(-0.25, 0.25) * L
        perp = Vector((-math.sin(phi), math.cos(phi), 0.0))
        pts = [p + d * (L * (s - 0.5)) + perp * (bow * math.sin(math.pi * s)) for s in (0, 1 / 3, 2 / 3, 1)]
        mat = "p_leaf_light" if rng.random() < 0.3 else "p_leaf"
        stroke(P, mat, pts, taper(rng.uniform(0.25, 0.45), 4), sides=6, thick=0.3, jit=0.02)
    for _ in range(cfg["blossom"]):
        c = clumps[rng.randrange(len(clumps))] + Vector((rng.gauss(0, 0.8), rng.gauss(0, 0.8), rng.gauss(0.5, 0.3)))
        N.daub(P, "p_blossom", c, Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0.1)),
               Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))), 0.5, 0.36, 0.14, detail=1)


# --- cypress ------------------------------------------------------------------------------------

def cypress(P):
    rng = P.rng
    violet = set(rng.sample(range(40), 4))
    for i in range(40):
        a0 = rng.uniform(0, TAU)
        H = rng.uniform(10.5, 12.4)
        tw = rng.uniform(0.6, 1.4) * rng.choice((-1, 1))
        pts, widths = [], []
        for k in range(6):
            s = k / 5
            r = 0.1 + 1.05 * math.sin(math.pi * (0.08 + 0.8 * s)) ** 0.8 * (1 - 0.35 * s)
            ang = a0 + tw * s
            pts.append(Vector((r * math.cos(ang), r * math.sin(ang), 0.12 + (H - 0.12) * s)))
            widths.append(0.46 * (1 - s) ** 0.6 + 0.04)
        stroke(P, "p_violet" if i in violet else "p_leaf", pts, widths, sides=6, thick=0.35, jit=0.025)


# --- hedge and reeds ----------------------------------------------------------------------------

def hedge(P):
    rng = P.rng

    def top(x):
        return 1.62 + 0.18 * math.sin(0.9 * x + 0.4) + 0.08 * math.sin(2.7 * x)

    for i in range(8):  # low dark ground course
        x = -5.6 + 11.2 * i / 7
        pts = [Vector((x + 0.6 * s, rng.uniform(-0.2, 0.2), 0.12 + rng.uniform(-0.03, 0.03)))
               for s in (-1, -0.33, 0.33, 1)]
        stroke(P, "p_leaf", pts, taper(0.3, 4), sides=6, thick=0.35, jit=0.02)
    for _ in range(60):
        x = max(-5.6, min(5.6, rng.uniform(-5.9, 5.9)))
        z = max(0.25, top(x) - abs(rng.gauss(0, 0.3)))
        y = max(-0.5, min(0.5, rng.gauss(0, 0.25)))
        L = rng.uniform(0.8, 1.4)
        phi = rng.gauss(0, 0.35)
        d = Vector((math.cos(phi), math.sin(phi), rng.gauss(0, 0.12)))
        pts = [Vector((x, y, z)) + d * (L * (s - 0.5)) for s in (0, 1 / 3, 2 / 3, 1)]
        mat = "p_leaf_light" if rng.random() < 0.35 else "p_leaf"
        stroke(P, mat, pts, taper(rng.uniform(0.22, 0.32), 4), sides=6, thick=0.3, jit=0.02)
    for _ in range(7):  # a few flowers
        x = rng.uniform(-5.4, 5.4)
        z = top(x) - rng.uniform(0.0, 0.25)
        N.daub(P, "p_yellow", Vector((x, rng.uniform(-0.4, 0.4), z)), Vector((1, 0, 0)), Z, 0.24, 0.24, 0.1, detail=0)


def reeds(P):
    rng = P.rng
    for _ in range(32):
        a = rng.uniform(0, TAU)
        rr = 0.35 * math.sqrt(rng.random())
        base = Vector((rr * math.cos(a), rr * math.sin(a), 0.0))
        H = rng.uniform(1.2, 2.3)
        phi = rng.uniform(0, TAU)
        lean = rng.uniform(0.3, 1.25)
        pts = []
        for k in range(5):
            s = k / 4
            off = lean * s ** 2
            pts.append(base + Vector((math.cos(phi) * off, math.sin(phi) * off, H * s)))
        mat = "p_yellow" if rng.random() < 0.3 else "p_leaf_light"
        stroke(P, mat, pts, taper(0.075, 5), sides=4, thick=0.4, jit=0.01, jit_z=False)


# --- houses -------------------------------------------------------------------------------------

HOUSES = {
    "a": dict(w=8.0, d=6.0, h=4.4, rise=2.6, lean=0.012, door=-1.4,
              windows=[(0.9, 1.1, False), (2.7, 1.1, True)], chimney=None, lean_to=False),
    "b": dict(w=7.0, d=6.5, h=4.2, rise=2.8, lean=-0.01, door=-1.3,
              windows=[(1.5, 1.1, False), (-2.6, 1.1, False)], chimney=2.0, lean_to=False),
    "c": dict(w=6.0, d=6.5, h=6.4, rise=2.6, lean=0.0, door=-0.8,
              windows=[(1.2, 1.0, False), (-1.2, 3.9, False), (1.2, 3.9, False)], chimney=None, lean_to=True),
}


def house(P, v):
    cfg = HOUSES[v]
    w, d, H, rise, ly = cfg["w"], cfg["d"], cfg["h"], cfg["rise"], cfg["lean"]
    top_y = ly * H
    box(P, "p_plaster", Vector((-w / 2, -d / 2, 0.0)), Vector((w / 2, d / 2, H)), n=4, lean=(0.0, ly), amp=0.05)
    gable_roof(P, "p_roof", 0.0, top_y, H, w, d, rise, ov=0.4, K=4)
    gable_end(P, "p_plaster", -w / 2 - 0.15, -w / 2 + 0.12, top_y, H, d, rise)
    gable_end(P, "p_plaster", w / 2 - 0.12, w / 2 + 0.15, top_y, H, d, rise)
    yf = -d / 2
    dx = cfg["door"]
    box(P, "p_wood_dark", Vector((dx - 0.42, yf - 0.05, 0.0)), Vector((dx + 0.42, yf + 0.03, 2.15)), n=2, amp=0.012)
    for xw, zw, shutters in cfg["windows"]:
        box(P, "p_wood_dark", Vector((xw - 0.42, yf - 0.05, zw)), Vector((xw + 0.42, yf + 0.03, zw + 1.0)), n=2, amp=0.01)
        box(P, "p_plaster", Vector((xw - 0.55, yf - 0.12, zw - 0.14)), Vector((xw + 0.55, yf + 0.06, zw)), n=2, amp=0.012)
        if shutters:
            for x0, x1 in ((xw - 0.66, xw - 0.48), (xw + 0.48, xw + 0.66)):
                box(P, "p_blue", Vector((x0, yf - 0.06, zw + 0.02)), Vector((x1, yf + 0.01, zw + 0.98)), n=1, amp=0.008)
    if cfg["chimney"] is not None:
        cx = cfg["chimney"]
        top = H + rise
        box(P, "p_stone", Vector((cx - 0.35, 0.65, top - 0.9)), Vector((cx + 0.35, 1.35, top + 0.9)), n=2, amp=0.03)
        box(P, "p_wood_dark", Vector((cx - 0.45, 0.55, top + 0.9)), Vector((cx + 0.45, 1.45, top + 1.05)), n=1, amp=0.02)
    if cfg["lean_to"]:
        lean_to(P, w, d)
        stroke(P, "p_plaster", [Vector((x, -d / 2 - 0.05, 3.25)) for x in (-w / 2 - 0.1, 0.0, w / 2 + 0.1)],
               [0.22] * 3, sides=6, thick=0.5, jit=0.02)


def lean_to(P, w, d):
    """A single-pitch outbuilding against the +X wall: a wedge of plaster under a sloping roof."""
    x0, x1, h0, h1, y0, y1 = w / 2 - 0.2, w / 2 + 2.4, 2.9, 2.1, -2.3, 2.3
    prof = [(x0, 0.0), (x1, 0.0), (x1, h1), (x0, h0)]
    cos = [Vector((x, y, z)) + P.jit(0.03) for y in (y0, y1) for x, z in prof]
    P.add("p_plaster", cos, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    L = math.hypot(x1 - x0, h0 - h1)
    along = Vector((x1 - x0, 0.0, h1 - h0)).normalized()
    nrm = Vector((-(h1 - h0), 0.0, x1 - x0)).normalized()
    for k in range(3):
        c = Vector((x0, 0.0, h0)) + along * (L * (k + 0.5) / 3) + nrm * 0.1
        pts = [Vector((c.x, y, c.z)) for y in (y0 - 0.3, 0.0, y1 + 0.3)]
        stroke(P, "p_roof", pts, [L / 3 * 1.6] * 3, sides=6, thick=0.22, ref=nrm, jit=0.03)


# --- church -------------------------------------------------------------------------------------

def church(P):
    box(P, "p_plaster", Vector((-7.0, -3.5, 0.0)), Vector((3.0, 3.5, 5.5)), n=5, amp=0.05)
    gable_roof(P, "p_roof", -2.0, 0.0, 5.5, 10.0, 7.0, 3.6, ov=0.45, K=5)
    gable_end(P, "p_plaster", -7.15, -6.88, 0.0, 5.5, 7.0, 3.6)
    for xw in (-5.9, -3.2, 1.8):
        box(P, "p_wood_dark", Vector((xw - 0.3, -3.56, 2.3)), Vector((xw + 0.3, -3.44, 3.9)), n=1, amp=0.01)
        box(P, "p_wood_dark", Vector((xw - 0.3, 3.44, 2.3)), Vector((xw + 0.3, 3.56, 3.9)), n=1, amp=0.01)
    box(P, "p_wood_dark", Vector((-0.9, -3.58, 0.0)), Vector((-0.1, -3.42, 2.8)), n=2, amp=0.01)
    # tower: square, stone below, quoined corners, louvres, pointed cap
    box(P, "p_stone", Vector((3.0, -2.0, 0.0)), Vector((7.0, 2.0, 16.0)), n=4, amp=0.05)
    for cx in (3.0, 7.0):
        for cy in (-2.0, 2.0):
            sx = -1 if cx == 3.0 else 1
            sy = -1 if cy == -2.0 else 1
            for kk in range(8):
                z0 = 2.0 * kk + (0.2 if kk % 2 else 0.0)
                box(P, "p_plaster",
                    Vector((min(cx, cx + sx * 0.4), min(cy, cy + sy * 0.4), z0)),
                    Vector((max(cx, cx + sx * 0.4), max(cy, cy + sy * 0.4), z0 + 1.85)), n=1, amp=0.02)
    box(P, "p_wood_dark", Vector((4.2, -2.06, 12.8)), Vector((5.8, -1.94, 14.4)), n=1, amp=0.01)
    box(P, "p_wood_dark", Vector((6.94, -0.8, 12.8)), Vector((7.06, 0.8, 14.4)), n=1, amp=0.01)
    base = [(2.75, -2.25), (7.25, -2.25), (7.25, 2.25), (2.75, 2.25)]
    mid = [(3.35, -1.6), (6.65, -1.6), (6.65, 1.6), (3.35, 1.6)]
    cos = [Vector((x, y, 16.0)) for x, y in base] + [Vector((x, y, 17.7)) + P.jit(0.06) for x, y in mid]
    cos.append(Vector((5.0, 0.0, 19.6)))
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append((i, j, 4 + j, 4 + i))
        faces.append((4 + i, 4 + j, 8))
    P.add("p_roof", cos, faces)


# --- hills --------------------------------------------------------------------------------------

def hill_mass(P, W, D, H, flank):
    """Distant hill: overlapping knife-laid slabs, each a long brush lens along X, flattened at z = 0."""
    rng = P.rng
    for _ in range(rng.randint(12, 16)):
        length = rng.uniform(0.5, 0.7) * W
        xc = rng.uniform(-0.16 * W, 0.16 * W)
        yc = rng.uniform(-0.12 * D, 0.12 * D)
        hs = rng.uniform(0.5, 0.95) * H
        depth = rng.uniform(0.4, 0.6) * D
        ss = (0, 0.2, 0.4, 0.6, 0.8, 1.0)
        pts = [Vector((xc - length / 2 + length * s, yc, hs * rng.uniform(0.4, 0.5))) for s in ss]
        widths = [max(0.5, depth * math.sin(math.pi * s) ** 0.6) for s in ss]
        r = rng.random()
        if flank and yc < -0.05 * D and rng.random() < 0.6:
            mat = "p_violet"
        elif r < 0.45:
            mat = "p_leaf"
        elif r < 0.7:
            mat = "p_leaf_light"
        else:
            mat = "p_yellow"
        stroke(P, mat, pts, widths, sides=8, thick=hs / depth, ref=Z, jit=0.6, jit_z=True)
    for bm in P.bms.values():
        for v in bm.verts:
            if v.co.z < 0.0:
                v.co.z = 0.0


# --- river bank ---------------------------------------------------------------------------------

def bank(P):
    NX, NY = 41, 8

    def edge(x):
        return -0.5 + 0.10 * math.sin(1.3 * x + 0.4) + 0.06 * math.sin(3.7 * x + 1.1) + 0.03 * math.sin(7.1 * x)

    def back(x):
        return 3.0 + 0.12 * math.sin(0.9 * x + 2.0)

    grid = []
    for j in range(NY):
        t = j / (NY - 1)
        row = []
        for i in range(NX):
            x = -10 + 20 * i / (NX - 1)
            y = edge(x) + (back(x) - edge(x)) * t
            z = -0.4 + 0.75 * (y + 0.5) / 3.5 + 0.03 * math.sin(5.0 * x + 2.0 * y) * (1 - 0.5 * t)
            row.append(Vector((x, y, z)) + P.jit(0.015))
        grid.append(row)
    # one leaf-green top (grid quads, normals up by construction: x and y both increase)
    for j in range(NY - 1):
        for i in range(NX - 1):
            P.add("p_leaf", [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]], [(0, 1, 2, 3)])

    # long brush strokes laid over the top, running along X, each kept between edge(x)+0.3 and back(x)-0.2
    def surf(x, y):
        t = (y - edge(x)) / (back(x) - edge(x))
        return -0.4 + 0.75 * (y + 0.5) / 3.5 + 0.03 * math.sin(5.0 * x + 2.0 * y) * (1 - 0.5 * t)

    rng = P.rng
    for _ in range(rng.randint(7, 10)):
        L = rng.uniform(4.0, 9.0)
        x0 = rng.uniform(-9.5, 9.5 - L)
        n = rng.randint(5, 7)
        xs = [x0 + L * k / (n - 1) for k in range(n)]
        ws = taper(rng.uniform(0.4, 1.1), n)
        xm = x0 + L / 2
        yc = edge(xm) + 0.3 + rng.uniform(0.0, 1.0) * (back(xm) - 0.2 - edge(xm) - 0.3)
        wob, ph = rng.uniform(0.04, 0.12), rng.uniform(0, TAU)
        pts = []
        for k, (x, w) in enumerate(zip(xs, ws)):
            y = yc + wob * math.sin(TAU * k / (n - 1) + ph)
            y = min(max(y, edge(x) + 0.3 + w / 2), back(x) - 0.2 - w / 2)
            pts.append(Vector((x, y, surf(x, y) + 0.03)))
        mat = rng.choices(["p_leaf_light", "p_yellow", "p_stone"], weights=[0.7, 0.2, 0.1])[0]
        stroke(P, mat, pts, ws, sides=6, thick=0.12, ref=Z, jit=0.01)
    # skirt down to z = -0.8 around the edge, and a bottom, so the strip is a solid lip
    loop = (grid[0] + [grid[j][-1] for j in range(1, NY)] + [grid[-1][i] for i in range(NX - 2, -1, -1)]
            + [grid[j][0] for j in range(NY - 2, 0, -1)])
    n = len(loop)
    low = [Vector((p.x, p.y, -0.8)) for p in loop]
    for k in range(n):
        a, b, la, lb = loop[k], loop[(k + 1) % n], low[k], low[(k + 1) % n]
        quad = [a, b, lb, la]
        out = (a + b) * 0.5 - Vector((0.0, 1.25, 0.0))
        if (b - a).cross(la - a).dot(out) < 0:
            quad = quad[::-1]
        P.add("p_stone", quad, [(0, 1, 2, 3)])
    bottom = list(low)
    if (bottom[1] - bottom[0]).cross(bottom[2] - bottom[0]).z > 0:
        bottom = bottom[::-1]
    P.add("p_stone", bottom, [tuple(range(n))])


# --- torn canvas and stretcher (1 m unit models, centred on the origin) -------------------------

def torn_mass(P):
    """A mass of torn, paint-soaked canvas: rippled top, ragged plan outline, sagging underside, tatters."""
    rng = P.rng
    K, M, T = 48, 12, 3
    p0, p1, p2, ph = (rng.uniform(0, TAU) for _ in range(4))
    k_r = rng.randint(5, 8)
    ths = [TAU * k / K for k in range(K)]

    def outline(th):  # plan radius: squarish blob, ragged, kept within 0.43..0.53 of the centre
        c, s = math.cos(th), math.sin(th)
        r = 0.5 / max(abs(c), abs(s)) ** 0.15
        r *= 1 + 0.04 * math.sin(3 * th + p0) + 0.03 * math.sin(7 * th + p1) + 0.02 * math.sin(13 * th + p2)
        return min(0.53, max(0.43, r + rng.uniform(-0.01, 0.01)))

    R = [outline(th) for th in ths]
    streak = [rng.uniform(-0.02, 0.02) for _ in ths]

    def ridge(y):  # knife-laid ridges running along X
        return 1 - abs(math.sin(math.pi * k_r * y + ph))

    def top_z(x, y, f):
        return 0.47 - 0.05 * f * f + 0.04 * ridge(y)

    def bot_z(f, th):  # underside sags in the middle
        return -0.40 - 0.08 * (1 - f * f) + 0.03 * math.sin(2 * th + p1)

    cos, faces = [], []

    def vert(p):
        cos.append(p)
        return len(cos) - 1

    def disc(zf):  # centre vertex + M polar rings of K vertices each
        c = vert(Vector((0.0, 0.0, zf(0.0, 0.0, 0.0, 0))))
        rings = []
        for j in range(1, M + 1):
            f = j / M
            row = []
            for k in range(K):
                x, y = f * R[k] * math.cos(ths[k]), f * R[k] * math.sin(ths[k])
                row.append(vert(Vector((x, y, zf(x, y, f, k))) + P.jit(0.008, False)))
            rings.append(row)
        return c, rings

    def fan(c, rings):
        for k in range(K):
            faces.append((c, rings[0][k], rings[0][(k + 1) % K]))
        for j in range(M - 1):
            for k in range(K):
                k1 = (k + 1) % K
                faces.append((rings[j][k], rings[j + 1][k], rings[j + 1][k1], rings[j][k1]))

    tc, tr = disc(lambda x, y, f, k: top_z(x, y, f))
    bc, br = disc(lambda x, y, f, k: bot_z(f, ths[k]))
    fan(tc, tr)
    fan(bc, br)

    # ragged wall from the top outline down to the sagging bottom outline, with vertical streaks
    rows = [tr[-1]]
    for t in range(1, T):
        row = []
        for k in range(K):
            rr = R[k] * (1 + streak[k] * (1 - t / T))
            x, y = rr * math.cos(ths[k]), rr * math.sin(ths[k])
            zt, zb = top_z(x, y, 1.0), bot_z(1.0, ths[k])
            z = zt + (zb - zt) * t / T + 0.015 * math.sin(9 * ths[k] + 3 * t)
            row.append(vert(Vector((x, y, z))))
        rows.append(row)
    rows.append(br[-1])
    for a, b in zip(rows, rows[1:]):
        for k in range(K):
            k1 = (k + 1) % K
            faces.append((a[k], a[k1], b[k1], b[k]))

    # 8-14 tatters: cone-like tongues hanging from the underside edge
    for k in rng.sample(range(K), rng.randint(8, 14)):
        th = ths[k]
        cx, cy = 0.9 * R[k] * math.cos(th), 0.9 * R[k] * math.sin(th)
        z0 = bot_z(1.0, th) + 0.02
        r0, L, bend = rng.uniform(0.04, 0.07), rng.uniform(0.1, 0.25), rng.uniform(-0.03, 0.03)
        tx, ty = -math.sin(th) * bend, math.cos(th) * bend
        c0 = vert(Vector((cx, cy, z0)))
        ang = [TAU * i / 6 for i in range(6)]
        r_top = [vert(Vector((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0))) for a in ang]
        r_mid = [vert(Vector((cx + tx * 0.5 + 0.6 * r0 * math.cos(a), cy + ty * 0.5 + 0.6 * r0 * math.sin(a),
                              z0 - 0.55 * L))) for a in ang]
        tip = vert(Vector((cx + tx, cy + ty, z0 - L)))
        for i in range(6):
            i1 = (i + 1) % 6
            faces.append((c0, r_top[i1], r_top[i]))
            faces.append((r_top[i], r_top[i1], r_mid[i1], r_mid[i]))
            faces.append((r_mid[i], r_mid[i1], tip))
    P.add("p_canvas", cos, faces)


def brace(P, mat, a, b, w, z0, z1, amp=0.01):
    """A square bar of width w from plan point a to b, z0..z1, lightly jittered (box() is axis-aligned only)."""
    d = Vector((b[0] - a[0], b[1] - a[1], 0.0)).normalized()
    p = Vector((-d.y, d.x, 0.0)) * (w / 2)
    A, B = Vector((a[0], a[1], 0.0)), Vector((b[0], b[1], 0.0))
    lo = [A - p, A + p, B + p, B - p]
    cos = [q + Vector((0.0, 0.0, z0)) + P.jit(amp) for q in lo] + [q + Vector((0.0, 0.0, z1)) + P.jit(amp) for q in lo]
    P.add(mat, cos, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])


def stretcher_deck(P):
    """A painter's stretcher frame carrying a canvas: a 1 m floating platform. Four wood bars, a diagonal and a
    middle brace underneath; a lumpy canvas over the top, wrapped down the sides, one corner torn and curling."""
    wood, cv = "p_wood", "p_canvas"
    for lo, hi in (((-0.5, -0.5), (0.5, -0.38)), ((-0.5, 0.38), (0.5, 0.5)),
                   ((-0.5, -0.38), (-0.38, 0.38)), ((0.38, -0.38), (0.5, 0.38))):
        box(P, wood, Vector((lo[0], lo[1], -0.5)), Vector((hi[0], hi[1], 0.3)), n=2, amp=0.012)
    brace(P, wood, (-0.46, -0.46), (0.46, 0.46), 0.1, -0.5, -0.38)
    box(P, wood, Vector((-0.46, -0.05, -0.46)), Vector((0.46, 0.05, -0.38)), n=1, amp=0.01)

    # canvas: a closed shell. Top grid (lumpy, z ~0.5), skirt wrapping the outer edge down to z 0.2,
    # underside grid (z 0.3 inside, 0.2 at the edge, under the bars).
    N = 12

    def ztop(x, y):
        return 0.5 + 0.012 * math.sin(7 * x + 1) * math.cos(5 * y) + 0.008 * math.sin(11 * y + 2 * x + 0.3)

    def zbot(x, y):
        return 0.2 + 0.1 * min(1.0, max(0.0, 0.5 - max(abs(x), abs(y))) / 0.1)

    cos, faces = [], []
    T = [[0] * (N + 1) for _ in range(N + 1)]
    B = [[0] * (N + 1) for _ in range(N + 1)]
    for i in range(N + 1):
        for j in range(N + 1):
            x, y = -0.5 + i / N, -0.5 + j / N
            on = i in (0, N) or j in (0, N)
            cos.append(Vector((x, y, ztop(x, y))) + (Vector((0.0, 0.0, 0.0)) if on else P.jit(0.006)))
            T[i][j] = len(cos) - 1
            s = 1.01 if on else 1.0
            cos.append(Vector((x * s, y * s, zbot(x, y))) + (Vector((0.0, 0.0, 0.0)) if on else P.jit(0.006)))
            B[i][j] = len(cos) - 1
    for i in range(N):
        for j in range(N):
            faces.append((T[i][j], T[i + 1][j], T[i + 1][j + 1], T[i][j + 1]))
            faces.append((B[i][j], B[i][j + 1], B[i + 1][j + 1], B[i + 1][j]))
    loop = ([(0, j) for j in range(N)] + [(i, N) for i in range(N)]
            + [(N, j) for j in range(N, 0, -1)] + [(i, 0) for i in range(N, 0, -1)])
    for k in range(len(loop)):
        (i0, j0), (i1, j1) = loop[k], loop[(k + 1) % len(loop)]
        faces.append((T[i0][j0], T[i1][j1], B[i1][j1], B[i0][j0]))
    P.add(cv, cos, faces)

    # one torn corner, lifting off the top and curling down the outside
    pts = [Vector(p) for p in ((0.27, 0.27, 0.53), (0.39, 0.39, 0.53), (0.46, 0.46, 0.50),
                               (0.49, 0.49, 0.42), (0.505, 0.505, 0.32), (0.51, 0.51, 0.24))]
    stroke(P, cv, pts, [0.1] * 6, sides=4, thick=0.2, jit=0.006)


# --- dispatch -----------------------------------------------------------------------------------

# key: (object name, Parts seed, builder, recalc normals)
MODELS = {
    "orchard_tree_a": ("orchard_tree_a", 131, lambda P: orchard(P, "a", False), True),
    "orchard_tree_a_lod": ("orchard_tree_a_lod", 131, lambda P: orchard(P, "a", True), True),
    "orchard_tree_b": ("orchard_tree_b", 137, lambda P: orchard(P, "b", False), True),
    "orchard_tree_b_lod": ("orchard_tree_b_lod", 137, lambda P: orchard(P, "b", True), True),
    "cypress": ("cypress", 139, cypress, True),
    "hedge": ("hedge", 149, hedge, True),
    "reeds": ("reeds", 151, reeds, True),
    "house_a": ("house_a", 601, lambda P: house(P, "a"), True),
    "house_b": ("house_b", 607, lambda P: house(P, "b"), True),
    "house_c": ("house_c", 613, lambda P: house(P, "c"), True),
    "church": ("church", 619, church, True),
    "hill_a": ("hill_a", 701, lambda P: hill_mass(P, 120.0, 38.0, 26.0, False), True),
    "hill_b": ("hill_b", 709, lambda P: hill_mass(P, 86.0, 30.0, 18.0, True), True),
    "hill_c": ("hill_c", 717, lambda P: hill_mass(P, 136.0, 44.0, 33.0, False), True),
    "bank": ("bank", 727, bank, False),
    "torn_mass": ("torn_mass", 811, torn_mass, True),
    "stretcher_deck": ("stretcher_deck", 821, stretcher_deck, True),
}


def build(args):
    key = args[0] if args else ""
    if key not in MODELS:
        raise SystemExit("unknown land model: " + key)
    name, seed, fn, recalc = MODELS[key]
    P = N.Parts(seed)
    fn(P)
    finish(P, name, recalc)
