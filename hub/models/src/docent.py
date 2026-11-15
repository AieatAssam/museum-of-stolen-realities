"""Docent-construct: a faceless, too-tall plaster figure (2.3 m) in a pleated floor-length robe with
a velvet stole, gilt collar, cuffs and hem,
long arms cradling a sketchboard and a pencil. A brass badge on a lanyard. `head` is a separate
object with its origin at the neck pivot (it turns to watch you)."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import orn  # noqa: E402

# robe profile (z, radius): hem flares, waist pinches, shoulders square off
PROF = [(0.0, 0.46), (0.06, 0.45), (0.4, 0.36), (0.8, 0.29), (1.1, 0.24), (1.25, 0.22), (1.45, 0.25),
        (1.65, 0.28), (1.78, 0.27), (1.86, 0.2), (1.93, 0.09), (1.98, 0.075)]


def robe():
    bm = bmesh.new()
    seg = 48
    rows = []
    for z, r in PROF:
        row = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            pleat = 1.0 + 0.07 * math.sin(a * 11) * max(0.0, 1.0 - z / 1.2) ** 1.5
            sq = 1.0 + 0.18 * max(0.0, (z - 1.5) / 0.3) * abs(math.cos(a)) if z < 1.9 else 1.0  # shoulders
            row.append(bm.verts.new((math.cos(a) * r * pleat * sq, math.sin(a) * r * pleat * 0.72, z)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(seg):
            bm.faces.new((rows[j][i], rows[j][(i + 1) % seg], rows[j + 1][(i + 1) % seg], rows[j + 1][i]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj("robe", bm, "plaster", 60.0)


def build(args):
    parts = [robe()]
    # long arms: shoulder -> elbow -> wrist, both cradling the board in front of the chest
    for s in (-1, 1):
        sh = (s * 0.33, 0.0, 1.74)
        el = (s * 0.38, -0.08, 1.36)
        wr = (s * 0.2, -0.34, 1.26)
        pts = [sh, ((sh[0] + el[0]) / 2, -0.03, 1.56), el, ((el[0] + wr[0]) / 2, -0.24, 1.29), wr]
        parts.append(orn.taper("arm%d" % s, pts, [0.07, 0.062, 0.05, 0.042, 0.036], 10, "plaster"))
        hand = orn.ellipsoid("hand%d" % s, (wr[0] * 0.8, -0.4, 1.28), (0.07, 0.05, 0.14), "plaster", 8, 5)
        parts.append(hand)
        for f in range(3):  # long fingers curling over the board edge
            parts.append(orn.taper("fing%d_%d" % (s, f), [(wr[0] * 0.8 + s * 0.01 * f, -0.43, 1.33 - f * 0.03), (wr[0] * 0.7, -0.47, 1.38 - f * 0.04), (wr[0] * 0.6, -0.46, 1.42 - f * 0.05)], [0.012, 0.01, 0.007], 5, "plaster"))
    # brass badge on a lanyard
    parts.append(orn.taper("lanyard", [(-0.1, -0.15, 1.82), (-0.06, -0.21, 1.6), (0.0, -0.215, 1.5), (0.06, -0.21, 1.6), (0.1, -0.15, 1.82)], [0.006] * 5, 4, "velvet"))
    parts.append(kit.box("badge", (0.08, 0.01, 0.05), (0.0, -0.22, 1.47), mat="brass", bevel=0.003, segments=1))
    # a velvet stole over the shoulders, falling in two bands down the front
    def front(z, x):
        r = next(r for zz, r in reversed(PROF) if zz <= z)
        return (x, -r * 0.72 - 0.015, z)
    for s in (-1, 1):
        pts = [(s * 0.2, 0.02, 1.86), front(1.78, s * 0.16), front(1.5, s * 0.13), front(1.2, s * 0.12), front(0.9, s * 0.13), front(0.75, s * 0.14)]
        parts.append(orn.taper("stole%d" % s, pts, [0.07, 0.075, 0.075, 0.07, 0.07, 0.07], 8, "velvet", flat=0.18, up=(0, -1, 0)))
        parts.append(orn.taper("fringe%d" % s, [front(0.75, s * 0.14), front(0.7, s * 0.14)], [0.072, 0.06], 8, "gilt", flat=0.25, up=(0, -1, 0)))
        cuff = kit.torus("cuff%d" % s, 0.042, 0.012, 16, 6, mat="gilt")
        kit.place(cuff, (s * 0.2, -0.34, 1.26), (math.radians(70), 0, s * 0.6))
        parts.append(cuff)
    collar = kit.torus("collar", 0.105, 0.022, 28, 8, mat="gilt")
    kit.place(collar, (0, 0, 1.9), (0, 0, 0), (1.0, 0.8, 1.0))
    parts.append(collar)
    hem = kit.torus("hem", 0.47, 0.018, 64, 6, mat="gilt")
    kit.place(hem, (0, 0, 0.05), (0, 0, 0), (1.0, 0.74, 1.0))
    parts.append(hem)
    kit.join("docent", parts)
    board = kit.box("board", (0.52, 0.025, 0.4), (0, 0, 0), mat="sketch_paper", bevel=0.004, segments=1)
    kit.place(board, (0, -0.44, 1.3), (math.radians(-38), 0, 0))
    clip = kit.box("clip", (0.14, 0.03, 0.04), (0, -0.09, 0.14), mat="brass", bevel=0.004, segments=1)
    kit.place(clip, (0, -0.44, 1.3), (math.radians(-38), 0, 0))
    kit.join("board", [board, clip])
    kit.tube("pencil", [(0.17, -0.44, 1.32), (0.05, -0.5, 1.42)], 0.007, 6, mat="ebony")
    # head: a smooth egg with a faint brow and no face, slightly too small for the body
    head = kit.lathe("head", [(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.1, 0.11), (0.125, 0.19), (0.12, 0.26), (0.095, 0.32), (0.05, 0.355), (0.0, 0.365)], 28, mat="plaster", smooth_angle=80.0)
    kit.place(head, (0, 0, 1.97), (math.radians(-6), 0, 0), (0.86, 1.02, 1.0))
    kit.box("docent-convcolonly", (0.8, 0.7, 2.3), (0, 0, 1.15))
