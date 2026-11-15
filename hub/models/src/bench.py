"""Gallery bench: a button-tufted oxblood velvet cushion with gilt piping on a carved ebony
apron, standing on four cabriole legs with gilt knee leaves and scroll feet. 2.4 m long, seat at
0.48 m."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

L, D = 2.4, 0.62


def build(args):
    p = [kit.box("cushion", (L, D, 0.14), (0, 0, 0.42), mat="velvet", bevel=0.06, segments=4)]
    for i in range(7):  # tufting buttons in a diamond grid
        for j in range(2 if i % 2 else 3):
            x = -L / 2 + 0.22 + (L - 0.44) * i / 6
            y = (-0.16 + 0.16 * j) if i % 2 == 0 else (-0.08 + 0.16 * j)
            p.append(orn.ellipsoid("btn%d_%d" % (i, j), (x, y, 0.488), (0.035, 0.035, 0.018), "velvet", 8, 4))
    pip = [(-L / 2 + 0.04, -D / 2 + 0.01, 0.36), (L / 2 - 0.04, -D / 2 + 0.01, 0.36), (L / 2 - 0.04, D / 2 - 0.01, 0.36), (-L / 2 + 0.04, D / 2 - 0.01, 0.36), (-L / 2 + 0.04, -D / 2 + 0.01, 0.36)]
    p.append(kit.tube("piping", pip, 0.012, 8, mat="gilt"))
    # apron with a gilt bead and a centre cartouche
    p.append(kit.box("apron", (L - 0.06, D - 0.06, 0.12), (0, 0, 0.29), mat="ebony", bevel=0.02, segments=2))
    p.append(kit.box("abead", (L - 0.02, D - 0.02, 0.025), (0, 0, 0.235), mat="gilt", bevel=0.01, segments=2))
    for s in (-1, 1):
        c = kit.lathe("cart%d" % s, [(0.0, 0.0), (0.09, 0.0), (0.08, 0.02), (0.05, 0.035), (0.0, 0.04)], 14, mat="gilt")
        kit.place(c, (0, s * (D / 2 - 0.03), 0.28), (s * 1.5708, 0, 0), (1.6, 1.0, 0.8))
        p.append(c)
    # cabriole legs: knee out, ankle in, scroll foot
    for x in (-1, 1):
        for y in (-1, 1):
            bx, by = x * (L / 2 - 0.12), y * (D / 2 - 0.1)
            ox, oy = x * 0.05, y * 0.05
            pts = [(bx, by, 0.24), (bx + ox, by + oy, 0.19), (bx + ox * 0.6, by + oy * 0.6, 0.12), (bx - ox * 0.2, by - oy * 0.2, 0.06), (bx + ox * 0.3, by + oy * 0.3, 0.015)]
            p.append(orn.taper("leg%d%d" % (x, y), pts, [0.045, 0.042, 0.03, 0.022, 0.03], 10, "ebony"))
            p.append(orn.leaf("knee%d%d" % (x, y), (bx + ox * 0.8, by + oy * 0.8, 0.235), (ox, oy, -1.0), 0.12, 0.05, curl=0.9, lift=(x, y, 0)))
            p.append(orn.ellipsoid("foot%d%d" % (x, y), (bx + ox * 0.4, by + oy * 0.4, 0.015), (0.07, 0.07, 0.03), "gilt", 10, 4))
    kit.join("bench", p)
    kit.box("bench-convcolonly", (L, D, 0.5), (0, 0, 0.25))
