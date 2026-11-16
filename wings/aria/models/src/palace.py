"""The Drowned Aria: hero props of the sunken opera palace.

Build one model per run:
  tools/blender_build.sh wings/aria/models/src/palace.py wings/aria/models/<kind>.glb <kind>
Kinds: chandelier, horn, pipes, seat, balustrade, column, sirena, audience, glass_bowls, cello, harp.
Units: metres, +Z up (Godot +Y after export). Origins are where the build puts them.
"""
import math

import kit  # tools/blender is on sys.path (export.py inserts it)


def _tube_pts(points, radius, name, mat, sides=8):
    return kit.tube(name, points, radius, sides=sides, mat=mat)


def chandelier():
    # cathedral chandelier: gilt frame, crystal drops; origin at the hanging point (top)
    parts = [kit.lathe("gilt_stem", [(0.07, 0.0), (0.07, -4.6)], segments=10, mat="gilt")]
    parts.append(kit.lathe("gilt_crown", [(0.0, 0.0), (0.45, -0.05), (0.7, -0.25), (0.55, -0.5), (0.2, -0.7), (0.0, -0.75)], segments=18, mat="gilt"))
    crystals = []
    for z, radius, n in [(-1.3, 1.5, 8), (-2.5, 2.4, 12), (-3.7, 3.0, 16)]:
        parts.append(kit.torus("gilt_ring", radius, 0.07, seg=48, rseg=8, mat="gilt", loc=(0, 0, z)))
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = radius * math.cos(a), radius * math.sin(a)
            parts.append(_tube_pts([(0, 0, z + 0.25), (x * 0.5, y * 0.5, z + 0.35), (x, y, z)], 0.05, "gilt_arm", "gilt", 6))
            # two drops per arm, hung from the ring
            for k in range(2):
                ox, oy = x + (k - 0.5) * 0.18 * math.cos(a + 1.57), y + (k - 0.5) * 0.18 * math.sin(a + 1.57)
                crystals.append(_place_drop(ox, oy, z))
    # outer ring of big globe drops at the rim
    for i in range(24):
        a = 2 * math.pi * i / 24
        crystals.append(_place_drop(3.35 * math.cos(a), 3.35 * math.sin(a), -3.95, scale=1.3))
    main = kit.join("chandelier", parts)
    glass = kit.join("chandelier_glass", [c for c in crystals if c is not None])
    main.location = (0, 0, 0)
    glass.location = (0, 0, 0)


def _place_drop(x, y, z, scale=1.0):
    ob = kit.lathe("drop", [(0.0, 0.0), (0.09, -0.12), (0.14, -0.35), (0.1, -0.6), (0.0, -0.72)], segments=6, mat="glass", smooth_angle=None)
    ob.scale = (scale, scale, scale)
    ob.location = (x, y, z)
    return ob


def horn():
    # caryatid holding a brass horn, on a plinth; ~2.4 m tall
    parts = [kit.lathe("plinth", [(0.62, 0.0), (0.6, 0.2), (0.45, 0.28), (0.36, 1.2), (0.46, 1.3), (0.32, 1.42), (0.0, 1.42)], segments=20, mat="fresco")]
    parts.append(kit.lathe("body", [(0.22, 1.4), (0.3, 1.9), (0.17, 2.3), (0.24, 2.7), (0.14, 3.0), (0.0, 3.05)], segments=14, mat="fresco"))
    parts.append(_tube_pts([(0.12, 0.0, 2.6), (0.45, 0.1, 2.65), (0.62, 0.15, 2.4)], 0.09, "arm", "fresco", 8))
    parts.append(kit.lathe("bell", [(0.02, 0.0), (0.05, 0.4), (0.1, 0.9), (0.28, 1.4), (0.55, 1.9), (0.62, 2.0)], segments=20, mat="brass", cap=False))
    for ob in parts[-1:]:
        ob.location = (0.62, 0.15, 2.45)
        ob.rotation_euler = (0.0, math.radians(-75), 0.0)
    kit.join("horn", parts)


def pipes():
    # three open organ pipes, C E G (tallest to shortest), on a wooden chest
    out = []
    for name, x, h, r in [("pipe_c", -0.6, 3.4, 0.14), ("pipe_e", 0.0, 2.8, 0.13), ("pipe_g", 0.6, 2.25, 0.12)]:
        ob = kit.lathe(name, [(r, 0.0), (r + 0.03, 0.2), (r - 0.01, 0.35), (r - 0.01, h), (r + 0.02, h + 0.05), (r, h + 0.08), (0.0, h + 0.08)], segments=16, mat="brass")
        ob.location = (x, 0, 0)
        out.append(ob)
    chest = kit.box("chest", (1.9, 0.5, 0.45), (0, 0, 0.225), mat="ebony", bevel=0.03)
    out.append(chest)
    kit.join("pipes_group", out)


def seat():
    # a velvet box seat with a gilt frame; origin at floor centre
    cushion = kit.box("cushion", (0.8, 0.7, 0.18), (0, 0.02, 0.45), mat="velvet", bevel=0.05)
    back = kit.box("back", (0.82, 0.14, 0.9), (0, -0.3, 0.9), mat="velvet", bevel=0.06)
    frame = kit.box("frame", (0.9, 0.82, 0.3), (0, 0.0, 0.15), mat="gilt", bevel=0.02)
    arm_l = kit.box("arm_l", (0.12, 0.7, 0.3), (-0.45, 0.0, 0.7), mat="velvet", bevel=0.05)
    arm_r = kit.box("arm_r", (0.12, 0.7, 0.3), (0.45, 0.0, 0.7), mat="velvet", bevel=0.05)
    kit.join("seat", [cushion, back, arm_l, arm_r])
    kit.join("seat_frame", [frame])


def balustrade():
    # 2.5 m balcony rail: gilt top and base, nine balusters
    parts = [kit.box("rail_top", (2.5, 0.16, 0.12), (0, 0, 1.0), mat="gilt", bevel=0.02),
             kit.box("rail_base", (2.5, 0.3, 0.12), (0, 0, 0.06), mat="gilt", bevel=0.02)]
    for i in range(9):
        x = -1.1 + i * 0.275
        parts.append(kit.lathe("baluster", [(0.03, 0.0), (0.08, 0.1), (0.04, 0.3), (0.09, 0.5), (0.05, 0.7), (0.11, 0.9), (0.06, 1.0)], segments=10, mat="gilt"))
        parts[-1].location = (x, 0, 0)
    kit.join("balustrade", parts)


def column():
    kit.lathe("column", [(0.62, 0.0), (0.58, 0.2), (0.44, 0.34), (0.38, 0.45), (0.36, 5.5), (0.42, 5.7), (0.52, 5.85), (0.62, 6.1), (0.6, 6.25)], segments=48, mat="fresco")


def sirena():
    # La Sirena: a bell of gown, two raised arms, a luminous head and hair streaming upward (~8 m)
    gown = kit.lathe("gown", [(0.06, 0.0), (1.6, 0.2), (1.85, 1.2), (1.15, 2.8), (0.9, 4.2), (0.8, 5.2), (0.5, 6.0), (0.28, 6.6), (0.0, 6.9)], segments=40, mat="sirena_glow")
    parts = [gown]
    for side in (-1, 1):
        parts.append(_tube_pts([(0.0, 0.0, 5.0), (side * 0.8, 0.1, 5.4), (side * 1.6, 0.25, 5.1), (side * 2.4, 0.3, 5.9)], 0.13, "arm", "sirena_glow", 8))
    head = kit.lathe("head", [(0.0, -0.3), (0.22, -0.2), (0.3, 0.0), (0.22, 0.2), (0.0, 0.3)], segments=18, mat="sirena_glow")
    head.location = (0, 0, 7.25)
    parts.append(head)
    for i in range(7):
        a = -0.9 + i * 0.3
        pts = [(0.25 * math.cos(a), 0.25 * math.sin(a), 7.0)]
        for k in range(1, 6):
            t = k / 5.0
            pts.append((0.25 * math.cos(a) + t * 1.1 * math.cos(a * 2.0), 0.25 * math.sin(a) + t * 0.9 * math.sin(a * 2.0), 7.0 + t * 4.2))
        parts.append(_tube_pts(pts, 0.07, "hair", "sirena_glow", 6))
    kit.join("sirena", parts)


def audience():
    # one drowned listener: body, a pivoting head and hair drifting upward (origin at seat base)
    body = kit.lathe("body", [(0.05, 0.0), (0.22, 0.1), (0.2, 0.6), (0.24, 1.0), (0.18, 1.25), (0.13, 1.36)], segments=12, mat="velvet")
    head = kit.lathe("head", [(0.0, -0.12), (0.1, -0.11), (0.13, -0.05), (0.12, 0.05), (0.08, 0.12), (0.0, 0.13)], segments=12, mat="fresco")
    head.location = (0, 0, 1.45)
    hair = []
    for i in range(3):
        x = (i - 1) * 0.07
        hair.append(_tube_pts([(x, 0.0, 1.5), (x * 2.0, 0.05, 1.9), (x * 3.0, 0.1, 2.5), (x * 4.0, 0.12, 3.1)], 0.03, "hair", "gilt", 4))
    kit.join("audience_body", [body])
    kit.join("audience_head", [head])
    kit.join("audience_hair", hair)


def glass_bowls():
    bowls = []
    for i, r in enumerate([0.55, 0.45, 0.36, 0.28, 0.2]):
        bowls.append(kit.lathe("bowl%d" % i, [(r, 0.0), (r * 0.95, 0.08), (r * 0.6, 0.12), (r * 0.25, 0.1), (0.0, 0.05)], segments=24, mat="glass", smooth_angle=None))
        bowls[-1].location = (0, 0, i * 0.02)
    kit.join("glass_bowls", bowls)


def cello():
    kit.lathe("cello", [(0.02, 0.0), (0.25, 0.05), (0.3, 0.3), (0.22, 0.5), (0.2, 0.62), (0.26, 0.8), (0.2, 1.0), (0.05, 1.25)], segments=16, mat="ebony")


def harp():
    arc = []
    for i in range(11):
        a = math.pi * i / 10
        arc.append((0.9 * math.cos(a) + 0.9, 0.0, 0.0 + 1.6 * math.sin(a) * 0.5 + 0.4 * (1 - i / 10)))
    frame = _tube_pts(arc, 0.04, "harp_frame", "gilt", 6)
    strings = []
    for i in range(10):
        t = i / 9.0
        base = (0.1 + t * 1.6, 0.0, 0.0)
        top = (0.1 + t * 1.6, 0.0, 1.6 - t * 0.6)
        strings.append(_tube_pts([base, top], 0.008, "string", "brass", 4))
    kit.join("harp_strings", strings)
    return frame


def _solid(name, size, loc, mat, bevel=0.0):
    """Visible box plus an identical trimesh collider (-colonly) so walking matches the visuals."""
    vis = kit.box(name, size, loc, mat=mat, bevel=bevel)
    kit.box(name + "-colonly", size, loc)
    return vis


def proscenium():
    # 8 m proscenium: two fluted gilt-capped pilasters and a round arch, centred on x=0, arch springs at z=9
    parts = []
    for x in (-4.0, 4.0):
        parts.append(kit.lathe("pros_pilaster", [(0.5, 0.0), (0.42, 0.35), (0.36, 0.5), (0.36, 8.5), (0.5, 8.7), (0.5, 9.0)], segments=20, mat="marble_ivory"))
        parts[-1].location = (x, 0, 0)
    arc = [(4.0 * math.cos(a), 0.0, 9.0 + 4.0 * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]]
    parts.append(kit.tube("pros_arch", arc, 0.3, sides=10, mat="gilt"))
    parts.append(kit.box("pros_keystone", (0.8, 0.5, 1.0), (0, 0, 13.1), mat="gilt", bevel=0.05))
    kit.join("proscenium", parts)
    kit.box("proscenium-colonly", (9.0, 0.6, 9.0), (0, 0, 4.5))


def box_bay():
    # one box-tier bay: velvet back panel, gilt frame, two pilasters, a marble tier floor
    parts = [kit.box("bay_panel", (3.0, 0.2, 3.6), (0, 0, 2.2), mat="velvet", bevel=0.04),
             kit.box("bay_frame_top", (3.5, 0.3, 0.25), (0, 0, 4.1), mat="gilt"),
             kit.box("bay_frame_sill", (3.5, 0.3, 0.25), (0, 0, 0.1), mat="gilt")]
    for x in (-1.75, 1.75):
        parts.append(kit.lathe("bay_pilaster", [(0.14, 0.0), (0.11, 0.2), (0.1, 3.9), (0.14, 4.1)], segments=12, mat="gilt"))
        parts[-1].location = (x, 0.0, 0.0)
    parts.append(kit.box("bay_tier_floor", (3.6, 2.4, 0.3), (0, -1.2, -0.15), mat="marble_ivory", bevel=0.02))
    kit.join("box_bay", parts)
    kit.box("box_bay-colonly", (3.6, 2.4, 0.3), (0, -1.2, -0.15))


def dome_shell():
    # 28 m hemispherical shell (open bowl, single-sided surfaces; the dome_fresco material is double-sided)
    R, T = 14.0, 0.6
    outer = [(R * math.sin(t), R * math.cos(t)) for t in [math.pi / 2 * i / 24 for i in range(25)]]
    inner = [(r - T, z) for r, z in reversed(outer)]
    kit.lathe("dome_bowl", outer, segments=56, mat="dome_fresco", cap=False)
    kit.lathe("dome_under", inner, segments=56, mat="dome_fresco", cap=False)
    kit.lathe("dome-colonly", outer, segments=40, mat=None, cap=False)


def stair_flight():
    # 12-step grand flight, 4 m wide, rising 3.6 m toward -Y (blender) so it climbs into the foyer
    parts = []
    for i in range(12):
        y = -i * 0.4
        z = 0.3 * (i + 1) - 0.15
        parts.append(kit.box("stair_step", (4.0, 0.42, 0.3), (0, y, z), mat="marble_ivory", bevel=0.015))
        kit.box("stair-colonly", (4.0, 0.42, 0.3), (0, y, z))
    kit.join("stair_flight", parts)


def pilaster():
    # a 5 m engaged pilaster with a gilt capital, for the foyer bays
    kit.lathe("pilaster", [(0.3, 0.0), (0.26, 0.2), (0.22, 0.4), (0.22, 4.6), (0.34, 4.75), (0.38, 5.0), (0.3, 5.1), (0.0, 5.1)], segments=20, mat="marble_ivory")


def floor_slab():
    # 30 x 30 m flooded marble floor, top surface at z=0
    kit.box("floor_slab", (30.0, 30.0, 0.8), (0, 0, -0.4), mat="marble_ivory")
    kit.box("floor_slab-colonly", (30.0, 30.0, 0.8), (0, 0, -0.4))


def wall_11():
    # an 11 m fresco wall, 14 m high, 0.8 m thick, with a gilt cornice; the Godot scene scales its length
    kit.box("wall_panel", (11.0, 0.8, 13.4), (0, 0, 6.7), mat="fresco", bevel=0.03)
    kit.box("wall_cornice", (11.2, 1.0, 0.6), (0, 0, 13.7), mat="gilt", bevel=0.03)
    kit.box("wall_11-colonly", (11.0, 0.8, 14.0), (0, 0, 7.0))


KINDS = {
    "chandelier": chandelier, "horn": horn, "pipes": pipes, "seat": seat, "balustrade": balustrade,
    "column": column, "sirena": sirena, "audience": audience, "glass_bowls": glass_bowls,
    "cello": cello, "harp": harp,
    "proscenium": proscenium, "box_bay": box_bay, "dome_shell": dome_shell,
    "stair_flight": stair_flight, "wall_11": wall_11, "pilaster": pilaster, "floor_slab": floor_slab,
}


def build(args):
    kind = args[0] if args else "horn"
    KINDS[kind]()
