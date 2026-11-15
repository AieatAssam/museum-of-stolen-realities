"""The crypt's low ribbed vault (visual only; the code boxes stay the colliders). Blender X = Godot x,
Blender Y = Godot -z, Z = Godot y; heights are absolute (crypt floor at -8, choir floor above at 2.1).
Arg:
  rib   one transverse rib across the 30 m crypt (segmental: springs at -3.0 on the walls x = +/-15,
        crowns at 1.9), with an engaged pier under each end (base, shaft, foliate capital). Origin at
        the rib's centre line, z = 0.
  web   one 1 m long slice of the barrel web between ribs (instances scale it along Y to the bay)
        plus, for a 6 m bay, two diagonal ribs and a ring boss; built at length 6 and scaled."""
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import RIB, roll, sweep  # noqa: E402

S2, SPRING, CROWN = 15.0, -3.0, 1.9
RISE = CROWN - SPRING
RAD = (S2 * S2 + RISE * RISE) / (2 * RISE)
CY = CROWN - RAD
L = 6.0


def f(x):
    """Barrel height over x."""
    return CY + math.sqrt(max(RAD * RAD - x * x, 0.0))


def arc(n=40):
    return [(-S2 + 2 * S2 * i / n, f(-S2 + 2 * S2 * i / n)) for i in range(n + 1)]


assert abs(f(S2) - SPRING) < 1e-6 and abs(f(0) - CROWN) < 1e-6


def pier(x, sign):
    prof = [(0.0, -8.0), (0.62, -8.0), (0.62, -7.75), (0.52, -7.65), (0.46, -7.45), (0.4, -7.35), (0.38, -4.2),
            (0.43, -4.1), (0.4, -4.0), (0.48, -3.7), (0.62, -3.45), (0.7, -3.3), (0.7, -3.05), (0.0, -3.05)]
    col = kit.lathe("pier", prof, 24, mat="glass_red_m")
    col.location = (x, 0, 0)
    ring = kit.torus("astragal", 0.41, 0.04, 24, 8, mat="brass", loc=(x, 0, -4.1))
    return [col, ring]


def rib():
    path = arc()
    plane = lambda h, y, v: (h, v, y)  # noqa: E731
    p = [sweep("rib", RIB, path, "lead", plane), sweep("rib_roll", roll(0.06, 10, 0.2), path, "brass", plane, smooth=70.0)]
    for s in (-1, 1):
        p += pier(s * 14.85, s)
    kit.join("crypt_rib", p)


def web():
    bm = bmesh.new()
    n = 40
    rows = []
    for j in (0, 1):
        rows.append([bm.verts.new((x, j * L, y)) for x, y in arc(n)])
    for i in range(n):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for fc in bm.faces:  # face down, into the crypt
        if fc.normal.z > 0:
            fc.normal_flip()
    p = [kit._obj("web", bm, "glass_vault", 30.0)]
    # diagonal ribs riding the barrel, corner to corner, and a ring boss where they cross
    for s in (-1, 1):
        def place(h, y, v, s=s):
            t = (h + S2) / (2 * S2)
            return (h, (t if s > 0 else 1 - t) * L + v, y)
        p.append(sweep("diag", RIB[:], arc(), "lead", place))
    boss = kit.torus("boss", 0.55, 0.12, 32, 10, mat="brass", loc=(0, L / 2, CROWN - 0.12))
    p.append(boss)
    p.append(kit.torus("boss_lead", 0.75, 0.05, 32, 8, mat="lead", loc=(0, L / 2, CROWN - 0.06)))
    kit.join("crypt_web", p)


def build(args):
    rib() if args and args[0] == "rib" else web()
