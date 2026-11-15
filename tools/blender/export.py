"""Headless export harness. Do not run directly; use tools/blender_build.sh.

Conventions enforced here (see tools/README.md):
  * 1 Blender unit = 1 m. Build with +Z up in Blender; glTF export converts to Godot's +Y up.
  * Object names become Godot node names. Suffixes are Godot import hints:
      name-col          -> mesh + StaticBody3D with trimesh (concave) collision
      name-convcol      -> mesh + convex collision
      name-colonly      -> invisible trimesh collision only
      name-convcolonly  -> invisible convex collision only (cheapest, preferred for props)
  * Custom properties export as glTF extras -> node meta "extras" (e.g. obj["surface"] = "carpet").
  * Material *names* are the contract: Godot's MaterialLib swaps them for res://assets/materials/<name>.tres
    (or wings/<id>/materials/<name>.tres). Blender shading is irrelevant.
  * All transforms are applied; each object's origin stays where the build script put it.
  * Objects without UVs get a world-scale cube projection (1 UV unit = 1 m).
"""
import importlib.util
import os
import sys

import bpy
import bmesh

argv = sys.argv[sys.argv.index("--") + 1:]
script, out = argv[0], argv[1]
extra = argv[2:]
MAX_TRIS = int(os.environ.get("MOSR_MAX_TRIS", "60000"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # so build scripts can `import kit`
bpy.ops.wm.read_factory_settings(use_empty=True)
spec = importlib.util.spec_from_file_location("build_script", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.build(extra)

bpy.ops.object.select_all(action="DESELECT")
total = 0
for ob in list(bpy.context.scene.objects):
    if ob.type == "CURVE":
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.convert(target="MESH")
        ob.select_set(False)
for ob in bpy.context.scene.objects:
    if ob.type != "MESH":
        continue
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    me = ob.data
    if not me.uv_layers:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=1.0, scale_to_bounds=False, correct_aspect=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    bm.from_mesh(me)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    if not any(ob.name.endswith(s) for s in ("-colonly", "-convcolonly")):
        total += tris
    ob.select_set(False)
    print(f"  {ob.name:32s} {tris:7d} tris  mats={[s.material.name for s in ob.material_slots if s.material]}")
print(f"TOTAL {total} tris -> {out}")
if total > MAX_TRIS:
    raise SystemExit(f"poly budget exceeded: {total} > {MAX_TRIS} (set MOSR_MAX_TRIS to override)")
bpy.ops.export_scene.gltf(
    filepath=out, export_format="GLB", export_apply=True, export_yup=True, export_extras=True,
    export_cameras=False, export_lights=False, export_materials="EXPORT", export_tangents=True,
    export_image_format="NONE",
)
print("EXPORTED", out)
