"""Small brass table easel holding a paper card (the pinned sketch of the thief's hands)."""
import math
import kit


def build(args):
    legs = []
    for s in (-1, 1):
        legs.append(kit.tube("leg%d" % s, [(s * 0.16, 0.02, 0), (s * 0.04, 0.0, 0.48)], 0.008, 6, mat="brass"))
    legs.append(kit.tube("back", [(0, 0.2, 0), (0, 0.02, 0.44)], 0.008, 6, mat="brass"))
    legs.append(kit.tube("ledge", [(-0.2, -0.02, 0.08), (0.2, -0.02, 0.08)], 0.01, 6, mat="brass"))
    kit.join("easel", legs)
    card = kit.box("card", (0.3, 0.004, 0.38), (0, -0.03, 0.28), mat="sketch_paper")
    card.rotation_euler = (math.radians(-12), 0, 0)
