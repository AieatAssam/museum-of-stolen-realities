"""Chitin Court modular wall tiles, 4 m wide (x -2..2 exactly) so the game can butt them edge to edge:
comb_panel, plate_panel, shelf_edge, column, web. One script, selected by args[0] (B_<name>).

Build: tools/blender_build.sh wings/chitin/models/src/modules.py wings/chitin/models/<name>.glb <name>
Helpers come from arch.py (Mesh, grid, thick_sheet, loft, superq, finish) and tools/blender/kit.py.
Fixed seeds per piece: the interiors are irregular but every build is identical.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch  # noqa: E402
import kit  # noqa: E402

TAU = 2.0 * math.pi
X0, X1, Z0, Z1 = -2.0, 2.0, 0.0, 4.0
EPS = 1e-6


# --- comb panel ----------------------------------------------------------------------------------

def _bulge(x, z):
    """Gentle outward swell of the whole panel, zero on the tile border so neighbours still match."""
    return math.sin(math.pi * (x - X0) / 4.0) * math.sin(math.pi * z / 4.0)


def _pt(x, z, y):
    return (x, y * (1.0 + 0.1 * _bulge(x, z)), z)


def _on_border(p):
    return abs(p[0] - X0) < EPS or abs(p[0] - X1) < EPS or abs(p[1] - Z0) < EPS or abs(p[1] - Z1) < EPS


def _shared_edge(p, q):
    """True when p-q lies on a tile border line: no wall is built there, so tiles meet cleanly."""
    for val, i in ((X0, 0), (X1, 0), (Z0, 1), (Z1, 1)):
        if abs(p[i] - val) < EPS and abs(q[i] - val) < EPS:
            return True
    return False


def _clip(poly, axis, val, keep_hi):
    """Sutherland-Hodgman against one half-plane; crossing points are snapped exactly onto val."""
    s = 1.0 if keep_hi else -1.0
    out = []
    n = len(poly)
    for k in range(n):
        p, q = poly[k], poly[(k + 1) % n]
        dp, dq = s * (p[axis] - val), s * (q[axis] - val)
        if dp >= 0:
            out.append(p)
        if (dp >= 0) != (dq >= 0):
            t = dp / (dp - dq)
            c = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]
            c[axis] = val
            out.append(tuple(c))
    return out


def _area(poly):
    return 0.5 * abs(sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly))))


def _inward(p, q):
    ex, ez = q[0] - p[0], q[1] - p[1]
    L = math.hypot(ex, ez) or 1.0
    return (-ez / L, ex / L)  # left of an edge of a CCW polygon points inside


def _inset(poly, o):
    """Offset a convex CCW polygon inward by o (miter). Border vertices stay put."""
    n = len(poly)
    out = []
    for k in range(n):
        p = poly[k]
        if _on_border(p):
            out.append(p)
            continue
        n1 = _inward(poly[k - 1], p)
        n2 = _inward(p, poly[(k + 1) % n])
        bx, bz = n1[0] + n2[0], n1[1] + n2[1]
        L = math.hypot(bx, bz) or 1.0
        bx, bz = bx / L, bz / L
        s = o / max(bx * n1[0] + bz * n1[1], 0.5)
        out.append((p[0] + bx * s, p[1] + bz * s))
    return out


_FLOOR = -0.04
# Cell wall profile: (inset from the outer hex, depth y as a function of cell depth d). Walls run from
# the back plate, round over a rim at -d, and drop to the floor. The rim is rounded, so neighbouring
# cells read as a V-groove along each shared wall.
_PROFILE = (
    (0.000, lambda d: 0.0),
    (0.000, lambda d: -(d - 0.04)),
    (0.012, lambda d: -(d - 0.012)),
    (0.025, lambda d: -d),
    (0.040, lambda d: -(d - 0.012)),
    (0.050, lambda d: -(d - 0.04)),
    (0.050, lambda d: _FLOOR),
)


def _cell_lod(poly, depth, kind, wax, amber, dull):
    """LOD cell: inner walls only (rim to floor, one quad per edge) and one flat hex fan as the back cap.
    Same rim, floor and cap depths as _cell, no rounding. ponytail: dome cap flattened to its mean depth."""
    n = len(poly)
    yb = _FLOOR if kind != "dome" else _FLOOR - 0.035  # the dome's mean depth (0.07 bulge, area-averaged)
    rim = [wax.v(_pt(p[0], p[1], -depth[k])) for k, p in enumerate(_inset(poly, 0.025))]
    fl = [_pt(p[0], p[1], yb) for p in _inset(poly, 0.05)]
    fw = [wax.v(p) for p in fl]
    for i in range(n):
        j = (i + 1) % n
        if not _shared_edge(poly[i], poly[j]):
            wax.f([rim[i], rim[j], fw[j], fw[i]])
    fx = sum(p[0] for p in fl) / n
    fz = sum(p[2] for p in fl) / n
    mesh = dull if kind != "dome" else amber
    c = mesh.v(_pt(fx, fz, yb))
    fv = [mesh.v(p) for p in fl]
    for i in range(n):
        mesh.f([c, fv[i], fv[(i + 1) % n]])


def _cell(rnd, poly, wax, amber, dull, lod=False):
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cz = sum(p[1] for p in poly) / n
    d0 = rnd.uniform(0.30, 0.38)
    roll = rnd.random()
    kind = "dome" if roll < 0.6 else ("open" if roll < 0.9 else "broken")
    ang = rnd.uniform(0.0, TAU)
    depth = []
    for p in poly:
        cut = kind == "broken" and (p[0] - cx) * math.cos(ang) + (p[1] - cz) * math.sin(ang) > 0.0
        depth.append(d0 * 0.45 if cut else d0)  # broken cells lose half their rim

    if lod:
        _cell_lod(poly, depth, kind, wax, amber, dull)
        return
    rings = [[_pt(p[0], p[1], yf(depth[k])) for k, p in enumerate(_inset(poly, o))] for o, yf in _PROFILE]
    rv = [[wax.v(p) for p in r] for r in rings]
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            if not _shared_edge(poly[i], poly[j]):
                wax.f([rv[k][i], rv[k][j], rv[k + 1][j], rv[k + 1][i]])

    fl = [_pt(p[0], p[1], _FLOOR) for p in _inset(poly, 0.05)]
    fx = sum(p[0] for p in fl) / n
    fz = sum(p[2] for p in fl) / n
    if kind != "dome":
        c = dull.v(_pt(fx, fz, _FLOOR))
        fv = [dull.v(p) for p in fl]
        for i in range(n):
            dull.f([c, fv[i], fv[(i + 1) % n]])
        return
    # domed wax cap, bulging toward -Y (amber glows in game)
    rings_d = []
    for r in (1.0, 0.6, 0.25):
        dy = 0.07 * (1.0 - r * r)
        rings_d.append([amber.v(_pt(fx + (p[0] - fx) * r, fz + (p[2] - fz) * r, _FLOOR - dy)) for p in fl])
    for a, b in zip(rings_d, rings_d[1:]):
        for i in range(n):
            j = (i + 1) % n
            if not _shared_edge(poly[i], poly[j]):
                amber.f([a[i], a[j], b[j], b[i]])
    c = amber.v(_pt(fx, fz, _FLOOR - 0.07))
    last = rings_d[-1]
    for i in range(n):
        amber.f([c, last[i], last[(i + 1) % n]])


def _comb_panel(lod, name):
    rnd = random.Random(11)  # same seed and draws for both: identical cell layout
    wax, amber, dull = arch.Mesh(), arch.Mesh(), arch.Mesh()
    R = 0.28
    sx, sz = math.sqrt(3.0) * R, 1.5 * R  # pointy-top hex lattice
    for row in range(-2, 12):
        for col in range(-6, 7):
            cx = col * sx + (row % 2) * sx / 2.0
            cz = row * sz
            if cx < X0 - 0.5 or cx > X1 + 0.5 or cz < Z0 - 0.5 or cz > Z1 + 0.5:
                continue
            Rc = R * (1.0 + rnd.uniform(-0.08, 0.08))
            poly = [(cx + Rc * math.cos(math.pi / 2 + k * math.pi / 3), cz + Rc * math.sin(math.pi / 2 + k * math.pi / 3))
                    for k in range(6)]
            for axis, val, hi in ((0, X0, True), (0, X1, False), (1, Z0, True), (1, Z1, False)):
                poly = _clip(poly, axis, val, hi)
            if len(poly) < 3 or _area(poly) < 0.04:
                continue
            _cell(rnd, poly, wax, amber, dull, lod)
    wax.f([wax.v((X0, 0.0, Z0)), wax.v((X1, 0.0, Z0)), wax.v((X1, 0.0, Z1)), wax.v((X0, 0.0, Z1))])  # closed back
    wax.done("comb_wax", "wax")
    amber.done("comb_amber", "amber")
    dull.done("comb_dull", "carapace_dull")
    return arch.finish(name)


def B_comb_panel():
    return _comb_panel(False, "comb_panel")


def B_comb_panel_lod():
    return _comb_panel(True, "comb_panel_lod")


# --- plate panel ---------------------------------------------------------------------------------

def _scale(m, rnd, x0, x1, zb, h, row, lod=False):
    """One elytron-like plate: rounded bottom, bowed outward, central ridge, 0.04 m thick."""
    xc, hw0 = (x0 + x1) / 2.0, (x1 - x0) / 2.0
    base = -0.05 * row
    tilt = rnd.uniform(-0.05, 0.05)
    ridge_amp = rnd.uniform(0.05, 0.07)

    def front(u, v):
        a = 2.0 * u - 1.0
        t = v  # 0 at the top edge, 1 at the rounded bottom
        z = zb + h * (1.0 - t)
        hw = hw0 * (math.sqrt(max(0.0, 1.0 - ((t - 0.6) / 0.4) ** 2)) if t > 0.6 else 1.0)
        x = xc + max(hw, 0.02) * a
        bow = 0.25 * math.sqrt(max(0.0, 1.0 - a * a)) * math.sin(math.pi * (0.15 + 0.85 * t))
        ridge = ridge_amp * math.exp(-(a / 0.09) ** 2) * math.sin(math.pi * t)
        return (x, base - bow - ridge + tilt * (0.5 - t), z)

    def back(u, v):
        x, y, z = front(u, v)
        return (xc + (x - xc) * 0.94, y + 0.04, z)

    if lod:  # LOD: the front sheet only, no thickness, coarse grid
        arch.grid(m, front, 4, 3)
    else:
        arch.thick_sheet(m, front, back, 10, 6)


def _plate_panel(lod, name):
    rnd = random.Random(23)  # same seed and draws for both: identical scale layout
    sc, bk = arch.Mesh(), arch.Mesh()
    H = 1.0
    for k in range(5):  # 5 courses, pitch 0.75 with 1.0 m plates, so each course overlaps the one below
        zb = k * 0.75
        x = X0
        first = True
        while x < X1 - EPS:
            stagger = k % 2 == 1 and first
            w = rnd.uniform(0.45, 0.7) if stagger else rnd.uniform(1.0, 1.4)
            if X1 - (x + w) < 0.45:
                w = X1 - x  # the last plate absorbs the remainder so the course ends exactly on x=2
            first = False
            _scale(sc, rnd, x, x + w, zb, H, k, lod)
            x += w
    nb = 1 if lod else 4
    arch.grid(bk, lambda u, v: (X0 + 4.0 * u, 0.0, Z0 + 4.0 * v), nb, nb)
    bk.done("plate_back", "carapace_dull")
    sc.done("plate_scales", "carapace")
    return arch.finish(name)


def B_plate_panel():
    return _plate_panel(False, "plate_panel")


def B_plate_panel_lod():
    return _plate_panel(True, "plate_panel_lod")


# --- shelf edge ----------------------------------------------------------------------------------

# (zc, projection toward -Y, full thickness, lobes as (centre x, width)), top tier first
_SHELF_TIERS = (
    (-0.15, 0.50, 0.12, ((-1.5, 1.1), (-0.4, 1.4), (0.6, 0.9), (1.55, 1.0))),
    (-0.60, 0.35, 0.10, ((-1.7, 0.7), (-0.9, 0.6), (0.0, 1.0), (0.95, 0.8), (1.7, 0.6))),
    (-1.10, 0.25, 0.09, ((-1.6, 0.9), (-0.5, 0.7), (0.4, 1.2), (1.5, 0.9))),
)


def _lobe_fn(xc, W, D, zc, T, ph, sgn, r0, r1):
    """Surface of one bracket lobe. u sweeps a half-disc that starts and ends on the wall line (y = 0) and
    bulges toward -Y; v runs from radius r0 to r1. sgn picks the top (+1) or bottom (-1) face."""
    def fn(u, v):
        phi = math.pi * u
        rho = r0 + (r1 - r0) * v
        half = T * 0.5 * (0.35 + 0.65 * math.sqrt(max(0.0, 1.0 - rho * rho)))  # thick middle, rounded rim
        wob = 1.0 + 0.05 * math.sin(5.0 * phi + ph)  # irregular outline
        x = xc + 0.5 * W * rho * math.cos(phi)
        y = -D * rho * wob * math.sin(phi)
        z = zc + sgn * half + 0.008 * math.sin(7.0 * phi + ph) * rho
        return (x, y, z)
    return fn


def B_shelf_edge():
    rnd = random.Random(31)
    dull, wax = arch.Mesh(), arch.Mesh()
    gill_objs = []
    last = len(_SHELF_TIERS) - 1
    for ti, (zc, D, T, lobes) in enumerate(_SHELF_TIERS):
        for k, (xc, W) in enumerate(lobes):
            xc = min(max(xc, X0 + 0.5 * W), X1 - 0.5 * W)  # every lobe stays inside the 4 m tile
            Dk = D * rnd.uniform(0.85, 1.15)
            ph = rnd.uniform(0.0, TAU)
            arch.thick_sheet(dull, _lobe_fn(xc, W, Dk, zc, T, ph, 1.0, 0.04, 1.0),
                             _lobe_fn(xc, W, Dk, zc, T, ph, -1.0, 0.04, 1.0), 12, 3)
            # wax rim band, about 0.05 m, wrapping the outer edge of the lobe
            arch.thick_sheet(wax, _lobe_fn(xc, W, Dk, zc, T * 1.04, ph, 1.0, 0.95, 1.0),
                             _lobe_fn(xc, W, Dk, zc, T * 1.04, ph, -1.0, 0.95, 1.0), 12, 1)
            if ti == last:  # fungus gills hanging under the lowest tier, wall to rim
                under = _lobe_fn(xc, W, Dk, zc, T, ph, -1.0, 0.04, 1.0)
                for g in range(3):
                    pts = []
                    for s in range(5):
                        p = under((g + 0.5) / 3.0, 0.25 + 0.7 * s / 4.0)
                        pts.append((p[0], p[1], p[2] - 0.006))
                    gill_objs.append(kit.tube("shelf_gill%d_%d" % (k, g), pts, 0.012, sides=4, mat="fungus"))

    # 0.05 m wax strip along the top edge of the wall, top face at z = 0
    def quad(a, b, c, d):
        wax.f([wax.v(a), wax.v(b), wax.v(c), wax.v(d)])
    quad((X0, -0.05, -0.05), (X1, -0.05, -0.05), (X1, -0.05, 0.0), (X0, -0.05, 0.0))
    quad((X0, -0.05, 0.0), (X1, -0.05, 0.0), (X1, 0.0, 0.0), (X0, 0.0, 0.0))
    quad((X0, -0.05, -0.05), (X0, 0.0, -0.05), (X1, 0.0, -0.05), (X1, -0.05, -0.05))

    dull.done("shelf_body", "carapace_dull")
    wax.done("shelf_wax", "wax")
    body = arch.finish("shelf_edge")
    return kit.join("shelf_edge", [body] + gill_objs)


# --- column --------------------------------------------------------------------------------------

def _col_r(z, th):
    base = 0.55 + 0.45 * math.exp(-(z / 0.7) ** 2) + 0.45 * math.exp(-((8.0 - z) / 0.8) ** 2)
    frac = (3.0 * th / TAU - z / 2.2) % 1.0  # three spiralling fused drip ridges
    ridge = 0.05 * math.exp(-((frac - 0.5) / 0.12) ** 2)
    collar = sum(0.06 * math.exp(-((z - zc) / 0.1) ** 2) for zc in (1.6, 3.2, 4.8, 6.4))
    breathe = 0.015 * math.sin(5.0 * th + 2.0 * z)
    return base * (1.0 + ridge + breathe) + collar


def B_column():
    rnd = random.Random(41)
    NA, NZ = 36, 72
    angs = [TAU * k / NA for k in range(NA)]
    rings = []
    for j in range(NZ + 1):
        z = 8.0 * j / NZ
        rings.append([(_col_r(z, a) * math.cos(a), _col_r(z, a) * math.sin(a), z) for a in angs])
    m = arch.Mesh()
    arch.loft(m, rings, caps=True, wrap=False)
    m.done("column_body", "carapace_dull")
    body = arch.finish("column_body")

    parts = [body]
    prof = [(0.0, -0.19), (0.018, -0.16), (0.03, -0.07), (0.035, 0.0), (0.0, 0.0)]
    for i in range(6):  # wax drips hanging off the body
        z = rnd.uniform(0.5, 7.5)
        th = rnd.uniform(0.0, TAU)
        drip = kit.lathe("drip%d" % i, prof, segments=8, mat="wax")
        r = _col_r(z, th) - 0.01
        kit.place(drip, loc=(r * math.cos(th), r * math.sin(th), z))
        parts.append(drip)
    return kit.join("column", parts)


# --- web -----------------------------------------------------------------------------------------

def _edge_r(hx, hz, th):
    """Distance from the hub along direction th to the tile border."""
    dx, dz = math.cos(th), math.sin(th)
    ts = []
    if dx > 1e-9:
        ts.append((X1 - hx) / dx)
    if dx < -1e-9:
        ts.append((X0 - hx) / dx)
    if dz > 1e-9:
        ts.append((Z1 - hz) / dz)
    if dz < -1e-9:
        ts.append((Z0 - hz) / dz)
    return min(ts)


def _ang_frac(th, angs):
    """Where angle th falls between its two neighbouring radials: 0 on a radial, 0.5 halfway between."""
    tt = th % TAU
    n = len(angs)
    for i in range(n):
        a0 = angs[i]
        a1 = angs[(i + 1) % n] + (TAU if i + 1 == n else 0.0)
        t = tt if tt >= a0 else tt + TAU
        if a0 <= t < a1:
            return (t - a0) / (a1 - a0)
    return 0.0


def B_web():
    rnd = random.Random(47)
    hx, hz = 0.35, 2.15  # hub, off-centre
    N = rnd.randint(11, 13)
    angs = sorted(((k + rnd.uniform(-0.3, 0.3)) * TAU / N) % TAU for k in range(N))
    reach = [_edge_r(hx, hz, th) * rnd.uniform(0.93, 0.99) for th in angs]  # anchors, not all the same

    def radial_pt(i, t):
        r = reach[i] * t
        return (hx + r * math.cos(angs[i]), hz + r * math.sin(angs[i]))

    objs = []
    for i, th in enumerate(angs):  # radial threads, sagging a touch
        pts = []
        for s in range(6):
            t = s / 5.0
            x, z = radial_pt(i, t)
            pts.append((x, 0.0, z - 0.05 * math.sin(math.pi * t)))
        objs.append(kit.tube("radial%d" % i, pts, 0.012, sides=4, mat="silk"))

    for i in rnd.sample(range(N), 3):  # a few frame threads, chords between neighbouring anchors
        j = (i + 1) % N
        (x1, z1), (x2, z2) = radial_pt(i, 0.9), radial_pt(j, 0.9)
        pts = []
        for s in range(5):
            u = s / 4.0
            pts.append((x1 + (x2 - x1) * u, 0.0, z1 + (z2 - z1) * u - 0.08 * math.sin(math.pi * u)))
        objs.append(kit.tube("frame%d" % i, pts, 0.012, sides=4, mat="silk"))

    K, turns = 120, 6.0  # capture spiral, out to the border, drooping between radials
    spiral = []
    for k in range(K + 1):
        t = k / K
        th = t * turns * TAU
        r = t * _edge_r(hx, hz, th) * 0.95
        sag = 0.05 * t * math.sin(math.pi * _ang_frac(th, angs))
        spiral.append((hx + r * math.cos(th), 0.0, hz + r * math.sin(th) - sag))
    objs.append(kit.tube("spiral", spiral, 0.012, sides=4, mat="silk"))

    m = arch.Mesh()
    for _ in range(rnd.randint(12, 20)):  # dew beads sitting on the spiral
        arch.superq(m, spiral[rnd.randint(10, K - 5)], (0.018, 0.012, 0.018), nu=6, nv=4)
    m.done("dew", "silk")
    objs.append(arch.finish("dew"))
    return kit.join("web", objs)


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown module: " + args[0])
    fn()
