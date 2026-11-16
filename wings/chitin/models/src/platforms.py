"""Chitin Court platform skins: organic walkable tops laid over the unchanged platform boxes.

One script; build(args) with args[0] = a platform name from shells.json "platforms". Four kinds:
bracket (fungus shelf of fan lobes), shelf (shingled chitin plates that splay out and curl under),
stump (wax comb with dripping clusters), cocoon (silk-slung ovoid wider than the deck).

Every platform has a flat "floor" top at exactly `top` covering its rect. For the top 0.4 m the outline sits
0.05..0.3 m outside the rect (corners 0.3 m). Below that the body may reach up to 1.8 m beyond the rect and
breaks the rectangle: lobes, plates, cell clusters and an ovoid, all with off-centre stems or keels.
Coordinates are Godot world (x, y up, z); G() maps them to Blender (x, -z, y).

Build: tools/blender_build.sh wings/chitin/models/src/platforms.py wings/chitin/models/<name>.glb <name>
"""
import json
import math
import os
import random
import zlib

import bmesh
import kit

HERE = os.path.dirname(os.path.abspath(__file__))
TAU = 2.0 * math.pi
RIM_R = 0.15          # radius of the rolled lip
NF = 4                # steps in the lip fillet
SPACING = 0.6         # outline sample spacing, metres
CORNER_R = 0.4        # base-curve corner radius (the top corners are pushed to 0.3 m, asserted)
STEM_R = 0.3          # stem radius at base
WALL_ANG = math.pi    # Godot angle of the wall a shelf grows out of (assumed: the -x side)
TOP_BAND = 0.4        # the 0.3 m outline rule binds only this far below the top
RAMP0, RAMP1 = 0.4, 0.9   # body reach grows from 0 at RAMP0 to full at RAMP1 (depth below top)
REACH_MAX = 1.8       # max outward reach beyond the rect, metres
BUDGET = 25000


def G(p):
    """Godot world (x, y, z) -> Blender (x, -z, y)."""
    return (p[0], -p[2], p[1])


def lerp3(a, b, w):
    return tuple(a[i] + (b[i] - a[i]) * w for i in range(3))


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def ramp(depth):
    """0 inside the top band, full reach from RAMP1 down."""
    return smooth01((depth - RAMP0) / (RAMP1 - RAMP0))


def smooth_loop(vals, passes=2):
    """Circular 5-tap smoothing (1 2 3 2 1)/9 over per-point values, repeated: caps the slope between samples."""
    n = len(vals)
    for _ in range(passes):
        vals = [(vals[k - 2] + 2 * vals[k - 1] + 3 * vals[k] + 2 * vals[(k + 1) % n] + vals[(k + 2) % n]) / 9.0
                for k in range(n)]
    return vals


def lobe(ang, c, hw):
    """Fan-lobe weight at polar angle ang: 1 on its axis c, 0 beyond half-width hw."""
    d = (ang - c + math.pi) % TAU - math.pi
    if abs(d) >= hw:
        return 0.0
    u = 1.0 - abs(d) / hw          # cone-squared: a sharp crest, so broad lobes never read as flat
    return u * u


def load_platform(name):
    with open(os.path.join(HERE, "shells.json")) as fh:
        plats = json.load(fh)["platforms"]
    for p in plats:
        if p["name"] == name:
            return p
    raise SystemExit("unknown platform: " + name)


def inside(poly, x, z):
    """Even-odd point-in-polygon on (x, z) pairs."""
    hit = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            hit = not hit
        j = i
    return hit


class Plat:
    """A platform: lobed outline around its rect, with per-point normals, offsets and lip radii."""

    def __init__(self, p):
        self.name, self.kind = p["name"], p["kind"]
        x0, x1, z0, z1 = p["rect"]
        self.rect = (x0, x1, z0, z1)
        self.cx, self.cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
        self.hx, self.hz = (x1 - x0) / 2.0, (z1 - z0) / 2.0
        self.top, self.base = float(p["top"]), float(p["base"])
        self.H = self.top - self.base
        self.crc = zlib.crc32(self.name.encode())
        ph = random.Random(self.crc ^ 0x9E37)
        self.ph = [ph.uniform(0.0, TAU) for _ in range(3)]
        psi_s = ph.uniform(0.0, TAU)                       # stem sits off-centre, toward psi_s
        self.sx = self.cx + 0.4 * self.hx * math.cos(psi_s)
        self.sz = self.cz + 0.4 * self.hz * math.sin(psi_s)
        self._outline()
        self.maxoff = list(self.d)                          # widest outward offset seen per outline point

    def _outline(self):
        r0 = CORNER_R
        ax, az = self.hx - r0, self.hz - r0
        cen = [(ax, az), (-ax, az), (-ax, -az), (ax, -az)]
        pts = []   # (x, z, nx, nz, arc length) relative to centre
        arcs = []  # corner arc intervals in arc length
        s = 0.0
        for i, (ux, uz) in enumerate(cen):
            a0 = i * math.pi / 2
            s0 = s
            for q in range(6):
                a = a0 + math.pi / 2 * q / 6
                pts.append((ux + r0 * math.cos(a), uz + r0 * math.sin(a), math.cos(a), math.sin(a), s))
                s += r0 * (math.pi / 2) / 6
            arcs.append((s0, s))
            a1 = a0 + math.pi / 2
            px, pz = ux + r0 * math.cos(a1), uz + r0 * math.sin(a1)
            vx, vz = cen[(i + 1) % 4]
            qx, qz = vx + r0 * math.cos(a1), vz + r0 * math.sin(a1)
            L = math.hypot(qx - px, qz - pz)
            m = max(1, int(math.ceil(L / SPACING)))
            nxe, nze = (qz - pz) / L, -(qx - px) / L
            for q in range(m):
                t = q / float(m)
                pts.append((px + (qx - px) * t, pz + (qz - pz) * t, nxe, nze, s + L * t))
            s += L
        P = s
        n1 = max(1, round(P / 7.0))
        n2 = max(1, round(P / 3.0))
        n3 = max(1, round(P / 1.4))
        na = max(1, round(P / 6.0))     # integer harmonics: the wobble closes exactly around the loop
        nb = max(1, round(P / 9.0))
        nc = max(1, round(P / 13.0))

        def cdist(sk):
            best = P
            for a, b in arcs:
                if a <= sk <= b:
                    return 0.0
                best = min(best, abs(sk - a), abs(sk - b), P - abs(sk - a), P - abs(sk - b))
            return best

        self.M = len(pts)
        self.px, self.pz, self.nx, self.nz = [], [], [], []
        self.d, self.rf, self.wk, self.th = [], [], [], []
        self.ang, self.sk, self.cw, self.wb = [], [], [], []
        for x, z, nx, nz, sk in pts:
            ph_s = TAU * sk / P
            lob = 0.6 * math.sin(n1 * ph_s + 0.9) + 0.3 * math.sin(n2 * ph_s + 2.1) + 0.1 * math.sin(n3 * ph_s + 0.4)
            dl = 0.06 + 0.24 * (lob + 1.0) / 2.0             # top lobes: 0.06..0.30 m outside the rect
            cw = max(0.0, 1.0 - cdist(sk) / 0.9)            # top corners: pushed out to 0.3 m
            d = dl + (max(dl, 0.3) - dl) * cw
            self.d.append(d)
            self.rf.append(min(RIM_R, 0.4 * d))
            self.px.append(self.cx + x)
            self.pz.append(self.cz + z)
            self.nx.append(nx)
            self.nz.append(nz)
            self.th.append(math.atan2(nz, nx))
            ang = math.atan2(z, x)
            self.ang.append(ang)
            self.sk.append(sk)
            # lower body: corner weight (1 at the corners, fading over ~2 m) and a small-scale wobble
            # of 0..0.6 m with integer harmonics, so no straight run survives below the top band
            self.cw.append(max(0.0, 1.0 - cdist(sk) / 3.0) ** 2)
            self.wb.append(max(0.0, 0.6 + 0.45 * math.sin(na * ph_s + self.ph[0])
                               + 0.25 * math.sin(nb * ph_s + self.ph[1])
                               + 0.15 * math.sin(nc * ph_s + self.ph[2])))
            self.wk.append((1.0 + math.cos(ang - WALL_ANG)) / 2.0)
        self.cw = smooth_loop(self.cw)     # caps the slope between samples on short edges
        # scallop base, about 2.6 m wavelength and 0.2 m amplitude: every 2 m window bends, so none reads straight
        nbl = max(2, round(P / 6.0))
        self.bl = [0.4 * (0.5 + 0.5 * math.cos(TAU * nbl * self.sk[k] / P + self.ph[1])) for k in range(self.M)]

    def pt(self, k, off, y):
        """Outline point k pushed off metres along its normal, at height y. Asserts the top-band and reach rules."""
        if y >= self.top - TOP_BAND - 1e-9:
            assert off <= 0.3 + 1e-9, (self.name, k, off, y)
        assert off <= REACH_MAX + 1e-9, (self.name, k, off)
        assert y <= self.top + 1e-9, (self.name, y)
        self.maxoff[k] = max(self.maxoff[k], off)
        return (self.px[k] + self.nx[k] * off, y, self.pz[k] + self.nz[k] * off)

    def note(self, k, p, outline=True):
        """Record a free-form point against outline point k's normal, asserting the reach rule.
        outline=False for hanging drips: they must stay within reach but are not part of the plan outline."""
        off = (p[0] - self.px[k]) * self.nx[k] + (p[2] - self.pz[k]) * self.nz[k]
        assert off <= REACH_MAX + 1e-9, (self.name, k, off)
        assert p[1] <= self.top + 1e-9
        if outline:
            self.maxoff[k] = max(self.maxoff[k], off)

    def ring(self, offs, ys):
        out = []
        for k in range(self.M):
            o = offs[k] if isinstance(offs, list) else offs
            y = ys[k] if isinstance(ys, list) else ys
            out.append(self.pt(k, o, y))
        return out

    def stem(self, k):
        return (self.sx + STEM_R * math.cos(self.th[k]), self.base, self.sz + STEM_R * math.sin(self.th[k]))

    def reach(self, k, e):
        """Outline offset of point k with extra reach e. Soft limit: linear to 1.4 m, then approaching 1.8 m
        asymptotically, so the crest stays curved instead of clamping flat (the 1.8 m rule still holds)."""
        r = self.d[k] + e
        if r <= 1.6:
            return r
        return 1.6 + 0.2 * (1.0 - math.exp(-(r - 1.6) / 0.2))

    def fillet(self):
        """Rolled lip: ring 0 is the flat top's edge at y == top, ring NF is the outline at top - rf."""
        rings = []
        for i in range(NF + 1):
            a = (math.pi / 2) * i / NF
            offs = [self.d[k] - self.rf[k] + self.rf[k] * math.sin(a) for k in range(self.M)]
            ys = [self.top - self.rf[k] + self.rf[k] * math.cos(a) for k in range(self.M)]
            if i == 0:
                ys = self.top
            rings.append(self.ring(offs, ys))
        return rings


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(G(p)) for p in pts]

    def face(self, vs):
        try:
            self.bm.faces.new(vs)
        except ValueError:
            pass

    def strip(self, a, b):
        n = len(a)
        for k in range(n):
            k2 = (k + 1) % n
            self.face([a[k], b[k], b[k2], a[k2]])

    def fan(self, vs, center):
        c = self.bm.verts.new(G(center))
        n = len(vs)
        for k in range(n):
            self.face([c, vs[k], vs[(k + 1) % n]])

    def obj(self, name, mat, smooth=60.0, up=False):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if up:
            for f in bm.faces:
                if f.normal.z < 0:
                    f.normal_flip()
        return kit._obj(name, bm, mat, smooth)


def chain(m, rings):
    """Loft consecutive rings of points into quads. Returns the vertex list of every ring."""
    vl = [m.ring(rings[0])]
    for r in rings[1:]:
        cur = m.ring(r)
        m.strip(vl[-1], cur)
        vl.append(cur)
    return vl


class Parts:
    """Meshes keyed by material group; each becomes one object named <platform>_<key>."""

    def __init__(self, prefix):
        self.prefix = prefix
        self.meshes = {}
        self.extra = []

    def get(self, key, mat, smooth=60.0):
        if key not in self.meshes:
            self.meshes[key] = (Mesh(), mat, smooth)
        return self.meshes[key][0]

    def finish(self):
        objs = [m.obj(f"{self.prefix}_{key}", mat, smooth) for key, (m, mat, smooth) in self.meshes.items()]
        return objs + self.extra


def fin(m, p, n, L=0.2, T=0.03, hh=0.12):
    """A thin radial gill plate hanging below an underside point p, pointing along the outward normal n."""
    x, y, z = p
    nx, nz = n
    tx, tz = -nz, nx
    A = [(x - tx * T / 2, y, z - tz * T / 2), (x + tx * T / 2, y, z + tz * T / 2),
         (x + tx * T / 2 + nx * L, y, z + tz * T / 2 + nz * L), (x - tx * T / 2 + nx * L, y, z - tz * T / 2 + nz * L)]
    B = [(q[0], q[1] - hh, q[2]) for q in A]
    va, vb = m.ring(A), m.ring(B)
    m.face(va)
    m.face(vb[::-1])
    m.strip(va, vb)


# --- kinds -------------------------------------------------------------------------------------------

def kind_bracket(P, parts, fr):
    """Fungus shelf: 3-5 fan lobes of different reach fan out below the deck, growth bands run across each
    lobe, the underside funnels to an off-centre stem, and gill plates hang from the lobe undersides."""
    rnd = random.Random(P.crc)
    n = rnd.choice([3, 4, 4, 5])
    psi0 = rnd.uniform(0.0, TAU)
    lobes = []
    for i in range(n):
        lobes.append((psi0 + TAU * i / n + rnd.uniform(-0.3, 0.3),   # axis, rad
                      TAU / n * rnd.uniform(0.4, 0.55),             # half-width, rad: narrow lobes leave notches between
                      rnd.uniform(1.0, 1.5),                         # reach beyond the outline, m
                      rnd.uniform(0.5, 0.95)))                       # lobe edge closes at this fraction of H

    def ext(k, depth):
        a = P.ang[k]
        e = 0.0
        for c, hw, R, hang in lobes:
            w = lobe(a, c, hw)
            if w > 0.0:
                e = max(e, R * w * (1.0 - smooth01(depth / (hang * P.H))))
        e = max(e, 1.2 * P.cw[k])                                     # corners bulge out: no square corners
        band = 0.85 + 0.15 * math.cos(TAU * depth / 0.45 + 2.0 * a)   # curved growth bands
        return ramp(depth) * (e * band + 0.3 * P.wb[k] + 0.5 * P.bl[k])

    Lk = [max(lobe(P.ang[k], c, hw) for c, hw, _, _ in lobes) for k in range(P.M)]
    J = max(16, int(P.H * 6))
    rings = []
    for j in range(J + 1):
        u = j / float(J)
        row = []
        for k in range(P.M):
            hd = P.H * (0.3 + 0.7 * math.sqrt(Lk[k]))      # lobe tips hang to full depth, valleys stay shallow
            depth = P.rf[k] + (hd - P.rf[k]) * u
            p = P.pt(k, P.reach(k, ext(k, depth)), P.top - depth)
            row.append(lerp3(p, P.stem(k), smooth01((u - 0.55) / 0.45)))
        rings.append(row)
    chain(parts.get("lip", "carapace"), fr)
    body = parts.get("body", "carapace")
    vl = chain(body, rings)
    body.fan(vl[-1], (P.sx, P.base, P.sz))

    gills = parts.get("gills", "fungus", smooth=None)
    for j in range(2, J // 2, 2):
        for k in range(0, P.M, 4):
            # gills start a metre below the top band, and only where the lobe leaves room for the 0.2 m fin
            if Lk[k] < 0.35 or P.top - rings[j][k][1] < 1.0 or P.maxoff[k] > 1.55:
                continue
            fin(gills, rings[j][k], (P.nx[k], P.nz[k]))


def kind_shelf(P, parts, fr):
    """Chitin shelf: overlapping plates splay out past the edges and corners, each plate's sawtooth overhang
    steps out then back in, the far plate curls under, and an off-centre keel runs along the underside."""
    rnd = random.Random(P.crc)
    J, K = 24, 4
    psi0 = rnd.uniform(0.0, TAU)
    plates = [(psi0 + TAU * i / 4 + rnd.uniform(-0.3, 0.3), rnd.uniform(0.5, 0.8), rnd.uniform(0.7, 1.2))
              for i in range(4)]
    Emax = smooth_loop([max([E * lobe(P.ang[k], c, hw) for c, hw, E in plates] + [1.0 * P.cw[k]])
                        for k in range(P.M)])
    T = [1.0 + (P.H - 1.2) * (P.wk[k] ** 1.5) for k in range(P.M)]   # >= 1 m everywhere, so the ramp is full

    def row(j):
        v = j / float(J)
        S = math.sin(math.pi * v / 2.0) ** 0.7
        curl = math.sin(math.pi * v) ** 0.7
        saw = 0.05 * (1.0 - 2.0 * ((K * v) % 1.0))         # each plate overhangs the one below
        out = []
        for k in range(P.M):
            depth = P.rf[k] + (T[k] - P.rf[k]) * S
            r = ramp(depth)
            e = Emax[k] * curl + 0.6 * P.wb[k] + P.bl[k] + saw
            out.append(P.pt(k, P.reach(k, r * e), P.top - depth))
        return out

    rings = [row(j) for j in range(1, J + 1)]
    chain(parts.get("lip", "carapace"), fr)
    body = parts.get("body", "carapace")
    vl = chain(body, [fr[-1]] + rings)
    ybar = sum(p[1] for p in rings[-1]) / float(P.M)
    body.fan(vl[-1], (P.sx, ybar, P.sz))
    for r in range(1, K):
        pts = rings[r * J // K - 1]
        loop = [G(p) for p in pts] + [G(pts[0])]
        parts.extra.append(kit.tube(f"{P.name}_seam{r}", loop, 0.012, sides=4, mat="carapace_dull"))

    # off-centre keel: a ridge along the underside, nearer the far side than the middle
    Tm = sum(T) / float(P.M)
    keel = []
    for s in range(25):
        t = -1.0 + 2.0 * s / 24.0
        keel.append((P.cx + 0.85 * P.hx * t, max(P.base + 0.15, P.top - Tm) - 0.05, P.cz + 0.45 * P.hz))
    parts.extra.append(kit.tube(f"{P.name}_keel", [G(p) for p in keel], 0.12, sides=5, mat="carapace_dull"))


def kind_stump(P, parts, fr):
    """Wax comb stump: a wax slab reaches out in clusters, hex cells hang from its underside, and the cells
    past the edge are long drips (1-3.5 m) under the clusters. A few open cells glow."""
    rnd = random.Random(P.crc)
    R, s3 = 0.7, math.sqrt(3.0)
    slab_d = 1.0
    clus = [(rnd.uniform(0.0, TAU), rnd.uniform(0.6, 0.95), rnd.uniform(0.9, 1.3)) for _ in range(3)]

    def cluster_reach(a):
        return max(E * lobe(a, c, hw) for c, hw, E in clus)

    CR = smooth_loop([max(cluster_reach(P.ang[k]), 1.0 * P.cw[k]) for k in range(P.M)])

    def slab_e(k, depth):
        return ramp(depth) * (CR[k] + 0.6 * P.wb[k] + P.bl[k])

    SJ = 4
    rings = []
    for j in range(1, SJ + 1):
        u = j / float(SJ)
        row = []
        for k in range(P.M):
            depth = P.rf[k] + (slab_d - P.rf[k]) * u
            row.append(P.pt(k, P.reach(k, slab_e(k, depth)), P.top - depth))
        rings.append(row)
    chain(parts.get("lip", "wax"), fr)
    body = parts.get("body", "wax")
    vl = chain(body, [fr[-1]] + rings)
    body.fan(vl[-1], (P.cx, P.top - slab_d, P.cz))

    def hexring(cx, cz, rad, ys):
        out = []
        for q in range(6):
            a = TAU * q / 6.0
            y = ys[q] if isinstance(ys, list) else ys
            out.append((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
        return out

    cells = parts.get("cells", "wax")
    amber = parts.get("amber", "amber", smooth=None)
    crnd = random.Random(P.crc ^ 0xC311)
    nx_ = int((P.hx + 1.6) / (1.5 * R)) + 1
    nz_ = int((P.hz + 1.6) / (s3 * R)) + 1
    for i in range(-nx_, nx_ + 1):
        dx = 1.5 * R * i
        for j in range(-nz_, nz_ + 1):
            dz = s3 * R * j + (s3 * R / 2.0 if i % 2 else 0.0)
            ex = max(0.0, abs(dx) - (P.hx - 0.5 * R))
            ez = max(0.0, abs(dz) - (P.hz - 0.5 * R))
            dist = math.hypot(ex, ez)
            cx, cz = P.cx + dx, P.cz + dz
            top_y = P.top - slab_d + 0.1       # cell tops sit just inside the slab
            if dist == 0.0:
                yb = P.top - slab_d - crnd.uniform(0.35, 1.0) * (P.H - slab_d)
                yb = max(yb, P.base + 0.3)
                jit = [crnd.uniform(-0.15, 0.15) for _ in range(6)]
                rings_c = [hexring(cx, cz, 0.96 * R, top_y),
                           hexring(cx, cz, 0.9 * R, [yb + x for x in jit])]
                if crnd.random() < 0.12:
                    cen = (cx, yb + 0.03, cz)
                    amb = amber.ring(hexring(cx, cz, 0.7 * R, yb + 0.03))
                    amber.fan(amb, cen)
                    chain(cells, rings_c[:1] + [hexring(cx, cz, 0.9 * R, yb + 0.25)])
                    continue
                vl_c = chain(cells, rings_c)
                cells.fan(vl_c[-1], (cx, yb, cz))
            else:
                e_a = cluster_reach(math.atan2(dz, dx))
                if dist > min(1.0, 1.6 * e_a) or crnd.random() > 0.6:
                    continue                                # only under a cluster, within reach
                L = min(3.5, 1.0 + 2.5 * crnd.random() ** 1.5)     # drips skew short
                yb = max(P.top - slab_d - L, P.base + 0.3)
                jit = [crnd.uniform(-0.15, 0.15) for _ in range(6)]
                rings_c = [hexring(cx, cz, 0.96 * R, top_y),
                           hexring(cx, cz, 1.0 * R, [yb + 0.6 + 0.4 * x for x in jit]),
                           hexring(cx, cz, 0.7 * R, [yb + x for x in jit])]
                for q in range(6):
                    P.note(min(range(P.M), key=lambda k: abs(P.px[k] - rings_c[2][q][0]) + abs(P.pz[k] - rings_c[2][q][2])),
                           rings_c[2][q], outline=False)
                vl_c = chain(cells, rings_c)
                cells.fan(vl_c[-1], (cx, yb, cz))


def kind_cocoon(P, parts, fr):
    """Silk cocoon: an ovoid hangs from the deck, wider than it, with silk-wrapped corner lobes so it still
    covers the rect corners. Helical silk bands and strands run from the cocoon up to the deck edge."""
    rnd = random.Random(P.crc)
    yc = P.top - 0.6
    c = P.H - 0.6
    a_ax, b_ax = P.hx + 1.4, P.hz + 1.4
    lumps = (rnd.uniform(0.0, TAU), rnd.uniform(0.0, TAU))
    corners = [math.atan2(sz * P.hz, sx * P.hx) for sx, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1))]

    def corner_w(t):
        return max(math.exp(-((math.atan2(math.sin(t - cc), math.cos(t - cc))) / 0.35) ** 2) for cc in corners)

    def ovo_r(t):
        """Surface radius at polar angle t: a lumpy ellipse wider than the rect, swelling at the corners."""
        r_el = 1.0 / math.sqrt(math.cos(t) ** 2 / a_ax ** 2 + math.sin(t) ** 2 / b_ax ** 2)
        r_el *= 1.0 + 0.06 * math.sin(3 * t + lumps[0]) + 0.04 * math.sin(5 * t + lumps[1])
        # an ellipse wider than the rect (its corners clear the rect corners); a swell at the corners
        return r_el * (1.0 + 0.1 * corner_w(t))

    def surf(psi, t):
        r = 0.9 * ovo_r(t) * math.sin(1.4 * psi + 0.3)     # belly (about psi 0.9) is the widest part, seen from below
        return (P.cx + r * math.cos(t), yc - c * math.sin(psi), P.cz + r * math.sin(t))

    lip = parts.get("lip", "carapace")
    vl = chain(lip, fr + [P.ring(P.d, yc)])
    lip.fan(vl[-1], (P.cx, yc + 0.45, P.cz))        # deck underside domes up: concave from below

    JC = 18
    rings = []
    for j in range(JC):
        psi = (math.pi / 2) * j / JC
        w = smooth01(psi / 0.9)
        row = []
        for k in range(P.M):
            ox, oy, oz = P.pt(k, P.d[k], yc)
            sx_, sy_, sz_ = surf(psi, P.ang[k])
            p = (lerp3((ox, oy, oz), (sx_, sy_, sz_), w)[0], yc - c * math.sin(psi),
                 lerp3((ox, oy, oz), (sx_, sy_, sz_), w)[2])
            P.note(k, p)
            row.append(p)
        rings.append(row)
    body = parts.get("body", "silk")
    vl = chain(body, rings)
    body.fan(vl[-1], (P.cx, P.base, P.cz))

    NBs = 64
    for q in range(7):
        pts = []
        for s in range(NBs):
            t = s / float(NBs - 1)
            psi = 0.9 + 0.55 * t
            th = TAU * (q / 7.0 + 1.6 * t)
            x, y, z = surf(psi, th)
            pts.append((P.cx + (x - P.cx) * 1.03, y, P.cz + (z - P.cz) * 1.03))
        parts.extra.append(kit.tube(f"{P.name}_band{q}", [G(p) for p in pts], 0.09, sides=4, mat="silk"))

    NS, NSp = 7, 24
    for q in range(NS):
        th = TAU * q / NS + 0.35
        start = surf(1.1, th)
        k_s = min(range(P.M), key=lambda k: abs(math.atan2(math.sin(P.ang[k] - th), math.cos(P.ang[k] - th))))
        end = P.pt(k_s, min(P.d[k_s], 0.2), P.top - 0.3)     # strand ends stay inside the 0.3 m top band
        pts = []
        for s in range(NSp):
            t = s / float(NSp - 1)
            x, y, z = (start[i] + (end[i] - start[i]) * t for i in range(3))
            bow = 0.35 * math.sin(math.pi * t)
            pts.append((x + bow * math.cos(th), y, z + bow * math.sin(th)))
        parts.extra.append(kit.tube(f"{P.name}_strand{q}", [G(p) for p in pts], 0.07, sides=5, mat="silk"))
        for f in (-0.25, 0.0, 0.25):      # frayed tip at the deck edge
            dx, dz = math.cos(th) * 0.5 - math.sin(th) * f, math.sin(th) * 0.5 + math.cos(th) * f
            p2 = (end[0] + dx * 0.15, end[1] - 0.25, end[2] + dz * 0.15)    # short frays: stay within 0.3 m out
            parts.extra.append(kit.tube(f"{P.name}_fray{q}", [G(end), G(p2)], 0.03, sides=4, mat="silk"))


KINDS = {"bracket": kind_bracket, "shelf": kind_shelf, "stump": kind_stump, "cocoon": kind_cocoon}


# --- checks and build --------------------------------------------------------------------------------

def check_floor(P, ring):
    poly = [(p[0], p[2]) for p in ring]
    x0, x1, z0, z1 = P.rect
    for i in range(41):
        t = i / 40.0
        for x, z in ((x0 + (x1 - x0) * t, z0), (x0 + (x1 - x0) * t, z1),
                     (x0, z0 + (z1 - z0) * t), (x1, z0 + (z1 - z0) * t)):
            assert inside(poly, x, z), "floor does not cover the rect at %s" % ((x, z),)


def check_mesh(P, objs):
    """Every vertex of every object, tubes included: y <= top; within the top 0.4 m, at most 0.3 m beyond the
    rect; never more than 1.8 m beyond it. Blender (x, y, z) -> Godot (x, z, -y)."""
    x0, x1, z0, z1 = P.rect
    for ob in objs:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            x, y, z = w.x, w.z, -w.y
            assert y <= P.top + 0.001, (P.name, ob.name, "above top", y)
            dist = math.hypot(max(x0 - x, 0.0, x - x1), max(z0 - z, 0.0, z - z1))
            assert dist <= REACH_MAX + 0.005, (P.name, ob.name, "reach", dist)   # 5 mm: float32 mesh coords
            if y > P.top - TOP_BAND:
                assert dist <= 0.3 + 0.005, (P.name, ob.name, "top band beyond 0.3 m", round(dist, 3), round(y, 3))


def build(args):
    P = Plat(load_platform(args[0]))
    fr = P.fillet()
    check_floor(P, fr[0])

    floor = Mesh()
    floor.fan(floor.ring(fr[0]), (P.cx, P.top, P.cz))
    floor_ob = floor.obj(P.name + "_floor", "floor", smooth=None, up=True)
    for v in floor_ob.data.vertices:
        assert abs(v.co.z - P.top) <= 0.001, (P.name, v.co.z)

    parts = Parts(P.name)
    KINDS[P.kind](P, parts, fr)
    objs = [floor_ob] + parts.finish()
    check_mesh(P, objs)

    total = 0
    for ob in objs:
        t = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        total += t
        print(f"  {ob.name:30s} {t:7d} tris  mat={[s.material.name for s in ob.material_slots if s.material]}")
    print(f"TOTAL {P.name} kind={P.kind} tris={total} budget={BUDGET} outline_offset=[{min(P.d):.3f},{max(P.maxoff):.3f}] "
          f"outline_pts={P.M}")
    assert total <= BUDGET, (P.name, total)
    print("SELF-CHECK ok: floor y == top (+-0.001), floor covers rect, nothing in top 0.4 m beyond 0.3 m, "
          "nothing beyond 1.8 m, nothing above top")
