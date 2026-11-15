"""Monumental baroque gilt frame. Opening 4.6 x 7.2 m, bottom of the opening at floor level (z=0)
so the player walks straight through. Faces -Y (toward the viewer).

Deep stepped moulding (1.3 m wide, 0.66 m proud) with a bead row on the sight edge, egg-and-dart
on the outer torus, acanthus corner clusters, side cartouches with leaf drops, and a crest:
cartouche between two C-scrolls, fanned acanthus, a scallop shell and a flame finial. A dark
ebony reveal lines the opening so the picture sits back like a window."""
import math
import os
import sys

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

W, H = 4.6, 7.2


def build(args):
    prof = [(0.0, -0.45), (0.0, 0.1), (0.03, 0.15), (0.07, 0.17), (0.1, 0.14), (0.13, 0.13), (0.16, 0.24),
            (0.22, 0.3), (0.3, 0.31), (0.34, 0.27), (0.38, 0.27), (0.42, 0.38), (0.5, 0.52), (0.6, 0.62),
            (0.7, 0.66), (0.8, 0.64), (0.88, 0.56), (0.92, 0.5), (0.95, 0.52), (0.99, 0.57), (1.03, 0.55),
            (1.07, 0.47), (1.12, 0.42), (1.18, 0.36), (1.24, 0.24), (1.28, 0.14), (1.3, 0.14), (1.3, -0.45)]
    path = [(-W / 2, 0, 0), (W / 2, 0, 0), (W / 2, 0, H), (-W / 2, 0, H)]
    parts = [orn.face_toward(kit.sweep_closed("frame", [(u, -v) for u, v in prof], path, mat="gilt", smooth_angle=50.0))]

    # bead row on the sight edge and egg-and-dart on the outer torus
    for i, (x, z, dx, dz) in enumerate(orn.along_rect(W, H, 0.17, 0.07)):
        parts.append(orn.ellipsoid("bead%d" % i, (x, -0.2, z), (0.075, 0.07, 0.075), seg=8, rings=4))
    for i, (x, z, dx, dz) in enumerate(orn.along_rect(W, H, 0.3, 0.99)):
        long_ = (0.13, 0.1, 0.2) if abs(dx) > 0.5 else (0.2, 0.1, 0.13)
        parts.append(orn.ellipsoid("egg%d" % i, (x, -0.6, z), long_, seg=8, rings=5))

    # corner clusters: rosette + five acanthus leaves splaying outward
    for s in (-1, 1):
        cx, cz = s * (W / 2 + 0.7), H + 0.7
        r = kit.lathe("ros%d" % s, [(0.0, 0.0), (0.4, 0.0), (0.38, 0.1), (0.26, 0.16), (0.3, 0.22), (0.16, 0.3), (0.1, 0.38), (0.0, 0.42)], 20, mat="gilt")
        kit.place(r, (cx, -0.62, cz), (math.radians(90), 0, 0))
        parts.append(r)
        for k in range(5):
            a = math.radians(-20 + 32 * k)
            d = (s * math.cos(a), 0, math.sin(a))
            parts.append(orn.leaf("cl%d_%d" % (s, k), (cx + d[0] * 0.25, -0.72, cz + d[2] * 0.25), d, 0.95, 0.3, curl=0.8))
        # side cartouche with a leaf drop
        sz = H * 0.6
        sx = s * (W / 2 + 0.68)
        c = kit.lathe("sc%d" % s, [(0.0, 0.0), (0.34, 0.0), (0.33, 0.06), (0.24, 0.1), (0.26, 0.15), (0.12, 0.2), (0.0, 0.22)], 18, mat="gilt")
        kit.place(c, (sx, -0.66, sz), (math.radians(90), 0, 0), (0.8, 1.25, 1.0))
        parts.append(c)
        parts.extend(orn.shell("ssh%d" % s, (sx, -0.7, sz + 0.35), 0.38, 7))
        for k in range(3):
            parts.append(orn.leaf("drop%d_%d" % (s, k), (sx, -0.72, sz - 0.3 - k * 0.55), (s * 0.15, 0, -1), 0.7, 0.16, curl=0.9))
        # foot: a gilt scroll bracket on a black marble block, so the sides land on the floor
        parts.append(kit.box("foot%d" % s, (1.6, 1.1, 0.55), (s * (W / 2 + 0.65), -0.05, 0.275), mat="marble_black", bevel=0.03))
        parts.append(kit.box("footcap%d" % s, (1.7, 1.2, 0.08), (s * (W / 2 + 0.65), -0.05, 0.58), mat="gilt", bevel=0.02))
        m = Matrix.Translation((s * (W / 2 + 0.68), -0.72, 1.15)) @ Matrix.Scale(-1 if s < 0 else 1, 4, (1, 0, 0))
        parts.append(orn.scroll("footscroll%d" % s, m, 0.42, 0.06, 1.15, 0.13, 0.04))

    # crest
    cz = H + 1.75
    shield = kit.lathe("shield", [(0.0, 0.0), (0.82, 0.0), (0.8, 0.1), (0.66, 0.14), (0.62, 0.2), (0.4, 0.26), (0.0, 0.3)], 32, mat="gilt")
    kit.place(shield, (0, -0.55, cz), (math.radians(90), 0, 0), (0.9, 1.25, 1.0))
    parts.append(shield)
    rim = kit.torus("shield_rim", 0.8, 0.07, 40, 8, mat="gilt", loc=(0, 0, 0), rot=(math.radians(90), 0, 0))
    kit.place(rim, (0, -0.62, cz), (0, 0, 0), (0.92, 1.0, 1.27))
    parts.append(rim)
    for s in (-1, 1):
        flip = Matrix.Scale(-1, 4, (1, 0, 0)) if s < 0 else Matrix.Identity(4)
        m = Matrix.Translation((s * 1.35, -0.62, cz - 0.15)) @ flip @ Matrix.Rotation(math.radians(200), 4, "Y")
        parts.append(orn.scroll("cs%d" % s, m, 0.75, 0.1, 1.2, 0.2, 0.05))
        m2 = Matrix.Translation((s * 2.1, -0.5, H + 0.75)) @ flip @ Matrix.Rotation(math.radians(30), 4, "Y")
        parts.append(orn.scroll("cs2_%d" % s, m2, 0.45, 0.06, 1.1, 0.14, 0.04))
        for k in range(4):
            a = math.radians(25 + 22 * k)
            d = (s * math.cos(a), 0, math.sin(a))
            parts.append(orn.leaf("cl_%d_%d" % (s, k), (s * 0.55, -0.75, cz + 0.4), d, 1.25 - 0.12 * k, 0.34, curl=0.9))
        parts.append(orn.leaf("hang%d" % s, (s * 0.7, -0.75, cz - 0.6), (s * 0.5, 0, -1), 0.9, 0.2, curl=0.7))
        parts.append(orn.leaf("rail%d" % s, (s * 0.9, -0.7, H + 0.95), (s, 0, -0.1), 1.6, 0.3, curl=0.5))
        f = kit.lathe("finial%d" % s, [(0.0, 0.0), (0.2, 0.0), (0.22, 0.12), (0.12, 0.3), (0.18, 0.5), (0.1, 0.7), (0.04, 0.9), (0.0, 1.0)], 16, mat="gilt")
        kit.place(f, (s * (W / 2 + 0.72), -0.4, H + 1.25))
        parts.append(f)
    parts.extend(orn.shell("crest_shell", (0, -0.62, cz + 0.95), 0.85, 11, depth=0.35))
    flame = kit.lathe("flame", [(0.0, 0.0), (0.22, 0.0), (0.28, 0.15), (0.16, 0.35), (0.2, 0.5), (0.1, 0.75), (0.05, 1.0), (0.0, 1.15)], 16, mat="gilt")
    kit.place(flame, (0, -0.45, cz + 1.75))
    parts.append(flame)
    kit.join("frame", parts)

    # ebony reveal lining the opening (inner faces), so the picture sits ~0.5 m back
    rv = []
    rv.append(kit.box("rv_l", (0.06, 0.55, H), (-W / 2 + 0.03, 0.22, H / 2), mat="ebony"))
    rv.append(kit.box("rv_r", (0.06, 0.55, H), (W / 2 - 0.03, 0.22, H / 2), mat="ebony"))
    rv.append(kit.box("rv_t", (W, 0.55, 0.06), (0, 0.22, H - 0.03), mat="ebony"))
    kit.join("reveal", rv)

    # colliders: two posts and the lintel (opening stays clear)
    kit.collision_box("post_l", (1.4, 1.2, H + 1.0), (-W / 2 - 0.7, 0.0, H / 2))
    kit.collision_box("post_r", (1.4, 1.2, H + 1.0), (W / 2 + 0.7, 0.0, H / 2))
    kit.collision_box("lintel", (W + 2.6, 1.2, 1.2), (0, 0.0, H + 0.6))
