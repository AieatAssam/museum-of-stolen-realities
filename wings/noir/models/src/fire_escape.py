"""Fire-escape landing with a stair flight, projecting +X from a wall at x=0. Landing 2.4 m wide
(z 0..2.4 along the wall), 1.3 m deep, top surface at y=0 in Blender Z (Godot Y) = landing height.
Origin at the landing's wall-side, bottom of the landing deck."""
import kit


def build(args):
    parts = []
    deck_z = 0.0
    parts.append(kit.box("deck", (1.3, 2.4, 0.07), (0.65, 1.2, deck_z - 0.035), mat="iron_grate"))
    # bearers under the deck
    for y in (0.1, 2.3):
        parts.append(kit.box("bearer", (1.3, 0.07, 0.1), (0.65, y, deck_z - 0.12), mat="iron"))
    parts.append(kit.box("bearer_wall", (0.12, 2.4, 0.12), (0.06, 1.2, deck_z - 0.1), mat="iron"))
    # railings on the open sides (+X edge and both ends) with a top rail
    rail_h = 1.0
    parts.append(kit.box("rail_front", (0.04, 2.4, 0.04), (1.3, 1.2, rail_h), mat="iron"))
    parts.append(kit.box("rail_front_low", (0.04, 2.4, 0.04), (1.3, 1.2, 0.5), mat="iron"))
    for y in (0.0, 2.4):
        parts.append(kit.box("rail_side", (1.3, 0.04, 0.04), (0.65, y, rail_h), mat="iron"))
    for i in range(9):
        x = 0.1 + i * 0.14
        parts.append(kit.box("baluster", (0.02, 0.02, rail_h), (1.3 - 0.0, 0.1 + i * 0.27, rail_h / 2), mat="iron"))
    # stair flight down to the pavement at +Y side (a stringer ladder dropping away from the deck)
    for i in range(10):
        z = -0.2 - i * 0.3
        y = 0.25 + i * 0.0
        parts.append(kit.box("tread", (0.55, 0.9, 0.04), (0.45 + 0.0, 2.6 + 0.0, z), mat="iron_grate"))
    parts.append(kit.box("stringer", (0.05, 0.05, 3.4), (1.0, 2.6, -1.8), mat="iron"))
    kit.join("fire_escape", parts)
    kit.box("landing-convcolonly", (1.3, 2.4, 0.1), (0.65, 1.2, -0.05))
