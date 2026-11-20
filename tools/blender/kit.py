"""Small modelling kit for headless build scripts (import kit). Blender units = metres, +Z up.

Everything builds real geometry with bmesh (no operators that need a GUI context) so scripts are
deterministic and parallel-safe.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


def material(name):
    """Get/create a material by name. Only the NAME matters (Godot remaps it)."""
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def _obj(name, bm, mat=None, smooth_angle=35.0):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    if smooth_angle is not None:
        for p in me.polygons:
            p.use_smooth = True
        # mark sharp edges by angle so Godot keeps hard creases
        bm2 = bmesh.new()
        bm2.from_mesh(me)
        for e in bm2.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(smooth_angle):
                e.smooth = False
        bm2.to_mesh(me)
        bm2.free()
        try:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except AttributeError:
            pass
    return ob


def lathe(name, profile, segments=32, mat=None, smooth_angle=40.0, cap=True):
    """Revolve a (radius, z) profile around Z. Profile goes bottom -> top."""
    bm = bmesh.new()
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z)) for r, z in profile])
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for j in range(len(profile) - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    if cap:
        for j in (0, len(profile) - 1):
            if profile[j][0] > 1e-4:
                f = bm.faces.new([rings[i][j] for i in range(segments)])
                if j == 0:
                    f.normal_flip()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth_angle)


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segments, affect="EDGES", profile=0.5)
    return _obj(name, bm, mat, 40.0)


def sweep_closed(name, profile, path, mat=None, smooth_angle=40.0):
    """Sweep a 2D profile [(u, v)] along a closed polyline path [(x, y, z)] lying in a plane.
    u = outward offset (perpendicular to path, in-plane), v = offset along the plane normal.
    Mitred corners. Perfect for picture-frame mouldings and cornices."""
    n = len(path)
    pts = [Vector(p) for p in path]
    # plane normal
    nrm = Vector((0, 0, 0))
    for i in range(n):
        nrm += pts[i].cross(pts[(i + 1) % n])
    nrm.normalize()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        prev, cur, nxt = pts[i - 1], pts[i], pts[(i + 1) % n]
        d0 = (cur - prev).normalized()
        d1 = (nxt - cur).normalized()
        o0 = d0.cross(nrm).normalized()
        o1 = d1.cross(nrm).normalized()
        miter = (o0 + o1).normalized()
        scale = 1.0 / max(miter.dot(o0), 0.2)
        rings.append([bm.verts.new(cur + miter * u * scale + nrm * v) for u, v in profile])
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for j in range(len(profile) - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth_angle)


def rect_path(w, h, z_axis_up=False):
    """Closed rectangle path centred at origin in the XZ plane (a frame standing upright, facing -Y)."""
    hw, hh = w / 2, h / 2
    return [(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)]


def torus(name, major, minor, seg=48, rseg=12, mat=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        c = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(c * (major + minor * math.cos(2 * math.pi * j / rseg)) + Vector((0, 0, minor * math.sin(2 * math.pi * j / rseg)))) for j in range(rseg)])
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    m = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return _obj(name, bm, mat, None if False else 60.0)


def tube(name, points, radius, sides=10, mat=None):
    """Open tube along a polyline (ropes, rails)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = x.cross(d).normalized()
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * radius) for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    return _obj(name, bm, mat, 80.0)


def join(name, objs):
    """Join objects into one (keeps material slots)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = scale
    return ob


def duplicate(ob, name):
    d = ob.copy()
    d.data = ob.data.copy()
    d.name = name
    bpy.context.scene.collection.objects.link(d)
    return d


def collision_box(name, size, loc=(0, 0, 0)):
    """Invisible convex collider: names it <name>-convcolonly."""
    return box(name + "-convcolonly", size, loc)


# --- hands ------------------------------------------------------------------------------------
# hand(side, pose, scale, name, mat) -> one object, all geometry real (no modifiers), origin at the wrist.
# Local frame in metres (before scale): wrist centre at (0, 0, 0); fingers point +Y; the palm faces -Z,
# the back of the hand is +Z. side = +1 puts the thumb on +X, side = -1 on -X. A 4 cm forearm stub runs
# to y = -0.06: sink it into a sleeve. Hand length, wrist to middle fingertip, is about 0.19 m.
# Poses: "open", "relaxed", "grip" (fingers wrap about 2-3 cm across, thumb opposed), "point"
# (index straight, the rest curled). Mesh is about 1000 tris. Place with matrix_world or kit.place().

HAND_POSES = {
    # spread deg per finger (index, middle, ring, pinky); flex deg (MCP, PIP, DIP) per finger;
    # thumb: (splay deg, flex deg at its base joint, flex deg at its tip joint)
    "open": ([8, 1, -4, -10], [(4, 6, 4), (4, 6, 4), (4, 6, 4), (5, 8, 5)], (40, 6, 4)),
    "relaxed": ([6, 1, -3, -8], [(12, 22, 12), (14, 26, 16), (18, 32, 20), (22, 38, 24)], (35, 12, 10)),
    "grip": ([3, 0, -2, -4], [(72, 88, 50), (82, 96, 58), (88, 100, 62), (92, 100, 66)], (28, 42, 50)),
    "point": ([6, 1, -3, -8], [(0, 0, 0), (82, 96, 58), (88, 100, 62), (92, 100, 66)], (30, 40, 40)),
}
_HAND_FINGERS = [  # x (thumb side +), knuckle y, half-width, half-depth, length vs the middle finger
    (0.031, 0.100, 0.0100, 0.0095, 0.93),  # index
    (0.011, 0.104, 0.0105, 0.0100, 1.00),  # middle
    (-0.010, 0.101, 0.0098, 0.0093, 0.94),  # ring
    (-0.030, 0.093, 0.0082, 0.0078, 0.79),  # pinky
]
_HAND_PHALANGES = (0.047, 0.028, 0.021)  # proximal, middle, distal of the middle finger
_HAND_PALM = [  # y, half-width, half-thickness (palm side -Z), wrist at 0, knuckles at 0.104
    (-0.060, 0.024, 0.016), (-0.020, 0.026, 0.017), (0.0, 0.028, 0.018), (0.035, 0.036, 0.017),
    (0.075, 0.041, 0.016), (0.104, 0.0425, 0.0145),
]


def _hand_ring(bm, c, d, B, a, b, sides):
    """Ellipse around c in the plane normal to d: half-width a along B (the bend axis), half-depth b."""
    u = (B - d * B.dot(d)).normalized()
    v = d.cross(u).normalized()
    return [bm.verts.new(c + u * (a * math.cos(2 * math.pi * k / sides)) + v * (b * math.sin(2 * math.pi * k / sides)))
            for k in range(sides)]


def _hand_stitch(bm, rings, sides, end_fan=True):
    """Quads between consecutive rings, fan caps on both ends (a 'tube' with closed ends)."""
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    for ring in (rings[0], rings[-1]):
        ctr = bm.verts.new(sum((v.co for v in ring), Vector()) / sides)
        for k in range(sides):
            bm.faces.new((ring[k], ring[(k + 1) % sides], ctr))


def _hand_digit(bm, base, d0, B, lens, flex, radii, sides=8):
    """Phalanx chain. flex[i] (deg) bends the chain about B toward the palm before phalanx i.
    radii[i] = (a, b) at joint i (0 = base, last = tip). Returns the ring list for _hand_stitch."""
    rings = []
    P, d = Vector(base), Vector(d0).normalized()
    for i, L in enumerate(lens):
        d = (Matrix.Rotation(-math.radians(flex[i]), 3, B) @ d).normalized()
        a0, b0 = radii[i]
        a1, b1 = radii[i + 1]
        knuckle = 1.12 if i == 0 else 1.06  # bulge at each joint
        rings.append(_hand_ring(bm, P, d, B, a0 * knuckle, b0 * knuckle, sides))
        rings.append(_hand_ring(bm, P + d * (L * 0.5), d, B, (a0 + a1) / 2, (b0 + b1) / 2, sides))
        P = P + d * L
        rings.append(_hand_ring(bm, P, d, B, a1, b1, sides))
    # rounded tip: three shrinking rings, then the fan cap closes it
    a, b = radii[-1]
    for along, k in ((0.45, 0.93), (0.8, 0.7), (0.97, 0.3)):
        rings.append(_hand_ring(bm, P + d * (along * a), d, B, a * k, b * k, sides))
    rings.append(_hand_ring(bm, P + d * (a * 1.0), d, B, a * 0.05, b * 0.05, sides))
    return rings


def hand(side, pose="relaxed", scale=1.0, name="hand", mat="skin"):
    """Sculpted hand and forearm stub, origin at the wrist. See the block above for the frame and poses."""
    if pose not in HAND_POSES:
        raise ValueError("hand pose must be one of %s" % sorted(HAND_POSES))
    s = 1.0 if side >= 0 else -1.0
    spreads, flexes, (t_splay, t_f1, t_f2) = HAND_POSES[pose]
    bm = bmesh.new()
    SIDES = 12

    # palm and forearm: superellipse rings, cupped toward -Z, with a thenar bulge on the thumb side
    prings = []
    for y, w, t in _HAND_PALM:
        ring = []
        for k in range(SIDES):
            th = 2 * math.pi * k / SIDES
            cx, cz = math.cos(th), math.sin(th)
            x = w * math.copysign(abs(cx) ** 0.77, cx)
            z = t * math.copysign(abs(cz) ** 0.77, cz)
            if z < 0 and 0.0 <= y <= 0.104:
                z += 0.006 * max(0.0, math.sin(math.pi * y / 0.13)) * (1 - (x / w) ** 2)  # cup
                if s * x > 0:
                    z -= 0.005 * math.exp(-((y - 0.045) / 0.03) ** 2) * (s * x / w) ** 2  # thenar
            ring.append(bm.verts.new((x * s, y, z)))
        prings.append(ring)
    _hand_stitch(bm, prings, SIDES)

    # fingers: start inside the palm at the knuckle line, bend about their own axis
    for fi, (fx, my, a, b, lsc) in enumerate(_HAND_FINGERS):
        sp = math.radians(spreads[fi])
        d0 = Vector((s * math.sin(sp), math.cos(sp), 0.0))
        B = d0.cross(Vector((0, 0, 1))).normalized()
        base = Vector((fx * s, my - 0.012, -0.002))
        lens = [L * lsc for L in _HAND_PHALANGES]
        radii = [(a, b), (a * 0.94, b * 0.94), (a * 0.88, b * 0.90), (a * 0.72, b * 0.70)]
        rings = _hand_digit(bm, base, d0, B, lens, flexes[fi], radii, 10)
        _hand_stitch(bm, rings, 10)

    # thumb: from the thenar, splayed and opposed; two phalanges
    sp = math.radians(t_splay)
    d0 = Vector((s * math.sin(sp), math.cos(sp), 0.0))
    B = d0.cross(Vector((0, 0, 1))).normalized()
    base = Vector((0.026 * s, 0.030, -0.010))
    radii = [(0.0135, 0.0125), (0.0115, 0.0105), (0.0100, 0.0092)]
    rings = _hand_digit(bm, base, d0, B, [0.036, 0.027], (t_f1, t_f2), radii, 10)
    _hand_stitch(bm, rings, 10)

    for v in bm.verts:
        v.co *= scale
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, 180.0)
