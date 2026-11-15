"""Exhibit 0: your world, kept inside a shattered crystal shell (r = 2.4 m).
  frag_<wing>_<n>  the six wings' missing shell pieces (3 each), core_<n> what remains. Each shard
                   has a glass face (exhibit_skin) and gold-leafed broken edges (exhibit_core).
                   Origin of every shard at the sphere centre so Godot can explode/assemble them.
  world            the small world inside (exhibit_world), lit from within.
  chip_<n>         loose crystal splinters that orbit the sphere (origin at their own centre)."""
import math
import random

import bmesh
import kit
from mathutils import Vector

R = 2.4
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
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=R)
    groups = {}
    for f in bm.faces:
        c = f.calc_center_median().normalized()
        k = max(range(len(seeds)), key=lambda i: c.dot(seeds[i]))
        groups.setdefault(k, []).append([v.co.copy() for v in f.verts])
    bm.free()
    wing_of = {}
    anchors = [Vector(v).normalized() for v in [(1, 0, 0.3), (-0.5, 0.86, 0.3), (-0.5, -0.86, 0.3), (0.3, 0.5, -0.8), (0.4, -0.6, -0.7), (-0.9, 0, -0.4)]]
    used = set()
    for w, a in zip(WINGS, anchors):
        near = sorted((i for i in range(len(seeds)) if i not in used), key=lambda i: -seeds[i].dot(a))[:3]
        for i in near:
            wing_of[i] = w
            used.add(i)
    counts = {}
    for k, faces in groups.items():
        sb = bmesh.new()
        vmap = {}
        seed = seeds[k]

        def V(co):
            key = (round(co.x, 5), round(co.y, 5), round(co.z, 5))
            if key not in vmap:
                # shrink each shard toward its own seed a little so gold seams open between them
                d = co.normalized()
                d = (d + (seed - d) * 0.035).normalized()
                bulge = 1.0 + 0.04 * (d.dot(seed) - 0.9)
                vmap[key] = sb.verts.new(d * R * bulge)
            return vmap[key]
        for fv in faces:
            sb.faces.new([V(co) for co in fv])
        ret = bmesh.ops.extrude_face_region(sb, geom=sb.faces[:])
        inner = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
        for v in inner:
            v.co = v.co * (1.0 - 0.07 - random.uniform(0, 0.03))
        bmesh.ops.recalc_face_normals(sb, faces=sb.faces)
        w = wing_of.get(k)
        name = "frag_%s_%d" % (w, counts.get(w, 0)) if w else "core_%d" % k
        counts[w] = counts.get(w, 0) + 1
        ob = kit._obj(name, sb, None, 25.0)
        ob.data.materials.append(kit.material("exhibit_skin"))
        ob.data.materials.append(kit.material("exhibit_core"))
        for p in ob.data.polygons:
            n = Vector(p.normal)
            c = Vector(p.center).normalized()
            p.material_index = 0 if abs(n.dot(c)) > 0.75 else 1
    # the world inside
    wb = bmesh.new()
    bmesh.ops.create_icosphere(wb, subdivisions=4, radius=R * 0.62)
    kit._obj("world", wb, "exhibit_world", 80.0)
    # orbiting splinters: thin crystal blades
    for i in range(26):
        cb = bmesh.new()
        L = random.uniform(0.18, 0.5)
        Wd = L * random.uniform(0.25, 0.45)
        tip, tail = Vector((0, 0, L)), Vector((0, 0, -L * 0.6))
        ring = [cb.verts.new((math.cos(a) * Wd * random.uniform(0.7, 1.2), math.sin(a) * Wd * 0.45, random.uniform(-0.05, 0.05))) for a in (0.3, 2.2, 4.2)]
        t, b = cb.verts.new(tip), cb.verts.new(tail)
        for j in range(3):
            cb.faces.new((ring[j], ring[(j + 1) % 3], t))
            cb.faces.new((ring[(j + 1) % 3], ring[j], b))
        bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
        ob = kit._obj("chip_%d" % i, cb, "exhibit_skin", 10.0)
        ob.rotation_euler = (random.uniform(0, 6.3), random.uniform(0, 6.3), random.uniform(0, 6.3))
