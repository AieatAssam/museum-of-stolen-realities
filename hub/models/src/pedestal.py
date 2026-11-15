"""Museum pedestal (THE THIEF, ACQUIRED). 1.2 x 1.2 footprint, top at 1.15 m."""
import kit


def build(args):
    p = []
    p.append(kit.box("foot", (1.3, 1.3, 0.14), (0, 0, 0.07), mat="marble_black", bevel=0.02))
    p.append(kit.box("band", (1.22, 1.22, 0.05), (0, 0, 0.165), mat="gilt", bevel=0.01))
    p.append(kit.box("body", (1.08, 1.08, 0.82), (0, 0, 0.6), mat="marble_black", bevel=0.015))
    p.append(kit.box("band2", (1.16, 1.16, 0.05), (0, 0, 1.03), mat="gilt", bevel=0.01))
    p.append(kit.box("top", (1.24, 1.24, 0.1), (0, 0, 1.1), mat="marble_ivory", bevel=0.02))
    kit.join("pedestal", p)
    kit.box("pedestal-convcolonly", (1.3, 1.3, 1.15), (0, 0, 0.575))
