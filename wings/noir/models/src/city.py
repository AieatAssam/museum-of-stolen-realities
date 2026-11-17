"""Street architecture and furniture for The Long Shadow. Arg = part. Blender Z up; a front faces -Y
(Godot +Z). Origins noted per part.
  facade_a / facade_b / facade_low   3 m brick bay, front plane at y=0, wall behind (+Y), origin at the
                                     bay's foot centre. a: 13.6 m, dark windows; b: one lit window; low: 7.2 m
  back_door      a steel back door in a stone surround with a stoop and a caged bulb, origin foot centre
  fire_escape    3.6 m wide, three landings (4.0, 7.2, 10.4) with stairs and a drop ladder, origin on the wall
  diner_front    4 m diner run: ribbed steel apron, window mullions, chrome band, blinds; origin foot centre
  neon_eat       blade sign, EAT and a cup in red neon on both faces; origin where it meets the wall
  trash_can, crate, manhole, hydrant, bench, shopfront, curb (3 m), lamp_bracket"""
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


# --- facades -------------------------------------------------------------------------------------

def _window(p, cx, z0, w=1.1, h=1.8, lit=False):
    """A sash window in a 0.22 m reveal, its sill at z0. Front plane of the wall at y=0."""
    gy = 0.2
    p.append(B("glass", (w, 0.02, h), (cx, gy + 0.03, z0 + h / 2), "window_lit" if lit else "window_glass"))
    path = [(cx - w / 2, gy, z0), (cx + w / 2, gy, z0), (cx + w / 2, gy, z0 + h), (cx - w / 2, gy, z0 + h)]
    p.append(kit.sweep_closed("frame", [(-0.07, -0.03), (0.0, -0.03), (0.0, 0.03), (-0.07, 0.03)], path, mat="sash"))
    # meeting rail and muntins (2 over 2)
    p.append(B("rail", (w, 0.05, 0.05), (cx, gy - 0.01, z0 + h / 2), "sash"))
    p.append(B("rail2", (w, 0.03, 0.04), (cx, gy + 0.02, z0 + h / 2 + 0.05), "sash"))
    for s in (-1, 1):
        p.append(B("muntin", (0.03, 0.03, h), (cx, gy, z0 + h / 2), "sash"))
    p.append(B("muntin_h", (w, 0.03, 0.03), (cx, gy, z0 + h * 0.25), "sash"))
    p.append(B("muntin_h", (w, 0.03, 0.03), (cx, gy, z0 + h * 0.75), "sash"))
    # stone sill (projecting, with a drip) and a flat lintel with a keystone
    p.append(B("sill", (w + 0.24, 0.3, 0.08), (cx, 0.03, z0 - 0.04), "stone", bevel=0.012))
    p.append(B("sill_drip", (w + 0.2, 0.04, 0.04), (cx, -0.1, z0 - 0.1), "stone"))
    p.append(B("lintel", (w + 0.3, 0.06, 0.26), (cx, -0.02, z0 + h + 0.13), "stone", bevel=0.01))
    p.append(B("key", (0.18, 0.1, 0.32), (cx, -0.04, z0 + h + 0.15), "stone", bevel=0.015))


def _cornice(p, z, w=3.0):
    p.append(B("frieze", (w, 0.08, 0.5), (0, -0.04, z + 0.25), "brick_dark"))
    p.append(B("bed", (w, 0.2, 0.1), (0, -0.1, z + 0.55), "stone", bevel=0.02))
    n = int(w / 0.25)
    for i in range(n):
        p.append(B("dentil", (0.11, 0.16, 0.14), (-w / 2 + 0.125 + i * 0.25, -0.16, z + 0.67), "stone"))
    p.append(B("corona", (w, 0.48, 0.14), (0, -0.2, z + 0.81), "stone", bevel=0.02))
    p.append(B("cyma", (w, 0.56, 0.06), (0, -0.24, z + 0.91), "stone", bevel=0.02))
    p.append(B("blocking", (w, 0.3, 0.45), (0, 0.05, z + 1.16), "brick_dark"))
    p.append(B("coping", (w, 0.38, 0.06), (0, 0.05, z + 1.41), "stone", bevel=0.015))


def facade(variant):
    p = []
    H = 7.2 if variant == "low" else 13.6
    floors = [4.4] if variant == "low" else [4.4, 7.6, 10.8]
    D = 0.35
    # piers either side of the window column, full height; spandrels between windows
    p.append(B("pier", (0.95, D, H), (-1.025, D / 2, H / 2), "brick"))
    p.append(B("pier", (0.95, D, H), (1.025, D / 2, H / 2), "brick"))
    edges = [0.0]
    for z in floors:
        edges += [z, z + 1.8]
    edges.append(H)
    for i in range(0, len(edges), 2):
        z0, z1 = edges[i], edges[i + 1]
        p.append(B("spandrel", (1.1, D, z1 - z0), (0, D / 2, (z0 + z1) / 2), "brick"))
    for i in range(len(floors)):
        z0, z1 = floors[i], floors[i] + 1.8  # reveal back wall behind the glass
        p.append(B("reveal", (1.1, 0.1, 1.8), (0, 0.3, (z0 + z1) / 2), "brick_dark"))
    for k, z in enumerate(floors):
        _window(p, 0.0, z, lit=(variant == "b" and k == 1) or (variant == "c" and k != 1))
    # granite plinth, belt course at the first floor, a pilaster strip at each bay edge
    p.append(B("plinth", (3.0, 0.1, 0.6), (0, -0.05, 0.3), "stone", bevel=0.015))
    p.append(B("belt", (3.0, 0.16, 0.22), (0, -0.06, 4.0), "stone", bevel=0.02))
    p.append(B("belt2", (3.0, 0.1, 0.08), (0, -0.04, 3.84), "stone"))
    for s in (-1, 1):
        p.append(B("quoin", (0.08, 0.04, H - 0.6), (s * 1.46, -0.02, 0.6 + (H - 0.6) / 2), "brick_dark"))
    _cornice(p, H - 1.45 if variant != "low" else H - 1.45)
    # downpipe on the left edge
    p.append(kit.tube("pipe", [(-1.38, -0.09, 0.15), (-1.38, -0.09, H - 1.0)], 0.045, 8, mat="iron"))
    for z in range(1, int(H) - 1, 2):
        p.append(B("pipe_clip", (0.12, 0.1, 0.04), (-1.38, -0.05, z), "iron"))
    kit.join("facade_" + variant, p)


def back_door():
    p = []
    p.append(B("surround_l", (0.22, 0.12, 2.5), (-0.66, -0.06, 1.25), "stone", bevel=0.015))
    p.append(B("surround_r", (0.22, 0.12, 2.5), (0.66, -0.06, 1.25), "stone", bevel=0.015))
    p.append(B("head", (1.6, 0.16, 0.28), (0, -0.08, 2.62), "stone", bevel=0.02))
    p.append(B("door", (1.1, 0.06, 2.4), (0, 0.04, 1.2), "iron", bevel=0.01))
    for z in (0.5, 1.3, 2.0):
        p.append(B("panel", (0.9, 0.03, 0.5 if z != 1.3 else 0.8), (0, 0.0, z), "iron", bevel=0.01))
    p.append(B("wire_glass", (0.5, 0.02, 0.4), (0, -0.01, 1.95), "window_glass"))
    p.append(B("push_bar", (0.7, 0.06, 0.05), (0.05, -0.04, 1.05), "zinc", bevel=0.01))
    p.append(B("stoop", (1.7, 0.6, 0.18), (0, -0.3, 0.09), "stone", bevel=0.02))
    # caged bulb on a gooseneck bracket over the door
    p.append(kit.tube("neck", [(0, 0.0, 2.95), (0, -0.25, 3.15), (0, -0.45, 3.1)], 0.02, 8, mat="iron"))
    p.append(kit.lathe("shade", [(0.0, 3.2), (0.04, 3.2), (0.2, 3.04), (0.22, 3.0), (0.0, 3.0)], 16, mat="iron", cap=False))
    for ob in p[-1:]:
        ob.location = (0, -0.45, -0.02)
    bulb = kit.lathe("bulb", [(0.0, 2.88), (0.05, 2.9), (0.06, 2.95), (0.03, 3.01), (0.0, 3.01)], 12, mat="bulb")
    bulb.location = (0, -0.45, 0)
    p.append(bulb)
    kit.join("back_door", p)


def fire_escape():
    p = []
    W, Dp = 3.6, 1.1
    levels = [4.0, 7.2, 10.4]
    for li, z in enumerate(levels):
        # landing: angle frame, slatted deck, brackets back to the wall
        p.append(B("frame_f", (W, 0.05, 0.08), (0, -Dp, z - 0.04), "iron"))
        p.append(B("frame_b", (W, 0.05, 0.08), (0, -0.03, z - 0.04), "iron"))
        for x in (-W / 2, W / 2):
            p.append(B("frame_s", (0.05, Dp, 0.08), (x, -Dp / 2, z - 0.04), "iron"))
        for i in range(int(W / 0.09)):
            p.append(B("slat", (0.035, Dp - 0.06, 0.025), (-W / 2 + 0.06 + i * 0.09, -Dp / 2, z - 0.0125), "iron"))
        for x in (-W / 2 + 0.2, W / 2 - 0.2):
            p.append(kit.tube("bracket", [(x, -0.02, z - 0.9), (x, -Dp + 0.05, z - 0.06)], 0.025, 6, mat="iron"))
        # railing: top and mid rails, close balusters on the front and ends
        for zz in (0.95, 0.5):
            p.append(kit.tube("rail", [(-W / 2, -0.02, z + zz), (-W / 2, -Dp, z + zz), (W / 2, -Dp, z + zz), (W / 2, -0.02, z + zz)], 0.018, 6, mat="iron"))
        for i in range(int(W / 0.15) + 1):
            p.append(B("baluster", (0.016, 0.016, 0.95), (-W / 2 + i * 0.15, -Dp, z + 0.475), "iron"))
        for x in (-W / 2, W / 2):
            for j in range(1, int(Dp / 0.15)):
                p.append(B("baluster", (0.016, 0.016, 0.95), (x, -j * 0.15, z + 0.475), "iron"))
        # a stair from this landing down to the one below (or a drop ladder from the lowest)
        if li > 0:
            z0, z1 = levels[li - 1], z
            x0, x1 = (W / 2 - 0.4, -W / 2 + 0.9) if li % 2 else (-W / 2 + 0.4, W / 2 - 0.9)
            n = 12
            for s in (-0.78, -0.32):
                p.append(kit.tube("stringer", [(x0, s, z0 + 0.02), (x1, s, z1 - 0.02)], 0.03, 6, mat="iron"))
                p.append(kit.tube("handrail", [(x0, s, z0 + 0.9), (x1, s, z1 + 0.9)], 0.016, 6, mat="iron"))
            for k in range(1, n):
                t = k / n
                p.append(B("tread", (0.22, 0.48, 0.03), (x0 + (x1 - x0) * t, -0.55, z0 + (z1 - z0) * t), "iron"))
    for x in (-0.3, 0.3):
        p.append(B("ladder_rail", (0.04, 0.04, 2.2), (W / 2 - 0.6 + x, -Dp + 0.08, levels[0] - 1.1), "iron"))
    for k in range(8):
        p.append(B("rung", (0.6, 0.025, 0.025), (W / 2 - 0.6, -Dp + 0.08, levels[0] - 0.2 - k * 0.27), "iron"))
    kit.join("fire_escape", p)


# --- diner ---------------------------------------------------------------------------------------

def diner_front():
    """4 m along X. The window opening runs z 1.15..3.45; the glowing pane itself is the wing's
    (it carries the silhouette), so this is the frame, blinds and the steel round it."""
    p = []
    L = 4.0
    p.append(B("apron", (L, 0.12, 1.1), (0, -0.06, 0.55), "steel", bevel=0.01))
    for z in (0.25, 0.45, 0.65, 0.85):
        p.append(B("rib", (L, 0.05, 0.04), (0, -0.13, z), "chrome", bevel=0.01))
    # sill: a chrome nosing sloped to shed rain, a drip bead under it, an inner stool behind the glass
    sl = B("sill", (L, 0.34, 0.06), (0, -0.09, 1.14), "chrome", bevel=0.02)
    sl.rotation_euler = (math.radians(-6), 0, 0)
    p.append(sl)
    p.append(B("drip", (L, 0.03, 0.04), (0, -0.25, 1.08), "chrome", bevel=0.01))
    p.append(B("stool", (L, 0.3, 0.04), (0, 0.18, 1.17), "wood", bevel=0.01))
    # deep box mullions (pane edges at x = -2, -2/3, 2/3; each mullion carries a pressed cover cap)
    mx = (-L / 2, -L / 6, L / 6)
    for x in mx:
        c = x + (0.05 if x == -L / 2 else 0)
        p.append(B("mullion", (0.1, 0.32, 2.3), (c, 0.0, 2.3), "chrome", bevel=0.015))
        p.append(B("cap", (0.06, 0.04, 2.3), (c, -0.17, 2.3), "steel", bevel=0.01))
    p.append(B("head", (L, 0.34, 0.14), (0, 0.0, 3.5), "chrome", bevel=0.02))
    # each pane: a glazing bead round the glass (the wing's pane sits at y 0.02), then a venetian blind
    # behind it (+Y): head rail, 20 crowned slats tilted half open on two ladder tapes, a bottom rail and a
    # tilt wand. Slats stop short of the mullions so the blind reads as hung in the opening.
    lefts = [mx[0] + 0.1, mx[1] + 0.05, mx[2] + 0.05]
    rights = [mx[1] - 0.05, mx[2] - 0.05, L / 2]
    for a, b in zip(lefts, rights):
        w, cx = b - a, (a + b) / 2
        for z, h in ((1.2, 0.04), (3.41, 0.04)):
            p.append(B("bead", (w, 0.04, h), (cx, 0.0, z), "chrome", bevel=0.008))
        for x in (a + 0.02, b - 0.02):
            p.append(B("bead", (0.04, 0.04, 2.21), (x, 0.0, 2.305), "chrome", bevel=0.008))
        bw = w - 0.1
        p.append(B("head_rail", (bw, 0.07, 0.06), (cx, 0.13, 3.35), "steel", bevel=0.01))
        for i in range(20):
            z = 1.36 + i * 0.098
            for k, (dy, dz) in enumerate(((-0.026, -0.003), (0.0, 0.003), (0.026, -0.003))):  # crowned: three strips
                s = B("slat", (bw, 0.027, 0.006), (cx, 0.13 + dy * 0.77, z + dy * 0.64 + dz), "shirt")
                s.rotation_euler = (math.radians(40 + (k - 1) * 8), 0, 0)
                p.append(s)
        p.append(B("bottom_rail", (bw, 0.06, 0.025), (cx, 0.13, 1.3), "steel", bevel=0.008))
        for tx in (cx - bw * 0.32, cx + bw * 0.32):
            for ty in (0.1, 0.16):
                p.append(B("ladder", (0.012, 0.003, 2.05), (tx, ty, 2.33), "shirt"))
        p.append(kit.tube("wand", [(b - 0.12, 0.09, 3.32), (b - 0.12, 0.08, 2.2)], 0.005, 6, mat="chrome"))
        p.append(B("cord", (0.006, 0.006, 1.6), (a + 0.1, 0.1, 2.5), "black"))
    # enamel fascia with chrome bands
    p.append(B("fascia", (L, 0.16, 0.9), (0, -0.06, 4.05), "paint", bevel=0.01))
    for z in (3.66, 4.48):
        p.append(B("band", (L, 0.2, 0.05), (0, -0.09, z), "chrome", bevel=0.01))
    # a neon run along the fascia
    p.append(kit.tube("neon", [(-L / 2, -0.2, 4.2), (L / 2, -0.2, 4.2)], 0.018, 8, mat="neon_red"))
    for x in (-1.5, 0.0, 1.5):
        p.append(B("neon_clip", (0.03, 0.06, 0.05), (x, -0.16, 4.2), "chrome"))
    kit.join("diner_front", p)


def diner_end():
    """The diner run's closing pier (0.4 m along X, origin foot centre, front -Y): a steel-cased return from
    the apron to the fascia, deep enough (to y 1.0) to close the lit room's end behind the glass, with the
    apron's chrome ribs and the fascia bands wrapped round its front."""
    p = [B("core", (0.4, 1.3, 4.5), (0, 0.35, 2.25), "steel", bevel=0.02)]
    for z in (0.25, 0.45, 0.65, 0.85):
        p.append(B("rib", (0.44, 0.05, 0.04), (0, -0.32, z), "chrome", bevel=0.01))
    for z in (3.66, 4.48):
        p.append(B("band", (0.44, 0.06, 0.05), (0, -0.32, z), "chrome", bevel=0.01))
    for x in (-0.2, 0.2):
        p.append(kit.tube("bead", [(x, -0.3, 0.0), (x, -0.3, 4.5)], 0.02, 8, mat="chrome"))
    p.append(B("plate", (0.3, 0.02, 2.2), (0, -0.31, 2.3), "chrome", bevel=0.006))
    kit.join("diner_end", p)


LETTERS = {  # tube polylines in a 0.5 x 0.7 cell, (x, z)
    "E": [[(0.45, 0.7), (0.05, 0.7), (0.05, 0.0), (0.45, 0.0)], [(0.05, 0.35), (0.35, 0.35)]],
    "A": [[(0.0, 0.0), (0.25, 0.7), (0.5, 0.0)], [(0.1, 0.28), (0.4, 0.28)]],
    "T": [[(0.0, 0.7), (0.5, 0.7)], [(0.25, 0.7), (0.25, 0.0)]],
}


def neon_eat():
    """Blade sign standing out from the wall along -Y, 2.3 m tall, letters stacked."""
    p = []
    p.append(B("board", (0.14, 1.0, 3.0), (0, -0.7, 0), "paint", bevel=0.03))
    p.append(kit.sweep_closed("edge", [(0.0, -0.09), (0.04, -0.09), (0.04, 0.09), (0.0, 0.09)],
                              [(0, -0.2, -1.5), (0, -1.2, -1.5), (0, -1.2, 1.5), (0, -0.2, 1.5)], mat="chrome"))
    for z in (1.1, -1.1):
        p.append(kit.tube("arm", [(0, 0.0, z), (0, -0.22, z)], 0.03, 8, mat="iron"))
    for side in (-1, 1):
        x = side * 0.1  # seen from +X the reader's right is +Y; mirrored on the other face
        for ch, zc in zip("EAT", (0.85, 0.05, -0.75)):
            for stroke in LETTERS[ch]:
                pts = [(x, -0.7 + side * (u - 0.25) * 0.85, zc + (v - 0.35) * 0.85) for u, v in stroke]
                p.append(kit.tube("tube", pts, 0.022, 8, mat="neon_red"))
        cup = [(x, -0.7 + 0.2 * math.cos(a), -1.18 - 0.14 * math.sin(a)) for a in [math.pi * i / 10 for i in range(11)]]
        p.append(kit.tube("cup", cup, 0.02, 8, mat="neon_red"))
        p.append(kit.tube("saucer", [(x, -0.98, -1.36), (x, -0.42, -1.36)], 0.02, 8, mat="neon_red"))
    kit.join("neon_eat", p)


# --- street furniture ----------------------------------------------------------------------------

def trash_can():
    prof = [(0.0, 0.0), (0.24, 0.0), (0.25, 0.04)]
    for i in range(6):
        z = 0.1 + i * 0.13
        prof += [(0.255, z - 0.03), (0.27, z), (0.255, z + 0.03)]
    prof += [(0.27, 0.86), (0.28, 0.88), (0.0, 0.88)]
    p = [kit.lathe("can", prof, 24, mat="zinc")]
    p.append(kit.lathe("lid", [(0.0, 0.88), (0.3, 0.88), (0.3, 0.9), (0.2, 0.97), (0.0, 0.99)], 24, mat="zinc"))
    p.append(kit.torus("lid_handle", 0.06, 0.012, 16, 6, mat="zinc", loc=(0, 0, 1.01), rot=(math.pi / 2, 0, 0)))
    for s in (-1, 1):
        p.append(kit.tube("handle", [(s * 0.27, -0.08, 0.7), (s * 0.31, -0.06, 0.72), (s * 0.31, 0.06, 0.72), (s * 0.27, 0.08, 0.7)], 0.012, 6, mat="zinc"))
    kit.join("trash_can", p)
    kit.box("trash_can-convcolonly", (0.56, 0.56, 1.0), (0, 0, 0.5))


def crate():
    p = []
    S = 0.9
    for z in range(5):
        for side in range(4):
            a = side * math.pi / 2
            r = S / 2 - 0.012  # one face per side, turned about the crate's axis
            slat = B("slat", (S - 0.04, 0.025, 0.16), (r * math.sin(a), -r * math.cos(a), 0.1 + z * 0.175), "wood", bevel=0.004)
            slat.rotation_euler = (0, 0, a)
            p.append(slat)
    p.append(B("top", (S - 0.02, S - 0.02, 0.025), (0, 0, S - 0.012), "wood", bevel=0.004))
    for x in (-1, 1):
        for y in (-1, 1):
            p.append(B("corner", (0.07, 0.07, S), (x * (S / 2 - 0.035), y * (S / 2 - 0.035), S / 2), "wood", bevel=0.006))
    for side in range(4):
        a = side * math.pi / 2
        r = S / 2 + 0.005
        d = B("brace", (S * 1.25, 0.03, 0.08), (r * math.sin(a), -r * math.cos(a), S / 2), "wood", bevel=0.004)
        d.rotation_euler = (0, math.atan2(S - 0.2, S - 0.2), a)
        p.append(d)
    kit.join("crate", p)


def _light_crate():
    """crate() with 4 slats a side and 1-segment bevels, so three of them stay within the tri budget. Origin at
    the crate's footprint centre, ~0.9 m tall."""
    p = []
    S = 0.9
    for z in range(4):
        for side in range(4):
            a = side * math.pi / 2
            r = S / 2 - 0.012
            slat = B("slat", (S - 0.04, 0.025, 0.16), (r * math.sin(a), -r * math.cos(a), 0.1 + z * 0.24), "wood", bevel=0.004, seg=1)
            slat.rotation_euler = (0, 0, a)
            p.append(slat)
    p.append(B("top", (S - 0.02, S - 0.02, 0.025), (0, 0, S - 0.012), "wood", bevel=0.004, seg=1))
    for x in (-1, 1):
        for y in (-1, 1):
            p.append(B("corner", (0.07, 0.07, S), (x * (S / 2 - 0.035), y * (S / 2 - 0.035), S / 2), "wood", bevel=0.006, seg=1))
    return kit.join("crate", p)


def crate_stack():
    """Three 0.9-scale crates (two on the pavement, one on top at the left) and a wood barrel in front.
    Footprint about 1.65 x 1.3 m, top at 1.62 m. Origin at the footprint's centre on the floor.
    Seeded yaw jitter on the crates so they do not sit square."""
    import random
    rng = random.Random(7)
    p = []
    for x, z in ((-0.42, 0.0), (0.42, 0.0), (-0.42, 0.81)):
        c = _light_crate()
        c.scale = (0.9, 0.9, 0.9)
        c.rotation_euler = (0, 0, rng.uniform(-0.05, 0.05))
        c.location = (x, -0.25, z)
        p.append(c)
    barrel = kit.lathe("barrel", [(0, 0), (0.22, 0), (0.25, 0.1), (0.28, 0.45), (0.25, 0.8), (0.22, 0.9), (0, 0.9)], 18, mat="wood")
    barrel.location = (0, 0.37, 0)
    p.append(barrel)
    for z in (0.12, 0.78):
        p.append(kit.torus("hoop", 0.26, 0.012, 24, 6, mat="iron", loc=(0, 0.37, z)))
    kit.join("crate_stack", p)


def newsstand():
    """2.0 w x 1.2 d x 2.4 h kiosk, origin at the floor centre, open counter on the +Y front. Plinth, back and side
    panels, roof, a wood counter with newspaper stacks, two magazine shelves on the back, a striped awning and a
    lit bulb under it."""
    p = [B("plinth", (2.0, 1.2, 0.1), (0, 0, 0.05), "black", bevel=0.01)]
    p.append(B("back", (2.0, 0.06, 2.2), (0, -0.57, 1.2), "paint", bevel=0.01))
    for sx in (-1, 1):
        p.append(B("side", (0.06, 1.2, 2.2), (sx * 0.97, 0, 1.2), "paint", bevel=0.01))
    p.append(B("roof", (2.0, 1.2, 0.1), (0, 0, 2.35), "paint", bevel=0.01))
    p.append(B("counter", (2.0, 1.2, 0.05), (0, 0, 0.975), "wood", bevel=0.008))
    for x in (-0.45, 0.45):
        p.append(B("papers", (0.85, 0.5, 0.1), (x, 0.2, 1.05), "paper", bevel=0.004))
        p.append(B("band", (0.87, 0.52, 0.02), (x, 0.2, 1.05), "card_red", bevel=0.002))
    for j, z in enumerate((1.3, 1.65)):
        p.append(B("shelf", (1.8, 0.25, 0.03), (0, -0.42, z), "wood", bevel=0.004))
        for i in range(8):
            mx = -0.78 + i * 0.22
            p.append(B("mag", (0.2, 0.02, 0.28), (mx, -0.36, z + 0.16), "card_red" if (i + j) % 2 else "paper", bevel=0.002))
    for i, x in enumerate((-0.75, -0.25, 0.25, 0.75)):
        a = B("awning", (0.5, 0.5, 0.03), (x, 0.35, 1.95), "card_red" if i % 2 == 0 else "paper", bevel=0.004)
        a.rotation_euler = (-0.3, 0, 0)
        p.append(a)
    bulb = kit.lathe("bulb", [(0, 0), (0.05, 0), (0.06, 0.05), (0.05, 0.1), (0, 0.11)], 14, mat="bulb")
    bulb.location = (0, 0.5, 1.8)
    p.append(bulb)
    kit.join("newsstand", p)


def manhole():
    p = [kit.lathe("lid", [(0.0, 0.0), (0.38, 0.0), (0.38, 0.015), (0.0, 0.015)], 32, mat="iron")]
    p.append(kit.torus("rim", 0.4, 0.025, 32, 6, mat="iron", loc=(0, 0, 0.005)))
    for r in (0.12, 0.24, 0.33):
        p.append(kit.torus("ring", r, 0.01, 32, 4, mat="iron", loc=(0, 0, 0.016)))
    for k in range(8):
        a = k * math.pi / 4
        b = B("spoke", (0.32, 0.02, 0.012), (0.17 * math.cos(a), 0.17 * math.sin(a), 0.02), "iron")
        b.rotation_euler = (0, 0, a)
        p.append(b)
    kit.join("manhole", p)


def hydrant():
    p = [kit.lathe("body", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.06), (0.12, 0.08), (0.11, 0.5), (0.13, 0.52), (0.13, 0.56), (0.1, 0.6), (0.06, 0.7), (0.02, 0.74), (0.0, 0.75)], 18, mat="iron")]
    for a in (0, math.pi):
        n = kit.lathe("nozzle", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.1), (0.06, 0.1), (0.06, 0.13), (0.0, 0.13)], 12, mat="iron")
        n.rotation_euler = (0, math.pi / 2, a)
        n.location = (0.1 * math.cos(a), 0.1 * math.sin(a), 0.42)
        p.append(n)
    kit.join("hydrant", p)


def bench():
    p = []
    L = 1.9
    for x in (-0.8, 0.8):  # scrolled cast-iron ends
        p.append(kit.tube("end", [(x, 0.25, 0.0), (x, 0.2, 0.42), (x, -0.22, 0.44), (x, -0.25, 0.0)], 0.03, 8, mat="iron"))
        p.append(kit.tube("back", [(x, 0.18, 0.44), (x, 0.28, 0.85), (x, 0.33, 0.9)], 0.028, 8, mat="iron"))
        p.append(kit.tube("arm", [(x, 0.22, 0.6), (x, -0.15, 0.62), (x, -0.22, 0.56)], 0.022, 8, mat="iron"))
    for i in range(5):
        p.append(B("seat", (L, 0.075, 0.035), (0, -0.18 + i * 0.085, 0.45), "wood", bevel=0.008))
    for i in range(3):
        b = B("back", (L, 0.075, 0.03), (0, 0.22 + i * 0.035, 0.6 + i * 0.11), "wood", bevel=0.008)
        b.rotation_euler = (math.radians(-70), 0, 0)
        p.append(b)
    kit.join("bench", p)
    kit.box("bench-convcolonly", (1.9, 0.5, 0.5), (0, 0, 0.25))


def shopfront():
    """4 m shuttered shop: rolling steel shutter, sign fascia, striped canvas awning rolled half out."""
    p = []
    L = 4.0
    for x in (-L / 2 + 0.2, L / 2 - 0.2):
        p.append(B("pier", (0.4, 0.3, 3.4), (x, 0.0, 1.7), "stone", bevel=0.02))
    for i in range(30):
        p.append(B("shutter", (L - 0.8, 0.04, 0.09), (0, 0.08, 0.05 + i * 0.1), "zinc", bevel=0.012))
    p.append(B("shutter_box", (L - 0.6, 0.3, 0.35), (0, 0.0, 3.2), "zinc", bevel=0.03))
    p.append(B("fascia", (L, 0.12, 0.6), (0, -0.1, 3.75), "paint", bevel=0.02))
    p.append(B("fascia_trim", (L, 0.16, 0.05), (0, -0.12, 4.07), "chrome"))
    # awning: alternating stripes on a sloped frame
    for i in range(10):
        s = B("stripe", (L / 10, 1.2, 0.02), (-L / 2 + L / 20 + i * L / 10, -0.6, 3.15), "canvas" if i % 2 else "awning")
        s.rotation_euler = (math.radians(18), 0, 0)
        p.append(s)
    for i in range(10):
        p.append(B("valance", (L / 10 - 0.01, 0.01, 0.2), (-L / 2 + L / 20 + i * L / 10, -1.17, 2.86), "canvas" if i % 2 else "awning"))
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        p.append(kit.tube("awning_arm", [(x, 0.0, 2.8), (x, -1.14, 2.95)], 0.015, 6, mat="iron"))
    kit.join("shopfront", p)


def curb():
    """3 m granite kerb and gutter strip along X; kerb top at z 0.02 (the road is at 0)."""
    p = [B("kerb", (3.0, 0.3, 0.16), (0, 0, -0.06), "stone", bevel=0.025)]
    p.append(B("gutter", (3.0, 0.25, 0.04), (0, -0.28, -0.03), "stone"))
    kit.join("curb", p)


def lamp_bracket():
    """Wall-hung gooseneck lamp, origin on the wall, reaching 0.9 m out along -Y."""
    p = [B("plate", (0.2, 0.04, 0.3), (0, -0.02, 0), "iron", bevel=0.01)]
    p.append(kit.tube("neck", [(0, -0.02, 0.0), (0, -0.4, 0.25), (0, -0.8, 0.28), (0, -0.9, 0.18)], 0.025, 8, mat="iron"))
    shade = kit.lathe("shade", [(0.0, 0.0), (0.05, 0.0), (0.24, -0.16), (0.26, -0.2), (0.0, -0.2)], 20, mat="iron")
    shade.location = (0, -0.9, 0.2)
    p.append(shade)
    bulb = kit.lathe("bulb", [(0.0, -0.08), (0.06, -0.1), (0.07, -0.16), (0.04, -0.24), (0.0, -0.25)], 12, mat="bulb")
    bulb.location = (0, -0.9, 0.2)
    p.append(bulb)
    kit.join("lamp_bracket", p)


def sign_bracket():
    """Wrought scroll bracket with a hanging framed board sign, origin on the wall, reaching 1.2 m out along -Y."""
    p = [B("plate", (0.12, 0.04, 0.9), (0, -0.02, 0), "iron", bevel=0.01)]
    p.append(kit.tube("arm", [(0, -0.02, 0.4), (0, -1.25, 0.4)], 0.022, 8, mat="iron"))
    p.append(kit.tube("stay", [(0, -0.02, -0.4), (0, -0.4, -0.05), (0, -0.85, 0.3), (0, -1.0, 0.4)], 0.018, 8, mat="iron"))
    p.append(kit.tube("scroll", [(0.0, -0.3, 0.4), (0, -0.42, 0.24), (0, -0.55, 0.22), (0, -0.62, 0.3), (0, -0.56, 0.36)], 0.012, 6, mat="iron"))
    for y in (-0.45, -1.15):
        p.append(kit.tube("chain", [(0, y, 0.38), (0, y, 0.22)], 0.01, 6, mat="iron"))
    p.append(B("board", (0.05, 0.9, 0.6), (0, -0.8, -0.1), "paint", bevel=0.01))
    p.append(kit.sweep_closed("frame", [(-0.03, -0.035), (0.0, -0.035), (0.0, 0.035), (-0.03, 0.035)],
                              [(0, -0.35, -0.4), (0, -1.25, -0.4), (0, -1.25, 0.2), (0, -0.35, 0.2)], mat="iron"))
    kit.join("sign_bracket", p)


PARTS = {
    "sign_bracket": sign_bracket,
    "facade_a": lambda: facade("a"), "facade_b": lambda: facade("b"), "facade_c": lambda: facade("c"), "facade_low": lambda: facade("low"),
    "back_door": back_door, "fire_escape": fire_escape, "diner_front": diner_front, "diner_end": diner_end, "neon_eat": neon_eat,
    "trash_can": trash_can, "crate": crate, "manhole": manhole, "hydrant": hydrant, "bench": bench,
    "shopfront": shopfront, "curb": curb, "lamp_bracket": lamp_bracket,
    "newsstand": newsstand, "crate_stack": crate_stack,
}


def build(args):
    PARTS[args[0]]()
