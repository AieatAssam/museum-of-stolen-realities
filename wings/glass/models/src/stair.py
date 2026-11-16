"""Gothic glass tower stair. Arg = part (Blender X along the flight, Z up):
  tower_flight <gold|red>  one straight flight along +X, x 0..7 (slope 2.4 over 7), width y +-1.3, 12 steps.
               Origin at the start of the slope on the centreline. Glass treads with brass nosings, a quarry
               soffit with lead ribs, lead stringers with brass rolls, a lead balustrade with pointed tracery.
  tower_landing  2.5 x 8.2 m landing slab, top face at z=0, centred on the origin. Quarry field, lead edge
               moulding, brass border line, brass eight-point star, lead drip under the edge."""
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import pointed, roll, sweep  # noqa: E402

RUN, RISE = 7.0, 2.4
STEPS = 12
STEP_RUN = RUN / STEPS                 # 0.583
STEP_RISE = RISE / STEPS               # 0.2
SLOPE = math.hypot(RUN, RISE)          # 7.4, the walking line's length
DX, DZ = RUN / SLOPE, RISE / SLOPE     # unit tangent in x-z
NX, NZ = -DZ, DX                       # unit normal (up and back)
ANG = math.atan2(RISE, RUN)
HALF_W = 1.3
STR_Y = 1.36                           # stringer and balustrade plane
RAIL = 0.95                            # handrail height above the walking line (vertical)
LEAD_SEC = [(-0.015, -0.025), (0.015, -0.025), (0.015, 0.025), (-0.015, 0.025)]   # 0.03 x 0.05 came
STRINGER = [(0.0, -0.09), (0.0, 0.09), (0.42, 0.09), (0.45, 0.06), (0.45, -0.06), (0.42, -0.09)]


def line_z(x):
    return x * RISE / RUN


def slope_pt(L, off, y):
    """Point at length L along the walking line, off along its normal, y across the flight -> (x, y, z)."""
    return (L * DX + off * NX, y, L * DZ + off * NZ)


def _side_place(s):
    return lambda h, y, v: slope_pt(h, y, s * STR_Y + v)


def _panel_place(lc, off0, s):
    return lambda h, y, v: slope_pt(lc + h, off0 + y, s * STR_Y + v)


def prism(name, ring, d, mat, smooth=40.0):
    """Extrude a closed planar ring of 3D points by vector d."""
    bm = bmesh.new()
    n = len(ring)
    a = [bm.verts.new(p) for p in ring]
    b = [bm.verts.new(Vector(p) + Vector(d)) for p in ring]
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def _tread_parts(glass, p):
    for k in range(STEPS):
        x0, x1 = k * STEP_RUN, (k + 1) * STEP_RUN
        top = (k + 0.5) * STEP_RISE
        p.append(kit.box("tread", (STEP_RUN, 2 * HALF_W, 0.06), ((x0 + x1) / 2, 0, top - 0.03), mat=glass, bevel=0.008))
        zb, zt = max(0.0, (k - 0.5) * STEP_RISE), top - 0.06
        p.append(kit.box("riser", (0.03, 2 * HALF_W, zt - zb), (x0, 0, (zb + zt) / 2), mat=glass, bevel=0.006))
        p.append(kit.tube("nosing", [(x0, -HALF_W, top - 0.02), (x0, HALF_W, top - 0.02)], 0.025, 8, mat="brass"))


def _balustrade(p):
    span = (STEP_RUN - 0.06) / DX          # arch width measured along the slope
    off0 = 0.12
    for s in (-1, 1):
        for i in range(STEPS):
            lc = (i + 0.5) * STEP_RUN / DX
            p.append(sweep("tracery", LEAD_SEC, pointed(span, 0.55, 10), "lead", place=_panel_place(lc, off0, s)))
            p.append(sweep("tracery_in", LEAD_SEC, pointed(span * 0.46, 0.27, 8), "lead", place=_panel_place(lc, off0 + 0.08, s)))
        for i in range(STEPS + 1):
            x = i * STEP_RUN
            zb, zt = line_z(x) - 0.06, line_z(x) + RAIL - 0.03
            post = kit.box("post", (0.06, 0.06, zt - zb), (x, s * STR_Y, (zb + zt) / 2), mat="lead", bevel=0.01)
            p.append(post)
            cap = kit.lathe("cap", [(0.0, 0.0), (0.03, 0.005), (0.04, 0.02), (0.03, 0.035), (0.0, 0.04)], 8, mat="brass")
            cap.location = (x, s * STR_Y, zt)
            p.append(cap)
        rail = [(x, s * STR_Y, line_z(x) + RAIL) for x in (RUN * j / 16 for j in range(17))]
        p.append(kit.tube("handrail", rail, 0.03, 8, mat="brass"))


def flight(variant):
    if variant not in ("gold", "red"):
        raise SystemExit("tower_flight needs gold or red")
    glass = "glass_%s_m" % variant
    p = []
    _tread_parts(glass, p)

    # sloped soffit plate, 0.33..0.41 below the walking line, spanning the full width
    off_pts = [(0.0, -0.33), (SLOPE, -0.33), (SLOPE, -0.41), (0.0, -0.41)]
    ring = [slope_pt(L, o, -HALF_W) for L, o in off_pts]
    p.append(prism("soffit", ring, (0, 2 * HALF_W, 0), "glass_quarry"))
    for k in range(6):                       # transverse lead ribs under the plate, every 1.2 m
        rib = kit.box("rib", (0.07, 2 * HALF_W, 0.08), (0, 0, 0), mat="lead", bevel=0.012)
        rib.location = slope_pt(0.6 + 1.2 * k, -0.45, 0)
        rib.rotation_euler = (0, -ANG, 0)
        p.append(rib)

    # stringers: lead moulding with a brass roll on the outer face, lower arris chamfered
    path = [(SLOPE * j / 24, -0.06) for j in range(25)]
    for s in (-1, 1):
        p.append(sweep("stringer", STRINGER, path, "lead", place=_side_place(s), smooth=40.0))
        p.append(sweep("stringer_roll", roll(0.022, 8, 0.22, 0.09 * s), path, "brass", place=_side_place(s), smooth=70.0))

    _balustrade(p)
    kit.join("tower_flight", p)


def star_ring(n=8, R=0.6, r=0.23):
    pts = []
    for k in range(2 * n):
        a = math.pi * k / n
        rad = R if k % 2 == 0 else r
        pts.append((rad * math.cos(a), rad * math.sin(a), 0.0))
    return pts


def landing():
    def rect(a, b, z):
        return [(-a, -b, z), (a, -b, z), (a, b, z), (-a, b, z)]          # counter-clockwise from above

    p = [kit.box("field", (2.5, 8.2, 0.4), (0, 0, -0.2), mat="glass_quarry", bevel=0.02)]
    p.append(kit.sweep_closed("edge", [(-0.05, 0.0), (-0.03, 0.02), (0.03, 0.02), (0.05, 0.0)], rect(1.2, 4.05, 0.0), mat="lead"))
    p.append(kit.sweep_closed("border", [(-0.015, 0.0), (0.015, 0.0), (0.015, 0.005), (-0.015, 0.005)], rect(1.1, 3.95, 0.0), mat="brass"))
    p.append(kit.sweep_closed("drip", [(0.0, 0.0), (0.035, -0.005), (0.035, -0.02), (0.0, -0.035)], rect(1.25, 4.1, -0.4), mat="lead"))
    p.append(prism("star", star_ring(), (0, 0, 0.005), "brass", smooth=10.0))
    kit.join("tower_landing", p)


def build(args):
    if args[0] == "tower_flight":
        flight(args[1] if len(args) > 1 else "gold")
    elif args[0] == "tower_landing":
        landing()
    else:
        raise SystemExit("unknown part: %s" % args[0])
