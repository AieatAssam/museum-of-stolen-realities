"""Clustered nave pier, in three stackable parts (MultiMesh-instanced in Godot). Arg = part:
  base     moulded plinth, 0..0.62 m
  shaft    1 m of clustered shafts (core + 4 major + 4 minor + lead cames), scaled in Y per instance
  capital  bell capital with eight curled stiff-leaf crockets and an octagonal abacus, 0..0.72 m
Everything stays inside a 1.2 m square (the pier's box collider)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

OCT = math.pi / 8


def octagon(name, r, z0, z1, mat):
    """Octagonal prism, flats facing the axes so the corners stay inside a 2r square."""
    ob = kit.lathe(name, [(0.0, z0), (r, z0), (r, z1), (0.0, z1)], 8, mat=mat, smooth_angle=30.0)
    ob.rotation_euler = (0, 0, OCT)
    return ob


def base():
    p = [octagon("plinth", 0.6, 0.0, 0.26, "lead")]
    # attic base: torus, scotia, torus, then a brass ring where the glass begins
    p.append(kit.lathe("mould", [(0.0, 0.26), (0.54, 0.26), (0.56, 0.29), (0.555, 0.33), (0.52, 0.355),
                                 (0.47, 0.37), (0.455, 0.40), (0.47, 0.43), (0.49, 0.455),
                                 (0.485, 0.49), (0.45, 0.51), (0.42, 0.52), (0.0, 0.52)], 40, mat="lead"))
    p.append(kit.torus("band", 0.43, 0.035, 40, 10, mat="brass", loc=(0, 0, 0.56)))
    p.append(kit.lathe("seat", [(0.0, 0.52), (0.40, 0.52), (0.39, 0.62), (0.0, 0.62)], 24, mat="lead"))
    kit.join("pier_base", p)


def shaft():
    p = [octagon("core", 0.37, 0.0, 1.0, "glass_gold_m")]
    for k in range(4):
        a = k * math.pi / 2
        p.append(kit.lathe("major%d" % k, [(0.15, 0.0), (0.15, 1.0)], 16, mat="glass_gold_m", cap=False))
        p[-1].location = (math.cos(a) * 0.41, math.sin(a) * 0.41, 0)
        p.append(kit.box("came%d" % k, (0.035, 0.035, 1.0), (0, 0, 0.5), mat="lead"))
        p[-1].location = (math.cos(a) * 0.565, math.sin(a) * 0.565, 0)
        b = a + math.pi / 4
        p.append(kit.lathe("minor%d" % k, [(0.07, 0.0), (0.07, 1.0)], 10, mat="glass_gold_m", cap=False))
        p[-1].location = (math.cos(b) * 0.44, math.sin(b) * 0.44, 0)
    kit.join("pier_shaft", p)


def capital():
    p = [kit.torus("astragal", 0.45, 0.04, 40, 10, mat="brass", loc=(0, 0, 0.05))]
    p.append(kit.lathe("bell", [(0.0, 0.0), (0.44, 0.0), (0.42, 0.12), (0.43, 0.26), (0.48, 0.38),
                                (0.55, 0.46), (0.57, 0.5), (0.0, 0.5)], 40, mat="lead"))
    p.append(octagon("abacus", 0.6, 0.5, 0.6, "brass"))
    lip = kit.lathe("abacus_lip", [(0.0, 0.6), (0.55, 0.6), (0.52, 0.66), (0.44, 0.72), (0.0, 0.72)], 8, mat="lead", smooth_angle=30.0)
    lip.rotation_euler = (0, 0, OCT)
    p.append(lip)
    # eight stiff-leaf crockets curling out under the abacus: the carved bit the eye rests on
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for i in range(9):
            t = i / 8
            r = 0.43 + 0.09 * t * t + 0.04 * math.sin(t * math.pi)
            z = 0.1 + 0.34 * t - 0.4 * max(0.0, t - 0.75)
            pts.append((ca * r, sa * r, z))
        p.append(kit.tube("leaf%d" % k, pts, 0.028, 8, mat="brass"))
        bud = kit.lathe("bud%d" % k, [(0.0, -0.05), (0.04, -0.03), (0.045, 0.0), (0.03, 0.03), (0.0, 0.04)], 10, mat="brass")
        bud.location = pts[-1]
        p.append(bud)
    kit.join("pier_capital", p)


def build(args):
    {"base": base, "shaft": shaft, "capital": capital}[args[0]]()
