"""The Widow's lantern: a leaded cage around an ember. Centred at origin, ~0.6 m tall."""
import math

import kit


def build(args):
    p = [kit.lathe("cap", [(0.17, 0.2), (0.14, 0.25), (0.04, 0.3), (0.0, 0.3)], 24, mat="lead")]
    p.append(kit.lathe("base", [(0.0, -0.24), (0.18, -0.24), (0.17, -0.2), (0.0, -0.2)], 24, mat="lead"))
    p.append(kit.torus("hoop", 0.07, 0.012, mat="brass", loc=(0, 0, 0.33), rot=(math.pi / 2, 0, 0)))
    for i in range(6):
        a = i * math.pi / 3
        p.append(kit.tube("bar%d" % i, [(math.cos(a) * 0.16, math.sin(a) * 0.16, -0.2), (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.2)], 0.012, 6, mat="lead"))
    p.append(kit.lathe("pane", [(0.0, -0.2), (0.15, -0.2), (0.14, 0.2), (0.0, 0.2)], 6, mat="glass_gold", smooth_angle=None))
    p.append(kit.lathe("ember", [(0.0, -0.12), (0.06, -0.08), (0.05, 0.05), (0.0, 0.12)], 12, mat="ember"))
    kit.join("lantern", p)
