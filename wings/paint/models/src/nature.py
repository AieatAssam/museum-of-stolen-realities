"""Painted nature for the paint wing: every form is built from flattened brush ribbons (elliptic
sections, tapering like a lifted brush) and palette-knife daubs (cupped flattened ellipsoids).
Headless bmesh only, deterministic (seeded). One script, selected by args[0]; see
wings/paint/tools/build_nature.sh.
  tree <a|b|c> [lod]    rock <a|b>    bush    tuft    foliage_seg    knot
Blender: +Z up, 1 unit = 1 m, origin at the base centre. Material names are the contract."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "clay", "models", "src"))
import bmesh  # noqa: E402
import kit  # noqa: E402
import sculpt as S  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

_ICO = {}


def _ico(detail):
    """Unit icosphere (cached): vertex coords and face index lists."""
    if detail not in _ICO:
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=detail, radius=1.0)
        tmp.verts.index_update()
        _ICO[detail] = ([v.co.copy() for v in tmp.verts], [[v.index for v in f.verts] for f in tmp.faces])
        tmp.free()
    return _ICO[detail]


class Parts:
    """Geometry per material: one bmesh each, written as one object per material."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.bms = {}

    def bm(self, mat):
        if mat not in self.bms:
            self.bms[mat] = bmesh.new()
        return self.bms[mat]

    def jit(self, amt, z=True):
        r = self.rng
        return Vector((r.uniform(-amt, amt), r.uniform(-amt, amt), r.uniform(-amt, amt) if z else 0.0))

    def add(self, mat, cos, faces):
        bm = self.bm(mat)
        vs = [bm.verts.new(c) for c in cos]
        for f in faces:
            bm.faces.new([vs[i] for i in f])

    def write(self, name):
        verts = [v.co for bm in self.bms.values() for v in bm.verts]
        lo = [min(c[i] for c in verts) for i in range(3)]
        hi = [max(c[i] for c in verts) for i in range(3)]
        print("BOUNDS %s min=(%.2f, %.2f, %.2f) max=(%.2f, %.2f, %.2f) size=(%.2f, %.2f, %.2f)"
              % ((name,) + tuple(lo) + tuple(hi) + tuple(hi[i] - lo[i] for i in range(3))))
        return [kit._obj("%s_%s" % (name, mat), bm, mat, 60.0) for mat, bm in self.bms.items()]


def ribbon(P, mat, pts, widths, sides=8, thick=0.32, twist=0.0, jit=0.02, jit_z=True):
    """A flattened brush stroke along pts: elliptic section (width x width*thick), width per point,
    fan-capped at both ends. Vertices jittered a little so no line is ruler-straight."""
    n = len(pts)
    bm = P.bm(mat)
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        w = Matrix.Rotation(twist * i / max(n - 1, 1), 3, d) @ d.cross(ref).normalized()
        t = d.cross(w).normalized()
        a = max(widths[i], 0.01) * 0.5
        b = a * thick
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            co = p + w * (a * math.cos(th)) + t * (b * math.sin(th)) + P.jit(jit, jit_z)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    for end in (0, n - 1):
        c = bm.verts.new(pts[end])
        for k in range(sides):
            bm.faces.new((rings[end][k], rings[end][(k + 1) % sides], c))


def daub(P, mat, c, d, nrm, L, W, T, detail=2, cup=0.3, jit=0.02):
    """A palette-knife / brush dab: flattened, cupped ellipsoid centred at c. Long axis d (length L),
    face normal nrm (thickness T), width W across."""
    d = d.normalized()
    nrm = (nrm - d * nrm.dot(d)).normalized()
    M = Matrix((d, nrm.cross(d).normalized(), nrm)).transposed()
    base, faces = _ico(detail)
    cos = []
    for u in base:
        z = u.z * T * 0.5
        if z > 0:
            z += cup * T * 0.5 * (u.x * u.x + u.y * u.y)
        cos.append(c + M @ Vector((u.x * L * 0.5, u.y * W * 0.5, z)) + P.jit(jit))
    P.add(mat, cos, faces)


def leaf_mat(rng, light=0.3):
    return "p_leaf_light" if rng.random() < light else "p_leaf"


# --- tree ---------------------------------------------------------------------------------------

TREES = {
    "a": dict(seed=131, trunks=4, limbs=6, masses=4, lean=0.3, crown=5.6),
    "b": dict(seed=137, trunks=3, limbs=5, masses=3, lean=-0.25, crown=5.5),
    "c": dict(seed=139, trunks=5, limbs=7, masses=5, lean=0.15, crown=5.8),
}


def tree(P, v, lod):
    cfg = TREES[v]
    rng = P.rng
    segs = 5 if lod else 10
    sides = 5 if lod else 8
    split = rng.uniform(2.7, 3.2)
    lean = cfg["lean"]
    # trunk: 3-5 twisted flat ribbons rising together from a flared root, converging toward the split
    for j in range(cfg["trunks"]):
        a0 = 2 * math.pi * j / cfg["trunks"] + rng.uniform(-0.35, 0.35)
        r0 = rng.uniform(0.22, 0.4)
        tw = rng.uniform(0.9, 1.6) * rng.choice((-1, 1))
        pts, widths = [], []
        for k in range(segs + 1):
            t = k / segs
            R = r0 * (1 - t) + 0.1
            ang = a0 + tw * t
            pts.append(Vector((math.cos(ang) * R + lean * t * 0.5, math.sin(ang) * R, split * t)))
            flare = 1 + 1.2 * math.exp(-t * split / 0.45)
            widths.append(0.5 * flare * (1 - 0.55 * t) + 0.04)
        ribbon(P, "p_bark", pts, widths, sides=sides, thick=0.32, jit=0.03, jit_z=False)
    # limbs: 4-7 branches splaying out of the split into the crown
    for k in range(cfg["limbs"]):
        a = 2 * math.pi * k / cfg["limbs"] + rng.uniform(-0.4, 0.4)
        el = rng.uniform(0.35, 0.95)
        L = rng.uniform(2.0, 3.0)
        start = Vector((lean * 0.5 + 0.12 * math.cos(a), 0.12 * math.sin(a), split * rng.uniform(0.8, 0.98)))
        dr = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        bow = rng.uniform(-0.25, 0.25)
        pts, widths = [], []
        for i in range(6):
            s = i / 5
            pts.append(start + dr * (L * s) + Vector((-math.sin(a), math.cos(a), 0)) * (bow * math.sin(math.pi * s)))
            widths.append(0.34 * (1 - s) ** 0.7 + 0.05)
        ribbon(P, "p_bark", pts, widths, sides=sides, thick=0.35, twist=rng.uniform(-1, 1), jit=0.025)
    # crown: clustered masses of dabs, swirled like a brush
    total = 30 if lod else 72
    centers = []
    for m in range(cfg["masses"]):
        a = 2 * math.pi * m / cfg["masses"] + rng.uniform(-0.4, 0.4)
        dist = rng.uniform(0.9, 1.7)
        centers.append(Vector((math.cos(a) * dist * 1.1, math.sin(a) * dist * 0.8, cfg["crown"] + rng.uniform(-0.5, 0.6))))
    for i in range(total):
        c = centers[i % len(centers)]
        g = Vector((rng.gauss(0, 0.55), rng.gauss(0, 0.55), rng.gauss(0, 0.45)))
        p = c + Vector((g.x * 1.3, g.y * 1.1, g.z * 0.9))
        phi = math.atan2(g.y, g.x) + math.pi / 2 + rng.gauss(0, 0.4)
        d = Vector((math.cos(phi), math.sin(phi), rng.uniform(-0.35, 0.35)))
        nrm = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        L = rng.uniform(1.2, 1.8) if lod else rng.uniform(0.7, 1.6)
        W = L * 0.55 if lod else L * rng.uniform(0.45, 0.6)
        daub(P, leaf_mat(rng), p, d, nrm, L, W, rng.uniform(0.12, 0.2), detail=1 if lod else 2)
    for i in range(2 if lod else 4):
        c = centers[i % len(centers)]
        p = c + Vector((rng.gauss(0, 0.9), rng.gauss(0, 0.9), rng.gauss(0.5, 0.4)))
        daub(P, "p_blossom", p, Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0.1)),
             Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))), rng.uniform(0.3, 0.45), 0.25, 0.1,
             detail=1 if lod else 2)


# --- rock ---------------------------------------------------------------------------------------

def rock(P):
    rng = P.rng
    rx, ry, rz = rng.uniform(1.6, 2.0), rng.uniform(1.25, 1.5), rng.uniform(0.75, 1.2)
    planes = []
    for _ in range(rng.randint(4, 8)):
        th, el = rng.uniform(0, 2 * math.pi), rng.uniform(-0.2, 0.7)
        n = Vector((math.cos(th) * math.cos(el), math.sin(th) * math.cos(el), math.sin(el))).normalized()
        planes.append((n, rng.uniform(0.8, 0.9)))
    base, faces = _ico(4)
    cos = []
    for u in base:
        p = u.copy()
        for n, dd in planes:  # knife cuts: clip to each facet plane
            dot = p.dot(n)
            if dot > dd:
                p -= n * (dot - dd)
        g = min(dd - p.dot(n) for n, dd in planes)
        if 1e-4 < g < 0.09:  # raised ridge just inside each cut edge
            p *= 1 + 0.12 * (1 - g / 0.09)
        cos.append(Vector((p.x * rx, p.y * ry, p.z * rz)))
    P.add("p_stone", cos, faces)
    S.deform(P.bm("p_stone"), rng.randint(1, 999), lump=0.09, scale=1.5, dents=2, dent_r=0.35, dent_d=0.05)


# --- bush / tuft / foliage / knot ---------------------------------------------------------------

def bush(P):
    rng = P.rng
    for _ in range(4):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.15, 0.3)
        base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        top = Vector((base.x * 0.6, base.y * 0.6, rng.uniform(0.5, 0.9)))
        ribbon(P, "p_bark", [base, base.lerp(top, 0.5) + P.jit(0.03), top], [0.07, 0.05, 0.03], sides=6, jit=0.01)
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi)
        r = 0.85 * math.sqrt(rng.random())
        c = Vector((math.cos(a) * r, math.sin(a) * r, rng.uniform(0.5, 1.15)))
        d = Vector((math.cos(a + math.pi / 2) + rng.gauss(0, 0.5), math.sin(a + math.pi / 2) + rng.gauss(0, 0.5), rng.gauss(0, 0.4)))
        L = rng.uniform(0.5, 0.8)
        daub(P, leaf_mat(rng), c, d, Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))), L, L * 0.55, 0.12)


def tuft(P):
    rng = P.rng
    for _ in range(rng.randint(6, 10)):
        bx, by = rng.gauss(0, 0.07), rng.gauss(0, 0.07)
        H = rng.uniform(0.5, 0.8)
        phi, lean = rng.uniform(0, 2 * math.pi), rng.uniform(0.15, 0.35)
        pts = [Vector((bx + math.cos(phi) * lean * H * (k / 4) ** 2, by + math.sin(phi) * lean * H * (k / 4) ** 2, H * k / 4))
               for k in range(5)]
        widths = [0.045 * (1 - k / 4) ** 0.7 + 0.006 for k in range(5)]
        ribbon(P, leaf_mat(rng, 0.5), pts, widths, sides=4, thick=0.45, twist=rng.uniform(-0.6, 0.6), jit=0.008, jit_z=False)


def foliage_seg(P):
    rng = P.rng
    zs = [0.0, 0.5, 1.0, 1.5, 2.0]  # the stalk spans exactly z 0..2, so stacked copies join
    pts = [Vector((0.02 * math.sin(z * 1.3 + 0.5), 0.03 * math.cos(z * 1.1), z)) for z in zs]
    ribbon(P, "p_bark", pts, [0.2, 0.17, 0.15, 0.13, 0.1], sides=8, thick=0.35, twist=1.2, jit=0.015, jit_z=False)
    for _ in range(rng.randint(10, 16)):
        ph = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.9, 1.1)
        c = Vector((math.cos(ph) * r, math.sin(ph) * r, rng.uniform(0.4, 1.6)))
        d = Vector((-math.sin(ph), math.cos(ph), rng.uniform(-0.25, 0.35)))  # swirls around the stalk
        L = rng.uniform(0.95, 1.15)
        daub(P, leaf_mat(rng), c, d, Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))), L, L * 0.5, 0.14)


def knot(P):
    rng = P.rng
    a, b, c = 0.72, 0.31, 0.28  # resin body inside the 1.6 x 0.7 x 0.7 box
    base, faces = _ico(3)
    P.add("p_varnish", [Vector((u.x * a, u.y * b, u.z * c)) for u in base], faces)
    S.deform(P.bm("p_varnish"), 7, lump=0.012, scale=3.0)

    def top(x):
        return c * math.sqrt(max(0.0, 1 - (x / a) ** 2))
    # cracked top ridge: three broken pieces following the crown of the lump
    for x0, x1 in ((-0.6, -0.12), (0.0, 0.3), (0.42, 0.62)):
        xs = [x0 + (x1 - x0) * k / 4 for k in range(5)]
        pts = [Vector((x, rng.uniform(-0.01, 0.01), top(x) + 0.02)) for x in xs]
        ribbon(P, "p_varnish", pts, [0.1 * math.sin(math.pi * k / 4) ** 0.5 + 0.02 for k in range(5)], sides=6, thick=0.35, jit=0.006)
    # 4 drips running down the sides, each three dabs thinning downward
    for _ in range(4):
        x0 = rng.uniform(-0.5, 0.5)
        side = rng.choice((-1, 1))
        for zc, L in ((0.1, 0.24), (-0.04, 0.2), (-0.16, 0.16)):
            x = x0 + rng.uniform(-0.02, 0.02)
            y = side * b * math.sqrt(max(0.05, 1 - (x / a) ** 2 - (zc / c) ** 2))
            daub(P, "p_varnish", Vector((x, y, zc)), Vector((0, 0, -1)), Vector((0, side, 0)), L, 0.13, 0.06,
                 cup=0.0, jit=0.01)


# --- dispatch -----------------------------------------------------------------------------------

def build(args):
    kind, rest = args[0], args[1:]
    if kind == "tree":
        v = rest[0]
        lod = "lod" in rest[1:]
        name = "tree_%s%s" % (v, "_lod" if lod else "")
        P = Parts(TREES[v]["seed"])
        tree(P, v, lod)
    elif kind == "rock":
        v = rest[0]
        name = "rock_" + v
        P = Parts({"a": 211, "b": 223}[v])
        rock(P)
    elif kind == "bush":
        name, P = "bush", Parts(229)
        bush(P)
    elif kind == "tuft":
        name, P = "tuft", Parts(233)
        tuft(P)
    elif kind == "foliage_seg":
        name, P = "foliage_seg", Parts(241)
        foliage_seg(P)
    elif kind == "knot":
        name, P = "knot", Parts(251)
        knot(P)
    else:
        raise SystemExit("unknown nature model: " + kind)
    P.write(name)
