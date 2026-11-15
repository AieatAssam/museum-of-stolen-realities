"""Hand props and small architecture. Arg = part (origin noted per part, Blender Z up):
  fourth_sun     the fragment: a faceted sun-disc of gold glass in a leaded ring with 16 brass rays, centred.
  prov_face      Provenance A: a saint's face pane in a lead came with a brass hanging loop, centred.
  prov_veil      Provenance B: a spool of violet veil thread on a brass bobbin, centred.
  prov_iron      Provenance C: a grozing iron (glazier's notched pliers-hook), centred.
  reliquary      the chest the veil lies in: moulded base, glass panels, corner shafts; origin at the floor.
  reliquary_lid  its gabled lid with a ridge crest and finials; origin at the lid's bottom.
  pinnacle       flying-buttress pinnacle: octagonal spire with crockets and a finial; origin at its base."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

UPRIGHT = (math.pi / 2, 0, 0)  # lathe axis Z -> face toward Godot +Z


def fourth_sun():
    p = [kit.lathe("disc", [(0.0, -0.05), (0.12, -0.045), (0.2, -0.02), (0.22, 0.0), (0.2, 0.02), (0.12, 0.045), (0.0, 0.05)], 12, mat="sun", smooth_angle=10.0)]
    p.append(kit.torus("came", 0.225, 0.018, 48, 8, mat="lead"))
    for ob in p:
        ob.rotation_euler = UPRIGHT
    for k in range(16):
        a = k * math.pi / 8
        long = 0.42 if k % 2 == 0 else 0.33
        ray = kit.lathe("ray", [(0.0, 0.0), (0.03, 0.0), (0.0, long - 0.24)], 6, mat="brass" if k % 2 else "sun", smooth_angle=10.0)
        ray.rotation_euler = (0, a + math.pi / 2, 0)
        ray.location = (math.cos(a) * 0.24, 0, math.sin(a) * 0.24)
        p.append(ray)
    kit.join("fourth_sun", p)


def prov_face():
    p = [kit.box("pane", (0.22, 0.02, 0.3), (0, 0, 0), mat="glass_gold_m", bevel=0.008)]
    path = kit.rect_path(0.24, 0.32)
    p.append(kit.sweep_closed("came", [(-0.015, -0.015), (0.01, -0.015), (0.01, 0.015), (-0.015, 0.015)], path, mat="lead"))
    p.append(kit.box("lead_brow", (0.24, 0.025, 0.012), (0, 0, 0.05), mat="lead"))
    p.append(kit.box("lead_nose", (0.012, 0.025, 0.12), (0, 0, -0.01), mat="lead"))
    p.append(kit.torus("loop", 0.03, 0.006, 24, 6, mat="brass", loc=(0, 0, 0.19), rot=(math.pi / 2, 0, 0)))
    kit.join("prov_face", p)


def prov_veil():
    p = [kit.lathe("bobbin", [(0.0, -0.13), (0.07, -0.13), (0.075, -0.115), (0.03, -0.1), (0.03, 0.1), (0.075, 0.115), (0.07, 0.13), (0.0, 0.13)], 24, mat="brass")]
    p.append(kit.lathe("thread", [(0.03, -0.095), (0.058, -0.09), (0.062, 0.0), (0.058, 0.09), (0.03, 0.095)], 24, mat="veil", cap=False))
    # a loose end of thread trailing off the spool
    pts = [(0.06, 0.0, 0.02 * i) for i in range(1)] + [(0.07 + 0.02 * i, -0.01 * i, -0.03 * i - 0.04 * math.sin(i)) for i in range(1, 7)]
    p.append(kit.tube("tail", pts, 0.006, 6, mat="veil"))
    kit.join("prov_veil", p)


def prov_iron():
    p = []
    for s in (-1, 1):  # two handles meeting at a rivet, the jaws notched
        p.append(kit.tube("handle", [(s * 0.012, 0, -0.16), (s * 0.02, 0, -0.06), (s * 0.01, 0, 0.0)], 0.011, 8, mat="lead"))
        p.append(kit.box("jaw", (0.012, 0.03, 0.09), (s * 0.008, 0, 0.045), mat="silver", bevel=0.003))
        for k in range(3):
            p.append(kit.box("notch", (0.014, 0.032, 0.006), (s * 0.008, 0, 0.06 + k * 0.012), mat="lead"))
    rv = kit.lathe("rivet", [(0.0, -0.02), (0.014, -0.02), (0.014, 0.02), (0.0, 0.02)], 12, mat="brass")
    rv.rotation_euler = (0, math.pi / 2, 0)
    p.append(rv)
    kit.join("prov_iron", p)


def reliquary():
    p = [kit.box("plinth", (1.1, 0.9, 0.08), (0, 0, 0.04), mat="lead", bevel=0.01)]
    p.append(kit.box("base_mould", (1.04, 0.84, 0.05), (0, 0, 0.105), mat="brass", bevel=0.012))
    p.append(kit.box("body", (0.92, 0.72, 0.24), (0, 0, 0.25), mat="glass_red_m", bevel=0.006))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(kit.lathe("shaft", [(0.0, 0.13), (0.045, 0.13), (0.035, 0.16), (0.035, 0.34), (0.05, 0.37), (0.0, 0.38)], 12, mat="brass"))
            p[-1].location = (sx * 0.48, sy * 0.38, 0)
    for z in (0.135, 0.365):
        p.append(kit.sweep_closed("band", [(-0.01, -0.012), (0.012, -0.012), (0.012, 0.012), (-0.01, 0.012)],
                                  [(-0.47, -0.37, z), (0.47, -0.37, z), (0.47, 0.37, z), (-0.47, 0.37, z)], mat="brass"))
    for x in (-0.23, 0.0, 0.23):  # mullions on the long faces
        for sy in (-1, 1):
            p.append(kit.box("mullion", (0.015, 0.015, 0.22), (x, sy * 0.365, 0.25), mat="lead"))
    kit.join("reliquary", p)


def reliquary_lid():
    bm = bmesh.new()
    w, d, h = 0.55, 0.45, 0.24
    v = [bm.verts.new(c) for c in [(-w, -d, 0), (w, -d, 0), (w, d, 0), (-w, d, 0), (-w, 0, h), (w, 0, h)]]
    for f in [(0, 1, 2, 3), (0, 4, 5, 1), (3, 2, 5, 4), (0, 3, 4), (1, 5, 2)]:
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.012, segments=2, affect="EDGES")
    p = [kit._obj("roof", bm, "brass", 35.0)]
    p.append(kit.tube("ridge", [(-w, 0, h + 0.01), (w, 0, h + 0.01)], 0.02, 8, mat="lead"))
    for k in range(9):  # cresting along the ridge
        x = -0.44 + k * 0.11
        p.append(kit.lathe("crest", [(0.0, 0.0), (0.02, 0.0), (0.03, 0.03), (0.0, 0.07)], 6, mat="brass"))
        p[-1].location = (x, 0, h)
    for s in (-1, 1):
        p.append(kit.lathe("finial", [(0.0, 0.0), (0.03, 0.0), (0.04, 0.05), (0.02, 0.09), (0.035, 0.12), (0.0, 0.18)], 12, mat="brass"))
        p[-1].location = (s * w, 0, h - 0.02)
    kit.join("reliquary_lid", p)


def pinnacle():
    p = [kit.lathe("spire", [(0.0, 0.0), (0.7, 0.0), (0.7, 0.25), (0.6, 0.3), (0.55, 0.45), (0.06, 3.0), (0.0, 3.05)], 8, mat="glass_gold_m", smooth_angle=30.0)]
    p[-1].rotation_euler = (0, 0, math.pi / 8)
    for k in range(8):  # crockets climbing the arrises
        a = k * math.pi / 4
        for j, t in enumerate((0.25, 0.48, 0.7)):
            r = 0.6 * (1 - t) + 0.06 * t
            z = 0.45 + t * 2.55
            c = kit.lathe("crocket", [(0.0, -0.05), (0.05, -0.02), (0.06, 0.03), (0.0, 0.07)], 8, mat="brass")
            c.location = (math.cos(a) * (r + 0.04), math.sin(a) * (r + 0.04), z)
            p.append(c)
    p.append(kit.lathe("finial", [(0.0, 2.95), (0.08, 3.0), (0.14, 3.12), (0.08, 3.22), (0.05, 3.3), (0.1, 3.38), (0.0, 3.55)], 16, mat="brass"))
    kit.join("pinnacle", p)


def build(args):
    globals()[args[0]]()
