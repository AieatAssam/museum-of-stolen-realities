"""Chitin Court props: carapace, silk, wax, amber, fungus. One script, selected by args[0]:
    tools/blender_build.sh wings/chitin/models/src/props.py wings/chitin/models/<name>.glb <name>
Blender +Z up, 1 m = 1 unit, front faces -Y. Origins are as each builder states."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import kit  # noqa: E402
import sculpt as S  # noqa: E402
from mathutils import Vector  # noqa: E402


# --- generic surface helpers ----------------------------------------------------------------------

def loops(name, rings, mat, cap=True, smooth=40.0):
    """Loft through closed rings (lists of Vector, equal length). cap closes the two ends with fans."""
    bm = bmesh.new()
    n = len(rings[0])
    R = [[bm.verts.new(p) for p in ring] for ring in rings]
    for i in range(len(R) - 1):
        for k in range(n):
            k1 = (k + 1) % n
            bm.faces.new((R[i][k], R[i + 1][k], R[i + 1][k1], R[i][k1]))
    if cap:
        for idx in (0, len(R) - 1):
            c = bm.verts.new(sum(rings[idx], Vector()) / n)
            for k in range(n):
                a, b = R[idx][k], R[idx][(k + 1) % n]
                bm.faces.new((c, b, a) if idx == 0 else (c, a, b))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return kit._obj(name, bm, mat, smooth)


def sheet(name, fn, U, V, thick, top_mat, rim_mat=None, uvfn=None, hint=None):
    """Thin closed slab over the grid fn(u, v), u and v in 0..1: top surface, underside `thick` below
    the surface normal, and rim strips on the four edges. Material slot 0 = top_mat, 1 = rim_mat."""
    e = 1e-3

    def nrm(u, v):
        du = fn(min(u + e, 1.0), v) - fn(max(u - e, 0.0), v)
        dv = fn(u, min(v + e, 1.0)) - fn(u, max(v - e, 0.0))
        n = du.cross(dv)
        return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))

    sgn = 1.0
    if hint is not None and nrm(0.5, 0.5).dot(Vector(hint)) < 0:
        sgn = -1.0
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap") if uvfn else None
    T = [[None] * (V + 1) for _ in range(U + 1)]
    B = [[None] * (V + 1) for _ in range(U + 1)]
    for i in range(U + 1):
        for j in range(V + 1):
            u, v = i / U, j / V
            p = fn(u, v)
            T[i][j] = bm.verts.new(p)
            B[i][j] = bm.verts.new(p - nrm(u, v) * (sgn * thick))

    def uvf(i, j):
        return uvfn(i / U, j / V) if uvfn else None

    def quad(items, mat):
        f = bm.faces.new([(T if b == 0 else B)[i][j] for (i, j), b in items])
        f.material_index = mat
        if uvl is not None:
            for lp, (ij, _) in zip(f.loops, items):
                lp[uvl].uv = uvf(*ij)

    for i in range(U):
        for j in range(V):
            quad([((i, j), 0), ((i + 1, j), 0), ((i + 1, j + 1), 0), ((i, j + 1), 0)], 0)
            quad([((i, j), 1), ((i, j + 1), 1), ((i + 1, j + 1), 1), ((i + 1, j), 1)], 0)
    rm = 1 if rim_mat and rim_mat != top_mat else 0
    for i in range(U):
        quad([((i, 0), 0), ((i + 1, 0), 0), ((i + 1, 0), 1), ((i, 0), 1)], rm)
        quad([((i, V), 0), ((i, V), 1), ((i + 1, V), 1), ((i + 1, V), 0)], rm)
    for j in range(V):
        quad([((0, j), 0), ((0, j), 1), ((0, j + 1), 1), ((0, j + 1), 0)], rm)
        quad([((U, j), 0), ((U, j + 1), 0), ((U, j + 1), 1), ((U, j), 1)], rm)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    ob = kit._obj(name, bm, None, 40.0)
    ob.data.materials.append(kit.material(top_mat))
    if rm:
        ob.data.materials.append(kit.material(rim_mat))
    return ob


def _to(f, n):
    if f.normal.dot(Vector(n)) < 0:
        f.normal_flip()


def _radial(f, cx, cz, out=True):
    c = f.calc_center_median()
    radial = Vector((c.x - cx, 0.0, c.z - cz))
    if (f.normal.dot(radial) < 0) == out:
        f.normal_flip()


# --- 1. fungus_cap ---------------------------------------------------------------------------------

def _mushroom(tag, x, y, h, R, seed, parts):
    rnd = random.Random(seed)
    bend = rnd.uniform(-0.12, 0.12) * h
    cx, cy = x + bend, y
    parts.append(S.snake(tag + "_stem", [(x, y, 0.0), (x + bend * 0.35, y + 0.01, h * 0.5), (cx, cy, h - 0.02)],
                         0.022 + 0.02 * h, "carapace_dull", seed, sides=8, wobble=0.05, taper=(1.0, 0.7), steps=2))
    H = R * 0.6
    prof = [(R * 0.96, h - 0.012)] + [(R * math.cos(a), h + H * math.sin(a)) for a in (0.0, 0.35, 0.7, 1.0, 1.25, 1.42)]
    n = 16
    rings = []
    for rr, z in prof:
        ring = []
        for k in range(n):
            th = 2 * math.pi * k / n
            wob = 1 + 0.05 * math.sin(5 * th + seed) + 0.025 * math.sin(9 * th + 2 * seed)
            ring.append(Vector((cx + rr * wob * math.cos(th), cy + rr * wob * math.sin(th), z)))
        rings.append(ring)
    parts.append(loops(tag + "_cap", rings, "fungus", cap=True))
    for g in range(8):
        th = 2 * math.pi * g / 8 + 0.2
        mid = R * 0.6
        b = kit.box(tag + "_gill%d" % g, (R * 0.7, 0.008, 0.022), mat="carapace_dull")
        kit.place(b, loc=(cx + mid * math.cos(th), cy + mid * math.sin(th), h - 0.02), rot=(0, 0, th))
        parts.append(b)


def B_fungus_cap():
    parts = []
    for k, (x, y, h, R) in enumerate([(0.0, 0.0, 1.4, 0.26), (0.32, -0.12, 0.95, 0.2), (-0.3, -0.06, 0.7, 0.17),
                                      (0.12, 0.28, 0.42, 0.14), (-0.14, 0.25, 0.3, 0.11), (0.42, 0.24, 0.55, 0.14)]):
        _mushroom("m%d" % k, x, y, h, R, 11 + k, parts)
    parts.append(S.blob("fc_floor", (1.5, 1.3, 0.06), (0, 0, -0.025), "carapace_dull", 3, lump=0.01, subdiv=2))
    return kit.join("fungus_cap", parts)


# --- 2. fungus_shelf -------------------------------------------------------------------------------

def _shelf_fn(x0, z0, R, droop, seed):
    def fn(u, v):
        phi = math.pi * u
        r = R * (0.02 + 0.98 * v)
        ripple = 0.012 * math.sin(2 * math.pi * r / 0.07 + seed) * (0.3 + 0.7 * v)  # growth rings
        gills = 0.006 * max(0.0, math.cos(16 * phi + seed)) ** 2 * v  # radial gill ridges on the underside
        lift = 0.025 * (r / R) ** 4  # the rim curls up: the shelf cups
        return Vector((x0 + r * math.cos(phi), -r * math.sin(phi),
                       z0 - droop * (r / R) ** 2 + ripple + gills + lift))
    return fn


def B_fungus_shelf():
    parts = []
    specs = [(0.02, -0.5, 0.5, 0.10, 1), (-0.04, -0.25, 0.56, 0.12, 2), (0.05, 0.0, 0.55, 0.14, 3),
             (-0.02, 0.25, 0.45, 0.10, 4), (0.04, 0.5, 0.33, 0.07, 5)]
    for x0, z0, R, droop, sd in specs:
        parts.append(sheet("shelf%d" % sd, _shelf_fn(x0, z0, R, droop, sd), 24, 6, 0.03, "fungus",
                           rim_mat="carapace_dull", hint=(0, 0, 1)))
        parts.append(S.blob("pad%d" % sd, (0.22, 0.07, 0.12), (x0, -0.02, z0), "carapace_dull", sd, lump=0.008, subdiv=1))
    return kit.join("fungus_shelf", parts)


# --- 3. cocoon_a / cocoon_b ------------------------------------------------------------------------

def _cocoon(name, L, rmax, bend, lumpy, turns, seed):
    z0 = -1.0  # the thread is 1.0 m; the cocoon hangs from its end

    def cen(t):
        return Vector((bend * math.sin(math.pi * t), 0.0, z0 - L * t))

    def rad(t, th):
        base = rmax * max(math.sin(math.pi * t), 0.0) ** 0.6
        lump = 1 + lumpy * (math.sin(3 * th + 7 * t + seed) + 0.5 * math.sin(5 * th - 3 * t + 2 * seed)
                            + 0.3 * math.sin(11 * th + 2 * t))
        return base * lump

    def pt(t, th, off=0.0):
        r = rad(t, th) + off
        return cen(t) + Vector((r * math.cos(th), r * math.sin(th), 0.0))

    NT, N = 18, 16
    rings = [[pt(0.03 + 0.94 * i / NT, 2 * math.pi * k / N) for k in range(N)] for i in range(NT + 1)]
    parts = [loops(name + "_body", rings, "silk", cap=True)]
    for k in range(4):  # spiral silk strands wrapped round the body, four of them, each a rounded cord
        th0 = k * math.pi / 2
        M = 40
        pts = [pt(0.04 + 0.92 * m / (M - 1), th0 + 2 * math.pi * turns * m / (M - 1), 0.008) for m in range(M)]
        parts.append(S.snake("%s_band%d" % (name, k), pts, 0.011, "silk", seed + k, sides=4, wobble=0.0, steps=1, caps=False))
    rf = random.Random(seed)
    for k in range(7):  # loose fibres pulled off the body, drooping
        t = 0.2 + 0.1 * k
        th = rf.uniform(0.0, 2 * math.pi)
        p0 = pt(t, th, 0.0)
        out = Vector((math.cos(th), math.sin(th), 0.0))
        parts.append(S.snake("%s_fibre%d" % (name, k), [p0, p0 + out * 0.04 + Vector((0, 0, -0.03)),
                                                         p0 + out * 0.07 + Vector((0, 0, -0.09))],
                             0.0035, "silk", seed + 20 + k, sides=4, wobble=0.2, taper=(1, 0.2), steps=2))
    zb = z0 - L
    for k in range(3):
        a = k * 2.1
        parts.append(S.snake("%s_wispT%d" % (name, k), [Vector((0, 0, z0 + 0.01)),
                                                         Vector((0.03 * math.cos(a), 0.03 * math.sin(a), z0 + 0.1)),
                                                         Vector((0.07 * math.cos(a + 0.5), 0.07 * math.sin(a + 0.5), z0 + 0.18))],
                             0.004, "silk", seed + k, sides=4, wobble=0.1, taper=(1, 0.3), steps=2))
        parts.append(S.snake("%s_wispB%d" % (name, k), [Vector((0, 0, zb - 0.01)),
                                                         Vector((0.02 * math.cos(a), 0.02 * math.sin(a), zb - 0.09)),
                                                         Vector((0.05 * math.cos(a + 1), 0.05 * math.sin(a + 1), zb - 0.2))],
                             0.004, "silk", seed + 9 + k, sides=4, wobble=0.1, taper=(1, 0.2), steps=2))
    parts.append(kit.tube(name + "_thread", [(0, 0, 0.0), (0.008, 0, -0.35), (-0.008, 0, -0.7), (0, 0, z0)], 0.008, sides=5, mat="silk"))
    # a silk collar where the thread meets the cocoon neck
    ring = [Vector((0.075 * math.cos(2 * math.pi * k / 10), 0.075 * math.sin(2 * math.pi * k / 10), z0 + 0.03)) for k in range(11)]
    parts.append(S.snake(name + "_collar", ring, 0.009, "silk", seed, sides=4, wobble=0.0, steps=1, caps=False))
    return kit.join(name, parts)


def B_cocoon_a():
    return _cocoon("cocoon_a", 1.6, 0.2, 0.0, 0.04, 5, 3)


def B_cocoon_b():
    return _cocoon("cocoon_b", 2.4, 0.28, 0.12, 0.12, 6, 7)


# --- 4. comb ---------------------------------------------------------------------------------------

def B_comb():
    rnd = random.Random(31)
    A = 0.09                       # apothem: half the cell width (0.18 across flats)
    Rc = A / math.cos(math.pi / 6)
    bm = bmesh.new()

    def ring(cx, cz, s, y):
        return [bm.verts.new(Vector((cx + Rc * s * math.cos(math.radians(30 + 60 * k)), y,
                                     cz + Rc * s * math.sin(math.radians(30 + 60 * k))))) for k in range(6)]

    for j in range(-6, 7):
        cz = j * 1.5 * Rc
        off = A if j % 2 else 0.0
        for i in range(-7, 8):
            cx = 2 * A * i + off
            ell = (cx / 1.1) ** 2 + (cz / 0.9) ** 2 + 0.08 * math.sin(3 * cx + 1.0) * math.cos(4 * cz)
            if ell > 0.9:
                continue
            d = 0.22 + 0.5 * (1 - ell) + 0.06 * math.sin(9 * cx + 5 * cz)
            kind = rnd.random()
            o0, o1 = ring(cx, cz, 0.97, 0.0), ring(cx, cz, 0.97, -d)
            i0, i1 = ring(cx, cz, 0.667, 0.0), ring(cx, cz, 0.667, -d)
            for k in range(6):
                k1 = (k + 1) % 6
                _radial(bm.faces.new((o0[k], o1[k], o1[k1], o0[k1])), cx, cz, True)
                _radial(bm.faces.new((i0[k], i0[k1], i1[k1], i1[k])), cx, cz, False)
                _to(bm.faces.new((o1[k], o1[k1], i1[k1], i1[k])), (0, -1, 0))
            if kind < 0.7:
                ya = -d + 0.04
                r = ring(cx, cz, 0.667, ya)
                c = bm.verts.new(Vector((cx, ya, cz)))
                for k in range(6):
                    f = bm.faces.new((c, r[k], r[(k + 1) % 6]))
                    f.material_index = 1
                    _to(f, (0, -1, 0))
            elif kind < 0.85:
                r0 = ring(cx, cz, 0.97, -d)
                r1 = ring(cx, cz, 0.6, -d - 0.035)
                ap = bm.verts.new(Vector((cx, -d - 0.06, cz)))
                for k in range(6):
                    k1 = (k + 1) % 6
                    _radial(bm.faces.new((r0[k], r0[k1], r1[k1], r1[k])), cx, cz, True)
                    _to(bm.faces.new((r1[k], r1[k1], ap)), (0, -1, 0))
    ob = kit._obj("comb", bm, None, 40.0)
    ob.data.materials.append(kit.material("wax"))
    ob.data.materials.append(kit.material("amber"))
    return ob


# --- 5. tapestry -----------------------------------------------------------------------------------

def _fold(x):
    return -0.04 + 0.03 * math.sin(2 * math.pi * x / 0.75)


def B_tapestry():
    def fn(u, v):
        x = -1.5 + 3.0 * u
        return Vector((x, _fold(x), -6.5 * v))

    parts = [sheet("tapestry_panel", fn, 20, 12, 0.008, "tapestry", uvfn=lambda u, v: (u, 1.0 - v))]
    parts.append(kit.tube("tap_rod", [(-1.7, 0, 0), (-0.9, 0, 0), (0, 0, 0), (0.9, 0, 0), (1.7, 0, 0)], 0.025, sides=8, mat="carapace"))
    for sx in (-1, 1):
        parts.append(kit.place(kit.lathe("tap_finial", [(0.0, -0.05), (0.03, -0.04), (0.045, -0.012), (0.045, 0.012),
                                                       (0.03, 0.04), (0.0, 0.05)], segments=14, mat="brass"),
                               loc=(sx * 1.72, 0, 0), rot=(0, math.pi / 2, 0)))
    for i in range(24):
        x = -1.5 + 3.0 * (i + 0.5) / 24
        y = _fold(x)
        parts.append(kit.tube("tap_fringe%d" % i, [(x, y, -6.5), (x + 0.004, y, -6.6), (x - 0.003, y, -6.7)], 0.006, sides=4, mat="silk"))
    return kit.join("tapestry", parts)


# --- 6. drape --------------------------------------------------------------------------------------

def B_drape():
    def z_of(x):
        return -1.2 * (1 - (x / 3.0) ** 2)

    def fn(u, v):
        x = -3.0 + 6.0 * u
        tear = 0.02 * math.sin(23 * x) * abs(2 * v - 1) ** 6 * (1 if v > 0.5 else -1)
        y = -0.25 + 0.5 * v + 0.05 * math.sin(11 * x + 0.7) + tear
        z = z_of(x) + 0.03 * math.sin(17 * x + 2.0 * v)
        return Vector((x, y, z))

    parts = [sheet("drape_ribbon", fn, 50, 5, 0.01, "silk")]
    for k, (x, L) in enumerate([(-0.9, 0.55), (0.5, 0.8), (1.4, 0.45)]):
        z = z_of(x)
        parts.append(S.snake("drape_tail%d" % k, [(x, 0.0, z - 0.02), (x + 0.02, 0.0, z - 0.3), (x + 0.01, 0.0, z - 0.6),
                                                  (x - 0.03, 0.0, z - L)], 0.017, "silk", k, sides=6, wobble=0.1,
                             taper=(1.0, 0.5), steps=2))
    return kit.join("drape", parts)


# --- 7. lamp ---------------------------------------------------------------------------------------

def B_lamp():
    parts = [kit.tube("lamp_thread", [(0, 0, 0), (0.0, 0.0, -0.5), (0.012, 0.0, -1.0), (0.0, 0.0, -1.5)], 0.008, sides=6, mat="silk"),
             kit.torus("lamp_ring", 0.16, 0.01, seg=16, rseg=6, mat="carapace", loc=(0, 0, -1.6))]
    for k in range(6):
        th = 2 * math.pi * k / 6 + 0.3
        c, s = math.cos(th), math.sin(th)
        parts.append(S.snake("lamp_rib%d" % k, [(0.16 * c, 0.16 * s, -1.6), (0.235 * c, 0.235 * s, -1.8),
                                                (0.11 * c, 0.11 * s, -1.98)], 0.011, "carapace", k, sides=6, wobble=0.04, steps=3))
    parts.append(kit.lathe("lamp_cup", [(0.0, -2.05), (0.06, -2.05), (0.1, -2.025), (0.115, -1.99), (0.118, -1.97),
                                        (0.108, -1.97), (0.1, -1.99), (0.06, -2.02), (0.0, -2.03)], segments=20, mat="wax"))
    parts.append(S.blob("lamp_bulb0", (0.1, 0.1, 0.09), (0, 0, -1.93), "fungus", 5, lump=0.01, subdiv=2))
    for k in range(4):
        th = k * math.pi / 2 + 0.7
        parts.append(S.blob("lamp_bulb%d" % (k + 1), (0.06, 0.06, 0.06), (0.05 * math.cos(th), 0.05 * math.sin(th), -1.9),
                            "fungus", 9 + k, lump=0.008, subdiv=1))
    return kit.join("lamp", parts)


# --- 8. bell ---------------------------------------------------------------------------------------

def B_bell():
    prof = [(0.1, 0.0), (0.104, 0.012), (0.08, 0.085), (0.042, 0.135), (0.012, 0.162), (0.004, 0.166),
            (0.0, 0.158), (0.02, 0.148), (0.058, 0.1), (0.085, 0.04), (0.092, 0.0)]
    n = 20
    rings = []
    for rr, z in prof:
        ring = []
        for k in range(n):
            th = 2 * math.pi * k / n
            w = 1 + 0.02 * math.sin(3 * th + z * 9)
            ring.append(Vector((rr * w * math.cos(th), rr * w * math.sin(th), z)))
        rings.append(ring)
    parts = [loops("bell_body", rings, "brass", cap=False)]
    parts.append(kit.torus("bell_loop", 0.025, 0.008, seg=20, rseg=8, mat="brass", loc=(0, 0, 0.19), rot=(math.pi / 2, 0, 0)))
    parts.append(S.snake("bell_stalk", [(0, 0, 0.15), (0, 0, 0.07), (0, 0, 0.045)], 0.004, "brass", 2, sides=6, wobble=0.0, steps=2))
    parts.append(S.blob("bell_clapper", (0.034, 0.034, 0.036), (0, 0, 0.034), "brass", 3, lump=0.002, subdiv=1))
    return kit.join("bell", parts)


# --- 9. guild_key ----------------------------------------------------------------------------------

def B_guild_key():
    parts = [kit.torus("key_bow", 0.03, 0.008, seg=20, rseg=8, mat="brass", loc=(-0.115, 0, 0)),
             S.blob("key_amber", (0.04, 0.04, 0.012), (-0.115, 0, 0), "amber", 4, lump=0.003, subdiv=2),
             kit.box("key_shaft", (0.18, 0.012, 0.012), loc=(0.01, 0, 0), mat="brass", bevel=0.003),
             kit.box("key_bit", (0.05, 0.02, 0.012), loc=(0.125, 0, 0), mat="brass", bevel=0.003)]
    for k, (x, sy) in enumerate([(0.108, 1), (0.124, -1), (0.14, 1), (0.116, -1)]):
        rot = (-math.pi / 2, 0, 0) if sy > 0 else (math.pi / 2, 0, 0)
        parts.append(kit.place(kit.lathe("key_tooth%d" % k, [(0.0, 0.0), (0.0055, 0.0), (0.0, 0.016)], segments=6, mat="brass"),
                               loc=(x, sy * 0.01, 0), rot=rot))
    return kit.join("guild_key", parts)


# --- 10. hem ---------------------------------------------------------------------------------------

def B_hem():
    N, L = 40, 0.45
    ds = L / N
    C = [Vector((0, 0, 0))]
    x = z = 0.0
    for i in range(N):
        s = (i + 0.5) * ds
        th = 0.0 if s < 0.12 else 2.6 * math.pi * ((s - 0.12) / 0.33) ** 1.6
        x += math.cos(th) * ds
        z += math.sin(th) * ds
        C.append(Vector((x, 0, z)))

    def curve(u):
        f = min(max(u, 0.0), 1.0) * N
        i = min(int(f), N - 1)
        return C[i].lerp(C[i + 1], f - i)

    def fn(u, v):
        w = 0.055 * (0.8 + 0.2 * math.sin(17 * u * L))
        p = curve(u)
        return Vector((p.x, (2 * v - 1) * w, p.z))

    parts = [sheet("hem_strip", fn, N, 4, 0.006, "tapestry", uvfn=lambda u, v: (u, v))]
    for u in (0.0, 1.0):  # rolled ends: a silk bead across each end closes the strip
        parts.append(S.snake("hem_end%d" % int(u), [fn(u, 0.0), fn(u, 1.0)], 0.005, "silk", int(u) + 5,
                             sides=6, wobble=0.0, steps=1))
    rf = random.Random(23)
    for i in range(1, 50):  # torn edge (v=1): frayed threads hang off it
        u = i / 50.0
        p = fn(u, 1.0)
        ln = 0.012 + 0.012 * rf.random()
        parts.append(S.snake("hem_fray%d" % i, [p, p + Vector((0, 0.6 * ln, -0.4 * ln)), p + Vector((0, ln, -0.9 * ln))],
                             0.0022, "silk", 30 + i, sides=4, wobble=0.2, taper=(1, 0.2), steps=1))
    return kit.join("hem", parts)


# --- 11. fragment ----------------------------------------------------------------------------------

def _hull(name, pts, mat, smooth, rnd):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    for v in bm.verts:
        if v.co.z > 0.2 and rnd.random() < 0.5:
            v.co *= 0.82            # broken top facets
        if v.co.z < -0.25:
            v.co += Vector((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), 0.0))
    return kit._obj(name, bm, mat, smooth)


def _shard_pts(scale, rnd):
    """Hull points of a faceted amber shard: a broken crown, a wide girdle, a blunt foot."""
    pts = [Vector((0, 0, 0.29 * scale))]
    for z, s, n in ((0.16, 0.6, 9), (0.02, 1.0, 13), (-0.11, 0.9, 12), (-0.23, 0.5, 8)):
        for k in range(n):
            a = 2 * math.pi * k / n + rnd.uniform(-0.15, 0.15)
            rr = s * rnd.uniform(0.85, 1.0)
            pts.append(Vector((0.2 * rr * math.cos(a) * scale, 0.12 * rr * math.sin(a) * scale, z * scale)))
    pts.append(Vector((0.02 * scale, 0.0, -0.28 * scale)))
    return pts


def _inclusion(seed):
    """A smaller carapace insect trapped in the amber: abdomen, thorax, head, ink eyes, antennae, six legs."""
    parts = [S.blob("inc_abd", (0.068, 0.045, 0.038), (-0.035, 0, -0.008), "carapace", seed, lump=0.02, subdiv=2),
             S.blob("inc_thx", (0.046, 0.038, 0.038), (0.012, 0, 0.0), "carapace", seed + 1, lump=0.02, subdiv=2),
             S.blob("inc_head", (0.028, 0.028, 0.024), (0.052, 0, 0.004), "carapace", seed + 2, lump=0.0, subdiv=2)]
    for s in (-1, 1):
        parts.append(S.blob("inc_eye%d" % s, (0.009, 0.009, 0.009), (0.066, 0.016 * s, 0.01), "ink", seed + 3, lump=0.0, subdiv=1))
        parts.append(S.snake("inc_ant%d" % s, [Vector((0.064, 0.012 * s, 0.006)), Vector((0.09, 0.04 * s, 0.03)),
                                               Vector((0.105, 0.06 * s, 0.02))], 0.0035, "carapace_dull", seed + 4, sides=4,
                             wobble=0.0, taper=(1, 0.4), steps=2))
        for k, x in enumerate((-0.03, 0.0, 0.03)):
            parts.append(S.snake("inc_leg%d%d" % (s, k), [Vector((x, 0.02 * s, -0.012)), Vector((x + 0.01, 0.055 * s, -0.05)),
                                                           Vector((x - 0.004, 0.075 * s, -0.07))], 0.0055, "carapace_dull",
                                 seed + 5 + k, sides=4, wobble=0.0, taper=(1, 0.5), steps=2))
    return parts


def _cradle(seed):
    """Brass filigree held round the shard: two elliptical girdle bands, four bowed prongs curling over the
    crown, a brass finial and small scroll curls at each foot."""
    parts = []
    for z in (-0.13, 0.1):
        ob = kit.torus("frag_band", major=0.215, minor=0.011, seg=48, rseg=6, mat="brass", loc=(0, 0, z))
        ob.scale = (1.0, 0.6, 1.0)
        parts.append(ob)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        ca, sa = math.cos(a), math.sin(a)
        pts = [Vector((0.215 * f * ca, 0.13 * f * sa, z)) for z, f in ((-0.2, 1.0), (-0.08, 1.06), (0.05, 1.1), (0.16, 1.03))]
        pts += [Vector((0.15 * ca, 0.09 * sa, 0.26)), Vector((0.08 * ca, 0.05 * sa, 0.27))]
        parts.append(S.snake("frag_prong%d" % k, pts, 0.011, "brass", seed + k, sides=6, wobble=0.0, taper=(1.0, 0.7), steps=3))
        cx, cy, cz = 0.25 * ca, 0.15 * sa, -0.26
        spiral = []
        for m in range(12):
            t = m / 11
            th = 3 * math.pi * t
            r = 0.03 * (1 - 0.5 * t)
            spiral.append(Vector((cx + r * math.cos(th) * ca, cy + r * math.cos(th) * sa, cz + r * math.sin(th))))
        parts.append(S.snake("frag_scroll%d" % k, spiral, 0.0045, "brass", seed + 10 + k, sides=4, wobble=0.0, steps=1))
    parts.append(S.blob("frag_finial", (0.04, 0.04, 0.035), (0, 0, 0.31), "brass", seed, lump=0.0, subdiv=2))
    return parts


def B_fragment():
    rnd = random.Random(19)
    shard = _hull("fragment", _shard_pts(1.0, rnd), "amber", 22.0, rnd)
    return kit.join("fragment", [shard] + _inclusion(23) + _cradle(31))


# --- 12. honey_drip --------------------------------------------------------------------------------

def _drip(tag, x, y, L, r0, bend, seed):
    rnd = random.Random(seed)
    NR, n = 13, 10
    rings = []
    for i in range(NR):
        t = i / (NR - 1)
        z = 0.012 - L * t
        cx = x + bend * t * t
        swell = 0.45 * math.exp(-((t - 0.12) / 0.07) ** 2)  # bead swelling just under the ceiling
        rr = r0 * ((1 - t) ** 0.7 + swell) + 0.01 if i else r0 * 1.3
        ring = []
        for k in range(n):
            th = 2 * math.pi * k / n
            w = 1 + 0.08 * math.sin(3 * th + seed + 5 * t) + rnd.uniform(-0.02, 0.02)
            ring.append(Vector((cx + rr * w * math.cos(th), y + rr * w * math.sin(th), z)))
        rings.append(ring)
    return [loops(tag, rings, "amber", cap=True),
            S.blob(tag + "_bulb", (0.05, 0.05, 0.06), (x + bend, y, -L - 0.02), "wax", seed, lump=0.006, subdiv=1)]


def B_honey_drip():
    parts = []
    for k, (x, y, L, r0, bend) in enumerate([(0.0, 0.0, 1.2, 0.05, 0.03), (0.22, -0.06, 0.3, 0.035, 0.0),
                                             (-0.25, 0.05, 0.6, 0.04, -0.02), (0.42, 0.03, 0.9, 0.045, 0.03),
                                             (-0.5, -0.04, 0.45, 0.035, 0.01)]):
        parts += _drip("drip%d" % k, x, y, L, r0, bend, 40 + k)
    return kit.join("honey_drip", parts)


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown prop: " + args[0])
    fn(*args[1:])
