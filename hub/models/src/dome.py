"""Ribbed coffered dome over the atrium, springing at z=30.9 from the dodecagon (r 24.4) and
closing on an oculus (r 4.5) at z=46. Twelve gilt ribs, four gilt rings, a gilt oculus ring and a
warm disc of sky above it, where the light shafts come from. Normals face inward."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

R0, Z0, RO, ZT = 25.2, 29.9, 4.5, 46.0


def prof(t):
    a = t * math.pi / 2
    return (RO + (R0 - RO) * math.cos(a), Z0 + (ZT - Z0) * math.sin(a))


def build(args):
    pts = [prof(i / 16) for i in range(17)]
    shell = kit.lathe("shell", pts, 48, mat="dome", smooth_angle=60.0, cap=False)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(shell.data)
    bm.free()
    parts = [shell]
    for k in range(12):
        a = (k + 0.5) * 2 * math.pi / 12
        rib = []
        for i in range(17):
            r, z = prof(i / 16)
            r -= 0.25
            rib.append((math.cos(a) * r, math.sin(a) * r, z - 0.1))
        parts.append(orn.taper("rib%d" % k, rib, [0.45 - 0.25 * i / 16 for i in range(17)], 6, "gilt", flat=0.6))
    for j, t in enumerate((0.22, 0.45, 0.66, 0.84)):
        r, z = prof(t)
        parts.append(kit.torus("ring%d" % j, r - 0.2, 0.16, 96, 6, mat="gilt", loc=(0, 0, z - 0.15)))
    parts.append(kit.torus("oculus", RO, 0.45, 64, 10, mat="gilt", loc=(0, 0, ZT)))
    kit.join("dome", parts)
    sky = kit.lathe("sky", [(0.0, ZT + 3.0), (RO + 1.0, ZT + 3.0)], 32, mat="oculus_sky", cap=False)
    bm = bmesh.new()
    bm.from_mesh(sky.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(sky.data)
    bm.free()
