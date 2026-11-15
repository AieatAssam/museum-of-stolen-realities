"""Docent-construct: a faceless, slightly too-tall plaster figure (2.3 m) in a pleated floor-length robe
with a velvet stole, gilt collar, sleeve trims and hem, a brass badge on a lanyard, cradling a
sketchboard with a pencil in the right hand (figure's right = -X, the figure faces -Y).

Split into objects with pivots so the figure can be animated in code:
  docent  static body (robe, stole, collar, hem, lanyard, badge, neck); origin at the floor centre
  head    faceless mannequin head; origin at the neck pivot
  arm_L   origin at the left shoulder joint;  arm_R origin at the right shoulder joint
  board   sketchboard with clip and sheet; origin at the board centre
  pencil  hexagonal pencil; origin at the grip point
  docent-convcolonly  invisible convex collider
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

NPLEAT = 20  # deep vertical pleats on the robe skirt
NSEG = 80  # 4 segments per pleat, creases land exactly on vertices
# robe section (z, half-width x, half-depth y): hem flare, waist pinch, bust, shoulders
ROBE = [(0.00, 0.40, 0.34), (0.12, 0.385, 0.325), (0.35, 0.355, 0.28), (0.70, 0.31, 0.235),
        (0.95, 0.262, 0.195), (1.08, 0.236, 0.178), (1.22, 0.255, 0.186), (1.40, 0.28, 0.20),
        (1.55, 0.305, 0.20), (1.67, 0.322, 0.185), (1.77, 0.332, 0.165), (1.85, 0.29, 0.13),
        (1.91, 0.18, 0.105), (1.95, 0.10, 0.09)]
HEAD_PIVOT = (0.0, -0.02, 1.97)


def V(*a):
    return Vector(a)


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def gauss(v, c, s):
    return math.exp(-((v - c) / s) ** 2)


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


def rxry(z):
    if z <= ROBE[0][0]:
        return ROBE[0][1], ROBE[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(ROBE, ROBE[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return ROBE[-1][1], ROBE[-1][2]


def robe_pt(z, a):
    rx, ry = rxry(z)
    c, s = math.cos(a), math.sin(a)
    front, back = max(0.0, -s), max(0.0, s)
    bust = 1 + 0.10 * gauss(z, 1.52, 0.13) * front * front  # bust, front only
    blade = 1 + 0.06 * gauss(z, 1.60, 0.10) * back * back  # shoulder blades, back only
    amp = 0.11 * smooth((1.14 - z) / 0.2)  # pleats run from the hem and stop at the waist
    fold = abs(math.sin(NPLEAT * a / 2))  # 0 at each crease
    pleat = 1 - amp * (1 - fold ** 0.6)
    lean = -0.02 * (z / 1.95) ** 2  # the whole figure leans slightly forward
    return Vector((c * rx * pleat, s * ry * pleat * bust * blade + lean, z))


def front_pt(z, x, out=0.012):
    """A point on the robe's front surface at height z and x offset, pushed out by `out`."""
    rx, _ = rxry(z)
    c = max(-0.999, min(0.999, x / rx))
    a = -math.acos(c)
    p = robe_pt(z, a)
    return p + Vector((math.cos(a), math.sin(a), 0)) * out


def robe():
    zs = []
    for (z0, _, _), (z1, _, _) in zip(ROBE, ROBE[1:]):
        zs += [z0, z0 + (z1 - z0) / 2]
    zs.append(ROBE[-1][0])
    bm = bmesh.new()
    rows = []
    for z in zs:
        rows.append([bm.verts.new(robe_pt(z, 2 * math.pi * i / NSEG)) for i in range(NSEG)])
    for j in range(len(rows) - 1):
        for i in range(NSEG):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % NSEG], rows[j + 1][(i + 1) % NSEG], rows[j + 1][i]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj("robe", bm, "plaster", 60.0)


def docent_face(x, y, z):
    """Faceless: a brow ridge, a soft nose ridge, cheek planes, ear bumps and a jaw line."""
    dx = dy = 0.0
    ax = abs(x)
    sx = 1.0 if x >= 0 else -1.0
    w = gauss(x, 0, 0.05) * gauss(z, 0.2, 0.022)  # brow ridge
    if y < 0:
        dy -= 0.012 * w
    w = gauss(x, 0, 0.011) * gauss(z, 0.13, 0.05)  # nose ridge
    if y < 0:
        dy -= 0.02 * w
    w = gauss(ax, 0.06, 0.025) * gauss(z, 0.1, 0.04)  # cheek planes
    dx += sx * 0.006 * w
    if y < 0:
        dy -= 0.004 * w
    w = gauss(ax, 0.078, 0.013) * gauss(y, 0.0, 0.03) * gauss(z, 0.14, 0.035)  # ears
    dx += sx * 0.012 * w
    w = gauss(z, 0.03, 0.03) * min(ax / 0.06, 1.0)  # jaw line
    dx += sx * 0.003 * w
    w = gauss(x, 0, 0.035) * gauss(z, -0.01, 0.03)  # chin
    if y < 0:
        dy -= 0.006 * w
    return dx, dy, 0.0


def head():
    prof = densify([(0.0, -0.035), (0.04, -0.035), (0.05, -0.012), (0.066, 0.03), (0.08, 0.07),
                    (0.09, 0.11), (0.093, 0.16), (0.088, 0.21), (0.075, 0.26), (0.05, 0.305),
                    (0.02, 0.33), (0.0, 0.335)], 2)
    ob = kit.lathe("head", prof, 36, mat="plaster", smooth_angle=80.0)
    bake(ob, Matrix.Diagonal((0.85, 1.1, 1.0, 1.0)))
    sculpt(ob, docent_face)
    subsurf(ob, 1)
    ob.location = Vector(HEAD_PIVOT)  # built around its own origin (the neck pivot)
    return ob


def arm(s, name):
    """Arm on side s (-1 = figure's right, +1 = left). Origin at the shoulder joint."""
    sh = V(s * 0.33, 0.0, 1.72)
    el = V(s * 0.37, -0.09, 1.36)
    wr = V(s * 0.2, -0.34, 1.26)
    d = (wr - el).normalized()
    up = V(0, 0, 1)
    lat = d.cross(up).normalized()
    inner = V(-s, 0, 0)
    parts = [orn.taper(name + "_fore", [sh, sh.lerp(el, 0.5) + V(0, -0.02, 0), el,
                                       el.lerp(wr, 0.5) + V(0, -0.03, 0), wr],
                       [0.06, 0.052, 0.043, 0.035, 0.03], 10, "plaster")]
    parts.append(orn.taper(name + "_palm", [wr, wr + d * 0.04, wr + d * 0.085], [0.03, 0.036, 0.03],
                           10, "plaster", flat=0.5, up=(0, 0, 1)))
    for k, (off, L) in enumerate(zip([-0.024, -0.008, 0.008, 0.024], [0.07, 0.08, 0.08, 0.065])):
        K = wr + d * 0.075 + lat * off
        parts.append(orn.taper("%s_f%d" % (name, k), [K, K + d * 0.03, K + d * (L * 0.7) + up * 0.012,
                                                      K + d * L + up * 0.026],
                               [0.0105, 0.0095, 0.0085, 0.007], 6, "plaster"))
    parts.append(orn.taper(name + "_thumb", [wr + d * 0.02 + inner * 0.01, wr + d * 0.05 + inner * 0.03 + up * 0.01,
                                             wr + d * 0.085 + inner * 0.045 + up * 0.02],
                           [0.013, 0.012, 0.009], 6, "plaster"))
    cuff = kit.lathe(name + "_cuff", [(0.034, 0.0), (0.042, 0.006), (0.042, 0.014), (0.034, 0.02)], 24, mat="gilt")
    parts.append(bake(cuff, frame(wr - d * 0.02, d)))
    return pivot(kit.join(name, parts), sh)


def build(args):
    parts = []
    robe_ob = subsurf(robe(), 1)
    parts.append(robe_ob)
    parts.append(orn.taper("neck", [V(0, -0.02, 1.86), V(0, -0.02, 1.93), V(0, -0.02, 1.98)],
                           [0.06, 0.052, 0.05], 12, "plaster"))
    parts.append(kit.lathe("collar", [(0.098, 1.93), (0.112, 1.945), (0.118, 1.955), (0.11, 1.968),
                                      (0.09, 1.972)], 40, mat="gilt", cap=False))
    # sleeve openings at the shoulders, gilt rim at each mouth
    for s in (-1, 1):
        sh = V(s * 0.33, 0.0, 1.72)
        d = (V(s * 0.37, -0.09, 1.36) - sh).normalized()
        mouth = kit.lathe("mouth", [(0.068, 0.0), (0.082, 0.02), (0.086, 0.045), (0.076, 0.062)], 32,
                          mat="plaster", cap=False)
        parts.append(bake(mouth, frame(sh - d * 0.03, d)))
        rim = kit.torus("rim", 1.0, 0.006, 40, 6, mat="gilt")
        parts.append(bake(rim, Matrix.Diagonal((0.078, 0.078, 0.078, 1.0)) @ frame(sh + d * 0.03, d)))
    # velvet stole over the shoulders, falling in two bands down the front
    for s in (-1, 1):
        pts = [V(s * 0.22, 0.02, 1.87), V(s * 0.25, -0.02, 1.82), front_pt(1.7, s * 0.17, 0.02),
               front_pt(1.45, s * 0.15, 0.02), front_pt(1.15, s * 0.14, 0.02), front_pt(0.9, s * 0.15, 0.02),
               front_pt(0.7, s * 0.16, 0.02)]
        parts.append(orn.taper("stole%d" % s, pts, [0.05, 0.06, 0.065, 0.068, 0.068, 0.068, 0.066], 8,
                               "velvet", flat=0.18, up=(0, -1, 0)))
        parts.append(orn.taper("stole_trim%d" % s, [front_pt(0.72, s * 0.16, 0.02), front_pt(0.69, s * 0.16, 0.02)],
                               [0.069, 0.069], 8, "gilt", flat=0.2, up=(0, -1, 0)))
    # gilt hem band on the floor and a velvet lanyard with a brass medallion
    hem = kit.torus("hem", 1.0, 0.014, 72, 8, mat="gilt")
    parts.append(bake(hem, Matrix.Translation((0, 0, 0.012)) @ Matrix.Diagonal((0.41, 0.35, 1.0, 1.0))))
    parts.append(orn.taper("lanyard", [front_pt(1.9, 0, 0.008), front_pt(1.75, 0, 0.008),
                                       front_pt(1.6, 0, 0.008), front_pt(1.52, 0, 0.008)],
                           [0.0045] * 4, 6, "velvet"))
    badge_o = front_pt(1.46, 0, 0.0)
    badge = kit.lathe("badge", [(0.0, 0.0), (0.036, 0.0), (0.04, 0.003), (0.036, 0.007), (0.0, 0.007)],
                      28, mat="brass")
    parts.append(bake(badge, frame(badge_o, (0, -1, 0))))
    docent = pivot(kit.join("docent", parts), (0, 0, 0))

    arm_l = arm(1, "arm_L")
    arm_r = arm(-1, "arm_R")
    head_ob = head()
    board = _board()
    pencil = _pencil()
    coll = kit.box("docent-convcolonly", (0.8, 0.7, 2.3), (0, 0, 1.15))

    for ob in (docent, head_ob, arm_l, arm_r, board, pencil, coll):
        print("OBJECT %-22s origin=(%.3f, %.3f, %.3f)" % (ob.name, *ob.location))
    return None


BOARD_C = V(0.0, -0.44, 1.3)
BOARD_ROT = Matrix.Rotation(math.radians(-38), 4, "X")


def _board():
    M = Matrix.Translation(BOARD_C) @ BOARD_ROT
    plate = kit.box("bd_plate", (0.52, 0.02, 0.4), (0, 0, 0), mat="ebony", bevel=0.006, segments=2)
    sheet = kit.box("bd_sheet", (0.47, 0.002, 0.36), (0, -0.0115, 0), mat="sketch_paper", bevel=0.0008, segments=1)
    clip = kit.box("bd_clip", (0.14, 0.035, 0.05), (0, 0.0, 0.19), mat="brass", bevel=0.012, segments=3)
    parts = [bake(p, M) for p in (plate, sheet, clip)]
    return pivot(kit.join("board", parts), BOARD_C)


def _pencil():
    el = V(-0.37, -0.09, 1.36)
    wr = V(-0.2, -0.34, 1.26)
    d = (wr - el).normalized()
    G = wr + d * 0.05
    parts = [
        kit.lathe("pen_body", [(0.0075, -0.06), (0.0075, 0.04)], 6, mat="ebony"),
        kit.lathe("pen_ferrule", [(0.0085, 0.04), (0.0085, 0.056)], 12, mat="brass"),
        kit.lathe("pen_wood", [(0.0075, 0.056), (0.0045, 0.085), (0.0013, 0.1)], 6, mat="sketch_paper"),
        kit.lathe("pen_lead", [(0.0013, 0.095), (0.0, 0.112)], 6, mat="ebony"),
    ]
    for p in parts:
        bake(p, frame(G, d))
    return pivot(kit.join("pencil", parts), G)
