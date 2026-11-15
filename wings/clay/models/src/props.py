"""Clay wing props. One script, selected by args[0]. Run through tools/blender_build.sh.
Blender: +Z up, 1 unit = 1 m. Material names are the contract (see wings/clay/materials)."""
import math

import kit


def _sphere(name, r, loc, mat, n=10):
    prof = [(r * math.sin(math.pi * i / n), -r * math.cos(math.pi * i / n)) for i in range(n + 1)]
    ob = kit.lathe(name, prof, segments=16, mat=mat)
    kit.place(ob, loc=loc)
    return ob


def _disc(name, r, h, loc, mat):
    ob = kit.lathe(name, [(0.0, 0.0), (r, 0.0), (r * 1.02, h * 0.5), (r * 0.95, h), (0.0, h)], segments=20, mat=mat)
    kit.place(ob, loc=loc)
    return ob


def B_thumb():
    parts = [_disc("thumb_pad", 0.6, 0.12, (0, 0, 0), "clay")]
    for i, rr in enumerate([0.15, 0.27, 0.39, 0.5]):
        parts.append(kit.torus("ridge%d" % i, rr, 0.025, seg=24, rseg=6, mat="clay", loc=(0, 0, 0.12)))
    kit.join("thumb", parts).name = "thumb"


def B_boulder():
    parts = [_sphere("boulder_main", 1.15, (0, 0, 0), "clay", n=12)]
    for i in range(4):
        a = i * math.pi / 2 + 0.4
        lump = kit.lathe("lump%d" % i, [(0, 0), (0.35, 0.0), (0.3, 0.3), (0, 0.35)], segments=8, mat="clay")
        kit.place(lump, loc=(math.cos(a) * 0.95, math.sin(a) * 0.95, 0.4 - i * 0.2))
        parts.append(lump)
    kit.join("boulder", parts).name = "boulder"


def B_film():
    # a crumpled ball of cling film
    parts = [_sphere("film_ball", 0.42, (0, 0, 0.42), "film", n=10)]
    for i in range(5):
        a = i * 1.26
        parts.append(_sphere("crease%d" % i, 0.18, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.45 + 0.1 * (i % 2)), "film", n=6))
    kit.join("film", parts).name = "film"


def B_river():
    # a sheet of cling film laid flat: 24 m long, 4 m wide
    kit.box("river", (24.0, 4.0, 0.03), loc=(0, 0, 0.0), mat="film").name = "river"


def _wire_figure(height, arms, prefix):
    parts = [kit.tube(prefix + "_spine", [(0, 0, 0.0), (0, 0, height * 0.9)], 0.025, sides=6, mat="wire")]
    for s in (-1, 1):
        parts.append(kit.tube(prefix + "_arm%d" % s,
            [(0.0, 0.0, height * 0.7), (s * 0.3, -0.1, height * 0.62), (s * arms, -0.25, height * 0.7)], 0.02, sides=6, mat="wire"))
        parts.append(kit.tube(prefix + "_leg%d" % s,
            [(s * 0.12, 0, 0.0), (s * 0.12, 0, height * 0.45)], 0.025, sides=6, mat="wire"))
    parts.append(kit.tube(prefix + "_hoop", [(-0.16, 0, height * 0.9), (0.0, 0, height * 0.97), (0.16, 0, height * 0.9)], 0.02, sides=6, mat="wire"))
    return parts


def B_villager():
    body = kit.lathe("v_body", [(0.0, 0.0), (0.26, 0.0), (0.3, 0.3), (0.22, 0.9), (0.26, 1.15), (0.18, 1.45), (0.0, 1.5)],
        segments=12, mat="clay")
    head = _sphere("v_head", 0.16, (0, 0, 1.6), "clay", n=8)
    kit.join("villager", [body, head] + _wire_figure(1.6, 0.42, "v")).name = "villager"


def B_unfinished():
    body = kit.lathe("u_body", [(0.0, 0.0), (0.3, 0.0), (0.34, 0.5), (0.26, 1.1), (0.3, 1.5), (0.14, 1.9), (0.0, 2.0)],
        segments=14, mat="clay")
    head = _sphere("u_head", 0.2, (0.0, 0.0, 2.05), "clay", n=8)
    # one arm reaching forward, holding a clay spatula
    arm = kit.box("u_arm", (0.12, 0.12, 0.9), loc=(0.42, 0.0, 1.2), mat="clay")
    tool = kit.box("u_tool", (0.06, 0.34, 0.5), loc=(0.42, -0.1, 0.7), mat="wood")
    kit.join("unfinished", [body, head, arm, tool] + _wire_figure(2.1, 0.2, "u")).name = "unfinished"


def B_horse():
    parts = [
        kit.tube("h_body", [(-0.5, 0, 0.9), (0.4, 0, 0.92)], 0.04, sides=6, mat="wire"),
        kit.tube("h_neck", [(0.35, 0, 0.9), (0.6, 0, 1.25)], 0.035, sides=6, mat="wire"),
        kit.tube("h_head", [(0.6, 0, 1.25), (0.8, 0, 1.12)], 0.035, sides=6, mat="wire"),
        kit.tube("h_tail", [(-0.5, 0, 0.9), (-0.7, 0, 0.7)], 0.02, sides=6, mat="wire"),
        kit.tube("h_mane", [(0.35, 0, 1.2), (0.0, 0, 1.25)], 0.015, sides=5, mat="wire"),
    ]
    for i, (x, bend) in enumerate([(-0.4, 0.0), (-0.35, 0.0), (0.3, 0.0), (0.35, 0.22)]):
        parts.append(kit.tube("h_leg%d" % i, [(x, 0, 0.9), (x + bend, 0, 0.4), (x + bend, 0, 0.0)], 0.022, sides=5, mat="wire"))
    kit.join("horse", parts).name = "horse"


def B_bench():
    parts = [kit.box("top", (3.0, 1.2, 0.12), loc=(0, 0, 0.06), mat="wood")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(kit.box("leg", (0.12, 0.12, 0.6), loc=(sx * 1.4, sy * 0.5, -0.3), mat="wood"))
    parts.append(kit.box("shelf", (2.8, 1.0, 0.04), loc=(0, 0, -0.2), mat="wood"))
    # open jar of eyes (glass, with a few ivory eyes inside)
    jar = kit.lathe("jar", [(0.0, 0.0), (0.22, 0.0), (0.25, 0.3), (0.25, 0.5), (0.0, 0.5)], segments=16, mat="glass")
    kit.place(jar, loc=(-1.0, 0.0, 0.12))
    parts.append(jar)
    for i in range(3):
        parts.append(_sphere("eye%d" % i, 0.05, (-1.0 + 0.08 * (i - 1), 0.0, 0.42), "ivory", n=6))
    # open scissors on the bench top
    for ang in (0.45, -0.45):
        blade = kit.box("blade", (0.55, 0.04, 0.02), loc=(0.6, -0.2, 0.14), mat="steel")
        blade.rotation_euler = (0, 0, ang)
        parts.append(blade)
    kit.join("bench", parts).name = "bench"


def B_fragment():
    kit.lathe("fragment", [(0.0, -0.3), (0.22, -0.2), (0.28, 0.0), (0.16, 0.25), (0.0, 0.32)], segments=7, mat="clay").name = "fragment"


def B_gate():
    # a wire gate module, 4 m wide, 2.4 m tall, standing in the XZ plane (Godot: XY plane)
    parts = []
    for sx in (-2.0, 2.0):
        parts.append(kit.box("post", (0.09, 0.09, 2.4), loc=(sx, 0, 1.2), mat="wire"))
    for z in (0.5, 1.2, 1.9):
        parts.append(kit.tube("rail", [(-2.0, 0, z), (2.0, 0, z)], 0.03, sides=6, mat="wire"))
    for i in range(9):
        x = -2.0 + 0.5 * i
        parts.append(kit.tube("wire", [(x, 0, 0.0), (x, 0, 2.4)], 0.02, sides=5, mat="wire"))
    parts.append(_sphere("knot", 0.25, (0, 0, 1.2), "clay", n=6))
    kit.join("gate", parts).name = "gate"


def B_burrow():
    # the chamber: a clay dome, open on the west side
    kit.lathe("burrow", [(0.0, 0.0), (3.2, 0.0), (3.1, 0.8), (2.6, 1.8), (1.6, 2.6), (0.0, 3.0)],
        segments=24, mat="clay", cap=False).name = "burrow"


def B_plug():
    parts = [kit.box("plug_block", (0.9, 4.0, 2.4), loc=(0, 0, 1.2), mat="clay"),
             _disc("plug_thumb", 0.9, 0.06, (-0.45, 0, 1.6), "clay")]
    kit.join("plug", parts).name = "plug"


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown prop: " + args[0])
    fn()
