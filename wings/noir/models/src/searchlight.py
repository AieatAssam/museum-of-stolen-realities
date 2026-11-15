"""Rooftop searchlight on a yoke, 1.6 m tall. The drum points along +Y in Blender, which is -Z in
Godot (the forward of a SpotLight3D). Origin at the base plate. Pivot node: 'head'."""
import math

import kit


def build(args):
    base = kit.box("base", (1.0, 1.0, 0.25), (0, 0, 0.125), mat="iron", bevel=0.04)
    column = kit.lathe("column", [(0.0, 0.25), (0.18, 0.25), (0.14, 0.5), (0.1, 1.0), (0.0, 1.0)], 16, mat="iron")
    yoke = []
    for x in (-0.42, 0.42):
        yoke.append(kit.box("yoke", (0.07, 0.07, 0.9), (x, 0, 1.2), mat="iron"))
    yoke.append(kit.box("yoke_bar", (0.9, 0.07, 0.07), (0, 0, 1.62), mat="iron"))
    kit.join("yoke_frame", [base, column] + yoke)

    # drum (the lamp head). Built along +Y, centred on origin, then carried by 'head'.
    head = []
    drum = kit.lathe("drum", [(0.0, -0.02), (0.36, -0.02), (0.42, 0.0), (0.46, 0.15), (0.5, 0.4), (0.5, 0.55), (0.0, 0.55)], 24, mat="iron")
    head.append(drum)
    lens = kit.lathe("lens", [(0.0, 0.55), (0.46, 0.55), (0.48, 0.56), (0.0, 0.56)], 24, mat="glass", smooth_angle=None)
    head.append(lens)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        head.append(kit.box("rib", (0.02, 0.62, 0.02), (0.5 * math.cos(a) * 0.9, 0.2, 0.5 * math.sin(a) * 0.9), mat="iron"))
    # place the head so the drum sits across the yoke bar, pointing +Y
    kit.join("head", head)
    kit.place(bpy_object("head"), loc=(0, 0, 1.62), rot=(math.radians(90), 0, 0))
    kit.box("base-convcolonly", (1.0, 1.0, 1.6), (0, 0, 0.8))


def bpy_object(name):
    import bpy
    return bpy.data.objects[name]
