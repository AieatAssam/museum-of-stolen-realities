"""Cloth draping for the atrium figures (thief.py, docent.py): garments are simulated with Blender's cloth solver
over a hidden collision body, then the simulation is applied, smoothed and given thickness.

    drape.simulate(garment, colliders, pin=lambda co: weight, frames=80)
garment: a mesh object in its rest shape; pin(co) -> 0..1 pin weight per vertex (1 = held in place).
colliders: mesh objects that the cloth rests on (removed by the caller afterwards).
"""
import bmesh
import bpy
import kit


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
