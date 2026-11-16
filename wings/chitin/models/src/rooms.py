"""Chitin Court room shells (pass 3): one generic builder for the five room shells in shells.json.

Build: tools/blender_build.sh wings/chitin/models/src/rooms.py wings/chitin/models/<room>.glb <room>
  <room> is shell_gate, shell_districts, shell_foundry, shell_gallery or shell_arena.

Geometry comes from that room's shells.json entry (GODOT world, mapped to Blender (x, -z, y)): a
carapace vault over walls rising from the floor to wall_top, swept along the axis a[0]..a[1], section
across c[0]..c[1] (collision wall inner faces). Below wall_top every wall vertex lies between its
collision face and at most `bulge` into the room (never more than 0.05 m behind it); the self-check
measures the final vertex positions in Godot coordinates and asserts this.

Comb is NOT painted on the shell faces. Comb patches (comb_patch.py) are separate blob meshes placed on
the finished shell and exported as their own model: build "<room>" gives the shell only, build "<room>_comb"
gives the comb patches only (same deterministic shell, own 60000-tri budget).
"""
import json
import math
import os
import random
import sys
import zlib

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import comb_patch  # noqa: E402

FOOT_H = 0.6        # floor fillet height: the wall rolls out onto the floor
RIB_HALF = 0.3      # rib half-width along the axis (rib is 0.6 m wide)
RIB_UP = 0.6        # rib depth above wall_top, reached 0.8 m above it
VAULT_N = 1.5       # superellipse exponent of the vault: pointed-ish crown, vertical springing
TRANS = 1.5         # blend length across floor steps (drops)
CAP_OUT = 0.95      # closed-end dome depth as a fraction of bulge (stays inside the bulge limit)
CAP_RINGS = 4
TOL_BEHIND = 0.05   # max distance a wall may sit behind its collision face
VAULT_NOISE = 0.6   # vault irregularity above wall_top
LIP_SIDES = 6
SHELL_CAP = 58500   # shell alone (its own model) is coarsened above this (MOSR_MAX_TRIS is 60000)
TOTAL_CAP = 58500   # comb model alone (its own model) stops placing patches at this
CHEAP_COMB_ROOMS = ("shell_arena", "shell_foundry")  # low-poly comb cells (comb_patch cheap=True)
MAT_NAMES = ["carapace", "carapace_dull"]
SEED_V = Vector((7.3, 1.1, 3.7))


# --- room data and mapping -----------------------------------------------------------------------

def _room(name):
    with open(os.path.join(HERE, "shells.json")) as fh:
        rooms = json.load(fh)["rooms"]
    for r in rooms:
        if r["name"] == name:
            return r
    raise SystemExit("rooms.py: unknown room %r" % name)


def _godot(room, s, q, y):
    """Axis coordinate s, cross coordinate q, height y -> Godot (x, y, z). Linear, so also maps directions."""
    return (s, y, q) if room["axis"] == "x" else (q, y, s)


def _blender(g):
    return Vector((g[0], -g[2], g[1]))


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


# --- floor: drops blended over TRANS -------------------------------------------------------------

def _step_floor(room, s):
    for lo, hi, y in room["drops"]:
        if lo <= s < hi:
            return y, 0.0
    return room["floor"], 1.0


def _blend(room, s):
    """Bottom height and fillet weight at station s: a box average of the step function, so
    adjacent drops blend piecewise instead of double-counting."""
    n = 17
    vals, fws = [], []
    for i in range(n):
        x = s - TRANS / 2 + TRANS * i / (n - 1)
        y, fw = _step_floor(room, x)
        vals.append(y)
        fws.append(fw)
    b = vals[0] if max(vals) - min(vals) < 1e-12 else sum(vals) / n
    fw = fws[0] if max(fws) - min(fws) < 1e-12 else sum(fws) / n
    return b, fw


# --- vault section ---------------------------------------------------------------------------------

def _vault(room):
    c0, c1 = room["c"]
    H = (c1 - c0) / 2.0
    uc = (c0 + c1) / 2.0
    ys = room["wall_top"] + 1.5
    D = room["peak"] - ys
    assert H > 0 and D > 0, "vault needs positive half-width and rise"

    def yof(u):
        x = min(1.0, abs(u) / H)
        return ys + D * max(0.0, 1.0 - x ** VAULT_N) ** (1.0 / VAULT_N)

    def slope(u):
        x = min(1.0 - 1e-9, abs(u) / H)
        sg = 1.0 if u >= 0 else -1.0
        return -D * max(1.0 - x ** VAULT_N, 1e-12) ** (1.0 / VAULT_N - 1.0) * x ** (VAULT_N - 1.0) * sg / H

    return H, uc, ys, D, yof, slope


def _arch(H, yof, slope, ds):
    """Vault points resampled at ~ds arc length: (u, y, inward_nu, inward_ny), springing to springing."""
    M = 4000
    pts = [(-H + 2.0 * H * i / M, 0.0) for i in range(M + 1)]
    pts = [(u, yof(u)) for u, _ in pts]
    cum = [0.0]
    for i in range(1, M + 1):
        cum.append(cum[-1] + math.dist(pts[i], pts[i - 1]))
    L = cum[-1]
    n = max(6, round(L / ds))
    out = []
    j = 0
    for k in range(n + 1):
        tgt = L * k / n
        while j < M - 1 and cum[j + 1] < tgt:
            j += 1
        seg = cum[j + 1] - cum[j]
        f = min(1.0, max(0.0, (tgt - cum[j]) / seg)) if seg > 0 else 0.0
        u = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f
        y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f
        sl = slope(u)
        nn = math.hypot(sl, 1.0)
        out.append((u, y, sl / nn, -1.0 / nn))
    return out


def _section(H, ys, arch, b, Nw):
    """Section points left foot -> left wall -> vault -> right wall -> right foot.
    Each: (u, y, inward_nu, inward_ny, kind, tau). Wall counts are fixed per room so stations loft."""
    pts = []
    for k in range(Nw):
        tau = k / Nw
        pts.append((-H, b + (ys - b) * tau, 1.0, 0.0, "w", tau))
    for u, y, nu, ny in arch:
        pts.append((u, y, nu, ny, "a", 1.0))
    for k in range(Nw - 1, -1, -1):
        tau = k / Nw
        pts.append((H, b + (ys - b) * tau, -1.0, 0.0, "w", tau))
    return pts


def _foot(t, fw, bulge):
    """Floor fillet: inward depth bulge at the floor, flush (horizontal) there, zero at FOOT_H."""
    if t >= FOOT_H or fw <= 0.0:
        return 0.0
    return fw * bulge * (1.0 - math.sqrt(max(t, 0.0) / FOOT_H)) ** 2


def _ribw(s, ribs):
    best = min(abs(s - c) for c in ribs) if ribs else 9.0
    if best <= RIB_HALF:
        return 1.0
    if best >= RIB_HALF + 0.05:
        return 0.0
    return (RIB_HALF + 0.05 - best) / 0.05


def _rib_amp(y, wt, bulge):
    return bulge + (RIB_UP - bulge) * _smooth(wt, wt + 0.8, y)


def _hash(i, j):
    h = math.sin(i * 127.1 + j * 311.7) * 43758.5453
    return h - math.floor(h)


def _plate(s, arc, cs, ca, bulge):
    """Shingle plate field: domed cells, zero at the seams, at most 0.66 * bulge deep."""
    row = math.floor(arc / ca)
    fx = s / cs + 0.5 * (row % 2)
    col = math.floor(fx)
    dome = math.sin(math.pi * (fx - col)) * math.sin(math.pi * (arc / ca - row))
    if dome <= 0.0:
        return 0.0
    return bulge * 0.55 * dome ** 0.7 * (0.8 + 0.4 * _hash(col, row))


# --- closed ends, lips and openings -----------------------------------------------------------------

def _strip(bm, A, B):
    fs = []
    N = len(A)
    for i in range(N - 1):
        fs.append(bm.faces.new((A[i], A[i + 1], B[i + 1], B[i])))
    fs.append(bm.faces.new((A[N - 1], A[0], B[0], B[N - 1])))  # close the foot chord to the floor
    return fs


def _cap(bm, room, ring, end_s, sign, bulge, vband, vfoot):
    """Closed end: a shallow dome of rings shrinking toward the section centroid, fanned shut.
    Foot points keep their floor height so the end wall meets the floor flush."""
    prev = [r[0] for r in ring]
    qy = [(r[1], r[2], r[3]) for r in ring]
    cu = sum(q for q, _, _ in qy) / len(qy)
    cy = sum(y for _, y, _ in qy) / len(qy)
    faces = []
    for j in range(1, CAP_RINGS + 1):
        lam = 1.0 - j / (CAP_RINGS + 1.0)
        sc = end_s + sign * CAP_OUT * bulge * (1.0 - lam * lam)
        cur = []
        for q, y, foot in qy:
            qn = cu + lam * (q - cu)
            yn = y if foot else cy + lam * (y - cy)
            v = bm.verts.new(_blender(_godot(room, sc, qn, yn)))
            vband[v], vfoot[v] = False, foot
            cur.append(v)
        faces += _strip(bm, prev, cur)
        prev = cur
    sc = end_s + sign * CAP_OUT * bulge
    c = bm.verts.new(_blender(_godot(room, sc, cu, cy)))
    vband[c], vfoot[c] = False, False
    N = len(prev)
    for i in range(N - 1):
        faces.append(bm.faces.new((c, prev[i], prev[i + 1])))
    faces.append(bm.faces.new((c, prev[N - 1], prev[0])))
    return faces


def _mat_index(f, vband):
    """0 carapace, 1 dark floor band (the first 0.6 m of the wall above the floor)."""
    return 1 if any(vband.get(v, False) for v in f.verts) else 0


def _lips(bm, roomc, rl, vfoot, wt):
    """Rolled lip on every open boundary edge above wall_top (below it a lip would push walls past
    the bulge limit, so those edges stay plain). Each lip is a small closed tube set 0.9 rl toward the room."""
    edges = [e for e in bm.edges if len(e.link_faces) == 1]
    n = 0
    for e in edges:
        v1, v2 = e.verts
        if vfoot.get(v1, False) and vfoot.get(v2, False):
            continue
        if min(v1.co.z, v2.co.z) < wt - 1e-6:
            continue
        p1, p2 = v1.co.copy(), v2.co.copy()
        mid = (p1 + p2) / 2.0
        if (p2 - p1).length < 1e-6:
            continue
        dirr = roomc - mid
        if dirr.length < 1e-6:
            continue
        off = dirr.normalized() * (0.9 * rl)
        a, b = p1 + off, p2 + off
        ed = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(ed.z) < 0.9 else Vector((1, 0, 0))
        u = ed.cross(ref).normalized()
        w = ed.cross(u)
        ra, rb = [], []
        for k in range(LIP_SIDES):
            t = 2.0 * math.pi * k / LIP_SIDES
            o = (u * math.cos(t) + w * math.sin(t)) * rl
            ra.append(bm.verts.new(a + o))
            rb.append(bm.verts.new(b + o))
        fs = []
        for k in range(LIP_SIDES):
            kk = (k + 1) % LIP_SIDES
            fs.append(bm.faces.new((ra[k], ra[kk], rb[kk], rb[k])))
        fs.append(bm.faces.new(tuple(ra)))
        fs.append(bm.faces.new(tuple(reversed(rb))))
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        n += 1
    return n


# --- comb patch hooks (rooms) -----------------------------------------------------------------------

def _ribs(room):
    a0, a1 = room["a"]
    ribs = []
    k = 0
    while a0 + room["rib"] * (k + 0.5) <= a1 - 0.5:
        ribs.append(a0 + room["rib"] * (k + 0.5))
        k += 1
    return ribs


def _comb_hooks(room):
    """Flows, radius and dn for comb_patch.build_flows, from this room's data.

    3-6 flows per shell, each a dense sample list of (origin_b, dir_b, size). Arch flows run from the crown
    down one wall (fixed station along the axis, the section angle sweeping from the crown); axis flows run
    along the vault (fixed section angle, the station sweeping the length). Size is a bump: small at both ends,
    full in the middle. Flows are spaced so the dark wall stays between them."""
    a0, a1 = room["a"]
    c0, c1 = room["c"]
    uc = (c0 + c1) / 2.0
    H = (c1 - c0) / 2.0
    ax = room["axis"]
    floor = room["floor"]
    peak = room["peak"]
    mid = (floor + peak) / 2.0
    closed_s = room["start"] == "closed"
    closed_e = room["end"] == "closed"
    openings = room["openings"]
    rng = random.Random(zlib.crc32(("flows " + room["name"]).encode()) & 0xFFFFFFFF)
    NS = 240

    def ray(s, phi):
        origin = _blender(_godot(room, s, uc, mid))
        return origin, _blender(_godot(room, 0.0, math.cos(phi), math.sin(phi)))

    def bump(t):
        return math.sin(math.pi * (0.04 + 0.92 * t)) ** 0.6

    def flow_of(path):
        out = []
        for i in range(NS):
            t = i / (NS - 1.0)
            origin, d = path(t)
            out.append((origin, d, bump(t)))
        return out

    flows, arch_s, axis_phi = [], [], []
    room_len = a1 - a0
    n_flows = rng.randint(4, 6)
    for _ in range(400):
        if len(flows) >= n_flows:
            break
        if rng.random() < 0.5:
            s0 = rng.uniform(a0 + 4.0, a1 - 4.0)
            if any(abs(s0 - s) < 2.0 * comb_patch.MAX_R + 3.0 for s in arch_s):
                continue
            side = rng.choice((-1.0, 1.0))
            end = rng.uniform(-25.0, 40.0)
            arch_s.append(s0)

            def path(t, s0=s0, side=side, end=end):
                phi = math.radians(88.0 + (end - 88.0) * t)
                return ray(s0, math.pi - phi if side < 0 else phi)
            flows.append(flow_of(path))
        else:
            phi_deg = rng.uniform(20.0, 80.0)
            if any(abs(phi_deg - p) < 20.0 for p in axis_phi):
                continue
            axis_phi.append(phi_deg)
            L = rng.uniform(0.5, 0.9) * (room_len - 6.0)
            sa = a0 + 3.0 + rng.uniform(0.0, room_len - 6.0 - L)

            def path(t, phi_deg=phi_deg, sa=sa, L=L):
                return ray(sa + L * t, math.radians(phi_deg))
            flows.append(flow_of(path))

    def radius(g):
        """Largest blob allowed at g (Godot): 0 on floors, inside openings, past closed ends."""
        y = g[1]
        if y < floor + 0.8:
            return 0.0
        for x0, y0, z0, x1, y1, z1 in openings:
            if x0 - 1.2 <= g[0] <= x1 + 1.2 and y0 - 1.2 <= g[1] <= y1 + 1.2 and z0 - 1.2 <= g[2] <= z1 + 1.2:
                return 0.0
        s = g[0] if ax == "x" else g[2]
        lim = min(comb_patch.MAX_R, 1.5 * H)
        if closed_s:
            lim = min(lim, s - a0 - 1.0)
        if closed_e:
            lim = min(lim, a1 - s - 1.0)
        return max(0.0, lim)

    def dn(g):
        s = g[0] if ax == "x" else g[2]
        q = g[2] if ax == "x" else g[0]
        dl = [q - c0, c1 - q]
        if closed_s:
            dl.append(s - a0)
        if closed_e:
            dl.append(a1 - s)
        return min(dl, key=abs)

    return flows, radius, dn


# --- build -----------------------------------------------------------------------------------------

def _build_room(room, grid):
    """Shell only (bmesh, info). Comb is built from the same shell by build() for the _comb model."""
    a0, a1 = room["a"]
    c0, c1 = room["c"]
    ax = room["axis"]
    bulge = room["bulge"]
    wt = room["wall_top"]
    floor = room["floor"]
    H, uc, ys, D, yof, slope = _vault(room)
    arch = _arch(H, yof, slope, grid)
    b_min = min([floor] + [d[2] for d in room["drops"]])
    Nw = max(3, round((ys - b_min) / (1.2 * grid)))
    L = a1 - a0
    n = max(2, math.ceil(L / grid))
    ribs = _ribs(room)
    st = set(round(a0 + L * i / n, 6) for i in range(n + 1))
    for c in ribs:
        for off in (-0.35, -0.3, 0.3, 0.35):
            x = round(c + off, 6)
            if a0 < x < a1:
                st.add(x)
    stations = sorted(st)
    cs = ca = 3.0 * grid
    roomc = _blender(_godot(room, (a0 + a1) / 2.0, uc, (floor + room["peak"]) / 2.0))

    bm = bmesh.new()
    vband, vfoot = {}, {}
    rings = []
    for s in stations:
        b, fw = _blend(room, s)
        base = _section(H, ys, arch, b, Nw)
        arc = [0.0]
        for i in range(1, len(base)):
            arc.append(arc[-1] + math.dist(base[i][:2], base[i - 1][:2]))
        rw = _ribw(s, ribs)
        ring = []
        for i, (u, y, nu, ny, kind, tau) in enumerate(base):
            foot = kind == "w" and tau == 0.0 and fw == 1.0 and abs(b - floor) < 1e-9
            d = _foot(y - b, fw, bulge) if kind == "w" else 0.0
            d = max(d, rw * _rib_amp(y, wt, bulge), _plate(s, arc[i], cs, ca, bulge) * (1.0 - rw), 0.0)
            if y < wt:
                d = min(d, 0.97 * bulge)  # margin for float round-trip through Blender
            else:
                g0 = _godot(room, s, uc + u + nu * d, y + ny * d)
                d += VAULT_NOISE * _smooth(wt, wt + 2.0, y) * noise.noise(Vector(g0) * 0.25 + SEED_V)
            g = _godot(room, s, uc + u + nu * d, y + ny * d)
            band = kind == "w" and (y - b) < FOOT_H
            bv = bm.verts.new(_blender(g))
            vband[bv], vfoot[bv] = band, foot
            q = g[2] if ax == "x" else g[0]
            ring.append((bv, q, g[1], foot))
        rings.append(ring)

    shell = []
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for i in range(len(A) - 1):
            shell.append(bm.faces.new((A[i][0], A[i + 1][0], B[i + 1][0], B[i][0])))
    caps = []
    if room["start"] == "closed":
        caps += _cap(bm, room, rings[0], a0, +1.0, bulge, vband, vfoot)
    if room["end"] == "closed":
        caps += _cap(bm, room, rings[-1], a1, -1.0, bulge, vband, vfoot)
    faces = shell + caps

    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    bm.normal_update()
    tot = sum(f.normal.dot(roomc - f.calc_center_median()) for f in faces)
    if tot < 0:
        for f in faces:
            f.normal_flip()
    for f in faces:
        f.material_index = _mat_index(f, vband)

    for lo_hi in room["openings"]:
        x0, y0, z0, x1, y1, z1 = lo_hi
        lo = (x0, -z1, y0)
        hi = (x1, -z0, y1)
        dels = [f for f in bm.faces
                if all(lo[i] <= f.calc_center_median()[i] <= hi[i] for i in range(3))]
        bmesh.ops.delete(bm, geom=dels, context="FACES")

    rl = bulge * 0.45
    _lips(bm, roomc, rl, vfoot, wt)
    shell_tris = sum(len(f.verts) - 2 for f in bm.faces)
    info = {"tris": shell_tris, "stations": len(stations), "arch_pts": len(arch), "Nw": Nw,
            "ribs": len(ribs), "grid": grid}
    return bm, info


def _check_vault(room):
    H, uc, ys, D, yof, slope = _vault(room)
    assert abs(yof(0.0) - room["peak"]) < 1e-9, "crown must sit at peak"
    prev = None
    for i in range(0, 201):
        y = yof(H * i / 200.0)
        if prev is not None:
            assert y <= prev + 1e-12, "vault must rise strictly toward the crown"
        prev = y


def _selfcheck(bm, room, name):
    """Final vertex positions, converted back to Godot, measured against the nearest collision face.
    Below wall_top, a wall vertex must sit between -TOL_BEHIND and bulge into the room."""
    c0, c1 = room["c"]
    a0, a1 = room["a"]
    wt = room["wall_top"]
    bulge = room["bulge"]
    ax = room["axis"]
    closed_s = room["start"] == "closed"
    closed_e = room["end"] == "closed"
    lo, hi, n_wall, n_free = 9.0, -9.0, 0, 0
    for v in bm.verts:
        gx, gy, gz = v.co.x, v.co.z, -v.co.y
        s = gx if ax == "x" else gz
        q = gz if ax == "x" else gx
        assert a0 - TOL_BEHIND <= s <= a1 + TOL_BEHIND, "%s: vertex outside axis range" % name
        if gy >= wt:
            continue
        dl = [q - c0, c1 - q]
        if closed_s:
            dl.append(s - a0)
        if closed_e:
            dl.append(a1 - s)
        dn = min(dl, key=abs)
        if abs(dn) > 1.0:
            n_free += 1
            continue
        n_wall += 1
        lo, hi = min(lo, dn), max(hi, dn)
        assert -TOL_BEHIND - 1e-9 <= dn <= bulge + 1e-6, (
            "%s: wall vertex at godot (%.2f, %.2f, %.2f) sits %.3f into room (limit %.2f / behind %.2f)"
            % (name, gx, gy, gz, dn, bulge, TOL_BEHIND))
    print("SELFCHECK %s: %d wall verts below wall_top, inward range [%.3f, %.3f] within [-%.2f, %.2f]; "
          "%d free (open-end lips/caps off a wall)" % (name, n_wall, lo, hi, TOL_BEHIND, bulge, n_free))


def build(args):
    """<room> -> shell model; <room>_comb -> comb-patch model (its own mesh, built on the same shell)."""
    name = args[0]
    comb_only = name.endswith("_comb")
    base = name[:-len("_comb")] if comb_only else name
    room = _room(base)
    _check_vault(room)
    grid = room["grid"]
    for _ in range(8):
        bm, st = _build_room(room, grid)
        if st["tris"] <= SHELL_CAP:
            break
        print("COARSEN %s grid %.3f -> %.3f (shell tris %d)" % (base, grid, grid * 1.08, st["tris"]))
        bm.free()
        grid *= 1.08
    assert st["tris"] <= SHELL_CAP, "%s: shell still over %d tris" % (base, SHELL_CAP)
    print("ROOM %s grid %.3f shell tris %d stations %d arch_pts %d wall_pts_per_side %d ribs %d"
          % (base, grid, st["tris"], st["stations"], st["arch_pts"], st["Nw"], st["ribs"]))
    _selfcheck(bm, room, base)

    if comb_only:
        flows, radius, dn = _comb_hooks(room)
        pbm, pst = comb_patch.build_flows(bm, base + "_comb", flows, radius, dn,
                                          room["wall_top"], room["bulge"], TOTAL_CAP,
                                          cheap=base in CHEAP_COMB_ROOMS)
        bm.free()
        print("TRIS %s comb %d (cap 60000, budget %d)" % (base + "_comb", pst["tris"], TOTAL_CAP))
        assert pst["tris"] <= 60000, pst["tris"]
        return comb_patch.make_object(base + "_comb", pbm)

    print("TRIS %s shell %d (cap %d)" % (base, st["tris"], SHELL_CAP))
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40.0):
            e.smooth = False
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    for m in MAT_NAMES:
        me.materials.append(bpy.data.materials.get(m) or bpy.data.materials.new(m))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob
