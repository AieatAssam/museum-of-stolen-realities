"""Chitin Court figures: two beetle courtiers, the stag-beetle usher, the Locksmith General and her
raptorial key-arm, and the pinned queen. One script, selected by args[0]. Run through
tools/blender_build.sh. Blender: +Z up, 1 unit = 1 m; a figure's front is -Y (Godot +Z).

Shells are lofts through superellipse cross-sections along curved spines (never single blobs),
limbs are tapered keeled lens sections with flared joint collars, membranes are UV'd grids."""
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import sculpt as S  # noqa: E402

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


# --- courtiers --------------------------------------------------------------------------------------

def _courtier(name, weevil):
    """A kneeling beetle courtier (weevil: taller, narrower, snouted, rougher, with a silk sash).
    Origin between the feet on the floor; front -Y."""
    sd = 300 if weevil else 200
    if weevil:
        shell = "carapace_dull"
        el = dict(spine=[(0, 0.82, 0.52), (0, 0.42, 0.66), (0, 0.06, 0.70), (0, -0.26, 0.64)],
                  hw=[0.08, 0.14, 0.16, 0.13], hh=[0.22, 0.42, 0.46, 0.36])
        pro = dict(spine=[(0, -0.02, 1.0), (0, -0.22, 1.04), (0, -0.42, 0.98)], hw=[0.2, 0.23, 0.19], hh=[0.18, 0.21, 0.18])
        head = dict(spine=[(0, -0.44, 1.12), (0, -0.6, 1.14), (0, -0.76, 1.08)], hw=[0.13, 0.16, 0.12], hh=[0.13, 0.15, 0.12])
        eye_c, eye_s = (0.15, -0.6, 1.14), (0.16, 0.14, 0.17)
        ant_pts = [(0.12, -0.56, 1.2), (0.3, -0.7, 1.24), (0.16, -0.92, 1.16)]
        nb, club, dz = 11, 1.9, 0.15
    else:
        shell = "carapace"
        el = dict(spine=[(0, 0.78, 0.5), (0, 0.42, 0.6), (0, 0.08, 0.63), (0, -0.26, 0.56)],
                  hw=[0.13, 0.2, 0.21, 0.17], hh=[0.2, 0.3, 0.31, 0.24])
        pro = dict(spine=[(0, 0.02, 0.82), (0, -0.22, 0.86), (0, -0.44, 0.78)], hw=[0.22, 0.25, 0.19], hh=[0.2, 0.24, 0.2])
        head = dict(spine=[(0, -0.3, 1.0), (0, -0.5, 1.02), (0, -0.72, 0.98)], hw=[0.17, 0.19, 0.16], hh=[0.15, 0.17, 0.16])
        eye_c, eye_s = (0.18, -0.52, 1.07), (0.2, 0.2, 0.22)
        ant_pts = [(0.1, -0.42, 1.2), (0.26, -0.5, 1.36), (0.36, -0.62, 1.3)]
        nb, club, dz = 9, 1.8, 0.0
    parts = []
    for s in (-1, 1):
        parts += _elytron("%s_elytra%d" % (name, s), s, el["spine"], el["hw"], el["hh"], shell, sd + s)
    parts += _plate(name + "_pronotum", pro["spine"], _spec(pro["hw"], pro["hh"]), shell, rim=0.022, exp=2.6)
    parts += _plate(name + "_head", head["spine"], _spec(head["hw"], head["hh"]), shell, exp=2.2)
    for s in (-1, 1):
        parts.append(_eye("%s_eye%d" % (name, s), (s * eye_c[0], eye_c[1], eye_c[2]), eye_s, sd + 3))
        parts.append(_lens("%s_mand%d" % (name, s), [(s * 0.08, -0.64, 0.9), (s * 0.16, -0.84, 0.92), (s * 0.09, -0.96, 0.8)],
                           [0.035, 0.03, 0.015], "carapace_dull", hr=0.7))
        parts.append(_thorn("%s_tooth%d" % (name, s), (s * 0.13, -0.84, 0.92), (s * 0.2, -0.6, 0.5), 0.05, 0.012, "carapace_dull"))
        parts.append(_beads("%s_ant%d" % (name, s), [(s * x, y, z) for x, y, z in ant_pts], nb, 0.028, 0.013, "carapace_dull", club))
    if weevil:
        parts.append(_lens(name + "_snout", [(0, -0.72, 1.12), (0, -0.96, 1.08), (0, -1.14, 0.96), (0, -1.22, 0.84)],
                           [0.075, 0.06, 0.05, 0.035], shell, hr=0.9, keel=0.3))
        for s in (-1, 1):
            parts.append(_thorn("%s_jaw%d" % (name, s), (s * 0.04, -1.2, 0.84), (s * 0.2, -0.4, -0.3), 0.08, 0.02, "carapace_dull"))
        parts.append(_lens(name + "_sash", [(-0.3, -0.25, 1.15), (-0.05, -0.05, 1.0), (0.25, 0.2, 0.55)],
                           [0.05, 0.05, 0.05], "silk", hr=0.5, keel=0.0))
    else:
        mantle = [(-0.44, -0.02, 0.66), (-0.22, -0.06, 0.9), (0, -0.08, 0.96), (0.22, -0.06, 0.9), (0.44, -0.02, 0.66)]
        mobj, msmp = _dome(name + "_mantle", mantle, _spec([0.2, 0.23, 0.24, 0.23, 0.2], [0.03, 0.05, 0.035, 0.05, 0.03]),
                           "silk", n=12, exp=2.0, low=1.0)
        parts.append(mobj)
        parts += _lines(name + "_fold", msmp, [0.25, 0.5, 0.75], "silk", w=0.012, h=0.01)
        parts.append(torus_ring(name + "_circlet", 0.15, 0.016, (0, -0.48, 1.18), "brass"))
    legs = [
        ([(0.2, -0.2, 0.85 + dz), (0.26, -0.48, 0.7 + dz), (0.14, -0.6, 0.56 + dz), (0.05, -0.6, 0.46 + dz)], 0.05),
        ([(0.3, -0.05, 0.55 + dz), (0.52, -0.22, 0.22), (0.42, -0.05, 0.04), (0.28, 0.12, 0.03)], 0.06),
        ([(0.3, 0.4, 0.42 + dz), (0.52, 0.5, 0.12), (0.4, 0.7, 0.04), (0.22, 0.8, 0.03)], 0.07),
    ]
    for li, (pts, r) in enumerate(legs):
        for s in (-1, 1):
            parts += _leg("%s_L%d%s" % (name, li, "rl"[(s + 1) // 2]), [(s * x, y, z) for x, y, z in pts], r, sd + 10 * li + (s + 1))
    return parts


def B_courtier_a():
    """The kneeling beetle courtier: domed carapace, silk mantle, brass circlet, folded legs."""
    kit.join("courtier_a", _courtier("courtier_a", weevil=False))


def B_courtier_b():
    """The kneeling weevil courtier: long curved snout, elbowed antennae, rough carapace, silk sash."""
    kit.join("courtier_b", _courtier("courtier_b", weevil=True))


# --- usher ------------------------------------------------------------------------------------------

def B_usher():
    """A stag-beetle usher standing on its hind legs (origin at centre, feet at z -1.1). Silk tabard with
    brass buttons; forelimbs hold a brass staff along Y, 3.0 m end to end."""
    sd = 400
    parts = []
    for s in (-1, 1):
        parts += _elytron("u_elytra%d" % s, s, [(0, 0.75, -0.4), (0, 0.35, -0.2), (0, 0.0, -0.18), (0, -0.22, -0.3)],
                          [0.12, 0.18, 0.195, 0.16], [0.3, 0.46, 0.49, 0.38], "carapace", sd + s)
    parts += _plate("u_thorax", [(0, 0.0, 0.36), (0, -0.2, 0.42), (0, -0.36, 0.34)], _spec([0.24, 0.28, 0.22], [0.22, 0.25, 0.2]),
                    "carapace", rim=0.02, exp=2.4)
    parts += _plate("u_head", [(0, -0.1, 0.86), (0, -0.26, 0.9), (0, -0.42, 0.84)], _spec([0.18, 0.22, 0.16], [0.17, 0.2, 0.16]),
                    "carapace", exp=2.2)
    parts.append(S.slab("u_tabard", (0.56, 0.08, 1.0), (0, -0.3, -0.3), "silk", sd, lump=0.012, bevel=0.03, cuts=6))
    for k, (x, z) in enumerate([(-0.13, -0.1), (0.13, -0.1), (-0.13, -0.45), (0.13, -0.45)]):
        parts.append(S.blob("u_button%d" % k, (0.04, 0.04, 0.04), (x, -0.37, z), "brass", sd + k, lump=0.0, subdiv=2))
    for s in (-1, 1):
        parts.append(_lens("u_mand%d" % s, [(s * 0.12, -0.4, 0.92), (s * 0.22, -0.66, 0.98), (s * 0.3, -0.82, 0.98)],
                           [0.05, 0.04, 0.02], "carapace", hr=0.7))
        parts.append(_thorn("u_tine%d" % s, (s * 0.2, -0.66, 0.96), (s * -0.4, -0.2, 0.8), 0.1, 0.02, "carapace"))
        parts.append(_eye("u_eye%d" % s, (s * 0.14, -0.36, 0.92), (0.16, 0.18, 0.2), sd))
        parts.append(_beads("u_ant%d" % s, [(s * 0.08, -0.3, 1.04), (s * 0.18, -0.42, 1.08), (s * 0.12, -0.5, 1.02)], 9,
                            0.02, 0.012, "carapace_dull", 1.6))
        # hind legs: standing, knees forward, feet flat
        parts += _leg("u_hind%d" % s, [(s * 0.22, 0.0, -0.35), (s * 0.25, -0.22, -0.78), (s * 0.2, -0.05, -1.0), (s * 0.2, -0.22, -1.06)],
                      0.07, sd + 20 + s, spines=0)
        # middle legs folded back against the body
        parts += _leg("u_mid%d" % s, [(s * 0.3, 0.0, 0.0), (s * 0.46, 0.2, -0.2), (s * 0.42, 0.45, -0.05), (s * 0.3, 0.55, 0.05)],
                      0.05, sd + 30 + s, spines=0)
        # forelimbs: shoulder, elbow, wrist, hand closed on the staff
        parts += _leg("u_fore%d" % s, [(s * 0.28, -0.2, 0.3), (s * 0.4, -0.5, 0.02), (s * 0.16, -0.6, -0.08), (s * 0.08, -0.62, -0.1)],
                      0.05, sd + 40 + s, spines=1)
    parts.append(_tube("u_staff", [(0, -1.44, -0.1), (0, 1.44, -0.1)], [0.03, 0.03], "brass", sd, sides=10, steps=1))
    for k, y in enumerate((-1.44, 1.44)):
        parts.append(S.blob("u_finial%d" % k, (0.12, 0.12, 0.12), (0, y, -0.1), "brass", sd + k, lump=0.0, subdiv=2))
    kit.join("usher", parts)


def _tube(name, pts, radii, mat, seed, sides=12, steps=6):
    """A smooth capped rod along a polyline (the usher's brass staff)."""
    n = (len(pts) - 1) * steps
    smp = _along(pts, [(r,) for r in radii], steps)
    st = [(p, v[0], v[0], 0.0) for p, v in smp]
    return loft(name, st, mat, n=sides, exp=2.0, low=1.0)


# --- the Locksmith General --------------------------------------------------------------------------

def B_general():
    """The Locksmith General, 7.5 m, origin at the feet. Four walking legs, an armoured prothorax, a long
    leaf-like abdomen of overlapping plates, a helm, layered tegmina folded over the back, and shoulder
    sockets at (+-1.6, z 5.0)."""
    sd = 500
    parts = []
    parts += _plate("g_thorax", [(0, -0.95, 4.0), (0, -0.4, 4.0), (0, 0.4, 4.0), (0, 0.95, 4.0)],
                    _spec([0.55, 0.75, 0.75, 0.55], [0.55, 0.75, 0.72, 0.55]), "carapace", exp=2.4, low=0.6)
    parts += _plate("g_pro", [(0, 0.1, 5.6), (0, -0.5, 5.6), (0, -1.1, 5.5)], _spec([0.42, 0.5, 0.4], [0.75, 0.9, 0.8]),
                    "carapace", rim=0.05, exp=2.4)
    parts += _plate("g_head", [(0, -1.0, 6.7), (0, -1.35, 6.75), (0, -1.75, 6.6)], _spec([0.36, 0.45, 0.3], [0.4, 0.47, 0.36]),
                    "carapace", exp=2.2)
    parts.append(S.blob("g_helm", (1.05, 1.0, 0.6), (0, -1.25, 7.15), "brass", sd + 3, lump=0.02, subdiv=3, dents=2))
    parts.append(kit.torus("g_brow", major=0.55, minor=0.05, seg=24, rseg=6, mat="brass", loc=(0, -1.35, 6.9)))
    for k, x in enumerate((-0.3, 0.0, 0.3)):
        parts.append(_lens("g_crest%d" % k, [(x, -1.3, 7.2), (x * 0.5, -1.45, 7.5 - 0.1 * abs(x))], [0.05, 0.02], "brass", hr=1.0))
    for s in (-1, 1):
        parts.append(S.blob("g_eye%d" % s, (0.95, 0.9, 1.05), (s * 0.45, -1.7, 6.85), "ink", sd + 4 + s, lump=0.0, subdiv=4))
        parts.append(S.blob("g_socket%d" % s, (0.45, 0.6, 0.5), (s * 1.6, -0.2, 5.0), "carapace_dull", sd + 6 + s, lump=0.02, subdiv=3))
        parts.append(_torus_at("g_socketring%d" % s, (s * 1.6, -0.2, 5.0), X * s, 0.36, 0.06, "brass"))
    # four walking legs: mid pair and hind pair
    for s in (-1, 1):
        parts += _leg("g_mid%d" % s, [(s * 1.0, -0.3, 3.2), (s * 2.3, -0.4, 2.2), (s * 2.4, -0.2, 0.8), (s * 2.7, 0.2, 0.02)],
                      0.24, sd + 10 + s, spines=4)
        parts += _leg("g_hind%d" % s, [(s * 1.0, 0.9, 3.0), (s * 2.4, 1.0, 2.0), (s * 2.5, 0.9, 0.9), (s * 2.8, 0.9, 0.02)],
                      0.24, sd + 20 + s, spines=4)
    # abdomen: a leaf of nine overlapping plates, each sinking under the next
    ab = [(0, 1.0, 3.9), (0, 2.6, 3.7), (0, 4.4, 3.0), (0, 6.0, 1.8), (0, 7.1, 0.6)]
    ar = [0.8, 0.85, 0.7, 0.45, 0.22]
    smp = _along(ab, [(r, r * 0.42, 0.0) for r in ar], steps=4)
    n = len(smp)
    plates = 9
    for k in range(plates):
        i0 = int(round(k * (n - 1) / plates))
        i1 = min(n - 1, i0 + 4)
        m = i1 - i0 + 1
        st = []
        for j, i in enumerate(range(i0, i1 + 1)):
            p, v = smp[i]
            u = j / (m - 1)
            st.append((p + Z * (-0.3 * v[1] * u), v[0] * (1 - 0.12 * u), v[1] * (1 - 0.2 * u), 0.0))
        parts.append(loft("g_plate%d" % k, st, "carapace", n=14, exp=2.4, low=0.35))
    for i in range(1, n - 1, 2):
        p, v = smp[i]
        parts.append(_thorn("g_spine%d" % i, p + Z * v[1] * 0.9, Z + Y * 0.3, 0.35, 0.05, "carapace_dull"))
    # tegmina: two layers over each flank, folded along the back, with vein ridges
    for s in (-1, 1):
        wing_pts = [(0, y, z + 0.3 * r) for (_, y, z), r in zip(ab, ar)]
        wing, wsmp = _dome("g_tegmen%d" % s, wing_pts, [(1.2 * r, 0.55 * r, s * 1.2 * r) for r in ar], "carapace",
                           n=14, exp=2.2, low=0.5)
        parts.append(wing)
        parts += _lines("g_vein%d" % s, wsmp, [0.2, 0.4, 0.6, 0.8], "carapace_dull", w=0.02, h=0.016)
        under_pts = [(0, y, z + 0.2 * r) for (_, y, z), r in zip(ab, ar)]
        under, usmp = _dome("g_membrane%d" % s, under_pts, [(1.0 * r, 0.42 * r, s * 1.0 * r) for r in ar], "membrane",
                            n=14, exp=2.2, low=0.5, uv=True)
        parts.append(under)
    kit.join("general", parts)


def B_general_arm():
    """ONE raptorial forelimb at the shoulder pivot (origin), reaching 5 m toward -Y. The lower limb is
    a giant brass key: the bit with wards at y -5."""
    sd = 600
    parts = [
        _dome("ga_coxa", [(0, 0.25, 0), (0, -0.2, 0), (0, -0.6, -0.02)], _spec([0.4, 0.45, 0.36], [0.42, 0.45, 0.4]),
              "carapace", n=14, exp=2.2, low=0.6)[0],
        _torus_at("ga_socket", (0, 0, 0), Y, 0.5, 0.06, "brass"),
    ]
    fem = [(0, -0.2, 0), (0, -1.2, 0.2), (0, -2.4, 0.5)]
    parts.append(_lens("ga_femur", fem, [0.42, 0.36, 0.3], "carapace", hr=0.7))
    for k in range(4):
        p = Vector(fem[0]).lerp(Vector(fem[1]), 0.2 + 0.2 * k)
        parts.append(_thorn("ga_fspine%d" % k, p - Z * 0.3, -Z + -Y * 0.1, 0.35, 0.05, "carapace_dull"))
    parts.append(_torus_at("ga_knee", (0, -2.4, 0.5), Y, 0.3, 0.07, "brass"))
    tib = [(0, -2.4, 0.5), (0, -3.3, 0.15), (0, -4.3, -0.2)]
    parts.append(_lens("ga_tibia", tib, [0.3, 0.22, 0.16], "carapace_dull", hr=0.7))
    for k in range(3):
        p = Vector(tib[0]).lerp(Vector(tib[1]), 0.3 + 0.25 * k)
        parts.append(_thorn("ga_tspine%d" % k, p + Z * 0.2, Z + Y * 0.2, 0.22, 0.03, "carapace_dull"))
    parts.append(_torus_at("ga_ankle", (0, -4.3, -0.2), Y, 0.17, 0.05, "brass"))
    parts.append(_lens("ga_shaft", [(0, -4.3, -0.2), (0, -4.85, -0.2)], [0.08, 0.07], "brass", hr=1.0))
    parts.append(S.slab("ga_bit", (0.14, 0.7, 0.8), (0, -5.0, 0.05), "brass", sd + 31, lump=0.0, bevel=0.02, cuts=2))
    for k, y in enumerate((-4.8, -5.0, -5.2)):
        parts.append(S.slab("ga_ward%d" % k, (0.2, 0.12, 0.2), (0, y, 0.5), "brass", sd + 32 + k, lump=0.0, bevel=0.02, cuts=1))
    kit.join("general_arm", parts)


# --- the pinned queen -------------------------------------------------------------------------------

def _wing_pt(s, u, v, xr, xt, le0, te0, le1, te1, z0, scal):
    """A point on a wing: u along the span (root 0 .. tip 1), v across the chord (leading 0 .. trailing 1).
    The trailing edge is scalloped by a cusp per lobe."""
    x = xr + (xt - xr) * u
    le = le0 + (le1 - le0) * u ** 0.8
    te = te0 + (te1 - te0) * u - scal * abs(math.sin(7 * math.pi * u)) * (0.3 + 0.7 * u)
    y = le + (te - le) * v
    z = z0 + 0.25 * u * u + 0.06 * math.sin(math.pi * v)
    return Vector((s * x, y, z))


def _wing(name, s, xr, xt, le0, te0, le1, te1, z0, eyespot=None, nu=20, nv=10):
    """A flat membrane wing in XY, mirrored by s: scalloped trailing edge, raised vein ridges, and an
    optional eyespot (fore wing) as a raised ring with an amber centre."""
    args = (xr, xt, le0, te0, le1, te1, z0, 0.18)
    grid = [[_wing_pt(s, i / nu, j / nv, *args) for j in range(nv + 1)] for i in range(nu + 1)]
    parts = [_grid(name, grid, "membrane", lambda i, j: (i / nu, j / nv))]
    for k, v in enumerate((0.12, 0.3, 0.48, 0.66)):
        pts = [_wing_pt(s, 0.02 + 0.98 * i / 12, v, *args) + Z * 0.01 for i in range(13)]
        parts.append(loft("%s_vein%d" % (name, k), [(p, 0.022, 0.016, 0.0) for p in pts], "carapace_dull", n=6))
    if eyespot:
        u, v, r = eyespot
        c = _wing_pt(s, u, v, *args)
        parts.append(_ring(name + "_eyering", c + Z * 0.02, X, Y, r, r, 0.03, "carapace_dull"))
        parts.append(S.blob(name + "_eyecore", (r * 1.2, r * 1.2, 0.05), c + Z * 0.03, "amber", 7, lump=0.0, subdiv=2))
    return parts


def _grid(name, grid, mat, uv_of):
    """A quad grid (rows of points) with a UV layer from uv_of(i, j)."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in row] for row in grid]
    for i in range(len(grid) - 1):
        for j in range(len(grid[0]) - 1):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    uvmap = {}
    for i, row in enumerate(vs):
        for j, v in enumerate(row):
            uvmap[v] = uv_of(i, j)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = uvmap[lp.vert]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return S.to_obj(name, bm, mat)


def B_queen():
    """The pinned queen, lying flat as in a collection: wingspan 12 m, body 6 m along Y, origin at the
    centre of the thorax. Thorax is a carapace ring round a r 1.0 hole for the pin."""
    sd = 700
    parts = []
    R = 1.42
    ring = [(Vector((R * math.cos(2 * math.pi * k / 24), R * math.sin(2 * math.pi * k / 24), 0.0)), 0.42, 0.85, 0.0)
            for k in range(24)]
    parts.append(loft("q_thorax", ring, "carapace", n=16, exp=2.2, low=0.7, closed=True))
    for k, zz in enumerate((-0.5, 0.5)):
        parts.append(_ring("q_band%d" % k, (0, 0, zz), X, Y, R + 0.3, R + 0.3, 0.05, "brass"))
    parts += _plate("q_head", [(0, -1.25, 0.05), (0, -1.75, 0.05), (0, -2.25, 0.0)], _spec([0.5, 0.62, 0.45], [0.45, 0.55, 0.42]),
                    "carapace", exp=2.2)
    for s in (-1, 1):
        parts.append(S.blob("q_eye%d" % s, (0.55, 0.55, 0.6), (s * 0.38, -2.3, 0.2), "ink", sd + 2 + s, lump=0.0, subdiv=3))
    for k in range(5):
        x = -0.4 + 0.2 * k
        parts.append(_lens("q_crown%d" % k, [(x, -1.75, 0.55), (x * 0.6, -1.75, 1.15)], [0.05, 0.01], "brass", hr=1.0))
    parts.append(kit.torus("q_crownring", major=0.6, minor=0.05, seg=24, rseg=6, mat="brass", loc=(0, -1.75, 0.55)))
    parts.append(_dome("q_abdomen", [(0, 1.1, 0), (0, 1.9, 0), (0, 2.6, 0), (0, 3.2, 0)],
                       [(0.45, 0.3, 0), (0.28, 0.22, 0), (0.42, 0.3, 0), (0.07, 0.08, 0)], "carapace", n=16, exp=2.0, low=0.6)[0])
    parts.append(_ring("q_band_ab0", (0, 1.9, 0), X, Z, 0.3, 0.25, 0.04, "brass"))
    parts.append(_ring("q_band_ab1", (0, 2.6, 0), X, Z, 0.44, 0.3, 0.05, "brass"))
    for s in (-1, 1):
        for k, y in enumerate((-0.8, 0.0, 0.8)):
            parts += _leg("q_leg%d%d" % (s, k), [(s * 1.3, y, -0.3), (s * 2.0, y + 0.1, -0.9), (s * 1.4, y + 0.2, -1.2), (s * 1.2, y + 0.3, -1.3)],
                          0.12, sd + 10 + k, spines=1)
    parts += _wing("q_fore_l", -1, 1.5, 6.0, 0.6, -1.4, -2.6, -2.0, 0.05, eyespot=(0.5, 0.42, 0.22))
    parts += _wing("q_fore_r", 1, 1.5, 6.0, 0.6, -1.4, -2.6, -2.0, 0.05, eyespot=(0.5, 0.42, 0.22))
    parts += _wing("q_hind_l", -1, 1.3, 4.3, -0.4, 1.9, -0.9, 0.6, -0.02)
    parts += _wing("q_hind_r", 1, 1.3, 4.3, -0.4, 1.9, -0.9, 0.6, -0.02)
    kit.join("queen", parts)


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown figure: " + args[0])
    fn(*args[1:])
