"""Contact sheet of glb models (workbench render, one tile each) for a quick shape check.
  blender --background --factory-startup --python wings/aria/tools/preview_models.py -- out.png a.glb b.glb ...
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out, files = argv[0], argv[1:]
tiles = []
for f in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    ctr = (lo + hi) / 2
    size = (hi - lo).length
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    bpy.context.scene.collection.objects.link(cam)
    d = Vector((0.55, -1.0, 0.35)).normalized()
    cam.location = ctr + d * size * 1.25
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x = 480
    sc.render.resolution_y = 480
    p = "/tmp/_prev_%d.png" % len(tiles)
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(p)
cols = 4
rows = math.ceil(len(tiles) / cols)
img = bpy.data.images.new("sheet", 480 * cols, 480 * rows)
px = [0.1] * (480 * cols * 480 * rows * 4)
for i, t in enumerate(tiles):
    im = bpy.data.images.load(t)
    src = list(im.pixels)
    cx, cy = (i % cols) * 480, (rows - 1 - i // cols) * 480
    for y in range(480):
        o = ((cy + y) * 480 * cols + cx) * 4
        px[o:o + 480 * 4] = src[y * 480 * 4:(y + 1) * 480 * 4]
img.pixels = px
img.filepath_raw = out
img.file_format = "PNG"
img.save()
