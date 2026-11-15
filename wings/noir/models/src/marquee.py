"""The cinema's broken marquee: a 7 m canopy frame with a letter board. Letter cells on the board
are deliberately missing in a fixed pattern ('broken'). Origin: centre of the board, at ground
level of the canopy's underside. Board material 'lamp' is made emissive white at runtime."""
import kit

LETTERS = "NEGATIVE PICTURES"
MISSING = {1, 4, 7, 9, 12, 15}  # cells that have dropped out


def build(args):
    parts = []
    parts.append(kit.box("canopy", (7.2, 1.2, 0.18), (0, 0, 0.09), mat="iron"))
    parts.append(kit.box("board", (6.6, 0.8, 0.12), (0, -0.2, -0.22), mat="lamp"))
    parts.append(kit.box("frame_l", (0.08, 0.5, 1.6), (-3.45, 0, -0.9), mat="iron"))
    parts.append(kit.box("frame_r", (0.08, 0.5, 1.6), (3.45, 0, -0.9), mat="iron"))
    cell_w = 6.2 / len(LETTERS)
    for i, ch in enumerate(LETTERS):
        if ch == " " or i in MISSING:
            continue
        x = -3.1 + cell_w * (i + 0.5)
        parts.append(kit.box("letter", (cell_w * 0.7, 0.04, 0.5), (x, -0.5, -0.22), mat="lamp_letter"))
    kit.join("marquee", parts)
    kit.box("marquee-convcolonly", (7.2, 1.2, 0.2), (0, 0, 0.0))
