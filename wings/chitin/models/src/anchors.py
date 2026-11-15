"""Chitin Court anchors: hook, peg, key, lift, carriage, track, moth. One script, selected by args[0].
Run through tools/blender_build.sh (see SPEC.txt). Blender: +Z up, 1 unit = 1 m, fronts face -Y.
Material names are the contract (carapace, carapace_dull, amber, brass, silk, membrane, ...)."""
import math
import random

import bmesh
from mathutils import Vector

import kit

TAU = 2 * math.pi


# --- helpers -----------------------------------------------------------------------------------

def _ell(name, radii, loc, mat, seg=12, rings=8, fuzz=0.0, seed=0):
    """Ellipsoid from a UV sphere. fuzz > 0 pushes each vertex out by a random 0..fuzz fraction (bumpy fur)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    if fuzz:
        for v in bm.verts:
            v.co = v.co * (1.0 + fuzz * rng.random())
    bmesh.ops.scale(bm, vec=Vector(radii), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    return kit._obj(name, bm, mat, 40.0)


def _tube(name, pts, radii, mat, sides=6, cap=True):
    """Tube along a polyline with a radius per point: horns, claws, legs, strands. Caps are fans, so a sharp
    end is a small radius (about 0.004) and the fan apex sits on the last point."""
    P = [Vector(p) for p in pts]
    n = len(P)
    bm = bmesh.new()
    rings = []
    for i in range(n):
        d = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = x.cross(d).normalized()
        rings.append([bm.verts.new(P[i] + (x * math.cos(TAU * k / sides) + y * math.sin(TAU * k / sides)) * radii[i])
                      for k in range(sides)])
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(sides):
            bm.faces.new((a[k], b[k], b[(k + 1) % sides], a[(k + 1) % sides]))
    if cap:
        c0 = bm.verts.new(P[0])
        c1 = bm.verts.new(P[-1])
        for k in range(sides):
            bm.faces.new((c0, rings[0][(k + 1) % sides], rings[0][k]))
            bm.faces.new((c1, rings[-1][k], rings[-1][(k + 1) % sides]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, mat, 40.0)


def _tor(name, major, minor, loc, mat, rot=(0, 0, 0), seg=24, rseg=8):
    return kit.torus(name, major, minor, seg=seg, rseg=rseg, mat=mat, loc=loc, rot=rot)


def _bez(p, n):
    """Cubic Bezier through control points p (4 of them), n+1 samples."""
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append(tuple(u ** 3 * p[0][j] + 3 * u * u * t * p[1][j] + 3 * u * t * t * p[2][j] + t ** 3 * p[3][j]
                         for j in range(3)))
    return out


# the tarsal claw: out from the bead, down to z -0.6, hooking back up at the tip (+X side, forward a little)
MAIN_CLAW = [(0.0, 0.0, -0.16), (0.1, -0.04, -0.3), (0.24, -0.1, -0.45), (0.36, -0.15, -0.58),
             (0.42, -0.18, -0.6), (0.46, -0.2, -0.52)]
MAIN_R = [0.07, 0.062, 0.05, 0.04, 0.024, 0.006]


def _bead_claws(parts, bead_r=0.24):
    """The amber bead at the origin, a brass collar ring round its equator, and a carapace claw curling down
    from it with a smaller claw opposite. Shared by hook, lift and carriage."""
    parts.append(_ell("bead", (bead_r, bead_r, bead_r), (0, 0, 0), "amber", seg=10, rings=7))
    parts.append(_tor("collar", 0.27, 0.03, (0, 0, 0), "brass"))
    parts.append(_tor("claw_root", 0.09, 0.03, (0, 0, -0.16), "carapace"))
    parts.append(_tube("claw", MAIN_CLAW, MAIN_R, "carapace", sides=8))
    small = [(-0.7 * x, 0.8 * y, -0.16 + 0.7 * (z + 0.16)) for x, y, z in MAIN_CLAW]
    parts.append(_tube("claw_small", small, [r * 0.7 for r in MAIN_R], "carapace", sides=6))


def _wing(name, cx, cz, a, b, sign, y0, droop):
    """A flat wing in the XZ plane, elliptical, drooping at the outer edge, with a bevelled rim (three rows:
    inset top, full rim, inset bottom). UV is 0..1 over the wing's own bounds."""
    n = 28
    ring = []
    for k in range(n):
        t = TAU * k / n
        xa = cx + a * math.cos(t)
        z = cz + b * math.sin(t) - droop * max(0.0, xa - 0.3)
        ring.append((sign * xa, z))
    mx = sum(p[0] for p in ring) / n
    mz = sum(p[1] for p in ring) / n
    bm = bmesh.new()
    rows = []
    for scale, dy in ((0.86, -0.01), (1.0, 0.0), (0.86, 0.01)):
        rows.append([bm.verts.new((mx + (px - mx) * scale, y0 + dy, mz + (pz - mz) * scale)) for px, pz in ring])
    for r in range(2):
        for k in range(n):
            bm.faces.new((rows[r][k], rows[r + 1][k], rows[r + 1][(k + 1) % n], rows[r][(k + 1) % n]))
    ct = bm.verts.new((mx, y0 - 0.01, mz))
    cb = bm.verts.new((mx, y0 + 0.01, mz))
    for k in range(n):
        bm.faces.new((ct, rows[0][(k + 1) % n], rows[0][k]))
        bm.faces.new((cb, rows[2][k], rows[2][(k + 1) % n]))
    xs = [p[0] for p in ring]
    zs = [p[1] for p in ring]
    x0, z0 = min(xs), min(zs)
    w, h = max(xs) - x0, max(zs) - z0
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = ((lp.vert.co.x - x0) / w, (lp.vert.co.z - z0) / h)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit._obj(name, bm, "membrane", 40.0)


# --- hook --------------------------------------------------------------------------------------

def _stalk_body_r(z):
    """Radius of the hook stalk at height z: the collar bands flare to 0.11, the shaft is 0.07."""
    for k in range(3):
        zb = 0.3 + 0.27 * k
        if zb <= z < zb + 0.27:
            t = z - zb
            return 0.11 if 0.02 <= t <= 0.05 else (0.075 if t < 0.09 else 0.07)
    return 0.07


def B_hook():
    parts = []
    _bead_claws(parts)
    # three chitin segments, each with a flared collar, rising to z 1.11
    prof = [(0.1, 0.18), (0.09, 0.24)]
    for k in range(3):
        zb = 0.3 + 0.27 * k
        prof += [(0.07, zb), (0.11, zb + 0.02), (0.11, zb + 0.05), (0.07, zb + 0.09), (0.065, zb + 0.2)]
    prof += [(0.06, 1.08), (0.03, 1.105), (0.004, 1.11)]
    parts.append(kit.lathe("stalk", prof, segments=16, mat="carapace"))
    # silk thread: four turns wound in the grooves between the collars
    n = 60
    pts = []
    for i in range(n + 1):
        t = i / n
        z = 0.34 + 0.64 * t
        R = _stalk_body_r(z) + 0.008
        a = TAU * 4 * t
        pts.append((R * math.cos(a), R * math.sin(a), z))
    parts.append(_tube("thread", pts, [0.015] * (n + 1), "silk", sides=5, cap=False))
    kit.join("hook", parts)


# --- peg ---------------------------------------------------------------------------------------

def B_peg():
    parts = []
    prof = [(0.24, -0.05), (0.24, -0.03), (0.21, -0.005), (0.12, 0.0), (0.07, 0.01), (0.07, 0.07),
            (0.078, 0.08), (0.1, 0.1), (0.1, 0.14), (0.05, 0.15), (0.004, 0.15)]
    parts.append(kit.lathe("stud", prof, segments=20, mat="carapace"))
    for i in range(6):
        a = TAU * i / 6
        parts.append(_ell("nub%d" % i, (0.03, 0.03, 0.02), (0.18 * math.cos(a), 0.18 * math.sin(a), -0.005),
                          "carapace", seg=6, rings=4))
    parts.append(_ell("cap", (0.09, 0.09, 0.08), (0, 0, 0.16), "amber", seg=14, rings=8))
    parts.append(_tor("ring", 0.074, 0.01, (0, 0, 0.01), "brass", seg=24, rseg=6))
    parts.append(_tor("line", 0.078, 0.006, (0, 0, 0.045), "silk", seg=24, rseg=6))
    kit.join("peg", parts)


# --- key ---------------------------------------------------------------------------------------

def B_key():
    parts = []
    # bow: outer r 0.85, inner r 0.45, in the XZ plane (facing -Y)
    parts.append(kit.torus("bow", 0.65, 0.2, seg=48, rseg=14, mat="carapace", rot=(math.pi / 2, 0, 0)))
    for k in range(8):
        a0 = TAU * k / 8 + 0.2
        pts = []
        for s in range(6):
            u = s / 5
            r = 0.6 + 0.4 * u
            a = a0 + 0.35 * u * u
            pts.append((r * math.cos(a), 0.0, r * math.sin(a)))
        parts.append(_tube("lobe%d" % k, pts, [0.1, 0.1, 0.095, 0.075, 0.045, 0.012], "carapace", sides=6))
    for k in range(4):
        a0 = math.pi / 4 + k * math.pi / 2
        pts = []
        for s in range(6):
            u = s / 5
            r = 0.6 - 0.3 * u
            a = a0 - 0.3 * u * u
            pts.append((r * math.cos(a), 0.0, r * math.sin(a)))
        parts.append(_tube("inner%d" % k, pts, [0.08, 0.08, 0.07, 0.05, 0.03, 0.01], "carapace", sides=6))
    parts.append(_ell("bead", (0.18, 0.18, 0.18), (0, 0, 0), "amber", seg=10, rings=6))
    for k in range(4):
        a = k * math.pi / 2
        parts.append(_tube("spoke%d" % k, [(0.15 * math.cos(a), 0, 0.15 * math.sin(a)),
                                           (0.5 * math.cos(a), 0, 0.5 * math.sin(a))],
                           [0.03, 0.03], "brass", sides=6))
    # shaft: brass, with a collar every 0.6 m, from the top of the bow to z 4.6
    prof = [(0.13, 0.7)]
    for zc in (1.45, 2.05, 2.65, 3.25, 3.85, 4.45):
        prof += [(0.13, zc - 0.04), (0.17, zc - 0.03), (0.17, zc + 0.03), (0.13, zc + 0.04)]
    prof += [(0.13, 4.6)]
    parts.append(kit.lathe("shaft", prof, segments=20, mat="brass"))
    # ward plate 0.8 wide, 0.6 tall, with mandible teeth along its top
    parts.append(kit.box("ward", (0.8, 0.12, 0.45), loc=(0, 0, 4.825), mat="brass", bevel=0.03))
    for x in (-0.32, -0.16, 0.0, 0.16, 0.32):
        sg = 1 if x >= 0 else -1
        parts.append(_tube("tooth", [(x, 0, 5.0), (x + 0.03 * sg, 0, 5.1), (x + 0.05 * sg, 0, 5.2)],
                           [0.06, 0.04, 0.004], "carapace", sides=4))
    kit.join("key", parts)


# --- lift --------------------------------------------------------------------------------------

def B_lift():
    parts = []
    _bead_claws(parts)
    parts.append(kit.lathe("hub", [(0.1, 0.18), (0.085, 0.3), (0.085, 0.5), (0.11, 0.52), (0.11, 0.58),
                                   (0.004, 0.62)], segments=16, mat="brass"))
    parts.append(kit.lathe("disc", [(0.1, 0.25), (0.7, 0.25), (0.74, 0.27), (0.74, 0.53), (0.7, 0.55),
                                    (0.1, 0.55)], segments=40, mat="carapace_dull"))
    # twelve curved mandibles round the rim, hooking forward
    for k in range(12):
        a0 = TAU * k / 12
        pts = []
        for s in range(6):
            u = s / 5
            r = 0.66 + 0.26 * u
            a = a0 + 0.22 * u * u
            pts.append((r * math.cos(a), r * math.sin(a), 0.4))
        parts.append(_tube("tooth%d" % k, pts, [0.12, 0.12, 0.11, 0.09, 0.06, 0.02], "carapace", sides=6))
    # six brass spokes on the disc face
    for k in range(6):
        a = TAU * k / 6
        parts.append(_tube("spoke%d" % k, [(0.12 * math.cos(a), 0.12 * math.sin(a), 0.57),
                                           (0.66 * math.cos(a), 0.66 * math.sin(a), 0.57)],
                           [0.03, 0.03], "brass", sides=6))
    kit.join("lift", parts)


# --- carriage ----------------------------------------------------------------------------------

def B_carriage():
    parts = []
    _bead_claws(parts)
    wheel = [(0.02, -0.06), (0.25, -0.06), (0.25, -0.04), (0.22, -0.04), (0.22, 0.04), (0.25, 0.04),
             (0.25, 0.06), (0.02, 0.06)]
    for x in (-0.35, 0.35):
        w = kit.lathe("wheel", wheel, segments=24, mat="brass")
        kit.place(w, loc=(x, 0, 1.5), rot=(math.pi / 2, 0, 0))
        parts.append(w)
        parts.append(_tube("axle", [(x, -0.4, 1.5), (x, 0.4, 1.5)], [0.035, 0.035], "brass", sides=6))
    # yoke: two domed carapace side shields the axles run through, and a convex hood over the top
    parts.append(_ell("plate_L", (0.5, 0.07, 0.3), (0, -0.3, 1.72), "carapace", seg=24, rings=12))
    parts.append(_ell("plate_R", (0.5, 0.07, 0.3), (0, 0.3, 1.72), "carapace", seg=24, rings=12))
    parts.append(_ell("hood", (0.56, 0.4, 0.1), (0, 0, 1.96), "carapace", seg=28, rings=12))
    # jointed chitin arm from the yoke down to the bead
    arm = [(0, 0, 1.92), (0, 0, 1.6), (0.05, 0, 1.25), (0, 0, 0.9), (-0.04, 0, 0.6), (0, 0, 0.2)]
    parts.append(_tube("arm", arm, [0.06, 0.05, 0.05, 0.045, 0.04, 0.035], "carapace", sides=8))
    for i, p in enumerate(arm[1:5]):
        parts.append(_ell("joint%d" % i, (0.06, 0.06, 0.06), p, "carapace", seg=8, rings=5))
    kit.join("carriage", parts)


# --- track -------------------------------------------------------------------------------------

def B_track():
    parts = []
    # I-beam 0.3 x 0.3 along X: brass flanges, carapace web
    parts.append(kit.box("flange_top", (30, 0.3, 0.05), loc=(0, 0, 0.125), mat="brass"))
    parts.append(kit.box("flange_bot", (30, 0.3, 0.05), loc=(0, 0, -0.125), mat="brass"))
    parts.append(kit.box("web", (30, 0.04, 0.2), loc=(0, 0, 0), mat="carapace"))
    rivet = [(0.0, 0.0), (0.018, 0.0), (0.02, 0.005), (0.0, 0.012)]
    for i in range(60):
        x = -14.75 + 0.5 * i
        parts.append(kit.lathe("rivet", rivet, segments=5, mat="brass", cap=False))
        kit.place(parts[-1], loc=(x, 0, 0.15))
    # hanging brackets every 5 m: curved chitin straps up to z 1.5
    for i in range(6):
        x = -12.5 + 5 * i
        pts = [(x, -0.06, 0.15), (x, -0.12, 0.5), (x, -0.14, 0.9), (x, -0.1, 1.3), (x, 0.0, 1.5)]
        parts.append(_tube("bracket", pts, [0.035, 0.035, 0.03, 0.028, 0.02], "carapace", sides=5))
    kit.join("track", parts)


# --- moth --------------------------------------------------------------------------------------

def B_moth():
    parts = []
    # fuzzy silk body: thorax, abdomen, head
    parts.append(_ell("thorax", (0.3, 0.32, 0.3), (0, 0, 1.4), "silk", seg=24, rings=14, fuzz=0.05, seed=1))
    parts.append(_ell("abdomen", (0.16, 0.45, 0.16), (0, 0.72, 1.3), "silk", seg=18, rings=10, fuzz=0.05, seed=2))
    parts.append(_ell("head", (0.2, 0.2, 0.2), (0, -0.4, 1.5), "silk", seg=14, rings=8, fuzz=0.05, seed=3))
    for s, side in ((-1, "L"), (1, "R")):
        parts.append(_ell("eye" + side, (0.05, 0.04, 0.05), (s * 0.1, -0.56, 1.56), "ink", seg=8, rings=5))
        # feathery antenna: a curved shaft with barbs on both sides
        ax = _bez([(s * 0.08, -0.48, 1.66), (s * 0.2, -0.66, 1.9), (s * 0.42, -0.7, 2.15), (s * 0.55, -0.72, 2.2)], 16)
        parts.append(_tube("antenna" + side, ax, [0.02 - 0.012 * i / 16 for i in range(17)], "silk", sides=6))
        for i in range(1, 16):
            p = Vector(ax[i])
            d = (Vector(ax[i + 1]) - Vector(ax[i - 1])).normalized()
            w = d.cross(Vector((0, 0, 1))).normalized()
            L = 0.16 - 0.06 * i / 15
            for sd in (-1, 1):
                out = (w * sd + d * 0.35 + Vector((0, 0, 0.2))).normalized()
                parts.append(_tube("barb", [tuple(p), tuple(p + out * L * 0.5), tuple(p + out * L)],
                                   [0.008, 0.006, 0.002], "silk", sides=4))
    # six thin legs, three a side
    for s in (-1, 1):
        for y in (-0.15, 0.05, 0.25):
            pts = [(s * 0.22, y, 1.22), (s * 0.52, y - 0.05, 1.0), (s * 0.42, y + 0.02, 0.7), (s * 0.5, y, 0.6)]
            parts.append(_tube("leg", pts, [0.035, 0.025, 0.018, 0.008], "carapace_dull", sides=5))
    # four membrane wings: forewings broad, hindwings behind and smaller; total span 3.2 m
    for s, sd in ((1, "R"), (-1, "L")):
        parts.append(_wing("forewing_" + sd, 0.9, 1.55, 0.7, 0.5, s, -0.02, 0.12))
        parts.append(_wing("hindwing_" + sd, 0.6, 1.1, 0.45, 0.36, s, 0.04, 0.08))
    # brass chain of five links from the thorax to the finger-bell whose top sits at the origin
    for k in range(5):
        rot = (math.pi / 2, 0, 0) if k % 2 == 0 else (0, math.pi / 2, 0)
        parts.append(_tor("link%d" % k, 0.09, 0.014, (0, 0, 0.12 + 0.22 * k), "brass", rot=rot, seg=16, rseg=6))
    parts.append(kit.lathe("bell", [(0.1, -0.2), (0.09, -0.17), (0.06, -0.12), (0.05, -0.06), (0.04, -0.02),
                                    (0.03, 0.0)], segments=14, mat="brass"))
    kit.join("moth", parts)


def build(args):
    fn = globals().get("B_" + args[0])
    if fn is None:
        raise SystemExit("unknown anchor: " + args[0])
    fn(*args[1:])
