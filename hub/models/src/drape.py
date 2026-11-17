"""Cloth draping for the atrium figures (thief.py, docent.py): garments are simulated with Blender's cloth solver
over a hidden collision body, then the simulation is applied, smoothed and given thickness.

    drape.simulate(garment, colliders, pin=lambda co: weight, frames=80)
garment: a mesh object in its rest shape; pin(co) -> 0..1 pin weight per vertex (1 = held in place).
colliders: mesh objects that the cloth rests on (removed by the caller afterwards).
"""
import math
import random

import bmesh
import bpy
import kit
from mathutils import Vector


def _select_only(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)


def grid_tube(name, rings, closed=True):
    """rings: list of vertex rings (each a list of (x, y, z)), top to bottom, equal length. Quads between rings;
    closed joins each ring end to its start."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for i in range(len(vs) - 1):
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            bm.faces.new((vs[i][k], vs[i][k2], vs[i + 1][k2], vs[i + 1][k]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def simulate(ob, colliders, pin, frames=80, mass=0.3, tension=15.0, bending=0.5, shrink=0.0,
             self_collision=True, distance=0.006, quality=8, gravity=1.0):
    vg = ob.vertex_groups.new(name="pin")
    for v in ob.data.vertices:
        w = max(0.0, min(1.0, pin(v.co)))
        if w > 0:
            vg.add([v.index], w, "REPLACE")
    cols = []
    for c in colliders:
        m = c.modifiers.new("collision", "COLLISION")
        c.collision.thickness_outer = 0.006
        c.collision.cloth_friction = 8.0
        c.collision.use_culling = False  # garments are open tubes: their normals may face inward
        cols.append((c, m))
    cl = ob.modifiers.new("cloth", "CLOTH")
    s = cl.settings
    s.quality = quality
    s.mass = mass
    s.tension_stiffness = s.compression_stiffness = tension
    s.shear_stiffness = tension
    s.bending_stiffness = bending
    s.vertex_group_mass = "pin"
    s.shrink_min = shrink
    s.effector_weights.gravity = gravity
    s.air_damping = 2.0
    cs = cl.collision_settings
    cs.use_collision = True
    cs.distance_min = distance
    cs.use_self_collision = self_collision
    cs.self_distance_min = distance * 0.8
    cs.collision_quality = 3
    cl.point_cache.frame_start = 1
    cl.point_cache.frame_end = frames
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    _select_only(ob)
    bpy.ops.object.modifier_apply(modifier=cl.name)
    ob.select_set(False)
    if "pin" in ob.vertex_groups:
        ob.vertex_groups.remove(ob.vertex_groups["pin"])
    for c, m in cols:
        c.modifiers.remove(m)
    sc.frame_set(1)
    return ob


def skin_graph(name, nodes, edges, mat, root=0, levels=2, flatten=None):
    """Skin-modifier body: nodes [(pos, radius)] joined by edges, hulled by the skin modifier and subdivided,
    so branches (shoulders, hips) blend instead of butting. flatten(co) -> y scale (torso depth)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p, _ in nodes], edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 1.0
    for i, (_, r) in enumerate(nodes):
        sv = me.skin_vertices[0].data[i]
        sv.radius = (r, r) if not isinstance(r, tuple) else r
        sv.use_root = i == root
    ss = ob.modifiers.new("subsurf", "SUBSURF")
    ss.levels = ss.render_levels = levels
    _select_only(ob)
    bpy.ops.object.modifier_apply(modifier=sk.name)
    bpy.ops.object.modifier_apply(modifier=ss.name)
    ob.select_set(False)
    if flatten:
        for v in me.vertices:
            v.co.y *= flatten(v.co)
    ob.data.materials.append(kit.material(mat))
    for f in me.polygons:
        f.use_smooth = True
    return ob


def _table(T, z):
    for (z0, *a), (z1, *b) in zip(T, T[1:]):
        if z1 <= z <= z0:
            t = (z0 - z) / (z0 - z1)
            return [x + (y - x) * t for x, y in zip(a, b)]
    return list(T[0][1:]) if z > T[0][0] else list(T[-1][1:])


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def envelope(name, under, collar, hem, gap=0.014, dz=0.008, fold=0.014, ns=128, seed=3, hang=0.3, shoulder=0.04):
    """A cape or mantle built, not simulated. collar: [(z, rx, ry)] top down, the fitted neck and yoke; hem(u) the
    hem height per direction u round the body (-Y = front). Below the collar, for each direction the cloth lies
    on the outermost surface of `under` (rays stop at the axis) and, past the widest point, hangs from it closing
    in by `hang` per metre of drop; it is blurred round (bridging between arms) and rounded down each fall (over the shoulder)
    and breaks into folds where it hangs free, deeper towards the hem."""
    from mathutils.bvhtree import BVHTree
    trees = []
    for ob in under:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        trees.append(BVHTree.FromBMesh(bm))
        bm.free()
    top, ztop = collar[0][0], collar[-1][0]
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]
    U = [2 * math.pi * i / ns for i in range(ns)]
    NR = int(round((top - min(hem(u) for u in U)) / dz)) + 1
    Zs = [[top - (top - hem(u)) * j / (NR - 1) for j in range(NR)] for u in U]
    R, SUP = [], []
    for u, zs in zip(U, Zs):
        d = Vector((math.cos(u), math.sin(u), 0))
        rs, ss, prev = [], [], None
        for z in zs:
            sup = 0.0
            for t in trees:
                hit = t.ray_cast(Vector((0, 0, z)) + d, -d, 1.0)
                if hit[0] is not None:
                    sup = max(sup, (hit[0] - Vector((0, 0, z))).length)
            rx, ry = _table(collar, z)
            r = max(sup + gap, rx * ry / math.hypot(ry * math.cos(u), rx * math.sin(u)) if z > ztop else 0.0)
            if prev is not None:
                r = max(r, prev[0] - hang * (prev[1] - z))
            rs.append(r)
            ss.append(sup)
            prev = (r, z)
        R.append(rs)
        SUP.append(ss)
    for _ in range(3):
        R = [[max(R[i][j], (R[i - 1][j] + 2 * R[i][j] + R[(i + 1) % ns][j]) / 4) for j in range(NR)]
             for i in range(ns)]
    # down each fall the profile is dilated by a disc of radius `shoulder`: the cloth rounds over the shoulder's
    # corner instead of turning it, and never passes inside what it lies on
    out = []
    for i in range(ns):
        z, r = Zs[i], R[i]
        col = []
        for j in range(NR):
            best = r[j]
            for k in range(NR):
                dzk = abs(z[j] - z[k])
                if dzk < shoulder:
                    best = max(best, r[k] - shoulder + math.sqrt(shoulder * shoulder - dzk * dzk))
            col.append(best)
        out.append(col)
    R = out
    rings = []
    for j in range(NR):
        ring = []
        for i, u in enumerate(U):
            z, r = Zs[i][j], R[i][j]
            free = _smooth((r - SUP[i][j] - gap) / 0.04)
            f = 0.6 * math.sin(11 * u + ph[0]) + 0.4 * math.sin(17 * u + ph[1]) + 0.3 * math.sin(6 * u + ph[2])
            rr = r + fold * free * _smooth((ztop - z) / 0.12) * f
            ring.append((rr * math.cos(u), rr * math.sin(u), z))
        rings.append(ring)
    return grid_tube(name, rings)
