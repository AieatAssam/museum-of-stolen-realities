"""1940s figures read by silhouette (mostly backlit). Origin at the soles, +Y is the facing direction,
Z up, metres. Parts are built at the origin and moved with explicit matrices (_put), so nothing
depends on object transforms surviving the join.

  figure            man, 1.80 m to hat top, hands in coat pockets, belted trench coat to the knee,
                    weight on the left leg (right knee bent), feet 0.25 m apart and splayed
  figure_b          same man, weight on one leg, one hand touching the brim, head turned 15 deg
  figure_woman      1.68 m, fitted belted coat, flared knee skirt, heels, shoulder bag, small tilted hat
  detective_seated  bench-edge pose of the man, fedora resting on one knee

Materials: coat (wool), skin, hat (felt), shirt (white collar), tyre (black shoes), paint (black
band, buttons, hair, tie).

Build: figure.py <args> with args[0] in figure | figure_b | figure_woman | detective_seated
(short forms b | woman | seated also accepted)."""
import math

import bmesh
import kit
from mathutils import Euler, Matrix, Vector

R = math.radians


def _M(p=(0, 0, 0), rot=(0, 0, 0), s=(1, 1, 1)):
    """Matrix: scale, then rotate (XYZ euler), then translate."""
    return Matrix.Translation(p) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))


def _put(ob, M):
    ob.data.transform(M)
    return ob


def _box(name, size, p, mat, rot=(0, 0, 0), bevel=0.0):
    return _put(kit.box(name, size, mat=mat, bevel=bevel), _M(p, rot))


def _lathe(name, prof, mat, p=(0, 0, 0), s=(1, 1, 1), rot=(0, 0, 0), segs=24):
    return _put(kit.lathe(name, prof, segs, mat=mat), _M(p, rot, s))


def _lathe_w(name, prof, mat, p=(0, 0, 0), s=(1, 1, 1), segs=24, warp=None, vent=None):
    """Lathe with optional per-vertex warp(q, angle) on local coords and a vent(world centre) face cut."""
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        row = []
        for r, z in prof:
            q = (r * math.cos(a), r * math.sin(a), z)
            if warp:
                q = warp(q, a)
            row.append(bm.verts.new((q[0] * s[0] + p[0], q[1] * s[1] + p[1], q[2] * s[2] + p[2])))
        rings.append(row)
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        for j in range(len(prof) - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    if prof[0][0] > 1e-4:
        bm.faces.new([rings[i][0] for i in range(segs)])
    if vent:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if vent(f.calc_center_median())], context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 40.0)


def _tube(name, pts, r, mat, sides=8):
    """Open tube along a polyline; r is one radius or one per point (tapered limbs)."""
    radii = list(r) if isinstance(r, (list, tuple)) else [r] * len(pts)
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = x.cross(d).normalized()
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * radii[i])
                      for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 80.0)


def _ell(name, c, radii, mat, segs=12, rings=8, warp=None):
    bm = bmesh.new()
    rows = []
    for j in range(rings + 1):
        v = math.pi * j / rings
        row = []
        for i in range(segs):
            u = 2 * math.pi * i / segs
            p = (c[0] + radii[0] * math.sin(v) * math.cos(u),
                 c[1] + radii[1] * math.sin(v) * math.sin(u),
                 c[2] + radii[2] * math.cos(v))
            if warp:
                p = warp(p)
            row.append(bm.verts.new(p))
        rows.append(row)
    for j in range(rings):
        for i in range(segs):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % segs], rows[j + 1][(i + 1) % segs], rows[j + 1][i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 50.0)


# --- hat (local origin = brim centre, crown up +Z; crown 0.10 above the band) ----------------------

CROWN = [(0.095, 0.0), (0.097, 0.03), (0.092, 0.07), (0.084, 0.098), (0.074, 0.114), (0.06, 0.12),
         (0.0, 0.10)]  # last point: the centre dent, 0.02 below the rim of the top
BAND = [(0.1, 0.0), (0.1, 0.022)]
BRIM_R = (0.09, 0.13, 0.17, 0.19)


def _brim(parts, M):
    """Wide brim: curls up at the sides, snaps down about 10 deg at the front. Closed thin shell."""
    bm = bmesh.new()
    segs = 28
    top, bot = [], []
    for r in BRIM_R:
        t = (r - BRIM_R[0]) / (BRIM_R[-1] - BRIM_R[0])
        trow, brow = [], []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ca, sa = math.cos(a), math.sin(a)
            z = 0.03 * t * t * ca * ca - 0.033 * t * max(sa, 0.0) + 0.01 * t * t * max(-sa, 0.0)
            trow.append(bm.verts.new((r * ca, r * sa, z)))
            brow.append(bm.verts.new((r * ca, r * sa, z - 0.004)))
        top.append(trow)
        bot.append(brow)
    n = len(BRIM_R)
    for j in range(n - 1):
        for i in range(segs):
            i1 = (i + 1) % segs
            bm.faces.new((top[j][i], top[j][i1], top[j + 1][i1], top[j + 1][i]))
            bm.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i1], bot[j][i1]))
    for j in (0, n - 1):  # rim edges close the shell
        for i in range(segs):
            i1 = (i + 1) % segs
            bm.faces.new((top[j][i], top[j][i1], bot[j][i1], bot[j][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    parts.append(_put(kit._obj("hat_brim", bm, "hat", 35.0), M))


def _hat(parts, M):
    crown = _lathe("hat_crown", CROWN, "hat", segs=20)
    for v in crown.data.vertices:  # front pinch: narrow the front of the crown, more toward the top
        if v.co.y > 0.01 and v.co.z > 0.03:
            v.co.x *= 1.0 - 0.14 * min(1.0, (v.co.z - 0.03) / 0.08)
            v.co.y *= 0.96
    parts.append(_put(crown, M))
    parts.append(_put(_lathe("hat_band", BAND, "paint", segs=20), M))
    _brim(parts, M)


# --- man -------------------------------------------------------------------------------------------

def _hem(q, a):
    """Uneven hem: the bottom of the skirt rides up and down around the coat."""
    x, y, z = q
    if z < 0.6:
        w = min(1.0, (0.6 - z) / 0.18)
        z += 0.045 * w * (0.5 + 0.5 * math.sin(3 * a + 0.7))
    return (x, y, z)


def _collar(dx, dz):
    """Turned-up collar: a sheet standing round the back of the neck, top at about 1.58 m."""
    bm = bmesh.new()
    cols = 12
    g = []
    for i in range(cols + 1):
        a = math.pi + math.pi * i / cols  # 180 deg (left) through 270 (back) to 360 (right)
        cx, cy = math.cos(a), math.sin(a)
        g.append([
            bm.verts.new((dx + cx * 0.086, cy * 0.078, dz + 1.34)),
            bm.verts.new((dx + cx * 0.094, cy * 0.086, dz + 1.58)),
            bm.verts.new((dx + cx * 0.072, cy * 0.064, dz + 1.58)),
            bm.verts.new((dx + cx * 0.07, cy * 0.062, dz + 1.34)),
        ])
    for i in range(cols):
        for k in range(3):
            bm.faces.new((g[i][k], g[i + 1][k], g[i + 1][k + 1], g[i][k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj("collar_back", bm, "coat", 30.0)


def _coat(parts, dx, dz, skirt=True, b=False):
    """Trench coat upper body at offset (dx, dz). Waist at z 1.0, shoulders ~1.37, collar top 1.58."""
    o = (dx, 0, dz)
    if skirt:
        parts.append(_lathe_w("coat_skirt", [(0.26, 0.42), (0.25, 0.55), (0.22, 0.72), (0.2, 0.86),
                                             (0.19, 0.96), (0.19, 1.0)], "coat", p=o, s=(1.15, 1.0, 1),
                              warp=_hem, vent=lambda c: abs(c.x - dx) < 0.05 and c.y < 0 and c.z < 0.66))
        parts.append(_lathe("belt", [(0.2, 0.935), (0.207, 0.935), (0.207, 0.97), (0.2, 0.97)], "coat",
                            p=o, s=(1.15, 1.0, 1)))
        parts.append(_box("buckle", (0.05, 0.01, 0.04), (dx, 0.212, dz + 0.952), "paint"))
    parts.append(_lathe("torso", [(0.19, 1.0), (0.2, 1.06), (0.205, 1.18), (0.2, 1.3), (0.16, 1.4),
                                  (0.1, 1.43), (0.0, 1.44)], "coat", p=o, s=(1.25, 1.0, 1)))
    # padded squared shoulders
    for s in (-1, 1):
        parts.append(_box("pad", (0.07, 0.22, 0.1), (dx + s * 0.215, 0, dz + 1.37), "coat", bevel=0.02))
    # double-breasted front: two columns of tiny buttons, the right column skipped when open
    # front details end below the chest top (~1.28) so they do not float off the torso
    parts.append(_box("shirt_v", (0.08, 0.012, 0.2), (dx, 0.2, dz + 1.15), "shirt"))
    parts.append(_box("tie", (0.035, 0.012, 0.18), (dx, 0.215, dz + 1.16), "paint"))
    parts.append(_box("tie_knot", (0.04, 0.02, 0.04), (dx, 0.2, dz + 1.27), "paint"))
    for s in (-1, 1):
        if b and s > 0:
            continue
        for z in (1.22, 1.12, 1.02):
            if not skirt and z < 1.1:
                continue
            parts.append(_box("button", (0.022, 0.01, 0.022), (dx + s * 0.05, 0.212, dz + z), "paint"))
    # notched lapels: slabs leaning in toward the neck, the open side splayed further
    for s in (-1, 1):
        ang = -13 if s > 0 else 13
        if b and s > 0:
            ang = -30
        parts.append(_box("lapel", (0.075, 0.012, 0.2), (dx + s * 0.07, 0.2, dz + 1.17), "coat",
                          rot=(0, R(ang), 0)))
    # white collar points at the front, turned-up coat collar behind the neck
    parts.append(_box("collar", (0.11, 0.02, 0.09), (dx, 0.085, dz + 1.44), "shirt", rot=(R(-15), 0, 0)))
    parts.append(_collar(dx, dz))
    # side pocket flaps
    if skirt:
        for s in (-1, 1):
            parts.append(_box("pocket_flap", (0.02, 0.13, 0.012), (dx + s * 0.228, 0.0, dz + 0.92), "coat"))


SHOE_PROFILE = [  # (y forward, z up, half width): heel at the back, rounded toe, vamp up to the ankle
    (-0.065, 0.0, 0.04), (0.0, 0.0, 0.05), (0.15, 0.0, 0.05), (0.19, 0.01, 0.045), (0.21, 0.025, 0.03),
    (0.2, 0.05, 0.028), (0.1, 0.075, 0.035), (0.02, 0.09, 0.045), (-0.04, 0.09, 0.045), (-0.065, 0.06, 0.04),
]


def _shoe(parts, x, y, rot_deg, k=1.0):
    """Shoe with its ankle footprint at (x, y) on the floor; the toe reaches forward (+Y), 0.27 L x 0.10 W x 0.09 H at k=1.
    Convex hull of a side profile mirrored across X: flat sole, heel, pointed-round toe, vamp."""
    bm = bmesh.new()
    for py, pz, hw in SHOE_PROFILE:
        for sx in (-1, 1):
            bm.verts.new((sx * hw * k, py * k, pz * k))
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    parts.append(_put(kit._obj("shoe", bm, "tyre", 30.0), _M((x, y, 0.0), (0, 0, R(rot_deg)))))


def _man_legs(parts, b):
    """Tapered trouser legs (0.085 thigh, 0.06 ankle, flared cuff) and shoes splayed 10 deg."""
    if b:
        legs = [([(-0.12, 0, 0.92), (-0.12, 0, 0.5), (-0.125, 0, 0.16), (-0.125, 0, 0.10)], (-0.125, 0.0), 10),
                ([(0.12, 0, 0.92), (0.165, 0.035, 0.5), (0.2, 0.06, 0.16), (0.2, 0.06, 0.10)], (0.2, 0.06), -10)]
    else:
        legs = [([(-0.12, 0, 0.92), (-0.12, 0, 0.5), (-0.125, 0, 0.16), (-0.125, 0, 0.10)], (-0.125, 0.0), 10),
                ([(0.12, 0, 0.92), (0.13, 0.06, 0.5), (0.125, 0, 0.16), (0.125, 0, 0.10)], (0.125, 0.0), -10)]
    for pts, foot, rot in legs:
        parts.append(_tube("leg", pts, [0.085, 0.07, 0.06, 0.066], "coat"))
        _shoe(parts, foot[0], foot[1], rot)


def _hand(parts, c):
    parts.append(_ell("hand", c, (0.03, 0.025, 0.042), "skin", 10, 6))


def _head(parts, dx, dz, yaw, hat):
    """Head, hat and neck. Head centre z 1.58 (+dz), 0.88 of the old size; the head turns about the neck."""
    o = (dx, 0, dz)
    piv = Vector((o[0], o[1], o[2] + 1.5))
    T = Matrix.Translation(piv) @ Matrix.Rotation(R(yaw), 4, "Z") @ Matrix.Translation(-piv)
    head_parts = [
        _ell("head", (o[0], o[1], o[2] + 1.58), (0.0774, 0.095, 0.104), "skin", 16, 12),
        _ell("jaw", (o[0], o[1] + 0.02, o[2] + 1.5), (0.066, 0.07, 0.05), "skin", 12, 8),
        _ell("chin", (o[0], o[1] + 0.06, o[2] + 1.46), (0.036, 0.034, 0.03), "skin", 8, 6),
        _ell("nose", (o[0], o[1] + 0.1, o[2] + 1.57), (0.013, 0.03, 0.03), "skin", 8, 6),
        _ell("ear", (o[0] - 0.077, o[1], o[2] + 1.56), (0.011, 0.024, 0.033), "skin", 8, 6),
        _ell("ear", (o[0] + 0.077, o[1], o[2] + 1.56), (0.011, 0.024, 0.033), "skin", 8, 6),
    ]
    for h in head_parts:
        parts.append(_put(h, T))
    parts.append(_tube("neck", [(o[0], o[1], o[2] + 1.36), (o[0], o[1], o[2] + 1.52)], 0.05, "skin"))
    if hat:
        _hat(parts, T @ Matrix.Translation((o[0], o[1], o[2] + 1.68)) @ Matrix.Rotation(R(-8), 4, "X"))


def _man(parts, b):
    dx = 0.02 if b else 0.0
    _coat(parts, dx, 0.0, True, b)
    _man_legs(parts, b)
    for s in (-1, 1):
        shoulder = (s * 0.24 + dx, 0, 1.31)
        if b and s > 0:
            # hand raised to touch the brim
            parts.append(_tube("arm", [shoulder, (0.32 + dx, 0.14, 1.5), (0.16 + dx, 0.1, 1.71)], 0.055, "coat"))
            _hand(parts, (0.16 + dx, 0.1, 1.72))
        else:
            # forearm angled into the side pocket, hand hidden in the coat
            parts.append(_tube("arm", [shoulder, (s * 0.29 + dx, 0.02, 1.08), (s * 0.2 + dx, 0.07, 0.93)], 0.055, "coat"))
    _head(parts, dx, 0.0, 15 if b else 0.0, hat=True)


def _seated(parts):
    dz = -0.3  # upper body sits 0.3 m lower than standing
    # legs: tapered thighs run forward from the hips, rounded knees, tapered shins down to the shoes
    for s in (-1, 1):
        x = s * 0.13
        parts.append(_tube("thigh", [(x, -0.02, 0.56), (x, 0.2, 0.56), (x, 0.4, 0.53)],
                           [0.095, 0.088, 0.075], "coat", 10))
        parts.append(_ell("knee", (x, 0.41, 0.5), (0.065, 0.065, 0.065), "coat", 10, 6))
        parts.append(_tube("shin", [(x, 0.41, 0.48), (x, 0.42, 0.25), (x, 0.42, 0.10)],
                           [0.062, 0.05, 0.042], "coat", 10))
        _shoe(parts, x, 0.42, -10 * s)
    # seat: rounded hips, the coat laps over each thigh and a folded panel falls between the knees
    parts.append(_ell("seat", (0.0, 0.02, 0.56), (0.22, 0.2, 0.12), "coat", 16, 10))
    for s in (-1, 1):
        parts.append(_ell("lap", (s * 0.13, 0.2, 0.6), (0.11, 0.2, 0.05), "coat", 12, 6))

    def fold(p):
        return (p[0], p[1] + 0.014 * math.cos(90 * p[0]), p[2])

    parts.append(_ell("coat_fold", (0.0, 0.36, 0.4), (0.065, 0.045, 0.19), "coat", 12, 8, warp=fold))

    # upper body: the trench coat without skirt, rounded shoulders, head tilted down; the torso
    # hunches forward about the hips and the head nods onto the chest
    upper, head_parts = [], []
    _coat(upper, 0.0, dz, skirt=False)
    # turned-up collar hides the back of the neck; shoulders sit inside the coat line
    upper.append(_ell("collar_up", (0.0, -0.03, dz + 1.4), (0.11, 0.08, 0.07), "coat", 12, 8))
    for s in (-1, 1):
        upper.append(_ell("shoulder", (s * 0.19, 0.0, dz + 1.33), (0.09, 0.12, 0.07), "coat", 12, 8))
    _head(head_parts, 0.0, dz, 0.0, hat=False)
    # dark hair over the top and back of the head, and at the nape so the neck is not a pale tube
    head_parts.append(_ell("hair", (0.0, -0.012, dz + 1.6), (0.081, 0.098, 0.092), "hat", 12, 8))
    head_parts.append(_ell("hair_nape", (0.0, -0.04, dz + 1.5), (0.06, 0.05, 0.06), "hat", 10, 6))
    piv = Vector((0.0, 0.0, 0.7))
    hunch = Matrix.Translation(piv) @ Matrix.Rotation(R(-14), 4, "X") @ Matrix.Translation(-piv)
    neck = Vector((0.0, 0.0, dz + 1.5))
    tilt = Matrix.Translation(neck) @ Matrix.Rotation(R(-18), 4, "X") @ Matrix.Translation(-neck)
    for ob in upper:
        ob.data.transform(hunch)
    for ob in head_parts:
        ob.data.transform(hunch @ tilt)
    parts += upper + head_parts

    # arms: forearms rest on the thighs, the right hand on the hat crown, the left on the knee
    for s in (-1, 1):
        sh = hunch @ Vector((s * 0.23, 0.0, dz + 1.31))
        wrist = (0.15, 0.27, 0.8) if s > 0 else (-0.16, 0.3, 0.68)
        parts.append(_tube("arm", [tuple(sh), (s * 0.27, 0.14, 0.8), wrist], [0.06, 0.05, 0.045], "coat", 10))
    _hand(parts, (0.14, 0.3, 0.8))
    _hand(parts, (-0.13, 0.36, 0.66))

    # fedora resting crown-up on the right knee, brim flat on the lap
    _hat(parts, Matrix.Translation((0.13, 0.3, 0.66)) @ Matrix.Rotation(R(10), 4, "Z"))


# --- woman -----------------------------------------------------------------------------------------

def _woman(parts):
    for s in (-1, 1):
        x = s * 0.085
        parts.append(_tube("leg", [(s * 0.1, 0, 0.85), (s * 0.09, 0, 0.48), (x, 0, 0.1)], 0.05, "skin"))
        _shoe(parts, x, 0.0, 0.0, k=0.85)
        parts.append(_box("heel", (0.03, 0.03, 0.035), (x, -0.045, 0.0175), "tyre"))
    # flared knee-length skirt, belt and slim bodice with padded shoulders
    parts.append(_lathe("skirt", [(0.26, 0.5), (0.22, 0.6), (0.18, 0.8), (0.16, 0.9), (0.15, 0.99)],
                        "coat", s=(1.0, 0.85, 1)))
    parts.append(_lathe("belt", [(0.152, 0.955), (0.159, 0.955), (0.159, 0.995), (0.152, 0.995)], "coat",
                        s=(1.0, 0.85, 1)))
    parts.append(_box("buckle", (0.035, 0.01, 0.03), (0, 0.135, 0.975), "paint"))
    parts.append(_lathe("bodice", [(0.14, 0.99), (0.155, 1.06), (0.165, 1.15), (0.16, 1.25), (0.13, 1.31),
                                   (0.07, 1.34), (0.0, 1.345)], "coat", s=(1.1, 0.78, 1)))
    for s in (-1, 1):
        parts.append(_box("pad", (0.06, 0.18, 0.07), (s * 0.19, 0, 1.3), "coat", bevel=0.015))
        parts.append(_box("lapel", (0.05, 0.01, 0.16), (s * 0.05, 0.13, 1.2), "coat", rot=(0, R(-s * 12), 0)))
    for z in (1.2, 1.1, 1.0):
        parts.append(_box("button", (0.02, 0.01, 0.02), (0, 0.135, z), "paint"))
    parts.append(_box("collar", (0.1, 0.015, 0.05), (0, 0.1, 1.33), "shirt", rot=(R(-20), 0, 0)))
    # left arm holds the bag strap, right arm hangs at the side
    parts.append(_tube("arm", [(-0.19, 0, 1.27), (-0.23, 0.05, 1.04), (-0.12, 0.07, 1.25)], 0.05, "coat"))
    _hand(parts, (-0.12, 0.07, 1.25))
    parts.append(_tube("arm", [(0.19, 0, 1.27), (0.22, 0.03, 1.02), (0.22, 0.03, 0.85)], 0.05, "coat"))
    _hand(parts, (0.22, 0.03, 0.82))
    # shoulder bag on a strap running across the body
    parts.append(_tube("strap", [(-0.15, 0, 1.33), (0.0, 0.08, 1.1), (0.1, 0.13, 0.9)], 0.012, "paint", 6))
    parts.append(_box("bag", (0.18, 0.06, 0.15), (0.1, 0.16, 0.8), "coat", bevel=0.01))
    # neck, head (0.88 scale), rolled hair at the nape
    parts.append(_tube("neck", [(0, 0, 1.32), (0, 0, 1.44)], 0.04, "skin"))
    parts.append(_ell("head", (0, 0, 1.42), (0.072, 0.088, 0.097), "skin", 16, 12))
    parts.append(_ell("jaw", (0, 0.02, 1.38), (0.06, 0.06, 0.045), "skin", 10, 6))
    parts.append(_ell("nose", (0, 0.086, 1.41), (0.01, 0.02, 0.022), "skin", 8, 6))
    for s in (-1, 1):
        parts.append(_ell("ear", (s * 0.072, 0, 1.4), (0.01, 0.02, 0.03), "skin", 8, 6))
    parts.append(kit.torus("hair_roll", 0.05, 0.028, 24, 8, mat="paint", loc=(0, -0.078, 1.4),
                           rot=(R(90), 0, 0)))
    # small brimmed hat at 0.8 scale, tilted 15 degrees over the hair
    M = Matrix.Translation((0, 0, 1.51)) @ Matrix.Rotation(R(15), 4, "Y") @ Matrix.Diagonal((0.8, 0.8, 0.8, 1.0))
    _hat(parts, M)


def build(args):
    a = args[0] if args else "figure"
    parts = []
    if a in ("figure_woman", "woman"):
        _woman(parts)
        name = "figure_woman"
    elif a in ("detective_seated", "seated"):
        _seated(parts)
        name = "detective_seated"
    elif a in ("figure_b", "b"):
        _man(parts, True)
        name = "figure_b"
    else:
        _man(parts, False)
        name = "figure"
    kit.join(name, parts)
