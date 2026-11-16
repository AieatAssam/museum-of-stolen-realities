"""Roofbits: broken and crypt-floor pieces for the Glass wing. Arg = part (Blender Z up, metres):
  fallen_flyer    a flying buttress fallen into a climbable ramp: coping on the slope from (0,0,0) to
                  (3.1,0,2.3), a shortened rib and lead struts under it, both ends broken, glass chunks at the foot.
  pinnacle_niche  a broken pinnacle on a buttress stump, with a canopied niche on top. Origin at the top centre of
                  the platform; the stump runs down to z -18.3. The relic sits under the canopy at about z 0.5.
  ledger          a memorial floor slab, 2.0 x 1.0 m, with a brass-inlaid recumbent figure. Origin at its centre."""
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import pointed, roll, sweep  # noqa: E402

RED, GOLD, QUARRY = "glass_red_m", "glass_gold_m", "glass_quarry"


def _put(ob, loc=(0, 0, 0), rot=(0, 0, 0)):
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def _done(name, parts):
    """Bake each part's transform into its mesh, then join, so the result keeps origin (0,0,0)."""
    for ob in parts:
        ob.data.transform(ob.matrix_basis)
        ob.location, ob.rotation_euler, ob.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    return kit.join(name, parts)


def _frustum(name, w0, w1, z0, z1, mat):
    bm = bmesh.new()
    vs = []
    for w, z in ((w0, z0), (w1, z1)):
        vs.append([bm.verts.new((sx * w / 2, sy * w / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(4):
        bm.faces.new((vs[0][i], vs[0][(i + 1) % 4], vs[1][(i + 1) % 4], vs[1][i]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 30.0)


# ---------------------------------------------------------------- fallen_flyer

TH = math.atan2(2.3, 3.1)                        # slope angle of the fallen buttress
D = Vector((math.cos(TH), 0.0, math.sin(TH)))   # along the slope (local +X)
N = Vector((-math.sin(TH), 0.0, math.cos(TH)))  # normal to the slope, up (local +Z)
TOP = Vector((3.1, 0.0, 2.3))
LEN = TOP.length
SLOPE_ROT = (0.0, -TH, 0.0)                      # local X -> D, local Z -> N
RIB_SEC = [(-0.14, -0.16), (0.08, -0.16), (0.13, -0.08), (0.13, 0.08), (0.08, 0.16), (-0.14, 0.16)]


def _on_slope(s, dz=0.0, y=0.0):
    return tuple(s * D + dz * N + Vector((0.0, y, 0.0)))


def _break(ob, half, low, high, rng, zamp):
    """Ragged low end, snapped high end: jitter the vertices in the last 0.3 m of each end."""
    for v in ob.data.vertices:
        if v.co.x > half - 0.3:
            v.co.x -= rng.uniform(0.0, high)
            v.co.z += rng.uniform(-zamp, zamp)
        elif v.co.x < -half + 0.3:
            v.co.x += rng.uniform(0.0, low)
            v.co.z += rng.uniform(-zamp, zamp)


def fallen_flyer():
    rng = random.Random(11)
    mid = TOP / 2
    s0, s1 = 0.7, 2.9

    def depth(s):
        return 0.42 + 0.3 * math.sin(math.pi * (s - s0) / (s1 - s0)) ** 0.8

    p = []
    cop = kit.box("coping", (LEN, 1.6, 0.45), mat=RED, bevel=0.05)
    _break(cop, LEN / 2, 0.25, 0.2, rng, 0.05)
    p.append(_put(cop, tuple(mid - N * 0.225), SLOPE_ROT))       # top face on the slope line
    cap = kit.box("cap", (LEN, 1.66, 0.06), mat="glass_gold_m", bevel=0.015)
    _break(cap, LEN / 2, 0.25, 0.2, rng, 0.01)
    p.append(_put(cap, tuple(mid), SLOPE_ROT))                   # lead cap, 0.03 proud of the line

    # the rib: flyer()'s arch shortened to the middle of the span, hung under the coping
    path = [(s, -depth(s)) for s in (s0 + (s1 - s0) * i / 16 for i in range(17))]
    place = lambda h, y, v: tuple(h * D + y * N + Vector((0.0, v, 0.0)))  # noqa: E731
    p.append(sweep("rib", RIB_SEC, path, GOLD, place, smooth=50.0))
    p.append(sweep("rib_roll", roll(0.035, 8, 0.1, 0.0), path, "brass", place, smooth=70.0))
    for s in (1.1, 1.8, 2.5):                                    # tracery struts coping -> rib
        dd = depth(s)
        st = kit.box("strut", (0.09, 0.12, dd - 0.4), mat="lead", bevel=0.015)
        p.append(_put(st, _on_slope(s, -(0.4 + dd) / 2), SLOPE_ROT))

    # shifted bevelled pieces at the ragged low end
    for s, dz, y, size in ((0.25, -0.2, 0.35, (0.55, 0.5, 0.3)), (-0.2, -0.05, -0.4, (0.45, 0.5, 0.28))):
        p.append(_put(kit.box("shifted", size, mat=RED, bevel=0.03), _on_slope(s, dz, y), SLOPE_ROT))

    # broken glass chunks around the foot
    for k in range(6):
        size = (rng.uniform(0.14, 0.26), rng.uniform(0.1, 0.2), rng.uniform(0.05, 0.09))
        ch = kit.box("chunk", size, mat=RED if k % 2 else GOLD, bevel=0.01)
        for v in ch.data.vertices:
            v.co += Vector((rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), rng.uniform(-0.01, 0.01)))
        p.append(_put(ch, (rng.uniform(-0.5, 0.5), rng.uniform(-0.7, 0.7), size[2] / 2),
                      (0.0, 0.0, rng.uniform(0.0, math.pi))))
    return _done("fallen_flyer", p)


# ---------------------------------------------------------------- pinnacle_niche

BASE = [(0.0, 0.0), (0.07, 0.0), (0.07, 0.04), (0.05, 0.07), (0.04, 0.09), (0.0, 0.09)]
SHAFT = [(0.0, 0.0), (0.035, 0.0), (0.03, 0.05), (0.03, 1.38), (0.04, 1.44), (0.04, 1.5), (0.0, 1.5)]
CAPITAL = [(0.0, 0.0), (0.06, 0.0), (0.07, 0.03), (0.05, 0.06), (0.0, 0.08)]
SPIRE = [(0.3, 1.66), (0.3, 1.7), (0.22, 1.75), (0.14, 2.4), (0.07, 2.9), (0.07, 3.0)]
CROCKET = [(0.0, 0.0), (0.03, 0.0), (0.0, 0.06)]
ARCH_SEC = [(-0.07, -0.05), (0.0, -0.05), (0.04, -0.02), (0.04, 0.02), (0.0, 0.05), (-0.07, 0.05)]
ZS = 1.48                                                    # arch springing, on the colonnette capitals


def _face(axis, c):
    """Canopy face placement: (h, y, v) -> world, with y absolute z; the face is at x = c or y = c."""
    if axis == "x":
        return lambda h, y, v: (c + v, h, y)
    return lambda h, y, v: (h, c + v, y)


def pinnacle_niche():
    rng = random.Random(5)
    p = []
    # platform: quarry field with a lead moulded edge round the top
    p.append(kit.box("field", (1.6, 2.4, 0.4), loc=(0, 0, -0.2), mat=QUARRY, bevel=0.02))
    rim = [(-0.8, -1.2, 0.0), (0.8, -1.2, 0.0), (0.8, 1.2, 0.0), (-0.8, 1.2, 0.0)]
    p.append(kit.sweep_closed("edge", [(-0.03, -0.1), (0.03, -0.1), (0.03, -0.02), (0.0, 0.0),
                                       (-0.03, 0.0), (-0.03, -0.1)], rim, mat="lead"))

    # buttress stump: 1.4 square at the foot, a lead set-back halfway down, 1.2 square above it
    for i, (w, z0, z1) in enumerate(((1.4, -18.3, -9.8), (1.2, -9.2, -0.4))):
        p.append(kit.box("stump%d" % i, (w, w, z1 - z0), loc=(0, 0, (z0 + z1) / 2), mat=RED, bevel=0.04))
        for sx in (-1, 1):
            for sy in (-1, 1):
                p.append(kit.box("quoin", (0.06, 0.06, z1 - z0), loc=(sx * w / 2, sy * w / 2, (z0 + z1) / 2), mat="lead"))
    p.append(_frustum("weather", 1.52, 1.22, -9.8, -9.2, "lead"))

    # tabernacle: four colonnettes at the corners of 1.0 x 1.4, 1.6 m tall, with a lead roof
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = 0.5 * sx, 0.7 * sy
            p.append(_put(kit.lathe("base", BASE, 12, mat="brass"), (x, y, 0.0)))
            p.append(_put(kit.lathe("shaft", SHAFT, 12, mat=GOLD), (x, y, 0.09)))
            p.append(_put(kit.lathe("capital", CAPITAL, 12, mat="brass"), (x, y, 1.52)))
    p.append(kit.box("roof", (0.9, 1.3, 0.06), loc=(0, 0, 1.63), mat="lead", bevel=0.01))

    # pointed arches on all four sides, each with a gablet and brass crockets
    for axis, c, span, rise in (("x", 0.5, 1.4, 0.85), ("x", -0.5, 1.4, 0.85),
                                ("y", 0.7, 1.0, 0.7), ("y", -0.7, 1.0, 0.7)):
        path = [(h, ZS + y) for h, y in pointed(span, rise, 16)]
        place = _face(axis, c)
        p.append(sweep("arch", ARCH_SEC, path, "lead", place))
        p.append(sweep("arch_roll", roll(0.025, 8, 0.04, 0.0), path, "brass", place, smooth=70.0))
        zc = ZS + rise - 0.04
        gab = [(-0.22, zc), (0.0, zc + 0.34), (0.22, zc)]
        p.append(sweep("gablet", [(-0.02, -0.02), (0.02, -0.02), (0.02, 0.02), (-0.02, 0.02)], gab, "lead", place))
        for t in (0.35, 0.7):
            for sgn in (-1, 1):
                p.append(_put(kit.lathe("crocket", CROCKET, 6, mat="brass"),
                              place(sgn * 0.22 * (1 - t), zc + 0.34 * t, 0.0)))

    # spirelet: octagonal, snapped with a jagged top at about 3.0 m, with crockets
    spire = kit.lathe("spire", SPIRE, 8, mat=GOLD, smooth_angle=30.0)
    for v in spire.data.vertices:
        if v.co.z > 2.9:
            v.co.z -= rng.uniform(0.0, 0.14)
            v.co.x += rng.uniform(-0.02, 0.02)
            v.co.y += rng.uniform(-0.02, 0.02)
    p.append(spire)
    for z, r in ((2.1, 0.177), (2.5, 0.126)):
        for k in range(8):
            a = k * math.pi / 4
            p.append(_put(kit.lathe("crocket", CROCKET, 6, mat="brass"),
                          (math.cos(a) * (r + 0.01), math.sin(a) * (r + 0.01), z)))
    return _done("pinnacle_niche", p)


# ---------------------------------------------------------------- ledger

STRIP = [(-0.004, -0.004), (0.004, -0.004), (0.004, 0.004), (-0.004, 0.004), (-0.004, -0.004)]


def ledger():
    p = [kit.box("field", (1.88, 0.88, 0.05), loc=(0, 0, -0.005), mat=RED)]
    # lead border 0.06 wide, its top flush with the field (z 0.02)
    for y in (-0.47, 0.47):
        p.append(kit.box("lead_edge", (2.0, 0.06, 0.05), loc=(0, y, -0.005), mat="lead", bevel=0.01))
    for x in (-0.97, 0.97):
        p.append(kit.box("lead_side", (0.06, 0.88, 0.05), loc=(x, 0, -0.005), mat="lead", bevel=0.01))
    # brass border line 0.1 inside the edge
    rect = [(-0.9, -0.4, 0.02), (0.9, -0.4, 0.02), (0.9, 0.4, 0.02), (-0.9, 0.4, 0.02)]
    p.append(kit.sweep_closed("border", STRIP, rect, mat="brass"))
    # pointed canopy over the head: springers at x -0.56, apex at x -0.80
    canopy = [(-0.56 - y, h, 0.02) for h, y in pointed(0.4, 0.24, 16)]
    p.append(kit.tube("canopy", canopy, 0.004, 6, mat="brass"))
    # head: a circle of brass, centre (-0.62, 0), radius 0.09
    head = [(-0.62 + 0.09 * math.cos(2 * math.pi * i / 16), 0.09 * math.sin(2 * math.pi * i / 16), 0.02)
            for i in range(17)]
    p.append(kit.tube("head", head, 0.004, 6, mat="brass"))
    # body: shoulders to feet, a robe tapering to the feet at x 0.8
    stations = [(-0.52, 0.08), (-0.46, 0.18), (-0.36, 0.19), (-0.2, 0.18), (0.0, 0.16), (0.2, 0.15),
                (0.4, 0.12), (0.6, 0.09), (0.74, 0.07), (0.8, 0.04)]
    outline = [(x, w, 0.02) for x, w in stations] + [(x, -w, 0.02) for x, w in reversed(stations)]
    outline.append(outline[0])
    p.append(kit.tube("body", outline, 0.004, 6, mat="brass"))
    # hands joined in prayer at the chest
    hands = [(-0.28 + 0.05 * math.cos(2 * math.pi * i / 10), 0.035 * math.sin(2 * math.pi * i / 10), 0.02)
             for i in range(11)]
    p.append(kit.tube("hands", hands, 0.004, 6, mat="brass"))
    return _done("ledger", p)


def build(args):
    {"fallen_flyer": fallen_flyer, "pinnacle_niche": pinnacle_niche, "ledger": ledger}[args[0]]()
