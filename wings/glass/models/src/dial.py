"""Sun-dial plinth (the turning head is built in code). Origin at the head pivot; base sits 0.35 below."""
import math

import kit


def build(args):
    p = [kit.lathe("plinth", [(0.62, -0.35), (0.62, -0.3), (0.5, -0.24), (0.44, -0.05), (0.5, 0.08), (0.5, 0.15), (0.0, 0.15)], 40, mat="brass")]
    p.append(kit.torus("ring_a", 0.6, 0.025, mat="lead", loc=(0, 0, -0.27)))
    p.append(kit.torus("ring_b", 0.5, 0.02, mat="lead", loc=(0, 0, 0.12)))
    for i in range(12):
        a = i * math.pi / 6
        p.append(kit.box("hour%d" % i, (0.04, 0.12, 0.02), (math.cos(a) * 0.4, math.sin(a) * 0.4, 0.155), mat="lead"))
    kit.join("dial", p)
