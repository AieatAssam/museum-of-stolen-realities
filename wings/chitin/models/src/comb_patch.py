"""Comb patches for the Chitin Court shells (shared by rooms.py and throat.py).

A patch is an organic mound of honeycomb grown onto the carapace: a lobed outline with a few satellite
clusters, hex cells 0.6-0.7 m across (wax walls and a wax top ring, ~30 tris each), 70% domed amber caps,
25% open dull cells, 5% broken. Cells are tallest at the centre of the patch and shortest at its rim, so it
swells out of the shell; heights are limited so that vertices below wall_top stay within the bulge.

Patches are exported as their own models "<shell>_comb" (materials wax, amber, carapace_dull by index 0-2).
A patch is kept only if every vertex passes the wall check below wall_top (inward distance in [-0.05, bulge]).
"""
import math
import random
import zlib

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import kit

WALL = 0.04         # cell wall thickness (m)
LIFT = 0.02         # cell bases sit this far above the shell
CAP_DOME = 0.05     # domed amber cap height above the top ring
FLOOR_DEPTH = 0.06  # open cell dish depth below the top ring
ROLL_R = 0.05       # rolled wax rim radius
ROLL_LIFT = 0.03    # rim centreline above the shell
ROLL_SIDES = 4
OUT_N = 20          # outline samples
MIN_R = 1.5         # blob radius range (m)
MAX_R = 2.6
HMAX = 0.5          # mound height at the centre (m); clamped below wall_top by the bulge
COVER = 0.12        # target share of shell surface covered by blobs
MEAN_AREA = 12.0    # mean blob area (m2), for the patch count
SAT_R = 0.8         # satellite cluster radius (m)
MIN_DEPTH = 0.06
TOL_BEHIND = 0.05
COS30 = math.sqrt(3.0) / 2.0
SQ3 = math.sqrt(3.0)
MAT_NAMES = ["wax", "amber", "carapace_dull"]


def to_g(v):
    """Blender (x, y, z) -> Godot (x, y, z)."""
    return (v.x, v.z, -v.y)


def _blob(rng, R):
    """Lobed outline: 4-7 irregular lobes over a circle of radius R (angle -> radius)."""
    k = rng.randint(4, 7)
    a1, p1 = rng.uniform(0.12, 0.18), rng.uniform(0.0, math.tau)
    a2, p2 = rng.uniform(0.03, 0.07), rng.uniform(0.0, math.tau)
    return lambda th: R * (1.0 + a1 * math.sin(k * th + p1) + a2 * math.sin((k + 1) * th + p2))


def _plan(bvh, rng, loc, N, R, dn, wt, bulge):
    """Plan one patch centred on loc (Blender) with inward normal N. Returns (verts, faces, cells, tris),
    or None if the patch cannot be made to pass the wall check. faces: (index tuple, material, smooth)."""
    ref = Vector((0.0, 0.0, 1.0)) if abs(N.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    t1 = N.cross(ref).normalized()
    t2 = N.cross(t1)
    phi = rng.uniform(0.0, math.tau)
    cp, sp = math.cos(phi), math.sin(phi)
    t1, t2 = t1 * cp + t2 * sp, t2 * cp - t1 * sp
    rad = _blob(rng, R)
    r = rng.uniform(0.30, 0.36)              # cell circumradius: 0.6-0.72 m across corners
    ri = r - WALL / COS30                    # inner corner radius for 0.04 m flats
    ANG = [k * math.pi / 3.0 for k in range(6)]
    sats = []
    for _ in range(rng.randint(0, 2)):
        th = rng.uniform(0.0, math.tau)
        d = rad(th) + 0.5 * r
        sats.append((d * math.cos(th), d * math.sin(th)))
    verts, faces = [], []

    def add(p):
        verts.append(p)
        return len(verts) - 1

    def face(idx, want, mat, smooth):
        a, b, c = (verts[i] for i in idx[:3])
        if (b - a).cross(c - a).dot(want) < 0:
            idx = tuple(reversed(idx))
        faces.append((idx, mat, smooth))

    def surf(u, v):
        h = bvh.ray_cast(loc + t1 * u + t2 * v + N, -N, 2.0)
        if h[0] is None:
            return None
        n = h[1].normalized()
        return h[0], (n if n.dot(N) >= 0.0 else -n)

    def clampr(u, v):
        rho = math.hypot(u, v)
        lim = rad(math.atan2(v, u)) - 0.02
        if lim > 0.0 and rho > lim:
            k = lim / rho
            return u * k, v * k
        return u, v

    def cell(cu, cv, kind, h):
        outs = [clampr(cu + r * math.cos(a), cv + r * math.sin(a)) for a in ANG]
        ins = [clampr(cu + ri * math.cos(a), cv + ri * math.sin(a)) for a in ANG]
        bo, bi, maxdn = [], [], -1e9
        for pts, out in ((outs, bo), (ins, bi)):
            for u, v in pts:
                hit = surf(u, v)
                if hit is None:
                    return False
                b = hit[0] + hit[1] * LIFT
                out.append((b, hit[1]))
                g = to_g(b)
                if g[1] < wt:
                    maxdn = max(maxdn, dn(g))
        if maxdn > -1e8:
            lim = bulge - maxdn - 0.05          # top sits at most bulge into the room below wall_top
            if lim < MIN_DEPTH:
                return False
            h = min(h, lim)
        cn = sum((n for _, n in bi), Vector()).normalized()
        ob = [add(b) for b, _ in bo]
        ot = [add(b + n * h) for b, n in bo]
        it = [add(b + n * h) for b, n in bi]
        ctr = sum((b for b, _ in bo), Vector()) / 6.0
        cen = sum((b + n * h for b, n in bi), Vector()) / 6.0
        for k in range(6):
            k1 = (k + 1) % 6
            q = (ob[k], ob[k1], ot[k1], ot[k])
            face(q, sum((verts[i] for i in q), Vector()) / 4.0 - ctr, 0, False)
            q = (ot[k], ot[k1], it[k1], it[k])
            face(q, sum((verts[i] for i in q), Vector()) / 4.0 - cen, 0, False)
        if kind == "dome":
            ap = add(cen + cn * CAP_DOME)
            for k in range(6):
                face((ap, it[k], it[(k + 1) % 6]), cn, 1, True)
        elif kind == "open":
            fc = add(cen - cn * FLOOR_DEPTH)
            for k in range(6):
                face((fc, it[k], it[(k + 1) % 6]), cn, 2, False)
        return True

    def rim():
        ring = []
        for k in range(OUT_N):
            th = math.tau * k / OUT_N
            rr = rad(th)
            hit = surf(rr * math.cos(th), rr * math.sin(th))
            if hit is None:
                return False
            ring.append((hit[0] + hit[1] * ROLL_LIFT, hit[1]))
        idx = []
        for k in range(OUT_N):
            c, n = ring[k]
            tng = ring[(k + 1) % OUT_N][0] - ring[k - 1][0]
            side = n.cross(tng).normalized()
            pts = [c + side * (math.cos(math.tau * m / ROLL_SIDES) * ROLL_R)
                   + n * (math.sin(math.tau * m / ROLL_SIDES) * ROLL_R) for m in range(ROLL_SIDES)]
            idx.append([add(p) for p in pts])
        for k in range(OUT_N):
            k1 = (k + 1) % OUT_N
            for m in range(ROLL_SIDES):
                m1 = (m + 1) % ROLL_SIDES
                q = (idx[k][m], idx[k][m1], idx[k1][m1], idx[k1][m])
                face(q, sum((verts[i] for i in q), Vector()) / 4.0 - ring[k][0], 0, True)
        return True

    def inside(cu, cv):
        rho = math.hypot(cu, cv)
        if rho <= rad(math.atan2(cv, cu)) + 0.3 * r:
            return True
        return any(math.hypot(cu - su, cv - sv) <= SAT_R for su, sv in sats)

    # cells on a hex lattice in the patch's tangent plane, clipped to the lobed outline and satellites
    cells = 0
    K = int((1.3 * R + SAT_R + 1.0) / (1.5 * r)) + 2
    for i in range(-K, K + 1):
        for j in range(-K, K + 1):
            cu = 1.5 * r * i
            cv = SQ3 * r * (j + 0.5 * (i % 2))
            if not inside(cu, cv):
                continue
            rho = math.hypot(cu, cv)
            edge = rho > rad(math.atan2(cv, cu)) - 0.9 * r
            roll = rng.random()
            kind = "dome" if roll < 0.70 else ("open" if roll < 0.95 else "broken")
            # mound: tallest at the centre, shortest at the rim
            dd = min(1.0, rho / R)
            h = HMAX * (0.25 + 0.75 * (1.0 - dd * dd)) * rng.uniform(0.85, 1.0)
            if edge:
                h *= 0.6
            h = max(h, 0.12)
            n0, f0 = len(verts), len(faces)
            if cell(cu, cv, kind, h):
                cells += 1
            else:
                del verts[n0:]
                del faces[f0:]
    if cells < 6 or not rim():
        return None
    for v in verts:
        g = to_g(v)
        if g[1] < wt:
            d = dn(g)
            if d > bulge + 1e-6 or d < -TOL_BEHIND:
                return None
    tris = sum(len(idx) - 2 for idx, _, _ in faces)
    return verts, faces, cells, tris


def build_patches(shell, name, sample, radius, accept, dn, wall_top, bulge, budget):
    """Place comb patches on the finished shell bmesh (Blender coords; normals face into the room).

    Hooks (Godot coordinates unless noted):
      sample(rng) -> (origin_b, target_b, meta): a ray from inside the room toward a candidate wall point.
      accept(g, meta) -> probability of keeping a hit (clusters on ribs and the crown, few near floors).
      radius(g, meta) -> largest blob radius allowed at hit g (ends, top, floor).
      dn(g) -> signed inward distance to the collision faces (positive into the room).
    Returns (bmesh of all patches, stats). Patches stop once the triangle budget is spent."""
    bvh = BVHTree.FromBMesh(shell)
    area = sum(f.calc_area() for f in shell.faces)
    want_n = max(1, round(COVER * area / MEAN_AREA))
    rng = random.Random(zlib.crc32(name.encode()) & 0xFFFFFFFF)
    placed = []
    out_v, out_f = [], []
    tris = cells = 0
    blob_area = 0.0
    tries = 0
    fails = {"hit": 0, "accept": 0, "radius": 0, "space": 0, "plan": 0}
    while len(placed) < want_n and tries < 60000:
        tries += 1
        origin, target, meta = sample(rng)
        hit = bvh.ray_cast(origin, (target - origin).normalized(), 1000.0)
        if hit[0] is None:
            fails["hit"] += 1
            continue
        loc = hit[0]
        n = hit[1].normalized()
        if n.dot(origin - loc) < 0.0:
            n = -n
        g = to_g(loc)
        if rng.random() > accept(g, meta):
            fails["accept"] += 1
            continue
        R = min(rng.uniform(MIN_R, MAX_R), radius(g, meta))
        if R < MIN_R:
            fails["radius"] += 1
            continue
        if any((loc - c).length < R + rc + 0.3 for c, rc in placed):
            fails["space"] += 1
            continue
        plan = _plan(bvh, rng, loc, n, R, dn, wall_top, bulge)
        if plan is None:
            fails["plan"] += 1
            continue
        pv, pf, nc, pt = plan
        if tris + pt > budget:
            break
        base = len(out_v)
        out_v.extend(pv)
        out_f.extend((tuple(i + base for i in idx), mat, sm) for idx, mat, sm in pf)
        placed.append((loc, R))
        tris += pt
        cells += nc
        blob_area += math.pi * R * R
    bvh = None

    bm = bmesh.new()
    bv = [bm.verts.new(p) for p in out_v]
    bm.verts.ensure_lookup_table()
    for idx, mat, sm in out_f:
        try:
            f = bm.faces.new(tuple(bv[i] for i in idx))
        except ValueError:
            continue
        f.material_index = mat
        f.smooth = sm
    below = [dn(to_g(p)) for p in out_v if to_g(p)[1] < wall_top]
    lo = min(below) if below else 0.0
    hi = max(below) if below else 0.0
    assert not below or (-TOL_BEHIND - 1e-9 <= lo and hi <= bulge + 1e-6), "comb patch outside wall band"
    stats = {"patches": len(placed), "cells": cells, "tris": tris, "area": area,
             "coverage": blob_area / area, "budget": budget, "tries": tries, "fails": fails,
             "below": len(below), "lo": lo, "hi": hi}
    print("COMB %s: %d patches (target %d), %d cells, %d tris (budget %d), blob cover %.1f%% of %.0f m2"
          % (name, len(placed), want_n, cells, tris, budget, 100.0 * stats["coverage"], area))
    print("COMB-CHECK %s: %d patch verts below wall_top, inward range [%.3f, %.3f] within [-%.2f, %.2f]; fails %s"
          % (name, len(below), lo, hi, TOL_BEHIND, bulge, fails))
    return bm, stats


def make_object(name, bm):
    """Patch bmesh -> scene object with materials wax, amber, carapace_dull (index order)."""
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in MAT_NAMES:
        me.materials.append(kit.material(m))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob
