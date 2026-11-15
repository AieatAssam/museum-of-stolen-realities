"""Monumental gilt picture frame. Opening 4.6 x 7.2 m, bottom of the opening at floor level
(z=0) so the player walks straight through. Faces -Y (toward the viewer)."""
import math
import kit

W, H = 4.6, 7.2


def build(args):
    # moulding profile: (u = outward from the sight edge, v = toward viewer)
    prof = [(0.0, -0.45), (0.0, 0.06), (0.05, 0.1), (0.09, 0.08), (0.12, 0.16), (0.2, 0.18),
            (0.24, 0.3), (0.34, 0.36), (0.44, 0.3), (0.5, 0.26), (0.58, 0.4), (0.66, 0.46),
            (0.74, 0.42), (0.8, 0.3), (0.86, 0.26), (0.9, 0.3), (0.96, 0.22), (1.0, 0.1), (1.0, -0.45)]
    path = [(-W / 2, 0, 0), (W / 2, 0, 0), (W / 2, 0, H), (-W / 2, 0, H)]
    frame = kit.sweep_closed("frame", [(u, -v) for u, v in prof], path, mat="gilt")
    # flip so ornament faces -Y if the path winding put it the other way
    import bmesh
    parts = [frame]
    # corner rosettes on the two top corners and the base corners
    for i, (x, z) in enumerate([(-W / 2 - 0.5, H + 0.5), (W / 2 + 0.5, H + 0.5)]):
        r = kit.lathe("rosette%d" % i, [(0.0, 0.0), (0.42, 0.0), (0.4, 0.08), (0.3, 0.12), (0.32, 0.18), (0.2, 0.24), (0.12, 0.3), (0.0, 0.34)], 24, mat="gilt")
        kit.place(r, (x, -0.42, z), (math.radians(90), 0, 0))
        parts.append(r)
    # crest cartouche above the opening
    cart = kit.lathe("cartouche", [(0.0, 0.0), (0.9, 0.0), (0.86, 0.1), (0.7, 0.16), (0.72, 0.22), (0.5, 0.28), (0.3, 0.3), (0.0, 0.32)], 32, mat="gilt")
    kit.place(cart, (0, -0.4, H + 1.25), (math.radians(90), 0, 0), (1.3, 0.8, 1.0))
    parts.append(cart)
    for side in (-1, 1):
        sc = kit.torus("scroll%d" % side, 0.42, 0.09, 32, 10, mat="gilt", loc=(side * 1.35, -0.32, H + 0.95), rot=(math.radians(90), 0, 0))
        parts.append(sc)
        lf = kit.lathe("finial%d" % side, [(0.0, 0.0), (0.16, 0.0), (0.2, 0.1), (0.1, 0.3), (0.14, 0.5), (0.0, 0.8)], 16, mat="gilt")
        kit.place(lf, (side * (W / 2 + 0.5), -0.25, H + 0.95))
        parts.append(lf)
    kit.join("frame", parts)
    # colliders: two posts and the lintel (opening stays clear)
    kit.collision_box("post_l", (1.0, 0.9, H + 1.0), (-W / 2 - 0.5, 0.0, H / 2))
    kit.collision_box("post_r", (1.0, 0.9, H + 1.0), (W / 2 + 0.5, 0.0, H / 2))
    kit.collision_box("lintel", (W + 2.0, 0.9, 1.2), (0, 0.0, H + 0.6))
