"""Baroque ornament helpers for the hub build scripts (tapered tubes, C-scrolls, acanthus leaves,
shells, beads). Import with:  sys.path.insert(0, os.path.dirname(__file__)); import orn"""
import math

import bmesh
from mathutils import Matrix, Vector

import kit


def taper(name, pts, radii, sides=8, mat=None, flat=1.0, up=(0, 0, 1)):
    """Closed tube along pts with per-point radius. `flat` squashes the cross-section along `up`
    (leaves, ribbons)."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    U = Vector(up)
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        u = U - d * U.dot(d)
        if u.length < 1e-4:
            u = Vector((1, 0, 0)) - d * d.x
        u.normalize()
        x = d.cross(u).normalized()
        r = radii[i]
        rings.append([bm.verts.new(p + (x * math.cos(2 * math.pi * k / sides) + u * math.sin(2 * math.pi * k / sides) * flat) * r) for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
    for ring in (rings[0], rings[-1]):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        for k in range(sides):
            bm.faces.new((ring[k], ring[(k + 1) % sides], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 70.0)


def spiral(c, r0, r1, a0, a1, n=24):
    """Points on a planar spiral in local (x, z), returned as 2D tuples."""
    out = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        r = r0 + (r1 - r0) * t
        out.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
    return out


def scroll(name, xf, r0, r1, turns, t0, t1, mat="gilt", y=0.0, n=28, sides=8):
    """C-scroll: a spiral ribbon thinning into a curl. `xf` (Matrix) places the local XZ plane."""
    pts2 = spiral((0, 0), r0, r1, 0.0, turns * 2 * math.pi, n)
    pts = [xf @ Vector((x, y, z)) for x, z in pts2]
    radii = [t0 + (t1 - t0) * (i / n) for i in range(n + 1)]
    return taper(name, pts, radii, sides, mat)


def leaf(name, base, direction, length, width, curl=0.6, lobes=4, mat="gilt", lift=(0, -1, 0), n=16):
    """Acanthus leaf: a flattened, lobed blade that rises off the surface (along `lift`) and curls
    over at the tip."""
    B, D, L = Vector(base), Vector(direction).normalized(), Vector(lift).normalized()
    pts, radii = [], []
    for i in range(n + 1):
        t = i / n
        bend = curl * t * t
        p = B + D * (length * t * (1 - 0.35 * bend)) + L * (length * (0.25 * math.sin(t * math.pi) + 0.35 * bend))
        pts.append(p)
        lobe = 0.85 + 0.15 * abs(math.sin(t * lobes * math.pi))
        radii.append(width * (0.35 + math.sin(min(t * 1.15, 1.0) * math.pi) * 0.75) * lobe * (1 - 0.6 * t) + 0.01)
    return taper(name, pts, radii, 8, mat, flat=0.22, up=tuple(L))


def shell(name, centre, radius, ribs=9, mat="gilt", facing=(0, -1, 0), up=(0, 0, 1), depth=0.25):
    """Scallop shell: fan of ribs on a half dome, hinge at `centre`, opening upward."""
    C, F, U = Vector(centre), Vector(facing).normalized(), Vector(up).normalized()
    S = U.cross(F).normalized()
    parts = []
    for k in range(ribs):
        a = math.pi * (0.08 + 0.84 * k / (ribs - 1))
        dirv = S * math.cos(a) + U * math.sin(a)
        pts, rr = [], []
        for i in range(9):
            t = i / 8
            pts.append(C + dirv * radius * t + F * depth * math.sin(t * math.pi * 0.9))
            rr.append(radius * 0.11 * (0.4 + t))
        parts.append(taper("%s_r%d" % (name, k), pts, rr, 6, mat, flat=0.55, up=tuple(F)))
    return parts


def ellipsoid(name, loc, size, mat="gilt", seg=8, rings=5):
    prof = [(math.sin(math.pi * j / rings) * 0.5, -0.5 * math.cos(math.pi * j / rings)) for j in range(rings + 1)]
    ob = kit.lathe(name, prof, seg, mat=mat, smooth_angle=80.0)
    kit.place(ob, loc, (0, 0, 0), size)
    return ob


def along_rect(w, h, step, inset=0.0, skip_bottom=True):
    """Points (x, z) evenly spaced around a rectangle (opening w x h, bottom at z=0) offset outward."""
    hw = w / 2 + inset
    segs = [((-hw, h + inset), (hw, h + inset)), ((hw, h + inset), (hw, 0.0)), ((-hw, 0.0), (-hw, h + inset))]
    if not skip_bottom:
        segs.append(((hw, -inset), (-hw, -inset)))
    out = []
    for (x0, z0), (x1, z1) in segs:
        L = math.hypot(x1 - x0, z1 - z0)
        n = max(1, int(L / step))
        for i in range(n):
            t = (i + 0.5) / n
            out.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, (x1 - x0) / L, (z1 - z0) / L))
    return out


def rot_y(a):
    return Matrix.Rotation(a, 4, "Y")


def face_toward(ob, direction=(0, -1, 0)):
    """Flip an open sweep's normals if they ended up pointing away from the viewer."""
    import bmesh as _bm
    D = Vector(direction)
    bm = _bm.new()
    bm.from_mesh(ob.data)
    score = sum(f.normal.dot(D) * f.calc_area() for f in bm.faces)
    if score < 0:
        _bm.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
    bm.free()
    return ob
