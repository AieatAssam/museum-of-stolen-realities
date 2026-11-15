"""Optical furniture. Arg = part:
  mirror_head    1.1 m silver face (toward Blender -Y = Godot +Z, the mirror's normal), moulded brass
                 bezel, ribbed lead back, trunnions and a finial. Origin at the face centre.
  mirror_collar  the floor slot the gimbal turns in: a lead ring with brass studs (origin on the floor).
  prism          bevelled triangular crystal with brass end-plates, 0.9 m, origin at its centre.
  prism_stand    turned brass drum the prism turns on (top at 0).
  lens           biconvex crystal in a knurled bezel, axis Blender Y, origin at its centre.
  lens_cradle    a ring on three claws with trunnion bosses (ring centre at origin)."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

FACE_ROT = (math.pi / 2, 0, 0)   # lathe axis Z -> Blender -Y (Godot +Z)


def mirror_head():
    p = [kit.lathe("face", [(0.0, 0.03), (0.56, 0.03), (0.56, 0.0), (0.0, 0.0)], 48, mat="silver", smooth_angle=20.0)]
    p.append(kit.lathe("bezel", [(0.54, 0.05), (0.56, 0.07), (0.6, 0.075), (0.64, 0.06), (0.665, 0.03),
                                 (0.665, -0.02), (0.65, -0.05), (0.62, -0.06)], 48, mat="brass", cap=False))
    p.append(kit.lathe("back", [(0.62, -0.06), (0.55, -0.1), (0.4, -0.15), (0.2, -0.18), (0.0, -0.19)], 32, mat="lead", cap=False))
    for k in range(8):
        a = k * math.pi / 4
        pts = [(math.cos(a) * r, math.sin(a) * r, -0.06 - 0.13 * (1 - (r / 0.62) ** 2)) for r in (0.6, 0.45, 0.3, 0.15, 0.05)]
        p.append(kit.tube("rib%d" % k, pts, 0.018, 6, mat="brass"))
    p.append(kit.lathe("finial", [(0.0, -0.19), (0.07, -0.2), (0.05, -0.26), (0.08, -0.3), (0.0, -0.36)], 16, mat="brass"))
    for ob in p:
        ob.rotation_euler = FACE_ROT
    for s in (-1, 1):  # trunnions on the horizontal axis
        t = kit.lathe("trunnion", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.08), (0.08, 0.1), (0.08, 0.13), (0.0, 0.14)], 16, mat="brass")
        t.rotation_euler = (0, s * math.pi / 2, 0)
        t.location = (s * 0.65, 0, 0)
        p.append(t)
    kit.join("mirror_head", p)


def mirror_collar():
    p = [kit.lathe("ring", [(0.7, 0.0), (0.72, 0.03), (0.8, 0.05), (0.88, 0.03), (0.9, 0.0)], 48, mat="lead", cap=False)]
    for k in range(12):
        a = k * math.pi / 6
        stud = kit.lathe("stud", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.03), (0.0, 0.05)], 10, mat="brass")
        stud.location = (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.04)
        p.append(stud)
    kit.join("mirror_collar", p)


def prism():
    # triangular section, apex up (Godot PrismMesh convention), extruded along Blender Y, bevelled
    w, h, d = 0.9, 0.8, 0.9
    bm = bmesh.new()
    tri = [(-w / 2, -h / 2), (w / 2, -h / 2), (0.0, h / 2)]
    front = [bm.verts.new((x, -d / 2 + 0.04, z)) for x, z in tri]
    back = [bm.verts.new((x, d / 2 - 0.04, z)) for x, z in tri]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(3):
        bm.faces.new((front[i], back[i], back[(i + 1) % 3], front[(i + 1) % 3]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.025, segments=2, affect="EDGES", profile=0.5)
    p = [kit._obj("crystal", bm, "crystal", 30.0)]
    for s in (-1, 1):  # brass end-plates following the triangle, inset
        bm2 = bmesh.new()
        sc = 1.08
        f = [bm2.verts.new((x * sc, s * (d / 2 - 0.02), z * sc - 0.02)) for x, z in tri]
        g = [bm2.verts.new((x * sc, s * (d / 2 + 0.03), z * sc - 0.02)) for x, z in tri]
        bm2.faces.new(f)
        bm2.faces.new(list(reversed(g)))
        for i in range(3):
            bm2.faces.new((f[i], g[i], g[(i + 1) % 3], f[(i + 1) % 3]))
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        bmesh.ops.bevel(bm2, geom=bm2.edges[:], offset=0.01, segments=1, affect="EDGES")
        p.append(kit._obj("plate", bm2, "brass", 30.0))
        for x, z in tri:
            rv = kit.lathe("rivet", [(0.0, 0.0), (0.035, 0.0), (0.03, 0.025), (0.0, 0.035)], 10, mat="brass")
            rv.rotation_euler = (-s * math.pi / 2, 0, 0)
            rv.location = (x * 0.8, s * (d / 2 + 0.03), z * 0.8 - 0.02)
            p.append(rv)
    kit.join("prism", p)


def prism_stand():
    kit.join("prism_stand", [
        kit.lathe("drum", [(0.0, -0.3), (0.62, -0.3), (0.64, -0.27), (0.6, -0.24), (0.52, -0.2),
                           (0.5, -0.08), (0.56, -0.05), (0.62, -0.02), (0.6, 0.0), (0.0, 0.0)], 48, mat="brass"),
        kit.torus("bead", 0.505, 0.02, 48, 8, mat="lead", loc=(0, 0, -0.14)),
    ])


def lens():
    p = [kit.lathe("glass", [(0.0, -0.13), (0.15, -0.11), (0.28, -0.06), (0.34, 0.0), (0.28, 0.06), (0.15, 0.11), (0.0, 0.13)], 40, mat="crystal")]
    p.append(kit.lathe("bezel", [(0.33, -0.06), (0.4, -0.07), (0.42, -0.04), (0.42, 0.04), (0.4, 0.07), (0.33, 0.06)], 48, mat="brass", cap=False))
    for k in range(24):
        a = k * math.pi / 12
        kn = kit.box("knurl", (0.03, 0.03, 0.1), (0, 0, 0), mat="brass")
        kn.location = (math.cos(a) * 0.425, math.sin(a) * 0.425, 0)
        kn.rotation_euler = (0, 0, a)
        p.append(kn)
    for ob in p:
        ob.rotation_euler = (ob.rotation_euler[0] + math.pi / 2, 0, ob.rotation_euler[2])
    kit.join("lens", p)


def lens_cradle():
    p = [kit.torus("ring", 0.5, 0.045, 48, 10, mat="brass", rot=(math.pi / 2, 0, 0))]
    for k in range(3):
        a = -math.pi / 2 + (k - 1) * 0.7
        pts = [(math.cos(a) * r, 0, math.sin(a) * r) for r in (0.5, 0.42, 0.36)]
        p.append(kit.tube("claw%d" % k, pts, 0.025, 8, mat="brass"))
    for s in (-1, 1):  # trunnion bosses where the ring meets the dais
        b = kit.lathe("boss", [(0.0, 0.0), (0.09, 0.0), (0.1, 0.05), (0.07, 0.1), (0.0, 0.12)], 16, mat="brass")
        b.rotation_euler = (0, s * math.pi / 2, 0)
        b.location = (s * 0.54, 0, 0)
        p.append(b)
    kit.join("lens_cradle", p)


def build(args):
    globals()[args[0]]()
