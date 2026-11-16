"""Paint wing, two set pieces that reuse the land.py brush helpers (stroke, box, finish) and nature.py daubs.

crown: a giant painted tree crown that is a walkable platform. Origin = centre of the platform top. The top is
a golden route (g_goal) over x -6..6, y -8..8 at z 0; a leaf dome hangs under it down to z -6 at the centre,
bulging 1.5-2 m past the rim; six boughs fan up from one gnarled trunk that runs down to the bare canvas floor
(z -31.45) and flares into five roots.
lookout_scaffold: a painter's stretcher scaffold holding up a U-shaped lookout deck, built at Godot world
coordinates (identity placement in Godot). Godot (x, y up, z) maps to Blender (x, -z, y).
Headless bmesh, deterministic (seeded). One script, selected by args[0]: crown | lookout_scaffold.
Blender: +Z up, 1 unit = 1 m. Material names are the contract."""
import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import land as L  # noqa: E402  (brush helpers: stroke, box, finish)
import nature as N  # noqa: E402  (Parts container and the daub helper)

TAU = 2 * math.pi
Z = Vector((0, 0, 1))


# --- crown --------------------------------------------------------------------------------------

RIM_LEN = 56.0  # perimeter of the 12 x 16 m golden rect
TRUNK_TOP, TRUNK_BOT, FLOOR = -8.0, -27.5, -31.45


GOLD_T = 0.35  # golden slab thickness: flat walk face at z 0, underside at z -0.35
CORNER_C = [(4.0, 6.0), (-4.0, 6.0), (-4.0, -6.0), (4.0, -6.0)]  # centres of the 2 m corner arcs


def gold_rim():
    """Base loop of the golden outline at z 0, CCW, ~0.5 m steps: points, outward normals, and the edge noise
    (+-0.5 m, two low harmonics of the loop). The noise phases are fixed so every caller sees the same edge."""
    R, pts = 2.0, []
    for i, (cx, cy) in enumerate(CORNER_C):
        a0 = math.pi / 2 * i
        for k in range(6):
            a = a0 + math.pi / 2 * k / 6
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        ang = a0 + math.pi / 2  # end of this arc, start of the straight edge
        ex, ey = cx + R * math.cos(ang), cy + R * math.sin(ang)
        j = (i + 1) % 4
        sx, sy = CORNER_C[j][0] + R * math.cos(math.pi / 2 * j), CORNER_C[j][1] + R * math.sin(math.pi / 2 * j)
        n = max(1, round(math.hypot(sx - ex, sy - ey) / 0.5))
        for t in range(n):
            pts.append((ex + (sx - ex) * t / n, ey + (sy - ey) * t / n))
    m = len(pts)
    s = [0.0]
    for i in range(1, m):
        s.append(s[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    perim = s[-1] + math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    nrm, grow = [], []
    for i in range(m):
        (x0, y0), (x1, y1) = pts[i - 1], pts[(i + 1) % m]
        L_ = math.hypot(x1 - x0, y1 - y0)
        tx, ty = (x1 - x0) / L_, (y1 - y0) / L_
        nrm.append(Vector((ty, -tx, 0.0)))  # CCW loop: outward is the tangent turned clockwise
        grow.append(0.3 * math.sin(TAU * 2 * s[i] / perim + 1.3) + 0.2 * math.sin(TAU * 3 * s[i] / perim + 4.1))
    return [Vector((x, y, 0.0)) for x, y in pts], nrm, grow


def golden_top(P):
    """Golden top: a 0.35 m slab with a flat walk face at z 0 and a rounded lip, built as stacked outline rings
    with fan caps (top at z 0 over the whole interior, underside at z -0.35)."""
    pts, nrm, grow = gold_rim()
    profile = [(-0.35, 0.0), (-0.10, 0.0), (0.02, -0.07), (0.04, -0.18), (0.0, -0.30), (-0.10, -GOLD_T)]
    n = len(pts)
    cos, faces = [], []
    for d, z in profile:
        for p, nv, g in zip(pts, nrm, grow):
            cos.append(Vector((p.x + nv.x * (g + d), p.y + nv.y * (g + d), z)))
    for r in range(len(profile) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i))
    last = (len(profile) - 1) * n
    top_c, bot_c = len(cos), len(cos) + 1
    cos += [Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, -GOLD_T))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((top_c, i, j))
        faces.append((bot_c, last + j, last + i))
    P.add("g_goal", cos, faces)


def leaf_ring(P):
    """Leaf blobs spilling over the golden edge: 52 blobs centred 0.2-0.5 m outside the rim. Radius <= 0.8 m
    keeps them at most ~0.72 m inward of the edge; the top stays under z 0.4 (only the edge rises above z 0)."""
    rng = P.rng
    pts, nrm, grow = gold_rim()
    n = len(pts)
    for k in range(52):
        i = int((k + rng.uniform(0, 1)) * n / 52) % n
        c = pts[i] + nrm[i] * (grow[i] + rng.uniform(0.2, 0.5))
        cz = rng.uniform(-0.6, 0.3)
        rz = min(rng.uniform(0.3, 0.45), (0.4 - cz) / 1.15)  # lump can add 15%: keep the top under 0.4
        rxy = rng.uniform(0.6, 0.8)
        L.blob(P, canopy_mat(rng), Vector((c.x, c.y, cz)), (rxy, rxy, rz), rng, detail=1)


def rim_branches(P):
    """Eight thick bough ends (bark) curling up through the golden rim at the edge, tips about 1.2 m out."""
    rng = P.rng
    pts, nrm, grow = gold_rim()
    n = len(pts)
    for k in range(8):
        i = int((k + rng.uniform(0.2, 0.8)) * n / 8) % n
        nv = nrm[i]
        base = pts[i] + nv * grow[i]
        curl = [Vector((base.x + nv.x * o, base.y + nv.y * o, z))
                for o, z in ((-0.6, -1.6), (0.0, -0.6), (0.5, -0.05), (0.95, 0.25), (1.2, 0.5))]
        L.stroke(P, "p_bark", curl, [0.9, 0.8, 0.7, 0.55, 0.35], sides=6, thick=0.6, jit=0.02)


def canopy_mat(rng):
    r = rng.random()
    return "p_yellow" if r < 0.08 else ("p_leaf_light" if r < 0.35 else "p_leaf")


def rim_point(s):
    """Point on the golden rect's edge and its outward normal, s in metres round the rim (0..56)."""
    s %= RIM_LEN
    if s < 12:
        return Vector((-6 + s, -8, 0)), Vector((0, -1, 0))
    s -= 12
    if s < 16:
        return Vector((6, -8 + s, 0)), Vector((1, 0, 0))
    s -= 16
    if s < 12:
        return Vector((6 - s, 8, 0)), Vector((0, 1, 0))
    s -= 12
    return Vector((-6, 8 - s, 0)), Vector((-1, 0, 0))


def tier(P, z, bulge, count, T=0.3, detail=2):
    """One tier of leaf daubs wrapping the golden rect's rim at height z, pushed out by bulge (metres)."""
    rng = P.rng
    for k in range(count):
        p, nrm = rim_point((k + rng.uniform(0, 1)) * RIM_LEN / count)
        c = Vector((p.x, p.y, z)) + nrm * (bulge * rng.uniform(0.7, 1.1)) + Vector((0, 0, rng.uniform(-0.1, 0.1)))
        tang = Vector((-nrm.y, nrm.x, 0.0))
        d = tang + Vector((0.0, 0.0, rng.gauss(0, 0.2)))
        nv = nrm * rng.uniform(0.5, 1.0) + Vector((0.0, 0.0, rng.gauss(0, 0.5)))
        N.daub(P, canopy_mat(rng), c, d, nv, rng.uniform(1.2, 1.7), rng.uniform(0.7, 1.0), T,
               detail=detail, jit=0.03)


def skirt(P):
    """Leaf dome, outer tiers: the top tier laps over the golden edge by ~0.5 m (stays below z 0.1 inside the
    rect), the middle tiers bulge 1.5-2 m past the rect at z -1..-3, the lowest tier pulls back in toward the trunk."""
    tier(P, -0.5, 0.1, 48, T=0.25)
    tier(P, -1.6, 1.4, 56)
    tier(P, -2.9, 1.8, 56)
    tier(P, -4.4, 0.9, 44)


def interior_canopy(P):
    """Leaf mass under the golden top, filling a bowl: z -6 at the trunk, about -0.5 at the rim. Dense enough
    that no gap shows the slab underside from below."""
    rng = P.rng
    for _ in range(330):
        x, y = rng.uniform(-6.8, 6.8), rng.uniform(-9.2, 9.2)
        q = (x / 6.8) ** 2 + (y / 9.2) ** 2
        if q > 1.0:
            continue
        zl = -6.0 + 5.5 * math.sqrt(q)
        z = rng.uniform(zl + 0.1, -0.4)
        phi = rng.uniform(0, TAU)
        d = Vector((math.cos(phi), math.sin(phi), rng.gauss(0, 0.15)))
        nv = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        N.daub(P, canopy_mat(rng), Vector((x, y, z)), d, nv, rng.uniform(1.2, 1.6), rng.uniform(0.7, 0.9), 0.25,
               detail=1, jit=0.03)


def boughs_and_trunk(P):
    rng = P.rng
    # six thick boughs fanning from the trunk top (z -8) up and out into the canopy
    for k in range(6):
        a = TAU * k / 6 + rng.uniform(-0.3, 0.3)
        pts = [Vector((r * math.cos(a), r * math.sin(a), z))
               for r, z in ((0.6, -8.0), (2.5, -6.2), (4.5, -4.2), (6.5, -2.4))]
        L.stroke(P, "p_bark", pts, [1.4, 1.2, 1.0, 0.7], sides=6, thick=0.8, jit=0.02)
    # trunk: four intertwined twisting strands, radius 1.2 m at the top to 1.8 m at the base, gnarled not a pole
    n = 14
    for k in range(4):
        a0 = TAU * k / 4 + rng.uniform(-0.25, 0.25)
        tw = rng.uniform(1.6, 2.2) * rng.choice((-1, 1))
        pts, widths = [], []
        for i in range(n + 1):
            u = i / n  # 0 at the top, 1 at the base
            R = 1.2 + 0.6 * u
            rc = 0.45 * R * (1 + 0.12 * math.sin(5 * u + a0))
            ang = a0 + tw * u
            pts.append(Vector((rc * math.cos(ang), rc * math.sin(ang), TRUNK_TOP + (TRUNK_BOT - TRUNK_TOP) * u)))
            widths.append(1.1 * R)
        L.stroke(P, "p_bark", pts, widths, sides=6, thick=0.6, jit=0.02, jit_z=False)
    # five roots flaring out across the canvas floor, tips ~4 m out at z -31.45
    for k in range(5):
        a = TAU * k / 5 + rng.uniform(-0.35, 0.35)
        pts, widths = [], []
        for i in range(7):
            s = i / 6
            r = 0.2 + 3.9 * s ** 0.9
            ang = a + 0.12 * math.sin(4 * s)
            pts.append(Vector((r * math.cos(ang), r * math.sin(ang), TRUNK_BOT - 3.95 * s ** 0.7)))
            widths.append(1.1 * (1 - s) ** 0.7 + 0.12)
        L.stroke(P, "p_bark", pts, widths, sides=6, thick=0.5, jit=0.02, jit_z=False)


def crown(P):
    golden_top(P)
    leaf_ring(P)
    rim_branches(P)
    skirt(P)
    interior_canopy(P)
    boughs_and_trunk(P)


# --- lookout scaffold (Godot world coordinates) -------------------------------------------------

LEGS = [(5.2, -163.4), (18.6, -163.4), (5.2, -176.1), (18.6, -176.1), (9.6, -176.1), (14.0, -176.1)]
WALLS = [((5.2, -163.4), (18.6, -163.4)),  # north
         ((5.2, -163.4), (5.2, -176.1)),   # west
         ((18.6, -163.4), (18.6, -176.1)),  # east
         ((5.2, -176.1), (9.6, -176.1)),   # south, west part
         ((14.0, -176.1), (18.6, -176.1))]  # south, east part (9.6..14.0 left open)
RAILS = [4.0, 8.5, 13.0, 17.5, 22.0]  # rail bottoms; the lowest sits at 4.0 so the player walks under
KEEP_X, KEEP_Z = (7.0, 17.0), (-175.5, -167.5)  # the growing tree column: nothing enters it at any height
CENTRE = (11.9, -169.75)


def g(x, y, z):
    """Godot (x, y up, z) -> Blender (x, -z, y)."""
    return Vector((x, -z, y))


def gbox(P, mat, xa, xb, ya, yb, za, zb, n=2, amp=0.01, lean=(0.0, 0.0)):
    """Axis-aligned bar given in Godot coordinates."""
    lo = g(min(xa, xb), min(ya, yb), max(za, zb))
    hi = g(max(xa, xb), max(ya, yb), min(za, zb))
    L.box(P, mat, lo, hi, n=n, lean=lean, amp=amp)


def bar(P, mat, A, B, w, nrm, amp=0.006):
    """A square bar from A to B (Blender points), section w, its thickness axis nrm perpendicular to A->B."""
    u = (B - A).normalized()
    p = u.cross(nrm).normalized() * (w / 2)
    q = nrm.normalized() * (w / 2)
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    cos = [end + p * sx + q * sy + P.jit(amp) for end in (A, B) for sx, sy in corners]
    P.add(mat, cos, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])


def wall_rail(P, a, b, y0):
    (xa, za), (xb, zb) = a, b
    if za == zb:  # runs along X
        gbox(P, "p_wood", min(xa, xb) - 0.14, max(xa, xb) + 0.14, y0, y0 + 0.2, za - 0.1, za + 0.1, n=2, amp=0.008)
    else:  # runs along Z
        gbox(P, "p_wood", xa - 0.1, xa + 0.1, y0, y0 + 0.2, min(za, zb) - 0.14, max(za, zb) + 0.14, n=2, amp=0.008)


def wall_brace(P, a, b, y0, y1):
    """Two X cross-braces filling the panel between rail levels y0 and y1 (rail centres)."""
    (xa, za), (xb, zb) = a, b
    nrm = Vector((0, 1, 0)) if za == zb else Vector((1, 0, 0))  # the wall's normal in Blender

    def pt(t, y):
        return g(xa + (xb - xa) * t, y, za + (zb - za) * t)

    lo, hi = y0 + 0.1, y1 + 0.1
    bar(P, "p_wood_dark", pt(0, lo), pt(1, hi), 0.14, nrm)
    bar(P, "p_wood_dark", pt(0, hi), pt(1, lo), 0.14, nrm)


def assert_clear(P):
    """The tree column stays empty: no triangle's bounding box may reach into KEEP_X x KEEP_Z."""
    for bm in P.bms.values():
        for f in bm.faces:
            xs = [v.co.x for v in f.verts]
            zs = [-v.co.y for v in f.verts]
            if min(xs) < KEEP_X[1] and max(xs) > KEEP_X[0] and min(zs) < KEEP_Z[1] and max(zs) > KEEP_Z[0]:
                raise SystemExit("lookout_scaffold: a member enters the tree column")


def scaffold(P):
    rng = P.rng
    for x, z in LEGS:  # square legs, slightly out of true, splayed feet on the ground (y 0.5)
        lean = (rng.uniform(-0.002, 0.002), rng.uniform(-0.002, 0.002))
        gbox(P, "p_wood", x - 0.14, x + 0.14, 0.5, 23.4, z - 0.14, z + 0.14, n=4, amp=0.012, lean=lean)
        cx, cz = CENTRE
        m = math.hypot(x - cx, z - cz)
        fx, fz = x + (x - cx) / m * 0.12, z + (z - cz) / m * 0.12
        gbox(P, "p_wood_dark", fx - 0.24, fx + 0.24, 0.5, 0.66, fz - 0.24, fz + 0.24, n=1, amp=0.01)
    for a, b in WALLS:
        for y0 in RAILS:
            wall_rail(P, a, b, y0)
        for y0, y1 in zip(RAILS, RAILS[1:]):
            wall_brace(P, a, b, y0, y1)
    for x, z in LEGS:  # wedge keys where the rails meet the legs
        for y0 in RAILS:
            gbox(P, "p_wood_dark", x - 0.22, x + 0.22, y0 - 0.04, y0 + 0.24, z - 0.22, z + 0.22, n=1, amp=0.006)
    assert_clear(P)


# --- dispatch -----------------------------------------------------------------------------------

MODELS = {
    "crown": ("crown", 901, crown),
    "lookout_scaffold": ("lookout_scaffold", 907, scaffold),
}


def build(args):
    key = args[0] if args else ""
    if key not in MODELS:
        raise SystemExit("unknown crown model: " + key)
    name, seed, fn = MODELS[key]
    P = N.Parts(seed)
    fn(P)
    L.finish(P, name)
