"""A hinged, hieratic glass icon: kneeling robed saint with a flat halo. Centred at origin, 1.1 m tall."""
import math

import kit


def build(args):
    m = "glass_gold"
    p = [kit.lathe("robe", [(0.0, -0.55), (0.26, -0.55), (0.25, -0.35), (0.18, -0.05), (0.13, 0.15), (0.0, 0.17)], 8, mat=m, smooth_angle=None)]
    p.append(kit.lathe("head", [(0.0, 0.15), (0.07, 0.18), (0.085, 0.27), (0.06, 0.35), (0.0, 0.37)], 8, mat=m, smooth_angle=None))
    halo = kit.lathe("halo", [(0.0, -0.01), (0.17, -0.01), (0.17, 0.01), (0.0, 0.01)], 16, mat=m, smooth_angle=None)
    kit.place(halo, loc=(0, 0.06, 0.29), rot=(math.pi / 2, 0, 0))
    p.append(halo)
    # hands raised together: the hinge of the icon
    p.append(kit.box("hands", (0.08, 0.1, 0.22), (0, -0.16, 0.08), mat=m))
    kit.join("icon_kneel", p)
