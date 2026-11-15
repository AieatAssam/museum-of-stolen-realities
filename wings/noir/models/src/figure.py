"""Two figures in a 1940s overcoat and trilby. Pass 'seated' to build the detective on a bench-edge
pose with the hat held in both hands at the lap. Standing figure is 1.8 m; origin at the soles.
Materials: 'coat' (wool), 'skin' (skin), 'hat' (felt), 'shirt' (white collar)."""
import math

import bmesh
import kit
from mathutils import Vector


def _ellipsoid(name, centre, radii, mat, segs=14, rings=10):
    bm = bmesh.new()
    rows = []
    for j in range(rings + 1):
        v = math.pi * j / rings
        row = []
        for i in range(segs):
            u = 2 * math.pi * i / segs
            row.append(bm.verts.new((
                centre[0] + radii[0] * math.sin(v) * math.cos(u),
                centre[1] + radii[1] * math.sin(v) * math.sin(u),
                centre[2] + radii[2] * math.cos(v))))
        rows.append(row)
    for j in range(rings):
        for i in range(segs):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % segs], rows[j + 1][(i + 1) % segs], rows[j + 1][i]))
    return kit._obj(name, bm, mat, 50.0)


def _limb(name, a, b, r, mat):
    return kit.tube(name, [a, b], r, 8, mat=mat)


def standing(parts):
    # legs (trousers) and shoes
    for x in (-0.12, 0.12):
        parts.append(_limb("leg", (x, 0, 0.12), (x, 0, 0.85), 0.085, "coat"))
        parts.append(kit.box("shoe", (0.14, 0.26, 0.09), (x, 0.03, 0.05), mat="coat", bevel=0.02))
    # long overcoat: a tapered lathe from hip to hem
    parts.append(kit.lathe("coat_skirt", [(0.28, 0.75), (0.3, 0.9), (0.24, 1.2), (0.2, 1.22), (0.0, 1.22)], 16, mat="coat"))
    parts.append(kit.lathe("torso", [(0.0, 0.8), (0.2, 0.8), (0.24, 1.0), (0.23, 1.25), (0.2, 1.42), (0.0, 1.45)], 16, mat="coat"))
    parts.append(kit.box("collar", (0.2, 0.12, 0.12), (0, 0.0, 1.45), mat="shirt"))
    # arms hanging, hands at the coat hem
    for x in (-0.3, 0.3):
        parts.append(_limb("arm", (x, 0, 1.36), (x * 1.05, 0.0, 0.85), 0.07, "coat"))
        parts.append(_ellipsoid("hand", (x * 1.05, 0.0, 0.8), (0.04, 0.05, 0.07), "skin"))
    parts.append(_ellipsoid("neck", (0, 0, 1.55), (0.06, 0.06, 0.09), "skin", 10, 6))
    parts.append(_ellipsoid("head", (0, 0.01, 1.7), (0.1, 0.11, 0.13), "skin", 14, 10))
    # trilby: crown + brim
    parts.append(kit.lathe("hat_crown", [(0.0, 1.8), (0.1, 1.8), (0.11, 1.84), (0.1, 1.9), (0.0, 1.93)], 16, mat="hat"))
    parts.append(kit.torus("hat_brim", 0.2, 0.025, 24, 6, mat="hat", loc=(0, 0, 1.8)))


def seated(parts):
    # bench-edge pose: thighs flat forward, shins down, torso upright, hat held at the lap
    for x in (-0.14, 0.14):
        parts.append(_limb("thigh", (x, 0.0, 0.5), (x, 0.42, 0.5), 0.09, "coat"))
        parts.append(_limb("shin", (x, 0.42, 0.5), (x, 0.42, 0.06), 0.08, "coat"))
        parts.append(kit.box("shoe", (0.14, 0.26, 0.09), (x, 0.47, 0.05), mat="coat", bevel=0.02))
    parts.append(kit.box("seat_hips", (0.42, 0.42, 0.22), (0, 0.1, 0.56), mat="coat", bevel=0.05))
    parts.append(kit.lathe("torso", [(0.0, 0.62), (0.2, 0.62), (0.22, 0.8), (0.21, 1.02), (0.19, 1.16), (0.0, 1.18)], 16, mat="coat"))
    parts.append(kit.box("collar", (0.2, 0.12, 0.12), (0, 0.0, 1.16), mat="shirt"))
    # forearms resting on the thighs, hands holding the hat on the lap
    for x in (-0.28, 0.28):
        parts.append(_limb("arm", (x, 0.02, 1.08), (x * 0.6, 0.3, 0.7), 0.065, "coat"))
        parts.append(_ellipsoid("hand", (x * 0.4, 0.36, 0.7), (0.05, 0.05, 0.04), "skin", 10, 6))
    parts.append(_ellipsoid("neck", (0, 0, 1.25), (0.06, 0.06, 0.08), "skin", 10, 6))
    parts.append(_ellipsoid("head", (0, 0.02, 1.36), (0.1, 0.11, 0.13), "skin", 14, 10))
    # hat held upside-down in the hands
    parts.append(kit.lathe("hat_crown", [(0.0, 0.7), (0.1, 0.7), (0.11, 0.74), (0.1, 0.8), (0.0, 0.83)], 16, mat="hat", smooth_angle=None))
    parts.append(kit.torus("hat_brim", 0.2, 0.025, 24, 6, mat="hat", loc=(0, 0.36, 0.66), rot=(math.radians(90), 0, 0)))


def build(args):
    parts = []
    if "seated" in args:
        seated(parts)
        kit.join("detective_seated", parts)
    else:
        standing(parts)
        kit.join("figure", parts)
