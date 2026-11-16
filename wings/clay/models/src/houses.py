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
    from mathutils import Matrix, Vector
    L, sag, zend = 1.447, 0.25, 1.5  # line ends at the leaning posts; sag below the ends
    lo, hi = 0.5, 60.0  # catenary parameter k: k*(cosh(L/k)-1) = sag
    for _ in range(60):
        kc = (lo + hi) / 2
        if kc * (math.cosh(L / kc) - 1) - sag > 0:
            lo = kc
        else:
            hi = kc
    kc = (lo + hi) / 2
    zmid = zend - sag

    def zl(x):
        return zmid + kc * (math.cosh(x / kc) - 1)

    def W(x0, beta, dx, dy, dz):
        """A point on an item hung at x0: offset (dx, dy, dz) turned by the breeze angle beta about the line."""
        return Vector((x0, 0, zl(x0))) + Matrix.Rotation(beta, 3, "X") @ Vector((dx, dy, dz))

    parts = []
    for s in (-1, 1):
        px = s * (1.4 + 0.05)  # posts lean out a touch
        parts.append(S.snake("wl_post%d" % s, [(s * 1.4, 0, 0.04), (s * 1.42, 0, 0.8), (px, 0, 1.6)], 0.045, "wood", 410 + s,
                             sides=6, wobble=0.03, steps=2))
        parts.append(S.snake("wl_bar%d" % s, [(px - 0.24, 0, 1.62), (px, 0, 1.63), (px + 0.24, 0, 1.62)], 0.03, "wood", 412 + s,
                             sides=6, wobble=0.0, steps=1))
        parts.append(S.blob("wl_foot%d" % s, (0.34, 0.3, 0.12), (s * 1.4, 0, 0.06), "ground", 414 + s, lump=0.03, subdiv=2, dents=1,
                            dent_r=0.1, dent_d=0.02))
    line = [(x, 0, zl(x)) for x in [-L + 2 * L * i / 12 for i in range(13)]]
    parts.append(S.snake("wl_line", line, 0.012, "wire", 415, sides=6, wobble=0.0, steps=3))

    def peg(x0, beta, dx):
        parts.append(S.blob("wl_peg%d" % len(parts), (0.026, 0.034, 0.1), W(x0, beta, dx, 0, 0), "wood", 440 + len(parts), lump=0.005,
                            subdiv=2, rot=(beta, 0, 0)))

    def cloth(name, x0, beta, w_top, w_bot, h, amp, folds, mat, seed, hem):
        """A hung sheet: pleated by a sine across its width, a little thick, with a hem snake along the bottom."""
        def yfun(u, v):
            return amp * math.sin(math.pi * folds * (u + 1) / 2) * (1 - 0.25 * v)

        bm = bmesh.new()
        nx, nz = 10, 8
        us = [-1 + 2 * i / nx for i in range(nx + 1)]
        grid = []
        for j in range(nz + 1):
            v = j / nz
            hw = (w_top + (w_bot - w_top) * v) / 2
            grid.append([bm.verts.new((u * hw, yfun(u, v), -0.01 - h * v)) for u in us])
        for j in range(nz):
            for i in range(nx):
                bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.012)
        M = Matrix.Translation(Vector((x0, 0, zl(x0)))) @ Matrix.Rotation(beta, 4, "X")
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        S.deform(bm, seed, 0.01, 2.5, 2, 0.1, 0.012)
        parts.append(S.to_obj(name, bm, mat))
        parts.append(S.snake(name + "_hem", [W(x0, beta, u * w_bot / 2, yfun(u, 1), -0.01 - h) for u in us], 0.012, hem, seed + 1,
                             sides=6, wobble=0.0, steps=2))

    # shirt: body, two sleeves splayed down, collar, three buttons, pegs at the shoulders
    b, x0 = 0.10, -0.85
    parts.append(S.slab("wl_shirt", (0.36, 0.03, 0.46), W(x0, b, 0, 0, -0.25), "blue", 450, lump=0.012, bevel=0.01, cuts=4, dents=1,
                        rot=(b, 0, 0)))
    for s in (-1, 1):
        parts.append(S.slab("wl_sleeve%d" % s, (0.09, 0.03, 0.36), W(x0, b, s * 0.22, 0, -0.22), "blue", 452 + s, lump=0.012, bevel=0.01,
                            cuts=4, rot=(b, -s * 0.25, 0)))
    parts.append(S.snake("wl_collar", [W(x0, b, -0.1, 0.02, -0.03), W(x0, b, 0, 0.035, -0.05), W(x0, b, 0.1, 0.02, -0.03)], 0.014,
                         "ivory", 455, sides=6, wobble=0.0, steps=2))
    for k in range(3):
        parts.append(S.blob("wl_btn%d" % k, (0.022, 0.02, 0.022), W(x0, b, 0, 0.02, -0.12 - 0.09 * k), "ivory", 456 + k, lump=0.0, subdiv=2))
    peg(x0, b, -0.09)
    peg(x0, b, 0.09)

    # a pair of long socks, folded over the line
    b, x0 = -0.06, -0.35
    for s in (-1, 1):
        dx = s * 0.07
        pts = [W(x0, b, dx, 0.0, -0.01), W(x0, b, dx, 0.0, -0.12), W(x0, b, dx, 0.0, -0.3), W(x0, b, dx, 0.03, -0.36),
               W(x0, b, dx, 0.1, -0.38)]
        parts.append(S.snake("wl_sock%d" % s, pts, 0.03, "orange", 460 + s, sides=8, wobble=0.0, steps=2))
        peg(x0, b, dx)

    # sheet with soft pleats and a pink hem; small red dress with a yellow belt
    cloth("wl_sheet", 0.2, 0.04, 0.7, 0.66, 0.8, 0.025, 3, "cloud", 470, "pink")
    peg(0.2, 0.04, -0.2)
    peg(0.2, 0.04, 0.2)
    cloth("wl_dress", 0.92, -0.09, 0.26, 0.46, 0.5, 0.03, 2, "red", 480, "yellow")
    parts.append(S.snake("wl_belt", [W(0.92, -0.09, dx, 0.03, -0.2) for dx in (-0.13, 0.0, 0.13)], 0.014, "yellow", 485, sides=6,
                         wobble=0.0, steps=2))
    peg(0.92, -0.09, -0.08)
    peg(0.92, -0.09, 0.08)

    # wicker basket on the ground under the left end, with a folded cloth in it
    bx, by = -1.12, 0.3
    basket = S.lathe("wl_basket", [(0.14, 0.0), (0.17, 0.04), (0.2, 0.12), (0.22, 0.2), (0.24, 0.27), (0.25, 0.3), (0.235, 0.31),
                                   (0.215, 0.29), (0.195, 0.2), (0.17, 0.1), (0.12, 0.03)], "wood", 490, segments=24, lump=0.012,
                     scale=1.5, cap=True)
    basket.location = (bx, by, 0)
    parts.append(basket)
    for z, r in ((0.1, 0.185), (0.18, 0.215), (0.26, 0.245)):
        parts.append(kit.torus("wl_band%d" % int(z * 100), r, 0.014, seg=24, rseg=6, mat="bark", loc=(bx, by, z)))
    parts.append(S.slab("wl_bcloth", (0.28, 0.2, 0.06), (bx, by, 0.24), "pink", 495, lump=0.01, bevel=0.02, cuts=4, rot=(0, 0, 0.2)))
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
    from mathutils import Matrix, Vector
    tilt, sx = -0.35, 0.8  # body axis tipped so the back (-Y) rides up into the tail
    M = Matrix.Translation(Vector((0, 0, 0.44))) @ Matrix.Rotation(tilt, 4, "X")
    R3 = Matrix.Rotation(tilt, 3, "X")
    prof = [(-0.36, 0.10), (-0.31, 0.17), (-0.22, 0.215), (-0.10, 0.24), (0.02, 0.245), (0.13, 0.225), (0.22, 0.18), (0.28, 0.12),
            (0.32, 0.06)]  # (position along Y, radius): plump low breast at +Y, narrowing to the tail at -Y

    def r_at(t):
        for (t0, r0), (t1, r1) in zip(prof, prof[1:]):
            if t0 <= t <= t1:
                return r0 + (r1 - r0) * (t - t0) / (t1 - t0)
        return prof[-1][1]

    def body_pt(t, a, lift=0.0):
        """World point on the body at axis position t, angle a (pi/2 = top), pushed out along the normal by lift."""
        n = R3 @ Vector((math.cos(a), 0, math.sin(a)))
        r = r_at(t)
        p = M @ Vector((sx * r * math.cos(a), t, r * math.sin(a), 1.0))
        return Vector((p.x, p.y, p.z)) + n * lift, n

    # body: a revolved egg, squeezed a little across, then hand-lumped and thumb-dented
    bm = bmesh.new()
    N = 36
    rings = []
    for t, r in prof:
        rings.append([bm.verts.new((sx * r * math.cos(2 * math.pi * i / N), t, r * math.sin(2 * math.pi * i / N))) for i in range(N)])
    for j in range(len(prof) - 1):
        for i in range(N):
            bm.faces.new((rings[j][i], rings[j + 1][i], rings[j + 1][(i + 1) % N], rings[j][(i + 1) % N]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    S.deform(bm, 500, 0.03, 1.8, 2, 0.16, 0.03)
    body = S.to_obj("hen_body", bm, "cloud")
    S.scatter_dents(body, 501, 5, r=0.12, d=0.02)
    parts = [body]

    # clay thumb-pressed darker spots on the back
    for t, a in ((-0.26, 1.2), (-0.26, 1.95), (-0.14, 1.55), (-0.02, 1.0), (-0.02, 2.1), (0.08, 1.5)):
        p, _ = body_pt(t, a, 0.012)
        parts.append(S.blob("hen_spot%d" % len(parts), (0.04, 0.09, 0.07), p, "clay", 540 + len(parts), lump=0.01, subdiv=2, rot=(0, -a, 0)))

    # folded wings: three overlapping rows of scalloped feathers per side, top tips crossing over the back
    for s in (-1, 1):
        for row, a0 in enumerate((0.3, 0.75, 1.2)):
            for i in range(5):
                a = a0
                if row == 2 and i >= 3:
                    a = 1.5 if i == 3 else 1.8
                if s < 0:
                    a = math.pi - a
                t = 0.12 - 0.11 * i
                p, _ = body_pt(t, a, 0.02)
                mat = "clay" if (row, i) in ((1, 1), (1, 3), (2, 2)) else "cloud"
                parts.append(S.blob("hen_wing%d" % len(parts), (0.035, 0.13, 0.12), p, mat, 600 + len(parts), lump=0.02, subdiv=2,
                                    rot=(0, -a, 0)))

    # tail: seven curved feathers fanning up and back, two darker
    for k in range(7):
        x = -0.18 + 0.06 * k
        tz = 0.9 - 0.5 * abs(x)
        pts = [(x * 0.5, -0.27, 0.55), (x, -0.5, 0.55 + (tz - 0.55) * 0.6), (x * 1.6, -0.68, tz)]
        parts.append(S.snake("hen_tail%d" % k, pts, 0.035, "clay" if k in (1, 5) else "cloud", 620 + k, sides=8, wobble=0.05,
                             taper=(1.0, 0.3), steps=3))

    # neck ruff: eight hackle feathers around the neck, falling onto the shoulders
    for k in range(8):
        th = -1.15 + 2.3 * k / 7
        pts = [(0.09 * math.sin(th), 0.17 + 0.09 * math.cos(th), 0.7), (0.14 * math.sin(th), 0.2 + 0.11 * math.cos(th), 0.55),
               (0.2 * math.sin(th), 0.24 + 0.12 * math.cos(th), 0.4)]
        parts.append(S.snake("hen_hackle%d" % k, pts, 0.035, "cloud", 650 + k, sides=6, wobble=0.05, taper=(1.0, 0.25), steps=2))
    parts.append(S.snake("hen_neck", [(0, 0.08, 0.5), (0, 0.18, 0.66), (0, 0.26, 0.8)], 0.085, "cloud", 660, sides=10, wobble=0.04,
                         taper=(1.0, 0.85), steps=3))

    # head, serrated comb, hanging wattles, hooked beak, eyes with a glint
    parts.append(S.blob("hen_head", (0.16, 0.2, 0.17), (0, 0.27, 0.84), "cloud", 661, lump=0.015, subdiv=3))
    parts.append(S.snake("hen_comb_strip", [(0, 0.19, 0.915), (0, 0.33, 0.915)], 0.018, "red", 662, sides=6, wobble=0.0, steps=2))
    for k, y in enumerate((0.19, 0.225, 0.26, 0.295, 0.33)):
        parts.append(S.blob("hen_comb%d" % k, (0.03, 0.04, 0.045), (0, y, 0.915 + 0.008 * (2 - abs(k - 2))), "red", 663 + k, lump=0.0,
                            subdiv=2))
    for s in (-1, 1):
        parts.append(S.blob("hen_wattle%d" % s, (0.03, 0.035, 0.1), (s * 0.03, 0.33, 0.73), "red", 670 + s, lump=0.0, subdiv=2))
        parts.append(S.blob("hen_eye%d" % s, (0.034, 0.03, 0.034), (s * 0.075, 0.3, 0.87), "ink", 673 + (s > 0), lump=0.0, subdiv=2))
        parts.append(S.blob("hen_glint%d" % s, (0.016, 0.016, 0.016), (s * 0.085, 0.315, 0.885), "ivory", 675 + (s > 0), lump=0.0,
                            subdiv=2))
    parts.append(S.snake("hen_beak", [(0, 0.34, 0.86), (0, 0.42, 0.85), (0, 0.46, 0.83), (0, 0.44, 0.8)], 0.032, "orange", 677,
                         sides=6, wobble=0.0, taper=(1.0, 0.45), steps=2))

    # scaled legs: thin rings, three forward toes and a back toe each, spread on the ground
    for s in (-1, 1):
        x = s * 0.1
        parts.append(S.snake("hen_leg%d" % s, [(x, 0.0, 0.26), (x, 0.0, 0.14), (x, 0.0, 0.05)], 0.02, "orange", 680 + (s > 0), sides=8,
                             wobble=0.0, steps=2))
        for z in (0.19, 0.14, 0.09):
            parts.append(kit.torus("hen_ring%d_%d" % (s, int(z * 100)), 0.028, 0.008, seg=12, rseg=4, mat="orange", loc=(x, 0.0, z)))
        for j, (a, ln) in enumerate(((-0.45, 0.11), (0.0, 0.12), (0.45, 0.11))):
            parts.append(S.snake("hen_toe%d_%d" % (s, j), [(x, 0.0, 0.035), (x + math.sin(a) * ln * 0.5, math.cos(a) * ln * 0.5, 0.016),
                                                          (x + math.sin(a) * ln, math.cos(a) * ln, 0.012)], 0.012, "orange", 690 + 3 * s + j,
                                 sides=6, wobble=0.0, taper=(1.0, 0.7), steps=2))
        parts.append(S.snake("hen_back%d" % s, [(x, 0.0, 0.035), (x, -0.04, 0.016), (x, -0.08, 0.012)], 0.011, "orange", 700 + (s > 0),
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
