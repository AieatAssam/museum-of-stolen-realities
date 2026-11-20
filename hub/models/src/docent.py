"""Docent-construct: a museum attendant, 2.3 m tall (on purpose a little too tall). The figure is carried by
cloth simulated with Blender's cloth solver (drape.py) over a hidden collision body, then applied and given
thickness:
  - a floor-length robe, held at the shoulders and cinched at the belt, pooling a little on the floor,
  - a velvet mantle over the shoulders and the tops of the sleeves,
  - wide sleeves held at the shoulder and the top of the wrist, so the bell of each hangs under the forearm,
  - a linen veil dropped over the whole head: the porcelain face is only read through the cloth (the mask is
    the collider the veil settles on), like a veiled statue.
The figure cradles a sketchboard in both gloved hands, pencil in the right (figure's right = -X; faces -Y).

Pivots (Godot animates these by name):
  docent  static body (robe, mantle, belt); origin at the floor centre
  head    veil (and the mask under it); origin at the neck pivot
  arm_L   origin at the left shoulder joint (+X);  arm_R origin at the right shoulder joint (-X)
  board   sketchboard with clip and sheet; origin at the board centre
  pencil  pencil; origin at the grip point
  docent-convcolonly  invisible convex collider
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

ROBE_M = "docent_robe"
PORC_M = "docent_porcelain"
GLOVE_M = "docent_glove"
VEIL_M = "docent_veil"
MANTLE_M = "velvet"

HEADC = Vector((0.0, -0.005, 2.165))  # centre of the mask
HEAD_PIVOT = (0.0, -0.005, 2.0)  # neck pivot
SHOULDER = {1: Vector((0.205, 0.0, 1.855)), -1: Vector((-0.205, 0.0, 1.855))}  # +1 = figure's left
BELT = 1.40

BOARD_C = Vector((0.0, -0.36, 1.27))
BOARD_ROT = Matrix.Rotation(math.radians(-38), 4, "X")
BOARD_M = Matrix.Translation(BOARD_C) @ BOARD_ROT
W_R = Vector((-0.30, -0.30, 1.10))  # right wrist: the hand cups the board's lower right edge
W_L = Vector((0.30, -0.30, 1.10))  # left wrist: the hand cups the board's lower left edge
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

def mask():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=56, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co.x * 0.098, v.co.y * 0.108, v.co.z * 0.13
        if y < 0:
            y -= face_relief(x, z) * min(1.0, -y / 0.05)
        v.co = (x, y, z)
    bmesh.ops.translate(bm, vec=HEADC, verts=bm.verts)
    return kit._obj("mask", bm, PORC_M, 50.0)

def hand(s, W, G):
    """Gloved grip on the board edge: kit.hand in a 'grip' pose, wrist at W, fingers aimed at the grip point G,
    thumb toward the board's front face (-Y board side). The basis is built so the hand's thumb side (s*X)
    lies along the front normal and the palm faces the edge."""
    Yh = (G - W).normalized()
    T = (BOARD_ROT @ V(0, -1, 0))
    T = (T - Yh * T.dot(Yh)).normalized()
    Zh = (-s * Yh.cross(T)).normalized()  # back of the hand
    Xh = Yh.cross(Zh)
    M = Matrix.Translation(W) @ Matrix((Xh, Yh, Zh)).transposed().to_4x4()
    return bake(kit.hand(s, "hold", 1.0, "hand_L" if s > 0 else "hand_R", mat=GLOVE_M), M)

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


# ---------------------------------------------------------------- hidden body and rest shapes

def torso_depth(co):
    trunk = gauss(co.x, 0.0, 0.17) * smooth((co.z - 1.15) / 0.12) * smooth((1.95 - co.z) / 0.06)
    return 1.0 - 0.3 * trunk


def body():
    N = [(V(0, 0, 1.30), 0.19), (V(0, 0, BELT), 0.15), (V(0, -0.005, 1.62), 0.17), (V(0, 0, 1.78), 0.165),
         (V(0, -0.005, 1.95), 0.062), (V(0, -0.005, 2.06), 0.055), (SHOULDER[1], 0.065), (SHOULDER[-1], 0.065),
         (V(0.10, 0, 1.18), 0.12), (V(0.11, 0, 0.65), 0.08), (V(0.11, 0, 0.08), 0.06),
         (V(-0.10, 0, 1.18), 0.12), (V(-0.11, 0, 0.65), 0.08), (V(-0.11, 0, 0.08), 0.06)]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (3, 6), (3, 7), (0, 8), (8, 9), (9, 10), (0, 11), (11, 12), (12, 13)]
    return drape.skin_graph("coll_body", N, E, ROBE_M, flatten=torso_depth)


def arm_path(s):
    S, E, W = SHOULDER[s], V(s * 0.25, -0.12, 1.45), (W_L if s > 0 else W_R)
    return [S, S.lerp(E, 0.5), E, E.lerp(W, 0.5), W]


def _lerp_table(T, z):
    for (z0, *a), (z1, *b) in zip(T, T[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return [x + (y - x) * t for x, y in zip(a, b)]
    return list(T[0][1:]) if z > T[0][0] else list(T[-1][1:])


def rings_from(T, z0, z1, step, ns, noise=None):
    rings = []
    for k in range(int((z0 - z1) / step) + 1):
        z = z0 - k * step
        rx, ry = _lerp_table(T, z)
        ring = []
        for i in range(ns):
            u = 2 * math.pi * i / ns
            m = noise(z, u) if noise else 1.0
            ring.append((rx * m * math.cos(u), ry * m * math.sin(u), z))
        rings.append(ring)
    return rings


ROBE_T = [(2.0, 0.065, 0.06), (1.96, 0.12, 0.09), (1.92, 0.21, 0.12), (1.86, 0.245, 0.135), (1.75, 0.235, 0.15),
          (1.62, 0.22, 0.155), (BELT, 0.19, 0.15), (1.30, 0.27, 0.22), (0.90, 0.35, 0.29), (0.02, 0.45, 0.39)]
# the mantle's fitted collar; below it the cloth lies over the robe and sleeves (drape.envelope)
MANTLE_COLLAR = [(2.0, 0.075, 0.068), (1.97, 0.14, 0.105), (1.95, 0.18, 0.125)]


def mantle_hem(u):
    """The mantle falls in a curve: short over the arms, dipping low at the breast and between the shoulder
    blades."""
    return 1.67 - 0.14 * abs(math.sin(u)) ** 1.5 + 0.006 * math.sin(7 * u + 1.1)


def robe():
    rnd = random.Random(3)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]

    def noise(z, u):
        free = smooth((BELT - 0.04 - z) / 0.4)
        return 1.0 + free * (0.04 * math.sin(3 * u + ph[0]) + 0.03 * math.sin(5 * u + ph[1]) +
                             0.02 * math.sin(8 * u + ph[2]))
    return drape.grid_tube("robe", rings_from(ROBE_T, 2.0, 0.02, 0.022, 120, noise))


def sleeve(s):
    P = arm_path(s)
    P = [P[0].lerp(P[1], 0.4)] + P[1:]
    pts = []
    for a, b in zip(P, P[1:]):
        pts += [a.lerp(b, t / 5) for t in range(5)]
    pts.append(P[-1])
    NS, n = 40, len(pts)
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        x = d.cross(Vector((0, 0, 1)))
        x = (x if x.length > 1e-3 else d.cross(Vector((1, 0, 0)))).normalized()
        up = x.cross(d).normalized()
        t = i / (n - 1)
        r = 0.085 + 0.05 * t ** 2  # widening toward the wrist
        rings.append([tuple(p + (x * math.cos(a) + up * math.sin(a)) * r) for a in (2 * math.pi * k / NS for k in range(NS))])
    ob = drape.grid_tube("sleeve", rings)
    start, wrist = pts[0], pts[-1]

    def pin(co):
        if (co - start).length < 0.1:
            return 1.0
        return 1.0 if (co - wrist).length < 0.09 and co.z > wrist.z + 0.03 else 0.0
    return ob, pin


def veil():
    """Rest shape: the head pushed out, closed over the crown; from the brow line it falls straight to the shoulders
    (a bridal veil, not a hood): it settles onto the face relief and hangs from the chin."""
    NU = 80
    R = (0.098 + 0.025, 0.108 + 0.025, 0.13 + 0.025)
    rows = [[tuple(HEADC + Vector((R[0] * math.cos(math.radians(lat)) * math.cos(2 * math.pi * k / NU),
                                   R[1] * math.cos(math.radians(lat)) * math.sin(2 * math.pi * k / NU),
                                   R[2] * math.sin(math.radians(lat))))) for k in range(NU)]
            for lat in range(84, -20, -8)]
    last = [Vector(p) for p in rows[-1]]
    for j, (zt, r) in enumerate([(2.07, 0.15), (2.02, 0.18), (1.98, 0.22), (1.94, 0.26), (1.91, 0.29)]):
        t = (j + 1) / 5.0
        rows.append([tuple(last[k].lerp(Vector((r * math.cos(2 * math.pi * k / NU),
                                                 r * 0.95 * math.sin(2 * math.pi * k / NU), zt)), t)) for k in range(NU)])
    ob = drape.grid_tube("veil", rows)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    top = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > HEADC.z + 0.1]
    bmesh.ops.triangle_fill(bm, edges=top, use_beauty=True)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def finish_cloth(ob, thick, mat, levels=0):
    ob.data.materials.clear()
    ob.data.materials.append(kit.material(mat))
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thick
    m.offset = 0.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    ob.select_set(False)
    if levels:
        subsurf(ob, levels)
    for f in ob.data.polygons:
        f.use_smooth = True
    return ob


# ---------------------------------------------------------------- build

def build(args):
    bodyc = body()
    floor = kit.box("coll_floor", (3, 3, 0.02), (0, 0, -0.01))
    head_c = mask()
    # 1. robe to the floor, held at the shoulders and the belt
    rb = drape.simulate(robe(), [bodyc, floor], lambda co: 1.0 if co.z > 1.84 or abs(co.z - BELT) < 0.02 else 0.0,
                        frames=120, tension=14, bending=1.0)
    # 2. sleeves
    sleeves = {}
    for s in (1, -1):
        ob, pin = sleeve(s)
        sleeves[s] = drape.simulate(ob, [], pin, frames=60, tension=10, bending=0.5,
                                    self_collision=False)
    # 3. mantle over robe and sleeves
    mt = drape.envelope("mantle", [rb, sleeves[1], sleeves[-1]], MANTLE_COLLAR, mantle_hem, gap=0.016, fold=0.018,
                        hang=0.8, shoulder=0.1)
    # 4. veil over the head, settling on the mask and the mantle collar
    vl = drape.simulate(veil(), [head_c, mt, bodyc], lambda co: 1.0 if co.z > HEADC.z + 0.15 else 0.0,
                        frames=70, tension=20, bending=0.6)
    for o in [bodyc, floor, head_c]:
        bpy.data.objects.remove(o, do_unlink=True)
    finish_cloth(rb, 0.008, ROBE_M)
    finish_cloth(mt, 0.008, MANTLE_M)
    finish_cloth(vl, 0.004, VEIL_M, 1)
    for s in (1, -1):
        finish_cloth(sleeves[s], 0.006, ROBE_M)
    rx, ry = _lerp_table(ROBE_T, BELT)
    belt = ring_tube("belt", [V(rx * 1.07 * math.cos(2 * math.pi * i / 96), ry * 1.09 * math.sin(2 * math.pi * i / 96), BELT)
                              for i in range(96)], 0.018, GLOVE_M)
    knot = [V(0.05, -ry * 1.09 - 0.01, BELT), V(0.06, -ry * 1.12 - 0.02, BELT - 0.15), V(0.075, -ry * 1.1 - 0.03, BELT - 0.32)]
    cord = sweep("cord", knot, [0.014, 0.012, 0.01], 8, GLOVE_M)
    docent = pivot(kit.join("docent", [rb, mt, belt, cord]), (0, 0, 0))

    arms = {}
    for s, name in ((1, "arm_L"), (-1, "arm_R")):
        W = W_L if s > 0 else W_R
        G = BOARD_M @ V(s * 0.23, 0.0, -0.13)  # lower side edge: fingers under it, thumb on the front
        E = V(s * 0.25, -0.12, 1.45)
        fore = sweep(name + "_fore", [E, W], [0.05, 0.04], 10, ROBE_M)
        arms[s] = pivot(kit.join(name, [sleeves[s], fore, hand(s, W, G)]), SHOULDER[s])
    head_ob = pivot(kit.join("head", [vl]), HEAD_PIVOT)
    board = _board()
    pencil = _pencil()
    coll = kit.box("docent-convcolonly", (0.8, 0.7, 2.3), (0, 0, 1.15))
    for ob in (docent, head_ob, arms[1], arms[-1], board, pencil, coll):
        print("OBJECT %-22s origin=(%.3f, %.3f, %.3f)" % (ob.name, *ob.location))
