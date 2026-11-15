"""The Kingdom's glass fabric: modular architecture instanced by MultiMesh. Visual only (the wing keeps
its box colliders). Arg = part (Blender X right, Z up; "facing" means the side toward the room):
  rotunda_bay  one 10-degree bay of the Rose Widow's round hall, origin on the hall's axis at floor
               level, centred on +X: smoked-glass wall (UV in metres for the leading), an engaged shaft,
               a blind arcade, a tall blind lancet, string courses and a cornice. z -11..23.
  triforium    11 m of triforium arcade along X, facing -Y: four pointed arches on colonnettes, sill and
               cornice; origin at the middle of the sill's back edge. 0..4 m tall.
  buttress     a stepped buttress pier with weatherings, 1.4 m square, 0..23 m; origin at its foot.
  flyer        a flying buttress from the pier (x 0.7) to the clerestory wall (x 7.8), coping on top and
               an arched rib below with tracery struts; same origin as the buttress.
  icon_stand   a hinged, hieratic glass icon, standing in prayer: three leaded panels folded like a
               screen, face, joined hands and halo. 1.9 m, origin at its feet, facing -Y."""
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import pointed, roll, sweep  # noqa: E402

MOULD = [(-0.05, -0.16), (0.08, -0.16), (0.14, -0.1), (0.14, 0.1), (0.08, 0.16), (-0.05, 0.16)]


def _curved_slab(name, r0, r1, a0, a1, z0, z1, mat, seg=6):
    """Curved wall between radii r0 < r1 and angles a0..a1 (radians). UV: metres along the inner arc, z."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rows = []
    for r in (r0, r1):
        row = []
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            row.append((bm.verts.new((r * math.cos(a), r * math.sin(a), z0)), bm.verts.new((r * math.cos(a), r * math.sin(a), z1))))
        rows.append(row)
    inner, outer = rows
    def quad(v, uvs):
        f = bm.faces.new(v)
        for loop, t in zip(f.loops, uvs):
            loop[uv].uv = t
    for i in range(seg):
        s0 = r0 * (a0 + (a1 - a0) * i / seg)
        s1 = r0 * (a0 + (a1 - a0) * (i + 1) / seg)
        quad((inner[i][0], inner[i][1], inner[i + 1][1], inner[i + 1][0]), [(s0, z0), (s0, z1), (s1, z1), (s1, z0)])
        quad((outer[i][0], outer[i + 1][0], outer[i + 1][1], outer[i][1]), [(s0, z0), (s1, z0), (s1, z1), (s0, z1)])
    # inner faces the hall axis, outer faces out (wound so; recalc flips an open shell unpredictably)
    return kit._obj(name, bm, mat, 30.0)


def _arc_sweep(name, section, r, a0, a1, z, mat, seg=8):
    """Sweep a 2D section (u = radial inward, v = up) along a horizontal arc."""
    bm = bmesh.new()
    rings = []
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(((r - u) * c, (r - u) * s, z + v)) for u, v in section])
    m = len(section)
    for i in range(seg):
        for j in range(m):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % m], rings[i][(j + 1) % m]))
    for rr in (rings[0], rings[-1]):
        bm.faces.new(rr)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 50.0)


def rotunda_bay():
    half = math.radians(5.0)
    R = 27.5
    p = [_curved_slab("wall", R, 28.5, -half, half, -11.0, 23.0, "glass_wall_uv")]
    # engaged shaft at the bay's edge, ringed with brass
    sh = kit.lathe("shaft", [(0.32, -11.0), (0.32, 23.0)], 12, mat="glass_red_m", cap=False)
    sh.location = (R * math.cos(half), R * math.sin(half), 0)
    p.append(sh)
    for z in (0.0, 10.0, 17.5):
        t = kit.torus("ring", 0.36, 0.05, 20, 8, mat="brass", loc=(R * math.cos(half), R * math.sin(half), z))
        p.append(t)
    # string courses and cornice
    course = [(0.0, -0.18), (0.22, -0.12), (0.3, 0.0), (0.22, 0.1), (0.0, 0.16)]
    for z in (-0.2, 10.0, 22.6):
        p.append(_arc_sweep("course", course, R, -half, half, z, "lead"))
    p.append(_arc_sweep("course_roll", roll(0.05, 8, 0.3, 0.0), R, -half, half, 10.0, "brass"))
    # leaded frames around the two glazed lancets (glass_wall_uv: lw 3.0, tiers 0.8+8.0 and 10.8+11.0,
    # equilateral heads), so the moulding sits exactly on the shader's rim
    def plane(off_z):
        def place(h, y, v):
            return (R - 0.02 - v, h, off_z + y)
        return place
    w = 3.12
    for base, hgt in ((0.8, 8.0), (10.8, 11.0)):
        spring = hgt + 0.06 - w * 0.866
        rt = sorted((q for q in pointed(w, w * 0.866, 20) if q[0] >= 0.0), key=lambda q: q[1])  # springer -> apex
        head = [(-h, y) for h, y in rt] + [q for q in reversed(rt)][1:]                          # left -> right
        path = [(-w / 2, 0.0)] + [(h, y + spring) for h, y in head] + [(w / 2, 0.0)]
        assert all(path[i][0] <= path[i + 1][0] + 1e-6 for i in range(len(path) - 1)), "frame path must run left to right"
        p.append(sweep("frame", MOULD, path, "lead", plane(base - 0.06)))
        p.append(sweep("frame_roll", roll(0.04, 8, 0.12, -0.17), path, "brass", plane(base - 0.06), smooth=70.0))
        p.append(kit.box("sill", (0.3, w + 0.4, 0.14), (R - 0.12, 0.0, base - 0.1), mat="lead", bevel=0.03))
    kit.join("rotunda_bay", p)


def triforium():
    p = [kit.box("sill", (11.0, 0.7, 0.3), (0, 0.35, 0.15), mat="lead", bevel=0.04)]
    p.append(kit.box("cornice", (11.0, 0.6, 0.35), (0, 0.3, 3.85), mat="lead", bevel=0.05))
    p.append(kit.box("cornice_roll", (11.0, 0.08, 0.08), (0, -0.02, 3.68), mat="brass", bevel=0.02))
    span = 11.0 / 4
    for k in range(5):
        x = -5.5 + k * span
        col = kit.lathe("col", [(0.0, 0.3), (0.16, 0.3), (0.16, 0.42), (0.1, 0.5), (0.1, 2.0), (0.14, 2.08), (0.2, 2.22), (0.2, 2.3), (0.0, 2.3)], 12, mat="glass_gold_m")
        col.location = (x, 0.15, 0)
        p.append(col)
        p.append(kit.torus("astragal", 0.11, 0.025, 16, 6, mat="brass", loc=(x, 0.15, 2.02)))
    for k in range(4):
        x = -5.5 + (k + 0.5) * span
        path = pointed(span - 0.2, 1.35, 16)
        place = (lambda xx: (lambda h, y, v: (xx + h, 0.15 + v, 2.3 + y)))(x)
        p.append(sweep("arch", [(-0.12, -0.12), (0.0, -0.12), (0.05, -0.06), (0.05, 0.06), (0.0, 0.12), (-0.12, 0.12)], path, "lead", place))
        p.append(sweep("arch_roll", roll(0.035, 8, 0.05, -0.12), path, "brass", place, smooth=70.0))
    kit.join("triforium", p)


def _frustum(name, w0, w1, z0, z1, mat):
    bm = bmesh.new()
    vs = []
    for w, z in ((w0, z0), (w1, z1)):
        vs.append([bm.verts.new((sx * w / 2, sy * w / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(4):
        bm.faces.new((vs[0][i], vs[0][(i + 1) % 4], vs[1][(i + 1) % 4], vs[1][i]))
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.03, segments=1, affect="EDGES")
    return kit._obj(name, bm, mat, 30.0)


def buttress():
    # three stages, each set back under a sloped weathering; lead quoins on every arris
    p = []
    stages = [(1.4, 0.0, 8.0), (1.2, 8.6, 15.0), (1.0, 15.6, 23.0)]
    for i, (w, z0, z1) in enumerate(stages):
        p.append(kit.box("stage%d" % i, (w, w, z1 - z0), (0, 0, (z0 + z1) / 2), mat="glass_red", bevel=0.04))
        p.append(_frustum("weather%d" % i, w + 0.12, (stages[i + 1][0] if i < 2 else w) + 0.02, z1, z1 + 0.6, "lead"))
        for sx in (-1, 1):
            for sy in (-1, 1):
                p.append(kit.box("quoin", (0.06, 0.06, z1 - z0), (sx * w / 2, sy * w / 2, (z0 + z1) / 2), mat="lead"))
        # a blind lancet on the face toward the nave
        path = [(-w * 0.28, 0.0)] + [(h, y + (z1 - z0) * 0.55) for h, y in pointed(w * 0.56, w * 0.5, 10)] + [(w * 0.28, 0.0)]
        place = (lambda zz, ww: (lambda h, y, v: (ww / 2 + 0.02 + v * 0.3, h, zz + y)))(z0 + 0.6, w)
        p.append(sweep("blind%d" % i, [(-0.04, -0.06), (0.04, -0.06), (0.04, 0.06), (-0.04, 0.06)], path, "brass", place))
    p.append(_frustum("plinth", 1.7, 1.45, -0.01, 0.8, "lead"))
    kit.join("buttress", p)


def flyer():
    p = []
    a = Vector((0.7, 0, 22.0))
    b = Vector((7.8, 0, 25.0))
    d = (b - a)
    ln = d.length
    ang = math.atan2(d.z, d.x)
    cop = kit.box("coping", (ln, 0.6, 0.45), (0, 0, 0), mat="glass_gold", bevel=0.05)
    cop.location = (a + b) / 2
    cop.rotation_euler = (0, -ang, 0)
    p.append(cop)
    cap = kit.box("coping_lead", (ln, 0.7, 0.08), (0, 0, 0.27), mat="lead", bevel=0.02)
    cap.location = (a + b) / 2
    cap.rotation_euler = (0, -ang, 0)
    p.append(cap)
    # the arch: quarter ellipse from the pier at z 17.5 up under the coping at the wall
    pts = []
    for i in range(17):
        t = i / 16
        x = 0.7 + 7.1 * math.sin(t * math.pi / 2)
        z = 17.5 + (24.2 - 17.5) * (1 - math.cos(t * math.pi / 2)) ** 0.8
        pts.append((x, z))
    p.append(sweep("rib", [(-0.22, -0.25), (0.12, -0.25), (0.2, -0.12), (0.2, 0.12), (0.12, 0.25), (-0.22, 0.25)], pts, "glass_gold", lambda h, y, v: (h, v, y)))
    p.append(sweep("rib_roll", roll(0.05, 8, 0.2, 0.0), pts, "brass", lambda h, y, v: (h, v, y), smooth=70.0))
    # tracery struts between rib and coping
    for k in range(1, 6):
        x = 0.7 + 7.1 * k / 6
        t = math.asin(min(1.0, (x - 0.7) / 7.1)) / (math.pi / 2)
        zr = 17.5 + (24.2 - 17.5) * (1 - math.cos(t * math.pi / 2)) ** 0.8
        zc = 22.0 + 3.0 * (x - 0.7) / 7.1 - 0.25
        if zc - zr > 0.3:
            p.append(kit.box("strut%d" % k, (0.09, 0.12, zc - zr), (x, 0, (zc + zr) / 2), mat="lead", bevel=0.015))
    kit.join("flyer", p)


def _extrude(name, poly, depth, mat):
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x, 0.0, z)) for x, z in poly])
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    vs = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0, depth, 0)), verts=vs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.006, segments=1, affect="EDGES")
    return kit._obj(name, bm, mat, 40.0)


def _came(name, poly, y):
    pts = [(x, y, z) for x, z in poly] + [(poly[0][0], y, poly[0][1])]
    return kit.tube(name, pts, 0.012, 6, mat="lead")


def icon_stand():
    # half-width of the robe by height (feet 0 .. shoulders 1.45)
    def w(z):
        return 0.34 - 0.12 * (z / 1.45) + 0.03 * math.sin(z * 2.2)
    hinge = 0.12
    zs = [i * 1.45 / 10 for i in range(11)]
    centre = [(-hinge, 0.0), (hinge, 0.0)] + [(hinge, z) for z in zs[1:]] + [(0.1, 1.5), (0.06, 1.52)] + [(-0.06, 1.52), (-0.1, 1.5)] + [(-hinge, z) for z in reversed(zs[1:])]
    p = [_extrude("panel_c", centre, 0.04, "icon_robe"), _came("came_c", centre, -0.004)]
    side = [(hinge, 0.0), (w(0.0), 0.0)] + [(w(z), z) for z in zs[1:]] + [(hinge + 0.02, 1.45)]
    for s in (-1, 1):
        poly = [(s * x, z) for x, z in side]
        if s < 0:
            poly = list(reversed(poly))
        pan = _extrude("panel", poly, 0.04, "icon_robe")
        came = _came("came", poly, -0.004)
        for ob in (pan, came):
            # fold back on the hinge like a triptych
            ob.location = (s * hinge, 0, 0)
            ob.data.transform(__import__("mathutils").Matrix.Translation((-s * hinge, 0, 0)))
            ob.rotation_euler = (0, 0, s * math.radians(22))
        p += [pan, came]
        # horizontal cames across the robe panels
        for z in (0.35, 0.75, 1.1):
            bar = kit.tube("rib", [(s * hinge, -0.006, z), (s * (hinge + (w(z) - hinge) * 0.93), -0.006 - (w(z) - hinge) * 0.4, z)], 0.01, 5, mat="lead")
            p.append(bar)
    # head: an oval pane with its came, a gold halo behind, a face in grisaille-pale glass
    head = [(0.11 * math.cos(a), 1.68 + 0.14 * math.sin(a)) for a in [k * 2 * math.pi / 20 for k in range(20)]]
    p.append(_extrude("face", head, 0.05, "icon_face"))
    p.append(_came("came_h", head, -0.004))
    halo = [(0.24 * math.cos(a), 1.7 + 0.24 * math.sin(a)) for a in [k * 2 * math.pi / 28 for k in range(28)]]
    hal = _extrude("halo", halo, 0.025, "glass_gold")
    hal.location = (0, 0.06, 0)
    p.append(hal)
    p.append(_came("came_halo", [(x, z) for x, z in halo], 0.056))
    # hands joined in prayer, pointing up, standing proud of the robe
    hands = [(-0.05, 1.05), (0.05, 1.05), (0.03, 1.22), (0.0, 1.3), (-0.03, 1.22)]
    hd = _extrude("hands", hands, 0.05, "icon_face")
    hd.location = (0, -0.06, 0)
    p.append(hd)
    p.append(_came("came_hands", hands, -0.065))
    # a lead plinth
    p.append(kit.box("foot", (0.8, 0.3, 0.06), (0, 0.02, 0.03), mat="lead", bevel=0.01))
    kit.join("icon_stand", p)


def build(args):
    {"rotunda_bay": rotunda_bay, "triforium": triforium, "buttress": buttress, "flyer": flyer,
     "icon_stand": icon_stand}[args[0]]()
