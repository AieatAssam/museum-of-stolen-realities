"""One wall bay of the dodecagonal atrium: 12.9 m wide, 22 m tall. Faces -Y (into the room).
Wainscot in black marble, damask field, gilt picture rail, cornice."""
import kit

W = 12.9


def build(args):
    parts = []
    parts.append(kit.box("back", (W, 0.4, 22.0), (0, 0.2, 11.0), mat="damask"))
    parts.append(kit.box("dado", (W, 0.3, 1.3), (0, -0.15, 0.65), mat="marble_black", bevel=0.02))
    parts.append(kit.box("dado_cap", (W, 0.42, 0.1), (0, -0.2, 1.33), mat="gilt", bevel=0.02))
    parts.append(kit.box("skirting", (W, 0.38, 0.18), (0, -0.19, 0.09), mat="gilt", bevel=0.015))
    parts.append(kit.box("rail", (W, 0.18, 0.12), (0, -0.09, 12.0), mat="gilt", bevel=0.02))
    # cornice: stacked steps
    z = 15.5
    for i, (d, h, m) in enumerate([(0.3, 0.3, "marble_black"), (0.5, 0.15, "gilt"), (0.8, 0.5, "marble_black"), (1.0, 0.12, "gilt")]):
        parts.append(kit.box("cornice%d" % i, (W, d, h), (0, -d / 2, z + h / 2), mat=m, bevel=0.02))
        z += h
    # pilaster strips at the bay edges
    for s in (-1, 1):
        parts.append(kit.box("pilaster%d" % s, (0.7, 0.3, 14.2), (s * (W / 2 - 0.35), -0.15, 8.4), mat="marble_black", bevel=0.03))
        parts.append(kit.box("pil_line%d" % s, (0.06, 0.32, 13.6), (s * (W / 2 - 0.35), -0.16, 8.4), mat="gilt"))
    kit.join("wall", parts)
    kit.box("wall-convcolonly", (W, 1.0, 8.0), (0, 0.2, 4.0))
