"""THE THIEF, ACQUIRED: a life-size (1.69 m) plaster cast of a young woman caught mid-theft, standing on
z=0 (the pedestal in pedestal.py is applied in Godot). Facing -Y. Figure's right = -X.

Weight on the back (left, +X) foot, the right arm reaching forward and down, the left hand closed at
the chest. A long coat open from the belt down (trousers show), lapels and brass buttons, a back vent,
a hem higher at the front, a symmetric rolled collar with a drape down the back, tall boots on flat soles,
domino mask over a sculpted face, hair with a bun.

Built in the live Blender session through Blender MCP (tools/blender/live.py runs this file and exports).
The clothed body is ONE skin-modifier graph (pelvis, spine, neck, shoulders, left arm, hips, legs) under
subdivision, so shoulders flow into the arms and the trousers run unbroken from hip to boot; the reaching
right arm is a second skin graph that shares the shoulder ball. Lapels, buttons and strap are projected
onto that surface. The coat skirt is a draped, solidified sheet from the belt to the hem.

Materials (names are the contract): thief_cloth (coat, trousers, collar, lapels), thief_leather (belt,
pouch, strap, boots, soles, heels, gloves, cuffs), brass (buckle, clasp, buttons, mask rivets), thief_skin (face,
neck, ears, nose, lips), thief_mask (domino mask), thief_hair (hair shell, strands, wisps, bun).

Objects (origin = pivot):
  thief       body (static); origin at the floor
  thief_head  head, domino mask, hair; origin at the neck pivot (0, 0, 1.45)
  thief_arm   right reaching arm incl. sleeve, cuff and gloved hand; origin at the right shoulder (-0.19, 0, 1.36)
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

NECK = Vector((0.0, 0.0, 1.45))
R_SHOULDER = Vector((-0.19, 0.0, 1.36))
L_SHOULDER = Vector((0.19, 0.0, 1.36))
# coat section (z, half-width x, half-depth y): fitted, bust and hip shaped; the top slopes from the
# shoulders (trapezius) into the neck
COAT = [(0.50, 0.215, 0.16), (0.62, 0.20, 0.15), (0.80, 0.195, 0.14), (0.92, 0.19, 0.13),
        (1.04, 0.14, 0.095), (1.14, 0.162, 0.115), (1.22, 0.182, 0.13), (1.30, 0.19, 0.115),
        (1.36, 0.18, 0.10), (1.41, 0.12, 0.078), (1.44, 0.07, 0.06)]
EYE_Z = 0.12  # eye line in head space
MAT_CLOTH, MAT_LEATHER, MAT_SKIN, MAT_MASK = "thief_cloth", "thief_leather", "thief_skin", "thief_mask"
MAT_HAIR = "thief_hair"


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

def skin_graph(name, nodes, edges, mat, root=0, levels=2, flatten=None):
    """Skin-modifier body: nodes [(pos, radius)] joined by edges, hulled by the skin modifier and subdivided,
    so branches (shoulders, hips) blend instead of butting. flatten(co) -> y scale (torso depth)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p, _ in nodes], edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 1.0
    for i, (_, r) in enumerate(nodes):
        sv = me.skin_vertices[0].data[i]
        sv.radius = (r, r) if not isinstance(r, tuple) else r
        sv.use_root = i == root
    ss = ob.modifiers.new("subsurf", "SUBSURF")
    ss.levels = ss.render_levels = levels
    _select_only(ob)
    bpy.ops.object.modifier_apply(modifier=sk.name)
    bpy.ops.object.modifier_apply(modifier=ss.name)
    ob.select_set(False)
    if flatten:
        for v in me.vertices:
            v.co.y *= flatten(v.co)
    ob.data.materials.append(kit.material(mat))
    for f in me.polygons:
        f.use_smooth = True
    return ob


def torso_depth(co):
    """Chest and hips are deeper than wide only a little: flatten the trunk front-to-back, not the limbs."""
    trunk = gauss(co.x, 0.0, 0.16) * smooth((co.z - 0.80) / 0.12) * smooth((1.40 - co.z) / 0.06)
    return 1.0 - 0.27 * trunk


def body():
    """Trunk, neck, shoulders, left arm (sleeve to the wrist), hips and trousered legs in one graph."""
    N = [  # 0 pelvis
        (V(0, 0.0, 0.97), (0.17, 0.17)), (V(0, 0.0, 1.06), (0.152, 0.152)), (V(0, -0.005, 1.20), (0.172, 0.172)),
        (V(0, 0.0, 1.31), (0.16, 0.16)), (V(0, 0.0, 1.40), (0.062, 0.062)), (V(0, 0.005, 1.49), (0.054, 0.054)),
        # 6,7 shoulder balls (right one is shared with the separate right arm)
        (V(0.17, 0.0, 1.35), (0.060, 0.060)), (V(-0.17, 0.0, 1.35), (0.060, 0.060)),
        # 8-11 left arm: upper arm, elbow, forearm, wrist (bent up to the fist at the chest)
        (V(0.20, -0.05, 1.25), (0.050, 0.050)), (V(0.20, -0.10, 1.11), (0.040, 0.040)),
        (V(0.155, -0.14, 1.165), (0.041, 0.041)), (V(0.12, -0.16, 1.215), (0.032, 0.032)),
        # 12-15 left leg (straight, weight-bearing): hip, thigh, knee, into the boot
        (V(0.095, 0.0, 0.88), (0.105, 0.105)), (V(0.10, 0.0, 0.72), (0.082, 0.082)),
        (V(0.10, 0.0, 0.52), (0.060, 0.060)), (V(0.10, 0.0, 0.40), (0.055, 0.055)),
        # 16-19 right leg (knee bent forward)
        (V(-0.095, -0.01, 0.88), (0.105, 0.105)), (V(-0.10, -0.03, 0.72), (0.082, 0.082)),
        (V(-0.10, -0.05, 0.50), (0.060, 0.060)), (V(-0.10, -0.03, 0.40), (0.055, 0.055)),
    ]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (3, 6), (3, 7), (6, 8), (8, 9), (9, 10), (10, 11),
         (0, 12), (12, 13), (13, 14), (14, 15), (0, 16), (16, 17), (17, 18), (18, 19)]
    ob = skin_graph("body", N, E, MAT_CLOTH, flatten=torso_depth)
    # the neck reads as skin: faces above the collar line and inside the neck radius
    ob.data.materials.append(kit.material(MAT_SKIN))
    for f in ob.data.polygons:
        c = f.center
        if c.z > 1.43 and abs(c.x) < 0.075:
            f.material_index = 1
    return ob


# ---------------------------------------------------------------- coat

NS = 96  # coat sides: 14 drape folds => ~7 samples per fold
FOLDS = 14
# coat rows as fixed heights; below the belt (h < 1.0) the hem is raised at the front and dropped at the back
HS = [0.42, 0.50, 0.58, 0.66, 0.74, 0.82, 0.90, 0.96, 1.00, 1.04, 1.08]  # skirt: hem to just over the belt
OPEN_COLS, OPEN_ROWS = set(range(67, 78)), 8   # front opening, belt (h 1.0) down to the hem
VENT_COLS, VENT_ROWS = set(range(22, 26)), 5   # back vent, hem up to h 0.82


def coat_rxry(z):
    if z <= COAT[0][0]:
        return COAT[0][1], COAT[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(COAT, COAT[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return COAT[-1][1], COAT[-1][2]


def drape(z, a):
    """Radial cloth folds as real ridges: none at the belt, growing toward the hem, deeper on the skirt front."""
    k = smooth((1.0 - z) / 0.45)
    front = max(0.0, -math.sin(a))
    return k * (0.018 + 0.012 * front) * sp(math.sin(FOLDS * a + 0.9 * math.sin(3.0 * z)), 0.6)


def coat_pt(z, a):
    rx, ry = coat_rxry(z)
    c, s = math.cos(a), math.sin(a)
    front, back = max(0.0, -s), max(0.0, s)
    bust = 1 + 0.12 * gauss(z, 1.2, 0.1) * front * front
    blade = 1 + 0.05 * gauss(z, 1.3, 0.08) * back * back
    p = Vector((c * rx, s * ry * bust * blade, z))
    return p + Vector((c, s, 0)) * drape(z, a)


def zmap(h, a):
    """Row height -> z for angle a: the hem follows the angle (0.62 at the front, 0.42 at the back)."""
    if h >= 1.0:
        return h
    zb = 0.42 + 0.20 * max(0.0, -math.sin(a))
    return zb + (h - 0.42) * (1.0 - zb) / 0.58


BODY_BVH = None  # set once the skinned body exists: front_pt() then projects onto it


def front_pt(z, x, out=0.012):
    """A point on the coat front at height z and x offset, pushed out by `out`."""
    if BODY_BVH is not None and z >= 1.04:
        hit, nrm, _, _ = BODY_BVH.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        if hit is not None:
            return hit + nrm * out
    rx, _ = coat_rxry(z)
    c = max(-0.999, min(0.999, x / rx))
    a = -math.acos(c)
    return coat_pt(z, a) + Vector((math.cos(a), math.sin(a), 0)) * out


def coat():
    bm = bmesh.new()
    rows = []
    for h in HS:
        row = []
        for i in range(NS):
            a = 2 * math.pi * i / NS
            row.append(bm.verts.new(coat_pt(zmap(h, a), a)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(NS):
            if (i in OPEN_COLS and j < OPEN_ROWS) or (i in VENT_COLS and j < VENT_ROWS):
                continue
            bm.faces.new((rows[j][i], rows[j][(i + 1) % NS], rows[j + 1][(i + 1) % NS], rows[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = kit._obj("coat", bm, MAT_CLOTH, 60.0)
    solidify(ob, 0.012)
    return subsurf(ob, 1)


def hood():
    """Stand-up collar."""
    # a stand-up collar: a flared band round the neck, open at the throat, thickened and softened
    prof = [(0.072, 1.37), (0.070, 1.40), (0.071, 1.43), (0.076, 1.455)]
    ob = kit.lathe("collar", prof, 40, mat=MAT_CLOTH, smooth_angle=80.0, cap=False)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.035 and abs(v.co.x) < 0.035], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    bake(ob, Matrix.Diagonal((1.0, 0.92, 1.0, 1.0)))
    solidify(ob, 0.008)
    return [subsurf(ob, 1)]


def lapel(sign):
    """A lapel as a real panel: inner edge down the coat opening, outer edge out to a notch under the collar,
    projected onto the chest, thickened and rounded."""
    rows = [(1.05, 0.012, 0.030), (1.12, 0.012, 0.055), (1.20, 0.014, 0.080), (1.27, 0.020, 0.100),
            (1.31, 0.030, 0.108), (1.325, 0.050, 0.090), (1.345, 0.052, 0.112), (1.37, 0.060, 0.098)]
    bm = bmesh.new()
    cols = 4
    grid = []
    for z, xi, xo in rows:
        grid.append([bm.verts.new(front_pt(z, sign * (xi + (xo - xi) * c / (cols - 1)), 0.010 + 0.004 * c / (cols - 1)))
                     for c in range(cols)])
    for j in range(len(rows) - 1):
        for c in range(cols - 1):
            bm.faces.new((grid[j][c], grid[j][c + 1], grid[j + 1][c + 1], grid[j + 1][c]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = kit._obj("lapel", bm, MAT_CLOTH, 70.0)
    solidify(ob, 0.007)
    return subsurf(ob, 1)


def buttons():
    out = []
    for k, z in enumerate((1.30, 1.22, 1.14, 1.06)):
        p = front_pt(z, 0.05, 0.02)
        out.append(orn.ellipsoid("button%d" % k, p, (0.011, 0.006, 0.011), "brass", 8, 4))
    return out


# ---------------------------------------------------------------- head

def thief_face(x, y, z):
    """Sculpted face: brow, cheekbones, eye sockets, ears, chin (the domino mask sits over the eyes)."""
    dx = dy = 0.0
    ax = abs(x)
    sx = 1.0 if x >= 0 else -1.0
    w = gauss(ax, 0.032, 0.018) * gauss(z, 0.115, 0.012)  # eye sockets, recessed
    if y < 0:
        dy += 0.006 * w
    w = gauss(ax, 0.03, 0.03) * gauss(z, 0.14, 0.014)  # brow
    if y < 0:
        dy -= 0.005 * w
    w = gauss(ax, 0.06, 0.02) * gauss(z, 0.08, 0.02)  # cheekbones
    dx += sx * 0.004 * w
    if y < 0:
        dy -= 0.004 * w
    return dx, dy, 0.0


def head_sculpt(x, y, z):
    """Face plus jaw, chin and back of the skull (the egg is broken here)."""
    dx, dy, dz = thief_face(x, y, z)
    j = smooth((0.085 - z) / 0.07)  # jaw narrows toward the chin
    dx += -x * 0.18 * j
    if y < 0:  # chin pushed forward
        dy -= 0.012 * gauss(x, 0.0, 0.03) * gauss(z, 0.02, 0.02)
    if y > 0:  # occiput
        dy += 0.012 * gauss(x, 0.0, 0.05) * gauss(z, 0.16, 0.05)
    return dx, dy, dz


PART_X = -0.035  # side parting, on the figure's right


def hairline(x, y):
    """Hair edge: a fringe over the brow swept off the side parting, lower over the temples, down to the nape."""
    if y < 0.0:  # the fringe comes down to the visor's top edge, a little higher at the parting
        return 0.150 + 0.012 * max(0.0, 1.0 - abs(x - PART_X) / 0.03)
    return 0.10


SKULL_C = V(0, 0.008, 0.115)
SKULL_R = (0.077, 0.096, 0.122)


def skull_pt(u, v, off=0.0):
    """Point on the (unsculpted) skull ellipsoid at longitude u (-pi/2 = front, -Y) and latitude v, pushed out."""
    rx, ry, rz = SKULL_R
    d = Vector((math.cos(v) * math.cos(u) * rx, math.cos(v) * math.sin(u) * ry, math.sin(v) * rz))
    n = Vector((d.x / rx ** 2, d.y / ry ** 2, d.z / rz ** 2)).normalized()
    return SKULL_C + d + n * off


def ellipsoid_mesh(name, centre, radii, mat, u=32, v=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(radii), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(centre), verts=bm.verts)
    return kit._obj(name, bm, mat, 80.0)


def visor():
    """A wraparound visor: a curved band over the eyes from temple to temple, its lower edge dipping at the
    nose bridge, thickened and rounded, with brass rivets at the temples."""
    cols, rows = 28, 4
    bm = bmesh.new()
    grid = []
    for j in range(rows):
        t = j / (rows - 1)
        row = []
        for i in range(cols):
            u = math.radians(-170 + 160 * i / (cols - 1))  # temple to temple round the front
            front = max(0.0, -math.sin(u))
            lo = EYE_Z - 0.024 - 0.006 * front  # deeper at the front, a shallow dip over the nose
            hi = EYE_Z + 0.022
            z = lo + (hi - lo) * t
            v = math.asin(max(-1.0, min(1.0, (z - SKULL_C.z) / SKULL_R[2])))
            row.append(bm.verts.new(skull_pt(u, v, 0.010 + 0.004 * front)))
        grid.append(row)
    for j in range(rows - 1):
        for i in range(cols - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = kit._obj("visor", bm, MAT_MASK, 80.0)
    solidify(ob, 0.007)
    parts = [subsurf(ob, 1)]
    for side in (-1, 1):
        u = math.radians(-170 if side < 0 else -10)
        parts.append(orn.ellipsoid("rivet", skull_pt(u, math.asin((EYE_Z - SKULL_C.z) / SKULL_R[2]), 0.018),
                                   (0.008, 0.008, 0.008), "brass", 10, 5))
    return parts


def hair_shell():
    """Hair with volume as one sculpted shell: fuller over the crown, swept back from a side parting in
    shallow ridges (strands carved into the surface), cut at the hairline; plus a bun that sits into it."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    rx, ry, rz = SKULL_R
    for vt in bm.verts:
        n = vt.co.copy()
        u = math.atan2(n.y, n.x)
        lat = math.asin(max(-1.0, min(1.0, n.z)))
        p = skull_pt(u, lat, 0.0)
        crown = 0.010 + 0.010 * smooth((lat - 0.2) / 0.9)  # thicker over the crown
        ridge = 0.0025 * math.sin(26 * (u + 0.35 * lat))  # strands swept back and round
        nn = Vector((p.x - SKULL_C.x, p.y - SKULL_C.y, p.z - SKULL_C.z)).normalized()
        # below the hairline the shell tucks under the skin, so the edge is the clean line where the two meet
        under = smooth((hairline(p.x, p.y) - p.z) / 0.012)
        vt.co = p + nn * ((crown + ridge) * (1.0 - under) - 0.012 * under)
    kill = [vt for vt in bm.verts if vt.co.z < hairline(vt.co.x, vt.co.y) - 0.05]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    ob = kit._obj("hair", bm, MAT_HAIR, 80.0)
    solidify(ob, 0.006)
    return [subsurf(ob, 1), ellipsoid_mesh("bun", (0, 0.112, 0.135), (0.042, 0.036, 0.040), MAT_HAIR, 20, 10)]


def thief_head():
    ob = ellipsoid_mesh("thief_head", SKULL_C, SKULL_R, MAT_SKIN, 40, 20)
    sculpt(ob, head_sculpt)
    subsurf(ob, 1)
    parts = [ob]
    # nose: a tapered ridge from brow to a rounded tip, about 2 cm proud of the face
    parts.append(orn.taper("nose", [V(0, -0.084, 0.115), V(0, -0.097, 0.088), V(0, -0.106, 0.062),
                                    V(0, -0.092, 0.05)], [0.008, 0.009, 0.011, 0.007], 10, MAT_SKIN))
    parts.append(orn.taper("lip_u", [V(-0.021, -0.081, 0.04), V(0, -0.088, 0.042), V(0.021, -0.081, 0.04)],
                           [0.005, 0.007, 0.005], 10, MAT_SKIN, flat=0.5, up=(0, 0, 1)))
    parts.append(orn.taper("lip_l", [V(-0.019, -0.080, 0.025), V(0, -0.086, 0.023), V(0.019, -0.080, 0.025)],
                           [0.006, 0.007, 0.006], 10, MAT_SKIN, flat=0.5, up=(0, 0, 1)))
    for side in (-1, 1):  # ears: flat shells set against the side of the skull
        parts.append(ellipsoid_mesh("ear", (side * 0.074, 0.012, 0.105), (0.009, 0.017, 0.028), MAT_SKIN, 14, 8))
    parts.extend(hair_shell())
    parts.extend(visor())
    head = kit.join("thief_head", parts)
    bm = bmesh.new()  # triangulate n-gon caps so Godot gets tangents for the skin normal map
    bm.from_mesh(head.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(head.data)
    bm.free()
    head.location = NECK
    return head


# ---------------------------------------------------------------- legs

def leg(s):
    """s = -1 right leg (knee bent forward, foot planted), +1 left leg (straight, weight carried here).
    Trousers tuck into tall boots that reach the knee; each boot stands on its sole at z=0."""
    k = -0.05 if s < 0 else 0.0
    x = 0.10 * s
    side = "L" if s > 0 else "R"
    trousers = [(V(0.09 * s, 0.0, 0.98), 0.11, 0.10), (V(x, 0.0, 0.86), 0.095, 0.095),
                (V(x, 0.0, 0.74), 0.08, 0.08), (V(x, 0.6 * k, 0.62), 0.07, 0.07),
                (V(x, k, 0.47), 0.06, 0.06), (V(x, 0.6 * k, 0.40), 0.057, 0.058)]
    boot = [(V(x, 0.85 * k, 0.52), 0.068, 0.07), (V(x, k, 0.47), 0.066, 0.066),
            (V(x, 0.5 * k, 0.36), 0.064, 0.064), (V(x, 0.2 * k, 0.22), 0.05, 0.05),
            (V(x, 0.0, 0.075), 0.042, 0.045), (V(x, -0.06, 0.06), 0.042, 0.04),
            (V(x, -0.12, 0.04), 0.042, 0.038), (V(x, -0.18, 0.04), 0.036, 0.036)]
    bt = limb("boot_" + side, boot, MAT_LEATHER, per=2, sides=12, sup=2.8)
    zmin = min(v.co.z for v in bt.data.vertices)
    bake(bt, Matrix.Translation((0, 0, -zmin)))  # sole exactly on z=0
    # one continuous sole from toe to heel, with a 3.5 cm heel block under the counter; both overlap the boot
    sole = kit.box("sole_" + side, (0.08, 0.24, 0.012), (x, -0.08, 0.006), mat=MAT_LEATHER, bevel=0.004)
    heel = kit.box("heel_" + side, (0.06, 0.07, 0.035), (x, 0.0, 0.0175), mat=MAT_LEATHER, bevel=0.006)
    return [kit.join("boot_" + side, [bt, sole, heel])]


# ---------------------------------------------------------------- arms

def elbow_warp(t, a):
    """Three compression folds across the elbow (t around the middle key), on the sides of the sleeve."""
    folds = gauss(t, 0.44, 0.025) + gauss(t, 0.5, 0.025) + gauss(t, 0.56, 0.025)
    return 1 - 0.05 * folds * (0.5 + 0.5 * math.cos(2 * a))


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


def left_arm():
    """The static left arm: sleeve to the wrist, a thick leather cuff, and a closed fist at the chest."""
    keys = [(L_SHOULDER, 0.06, 0.062), (V(0.2, -0.05, 1.27), 0.056, 0.058),
            (V(0.2, -0.10, 1.10), 0.037, 0.04), (V(0.15, -0.14, 1.17), 0.04, 0.042),
            (V(0.12, -0.16, 1.22), 0.03, 0.028)]
    parts = []  # the sleeve is part of body()
    Wr = V(0.12, -0.16, 1.22)
    d = (Wr - V(0.15, -0.14, 1.17)).normalized()
    parts.append(subsurf(loft("cuff_L", [Wr - d * 0.03, Wr - d * 0.01, Wr + d * 0.005], [0.036, 0.042, 0.036],
                              [0.036, 0.042, 0.036], MAT_LEATHER, sides=14, sup=2.4), 1))
    C = V(0.075, -0.18, 1.25)
    parts.extend(fist(C))
    # thumb from the inner side of the hand, wrapping across the front of the curled index and middle fingers,
    # ending over the middle finger's second segment
    keys = [(C + V(-0.044, -0.016, 0.012), 0.0095, 0.0095), (C + V(-0.034, -0.048, 0.008), 0.0093, 0.0093),
            (C + V(-0.018, -0.060, 0.0), 0.0089, 0.0089), (C + V(-0.005, -0.060, -0.014), 0.0085, 0.0085)]
    parts.append(limb("thumb_L", keys, MAT_LEATHER, per=2, sides=8, sup=2.2))
    return parts


def arm_r():
    """Reaching right arm, sleeve, cuff and an open gloved hand. Origin at the right shoulder."""
    sh = R_SHOULDER
    keys = [(sh, 0.066, 0.07), (V(-0.2, -0.05, 1.27), 0.058, 0.06), (V(-0.215, -0.13, 1.13), 0.037, 0.04),
            (V(-0.21, -0.25, 1.08), 0.042, 0.044), (V(-0.2, -0.36, 1.04), 0.033, 0.03)]
    parts = [skin_graph("thief_arm_sleeve", [(V(-0.17, 0.0, 1.35), 0.060), (keys[1][0], 0.051),
                                             (keys[2][0], 0.040), (keys[3][0], 0.039), (keys[4][0], 0.032)],
                        [(0, 1), (1, 2), (2, 3), (3, 4)], MAT_CLOTH)]
    W = V(-0.2, -0.36, 1.04)
    d_arm = (W - V(-0.21, -0.25, 1.08)).normalized()
    # cuff flares open over the end of the sleeve
    parts.append(subsurf(loft("cuff_R", [W - d_arm * 0.045, W - d_arm * 0.02, W, W + d_arm * 0.012],
                              [0.038, 0.046, 0.052, 0.045], [0.038, 0.046, 0.052, 0.045],
                              MAT_LEATHER, sides=14, sup=2.4), 1))
    d = Vector((0, -0.8, -0.25)).normalized()
    X, Z = V(1, 0, 0), V(0, 0, 1)
    # palm with volume: widest across the knuckles, domed on the back
    palm_end = W + d * 0.09
    parts.append(subsurf(loft("palm", [W - d * 0.005, W + d * 0.03, W + d * 0.06, palm_end],
                              [0.030, 0.042, 0.044, 0.038], [0.014, 0.020, 0.022, 0.018],
                              MAT_LEATHER, sides=12, sup=2.4), 1))
    # four relaxed fingers, little (-X) to index (+X): fanned a few degrees outward, reach index 1.0 / middle 1.08 /
    # ring 1.0 / little 0.8, curl growing toward the little finger, tapered 11.5 -> 7.5 mm with a swollen base knuckle
    for k, (off, fan, reach, curl) in enumerate(((-0.024, -6, 0.80, 1.3), (-0.008, -2, 1.0, 1.1),
                                                 (0.008, 2, 1.08, 0.9), (0.024, 6, 1.0, 0.7))):
        dk = Matrix.Rotation(math.radians(fan), 3, "Z") @ d
        B = palm_end + X * off
        keys = [(B, 0.0115 * 1.1, 0.0115 * 1.1),
                (B + dk * 0.040 * reach - Z * 0.003 * curl, 0.0105, 0.0105),
                (B + dk * 0.070 * reach - Z * 0.014 * curl, 0.0092, 0.0092),
                (B + dk * 0.092 * reach - Z * 0.024 * curl, 0.0075, 0.0075)]
        parts.append(limb("finger_R%d" % k, keys, MAT_LEATHER, per=3, sides=8, sup=2.2))
    # thumb from the palm's inner side, angled forward and slightly in, tapered
    keys = [(W + d * 0.02 + X * 0.030 - Z * 0.004, 0.0115, 0.0115),
            (W + d * 0.055 + X * 0.052 - Z * 0.008, 0.0102, 0.0102),
            (W + d * 0.085 + X * 0.068 - Z * 0.014, 0.0090, 0.0090),
            (W + d * 0.11 + X * 0.078 - Z * 0.018, 0.0075, 0.0075)]
    parts.append(limb("thumb_R", keys, MAT_LEATHER, per=3, sides=8, sup=2.2))
    return pivot(kit.join("thief_arm", parts), sh)


# ---------------------------------------------------------------- body

def build(args):
    global BODY_BVH
    from mathutils.bvhtree import BVHTree
    b = body()
    BODY_BVH = BVHTree.FromObject(b, bpy.context.evaluated_depsgraph_get())
    parts = [b, coat()]
    parts.extend(hood())
    parts.append(lapel(1))
    parts.append(lapel(-1))
    parts.extend(buttons())
    # belt: a rolled leather band following the waist of the coat, with a brass buckle at the front
    belt = [coat_pt(1.04, 2 * math.pi * k / 64) + Vector((math.cos(2 * math.pi * k / 64),
                                                          math.sin(2 * math.pi * k / 64), 0)) * 0.008
            for k in range(64)]
    parts.append(loop_tube("belt", belt, 0.014, MAT_LEATHER, 10))
    buckle = kit.torus("buckle", 0.026, 0.005, 20, 6, mat="brass")
    parts.append(bake(buckle, frame((0, -0.13, 1.04), (0, -1, 0))))
    # satchel on the left hip, clasp in brass, strap across the body from the right shoulder to the belt
    parts.append(orn.ellipsoid("pouch", V(0.2, -0.02, 0.84), (0.09, 0.07, 0.14), MAT_LEATHER, 12, 6))
    parts.append(kit.box("satchel_clasp", (0.03, 0.012, 0.03), V(0.2, -0.065, 0.9), mat="brass", bevel=0.004))
    strap_pts = [front_pt(1.34, -0.17, 0.014), front_pt(1.24, -0.12, 0.014), front_pt(1.14, -0.04, 0.014),
                 front_pt(1.07, 0.06, 0.014), front_pt(1.04, 0.12, 0.014)]
    parts.append(orn.taper("strap", strap_pts, [0.016] * len(strap_pts), 6, MAT_LEATHER, flat=0.3,
                           up=(0, -1, 0)))
    for s in (-1, 1):
        parts.extend(leg(s))
    parts.extend(left_arm())
    kit.join("thief", parts)
    thief_head()
    arm_r()
