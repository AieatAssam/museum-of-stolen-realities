"""Docent-construct: a museum attendant, 2.3 m tall (on purpose a little too tall), in a floor-length
pleated robe with a velvet stole, gilt collar, cuffs, hem band and a brass badge. A porcelain mask
(smooth oval, sculpted nose, closed lids, a small mouth line) sits inside a cloth veil. The figure
cradles a sketchboard in both hands, pencil in the right (figure's right = -X; the figure faces -Y).

Pivots (Godot animates these by name):
  docent  static body (robe, belt, hem, collar, stole, badge); origin at the floor centre
  head    mask, veil and neck; origin at the neck pivot
  arm_L   origin at the left shoulder joint (+X);  arm_R origin at the right shoulder joint (-X)
  board   sketchboard with clip and sheet; origin at the board centre
  pencil  pencil; origin at the grip point
  docent-convcolonly  invisible convex collider

Triangle budget: robe and veil are the only high-count parts. Limbs and hands are subdivided once.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

ROBE_M = "docent_robe"
PORC_M = "docent_porcelain"
GLOVE_M = "docent_glove"

NPLEAT = 24  # deep vertical pleats around the robe
NCOL = 168  # 7 columns per pleat
HEADC = Vector((0.0, -0.005, 2.165))  # centre of the mask
HEAD_PIVOT = (0.0, -0.005, 2.0)  # neck pivot
SHOULDER = {1: Vector((0.205, 0.0, 1.855)), -1: Vector((-0.205, 0.0, 1.855))}  # +1 = figure's left

# robe section stations (z, half-width x, half-depth y): hem flare, hip, waist, bust, shoulders
ROBE = [(0.00, 0.40, 0.33), (0.06, 0.385, 0.32), (0.20, 0.345, 0.28), (0.45, 0.30, 0.235),
        (0.80, 0.265, 0.20), (1.00, 0.25, 0.19), (1.15, 0.225, 0.175), (1.25, 0.19, 0.155),
        (1.40, 0.17, 0.13), (1.50, 0.18, 0.135), (1.60, 0.20, 0.15), (1.70, 0.215, 0.14),
        (1.80, 0.23, 0.13), (1.88, 0.245, 0.12), (1.93, 0.23, 0.11), (1.97, 0.10, 0.09)]

BOARD_C = Vector((0.0, -0.36, 1.27))
BOARD_ROT = Matrix.Rotation(math.radians(-38), 4, "X")
BOARD_M = Matrix.Translation(BOARD_C) @ BOARD_ROT
W_R = Vector((-0.27, -0.33, 1.30))  # right wrist (holds the pencil)
W_L = Vector((0.27, -0.33, 1.30))  # left wrist (holds the board edge)
SHEET_TIP = BOARD_M @ Vector((-0.10, -0.02, -0.04))  # pencil lies on the sheet (axis 7.5 mm in front of it)
PENCIL_U = (BOARD_ROT @ Vector((-0.9, 0.0, 0.434))).normalized()  # in the sheet plane, toward the right wrist
PENCIL_G = SHEET_TIP + PENCIL_U * 0.12  # grip point


def V(*a):
    return Vector(a)


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def gauss(v, c, s):
    return math.exp(-((v - c) / s) ** 2)


def lens(x, z, cx, cz, hw, hh):
    q = 1 - ((x - cx) / hw) ** 2 - ((z - cz) / hh) ** 2
    return math.sqrt(q) if q > 0 else 0.0


def bake(ob, M):
    ob.data.transform(M)
    return ob


def frame(origin, axis):
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
    return Matrix.Translation(Vector(origin)) @ q


def pivot(ob, p):
    """Move the origin to p without moving the geometry in the world."""
    p = Vector(p)
    ob.data.transform(Matrix.Translation(-p))
    ob.location = p
    return ob


def subsurf(ob, levels=1):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=m.name)
    ob.select_set(False)
    return ob


def sweep(name, pts, radii, sides=10, mat=None, flat=1.0, up=(0, 0, 1), fold=0.0, nfold=0,
          smooth_angle=45.0):
    """Capped tube (or flat ribbon when flat < 1) along pts with per-point radius. nfold > 0 adds
    lengthwise folds around the circumference (cloth)."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    U = Vector(up)
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        u = U - d * U.dot(d)
        if u.length < 1e-4:
            u = Vector((1, 0, 0)) - d * d.x
        u.normalize()
        x = d.cross(u).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            m = 1.0 + fold * math.sin(nfold * a) if nfold else 1.0
            ring.append(bm.verts.new(p + (x * math.cos(a) + u * math.sin(a) * flat) * radii[i] * m))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    for ring in (rings[0], rings[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / sides)
        for k in range(sides):
            bm.faces.new((ring[k], ring[(k + 1) % sides], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, smooth_angle)


def ring_tube(name, pts, r, mat, sides=8, up=(0, 0, 1)):
    """Closed round cord through a loop of points (belt, hem braid, mask lines). `up` sets the frame."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    n = len(P)
    rings = []
    U = Vector(up)
    for i, p in enumerate(P):
        d = (P[(i + 1) % n] - P[i - 1]).normalized()
        u = (U - d * U.dot(d)).normalized()
        x = d.cross(u).normalized()
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + u * math.sin(2 * math.pi * k / sides)) * r)
                      for k in range(sides)])
    for i in range(n):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[(i + 1) % n][k], rings[(i + 1) % n][(k + 1) % sides], rings[i][(k + 1) % sides]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 60.0)


def rxry(z):
    if z <= ROBE[0][0]:
        return ROBE[0][1], ROBE[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(ROBE, ROBE[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return ROBE[-1][1], ROBE[-1][2]


def _hash(k):
    return (math.sin(k * 12.9898) * 43758.5453) % 1.0


def pleat_amp(z):
    """Deep pleats from the hem up to the belt, gathered just under it."""
    return 0.11 * smooth((1.40 - z) / 0.55) + 0.035 * gauss(z, 1.36, 0.05)


def robe_pt(z, a):
    rx, ry = rxry(z)
    hb = 0.02 * gauss(z, 0.03, 0.03)  # rolled hem
    rx, ry = rx + hb, ry + hb * 0.8
    c, s = math.cos(a), math.sin(a)
    k = int((a % (2 * math.pi)) / (2 * math.pi) * NPLEAT) % NPLEAT
    brk = 0.6 + 0.8 * _hash(k + 1)  # every pleat breaks a little differently
    fold = abs(math.sin(NPLEAT * a / 2))  # 1 on the ridge, 0 in the crease
    bod = 0.012 * smooth((z - 1.40) / 0.04) * (1 - smooth((z - 1.66) / 0.12)) * (1 - abs(math.sin(6 * a)) ** 0.6)  # bodice folds
    pleat = 1 - pleat_amp(z) * brk * (1 - fold ** 0.6) - bod
    flare = 1 + 0.045 * fold * smooth((0.35 - z) / 0.35)  # ridges fan out at the floor
    front, back = max(0.0, -s), max(0.0, s)
    bust = 1 + 0.12 * gauss(z, 1.60, 0.10) * front * front
    blade = 1 + 0.05 * gauss(z, 1.82, 0.08) * back * back
    lean = -0.012 * (z / 2.0) ** 2
    return Vector((c * rx * pleat * flare, s * ry * pleat * flare * bust * blade + lean, z))


def front_pt(z, x, out=0.012):
    """A point on the robe front at height z and x offset, pushed out by `out`."""
    rx, _ = rxry(z)
    c = max(-0.999, min(0.999, x / rx))
    a = -math.acos(c)
    return robe_pt(z, a) + Vector((math.cos(a), math.sin(a), 0)) * out


def outward(p, off):
    return p + Vector((p.x, p.y, 0)).normalized() * off


def robe():
    zs = []
    for (z0, _, _), (z1, _, _) in zip(ROBE, ROBE[1:]):
        zs += [z0, z0 + (z1 - z0) / 2]
    zs.append(ROBE[-1][0])
    bm = bmesh.new()
    rows = [[bm.verts.new(robe_pt(z, 2 * math.pi * i / NCOL)) for i in range(NCOL)] for z in zs]
    for j in range(len(rows) - 1):
        for i in range(NCOL):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % NCOL], rows[j + 1][(i + 1) % NCOL], rows[j + 1][i]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj("robe", bm, ROBE_M, 50.0)


def face_relief(x, z):
    """Outward offset (m) of the mask at face coords x, z: nose bridge and tip, closed lids,
    faint brow and cheek planes, chin, a small mouth line."""
    r = 0.050 * gauss(x, 0, 0.011) * gauss(z, -0.005, 0.040)  # nose bridge (2x relief)
    r += 0.012 * gauss(x, 0, 0.012) * gauss(z, -0.050, 0.012)  # nose tip
    r += 0.0045 * lens(x, z, -0.031, 0.0, 0.021, 0.0065)  # closed lids, convex
    r += 0.0045 * lens(x, z, 0.031, 0.0, 0.021, 0.0065)
    r -= 0.0025 * lens(x, z, -0.031, 0.0, 0.026, 0.0095)  # almond sockets around the lids
    r -= 0.0025 * lens(x, z, 0.031, 0.0, 0.026, 0.0095)
    r -= 0.0018 * gauss(z, 0.010, 0.0025) * gauss(abs(x), 0.031, 0.020)  # lid crease
    r += 0.014 * gauss(abs(x), 0.036, 0.024) * gauss(z, 0.040, 0.011)  # brow ridge (2x)
    r += 0.012 * gauss(abs(x), 0.058, 0.03) * gauss(z, -0.02, 0.040)  # cheekbones (2x)
    r += 0.005 * gauss(x, 0, 0.03) * gauss(z, -0.112, 0.02)  # chin
    r += 0.002 * gauss(x, 0, 0.014) * gauss(z, -0.084, 0.006)  # lower lip
    r -= 0.003 * gauss(x, 0, 0.014) * gauss(z, -0.074 - 0.004 * (x / 0.016) ** 2, 0.0022)  # closed mouth line
    return r


def face_y(x, z):
    """Front surface y of the mask at face coords x, z, relief included (matches mask())."""
    y = -0.097 * math.sqrt(max(0.0, 1 - (x / 0.085) ** 2 - (z / 0.125) ** 2))
    return y - face_relief(x, z) * min(1.0, -y / 0.05)


def mask_lines():
    """Dark carved lines in the mask grooves: closed-eye almonds and the mouth (material docent_glove)."""
    parts = []
    for side, cx in (("L", -0.031), ("R", 0.031)):
        pts = []
        for k in range(24):
            t = 2 * math.pi * k / 24
            x, z = cx + 0.021 * math.cos(t), 0.0065 * math.sin(t)
            pts.append(V(x, face_y(x, z) - 0.0012, z) + HEADC)
        parts.append(ring_tube("lid_" + side, pts, 0.0011, GLOVE_M, 6, up=(0, -1, 0)))
    mouth = []
    for k in range(25):
        x = -0.016 + 0.032 * k / 24
        z = -0.074 - 0.004 * (x / 0.016) ** 2
        mouth.append(V(x, face_y(x, z) - 0.0012, z) + HEADC)
    parts.append(sweep("mouth_line", mouth, [0.0011] * len(mouth), 6, GLOVE_M, up=(0, -1, 0)))
    return parts


def mask():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=56, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co.x * 0.085, v.co.y * 0.097, v.co.z * 0.125
        if y < 0:
            y -= face_relief(x, z) * min(1.0, -y / 0.05)
        v.co = (x, y, z)
    bmesh.ops.translate(bm, vec=HEADC, verts=bm.verts)
    return kit._obj("mask", bm, PORC_M, 50.0)


VEIL_Z = [0.15, 0.14, 0.125, 0.10, 0.06, 0.02, -0.02, -0.07, -0.11, -0.13, -0.16, -0.19, -0.23]


def veil_radii(z):
    """Cloth around the head: the skull ellipsoid plus thickness, then dropping over the shoulders."""
    if z > -0.11:
        sc = math.sqrt(max(0.0, 1 - (z / 0.155) ** 2))
        return 0.095 * sc + 0.02, 0.107 * sc + 0.02
    t = smooth((-0.11 - z) / 0.12)
    r = 0.075 + 0.085 * t
    return r, r * 1.08


def veil():
    """Double-skinned cloth (outer face, dark inner face, thickness wall on the window edge)."""
    bm = bmesh.new()
    N = 120
    T = 0.006  # cloth thickness
    outer, inner, pairs = [], [], {}
    for z in VEIL_Z:
        rx, ry = veil_radii(z)
        fa = 0.3 + 0.7 * smooth((0.0 - z) / 0.2)  # folds grow towards the shoulders
        ro, ri = [], []
        for i in range(N):
            a = 2 * math.pi * i / N
            m = 1 + 0.02 * fa * math.sin(14 * a) + 0.045 * fa * math.sin(4 * a + 0.4)  # 4 soft folds
            vo = bm.verts.new(HEADC + V(math.cos(a) * rx * m, math.sin(a) * ry * m, z))
            vi = bm.verts.new(HEADC + V(math.cos(a) * (rx * m - T), math.sin(a) * (ry * m - T), z))
            ro.append(vo)
            ri.append(vi)
            pairs[vo] = vi
        outer.append(ro)
        inner.append(ri)
    of, inf = [], []
    for j in range(len(outer) - 1):
        for i in range(N):
            of.append(bm.faces.new((outer[j][i], outer[j][(i + 1) % N], outer[j + 1][(i + 1) % N], outer[j + 1][i])))
            inf.append(bm.faces.new((inner[j][i], inner[j + 1][i], inner[j + 1][(i + 1) % N], inner[j][(i + 1) % N])))
    of.append(bm.faces.new(outer[0]))  # crown
    inf.append(bm.faces.new(inner[0]))
    bmesh.ops.recalc_face_normals(bm, faces=of)
    bmesh.ops.recalc_face_normals(bm, faces=inf)
    bmesh.ops.reverse_faces(bm, faces=inf)  # inner skin faces back towards the head
    # open a window for the face: below the hairline, above the chin, on the front
    gone = []
    for f in bm.faces:
        c = f.calc_center_median() - HEADC
        if c.y < -0.02 and abs(c.x) < 0.10 and -0.14 <= c.z <= 0.075:
            gone.append(f)
    bmesh.ops.delete(bm, geom=gone, context="FACES_ONLY")
    # thickness: wall the open edges between the outer and inner skins
    for e in [e for e in bm.edges if len(e.link_faces) == 1]:
        a, b = e.verts
        if a in pairs and b in pairs and pairs[a].is_valid and pairs[b].is_valid:
            bm.faces.new((a, b, pairs[b], pairs[a]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj("veil", bm, ROBE_M, 60.0)


def bell(name, pts, radii, sides=16, mat=None, fold=0.0, nfold=0, T=0.005):
    """Open-ended sleeve: an outer skin and an inner skin T apart, joined by a rim at the cuff.
    The bore stays open at the cuff; the top is closed inside the shoulder."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    U = Vector((0, 0, 1))
    outer, inner = [], []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        u = U - d * U.dot(d)
        if u.length < 1e-4:
            u = Vector((1, 0, 0)) - d * d.x
        u.normalize()
        x = d.cross(u).normalized()
        ro, ri = [], []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            m = 1.0 + fold * math.sin(nfold * a) if nfold else 1.0
            dv = x * math.cos(a) + u * math.sin(a)
            ro.append(bm.verts.new(p + dv * radii[i] * m))
            ri.append(bm.verts.new(p + dv * (radii[i] * m - T)))
        outer.append(ro)
        inner.append(ri)
    last = len(P) - 1
    for i in range(last):
        for k in range(sides):
            k1 = (k + 1) % sides
            bm.faces.new((outer[i][k], outer[i + 1][k], outer[i + 1][k1], outer[i][k1]))
            bm.faces.new((inner[i][k], inner[i][k1], inner[i + 1][k1], inner[i + 1][k]))
    for ro, ri in ((outer[0], inner[0]), (outer[last], inner[last])):
        for k in range(sides):
            k1 = (k + 1) % sides
            bm.faces.new((ro[k], ro[k1], ri[k1], ri[k]))
    bm.faces.new(outer[0])  # shoulder end closed
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 45.0)


def neck():
    return sweep("neck", [V(0, -0.005, 1.93), V(0, -0.005, 2.00), V(0, -0.005, 2.07)],
                 [0.068, 0.052, 0.055], 14, PORC_M)


def arm(s, name):
    """Arm on side s (+1 = figure's left, -1 = right). Origin at the shoulder joint."""
    S, E, W = SHOULDER[s], V(s * 0.25, -0.12, 1.45), (W_L if s > 0 else W_R)
    f = (W - E).normalized()
    sleeve = bell(name + "_sleeve", [
        S, S.lerp(E, 0.5), E, E.lerp(W, 0.5), W - f * 0.03,
        W + V(0, 0, -0.06), W + V(0, 0, -0.11), W + V(0, 0, -0.16), W + V(0, 0, -0.22)],
        [0.095, 0.10, 0.078, 0.07, 0.04, 0.04, 0.07, 0.09, 0.11], 16, ROBE_M, fold=0.07, nfold=9)  # narrow cuff: hands show
    parts = [sleeve]
    for k, ang in enumerate((-0.45, 0.0, 0.45)):  # 3 drape folds hanging under the forearm
        dn = Matrix.Rotation(ang, 3, f) @ V(0, 0, -1)
        fpts = [E.lerp(W, t) + dn * 0.062 + V(0, 0, -0.012 * math.sin(math.pi * t)) for t in (0.15, 0.4, 0.65, 0.9)]
        parts.append(sweep(name + "_fold%d" % k, fpts, [0.009] * 4, 6, ROBE_M))
    cz = W.z - 0.22  # gilt cuff: short open cylinder on the outer rim, 3 cm tall, 4 mm thick
    parts.append(bake(kit.lathe(name + "_cuff", [(0.12, cz), (0.124, cz), (0.124, cz + 0.03), (0.12, cz + 0.03)],
                                40, mat="gilt", smooth_angle=60.0, cap=False), Matrix.Translation((W.x, W.y, 0))))
    G = BOARD_M @ V(s * 0.22, 0.0, 0.02 if s > 0 else 0.06)  # grip on the board's side edge, mid-plate
    parts += hand(s, W, G)
    ob = kit.join(name, parts)
    subsurf(ob, 1)
    return pivot(ob, S)


def hand(s, W, G):
    """Grip on the board's side edge at G (board-local x = s*0.22). Built in board-local coords and placed
    with BOARD_M. Palm wraps the edge; four tapered fingers lie behind the back face (+Y); the thumb wraps
    the edge and lies flat on the front face (-Y), about 4 mm off the sheet, pointing at the board centre."""
    K = 1.3  # hands ~30% larger so the grip on the board reads at 3 m
    inv = BOARD_M.inverted()
    wl, gl = inv @ W, inv @ G
    zw, zg = wl.z, gl.z
    N = BOARD_ROT @ V(0, 1, 0)  # board normal: flat sweeps lie in the board plane

    def B(x, y, z):
        return BOARD_M @ V(x, y, z)

    # palm: flattened, from the wrist to the edge (its end cap just clears the board edge at x = 0.22)
    parts = [sweep("palm", [B(wl.x, 0.004, zw), B(s * 0.245, 0.0, (zw + zg) / 2), B(s * 0.2225, 0.0, zg)],
                   [0.03 * K, 0.034 * K, 0.036 * K], 10, GLOVE_M, flat=0.5, up=N)]
    # fingers: behind the back face (y = +0.010), centre 26 mm off it, stacked along the edge
    for i in range(4):
        z = zg + (i - 1.5) * 0.026
        pts = [B(s * 0.236, 0.026, z), B(s * 0.20, 0.026, z), B(s * 0.165, 0.026, z), B(s * 0.135, 0.026, z)]
        parts.append(sweep("finger%d" % i, pts, [r * K for r in (0.0105, 0.0098, 0.0088, 0.0055)], 8, GLOVE_M,
                           flat=0.8, up=N))
    # thumb: round the edge, then flat on the front; centre 23 mm in front of the board plate (-0.0231),
    # half-thickness ~6.8 mm at the base, so the inner face sits ~4 mm off the sheet (front at -0.0125)
    thumb = [B(s * 0.24, -0.004, zg), B(s * 0.23, -0.018, zg), B(s * 0.20, -0.0231, zg),
             B(s * 0.165, -0.0231, zg), B(s * 0.158, -0.0231, zg)]
    parts.append(sweep("thumb", thumb, [r * K for r in (0.0095, 0.0092, 0.0085, 0.0070, 0.0040)], 8, GLOVE_M,
                       flat=0.55, up=N))
    return parts


def band(name, pts, mat, hw=0.03, ht=0.0055, sides=10):
    """Velvet band with rounded edges swept along pts: width lies across the body, thickness out of it."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        n = Vector((p.x, p.y, 0)).normalized()
        n = (n - d * n.dot(d)).normalized()
        w = d.cross(n).normalized()
        rings.append([bm.verts.new(p + w * hw * math.cos(2 * math.pi * k / sides) + n * ht * math.sin(2 * math.pi * k / sides))
                      for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 60.0)


def stole():
    """One continuous velvet band: chest-left, over the left shoulder, behind the neck, over the right
    shoulder, down chest-right. Each point is sampled from the robe surface and pushed 1.8 cm out."""
    def drop(z, x):  # front angle on the robe at height z for chest offset x
        return -math.acos(max(-0.999, min(0.999, x / rxry(z)[0])))
    keys = [(1.40, drop(1.40, 0.08)), (1.60, drop(1.60, 0.085)), (1.80, drop(1.80, 0.10)),
            (1.94, -0.75), (1.94, -0.15), (1.94, 0.45), (1.94, 1.05), (1.94, 1.65), (1.94, 2.25),
            (1.94, 2.85), (1.94, 3.45), (1.94, 3.85),
            (1.80, 2 * math.pi + drop(1.80, -0.10)), (1.60, 2 * math.pi + drop(1.60, -0.085)),
            (1.40, 2 * math.pi + drop(1.40, -0.08))]
    pts = []
    for (z0, a0), (z1, a1) in zip(keys, keys[1:]):
        for k in range(4):
            t = k / 4
            z, a = z0 + (z1 - z0) * t, a0 + (a1 - a0) * t
            pts.append(robe_pt(z, a) + V(math.cos(a), math.sin(a), 0) * 0.018)
    z, a = keys[-1]
    pts.append(robe_pt(z, a) + V(math.cos(a), math.sin(a), 0) * 0.018)
    return band("stole", pts, "velvet", hw=0.045, ht=0.006)


def build(args):
    parts = [robe()]
    # belt: a velvet cord at the waist, the folds pull down from it
    parts.append(ring_tube("belt", [outward(robe_pt(1.40, 2 * math.pi * i / 96), 0.012) for i in range(96)],
                           0.02, GLOVE_M))  # dark leather cinch
    # gilt hem band on the floor and a rolled hem
    parts.append(ring_tube("hem", [outward(robe_pt(0.035, 2 * math.pi * i / 120), 0.006) for i in range(120)],
                           0.0095, "gilt"))
    parts.append(kit.lathe("collar", [(0.095, 1.955), (0.11, 1.965), (0.118, 1.975), (0.11, 1.985), (0.09, 1.99)],
                           40, mat="gilt", cap=False))
    parts.append(stole())
    parts.append(kit.lathe("badge", [(0.0, 0.0), (0.036, 0.0), (0.04, 0.003), (0.036, 0.007), (0.0, 0.007)],
                           28, mat="brass"))
    badge_o = front_pt(1.62, 0, 0.0)
    parts[-1] = bake(parts[-1], frame(badge_o, (0, -1, 0)))
    parts.append(sweep("lanyard", [front_pt(1.93, 0, 0.004), front_pt(1.80, 0, 0.006),
                                   front_pt(1.70, 0, 0.006), front_pt(1.64, 0, 0.006)],
                       [0.0045] * 4, 6, "velvet"))
    docent = pivot(kit.join("docent", parts), (0, 0, 0))

    arm_l = arm(1, "arm_L")
    arm_r = arm(-1, "arm_R")

    head_ob = kit.join("head", [mask(), veil(), neck()] + mask_lines())
    pivot(head_ob, HEAD_PIVOT)

    board = _board()
    pencil = _pencil()
    coll = kit.box("docent-convcolonly", (0.8, 0.7, 2.3), (0, 0, 1.15))

    for ob in (docent, head_ob, arm_l, arm_r, board, pencil, coll):
        print("OBJECT %-22s origin=(%.3f, %.3f, %.3f)" % (ob.name, *ob.location))
    return None


def _board():
    plate = kit.box("bd_plate", (0.44, 0.02, 0.36), (0, 0, 0), mat="ebony", bevel=0.006, segments=2)
    sheet = kit.box("bd_sheet", (0.41, 0.002, 0.33), (0, -0.0115, 0), mat="sketch_paper", bevel=0.0008, segments=1)
    clip = kit.box("bd_clip", (0.12, 0.035, 0.05), (0, 0.0, 0.18), mat="brass", bevel=0.012, segments=3)
    parts = [bake(p, BOARD_M) for p in (plate, sheet, clip)]
    return pivot(kit.join("board", parts), BOARD_C)


def _pencil():
    T = SHEET_TIP
    parts = [
        kit.lathe("pen_lead", [(0.0, 0.0), (0.0009, 0.004), (0.0009, 0.012)], 6, mat="ebony", cap=False),
        kit.lathe("pen_wood", [(0.0013, 0.012), (0.0075, 0.028)], 6, mat="sketch_paper", cap=False),
        kit.lathe("pen_body", [(0.0075, 0.028), (0.0075, 0.15)], 6, mat="ebony", cap=False),
        kit.lathe("pen_ferrule", [(0.0082, 0.15), (0.0082, 0.165)], 12, mat="brass"),
    ]
    for p in parts:
        bake(p, frame(T, PENCIL_U))
    return pivot(kit.join("pencil", parts), PENCIL_G)
