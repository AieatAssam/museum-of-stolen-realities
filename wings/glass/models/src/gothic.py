"""Shared gothic helpers for the Vitrine Kingdom build scripts (import after sys.path insert)."""
import math

import bmesh
from mathutils import Vector

import kit


def pointed(span, rise, n=24):
    """Two-centred pointed arch centre-line as (h, y) from the left springer to the right one."""
    s2 = span / 2.0
    r = (rise * rise + s2 * s2) / span
    assert r >= s2 - 1e-6, "rise too low for a pointed arch"
    c = s2 - r                      # right arc's centre at h = c (left arc's at -c)
    a0 = math.atan2(rise, -c)       # apex angle seen from the right centre
    pts = []
    for i in range(n + 1):          # right half, springer -> apex
        a = a0 * i / n
        pts.append((c + r * math.cos(a), r * math.sin(a)))
    left = [(-h, y) for h, y in pts]           # left springer -> apex
    return left + list(reversed(pts))[1:]      # apex -> right springer


def sweep(name, section, path2d, mat, place=lambda h, y, v: (h, v, y), close=True, smooth=50.0):
    """Sweep a closed 2D section [(u, v)] along an open (h, y) path in a vertical plane.
    u is in-plane and points toward the intrados (the arch's inside), v is across the plane."""
    bm = bmesh.new()
    rings = []
    n = len(path2d)
    for i, (h, y) in enumerate(path2d):    # path runs left -> right, so (d.y, -d.x) is the intrados
        hp, yp = path2d[max(i - 1, 0)]
        hn, yn = path2d[min(i + 1, n - 1)]
        d = Vector((hn - hp, yn - yp)).normalized()
        o = Vector((d.y, -d.x))
        rings.append([bm.verts.new(place(h + o.x * u, y + o.y * u, v)) for u, v in section])
    m = len(section)
    for i in range(n - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(m if close else m - 1):
            bm.faces.new((a[j], b[j], b[(j + 1) % m], a[(j + 1) % m]))
    if close:
        for r in (rings[0], rings[-1]):
            bm.faces.new(r)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


# Rib section: chamfered core with a pear-ish keel roll below and two fillets (u = down/inward).
RIB = [(-0.28, -0.13), (0.02, -0.13), (0.10, -0.07), (0.17, -0.05), (0.24, 0.0), (0.17, 0.05),
       (0.10, 0.07), (0.02, 0.13), (-0.28, 0.13)]


def roll(r, sides=10, u0=0.0, v0=0.0):
    return [(u0 + r * math.cos(2 * math.pi * k / sides), v0 + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
