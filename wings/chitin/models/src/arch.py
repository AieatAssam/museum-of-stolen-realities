"""Chitin Court architecture: secreted ribs, vaults, the molted gate, guild doors, the case, curtain,
pin, dais and throne. One script, selected by args[0] (B_<name>).

Build: tools/blender_build.sh wings/chitin/models/src/arch.py wings/chitin/models/<name>.glb <name>
All parts are built with bmesh and joined per model. Only SPEC material names are used.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import kit  # noqa: E402
from mathutils import Vector  # noqa: E402

TAU = 2.0 * math.pi
_parts = []


# --- mesh helpers ------------------------------------------------------------------------------

def _sp(c, e):
    """Signed power, used for superellipse shapes."""
    return math.copysign(abs(c) ** e, c)


class Mesh:
    """Accumulates faces in a bmesh. uv=True stores parametric 0..1 UVs (membranes only)."""

    def __init__(self, uv=False):
        self.bm = bmesh.new()
        self.uvon = uv
        self.uvs = {}

    def v(self, p):
        return self.bm.verts.new((p[0], p[1], p[2]))

    def f(self, vs):
        out = []
        for x in vs:
            if not out or out[-1] is not x:
                out.append(x)
        while len(out) > 1 and out[0] is out[-1]:
            out.pop()
        if len(out) < 3:
            return
        try:
            self.bm.faces.new(out)
        except ValueError:
            pass

    def done(self, name, mat, smooth=60.0):  # 60 deg: 8-10 sided tubes stay smooth, not faceted
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if self.uvon and self.uvs and all(v in self.uvs for v in bm.verts):
            layer = bm.loops.layers.uv.new("UVMap")
            for face in bm.faces:
                for loop in face.loops:
                    loop[layer].uv = self.uvs[loop.vert]
        _parts.append(kit._obj(name, bm, mat, smooth))


def finish(name):
    """Join every part made since the last finish into one object called name."""
    global _parts
    parts = _parts
    _parts = []
    if len(parts) == 1:
        parts[0].name = name
        parts[0].data.name = name
        return parts[0]
    return kit.join(name, parts)


def loft(m, rings, caps=True, wrap=False):
    """Connect rings of points (each ring a closed loop). wrap joins the last ring to the first."""
    rings = [[Vector(p) for p in r] for r in rings]
    V = []
    for r in rings:
        if all((p - r[0]).length < 1e-9 for p in r):
            V.append([m.v(r[0])] * len(r))  # a point (pole): one shared vertex
        else:
            V.append([m.v(p) for p in r])
    R, n = len(rings), len(rings[0])
    for i in range(R if wrap else R - 1):
        a, b = V[i], V[(i + 1) % R]
        for k in range(n):
            k2 = (k + 1) % n
            m.f([a[k], b[k], b[k2], a[k2]])
    if caps and not wrap:
        for idx in (0, R - 1):
            ring = V[idx]
            c = m.v(sum((p for p in rings[idx]), Vector()) / n)
            for k in range(n):
                k2 = (k + 1) % n
                if idx == 0:
                    m.f([c, ring[k2], ring[k]])
                else:
                    m.f([c, ring[k], ring[k2]])


def grid(m, fn, nu, nv, wu=False):
    """Parametric surface fn(u, v) -> point, u and v in 0..1. wu: u wraps (closed around)."""
    nr = nu if wu else nu + 1
    G = []
    for i in range(nr):
        row = []
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            vert = m.v(fn(u, v))
            if m.uvon:
                m.uvs[vert] = (u, v)
            row.append(vert)
        G.append(row)
    for i in range(nr):
        i2 = (i + 1) % nr if wu else i + 1
        if i2 >= nr:
            break
        for j in range(nv):
            m.f([G[i][j], G[i2][j], G[i2][j + 1], G[i][j + 1]])
    return G


def thick_sheet(m, fnf, fnb, nu, nv):
    """Two parallel grids joined around their edge: a closed, consistently oriented thin slab."""
    gf = grid(m, fnf, nu, nv)
    gb = grid(m, fnb, nu, nv)
    per = ([(0, j) for j in range(nv + 1)] + [(i, nv) for i in range(1, nu + 1)]
           + [(nu, j) for j in range(nv - 1, -1, -1)] + [(i, 0) for i in range(nu - 1, 0, -1)])
    L = len(per)
    for k in range(L):
        a, b = per[k], per[(k + 1) % L]
        m.f([gf[a[0]][a[1]], gf[b[0]][b[1]], gb[b[0]][b[1]], gb[a[0]][a[1]]])


def superq(m, c, r, e1=1.0, e2=1.0, nu=24, nv=14, v0=-math.pi / 2, v1=math.pi / 2, xf=None):
    """Superellipsoid around c with radii r. xf maps the local point before the centre is added."""
    def fn(u, v):
        om = TAU * u
        eta = v0 + (v1 - v0) * v
        p = Vector((r[0] * _sp(math.cos(eta), e1) * _sp(math.cos(om), e2),
                    r[1] * _sp(math.cos(eta), e1) * _sp(math.sin(om), e2),
                    r[2] * _sp(math.sin(eta), e1)))
        return (xf(p) if xf else p) + Vector(c)
    return grid(m, fn, nu, nv, wu=(v0 == -math.pi / 2 and v1 == math.pi / 2) or True)


def torus(m, R, r, center=(0, 0, 0), xf=None, nu=40, nv=10):
    """Ring in the XY plane around Z (or mapped by xf)."""
    def fn(u, v):
        th, ph = TAU * u, TAU * v
        p = Vector(((R + r * math.cos(ph)) * math.cos(th), (R + r * math.cos(ph)) * math.sin(th), r * math.sin(ph)))
        return xf(p) if xf else p + Vector(center)
    return grid(m, fn, nu, nv, wu=True)


def sweep(m, path, sec, up=(0, 0, 1), caps=True):
    """Sweep a section sec(t) -> [(a, b)] along path (parallel-transported frame, N = up)."""
    P = [Vector(p) for p in path]
    n = len(P)
    up = Vector(up)
    rings = []
    N = None
    for i in range(n):
        T = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        if N is None:
            N = up - T * up.dot(T)
            if N.length < 1e-6:
                N = Vector((1, 0, 0)) - T * T.x
        N = N - T * N.dot(T)
        N.normalize()
        B = T.cross(N)
        t = i / (n - 1)
        rings.append([P[i] + N * a + B * b for a, b in sec(t)])
    loft(m, rings, caps=caps, wrap=False)


def _circ(rf, n=8):
    """Section factory: circle of radius rf(t) with n sides."""
    return lambda t: [(rf(t) * math.cos(TAU * k / n), rf(t) * math.sin(TAU * k / n)) for k in range(n)]


def hex_cell(m, R, ang0, to3, base_s=0.94, top_s=0.86):
    """A shallow bevelled hex: base ring (inset slightly) to a smaller top ring, capped. to3(a, b, level)."""
    r0, r1 = [], []
    for k in range(6):
        a = ang0 + k * math.pi / 3
        ca, sa = math.cos(a), math.sin(a)
        r0.append(m.v(to3(R * base_s * ca, R * base_s * sa, 0)))
        r1.append(m.v(to3(R * top_s * ca, R * top_s * sa, 1)))
    c = m.v(to3(0.0, 0.0, 1))
    for k in range(6):
        k2 = (k + 1) % 6
        m.f([r0[k], r0[k2], r1[k2], r1[k]])
        m.f([c, r1[k], r1[k2]])


def _seg(a, b, n):
    a, b = Vector(a), Vector(b)
    return [a + (b - a) * (k / n) for k in range(n)]


def _arc(c, r, a0, a1, n):
    return [Vector((c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n)))
            for k in range(n)]


# --- rib -----------------------------------------------------------------------------------------

def B_rib():
    """Engaged carapace rib, 1 m module along Z. Back flat on y=0, lens-shaped front with a keel and grooves."""
    m = Mesh()
    NZ, NS = 22, 26
    rings = []
    for j in range(NZ + 1):
        z = j / NZ
        d = (0.7 + (0.35 - 0.7) * z) * (1 + 0.03 * math.sin(TAU * 1.5 * z))
        w = 0.8 + (0.45 - 0.8) * z
        ring = []
        for i in range(NS + 1):
            s = -1 + 2 * i / NS
            f = ((1 - s * s) ** 0.6 * (1 + 0.12 * math.exp(-(s / 0.13) ** 2)) / 1.12
                 - 0.05 * math.exp(-((abs(s) - 0.52) / 0.09) ** 2))
            ring.append(Vector((w / 2 * s, -d * f, z)))
        rings.append(ring)
    loft(m, rings, caps=True, wrap=False)
    m.done("rib", "carapace")
    finish("rib")


# --- vault rib -------------------------------------------------------------------------------------

def B_vault_rib():
    """Free-standing gothic ogive, outer faces at x +-6 and z 0..9. Lens section with an outer keel; five
    segments swell mid-length and pinch at the joint collars; spines along the outer edge."""
    cx, R = 3.98, 9.56  # arc centre x and radius: springing at x=+-5.58 (centreline), apex at z 8.70
    ta = math.acos(-cx / R)

    def P(s):
        if s <= 0.5:
            th = math.pi + (ta - math.pi) * (s / 0.5)
            return Vector((cx + R * math.cos(th), 0.0, R * math.sin(th)))
        th = math.pi + (ta - math.pi) * ((1.0 - s) / 0.5)
        return Vector((-(cx + R * math.cos(th)), 0.0, R * math.sin(th)))

    def sec_at(s, sc=1.0):
        g = 1.0 - abs(2.0 * s - 1.0)  # 0 at the springings, 1 at the crown
        pinch = sum(math.exp(-((s - k / 5.0) / 0.025) ** 2) for k in range(1, 5))  # joint collars
        sw = 1.0 + 0.12 * math.sin(math.pi * ((s * 5.0) % 1.0)) - 0.12 * pinch  # swell mid-segment
        w = (0.6 - 0.2 * g) * sc * sw  # Y width (lens)
        d = (0.76 - 0.4 * g) * sc * sw  # radial depth
        out = []
        for k in range(16):
            th = TAU * k / 16
            c, sn = math.cos(th), math.sin(th)
            a = (w / 2) * _sp(c, 0.6)
            b = (d / 2) * _sp(sn, 0.6)
            if sn > 0:  # outer keel, a ridge along the extrados
                b += 0.035 * sc * sw * math.exp(-(a / 0.04) ** 2)
            out.append((a, b))
        return out

    N = 110
    main = Mesh()
    sweep(main, [P(i / (N - 1)) for i in range(N)], lambda t: sec_at(t), up=(0, 1, 0))
    main.done("vault_rib", "carapace")
    cols = Mesh()
    for k in range(1, 5):
        s0 = k / 5.0
        path = [P(s0 - 0.012 + 0.024 * i / 3) for i in range(4)]
        sweep(cols, path, lambda t, s0=s0: sec_at(s0 - 0.012 + 0.024 * t, 1.3), up=(0, 1, 0))
    cols.done("vault_collars", "carapace_dull")
    sp = Mesh()
    for k in range(12):  # spines on the outer edge, leaning up toward the crown; clear of the floor
        s = 0.04 + 0.92 * k / 11
        p = P(s)
        T = (P(min(s + 0.005, 1.0)) - P(max(s - 0.005, 0.0))).normalized()
        Bv = T.cross(Vector((0, 1, 0))).normalized()  # outward
        bmax = max(b for _, b in sec_at(s))
        base = p + Bv * bmax * 0.9
        tip = base + (Bv * 0.9 + T * 0.45).normalized() * 0.12
        sweep(sp, [base, tip], _circ(lambda t: 0.03 * (1 - t) + 0.004, 5), up=(0, 1, 0))
    sp.done("vault_spines", "carapace")
    finish("vault_rib")

# --- lip -----------------------------------------------------------------------------------------

def B_lip():
    """Ledge edge moulding, 1 m along X, periodic so modules tile. Bead, undercut, scalloped drip."""
    def prof(x):
        ph = (x % (1 / 6.0)) / (1 / 6.0)
        zb = -0.45 + 0.05 * abs(math.sin(math.pi * ph))
        return [(0.0, 0.06), (-0.05, 0.058), (-0.10, 0.03), (-0.09, -0.02), (-0.05, -0.05),
                (-0.20, -0.19), (-0.22, -0.28), (-0.14, zb), (-0.07, -0.36), (0.0, -0.34)]

    xs = [-0.5 + k / 24.0 for k in range(25)]
    rings = [[Vector((x, y, z)) for (y, z) in prof(x)] for x in xs]
    m = Mesh()
    loft(m, rings, caps=True, wrap=False)
    m.done("lip", "carapace")
    finish("lip")


# --- gate ----------------------------------------------------------------------------------------

def B_gate():
    """Molted outer gate: two split elytral husks (molt) with carapace hoops inside, and a domed head capsule
    with curved mandibles and broken antennae. Clear opening y -3..3, z 0..7."""
    NA, NZ = 36, 120
    phc = math.pi  # the split faces the opening on both jambs

    def hsh(n, s):
        return (math.sin(n * 12.9898 + s * 78.233) * 43758.5453) % 1.0

    def dsplit(j, sg):  # half-gap of the torn split, per row: irregular, so the edge tears in z
        return 0.6 + 0.2 * hsh(j, sg) + 0.04 * math.sin(0.9 * j + sg)

    def bw(z):  # tapers toward the lintel, bowed like an elytron
        return 0.9 - 0.3 * (z / 7.0) ** 2 + 0.06 * math.sin(math.pi * z / 7.0)

    def pt(sg, ph, z, da=0.0, outer=True):
        a = 1.45 - 0.5 * (z / 7.0)  # wall depth tapers toward the lintel
        b = bw(z)
        o = da
        if outer:  # raised longitudinal striae, grooved segment seams on the outer face
            o += 0.034 * max(0.0, math.cos(7.0 * ph)) ** 3
            o -= 0.012 * sum(math.exp(-((z - zk) / 0.045) ** 2) for zk in (1.2, 2.6, 4.0, 5.4))
        bow = sg * 0.2 * math.sin(math.pi * z / 7.0)  # jambs bow away from the opening
        return Vector(((b + o) * math.sin(ph), sg * (3.05 + a + (a + o) * math.cos(ph)) + bow, z))

    def curl(k):  # the torn lips curl slightly outward
        return 0.035 * (math.exp(-(k / 1.5) ** 2) + math.exp(-((NA - k) / 1.5) ** 2))

    mc = Mesh()
    for sg in (-1, 1):
        rings = []
        for j in range(NZ + 1):
            z = 7.0 * j / NZ
            d = dsplit(j, sg)
            ring = [pt(sg, phc + d + (TAU - 2 * d) * k / NA, z, curl(k)) for k in range(NA + 1)]
            ring += [pt(sg, phc + d + (TAU - 2 * d) * k / NA, z, -0.05, outer=False) for k in range(NA, -1, -1)]
            rings.append(ring)
        jm = Mesh()
        loft(jm, rings, caps=False, wrap=False)
        jm.done("jamb", "molt")
        for zk in (1.8, 4.0, 6.0):  # carapace hoops sunk into the inner wall: the ribs seen inside the husk
            d = dsplit(int(zk / 7.0 * NZ), sg)
            span = TAU - 2 * d
            path = [pt(sg, phc + d + 0.2 + 0.7 * span * k / 24, zk, -0.045, outer=False) for k in range(25)]
            sweep(mc, path, _circ(lambda t: 0.02, 6), up=(0, 0, 1), caps=False)

    def top(y):  # dome height above the lintel centre line, highest at y=0
        return 0.6 + 0.4 * math.sqrt(max(0.0, 1 - (y / 6.2) ** 2))

    for sx in (-1, 1):  # great curved mandibles hang from the head into the opening, tips above z 5.5
        pts = [Vector((sx * 0.72, y, z)) for y, z in ((-3.4, 7.6), (-2.9, 6.9), (-2.45, 6.35), (-1.95, 6.0), (-1.45, 5.85), (-1.05, 5.82))]
        sweep(mc, pts, lambda t: [((0.07 - 0.03 * t) * math.cos(TAU * k / 8), (0.2 * (1 - t) + 0.03 * t) * math.sin(TAU * k / 8))
                                  for k in range(8)], up=(1, 0, 0))
        for i in (1, 2, 3, 4):  # teeth along the blade edge
            base = pts[i] + Vector((0.0, 0.07, 0.0))
            sweep(mc, [base, base + Vector((0.0, 0.09, -0.1))], _circ(lambda t: 0.04 * (1 - t) + 0.003 * t, 5), up=(1, 0, 0))
    for sx in (-1, 1):  # broken antenna stubs lying along the dome
        pts = [Vector((sx * 0.5, y, 8.0 + 0.987 * top(y) - 0.02)) for y in (1.2, 2.2, 3.2, 4.2)]
        sweep(mc, pts, _circ(lambda t: 0.07 - 0.02 * t, 7), up=(0, 0, 1), caps=True)
    mc.done("gate_seams", "carapace")

    lt = Mesh()  # head capsule: domed, highest at y=0; blunt closed nose at -Y; underside >= 7.0 in the opening
    NY, NS = 48, 24

    def lint_ring(y):
        s = math.sqrt(max(0.0, 1 - ((y + 5.3) / 0.9) ** 2)) if y < -5.3 else 1.0
        taper = 1 - 0.3 * (y / 6.2) ** 2 if y > 0 else 1.0
        pinch = 1 - 0.08 * sum(math.exp(-((y - yk) / 0.15) ** 2) for yk in (-3.6, -1.2, 1.2, 3.6))
        ay = abs(y)
        bb = 0.95 if ay < 3.0 else 0.95 + 0.35 * min(1.0, (ay - 3.0) / 0.6)  # sinks onto the jamb tops outside
        a = 1.0 * s * taper * pinch
        bt = top(y) * s * pinch
        bl = bb * s * taper * pinch
        ring = []
        for k in range(NS):
            th = TAU * k / NS
            c, sn = math.cos(th), math.sin(th)
            x = a * _sp(c, 0.6)
            if sn > 0:
                zo = bt * _sp(sn, 0.25) + 0.12 * math.exp(-(x / 0.16) ** 2) * sn  # crest keel
            else:
                zo = bl * _sp(sn, 0.25)
            ring.append(Vector((x, y, 8.0 + zo)))
        return ring

    loft(lt, [lint_ring(-6.2 + 12.4 * j / NY) for j in range(NY + 1)], caps=True, wrap=False)
    lt.done("lintel", "carapace")
    ey = Mesh()
    for sx in (-1, 1):  # eyes
        superq(ey, (sx * 0.55, -5.9, 8.3), (0.22, 0.12, 0.22), nu=12, nv=8)
    ey.done("lintel_eyes", "ink")
    finish("gate")

# --- doors ---------------------------------------------------------------------------------------

def _door(name, W, H, fw, depth, R, lock_r, rc, yl, boss_r, sr):
    """A carapace frame with ogive top corners, a field of wax hex cells, and a round brass lock."""
    hw, hh = W / 2, H / 2
    cw, ch, rr = hw - fw / 2, hh - fw / 2, rc - fw / 2
    ax, az = hw - rc, hh - rc
    loop = (_seg((-cw, -ch), (cw, -ch), 22) + _seg((cw, -ch), (cw, az), 10)
            + _arc((ax, az), rr, 0.0, math.pi / 2, 12) + _seg((ax, ch), (-ax, ch), 10)
            + _arc((-ax, az), rr, math.pi / 2, math.pi, 12) + _seg((-cw, az), (-cw, -ch), 10))
    n = len(loop)

    def inside(x, z, inset):
        if abs(x) > hw - inset or abs(z) > hh - inset:
            return False
        if z > az and abs(x) > ax:
            r2 = rc - inset
            return ((abs(x) - ax) / r2) ** 2 + ((z - az) / r2) ** 2 <= 1.0
        return True

    fr = Mesh()
    rings = []
    for i in range(n):
        p = loop[i]
        t2 = (loop[(i + 1) % n] - loop[i - 1]).normalized()
        nrm = Vector((t2.y, -t2.x))  # outward for this CCW loop
        ring = []
        for k in range(12):
            ph = TAU * k / 12
            q = p + nrm * (_sp(math.cos(ph), 0.8) * fw / 2)
            ring.append(Vector((q.x, _sp(math.sin(ph), 0.8) * depth / 2, q.y)))
        rings.append(ring)
    loft(fr, rings, caps=False, wrap=True)
    fr.done(name + "_frame", "carapace")

    pl = Mesh()  # backing plate inside the frame, so the field is solid from behind
    pf = [pl.v(Vector((p.x, -0.02, p.y))) for p in loop]
    pb = [pl.v(Vector((p.x, 0.02, p.y))) for p in loop]
    cf, cb = pl.v((0, -0.02, 0)), pl.v((0, 0.02, 0))
    for k in range(n):
        k2 = (k + 1) % n
        pl.f([pf[k], pf[k2], pb[k2], pb[k]])
        pl.f([cf, pf[k], pf[k2]])
        pl.f([cb, pb[k2], pb[k]])
    pl.done(name + "_plate", "carapace_dull")

    cells = Mesh()
    sx, sz = math.sqrt(3) * R, 1.5 * R
    for j in range(-int(hh / sz) - 2, int(hh / sz) + 3):
        z = j * sz
        off = sx / 2 if j % 2 else 0.0
        for i in range(-int(hw / sx) - 2, int(hw / sx) + 3):
            x = i * sx + off
            if not inside(x, z, fw + R) or math.hypot(x, z) < lock_r + R:
                continue
            hex_cell(cells, R, math.pi / 2,
                     lambda a, b, l, x=x, z=z: Vector((x + a, 0.0 if l == 0 else -0.05, z + b)))
    cells.done(name + "_cells", "wax")

    lk = Mesh()
    torus(lk, lock_r, lock_r * 0.078, xf=lambda p: Vector((p.x, yl + p.z, p.y)), nu=56, nv=12)
    lk.done(name + "_ring", "brass")
    bs = Mesh()
    superq(bs, (0, yl, 0), (boss_r, boss_r * 0.6, boss_r), nu=16, nv=10)
    bs.done(name + "_boss", "amber")
    st = Mesh()
    for k in range(8):
        a = TAU * k / 8
        p0 = Vector((boss_r * 0.9 * math.cos(a), yl, boss_r * 0.9 * math.sin(a)))
        p1 = Vector((lock_r * math.cos(a), yl, lock_r * math.sin(a)))
        sweep(st, [p0, p1], _circ(lambda t: sr, 6), up=(0, 1, 0))
    st.done(name + "_strings", "silk")
    finish(name)


def B_door_guild():
    _door("door_guild", 8.0, 5.0, 0.35, 0.6, 0.25, 0.9, 1.5, -0.12, 0.22, 0.02)


def B_door_vault():
    _door("door_vault", 4.0, 5.0, 0.2, 0.4, 0.22, 0.5, 0.8, -0.1, 0.12, 0.012)


# --- dais case -----------------------------------------------------------------------------------

def B_case():
    """Dais case: four curved carapace ribs rising from a round wax base to a pointed crown with an amber
    finial; amber panels between the ribs follow the ogive profile."""
    zb, zt = -0.96, 0.98

    def R(u):  # ogive: belly at the base, pointed at the crown (u 0..1, base to crown)
        return 0.74 * max(0.0, 1 - u ** 2.4) ** 0.55 + 0.04 * math.sin(math.pi * u)

    def zof(u):
        return zb + (zt - zb) * u

    ribs = Mesh()
    for k in range(4):  # ribs at 0, 90, 180, 270 degrees: the bbox is set by the rib radius
        th = k * math.pi / 2
        path = [Vector((R(u) * math.cos(th), R(u) * math.sin(th), zof(u))) for u in [i / 16 * 0.97 for i in range(17)]]
        path.append(Vector((0.0, 0.0, zt)))
        sweep(ribs, path, _circ(lambda t: 0.058 - 0.04 * t, 8), up=(-math.sin(th), math.cos(th), 0))
    ribs.done("case_ribs", "carapace")

    def panel(a0, a1, off):
        def f(s, t):
            th = a0 + (a1 - a0) * s
            u = 0.1 + 0.72 * t
            r = 0.93 * R(u) + off
            return Vector((r * math.cos(th), r * math.sin(th), zof(u)))
        return f

    panels = Mesh()
    for k in range(4):
        a0, a1 = k * math.pi / 2 + 0.2, (k + 1) * math.pi / 2 - 0.2
        thick_sheet(panels, panel(a0, a1, 0.02), panel(a0, a1, 0.0), 6, 10)
    panels.done("case_panels", "amber")

    _parts.append(kit.lathe("case_base_ring", [(0.0, -1.1), (0.7, -1.1), (0.76, -1.07), (0.78, -1.0),
                                               (0.76, -0.95), (0.5, -0.94), (0.0, -0.94)], segments=40, mat="wax"))
    fin = Mesh()
    superq(fin, (0, 0, 0.97), (0.05, 0.05, 0.09), nu=12, nv=8)
    fin.done("case_finial", "amber")
    finish("case")

# --- curtain -------------------------------------------------------------------------------------

def B_curtain():
    """Two folded membrane panels parted at the centre, from a carapace rod. UV 0..1 per panel."""
    def panel(y0, y1, ph):
        m = Mesh(uv=True)

        def pt(u, v, off):
            y = y0 + (y1 - y0) * u
            x = 0.07 * math.sin(13.0 * y + ph) * (0.7 + 0.3 * v) - off
            return Vector((x, y, 1.7 - 3.45 * v))
        thick_sheet(m, lambda u, v: pt(u, v, 0.0), lambda u, v: pt(u, v, 0.02), 20, 14)
        m.done("curtain_panel", "membrane")

    panel(-1.5, -0.05, 0.0)
    panel(0.05, 1.5, 1.3)
    rod = Mesh()
    sweep(rod, [Vector((0, -1.55, 1.72)), Vector((0, 1.55, 1.72))], _circ(lambda t: 0.04, 8), up=(0, 0, 1))
    rod.done("curtain_rod", "carapace")
    finish("curtain")


# --- pin -----------------------------------------------------------------------------------------

def B_pin():
    """Colossal entomology pin along z -65..65: brass shaft with a collar and neck, a faceted ink bead head."""
    prof = [(0.0, -65.0)]
    for k in range(1, 7):
        prof.append((0.9 * math.sqrt(k / 6.0), -65.0 + k))
    prof += [(0.9, 57.3), (1.3, 57.5), (1.3, 58.1), (0.9, 58.3), (0.9, 58.73), (0.9, 59.98)]
    rings = [[Vector((r * math.cos(TAU * q / 24), r * math.sin(TAU * q / 24), z)) for q in range(24)] for r, z in prof]
    m = Mesh()
    loft(m, rings, caps=False, wrap=False)
    m.done("pin", "brass", smooth=40.0)

    # bead head: ellipsoid, 0.8x flattened in z, top at z 65, 12 facets; starts where the neck is radius 0.9
    zc, rz, rh = 62.44, 2.56, 3.2
    phi0 = math.asin(0.9 / rh)
    hr = []
    for k in range(11):
        phi = phi0 + (math.pi - phi0) * k / 10
        r, z = rh * math.sin(phi), zc - rz * math.cos(phi)
        hr.append([Vector((r * math.cos(TAU * q / 12), r * math.sin(TAU * q / 12), z)) for q in range(12)])
    hm = Mesh()
    loft(hm, hr, caps=False, wrap=False)
    hm.done("pin_head", "ink", smooth=15.0)
    finish("pin")

# --- dais slab -----------------------------------------------------------------------------------

def B_dais():
    """Hall dais: wax hex tiles in a scalloped carapace rim, a ring of twelve amber studs."""
    R, s3 = 0.74, math.sqrt(3)
    tiles = Mesh()
    for i in range(-10, 11):
        x = i * 1.5 * R
        if abs(x) > 5.3:
            continue
        off = s3 * R / 2 if i % 2 else 0.0
        for j in range(-10, 11):
            y = j * s3 * R + off
            if abs(y) > 5.3:
                continue
            hex_cell(tiles, R, 0.0, lambda a, b, l, x=x, y=y: Vector((x + a, y + b, 0.12 if l == 0 else 0.15)))
    tiles.done("dais_tiles", "wax")

    L = 5.7
    corners = [(-L, -L), (L, -L), (L, L), (-L, L)]
    pts = []
    for k in range(4):
        a, b = Vector(corners[k]), Vector(corners[(k + 1) % 4])
        pts += [a + (b - a) * (s / 40.0) for s in range(40)]
    n = len(pts)
    sacc = [0.0]
    for k in range(n):
        sacc.append(sacc[-1] + (pts[(k + 1) % n] - pts[k]).length)
    rings = []
    for k in range(n):
        p = pts[k]
        t2 = (pts[(k + 1) % n] - pts[k - 1]).normalized()
        nrm = Vector((t2.y, -t2.x))
        ph = (sacc[k] % 0.9) / 0.9
        hw = 0.25 + 0.04 * abs(math.sin(math.pi * ph))  # scallops along the edge
        ring = []
        for q in range(8):
            ang = TAU * q / 8
            e = p + nrm * (_sp(math.cos(ang), 0.8) * hw)
            ring.append(Vector((e.x, e.y, _sp(math.sin(ang), 0.8) * 0.15)))
        rings.append(ring)
    rim = Mesh()
    loft(rim, rings, caps=False, wrap=True)
    rim.done("dais_rim", "carapace")

    _parts.append(kit.box("dais_base", size=(12.0, 12.0, 0.27), loc=(0, 0, -0.015), mat="carapace_dull"))

    st = Mesh()
    for k in range(12):
        a = TAU * k / 12
        superq(st, (4.9 * math.cos(a), 4.9 * math.sin(a), 0.12), (0.16, 0.16, 0.05), nu=12, nv=6)
    st.done("dais_studs", "amber")
    finish("dais")


# --- throne --------------------------------------------------------------------------------------

def _t_radii(z):
    """Backrest shell radii (along X, along Y) at height z: a tapering, segmenting shell."""
    tz = (z - 0.7) / 2.4
    sw = 1.0 + 0.15 * math.sin(math.pi * (((z - 0.7) / 0.6) % 1.0))
    return (0.92 - 0.2 * tz) * sw, (0.62 - 0.12 * tz) * sw


def _t_back(th, z, off=0.0):
    """A point on the backrest at angle th (back is +Y), height z, pulled in by off."""
    a, b = _t_radii(z)
    return Vector(((a - off) * math.cos(th), 0.25 + (b - off) * math.sin(th), z))


def B_throne():
    """The moulted throne on the floor (z 0), front -Y: a wax plinth with a brass band and drips, a molt seat pan
    with a wax cushion, two split backrest shells rising to z 4 under a pronotum collar, armrests grown from
    shed forelegs, and brass rivets."""
    PHI = math.pi / 2  # back is +Y
    ZB, ZT = 0.62, 4.0

    plinth = Mesh()
    superq(plinth, (0, 0, 0.21), (1.12, 0.9, 0.21), e1=0.4, e2=0.6, nu=24, nv=10)
    plinth.done("plinth", "wax")

    band = Mesh()  # brass band round the plinth, squared ellipse
    rings = []
    for z, g in ((0.17, 0.0), (0.21, 0.02), (0.25, 0.0)):
        rings.append([Vector(((1.14 + g) * _sp(math.cos(t), 0.4), (0.92 + g) * _sp(math.sin(t), 0.4), z))
                      for t in [TAU * k / 48 for k in range(48)]])
    loft(band, rings, caps=False)
    band.done("plinth_band", "brass")

    drips = Mesh()  # wax runs down the front of the plinth
    for x, L in ((-0.8, 0.22), (-0.35, 0.12), (0.1, 0.28), (0.55, 0.15), (0.92, 0.1)):
        top = Vector((x, -0.9, 0.36))
        bot = Vector((x, -0.93, 0.36 - L))
        sweep(drips, [top, top.lerp(bot, 0.5), bot], _circ(lambda t: 0.035 * (1 - t) + 0.012 * t, 8))
    drips.done("plinth_drips", "wax")

    seat = Mesh()
    superq(seat, (0, 0.05, 0.56), (0.98, 0.8, 0.14), e1=0.5, e2=0.7, nu=20, nv=10)
    seat.done("seat_pan", "molt")
    cush = Mesh()
    superq(cush, (0, 0.05, 0.72), (0.9, 0.72, 0.1), e1=0.5, e2=0.7, nu=20, nv=10)
    cush.done("cushion", "wax")

    back = Mesh()  # two shells, split down the back midline, each a thick sheet
    for side in (1, -1):
        def f(u, v, side=side, off=0.0):
            return _t_back(PHI + side * (0.08 + u * 1.52), ZB + (ZT - ZB) * v, off)
        thick_sheet(back, lambda u, v, side=side: f(u, v, side, 0.0),
                    lambda u, v, side=side: f(u, v, side, 0.05), 30, 26)
    back.done("backrest_shells", "molt")

    col = Mesh()  # pronotum collar: a hood ring round the top of the shells
    rings = []
    for z, g in ((3.5, 0.12), (3.64, 0.08), (3.82, 0.1), (4.0, 0.12)):
        a, b = _t_radii(z)
        rings.append([Vector(((a + g) * math.cos(TAU * k / 40), 0.25 + (b + g) * math.sin(TAU * k / 40), z))
                      for k in range(40)])
    loft(col, rings, caps=False)
    col.done("pronotum_collar", "carapace")

    rivets = Mesh()  # brass rivets on the band and along the shell split edges
    for k in range(12):
        t = TAU * k / 12 + 0.26
        superq(rivets, (1.16 * _sp(math.cos(t), 0.4), 0.94 * _sp(math.sin(t), 0.4), 0.21),
               (0.028, 0.028, 0.028), nu=8, nv=6)
    for z in (1.1, 1.9, 2.7, 3.3):
        for side in (1, -1):
            superq(rivets, _t_back(PHI + side * 0.08, z, -0.03), (0.034, 0.034, 0.034), nu=8, nv=6)
    rivets.done("rivets", "brass")

    arms = Mesh()  # armrests: flattened forelegs, joint collars, a curled claw at the front
    sup = Mesh()
    for sg in (-1, 1):
        path = [(0.72, 0.2, 0.95), (0.88, -0.05, 1.02), (0.98, -0.25, 1.08), (1.02, -0.5, 1.13), (1.03, -0.7, 1.16), (1.02, -0.85, 1.14)]
        P = [Vector((sg * x, y, z)) for x, y, z in path]
        sweep(arms, P, lambda t: [((0.14 + 0.08 * t) * math.cos(TAU * k / 12), (0.09 + 0.05 * t) * math.sin(TAU * k / 12))
                                  for k in range(12)])
        for idx in (2, 4):
            d = (P[idx + 1] - P[idx - 1]).normalized()
            sweep(arms, [P[idx] - d * 0.03, P[idx] + d * 0.03], _circ(lambda t: 0.19, 10))
        claw = [P[-1], Vector((sg * 1.0, -0.95, 1.02)), Vector((sg * 0.98, -0.98, 0.9))]
        sweep(arms, claw, _circ(lambda t: 0.05 * (1 - t) + 0.01 * t, 6))
        sweep(sup, [Vector((sg * 0.95, -0.45, 0.45)), Vector((sg * 1.0, -0.55, 0.98))], _circ(lambda t: 0.07, 8), up=(0, 1, 0))
    arms.done("armrests", "carapace")
    sup.done("arm_supports", "carapace_dull")

    finish("throne")


# --- dispatch ------------------------------------------------------------------------------------

def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown arch piece: " + args[0])
    fn(*args[1:])
