"""THE THIEF, ACQUIRED: a life-size (1.69 m) plaster cast of a young woman caught mid-theft, standing on
z=0 (the pedestal in pedestal.py is applied in Godot). Facing -Y. Figure's right = -X.

Weight on the back (left, +X) foot, the right arm reaching forward and down, the left hand closed at
the chest. A long coat open from the belt down (trousers show), lapels and brass buttons, a back vent,
a hem higher at the front, a symmetric rolled collar with a drape down the back, tall boots on flat soles,
domino mask over a sculpted face, hair with a bun.

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
HEAD_PROF = [(0.0, -0.03), (0.036, -0.03), (0.05, -0.005), (0.066, 0.03), (0.077, 0.07), (0.082, 0.11),
             (0.083, 0.14), (0.078, 0.175), (0.066, 0.21), (0.045, 0.235), (0.0, 0.245)]
# head half-sizes at the eye line after the head bake (x 0.92, y 1.08)
EYE_RX, EYE_RY, EYE_Z = 0.0754, 0.0886, 0.12
MAT_CLOTH, MAT_LEATHER, MAT_SKIN, MAT_MASK = "thief_cloth", "thief_leather", "thief_skin", "thief_mask"
MAT_HAIR = "thief_hair"
HEAD_SCALE = (0.92, 1.08, 1.0, 1.0)


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


def densify(prof, k=2):
    out = []
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        for i in range(k):
            t = i / k
            out.append((r0 + (r1 - r0) * t, z0 + (z1 - z0) * t))
    out.append(prof[-1])
    return out


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


# ---------------------------------------------------------------- coat

NS = 96  # coat sides: 14 drape folds => ~7 samples per fold
FOLDS = 14
# coat rows as fixed heights; below the belt (h < 1.0) the hem is raised at the front and dropped at the back
HS = [0.42, 0.50, 0.58, 0.66, 0.74, 0.82, 0.90, 0.96, 1.00, 1.04, 1.10, 1.18, 1.26, 1.33, 1.38, 1.44]
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


def front_pt(z, x, out=0.012):
    """A point on the coat front at height z and x offset, pushed out by `out`."""
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
    bm.faces.new(rows[-1])  # closed under the collar; open at the hem and the front edges (solidify gives them thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = kit._obj("coat", bm, MAT_CLOTH, 60.0)
    solidify(ob, 0.012)
    return subsurf(ob, 1)


def hood():
    """Symmetric rolled collar wrapping behind the neck, plus a drape hanging down the upper back."""
    collar_keys = [(V(-0.17, -0.04, 1.36), 0.028, 0.028), (V(-0.14, 0.05, 1.42), 0.032, 0.032),
                   (V(0.0, 0.10, 1.44), 0.036, 0.036), (V(0.14, 0.05, 1.42), 0.032, 0.032),
                   (V(0.17, -0.04, 1.36), 0.028, 0.028)]
    drape_keys = [(V(0.0, 0.105, 1.42), 0.034, 0.034), (V(0.0, 0.14, 1.30), 0.03, 0.03),
                  (V(0.0, 0.135, 1.16), 0.028, 0.028), (V(0.0, 0.12, 1.06), 0.024, 0.024)]
    return [limb("collar", collar_keys, MAT_CLOTH, per=3, sides=14, sup=2.2),
            limb("hood_drape", drape_keys, MAT_CLOTH, per=3, sides=12, sup=2.2)]


def lapel(sign):
    pts = [front_pt(z, sign * x, 0.016) for z, x in ((1.36, 0.035), (1.24, 0.07), (1.12, 0.085), (1.04, 0.09))]
    return subsurf(loft("lapel", pts, [0.016] * 4, [0.009] * 4, MAT_CLOTH, sides=8, sup=2.2, hint=(0, -1, 0)), 1)


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


def _mask_surface(x, z):
    """Front surface of the head under the mask, offset outward by 12 mm."""
    y = -EYE_RY * math.sqrt(max(0.0, 1 - (x / EYE_RX) ** 2)) - 0.012
    return Vector((x, y, z))


def domino_mask():
    """Domino mask: a superellipse plate laid over the eyes, fitted to the face and thickened."""
    A, B, R, S = 0.068, 0.022, 5, 24
    bm = bmesh.new()
    centre = bm.verts.new(_mask_surface(0.0, EYE_Z))
    rings = []
    for i in range(1, R + 1):
        r = i / R
        ring = []
        for k in range(S):
            t = 2 * math.pi * k / S
            x = A * r * sp(math.cos(t), 0.5)
            z = EYE_Z + B * r * sp(math.sin(t), 0.5)
            ring.append(bm.verts.new(_mask_surface(x, z)))
        rings.append(ring)
    for k in range(S):
        bm.faces.new((centre, rings[0][(k + 1) % S], rings[0][k]))
    for i in range(R - 1):
        for k in range(S):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % S], rings[i + 1][(k + 1) % S], rings[i + 1][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = kit._obj("mask", bm, MAT_MASK, 60.0)
    orn.face_toward(ob, (0, -1, 0))
    solidify(ob, 0.006)
    return subsurf(ob, 1)


PART_X = -0.035  # side parting, on the figure's right


def hairline(x, y):
    """Hair edge: a fringe over the brow swept off the side parting, lower over the temples, down to the nape."""
    if y < 0.0:
        return 0.205 - 0.035 * min(1.0, abs(x - PART_X) / 0.08)
    return 0.12


def head_r(z):
    """Head profile radius at height z (linear between HEAD_PROF points)."""
    for (r0, z0), (r1, z1) in zip(HEAD_PROF, HEAD_PROF[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 0.0


def hair_pt(a, z, off=0.024):
    """Point just off the head surface. a = -pi/2 is the front (-Y), a = pi/2 the back (+Y)."""
    r = head_r(z) + off
    return V(r * math.cos(a) * HEAD_SCALE[0], r * math.sin(a) * HEAD_SCALE[1], z)


def swept_strands():
    """Six hair strands from the parting, swept back over the ear to the nape, in a loose wave."""
    base = [(-2.05, 0.205), (-2.45, 0.225), (-2.85, 0.205), (-3.14, 0.165), (-3.5, 0.125),
            (-3.9, 0.095), (-4.3, 0.085)]
    out = []
    for k in range(6):
        keys = [(hair_pt(a - 0.03 * k, z - 0.004 * k + 0.003 * math.sin(0.9 * i + k), 0.021), 0.0036, 0.0036)
                for i, (a, z) in enumerate(base)]
        pts, rx, ry = spline(keys, 2)  # no subsurf pass: strands are thin and numerous, budget matters
        out.append(loft("strand%d" % k, pts, rx, ry, MAT_HAIR, sides=6, sup=2.0))
    return out


def wisps():
    """Loose wisps breaking the hairline: three at each temple, two at the nape. (angle, drift direction)."""
    out = []
    for i, (a, d) in enumerate([(-2.17, -1), (-0.97, 1), (-2.40, -1), (-0.75, 1), (2.02, 1), (1.12, -1)]):
        p = hair_pt(a, 0.2)
        z0 = hairline(p.x, p.y) - 0.004  # start on the hairline
        pts = [hair_pt(a, z0, 0.022), hair_pt(a + 0.07 * d, z0 - 0.02, 0.03), hair_pt(a + 0.14 * d, z0 - 0.05, 0.038)]
        out.append(orn.taper("wisp%d" % i, pts, [0.0028, 0.0019, 0.0007], 4, MAT_HAIR, flat=1.0))
    return out


def thief_head():
    prof = densify(HEAD_PROF, 2)
    ob = kit.lathe("thief_head", prof, 36, mat=MAT_SKIN, smooth_angle=80.0)
    bake(ob, Matrix.Diagonal(HEAD_SCALE))
    sculpt(ob, head_sculpt)
    subsurf(ob, 1)
    parts = [ob]
    # nose: a tapered ridge from brow to a rounded tip, about 2 cm proud of the face
    parts.append(orn.taper("nose", [V(0, -0.078, 0.125), V(0, -0.095, 0.095), V(0, -0.108, 0.065),
                                    V(0, -0.09, 0.05)], [0.009, 0.008, 0.011, 0.007], 8, MAT_SKIN))
    # lips: an upper and a lower sweep
    parts.append(orn.taper("lip_u", [V(-0.022, -0.075, 0.04), V(0, -0.082, 0.042), V(0.022, -0.075, 0.04)],
                           [0.005, 0.007, 0.005], 8, MAT_SKIN, flat=0.5, up=(0, 0, 1)))
    parts.append(orn.taper("lip_l", [V(-0.02, -0.074, 0.024), V(0, -0.08, 0.022), V(0.02, -0.074, 0.024)],
                           [0.006, 0.007, 0.006], 8, MAT_SKIN, flat=0.5, up=(0, 0, 1)))
    # ears
    for side in (-1, 1):
        parts.append(orn.ellipsoid("ear", (side * 0.077, 0.0, 0.105), (0.013, 0.02, 0.03), MAT_SKIN, 10, 5))
    # hair: a shell over the crown with real volume, hairline cut by hairline()
    hair_prof = [(r + 0.018, z) for r, z in prof if z >= 0.06]
    hair = kit.lathe("hair", hair_prof, 36, mat=MAT_HAIR, smooth_angle=80.0, cap=False)
    bake(hair, Matrix.Diagonal(HEAD_SCALE))
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    kill = [v for v in bm.verts if v.co.z < hairline(v.co.x, v.co.y)]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(hair.data)
    bm.free()
    parts.append(subsurf(hair, 1))
    # a larger bun at the back of the head, with a rope of hair wound twice round it
    bun_c = V(0, 0.115, 0.10)
    parts.append(orn.ellipsoid("bun", bun_c, (0.06, 0.06, 0.056), MAT_HAIR, 14, 7))
    parts.extend(swept_strands())
    parts.extend(wisps())
    parts.append(domino_mask())
    for side in (-1, 1):  # brass rivets at the ends of the mask
        p = _mask_surface(side * 0.064, EYE_Z)
        parts.append(orn.ellipsoid("rivet", p, (0.009, 0.009, 0.009), "brass", 8, 4))
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
    tro = limb("trouser_" + side, trousers, MAT_CLOTH, per=3, sides=14, sup=2.4)
    bt = limb("boot_" + side, boot, MAT_LEATHER, per=2, sides=12, sup=2.8)
    zmin = min(v.co.z for v in bt.data.vertices)
    bake(bt, Matrix.Translation((0, 0, -zmin)))  # sole exactly on z=0
    # one continuous sole from toe to heel, with a 3.5 cm heel block under the counter; both overlap the boot
    sole = kit.box("sole_" + side, (0.08, 0.24, 0.012), (x, -0.08, 0.006), mat=MAT_LEATHER, bevel=0.004)
    heel = kit.box("heel_" + side, (0.06, 0.07, 0.035), (x, 0.0, 0.0175), mat=MAT_LEATHER, bevel=0.006)
    return [tro, kit.join("boot_" + side, [bt, sole, heel])]


# ---------------------------------------------------------------- arms

def elbow_warp(t, a):
    """Three compression folds across the elbow (t around the middle key), on the sides of the sleeve."""
    folds = gauss(t, 0.44, 0.025) + gauss(t, 0.5, 0.025) + gauss(t, 0.56, 0.025)
    return 1 - 0.05 * folds * (0.5 + 0.5 * math.cos(2 * a))


def fist(C):
    """Closed left fist: one rounded block 9 x 8 x 10 cm, three shallow grooves down the front for the fingers."""
    ob = orn.ellipsoid("fist", V(0, 0, 0), (0.09, 0.08, 0.10), MAT_LEATHER, 16, 8)
    ob.data.transform(Matrix.Diagonal((0.09, 0.08, 0.10, 1.0)))  # bake the size into the mesh
    ob.scale = (1, 1, 1)

    def groove(x, y, z):
        if y >= -0.01:
            return (0.0, 0.0, 0.0)
        band = gauss(z, 0.0, 0.035)  # grooves run over the finger band only
        g = sum(gauss(x, xg, 0.0045) for xg in (-0.018, 0.0, 0.018))
        return (0.0, 0.005 * g * band, 0.0)

    sculpt(ob, groove)
    ob.location = C
    return subsurf(ob, 1)


def left_arm():
    """The static left arm: sleeve to the wrist, a thick leather cuff, and a closed fist at the chest."""
    keys = [(L_SHOULDER, 0.06, 0.062), (V(0.2, -0.05, 1.27), 0.056, 0.058),
            (V(0.2, -0.10, 1.10), 0.037, 0.04), (V(0.15, -0.14, 1.17), 0.04, 0.042),
            (V(0.12, -0.16, 1.22), 0.03, 0.028)]
    parts = [limb("arm_L_sleeve", keys, MAT_CLOTH, per=3, sides=14, sup=2.5, warp=elbow_warp)]
    Wr = V(0.12, -0.16, 1.22)
    d = (Wr - V(0.15, -0.14, 1.17)).normalized()
    parts.append(subsurf(loft("cuff_L", [Wr - d * 0.03, Wr - d * 0.01, Wr + d * 0.005], [0.036, 0.042, 0.036],
                              [0.036, 0.042, 0.036], MAT_LEATHER, sides=14, sup=2.4), 1))
    C = V(0.075, -0.18, 1.25)
    parts.append(fist(C))
    # thumb lying on the top of the fist block
    keys = [(C + V(0.025, -0.005, 0.056), 0.009, 0.009), (C + V(0.0, -0.035, 0.058), 0.009, 0.009),
            (C + V(-0.025, -0.058, 0.055), 0.009, 0.009)]
    parts.append(limb("thumb_L", keys, MAT_LEATHER, per=2, sides=8, sup=2.2))
    return parts


def arm_r():
    """Reaching right arm, sleeve, cuff and an open gloved hand. Origin at the right shoulder."""
    sh = R_SHOULDER
    keys = [(sh, 0.066, 0.07), (V(-0.2, -0.05, 1.27), 0.058, 0.06), (V(-0.215, -0.13, 1.13), 0.037, 0.04),
            (V(-0.21, -0.25, 1.08), 0.042, 0.044), (V(-0.2, -0.36, 1.04), 0.033, 0.03)]
    parts = [limb("thief_arm_sleeve", keys, MAT_CLOTH, per=3, sides=14, sup=2.5, warp=elbow_warp)]
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
    # four fingers, about 1.7 cm thick, three phalanges each, bent slightly at every knuckle
    for k, (off, f) in enumerate(zip((-0.024, -0.008, 0.008, 0.024), (1.0, 1.05, 1.0, 0.85))):
        B = palm_end + X * off
        keys = [(B, 0.011, 0.011),
                (B + d * 0.040 * f - Z * 0.003, 0.0105, 0.0105),
                (B + d * 0.070 * f - Z * 0.014, 0.0098, 0.0098),
                (B + d * 0.092 * f - Z * 0.024, 0.0090, 0.0090)]
        parts.append(limb("finger_R%d" % k, keys, MAT_LEATHER, per=2, sides=8, sup=2.2))
    # thumb from the palm's inner side, angled out
    keys = [(W + d * 0.02 + X * 0.036 - Z * 0.004, 0.011, 0.011),
            (W + d * 0.05 + X * 0.060 - Z * 0.008, 0.0105, 0.0105),
            (W + d * 0.08 + X * 0.075 - Z * 0.020, 0.0095, 0.0095),
            (W + d * 0.11 + X * 0.085 - Z * 0.024, 0.0085, 0.0085)]
    parts.append(limb("thumb_R", keys, MAT_LEATHER, per=2, sides=8, sup=2.2))
    return pivot(kit.join("thief_arm", parts), sh)


# ---------------------------------------------------------------- body

def build(args):
    parts = [coat()]
    parts.append(limb("neck", [(V(0, 0, 1.30), 0.062, 0.058), (V(0, 0, 1.38), 0.052, 0.05),
                               (NECK + V(0, 0, 0.0), 0.046, 0.045)], MAT_SKIN, per=2, sides=12))
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
