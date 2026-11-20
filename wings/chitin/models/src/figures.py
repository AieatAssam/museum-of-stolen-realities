"""Chitin Court figures: two beetle courtiers, the stag-beetle usher, the Locksmith General and her
raptorial key-arm, and the pinned queen. One script, selected by args[0]. Run through
tools/blender_build.sh. Blender: +Z up, 1 unit = 1 m; a figure's front is -Y (Godot +Z).

Shells are lofts through superellipse cross-sections along curved spines (never single blobs),
limbs are tapered keeled lens sections with flared joint collars, membranes are UV'd grids."""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import sculpt as S  # noqa: E402
import arch  # noqa: E402

X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))


# --- loft kit: shells and limbs swept through cross-sections ----------------------------------------

def _sp(v, p):
    return math.copysign(abs(v) ** p, v)


def _ortho(t):
    """Lateral and up axes for travel direction t (lateral = Z x t, so a spine running -Y gives +X)."""
    ref = Z if abs(t.z) < 0.9 else Y
    x = ref.cross(t).normalized()
    return x, t.cross(x).normalized()


def _frames(P, closed=False):
    """(tangent, lateral, up) at every station of the polyline P."""
    m = len(P)
    out = []
    for i in range(m):
        if closed:
            d = P[(i + 1) % m] - P[(i - 1) % m]
        else:
            d = P[min(i + 1, m - 1)] - P[max(i - 1, 0)]
        t = d.normalized()
        x, v = _ortho(t)
        out.append((t, x, v))
    return out


def _cr(pts, steps):
    """Catmull-Rom spine through pts, `steps` samples per span."""
    P = [Vector(p) for p in pts]
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2 = P[max(i - 1, 0)], P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(steps):
            t = k / steps
            t2 = t * t
            t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out


def _along(pts, spec, steps=4):
    """Spine through pts with spec (one tuple per control point) interpolated along it: [(point, values)]."""
    P = _cr(pts, steps)
    out = []
    for k in range(len(P)):
        t = k / steps
        i = min(int(t), len(pts) - 2)
        f = t - i
        vals = tuple(a + (b - a) * f for a, b in zip(spec[i], spec[i + 1]))
        out.append((P[k], vals))
    return out


def _spec(hws, hhs, off=0.0):
    return [(a, b, off) for a, b in zip(hws, hhs)]


def loft(name, st, mat, n=12, exp=2.0, low=0.5, keel=0.0, closed=False, uv=False):
    """Loft a shell through stations st = [(centre, half_w, half_h, off)]. Each station is a superellipse
    ring: half_w across the lateral axis (centred on off), half_h up. The underside is squashed by low,
    keel lifts the top centre line. Open ends close to a point."""
    P = [Vector(s[0]) for s in st]
    fr = _frames(P, closed)
    m = len(st)
    bm = bmesh.new()
    rings, uvs = [], {}
    for i, (_c, w, h, off) in enumerate(st):
        _t, x, v = fr[i]
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            ca, sa = math.cos(a), math.sin(a)
            pz = h * _sp(sa, 2.0 / exp)
            if sa < 0:
                pz *= low
            else:
                pz += keel * h * (1 - abs(ca))
            vt = bm.verts.new(P[i] + x * (off + w * _sp(ca, 2.0 / exp)) + v * pz)
            uvs[vt] = (i / max(m - 1, 1), k / n)
            ring.append(vt)
        rings.append(ring)
    for i in range(m if closed else m - 1):
        a, b = rings[i], rings[(i + 1) % m]
        for k in range(n):
            bm.faces.new((a[k], b[k], b[(k + 1) % n], a[(k + 1) % n]))
    if not closed:
        for idx, sgn in ((0, -1.0), (m - 1, 1.0)):
            tip = bm.verts.new(P[idx] + fr[idx][0] * sgn * st[idx][2] * 0.9)
            uvs[tip] = (idx / max(m - 1, 1), 0.0)
            ring = rings[idx]
            for k in range(n):
                bm.faces.new((ring[k], ring[(k + 1) % n], tip))
    if uv:
        layer = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for lp in f.loops:
                lp[layer].uv = uvs.get(lp.vert, (0.5, 0.5))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return S.to_obj(name, bm, mat)


def _dome(name, pts, spec, mat, n=14, exp=2.2, low=0.5, keel=0.0, uv=False, steps=4):
    """A loft along a spine: returns (object, samples) so ridges can be laid on its surface."""
    smp = _along(pts, spec, steps)
    st = [(p, v[0], v[1], v[2]) for p, v in smp]
    return loft(name, st, mat, n=n, exp=exp, low=low, keel=keel, uv=uv), smp


def _lines(name, smp, fracs, mat, w=0.011, h=0.009):
    """Thin raised ridges laid across a dome surface, at lateral fractions f (0 = seam, 1 = outer edge)."""
    fr = _frames([p for p, _ in smp])
    out = []
    for k, f in enumerate(fracs):
        pts = []
        for (p, v), (_t, x, up) in zip(smp, fr):
            sgn = 1.0 if v[2] >= 0 else -1.0
            lat = v[2] + sgn * v[0] * (2 * f - 1)
            zt = v[1] * math.sqrt(max(0.0, 1 - (2 * f - 1) ** 2))
            pts.append(p + x * lat + up * (zt - 0.2 * h))
        out.append(loft("%s_line%d" % (name, k), [(q, w, h, 0.0) for q in pts], mat, n=6))
    return out


def _elytron(name, s, spine, hws, hhs, mat, sd, striae=6, low=0.45):
    """One elytron: a domed shell from the centre seam (x = 0) out to 2*hw, parted by a sliver at the
    rear, with `striae` shallow longitudinal ridges across its dome."""
    spec = [(hw, hh, s * hw) for hw, hh in zip(hws, hhs)]
    spec[0] = (spec[0][0], spec[0][1], s * (spec[0][0] + 0.012))
    body, smp = _dome(name, spine, spec, mat, n=14, exp=2.2, low=low)
    return [body] + _lines(name, smp, [(k + 0.5) / striae for k in range(striae)], mat)


def _plate(name, pts, spec, mat, rim=None, exp=2.6, low=0.6):
    """A hard plate (pronotum, head) lofted along its spine; rim = bead radius for a raised edge."""
    body, smp = _dome(name, pts, spec, mat, n=16, exp=exp, low=low)
    out = [body]
    if rim:
        fr = _frames([p for p, _ in smp])
        left, right = [], []
        for (p, v), (_t, x, _up) in zip(smp, fr):
            left.append(p + x * v[0] * 0.98)
            right.append(p - x * v[0] * 0.98)
        out.append(loft(name + "_rim", [(q, rim, rim, 0.0) for q in left + right[::-1]], mat, n=8, closed=True))
    return out


def _lens(name, pts, ws, mat, hr=0.6, keel=0.35):
    """A tapered keeled lens section (limb segment, claw, mandible): ws = half width per control point."""
    obj, _ = _dome(name, pts, [(w, w * hr, 0.0) for w in ws], mat, n=10, exp=2.0, low=0.6, keel=keel, steps=3)
    return obj


def _collar(name, c, d, w, h, mat):
    """A flared joint collar: a short ring round the limb axis d, flaring out at both lips."""
    d = Vector(d).normalized()
    c = Vector(c)
    st = [(c - d * w * 0.25, w * 1.35, h * 1.35, 0.0), (c, w * 1.1, h * 1.1, 0.0), (c + d * w * 0.25, w * 1.35, h * 1.35, 0.0)]
    return loft(name, st, mat, n=12, exp=2.0, low=1.0)


def _thorn(name, base, d, length, r, mat):
    """A short tapering spine or tooth, pointing along d."""
    base = Vector(base)
    d = Vector(d).normalized()
    st = [(base, r, r, 0.0), (base + d * length * 0.5, r * 0.55, r * 0.55, 0.0), (base + d * length, r * 0.1, r * 0.1, 0.0)]
    return loft(name, st, mat, n=8, exp=2.0, low=1.0)


def _ring(name, c, ua, va, ra, rb, r, mat):
    """A raised bead ring round centre c in the plane of ua and va (radii ra, rb)."""
    st = []
    for k in range(24):
        a = 2 * math.pi * k / 24
        st.append((Vector(c) + ua * (ra * math.cos(a)) + va * (rb * math.sin(a)), r, r, 0.0))
    return loft(name, st, mat, n=8, closed=True)


def _torus_at(name, c, d, r, minor, mat):
    ob = kit.torus(name, major=r, minor=minor, seg=16, rseg=6, mat=mat)
    ob.location = Vector(c)
    ob.rotation_euler = Z.rotation_difference(Vector(d).normalized()).to_euler()
    return ob


def _beads(name, pts, nb, r0, r1, mat, club=1.0):
    """A segmented antenna: nb beads tapering from r0 to r1 along the spine, the last one clubbed."""
    P = _cr(pts, 8)
    acc = [0.0]
    for a, b in zip(P, P[1:]):
        acc.append(acc[-1] + (b - a).length)
    bm = bmesh.new()
    for k in range(nb):
        u = k / (nb - 1)
        target = u * acc[-1]
        j = 0
        while j < len(P) - 2 and acc[j + 1] < target:
            j += 1
        seg = acc[j + 1] - acc[j]
        f = (target - acc[j]) / seg if seg > 1e-9 else 0.0
        c = P[j].lerp(P[j + 1], min(max(f, 0.0), 1.0))
        r = (r0 + (r1 - r0) * u) * (club if k == nb - 1 else 1.0)
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        bmesh.ops.translate(bm, vec=c, verts=res["verts"])
    return S.to_obj(name, bm, mat)


def _leg(pre, pts, r, seed, spines=2, mat="carapace_dull", claw="carapace"):
    """A segmented insect leg through pts = hip, knee, ankle, toe. Four keeled lens segments (thigh,
    shin, two tarsomeres), a flared collar at every joint, thorns on the thigh and a pair of curved
    claws at the toe."""
    P = [Vector(p) for p in pts]
    T = P[2].lerp(P[3], 0.5)
    J = [P[0], P[1], P[2], T, P[3]]
    ws = [r, r * 0.8, r * 0.6, r * 0.45, r * 0.3]
    out = []
    for i in range(4):
        out.append(_lens("%s_seg%d" % (pre, i), [J[i], J[i + 1]], [ws[i], ws[i + 1]], mat))
    for i in range(4):
        d = J[min(i + 1, 4)] - J[max(i - 1, 0)]
        out.append(_collar("%s_joint%d" % (pre, i), J[i], d, ws[i], ws[i] * 0.85, mat))
    d = (P[1] - P[0]).normalized()
    side = d.cross(Z)
    side = side.normalized() if side.length > 1e-3 else X
    for k in range(spines):
        base = P[0].lerp(P[1], 0.35 + 0.3 * (k % 2))
        s = 1 if k % 2 == 0 else -1
        dirv = side * (0.7 * s) + Z * 0.8 - d * 0.2
        out.append(_thorn("%s_spine%d" % (pre, k), base, dirv, r * 3.0, r * 0.3, claw))
    dt = (P[3] - P[2]).normalized()
    side = dt.cross(Z)
    side = side.normalized() if side.length > 1e-3 else X
    for k, s in enumerate((1, -1)):
        pts_c = [P[3], P[3] + dt * r * 1.2 + side * (s * r * 0.6), P[3] + dt * r * 2.6 + side * (s * r * 1.0) - Z * (r * 0.5)]
        out.append(_lens("%s_claw%d" % (pre, k), pts_c, [r * 0.36, r * 0.2, r * 0.03], claw, hr=0.7))
    return out


def _eye(name, c, size, seed):
    return S.blob(name, size, c, "ink", seed, lump=0.0, subdiv=2)


def torus_ring(name, major, minor, loc, mat):
    return kit.torus(name, major=major, minor=minor, seg=24, rseg=6, mat=mat, loc=loc)


# --- shared pieces ----------------------------------------------------------------------------------

def _pitch(p, ang, piv):
    """Tip point p about the X axis through piv; positive ang drops the front (-Y) and lifts the rear."""
    d = Vector(p) - Vector(piv)
    c, s = math.cos(ang), math.sin(ang)
    return Vector((d.x, d.y * c - d.z * s, d.y * s + d.z * c)) + Vector(piv)


def _hull(name, pts, mat, levels=1):
    """Convex hull of pts, rounded by a subdivision pass (triangular heads, rounded knobs)."""
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(Vector(p))
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    ob = S.to_obj(name, bm, mat)
    mod = ob.modifiers.new("smooth", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob


def _tube(name, pts, radii, mat, seed, sides=12, steps=6):
    """A smooth capped rod along a polyline (staffs, shafts)."""
    smp = _along(pts, [(r,) for r in radii], steps)
    st = [(p, v[0], v[0], 0.0) for p, v in smp]
    return loft(name, st, mat, n=sides, exp=2.0, low=1.0)


def _antenna(name, pts, r0, r1, mat, joints=4, club=1.0):
    """A segmented antenna: a tapering lofted rod along pts, a flared collar at each joint, clubbed tip."""
    n = len(pts)
    spec = [(r0 + (r1 - r0) * i / (n - 1), r0 + (r1 - r0) * i / (n - 1), 0.0) for i in range(n)]
    spec[-1] = (spec[-1][0] * club, spec[-1][0] * club, 0.0)
    obj, smp = _dome(name, pts, spec, mat, n=8, exp=2.0, low=1.0, steps=6)
    out = [obj]
    for j in range(1, joints):
        i = int(round(j * (n - 1) / joints)) * 6
        p, v = smp[i]
        d = (smp[min(i + 1, len(smp) - 1)][0] - smp[max(i - 1, 0)][0]).normalized()
        out.append(_collar("%s_joint%d" % (name, j), p, d, v[0] * 1.3, v[0] * 1.3, mat))
    return out


def _chain(name, pts, mat, r=0.07, minor=0.014):
    """A row of chain links, alternating between the XZ and YZ planes."""
    out = []
    for k, p in enumerate(pts):
        out.append(_torus_at("%s_link%d" % (name, k), p, Y if k % 2 == 0 else X, r, minor, mat))
    return out


# --- courtiers --------------------------------------------------------------------------------------

_KNEEL_LEGS = [
    ([(0.2, -0.12, 0.36), (0.34, -0.42, 0.14), (0.24, -0.54, 0.045), (0.12, -0.74, 0.035)], 0.05),
    ([(0.24, 0.1, 0.34), (0.5, 0.14, 0.14), (0.4, 0.3, 0.05), (0.32, 0.5, 0.035)], 0.055),
    ([(0.22, 0.36, 0.34), (0.56, 0.36, 0.12), (0.46, 0.56, 0.05), (0.38, 0.8, 0.035)], 0.06),
]
_STAND_LEGS = [
    ([(0.2, -0.12, 0.62), (0.44, -0.22, 0.5), (0.5, -0.24, 0.12), (0.42, -0.5, 0.04)], 0.05),
    ([(0.24, 0.1, 0.58), (0.6, 0.12, 0.42), (0.56, 0.3, 0.1), (0.5, 0.52, 0.04)], 0.06),
    ([(0.22, 0.36, 0.56), (0.56, 0.46, 0.46), (0.46, 0.62, 0.1), (0.4, 0.88, 0.04)], 0.07),
]
_HOLD = [(0.2, -0.12, 0.62), (0.4, -0.3, 0.56), (0.46, -0.44, 0.7), (0.5, -0.5, 0.72)]  # right foreleg on the staff


def _courtier(name, pose):
    """A beetle courtier. pose: 'kneel' (body low, forelegs folded, head bowed, silk mantle), 'bow'
    (standing, upper body tipped forward, wax seal on a silk sash), 'stand' (upright, brass key-staff in
    the right foreleg, brass circlet). Origin between the feet on the floor; front -Y."""
    sd = {"kneel": 200, "bow": 210, "stand": 220}[pose]
    shell = "carapace"
    tip, piv = 0.0, (0.0, 0.2, 0.7)
    if pose == "kneel":
        el = dict(spine=[(0, 0.8, 0.34), (0, 0.42, 0.4), (0, 0.08, 0.42), (0, -0.26, 0.36)],
                  hw=[0.13, 0.2, 0.21, 0.17], hh=[0.14, 0.22, 0.23, 0.18])
        pro = dict(spine=[(0, 0.02, 0.56), (0, -0.2, 0.58), (0, -0.4, 0.5)], hw=[0.2, 0.23, 0.18], hh=[0.16, 0.2, 0.17])
        head = dict(spine=[(0, -0.38, 0.5), (0, -0.52, 0.38), (0, -0.62, 0.22)], hw=[0.16, 0.18, 0.14], hh=[0.14, 0.15, 0.13])
        eye_c, eye_s = (0.16, -0.56, 0.4), (0.18, 0.18, 0.19)
        ant = [(0.1, -0.5, 0.46), (0.24, -0.7, 0.36), (0.32, -0.92, 0.14)]
        mand = [(0.07, -0.6, 0.45), (0.13, -0.74, 0.42), (0.08, -0.84, 0.36)]
        legs, nb = _KNEEL_LEGS, 9
    else:
        el = dict(spine=[(0, 0.78, 0.5), (0, 0.42, 0.6), (0, 0.08, 0.63), (0, -0.26, 0.56)],
                  hw=[0.13, 0.2, 0.21, 0.17], hh=[0.2, 0.3, 0.31, 0.24])
        pro = dict(spine=[(0, 0.02, 0.82), (0, -0.22, 0.86), (0, -0.44, 0.78)], hw=[0.22, 0.25, 0.19], hh=[0.2, 0.24, 0.2])
        head = dict(spine=[(0, -0.3, 1.0), (0, -0.5, 1.02), (0, -0.72, 0.98)], hw=[0.17, 0.19, 0.16], hh=[0.15, 0.17, 0.16])
        eye_c, eye_s = (0.18, -0.52, 1.07), (0.2, 0.2, 0.22)
        ant = [(0.1, -0.42, 1.2), (0.26, -0.5, 1.36), (0.36, -0.62, 1.3)]
        mand = [(0.08, -0.64, 0.9), (0.16, -0.84, 0.92), (0.09, -0.96, 0.8)]
        legs, nb = _STAND_LEGS, 11
        if pose == "bow":
            tip = 0.35
    club = 1.9

    def P(pts):
        return [_pitch(p, tip, piv) for p in pts]

    parts = []
    el_sp = P(el["spine"])
    for s in (-1, 1):
        parts += _elytron("%s_elytra%d" % (name, s), s, el_sp, el["hw"], el["hh"], shell, sd + s)
    parts += _plate(name + "_pronotum", P(pro["spine"]), _spec(pro["hw"], pro["hh"]), shell, rim=0.022, exp=2.6)
    parts += _plate(name + "_head", P(head["spine"]), _spec(head["hw"], head["hh"]), shell, exp=2.2)
    for s in (-1, 1):
        ex, ey, ez = eye_c
        parts.append(_eye("%s_eye%d" % (name, s), _pitch((s * ex, ey, ez), tip, piv), eye_s, sd + 3))
        parts.append(_lens("%s_mand%d" % (name, s), P([(s * x, y, z) for x, y, z in mand]), [0.035, 0.03, 0.015],
                           "carapace_dull", hr=0.7))
        parts += _antenna("%s_ant%d" % (name, s), P([(s * x, y, z) for x, y, z in ant]), 0.032, 0.02,
                          "carapace_dull", joints=4, club=club)

    if pose == "kneel":
        mantle = [(-0.38, 0.0, 0.6), (-0.2, -0.06, 0.68), (0, -0.1, 0.7), (0.2, -0.06, 0.68), (0.38, 0.0, 0.6)]
        parts.append(_dome(name + "_mantle", mantle, _spec([0.2, 0.23, 0.24, 0.23, 0.2], [0.03, 0.05, 0.035, 0.05, 0.03]),
                           "silk", n=12, exp=2.0, low=1.0)[0])
    elif pose == "bow":
        sash = P([(-0.16, -0.24, 0.9), (-0.06, -0.06, 0.96), (0.06, 0.14, 0.94), (0.2, 0.36, 0.82)])
        parts.append(_lens(name + "_sash", sash, [0.028, 0.032, 0.032, 0.028], "silk", hr=0.5, keel=0.0))
        parts.append(S.blob(name + "_seal", (0.1, 0.1, 0.035), P([(0.0, -0.02, 0.97)])[0], "wax", sd + 7, lump=0.0, subdiv=2))
    else:
        parts.append(torus_ring(name + "_circlet", 0.15, 0.016, (0, -0.48, 1.18), "brass"))

    for li, (pts, r) in enumerate(legs):
        for s in (-1, 1):
            if pose == "stand" and li == 0 and s == 1:
                pts_s = [(s * x, y, z) for x, y, z in _HOLD]
            else:
                pts_s = [(s * x, y, z) for x, y, z in pts]
            parts += _leg("%s_L%d%s" % (name, li, "rl"[(s + 1) // 2]), pts_s, r, sd + 10 * li + (s + 1))

    if pose == "stand":
        parts.append(_tube(name + "_staff", [(0.5, -0.5, 0.0), (0.5, -0.5, 1.3)], [0.022, 0.02], "brass", sd, sides=8, steps=3))
        parts.append(_torus_at(name + "_staffbow", (0.5, -0.5, 1.36), Y, 0.07, 0.014, "brass"))
        parts.append(S.slab(name + "_staffbit", (0.03, 0.1, 0.14), (0.5, -0.5, 1.2), "brass", sd + 5, lump=0.0, bevel=0.005, cuts=2))
    return parts


def B_courtier_a():
    """Kneeling courtier: body low, forelegs folded under, head bowed, silk mantle over the pronotum."""
    kit.join("courtier_a", _courtier("courtier_a", "kneel"))


def B_courtier_b():
    """Bowing courtier: standing, upper body tipped forward, wax seal on a silk sash across the elytra."""
    kit.join("courtier_b", _courtier("courtier_b", "bow"))


def B_courtier_c():
    """Standing courtier holding a brass key-staff (1.3 m, key-bow at the top) in the right foreleg."""
    kit.join("courtier_c", _courtier("courtier_c", "stand"))


# --- usher ------------------------------------------------------------------------------------------

def B_usher():
    """Stag-beetle usher in livery, standing on its hind legs (origin at centre, feet at z -1.15). Stag
    mandibles, silk tabard with brass buttons, a brass chain of office across the chest, and a brass staff
    along Y, 3.0 m end to end, held in the forelimbs."""
    sd = 400
    parts = []
    for s in (-1, 1):
        parts += _elytron("u_elytra%d" % s, s, [(0, 0.75, -0.45), (0, 0.35, -0.25), (0, 0.0, -0.22), (0, -0.22, -0.32)],
                          [0.12, 0.18, 0.195, 0.16], [0.3, 0.46, 0.49, 0.38], "carapace", sd + s)
    parts += _plate("u_thorax", [(0, 0.0, 0.36), (0, -0.2, 0.42), (0, -0.36, 0.34)], _spec([0.24, 0.28, 0.22], [0.22, 0.25, 0.2]),
                    "carapace", rim=0.02, exp=2.4)
    parts += _plate("u_head", [(0, -0.1, 0.86), (0, -0.26, 0.9), (0, -0.42, 0.84)], _spec([0.18, 0.22, 0.16], [0.17, 0.2, 0.16]),
                    "carapace", exp=2.2)
    # neck: bridges the head plate down onto the thorax so the head is not floating
    parts.append(S.blob("u_neck", (0.26, 0.3, 0.6), (0, -0.2, 0.6), "carapace", sd + 5, lump=0.01, subdiv=3))
    parts.append(S.slab("u_tabard", (0.4, 0.07, 0.62), (0, -0.3, -0.12), "silk", sd, lump=0.012, bevel=0.03, cuts=6))
    for k, (x, z) in enumerate([(-0.13, -0.05), (0.13, -0.05), (-0.13, -0.3), (0.13, -0.3)]):
        parts.append(S.blob("u_button%d" % k, (0.04, 0.04, 0.04), (x, -0.37, z), "brass", sd + k, lump=0.0, subdiv=2))
    # brass chain of office: nine links sagging across the tabard
    chain = []
    for k in range(9):
        t = -1 + 2 * k / 8
        chain.append((0.26 * t, -0.42, 0.2 - 0.36 * (1 - t * t)))
    parts += _chain("u_chain", chain, "brass", r=0.05, minor=0.011)
    for s in (-1, 1):
        # stag mandibles: long, curved, with an inner tooth
        parts.append(_lens("u_mand%d" % s, [(s * 0.12, -0.42, 0.9), (s * 0.3, -0.72, 0.98), (s * 0.27, -0.98, 0.9)],
                           [0.05, 0.045, 0.02], "carapace", hr=0.7))
        parts.append(_thorn("u_tine%d" % s, (s * 0.2, -0.7, 0.96), (s * -0.4, -0.2, 0.8), 0.12, 0.022, "carapace"))
        parts.append(_eye("u_eye%d" % s, (s * 0.14, -0.36, 0.92), (0.16, 0.18, 0.2), sd))
        parts += _antenna("u_ant%d" % s, [(s * 0.08, -0.3, 1.04), (s * 0.18, -0.42, 1.08), (s * 0.12, -0.5, 1.02)],
                          0.025, 0.015, "carapace_dull", joints=3, club=1.6)
        # hind legs standing: knee forward and out, foot planted at z -1.15
        parts += _leg("u_hind%d" % s, [(s * 0.22, 0.1, -0.4), (s * 0.42, -0.05, -0.72), (s * 0.3, 0.12, -1.05), (s * 0.28, 0.36, -1.14)],
                      0.07, sd + 20 + s, spines=0)
        # middle legs bent back, feet planted behind
        parts += _leg("u_mid%d" % s, [(s * 0.3, 0.0, -0.1), (s * 0.5, 0.22, -0.35), (s * 0.44, 0.42, -0.55), (s * 0.34, 0.6, -1.12)],
                      0.05, sd + 30 + s, spines=0)
        # forelimbs close on the staff
        parts += _leg("u_fore%d" % s, [(s * 0.28, -0.2, 0.05), (s * 0.44, -0.46, -0.02), (s * 0.2, -0.58, -0.08), (s * 0.08, -0.62, -0.1)],
                      0.05, sd + 40 + s, spines=1)
    parts.append(_tube("u_staff", [(0, -1.44, -0.1), (0, 1.44, -0.1)], [0.03, 0.03], "brass", sd, sides=10, steps=1))
    for k, y in enumerate((-1.44, 1.44)):
        parts.append(S.blob("u_finial%d" % k, (0.12, 0.12, 0.12), (0, y, -0.1), "brass", sd + k, lump=0.0, subdiv=2))
    kit.join("usher", parts)


# --- the Locksmith General --------------------------------------------------------------------------

def _am(name, mat, fn):
    """One arch.Mesh piece (superq, thick sheet, grids) built by fn(m), returned as an object."""
    m = arch.Mesh()
    fn(m)
    m.done(name, mat)
    return arch.finish(name)


def _mleg(pre, P, r):
    """A mantis walking leg through hip, knee, ankle, toe: three tapered keeled segments, flared joint collars,
    and a pair of claws. The tarsus runs flat along the ground."""
    P = [Vector(p) for p in P]
    ws = [(r, r * 0.8), (r * 0.8, r * 0.55), (r * 0.55, r * 0.3)]
    out = []
    for i in range(3):
        out.append(_lens("%s_seg%d" % (pre, i), [P[i], P[i + 1]], list(ws[i]), "carapace_dull", hr=0.65, keel=0.3))
    for i in (1, 2):
        out.append(_collar("%s_joint%d" % (pre, i), P[i], P[i + 1] - P[i - 1], ws[i - 1][1], ws[i - 1][1] * 0.85,
                           "carapace_dull"))
    dt = Vector((P[3].x - P[2].x, P[3].y - P[2].y, 0.0)).normalized()
    side = dt.cross(Z).normalized()
    for s in (1, -1):
        pts = [P[3], P[3] + dt * r * 1.0 + side * (s * r * 0.5), P[3] + dt * r * 2.2 + side * (s * r * 0.8) - Z * r * 0.1]
        out.append(_lens("%s_claw%d" % (pre, s), pts, [r * 0.3, r * 0.18, r * 0.03], "carapace", hr=0.7))
    return out


def B_general():
    """The Locksmith General: a praying mantis, origin at the feet, front to -Y. Triangular head with two
    bulging compound eyes, a 3 m raised prothorax with a brass-studded yoke at the forelimb sockets
    (+-1.6, 0, 5.0), a leaf-like six-segment abdomen, two folded membrane wings with veins, a silk sash
    and a brass key chain on the chest, and four walking legs. The raptorial forelimbs are the separate
    general_arm model, mounted at (+-1.6, 0, 5.0)."""
    sd = 500
    parts = []
    Y0, Y1 = 1.9, 6.8  # abdomen runs from the thorax to the tail

    def tt(y):
        return (y - Y0) / (Y1 - Y0)

    def zc(y):  # abdomen centre line, tail raised a little
        return 2.25 + 0.35 * tt(y)

    def wab(y):  # half width: leaf-shaped, widest mid-body
        return max(0.03, 0.72 * math.sin(math.pi * (0.1 + 0.8 * tt(y))))

    def hab(y):
        return 0.5 * wab(y)

    def top(x, y):  # height of the abdomen's top surface at lateral x
        r = min(1.0, abs(x) / wab(y))
        return zc(y) + hab(y) * math.sqrt(max(0.0, 1.0 - r * r))

    # abdomen: six overlapping segments, each a lofted plate whose flared back rim overlaps the next
    for k in range(6):
        y0 = Y0 + k * 0.8
        st = []
        for f, scl in ((0.0, 0.8), (0.45, 1.0), (0.9, 1.04 if k < 5 else 0.3)):
            y = y0 + f
            st.append(((0, y, zc(y)), wab(y) * scl, hab(y) * scl, 0.0))
        parts.append(loft("g_seg%d" % k, st, "carapace", n=14, exp=2.2, low=0.6))

    # folded wings: leaf membranes lying over the abdomen, veins as thin ridges
    def wing_fn(s, dz):
        def fn(u, v):
            y = 1.5 + 5.4 * u
            L = 0.85 * wab(y) * (math.sin(math.pi * u) ** 0.25)
            x = s * (0.02 + (L - 0.02) * v)
            return (x, y, top(x, y) + dz)
        return fn

    wm = arch.Mesh(uv=True)
    for s in (-1, 1):
        arch.thick_sheet(wm, wing_fn(s, 0.05), wing_fn(s, 0.01), 30, 6)
    wm.done("g_wings", "membrane")
    parts.append(arch.finish("g_wings"))
    for s in (-1, 1):
        for vf in (0.3, 0.55, 0.8):
            pts = []
            for k in range(14):
                u = 0.08 + 0.87 * k / 13
                y = 1.5 + 5.4 * u
                L = 0.85 * wab(y) * (math.sin(math.pi * u) ** 0.25)
                x = s * (0.02 + (L - 0.02) * vf)
                pts.append((x, y, top(x, y) + 0.07))
            parts.append(kit.tube("g_vein%d_%d" % (s, int(vf * 10)), pts, 0.014, sides=4, mat="carapace_dull"))

    # silk sash across the abdomen, lying on the wings
    sp = Vector((1.1, 3.8, 0)).normalized()
    perp = Vector((-sp.y, sp.x, 0))

    def sash_fn(dz):
        def fn(u, v):
            cx, cy = -0.55 + 1.1 * u, 2.6 + 3.8 * u
            off = (v - 0.5) * 0.24
            x, y = cx + perp.x * off, cy + perp.y * off
            return (x, y, top(x, y) + 0.12 + dz)
        return fn

    sm = arch.Mesh()
    arch.thick_sheet(sm, sash_fn(0.0), sash_fn(-0.03), 20, 2)
    sm.done("g_sash", "silk")
    parts.append(arch.finish("g_sash"))

    # prothorax: a 3 m neck rising at 55 degrees from the front of the abdomen, widening into the yoke
    parts.append(_dome("g_neck", [(0, 1.7, 2.6), (0, 0.7, 4.0), (0, -0.45, 5.6)],
                       [(0.26, 0.24, 0), (0.2, 0.2, 0), (0.23, 0.22, 0)], "carapace", n=14, exp=2.2, low=0.6)[0])
    # shoulder yoke: carries the forelimb sockets at (+-1.6, 0, 5)
    parts.append(_dome("g_yoke", [(-1.6, 0.0, 5.0), (-0.8, -0.15, 5.12), (0, -0.2, 5.15), (0.8, -0.15, 5.12),
                                  (1.6, 0.0, 5.0)],
                       [(0.25, 0.32, 0), (0.2, 0.3, 0), (0.22, 0.3, 0), (0.2, 0.3, 0), (0.25, 0.32, 0)],
                       "carapace", n=14, exp=2.2, low=0.6)[0])
    # brass-studded collar round the neck, and a chain of five keys hanging from it
    d = Vector((0, -0.59, 0.81)).normalized()
    va = d.cross(X).normalized()
    C = Vector((0, 0.4, 4.4))
    parts.append(_ring("g_collar", C, X, va, 0.3, 0.28, 0.05, "brass"))
    for k in range(10):
        a = 2 * math.pi * k / 10
        c = C + X * (0.3 * math.cos(a)) + va * (0.28 * math.sin(a))
        parts.append(_am("g_stud%d" % k, "brass", lambda m, c=c: arch.superq(m, c, (0.04, 0.035, 0.04), 0.6, 0.6, nu=8, nv=5)))
    chain = []
    for k in range(9):
        t = -1.0 + k / 4.0
        chain.append((0.3 * t, 0.35 - 0.5 * (1 - t * t), 4.3 - 0.75 * (1 - t * t)))
    parts += _chain("g_chain", chain, "brass", r=0.05, minor=0.012)
    for k, x in enumerate((-0.2, -0.1, 0.0, 0.1, 0.2)):
        t = x / 0.3
        yy, zz = 0.35 - 0.5 * (1 - t * t), 4.3 - 0.75 * (1 - t * t)
        parts.append(_lens("g_key%d" % k, [(x, yy, zz - 0.06), (x, yy, zz - 0.6)], [0.03, 0.03], "brass", hr=0.8))
        parts.append(S.slab("g_keybit%d" % k, (0.05, 0.12, 0.18), (x, yy, zz - 0.66), "brass", sd + 50 + k,
                            lump=0.0, bevel=0.01, cuts=2))

    # triangular head: wide at the eyes, drawn to a point at the mouth
    parts.append(_hull("g_head", [(-0.95, -0.9, 6.5), (0.95, -0.9, 6.5), (0, -0.1, 6.1), (-0.4, -1.8, 6.1),
                                  (0.4, -1.8, 6.1), (0, -2.0, 5.2), (0, -1.2, 6.9), (-0.5, -0.5, 5.6),
                                  (0.5, -0.5, 5.6)], "carapace", levels=1))
    for s in (-1, 1):
        parts.append(_am("g_eye%d" % s, "ink",
                         lambda m, s=s: arch.superq(m, (s * 0.78, -1.25, 6.3), (0.46, 0.38, 0.46), 1.0, 1.0,
                                                    nu=16, nv=10)))
        parts.append(_lens("g_mand%d" % s, [(s * 0.12, -1.85, 5.6), (s * 0.2, -2.15, 5.3), (s * 0.12, -2.05, 5.05)],
                           [0.08, 0.06, 0.02], "carapace_dull", hr=0.7))
        parts += _antenna("g_ant%d" % s, [(s * 0.35, -1.0, 6.7), (s * 0.6, -0.4, 7.5), (s * 0.95, 0.7, 8.0)],
                          0.045, 0.02, "carapace_dull", joints=6)

    # walking legs: two pairs, femur up to a high knee, tibia down, flat tarsus on the ground
    for s in (-1, 1):
        parts += _mleg("g_mid%d" % s, [(s * 0.5, 2.4, 2.3), (s * 1.9, 2.0, 4.1), (s * 2.6, 1.7, 0.35),
                                       (s * 2.85, 1.5, 0.05)], 0.13)
        parts += _mleg("g_hind%d" % s, [(s * 0.5, 3.8, 2.3), (s * 2.2, 3.9, 4.2), (s * 2.7, 3.7, 0.35),
                                        (s * 2.95, 3.6, 0.05)], 0.13)
    kit.join("general", parts)


def B_general_arm():
    """ONE raptorial forelimb at the shoulder pivot (origin), reaching 5.35 m toward -Y. Segmented: coxa,
    spiny femur, serrated tibia, a short hand, and an ornate brass key (bow, shaft, wards) for the tip."""
    sd = 600
    parts = [
        _dome("ga_coxa", [(0, 0.25, 0), (0, -0.2, 0), (0, -0.6, -0.02)], _spec([0.4, 0.45, 0.36], [0.42, 0.45, 0.4]),
              "carapace", n=14, exp=2.2, low=0.6)[0],
        _torus_at("ga_socket", (0, 0, 0), Y, 0.5, 0.06, "brass"),
        _collar("ga_trochanter", (0, -0.85, 0.05), Y, 0.3, 0.28, "carapace_dull"),
    ]
    fem = [(0, -0.4, 0.0), (0, -1.5, 0.22), (0, -2.7, 0.5)]
    parts.append(_lens("ga_femur", fem, [0.36, 0.3, 0.26], "carapace", hr=0.7))
    for k in range(5):
        p = Vector(fem[0]).lerp(Vector(fem[1]), 0.15 + 0.2 * k) if k < 3 else Vector(fem[1]).lerp(Vector(fem[2]), 0.3 * (k - 2))
        parts.append(_thorn("ga_fspine%d" % k, p - Z * 0.28, -Z * 0.6 - Y * 0.5, 0.3, 0.045, "carapace_dull"))
    parts.append(_torus_at("ga_knee", (0, -2.7, 0.5), Y, 0.3, 0.07, "brass"))
    tib = [(0, -2.7, 0.5), (0, -3.6, 0.22), (0, -4.45, 0.0)]
    parts.append(_lens("ga_tibia", tib, [0.28, 0.22, 0.16], "carapace_dull", hr=0.7))
    for k in range(4):
        p = Vector(tib[0]).lerp(Vector(tib[1]), 0.2 + 0.2 * k)
        parts.append(_thorn("ga_tspine%d" % k, p + Z * 0.18, Z * 0.5 + Y * 0.5, 0.2, 0.03, "carapace_dull"))
    parts.append(_lens("ga_hand", [(0, -4.45, 0.0), (0, -4.8, -0.05)], [0.14, 0.1], "carapace", hr=0.8))
    # the key: bow at the wrist, shaft, and a bit of wards at the tip
    bow = Vector((0, -4.95, -0.05))
    parts.append(_torus_at("ga_bow", bow, Y, 0.22, 0.045, "brass"))
    parts.append(_torus_at("ga_bow2", bow, Y, 0.13, 0.03, "brass"))
    for k in range(8):
        a = 2 * math.pi * k / 8
        c = bow + X * (0.22 * math.cos(a)) + Z * (0.22 * math.sin(a))
        parts.append(S.blob("ga_stud%d" % k, (0.05, 0.05, 0.05), c, "brass", sd + 10 + k, lump=0.0, subdiv=2))
    parts.append(_lens("ga_shaft", [(0, -4.95, -0.05), (0, -5.2, -0.05)], [0.05, 0.05], "brass", hr=1.0))
    parts.append(S.slab("ga_bit", (0.1, 0.2, 0.5), (0, -5.27, -0.05), "brass", sd + 31, lump=0.0, bevel=0.02, cuts=2))
    for k, z in enumerate((-0.25, -0.08, 0.1, 0.26)):
        for s in (-1, 1):
            parts.append(S.slab("ga_ward%d%d" % (k, s), (0.05, 0.08, 0.06), (s * 0.09, -5.27, z - 0.05), "brass",
                                sd + 40 + 2 * k + s, lump=0.0, bevel=0.005, cuts=1))
    kit.join("general_arm", parts)


# --- the pinned queen -------------------------------------------------------------------------------
# Built on the arch.py mesh helpers (Mesh, loft, grid, thick_sheet, sweep, superq, finish). Lies in XY,
# dorsal +Z, head -Y, abdomen +Y, origin at the thorax centre. The thorax is a lens-section ring whose
# inner edge is the r 1.0 bore for the pin; nothing else comes within 0.98 of the Z axis.

def q_tap(r0, r1, n=8):
    """Section factory for arch.sweep: a round section tapering from r0 to r1 along the path."""
    def sec(t):
        r = r0 + (r1 - r0) * t
        return [(r * math.cos((2.0 * math.pi) * k / n), r * math.sin((2.0 * math.pi) * k / n)) for k in range(n)]
    return sec


def q_frame(d):
    """Two unit vectors perpendicular to d."""
    d = Vector(d).normalized()
    n1 = d.cross(Z)
    if n1.length < 1e-4:
        n1 = d.cross(X)
    n1.normalize()
    return n1, d.cross(n1).normalized()


def q_collar(m, c, d, r, w=0.03, flare=1.35, n=10):
    """A flared joint collar round a limb: a short lofted ring, flared at both lips."""
    n1, n2 = q_frame(d)
    d = Vector(d).normalized()
    c = Vector(c)
    rings = []
    for off, rr in ((-w, r * flare), (0.0, r * 1.02), (w, r * flare)):
        cc = c + d * off
        rings.append([cc + (n1 * math.cos((2.0 * math.pi) * k / n) + n2 * math.sin((2.0 * math.pi) * k / n)) * rr for k in range(n)])
    arch.loft(m, rings, caps=True)


def q_along(pts, f):
    """Point and unit tangent at arc-length fraction f of a polyline of Vectors."""
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    target = f * acc[-1]
    for i in range(len(pts) - 1):
        if acc[i + 1] >= target or i == len(pts) - 2:
            g = min(max((target - acc[i]) / max(acc[i + 1] - acc[i], 1e-9), 0.0), 1.0)
            return pts[i].lerp(pts[i + 1], g), (pts[i + 1] - pts[i]).normalized()


def q_thorax():
    """Broad ovoid (about 2.3 x 2.6 outer) round the pin bore: silk fur on top, carapace below. Each side is a
    grid from the bore circle (r 1.0, at z 0) out to the ovoid rim (z 0)."""
    H = 1.05

    def ring_pt(th, s):
        ix, iy = math.cos(th), math.sin(th)  # inner edge: the bore, r 1.0
        ox, oy = 1.15 * math.cos(th), 1.3 * math.sin(th)  # outer edge: the ovoid rim
        return Vector((ix + (ox - ix) * s, iy + (oy - iy) * s, 0.0))

    def f_top(u, v):
        p = ring_pt((2.0 * math.pi) * u, v)
        p.z = H * math.sin(math.pi * v) ** 0.6
        return p

    def f_bot(u, v):
        p = ring_pt((2.0 * math.pi) * u, v)
        p.z = -0.85 * H * math.sin(math.pi * v) ** 0.6
        return p

    top = arch.Mesh()
    arch.grid(top, f_top, 56, 12, wu=True)
    top.done("q_thorax_fur", "silk")
    bot = arch.Mesh()
    arch.grid(bot, f_bot, 56, 12, wu=True)
    bot.done("q_thorax_shell", "carapace")


def q_abdomen():
    """Seven overlapping lofted segments tapering from r 0.9 (at y 1.2) to r 0.2 (at y 3.9), each with a collar
    rim. Starts well clear of the bore."""
    y0, y1, seg = 1.2, 3.9, 0.62

    def rad(y):
        return 0.9 + (0.2 - 0.9) * (y - y0) / (y1 - y0)

    for k in range(7):
        a = y0 + k * (y1 - y0 - seg) / 6
        b = min(a + seg, y1)
        stations = [(a, 1.12), (a + 0.04, 1.12), (a + 0.1, 0.98), ((a + b) / 2, 1.0), (b, 0.96)]
        rings = []
        for y, mult in stations:
            r = rad(y) * mult
            rings.append([Vector((r * math.cos((2.0 * math.pi) * j / 24), y, 0.85 * r * math.sin((2.0 * math.pi) * j / 24)))
                          for j in range(24)])
        m = arch.Mesh()
        arch.loft(m, rings, caps=True)
        m.done("q_abd%d" % k, "carapace")


def q_head(m):
    """Lofted head, about 0.9 wide, running -Y from the neck to the mouth."""
    st = [(-1.42, 0.34, 0.26), (-1.72, 0.44, 0.32), (-2.02, 0.46, 0.31), (-2.32, 0.36, 0.24), (-2.52, 0.14, 0.12)]
    rings = []
    for y, w, h in st:
        rings.append([Vector((w * math.cos((2.0 * math.pi) * k / 16), y, 0.05 + h * math.sin((2.0 * math.pi) * k / 16))) for k in range(16)])
    arch.loft(m, rings, caps=True)


def q_crown(m_brass, m_wax):
    """Seven tapered points in a ring on top of the head, brass and wax alternating."""
    for k in range(7):
        a = (2.0 * math.pi) * k / 7
        base = Vector((0.3 * math.cos(a), -1.9 + 0.36 * math.sin(a), 0.28))
        d = Vector((0.5 * math.cos(a), 0.5 * math.sin(a), 1.0)).normalized()
        arch.sweep(m_brass if k % 2 == 0 else m_wax, [base, base + d * 0.44], q_tap(0.07, 0.008, 7))


def q_mantle(m):
    """Silk mantle: a draped thick sheet over the front of the thorax, with a wavy hem."""
    def f(u, v):
        x = -1.5 + 3.0 * u
        y = -1.05 - 0.3 * v - 0.04 * math.sin(9 * x) * v
        z = 0.74 - 0.78 * v ** 1.1 + 0.07 * math.sin(9 * x) * v ** 3
        return Vector((x, y, z))

    def g(u, v):
        return f(u, v) - Z * 0.03

    arch.thick_sheet(m, f, g, 30, 8)


def q_mandible(m, s):
    arch.sweep(m, [Vector((s * 0.2, -2.4, 0.0)), Vector((s * 0.3, -2.68, 0.03)), Vector((s * 0.2, -2.92, 0.05))],
               q_tap(0.06, 0.01, 7))


def q_antenna(m_shaft, m_feather, s):
    """A 2.2 m antenna: a curved shaft with twenty feather barbs a side, shorter toward the tip."""
    pts = [Vector((s * x, y, z)) for x, y, z in ((0.2, -2.3, 0.12), (0.5, -2.7, 0.16), (0.9, -3.0, 0.2),
                                                  (1.3, -3.15, 0.2), (1.7, -3.22, 0.14), (2.0, -3.25, 0.08))]
    arch.sweep(m_shaft, pts, q_tap(0.03, 0.009, 8))
    for i in range(20):
        f = 0.04 + 0.92 * i / 19
        p, t = q_along(pts, f)
        L = 0.46 * (1.0 - 0.78 * f)
        side = Vector((-t.y, t.x, 0.0)).normalized()
        for sg in (1, -1):
            d = (side * (0.9 * sg) - t * 0.45 + Z * 0.25).normalized()
            arch.sweep(m_feather, [p, p + d * L * 0.5, p + d * L], q_tap(0.012, 0.003, 5))


def q_leg(m, s, pts, r0):
    """A splayed leg: coxa, femur and tibia, flared joint collars, a four-segment tarsus and a pair of claws.
    pts = hip, knee, ankle, toe on the right side; s = -1 or 1 mirrors it to the left."""
    H, K, An, T = [Vector((s * x, y, z)) for x, y, z in pts]
    C = H.lerp(K, 0.2)
    arch.sweep(m, [H, C], q_tap(r0, r0 * 1.05))
    arch.sweep(m, [C, K], q_tap(r0, r0 * 0.85))
    arch.sweep(m, [K, An], q_tap(r0 * 0.85, r0 * 0.6))
    tm = [An.lerp(T, k / 4) for k in range(5)]
    for k in range(4):
        arch.sweep(m, [tm[k], tm[k + 1]], q_tap(r0 * (0.5 - 0.08 * k), r0 * (0.42 - 0.08 * k), n=6))
    for c, d, r in ((C, K - C, r0 * 0.95), (K, An - K, r0 * 0.85), (An, T - An, r0 * 0.6)):
        q_collar(m, c, d, r)
    dt = (T - An).normalized()
    side = dt.cross(Z).normalized()
    for sg in (1, -1):
        arch.sweep(m, [T, T + dt * 0.1 + side * (sg * 0.05) - Z * 0.02,
                       T + dt * 0.18 + side * (sg * 0.12) - Z * 0.08], q_tap(0.02, 0.004, 6))


def q_wing_surf(s, x0, x1, cm, yc0, dy, z0, camber, sc_amp=0.22):
    """Moth wing surface in XY: u along the span (root 0 .. tip 1), v across the chord (leading 0 .. trailing 1).
    Rounded leading edge and tip, scalloped trailing edge, slight upward camber."""
    def f(u, v):
        x = x0 + (x1 - x0) * u
        c = cm * (1 - 0.4 * u ** 1.6) * max(0.02, 1 - u ** 6) ** 0.5
        yc = yc0 + dy * u ** 1.2
        y = yc - 0.5 * c * math.cos(math.pi * v)
        y -= sc_amp * abs(math.sin(6.5 * math.pi * u)) * (c / cm) * (0.35 + 0.65 * u) * v ** 6
        z = z0 + 0.25 * u * u + camber * math.sin(math.pi * v)
        return Vector((s * x, y, z))
    return f


def q_wing(name, s, x0, x1, cm, yc0, dy, z0, camber, veins):
    """A thick membrane wing (0.03 m, clean 0..1 UVs over the panel) with raised veins from the root."""
    f = q_wing_surf(s, x0, x1, cm, yc0, dy, z0, camber)
    m = arch.Mesh(uv=True)
    arch.thick_sheet(m, lambda u, v: f(u, v) + Z * 0.015, lambda u, v: f(u, v) - Z * 0.015, 26, 10)
    m.done(name, "membrane")
    vm = arch.Mesh()
    for vk in veins:
        path = [f(0.02 + 0.95 * i / 5, vk) + Z * 0.035 for i in range(6)]
        arch.sweep(vm, path, q_tap(0.02, 0.008, 6))
    vm.done(name + "_veins", "carapace_dull")


def B_queen():
    """The pinned queen, lying flat as in a collection: about 12 m wingspan along X, about 6 m body along Y
    (head -Y, abdomen +Y), origin at the thorax centre. The thorax is a fur-topped ring round a r 1.0 bore."""
    q_thorax()
    q_abdomen()
    m = arch.Mesh()
    q_head(m)
    m.done("q_head", "carapace")
    eyes = arch.Mesh()
    for s in (-1, 1):
        arch.superq(eyes, (s * 0.4, -2.0, 0.12), (0.3, 0.3, 0.3), nu=16, nv=10)
    eyes.done("q_eyes", "ink")
    mand = arch.Mesh()
    for s in (-1, 1):
        q_mandible(mand, s)
    mand.done("q_mandibles", "carapace")
    cb, cw = arch.Mesh(), arch.Mesh()
    q_crown(cb, cw)
    cb.done("q_crown_brass", "brass")
    cw.done("q_crown_wax", "wax")
    mantle = arch.Mesh()
    q_mantle(mantle)
    mantle.done("q_mantle", "silk")
    for s in (-1, 1):
        shaft, feath = arch.Mesh(), arch.Mesh()
        q_antenna(shaft, feath, s)
        shaft.done("q_antenna_shaft%d" % s, "carapace_dull")
        feath.done("q_antenna_feathers%d" % s, "silk")
    legs = [([(1.25, -0.8, -0.3), (1.95, -1.5, -0.85), (2.6, -1.25, -1.05), (3.1, -1.75, -1.15)], 0.13),
            ([(1.25, 0.0, -0.3), (2.3, -0.25, -0.85), (3.0, 0.45, -1.05), (3.7, 0.2, -1.15)], 0.13),
            ([(1.25, 1.0, -0.3), (2.2, 1.85, -0.85), (2.9, 1.6, -1.05), (3.6, 2.25, -1.15)], 0.13)]
    for li, (pts, r0) in enumerate(legs):
        for s in (-1, 1):
            lm = arch.Mesh()
            q_leg(lm, s, pts, r0)
            lm.done("q_leg%d%s" % (li, "lr"[(s + 1) // 2]), "carapace_dull")
    veins_f = (0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.9)
    veins_h = (0.12, 0.3, 0.46, 0.62, 0.78, 0.92)
    q_wing("q_fore_l", -1, 1.05, 6.5, 1.5, -0.3, 0.9, 0.02, 0.06, veins_f)
    q_wing("q_fore_r", 1, 1.05, 6.5, 1.5, -0.3, 0.9, 0.02, 0.06, veins_f)
    q_wing("q_hind_l", -1, 1.05, 5.1, 1.3, 0.7, 0.5, -0.04, 0.05, veins_h)
    q_wing("q_hind_r", 1, 1.05, 5.1, 1.3, 0.7, 0.5, -0.04, 0.05, veins_h)
    return arch.finish("queen")


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown figure: " + args[0])
    fn(*args[1:])
