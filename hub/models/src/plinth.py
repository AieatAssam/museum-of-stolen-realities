"""Private Collection plinth with a glass vitrine. Top at 1.05 m, vitrine 0.5 m cube above it."""
import kit


def build(args):
    p = []
    p.append(kit.box("foot", (0.7, 0.7, 0.1), (0, 0, 0.05), mat="marble_black", bevel=0.015))
    p.append(kit.box("body", (0.58, 0.58, 0.85), (0, 0, 0.52), mat="marble_black", bevel=0.012))
    p.append(kit.box("cap", (0.66, 0.66, 0.08), (0, 0, 1.0), mat="gilt", bevel=0.012))
    kit.join("plinth", p)
    kit.box("vitrine", (0.52, 0.52, 0.52), (0, 0, 1.3), mat="glass", bevel=0.004, segments=1)
    kit.box("plinth-convcolonly", (0.7, 0.7, 1.6), (0, 0, 0.8))
