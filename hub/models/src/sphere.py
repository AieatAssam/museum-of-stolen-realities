"""Exhibit 0: a shattered world-sphere (r = 1.8 m) cut into Voronoi shards with real thickness.
Shards are grouped: frag_<wing>_<n> for the six wings' missing pieces, core_<n> for what remains.
Origin of each shard at the sphere centre (so Godot can explode/assemble along the shard normal)."""
import math
import random

import bmesh
import kit
from mathutils import Vector

R = 1.8
WINGS = ["glass", "clay", "noir", "aria", "chitin", "paint"]


def fib(n):
    pts = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - y * y)
        pts.append(Vector((math.cos(g * i) * r, math.sin(g * i) * r, y)))
    return pts


def build(args):
    random.seed(7)
    seeds = [s + Vector((random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12))) for s in fib(42)]
    seeds = [s.normalized() for s in seeds]
    # dense icosphere, assign faces to nearest seed
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=5, radius=R)
    groups = {}
    for f in bm.faces:
        c = f.calc_center_median().normalized()
        k = max(range(len(seeds)), key=lambda i: c.dot(seeds[i]))
        groups.setdefault(k, []).append([v.co.copy() for v in f.verts])
    bm.free()
    # pick the six wings' fragments: one cluster of 3 shards each, spread around
    order = list(range(len(seeds)))
    wing_of = {}
    anchors = [Vector(v).normalized() for v in [(1, 0, 0.3), (-0.5, 0.86, 0.3), (-0.5, -0.86, 0.3), (0.3, 0.5, -0.8), (0.4, -0.6, -0.7), (-0.9, 0, -0.4)]]
    used = set()
    for w, a in zip(WINGS, anchors):
        near = sorted((i for i in order if i not in used), key=lambda i: -seeds[i].dot(a))[:3]
        for i in near:
            wing_of[i] = w
            used.add(i)
    counts = {}
    for k, faces in groups.items():
        sb = bmesh.new()
        vmap = {}
        def V(co):
            key = (round(co.x, 5), round(co.y, 5), round(co.z, 5))
            if key not in vmap:
                vmap[key] = sb.verts.new(co * 0.985)  # small gap between shards
            return vmap[key]
        for fv in faces:
            sb.faces.new([V(co) for co in fv])
        # thickness: extrude inward along normals
        ret = bmesh.ops.extrude_face_region(sb, geom=sb.faces[:])
        inner = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
        for v in inner:
            v.co = v.co * (1.0 - 0.16 - random.uniform(0, 0.05))
        bmesh.ops.recalc_face_normals(sb, faces=sb.faces)
        w = wing_of.get(k)
        name = "frag_%s_%d" % (w, counts.get(w, 0)) if w else "core_%d" % k
        counts[w] = counts.get(w, 0) + 1
        ob = kit._obj(name, sb, None, 30.0)
        # two materials: outer skin (the world) and broken edges (raw, gold-lit)
        ob.data.materials.append(kit.material("exhibit_skin"))
        ob.data.materials.append(kit.material("exhibit_core"))
        for p in ob.data.polygons:
            n = Vector(p.normal)
            c = Vector(p.center).normalized()
            p.material_index = 0 if n.dot(c) > 0.6 and Vector(p.center).length > R * 0.95 else 1
