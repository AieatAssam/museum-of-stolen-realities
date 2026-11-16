"""Chitin Court buttress masses (pass 4a): one secreted carapace column per collision mass in shells.json.

Build: tools/blender_build.sh wings/chitin/models/src/masses.py wings/chitin/models/masses_<area>.glb <Area>
  <Area> is HiveShaft, GeneralArena, Foundry, SilkDistricts or OuterGate (masses_<area lowercase>.glb).

Each "masses" entry is a vertical collision cylinder: centre c=[x, z], radius r, height y=[y0, y1], GODOT
world. The visual is a loft of rings built at world position (Godot (x, y, z) -> Blender (x, -z, y)):
  * the section stays between r+BAND_LO and r+BAND_HI for y in [y0+1.5, y1-1.5] (the self-check asserts
    r-0.05 .. r+0.35): lumpy noise radius, domed shingle plates from rooms.py (_plate), twisted vertical
    ribs (carapace_dull), and a few knobs;
  * insect-leg joint collars every 6.5-8.5 m from y0+3.5: a 1.4 m swell (up to +0.9 m, overhanging lip, then a
    0.12 m pinch above) with carapace_dull faces. Collar windows are outside the band and skipped by the
    self-check; between joints the section dips up to 0.1 m (hourglass), clamped to the band floor;
  * at the floor it fillets out to r+1.2 over the first 1.5 m; at the top it flares to r+1.5 over the last 1.5 m.
Reuses rooms.py for the plate field, hash, noise seed and carapace material names.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rooms as R  # noqa: E402  (plate field, hash, noise seed, carapace material names)

ANG = 36            # segments around each ring
DY = 1.2            # ring spacing along the height (m)
BAND_LO = 0.02      # in-band radius offset from r, lower bound
BAND_HI = 0.30      # in-band radius offset from r, upper bound
FLARE_LEN = 1.5     # both fillets run over this height
FLARE_BOT = 1.2     # floor fillet reaches r + this
FLARE_TOP = 1.5     # top flare reaches r + this into the wall/vault
PLATE_CS = 1.6      # plate cell size around (m)
PLATE_CA = 1.5      # plate cell size up (m)
RIBS = 6            # vertical ribs around the column
TWIST = 0.5         # rib twist over the full height (rad of angle)
RIB_AMP = 0.10
KNOBS = 3
KNOB_AMP = 0.12
JOINT_0 = 3.5       # first joint collar, m above y0
JOINT_STEP = 6.5    # joint spacing: 6.5 .. 8.5 m (hash jitter)
JOINT_JIT = 2.0
JOINT_TOP = 2.5     # last joint at least this far below y1
COLLAR_LO = 0.5     # collar window: from joint - COLLAR_LO ...
COLLAR_HI = 0.9     # ... to joint + COLLAR_HI (1.4 m tall; starts at y0+3.0 for the first joint)
COLLAR_H = COLLAR_LO + COLLAR_HI
COLLAR_AMP = 0.9    # peak swell (m), scaled 0.7..1.0 per joint
PINCH_H = 0.3       # pinch zone just above the collar
PINCH_AMP = 0.12
DIP_AMP = 0.10      # hourglass dip mid-segment between joints
LEVEL_STEP = 0.3    # ring spacing inside collar windows (the profile needs the detail; 0.1 blew the tri cap)
TOL_IN = 0.05
TOL_OUT = 0.35
TRI_CAP = 60000
MAT_RIB = 1         # index into rooms.MAT_NAMES: carapace_dull for the ribs and collar faces


def _masses(area):
    with open(os.path.join(HERE, "shells.json")) as fh:
        ms = [m for m in json.load(fh)["masses"] if m["area"] == area]
    if not ms:
        raise SystemExit("masses.py: no masses for area %r" % area)
    return ms


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _knobs(m, i):
    y0, y1 = m["y"]
    out = []
    for k in range(KNOBS):
        th = 2.0 * math.pi * R._hash(i + 1, k + 11)
        y = y0 + (y1 - y0) * (0.15 + 0.7 * R._hash(i + 3, k + 17))
        out.append((th, y, KNOB_AMP * (0.6 + 0.8 * R._hash(i + 5, k + 23))))
    return out


def _joints(m, i):
    """Collar joints (height, swell amplitude), deterministic per column."""
    y0, y1 = m["y"]
    out, y, j = [], y0 + JOINT_0, 0
    while y <= y1 - JOINT_TOP:
        out.append((y, COLLAR_AMP * (0.7 + 0.3 * R._hash(i + 7, j + 31))))
        y += JOINT_STEP + JOINT_JIT * R._hash(i + 2, j + 9)
        j += 1
    return out


def _collar(joints, y):
    """(swell, in_collar_window, shape) at height y. shape is <= 0: pinch above a collar or hourglass dip."""
    for yj, amp in joints:
        a, b = yj - COLLAR_LO, yj + COLLAR_HI
        if a <= y <= b:
            t = (y - a) / COLLAR_H
            if t < 0.3:  # quick swell
                u = t / 0.3
                g = u * u * (3 - 2 * u)
            elif t < 0.7:  # overhanging lip plateau
                g = 1.0 - 0.1 * (t - 0.3) / 0.4
            else:  # sharp drop under the lip
                g = 0.9 * (1 - (t - 0.7) / 0.3) ** 2
            return amp * g, True, 0.0
        if b < y <= b + PINCH_H:
            return 0.0, False, -PINCH_AMP * math.sin(math.pi * (y - b) / PINCH_H)
    for (ya, _), (yb, _) in zip(joints, joints[1:]):
        lo, hi = ya + COLLAR_HI + PINCH_H, yb - COLLAR_LO
        if lo <= y <= hi:
            return 0.0, False, -DIP_AMP * math.sin(math.pi * (y - lo) / (hi - lo))
    return 0.0, False, 0.0


def _levels(m, joints):
    y0, y1 = m["y"]
    n = max(2, math.ceil((y1 - y0) / DY))
    spans = [(yj - COLLAR_LO, yj + COLLAR_HI + PINCH_H) for yj, _ in joints]
    ys = [y0 + (y1 - y0) * k / n for k in range(n + 1)]
    ys = [y for y in ys if not any(a < y < b for a, b in spans)]  # collar windows get their own rings
    for a, b in spans:
        k = int(round((b - a) / LEVEL_STEP))
        ys += [a + (b - a) * q / k for q in range(k + 1)]
    ys.sort()
    out = []
    for y in ys:
        if not out or y - out[-1] > 0.02:
            out.append(y)
    return out


def _d(m, i, th, y, knobs):
    """Radial offset from r inside the band, as a function of angle th and height y."""
    c0, c1 = m["c"]
    r = m["r"]
    y0, y1 = m["y"]
    H = y1 - y0
    p = Vector((math.cos(th) * r * 0.8, y * 0.8, math.sin(th) * r * 0.8)) + R.SEED_V + Vector((i * 3.1, 0, c0 * 0.05))
    n01 = min(1.0, max(0.0, 0.5 + 1.2 * noise.noise(p)))
    d = BAND_LO + 0.09 * n01
    d += R._plate(r * th, y - y0, PLATE_CS, PLATE_CA, 0.3)
    tw = TWIST * (y - y0) / H
    wr = max(0.0, math.cos(RIBS * (th - tw))) ** 8
    d += RIB_AMP * wr
    for thk, yk, amp in knobs:
        dth = _wrap(th - thk) * r
        d += amp * math.exp(-(dth * dth) / (2 * 0.6 ** 2) - ((y - yk) / 1.0) ** 2)
    return min(BAND_HI, max(BAND_LO, d)), wr


def _flare(y, y0, y1, d):
    if y < y0 + FLARE_LEN:
        s = min(1.0, max(0.0, (y - y0) / FLARE_LEN))
        return (FLARE_BOT - d) * (1.0 - s) ** 2
    if y > y1 - FLARE_LEN:
        s = min(1.0, max(0.0, (y - (y1 - FLARE_LEN)) / FLARE_LEN))
        return (FLARE_TOP - d) * s ** 2
    return 0.0


def _mass(bm, m, i, mats, checks):
    c0, c1 = m["c"]
    r = m["r"]
    y0, y1 = m["y"]
    joints = _joints(m, i)
    levels = _levels(m, joints)
    knobs = _knobs(m, i)
    rings = []
    for y in levels:
        bump, coll, shape = _collar(joints, y)
        ring = []
        for j in range(ANG):
            th = 2.0 * math.pi * j / ANG
            d, wr = _d(m, i, th, y, knobs)
            if shape:
                d = max(BAND_LO, d + shape)  # hourglass / pinch, never below the band floor
            rad = r + d + _flare(y, y0, y1, d) + bump
            v = bm.verts.new(Vector((c0 + rad * math.cos(th), -(c1 + rad * math.sin(th)), y)))
            mats[v] = max(wr, 1.0) if coll else wr
            if y0 + 1.5 <= y <= y1 - 1.5:
                checks.append((v, c0, c1, r, y0, y1, coll))
            ring.append(v)
        rings.append(ring)
    bot = bm.verts.new(Vector((c0, -c1, y0)))
    top = bm.verts.new(Vector((c0, -c1, y1)))
    mats[bot], mats[top] = 0.0, 0.0
    faces = []
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for j in range(ANG):
            jj = (j + 1) % ANG
            faces.append(bm.faces.new((A[j], A[jj], B[jj], B[j])))
    R0, RN = rings[0], rings[-1]
    for j in range(ANG):
        jj = (j + 1) % ANG
        faces.append(bm.faces.new((bot, R0[jj], R0[j])))
        faces.append(bm.faces.new((top, RN[j], RN[jj])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = MAT_RIB if max(mats[v] for v in f.verts) > 0.6 else 0
    return faces


def _selfcheck(checks, name):
    """Final vertex positions, back in Godot coordinates: band vertices sit at r-TOL_IN .. r+TOL_OUT.
    Collar-window vertices are skipped (they swell past the band on purpose)."""
    worst_lo, worst_hi, n = 9.0, -9.0, 0
    for v, c0, c1, r, y0, y1, coll in checks:
        if coll:
            continue
        gx, gy, gz = v.co.x, v.co.z, -v.co.y
        assert y0 + 1.5 - 1e-6 <= gy <= y1 - 1.5 + 1e-6, "%s: band vertex outside height band" % name
        dist = math.hypot(gx - c0, gz - c1)
        assert r - TOL_IN <= dist <= r + TOL_OUT, (
            "%s: band vertex at dist %.3f, r %.2f (limits -%.2f / +%.2f)" % (name, dist, r, TOL_IN, TOL_OUT))
        worst_lo, worst_hi, n = min(worst_lo, dist - r), max(worst_hi, dist - r), n + 1
    print("SELFCHECK %s: %d band verts (collar windows skipped), offset from r in [%.3f, %.3f] within [-%.2f, +%.2f]"
          % (name, n, worst_lo, worst_hi, TOL_IN, TOL_OUT))


def build(args):
    area = args[0]
    name = "masses_" + area.lower()
    masses = _masses(area)
    bm = bmesh.new()
    mats, checks = {}, []
    for i, m in enumerate(masses):
        _mass(bm, m, i, mats, checks)
    _selfcheck(checks, name)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    print("TRIS %s %d (cap %d, %d masses)" % (name, tris, TRI_CAP, len(masses)))
    assert tris <= TRI_CAP, "%s: %d tris over cap" % (name, tris)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40.0):
            e.smooth = False
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    for mname in R.MAT_NAMES:
        me.materials.append(bpy.data.materials.get(mname) or bpy.data.materials.new(mname))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob
