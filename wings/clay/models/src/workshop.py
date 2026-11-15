"""Clay wing workshop props: a museum label sign in the meadow, and the sculptor's bench of plasticine.
Blender +Z up, metres. Built only from sculpt.py helpers; nothing imports props.py."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import kit  # noqa: E402
import sculpt as S  # noqa: E402
from mathutils import Vector  # noqa: E402

__all__ = ["B_sign", "B_plasticine"]


def _dent(ob, c, r, depth):
    """Press a thumb dent into an object's verts around world point c (objects here sit at identity)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    c = Vector(c)
    for v in bm.verts:
        d = (v.co - c).length
        if d < r:
            v.co -= v.normal * depth * (1.0 - d / r) ** 2
    bm.to_mesh(ob.data)
    bm.free()


def B_sign():
    """A museum label sign: a dark ink tablet on a wooden frame, a turned post behind, a clay foot with
    two moss tufts, and a clay snail on top of the frame. The label text floats in front (y < 0), so
    nothing may stand in front of y = 0 inside x in [-0.45, 0.45], z in [0.79, 1.41]."""
    sd = 301
    parts = []
    # the board: front face flat at y = 0 (clamped below, so no bevel or lump ever pokes out in front)
    board = S.slab("board", (0.96, 0.10, 0.68), (0, 0.05, 1.1), "ink", sd, lump=0.0, bevel=0.02, cuts=6)
    bm = bmesh.new()
    bm.from_mesh(board.data)
    for v in bm.verts:
        if v.co.y < 0.0:
            v.co.y = 0.0
    bm.to_mesh(board.data)
    bm.free()
    parts.append(board)
    # the wooden frame: four rolled snakes, corners overlapping, centred on y = 0, just outside the text
    fr = 0.035
    parts.append(S.snake("fr_top", [(-0.54, 0, 1.45), (0, 0, 1.452), (0.54, 0, 1.45)], fr, "wood", sd, sides=8, wobble=0.04, steps=3))
    parts.append(S.snake("fr_bot", [(-0.54, 0, 0.75), (0, 0, 0.748), (0.54, 0, 0.75)], fr, "wood", sd + 1, sides=8, wobble=0.04, steps=3))
    parts.append(S.snake("fr_l", [(-0.5, 0, 0.71), (-0.5, 0, 1.1), (-0.5, 0, 1.49)], fr, "wood", sd + 2, sides=8, wobble=0.04, steps=3))
    parts.append(S.snake("fr_r", [(0.5, 0, 0.71), (0.5, 0, 1.1), (0.5, 0, 1.49)], fr, "wood", sd + 3, sides=8, wobble=0.04, steps=3))
    # the post, behind the board
    post = S.lathe("post", [(0.0, 0.0), (0.05, 0.0), (0.045, 0.5), (0.05, 1.0), (0.045, 1.36), (0.05, 1.42), (0.0, 1.42)],
                   "wood", sd, segments=12, lump=0.003, scale=3.0)
    kit.place(post, loc=(0, 0.16, 0))
    parts.append(post)
    # two bark pegs joining the post to the top corners of the board, behind it (y >= 0.12)
    for s in (-1, 1):
        parts.append(S.snake("peg%d" % s, [(0, 0.16, 1.3), (s * 0.2, 0.15, 1.36), (s * 0.42, 0.14, 1.4)], 0.02, "bark", sd + 4 + s,
                             sides=6, wobble=0.0, steps=2))
    # the foot: a lumpy clay lump with thumb dents, two moss tufts on top
    parts.append(S.blob("foot", (0.5, 0.42, 0.24), (0, 0.08, 0.11), "clay", sd, lump=0.03, dents=3, dent_r=0.1, dent_d=0.02))
    parts.append(S.blob("tuft_a", (0.14, 0.12, 0.09), (-0.16, -0.02, 0.22), "moss", sd + 6, lump=0.05, subdiv=2, dents=2, dent_r=0.05, dent_d=0.015))
    parts.append(S.blob("tuft_b", (0.14, 0.12, 0.09), (0.18, 0.2, 0.22), "moss", sd + 7, lump=0.05, subdiv=2, dents=2, dent_r=0.05, dent_d=0.015))
    # the snail on top of the frame, above the text (z > 1.45)
    parts.append(S.blob("snail_body", (0.12, 0.05, 0.035), (0.31, 0.0, 1.5), "skin", sd + 8, lump=0.01, subdiv=2))
    shell = []
    for k in range(27):
        t = k / 26
        a = t * 4 * math.pi
        r = 0.03 * (1.0 - 0.75 * t)
        shell.append((0.36 + r * math.cos(a), 0.0, 1.545 + r * math.sin(a)))
    parts.append(S.snake("snail_shell", shell, 0.009, "orange", sd + 9, sides=6, wobble=0.0, steps=1))
    kit.join("sign", parts).name = "sign"


def B_plasticine():
    """The sculptor's bench of plasticine (footprint within +-1.5 x +-1.7 m, origin on the bench): a cardboard
    tray of five coloured bars, one pulled out over the rim and bent up with a thumbprint; a red coiled snake
    with its loose end lifting; a yellow ball with a deep thumbprint and whorl ridges; a blue block with a cut
    slice beside it; and a steel modelling knife across the bench."""
    sd = 401
    parts = []
    TX, TY = -0.6, -0.8
    # the tray: a plaster floor and four low walls
    parts.append(S.slab("tray_floor", (1.6, 1.2, 0.04), (TX, TY, 0.02), "plaster", sd, lump=0.005, bevel=0.01, cuts=4))
    parts.append(S.slab("tray_n", (1.6, 0.06, 0.12), (TX, TY + 0.57, 0.06), "plaster", sd + 1, lump=0.005, bevel=0.01, cuts=4))
    parts.append(S.slab("tray_s", (1.6, 0.06, 0.12), (TX, TY - 0.57, 0.06), "plaster", sd + 2, lump=0.005, bevel=0.01, cuts=4))
    parts.append(S.slab("tray_w", (0.06, 1.2, 0.12), (TX - 0.77, TY, 0.06), "plaster", sd + 3, lump=0.005, bevel=0.01, cuts=4))
    parts.append(S.slab("tray_e", (0.06, 1.2, 0.12), (TX + 0.77, TY, 0.06), "plaster", sd + 4, lump=0.005, bevel=0.01, cuts=4))
    # five bars side by side, lengthwise along x; bar 4 is half pulled out and bent up at its end
    colours = ["red", "yellow", "blue", "leaf_lt", "purple"]
    PULL = 4
    for i, mat in enumerate(colours):
        y = TY + (i - 2) * 0.2
        if i == PULL:
            parts.append(S.slab("bar%d" % i, (0.78, 0.19, 0.18), (-0.89, y, 0.13), mat, sd + 10 + i, lump=0.01, bevel=0.02, cuts=4))
            out = S.snake("bar%d_out" % i, [(-0.5, y, 0.13), (-0.1, y, 0.13), (0.12, y, 0.14), (0.3, y, 0.22), (0.42, y, 0.38)],
                          0.09, mat, sd + 10 + i, sides=10, wobble=0.04, steps=3)
            _dent(out, (0.42, y, 0.38), 0.12, 0.03)
            parts.append(out)
            gx1 = -0.6
        else:
            parts.append(S.slab("bar%d" % i, (1.36, 0.19, 0.18), (TX, y, 0.13), mat, sd + 10 + i, lump=0.01, bevel=0.02, cuts=6))
            gx1 = 0.0
        for g in (-0.05, 0.05):  # two lengthwise grooves, thin snakes of the same colour sunk into the top
            parts.append(S.snake("groove%d_%d" % (i, int(g * 100)), [(-1.2, y + g, 0.21), (gx1, y + g, 0.21)], 0.014, mat, sd + 30 + i,
                                 sides=6, wobble=0.0, steps=1))
    # a coiled snake of red plasticine: three turns, outer coil radius 0.55, loose end lifting off the bench
    cx, cy = 0.86, -0.9
    N = 90
    coil = []
    for i in range(N + 1):
        f = i / N
        th = 2 * math.pi * 3 * f
        s = 1.0 - 0.7 * f
        coil.append((cx + 0.52 * s * math.cos(th), cy + 0.55 * s * math.sin(th), 0.11 + 0.11 * f))
    last = coil[-1]
    coil += [(last[0] + 0.1, last[1] + 0.1, 0.25), (last[0] + 0.2, last[1] + 0.25, 0.45)]
    parts.append(S.snake("coil", coil, 0.11, "red", sd + 50, sides=10, wobble=0.05, steps=1))
    # a squashed yellow ball with a deep thumbprint and concentric whorl ridges pressed into it
    BC = (0.8, 0.6)
    parts.append(S.blob("ball", (0.7, 0.7, 0.45), (BC[0], BC[1], 0.225), "yellow", sd + 60, lump=0.02, subdiv=4))
    _dent(parts[-1], (BC[0], BC[1], 0.45), 0.2, 0.12)

    def top(rr):  # height of the ball's surface at radius rr from the dent centre, dent included
        z = 0.225 + 0.225 * math.sqrt(max(0.0, 1.0 - (rr / 0.35) ** 2))
        return z - (0.12 * (1.0 - rr / 0.2) ** 2 if rr < 0.2 else 0.0)

    for k in range(1, 7):
        rr = 0.03 * k
        ring = [(BC[0] + rr * math.cos(2 * math.pi * j / 24), BC[1] + rr * math.sin(2 * math.pi * j / 24), top(rr) - 0.004) for j in range(25)]
        parts.append(S.snake("whorl%d" % k, ring, 0.012, "yellow", sd + 60 + k, sides=6, wobble=0.1, steps=1, caps=False))
    # a blue block, lumpy, with one thin cut slice lying tilted beside it
    parts.append(S.slab("block", (0.9, 0.6, 0.5), (-0.5, 0.9, 0.25), "blue", sd + 70, lump=0.03, bevel=0.06, cuts=6))
    parts.append(S.slab("slice", (0.5, 0.35, 0.08), (0.3, 0.95, 0.12), "blue", sd + 71, lump=0.01, bevel=0.015, cuts=4, rot=(0.0, 0.3, 0.4)))
    # a steel modelling knife across the bench: wooden turned handle, flat blade
    kx, ky, rz = -0.3, 0.2, 0.6
    dx, dy = math.cos(rz), math.sin(rz)
    handle = S.lathe("knife_handle", [(0.0, 0.0), (0.03, 0.0), (0.035, 0.11), (0.03, 0.22), (0.0, 0.24)], "wood", sd + 80, segments=10, lump=0.002)
    kit.place(handle, loc=(kx - dx * 0.12, ky - dy * 0.12, 0.035), rot=(0, math.pi / 2, rz))
    parts.append(handle)
    parts.append(S.slab("knife_blade", (0.24, 0.045, 0.008), (kx + dx * 0.24, ky + dy * 0.24, 0.01), "steel", sd + 81, lump=0.0,
                        bevel=0.002, cuts=4, rot=(0, 0, rz)))
    kit.join("plasticine", parts).name = "plasticine"
