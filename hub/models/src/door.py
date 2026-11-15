"""Conservation door: a pair of panelled ebony leaves (raised fielded panels, brass lever handles
and kick plates) in a moulded marble architrave, under a broken scroll pediment with a gilt urn.
Opening 2.6 x 4.0 m, floor at z=0, faces -Y (the hall)."""
import math
import os
import sys

from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

W, H = 2.6, 4.0


def build(args):
    p = []
    # architrave: stepped moulding round the opening (the bottom run is buried in the floor)
    prof = [(0.0, -0.05), (0.0, 0.06), (0.05, 0.09), (0.12, 0.1), (0.16, 0.14), (0.24, 0.16), (0.3, 0.13), (0.34, 0.08), (0.36, -0.05)]
    arc = kit.sweep_closed("architrave", [(u, -v) for u, v in prof], [(-W / 2, 0, -0.4), (W / 2, 0, -0.4), (W / 2, 0, H), (-W / 2, 0, H)], mat="marble_ivory", smooth_angle=45.0)
    p.append(orn.face_toward(arc))
    for s in (-1, 1):
        p.append(kit.box("plinth%d" % s, (0.42, 0.24, 0.4), (s * (W / 2 + 0.18), -0.1, 0.2), mat="marble_black", bevel=0.015))
    # frieze + cornice + broken pediment
    p.append(kit.box("frieze", (W + 0.8, 0.22, 0.42), (0, -0.08, H + 0.38), mat="ebony", bevel=0.01))
    p.append(kit.box("fbead", (W + 0.86, 0.26, 0.04), (0, -0.08, H + 0.17), mat="gilt", bevel=0.015, segments=2))
    p.append(kit.box("corona", (W + 1.1, 0.42, 0.16), (0, -0.16, H + 0.67), mat="marble_ivory", bevel=0.02))
    p.append(kit.box("cyma", (W + 1.2, 0.46, 0.06), (0, -0.17, H + 0.78), mat="gilt", bevel=0.02, segments=2))
    for s in (-1, 1):
        flip = Matrix.Scale(-1, 4, (1, 0, 0)) if s > 0 else Matrix.Identity(4)
        m = Matrix.Translation((s * 0.75, -0.25, H + 1.25)) @ flip @ Matrix.Rotation(math.radians(160), 4, "Y")
        p.append(orn.scroll("ped%d" % s, m, 0.5, 0.07, 1.15, 0.12, 0.035, mat="marble_ivory"))
        p.append(orn.leaf("pl%d" % s, (s * 0.25, -0.3, H + 0.85), (s, 0, 0.5), 0.6, 0.16, curl=0.8))
    urn = kit.lathe("urn", [(0.0, 0.0), (0.14, 0.0), (0.12, 0.05), (0.06, 0.1), (0.07, 0.14), (0.2, 0.26), (0.22, 0.38), (0.14, 0.48),
                            (0.08, 0.52), (0.1, 0.56), (0.04, 0.62), (0.05, 0.72), (0.0, 0.8)], 20, mat="gilt")
    kit.place(urn, (0, -0.15, H + 0.82))
    p.append(urn)
    kit.join("surround", p)

    # leaves: two ebony doors with raised fielded panels
    lv = []
    for s in (-1, 1):
        cx = s * W / 4
        lv.append(kit.box("leaf%d" % s, (W / 2 - 0.02, 0.08, H - 0.02), (cx, 0.04, H / 2), mat="ebony", bevel=0.01))
        for (pz, ph) in ((1.0, 1.4), (2.95, 1.6)):
            lv.append(kit.box("field%d_%.0f" % (s, pz * 10), (W / 2 - 0.42, 0.05, ph - 0.12), (cx, -0.01, pz), mat="ebony", bevel=0.05, segments=2))
            fr = kit.sweep_closed("mould%d_%.0f" % (s, pz * 10), [(-0.01, 0.0), (0.0, 0.02), (0.03, 0.025), (0.045, 0.0)],
                                  [(cx - (W / 2 - 0.3) / 2, 0, pz - ph / 2), (cx + (W / 2 - 0.3) / 2, 0, pz - ph / 2),
                                   (cx + (W / 2 - 0.3) / 2, 0, pz + ph / 2), (cx - (W / 2 - 0.3) / 2, 0, pz + ph / 2)], mat="gilt", smooth_angle=45.0)
            lv.append(orn.face_toward(fr))
        lv.append(kit.box("kick%d" % s, (W / 2 - 0.12, 0.02, 0.22), (cx, -0.005, 0.14), mat="brass", bevel=0.004, segments=1))
        hx = s * 0.12
        lv.append(kit.lathe("rose%d" % s, [(0.0, 0.0), (0.045, 0.0), (0.04, 0.015), (0.02, 0.025), (0.0, 0.03)], 12, mat="brass"))
        kit.place(lv[-1], (hx, -0.005, 1.1), (math.radians(90), 0, 0))
        lv.append(orn.taper("lever%d" % s, [(hx, -0.03, 1.1), (hx, -0.07, 1.1), (hx + s * 0.06, -0.08, 1.1), (hx + s * 0.14, -0.075, 1.08)], [0.012, 0.012, 0.011, 0.014], 8, "brass"))
    kit.join("leaves", lv)
    kit.collision_box("doorway", (W + 0.8, 0.4, H + 0.6), (0, 0.1, (H + 0.6) / 2))
