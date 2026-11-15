"""Village houses and yard props, hand-built in plasticine. Imported by props.py (selected by args[0] there).
+Z up, metres, everything stands on z=0, front faces +Y. Materials come from the shared list only."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import kit  # noqa: E402
import sculpt as S  # noqa: E402

__all__ = ["B_cottage", "B_well", "B_cart", "B_barrel", "B_washline", "B_lantern", "B_hen", "B_sunflower"]

# build_models.sh passes only the seed, so the roof kind is chosen per seed here.
COTTAGE_ROOF = {201: "tile", 203: "thatch"}


def _prism(name, prof, x0, x1, z0, sd, mat, n=6, sag=0.0, dents=0):
    """A hand-pressed prism: profile [(y, z)] swept along X from x0 to x1, sagged a little at its middle."""
    bm = bmesh.new()
    rings = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        s = -sag * math.sin(math.pi * i / n)
        rings.append([bm.verts.new((x, y, z0 + z + s)) for (y, z) in prof])
    m = len(prof)
    for i in range(n):
        for k in range(m):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % m], rings[i][(k + 1) % m]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    S.deform(bm, sd, 0.04, 1.8, dents, 0.2, 0.05)
    return S.to_obj(name, bm, mat)


def _gable(name, w, d, rh, z0, sd, mat="roof"):
    """A gable roof shell: ridge along X, eaves at y=+-d/2, thick clay, ridge sagged."""
    prof = [(-d / 2, 0.0), (0.0, rh), (d / 2, 0.0), (0.0, rh - 0.16)]
    return _prism(name, prof, -w / 2, w / 2, z0, sd, mat, n=8, sag=0.06, dents=6)


def _tri(name, d, rh, x0, x1, z0, sd, mat):
    """A gable-end infill panel: a triangle of wall clay standing under the roof at one end of the house."""
    prof = [(-d / 2 + 0.2, 0.0), (0.0, rh - 0.2), (d / 2 - 0.2, 0.0)]
    return _prism(name, prof, x0, x1, z0, sd, mat, n=2)


def _slope(s, t, x, D, H, z0, lift=0.0):
    """Point on a gable slope: side s (+-1), t 0 at the eave to 1 at the ridge, lifted off the surface."""
    L = math.hypot(D, H)
    return (x, s * D * (1 - t) + s * H / L * lift, z0 + H * t + D / L * lift)


def _tiles(prefix, w, D, H, z0, rows, per_row, sd):
    """Rows of overlapping thumbed tile blobs laid on both slopes, staggered row to row, with a ridge roll."""
    a = math.atan2(H, D)
    L = math.hypot(D, H)
    tw = w / per_row * 1.15
    tl = L / rows * 1.3
    parts = []
    for s in (-1, 1):
        for r in range(rows):
            t = (r + 0.5) / rows
            off = 0.5 if r % 2 else 0.0
            for i in range(per_row):
                x = (i + 0.5 + off) * w / per_row - w / 2
                parts.append(S.blob("%s_tile%d_%d_%d" % (prefix, s, r, i), (tw, tl, 0.06), _slope(s, t, x, D, H, z0, 0.03), "roof",
                                    sd + r * 31 + i + (s > 0) * 500, lump=0.01, subdiv=2, dents=1, dent_r=0.05, dent_d=0.015,
                                    rot=(-s * a, 0, 0)))
    parts.append(S.snake(prefix + "_ridge", [(-w / 2, 0, z0 + H + 0.02), (0, 0, z0 + H + 0.03), (w / 2, 0, z0 + H + 0.02)], 0.07, "roof",
                         sd + 7, sides=8, wobble=0.03, steps=2))
    return parts


def _thatch(prefix, w, D, H, z0, n, sd):
    """Straw laid down the slopes as many loose snakes, plus a fat rounded roll at each eave and the ridge."""
    rnd = random.Random(sd)
    parts = []
    for s in (-1, 1):
        for k in range(n):
            x = rnd.uniform(-w / 2 - 0.12, w / 2 + 0.12)
            t0 = rnd.uniform(0.0, 0.65)
            p0 = _slope(s, t0, x, D, H, z0, 0.03)
            p1 = _slope(s, min(1.0, t0 + rnd.uniform(0.25, 0.4)), x + rnd.uniform(-0.06, 0.06), D, H, z0, 0.04)
            parts.append(S.snake("%s_straw%d_%d" % (prefix, s, k), [p0, p1], 0.035, rnd.choice(["yellow", "orange"]),
                                 sd + k + (s > 0) * 500, sides=4, wobble=0.0, steps=1))
    xs = [-w / 2 - 0.2 + i * (w + 0.4) / 6 for i in range(7)]
    for s in (-1, 1):
        parts.append(S.snake("%s_eave%d" % (prefix, s), [(x, s * D * 0.98, z0 + 0.06) for x in xs], 0.12, "yellow", sd + 900 + s,
                             sides=8, wobble=0.04, steps=2))
    parts.append(S.snake(prefix + "_rollridge", [(x, 0, z0 + H + 0.03) for x in xs], 0.13, "yellow", sd + 910, sides=8, wobble=0.04, steps=2))
    return parts


def _wall(name, w, d, h, sd):
    """A hand-cut wall: tapers toward the top and leans a touch, lumped like pressed clay."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for v in bm.verts:
        u = v.co.z + 0.5
        f = 1 - 0.08 * u
        v.co = ((v.co.x * w) * f + 0.05 * u, (v.co.y * d) * f, u * h)
    S.deform(bm, sd, 0.03, 1.6, 6, 0.2, 0.04)
    return S.to_obj(name, bm, "plaster")


def _cottage_wx(x0, z, h):
    """x of a point x0 on the front wall at height z (wall taper and lean)."""
    u = z / h
    return x0 * (1 - 0.08 * u) + 0.05 * u


def _cottage(name, sd, roof):
    w, d, h = 2.3, 2.0, 1.7
    D = (d + 0.5) / 2
    H = 1.05
    z0 = h - 0.05
    zb = h * 0.55

    def fy(z):  # front face y at height z
        return (d / 2) * (1 - 0.08 * z / h) + 0.02

    def front(x0, z):
        return (_cottage_wx(x0, z, h), fy(z), z)

    def side(s, y0, z):
        u = z / h
        return (s * ((w / 2) * (1 - 0.08 * u) + 0.02) + 0.05 * u, y0 * (1 - 0.08 * u), z)

    parts = [_wall("c_walls", w, d, h, sd)]
    parts.append(_gable("c_base", w + 0.36, d + 0.5, H, z0, sd + 1, "roof" if roof == "tile" else "bark"))
    parts.append(_tri("c_gableL", d, H, -w / 2 - 0.01, -w / 2 + 0.12, h - 0.02, sd + 2, "plaster"))
    parts.append(_tri("c_gableR", d, H, w / 2 - 0.12, w / 2 + 0.01, h - 0.02, sd + 3, "plaster"))
    if roof == "tile":
        parts += _tiles("c_tile", w + 0.36, D, H, z0, 7, 11, sd + 10)
    else:
        parts += _thatch("c_thatch", w + 0.36, D, H, z0, 85, sd + 20)

    def timber(pts, r=0.035):
        parts.append(S.snake("c_timber%d" % len(parts), pts, r, "bark", sd + len(parts), sides=8, wobble=0.08, steps=3))

    # half-timber frame: corner posts, mid beam (broken for the door), two braces per wall
    for x0 in (-w / 2 + 0.04, w / 2 - 0.04):
        timber([front(x0, 0.0), front(x0, h * 0.5), front(x0, h - 0.02)])
    timber([front(-w / 2 + 0.04, zb), front(-0.3, zb)])
    timber([front(0.3, zb), front(w / 2 - 0.04, zb)])
    timber([front(-w / 2 + 0.04, 0.02), front(-w / 2 + 0.3, zb)])
    timber([front(w / 2 - 0.04, 0.02), front(w / 2 - 0.3, zb)])
    for s in (-1, 1):
        for y0 in (-d / 2 + 0.04, d / 2 - 0.04):
            timber([side(s, y0, 0.0), side(s, y0, h * 0.5), side(s, y0, h - 0.02)])
        timber([side(s, -d / 2 + 0.04, zb), side(s, d / 2 - 0.04, zb)])
        timber([side(s, -d / 2 + 0.04, 0.02), side(s, -0.45, zb)])
        timber([side(s, d / 2 - 0.04, 0.02), side(s, 0.45, zb)])

    # door: arched wood with a bark frame, plank grooves, brass knob, stone step
    yd = d / 2 + 0.03
    parts.append(S.blob("c_door", (0.6, 0.07, 1.1), (0, yd, 0.55), "wood", sd + 30, lump=0.01, subdiv=2))
    parts.append(S.blob("c_door_arch", (0.6, 0.07, 0.6), (0, yd, 1.1), "wood", sd + 31, lump=0.01, subdiv=2))
    for x in (-0.2, 0.0, 0.2):
        parts.append(S.snake("c_groove%d" % int(x * 10 + 5), [(x, yd + 0.035, 0.05), (x, yd + 0.035, 1.3)], 0.012, "bark", sd + 32, sides=6,
                             wobble=0.0, steps=2))
    arc = [(-0.33, fy(0), 0.0), (-0.33, fy(0), 1.1)]
    for i in range(1, 6):
        a = math.pi - math.pi * i / 6
        arc.append((0.33 * math.cos(a), fy(0), 1.1 + 0.33 * math.sin(a)))
    arc += [(0.33, fy(0), 1.1), (0.33, fy(0), 0.0)]
    timber(arc)
    parts.append(S.blob("c_knob", (0.07, 0.07, 0.07), (0.22, yd + 0.05, 0.6), "brass", sd + 33, lump=0.0, subdiv=2))
    parts.append(S.blob("c_step", (0.9, 0.4, 0.12), (0, d / 2 + 0.25, 0.06), "stone", sd + 34, lump=0.02, subdiv=2))

    def window(prefix, P, gsize, out, bsize, cu, cz, sd_w):
        """Glass with a bark frame, cross mullion and transom, and a flower box with blooms on the sill."""
        parts.append(S.blob(prefix + "_glass", gsize, P(0, cz), "window", sd_w, lump=0.0, subdiv=2))
        for pts in ([(-0.2, cz - 0.2), (-0.2, cz + 0.2)], [(-0.2, cz + 0.2), (0.2, cz + 0.2)],
                    [(0.2, cz + 0.2), (0.2, cz - 0.2)], [(0.2, cz - 0.2), (-0.2, cz - 0.2)],
                    [(0, cz - 0.2), (0, cz + 0.2)], [(-0.2, cz), (0.2, cz)]):
            parts.append(S.snake("%s_bar%d" % (prefix, len(parts)), [P(u, z) for u, z in pts], 0.022, "bark", sd_w + len(parts),
                                 sides=6, wobble=0.0, steps=1))
        box = (P(0, cz - 0.27)[0] + out[0], P(0, cz - 0.27)[1] + out[1], cz - 0.27)
        parts.append(S.blob(prefix + "_box", bsize, box, "wood", sd_w + 1, lump=0.01, subdiv=2))
        for k, u in enumerate((-0.2, -0.1, 0.0, 0.1, 0.2)):
            p = P(u, cz - 0.2)
            parts.append(S.blob("%s_bloom%d" % (prefix, k), (0.08, 0.08, 0.08), (p[0] + out[0], p[1] + out[1], p[2] + 0.04),
                                "pink" if k % 2 else "red", sd_w + 10 + k, lump=0.01, subdiv=2))

    for k, cu in enumerate((-0.66, 0.66)):
        window("c_fwin%d" % k, lambda u, z, cu=cu: front(cu + u, z), (0.36, 0.06, 0.36), (0, 0.12), (0.5, 0.14, 0.1), cu, 1.2, sd + 40 + k * 20)
    window("c_swin", lambda u, z: side(1, u, z), (0.06, 0.36, 0.36), (0.12, 0), (0.14, 0.5, 0.1), 0, 1.2, sd + 60)

    # chimney: stacked stones, an orange pot, three cloud puffs rising from it
    cx, cy = 0.62, -0.2
    for k in range(6):
        parts.append(S.blob("c_stone%d" % k, (0.34, 0.3, 0.22), (cx + (0.02 if k % 2 else -0.02), cy, 1.5 + k * 0.19), "stone", sd + 70 + k,
                            lump=0.02, subdiv=2, dents=1))
    parts.append(S.blob("c_pot", (0.28, 0.28, 0.2), (cx, cy, 2.66), "orange", sd + 80, lump=0.02, subdiv=2))
    for k, (dx, dy, z, r) in enumerate(((0.0, 0.05, 2.9, 0.24), (0.1, 0.0, 3.15, 0.2), (-0.02, -0.05, 3.38, 0.16))):
        parts.append(S.blob("c_puff%d" % k, (r, r, r * 0.9), (cx + dx, cy + dy, z), "cloud", sd + 85 + k, lump=0.03, subdiv=2))
    kit.join("cottage", parts).name = name


def B_cottage(seed="201"):
    sd = int(seed)
    _cottage("cottage", sd, COTTAGE_ROOF.get(sd, "tile"))


def B_well():
    parts = []
    for c, z in enumerate((0.09, 0.27, 0.45, 0.63)):
        off = 0.5 if c % 2 else 0.0
        for k in range(12):
            a = (k + off) * 2 * math.pi / 12
            parts.append(S.blob("w_stone%d_%d" % (c, k), (0.35, 0.25, 0.18), (0.6 * math.cos(a), 0.6 * math.sin(a), z), "stone", 300 + c * 20 + k,
                                lump=0.04, subdiv=2, dents=1, dent_r=0.07, dent_d=0.02, rot=(0, 0, a + math.pi / 2)))
    for k in range(8):
        a = k * 2 * math.pi / 8
        parts.append(S.blob("w_moss%d" % k, (0.2, 0.2, 0.07), (0.6 * math.cos(a), 0.6 * math.sin(a), 0.76), "moss", 340 + k, lump=0.03, subdiv=2,
                            rot=(0, 0, a)))
    parts.append(S.blob("w_water", (0.8, 0.8, 0.05), (0, 0, 0.5), "blue", 350, lump=0.01, subdiv=2))
    for s in (-1, 1):
        parts.append(S.snake("w_post%d" % s, [(s * 0.6, 0, 0.72), (s * 0.6, 0, 1.2), (s * 0.6, 0, 1.75)], 0.05, "wood", 330 + s, sides=6,
                             wobble=0.04, steps=2))
    parts.append(S.snake("w_bar", [(-0.7, 0, 1.75), (0, 0, 1.78), (0.7, 0, 1.75)], 0.05, "wood", 335, sides=6, wobble=0.03, steps=2))
    parts.append(S.snake("w_rope", [(0, 0, 1.75), (0.0, 0.01, 1.4), (0, 0, 1.06)], 0.012, "wire", 340, sides=6, wobble=0.0, steps=2))
    parts.append(S.blob("w_bucket", (0.2, 0.2, 0.16), (0, 0, 1.0), "wood", 345, lump=0.02, subdiv=2, dents=1))
    parts += _tiles("w_tile", 1.7, 0.6, 0.35, 1.8, 4, 6, 380)
    parts.append(_gable("w_base", 1.7, 1.2, 0.35, 1.8, 390, "roof"))
    kit.join("well", parts).name = "well"


def B_cart():
    parts = [S.slab("cart_floor", (1.1, 2.0, 0.08), (0, 0, 0.6), "wood", 370, lump=0.01, bevel=0.02, cuts=4)]
    for s in (-1, 1):
        parts.append(S.slab("cart_side%d" % s, (0.06, 2.0, 0.3), (s * 0.52, 0, 0.79), "wood", 371 + s, lump=0.01, bevel=0.02, cuts=4))
    for s in (-1, 1):
        parts.append(S.slab("cart_end%d" % s, (1.1, 0.06, 0.3), (0, s * 0.98, 0.79), "wood", 373 + s, lump=0.01, bevel=0.02, cuts=4))
    rnd = random.Random(375)
    for k in range(70):  # the hay heaped above the boards
        x, y = rnd.uniform(-0.5, 0.5), rnd.uniform(-0.9, 0.9)
        z = 0.95 + rnd.uniform(0.0, 0.15)
        p1 = (x + rnd.uniform(-0.12, 0.12), y + rnd.uniform(-0.12, 0.12), z + rnd.uniform(0.1, 0.3))
        parts.append(S.snake("cart_straw%d" % k, [(x, y, z), p1], 0.03, "yellow", 400 + k, sides=4, wobble=0.0, steps=1))
    parts.append(S.blob("cart_heap", (1.0, 1.8, 0.5), (0, 0, 1.0), "yellow", 376, lump=0.06, subdiv=3, dents=2))
    for s in (-1, 1):
        x = s * 0.6
        parts.append(kit.torus("cart_rim%d" % s, 0.46, 0.07, seg=32, rseg=8, mat="wood", loc=(x, 0, 0.53), rot=(0, math.pi / 2, 0)))
        parts.append(S.blob("cart_hub%d" % s, (0.16, 0.16, 0.16), (x, 0, 0.53), "wood", 380 + s, lump=0.01, subdiv=2))
        for k in range(8):
            a = k * math.pi / 4
            parts.append(S.snake("cart_spoke%d_%d" % (s, k), [(x, 0.1 * math.cos(a), 0.53 + 0.1 * math.sin(a)),
                                                            (x, 0.44 * math.cos(a), 0.53 + 0.44 * math.sin(a))],
                                 0.025, "wood", 385 + k, sides=6, wobble=0.0, steps=1))
        parts.append(S.snake("cart_shaft%d" % s, [(s * 0.3, 1.0, 0.62), (s * 0.3, 1.6, 0.5), (s * 0.3, 2.2, 0.45)], 0.04, "wood",
                             390 + s, sides=6, wobble=0.03, steps=2))
    for k, (px, py, pz) in enumerate(((-0.2, -0.4, 1.2), (0.25, 0.3, 1.22))):
        parts.append(S.blob("cart_pumpkin%d" % k, (0.36, 0.36, 0.28), (px, py, pz), "orange", 395 + k, lump=0.03, subdiv=3, dents=3))
        for g, ang in enumerate((0.0, math.pi / 3, 2 * math.pi / 3)):  # three grooves down the pumpkin
            pts = []
            for z in (-0.12, -0.06, 0.0, 0.06, 0.12):
                r = 0.18 * math.sqrt(max(0.0, 1 - (z / 0.14) ** 2)) + 0.012
                pts.append((px + r * math.cos(ang), py + r * math.sin(ang), pz + z))
            parts.append(S.snake("cart_groove%d_%d" % (k, g), pts, 0.012, "bark", 398 + g, sides=4, wobble=0.0, steps=1))
        parts.append(S.snake("cart_stalk%d" % k, [(px, py, pz + 0.14), (px + 0.02, py, pz + 0.22)], 0.02, "bark", 401 + k, sides=4, wobble=0.0, steps=1))
    kit.join("cart", parts).name = "cart"


def B_barrel():
    parts = [S.lathe("barrel_body", [(0.24, 0.02), (0.3, 0.25), (0.34, 0.5), (0.3, 0.75), (0.24, 0.98)], "wood", 400,
                     segments=24, lump=0.02, scale=1.2, cap=True, dents=2)]
    for z, r in ((0.2, 0.29), (0.5, 0.34), (0.8, 0.29)):
        parts.append(kit.torus("barrel_hoop%d" % int(z * 10), r, 0.03, seg=24, rseg=6, mat="steel", loc=(0, 0, z)))
    kit.join("barrel", parts).name = "barrel"


def B_washline():
    parts = []
    for s in (-1, 1):
        parts.append(S.snake("wl_post%d" % s, [(s * 1.4, 0, 0.0), (s * 1.4, 0, 0.8), (s * 1.4, 0, 1.6)], 0.05, "wood", 410 + s,
                             sides=6, wobble=0.03, steps=2))
    parts.append(S.snake("wl_line", [(-1.4, 0, 1.5), (0, 0, 1.25), (1.4, 0, 1.5)], 0.012, "wire", 415, sides=6, wobble=0.0, steps=3))
    cloth = [("pink", -0.95, 0.42), ("blue", -0.35, 0.36), ("cloud", 0.3, 0.46), ("yellow", 0.95, 0.38)]
    for k, (mat, x, wdt) in enumerate(cloth):
        zline = 1.25 + 0.25 * (x / 1.4) ** 2
        parts.append(S.slab("wl_cloth%d" % k, (wdt, 0.04, 0.5), (x, 0, zline - 0.3), mat, 420 + k, lump=0.02, bevel=0.02, cuts=4, dents=1))
    kit.join("washline", parts).name = "washline"


def B_lantern():
    parts = [S.snake("lt_post", [(0, 0, 0.0), (0, 0, 0.9), (0, 0, 1.8)], 0.05, "wood", 430, sides=6, wobble=0.03, steps=3)]
    parts.append(S.blob("lt_base", (0.4, 0.4, 0.14), (0, 0, 0.1), "wood", 431, lump=0.02, subdiv=2, dents=1))
    parts.append(S.blob("lt_glass", (0.32, 0.32, 0.36), (0, 0, 1.92), "window", 432, lump=0.0, subdiv=3))
    parts.append(S.blob("lt_bulb", (0.2, 0.2, 0.22), (0, 0, 1.92), "bulb", 433, lump=0.01, subdiv=3))
    parts.append(kit.torus("lt_ring_top", 0.17, 0.025, seg=20, rseg=6, mat="brass", loc=(0, 0, 2.12)))
    parts.append(kit.torus("lt_ring_bot", 0.17, 0.025, seg=20, rseg=6, mat="brass", loc=(0, 0, 1.72)))
    parts.append(S.blob("lt_cap", (0.5, 0.5, 0.2), (0, 0, 2.2), "roof", 434, lump=0.02, subdiv=3, dents=1))
    parts.append(S.snake("lt_hook", [(0, 0, 2.27), (0, 0, 2.38), (0.0, 0.0, 2.46)], 0.02, "brass", 435, sides=6, wobble=0.0, steps=2))
    kit.join("lantern", parts).name = "lantern"


def B_hen():
    parts = [S.blob("hen_body", (0.5, 0.38, 0.42), (0, 0, 0.42), "cloud", 500, lump=0.03, subdiv=3, dents=2)]
    parts.append(S.blob("hen_tail", (0.3, 0.22, 0.4), (0, -0.28, 0.52), "cloud", 501, lump=0.03, subdiv=2, rot=(0.5, 0, 0)))
    parts.append(S.blob("hen_head", (0.22, 0.22, 0.22), (0, 0.22, 0.74), "cloud", 502, lump=0.02, subdiv=3))
    parts.append(S.blob("hen_comb", (0.08, 0.14, 0.08), (0, 0.22, 0.92), "red", 503, lump=0.0, subdiv=2))
    parts.append(S.blob("hen_wattle", (0.05, 0.05, 0.09), (0, 0.32, 0.62), "red", 504, lump=0.0, subdiv=2))
    parts.append(S.blob("hen_beak", (0.07, 0.12, 0.06), (0, 0.36, 0.72), "orange", 505, lump=0.0, subdiv=2))
    for s in (-1, 1):
        parts.append(S.blob("hen_eye%d" % s, (0.035, 0.035, 0.035), (s * 0.1, 0.32, 0.77), "ink", 510 + s, lump=0.0, subdiv=1))
        parts.append(S.blob("hen_wing%d" % s, (0.06, 0.3, 0.26), (s * 0.25, 0.0, 0.46), "cloud", 520 + s, lump=0.02, subdiv=2, rot=(0, 0, s * 0.15)))
        parts.append(S.snake("hen_leg%d" % s, [(s * 0.1, 0.0, 0.22), (s * 0.1, 0.02, 0.1), (s * 0.12, 0.04, 0.0)], 0.02, "orange", 530 + s,
                             sides=6, wobble=0.0, steps=2))
    kit.join("hen", parts).name = "hen"


def B_sunflower():
    sd = 601
    parts = [S.snake("sf_stem", [(0, 0, 0.0), (0.02, 0, 0.7), (0.0, 0.05, 1.35)], 0.035, "leaf", sd, sides=6, wobble=0.04, steps=3)]
    for s, z, tilt in ((-1, 0.45, 0.6), (1, 0.8, 0.6)):
        parts.append(S.blob("sf_leaf%d" % s, (0.16, 0.05, 0.34), (s * 0.18, 0.0, z), "leaf", sd + 10 + s,
                            lump=0.02, subdiv=2, rot=(0, s * tilt, 0)))
    parts.append(S.blob("sf_disc", (0.5, 0.1, 0.5), (0, 0.12, 1.45), "bark", sd + 1, lump=0.02, subdiv=3, dents=3, dent_r=0.1, dent_d=0.03))
    for k in range(12):
        a = k * 2 * math.pi / 12
        parts.append(S.blob("sf_petal%d" % k, (0.1, 0.05, 0.2), (0.36 * math.cos(a), 0.12, 1.45 + 0.36 * math.sin(a)), "yellow", sd + 20 + k,
                            lump=0.01, subdiv=2, rot=(0, math.pi / 2 - a, 0)))
    kit.join("sunflower", parts).name = "sunflower"
