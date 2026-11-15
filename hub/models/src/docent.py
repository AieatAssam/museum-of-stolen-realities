"""Docent-construct: a faceless, too-tall plaster figure holding a sketchboard. 2.25 m.
Head is a separate object (turns to watch you); origin of `head` at the neck pivot."""
import math
import kit


def build(args):
    body = kit.lathe("body", [(0.0, 0.0), (0.42, 0.0), (0.4, 0.1), (0.3, 0.6), (0.24, 1.0), (0.2, 1.3), (0.24, 1.55), (0.27, 1.68), (0.2, 1.78), (0.08, 1.84), (0.07, 1.92), (0.0, 1.93)], 32, mat="plaster", smooth_angle=80.0)
    kit.place(body, (0, 0, 0), (0, 0, 0), (1.0, 0.72, 1.0))
    # arms holding the board in front
    arm_l = kit.tube("arm_l", [(-0.27, 0, 1.62), (-0.32, -0.12, 1.35), (-0.18, -0.32, 1.22)], 0.05, 8, mat="plaster")
    arm_r = kit.tube("arm_r", [(0.27, 0, 1.62), (0.3, -0.15, 1.38), (0.12, -0.36, 1.32)], 0.05, 8, mat="plaster")
    board = kit.box("board", (0.5, 0.025, 0.38), (0, -0.36, 1.25), mat="sketch_paper", bevel=0.004, segments=1)
    board.rotation_euler = (math.radians(-35), 0, 0)
    kit.join("docent", [body, arm_l, arm_r])
    head = kit.lathe("head", [(0.0, 0.0), (0.09, 0.02), (0.12, 0.1), (0.125, 0.2), (0.1, 0.3), (0.0, 0.34)], 24, mat="plaster", smooth_angle=80.0)
    kit.place(head, (0, 0, 1.9), (0, 0, 0), (0.9, 1.05, 1.0))
    kit.box("docent-convcolonly", (0.7, 0.6, 2.2), (0, 0, 1.1))
