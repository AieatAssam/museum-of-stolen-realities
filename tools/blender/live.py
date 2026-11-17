"""Post-build steps shared by the headless harness (export.py) and live Blender MCP sessions.

Live use (Blender MCP, in the user's open Blender):
    import sys; sys.path.insert(0, "<repo>/tools/blender"); import live
    live.run("<repo>/hub/models/src/thief.py", "<repo>/hub/models/thief.glb")
clears the open scene, runs the build script's build([]), then finish() exports the GLB.
"""
import importlib.util
import os
import sys

import bmesh
import bpy


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def build(script, extra=()):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    spec = importlib.util.spec_from_file_location("build_script", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build(list(extra))
    return mod


def run(script, out, extra=(), max_tris=None):
    clear()
    build(script, extra)
    return finish(out, max_tris)


def finish(out, max_tris=None):
    MAX_TRIS = max_tris or int(os.environ.get("MOSR_MAX_TRIS", "60000"))
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
        raise RuntimeError(f"poly budget exceeded: {total} > {MAX_TRIS} (set MOSR_MAX_TRIS to override)")
    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", export_apply=True, export_yup=True, export_extras=True,
        export_cameras=False, export_lights=False, export_materials="EXPORT", export_tangents=True,
        export_image_format="NONE",
    )
    print("EXPORTED", out)
    return total
