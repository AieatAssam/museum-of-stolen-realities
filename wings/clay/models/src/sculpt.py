"""Hand-built plasticine helpers for the clay wing's build scripts (on top of tools/blender/kit.py).
Everything is deterministic (seeded mathutils.noise), bmesh only, so builds are headless and repeatable.
Forms are never quite true: lumps, thumb dents, soft irregular radii, as a model-maker's hands leave them."""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import kit


def _lump(p, seed, scale):
    return noise.fractal(p * scale + Vector((seed * 7.31, seed * 3.17, seed * 5.53)), 0.6, 2.1, 3, noise_basis="PERLIN_ORIGINAL")


def deform(bm, seed=0, lump=0.05, scale=1.6, dents=0, dent_r=0.18, dent_d=0.04, squash=None):
    """Push every vertex along its normal by fractal noise (lumps), then press in `dents` thumb dents."""
    bm.normal_update()
    rnd = random.Random(seed)
    vs = list(bm.verts)
    for v in vs:
        v.co += v.normal * (_lump(v.co, seed, scale) * lump)
    for _ in range(dents):
        c = rnd.choice(vs).co.copy()
        for v in vs:
            d = (v.co - c).length
            if d < dent_r:
                v.co -= v.normal * dent_d * (1.0 - d / dent_r) ** 2
    if squash:
        for v in vs:
            v.co = Vector((v.co.x * squash[0], v.co.y * squash[1], v.co.z * squash[2]))


def to_obj(name, bm, mat, smooth=True):
    return kit._obj(name, bm, mat, 180.0 if smooth else 35.0)


def blob(name, size, loc=(0, 0, 0), mat="clay", seed=0, lump=0.06, scale=1.6, subdiv=4, dents=0, dent_r=0.2,
         dent_d=0.04, rot=(0, 0, 0)):
    """An ellipsoid of plasticine, rolled by hand. size = full extents (x, y, z)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.5)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    deform(bm, seed, lump, scale, dents, dent_r, dent_d)
    m = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return to_obj(name, bm, mat)


def slab(name, size, loc=(0, 0, 0), mat="clay", seed=0, lump=0.02, bevel=0.06, cuts=6, dents=0, rot=(0, 0, 0)):
    """A hand-cut slab: bevelled box, subdivided and nudged so no edge is ruler-straight."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=3, affect="EDGES", profile=0.5)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if e.calc_length() > max(size) / cuts], cuts=2, use_grid_fill=True)
    deform(bm, seed, lump, 2.0, dents, 0.15, 0.025)
    m = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return to_obj(name, bm, mat, smooth=True)


def snake(name, points, radius, mat="clay", seed=0, sides=10, wobble=0.15, taper=(1.0, 1.0), caps=True, steps=4):
    """A rolled clay snake along a smooth path through `points`: soft round caps, radius that wanders."""
    pts = [Vector(p) for p in points]
    # Catmull-Rom resample so bends are smooth
    path = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    path.append(pts[-1])
    n = len(path)
    bm = bmesh.new()
    rings = []
    prev_x = None
    for i, p in enumerate(path):
        d = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        if prev_x is None:
            up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            x = d.cross(up).normalized()
        else:
            x = (prev_x - d * prev_x.dot(d)).normalized()
        prev_x = x
        y = x.cross(d).normalized()
        t = i / max(n - 1, 1)
        r = radius * (taper[0] + (taper[1] - taper[0]) * t) * (1.0 + wobble * noise.noise(p * 3.0 + Vector((seed, 0, 0))))
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)])
    for i in range(n - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    if caps:
        for end, sgn in ((0, -1), (n - 1, 1)):
            d = (path[min(end + 1, n - 1)] - path[max(end - 1, 0)]).normalized() * sgn
            c = sum((v.co for v in rings[end]), Vector()) / sides
            r = (rings[end][0].co - c).length
            tip = bm.verts.new(c + d * r * 0.8)
            mid = [bm.verts.new(c + (v.co - c) * 0.7 + d * r * 0.55) for v in rings[end]]
            for k in range(sides):
                a, b = rings[end][k], rings[end][(k + 1) % sides]
                ma, mb = mid[k], mid[(k + 1) % sides]
                if sgn > 0:
                    bm.faces.new((a, b, mb, ma))
                    bm.faces.new((ma, mb, tip))
                else:
                    bm.faces.new((b, a, ma, mb))
                    bm.faces.new((mb, ma, tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return to_obj(name, bm, mat)


def lathe(name, profile, mat="clay", seed=0, segments=32, lump=0.03, scale=2.0, cap=True, dents=0):
    """kit.lathe, then hand-worked: the revolved form loses its perfect symmetry."""
    ob = kit.lathe(name, profile, segments=segments, mat=mat, cap=cap)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    deform(bm, seed, lump, scale, dents, 0.2, 0.03)
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"  # cut faces keep the cutter's material (raw clay inside a moss mound)
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    return target


def scatter_dents(ob, seed, count, r=0.15, d=0.03):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    deform(bm, seed, 0.0, 1.0, count, r, d)
    bm.to_mesh(ob.data)
    bm.free()
    return ob
