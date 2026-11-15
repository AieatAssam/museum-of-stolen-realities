"""THE THIEF, ACQUIRED: a life-size (1.69 m) plaster cast of a young woman caught mid-theft, standing on
z=0 (the pedestal in pedestal.py is applied in Godot). Facing -Y. Figure's right = -X.

Weight on the back (left) foot, the right arm reaching forward and slightly down, the left hand
closed at her chest. Long fitted coat to the knee, hood thrown back on the shoulders, belt, trousers,
soft boots, satchel strap across the body.

Objects (origin = pivot):
  thief       body, legs, coat, hood, belt, satchel, left arm (static); origin at the floor
  thief_head  head with a low hair knot; origin at the neck pivot (0, 0, 1.45)
  thief_arm   right arm, sleeve and hand; origin at the right shoulder (-0.19, 0, 1.36)
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
# coat section (z, half-width x, half-depth y); fitted, knee length, bust and hip shaped
COAT = [(0.50, 0.215, 0.16), (0.62, 0.20, 0.15), (0.80, 0.195, 0.14), (0.92, 0.19, 0.13),
        (1.04, 0.15, 0.105), (1.14, 0.165, 0.12), (1.22, 0.178, 0.13), (1.30, 0.19, 0.115),
        (1.37, 0.20, 0.105), (1.42, 0.12, 0.075)]
HEAD_PROF = [(0.0, -0.03), (0.036, -0.03), (0.05, -0.005), (0.066, 0.03), (0.077, 0.07), (0.082, 0.11),
             (0.083, 0.14), (0.078, 0.175), (0.066, 0.21), (0.045, 0.235), (0.0, 0.245)]


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


def coat_rxry(z):
    if z <= COAT[0][0]:
        return COAT[0][1], COAT[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(COAT, COAT[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return COAT[-1][1], COAT[-1][2]


def coat_pt(z, a):
    rx, ry = coat_rxry(z)
    c, s = math.cos(a), math.sin(a)
    front, back = max(0.0, -s), max(0.0, s)
    bust = 1 + 0.12 * gauss(z, 1.2, 0.1) * front * front
    shoulder_blade = 1 + 0.05 * gauss(z, 1.3, 0.08) * back * back
    return Vector((c * rx, s * ry * bust * shoulder_blade, z))


def front(z, x, out=0.012):
    """Point on the coat's front at height z and x offset, pushed out by `out`."""
    rx, _ = coat_rxry(z)
    c = max(-0.999, min(0.999, x / rx))
    a = -math.acos(c)
    p = coat_pt(z, a)
    return p + Vector((math.cos(a), math.sin(a), 0)) * out


def coat():
    rows_z = []
    for (z0, _, _), (z1, _, _) in zip(COAT, COAT[1:]):
        rows_z += [z0, z0 + (z1 - z0) / 2]
    rows_z.append(COAT[-1][0])
    NS = 40
    bm = bmesh.new()
    rows = [[bm.verts.new(coat_pt(z, 2 * math.pi * i / NS)) for i in range(NS)] for z in rows_z]
    for j in range(len(rows) - 1):
        for i in range(NS):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % NS], rows[j + 1][(i + 1) % NS], rows[j + 1][i]))
    bm.faces.new(rows[-1])  # open at the hem, closed under the collar
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return subsurf(kit._obj("coat", bm, "plaster", 60.0), 1)


def thief_face(x, y, z):
    """Sculpted face: brow, cheekbones, eye sockets, nose ridge, ears, chin."""
    dx = dy = 0.0
    ax = abs(x)
    sx = 1.0 if x >= 0 else -1.0
    w = gauss(ax, 0.032, 0.018) * gauss(z, 0.105, 0.012)  # eye sockets, recessed
    if y < 0:
        dy += 0.006 * w
    w = gauss(ax, 0.03, 0.03) * gauss(z, 0.13, 0.014)  # brow
    if y < 0:
        dy -= 0.005 * w
    w = gauss(ax, 0.06, 0.02) * gauss(z, 0.07, 0.02)  # cheekbones
    dx += sx * 0.004 * w
    if y < 0:
        dy -= 0.004 * w
    w = gauss(ax, 0.08, 0.014) * gauss(y, 0.0, 0.025) * gauss(z, 0.09, 0.03)  # ears
    dx += sx * 0.01 * w
    w = gauss(x, 0, 0.035) * gauss(z, -0.005, 0.02)  # chin
    if y < 0:
        dy -= 0.005 * w
    return dx, dy, 0.0


def thief_head():
    prof = densify(HEAD_PROF, 2)
    ob = kit.lathe("thief_head", prof, 36, mat="plaster", smooth_angle=80.0)
    bake(ob, Matrix.Diagonal((0.92, 1.08, 1.0, 1.0)))
    sculpt(ob, thief_face)
    subsurf(ob, 1)
    parts = [ob]
    # nose: a tapered ridge from brow to a rounded tip
    parts.append(orn.taper("nose", [V(0, -0.078, 0.11), V(0, -0.095, 0.08), V(0, -0.108, 0.05),
                                    V(0, -0.09, 0.035)], [0.009, 0.008, 0.011, 0.007], 8, "plaster"))
    # lips: an upper and a lower sweep
    parts.append(orn.taper("lip_u", [V(-0.022, -0.075, 0.028), V(0, -0.082, 0.03), V(0.022, -0.075, 0.028)],
                           [0.005, 0.007, 0.005], 8, "plaster", flat=0.5, up=(0, 0, 1)))
    parts.append(orn.taper("lip_l", [V(-0.02, -0.074, 0.012), V(0, -0.08, 0.01), V(0.02, -0.074, 0.012)],
                           [0.006, 0.007, 0.006], 8, "plaster", flat=0.5, up=(0, 0, 1)))
    # hair pulled back: the skull shell from the crown to the nape, open at the hairline
    hair_prof = [(r + 0.008, z) for r, z in prof if z >= 0.09]
    hair = kit.lathe("hair", hair_prof, 36, mat="ebony", smooth_angle=80.0, cap=False)
    bake(hair, Matrix.Diagonal((0.92, 1.08, 1.0, 1.0)))
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    kill = [v for v in bm.verts if v.co.y > -0.02 and v.co.z > 0.1] + [v for v in bm.verts if v.co.z < 0.1]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(hair.data)
    bm.free()
    parts.append(hair)
    parts.append(orn.ellipsoid("bun", (0, 0.082, 0.07), (0.04, 0.04, 0.038), "ebony", 12, 6))
    head = kit.join("thief_head", parts)  # built about the neck pivot already: only move the origin
    head.location = NECK
    return head


def leg(s, name):
    """s = -1 right leg (forward), +1 left leg (back, weight carried here)."""
    if s < 0:
        pts = [V(-0.09, 0.0, 0.9), V(-0.1, -0.05, 0.72), V(-0.1, -0.1, 0.5), V(-0.095, -0.1, 0.3), V(-0.09, -0.12, 0.1)]
        ay = -0.12
    else:
        pts = [V(0.09, 0.0, 0.9), V(0.1, 0.02, 0.72), V(0.1, 0.05, 0.5), V(0.095, 0.06, 0.3), V(0.09, 0.08, 0.1)]
        ay = 0.08
    ax = pts[-1].x
    parts = [orn.taper(name + "_trouser", pts, [0.11, 0.09, 0.062, 0.066, 0.044], 10, "plaster")]
    boot = [V(ax, ay + 0.03, 0.13), V(ax, ay + 0.005, 0.075), V(ax, ay - 0.03, 0.04),
            V(ax, ay - 0.09, 0.035), V(ax, ay - 0.125, 0.04)]
    parts.append(orn.taper(name + "_boot", boot, [0.046, 0.046, 0.04, 0.034, 0.024], 10, "ebony", flat=0.9))
    return parts


def left_arm():
    sh = L_SHOULDER
    el = V(0.2, -0.1, 1.12)
    wr = V(0.07, -0.19, 1.2)
    parts = [orn.taper("arm_L_sleeve", [sh, V(0.21, -0.04, 1.24), el, V(0.14, -0.16, 1.14), wr],
                       [0.058, 0.052, 0.046, 0.04, 0.038], 10, "plaster")]
    # closed fist at the chest: a knuckle block and a folded thumb
    parts.append(orn.taper("fist", [wr, V(0.05, -0.215, 1.22), V(0.05, -0.235, 1.225)],
                           [0.036, 0.04, 0.034], 10, "plaster", flat=0.85, up=(0, 0, 1)))
    parts.append(orn.taper("fist_thumb", [V(0.055, -0.19, 1.23), V(0.05, -0.22, 1.25), V(0.04, -0.23, 1.23)],
                           [0.011, 0.012, 0.01], 8, "plaster"))
    return parts


def hood():
    """Hood thrown back over the shoulders: plaster outside, velvet lining inside."""
    pts = [V(-0.2, 0.05, 1.34), V(-0.19, 0.1, 1.42), V(-0.1, 0.13, 1.46), V(0.0, 0.14, 1.47),
           V(0.1, 0.13, 1.46), V(0.19, 0.1, 1.42), V(0.2, 0.05, 1.34)]
    rad = [0.03, 0.05, 0.06, 0.06, 0.06, 0.05, 0.03]
    outer = orn.taper("hood", pts, rad, 10, "plaster", flat=0.6, up=(0, 1, 0))
    inner_pts = [V(p.x * 0.9, p.y - 0.012, p.z - 0.004) for p in pts]
    inner = orn.taper("hood_lining", inner_pts, [r * 0.8 for r in rad], 10, "velvet", flat=0.5, up=(0, 1, 0))
    return [outer, inner]


def build(args):
    parts = []
    parts.append(coat())
    parts.append(orn.taper("neck", [V(0, 0, 1.33), V(0, 0, 1.40), NECK + V(0, 0, 0.01)], [0.07, 0.048, 0.045],
                           12, "plaster"))
    parts.extend(hood())
    # velvet lining band down the coat front
    zs = [1.38, 1.25, 1.1, 0.95, 0.8, 0.65, 0.55]
    parts.append(orn.taper("lapel", [front(z, 0.0, 0.008) for z in zs], [0.011] * len(zs), 6, "velvet",
                           flat=0.3, up=(0, -1, 0)))
    # belt with brass buckle
    belt = kit.torus("belt", 0.152, 0.016, 48, 6, mat="ebony")
    parts.append(bake(belt, Matrix.Translation((0, 0, 1.04)) @ Matrix.Diagonal((1.0, 0.72, 1.0, 1.0))))
    buckle = kit.torus("buckle", 0.026, 0.005, 20, 6, mat="brass")
    parts.append(bake(buckle, frame((0, -0.125, 1.04), (0, -1, 0))))
    # satchel pouch on the left hip and its strap across the body from the right shoulder
    pouch = kit.lathe("pouch", [(0.0, 0.0), (0.05, 0.0), (0.066, 0.02), (0.07, 0.06), (0.066, 0.11),
                                (0.05, 0.13), (0.0, 0.135)], 24, mat="ebony")
    bake(pouch, Matrix.Diagonal((0.42, 1.0, 1.0, 1.0)) @ Matrix.Translation((0, 0, 0)))
    pouch.location = V(0.2, -0.02, 0.86)
    parts.append(pouch)
    strap_pts = [front(1.34, -0.17, 0.012), front(1.24, -0.12, 0.012), front(1.12, -0.02, 0.012),
                 front(1.0, 0.1, 0.012), front(0.94, 0.16, 0.012)]
    parts.append(orn.taper("strap", strap_pts, [0.018] * len(strap_pts), 6, "ebony", flat=0.25, up=(0, -1, 0)))
    # trousers and soft boots
    parts.extend(leg(-1, "right"))
    parts.extend(leg(1, "left"))
    # neck seam, hood and arm
    parts.extend(left_arm())
    thief = kit.join("thief", parts)
    thief_head()
    arm_r()
    return thief


def arm_r():
    """Reaching right arm, sleeve and hand. Origin at the right shoulder."""
    sh = R_SHOULDER
    el = V(-0.2, -0.14, 1.12)
    wr = V(-0.2, -0.40, 1.04)
    d = (wr - el).normalized()
    X = V(1, 0, 0)
    Z = V(0, 0, 1)
    parts = [orn.taper("thief_arm_sleeve", [sh, V(-0.21, -0.08, 1.25), el, V(-0.2, -0.27, 1.07), wr],
                       [0.058, 0.052, 0.047, 0.042, 0.038], 10, "plaster")]
    parts.append(orn.taper("thief_palm", [wr, wr + d * 0.035, wr + d * 0.07], [0.03, 0.036, 0.031], 10,
                           "plaster", flat=0.5, up=(0, 0, 1)))
    for k, (off, L) in enumerate(zip([-0.022, -0.007, 0.008, 0.023], [0.07, 0.078, 0.076, 0.062])):
        K = wr + d * 0.065 + X * off
        parts.append(orn.taper("thief_finger%d" % k, [K, K + d * 0.03, K + d * (L * 0.7) - Z * 0.012,
                                                      K + d * L - Z * 0.028],
                               [0.0105, 0.0095, 0.009, 0.0082], 6, "plaster"))
    parts.append(orn.taper("thief_thumb", [wr + d * 0.01 + X * 0.02, wr + d * 0.035 + X * 0.045,
                                           wr + d * 0.06 + X * 0.05 + Z * 0.012],
                           [0.012, 0.011, 0.009], 6, "plaster"))
    return pivot(kit.join("thief_arm", parts), sh)


if __name__ == "__main__":
    pass
