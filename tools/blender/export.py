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
import live  # noqa: E402

live.build(script, extra)
live.finish(out, MAX_TRIS)

