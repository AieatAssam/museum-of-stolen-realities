"""Chitin Court buttress masses (pass 4a): one secreted carapace column per collision mass in shells.json.

Build: tools/blender_build.sh wings/chitin/models/src/masses.py wings/chitin/models/masses_<area>.glb <Area>
  <Area> is HiveShaft, GeneralArena, Foundry, SilkDistricts or OuterGate (masses_<area lowercase>.glb).

Each "masses" entry is a vertical collision cylinder: centre c=[x, z], radius r, height y=[y0, y1], GODOT
world. The visual is a loft of rings built at world position (Godot (x, y, z) -> Blender (x, -z, y)):
  * the section stays between r+BAND_LO and r+BAND_HI for y in [y0+1.5, y1-1.5] (the self-check asserts
    r-0.05 .. r+0.35): lumpy noise radius, domed shingle plates from rooms.py (_plate), twisted vertical
    ribs (carapace_dull), and a few knobs;
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

ANG = 40            # segments around each ring
DY = 0.9            # ring spacing along the height (m)
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
TOL_IN = 0.05
TOL_OUT = 0.35
TRI_CAP = 60000
MAT_RIB = 1         # index into rooms.MAT_NAMES: carapace_dull for the ribs


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
    n = max(2, math.ceil((y1 - y0) / DY))
    levels = [y0 + (y1 - y0) * k / n for k in range(n + 1)]
    knobs = _knobs(m, i)
    rings = []
    for y in levels:
        ring = []
        for j in range(ANG):
            th = 2.0 * math.pi * j / ANG
            d, wr = _d(m, i, th, y, knobs)
            rad = r + d + _flare(y, y0, y1, d)
            v = bm.verts.new(Vector((c0 + rad * math.cos(th), -(c1 + rad * math.sin(th)), y)))
            mats[v] = wr
            if y0 + 1.5 <= y <= y1 - 1.5:
                checks.append((v, c0, c1, r, y0, y1))
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
    """Final vertex positions, back in Godot coordinates: band vertices sit at r-TOL_IN .. r+TOL_OUT."""
    worst_lo, worst_hi, n = 9.0, -9.0, 0
    for v, c0, c1, r, y0, y1 in checks:
        gx, gy, gz = v.co.x, v.co.z, -v.co.y
        assert y0 + 1.5 - 1e-6 <= gy <= y1 - 1.5 + 1e-6, "%s: band vertex outside height band" % name
        dist = math.hypot(gx - c0, gz - c1)
        assert r - TOL_IN <= dist <= r + TOL_OUT, (
            "%s: band vertex at dist %.3f, r %.2f (limits -%.2f / +%.2f)" % (name, dist, r, TOL_IN, TOL_OUT))
        worst_lo, worst_hi, n = min(worst_lo, dist - r), max(worst_hi, dist - r), n + 1
    print("SELFCHECK %s: %d band verts, offset from r in [%.3f, %.3f] within [-%.2f, +%.2f]"
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
