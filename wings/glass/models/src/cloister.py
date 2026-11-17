"""Dressing for the cloister walks (glass.gd _build_cloister): the outer glazed walls and the flat walk roof
were bare boxes. Visual only, laid by MultiMesh; the boxes and their colliders stay.

Pass one part name (each exports its own glb, cloister_<part>.glb):
  bay   - one 3 m bay of outer wall, origin on the wall face at floor level, centred on a bay division
          (the glazed_wall shader puts lancet centres on multiples of 3 m, so divisions fall at 1.5 + 3k).
          Front (into the walk) is -Y. An engaged shaft with base and capital between two lancets, and the
          bay's run of moulded plinth and wall-head cornice (the walk roof's underside is at 7.2 m).
  rib   - a transverse rib across the 6.5 m walk, from the arcade pier's top (5.2 m, y -6.5) up under the
          roof and down onto the wall shaft's capital; same frame as `bay`.
  kerb  - 1 m of moulded edge over the walk slab's garth face (slab top at 0, face at y 0, garth -Y):
          a roll under a fillet and a chamfered fascia, flush with the walk top so nobody trips on it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import RIB, roll, sweep  # noqa: E402

BAY = 3.0
CAP = 6.45  # wall shaft capital top
WALK = 6.5


def run(name, z, sec, mat):
    """A moulding along the wall face (x -1.5..1.5) at height z; sec [(out, up)]."""
    return sweep(name, sec, [(-BAY / 2, 0.0), (BAY / 2, 0.0)], mat, place=lambda h, y, v: (h, y, z + v), smooth=40.0)


def bay():
    p = []
    # plinth: a chamfered base course with a roll on top
    p.append(run("plinth", 0.0, [(0.0, 0.0), (0.16, 0.0), (0.16, 0.32), (0.08, 0.42), (0.0, 0.42)], "lead"))
    p.append(run("plinth_roll", 0.44, [(u, v) for u, v in roll(0.045, 8, 0.04, 0.0)], "brass"))
    # wall-head cornice tucked under the roof (kept thin: the lancets' pointed heads rise to the roof line)
    p.append(run("cornice", 7.0, [(0.0, 0.0), (0.05, 0.0), (0.1, 0.08), (0.16, 0.14), (0.16, 0.2), (0.0, 0.2)], "lead"))
    p.append(run("cornice_roll", 7.02, [(u, v) for u, v in roll(0.03, 8, 0.08, 0.0)], "brass"))
    # engaged shaft between two lancets (they leave 0.56 m of wall), on its own base, under a moulded capital
    r = 0.1
    base = kit.lathe("base", [(0.0, 0.0), (0.2, 0.0), (0.2, 0.5), (0.16, 0.56), (0.13, 0.62), (r, 0.7), (0.0, 0.7)],
                     16, mat="lead")
    base.location = (0, -0.12, 0)
    p.append(base)
    shaft = kit.lathe("shaft", [(0.0, 0.7), (r, 0.7), (r, CAP - 0.42), (0.0, CAP - 0.42)], 16, mat="brass")
    shaft.location = (0, -0.12, 0)
    p.append(shaft)
    cap = kit.lathe("capital", [(0.0, CAP - 0.42), (r + 0.02, CAP - 0.42), (r + 0.02, CAP - 0.36), (r, CAP - 0.32),
                                (0.16, CAP - 0.12), (0.2, CAP - 0.08), (0.2, CAP), (0.0, CAP)], 16, mat="lead")
    cap.location = (0, -0.12, 0)
    p.append(cap)
    for s in (-1, 1):  # bands of brass on the shaft
        b = kit.torus("band", r + 0.012, 0.016, 16, 6, mat="brass")
        b.location = (0, -0.12, 2.4 if s < 0 else 4.4)
        p.append(b)
    kit.join("cloister_bay", p)


def bez(p0, p1, p2, p3, n=28):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def rib():
    # (h, y) = (distance out from the wall, height), wall -> pier so the intrados (keel) is below
    path = bez((0.12, CAP), (1.6, 7.12), (5.5, 6.95), (WALK, 5.2))
    sec = [(u * 0.55, v * 0.55) for u, v in RIB]
    r = sweep("rib", sec, path, "brass", place=lambda h, y, v: (v, -h, y), smooth=50.0)
    # a carved boss where the rib meets the roof line, and a lead springer block on the wall
    boss = kit.lathe("boss", [(0.0, -0.12), (0.12, -0.08), (0.15, 0.0), (0.1, 0.07), (0.0, 0.09)], 14, mat="lead")
    top = max(path, key=lambda q: q[1])
    boss.location = (0, -top[0], top[1] - 0.12)
    kit.join("cloister_rib", [r, boss])


def kerb():
    sec = [(0.0, 0.0), (0.06, 0.0), (0.06, -0.08)] + \
          [(0.05 + 0.06 * math.sin(a), -0.16 + 0.06 * math.cos(a)) for a in (math.pi * k / 8 for k in range(9))] + \
          [(0.04, -0.24), (0.04, -0.7), (0.1, -0.86), (0.0, -0.98)]
    # path along X; section u points out over the garth (-Y), v is up
    k = sweep("kerb", sec, [(-0.5, 0.0), (0.5, 0.0)], "lead", place=lambda h, y, v: (h, y - 0.001, v),
              smooth=40.0)
    # under the slab: a brass bead, then a corbel table hanging over the garth (one ogee corbel per metre)
    bead = sweep("bead", [(u, v) for u, v in roll(0.035, 8, 0.03, -1.02)], [(-0.5, 0.0), (0.5, 0.0)], "brass",
                 place=lambda h, y, v: (h, y - 0.001, v), smooth=60.0)
    ogee = [(0.0, -1.05), (0.15, -1.05), (0.15, -1.12)] + \
           [(0.15 - 0.07 * (1 - math.cos(a)), -1.12 - 0.12 * math.sin(a)) for a in (math.pi / 2 * j / 6 for j in range(1, 7))] + \
           [(0.08 - 0.08 * math.sin(a), -1.24 - 0.24 * (1 - math.cos(a))) for a in (math.pi / 2 * j / 6 for j in range(1, 7))] + \
           [(0.0, -1.48)]
    cor = sweep("corbel", ogee, [(-0.13, 0.0), (0.13, 0.0)], "lead", place=lambda h, y, v: (h, y - 0.001, v),
                smooth=40.0)
    kit.join("cloister_kerb", [k, bead, cor])


NBAY = 5.5  # glazed_nave: lancets 4.4 wide on 5.5 m bays, tiers 0.5..12.5 and 14.2..25.2


def nave():
    """One 5.5 m bay of nave wall, origin on the wall face at walk level (0), centred on a division between
    two lancets; front -Y. An engaged shaft the full height on a corbelled base, a moulded string course
    under the lower tier and a deep course with a corbel table filling the band between the tiers."""
    def course(name, z, sec, mat):
        return sweep(name, sec, [(-NBAY / 2, 0.0), (NBAY / 2, 0.0)], mat, place=lambda h, y, v: (h, y, z + v), smooth=40.0)
    p = []
    p.append(course("sill", 0.0, [(0.0, -0.3), (0.06, -0.3), (0.18, -0.12), (0.18, 0.3), (0.1, 0.42), (0.0, 0.42)], "lead"))
    p.append(course("sill_roll", 0.44, [(u, v) for u, v in roll(0.04, 8, 0.04, 0.0)], "brass"))
    p.append(course("band", 12.55, [(0.0, 0.0), (0.12, 0.0), (0.22, 0.12), (0.22, 0.3), (0.14, 0.38), (0.14, 1.2),
                                    (0.26, 1.35), (0.26, 1.55), (0.0, 1.62)], "lead"))
    p.append(course("band_roll", 12.92, [(u, v) for u, v in roll(0.05, 8, 0.16, 0.0)], "brass"))
    p.append(course("cornice", 25.2, [(0.0, 0.0), (0.1, 0.0), (0.2, 0.1), (0.2, 0.3), (0.0, 0.3)], "lead"))
    for x in (-2.25, -0.75, 0.75, 2.25):  # corbel table under the band's upper lip
        c = kit.lathe("corbel", [(0.0, 13.5), (0.1, 13.5), (0.12, 13.62), (0.16, 13.75), (0.0, 13.75)], 10, mat="lead")
        c.location = (x, -0.14, 0)
        p.append(c)
    r = 0.15
    for z0, z1 in ((0.45, 12.55), (14.17, 25.2)):
        base = kit.lathe("base", [(0.0, z0), (0.26, z0), (0.26, z0 + 0.3), (0.2, z0 + 0.38), (r, z0 + 0.5), (0.0, z0 + 0.5)], 16, mat="lead")
        shaft = kit.lathe("shaft", [(0.0, z0 + 0.5), (r, z0 + 0.5), (r, z1 - 0.45), (0.0, z1 - 0.45)], 16, mat="brass")
        cap = kit.lathe("capital", [(0.0, z1 - 0.45), (r + 0.03, z1 - 0.45), (r + 0.03, z1 - 0.38), (0.2, z1 - 0.15),
                                    (0.26, z1 - 0.1), (0.26, z1), (0.0, z1)], 16, mat="lead")
        for o in (base, shaft, cap):
            o.location = (0, -0.17, 0)
            p.append(o)
        for t in (0.33, 0.66):
            b = kit.torus("band", r + 0.014, 0.02, 16, 6, mat="brass")
            b.location = (0, -0.17, z0 + (z1 - z0) * t)
            p.append(b)
    kit.join("cloister_nave", p)


def build(args):
    {"bay": bay, "rib": rib, "kerb": kerb, "nave": nave}[args[0] if args else "bay"]()
