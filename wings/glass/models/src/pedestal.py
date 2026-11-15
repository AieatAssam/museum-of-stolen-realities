"""The museum's own pedestal, glazed into every edited window and here made real. 0.8 m square, top at 1.05."""
import kit


def build(args):
    p = [kit.box("foot", (0.86, 0.86, 0.1), (0, 0, 0.05), mat="museum_white", bevel=0.015)]
    p.append(kit.box("body", (0.74, 0.74, 0.85), (0, 0, 0.525), mat="museum_white", bevel=0.01))
    p.append(kit.box("band", (0.78, 0.78, 0.03), (0, 0, 0.94), mat="brass", bevel=0.006))
    p.append(kit.box("top", (0.84, 0.84, 0.09), (0, 0, 1.005), mat="museum_white", bevel=0.015))
    kit.join("pedestal", p)
