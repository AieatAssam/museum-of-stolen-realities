"""Clay wing props, hand-built in plasticine. One script, selected by args[0]. Run through
tools/blender_build.sh (wings/clay/tools/build_models.sh builds them all).
Blender: +Z up, 1 unit = 1 m; a figure's front is +Y (Godot -Z). Material names are the contract
(see wings/clay/tools/make_materials.py). Colliders keep the gameplay sizes they always had: the
boulder, plug and fence colliders live in GDScript, and nothing here adds one unless named -convcolonly."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import sculpt as S  # noqa: E402
from mathutils import Vector  # noqa: E402


# --- characters ---------------------------------------------------------------------------------

def _face(prefix, head_c, head_r, seed, parts, eye_mat="ivory"):
    """Two ivory eyes with ink pupils, a nose lump and a pressed-in smile line, on a +Y-facing head."""
    hx, hy, hz = head_c
    for s in (-1, 1):
        e = (hx + s * head_r * 0.36, hy + head_r * 0.82, hz + head_r * 0.18)
        parts.append(S.blob(prefix + "_eye%d" % s, (head_r * 0.36, head_r * 0.22, head_r * 0.4), e, eye_mat, seed + s, lump=0.004, subdiv=2))
        parts.append(S.blob(prefix + "_pupil%d" % s, (head_r * 0.13, head_r * 0.08, head_r * 0.15),
                            (e[0], e[1] + head_r * 0.1, e[2] - head_r * 0.03), "ink", seed + 2 * s, lump=0.0, subdiv=1))
    parts.append(S.blob(prefix + "_nose", (head_r * 0.3, head_r * 0.42, head_r * 0.28), (hx, hy + head_r * 0.98, hz - head_r * 0.08), "skin", seed + 9, lump=0.01, subdiv=2))
    parts.append(S.snake(prefix + "_mouth", [(hx - head_r * 0.3, hy + head_r * 0.86, hz - head_r * 0.42), (hx, hy + head_r * 0.95, hz - head_r * 0.5),
                                            (hx + head_r * 0.3, hy + head_r * 0.86, hz - head_r * 0.42)], head_r * 0.04, "roof", seed, sides=6, wobble=0.05))


def _hand(prefix, c, palm_dir, r, seed, mat):
    """An open hand: a flattened palm and four rolled fingers, splayed."""
    parts = [S.blob(prefix + "_palm", (r * 1.6, r * 0.7, r * 1.8), c, mat, seed, lump=0.01, subdiv=2)]
    px, py, pz = c
    for i in range(4):
        a = (i - 1.5) * 0.32
        tip = (px + math.sin(a) * r * 2.2, py + palm_dir * r * 0.3, pz + math.cos(a) * r * 2.1)
        parts.append(S.snake(prefix + "_f%d" % i, [(px + math.sin(a) * r * 0.6, py, pz + r * 0.6), tip], r * 0.28, mat, seed + i, sides=6, wobble=0.08, steps=2))
    parts.append(S.snake(prefix + "_th", [(px, py, pz), (px - r * 1.6, py + palm_dir * r * 0.4, pz + r * 0.6)], r * 0.3, mat, seed + 7, sides=6, steps=2))
    return parts


def B_unfinished():
    """The Unfinished One: 2.1 m, a lump of raw clay from the waist down, wire above with clay only half
    pressed on, holding a wooden modelling tool forward in its right hand."""
    sd = 11
    parts = [S.blob("u_base", (0.95, 0.85, 1.05), (0, 0, 0.45), "clay", sd, lump=0.07, dents=10, dent_r=0.18, dent_d=0.05)]
    parts.append(S.blob("u_waist", (0.62, 0.5, 0.6), (0, 0, 1.0), "clay", sd + 1, lump=0.05, dents=6))
    parts.append(S.snake("u_spine", [(0, 0, 1.1), (0.0, 0.02, 1.6), (0.0, 0.0, 1.95)], 0.03, "wire", sd, sides=6, wobble=0.0))
    # ribs of wire with clay pressed onto one side
    for i, z in enumerate((1.35, 1.5, 1.65)):
        parts.append(S.snake("u_rib%d" % i, [(-0.22, -0.02, z), (0.0, 0.14, z + 0.03), (0.22, -0.02, z)], 0.018, "wire", sd + i, sides=6, wobble=0.0))
    parts.append(S.blob("u_chest", (0.34, 0.3, 0.46), (0.1, 0.03, 1.5), "clay", sd + 2, lump=0.04, dents=5))
    # arms: the left bare wire, hanging; the right clay-covered, reaching forward with the tool
    parts.append(S.snake("u_armL", [(-0.22, 0, 1.72), (-0.34, 0.05, 1.4), (-0.36, 0.15, 1.12)], 0.02, "wire", sd, sides=6, wobble=0.0))
    parts += _hand("u_hL", (-0.36, 0.18, 1.08), 1, 0.055, sd + 3, "clay")
    parts.append(S.snake("u_armR", [(0.22, 0, 1.72), (0.36, 0.2, 1.45), (0.42, 0.55, 1.35)], 0.07, "clay", sd + 4, sides=10, wobble=0.15))
    parts.append(S.blob("u_fistR", (0.16, 0.18, 0.16), (0.43, 0.62, 1.34), "clay", sd + 5, lump=0.015))
    # the modelling tool: turned handle, flat spatula blade
    parts.append(S.lathe("u_handle", [(0.0, 0.0), (0.025, 0.0), (0.03, 0.1), (0.022, 0.3), (0.0, 0.32)], "wood", sd, segments=10, lump=0.002))
    kit.place(parts[-1], loc=(0.43, 0.62, 1.12))
    parts.append(S.slab("u_blade", (0.09, 0.012, 0.3), (0.43, 0.62, 1.55), "wood", sd, lump=0.002, bevel=0.004, cuts=3))
    # a head only roughed out: one eye pressed in, the other still a thumb hollow
    head = (0.0, 0.03, 2.05)
    parts.append(S.blob("u_head", (0.32, 0.3, 0.36), head, "clay", sd + 6, lump=0.03, dents=4, dent_r=0.08, dent_d=0.02))
    parts.append(S.blob("u_eye", (0.06, 0.03, 0.07), (0.06, 0.18, 2.08), "ivory", sd, lump=0.0, subdiv=2))
    parts.append(S.blob("u_pupil", (0.025, 0.02, 0.03), (0.06, 0.195, 2.075), "ink", sd, lump=0.0, subdiv=1))
    parts.append(S.snake("u_hoop", [(-0.14, 0, 2.2), (0.0, 0.0, 2.32), (0.14, 0, 2.2)], 0.015, "wire", sd, sides=6, wobble=0.0))
    kit.join("unfinished", parts).name = "unfinished"


def B_horse():
    """A pocket horse bent from twisted wire, one hind leg bent back; a clay saddle lump and tail tuft."""
    sd = 21
    parts = []

    def twisted(name, pts, r):
        out = []
        for k in range(2):
            a = k * math.pi
            tw = []
            p0 = [Vector(p) for p in pts]
            n = 12
            for i in range(n + 1):
                t = i / n
                seg = t * (len(p0) - 1)
                j = min(int(seg), len(p0) - 2)
                f = seg - j
                c = p0[j].lerp(p0[j + 1], f)
                ang = a + t * 10.0
                tw.append(c + Vector((0, math.cos(ang), math.sin(ang))) * r)
            out.append(S.snake(name + "%d" % k, tw, r * 0.7, "wire", sd + k, sides=5, wobble=0.0, steps=1))
        return out

    parts += twisted("h_body", [(-0.42, 0, 0.92), (0.0, 0, 0.96), (0.38, 0, 0.94)], 0.022)
    parts += twisted("h_neck", [(0.36, 0, 0.94), (0.52, 0, 1.12), (0.62, 0, 1.26)], 0.02)
    parts += twisted("h_head", [(0.6, 0, 1.28), (0.72, 0, 1.22), (0.84, 0, 1.1)], 0.02)
    for i, (x, y, back) in enumerate([(-0.38, -0.08, 0.0), (-0.36, 0.08, 1.0), (0.32, -0.08, 0.0), (0.34, 0.08, 0.0)]):
        knee = (x - 0.12 * back, y, 0.5 + 0.12 * back)
        foot = (x + 0.25 * back, y, 0.02 + 0.32 * back)
        parts.append(S.snake("h_leg%d" % i, [(x, y, 0.92), knee, foot], 0.016, "wire", sd + i, sides=6, wobble=0.0))
        if not back:
            parts.append(S.blob("h_hoof%d" % i, (0.07, 0.06, 0.05), (foot[0], y, 0.03), "bark", sd + i, lump=0.005, subdiv=2))
    parts.append(S.blob("h_saddle", (0.3, 0.2, 0.08), (0.0, 0, 1.0), "red", sd, lump=0.01, dents=2, dent_r=0.05, dent_d=0.01))
    parts.append(S.snake("h_tail", [(-0.44, 0, 0.92), (-0.58, 0, 0.82), (-0.62, 0.02, 0.62)], 0.03, "bark", sd, sides=7, taper=(1.0, 0.4)))
    parts.append(S.snake("h_mane", [(0.38, 0, 1.0), (0.5, 0, 1.18), (0.6, 0, 1.32)], 0.025, "bark", sd + 1, sides=7))
    kit.join("horse", parts).name = "horse"


# --- provenances, fragment -------------------------------------------------------------------------

def B_thumb():
    """A thumbprint larger than a hand: an oval pad of terracotta pressed with whorl ridges."""
    sd = 31
    pad = S.blob("thumb_pad", (1.1, 0.8, 0.22), (0, 0, 0.08), "clay", sd, lump=0.015, subdiv=4)
    parts = [pad]
    for i in range(9):
        rr = 0.06 + i * 0.055
        pts = []
        for k in range(29):
            a = (k / 28) * 2 * math.pi * (0.92 if i > 5 else 1.0) + i * 0.4
            wob = 1.0 + 0.04 * math.sin(a * 3 + i)
            pts.append((math.cos(a) * rr * 1.25 * wob, math.sin(a) * rr * 0.9 * wob + 0.03 * i * 0.2, 0.18 - (rr / 0.6) ** 2 * 0.08))
        parts.append(S.snake("ridge%d" % i, pts, 0.016, "clay", sd + i, sides=6, wobble=0.2, steps=2))
    kit.join("thumb", parts).name = "thumb"


def B_film():
    """A scrap of cling film, scrunched in a fist and let go."""
    S.blob("film", (0.7, 0.62, 0.5), (0, 0, 0.3), "film", 41, lump=0.16, scale=5.0, subdiv=5)


def B_fragment():
    """A pinch of the Pinched Forest: a thumb-pressed disc of moss and clay with a tiny tree and a
    pebble path on it, pinched up at one edge where it was torn from the rest."""
    sd = 51
    parts = [S.blob("f_base", (0.62, 0.54, 0.2), (0, 0, -0.08), "clay", sd, lump=0.03, dents=3, dent_r=0.1, dent_d=0.02)]
    parts.append(S.blob("f_moss", (0.58, 0.5, 0.08), (0, 0, 0.03), "moss", sd + 1, lump=0.02, dents=4, dent_r=0.08, dent_d=0.015))
    parts.append(S.blob("f_pinch", (0.2, 0.16, 0.22), (0.26, -0.12, 0.05), "clay", sd + 2, lump=0.02, dents=2, dent_r=0.06, dent_d=0.02))
    parts.append(S.snake("f_trunk", [(-0.12, 0.08, 0.05), (-0.11, 0.07, 0.2), (-0.1, 0.09, 0.3)], 0.025, "bark", sd, sides=7))
    for i, (x, y, z, r) in enumerate([(-0.1, 0.09, 0.38, 0.11), (-0.18, 0.06, 0.32, 0.08), (-0.03, 0.12, 0.33, 0.08)]):
        parts.append(S.blob("f_leaf%d" % i, (r * 2, r * 2, r * 1.8), (x, y, z), "leaf_lt" if i else "leaf", sd + i, lump=0.01, subdiv=2))
    for i in range(5):
        parts.append(S.blob("f_peb%d" % i, (0.05, 0.04, 0.025), (0.05 + i * 0.06, -0.05 + i * 0.03, 0.07), "stone", sd + i, lump=0.004, subdiv=1))
    parts.append(S.blob("f_flower", (0.05, 0.05, 0.03), (0.1, 0.2, 0.08), "pink", sd, lump=0.0, subdiv=1))
    kit.join("fragment", parts).name = "fragment"


# --- river, boulder ---------------------------------------------------------------------------------

def B_boulder():
    """A boulder of grey plasticine, thumbed all over, with moss pressed onto its crown. r = 1.15 m."""
    sd = 61
    parts = [S.blob("b_rock", (2.3, 2.2, 2.2), (0, 0, 0), "stone", sd, lump=0.12, scale=0.9, subdiv=5, dents=14, dent_r=0.35, dent_d=0.07)]
    for i, (a, z) in enumerate([(0.4, 0.95), (2.2, 0.85), (4.0, 0.9)]):
        parts.append(S.blob("b_moss%d" % i, (0.9, 0.7, 0.28), (math.cos(a) * 0.35, math.sin(a) * 0.35, z), "moss", sd + i, lump=0.04, dents=3, dent_r=0.12, dent_d=0.03))
    kit.join("boulder", parts).name = "boulder"


def B_river():
    """Cling film laid over the trench: 80 m long, sagging into it, crinkled, tucked at both banks.
    Placed at y=-0.2 on the trench centre line by clay.gd."""
    import bmesh
    bm = bmesh.new()
    nx, nz = 320, 24
    L, W = 80.0, 5.2
    grid = []
    for i in range(nx + 1):
        row = []
        for j in range(nz + 1):
            x = -L / 2 + L * i / nx
            y = -W / 2 + W * j / nz
            v = abs(y) / (W / 2)
            sag = -0.42 * (1.0 - v * v)
            crinkle = 0.035 * (S._lump(Vector((x, y, 0)), 7, 2.6))
            row.append(bm.verts.new((x, y, sag + crinkle + 0.06 * v ** 6)))
        grid.append(row)
    for i in range(nx):
        for j in range(nz):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    S.to_obj("river", bm, "film")


# --- the hill: burrow and plug ----------------------------------------------------------------------

INNER = [(-0.4, 2.42), (0.6, 2.42), (1.7, 2.2), (2.55, 1.5), (2.85, 0.0)]  # burrow chamber (z, r), bottom up


def _inner_r(z):
    for (z0, r0), (z1, r1) in zip(INNER, INNER[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * max(0.0, (z - z0) / (z1 - z0))
    return 0.0


def _inner_z(r):
    """Ceiling height of the chamber at radius r."""
    for (z0, r0), (z1, r1) in zip(INNER[2:], INNER[3:]):
        if r >= r1:
            return z0 + (z1 - z0) * (r0 - r) / max(r0 - r1, 1e-4)
    return INNER[-1][0]


def _ring_pt(r, a, z):
    return (math.cos(a) * r, math.sin(a) * r, z)


def B_burrow():
    """The chamber in the hill, hand-dug: a thick lumpy mound (moss outside, raw clay inside) with a round
    doorway on its west face (where the plug sits, x = -2.4) and a thumb-hole skylight in its crown over
    the plinth. Inside: spatula-gouged walls, roots through the ceiling, two shelves let into the wall
    with jars and a candle, a packed floor, and a cotton reel for a plinth under the skylight's pool
    (the film sits on it, local (1.7, 0)). A low trimesh collider gives the walls substance."""
    sd = 71
    SKY = (1.55, 0.0)
    outer = S.lathe("burrow", [(0.0, 3.9), (1.4, 3.75), (2.6, 3.0), (3.3, 1.7), (3.55, 0.5), (3.7, -0.3), (0.0, -0.3)], "moss", sd,
                    segments=48, lump=0.14, scale=0.8)
    inner = S.lathe("inner", [(r, z) for z, r in INNER][:1] + [(r, z) for z, r in INNER], "clay", sd + 1, segments=40, lump=0.07, scale=1.4)
    S.boolean(outer, inner)
    door = S.lathe("door", [(0.0, 0.0), (1.28, 0.0), (1.28, 3.0), (0.0, 3.0)], "clay", sd, segments=28, lump=0.0)
    door.rotation_euler = (0, math.pi / 2, 0)
    door.location = (-4.5, 0.0, 1.05)
    bpy_apply(door)
    S.boolean(outer, door)
    sky = S.lathe("sky", [(0.0, 0.0), (0.45, 0.0), (0.45, 3.0), (0.0, 3.0)], "clay", sd, segments=16, lump=0.0)
    sky.location = (SKY[0], SKY[1], 1.8)
    bpy_apply(sky)
    S.boolean(outer, sky)
    S.scatter_dents(outer, sd, 70, r=0.32, d=0.07)  # scoops where the digger's thumb went in

    def wall_r(z):  # outer radius of the mound at height z
        pts = [(-0.3, 3.7), (0.5, 3.55), (1.7, 3.3), (3.0, 2.6), (3.75, 1.4)]
        for (z0, r0), (z1, r1) in zip(pts, pts[1:]):
            if z <= z1:
                return r0 + (r1 - r0) * max(0.0, (z - z0) / (z1 - z0))
        return pts[-1][1]
    rim = []
    for k in range(25):
        a = math.pi * (k / 24)
        y = math.cos(a) * 1.36
        z = max(0.0, 1.05 + math.sin(a) * 1.36)
        rim.append((-math.sqrt(max(wall_r(z) ** 2 - y * y, 0.0)) + 0.05, y, z))
    parts = [outer, S.snake("rim", rim, 0.14, "clay", sd, sides=10, wobble=0.25)]
    # a rolled lip round the skylight, outside and in
    for k, (zz, rr) in enumerate(((3.62, 0.5), (2.5, 0.5))):
        parts.append(S.snake("skyrim%d" % k, [(SKY[0] + math.cos(t / 16 * 2 * math.pi) * rr, SKY[1] + math.sin(t / 16 * 2 * math.pi) * rr, zz) for t in range(17)],
                             0.07, "clay" if k else "moss", sd + k, sides=8, wobble=0.3))
    for i in range(6):
        a = i * 1.05 + 0.3
        parts.append(S.blob("tuft%d" % i, (0.9, 0.7, 0.35), (math.cos(a) * 2.6, math.sin(a) * 2.6, 2.9 - 0.25 * (i % 2)), "leaf", sd + i, lump=0.05, dents=2))
    for i in range(4):
        a = i * 1.6 + 0.9
        parts.append(S.blob("stone%d" % i, (0.5, 0.4, 0.32), (math.cos(a) * 3.8, math.sin(a) * 3.8, 0.05), "stone", sd + i, lump=0.04, dents=2))
    rnd = random.Random(sd)
    DOOR = math.pi
    # spatula gouges: short raised ridges swept round the wall, the edge a modelling tool leaves
    for i in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        if abs((a - DOOR + math.pi) % (2 * math.pi) - math.pi) < 0.75:
            continue
        z = rnd.uniform(0.25, 2.3)
        span = rnd.uniform(0.25, 0.6)
        dz = rnd.uniform(-0.25, 0.25)
        pts = []
        for k in range(5):
            t = k / 4
            zz = z + dz * t
            pts.append(_ring_pt(_inner_r(zz) - 0.015, a + span * t, zz))
        parts.append(S.snake("gouge%d" % i, pts, rnd.uniform(0.02, 0.04), "clay", sd + i, sides=6, wobble=0.35, taper=(0.4, 1.0), steps=3))
    # roots through the ceiling: tapered bark snakes that wander down, a few forking
    for i in range(9):
        r = rnd.uniform(0.6, 1.9)
        a = rnd.uniform(0, 2 * math.pi)
        z = _inner_z(r) + 0.05
        L = rnd.uniform(0.5, 1.2)
        pts = [_ring_pt(r, a, z)]
        for k in range(1, 6):
            pts.append((pts[-1][0] + rnd.uniform(-0.12, 0.12), pts[-1][1] + rnd.uniform(-0.12, 0.12), z - L * k / 5))
        parts.append(S.snake("root%d" % i, pts, rnd.uniform(0.03, 0.055), "bark", sd + i, sides=7, wobble=0.3, taper=(1.0, 0.15)))
        if i % 2 == 0:
            m = pts[2]
            parts.append(S.snake("rootb%d" % i, [m, (m[0] + 0.2, m[1] + 0.1, m[2] - 0.25), (m[0] + 0.25, m[1] + 0.22, m[2] - 0.45)], 0.02, "bark", sd, sides=5, wobble=0.2, taper=(1.0, 0.1)))
    # two shelves let into the wall, north and south, with what a burrow keeps
    for k, (a, z) in enumerate(((math.pi / 2, 1.25), (-math.pi / 2 + 0.25, 0.85))):
        r = _inner_r(z) - 0.2
        c = Vector(_ring_pt(r, a, z))
        t = Vector((-math.sin(a), math.cos(a), 0))
        shelf = S.slab("shelf%d" % k, (1.25, 0.42, 0.07), (0, 0, 0), "wood", sd + k, lump=0.008, bevel=0.025, cuts=4)
        shelf.rotation_euler = (0, 0, a + math.pi / 2)
        shelf.location = c
        parts.append(shelf)
        for j in range(2):
            parts.append(S.snake("peg%d_%d" % (k, j), [tuple(c + t * (0.45 * (2 * j - 1)) + Vector((0, 0, -0.03))),
                                                     tuple(c + t * (0.45 * (2 * j - 1)) + Vector((0, 0, -0.03)) - Vector((math.cos(a), math.sin(a), 0)) * -0.25 + Vector((0, 0, -0.18)))],
                                 0.03, "bark", sd, sides=6, steps=2))
        top = z + 0.035
        # a jar with something kept in it, a little pot, a candle, a ball of string
        jar = S.lathe("bjar%d" % k, [(0.0, 0.0), (0.09, 0.0), (0.1, 0.18), (0.07, 0.22), (0.075, 0.25), (0.0, 0.25)], "glass", sd, segments=16, lump=0.0)
        kit.place(jar, loc=tuple(c + t * -0.35 + Vector((0, 0, top - c.z + 0.0))))
        parts.append(jar)
        parts.append(S.blob("bjarin%d" % k, (0.13, 0.13, 0.12), tuple(c + t * -0.35 + Vector((0, 0, top - c.z + 0.07))), ["red", "yellow"][k], sd + k, lump=0.02, subdiv=2))
        pot = S.lathe("bpot%d" % k, [(0.0, 0.0), (0.08, 0.0), (0.11, 0.1), (0.09, 0.16), (0.1, 0.18), (0.0, 0.17)], "orange", sd + k, segments=14, lump=0.01)
        kit.place(pot, loc=tuple(c + t * 0.05 + Vector((0, 0, top - c.z))))
        parts.append(pot)
        if k == 0:
            parts.append(S.lathe("candle", [(0.0, 0.0), (0.05, 0.0), (0.045, 0.2), (0.0, 0.21)], "ivory", sd, segments=10, lump=0.004))
            kit.place(parts[-1], loc=tuple(c + t * 0.38 + Vector((0, 0, top - c.z))))
            parts.append(S.blob("flame", (0.035, 0.035, 0.07), tuple(c + t * 0.38 + Vector((0, 0, top - c.z + 0.25))), "bulb", sd, lump=0.0, subdiv=1))
        else:
            coil = [tuple(c + t * 0.38 + Vector((math.cos(q * 0.9) * 0.07, math.sin(q * 0.9) * 0.07, top - c.z + 0.07 + 0.004 * q))) for q in range(24)]
            parts.append(S.snake("string", coil, 0.022, "ivory", sd, sides=5, wobble=0.0, steps=1))
    # packed floor, trodden smoother at the middle; pebbles and a toadstool cluster at the foot of the wall
    parts.append(S.lathe("floor", [(0.0, 0.1), (2.38, 0.06), (2.38, -0.1), (0.0, -0.1)], "clay", sd + 5, segments=36, lump=0.02, scale=2.5, dents=14))
    for i in range(10):
        a = rnd.uniform(0.3, 2 * math.pi - 0.3) + DOOR
        parts.append(S.blob("pb%d" % i, (rnd.uniform(0.08, 0.18),) * 2 + (0.07,), _ring_pt(_inner_r(0.1) - 0.25, a, 0.12), "stone", sd + i, lump=0.02, subdiv=2))
    for i in range(3):
        a = -0.9 + i * 0.12
        cx, cy, _ = _ring_pt(_inner_r(0.1) - 0.3, a, 0)
        h = 0.12 + 0.06 * i
        parts.append(S.snake("tst%d" % i, [(cx, cy, 0.08), (cx, cy, 0.08 + h)], 0.025, "ivory", sd + i, sides=6, steps=2))
        parts.append(S.blob("tcap%d" % i, (0.12, 0.12, 0.06), (cx, cy, 0.08 + h), "red", sd + i, lump=0.01, subdiv=2))
    # the plinth: a cotton reel, red thread wound on a wooden core, under the skylight
    reel = S.lathe("reel", [(0.0, 0.0), (0.42, 0.0), (0.44, 0.02), (0.42, 0.06), (0.26, 0.07), (0.26, 0.24), (0.42, 0.25), (0.44, 0.28), (0.42, 0.31), (0.0, 0.31)],
                   "wood", sd + 9, segments=32, lump=0.004)
    kit.place(reel, loc=(1.7, 0.0, 0.1))
    parts.append(reel)
    parts.append(S.snake("thread", [(1.7 + math.cos(q * 0.55) * 0.3, math.sin(q * 0.55) * 0.3, 0.19 + 0.0042 * q) for q in range(40)], 0.035, "red", sd, sides=6, wobble=0.05, steps=1))
    ob = kit.join("burrow", parts)
    ob.name = "burrow"
    for p in ob.data.polygons:
        p.use_smooth = True
    # collider: the same shell, plain and low, so the walls stop you
    co = kit.lathe("burrow_col-colonly", [(0.0, 3.85), (1.4, 3.7), (2.6, 2.95), (3.3, 1.65), (3.55, 0.45), (3.65, -0.3), (0.0, -0.3)], segments=20)
    ci = kit.lathe("ci", [(r, z) for z, r in INNER][:1] + [(r - 0.04, z) for z, r in INNER], segments=20)
    S.boolean(co, ci)
    cd = kit.lathe("cd", [(0.0, 0.0), (1.3, 0.0), (1.3, 3.0), (0.0, 3.0)], segments=16)
    cd.rotation_euler = (0, math.pi / 2, 0)
    cd.location = (-4.5, 0.0, 1.05)
    bpy_apply(cd)
    S.boolean(co, cd)
    co.name = "burrow_col-colonly"


def bpy_apply(ob):
    import bpy
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ob.select_set(False)


def B_plug():
    """The door-sized plug: a round slab of clay facing west, a thumbprint the size of a door pressed in.
    Its collider (0.9 x 2.4 x 4 m) stays in clay.gd; this is only what you see."""
    sd = 81
    disc = S.lathe("plug_disc", [(0.0, -0.32), (1.3, -0.3), (1.42, -0.1), (1.4, 0.2), (1.25, 0.34), (0.0, 0.3)], "clay", sd, segments=40, lump=0.05, scale=1.2)
    parts = [disc]
    for i in range(10):
        rr = 0.12 + i * 0.105
        pts = []
        for k in range(33):
            a = (k / 32) * 2 * math.pi * (0.9 if i > 6 else 1.0) + i * 0.5
            pts.append((math.cos(a) * rr * 0.86, math.sin(a) * rr * 1.08 - 0.05, 0.3 - (rr / 1.3) ** 2 * 0.1))
        parts.append(S.snake("whorl%d" % i, pts, 0.028, "clay", sd + i, sides=6, wobble=0.25, steps=2))
    parts.append(S.blob("knob", (0.22, 0.22, 0.2), (0.0, 0.85, 0.38), "bark", sd, lump=0.01))
    ob = kit.join("plug", parts)
    ob.rotation_euler = (0, -math.pi / 2, 0)
    ob.location = (0.0, 0.0, 1.2)
    ob.name = "plug"


# --- fence ---------------------------------------------------------------------------------------

def B_gate():
    """One wire fence module, 4 m wide, 2.4 m tall, standing in the XZ plane: two whittled stakes, three
    twisted wire strands sagging between them, a tie of clay knotted at the middle."""
    sd = 91
    parts = []
    for s in (-1, 1):
        parts.append(S.lathe("stake%d" % s, [(0.0, -0.05), (0.06, -0.05), (0.075, 0.6), (0.07, 2.2), (0.05, 2.38), (0.0, 2.48)], "bark", sd + s,
                             segments=8, lump=0.012, scale=3.0))
        kit.place(parts[-1], loc=(s * 1.96, 0, 0))
    for z in (0.55, 1.25, 1.95):
        for k in range(2):
            pts = []
            for i in range(13):
                t = i / 12
                x = -1.96 + 3.92 * t
                sag = -0.08 * math.sin(math.pi * t)
                ang = t * 26.0 + k * math.pi
                pts.append((x, math.cos(ang) * 0.012, z + sag + math.sin(ang) * 0.012))
            parts.append(S.snake("strand%d_%d" % (int(z * 10), k), pts, 0.009, "wire", sd, sides=5, wobble=0.0, steps=1, caps=False))
    for i in range(7):
        x = -1.5 + 0.5 * i
        parts.append(S.snake("pick%d" % i, [(x, 0, 0.2), (x + 0.02, 0, 1.2), (x, 0, 2.15)], 0.008, "wire", sd + i, sides=5, wobble=0.0, steps=2, caps=False))
    parts.append(S.blob("knot", (0.34, 0.2, 0.3), (0, 0, 1.25), "red", sd, lump=0.02, dents=2, dent_r=0.06, dent_d=0.02))
    kit.join("gate", parts).name = "gate"


# --- the workbench ---------------------------------------------------------------------------------

def B_bench():
    """What stands on the giant workbench (the plateau, top at y=2.6): a sculptor's turntable under the
    fragment, an open pair of scissors, a jar of eyes, rolls of plasticine, a pot of tools, a scalpel.
    Origin = the bench-top centre (TABLE). Props with -convcolonly colliders are kept clear of the
    fragment (local -0.6, -0.4) and the walk from the front edge."""
    sd = 101
    parts = []
    cols = []
    # the turntable the fragment waits on: a wooden disc on a steel post with a felt top
    parts.append(S.lathe("tt_disc", [(0.0, 0.0), (0.7, 0.0), (0.74, 0.06), (0.7, 0.12), (0.0, 0.12)], "wood", sd, segments=36, lump=0.003))
    kit.place(parts[-1], loc=(-0.6, 0.4, 0.52))
    parts.append(S.lathe("tt_felt", [(0.0, 0.0), (0.62, 0.0), (0.6, 0.02), (0.0, 0.02)], "felt", sd, segments=36, lump=0.0))
    kit.place(parts[-1], loc=(-0.6, 0.4, 0.64))
    parts.append(S.lathe("tt_post", [(0.0, 0.0), (0.5, 0.0), (0.45, 0.06), (0.08, 0.12), (0.06, 0.5), (0.0, 0.52)], "steel", sd, segments=24, lump=0.0))
    kit.place(parts[-1], loc=(-0.6, 0.4, 0.0))
    cols.append(kit.collision_box("tt-convcolonly", (1.0, 1.0, 0.64), (-0.6, 0.4, 0.32)))
    # open scissors, 4.4 m: two bevelled blades crossing at a brass pivot, red moulded handles
    for k, ang in enumerate((0.28, -0.28)):
        blade = S.slab("blade%d" % k, (2.6, 0.26, 0.05), (1.3, 0.0, 0.0), "steel", sd + k, lump=0.0, bevel=0.02, cuts=4)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(blade.data)
        for v in bm.verts:  # taper to a point
            t = max(0.0, v.co.x) / 2.6
            v.co.y *= 1.0 - 0.85 * t
        bm.to_mesh(blade.data)
        bm.free()
        handle = S.snake("handle%d" % k, [(-0.2, 0.0, 0.0), (-0.9, 0.35, 0.0), (-1.5, 0.2, 0.0), (-1.55, -0.3, 0.0), (-0.95, -0.3, 0.0), (-0.3, -0.06, 0.0)],
                         0.11, "red", sd + k, sides=10, wobble=0.04)
        for ob in (blade, handle):
            ob.rotation_euler = (0, 0, ang + (math.pi if k else 0.0) * 0)
            ob.location = (3.0, -2.1, 0.08 + 0.1 * k)
            if k:
                ob.scale = (1, -1, 1)
        parts += [blade, handle]
    parts.append(S.lathe("pivot", [(0.0, 0.0), (0.13, 0.0), (0.12, 0.26), (0.0, 0.28)], "brass", sd, segments=16, lump=0.0))
    kit.place(parts[-1], loc=(3.0, -2.1, 0.0))
    # the jar of eyes, 2.2 m tall: glass body, brass lid lying beside it, eyes inside and spilt
    jar = S.lathe("jar", [(0.0, 0.0), (0.82, 0.0), (0.9, 0.12), (0.92, 1.7), (0.78, 1.95), (0.72, 2.1), (0.76, 2.2), (0.0, 2.2)], "glass", sd,
                  segments=40, lump=0.0, cap=False)
    kit.place(jar, loc=(-4.2, -1.6, 0.0))
    parts.append(jar)
    cols.append(kit.collision_box("jar-convcolonly", (1.8, 1.8, 2.2), (-4.2, -1.6, 1.1)))
    parts.append(S.lathe("lid", [(0.0, 0.0), (0.8, 0.0), (0.82, 0.18), (0.7, 0.22), (0.0, 0.22)], "brass", sd, segments=32, lump=0.0))
    kit.place(parts[-1], loc=(-2.9, -3.1, 0.0), rot=(0.25, 0, 0))
    rnd = random.Random(5)
    eyes = [(-4.2 + rnd.uniform(-0.55, 0.55), -1.6 + rnd.uniform(-0.55, 0.55), 0.3 + 0.4 * (i // 6)) for i in range(16)]
    eyes += [(-3.0, -1.0, 0.3), (-2.4, -0.6, 0.3), (-3.3, -0.2, 0.3)]
    for i, (x, y, z) in enumerate(eyes):
        a = rnd.uniform(0, 2 * math.pi)
        d = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.2, 0.6))).normalized()
        c = Vector((x, y, z))
        parts.append(S.blob("eye%d" % i, (0.56, 0.56, 0.56), c, "ivory", sd + i, lump=0.006, subdiv=3))
        parts.append(S.blob("iris%d" % i, (0.3, 0.3, 0.12), c + d * 0.25, ["blue", "leaf", "bark"][i % 3], sd + i, lump=0.0, subdiv=2,
                            rot=(math.acos(max(-1, min(1, d.z))) * 0 + math.atan2(math.hypot(d.x, d.y), d.z), 0, math.atan2(d.x, -d.y))))
        parts.append(S.blob("pupil%d" % i, (0.14, 0.14, 0.06), c + d * 0.29, "ink", sd + i, lump=0.0, subdiv=1,
                            rot=(math.atan2(math.hypot(d.x, d.y), d.z), 0, math.atan2(d.x, -d.y))))
    # the plasticine itself (tray of bars, coil, squashed ball, cut block) is plasticine.glb, placed by clay.gd here
    cols.append(kit.collision_box("rolls-convcolonly", (3.0, 3.4, 0.9), (3.9, 2.5, 0.45)))
    # a pot of modelling tools
    parts.append(S.lathe("pot", [(0.0, 0.0), (0.55, 0.0), (0.6, 0.9), (0.66, 1.0), (0.6, 1.02), (0.5, 0.95), (0.0, 0.95)], "orange", sd, segments=28, lump=0.02))
    kit.place(parts[-1], loc=(-4.4, 2.6, 0.0))
    cols.append(kit.collision_box("pot-convcolonly", (1.3, 1.3, 1.0), (-4.4, 2.6, 0.5)))
    for i, (dx, dy, tilt, kind) in enumerate([(0.15, 0.1, 0.25, 0), (-0.2, 0.05, -0.2, 1), (0.0, -0.2, 0.1, 2), (0.1, 0.25, -0.3, 0)]):
        h = S.lathe("tool%d" % i, [(0.0, 0.0), (0.07, 0.0), (0.08, 1.2), (0.06, 2.1), (0.0, 2.15)], "wood", sd + i, segments=10, lump=0.004)
        kit.place(h, loc=(-4.4 + dx, 2.6 + dy, 0.3), rot=(tilt, tilt * 0.5, 0))
        parts.append(h)
        tip = S.slab("tip%d" % i, (0.2 if kind == 0 else 0.06, 0.03, 0.6), (-4.4 + dx + math.sin(tilt * 0.5) * 2.3, 2.6 + dy - math.sin(tilt) * 2.3, 2.7),
                     "steel", sd + i, lump=0.0, bevel=0.01, cuts=2) if kind != 1 else S.snake("loop%d" % i, [(-4.4 + dx - 0.1, 2.6 + dy + 0.5, 2.45), (-4.4 + dx, 2.6 + dy + 0.55, 2.8), (-4.4 + dx + 0.1, 2.6 + dy + 0.5, 2.45)], 0.025, "steel", sd, sides=6, wobble=0.0)
        parts.append(tip)
    # a scalpel and a pencil, dropped
    parts.append(S.snake("pencil", [(1.6, 3.6, 0.1), (3.6, 3.9, 0.1)], 0.1, "yellow", sd, sides=6, wobble=0.0, taper=(1.0, 0.95)))
    parts.append(S.snake("lead", [(3.6, 3.9, 0.1), (3.95, 3.95, 0.1)], 0.08, "plaster", sd, sides=6, wobble=0.0, taper=(1.0, 0.1)))
    ob = kit.join("bench", parts)
    ob.name = "bench"


def B_lamp():
    """The anglepoise that lights the workbench at night: weighted base, two arms with springs, a red shade
    with a bulb. Origin at its base on the bench top; the head sits over the turntable (see ClayLook)."""
    sd = 111
    parts = [S.lathe("base", [(0.0, 0.0), (1.1, 0.0), (1.12, 0.25), (0.9, 0.42), (0.25, 0.5), (0.0, 0.5)], "lampshade", sd, segments=36, lump=0.01)]
    a0, a1, a2 = Vector((0, 0, 0.5)), Vector((0.6, -1.0, 5.6)), Vector((3.8, 1.2, 9.6))
    for s in (-1, 1):
        off = Vector((0.18 * s, 0.1 * s, 0))
        parts.append(S.snake("arm1_%d" % s, [a0 + off, a1 + off], 0.07, "steel", sd, sides=10, wobble=0.0))
        parts.append(S.snake("arm2_%d" % s, [a1 + off, a2 + off], 0.06, "steel", sd, sides=10, wobble=0.0))
    for i, (p, q) in enumerate([(a0 + Vector((0, 0.3, 0.6)), a1 + Vector((0, 0.3, -1.4))), (a1 + Vector((0.3, 0, 0.3)), a2 + Vector((-1.2, -0.4, -0.6)))]):
        coil = []
        n = 70
        d = (q - p).normalized()
        x = d.cross(Vector((0, 0, 1))).normalized()
        y = x.cross(d)
        for k in range(n + 1):
            t = k / n
            c = p.lerp(q, t)
            coil.append(c + (x * math.cos(t * 60) + y * math.sin(t * 60)) * 0.09)
        parts.append(S.snake("spring%d" % i, coil, 0.018, "steel", sd, sides=5, wobble=0.0, steps=1))
    for p in (a1, a2):
        parts.append(S.lathe("joint", [(0.0, -0.18), (0.2, -0.18), (0.22, 0.18), (0.0, 0.18)], "brass", sd, segments=16, lump=0.0))
        kit.place(parts[-1], loc=p, rot=(math.pi / 2, 0, 0.5))
    shade = S.lathe("shade", [(0.12, 0.0), (0.35, 0.05), (0.5, 0.5), (1.35, 1.7), (1.4, 1.78), (1.25, 1.75), (0.42, 0.55), (0.12, 0.1)], "lampshade", sd,
                    segments=40, lump=0.0, cap=False)
    bulb = S.blob("bulb", (0.9, 0.9, 1.0), (0, 0, 1.0), "bulb", sd, lump=0.0, subdiv=3)
    for ob in (shade, bulb):
        ob.rotation_euler = (math.pi - 0.25, 0.0, 0.0)
        ob.location = a2 + Vector((0, 0, 0.9))
    parts += [shade, bulb]
    kit.join("lamp", parts).name = "lamp"
    kit.collision_box("lamp-convcolonly", (2.2, 2.2, 0.6), (0, 0, 0.3))


def B_apron():
    """The workbench's own edge, seen from the set below: a thick front board with a routed lip and a
    drawer with a brass pull, side boards and two chunky legs, sized to the plateau (12 x 10 m, top
    2.6 m). Origin = plateau centre at ground level. Collider only under the top board behind z=-40, where the terrain ends."""
    sd = 121
    parts = []
    # front board (faces +Y = Godot -Z? no: the set lies at Godot +Z of the bench, Blender -Y)
    parts.append(S.slab("front", (12.6, 0.5, 0.75), (0, -5.25, 2.25), "wood", sd, lump=0.006, bevel=0.06, cuts=12))
    parts.append(S.slab("panel", (11.4, 0.3, 1.9), (0, -5.15, 0.95), "wood", sd + 9, lump=0.005, bevel=0.05, cuts=10))
    parts.append(S.slab("drawer", (4.4, 0.12, 1.2), (3.2, -5.34, 1.15), "wood", sd + 1, lump=0.004, bevel=0.05, cuts=6))
    parts.append(S.lathe("pull", [(0.0, 0.0), (0.16, 0.0), (0.18, 0.12), (0.1, 0.2), (0.0, 0.22)], "brass", sd, segments=16, lump=0.0))
    kit.place(parts[-1], loc=(3.2, -5.4, 1.15), rot=(math.pi / 2, 0, 0))
    for s in (-1, 1):
        parts.append(S.slab("side%d" % s, (0.5, 10.6, 0.75), (s * 6.3, 0, 2.25), "wood", sd + s, lump=0.006, bevel=0.06, cuts=10))
        parts.append(S.slab("leg%d" % s, (1.0, 1.0, 2.0), (s * 5.7, -4.7, 0.95), "wood", sd + 2 + s, lump=0.006, bevel=0.08, cuts=4))
        parts.append(S.slab("legb%d" % s, (1.0, 1.0, 2.0), (s * 5.7, 4.7, 0.95), "wood", sd + 4 + s, lump=0.006, bevel=0.08, cuts=4))
    parts.append(S.slab("back", (12.6, 0.5, 0.75), (0, 5.25, 2.25), "wood", sd + 7, lump=0.006, bevel=0.06, cuts=12))
    # the terrain stops at Godot z=-40, so the back of the bench top (z -46..-40) is a board, flush under the clay
    parts.append(S.slab("top", (12.2, 6.3, 0.4), (0, 2.1, 2.38), "wood", sd + 8, lump=0.0, bevel=0.03, cuts=12))
    kit.join("apron", parts).name = "apron"
    kit.collision_box("top", (12.2, 6.3, 0.4), (0, 2.1, 2.38))


# --- set dressing ----------------------------------------------------------------------------------

def B_tree(seed="131"):
    """A plasticine tree: a twisted trunk of rolled bark snakes and a canopy of thumbed green balls."""
    sd = int(seed)
    rnd = random.Random(sd)
    h = rnd.uniform(3.2, 4.4)
    parts = []
    for k in range(3):
        a = k * 2.1
        pts = [(math.cos(a) * 0.22, math.sin(a) * 0.22, 0.0), (math.cos(a + 0.8) * 0.12, math.sin(a + 0.8) * 0.12, h * 0.4),
               (math.cos(a + 1.6) * 0.1, math.sin(a + 1.6) * 0.1, h * 0.75)]
        parts.append(S.snake("trunk%d" % k, pts, 0.17, "bark", sd + k, sides=8, wobble=0.2, taper=(1.3, 0.7)))
    for k in range(3):
        a = k * 2.1 + 0.6
        parts.append(S.snake("bough%d" % k, [(0, 0, h * 0.62), (math.cos(a) * 0.9, math.sin(a) * 0.9, h * 0.85)], 0.09, "bark", sd + k, sides=7, taper=(1.0, 0.6)))
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.2, 1.1)
        s = rnd.uniform(1.1, 1.7)
        c = (math.cos(a) * r, math.sin(a) * r, h * 0.85 + rnd.uniform(-0.2, 0.9))
        parts.append(S.blob("ball%d" % k, (s, s, s * 0.9), c, "leaf" if k % 3 else "leaf_lt", sd + k, lump=0.08, scale=1.4, subdiv=4, dents=4, dent_r=0.25, dent_d=0.06))
    kit.join("tree", parts).name = "tree"


def B_flower(col="pink", seed="141"):
    """A clay daisy: rolled stem, two leaves, five petal dabs round a yellow button. Colour by args."""
    sd = int(seed)
    h = 0.32
    parts = [S.snake("stem", [(0, 0, 0), (0.02, 0.01, h * 0.5), (0.0, 0.03, h)], 0.012, "leaf", sd, sides=6, wobble=0.0)]
    for s in (-1, 1):
        parts.append(S.blob("leaf%d" % s, (0.12, 0.04, 0.02), (s * 0.06, 0.0, 0.08), "leaf", sd + s, lump=0.0, subdiv=1, rot=(0, -0.4 * s, 0)))
    for k in range(5):
        a = k * 2 * math.pi / 5
        parts.append(S.blob("petal%d" % k, (0.09, 0.05, 0.02), (math.cos(a) * 0.055, 0.03 + math.sin(a) * 0.055, h), col, sd + k, lump=0.0, subdiv=1, rot=(0, 0, a)))
    parts.append(S.blob("eye", (0.05, 0.05, 0.035), (0, 0.03, h + 0.012), "yellow" if col != "yellow" else "orange", sd, lump=0.0, subdiv=1))
    kit.join("flower", parts).name = "flower"


def B_tuft():
    """A tuft of grass: a bunch of rolled, flattened blades pinched together at the root."""
    sd = 151
    rnd = random.Random(sd)
    parts = []
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.05, 0.18)
        h = rnd.uniform(0.25, 0.45)
        parts.append(S.snake("blade%d" % k, [(0, 0, 0), (math.cos(a) * lean * 0.4, math.sin(a) * lean * 0.4, h * 0.6), (math.cos(a) * lean, math.sin(a) * lean, h)],
                             0.02, "leaf_lt" if k % 3 == 0 else "leaf", sd + k, sides=5, taper=(1.0, 0.25), steps=2))
    kit.join("tuft", parts).name = "tuft"


def B_toadstool():
    """A red-capped toadstool with ivory dots and a fat stem."""
    sd = 161
    parts = [S.lathe("stem", [(0.0, 0.0), (0.09, 0.0), (0.075, 0.15), (0.07, 0.24), (0.0, 0.25)], "ivory", sd, segments=14, lump=0.01)]
    parts.append(S.blob("cap", (0.36, 0.36, 0.2), (0, 0, 0.28), "red", sd, lump=0.012, subdiv=3))
    for k in range(7):
        a = k * 0.9
        r = 0.08 + 0.05 * (k % 2)
        parts.append(S.blob("dot%d" % k, (0.05, 0.05, 0.02), (math.cos(a) * r, math.sin(a) * r, 0.36 - r * 0.4), "ivory", sd + k, lump=0.0, subdiv=1))
    kit.join("toadstool", parts).name = "toadstool"


def B_pebble():
    sd = 171
    parts = []
    for k, (x, y, s) in enumerate([(0, 0, 0.32), (0.3, 0.12, 0.2), (-0.22, 0.2, 0.16)]):
        parts.append(S.blob("peb%d" % k, (s * 1.3, s, s * 0.6), (x, y, s * 0.2), "stone", sd + k, lump=0.02, subdiv=2, dents=1, dent_r=s * 0.4, dent_d=s * 0.1))
    kit.join("pebble", parts).name = "pebble"


def B_reed():
    """Bulrushes from rolled clay: tall leaves and two brown heads, for the riverbanks."""
    sd = 181
    rnd = random.Random(sd)
    parts = []
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        h = rnd.uniform(0.9, 1.5)
        lean = rnd.uniform(0.1, 0.35)
        parts.append(S.snake("rleaf%d" % k, [(0, 0, 0), (math.cos(a) * lean * 0.3, math.sin(a) * lean * 0.3, h * 0.6), (math.cos(a) * lean, math.sin(a) * lean, h)],
                             0.03, "leaf" if k % 2 else "leaf_lt", sd + k, sides=5, taper=(1.0, 0.2), steps=2))
    for k in range(2):
        x = 0.06 * (1 - 2 * k)
        h = 1.3 + 0.2 * k
        parts.append(S.snake("rstem%d" % k, [(x, 0, 0), (x, 0.02, h)], 0.012, "leaf", sd, sides=5))
        parts.append(S.snake("rhead%d" % k, [(x, 0.02, h - 0.12), (x, 0.02, h + 0.12)], 0.045, "bark", sd + k, sides=8))
    kit.join("reed", parts).name = "reed"


def B_cloud(seed="191"):
    """A cotton-white cloud of thumbed plasticine puffs, hung on two wires from the studio dark above."""
    sd = int(seed)
    rnd = random.Random(sd)
    parts = []
    for k in range(7):
        x = (k - 3) * 1.1 + rnd.uniform(-0.3, 0.3)
        s = 2.4 - abs(k - 3) * 0.45 + rnd.uniform(-0.2, 0.3)
        parts.append(S.blob("puff%d" % k, (s, s * 0.9, s * 0.8), (x, rnd.uniform(-0.3, 0.3), s * 0.25), "cloud", sd + k, lump=0.06, scale=1.2, subdiv=4, dents=3, dent_r=0.4, dent_d=0.07))
    for s in (-1, 1):
        parts.append(S.snake("hang%d" % s, [(s * 2.0, 0, 0.8), (s * 2.0, 0, 30.0)], 0.012, "wire", sd, sides=4, wobble=0.0, steps=1))
    kit.join("cloud", parts).name = "cloud"


def _roof(w, d, rh, z0, sd):
    """A thumbed roof: a gabled prism of clay, thick at the eaves, ridge a little sagged."""
    import bmesh
    bm = bmesh.new()
    prof = [(-d / 2, 0.0), (-d / 2 + 0.05, 0.22), (0.0, rh + 0.22), (d / 2 - 0.05, 0.22), (d / 2, 0.0), (0.0, rh - 0.15)]
    rings = []
    n = 10
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        sag = -0.08 * math.sin(math.pi * i / n)
        rings.append([bm.verts.new((x, y, z0 + z + (sag if k == 2 else 0.0))) for k, (y, z) in enumerate(prof)])
    m = len(prof)
    for i in range(n):
        for k in range(m):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % m], rings[i][(k + 1) % m]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    S.deform(bm, sd, 0.05, 1.8, 10, 0.25, 0.05)
    return S.to_obj("roof", bm, "roof")


def B_crumb():
    """A crumb of clay for the reshaping spray."""
    S.blob("crumb", (1.0, 0.8, 0.7), (0, 0, 0), "clay", 5, lump=0.12, scale=2.0, subdiv=2)


def B_backhills():
    """The distant painted-on-clay hills that close the set: a lumpy ring from 41 m out to 70 m, rising
    to 9 m, green with clay showing on the steep faces (the terrain shader is not on these, so the moss
    and clay are separate materials)."""
    import bmesh
    sd = 211
    bm = bmesh.new()
    seg, rings = 160, 9
    radii = [39.5, 42.0, 45.0, 48.0, 52.0, 56.0, 60.0, 65.0, 72.0]
    grid = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j, r in enumerate(radii):
            t = j / (rings - 1)
            base = Vector((math.cos(a) * r, math.sin(a) * r, 0))
            hill = (0.5 + 0.5 * math.sin(a * 5 + 1.3) * math.cos(a * 3)) * 6.0 + 2.0
            hgt = (-0.6 + hill * math.sin(min(t * 1.6, 1.0) * math.pi * 0.5) * (1.0 - 0.6 * t * t)) + 1.6 * S._lump(base * 0.08, sd, 1.0) * t
            if abs(base.x) < 9.0 and base.y > 0 and r < 50.0:  # stay under the workbench top (2.6, z -46..-36)
                hgt = min(hgt, 1.8)
            row.append(bm.verts.new((base.x, base.y, max(hgt, -0.6))))
        grid.append(row)
    for i in range(seg):
        for j in range(rings - 1):
            a, b = grid[i][j], grid[(i + 1) % seg][j]
            c, d = grid[(i + 1) % seg][j + 1], grid[i][j + 1]
            bm.faces.new((a, b, c, d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = S.to_obj("backhills", bm, "moss")
    ob.data.materials.append(kit.material("leaf"))
    for p in ob.data.polygons:
        if p.normal.z < 0.8 and p.center.length > 46:
            p.material_index = 1


def B_bush(seed="231"):
    sd = int(seed)
    rnd = random.Random(sd)
    parts = []
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.1, 0.5)
        s = rnd.uniform(0.5, 0.8)
        parts.append(S.blob("b%d" % k, (s, s, s * 0.85), (math.cos(a) * r, math.sin(a) * r, s * 0.35 + rnd.uniform(0, 0.2)), "leaf" if k % 2 else "moss", sd + k,
                            lump=0.05, subdiv=2, dents=2, dent_r=0.12, dent_d=0.03))
    for k in range(4):
        a = k * 1.7
        parts.append(S.blob("berry%d" % k, (0.08, 0.08, 0.08), (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.55), "red", sd + k, lump=0.0, subdiv=1))
    kit.join("bush", parts).name = "bush"


from figures import *  # noqa: E402,F401,F403  B_villager(variant)
from houses import *  # noqa: E402,F401,F403  B_cottage, village props
from workshop import *  # noqa: E402,F401,F403  B_sign, B_plasticine


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown prop: " + args[0])
    fn(*args[1:])
