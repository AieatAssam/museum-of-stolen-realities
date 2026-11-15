"""Brass rope stanchion (post) and a 2 m velvet rope span between x = -1 and x = +1."""
import math
import kit


def build(args):
    kit.lathe("post", [(0.17, 0.0), (0.17, 0.03), (0.12, 0.06), (0.04, 0.09), (0.025, 0.12), (0.025, 0.86), (0.04, 0.9), (0.05, 0.93), (0.045, 0.97), (0.0, 1.0)], 24, mat="brass")
    kit.box("post-convcolonly", (0.34, 0.34, 1.0), (0, 0, 0.5))
    pts = []
    for i in range(25):
        t = i / 24
        x = -1 + 2 * t
        z = 0.88 - 0.22 * (1 - (2 * t - 1) ** 2)
        pts.append((x, 0, z))
    kit.tube("rope", pts, 0.025, 10, mat="velvet")
