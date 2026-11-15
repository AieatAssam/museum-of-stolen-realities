"""Small modelling kit for headless build scripts (import kit). Blender units = metres, +Z up.

Everything builds real geometry with bmesh (no operators that need a GUI context) so scripts are
deterministic and parallel-safe.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


def material(name):
    """Get/create a material by name. Only the NAME matters (Godot remaps it)."""
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def _obj(name, bm, mat=None, smooth_angle=35.0):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    if smooth_angle is not None:
        for p in me.polygons:
            p.use_smooth = True
        # mark sharp edges by angle so Godot keeps hard creases
        bm2 = bmesh.new()
        bm2.from_mesh(me)
        for e in bm2.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(smooth_angle):
                e.smooth = False
        bm2.to_mesh(me)
        bm2.free()
        try:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except AttributeError:
            pass
    return ob


def lathe(name, profile, segments=32, mat=None, smooth_angle=40.0, cap=True):
    """Revolve a (radius, z) profile around Z. Profile goes bottom -> top."""
    bm = bmesh.new()
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z)) for r, z in profile])
    for i in range(segments):
        r0, r1 = rings[i], rings[(i + 1) % segments]
        for j in range(len(profile) - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    if cap:
        for j in (0, len(profile) - 1):
            if profile[j][0] > 1e-4:
                f = bm.faces.new([rings[i][j] for i in range(segments)])
                if j == 0:
                    f.normal_flip()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth_angle)


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segments, affect="EDGES", profile=0.5)
    return _obj(name, bm, mat, 40.0)


def sweep_closed(name, profile, path, mat=None, smooth_angle=40.0):
    """Sweep a 2D profile [(u, v)] along a closed polyline path [(x, y, z)] lying in a plane.
    u = outward offset (perpendicular to path, in-plane), v = offset along the plane normal.
    Mitred corners. Perfect for picture-frame mouldings and cornices."""
    n = len(path)
    pts = [Vector(p) for p in path]
    # plane normal
    nrm = Vector((0, 0, 0))
    for i in range(n):
        nrm += pts[i].cross(pts[(i + 1) % n])
    nrm.normalize()
    bm = bmesh.new()
    rings = []
    for i in range(n):
        prev, cur, nxt = pts[i - 1], pts[i], pts[(i + 1) % n]
        d0 = (cur - prev).normalized()
        d1 = (nxt - cur).normalized()
        o0 = d0.cross(nrm).normalized()
        o1 = d1.cross(nrm).normalized()
        miter = (o0 + o1).normalized()
        scale = 1.0 / max(miter.dot(o0), 0.2)
        rings.append([bm.verts.new(cur + miter * u * scale + nrm * v) for u, v in profile])
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for j in range(len(profile) - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, smooth_angle)


def rect_path(w, h, z_axis_up=False):
    """Closed rectangle path centred at origin in the XZ plane (a frame standing upright, facing -Y)."""
    hw, hh = w / 2, h / 2
    return [(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)]


def torus(name, major, minor, seg=48, rseg=12, mat=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        c = Vector((math.cos(a), math.sin(a), 0))
        rings.append([bm.verts.new(c * (major + minor * math.cos(2 * math.pi * j / rseg)) + Vector((0, 0, minor * math.sin(2 * math.pi * j / rseg)))) for j in range(rseg)])
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    m = Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return _obj(name, bm, mat, None if False else 60.0)


def tube(name, points, radius, sides=10, mat=None):
    """Open tube along a polyline (ropes, rails)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        x = d.cross(up).normalized()
        y = x.cross(d).normalized()
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + y * math.sin(2 * math.pi * k / sides)) * radius) for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    return _obj(name, bm, mat, 80.0)


def join(name, objs):
    """Join objects into one (keeps material slots)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = scale
    return ob


def duplicate(ob, name):
    d = ob.copy()
    d.data = ob.data.copy()
    d.name = name
    bpy.context.scene.collection.objects.link(d)
    return d


def collision_box(name, size, loc=(0, 0, 0)):
    """Invisible convex collider: names it <name>-convcolonly."""
    return box(name + "-convcolonly", size, loc)
