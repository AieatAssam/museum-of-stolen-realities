"""Chitin Court eye lid (pass 4c): visual-only carapace ceiling over the hive shaft's amber eye.

Build: tools/blender_build.sh wings/chitin/models/src/eye_lid.py wings/chitin/models/eye_lid.glb eye_lid

The eye is a hemisphere of radius 60 centred (115, 20, -8), opening down at y 20; from the districts its
underside reads as a flat comb ceiling. This lid hangs under that rim: a membrane from an irregular oculus
lip (y ~14, radius ~20-26 about (115, -8), rolled tube) out to the rim circle (radius 60, y 20). Between
radial ribs the underside sags into uneven domes; wax drips and stalactite stumps hang from it, and a few
comb patches (comb_patch.build_patches) sit near the oculus rim.

Godot world coordinates throughout; Blender (x, y, z) = (x, -z, y) via rooms._blender.
Hard limits, self-checked at the end of build(): nothing above y 20; nothing below y 12 inside the shaft
footprint x 80..150, z -30..14; outside it nothing below y 16 except drips and stalactites, which stop at
y 13. The brief's sag bottoms (y 9-12) cannot satisfy those limits, so the sag stops at ~13.4 inside the
footprint and ~16.5 outside.

Outputs: eye_lid (lip and membrane, carapace), eye_lid_comb (comb patches), eye_lid_drip (wax),
eye_lid_stal (stalactites, carapace_dull).
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import comb_patch  # noqa: E402
import kit  # noqa: E402
import rooms  # noqa: E402

TAU = 2.0 * math.pi
CX, CZ = 115.0, -8.0
RIM_R = 60.0
RIM_Y = 20.0
LIP_Y = 14.0
FOOT = (80.0, 150.0, -30.0, 14.0)  # shaft footprint x0, x1, z0, z1 (Godot)
LIM_IN = 12.8    # membrane floor inside the footprint, reached RAMP m inside the edge
LIM_OUT = 16.3   # membrane floor outside the footprint
RAMP = 4.0
N_TH = 240
N_T = 28
N_RIB = 12
DRIP_N = 70
STAL_N = 26
HANG_IN = 12.3   # drips and stalactites inside the footprint (hard limit 12)
HANG_OUT = 13.0  # drips and stalactites outside the footprint (hard limit 13)
PATCH_MIN_Y = 16.8


# --- geometry in Godot coordinates -----------------------------------------------------------------

def r_oc(th):
    """Oculus radius about (CX, CZ), angle th: roughly round, short along z so the lip stays in the footprint."""
    return 21.6 + 1.8 * math.cos(2 * th) + 0.8 * math.sin(3 * th + 0.7) + 0.45 * math.sin(5 * th + 1.9)


def lip_c(th):
    """Lip centreline height."""
    return LIP_Y + 0.15 * math.sin(4 * th + 0.3)


def lip_r(th):
    """Rolled lip tube radius (thick rim)."""
    return 0.8 + 0.12 * math.sin(6 * th + 2.1)


def rim_start(th):
    """Radius where the membrane starts: the outer equator of the lip tube."""
    return r_oc(th) + lip_r(th)


def in_foot(x, z):
    return FOOT[0] <= x <= FOOT[1] and FOOT[2] <= z <= FOOT[3]


def ylim(x, z):
    """Lowest the membrane may sag at (x, z): 16.3 outside, ramping down to 12.8 inside the footprint."""
    if not in_foot(x, z):
        return LIM_OUT
    d = min(x - FOOT[0], FOOT[1] - x, z - FOOT[2], FOOT[3] - z)
    return LIM_OUT - (LIM_OUT - LIM_IN) * rooms._smooth(0.0, RAMP, d)


RIB_TH = [TAU * k / N_RIB + 0.05 * math.sin(1.7 * k) for k in range(N_RIB)]
CELL_AMP = [0.55 + 0.45 * rooms._hash(k, 3) for k in range(N_RIB)]


def cell(th):
    """Rib cell index and fractional position across it (0 on a rib, 1 at the next rib)."""
    t = th % TAU
    if t < RIB_TH[0]:
        t += TAU
    for k in range(N_RIB):
        a = RIB_TH[k]
        b = RIB_TH[k + 1] if k + 1 < N_RIB else RIB_TH[0] + TAU
        if a <= t < b:
            return k, (t - a) / (b - a)
    raise AssertionError("cell lookup")


def surface(th, t):
    """Membrane underside at angle th, radial fraction t (0 at the lip, 1 at the rim): Godot (x, y, z)."""
    rs = rim_start(th)
    rho = rs + t * (RIM_R - rs)
    x = CX + rho * math.cos(th)
    z = CZ + rho * math.sin(th)
    yc = lip_c(th)
    base = yc + (RIM_Y - yc) * rooms._smooth(0.0, 2.0, rho - rs)
    k, f = cell(th)
    sag = CELL_AMP[k] * math.sin(math.pi * f) ** 0.8 * max(0.0, math.sin(math.pi * t)) ** 0.6
    lo = min(ylim(x, z), base)
    y = base - (base - lo) * 0.92 * sag
    return (x, y, z)


def _radial(th, rho):
    return (CX + rho * math.cos(th), CZ + rho * math.sin(th))


# --- mesh pieces -----------------------------------------------------------------------------------

def build_sheet(bm):
    """Membrane grid: N_TH angles x N_T radial rings, rim-ward rings denser near the lip."""
    TS = [(i / N_T) ** 1.6 for i in range(N_T + 1)]
    grid = []
    for j in range(N_TH):
        th = TAU * j / N_TH
        grid.append([bm.verts.new(rooms._blender(surface(th, t))) for t in TS])
    faces, mats = [], []
    for j in range(N_TH):
        j1 = (j + 1) % N_TH
        for i in range(N_T):
            faces.append(bm.faces.new((grid[j][i], grid[j][i + 1], grid[j1][i + 1], grid[j1][i])))
            mats.append(1 if TS[i] > 0.6 else 0)
    return faces, mats


def build_lip(bm):
    """Rolled lip: an 8-sided tube swept round the oculus centreline."""
    rings = []
    for j in range(N_TH):
        th = TAU * j / N_TH
        ro, R, yc = r_oc(th), lip_r(th), lip_c(th)
        ring = []
        for m in range(8):
            ph = TAU * m / 8
            rr = ro + R * math.cos(ph)
            ring.append(bm.verts.new(rooms._blender((CX + rr * math.cos(th), yc + R * math.sin(ph),
                                                     CZ + rr * math.sin(th)))))
        rings.append(ring)
    faces = []
    for j in range(N_TH):
        j1 = (j + 1) % N_TH
        for m in range(8):
            m1 = (m + 1) % 8
            faces.append(bm.faces.new((rings[j][m], rings[j][m1], rings[j1][m1], rings[j1][m])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def spike(bm, top, L, rb, rt, sides):
    """Closed tapered spike hanging down from Blender point top: base radius rb, tip radius rt, length L."""
    ring_t = [bm.verts.new(top + Vector((rb * math.cos(TAU * k / sides), rb * math.sin(TAU * k / sides), 0.0)))
              for k in range(sides)]
    ring_b = [bm.verts.new(top + Vector((rt * math.cos(TAU * k / sides), rt * math.sin(TAU * k / sides), -L)))
              for k in range(sides)]
    ct = bm.verts.new(top)
    cb = bm.verts.new(top + Vector((0.0, 0.0, -L)))
    faces = []
    for k in range(sides):
        k1 = (k + 1) % sides
        faces.append(bm.faces.new((ring_t[k], ring_t[k1], ring_b[k1], ring_b[k])))
        faces.append(bm.faces.new((ct, ring_t[k1], ring_t[k])))
        faces.append(bm.faces.new((cb, ring_b[k], ring_b[k1])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def hang_points(rng, count, rb_range, rt_range, len_range, sides, bm):
    """Hanging pieces from random underside points; each is cut short to stay above its floor."""
    made = 0
    for _ in range(count):
        th = rng.uniform(0.0, TAU)
        t = rng.uniform(0.05, 0.9)
        x, y, z = surface(th, t)
        lim = HANG_IN if in_foot(x, z) else HANG_OUT
        L = min(rng.uniform(*len_range), y - 0.03 - lim)
        if L < 0.5:
            continue
        spike(bm, rooms._blender((x, y - 0.03, z)), L, rng.uniform(*rb_range), rng.uniform(*rt_range), sides)
        made += 1
    return made


def obj_from_bm(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(kit.material(m))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# --- self-check ------------------------------------------------------------------------------------

def selfcheck(objs):
    """Asserts the brief's hard limits on every final vertex (Godot coordinates)."""
    for th in [TAU * i / 720 for i in range(720)]:
        assert 19.0 <= r_oc(th) <= 26.0, "oculus radius %.2f out of range" % r_oc(th)
    lo_in = lo_out = lo_hang_out = 99.0
    hi = -99.0
    tris = 0
    for ob in objs:
        hang = ob.name.startswith(("eye_lid_drip", "eye_lid_stal"))
        for v in ob.data.vertices:
            gx, gy, gz = v.co.x, v.co.z, -v.co.y
            assert gy <= RIM_Y + 1e-6, "%s: vertex above y 20 (%.3f)" % (ob.name, gy)
            assert math.hypot(gx - CX, gz - CZ) <= RIM_R + 0.5, "%s: vertex outside the dome circle" % ob.name
            hi = max(hi, gy)
            if in_foot(gx, gz):
                assert gy >= 12.0, "%s: below y 12 in the shaft footprint (%.3f at %.2f,%.2f)" % (ob.name, gy, gx, gz)
                lo_in = min(lo_in, gy)
            elif hang:
                assert gy >= HANG_OUT, "%s: hanging piece below y 13 outside (%.3f)" % (ob.name, gy)
                lo_hang_out = min(lo_hang_out, gy)
            else:
                assert gy >= 16.0, "%s: below y 16 outside the footprint (%.3f at %.2f,%.2f)" % (ob.name, gy, gx, gz)
                lo_out = min(lo_out, gy)
        tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("SELFCHECK eye_lid: max y %.3f (<= 20); min y inside footprint %.3f (>= 12); min y outside %.3f "
          "(>= 16); min hanging outside %.3f (>= 13); all asserts passed" % (hi, lo_in, lo_out, lo_hang_out))
    print("SELFCHECK eye_lid: oculus radius range %.2f..%.2f; total tris %d (cap 60000)"
          % (min(r_oc(TAU * i / 720) for i in range(720)), max(r_oc(TAU * i / 720) for i in range(720)), tris))
    return tris


# --- build -----------------------------------------------------------------------------------------

def build(args):
    rng = random.Random(4201)

    bm = bmesh.new()
    sheet, mats = build_sheet(bm)
    lip = build_lip(bm)
    bm.normal_update()
    for f in sheet:  # the membrane is seen from below: underside normals point down
        if f.normal.z > 0.0:
            f.normal_flip()
    bm.normal_update()
    for f, m in zip(sheet, mats):
        f.material_index = m
    for f in lip:
        f.material_index = 0
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40.0):
            e.smooth = False
    for f in bm.faces:
        f.smooth = True

    # comb patches: three short flows just outside the oculus rim, rays shot up from below through the hole
    # side (wall check disabled with wall_top=-1e9: nothing here is a wall)
    def patch_gap(g):
        dx, dz = g[0] - CX, g[2] - CZ
        return math.hypot(dx, dz) - rim_start(math.atan2(dz, dx) % TAU)

    def radius(g):
        dr = patch_gap(g)
        if dr < 2.8 or dr > 9.0 or g[1] < PATCH_MIN_Y or math.hypot(g[0] - CX, g[2] - CZ) > 56.0:
            return 0.0
        return dr - 1.2

    def flow(th0, th1, dd, n):
        out = []
        for k in range(n):
            th = th0 + (th1 - th0) * k / (n - 1)
            x, z = _radial(th, rim_start(th) + dd)
            size = math.sin(math.pi * k / (n - 1)) ** 0.7
            out.append((rooms._blender((x, 2.0, z)), Vector((0.0, 0.0, 1.0)), size))
        return out

    flows = [flow(0.5, 1.1, 4.0, 7), flow(3.6, 4.4, 5.0, 7), flow(-2.6, -2.0, 4.5, 7)]
    pbm, pst = comb_patch.build_flows(bm, "eye_lid_comb", flows, radius, lambda g: 0.0,
                                      -1e9, 0.3, 20000, cheap=False)
    comb_obj = comb_patch.make_object("eye_lid_comb", pbm)

    shell = obj_from_bm("eye_lid", bm, ["carapace", "carapace_dull"])

    bd = bmesh.new()
    nd = hang_points(rng, DRIP_N, (0.05, 0.08), (0.02, 0.03), (0.5, 3.0), 6, bd)
    drip_obj = obj_from_bm("eye_lid_drip", bd, ["wax"])
    bs = bmesh.new()
    ns = hang_points(rng, STAL_N, (0.22, 0.32), (0.04, 0.06), (1.0, 4.0), 8, bs)
    stal_obj = obj_from_bm("eye_lid_stal", bs, ["carapace_dull"])
    print("LID eye_lid: %d membrane faces, %d lip faces, %d comb patches, %d drips, %d stalactites"
          % (len(sheet), len(lip), pst["blobs"], nd, ns))

    selfcheck([shell, comb_obj, drip_obj, stal_obj])
