"""Paint wing props: the inside of an oil painting. Loose, hand-made forms: every part is bevelled,
tapered or lumped, and vertices are nudged a few centimetres so no line is ruler-straight.
One script, selected by args[0]. Run through tools/blender_build.sh (wings/paint/tools/build_props.sh
builds them all).
Blender: +Z up, 1 unit = 1 m, origin at base centre on the ground unless stated. Material names are the
contract (Godot swaps them): p_wood p_wood_dark p_plaster p_roof p_red p_blue p_steel p_brass p_gilt
p_canvas p_bark."""
import math
import os
import random
import sys

import bmesh
import bpy  # noqa: F401  (used by the sculpt helpers' scene operations)
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "clay", "models", "src"))
import kit  # noqa: E402  (tools/blender is on sys.path through tools/blender/export.py)
import sculpt as S  # noqa: E402

TAU = 2 * math.pi


# --- helpers ------------------------------------------------------------------------------------

def _bm_obj(name, bm, mat, seed=0, lump=0.0, scale=1.6, smooth=40.0, dents=0):
    """Finish a bmesh: fix normals, hand-jitter it (noise along normals, metres ~ lump), make an object."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if lump or dents:
        S.deform(bm, seed, lump, scale, dents, 0.06, 0.012)
    return kit._obj(name, bm, mat, smooth)


def _jit(ob, seed, lump, scale=1.6, dents=0):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    S.deform(bm, seed, lump, scale, dents, 0.08, 0.012)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def _xf(ob, m):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def _bez(p0, p1, p2, p3, n):
    """Cubic bezier, n samples (p0 excluded, p3 included)."""
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k] for k in (0, 1)))
    return out


def _arc(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(a), c[1] + r * math.sin(a))
            for a in [a0 + (a1 - a0) * i / n for i in range(1, n + 1)]]


def _prism(name, tri, x0, x1, mat, seed):
    """Triangle (y, z) extruded along X from x0 to x1: a gable end."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in tri]
    b = [bm.verts.new((x1, y, z)) for y, z in tri]
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    n = len(tri)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    return _bm_obj(name, bm, mat, seed, 0.012, 2.0)


def _beads(name, centres, r, mat):
    bm = bmesh.new()
    for c in centres:
        ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        bmesh.ops.translate(bm, vec=Vector(c), verts=ret["verts"])
    return _bm_obj(name, bm, mat, 0, 0.0, smooth=None)


# --- 1. mill ------------------------------------------------------------------------------------

def _roof(name, mat, seed):
    """Pitched roof: two sloping sides swept as stepped tile courses, eaves overhang, ridge sag."""
    bm = bmesh.new()
    cols = [-4.3 + 8.6 * i / 10 for i in range(11)]
    courses = 9
    for sig in (-1, 1):
        ny, nz = 3.2 * sig, 3.6
        nl = math.hypot(ny, nz)
        ny, nz = ny / nl, nz / nl
        prof = []
        for k in range(courses):
            s0, s1 = k / courses, (k + 1) / courses
            prof += [(s0, 0.0), (s0 + 0.02, 0.05), (s1 - 0.005, 0.0)]
        prof.append((1.0, 0.0))
        rows = []
        for s, off in prof:
            row = []
            for x in cols:
                y = sig * 3.6 * (1 - s) + ny * off
                z = 3.8 + 3.2 * s + nz * off - 0.18 * s ** 6 * (1 - (x / 4.3) ** 2)
                row.append(bm.verts.new((x + random.uniform(-0.01, 0.01), y, z)))
            rows.append(row)
        for r in range(len(rows) - 1):
            for c in range(len(cols) - 1):
                bm.faces.new((rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return _bm_obj(name, bm, mat, seed, 0.012, 1.4, smooth=35.0)


def _waterwheel(out):
    cx, cy, cz = 4.8, 0.0, 2.3
    rim = kit.torus("wheel_rim", 2.2, 0.075, seg=64, rseg=10, mat="p_wood", loc=(cx, cy, cz), rot=(0, math.pi / 2, 0))
    out.append(_jit(rim, 501, 0.01))
    for i in range(12):
        a = i * TAU / 12
        c = (cx, cy + 1.95 * math.cos(a), cz + 1.95 * math.sin(a))
        # board: 0.5 wide along the axle (X), 0.56 long radially (Z local), 0.06 thick tangentially (Y local)
        out.append(S.slab("paddle%02d" % i, (0.5, 0.06, 0.56), c, "p_wood", 510 + i, lump=0.008, bevel=0.012, cuts=2, rot=(a + math.pi / 2, 0, 0)))
    for i in range(8):
        a = i * TAU / 8 + 0.1
        ca, sa = math.cos(a), math.sin(a)
        out.append(S.snake("spoke%d" % i, [(cx, cy + 0.15 * ca, cz + 0.15 * sa), (cx, cy + 1.85 * ca, cz + 1.85 * sa)],
                           0.035, "p_wood", 530 + i, sides=6, wobble=0.05, steps=2))
    out.append(S.blob("wheel_hub", (0.42, 0.3, 0.3), (cx, cy, cz), "p_wood", 541, lump=0.01, subdiv=2))
    out.append(S.snake("axle", [(3.9, cy, cz), (cx, cy, cz), (5.55, cy, cz)], 0.07, "p_wood", 542, sides=8, wobble=0.03, steps=2))


def B_mill():
    out = []
    # plaster walls, bevelled and lumped
    out.append(S.slab("mill_walls", (8.0, 6.0, 3.8), (0, 0, 1.9), "p_plaster", 301, lump=0.03, bevel=0.1, cuts=5))
    # gable ends, triangles that sit under the roof
    for sx in (-1, 1):
        out.append(_prism("mill_gable", [(-3.1, 3.7), (3.1, 3.7), (0.0, 6.9)], sx * 3.875, sx * 4.0, "p_plaster", 310 + sx))
    # timber framing proud of the wall: posts and girts on both long faces and the short ends
    k = 0
    for sy in (-1, 1):
        y = sy * 3.05
        for x in (-3.9, -1.3, 1.3, 3.9):
            k += 1
            out.append(S.slab("beam_post", (0.22, 0.1, 3.8), (x, y, 1.9), "p_wood_dark", 400 + k, lump=0.006, bevel=0.02, cuts=2))
        for z in (1.2, 2.6):
            k += 1
            out.append(S.slab("beam_girt", (8.1, 0.1, 0.2), (0, y, z), "p_wood_dark", 400 + k, lump=0.006, bevel=0.02, cuts=2))
    for sx in (-1, 1):
        x = sx * 4.05
        for y in (-2.0, 2.0):
            k += 1
            out.append(S.slab("beam_post", (0.1, 0.22, 3.8), (x, y, 1.9), "p_wood_dark", 400 + k, lump=0.006, bevel=0.02, cuts=2))
        for z in (1.2, 2.6):
            k += 1
            out.append(S.slab("beam_girt", (0.1, 6.1, 0.2), (x, 0, z), "p_wood_dark", 400 + k, lump=0.006, bevel=0.02, cuts=2))
    # door (front, left of centre) with a lintel
    out.append(S.slab("mill_door", (1.0, 0.08, 2.2), (-2.6, -3.03, 1.1), "p_wood_dark", 421, lump=0.01, bevel=0.02, cuts=2))
    out.append(S.slab("door_lintel", (1.3, 0.12, 0.14), (-2.6, -3.08, 2.25), "p_wood_dark", 422, lump=0.006, bevel=0.03, cuts=2))
    # two small deep-set windows: a dark recessed shutter behind a proud sill and frame
    for wx in (0.0, 2.6):
        out.append(S.slab("window_dark", (0.7, 0.04, 0.8), (wx, -3.02, 2.0), "p_wood_dark", 430 + int(wx * 3), lump=0.005, bevel=0.01, cuts=2))
        out.append(S.slab("window_sill", (0.9, 0.22, 0.09), (wx, -3.12, 1.55), "p_plaster", 436 + int(wx * 3), lump=0.01, bevel=0.03, cuts=2))
        out.append(S.slab("window_head", (0.86, 0.12, 0.08), (wx, -3.07, 2.46), "p_wood_dark", 440 + int(wx * 3), lump=0.006, bevel=0.02, cuts=2))
    # pitched roof, overhanging eaves, stepped tile courses; chimney
    out.append(_roof("mill_roof", "p_roof", 450))
    out.append(S.slab("chimney", (0.7, 0.7, 3.0), (2.6, -1.4, 6.0), "p_plaster", 460, lump=0.02, bevel=0.05, cuts=2))
    out.append(S.slab("chimney_cap", (0.84, 0.84, 0.1), (2.6, -1.4, 7.5), "p_wood_dark", 461, lump=0.01, bevel=0.03, cuts=2))
    # the waterwheel on the +X side
    _waterwheel(out)


# --- 2. boat ------------------------------------------------------------------------------------

def _hull_w(y):
    t = min(abs(y) / 2.1, 1.0)
    return max(0.70 * (1 - t ** 3) ** 0.5, 0.03)


def _hull_top(y):
    return 0.6 + 0.10 * (min(abs(y) / 2.1, 1.0)) ** 2.5


def _hull_keel(y):
    return 0.17 * (min(abs(y) / 2.1, 1.0)) ** 2.5


def _hp(y, s):
    """Cross-section point on the hull at station y: s = 0 port gunwale, 1 starboard, bottom at s = 0.5."""
    w, top, keel = _hull_w(y), _hull_top(y), _hull_keel(y)
    x = -w * math.cos(math.pi * s)
    z = top - (top - keel) * math.sin(math.pi * s) ** 0.85
    return (x, y, z)


def B_boat():
    out = []
    ny = 25
    stations = [-2.1 + 4.2 * i / (ny - 1) for i in range(ny)]
    bounds = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    bm = bmesh.new()
    grid = []
    for y in stations:
        zmid = 0.5 * (_hull_top(y) + _hull_keel(y))
        row = []
        for k in range(len(bounds) - 1):
            a, b = bounds[k], bounds[k + 1]
            off = 0.012 + 0.016 * (k % 2)  # alternating strakes, one proud of the next
            band = []
            for j in range(3):
                s = a + (b - a) * j / 2
                x, yy, z = _hp(y, s)
                n = Vector((x, 0.0, z - zmid)).normalized()
                band.append(bm.verts.new((x + n.x * off, yy, z + n.z * off)))
            row.append(band)
        grid.append(row)
    for i in range(ny - 1):
        for k in range(len(bounds) - 1):
            for j in range(2):
                a, b = grid[i][k], grid[i + 1][k]
                bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    hull = _bm_obj("boat_hull", bm, "p_wood", 601, 0.008, 4.0, smooth=35.0)
    out.append(hull)
    # gunwales and the red stripe just below them
    for sgn, s in ((-1, 0.0), (1, 1.0)):
        ys = [-2.05 + 4.1 * i / 8 for i in range(9)]
        pts = []
        for y in ys:
            x, yy, z = _hp(y, s)
            pts.append((x + sgn * 0.01, yy, z + 0.01))
        out.append(S.snake("gunwale", pts, 0.03, "p_wood", 610 + (sgn > 0), sides=6, wobble=0.04, steps=2))
        stripe = []
        for y in ys:
            x, yy, z = _hp(y, 0.1 if sgn < 0 else 0.9)
            stripe.append((x + sgn * 0.012, yy, z))
        out.append(S.snake("gunwale_stripe", stripe, 0.017, "p_red", 620 + (sgn > 0), sides=6, wobble=0.03, steps=2))
    # three thwarts across, bevelled
    for i, y in enumerate((-1.0, 0.1, 1.1)):
        w = _hull_w(y)
        out.append(S.slab("thwart", (2 * w * 0.96, 0.2, 0.035), (0, y, _hull_top(y) - 0.08), "p_wood", 630 + i, lump=0.004, bevel=0.01, cuts=2))
    # two oars resting across the gunwale, one blade each
    for i, y in enumerate((0.42, 0.52)):
        z = _hull_top(y) + 0.07
        out.append(S.snake("oar", [(-0.7, y, z), (0.4, y, z), (0.63, y, z - 0.01)], 0.018, "p_wood", 640 + i, sides=6, wobble=0.05, steps=3))
        out.append(S.slab("oar_blade", (0.34, 0.1, 0.012), (0.8, y, z - 0.01), "p_wood", 645 + i, lump=0.003, bevel=0.004, cuts=2))
    # hull keel sits at z = 0.17: lift so the lowest point rests on the ground
    for ob in out:
        ob.location.z -= 0.17
    return out


# --- 3. frame -----------------------------------------------------------------------------------

def _frame_profile():
    """(u, v) moulding: u outward from the path (-0.5 inner edge, +0.5 outer), v toward the viewer."""
    p = [(-0.5, -0.3), (-0.5, -0.04)]
    p += _arc((-0.44, 0.03), 0.06, math.pi, 0.0, 6)                       # bead on the inner sight edge
    p += _bez((-0.38, 0.03), (-0.30, 0.03), (-0.20, 0.06), (-0.20, 0.14), 4)  # cove
    p += _bez((-0.20, 0.14), (-0.10, 0.14), (-0.10, 0.26), (0.05, 0.26), 4)   # ogee
    p += _bez((0.05, 0.26), (0.15, 0.30), (0.22, 0.30), (0.30, 0.30), 3)      # flat fillet
    p += _bez((0.30, 0.30), (0.42, 0.30), (0.50, 0.22), (0.50, 0.10), 4)      # outer roll
    p += [(0.5, -0.04), (0.5, -0.3)]
    return p


def _frame_path(h=6.0, k=6):
    corners = [(-h, -h), (h, -h), (h, h), (-h, h)]
    pts = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        for j in range(k + 1):
            t = j / (k + 1)
            pts.append((a[0] + (b[0] - a[0]) * t, 0.0, a[1] + (b[1] - a[1]) * t))
    return pts


def B_frame():
    out = []
    from_kit = kit.sweep_closed("frame_moulding", _frame_profile(), _frame_path(), mat="p_gilt", smooth_angle=35.0)
    out.append(_jit(from_kit, 701, 0.02, 2.5))
    # carved corner cartouches: lumpy acanthus-like blobs with two leaves each
    for sx in (-1, 1):
        for sz in (-1, 1):
            cx, cz = sx * 6.0, sz * 6.0
            out.append(S.blob("cartouche", (1.3, 0.6, 1.3), (cx, -0.3, cz), "p_gilt", 710 + sx + 2 * sz, lump=0.07, subdiv=3, dents=2, dent_r=0.2, dent_d=0.04))
            out.append(S.blob("leaf", (0.5, 0.35, 0.9), (cx - sx * 0.85, -0.34, cz), "p_gilt", 720 + sx + 2 * sz, lump=0.05, subdiv=2))
            out.append(S.blob("leaf", (0.9, 0.35, 0.5), (cx, -0.34, cz - sz * 0.85), "p_gilt", 730 + sx + 2 * sz, lump=0.05, subdiv=2))
    # a bead row along the inner sight edge
    centres = []
    for t in [-5.0 + 10.0 * i / 9 for i in range(10)]:
        centres += [(t, -0.03, -5.56), (t, -0.03, 5.56), (-5.56, -0.03, t), (5.56, -0.03, t)]
    out.append(_beads("frame_beads", centres, 0.05, "p_gilt"))
    return out


# --- 4. stretcher -------------------------------------------------------------------------------

def _canvas(name, seed):
    """Raw canvas over the top and down one side; its free edge hangs jagged along the length."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    rows = []
    n = 41
    for i in range(n):
        y = -5.0 + 10.0 * i / (n - 1)
        zb = 1.22 + rnd.uniform(-0.1, 0.14) + (0.08 if i % 2 else 0.0)
        prof = [(-1.0, 2.025), (0.0, 2.03), (1.0, 2.025), (1.03, 1.92), (1.035, 1.6), (1.03, zb)]
        rows.append([bm.verts.new((x + rnd.uniform(-0.006, 0.006), y + rnd.uniform(-0.03, 0.03), z + rnd.uniform(-0.006, 0.006))) for x, z in prof])
    for i in range(n - 1):
        for j in range(len(rows[0]) - 1):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, "p_canvas", None)


def B_stretcher():
    out = []
    out.append(S.slab("stretcher_bar", (2.0, 10.0, 2.0), (0, 0, 1.0), "p_wood", 801, lump=0.02, bevel=0.14, cuts=8, dents=3))
    out.append(_canvas("canvas", 802))
    for i in range(8):
        y = -3.5 + i * 1.0
        out.append(S.snake("staple", [(0.8, y, 1.53), (1.1, y, 1.53), (1.1, y, 1.47), (0.8, y, 1.47)], 0.012, "p_steel", 810 + i, sides=6, wobble=0.05, steps=2))
    return out


# --- 5. post (giant paintbrush planted handle-down) --------------------------------------------

def B_post():
    out = []
    out.append(_jit(kit.lathe("post_handle", [(0.0, 0.0), (0.02, 0.03), (0.035, 0.12), (0.045, 0.4), (0.055, 0.7), (0.062, 0.84)],
                              segments=20, mat="p_wood_dark", cap=False), 901, 0.004, 4.0))
    out.append(_jit(kit.lathe("post_ferrule", [(0.072, 0.835), (0.078, 0.85), (0.068, 0.88), (0.08, 0.9), (0.068, 0.93), (0.08, 0.955), (0.07, 0.98), (0.06, 1.0)],
                              segments=20, mat="p_brass", cap=False), 902, 0.002, 3.0))
    out.append(_jit(kit.lathe("post_bristles", [(0.066, 0.97), (0.078, 1.02), (0.084, 1.08), (0.076, 1.14), (0.05, 1.18), (0.0, 1.2)],
                              segments=20, mat="p_bark", cap=False), 903, 0.012, 3.0))
    out.append(S.blob("post_paint", (0.11, 0.11, 0.06), (0, 0, 1.19), "p_red", 904, lump=0.006, subdiv=2))
    return out


# --- 6. easel -----------------------------------------------------------------------------------

def B_easel():
    out = []
    t_y, t_z = -0.4, 2.55
    f_y, b_y = -0.9, 0.2
    for i, x in enumerate((-0.55, 0.55)):
        out.append(S.snake("leg_front", [(x, f_y, 0.02), (x, f_y + (t_y - f_y) * 0.5, 1.3), (x, t_y, t_z)], 0.03, "p_wood", 1001 + i, sides=6, wobble=0.05, steps=3))
        out.append(S.snake("leg_back", [(x, b_y, 0.02), (x, b_y + (t_y - b_y) * 0.5, 1.3), (x, t_y, t_z)], 0.03, "p_wood", 1003 + i, sides=6, wobble=0.05, steps=3))
    yf = lambda z: f_y + (t_y - f_y) * z / t_z
    out.append(S.snake("brace", [(-0.55, yf(0.6), 0.6), (0.55, yf(0.6), 0.6)], 0.022, "p_wood", 1005, sides=6, wobble=0.04, steps=2))
    out.append(S.slab("top_beam", (1.3, 0.07, 0.1), (0, t_y, t_z), "p_wood", 1006, lump=0.004, bevel=0.012, cuts=2))
    out.append(S.slab("tray", (1.25, 0.14, 0.05), (0, -0.42, 1.0), "p_wood", 1007, lump=0.004, bevel=0.012, cuts=2))
    # blank canvas resting on the tray, with a thin stretcher edge behind it
    out.append(S.slab("easel_canvas", (1.2, 0.04, 1.5), (0, -0.45, 1.775), "p_canvas", 1008, lump=0.008, bevel=0.012, cuts=4))
    out.append(S.slab("edge_top", (1.25, 0.05, 0.05), (0, -0.4, 2.5), "p_wood", 1009, lump=0.003, bevel=0.01, cuts=2))
    out.append(S.slab("edge_bottom", (1.25, 0.05, 0.05), (0, -0.4, 1.05), "p_wood", 1010, lump=0.003, bevel=0.01, cuts=2))
    for i, x in enumerate((-0.6, 0.6)):
        out.append(S.slab("edge_side", (0.05, 0.05, 1.5), (x, -0.4, 1.775), "p_wood", 1011 + i, lump=0.003, bevel=0.01, cuts=2))
    return out


# --- 7. palette ---------------------------------------------------------------------------------

def _kidney(th):
    x = 0.40 * math.cos(th)
    y = 0.30 * math.sin(th) - 0.07 * math.exp(-((th - math.pi / 2) / 0.5) ** 2)
    return x, y


def B_palette():
    rnd = random.Random(1101)
    n = 64
    outline = []
    for i in range(n):
        x, y = _kidney(TAU * i / n)
        outline.append((x + rnd.uniform(-0.008, 0.008), y + rnd.uniform(-0.008, 0.008)))
    levels = [(0.94, 0.0), (1.0, 0.006), (1.0, 0.014), (0.94, 0.02)]
    bm = bmesh.new()
    rings = []
    for s, z in levels:
        rings.append([bm.verts.new((s * x, s * y, z)) for x, y in outline])
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    pal = _bm_obj("palette", bm, "p_wood", 1102, 0.0, smooth=35.0)
    # thumb hole in the wide end, cut with a boolean (the cutter is removed by sculpt.boolean)
    cutter = kit.lathe("thumb_cutter", [(0.03, -0.05), (0.03, 0.05)], segments=16, cap=True)
    cutter.location = (-0.2, 0.0, 0.01)
    S.boolean(pal, cutter)
    # glossy paint dabs on the rim and smeared mixtures
    dabs = ["p_red", "p_blue", "p_canvas", "p_brass", "p_red", "p_blue", "p_canvas", "p_brass"]
    for i, th in enumerate([0.3, 1.0, 1.7, 2.6, 3.4, 4.2, 5.0, 5.9]):
        x, y = _kidney(th)
        out_x, out_y = x * 0.84, y * 0.84
        S.blob("paint_dab", (0.07, 0.05, 0.02), (out_x, out_y, 0.02), dabs[i], 1110 + i, lump=0.002, subdiv=2)
    for i, (mat, pts) in enumerate([
        ("p_blue", [(0.1, -0.1), (0.2, -0.13), (0.27, -0.1)]),
        ("p_canvas", [(-0.05, 0.14), (0.02, 0.17), (0.1, 0.14)]),
        ("p_red", [(0.3, 0.05), (0.33, 0.1), (0.31, 0.15)]),
    ]):
        S.snake("paint_smear", [(x, y, 0.024) for x, y in pts], 0.008, mat, 1130 + i, sides=6, wobble=0.1, steps=3)  # noqa: E501
    return [pal]


# --- 8. tube (and tube_blue) --------------------------------------------------------------------

BODY = [(0.0, -0.5), (0.03, -0.48), (0.045, -0.46), (0.032, -0.44), (0.046, -0.42), (0.034, -0.40), (0.05, -0.38),
        (0.056, -0.30), (0.057, -0.10), (0.057, 0.10), (0.055, 0.22), (0.046, 0.30), (0.036, 0.34),
        (0.03, 0.36), (0.035, 0.38), (0.029, 0.40), (0.035, 0.42), (0.029, 0.44), (0.034, 0.46), (0.03, 0.5)]


def _tube_part(name, profile, mat, seed, dents=0):
    """A lathe along Z, squeezed flat (lying on its side, wide in X, thin in Z), then turned to lie along Y."""
    ob = kit.lathe(name, profile, segments=24, mat=mat, smooth_angle=40.0, cap=False)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for v in bm.verts:
        x, y, z = v.co
        f = 0.3 if z < -0.36 else 0.42  # the crimped tail is pressed flatter than the body
        v.co = Vector((x, y * f, z))
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(-math.pi / 2, 4, "X"), verts=bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    return _jit(ob, seed, 0.004, 4.0, dents)


def _tube(paint):
    out = []
    out.append(_tube_part("tube_body", BODY, "p_steel", 1201, dents=3))
    out.append(_tube_part("tube_label", [(0.061, -0.2), (0.061, 0.1)], paint, 1202))
    cap = kit.lathe("tube_cap", [(0.0, -0.035), (0.036, -0.035), (0.04, -0.025), (0.04, 0.025), (0.036, 0.035), (0.0, 0.035)],
                    segments=16, mat="p_wood_dark", cap=True)
    _xf(cap, Matrix.Translation((0.12, 0.40, 0.04)) @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    out.append(_jit(cap, 1203, 0.002))
    out.append(S.blob("tube_paint", (0.06, 0.05, 0.05), (0, 0.49, 0), paint, 1204, lump=0.002, subdiv=3))
    # the squashed tube is about 0.024 m thick: lift so it rests on the ground (z = 0)
    for ob in out:
        ob.location.z += 0.024
    return out


def B_tube():
    _tube("p_red")


def B_tube_blue():
    _tube("p_blue")


# --- dispatch -----------------------------------------------------------------------------------

def build(args):
    fns = {"mill": B_mill, "boat": B_boat, "frame": B_frame, "stretcher": B_stretcher, "post": B_post,
           "easel": B_easel, "palette": B_palette, "tube": B_tube, "tube_blue": B_tube_blue}
    fn = fns.get(args[0]) if args else None
    if fn is None:
        raise SystemExit("unknown prop: " + (args[0] if args else ""))
    fn()
