"""Provenance relics: 18 separate collectible objects, one per provenance row. Each object is named
relic_<wing>_<id>, sits on the vitrine floor with its base centre at the origin on z=0, and is
built from baked mesh-space parts (no object transforms) so every joined object is clean.
Flat items (panel, ticket, card) stand on small brass stands. `relic_tint` marks the one coloured
part of each object; Godot tints it with the wing colour."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402
import kit  # noqa: E402
import orn  # noqa: E402

R = math.radians


# ---- helpers: every part is baked into mesh space, so all objects keep identity transforms ----

def xf(ob, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1)):
    """Scale, then rotate (Euler XYZ, radians), then move, applied to the mesh data."""
    M = Matrix.Translation(loc) @ Euler(rot, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal(Vector(scale).to_4d())
    ob.data.transform(M)
    return ob


def bake(ob):
    """Apply an object's own loc/rot/scale (set by kit.place) into its mesh."""
    ob.data.transform(ob.matrix_basis)
    ob.location = (0, 0, 0)
    ob.rotation_euler = (0, 0, 0)
    ob.scale = (1, 1, 1)
    return ob


def B(name, size, loc=(0, 0, 0), mat="plaster", bevel=0.0, seg=1):
    return kit.box(name, size, loc, mat=mat, bevel=bevel, segments=seg)


def L(name, prof, mat, seg=16, cap=True, z=0.0):
    return xf(kit.lathe(name, prof, seg, mat=mat, cap=cap), loc=(0, 0, z))


def T(name, pts, r, mat, sides=6):
    return kit.tube(name, pts, r, sides, mat=mat)


def TP(name, pts, radii, mat, sides=8, flat=1.0):
    return orn.taper(name, pts, radii, sides, mat, flat=flat)


def E(name, loc, size, mat, seg=10, rings=5):
    return bake(orn.ellipsoid(name, loc, size, mat, seg, rings))


def RING(name, major, minor, mat, seg=28, rseg=5, rot=(0, 0, 0), loc=(0, 0, 0), scale=(1, 1, 1)):
    return xf(kit.torus(name, major, minor, seg, rseg, mat=mat), rot=rot, loc=loc, scale=scale)


def finish(name, parts):
    """Join parts into one object named `name` and put its base centre at the origin on z=0."""
    ob = kit.join(name, parts)
    me = ob.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    me.transform(Matrix.Translation(-off))
    ob.location = (0, 0, 0)
    return ob


# ---- the 18 relics ----

def glass_face():
    """The face of St. Lumen, leaded out: a glass panel with an arched top, lead came, halo, brass stand."""
    p = []
    p.append(B("panel", (0.18, 0.008, 0.16), (0, 0, 0.13), "relic_tint", bevel=0.001))
    p.append(E("archtop", (0, -0.004, 0.2), (0.09, 0.004, 0.07), "relic_tint", 20, 8))
    p.append(E("face", (0, -0.004, 0.15), (0.09, 0.008, 0.11), "relic_tint", 12, 6))
    p.append(RING("facecame", 0.05, 0.0026, "brass", seg=32, rseg=5, rot=(R(90), 0, 0), loc=(0, -0.006, 0.15), scale=(1, 1.2, 1)))
    p.append(RING("halo", 0.075, 0.0045, "brass", seg=40, rseg=6, rot=(R(90), 0, 0), loc=(0, -0.002, 0.15)))
    for s in (-1, 1):
        p.append(T("eye%d" % s, [(s * 0.026, -0.011, 0.162), (s * 0.018, -0.012, 0.166), (s * 0.01, -0.011, 0.162)], 0.0016, "ebony", 4))
    p.append(T("mouth", [(-0.012, -0.011, 0.125), (0, -0.012, 0.122), (0.012, -0.011, 0.125)], 0.0014, "ebony", 4))
    p.append(B("lead_h1", (0.18, 0.004, 0.004), (0, -0.006, 0.09), "brass"))
    p.append(B("lead_h2", (0.18, 0.004, 0.004), (0, -0.006, 0.2), "brass"))
    for x in (-0.05, 0.05):
        p.append(B("lead_v%d" % int(x * 100), (0.004, 0.004, 0.16), (x, -0.006, 0.13), "brass"))
    p.append(B("plate", (0.22, 0.05, 0.006), (0, 0, 0.003), "brass", bevel=0.001))
    p.append(B("sill", (0.18, 0.012, 0.008), (0, -0.002, 0.046), "brass"))
    for s in (-1, 1):
        p.append(T("upright%d" % s, [(s * 0.085, 0, 0.006), (s * 0.085, 0, 0.046)], 0.0035, "brass", 6))
    return finish("relic_glass_face", p)


def glass_veil():
    """A thread of the Widow's veil: brass-capped glass capsule holding a coiled relic_tint thread."""
    p = []
    p.append(L("pedestal", [(0, 0), (0.05, 0), (0.05, 0.008), (0.036, 0.012), (0.03, 0.02), (0, 0.02)], "brass", 20))
    p.append(L("capsule", [(0, 0.02), (0.03, 0.02), (0.036, 0.03), (0.04, 0.05), (0.04, 0.11), (0.036, 0.13),
                           (0.03, 0.14), (0, 0.148)], "glass", 20))
    p.append(L("collar_lo", [(0.034, 0.02), (0.044, 0.02), (0.044, 0.032), (0.034, 0.032)], "brass", 20))
    p.append(L("collar_hi", [(0.036, 0.122), (0.044, 0.122), (0.044, 0.136), (0.036, 0.136)], "brass", 20))
    p.append(L("knob", [(0, 0.148), (0.012, 0.15), (0.014, 0.158), (0.008, 0.166), (0, 0.166)], "brass", 12))
    pts = []
    n = 72
    for i in range(n + 1):
        a = i * 2 * math.pi / 12
        pts.append((0.016 * math.cos(a), 0.016 * math.sin(a), 0.03 + 0.055 * i / n))
    p.append(T("thread", pts, 0.0011, "relic_tint", 4))
    return finish("relic_glass_veil", p)


def glass_iron():
    """A glazier's grozing iron: notched flat jaws, brass pivot and a worn ebony handle, lying flat."""
    p = []
    p.append(TP("grip", [(x, 0, 0.012) for x in (-0.13, -0.12, -0.10, -0.08, -0.05, -0.03, -0.02)],
                [0.006, 0.0095, 0.011, 0.0105, 0.009, 0.008, 0.008], "ebony", 10))
    ferrule = L("ferrule", [(0, 0), (0.0105, 0), (0.0105, 0.012), (0, 0.012)], "brass", 14)
    p.append(xf(ferrule, rot=(0, R(90), 0), loc=(-0.02, 0, 0.012)))
    for s, a in ((1, 7), (-1, -7)):
        blade = B("blade", (0.11, 0.012, 0.004), (0.065, 0, 0.012), "brass")
        xf(blade, rot=(0, 0, R(a)))
        p.append(blade)
        for i in range(3):
            t = B("tooth", (0.008, 0.004, 0.006), (0.09 + 0.012 * i, -s * 0.006, 0.012), "brass")
            p.append(xf(t, rot=(0, 0, R(a))))
    p.append(L("rivet", [(0, 0), (0.004, 0), (0.004, 0.008), (0, 0.008)], "brass", 10, z=0.008))
    return finish("relic_glass_iron", p)


def clay_thumb():
    """A thumbprint, larger than a hand: a plasticine slab with concentric oval whorl ridges."""
    p = [B("slab", (0.2, 0.16, 0.035), (0, 0, 0.0175), "relic_tint", bevel=0.008, seg=2)]
    for k, r in enumerate((0.07, 0.057, 0.044, 0.031, 0.018)):
        p.append(RING("whorl%d" % k, r, 0.0028, "relic_tint", seg=36, rseg=4, loc=(0, 0, 0.035), scale=(1, 0.78, 1)))
    return finish("relic_clay_thumb", p)


def clay_horse():
    """A wire horse, one hind leg bent back, on a small ebony block."""
    p = [B("block", (0.12, 0.05, 0.02), (0, 0, 0.01), "ebony", bevel=0.002)]
    p.append(T("body", [(-0.035, 0, 0.08), (-0.01, 0, 0.09), (0.015, 0, 0.09), (0.035, 0, 0.08)], 0.0035, "brass"))
    p.append(T("neck", [(0.03, 0, 0.085), (0.05, 0, 0.11), (0.068, 0, 0.13)], 0.003, "brass"))
    p.append(T("head", [(0.068, 0, 0.13), (0.09, 0, 0.118)], 0.0028, "brass"))
    p.append(T("tail", [(-0.035, 0, 0.08), (-0.052, 0, 0.082), (-0.06, 0, 0.07)], 0.0022, "brass"))
    for y in (-0.008, 0.008):
        p.append(T("foreleg", [(0.03, y, 0.085), (0.034, y, 0.05), (0.03, y, 0.021)], 0.0025, "brass"))
        if y < 0:
            p.append(T("hindleg", [(-0.03, y, 0.085), (-0.036, y, 0.05), (-0.03, y, 0.021)], 0.0025, "brass"))
        else:
            p.append(T("hindleg_back", [(-0.03, y, 0.085), (-0.045, y, 0.05), (-0.09, y, 0.024)], 0.0025, "brass"))
    return finish("relic_clay_horse", p)


def clay_film():
    """A scrap of cling film, fingerprinted: a crumpled glass sheet draped over a plaster mound."""
    def surf(x, y):
        inside = max(0.0, 1 - (x / 0.09) ** 2 - (y / 0.07) ** 2)
        mound = 0.035 * math.sqrt(inside)
        wr = 0.0035 * abs(math.sin(x * 71 + y * 23) * math.cos(y * 53 - x * 17)) + \
            0.0015 * abs(math.sin(x * 149) * math.sin(y * 131))
        return 0.003 + mound + wr

    n = 22
    bm = bmesh.new()
    xs = [-0.13 + 0.26 * i / n for i in range(n + 1)]
    ys = [-0.1 + 0.2 * j / n for j in range(n + 1)]
    g = [[bm.verts.new((x, y, surf(x, y))) for y in ys] for x in xs]
    for i in range(n):
        for j in range(n):
            bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sheet = kit._obj("film", bm, "glass")
    p = [sheet, E("mound", (0, 0, 0.035), (0.18, 0.14, 0.07), "plaster", 16, 8)]
    fx, fy = 0.04, -0.03
    fz = surf(fx, fy) + 0.001
    for k, r in enumerate((0.008, 0.012, 0.016)):
        p.append(RING("print%d" % k, r, 0.0008, "ebony", seg=24, rseg=3, loc=(fx, fy, fz)))
    return finish("relic_clay_film", p)


def noir_pawn():
    """A pawn ticket for a camera: a paper ticket with a brass eyelet and string on a brass stand."""
    p = []
    card = [B("card", (0.09, 0.002, 0.13), (0, 0, 0.08), "sketch_paper"),
            RING("eyelet", 0.007, 0.0012, "brass", seg=24, rseg=4, rot=(R(90), 0, 0), loc=(0, 0, 0.12)),
            T("string_r", [(0.0075, 0, 0.12), (0.02, -0.003, 0.15), (0.03, -0.004, 0.165)], 0.0009, "ebony", 4),
            T("string_l", [(-0.0075, 0, 0.12), (-0.015, -0.003, 0.15), (-0.02, -0.004, 0.17)], 0.0009, "ebony", 4)]
    for c in card:
        xf(c, rot=(R(-12), 0, 0))
    p += card
    p.append(B("clip", (0.05, 0.012, 0.008), (0, 0.003, 0.012), "brass"))
    p.append(B("foot", (0.1, 0.07, 0.004), (0, 0.02, 0.002), "brass", bevel=0.001))
    p.append(T("brace", [(0, 0.05, 0.004), (0, 0.04, 0.06), (0, 0.03, 0.1)], 0.0025, "brass"))
    return finish("relic_noir_pawn", p)


def noir_matchbook():
    """A matchbook from a bar that closed: an open matchbook standing in a V, one match lying in front."""
    p = []
    cover = B("cover", (0.065, 0.002, 0.11), (0, 0, 0.055), "relic_tint")
    inside = B("inside", (0.065, 0.002, 0.11), (0, 0, 0.055), "sketch_paper")
    striker = B("striker", (0.05, 0.0035, 0.012), (0, 0, 0.012), "ebony")
    xf(cover, rot=(R(35), 0, 0))
    xf(inside, rot=(R(-35), 0, 0))
    xf(striker, rot=(R(-35), 0, 0))
    p += [cover, inside, striker]
    p.append(B("spine", (0.065, 0.008, 0.006), (0, 0, 0.003), "brass"))
    p.append(T("match", [(-0.03, -0.022, 0.0025), (0.0, -0.022, 0.0025), (0.028, -0.022, 0.0025)], 0.0015, "ebony", 5))
    p.append(E("matchhead", (0.031, -0.022, 0.0025), (0.006, 0.006, 0.006), "plaster", 6, 3))
    return finish("relic_noir_matchbook", p)


def noir_stub():
    """A cinema stub, row G: a torn paper stub standing in a brass clip on a brass foot."""
    pts = [(-0.028, 0.05), (0.028, 0.05)]
    for i in range(1, 8):
        pts.append((0.028 - (0.003 if i % 2 else 0.0), 0.05 + 0.15 * i / 8))
    for i in range(8):
        pts.append((0.028 - 0.056 * (i + 1) / 8, 0.2 - (0.0025 if i % 2 else 0.0)))
    bm = bmesh.new()
    f = [bm.verts.new((x, -0.00075, z)) for x, z in pts]
    b = [bm.verts.new((x, 0.00075, z)) for x, z in pts]
    bm.faces.new(f)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    p = [kit._obj("stub", bm, "sketch_paper")]
    p.append(B("row_bar", (0.03, 0.0022, 0.006), (0, 0, 0.11), "ebony"))
    p.append(B("clip", (0.07, 0.01, 0.012), (0, 0, 0.046), "brass"))
    p.append(B("foot", (0.09, 0.06, 0.004), (0, 0.02, 0.002), "brass", bevel=0.001))
    p.append(T("arm", [(0, 0.02, 0.004), (0, 0.012, 0.03), (0, 0.005, 0.046)], 0.0028, "brass"))
    return finish("relic_noir_stub", p)


def aria_score():
    """A pencilled score, page nine: a sheet of pencilled staves on a brass lyre-topped music stand."""
    sheet = [B("sheet", (0.14, 0.002, 0.2), (0, 0, 0.11), "sketch_paper")]
    for s in range(3):
        z0 = 0.05 + s * 0.06
        for k in range(5):
            sheet.append(B("staff", (0.12, 0.0008, 0.0008), (0, -0.0012, z0 + k * 0.0045), "ebony"))
        for n in range(4):
            x = -0.045 + 0.03 * n
            zn = z0 + 0.01 + 0.0045 * ((n * 3 + s) % 5)
            sheet.append(E("note", (x, -0.0012, zn), (0.0075, 0.0025, 0.0062), "ebony", 6, 3))
            sheet.append(B("stem", (0.0009, 0.0008, 0.018), (x + 0.0035, -0.0012, zn + 0.009), "ebony"))
    sheet.append(T("title", [(-0.05 + 0.1 * i / 20, -0.0012, 0.195 + 0.003 * math.sin(i * 0.8)) for i in range(21)],
                   0.0008, "ebony", 4))
    for c in sheet:
        xf(c, rot=(R(-10), 0, 0))
    p = sheet
    p.append(L("foot", [(0, 0), (0.05, 0), (0.05, 0.006), (0, 0.006)], "brass", 20, z=0.0, cap=True))
    p[-1] = xf(p[-1], loc=(0, 0.045, 0))
    p.append(T("pole", [(0, 0.045, 0.006), (0, 0.045, 0.06), (0, 0.045, 0.1)], 0.0035, "brass", 8))
    arms = [(-0.085, 0.045, 0.1), (-0.085, 0.045, 0.14), (-0.08, 0.045, 0.19), (-0.06, 0.045, 0.225),
            (0, 0.045, 0.238), (0.06, 0.045, 0.225), (0.08, 0.045, 0.19), (0.085, 0.045, 0.14), (0.085, 0.045, 0.1)]
    p.append(T("lyre", arms, 0.0026, "brass", 6))
    return finish("relic_aria_score", p)


def aria_baton():
    """A conductor's baton, ash: relic_tint shaft, ebony cork-like grip, brass ferrule, two brass cradles."""
    p = []
    p.append(TP("shaft", [(x, 0, 0.03) for x in (-0.07, -0.03, 0.0, 0.05, 0.1, 0.14)],
                [0.0088, 0.0084, 0.0076, 0.0064, 0.005, 0.0038], "relic_tint", 10))
    p.append(TP("grip", [(x, 0, 0.03) for x in (-0.14, -0.13, -0.1, -0.08, -0.06)],
                [0.0098, 0.0118, 0.0121, 0.0116, 0.0108], "ebony", 10))
    p.append(TP("ferrule", [(-0.064, 0, 0.03), (-0.058, 0, 0.03)], [0.0125, 0.0125], "brass", 10))
    for x, sz in ((-0.1, 0.018), (0.07, 0.0235)):
        p.append(B("cradle_base", (0.03, 0.03, 0.003), (x, 0, 0.0015), "brass"))
        for s in (-1, 1):
            p.append(T("cradle_post", [(x, s * 0.011, 0.003), (x, s * 0.011, sz)], 0.0022, "brass", 6))
        p.append(T("cradle_saddle", [(x, -0.011, sz), (x, 0.011, sz)], 0.0022, "brass", 6))
    return finish("relic_aria_baton", p)


def aria_tuning_fork():
    """A tuning fork, A-440: brass fork standing in an ebony block."""
    p = [B("block", (0.08, 0.05, 0.03), (0, 0, 0.015), "ebony", bevel=0.002),
         B("stem", (0.012, 0.008, 0.09), (0, 0, 0.065), "brass"),
         B("crotch", (0.04, 0.008, 0.02), (0, 0, 0.12), "brass"),
         B("prong_l", (0.009, 0.008, 0.14), (-0.0105, 0, 0.19), "brass", bevel=0.0015),
         B("prong_r", (0.009, 0.008, 0.14), (0.0105, 0, 0.19), "brass", bevel=0.0015)]
    return finish("relic_aria_tuning_fork", p)


def chitin_bell():
    """A moth's finger-bell: a relic_tint bell with a clapper, hung from a ring on a brass gallows."""
    p = [L("bell", [(0.03, 0.0), (0.026, 0.006), (0.02, 0.02), (0.013, 0.036), (0.008, 0.048), (0.0035, 0.056),
                    (0.0, 0.06)], "relic_tint", 20, z=0.13)]
    p.append(RING("rim", 0.03, 0.0025, "relic_tint", seg=24, rseg=4, loc=(0, 0, 0.13)))
    p.append(E("clapper", (0, 0, 0.12), (0.012, 0.012, 0.012), "brass", 8, 4))
    p.append(T("hook", [(0, 0, 0.19), (0, 0, 0.1975)], 0.0012, "brass", 4))
    p.append(RING("hanger", 0.0075, 0.0015, "brass", seg=20, rseg=4, rot=(R(90), 0, 0), loc=(0, 0, 0.205)))
    p.append(T("beam_hook", [(0, 0, 0.225), (0, 0, 0.2125)], 0.0012, "brass", 4))
    p.append(T("beam", [(-0.05, 0, 0.225), (0.05, 0, 0.225)], 0.0028, "brass"))
    for s in (-1, 1):
        p.append(T("upright", [(s * 0.05, 0, 0.004), (s * 0.05, 0, 0.225)], 0.0028, "brass"))
    p.append(B("base", (0.12, 0.05, 0.004), (0, 0, 0.002), "brass", bevel=0.001))
    return finish("relic_chitin_bell", p)


def chitin_guild_key():
    """A guild key, cut to six metres: an ornate key with wing filigree, lying diagonally on a velvet cushion."""
    z = 0.0335
    cx = -0.07
    p = [E("pillow", (0, 0, 0.015), (0.2, 0.12, 0.03), "velvet", 14, 6)]
    key = []
    key.append(RING("bow", 0.028, 0.0045, "gilt", seg=28, rseg=6, loc=(cx, 0, z)))
    key.append(RING("bow_in", 0.013, 0.0018, "gilt", seg=16, rseg=4, loc=(cx, 0, z)))
    for a in (60, 120, 240, 300):
        ca, sa = math.cos(R(a)), math.sin(R(a))
        key.append(orn.leaf("wing%d" % a, (cx + 0.028 * ca, 0.028 * sa, z), (ca, sa, 0), 0.03, 0.012,
                            curl=0.5, lobes=3, mat="gilt", lift=(0, 0, 1), n=8))
    key.append(TP("shaft", [(cx + 0.024 + (0.12 - cx - 0.024) * i / 8, 0, z) for i in range(9)],
                  [0.0032] * 9, "gilt", 6))
    key.append(B("bit", (0.024, 0.012, 0.006), (0.126, 0, z), "gilt"))
    key.append(B("tooth_a", (0.008, 0.005, 0.007), (0.12, 0.0085, z), "gilt"))
    key.append(B("tooth_b", (0.008, 0.005, 0.007), (0.134, 0.0085, z), "gilt"))
    for k in key:
        xf(k, rot=(0, 0, R(28)))
    return finish("relic_chitin_guild_key", p + key)


def chitin_tapestry():
    """A strip of ancestor tapestry: a narrow relic_tint weave with gilt bands and fringe, hung from a brass rod."""
    p = []
    p.append(T("rod", [(-0.045, 0, 0.2), (0.045, 0, 0.2)], 0.0028, "brass"))
    for s in (-1, 1):
        p.append(E("finial%d" % s, (s * 0.047, 0, 0.2), (0.008, 0.008, 0.008), "brass", 8, 4))
        p.append(T("post%d" % s, [(s * 0.04, 0, 0.005), (s * 0.04, 0, 0.2)], 0.0025, "brass"))
    p.append(B("base", (0.08, 0.05, 0.005), (0, 0, 0.0025), "brass", bevel=0.001))
    p.append(B("strip", (0.05, 0.002, 0.16), (0, 0, 0.12), "relic_tint"))
    p.append(B("sleeve", (0.054, 0.005, 0.012), (0, 0, 0.196), "relic_tint"))
    for i in range(7):
        p.append(B("weft%d" % i, (0.05, 0.0035, 0.004), (0, 0, 0.05 + i * 0.02), "gilt"))
    for i in range(7):
        x = -0.024 + i * 0.008
        p.append(T("fringe%d" % i, [(x, 0, 0.04), (x, 0, 0.015)], 0.0014, "relic_tint", 4))
    return finish("relic_chitin_tapestry", p)


def paint_stub():
    """A pencil stub: a short hexagonal relic_tint pencil sharpened at both ends, on a velvet cushion."""
    z = 0.03 + 0.0085
    p = [B("cushion", (0.2, 0.14, 0.03), (0, 0, 0.015), "velvet", bevel=0.012, seg=2)]
    p.append(TP("body", [(-0.072, 0, z), (-0.066, 0, z), (0, 0, z), (0.066, 0, z), (0.072, 0, z)],
                [0.0045, 0.0085, 0.0085, 0.0085, 0.0045], "relic_tint", 6))
    for s in (-1, 1):
        p.append(TP("lead%d" % s, [(s * 0.072, 0, z), (s * 0.082, 0, z)], [0.0045, 0.0007], "ebony", 6))
    return finish("relic_paint_stub", p)


def paint_swatch():
    """A dried colour swatch: a card with a thick relic_tint impasto dab and ridges, on a brass easel."""
    card = [B("card", (0.1, 0.002, 0.13), (0, 0, 0.075), "sketch_paper"),
            E("dab", (0, -0.002, 0.085), (0.05, 0.014, 0.04), "relic_tint", 10, 5)]
    for z in (0.078, 0.088, 0.098):
        pts = []
        for i in range(9):
            x = -0.018 + 0.0045 * i
            d = max(0.0, 1 - (x / 0.025) ** 2 - ((z - 0.085) / 0.02) ** 2)
            pts.append((x, -0.002 - 0.007 * math.sqrt(d) - 0.0006, z))
        card.append(T("ridge", pts, 0.0016, "relic_tint", 4))
    for c in card:
        xf(c, rot=(R(-15), 0, 0))
    p = card
    p.append(B("foot", (0.13, 0.05, 0.004), (0, 0.025, 0.002), "brass", bevel=0.001))
    p.append(B("ledge", (0.12, 0.01, 0.009), (0, 0, 0.0045), "brass"))
    p.append(T("strut", [(0, 0.045, 0.004), (0, 0.04, 0.06), (0, 0.035, 0.105)], 0.0025, "brass"))
    return finish("relic_paint_swatch", p)


def paint_ferrule():
    """The palette knife's ferrule: a crimped brass tube standing on a black marble block."""
    zs = [0.005 + 0.0055 * k for k in range(14)]
    prof = [(0.017, 0.0)] + [(0.0165 + 0.001 * (k % 2), z) for k, z in enumerate(zs)]
    prof += [(0.0165, 0.09), (0.0115, 0.09), (0.0115, 0.0)]
    p = [B("block", (0.1, 0.1, 0.03), (0, 0, 0.015), "marble_black", bevel=0.003),
         L("ferrule", prof, "brass", 16, cap=False, z=0.03)]
    return finish("relic_paint_ferrule", p)


def build(args):
    for fn in (glass_face, glass_veil, glass_iron, clay_thumb, clay_horse, clay_film,
               noir_pawn, noir_matchbook, noir_stub, aria_score, aria_baton, aria_tuning_fork,
               chitin_bell, chitin_guild_key, chitin_tapestry, paint_stub, paint_swatch, paint_ferrule):
        fn()
