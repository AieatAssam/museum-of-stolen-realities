"""Private Collection plinth: a black-marble pedestal with a moulded plinth base, sunk panels framed
in gilt on all four faces, a gilt cornice and a brass-framed glass vitrine. Top of the cornice
(the vitrine floor) at 1.05 m; vitrine 0.5 m cube above it."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402


def square(h, z):
    """Closed square path (CCW from above, so sweeps offset outward and upward)."""
    return [(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)]


def build(args):
    p = []
    H = 0.27  # half-width of the shaft
    # moulded base: plinth block, torus, scotia, fillet
    p.append(kit.sweep_closed("base", [(0.0, 0.0), (0.08, 0.0), (0.08, 0.07), (0.07, 0.08), (0.075, 0.1), (0.06, 0.125),
                                       (0.035, 0.13), (0.03, 0.15), (0.015, 0.16), (0.0, 0.17)], square(H, 0.0), mat="marble_black", smooth_angle=50.0))
    p.append(kit.box("shaft", (2 * H, 2 * H, 0.78), (0, 0, 0.16 + 0.39), mat="marble_black", bevel=0.006, segments=1))
    # sunk panels: a gilt bolection frame on each face
    for k in range(4):
        a = k * math.pi / 2
        fr = kit.sweep_closed("panel%d" % k, [(-0.012, 0.0), (0.0, 0.012), (0.012, 0.016), (0.022, 0.008), (0.026, 0.0)],
                              kit.rect_path(0.36, 0.54), mat="gilt", smooth_angle=45.0)
        orn.face_toward(fr)
        kit.place(fr, (math.sin(a) * -(H + 0.001), math.cos(a) * -(H + 0.001), 0.56), (0, 0, -a))
        p.append(fr)
        ros = kit.lathe("ros%d" % k, [(0.0, 0.0), (0.045, 0.0), (0.04, 0.012), (0.025, 0.018), (0.012, 0.026), (0.0, 0.028)], 12, mat="gilt")
        kit.place(ros, (math.sin(a) * -(H + 0.001), math.cos(a) * -(H + 0.001), 0.56), (math.radians(90), 0, -a))
        p.append(ros)
    # gilt cornice under the vitrine, with a bead row
    p.append(kit.sweep_closed("cornice", [(0.0, 0.0), (0.01, 0.0), (0.015, 0.02), (0.03, 0.035), (0.05, 0.055), (0.07, 0.07),
                                          (0.075, 0.08), (0.075, 0.1), (0.0, 0.1)], square(H, 0.94), mat="gilt", smooth_angle=50.0))
    for i in range(4):
        for j in range(7):
            t = -H - 0.03 + (2 * H + 0.06) * (j + 0.5) / 7
            a = i * math.pi / 2
            x, y = math.cos(a) * t + math.sin(a) * (H + 0.022), -math.sin(a) * t + math.cos(a) * (H + 0.022)
            p.append(orn.ellipsoid("bead%d_%d" % (i, j), (x, -y, 0.955), (0.02, 0.02, 0.02), seg=6, rings=4))
    p.append(kit.box("top", (2 * H + 0.15, 2 * H + 0.15, 0.012), (0, 0, 1.044), mat="marble_black", bevel=0.004, segments=1))
    kit.join("plinth", p)

    # vitrine: glass with a slim brass frame and a finial
    kit.box("vitrine", (0.5, 0.5, 0.5), (0, 0, 1.3), mat="glass", bevel=0.003, segments=1)
    f = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.append(kit.box("post%d%d" % (sx, sy), (0.018, 0.018, 0.5), (sx * 0.25, sy * 0.25, 1.3), mat="brass", bevel=0.003, segments=1))
    for z in (1.055, 1.545):
        f.append(kit.sweep_closed("rim%.2f" % z, [(-0.004, 0.0), (0.012, 0.0), (0.012, 0.012), (-0.004, 0.012)], square(0.25, z - 0.006), mat="brass", smooth_angle=30.0))
    fin = kit.lathe("finial", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.008), (0.012, 0.02), (0.018, 0.04), (0.008, 0.06), (0.0, 0.07)], 12, mat="brass")
    kit.place(fin, (0, 0, 1.55))
    f.append(fin)
    kit.join("vitrine_frame", f)
    kit.box("plinth-convcolonly", (0.7, 0.7, 1.6), (0, 0, 0.8))
