"""Paint wing figures, built as oil studies: masses are long flattened brushstroke ribbons (a swept
lens cross-section that tapers at both ends), never bare primitives. One script, selected by args[0].
Run through tools/blender_build.sh (wings/paint/tools/build_figures.sh builds them all).
Blender: +Z up, 1 unit = 1 m. Figures face -Y. Material names are the contract (p_* only)."""
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "clay", "models", "src"))
import kit  # noqa: E402  (tools/blender is on sys.path via the export harness)
import sculpt as S  # noqa: E402

PI = math.pi


# --- helpers ------------------------------------------------------------------------------------

def _unit(v):
    return v.normalized() if v.length > 1e-9 else Vector((0.0, 0.0, 1.0))


def _sm(t, a, b):
    """Smoothstep from a to b (a > b gives a falling ramp)."""
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3.0 - 2.0 * x)


def taper(w, p=0.4):
    """Half-width profile: swells across the stroke and tapers to a point at both ends."""
    return lambda u: w * max(math.sin(PI * u), 0.0) ** p


def _ls(a, b, n):
    return [a + (b - a) * k / (n - 1) for k in range(n)]


def _lerp(a, b, n):
    a, b = Vector(a), Vector(b)
    return [tuple(a + (b - a) * (k / (n - 1))) for k in range(n)]


def _poly(points, n):
    out = []
    for i in range(len(points) - 1):
        seg = _lerp(points[i], points[i + 1], n)
        out += seg if i == 0 else seg[1:]
    return out


def _ax_x(x0, z0):
    """A lathe built on +Z, moved to run along +X from x0 with its axis at height z0."""
    return Matrix.Translation((x0, 0.0, z0)) @ Matrix.Rotation(PI / 2, 4, "Y")


def _ax_y(y0=0.0):
    """A lathe built on +Z, turned to run along +Y from y0."""
    return Matrix.Translation((0.0, y0, 0.0)) @ Matrix.Rotation(-PI / 2, 4, "X")


class Paint:
    """Strokes binned per material into one bmesh each; finish() writes one object per material."""

    def __init__(self, prefix):
        self.prefix = prefix
        self.bms = {}

    def _bm(self, mat):
        if mat not in self.bms:
            self.bms[mat] = bmesh.new()
        return self.bms[mat]

    def ribbon(self, pts, mat, hint, wfun, tfun, K=8):
        """Sweep a flat lens along pts. hint = canvas normal (tuple, or callable(i, p) -> Vector):
        the broad face of the stroke faces it. wfun / tfun give the half-width / half-thickness at
        u in [0, 1] along the stroke. Both ends close to points."""
        P = [Vector(p) for p in pts]
        n = len(P)
        bm = self._bm(mat)
        rings = []
        for i, p in enumerate(P):
            u = i / (n - 1)
            d = _unit(P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
            h = hint(i, p) if callable(hint) else Vector(hint)
            h = _unit(h - d * h.dot(d))
            w_ax = _unit(d.cross(h))
            W, T = max(wfun(u), 1e-4), max(tfun(u), 1e-4)
            rings.append([bm.verts.new(p + w_ax * (W * math.cos(a)) + h * (T * math.sin(a)))
                          for a in (2 * PI * k / K for k in range(K))])
        for i in range(n - 1):
            a, b = rings[i], rings[i + 1]
            for k in range(K):
                bm.faces.new((a[k], b[k], b[(k + 1) % K], a[(k + 1) % K]))
        t0, t1 = bm.verts.new(P[0]), bm.verts.new(P[-1])
        for k in range(K):
            bm.faces.new((t0, rings[0][(k + 1) % K], rings[0][k]))
            bm.faces.new((t1, rings[-1][k], rings[-1][(k + 1) % K]))

    def lathe(self, mat, profile, segs=12, M=None, cap_lo=True, cap_hi=True, post=None):
        """Revolve a (radius, z) profile about Z (bottom to top), optionally deform, then move by M."""
        bm = bmesh.new()
        rings = [[bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for r, z in profile]
                 for a in (2 * PI * i / segs for i in range(segs))]
        for i in range(segs):
            r0, r1 = rings[i], rings[(i + 1) % segs]
            for j in range(len(profile) - 1):
                bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
        if cap_lo:
            bm.faces.new(tuple(rings[i][0] for i in range(segs)))
        if cap_hi:
            bm.faces.new(tuple(rings[i][-1] for i in range(segs)))
        if post:
            post(bm)
        if M is not None:
            bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        self._merge(mat, bm)

    def _merge(self, mat, src):
        dst = self._bm(mat)
        mp = {v: dst.verts.new(v.co) for v in src.verts}
        for f in src.faces:
            dst.faces.new([mp[v] for v in f.verts])
        src.free()

    def bounds(self):
        lo, hi = [1e9] * 3, [-1e9] * 3
        for bm in self.bms.values():
            for v in bm.verts:
                for k in range(3):
                    lo[k] = min(lo[k], v.co[k])
                    hi[k] = max(hi[k], v.co[k])
        return Vector(lo), Vector(hi)

    def settle(self, mode):
        """mode 'base': origin at base centre on the ground. 'centre': origin at bounding-box centre."""
        lo, hi = self.bounds()
        s = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) if mode == "base" else -(lo + hi) / 2
        for bm in self.bms.values():
            bmesh.ops.transform(bm, matrix=Matrix.Translation(s), verts=bm.verts)

    def finish(self, smooth=50.0):
        objs = []
        for mat, bm in self.bms.items():
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            objs.append(kit._obj(f"{self.prefix}_{mat}", bm, mat, smooth))
        self.bms = {}
        return objs


# --- 1. figure: the Pentimento figure, 62 m robed woman ----------------------------------------

def _robe_a(z):
    """Robe half-width (x) at height z: a column to z=38, then the shoulders open to about 7 m."""
    return 2.9 + 0.35 * math.exp(-z / 4.0) + 3.8 * _sm(z, 38.0, 47.0)


def _robe_b(z):
    """Robe half-depth (y)."""
    return 2.3 + 0.3 * math.exp(-z / 4.0) + 0.5 * _sm(z, 40.0, 47.0)


def B_figure():
    P = Paint("figure")
    Cz, Cy = 56.9, -0.25  # head centre

    # robe: 30 long vertical strokes wrapping the column, the side ones carried up into the shoulders
    for i in range(30):
        th = 2 * PI * i / 30 + 0.1
        ca, sa = math.cos(th), math.sin(th)
        z1 = 47.0 if abs(ca) > 0.45 else 41.0
        pts = []
        for k in range(12):
            z = 0.3 + (z1 - 0.3) * k / 11
            m = 1.0 + 0.045 * math.sin(2 * PI * z / 11.0 + 0.7 * i)
            A, B = _robe_a(z) + 0.12, _robe_b(z) + 0.12
            pts.append((A * ca * m, B * sa * m, z))
        light = i % 4 == 1
        P.ribbon(pts, "p_robe_light" if light else "p_robe", (ca, sa, 0.0),
                 taper(0.55 if light else 0.66, 0.35), taper(0.15, 0.35))

    # hem: three horizontal arcs at the foot
    for phi0 in (0.2, 2.5, 4.6):
        phs = _ls(phi0, phi0 + 2.0, 9)
        pts = [((_robe_a(0.6) + 0.1) * math.cos(p), (_robe_b(0.6) + 0.1) * math.sin(p), 0.6 + 0.05 * math.sin(3 * p))
               for p in phs]
        P.ribbon(pts, "p_robe", lambda i, p, ph=phs: Vector((math.cos(ph[i]), math.sin(ph[i]), 0.0)),
                 taper(0.42, 0.3), taper(0.22, 0.3))

    # shoulder mantle: three arcs laid across the top of the robe
    for j, z in enumerate((43.0, 44.8, 46.2)):
        pts = []
        for k in range(9):
            x = -6.4 + 12.8 * k / 8
            y = -2.9 * math.sqrt(max(0.05, 1 - (x / 7.0) ** 2)) - 0.2 * j
            pts.append((x, y, z + 0.25 * (1 - (x / 6.4) ** 2)))
        P.ribbon(pts, "p_robe_light" if j == 1 else "p_robe", (0, -1, 0), taper(0.55, 0.4), taper(0.3, 0.4))

    # folded arms: upper arms down from the shoulders, forearms across the waist, hands at the centre
    for sx in (-1.0, 1.0):
        P.ribbon(_lerp((sx * 6.0, -0.6, 45.0), (sx * 5.0, -2.2, 40.2), 6), "p_robe", (sx, -0.4, 0.0),
                 taper(0.7, 0.4), taper(0.5, 0.4))
        P.ribbon(_lerp((sx * 5.0, -2.2, 40.2), (-sx * 0.5, -3.5, 40.7), 7), "p_robe", (0, 0, 1),
                 taper(0.5, 0.4), taper(0.42, 0.4))
        P.ribbon(_lerp((sx * 2.9, -3.6, 41.0), (-sx * 0.4, -3.9, 40.6), 7), "p_skin", (0, -1, 0),
                 taper(0.7, 0.4), taper(0.36, 0.4))
        for f in range(3):
            z = 40.9 - 0.3 * f
            P.ribbon(_lerp((-sx * 0.4, -3.95, z), (-sx * 1.5, -3.95, z), 5), "p_skin", (0, -1, 0),
                     taper(0.22, 0.4), taper(0.22, 0.4))

    # neck, with its shadowed back
    P.ribbon(_lerp((0.0, -0.2, 46.0), (0.0, -0.4, 52.6), 6), "p_skin", (0, -1, 0), taper(1.0, 0.3), taper(0.7, 0.3))
    P.ribbon(_lerp((0.0, 0.5, 46.6), (0.0, 0.5, 52.2), 5), "p_skin_shadow", (0, 1, 0), taper(0.8, 0.3), taper(0.35, 0.3))

    # face: rolled latitude strokes over the front three-quarters of the head
    for off in (-3.5, -2.1, -0.7, 0.7, 2.0):
        s = math.sqrt(max(0.05, 1 - (off / 3.7) ** 2)) * 0.92
        phs = _ls(-PI / 2 - 1.35, -PI / 2 + 1.35, 7)
        pts = [(2.3 * s * math.cos(p), Cy + 2.6 * s * math.sin(p), Cz + off) for p in phs]
        P.ribbon(pts, "p_skin", lambda i, p, ph=phs: Vector((math.cos(ph[i]), math.sin(ph[i]), 0.0)),
                 taper(0.62, 0.35), taper(0.3, 0.35))
    for sx in (-1.0, 1.0):  # bowed eyes: brow and socket shadows
        P.ribbon(_lerp((sx * 0.25, -2.2, Cz + 0.55), (sx * 1.25, -2.15, Cz + 0.45), 5), "p_skin_shadow", (0, -1, 0),
                 taper(0.14, 0.3), taper(0.22, 0.3))
    P.ribbon(_lerp((0.0, -2.5, Cz + 0.6), (0.0, -2.8, Cz - 1.3), 6), "p_skin", (0, -1, 0),
             taper(0.24, 0.3), taper(0.32, 0.3))                                       # nose
    P.ribbon(_lerp((-0.5, -2.5, Cz - 1.4), (0.5, -2.5, Cz - 1.4), 5), "p_skin_shadow", (0, -1, 0),
             taper(0.12, 0.3), taper(0.14, 0.3))                                       # under the nose
    P.ribbon(_lerp((-0.9, -2.0, Cz - 2.9), (0.9, -2.0, Cz - 2.9), 5), "p_skin_shadow", (0, -1, 0),
             taper(0.18, 0.3), taper(0.2, 0.3))                                        # under the chin
    P.ribbon(_lerp((-0.45, -2.2, Cz - 2.0), (0.45, -2.2, Cz - 2.0), 4), "p_skin_shadow", (0, -1, 0),
             taper(0.06, 0.3), taper(0.06, 0.3))                                       # mouth

    # hair: six swirling meridian strokes over the crown, twelve locks falling to the shoulders
    rxh, ryh, rzh = 2.7, 3.0, 4.85
    for k in range(6):
        phi = -PI / 2 + 1.1 + k * (2 * PI - 2.2) / 5
        betas = [-0.35 + (PI + 0.7) * s / 13 for s in range(14)]
        pts = [(rxh * math.cos(b) * math.cos(phi), Cy + ryh * math.cos(b) * math.sin(phi), Cz + rzh * math.sin(b))
               for b in betas]
        hints = [(math.cos(b) * math.cos(phi), math.cos(b) * math.sin(phi), math.sin(b)) for b in betas]
        P.ribbon(pts, "p_hair", lambda i, p, h=hints: Vector(h[i]), taper(0.85, 0.35), taper(0.25, 0.35))
    for j in range(12):
        ph0 = PI / 2 - 2.2 + 4.4 * j / 11
        zs = [Cz + 3.2 - (Cz + 3.2 - 44.5) * s / 11 for s in range(12)]
        pts, hints = [], []
        for s, z in enumerate(zs):
            sc = math.sqrt(max(0.05, 1 - ((z - Cz) / rzh) ** 2))
            fl = _sm(z, 55.9, 46.0)
            Rx, Ry = rxh * sc + 3.2 * fl, ryh * sc + 2.6 * fl
            ph = ph0 + 0.3 * math.sin(2.2 * s + 1.7 * j)
            pts.append((Rx * math.cos(ph), Cy + Ry * math.sin(ph), z))
            hints.append((math.cos(ph), math.sin(ph), 0.0))
        P.ribbon(pts, "p_hair", lambda i, p, h=hints: Vector(h[i]), taper(0.6, 0.3), taper(0.18, 0.3))

    P.settle("base")
    return P.finish()


# --- 2. hand: the painter's giant hand holding a brush, on its little-finger edge --------------

def B_hand():
    P = Paint("hand")
    zb, Rf = 1.45, 0.66             # brush axis height, finger loop radius about the brush
    xs = (-1.0, -0.35, 0.3, 0.95)   # four finger loops stacked along the brush

    # palm (faces -Y): three long strokes; the little-finger edge (z=0) is the ground
    for z in (0.45, 1.25, 2.05):
        P.ribbon(_lerp((-3.2, -0.9, z), (0.5, -0.9, z + 0.06), 9), "p_skin", (0, -1, 0),
                 taper(0.45, 0.3), taper(0.36, 0.3))
    # back of the hand, with tendons
    for z in (0.9, 1.7):
        P.ribbon(_lerp((-2.9, 0.25, z), (0.1, 0.25, z + 0.05), 8), "p_skin", (0, 1, 0), taper(0.4, 0.3), taper(0.2, 0.3))
    P.ribbon(_lerp((-2.9, -0.92, 0.85), (0.1, -0.92, 0.85), 8), "p_skin_shadow", (0, -1, 0),
             taper(0.06, 0.3), taper(0.12, 0.3))  # crease under the palm

    # four fingers: rolled strokes wrapping the brush from the palm, over the top and back under
    for x in xs:
        phs = _ls(-0.45, PI + 0.25, 11)
        pts = [(x, -Rf * math.cos(t), zb + Rf * math.sin(t)) for t in phs]
        P.ribbon(pts, "p_skin", lambda i, p, ph=phs: Vector((0.0, -math.cos(ph[i]), math.sin(ph[i]))),
                 taper(0.27, 0.3), taper(0.26, 0.3))
    for i in range(3):  # creases between the fingers
        xm = (xs[i] + xs[i + 1]) / 2
        phs = _ls(0.2, PI, 9)
        pts = [(xm, -(Rf + 0.25) * math.cos(t), zb + (Rf + 0.25) * math.sin(t)) for t in phs]
        P.ribbon(pts, "p_skin_shadow", lambda i2, p, ph=phs: Vector((0.0, -math.cos(ph[i2]), math.sin(ph[i2]))),
                 taper(0.07, 0.3), taper(0.05, 0.3))
    # thumb: a rolled stroke laid over the brush
    P.ribbon(_poly([(-1.9, -1.0, 1.75), (-0.3, -0.85, 2.05), (1.0, -0.7, 2.0), (2.1, -0.25, 1.6)], 5), "p_skin",
             (0, -1, 0), taper(0.26, 0.3), taper(0.24, 0.3))

    # brush: 7 m handle, brass ferrule, red bristle tip (brush axis at y=0, z=zb)
    P.lathe("p_wood_dark", [(0.002, 0.0), (0.26, 0.0), (0.3, 0.5), (0.31, 3.4), (0.28, 6.5), (0.3, 7.0), (0.002, 7.0)],
            segs=24, M=_ax_x(-5.5, zb), post=lambda bm: S.deform(bm, 3, 0.012, 1.2))
    P.lathe("p_brass", [(0.33, 0.0), (0.36, 0.06), (0.36, 0.54), (0.33, 0.6)], segs=24, M=_ax_x(1.5, zb))
    for k in range(7):
        a = 2 * PI * k / 7 + 0.3
        pts = [(2.05 + 1.35 * t, (0.3 * (1 - t) ** 0.7 + 0.02) * math.cos(a),
                zb + (0.3 * (1 - t) ** 0.7 + 0.02) * math.sin(a)) for t in _ls(0.0, 1.0, 9)]
        P.ribbon(pts, "p_red", (0.0, math.cos(a), math.sin(a)),
                 lambda u: 0.12 * (1 - u) ** 0.5 + 0.01, lambda u: 0.05 * (1 - u) ** 0.5 + 0.01, K=6)

    P.settle("base")
    return P.finish()


# --- 3. knife: palette knife, 0.5 m along Y ----------------------------------------------------

def _blade_w(u):
    if u < 0.12:
        return 0.0035
    if u < 0.55:
        return 0.0035 + 0.0365 * ((u - 0.12) / 0.43) ** 0.8
    return 0.04 * math.sqrt(max(0.0, 1 - ((u - 0.55) / 0.45) ** 2)) + 0.0004


def B_knife():
    P = Paint("knife")
    P.lathe("p_wood_dark", [(0.002, 0.0), (0.0165, 0.0), (0.0185, 0.05), (0.0135, 0.10), (0.0185, 0.16),
                            (0.0150, 0.19), (0.002, 0.19)], segs=14, M=_ax_y(-0.25))      # walnut handle
    P.lathe("p_brass", [(0.0150, 0.0), (0.0160, 0.012), (0.0150, 0.025)], segs=14, M=_ax_y(-0.06))  # ferrule
    N = 22  # cranked neck rising into the flexible trowel blade (broad face up)
    pts = [(0.0, -0.035 + 0.285 * i / (N - 1), 0.012 * _sm(i / (N - 1), 0.0, 0.2)) for i in range(N)]
    P.ribbon(pts, "p_steel", (0, 0, 1), _blade_w, lambda u: 0.0015, K=6)
    P.settle("centre")
    return P.finish()


# --- 4. swatch: dried colour card on a stand, origin at the bottom -----------------------------

def B_swatch():
    objs = [
        S.slab("swatch_foot", (0.14, 0.05, 0.025), (0.0, 0.0, 0.0125), "p_wood", 1, lump=0.0008, bevel=0.004, cuts=2),
        S.slab("swatch_card", (0.32, 0.01, 0.24), (0.0, 0.0, 0.145), "p_canvas", 2, lump=0.0006, bevel=0.002, cuts=3),
    ]
    P = Paint("swatch")
    for i in range(5):  # thick violet dab, laid in ridged knife strokes on the card front (-Y)
        z0 = 0.11 + 0.022 * i
        pts = [(x, -0.0065, z0 + 0.012 * math.sin(PI * u) + 0.004 * i)
               for u, x in zip(_ls(0, 1, 9), _ls(-0.12 + 0.01 * i, 0.08 - 0.012 * i, 9))]
        P.ribbon(pts, "p_violet", (0, -1, 0), taper(0.012, 0.3), taper(0.011, 0.3), K=6)
    P.ribbon([(x, -0.0058, 0.05 + 0.004 * math.sin(k * 0.9)) for k, x in enumerate(_ls(-0.12, 0.12, 17))],
             "p_graphite", (0, -1, 0), taper(0.0016, 0.3), taper(0.0009, 0.3), K=6)  # pencil note line
    return objs + P.finish()


# --- 5. stub: hexagonal pencil stub, 0.22 m along Y --------------------------------------------

def B_stub():
    P = Paint("stub")
    M = _ax_y(0.0)
    M_neg = M @ Matrix.Scale(-1.0, 4, (0, 0, 1))
    P.lathe("p_red", [(0.0045, -0.075), (0.0045, 0.075)], segs=6, M=M, cap_lo=False, cap_hi=False)
    for MM in (M, M_neg):  # knife-cut wood cones and graphite points at both ends
        P.lathe("p_wood", [(0.0045, 0.075), (0.0030, 0.090), (0.0016, 0.105)], segs=6, M=MM, cap_lo=False, cap_hi=False)
        P.lathe("p_graphite", [(0.0016, 0.105), (0.0004, 0.110)], segs=6, M=MM, cap_lo=False)
    P.settle("centre")
    return P.finish()


# --- 6. ferrule: brass brush ferrule, 0.14 m along Y -------------------------------------------

def B_ferrule():
    P = Paint("ferrule")

    def crimp(bm):  # crimped top end flattened in x, slightly dented
        S.deform(bm, 4, 0.0004, 60.0, 2, 0.012, 0.0015)
        for v in bm.verts:
            if v.co.z > 0.035:
                v.co.x *= 0.55

    P.lathe("p_brass", [(0.0105, -0.065), (0.0112, -0.02), (0.0112, 0.04), (0.0108, 0.065), (0.0098, 0.065),
                        (0.0098, -0.065)], segs=16, M=_ax_y(0.0), cap_lo=False, cap_hi=False, post=crimp)
    # a few broken bristles at the crimp
    for x0, z0, L in ((-0.004, 0.002, 0.014), (0.0, -0.003, 0.02), (0.004, 0.001, 0.012),
                      (-0.002, 0.004, 0.017), (0.003, -0.004, 0.009)):
        pts = [(x0 + 0.002 * u, 0.058 + L * u, z0 + 0.002 * u) for u in _ls(0.0, 1.0, 6)]
        P.ribbon(pts, "p_wood_dark", (1, 0, 0), lambda u: 0.0012 * (1 - u) ** 0.5 + 0.0002,
                 lambda u: 0.0009 * (1 - u) ** 0.5 + 0.0002, K=6)
    P.settle("centre")
    return P.finish()


# --- 7. fragment: the first stroke, a lifted curl of red paint, 0.9 m along Y -----------------

def _frag_wt(u):
    """(half-width, half-thickness) along the stroke: rounded blob, flat body, thin curled tail."""
    if u <= 0.7:
        if u < 0.12:
            s = math.sqrt(max(0.0, 1 - ((0.12 - u) / 0.12) ** 2))
            return 0.125 * s, 0.06 * s
        return 0.125, 0.035 + 0.025 * max(0.0, 1 - (u - 0.12) / 0.18)
    v = (u - 0.7) / 0.3
    s = max(0.0, 1 - v) ** 1.5
    return 0.006 + 0.119 * s, 0.008 + 0.027 * s


def _frag_pose(u):
    """(y, z) of the stroke centre: body lies on the ground, then the tail lifts and curls up."""
    if u <= 0.7:
        return -0.45 + 0.65 * u / 0.7, _frag_wt(u)[1]
    v = (u - 0.7) / 0.3
    ph = 1.2 * PI * v
    return 0.2 + 0.25 * v + 0.035 * math.sin(ph), 0.07 - 0.035 * math.cos(ph)


def B_fragment():
    P = Paint("fragment")
    N = 26
    us = _ls(0.0, 1.0, N)
    poses = [_frag_pose(u) for u in us]
    P.ribbon([(0.0, y, z) for y, z in poses], "p_red", (0, 0, 1),
             lambda u: _frag_wt(u)[0], lambda u: _frag_wt(u)[1], K=8)
    # six bristle ridges running along the top
    for k in range(6):
        frac = -0.8 + 1.6 * k / 5
        pts = []
        for u, (y, z) in zip(us, poses):
            W, T = _frag_wt(u)
            pts.append((frac * W, y, z + T * math.sqrt(max(0.0, 1 - frac ** 2)) - 0.0015))
        P.ribbon(pts, "p_red", (0, 0, 1),
                 lambda u: 0.0042 * max(math.sin(PI * u), 0.0) ** 0.25 + 0.0002,
                 lambda u: 0.006 * max(math.sin(PI * u), 0.0) ** 0.25 + 0.0002, K=6)
    P.settle("centre")
    return P.finish()


# --- 8. study: a Corrections figure, 3.2 m along X by 5 m tall, 0.4 m deep, origin at the base --
# A standing figure laid in thick paint, rows of knife strokes filling the silhouette. "study_N" is the
# umber figure with diagonal knife scrapes through it down to the primed ground; "study_eN" is the pale
# earlier pose, whole. Godot stretches it over the upright stroke's collider (visual only).

def _study_hw(z):
    """Half-width of the robed body at height z (robe flaring to the hem, waist, shoulders)."""
    if z < 2.4:
        return 1.5 - 0.72 * (z / 2.4) ** 0.8
    if z < 3.75:
        return 0.78 + 0.27 * (z - 2.4) / 1.35
    return 1.05 - 1.6 * (z - 3.75)


_STUDY_ARMS = (  # per pose: (shoulder, elbow, hand) for the left (-X) and right (+X) arm
    (((-0.95, 3.7), (-1.3, 2.9), (-1.25, 2.15)), ((0.95, 3.7), (1.3, 2.9), (1.25, 2.15))),     # arms down
    (((-0.95, 3.7), (-1.5, 3.0), (-0.75, 2.55)), ((0.95, 3.7), (1.35, 4.35), (1.05, 4.95))),   # hand raised
    (((-0.95, 3.7), (-1.5, 3.55), (-1.55, 2.85)), ((0.95, 3.7), (1.5, 3.55), (1.55, 2.85))),   # arms open
)


def B_study(pose=0, early=False):
    P = Paint("study_e" if early else "study")
    body, light = ("p_plaster", "p_canvas") if early else ("p_bark", "p_hair")
    D = -0.2  # front face of the paint (-Y)

    def scraped(x, z):
        if early or z < 0.5 or z > 3.6:
            return False
        q = (x * 0.62 + z * 0.9) / 0.95 + 0.37 * pose
        return q - math.floor(q) < 0.24 + 0.1 * math.sin(3.1 * x + 1.7 * z + pose)

    # body rows, broken where the knife has scraped through
    z = 0.12
    while z < 3.9:
        hw = _study_hw(z) * (1.0 + 0.04 * math.sin(7.0 * z + pose))
        xs = _ls(-hw, hw, max(4, int(2 * hw / 0.08)))
        runs, cur = [], []
        for x in xs:
            if scraped(x, z):
                if len(cur) > 2:
                    runs.append(cur)
                cur = []
            else:
                cur.append(x)
        if len(cur) > 2:
            runs.append(cur)
        for k, r in enumerate(runs):
            n = max(3, int((r[-1] - r[0]) / 0.25) + 2)
            pts = [(x, D * 0.15 + 0.02 * math.sin(3 * x + z), z + 0.03 * math.sin(2.1 * x + 5 * z))
                   for x in _ls(r[0], r[-1], n)]
            mat = light if (int(z * 5) + k + pose) % 5 == 0 else body
            P.ribbon(pts, mat, (0, -1, 0), taper(0.15, 0.15), taper(0.18, 0.25))
        z += 0.19
    if not early:  # the primed ground the scrapes lay bare, set back inside the silhouette
        z = 0.5
        while z < 3.7:
            hw = _study_hw(z) * 0.94
            P.ribbon(_lerp((-hw, 0.0, z), (hw, 0.0, z), max(3, int(2 * hw / 0.3) + 2)), "p_canvas", (0, -1, 0),
                     taper(0.13, 0.12), taper(0.08, 0.2))
            z += 0.22
        for k in range(5):  # knife drags: pale streaks pulled diagonally down out of the scrapes
            x0 = -1.0 + 0.5 * k + 0.13 * pose
            P.ribbon(_lerp((x0, D * 0.6, 3.3 - 0.25 * k), (x0 - 0.75, D * 0.6, 1.1 - 0.15 * k), 7), "p_canvas",
                     (0, -1, 0), taper(0.05, 0.3), taper(0.03, 0.3))

    # neck and head (a lit face on the front, hair over the crown)
    P.ribbon(_lerp((0.0, 0.0, 3.75), (0.0, 0.0, 4.15), 4), body, (0, -1, 0), taper(0.22, 0.2), taper(0.16, 0.2))
    for j in range(5):
        hz = 4.18 + 0.17 * j
        hw = 0.44 * math.sqrt(max(0.05, 1 - ((hz - 4.52) / 0.42) ** 2))
        P.ribbon(_lerp((-hw, 0.0, hz), (hw, 0.0, hz), 4), body, (0, -1, 0), taper(0.12, 0.2), taper(0.2, 0.3))
    P.ribbon(_lerp((-0.03, D * 1.2, 4.7), (0.04, D * 1.2, 4.22), 5), "p_skin", (0, -1, 0),
             taper(0.26, 0.5), taper(0.07, 0.5))
    P.ribbon([(0.44 * math.cos(a), D * 0.4, 4.52 + 0.44 * math.sin(a)) for a in _ls(0.15, PI - 0.15, 7)],
             light, (0, -1, 0), taper(0.12, 0.3), taper(0.14, 0.3))

    # arms and hands
    for arm in _STUDY_ARMS[pose % 3]:
        pts = _poly([(arm[0][0], D * 0.3, arm[0][1]), (arm[1][0], D * 0.3, arm[1][1]),
                     (arm[2][0], D * 0.3, arm[2][1])], 5)
        P.ribbon(pts, body, (0, -1, 0), taper(0.17, 0.15), taper(0.15, 0.2))
        hx, hz = arm[2]
        P.ribbon(_lerp((hx, D * 0.5, hz + 0.12), (hx, D * 0.5, hz - 0.14), 4), "p_skin", (0, -1, 0),
                 taper(0.11, 0.4), taper(0.08, 0.4))

    P.settle("base")
    return P.finish()


BUILDERS = {"figure": B_figure, "hand": B_hand, "knife": B_knife, "swatch": B_swatch,
            "stub": B_stub, "ferrule": B_ferrule, "fragment": B_fragment,
            "study_0": lambda: B_study(0), "study_1": lambda: B_study(1), "study_2": lambda: B_study(2),
            "study_e": lambda: B_study(1, True)}


def build(args):
    name = args[0] if args else "figure"
    objs = BUILDERS[name]()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in objs:
        for v in ob.data.vertices:
            for k in range(3):
                lo[k] = min(lo[k], v.co[k])
                hi[k] = max(hi[k], v.co[k])
    print(f"BOUNDS {name} min=({lo[0]:.3f}, {lo[1]:.3f}, {lo[2]:.3f}) max=({hi[0]:.3f}, {hi[1]:.3f}, {hi[2]:.3f}) "
          f"size=({hi[0] - lo[0]:.3f}, {hi[1] - lo[1]:.3f}, {hi[2] - lo[2]:.3f})")
