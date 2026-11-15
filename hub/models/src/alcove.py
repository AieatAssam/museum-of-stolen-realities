"""Private Collection surround: a gilt-and-ebony proscenium for the 12.2 m alcove mouth (fluted
pilasters with acanthus capitals, a full entablature with dentils, a crowning cartouche) and a
coffered ebony ceiling over the recess. Origin at the floor centre of the mouth; the hall is -Y
(Godot +Z), the recess runs to +Y 8.5 m. Ceiling underside at 6.15 m."""
import math
import os
import sys

from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

HALF = 6.45  # pilaster centre-line
DEPTH = 8.5


def build(args):
    p = []
    for s in (-1, 1):
        x = s * HALF
        p.append(kit.box("plinth%d" % s, (1.1, 0.9, 0.5), (x, -0.25, 0.25), mat="marble_black", bevel=0.02))
        p.append(kit.box("pbase%d" % s, (1.0, 0.8, 0.12), (x, -0.25, 0.56), mat="gilt", bevel=0.03, segments=3))
        p.append(kit.box("shaft%d" % s, (0.86, 0.66, 5.0), (x, -0.25, 3.12), mat="marble_ivory", bevel=0.015))
        for k in range(5):  # sunk flutes, gilt-lined
            fx = x - 0.3 + 0.15 * k
            p.append(kit.box("flute%d_%d" % (s, k), (0.07, 0.04, 4.4), (fx, -0.585, 3.12), mat="gilt", bevel=0.02, segments=3))
        # acanthus capital
        p.append(kit.box("necking%d" % s, (0.92, 0.72, 0.1), (x, -0.25, 5.67), mat="gilt", bevel=0.02, segments=2))
        for k in range(3):
            lx = x - 0.28 + 0.28 * k
            p.append(orn.leaf("cap%d_%d" % (s, k), (lx, -0.62, 5.7), (0, -0.25, 1), 0.42, 0.13, curl=1.0))
        for v in (-1, 1):
            m = Matrix.Translation((x + v * 0.4, -0.64, 5.95)) @ (Matrix.Scale(-1, 4, (1, 0, 0)) if v < 0 else Matrix.Identity(4))
            p.append(orn.scroll("vol%d_%d" % (s, v), m, 0.14, 0.02, 1.3, 0.05, 0.02))
        p.append(kit.box("abacus%d" % s, (1.04, 0.84, 0.1), (x, -0.25, 6.1), mat="gilt", bevel=0.02, segments=2))
        kit.collision_box("pilaster%d" % s, (1.1, 0.9, 6.15), (x, -0.25, 3.07))

    W = 2 * HALF + 1.2
    # entablature: two-fascia architrave, ebony frieze with gilt rosettes, dentil course, cornice
    p.append(kit.box("arch1", (W, 0.86, 0.22), (0, -0.25, 6.26), mat="marble_ivory", bevel=0.01))
    p.append(kit.box("arch2", (W + 0.06, 0.92, 0.2), (0, -0.25, 6.47), mat="marble_ivory", bevel=0.01))
    p.append(kit.box("archbead", (W + 0.1, 0.96, 0.05), (0, -0.25, 6.595), mat="gilt", bevel=0.02, segments=3))
    p.append(kit.box("frieze", (W, 0.84, 0.62), (0, -0.25, 6.93), mat="ebony", bevel=0.01))
    n = 9
    for i in range(n):
        rx = -W / 2 + 0.9 + (W - 1.8) * i / (n - 1)
        r = kit.lathe("fr%d" % i, [(0.0, 0.0), (0.2, 0.0), (0.19, 0.05), (0.12, 0.08), (0.14, 0.11), (0.07, 0.15), (0.0, 0.17)], 16, mat="gilt")
        kit.place(r, (rx, -0.66, 6.93), (math.radians(90), 0, 0))
        p.append(r)
    p.append(kit.box("bed", (W + 0.2, 1.0, 0.08), (0, -0.25, 7.28), mat="gilt", bevel=0.02, segments=2))
    for i in range(int((W + 0.1) / 0.22)):
        dx = -(W + 0.1) / 2 + 0.11 + 0.22 * i
        p.append(kit.box("dent%d" % i, (0.12, 0.14, 0.16), (dx, -0.79, 7.4), mat="marble_ivory", bevel=0.008, segments=1))
    p.append(kit.box("corona", (W + 0.5, 1.3, 0.24), (0, -0.4, 7.6), mat="marble_ivory", bevel=0.02))
    p.append(kit.box("cyma", (W + 0.6, 1.4, 0.1), (0, -0.42, 7.77), mat="gilt", bevel=0.04, segments=3))

    # crowning cartouche: a shield between C-scrolls with a shell, fanned acanthus and a flame
    cz = 8.9
    sh = kit.lathe("shield", [(0.0, 0.0), (0.9, 0.0), (0.88, 0.1), (0.72, 0.15), (0.68, 0.22), (0.44, 0.28), (0.0, 0.32)], 32, mat="gilt")
    kit.place(sh, (0, -0.5, cz), (math.radians(90), 0, 0), (0.85, 1.3, 1.0))
    p.append(sh)
    p.append(kit.box("shieldfield", (0.9, 0.05, 1.3), (0, -0.82, cz), mat="ebony", bevel=0.2, segments=4))
    for s in (-1, 1):
        flip = Matrix.Scale(-1, 4, (1, 0, 0)) if s < 0 else Matrix.Identity(4)
        m = Matrix.Translation((s * 1.45, -0.55, cz - 0.3)) @ flip @ Matrix.Rotation(math.radians(200), 4, "Y")
        p.append(orn.scroll("cs%d" % s, m, 0.8, 0.1, 1.2, 0.2, 0.05))
        for k in range(4):
            a = math.radians(10 + 20 * k)
            d = (s * math.cos(a), 0, math.sin(a))
            p.append(orn.leaf("fan%d_%d" % (s, k), (s * 0.7, -0.7, 8.0), d, 1.6 - 0.15 * k, 0.32, curl=0.85))
        for k in range(3):
            p.append(orn.leaf("swag%d_%d" % (s, k), (s * (2.6 + k * 1.4), -0.75, 7.9), (s, 0, 0.15 - 0.2 * k), 1.2, 0.26, curl=0.6))
    p.extend(orn.shell("crest", (0, -0.6, cz + 1.05), 0.95, 11, depth=0.35))
    fl = kit.lathe("flame", [(0.0, 0.0), (0.24, 0.0), (0.3, 0.16), (0.17, 0.38), (0.22, 0.55), (0.1, 0.82), (0.05, 1.08), (0.0, 1.25)], 16, mat="gilt")
    kit.place(fl, (0, -0.45, cz + 1.9))
    p.append(fl)
    kit.join("surround", p)

    # coffered ceiling: ebony beams on a grid, damask-lined coffers with gilt bosses
    c = [kit.box("lid", (2 * HALF - 0.6, DEPTH, 0.2), (0, DEPTH / 2, 6.55), mat="ebony")]
    nx, ny = 5, 4
    cw, cd = (2 * HALF - 0.6) / nx, DEPTH / ny
    for i in range(nx + 1):
        bx = -(HALF - 0.3) + cw * i
        c.append(kit.box("bx%d" % i, (0.24, DEPTH, 0.3), (bx, DEPTH / 2, 6.3), mat="ebony", bevel=0.03, segments=2))
    for j in range(ny + 1):
        by = cd * j
        c.append(kit.box("by%d" % j, (2 * HALF - 0.6, 0.24, 0.3), (0, by, 6.3), mat="ebony", bevel=0.03, segments=2))
    for i in range(nx):
        for j in range(ny):
            cx, cy = -(HALF - 0.3) + cw * (i + 0.5), cd * (j + 0.5)
            c.append(kit.box("cof%d_%d" % (i, j), (cw - 0.5, cd - 0.5, 0.04), (cx, cy, 6.44), mat="damask"))
            fr = kit.sweep_closed("cf%d_%d" % (i, j), [(0.0, 0.0), (0.04, 0.0), (0.04, 0.03), (0.0, 0.05)],
                                  [(cx - cw / 2 + 0.25, cy - cd / 2 + 0.25, 6.42), (cx - cw / 2 + 0.25, cy + cd / 2 - 0.25, 6.42),
                                   (cx + cw / 2 - 0.25, cy + cd / 2 - 0.25, 6.42), (cx + cw / 2 - 0.25, cy - cd / 2 + 0.25, 6.42)], mat="gilt")
            c.append(orn.face_toward(fr, (0, 0, -1)))
            b = kit.lathe("boss%d_%d" % (i, j), [(0.0, 0.0), (0.13, 0.0), (0.12, 0.04), (0.07, 0.07), (0.0, 0.09)], 12, mat="gilt")
            kit.place(b, (cx, cy, 6.42), (math.radians(180), 0, 0))
            c.append(b)
    kit.join("ceiling", c)
