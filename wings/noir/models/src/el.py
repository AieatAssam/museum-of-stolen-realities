"""Elevated railway and rooftop kit. Arg = part. Blender Z up; Godot x = Blender x, Godot z = -Blender y.
  el_bent     a trestle bent across the line: two laced lattice columns 9 m apart (Blender y +-4.5) from
              z -7.85 (the street) to 0 (the girder top, where the deck sits), cap girder, knee braces
  el_span     6 m of deck along X: two plate girders with stiffeners, ties, running rails, guard rail;
              origin at the deck's centre on the girder tops (z 0), rail top at z 0.3
  el_car      a 1930s el car 10 m along X, rail top at z 0; lit windows, trucks, headlamp at +X
  water_tower stave tank on a steel stand, 6.8 m, origin at its feet
  chimney     brick stack 2.4 m with stone cap and two pots, origin at its foot
  roof_vent   mushroom vent, roof_hatch  a hatch with a raised lid, parapet  3 m coping run (front -Y)
  skyline_block a far tower massing 12 x 12 x 40 m with window grid, origin at its foot centre"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import kit  # noqa: E402


def B(name, size, loc, mat, bevel=0.0, seg=2):
    """A box built about its own centre and moved to `loc`, so a rotation set afterwards turns it in place
    (kit.box bakes `loc` into the vertices, which would swing a rotated part about the world origin)."""
    ob = kit.box(name, size, (0, 0, 0), mat=mat, bevel=bevel, segments=seg)
    ob.location = loc
    return ob


_join = kit.join


def _join_baked(name, objs):
    """kit.join, then bake the transforms so the mesh's own origin is the part's origin."""
    ob = _join(name, objs)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


kit.join = _join_baked


def _lattice_column(p, x, y, z0, z1, w=0.5):
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(B("angle", (0.08, 0.08, z1 - z0), (x + sx * w / 2, y + sy * w / 2, (z0 + z1) / 2), "iron"))
    n = int((z1 - z0) / 0.45)
    for k in range(n):
        za, zb = z0 + k * (z1 - z0) / n, z0 + (k + 1) * (z1 - z0) / n
        for side in (-1, 1):  # lacing bars zig-zag on the two faces seen from the line
            p.append(kit.tube("lace", [(x - w / 2 if k % 2 else x + w / 2, y + side * w / 2, za), (x + w / 2 if k % 2 else x - w / 2, y + side * w / 2, zb)], 0.018, 4, mat="iron"))
    p.append(B("base", (w + 0.3, w + 0.3, 0.1), (x, y, z0 + 0.05), "iron", bevel=0.02))
    p.append(B("cap", (w + 0.1, w + 0.1, 0.12), (x, y, z1 - 0.06), "iron"))


def el_bent():
    p = []
    for y in (-4.5, 4.5):
        _lattice_column(p, 0, y, -7.85, -0.9)
    # cap girder across, riveted web with stiffeners, flanges
    p.append(B("web", (0.04, 10.0, 0.9), (0, 0, -0.45), "steel"))
    for z in (-0.02, -0.88):
        p.append(B("flange", (0.35, 10.0, 0.04), (0, 0, z), "iron"))
    for i in range(14):
        p.append(B("stiff", (0.3, 0.04, 0.82), (0, -4.6 + i * 0.7, -0.45), "iron"))
    for y in (-4.5, 4.5):
        for x in (-0.2, 0.2):
            p.append(kit.tube("knee", [(x, y * 0.95, -2.4), (x, y * 0.66, -0.9)], 0.04, 6, mat="iron"))
    kit.join("el_bent", p)


def el_span():
    p = []
    L = 6.0
    for y in (-1.05, 1.05):
        p.append(B("web", (L, 0.03, 0.85), (0, y, -0.43), "steel"))
        for z in (-0.02, -0.84):
            p.append(B("flange", (L, 0.32, 0.04), (0, y, z), "iron"))
        for i in range(9):
            p.append(B("stiff", (0.05, 0.28, 0.78), (-L / 2 + 0.33 + i * 0.67, y, -0.43), "iron"))
    for i in range(int(L / 0.5)):
        p.append(B("tie", (0.22, 3.2, 0.16), (-L / 2 + 0.25 + i * 0.5, 0, 0.08), "wood", bevel=0.01))
    for y in (-0.72, 0.72):
        p.append(B("rail_web", (L, 0.03, 0.1), (0, y, 0.21), "steel"))
        p.append(B("rail_head", (L, 0.07, 0.04), (0, y, 0.28), "chrome"))
        p.append(B("rail_foot", (L, 0.13, 0.02), (0, y, 0.17), "steel"))
    p.append(B("third_rail", (L, 0.08, 0.06), (0, 1.25, 0.22), "steel"))
    # guard rail along the outer edge
    for x in range(-3, 4, 1):
        p.append(B("post", (0.05, 0.05, 1.0), (x * 1.0 * (L / 6), -1.62, 0.5), "iron"))
    for z in (0.5, 1.0):
        p.append(B("guard", (L, 0.04, 0.05), (0, -1.62, z), "iron"))
    p.append(B("walk", (L, 0.5, 0.04), (0, -1.4, 0.06), "iron"))
    kit.join("el_span", p)


def el_car():
    p = []
    L, W, z0 = 10.0, 2.6, 0.95  # body floor sits 0.95 over the rail top
    H = 2.4
    p.append(B("body_low", (L, W, 1.0), (0, 0, z0 + 0.5), "paint", bevel=0.05))
    p.append(B("belt", (L + 0.02, W + 0.04, 0.08), (0, 0, z0 + 1.02), "chrome"))
    # window band: piers between lit windows on both sides
    n = 8
    pitch = (L - 1.2) / n
    for side in (-1, 1):
        y = side * (W / 2 - 0.04)
        for i in range(n + 1):
            x = -L / 2 + 0.6 + i * pitch
            p.append(B("pier", (0.2, 0.1, 0.9), (x, y, z0 + 1.5), "paint"))
        for i in range(n):
            x = -L / 2 + 0.6 + (i + 0.5) * pitch
            p.append(B("win", (pitch - 0.22, 0.04, 0.8), (x, y - side * 0.02, z0 + 1.5), "window_lit"))
    p.append(B("inner", (L - 0.1, W - 0.2, 0.9), (0, 0, z0 + 1.5), "black"))
    p.append(B("upper", (L, W, 0.35), (0, 0, z0 + 2.12), "paint", bevel=0.04))
    p.append(B("roof", (L + 0.1, W - 0.2, 0.18), (0, 0, z0 + 2.38), "paint", bevel=0.06))
    p.append(B("monitor", (L - 1.6, 1.2, 0.3), (0, 0, z0 + 2.6), "paint", bevel=0.04))
    for i in range(10):
        p.append(B("vent", (0.3, 0.04, 0.14), (-L / 2 + 1.4 + i * 0.8, 0.62, z0 + 2.62), "window_lit"))
    for x in (-L / 2 + 0.05, L / 2 - 0.05):  # end bulkheads with a door and window
        p.append(B("end", (0.1, W, H), (x, 0, z0 + H / 2), "paint", bevel=0.03))
        s = 1 if x > 0 else -1
        p.append(B("end_win", (0.04, 0.7, 0.6), (x + s * 0.05, 0.55, z0 + 1.6), "window_lit"))
        p.append(B("end_win", (0.04, 0.7, 0.6), (x + s * 0.05, -0.55, z0 + 1.6), "window_lit"))
        p.append(B("anticlimber", (0.12, W - 0.4, 0.14), (x + s * 0.1, 0, z0 + 0.1), "iron"))
    head = kit.lathe("headlamp", [(0.0, 0.0), (0.14, 0.0), (0.16, 0.12), (0.0, 0.14)], 16, mat="beam_lens")
    head.rotation_euler = (0, math.pi / 2, 0)
    head.location = (L / 2 + 0.1, 0, z0 + 2.0)
    p.append(head)
    # trucks: side frames, wheels, springs
    for xc in (-L / 2 + 1.6, L / 2 - 1.6):
        for y in (-0.72, 0.72):
            p.append(B("frame", (2.0, 0.08, 0.3), (xc, y * 1.1, 0.45), "iron", bevel=0.02))
            for dx in (-0.6, 0.6):
                w = kit.lathe("wheel", [(0.0, -0.05), (0.38, -0.05), (0.4, -0.02), (0.4, 0.05), (0.0, 0.05)], 18, mat="iron")
                w.rotation_euler = (math.pi / 2, 0, 0)
                w.location = (xc + dx, y, 0.38)
                p.append(w)
        p.append(B("bolster", (0.4, 2.0, 0.25), (xc, 0, 0.75), "iron"))
    p.append(B("underframe", (L - 1.0, W - 0.6, 0.3), (0, 0, z0 - 0.1), "iron"))
    kit.join("el_car", p)


def water_tower():
    p = []
    z0 = 3.0
    staves = []
    prof = [(1.5, z0), (1.6, z0 + 1.4), (1.5, z0 + 2.8)]
    p.append(kit.lathe("tank", prof, 48, mat="wood", cap=True))
    for z in (0.3, 0.9, 1.5, 2.1, 2.6):
        r = 1.5 + 0.1 * math.sin(math.pi * z / 2.8) + 0.02
        p.append(kit.torus("hoop", r, 0.025, 64, 6, mat="iron", loc=(0, 0, z0 + z)))
    p.append(kit.lathe("roof", [(0.0, z0 + 2.8), (1.7, z0 + 2.8), (1.7, z0 + 2.85), (0.15, z0 + 3.8), (0.0, z0 + 3.85)], 48, mat="roof"))
    p.append(kit.lathe("finial", [(0.0, z0 + 3.8), (0.06, z0 + 3.8), (0.04, z0 + 4.1), (0.0, z0 + 4.15)], 16, mat="iron"))
    p.append(kit.lathe("floor", [(0.0, z0 - 0.15), (1.85, z0 - 0.15), (1.85, z0), (0.0, z0)], 48, mat="wood"))
    legs = [(1.2, 1.2), (-1.2, 1.2), (1.2, -1.2), (-1.2, -1.2)]
    for x, y in legs:
        p.append(kit.tube("leg", [(x * 1.12, y * 1.12, 0), (x * 0.92, y * 0.92, z0 - 0.15)], 0.08, 8, mat="iron"))
    for (x0, y0), (x1, y1) in zip(legs, [legs[1], legs[3], legs[0], legs[2]]):
        p.append(kit.tube("brace", [(x0 * 1.06, y0 * 1.06, 0.3), (x1 * 0.98, y1 * 0.98, z0 - 0.4)], 0.025, 4, mat="iron"))
        p.append(kit.tube("brace", [(x1 * 1.06, y1 * 1.06, 0.3), (x0 * 0.98, y0 * 0.98, z0 - 0.4)], 0.025, 4, mat="iron"))
    p.append(kit.tube("ladder", [(1.85, 0, 0), (1.85, 0, z0 + 2.8)], 0.02, 4, mat="iron"))
    kit.join("water_tower", p)


def chimney():
    p = [B("stack", (0.9, 0.6, 2.2), (0, 0, 1.1), "brick", bevel=0.01)]
    p.append(B("band", (1.0, 0.7, 0.12), (0, 0, 1.9), "brick_dark", bevel=0.01))
    p.append(B("cap", (1.06, 0.76, 0.1), (0, 0, 2.25), "stone", bevel=0.02))
    for x in (-0.22, 0.22):
        pot = kit.lathe("pot", [(0.0, 2.3), (0.13, 2.3), (0.11, 2.5), (0.1, 2.7), (0.13, 2.74), (0.11, 2.76), (0.09, 2.76), (0.09, 2.5), (0.0, 2.5)], 14, mat="stone")
        pot.location = (x, 0, 0)
        p.append(pot)
    kit.join("chimney", p)


def roof_vent():
    p = [kit.lathe("vent", [(0.0, 0.0), (0.2, 0.0), (0.18, 0.1), (0.12, 0.15), (0.12, 0.8), (0.32, 0.85), (0.34, 0.9), (0.18, 1.05), (0.0, 1.08)], 18, mat="zinc")]
    p.append(B("curb", (0.6, 0.6, 0.12), (0, 0, 0.06), "roof", bevel=0.02))
    kit.join("roof_vent", p)


def roof_hatch():
    """Brick curb with a zinc cap flashing; a framed zinc lid with standing seams, strap hinges at the back,
    a pull handle at the front and a prop rod holding it a hand's width open."""
    p = [B("curb", (1.2, 1.0, 0.40), (0, 0, 0.20), "brick", bevel=0.02)]
    p.append(B("flashing", (1.28, 1.08, 0.05), (0, 0, 0.425), "zinc", bevel=0.012))
    p.append(B("drip", (1.3, 1.1, 0.02), (0, 0, 0.395), "zinc", bevel=0.005))
    p.append(B("well", (1.04, 0.84, 0.02), (0, 0, 0.452), "iron"))  # the dark gap under the open lid
    # the lid, hinged at the back edge (+Y), opened 12 degrees: built flat about the hinge, then turned
    hinge = (0.0, 0.53, 0.47)
    lid = [B("panel", (1.3, 1.1, 0.035), (0, -0.55, 0.0175), "zinc", bevel=0.008)]
    for x in (-0.63, 0.63):
        lid.append(B("rim_x%d" % (x > 0), (0.04, 1.1, 0.06), (x, -0.55, 0.03), "zinc", bevel=0.01))
    lid.append(B("rim_f", (1.3, 0.04, 0.06), (0, -1.08, 0.03), "zinc", bevel=0.01))
    for k in range(-2, 3):
        lid.append(B("seam%d" % (k + 2), (0.018, 1.02, 0.03), (k * 0.22, -0.55, 0.045), "zinc", bevel=0.006))
    for x in (-0.4, 0.4):
        lid.append(B("strap%d" % (x > 0), (0.06, 0.34, 0.012), (x, -0.17, 0.042), "iron", bevel=0.003))
        lid.append(kit.tube("knuckle%d" % (x > 0), [(x - 0.06, 0.0, 0.0), (x + 0.06, 0.0, 0.0)], 0.018, 10, mat="iron"))
    lid.append(kit.tube("handle", [(-0.1, -1.1, 0.03), (-0.1, -1.16, 0.06), (0.1, -1.16, 0.06), (0.1, -1.1, 0.03)],
                        0.011, 8, mat="iron"))
    lid_ob = _join_baked("lid", lid)
    lid_ob.rotation_euler = (math.radians(-12), 0, 0)  # front edge up
    lid_ob.location = hinge
    p.append(lid_ob)
    # prop rod from the curb's front corner up under the lid's front rim
    p.append(kit.tube("prop", [(0.5, -0.42, 0.45), (0.5, -0.5, 0.68)], 0.012, 8, mat="iron"))
    kit.join("roof_hatch", p)


def parapet():
    """3 m run along X, front face (the roof's outer face) at y=-0.15, 0.6 m tall; origin roof level."""
    p = [B("wall", (3.0, 0.3, 0.5), (0, 0, 0.25), "brick")]
    p.append(B("coping", (3.0, 0.42, 0.08), (0, 0, 0.54), "stone", bevel=0.015))
    p.append(B("drip", (3.0, 0.04, 0.03), (0, -0.19, 0.49), "stone"))
    kit.join("parapet", p)


def skyline_block():
    """Distant tower massing (seen through fog only): stepped setbacks, a window grid as lit and dark
    glass strips, a crown. 12 x 12 base, 46 m."""
    p = []
    tiers = [(12.0, 0.0, 24.0), (9.0, 24.0, 36.0), (6.0, 36.0, 44.0)]
    for w, z0, z1 in tiers:
        p.append(B("mass", (w, w, z1 - z0), (0, 0, (z0 + z1) / 2), "brick_dark"))
        floors = int((z1 - z0) / 3.2)
        for f in range(floors):
            z = z0 + 1.6 + f * 3.2
            for side in range(4):
                a = side * math.pi / 2
                lit = (f * 7 + side * 3) % 5 == 0
                r = w / 2 + 0.02
                strip = B("glass", (w * 0.86, 0.06, 1.3), (r * math.sin(a), -r * math.cos(a), z), "window_lit" if lit else "window_glass")
                strip.rotation_euler = (0, 0, a)
                p.append(strip)
        p.append(B("ledge", (w + 0.4, w + 0.4, 0.3), (0, 0, z1), "stone"))
    p.append(kit.lathe("spire", [(0.0, 44.0), (2.0, 44.0), (1.6, 47.0), (0.6, 50.0), (0.1, 55.0), (0.0, 55.2)], 8, mat="stone"))
    kit.join("skyline_block", p)


PARTS = {n: globals()[n] for n in ("el_bent", "el_span", "el_car", "water_tower", "chimney", "roof_vent",
                                   "roof_hatch", "parapet", "skyline_block")}


def build(args):
    PARTS[args[0]]()
