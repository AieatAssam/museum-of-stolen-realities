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
ARM_L = [L_SH, Vector((0.19, -0.03, 1.25)), Vector((0.195, -0.09, 1.115)), Vector((0.16, -0.135, 1.165)),
         Vector((0.12, -0.16, 1.22))]
ARM_R = [R_SH, Vector((-0.195, -0.04, 1.25)), Vector((-0.212, -0.13, 1.125)), Vector((-0.208, -0.25, 1.078)),
         Vector((-0.2, -0.36, 1.04))]
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



def fist(C):
    """Closed left fist, about 9 x 8 x 10 cm, centred on C, knuckles forward (-Y): a back-of-hand block with four
    curled fingers (index, middle, ring, little; middle longest, little shortest). The thumb is in left_arm()."""
    parts = [limb("fist_hand", [(C + V(0, 0.030, 0), 0.036, 0.040), (C + V(0, 0.0, 0), 0.044, 0.046),
                                (C + V(0, -0.026, 0), 0.043, 0.044), (C + V(0, -0.040, 0), 0.032, 0.034)],
                  MAT_LEATHER, per=2, sides=14, sup=2.5)]
    # (name, x across the knuckle row, forward reach factor); index on the inner (-X) side, little on the outer
    # each finger is a tight arc (knuckle over the top, down the front, curling back under to the palm); the arc
    # radius scales with the finger's reach. X hint keeps the loft frame stable where the tangent points along Z.
    for name, xo, L in (("index", -0.027, 1.0), ("middle", -0.009, 1.08), ("ring", 0.009, 0.97),
                        ("little", 0.027, 0.85)):
        R, cy, cz = 0.018 * L, -0.024, -0.010
        keys = []
        for th, rad in ((90, 0.0105), (150, 0.0100), (210, 0.0093), (270, 0.0085)):
            t = math.radians(th)
            keys.append((C + V(xo, cy + R * math.cos(t), cz + R * math.sin(t)), rad, rad))
        parts.append(limb("fist_" + name, keys, MAT_LEATHER, per=2, sides=8, sup=2.2, hint=(1, 0, 0)))
    return parts



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


# a stand collar under the hood's cowl, a yoke over the shoulders (held), a skirt falling over the sleeve tops
CAPE_T = [(1.47, 0.085, 0.075), (1.43, 0.12, 0.10), (1.40, 0.17, 0.125), (1.36, 0.215, 0.145), (1.31, 0.25, 0.16),
          (1.24, 0.28, 0.18)]


def cape():
    NS = 112
    rings = []
    for k in range(int((1.47 - 1.24) / 0.012) + 1):
        z = 1.47 - k * 0.012
        rx, ry = _lerp_table(CAPE_T, z)
        rings.append([(rx * math.cos(2 * math.pi * i / NS), ry * math.sin(2 * math.pi * i / NS), z) for i in range(NS)])
    return drape.grid_tube("cape", rings)


def hood():
    """Rest shape: the head ellipsoid pushed out (deeper over the crown, gathered to a point at the back), open
    at the face, running down into a wide cowl round the neck that lies over the cape."""
    NU = 72
    rows = []
    for lat in [88 - 8 * i for i in range(15)]:  # 88 .. -24 deg
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
        if c.y < 0 and ang < 34 and -48 < lat < 36:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    top = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > HEAD_C.z + 0.12]
    bmesh.ops.triangle_fill(bm, edges=top, use_beauty=True)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def hood_pin(co):
    """The cowl's lowest ring and the crown are held: the sides and back fall into their own folds."""
    return 1.0 if co.z < 1.437 or co.z > HEAD_C.z + 0.07 else 0.0


def sleeve(name, path, r=0.062, cuff=0.05):
    path = [path[0].lerp(path[1], 0.05)] + path[1:]  # the open top sits round the shoulder joint, under the cape
    pts, _, _ = spline([(p, r, r) for p in path], per=6)
    NS = 40
    rings = []
    n = len(pts)
    for i in range(n):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        s = d.cross(Vector((0, 0, 1)))
        if s.length < 1e-3:
            s = d.cross(Vector((1, 0, 0)))
        s.normalize()
        up = s.cross(d).normalized()
        t = i / (n - 1)
        rr = r * (1.0 - 0.25 * t) if t < 0.9 else cuff
        rings.append([tuple(pts[i] + (s * math.cos(a) + up * math.sin(a)) * rr)
                      for a in (2 * math.pi * k / NS for k in range(NS))])
    return drape.grid_tube(name, rings), (pts[0], pts[-1])


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

def left_hand():
    Wr = ARM_L[-1]
    d = (Wr - ARM_L[-2]).normalized()
    parts = [subsurf(loft("cuff_L", [Wr - d * 0.035, Wr - d * 0.012, Wr + d * 0.006], [0.04, 0.046, 0.04],
                          [0.04, 0.046, 0.04], MAT_LEATHER, sides=16, sup=2.4), 1)]
    C = V(0.075, -0.18, 1.25)
    parts.extend(fist(C))
    keys = [(C + V(-0.044, -0.016, 0.012), 0.0095, 0.0095), (C + V(-0.034, -0.048, 0.008), 0.0093, 0.0093),
            (C + V(-0.018, -0.060, 0.0), 0.0089, 0.0089), (C + V(-0.005, -0.060, -0.014), 0.0085, 0.0085)]
    parts.append(limb("thumb_L", keys, MAT_LEATHER, per=2, sides=8, sup=2.2))
    return parts


def right_hand():
    W = ARM_R[-1]
    d_arm = (W - ARM_R[-2]).normalized()
    parts = [subsurf(loft("cuff_R", [W - d_arm * 0.045, W - d_arm * 0.02, W, W + d_arm * 0.012],
                          [0.042, 0.048, 0.054, 0.046], [0.042, 0.048, 0.054, 0.046],
                          MAT_LEATHER, sides=16, sup=2.4), 1)]
    d = Vector((0, -0.8, -0.25)).normalized()
    X, Z = V(1, 0, 0), V(0, 0, 1)
    palm_end = W + d * 0.09
    parts.append(subsurf(loft("palm", [W - d * 0.005, W + d * 0.03, W + d * 0.06, palm_end],
                              [0.030, 0.042, 0.044, 0.038], [0.014, 0.020, 0.022, 0.018],
                              MAT_LEATHER, sides=12, sup=2.4), 1))
    for k, (off, fan, reach, curl) in enumerate(((-0.024, -6, 0.80, 1.3), (-0.008, -2, 1.0, 1.1),
                                                 (0.008, 2, 1.08, 0.9), (0.024, 6, 1.0, 0.7))):
        dk = Matrix.Rotation(math.radians(fan), 3, "Z") @ d
        B = palm_end + X * off
        keys = [(B, 0.0115 * 1.1, 0.0115 * 1.1),
                (B + dk * 0.040 * reach - Z * 0.003 * curl, 0.0105, 0.0105),
                (B + dk * 0.070 * reach - Z * 0.014 * curl, 0.0092, 0.0092),
                (B + dk * 0.092 * reach - Z * 0.024 * curl, 0.0075, 0.0075)]
        parts.append(limb("finger_R%d" % k, keys, MAT_LEATHER, per=3, sides=8, sup=2.2))
    keys = [(W + d * 0.02 + X * 0.030 - Z * 0.004, 0.0115, 0.0115),
            (W + d * 0.055 + X * 0.052 - Z * 0.008, 0.0102, 0.0102),
            (W + d * 0.085 + X * 0.068 - Z * 0.014, 0.0090, 0.0090),
            (W + d * 0.11 + X * 0.078 - Z * 0.018, 0.0075, 0.0075)]
    parts.append(limb("thumb_R", keys, MAT_LEATHER, per=3, sides=8, sup=2.2))
    return parts


def boot(s):
    """s = -1 right (knee bent forward), +1 left. Tall riding boot to just under the knee, flat sole and heel."""
    k = -0.05 if s < 0 else 0.0
    x = 0.10 * s
    shaft = [(V(x, 0.85 * k, 0.50), 0.072, 0.074), (V(x, k * 0.8, 0.44), 0.068, 0.07),
             (V(x, 0.4 * k, 0.33), 0.063, 0.065), (V(x, 0.2 * k, 0.20), 0.055, 0.058),
             (V(x, 0.0, 0.11), 0.05, 0.056), (V(x, 0.0, 0.06), 0.05, 0.058)]
    foot = [(V(x, 0.045, 0.058), 0.044, 0.046), (V(x, -0.02, 0.058), 0.047, 0.044),
            (V(x, -0.10, 0.045), 0.046, 0.033), (V(x, -0.165, 0.038), 0.036, 0.026)]
    bt = limb("boot", shaft, MAT_LEATHER, per=3, sides=16, sup=2.2)
    ft = limb("foot", foot, MAT_LEATHER, per=3, sides=16, sup=2.4, hint=(0, 0, 1))
    zmin = min(v.co.z for v in ft.data.vertices) - 0.012
    for o in (bt, ft):
        bake(o, Matrix.Translation((0, 0, -zmin)))
    sole = kit.box("sole", (0.08, 0.235, 0.012), (x, -0.075, 0.006), mat=MAT_LEATHER, bevel=0.004)
    heel = kit.box("heel", (0.06, 0.07, 0.03), (x, 0.0, 0.015), mat=MAT_LEATHER, bevel=0.006)
    return [bt, ft, sole, heel]


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
    arm_l = arm_collider("coll_arm_l", ARM_L)
    arm_r = arm_collider("coll_arm_r", ARM_R)
    head = ellipsoid_mesh("coll_head", HEAD_C, tuple(r + 0.004 for r in HEAD_R), MAT_MASK, 24, 12)
    # 1. greatcoat over the body
    c = drape.simulate(coat(), [trousers], coat_pin, frames=120, tension=14, bending=3.0)
    # 2. loose sleeves over the arms, held at shoulder and cuff
    sl, ends_l = sleeve("sleeve_L", ARM_L)
    sr, ends_r = sleeve("sleeve_R", ARM_R)
    # (the bent left sleeve only sags between its held ends: its rest tube crosses the collider in the bend)
    drape.simulate(sl, [], _near(*ends_l), frames=30, tension=10, bending=0.2, self_collision=False)
    drape.simulate(sr, [arm_r], _near(*ends_r), frames=50, tension=10, bending=0.2,
                   self_collision=False)
    # 3. short cape over the coat, its hem just over the sleeve tops
    cp = drape.simulate(cape(), [trousers, c], lambda co: 1.0 if co.z > 1.375 else 0.0,
                        frames=80, tension=15, bending=0.6)
    # 4. hood over the head and the cape
    hd = drape.simulate(hood(), [head, cp], hood_pin, frames=60, tension=25, bending=2.0)
    _remove(arm_l, arm_r, head)
    # hidden under the cape and coat: the sleeve tops, and the legs and hips (the trunk stays: it fills the
    # coat's armholes)
    for ob in (sl, sr):
        _cull(ob, lambda co: co.z > 1.27)
    _cull(trousers, lambda co: 0.5 < co.z < 1.15)
    for ob, t, lv in ((c, 0.007, 0), (sl, 0.005, 1), (sr, 0.005, 1), (cp, 0.007, 0), (hd, 0.006, 1)):
        finish_cloth(ob, t, MAT_CLOTH, lv)
    rx, ry = _lerp_table(COAT_T, WAIST)
    belt = [Vector((rx * 1.06 * math.cos(2 * math.pi * k / 64), ry * 1.08 * math.sin(2 * math.pi * k / 64), WAIST))
            for k in range(64)]
    parts = [trousers, c, sl, cp, loop_tube("belt", belt, 0.016, MAT_LEATHER, 10)]
    buckle = kit.torus("buckle", 0.026, 0.006, 24, 8, mat="brass")
    parts.append(bake(buckle, frame((0, -ry * 1.08 - 0.012, WAIST), (0, -1, 0))))
    parts.extend(left_hand())
    for s in (-1, 1):
        parts.extend(boot(s))
    kit.join("thief", parts)
    pivot(kit.join("thief_head", [hd, mask()]), NECK)
    pivot(kit.join("thief_arm", [sr] + right_hand()), R_SH)
