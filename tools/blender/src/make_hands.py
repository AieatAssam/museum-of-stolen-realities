"""Cut the hand library (tools/blender/assets/hands.blend) from the Quaternius Universal Base Characters.

Run once, by hand (the source .gltf is not in the repo):
  /opt/homebrew/bin/blender -b --factory-startup -P tools/blender/src/make_hands.py -- \
      <path>/Superhero_Male_FullBody.gltf tools/blender/assets/hands.blend

Source: Quaternius, "Universal Base Characters" (Standard), CC0. The rig's finger bones pose four
static hands: relaxed, open, grip, point. Frame of each saved mesh (RIGHT hand, metres):
  origin at the wrist joint (hand_r head); fingers +Y; palm -Z; back of hand +Z; thumb on -X.
kit.hand() mirrors the mesh on X for the left hand. Mesh names: hand_relaxed, hand_open, hand_grip, hand_point.
Scale: the rig is 1.82 m tall, so the hand comes out at human size with no scaling.
"""
import math
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = argv[0], argv[1]
MAX_TRIS = 1500

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC, merge_vertices=True)
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["SuperHero_Male"]
W = arm.data.bones["hand_r"].head_local.copy()  # wrist joint, armature space (rig at identity transform)
# hand basis in armature (world) coordinates: rows = hand X, Y, Z
Q = Matrix(((0, 1, 0), (-1, 0, 0), (0, 0, 1)))
CUT = -0.02  # wrist stub: 2 cm of forearm kept, the rest is cut off and capped
FINGERS = ["index", "middle", "ring", "pinky"]

# joint flex in degrees (proximal, middle, distal) per finger; thumb (base, tip). Positive bends toward the palm.
POSES = {
    "relaxed": ({"index": (10, 14, 10), "middle": (12, 16, 12), "ring": (16, 20, 14), "pinky": (20, 24, 16)}, (12, 14)),
    "open": ({f: (0, 0, 0) for f in FINGERS}, (0, 0)),
    "grip": ({"index": (80, 95, 65), "middle": (85, 100, 70), "ring": (88, 100, 70), "pinky": (92, 100, 72)}, (35, 45)),
    "point": ({"index": (0, 0, 0), "middle": (85, 100, 70), "ring": (88, 100, 70), "pinky": (92, 100, 72)}, (35, 45)),
}


def pose_hand(fingers, thumb):
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    for f, joints in fingers.items():
        for j, deg in enumerate(joints, start=1):
            arm.pose.bones["%s_0%d_r" % (f, j)].rotation_euler = (math.radians(deg), 0, 0)
    for j, deg in enumerate(thumb, start=1):
        arm.pose.bones["thumb_0%d_r" % j].rotation_euler = (math.radians(deg), 0, 0)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return bpy.data.meshes.new_from_object(ev)


def cut_hand(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in bm.verts:
        v.co = Q @ (v.co - W)
    # the hand is the only geometry that stays at x_w < -0.6 (right side), and the wrist cut is in hand coords
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0, CUT, 0), plane_no=(0, 1, 0), clear_inner=True)
    # the body's right arm is now only the hand (x_w < -0.6 is the right hand side only)
    outside = [v for v in bm.verts if v.co.x > 0.25 or v.co.z < -0.25]  # torso/legs (none expected)
    bmesh.ops.delete(bm, geom=outside, context="VERTS")
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    print("       open edges before fill: %d" % len(bnd))
    if bnd:
        bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    return bm


def tri_count(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


meshes = {}
for name, (fingers, thumb) in POSES.items():
    bm = cut_hand(pose_hand(fingers, thumb))
    length = max(v.co.y for v in bm.verts)  # wrist to the farthest fingertip
    me = bpy.data.meshes.new("hand_" + name)
    bm.to_mesh(me)
    bm.free()
    n = len(me.polygons) and sum(len(p.vertices) - 2 for p in me.polygons)
    print("HAND %-8s tris=%d length=%.3f m (before decimate)" % (name, n, length))
    if n > MAX_TRIS:
        ob = bpy.data.objects.new("tmp", me)
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.ratio = MAX_TRIS * 0.9 / n
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=mod.name)
        me = ob.data
        bpy.data.objects.remove(ob)
        n = sum(len(p.vertices) - 2 for p in me.polygons)
        print("       decimated tris=%d" % n)
    me.name = "hand_" + name
    meshes[me.name] = me

for me in meshes.values():
    me.use_fake_user = True
bpy.data.libraries.write(OUT, set(meshes.values()), fake_user=True)
print("WROTE", OUT, sorted(meshes))
