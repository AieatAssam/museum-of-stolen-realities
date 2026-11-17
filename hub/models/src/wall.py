"""One wall bay of the dodecagonal atrium: 12.9 m wide, 17 m tall (the gallery sits above).
Faces -Y (into the room). Black marble wainscot, damask field in a gilt panel moulding, cornice."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

W = 12.9


def build(args):
    parts = []
    parts.append(kit.box("back", (W, 0.4, 17.0), (0, 0.2, 8.5), mat="damask"))
    parts.append(kit.box("dado", (W, 0.3, 1.3), (0, -0.15, 0.65), mat="marble_black", bevel=0.02))
    # the dado fielded: five panels of a dark veined sienna marble a bay, raised in the black marble, each in a gilt bead
    n, x0, x1 = 5, -(W / 2 - 0.85), W / 2 - 0.85
    pw = (x1 - x0 - (n - 1) * 0.24) / n
    for k in range(n):
        cx = x0 + pw / 2 + k * (pw + 0.24)
        parts.append(kit.box("dado_field%d" % k, (pw, 0.05, 0.78), (cx, -0.32, 0.73), mat="marble_dado", bevel=0.012))
        hw = pw / 2 + 0.02
        bead = [(0.0, 0.0), (0.0, 0.02), (0.015, 0.035), (0.035, 0.02), (0.035, 0.0)]
        b = kit.sweep_closed("dado_bead%d" % k, [(u, -v) for u, v in bead], [(cx - hw, 0, 0.32), (cx + hw, 0, 0.32), (cx + hw, 0, 1.14), (cx - hw, 0, 1.14)], mat="gilt")
        b.location = (0, -0.3, 0)
        parts.append(orn.face_toward(b))
    parts.append(kit.box("dado_cap", (W, 0.42, 0.1), (0, -0.2, 1.33), mat="gilt", bevel=0.02))
    parts.append(kit.box("skirting", (W, 0.38, 0.18), (0, -0.19, 0.09), mat="gilt", bevel=0.015))
    # gilt panel moulding around the damask field
    prof = [(0.0, 0.0), (0.0, 0.05), (0.04, 0.09), (0.1, 0.1), (0.14, 0.06), (0.18, 0.04), (0.2, 0.0)]
    hw = W / 2 - 1.2
    path = [(-hw, 0, 1.9), (hw, 0, 1.9), (hw, 0, 14.6), (-hw, 0, 14.6)]
    pm = kit.sweep_closed("panel", [(u, -v) for u, v in prof], path, mat="gilt")
    parts.append(orn.face_toward(pm))
    z = 15.4
    for i, (d, h, m) in enumerate([(0.3, 0.3, "marble_black"), (0.5, 0.15, "gilt"), (0.8, 0.5, "marble_black"), (1.0, 0.12, "gilt")]):
        parts.append(kit.box("cornice%d" % i, (W, d, h), (0, -d / 2, z + h / 2), mat=m, bevel=0.02))
        z += h
    for s in (-1, 1):
        parts.append(kit.box("pilaster%d" % s, (0.7, 0.3, 14.0), (s * (W / 2 - 0.35), -0.15, 8.4), mat="marble_black", bevel=0.03))
        parts.append(kit.box("pil_line%d" % s, (0.06, 0.32, 13.4), (s * (W / 2 - 0.35), -0.16, 8.4), mat="gilt"))
    kit.join("wall", parts)
    kit.box("wall-convcolonly", (W, 1.0, 8.0), (0, 0.2, 4.0))
