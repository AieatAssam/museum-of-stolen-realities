"""Paint wing, two set pieces that reuse the land.py brush helpers (stroke, box, finish) and nature.py daubs.

crown: a giant painted tree crown that is a walkable platform. Origin = centre of the platform top. The top is
a golden route (g_goal) over x -6..6, y -8..8 at z 0; a leaf dome hangs under it down to z -6 at the centre,
bulging 1.5-2 m past the rim; six boughs fan up from one gnarled trunk that runs down to the bare canvas floor
(z -31.45) and flares into five roots.
lookout_scaffold: a painter's stretcher scaffold holding up a U-shaped lookout deck, built at Godot world
coordinates (identity placement in Godot). Godot (x, y up, z) maps to Blender (x, -z, y).
view_scaffold: the four-leg stretcher frame under the View deck, same Godot placement as lookout_scaffold.
Headless bmesh, deterministic (seeded). One script, selected by args[0]: crown | lookout_scaffold | view_scaffold.
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


def walk_edge():
    """Outline of the flat walk face at z 0: the rim loop pulled in to the top's flat ring (d -0.10), edge noise
    included. Returns (outline as (x, y) tuples, rim points, rim outward normals)."""
    pts, nrm, grow = gold_rim()
    poly = [(p.x + n.x * (g - 0.10), p.y + n.y * (g - 0.10)) for p, n, g in zip(pts, nrm, grow)]
    return poly, pts, nrm


def sd(poly, x, y):
    """Signed distance from (x, y) to the outline: positive inside, negative outside."""
    best, inside, n = 1e9, False, len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
        best = min(best, math.hypot(ax + t * vx - x, ay + t * vy - y))
        if (ay > y) != (by > y) and x < ax + (y - ay) * vx / vy:
            inside = not inside
    return best if inside else -best


def _mark(P):
    return {m: len(bm.verts) for m, bm in P.bms.items()}


def _since(P, mark):
    """Vertices created after mark (from _mark), across all materials."""
    return [v for m, bm in P.bms.items() for v in list(bm.verts)[mark.get(m, 0):]]


def impasto(P):
    """Painterly relief on the golden walk face. Brush daubs stand at most 0.04 m above z 0, fallen leaves at most
    0.045 m, and the rim clumps (up to 0.45 m) sit within 0.8 m of the outline. Asserts check these rules."""
    rng = P.rng
    poly, pts, nrm = walk_edge()

    def flow(x, y):  # loose swirling field: brush directions follow a few curved lines
        return 0.9 * math.sin(0.35 * x + 0.6) + 0.7 * math.cos(0.28 * y + 1.1) + 0.4 * math.sin(0.2 * (x + y))

    def pick_tone():  # lighter and cooler than the gold so the strokes read against it; a few leaf/umber
        r = rng.random()  # foliage over gold: 35% light leaf, 25% leaf, 15% blue, 15% cream, 10% umber
        if r < 0.35:
            return "p_leaf_light"
        if r < 0.60:
            return "p_leaf"
        if r < 0.75:
            return "p_blue"
        if r < 0.90:
            return "p_plaster"
        return "p_bark"

    # brush daubs: broad sweeping strokes, 1.0-3.0 m long, 0.3-0.8 m wide, 0.04 thick, centred 0.005-0.013 above z 0
    # so the crown of each stroke stands ~0.025-0.038 proud of the gold; jit 0.005 keeps the top under 0.04
    m = _mark(P)
    shapes = []  # (cx, cy, cos a, sin a, L, W) for the coverage report
    placed, tries = 0, 0
    while placed < 480:
        tries += 1
        if tries > 40000:
            raise SystemExit("crown: could not place brush daubs inside the outline")
        cx, cy = rng.uniform(-6, 6), rng.uniform(-8, 8)
        L, W = rng.uniform(1.0, 3.0), rng.uniform(0.3, 0.8)
        a = flow(cx, cy) + rng.uniform(-0.15, 0.15)
        ca, sa = math.cos(a), math.sin(a)
        ring = [(cx + ca * (L / 2) * math.cos(t) - sa * (W / 2) * math.sin(t),
                 cy + sa * (L / 2) * math.cos(t) + ca * (W / 2) * math.sin(t)) for t in [TAU * k / 8 for k in range(8)]]
        if sd(poly, cx, cy) > 0.1 and all(sd(poly, x, y) > 0.1 for x, y in ring):
            N.daub(P, pick_tone(), Vector((cx, cy, 0.005 + rng.uniform(0.0, 0.008))), Vector((ca, sa, 0.0)), Z,
                   L, W, 0.04, detail=1, jit=0.005)
            shapes.append((cx, cy, ca, sa, L, W))
            placed += 1
    daub_v = _since(P, m)

    # fallen leaves: flat, 0.025 thick, 0.3-0.5 m long, centred z 0.02 so they sit on top of the brush daubs
    m = _mark(P)
    placed, tries = 0, 0
    while placed < 35:
        tries += 1
        if tries > 20000:
            raise SystemExit("crown: could not place fallen leaves inside the outline")
        cx, cy = rng.uniform(-6, 6), rng.uniform(-8, 8)
        if sd(poly, cx, cy) < 0.3:
            continue
        a = rng.uniform(0, TAU)
        mat = "p_yellow" if rng.random() < 0.2 else ("p_leaf_light" if rng.random() < 0.5 else "p_leaf")
        N.daub(P, mat, Vector((cx, cy, 0.02)), Vector((math.cos(a), math.sin(a), 0.0)), Z,
               rng.uniform(0.3, 0.5), rng.uniform(0.16, 0.26), 0.025, detail=0, jit=0.005)
        placed += 1
    leaf_v = _since(P, m)

    # rim clumps: 27 irregular spots, 0.3-0.4 m inside the outline, a few leaf daubs each (crown's leaf helper)
    m = _mark(P)
    n = len(pts)
    for k in range(27):
        i = int((k + rng.uniform(0.1, 0.9)) * n / 27) % n
        ex, ey = poly[i]
        inset = rng.uniform(0.3, 0.4)
        cx, cy = ex - nrm[i].x * inset, ey - nrm[i].y * inset
        for _ in range(rng.randint(3, 4)):
            a = rng.uniform(0, TAU)
            c = Vector((cx + rng.uniform(-0.05, 0.05), cy + rng.uniform(-0.05, 0.05), rng.uniform(0.0, 0.08)))
            N.daub(P, canopy_mat(rng), c, Vector((math.cos(a), math.sin(a), 0.0)),
                   Vector((rng.gauss(0, 0.3), rng.gauss(0, 0.3), 1.0)), rng.uniform(0.4, 0.5),
                   rng.uniform(0.28, 0.32), 0.26, detail=1, jit=0.02)
    clump_v = _since(P, m)

    # checks: flat pieces stay low and inside the walk face; clumps stay under 0.45 and within 0.8 m of the rim
    for v in daub_v:
        if v.co.z > 0.04 or sd(poly, v.co.x, v.co.y) < -0.05:
            raise SystemExit("crown: brush daub too proud or outside the walk face")
    for v in leaf_v:
        if v.co.z > 0.045 or sd(poly, v.co.x, v.co.y) < -0.05:  # raised from 0.03: leaves must clear the daubs
            raise SystemExit("crown: fallen leaf too proud or outside the walk face")
    for v in clump_v:
        if v.co.z > 0.45:
            raise SystemExit("crown: rim clump taller than 0.45 m")
        if v.co.z > 0.04 and abs(sd(poly, v.co.x, v.co.y)) > 0.8:
            raise SystemExit("crown: rim clump more than 0.8 m from the rim")
    def covered(x, y):
        return any(((x - cx) * ca + (y - cy) * sa) ** 2 / (L / 2) ** 2
                   + (-(x - cx) * sa + (y - cy) * ca) ** 2 / (W / 2) ** 2 <= 1
                   for cx, cy, ca, sa, L, W in shapes)

    grid = [(-6 + 0.25 * i, -8 + 0.25 * j) for i in range(49) for j in range(65)]
    grid = [p for p in grid if sd(poly, *p) > 0]
    cover = sum(covered(*p) for p in grid) / len(grid)
    print("IMPASTO brush=%d fallen=35 clumps=27 coverage=%.0f%% (checks passed)" % (len(shapes), 100 * cover))


def crown(P):
    golden_top(P)
    leaf_ring(P)
    rim_branches(P)
    skirt(P)
    interior_canopy(P)
    boughs_and_trunk(P)
    impasto(P)  # last, so the random stream of the existing parts is unchanged


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


# --- view scaffold (Godot world coordinates) ----------------------------------------------------

VIEW_LEGS = [(-18.7, -305.4), (-18.7, -314.6), (-14.6, -305.4), (-14.6, -314.6)]  # west pair, then east pair
VIEW_CENTRE = (-16.3, -310.0)
VIEW_WALLS = [((-18.7, -305.4), (-14.6, -305.4)),  # north
              ((-18.7, -314.6), (-14.6, -314.6)),  # south
              ((-18.7, -305.4), (-18.7, -314.6))]  # west (east side open)
VIEW_RAILS = [3.0, 5.2]
VIEW_DECK_UNDER = 5.6  # underside of the View deck (box spans x -19..-13.2, z -315..-305)


def view_scaffold(P):
    """Stretcher-style legs holding up the View deck. Built in Godot coordinates (identity placement)."""
    rng = P.rng
    m0 = _mark(P)
    for x, z in VIEW_LEGS:  # 0.28 m legs, slightly out of true, splayed dark feet on the ground
        lean = (rng.uniform(-0.002, 0.002), rng.uniform(-0.002, 0.002))
        gbox(P, "p_wood", x - 0.14, x + 0.14, 0.0, VIEW_DECK_UNDER, z - 0.14, z + 0.14, n=4, amp=0.012, lean=lean)
        cx, cz = VIEW_CENTRE
        m = math.hypot(x - cx, z - cz)
        # feet splay away from the frame centre; the east pair splays in z only, so the east clearance
        # rule (x > -14.35 stays free below y 4.5) holds
        fx = x + (x - cx) / m * 0.12 if x < cx else x
        fz = z + (z - cz) / m * 0.12
        gbox(P, "p_wood_dark", fx - 0.22, fx + 0.22, 0.0, 0.16, fz - 0.22, fz + 0.22, n=1, amp=0.01)
    legs_v = _since(P, m0)
    for a, b in VIEW_WALLS:
        along_x = a[1] == b[1]
        for y0 in (VIEW_RAILS if along_x else VIEW_RAILS[-1:]):  # west face: top rail only
            wall_rail(P, a, b, y0)
        if along_x:  # X cross-braces fill the panel between the two rails
            wall_brace(P, a, b, VIEW_RAILS[0], VIEW_RAILS[1])
    for x, z in VIEW_LEGS:  # wedge keys where the rails meet the legs
        for y0 in VIEW_RAILS:
            gbox(P, "p_wood_dark", x - 0.22, x + 0.22, y0 - 0.04, y0 + 0.24, z - 0.22, z + 0.22, n=1, amp=0.006)
    for z in (-305.4, -314.6):  # knee braces from the east legs up to the deck underside
        bar(P, "p_wood_dark", g(-14.6, 4.6, z), g(-13.5, 5.55, z), 0.16, Vector((0, 1, 0)))
    assert_view_clear(P, legs_v)


def assert_view_clear(P, legs_v):
    """Keep-clear rules: nothing but legs and feet below y 2.9; no triangle east of x -14.35 dips below y 4.5."""
    legs = set(legs_v)
    tris = 0
    for bm in P.bms.values():
        for v in bm.verts:
            if v not in legs and v.co.z < 2.9:
                raise SystemExit("view_scaffold: a member other than a leg or foot sits below y 2.9")
        for f in bm.faces:
            tris += len(f.verts) - 2
            if min(v.co.x for v in f.verts) > -14.35 and min(v.co.z for v in f.verts) < 4.5:
                raise SystemExit("view_scaffold: a member enters the east clearance below y 4.5")
    if tris >= 4000:
        raise SystemExit("view_scaffold: %d tris over the 4000 budget" % tris)
    print("VIEW_SCAFFOLD tris=%d" % tris)


# --- dispatch -----------------------------------------------------------------------------------

MODELS = {
    "crown": ("crown", 901, crown),
    "lookout_scaffold": ("lookout_scaffold", 907, scaffold),
    "view_scaffold": ("view_scaffold", 911, view_scaffold),
}


def build(args):
    key = args[0] if args else ""
    if key not in MODELS:
        raise SystemExit("unknown crown model: " + key)
    name, seed, fn = MODELS[key]
    P = N.Parts(seed)
    fn(P)
    L.finish(P, name)
