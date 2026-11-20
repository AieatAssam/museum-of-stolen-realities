"""THE THIEF, ACQUIRED: a life-size plaster-and-velvet cast of a young woman caught mid-theft, standing on
z=0 (the pedestal in pedestal.py is applied in Godot). Facing -Y. Figure's right = -X.

The figure is carried by cloth: a hidden collision body (about 7.5 heads, narrow shoulders, a real neck) wears
garments simulated with Blender's cloth solver (drape.py) and then applied, smoothed and given thickness:
  - a belted greatcoat to the calves, with tall riding boots below the hem,
  - a shoulder cape (capelet) over the coat and the tops of the sleeves,
  - a deep hood whose shadow holds a smooth lacquered mask with a brass visor slit,
  - loose sleeves pinned at shoulder and cuff, sagging over the arms.
The two gloved hands (a closed fist at the chest, an open hand reaching forward and down) are modelled.

Built in the live Blender session through Blender MCP (tools/blender/live.py runs this file and exports).

Materials (names are the contract): thief_cloth (coat, cape, hood, sleeves, trousers), thief_leather (belt, gloves,
cuffs, boots), brass (buckle, visor rim, clasp), thief_mask (the mask).

Objects (origin = pivot):
  thief       body (static); origin at the floor
  thief_head  hood and mask; origin at the neck pivot (0, 0, 1.45)
  thief_arm   right reaching arm: sleeve, cuff and gloved hand; origin at the right shoulder
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drape  # noqa: E402
import kit  # noqa: E402
import orn  # noqa: E402

MAT_CLOTH, MAT_LEATHER, MAT_MASK = "thief_cloth", "thief_leather", "thief_mask"
NECK = Vector((0.0, 0.0, 1.45))
HEAD_C = Vector((0.0, 0.006, 1.552))
HEAD_R = (0.071, 0.087, 0.106)
L_SH = Vector((0.165, 0.0, 1.37))
R_SH = Vector((-0.165, 0.0, 1.37))
# arm centre lines, shoulder to wrist (the wrists are where the modelled hands begin)
# (index 2 is the elbow: both arms break there, out from the body, the forearms angled in and forward)
ARM_L = [L_SH, Vector((0.205, -0.005, 1.25)), Vector((0.235, -0.04, 1.125)), Vector((0.185, -0.125, 1.17)),
         Vector((0.12, -0.16, 1.22))]
ARM_R = [R_SH, Vector((-0.205, -0.005, 1.25)), Vector((-0.235, -0.045, 1.125)), Vector((-0.215, -0.20, 1.075)),
         Vector((-0.19, -0.34, 1.04))]
WAIST = 1.04


def V(*a):
    return Vector(a)


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def gauss(v, c, s):
    return math.exp(-((v - c) / s) ** 2)


def sp(c, e):
    """Signed power: keeps the sign of c, raises |c| to e (superellipse sections, sharp folds)."""
    return math.copysign(abs(c) ** e, c)


def bake(ob, M):
    ob.data.transform(M)
    return ob


def frame(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
    return Matrix.Translation(Vector(origin)) @ q


def pivot(ob, p):
    p = Vector(p)
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p
    return ob


def _select_only(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)


def subsurf(ob, levels=1):
    _select_only(ob)
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    ob.select_set(False)
    return ob


def solidify(ob, thickness):
    _select_only(ob)
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thickness
    m.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    ob.select_set(False)
    return ob


def sculpt(ob, fn):
    for v in ob.data.vertices:
        d = fn(v.co.x, v.co.y, v.co.z)
        v.co = (v.co.x + d[0], v.co.y + d[1], v.co.z + d[2])


# ---------------------------------------------------------------- sweeps

def spline(keys, per=3):
    """Catmull-Rom through keys [(pos, rx, ry)]. Returns (points, rx list, ry list)."""
    P = [Vector(k[0]) for k in keys]
    RX = [k[1] for k in keys]
    RY = [k[2] for k in keys]
    E = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    pts, rx, ry = [], [], []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = E[i], E[i + 1], E[i + 2], E[i + 3]
        for j in range(per):
            t = j / per
            pts.append(0.5 * ((2 * p1) + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
            rx.append(RX[i] + (RX[i + 1] - RX[i]) * t)
            ry.append(RY[i] + (RY[i + 1] - RY[i]) * t)
    pts.append(P[-1])
    rx.append(RX[-1])
    ry.append(RY[-1])
    return pts, rx, ry


def loft(name, pts, rx, ry, mat, sides=14, sup=2.5, hint=(0, 0, 1), warp=None, smooth_angle=60.0):
    """Superellipse section swept along pts with per-ring radii rx (side) and ry (up).
    sup = superellipse exponent (2 = round, 2.5-3 = squarer, muscle and cloth). warp(t, a) -> scale."""
    H = Vector(hint).normalized()
    n = len(pts)
    bm = bmesh.new()
    rings = []
    for i in range(n):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        s = d.cross(H)
        if s.length < 1e-4:
            s = d.cross(Vector((1, 0, 0)))
        s.normalize()
        u = s.cross(d).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            x = sp(math.cos(a), 2 / sup) * rx[i]
            y = sp(math.sin(a), 2 / sup) * ry[i]
            if warp:
                w = warp(i / (n - 1), a)
                x *= w
                y *= w
            ring.append(bm.verts.new(pts[i] + s * x + u * y))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, smooth_angle)


def limb(name, keys, mat, per=3, sides=14, sup=2.5, hint=(0, 0, 1), warp=None):
    """A spline-swept, subdivided limb or garment from keys [(pos, rx, ry)]."""
    pts, rx, ry = spline(keys, per)
    return subsurf(loft(name, pts, rx, ry, mat, sides, sup, hint, warp), 1)


def loop_tube(name, pts, rad, mat, sides=10):
    """Closed tube around a loop of points (belt)."""
    n = len(pts)
    bm = bmesh.new()
    rings = []
    for i in range(n):
        d = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        s = d.cross(Vector((0, 0, 1))).normalized()
        u = s.cross(d).normalized()
        rings.append([bm.verts.new(pts[i] + (s * math.cos(a) + u * math.sin(a)) * rad)
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for i in range(n):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[(i + 1) % n][k], rings[(i + 1) % n][(k + 1) % sides],
                          rings[i][(k + 1) % sides]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return subsurf(kit._obj(name, bm, mat, 70.0), 1)


# ---------------------------------------------------------------- skinned body



skin_graph = drape.skin_graph


def ellipsoid_mesh(name, centre, radii, mat, u=32, v=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(radii), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(centre), verts=bm.verts)
    return kit._obj(name, bm, mat, 80.0)



# ---------------------------------------------------------------- the hidden body

def torso_depth(co):
    """The trunk is shallower front-to-back than it is wide; the limbs stay round."""
    trunk = gauss(co.x, 0.0, 0.15) * smooth((co.z - 0.80) / 0.12) * smooth((1.40 - co.z) / 0.06)
    return 1.0 - 0.3 * trunk


def body():
    """Collision body: trunk, neck, shoulder balls, hips and legs (the right knee bent forward). The legs are
    exported as the trousers that show between the open coat panels."""
    N = [(V(0, 0.0, 0.96), 0.16), (V(0, 0.0, WAIST), 0.135), (V(0, -0.005, 1.19), 0.15), (V(0, 0.0, 1.30), 0.14),
         (V(0, 0.0, 1.41), 0.05), (V(0, 0.005, 1.47), 0.045),
         (L_SH, 0.03), (R_SH, 0.03),  # small: the shoulder balls must stay inside the coat
         (V(0.09, 0.0, 0.88), 0.10), (V(0.10, 0.0, 0.70), 0.075), (V(0.10, 0.0, 0.50), 0.056), (V(0.10, 0.0, 0.30), 0.05),
         (V(-0.09, -0.01, 0.88), 0.10), (V(-0.10, -0.035, 0.70), 0.075), (V(-0.10, -0.06, 0.49), 0.056),
         (V(-0.10, -0.03, 0.30), 0.05)]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (3, 6), (3, 7), (0, 8), (8, 9), (9, 10), (10, 11),
         (0, 12), (12, 13), (13, 14), (14, 15)]
    return skin_graph("trousers", N, E, MAT_CLOTH, flatten=torso_depth)


def arm_collider(name, path, r0=0.05, r1=0.035):
    keys = [(p, r0 + (r1 - r0) * i / (len(path) - 1), r0 + (r1 - r0) * i / (len(path) - 1)) for i, p in enumerate(path)]
    return limb(name, keys, MAT_CLOTH, per=3, sides=12, sup=2.0)


# ---------------------------------------------------------------- garments (rest shapes, then simulated)

def _lerp_table(T, z):
    for (z0, *a), (z1, *b) in zip(T, T[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return [x + (y - x) * t for x, y in zip(a, b)]
    return list(T[0][1:]) if z > T[0][0] else list(T[-1][1:])


# (z, half-width, half-depth): fitted from the collar over narrow shoulders, in at the belt, flaring to the calves
COAT_T = [(1.47, 0.058, 0.052), (1.43, 0.10, 0.075), (1.39, 0.18, 0.105), (1.34, 0.198, 0.118),
          (1.24, 0.185, 0.125), (1.13, 0.162, 0.118), (WAIST, 0.152, 0.11), (0.94, 0.21, 0.16),
          (0.72, 0.26, 0.21), (0.30, 0.30, 0.255)]


def coat():
    rnd = random.Random(7)
    NS = 112
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    Z = [1.47 - k * 0.0165 for k in range(int((1.47 - 0.31) / 0.0165) + 1)]
    rings = []
    for z in Z:
        rx, ry = _lerp_table(COAT_T, z)
        free = smooth((WAIST - 0.03 - z) / 0.3)  # irregularity only where the skirt hangs free
        ring = []
        for k in range(NS):
            u = 2 * math.pi * k / NS
            back = 1.0 + 0.10 * free * max(0.0, math.sin(u))  # more cloth at the back: a fuller fall
            n = 1.0 + free * (0.05 * math.sin(3 * u + ph[0]) + 0.035 * math.sin(5 * u + ph[1]) +
                              0.02 * math.sin(7 * u + ph[2]))
            ring.append((rx * n * math.cos(u), ry * n * back * math.sin(u), z))
        rings.append(ring)
    return drape.grid_tube("coat", rings)


def coat_pin(co):
    if co.z > 1.31:
        return 1.0
    if abs(co.z - WAIST) < 0.02:
        return 1.0
    return 0.0


# an Inverness cape: a stand collar under the hood's cowl, sloping off the shoulders and falling over the sleeves
# to the elbows; short at the front (clear of the raised fist), longest at the back
CAPE_COLLAR = [(1.47, 0.085, 0.075), (1.43, 0.12, 0.095), (1.40, 0.15, 0.11)]


def cape_hem(u):
    """Longest at the back, to the elbows at the sides, rising across the front clear of the raised fist."""
    s = math.sin(u)
    return 1.10 - 0.03 * max(0.0, s) + 0.22 * max(0.0, -s) ** 0.8 + 0.008 * math.sin(5 * u + 0.7)


def cape(under):
    return drape.envelope("cape", under, CAPE_COLLAR, cape_hem)


def hood():
    """Rest shape: the head ellipsoid pushed out (deeper over the crown, gathered to a point at the back), open
    at the face, running down into a wide cowl round the neck that lies over the cape."""
    NU = 96
    rows = []
    for lat in [88 - 4 * i for i in range(29)]:  # 88 .. -24 deg
        a = math.radians(lat)
        row = []
        for k in range(NU):
            u = 2 * math.pi * k / NU
            d = Vector((math.cos(a) * math.cos(u), math.cos(a) * math.sin(u), math.sin(a)))
            p = Vector((d.x * HEAD_R[0], d.y * HEAD_R[1], d.z * HEAD_R[2]))
            # the back of the hood hangs as a soft point behind the nape, not up over the crown
            back = max(0.0, math.sin(u)) ** 2 * smooth((0.9 - a) / 0.9)
            off = 0.045 + 0.015 * max(0.0, math.sin(a))
            fwd = 0.075 * max(0.0, -math.sin(u)) ** 2 * max(0.0, math.cos(a)) * (0.6 + 0.4 * max(0.0, math.sin(a)))  # brim ahead of the mask
            row.append(tuple(HEAD_C + p + d * off + Vector((0, 0.05 * back - fwd, -0.03 * back))))
        rows.append(row)
    last = [Vector(p) for p in rows[-1]]  # cowl: from the last head row down round the cape's collar
    for j, (zt, r) in enumerate([(1.465, 0.115), (1.45, 0.135), (1.432, 0.155)]):  # round the cape's collar
        t = (j + 1) / 3.0
        rows.append([tuple(last[k].lerp(Vector((r * math.cos(2 * math.pi * k / NU),
                                                 r * 0.85 * math.sin(2 * math.pi * k / NU) + 0.01, zt)), t))
                     for k in range(NU)])
    ob = drape.grid_tube("hood", rows)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median() - HEAD_C
        ang = abs(math.degrees(math.atan2(c.x, -c.y)))
        lat = math.degrees(math.atan2(c.z, Vector((c.x, c.y)).length))
        if c.y < 0 and (ang / 34) ** 2 + ((lat + 6) / 42) ** 2 < 1:  # an oval face opening
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    for v in bm.verts:  # pull the stair-stepped opening onto the oval, over the hood's surface
        c = v.co - HEAD_C
        if c.y >= 0 or not v.is_boundary:
            continue
        rho = c.length
        ang = math.degrees(math.atan2(c.x, -c.y))
        lat = math.degrees(math.atan2(c.z, Vector((c.x, c.y)).length))
        e = (ang / 34) ** 2 + ((lat + 6) / 42) ** 2
        if e > 3.0:
            continue
        k = 1 / math.sqrt(e)
        a, la = math.radians(ang * k), math.radians(-6 + (lat + 6) * k)
        v.co = HEAD_C + Vector((math.cos(la) * math.sin(a), -math.cos(la) * math.cos(a), math.sin(la))) * rho
    top =[e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > HEAD_C.z + 0.12]
    bmesh.ops.triangle_fill(bm, edges=top, use_beauty=True)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def hood_pin(co):
    """The cowl's lowest ring and the crown are held: the sides and back fall into their own folds."""
    return 1.0 if co.z < 1.437 or co.z > HEAD_C.z + 0.07 else 0.0


def sleeve(name, path, r0=0.074, r1=0.058, per=8, seed=0):
    """A sculpted greatcoat sleeve along the arm path (path[2] = elbow): compression folds stacked on the inside
    of the elbow, the outer elbow drawn tight, drag folds spiralling down the forearm, the cloth sagging under
    the forearm and gathering at the cuff, which overhangs the glove."""
    path = [path[0].lerp(path[1], 0.35)] + path[1:]  # the open top sits under the cape
    pts, _, _ = spline([(p, 0, 0) for p in path], per)
    pts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.025)
    ie = 2 * per
    E = pts[ie]
    b = ((pts[ie - per // 2] + pts[ie + per // 2]) * 0.5 - E).normalized()  # into the bend
    L = [0.0]
    for p, q in zip(pts, pts[1:]):
        L.append(L[-1] + (q - p).length)
    Lt = L[-1]
    Z = Vector((0, 0, 1))
    n = len(pts)
    d = (pts[1] - pts[0]).normalized()
    s = d.cross(Z).normalized()
    NS = 48
    ph = random.Random(seed).uniform(0, 6.28)
    rings = []
    for i in range(n):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        s = (s - d * s.dot(d)).normalized()  # parallel transport: no twist
        u = d.cross(s).normalized()
        de = L[i] - L[ie]
        tf = min(max(de / (Lt - L[ie]), 0.0), 1.0)
        r = r0 + (r1 - r0) * L[i] / Lt
        c = pts[i] - Z * 0.012 * math.sin(math.pi * tf)
        ring = []
        for k in range(NS):
            a = 2 * math.pi * k / NS
            rd = s * math.cos(a) + u * math.sin(a)
            inner = max(0.0, rd.dot(b)) ** 2
            outer = max(0.0, -rd.dot(b))
            fold = inner * math.exp(-(de / 0.07) ** 2) * (0.5 + 0.5 * math.sin(2 * math.pi * de / 0.03)) ** 2
            down = max(0.0, -rd.z) ** 2 * math.sin(math.pi * tf)
            drag = 0.045 * math.sin(3 * a + 2 * math.pi * L[i] / 0.11 + ph) * smooth((L[i] - 0.05) / 0.05)
            cuff = 0.07 * math.sin(9 * a + ph) * gauss(Lt - L[i], 0.03, 0.025)
            f = 1 + 0.24 * fold + 0.28 * down + drag + cuff - 0.07 * outer * math.exp(-(de / 0.05) ** 2)
            ring.append(tuple(c + rd * r * f))
        rings.append(ring)
    # the cuff turns back on itself: a rolled edge, then a band lying over the sleeve end
    last = [Vector(p) for p in rings[-1]]
    cen = sum(last, Vector()) / len(last)
    for out, back in ((0.006, 0.004), (0.011, 0.016), (0.012, 0.045)):
        rings.append([tuple(p + (p - cen).normalized() * out - d * back) for p in last])
    return drape.grid_tube(name, rings), (pts[0], pts[-1])


def turn_edge(ob, pred, steps):
    """Roll the sheet's boundary where pred holds: extrude it in steps, each moving the new edge by
    step(co) (out and back over the cloth), so the edge has a soft turned thickness instead of a cut."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    edges = [e for e in bm.edges if e.is_boundary and all(pred(v.co) for v in e.verts)]
    for step in steps:
        r = bmesh.ops.extrude_edge_only(bm, edges=edges)
        nv = {g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)}
        for v in nv:
            v.co += step(v.co)
        edges = [g for g in r["geom"] if isinstance(g, bmesh.types.BMEdge) and all(v in nv for v in g.verts)]
    bm.to_mesh(ob.data)
    bm.free()


def coat_shape(c):
    """Folds breaking below the belt, an uneven hem, and the left front panel lapped over the right."""
    rnd = random.Random(11)
    ph = [rnd.uniform(0, 6.28) for _ in range(5)]
    for v in c.data.vertices:
        x, y, z = v.co
        u = math.atan2(y, x)
        h = Vector((x, y, 0))
        nh = h.normalized() if h.length > 1e-6 else Vector((1, 0, 0))
        free = smooth((WAIST - 0.04 - z) / 0.35)
        fold = 0.017 * free * (0.55 * math.sin(7 * u + ph[0]) + 0.35 * math.sin(11 * u + ph[1]) +
                               0.25 * math.sin(4 * u + ph[2]))
        lap = 0.006 * smooth((x - LAP_X) / 0.012) * smooth((-y - 0.05) / 0.03) if y < 0 else 0.0
        dz = (0.03 * math.sin(2 * u + ph[3]) + 0.014 * math.sin(5 * u + ph[4])) * smooth((0.55 - z) / 0.25)
        v.co = (x + nh.x * (fold + lap), y + nh.y * (fold + lap), z + dz)


LAP_X = -0.035  # the edge of the overlapping front panel


def front_hits(c, x, zs):
    """Where the coat's front surface crosses the vertical line at x, at heights zs."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(c.data)
    tree = BVHTree.FromBMesh(bm)
    out = []
    for z in zs:
        hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        if hit[0] is not None:
            out.append(hit[0])
    bm.free()
    return out


def coat_front(c):
    """The placket seam down the overlap and brass buttons above and below the belt."""
    zs = [1.44 - 0.02 * k for k in range(60)]
    seam = [p + Vector((0, -0.004, 0)) for p in front_hits(c, LAP_X + 0.002, zs)]
    parts = [orn.taper("seam", seam, [0.0045] * len(seam), 8, MAT_CLOTH, 0.6)]
    for p in front_hits(c, LAP_X + 0.03, [1.37, 1.28, 1.19, 1.11, 0.92, 0.80]):
        btn = kit.lathe("button", [(0.0, 0.0), (0.012, 0.0), (0.013, 0.003), (0.009, 0.007), (0.0, 0.008)], 12,
                        mat="brass")
        parts.append(bake(btn, frame(p + Vector((0, -0.004, 0)), (0, -1, 0))))
    return parts


def trouser_leg(s):
    """Trousers below the coat with a break where the hem rests on the boot: higher at the instep, lower at the
    heel. s = -1 right (knee bent forward), +1 left."""
    x = 0.10 * s
    ky = -1.0 if s < 0 else 0.0
    ph = random.Random(int(5 + s)).uniform(0, 6.28)
    NS, NR = 36, 26

    def hem(a):
        return 0.075 + 0.05 * max(0.0, -math.sin(a))
    rings = []
    for j in range(NR + 1):
        ring = []
        for k in range(NS):
            a = 2 * math.pi * k / NS
            hz = hem(a)
            z = 0.47 + (hz - 0.47) * j / NR
            zz = z - hz
            front = max(0.0, -math.sin(a))
            cy = ky * (0.06 * smooth((z - 0.12) / 0.37))
            r = 0.064 + 0.007 * smooth((0.25 - z) / 0.1)
            r *= 1 + front * (0.15 * gauss(zz, 0.045, 0.02) - 0.05 * gauss(zz, 0.085, 0.015))
            r *= 1 + 0.05 * math.sin(5 * a + ph) * smooth((0.24 - z) / 0.08)
            ring.append((x + r * math.cos(a), cy + r * math.sin(a), z))
        rings.append(ring)
    return drape.grid_tube("trouser", rings)


def finish_cloth(ob, thick, mat, levels=1):
    ob.data.materials.clear()
    ob.data.materials.append(kit.material(mat))
    solidify(ob, thick)
    if levels:
        subsurf(ob, levels)
    for f in ob.data.polygons:
        f.use_smooth = True
    return ob


# ---------------------------------------------------------------- mask

def mask():
    """A smooth lacquered mask over the face (only a soft brow and nose ridge) with a brass-rimmed visor slit
    across the eyes; the back of the head is the same dark cap, hidden by the hood."""
    ob = ellipsoid_mesh("mask", HEAD_C, HEAD_R, MAT_MASK, 40, 20)

    def shape(x, y, z):
        f = max(0.0, -(y - HEAD_C.y) / HEAD_R[1])  # 1 at the face, 0 at the sides
        zz = (z - HEAD_C.z) / HEAD_R[2]
        brow = 0.006 * gauss(zz, 0.18, 0.08) * f
        nose = 0.012 * gauss(x, 0.0, 0.012) * gauss(zz, -0.05, 0.22) * f ** 3
        jaw = -0.04 * smooth((-0.4 - zz) / 0.4)  # the jaw narrows
        return (x * jaw, -(brow + nose), 0.0)
    sculpt(ob, shape)
    subsurf(ob, 1)
    parts = [ob]
    ez = HEAD_C.z + 0.012
    pts = []
    for i in range(25):
        u = math.radians(-160 + 140 * i / 24)
        pts.append(Vector((math.cos(u) * (HEAD_R[0] + 0.004), math.sin(u) * (HEAD_R[1] + 0.004) + HEAD_C.y, ez)))
    for dz in (-0.011, 0.011):
        parts.append(orn.taper("visor_rim", [p + Vector((0, 0, dz)) for p in pts], [0.0035] * len(pts), 8, "brass"))
    return kit.join("mask", parts)


# ---------------------------------------------------------------- hands, cuffs, boots

def hand_at(s, W, Yh, T, pose):
    """kit.hand placed at wrist W: fingers along Yh, thumb toward T (both made perpendicular to each other).
    The basis is chosen so the hand's thumb side (s*X) lies along T and the back of the hand faces away from it."""
    Yh = Yh.normalized()
    T = (T - Yh * T.dot(Yh)).normalized()
    Zh = (-s * Yh.cross(T)).normalized()
    Xh = Yh.cross(Zh)
    M = Matrix.Translation(W) @ Matrix((Xh, Yh, Zh)).transposed().to_4x4()
    return bake(kit.hand(s, pose, 1.0, "thief_hand", mat=MAT_LEATHER), M)


def left_hand():
    Wr = ARM_L[-1]
    d = (Wr - ARM_L[-2]).normalized()
    parts = [subsurf(loft("cuff_L", [Wr - d * 0.035, Wr - d * 0.012, Wr + d * 0.006], [0.036, 0.04, 0.037],
                          [0.036, 0.04, 0.037], MAT_LEATHER, sides=16, sup=2.2), 1)]
    # closed fist held at the chest: fingers continue the forearm, thumb up and across the front
    parts.append(hand_at(1, Wr, d, V(0.3, -0.4, 1.0), "grip"))
    return parts


def right_hand():
    W = ARM_R[-1]
    d_arm = (W - ARM_R[-2]).normalized()
    parts = [subsurf(loft("cuff_R", [W - d_arm * 0.045, W - d_arm * 0.02, W, W + d_arm * 0.012],
                          [0.036, 0.039, 0.041, 0.038], [0.036, 0.039, 0.041, 0.038],
                          MAT_LEATHER, sides=16, sup=2.2), 1)]
    # open hand reaching forward and down, palm down, thumb toward the body's midline
    d = Vector((0, -0.8, -0.25)).normalized()
    parts.append(hand_at(-1, W, d, V(1, 0, 0.2), "open"))
    return parts


def _sole_bottom(y):
    """Underside of the sole: on the ground at the ball, rising over the waist onto the heel block, the toe
    sprung up a little."""
    return 0.03 * smooth((y + 0.035) / 0.05) + 0.012 * smooth((-0.15 - y) / 0.05)


def _outline(y, w):
    """Half-width of the footprint at y (heel +0.07 .. toe -0.19), scaled by w."""
    pts = [(0.075, 0.0), (0.065, 0.026), (0.04, 0.036), (0.0, 0.035), (-0.06, 0.042), (-0.11, 0.046),
           (-0.15, 0.038), (-0.175, 0.025), (-0.192, 0.0)]
    for (y0, a), (y1, b) in zip(pts, pts[1:]):
        if y1 <= y <= y0:
            return w * (a + (b - a) * (y0 - y) / (y0 - y1))
    return 0.0


def _slab(name, x, y0, y1, zb, zt, w, mat, n=28):
    """A rounded footprint slab between y0 (back) and y1 (front): zb(y)/zt(y) bottom and top, edges eased."""
    bm = bmesh.new()
    ys = [y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(math.pi * i / n)) for i in range(n + 1)]
    outline = [(y, _outline(y, w)) for y in ys]
    loop = [(x + hw, y) for y, hw in outline] + [(x - hw, y) for y, hw in reversed(outline[1:-1])]
    ring_b = [bm.verts.new((px, py, zb(py))) for px, py in loop]
    ring_m = [bm.verts.new((x + (px - x) * 1.04, py, 0.5 * (zb(py) + zt(py)))) for px, py in loop]
    ring_t = [bm.verts.new((px, py, zt(py))) for px, py in loop]
    m = len(loop)
    for r0, r1 in ((ring_b, ring_m), (ring_m, ring_t)):
        for k in range(m):
            bm.faces.new((r0[k], r0[(k + 1) % m], r1[(k + 1) % m], r1[k]))
    bm.faces.new(ring_b[::-1])
    bm.faces.new(ring_t)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 50.0)


def boot(s):
    """s = -1 right, +1 left. An ankle boot: a shaft under the trouser hem, a rounded toe with a little spring,
    the counter round the heel, a welted sole (proud of the upper) arching from the ball onto a stacked heel."""
    x = 0.10 * s

    def top(y):
        return _sole_bottom(y) + 0.013
    foot = []
    for y, rx, ry in ((0.05, 0.040, 0.045), (0.0, 0.043, 0.05), (-0.06, 0.046, 0.042), (-0.11, 0.046, 0.032),
                      (-0.155, 0.038, 0.024), (-0.182, 0.024, 0.016)):
        foot.append((V(x, y, top(y) + ry - 0.003), rx, ry))
    ft = limb("foot", foot, MAT_LEATHER, per=3, sides=18, sup=2.6)
    shaft = [(V(x, 0.03, 0.07), 0.046, 0.05), (V(x, 0.012, 0.14), 0.047, 0.05), (V(x, 0.008, 0.22), 0.052, 0.054)]
    sh = limb("boot", shaft, MAT_LEATHER, per=3, sides=18, sup=2.2)
    sole = _slab("sole", x, 0.072, -0.192, _sole_bottom, top, 1.1, MAT_LEATHER)
    heel = _slab("heel", x, 0.072, -0.005, lambda y: 0.0, lambda y: _sole_bottom(y) + 0.002, 0.98, MAT_LEATHER, 12)
    return [ft, sh, sole, heel]


# ---------------------------------------------------------------- build

def _remove(*obs):
    for o in obs:
        bpy.data.objects.remove(o, do_unlink=True)


def _cull(ob, drop):
    """Delete the faces whose centre satisfies drop(c): cloth that ends up hidden under another garment."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if drop(f.calc_center_median())], context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def _near(*ends, r=0.07):
    return lambda co: 1.0 if any((co - e).length < r for e in ends) else 0.0


def build(args):
    trousers = body()
    head = ellipsoid_mesh("coll_head", HEAD_C, tuple(r + 0.004 for r in HEAD_R), MAT_MASK, 24, 12)
    # 1. greatcoat over the body, then its folds, hem and front overlap
    c = drape.simulate(coat(), [trousers], coat_pin, frames=120, tension=14, bending=3.0)
    coat_shape(c)
    # 2. sculpted sleeves along the bent arms
    sl, ends_l = sleeve("sleeve_L", ARM_L, seed=1)
    sr, ends_r = sleeve("sleeve_R", ARM_R, seed=2)
    # 3. the cape falls over the coat and the sleeve tops to the elbows
    cp = cape([c, sl, sr])
    # 4. hood over the head and the cape
    hd = drape.simulate(hood(), [head, cp], hood_pin, frames=60, tension=25, bending=6.0)
    _remove(head)
    _cull(trousers, lambda co: co.z < 1.15)  # the trunk stays: it fills the coat's armholes
    legs = [trouser_leg(s) for s in (-1, 1)]
    # turned edges on the single sheets before they are given thickness: hems turned up inside, the hood's face
    # edge rolled back over its outside
    Z = Vector((0, 0, 1))

    def hem(cx, cy, a, b):
        def out(co):
            h = Vector((co.x - cx, co.y - cy, 0))
            return h.normalized() if h.length > 1e-6 else Vector((1, 0, 0))
        return [lambda co: out(co) * a - Z * 0.002, lambda co: -out(co) * (a + 0.004) + Z * b]
    front = coat_front(c)
    turn_edge(c, lambda co: co.z < 0.6, hem(0, 0, 0.006, 0.03))
    turn_edge(cp, lambda co: co.z < 1.40, hem(0, 0, 0.005, 0.02))
    for s, lg in zip((-1, 1), legs):
        turn_edge(lg, lambda co: co.z < 0.2, hem(0.10 * s, 0.0, 0.004, 0.02))

    def head_out(co):
        return (co - HEAD_C).normalized()
    turn_edge(hd, lambda co: co.z > 1.45 and co.y < HEAD_C.y + 0.02,
              [lambda co: head_out(co) * 0.006 + Vector((0, 0.003, 0)),
               lambda co: head_out(co) * 0.002 + Vector((0, 0.012, 0))])
    for ob, t, lv in ((c, 0.007, 0), (sl, 0.006, 0), (sr, 0.006, 0), (cp, 0.007, 0), (hd, 0.010, 0)):
        finish_cloth(ob, t, MAT_CLOTH, lv)
    for lg in legs:
        finish_cloth(lg, 0.005, MAT_CLOTH, 0)
    rx, ry = _lerp_table(COAT_T, WAIST)
    belt = [Vector((rx * 1.06 * math.cos(2 * math.pi * k / 64), ry * 1.08 * math.sin(2 * math.pi * k / 64), WAIST))
            for k in range(64)]
    parts = [trousers, c, sl, cp, loop_tube("belt", belt, 0.016, MAT_LEATHER, 10)] + legs + front
    buckle = kit.torus("buckle", 0.026, 0.006, 24, 8, mat="brass")
    parts.append(bake(buckle, frame((0, -ry * 1.08 - 0.012, WAIST), (0, -1, 0))))
    parts.extend(left_hand())
    for s in (-1, 1):
        parts.extend(boot(s))
    kit.join("thief", parts)
    pivot(kit.join("thief_head", [hd, mask()]), NECK)
    pivot(kit.join("thief_arm", [sr] + right_hand()), R_SH)
