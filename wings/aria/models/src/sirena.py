"""La Sirena: the drowned soprano on the stage of the underwater opera house, mid-aria.

Build one model per run:
  tools/blender_build.sh wings/aria/models/src/sirena.py wings/aria/models/sirena.glb

Built at human scale (1.75 m) and scaled x4 at the end. Units: metres, +Z up, origin at the
centre of her feet, facing -Y. Materials: sirena_gown, sirena_skin, sirena_hair.
"""
import math

import bmesh
from mathutils import Matrix, Vector

import kit

TAU = 2 * math.pi
Y_AXIS = Vector((0, 1, 0))


# --- helpers -------------------------------------------------------------------------------------

def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lathe_fn(name, zs, rfn, segments, mat, smooth=50.0, cap=True):
    """Lathe whose radius depends on height and angle: rfn(z, theta)."""
    bm = bmesh.new()
    rings = []
    for z in zs:
        ring = []
        for i in range(segments):
            th = TAU * i / segments
            r = rfn(z, th)
            ring.append(bm.verts.new((r * math.cos(th), r * math.sin(th), z)))
        rings.append(ring)
    for j in range(len(zs) - 1):
        for i in range(segments):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % segments], rings[j + 1][(i + 1) % segments], rings[j + 1][i]))
    if cap:
        f = bm.faces.new(rings[0])
        f.normal_flip()
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def grid(name, nx, nz, fn, mat, smooth=60.0):
    """A sheet: fn(u, v) -> (x, y, z) for u, v in 0..1. For cloth."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(i / nx, j / nz)) for i in range(nx + 1)] for j in range(nz + 1)]
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    uv = bm.loops.layers.uv.new()
    bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            i = lp.vert.index % (nx + 1)
            j = lp.vert.index // (nx + 1)
            lp[uv].uv = (i / nx, 1.0 - j / nz)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def blob(name, c, U, V, W, mat, nu=20, nv=10):
    """Ellipsoid with centre c and semi-axis vectors U, V, W (may be rotated)."""
    bm = bmesh.new()
    rows = []
    for j in range(nv + 1):
        phi = -math.pi / 2 + math.pi * j / nv
        if j == 0 or j == nv:
            rows.append([bm.verts.new(Vector(c) + W * math.sin(phi))])
            continue
        row = []
        for i in range(nu):
            th = TAU * i / nu
            p = Vector(c) + U * (math.cos(phi) * math.cos(th)) + V * (math.cos(phi) * math.sin(th)) + W * math.sin(phi)
            row.append(bm.verts.new(p))
        rows.append(row)
    for j in range(nv):
        r0, r1 = rows[j], rows[j + 1]
        if len(r0) == 1:
            for i in range(nu):
                bm.faces.new((r0[0], r1[(i + 1) % nu], r1[i]))
        elif len(r1) == 1:
            for i in range(nu):
                bm.faces.new((r0[i], r0[(i + 1) % nu], r1[0]))
        else:
            for i in range(nu):
                bm.faces.new((r0[i], r0[(i + 1) % nu], r1[(i + 1) % nu], r1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 40.0)


def vtube(name, pts, radii, sides, mat, smooth=80.0):
    """Open tube along a polyline with a radius per point (tapers)."""
    bm = bmesh.new()
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = x.cross(d).normalized()
        ring = []
        for k in range(sides):
            a = TAU * k / sides
            ring.append(bm.verts.new(p + (x * math.cos(a) + y * math.sin(a)) * radii[i]))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    return kit._obj(name, bm, mat, smooth)


def spline(ctrl, radii, per):
    """Uniform Catmull-Rom through the control points; returns (points, radii) with `per` samples a span."""
    pts = [Vector(p) for p in ctrl]
    ext = [pts[0]] + pts + [pts[-1]]
    out, rad = [], []
    for s in range(len(pts) - 1):
        p0, p1, p2, p3 = ext[s], ext[s + 1], ext[s + 2], ext[s + 3]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
            rad.append(radii[s] + (radii[s + 1] - radii[s]) * t)
    out.append(pts[-1])
    rad.append(radii[-1])
    return out, rad


# --- gown ----------------------------------------------------------------------------------------

GOWN_KEYS = [(0.0, 0.55), (0.45, 0.22), (0.9, 0.19), (1.05, 0.13), (1.25, 0.17), (1.32, 0.15)]


def gown_base(z):
    for (z0, r0), (z1, r1) in zip(GOWN_KEYS, GOWN_KEYS[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return GOWN_KEYS[-1][1]


def gown_r(z, th):
    r = gown_base(z)
    # 14 vertical folds, 0.05 deep, fading out above z 0.5 (gone by 1.0)
    fade = min(1.0, max(0.0, (1.0 - z) / 0.5))
    r += 0.05 * math.sin(14 * th) * fade
    # the train: the +Y side sweeps back to 1.4 m at the hem, with ripples down its length
    back = max(0.0, math.cos(th - math.pi / 2))
    fall = max(0.0, 1.0 - z)
    r += 0.85 * back ** 6 * fall ** 1.5
    r += 0.05 * math.sin(5 * (th - math.pi / 2)) * back ** 2 * fall
    # ripple along the hem edge
    r += 0.02 * math.sin(9 * th) * max(0.0, 1.0 - z / 0.12)
    # sweetheart neckline: the front of the bodice dips low
    front = max(0.0, math.cos(th + math.pi / 2))
    r -= 0.1 * front ** 4 * smoothstep(1.2, 1.32, z)
    return r


def gown():
    zs = [0.0, 0.015, 0.035, 0.07, 0.12] + [0.12 + (1.32 - 0.12) * k / 40 for k in range(1, 41)]
    return lathe_fn("sirena_gown", zs, gown_r, 64, "sirena_gown")


def scarf(name, wrist, side):
    """A long trailing scarf from one wrist: 0.25 wide, ~1.6 long, billowing back and down in waves."""
    def fn(u, v):
        x = wrist.x + (u - 0.5) * 0.25 + 0.2 * math.sin(TAU * 1.4 * v + side * 1.3) * v
        y = wrist.y + 0.35 + 1.0 * v
        z = wrist.z - 1.2 * v + 0.18 * math.sin(TAU * 1.1 * v + side * 0.7) * v
        return (x, y, z)
    return grid(name, 3, 24, fn, "sirena_gown")


# --- head, neck, shoulders -----------------------------------------------------------------------

HEAD_C = Vector((0, 0, 1.6))
TILT = Matrix.Rotation(math.radians(-15), 3, "X")   # tilted back: face lifts up and forward


def head_r(z, th):
    # ellipsoid-ish cross-section: narrow at the jaw (0.07), full at the cranium (0.09)
    w = 0.07 + 0.02 * smoothstep(-0.1, 0.05, z)
    return w * math.sqrt(max(0.0, 1.0 - (z / 0.12) ** 2))


def head_parts():
    head = lathe_fn("sirena_head", [-0.115 + 0.23 * k / 16 for k in range(17)], head_r, 24, "sirena_skin", smooth=40.0)
    head.rotation_euler = (math.radians(-15), 0, 0)
    head.location = HEAD_C
    P = [head]
    # hair mass: a cap a little bigger than the skull, covering the back and top, with a chignon
    P.append(blob("sirena_hair_cap", HEAD_C + TILT @ Vector((0, 0.02, 0.02)), TILT @ Vector((0.1, 0, 0)),
                  TILT @ Vector((0, 0.1, 0)), TILT @ Vector((0, 0, 0.125)), "sirena_hair"))
    P.append(blob("sirena_bun", HEAD_C + TILT @ Vector((0, 0.11, -0.04)), TILT @ Vector((0.045, 0, 0)),
                  TILT @ Vector((0, 0.045, 0)), TILT @ Vector((0, 0, 0.045)), "sirena_hair", nu=14, nv=8))
    # face: a nose ridge, a chin, and a small dark open mouth
    P.append(blob("sirena_nose", HEAD_C + TILT @ Vector((0, -0.088, -0.005)), TILT @ Vector((0.011, 0, 0)),
                  TILT @ Vector((0, 0.012, 0)), TILT @ Vector((0, 0, 0.03)), "sirena_skin", nu=10, nv=6))
    P.append(blob("sirena_chin", HEAD_C + TILT @ Vector((0, -0.06, -0.1)), TILT @ Vector((0.028, 0, 0)),
                  TILT @ Vector((0, 0.03, 0)), TILT @ Vector((0, 0, 0.025)), "sirena_skin", nu=12, nv=6))
    P.append(blob("sirena_mouth", HEAD_C + TILT @ Vector((0, -0.084, -0.035)),
                  TILT @ Vector((0.02, 0, 0)), TILT @ Vector((0, 0.004, 0)), TILT @ Vector((0, 0, 0.016)),
                  "sirena_hair", nu=12, nv=6))
    P.append(kit.lathe("sirena_neck", [(0.055, 1.34), (0.05, 1.42), (0.04, 1.5)], segments=16, mat="sirena_skin"))
    P.append(blob("sirena_shoulders", Vector((0, 0, 1.38)), Vector((0.2, 0, 0)), Vector((0, 0.06, 0)),
                  Vector((0, 0, 0.06)), "sirena_skin"))
    # bust under the bodice (gown material), and the skin of the sweetheart neckline
    for sx in (-1, 1):
        P.append(blob("sirena_bust", Vector((sx * 0.085, -0.13, 1.2)), Vector((0.07, 0, 0)),
                      Vector((0, 0.06, 0)), Vector((0, 0, 0.07)), "sirena_gown"))
    P.append(blob("sirena_chest", Vector((0, -0.12, 1.27)), Vector((0.13, 0, 0)), Vector((0, 0.07, 0)),
                  Vector((0, 0, 0.08)), "sirena_skin"))
    return P


# --- arms and hands ------------------------------------------------------------------------------

def arm(name, ctrl):
    pts, rad = spline(ctrl, [0.045, 0.035, 0.024], per=4)
    return vtube(name, pts, rad, 8, "sirena_skin")


def hand(name, wrist, elbow, sign):
    P = []
    f = (wrist - elbow).normalized()
    s = f.cross(Y_AXIS).normalized()
    n = s.cross(f).normalized()
    c = wrist + f * 0.045
    P.append(blob(name + "_palm", c, f * 0.045, s * 0.025, n * 0.01, "sirena_skin", nu=12, nv=6))
    for k in range(4):
        off = k - 1.5
        base = c + f * 0.04 + s * (off * 0.016)
        d = (f + s * off * 0.12).normalized()
        P.append(kit.tube(name + "_finger", [base, base + d * 0.035, base + d * 0.07], 0.008, 6, mat="sirena_skin"))
    tb = c - f * 0.005 + s * (sign * 0.025)
    td = (f * 0.4 + s * sign * 1.0).normalized()
    P.append(kit.tube(name + "_thumb", [tb, tb + td * 0.025, tb + td * 0.05], 0.009, 6, mat="sirena_skin"))
    return P


# --- hair ----------------------------------------------------------------------------------------

def hair():
    P = []
    for i in range(24):
        # roots over the back half of the hair mass (+Y is behind her)
        lat = math.radians(-5 + 60 * ((i * 7) % 24) / 23)
        lon = math.pi / 2 + (((i * 5) % 24) / 23 - 0.5) * 2.2
        root = HEAD_C + Vector((0.105 * math.cos(lat) * math.cos(lon),
                                0.105 * math.cos(lat) * math.sin(lon) + 0.02,
                                0.13 * math.sin(lat) + 0.02))
        L = 0.8 + 0.2 * ((i * 0.618) % 1.0)
        ph = i * 0.9
        pts = []
        for k in range(12):
            t = k / 11
            pts.append(Vector((root.x + 0.09 * math.sin(TAU * 1.2 * t + ph) * t,
                               root.y + L * 0.8 * t,
                               root.z + L * 0.3 * t + 0.03 * math.sin(TAU * t + ph) * t)))
        radii = [0.025 - 0.019 * k / 11 for k in range(12)]
        P.append(vtube("sirena_hair", pts, radii, 6, "sirena_hair"))
    return P


# --- build ---------------------------------------------------------------------------------------

def build(args):
    right = [(0.2, 0, 1.38), (0.38, -0.05, 1.62), (0.42, -0.12, 1.78)]
    left = [(-0.2, 0, 1.38), (-0.42, -0.18, 1.42), (-0.62, -0.38, 1.5)]
    parts = [gown(), scarf("sirena_scarf_r", Vector(right[-1]), 1), scarf("sirena_scarf_l", Vector(left[-1]), -1)]
    parts += head_parts()
    parts.append(arm("sirena_arm_r", right))
    parts.append(arm("sirena_arm_l", left))
    parts += hand("sirena_hand_r", Vector(right[-1]), Vector(right[-2]), 1.0)
    parts += hand("sirena_hand_l", Vector(left[-1]), Vector(left[-2]), -1.0)
    parts += hair()
    ob = kit.join("sirena", parts)
    # triangulate so glTF tangents can be computed
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.scale = (4.0, 4.0, 4.0)
    return ob
