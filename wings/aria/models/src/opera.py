"""The Drowned Aria, art pass: the opera-house kit and hero props.

Build one model per run:
  tools/blender_build.sh wings/aria/models/src/opera.py wings/aria/models/<kind>.glb <kind>
(wings/aria/tools/build_models.sh builds them all.)

Units: metres, +Z up (Godot +Y). Wall modules stand on z=0 with their wall plane at y=0 and their
front toward -Y (Godot +Z). No colliders anywhere: the wing keeps its own code-built colliders, so
dressing can never change a route or a lift.
"""
import math

import bmesh
import bpy
from mathutils import Vector

import kit

TAU = 2 * math.pi
UP = Vector((0, 0, 1))


# --- helpers -------------------------------------------------------------------------------------

def sweep(name, profile, path, mat, closed_path=False, cap=True, smooth=40.0, axis=None):
    """Sweep a closed 2D profile [(u, v)] along a 3D polyline. u = horizontal outward (tangent x up),
    v = world up. A path that runs toward +X has its outward side at -Y (the front)."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    bm = bmesh.new()
    rings = []
    for i in range(n):
        if closed_path:
            t = (pts[(i + 1) % n] - pts[i - 1])
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        up = UP if axis is None else Vector(axis)
        if axis is None:
            t.z = 0.0
        t.normalize()
        o = t.cross(up).normalized()
        if axis is None and (closed_path or 0 < i < n - 1):
            # mitre: scale so straight runs keep their width through a corner
            a = (pts[i] - pts[i - 1 if i > 0 else n - 1])
            a.z = 0
            if a.length > 1e-6:
                o0 = a.normalized().cross(UP)
                k = max(o.dot(o0), 0.35)
                o = o / k
        rings.append([bm.verts.new(pts[i] + o * u + up * v) for u, v in profile])
    m = len(profile)
    segs = n if closed_path else n - 1
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % n]
        for j in range(m):
            bm.faces.new((a[j], b[j], b[(j + 1) % m], a[(j + 1) % m]))
    if cap and not closed_path:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def arc(cx, cy, r, a0, a1, n, z=0.0, sx=1.0, sy=1.0):
    return [(cx + sx * r * math.cos(a0 + (a1 - a0) * i / n), cy + sy * r * math.sin(a0 + (a1 - a0) * i / n), z) for i in range(n + 1)]


def lathe_fn(name, zs, rfn, segments, mat, smooth=50.0, cap=True):
    """Lathe whose radius depends on height and angle: rfn(z, theta). For flutes and gadrooning."""
    bm = bmesh.new()
    rings = []
    for z in zs:
        rings.append([bm.verts.new((rfn(z, TAU * i / segments) * math.cos(TAU * i / segments),
                                    rfn(z, TAU * i / segments) * math.sin(TAU * i / segments), z)) for i in range(segments)])
    for j in range(len(zs) - 1):
        for i in range(segments):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % segments], rings[j + 1][(i + 1) % segments], rings[j + 1][i]))
    if cap:
        f = bm.faces.new(rings[0])
        f.normal_flip()
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def grid(name, nx, nz, fn, mat, smooth=60.0):
    """A sheet: fn(u, v) -> (x, y, z) for u, v in 0..1. For curtains, canvases and cloth."""
    bm = bmesh.new()
    vs = [[bm.verts.new(fn(i / nx, j / nz)) for i in range(nx + 1)] for j in range(nz + 1)]
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for lp in f.loops:
            idx = lp.vert.index
            lp[uv].uv = (0, 0)
    bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            i = lp.vert.index % (nx + 1)
            j = lp.vert.index // (nx + 1)
            lp[uv].uv = (i / nx, 1.0 - j / nz)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, smooth)


def ring_of(fn, n, *args):
    return [fn(i, *args) for i in range(n)]


def moved(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    ob.location = loc
    ob.rotation_euler = rot
    if scale:
        ob.scale = scale
    return ob


# profiles (u outward, v up), closed loops
def p_rect(w, h, u0=0.0, v0=0.0):
    return [(u0, v0), (u0 + w, v0), (u0 + w, v0 + h), (u0, v0 + h)]


P_CORNICE = [(0.0, 0.0), (0.06, 0.0), (0.08, 0.04), (0.06, 0.08), (0.12, 0.14), (0.2, 0.22), (0.24, 0.3), (0.34, 0.34),
             (0.42, 0.42), (0.42, 0.48), (0.46, 0.5), (0.46, 0.58), (0.0, 0.58)]
P_RAIL = [(0.0, 0.0), (0.09, 0.0), (0.11, 0.03), (0.1, 0.07), (0.12, 0.1), (0.1, 0.14), (0.0, 0.14)]
P_BEAD = [(0.0, 0.0), (0.04, 0.01), (0.06, 0.04), (0.04, 0.07), (0.0, 0.08)]
P_FRAME = [(0.0, 0.0), (0.03, 0.0), (0.05, 0.02), (0.07, 0.025), (0.09, 0.012), (0.1, 0.0), (0.1, -0.02), (0.0, -0.02)]


def frame(name, w, h, loc, mat="gilt", prof=None, y=0.0):
    """Moulded picture frame standing upright in the XZ plane, front toward -Y."""
    prof = prof or [(0.0, 0.0), (0.0, 0.04), (0.03, 0.07), (0.07, 0.06), (0.1, 0.03), (0.12, 0.0)]
    hw, hh = w / 2, h / 2
    path = [(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)]
    ob = kit.sweep_closed(name, [(u, -v) for u, v in prof], path, mat=mat)
    ob.location = (loc[0], y + loc[1], loc[2])
    return ob


def fluted_column(name, h, r, mat, base=True, flutes=20):
    """Corinthian-ish column: attic base, fluted shaft with entasis, a bell capital with volutes."""
    parts = []
    if base:
        parts.append(kit.lathe(name + "_base", [(r * 1.45, 0.0), (r * 1.45, 0.12), (r * 1.3, 0.16), (r * 1.32, 0.24), (r * 1.18, 0.3),
                                                (r * 1.12, 0.36), (r * 1.2, 0.42), (r * 1.08, 0.48), (r * 1.02, 0.5)], segments=24, mat=mat))
    z0, z1 = 0.5, h - 0.9 * r * 1.6
    zs = [z0 + (z1 - z0) * k / 16 for k in range(17)]

    def rfn(z, th):
        t = (z - z0) / (z1 - z0)
        ent = r * (1.0 - 0.12 * t * t)
        fl = 0.0 if t < 0.02 or t > 0.98 else 0.06 * r * max(0.0, math.cos(flutes * th)) ** 0.5
        return ent - fl
    parts.append(lathe_fn(name + "_shaft", zs, rfn, flutes * 4, mat))
    ch = h - z1
    parts.append(kit.lathe(name + "_cap", [(r * 0.9, z1), (r * 1.0, z1 + 0.04), (r * 0.92, z1 + 0.08), (r * 1.0, z1 + ch * 0.45),
                                           (r * 1.35, z1 + ch * 0.8), (r * 1.55, z1 + ch * 0.82), (r * 1.55, h), (0.0, h)], segments=24, mat="gilt"))
    # acanthus: two rings of leaves curling outward
    for row, (zz, n, ln) in enumerate([(z1 + ch * 0.12, 8, 0.45), (z1 + ch * 0.32, 8, 0.5)]):
        for i in range(n):
            a = TAU * (i + 0.5 * row) / n
            c, s = math.cos(a), math.sin(a)
            rr = r * 0.95
            pts = [(rr * c, rr * s, zz), (rr * 1.08 * c, rr * 1.08 * s, zz + ch * ln * 0.6), (rr * 1.35 * c, rr * 1.35 * s, zz + ch * ln),
                   (rr * 1.42 * c, rr * 1.42 * s, zz + ch * ln * 0.82)]
            parts.append(kit.tube(name + "_leaf", pts, r * 0.11, sides=6, mat="gilt"))
    for i in range(4):  # corner volutes
        a = TAU * (i + 0.5) / 4
        c, s = math.cos(a), math.sin(a)
        v = kit.torus(name + "_volute", r * 0.18, r * 0.06, seg=16, rseg=6, mat="gilt",
                      loc=(r * 1.4 * c, r * 1.4 * s, h - ch * 0.25), rot=(math.pi / 2, 0, a + math.pi / 2))
        parts.append(v)
    return kit.join(name, parts)


def lamp(name, loc, scale=1.0):
    """Wall sconce on the wall plane y = loc[1], projecting toward -Y: a gilt oval backplate with a moulded
    rim, two S-scrolled gilt arms to bobeche cups, a wax candle with a teardrop flame in each, a pleated
    silk shade over each candle, and three crystal drops. Every size is multiplied by scale."""
    x, y, z = loc
    s = scale
    P = []

    # backplate: a flat oval cartouche 0.16 x 0.30, moulded rim swept round its edge
    plate = kit.lathe(name + "_plate", [(1.0, -0.5), (1.0, 0.5)], segments=24, mat="gilt")
    plate.rotation_euler = (math.pi / 2, 0, 0)
    plate.scale = (0.08 * s, 0.15 * s, 0.02 * s)
    plate.location = (x, y, z)
    P.append(plate)
    rim_path = [(x + 0.08 * s * math.cos(TAU * i / 20), y - 0.02 * s, z + 0.15 * s * math.sin(TAU * i / 20)) for i in range(20)]
    P.append(sweep(name + "_rim", [(-0.008 * s, 0.0), (-0.006 * s, 0.007 * s), (0.0, 0.011 * s), (0.006 * s, 0.007 * s),
                                   (0.008 * s, 0.0), (0.0, -0.004 * s)], rim_path, "gilt", closed_path=True, axis=(0, -1, 0)))

    def shade_r(zz, th):
        # 12 pleats: a sin on the radius, widening from 0.05 to 0.08 over the height
        return s * (0.05 + 0.03 * zz / (0.1 * s)) * (1 + 0.04 * math.sin(12 * th))

    for k in (-1, 1):
        cx, cy, cz = x + k * 0.085 * s, y - 0.2 * s, z + 0.1 * s
        # S-scroll arm: out from the plate, down-and-up in an S, ending under the cup
        arm = []
        for i in range(7):
            t = i / 6
            sm = t * t * (3 - 2 * t)
            arm.append((x + k * s * (0.01 + 0.075 * t), y - s * (0.02 + 0.18 * t), z - s * (0.09 - 0.17 * sm) + 0.025 * s * math.sin(TAU * t)))
        P.append(kit.tube(name + "_arm", arm, 0.011 * s, 8, "gilt"))
        P.append(kit.lathe(name + "_drop_arm", [(0.0, 0.0), (0.006 * s, -0.012 * s), (0.008 * s, -0.03 * s), (0.004 * s, -0.045 * s), (0.0, -0.05 * s)],
                           segments=6, mat="crystal", smooth_angle=None))
        P[-1].location = (arm[3][0], arm[3][1], arm[3][2] - 0.006 * s)
        # bobeche dish, candle, flame and pleated shade
        cup = kit.lathe(name + "_cup", [(0.0, 0.0), (0.02 * s, 0.0), (0.03 * s, 0.006 * s), (0.05 * s, 0.016 * s),
                                        (0.045 * s, 0.02 * s), (0.035 * s, 0.012 * s), (0.0, 0.012 * s)], segments=20, mat="gilt")
        cup.location = (cx, cy, cz)
        P.append(cup)
        candle = kit.lathe(name + "_candle", [(0.0, 0.0), (0.012 * s, 0.0), (0.012 * s, 0.12 * s), (0.0, 0.12 * s)], segments=12, mat="wax")
        candle.location = (cx, cy, cz + 0.012 * s)
        P.append(candle)
        flame = kit.lathe(name + "_flame", [(0.0, 0.0), (0.005 * s, 0.01 * s), (0.007 * s, 0.025 * s), (0.003 * s, 0.04 * s), (0.0, 0.045 * s)],
                          segments=8, mat="flame", smooth_angle=None)
        flame.location = (cx, cy, cz + 0.132 * s)
        P.append(flame)
        shade = lathe_fn(name + "_shade", [q * s for q in (0.0, 0.02, 0.04, 0.06, 0.08, 0.1)], shade_r, 36, "lamp_glow", cap=False)
        shade.location = (cx, cy, cz + 0.02 * s)
        P.append(shade)

    # three crystal drops: one under each arm and one under the plate
    P.append(kit.lathe(name + "_drop", [(0.0, 0.0), (0.006 * s, -0.012 * s), (0.008 * s, -0.03 * s), (0.004 * s, -0.045 * s), (0.0, -0.05 * s)],
                       segments=6, mat="crystal", smooth_angle=None))
    P[-1].location = (x, y - 0.13 * s, z - 0.12 * s)
    return P


def drape(name, x0, x1, z_top, sag, y=0.0, depth=0.25, folds=7, mat="velvet_drape", tassel=True):
    """A swagged valance: a fabric band hanging in a catenary with vertical folds and gathered ends."""
    def fn(u, v):
        x = x0 + (x1 - x0) * u
        drop = sag * math.sin(math.pi * u)
        z = z_top - v * (0.35 + drop)
        fold = depth * 0.25 * math.sin(folds * TAU * u) * (0.4 + v)
        return (x, y - depth * 0.5 * math.sin(math.pi * u) - fold, z)
    parts = [grid(name, 40, 6, fn, mat)]
    if tassel:
        for xx in (x0, x1):
            parts.append(kit.lathe(name + "_tassel", [(0.0, 0.0), (0.06, 0.04), (0.07, 0.22), (0.03, 0.3), (0.04, 0.36), (0.0, 0.42)], segments=10, mat="gilt"))
            parts[-1].location = (xx, y - 0.05, z_top - 0.95)
    return parts


# --- wall modules --------------------------------------------------------------------------------

def tier_bay():
    """One 4 m bay of the horseshoe: a rusticated base, three tiers of boxes with bellied gilt parapets,
    velvet interiors and valances, fluted columns between bays, a cornice and an ornament frieze."""
    W = 4.0
    P = []
    # rusticated base, five courses
    for k in range(5):
        P.append(kit.box("rustic", (W - 0.02, 0.32, 0.56), (0, -0.16, 0.3 + 0.6 * k), mat="marble_teal", bevel=0.04, segments=2))
    P.append(kit.box("base_plinth", (W, 0.4, 0.2), (0, -0.2, 0.1), mat="marble_teal", bevel=0.02))
    for t in range(3):
        z = 3.2 + 3.2 * t
        # box back wall and its gilt-framed velvet panel
        P.append(kit.box("box_back", (W, 0.1, 3.2), (0, 0.05, z + 1.6), mat="velvet"))
        P.append(frame("box_panel", 2.2, 1.6, (0, -0.0, z + 1.75), mat="gilt"))
        # partitions between boxes
        for sx in (-1, 1):
            P.append(kit.box("partition", (0.12, 1.25, 2.7), (sx * (W / 2 - 0.06), -0.62, z + 1.35), mat="velvet", bevel=0.03))
            P.append(kit.box("partition_edge", (0.16, 0.08, 2.7), (sx * (W / 2 - 0.06), -1.25, z + 1.35), mat="gilt", bevel=0.02))
            P.extend(lamp("sconce", (sx * (W / 2 - 0.2), -0.9, z + 1.9), 1.0))
        # the tier floor: a bellied slab, plan arc from the partitions out to the parapet
        plan = arc(0, -1.1, W / 2 - 0.02, math.pi, 2 * math.pi, 16, sy=0.25)
        slab = [(x, y, z - 0.28) for x, y, _ in plan]
        P.append(sweep("tier_soffit", [(0.0, 0.0), (0.0, 0.28), (-1.2, 0.28), (-1.2, 0.0)], slab, "gilt", cap=True))
        # bellied parapet: a moulded band swept along the plan arc
        rail = [(x, y, z) for x, y, _ in plan]
        P.append(sweep("parapet_face", [(-0.08, 0.0), (0.02, 0.0), (0.06, 0.12), (0.06, 0.8), (0.02, 0.9), (-0.08, 0.9)], rail, "gilt_orn"))
        P.append(sweep("parapet_base", [(-0.1, -0.12), (0.1, -0.12), (0.14, -0.04), (0.1, 0.04), (-0.1, 0.04)], rail, "gilt"))
        P.append(sweep("parapet_rail", [(-0.12, 0.88), (0.1, 0.88), (0.14, 0.94), (0.12, 1.0), (0.04, 1.04), (-0.12, 1.04)], rail, "velvet"))
        P.append(sweep("parapet_bead", [(-0.02, 0.86), (0.13, 0.86), (0.15, 0.9), (-0.02, 0.9)], rail, "gilt"))
        # a cartouche at the belly
        c = kit.lathe("cartouche", [(0.0, 0.0), (0.22, 0.0), (0.26, 0.03), (0.22, 0.06), (0.12, 0.09), (0.0, 0.1)], segments=20, mat="gilt")
        c.rotation_euler = (math.pi / 2, 0, 0)
        c.scale = (1.0, 1.3, 1.0)
        c.location = (0, -1.1 - (W / 2) * 0.25 - 0.07, z + 0.45)
        P.append(c)
        # valance across the box opening
        P.extend(drape("valance", -W / 2 + 0.2, W / 2 - 0.2, z + 3.0, 0.25, y=-1.2, depth=0.2, folds=6, tassel=True))
    # columns between bays (half of each at either edge, so bays tile)
    for sx in (-1, 1):
        col = fluted_column("bay_column", 9.6, 0.2, "marble_ivory", flutes=16)
        col.location = (sx * W / 2, -1.35, 3.0)
        P.append(col)
    # cornice and frieze
    P.append(sweep("cornice", P_CORNICE, [(-W / 2, -1.0, 12.8), (W / 2, -1.0, 12.8)], "gilt"))
    P.append(kit.box("frieze", (W, 0.9, 0.9), (0, -0.5, 12.35), mat="gilt_orn"))
    P.append(kit.box("attic", (W, 0.3, 1.2), (0, -0.15, 13.9), mat="damask_ox"))
    kit.join("tier_bay", P)


def panel_bay():
    """A 4 m wall bay for the foyer and the passages: marble dado, a gilt-framed damask panel between
    fluted pilasters, an entablature, an upper lunette panel and a cornice. 14 m tall."""
    W = 4.0
    P = [kit.box("dado", (W, 0.18, 1.1), (0, -0.09, 0.55), mat="marble_teal", bevel=0.01),
         kit.box("skirt", (W, 0.26, 0.18), (0, -0.13, 0.09), mat="marble_ivory", bevel=0.02)]
    P.append(sweep("dado_rail", [(0.0, 0.0), (0.06, 0.0), (0.08, 0.04), (0.05, 0.08), (0.0, 0.08)], [(-W / 2, -0.18, 1.1), (W / 2, -0.18, 1.1)], "gilt"))
    P.append(kit.box("wall", (W, 0.1, 12.9), (0, -0.05, 1.1 + 6.45), mat="damask_ox"))
    P.append(frame("panel_frame", 2.5, 4.4, (0, -0.1, 3.7), mat="gilt"))
    P.append(frame("panel_inner", 2.1, 4.0, (0, -0.1, 3.7), mat="gilt", prof=[(0.0, 0.0), (0.0, 0.02), (0.02, 0.03), (0.04, 0.0)]))
    # rosette crest above the panel
    ros = kit.lathe("rosette", [(0.0, 0.0), (0.3, 0.0), (0.34, 0.04), (0.26, 0.09), (0.16, 0.08), (0.08, 0.13), (0.0, 0.14)], segments=24, mat="gilt")
    ros.rotation_euler = (math.pi / 2, 0, 0)
    ros.location = (0, -0.1, 6.35)
    P.append(ros)
    for sx in (-1, 1):
        pil = fluted_column("pilaster", 6.6, 0.22, "marble_ivory", flutes=12)
        pil.scale = (1.0, 0.5, 1.0)
        pil.location = (sx * W / 2, -0.1, 1.1)
        P.append(pil)
        P.extend(lamp("sconce", (sx * 1.5, -0.12, 2.4), 1.2))
    P.append(kit.box("architrave", (W, 0.4, 0.4), (0, -0.2, 7.9), mat="marble_ivory", bevel=0.02))
    P.append(kit.box("frieze", (W, 0.34, 0.55), (0, -0.17, 8.37), mat="gilt_orn"))
    P.append(sweep("entab_cornice", [(u * 0.7, v * 0.7) for u, v in P_CORNICE], [(-W / 2, -0.34, 8.62), (W / 2, -0.34, 8.62)], "gilt"))
    # upper lunette: an arched frame
    lun = arc(0, 0, 1.4, math.pi, 0, 20)
    P.append(sweep("lunette", [(0.0, 0.0), (0.0, 0.1), (-0.06, 0.14), (-0.12, 0.1), (-0.12, 0.0)],
                   [(-1.4, -0.12, 9.4)] + [(x, -0.12, 10.4 + y) for x, y, _ in lun] + [(1.4, -0.12, 9.4)], "gilt", smooth=60, axis=(0, -1, 0)))
    P.append(kit.box("lunette_field", (2.8, 0.06, 1.0), (0, -0.07, 9.9), mat="gilt_orn"))
    P.append(sweep("cornice", P_CORNICE, [(-W / 2, -0.1, 13.3), (W / 2, -0.1, 13.3)], "gilt"))
    kit.join("panel_bay", P)


def proscenium():
    """The hero: a 30 m gilt proscenium. Paired giant columns on pedestals, a moulded arch with a lyre
    cartouche, an ornament band, heavy oxblood swags across the top and side curtains pooled on the
    stage. Front toward -Y. Opening is x -11..11, up to z 11.5."""
    P = []
    for sx in (-1, 1):
        for dx in (0.0, 1.4):
            x = sx * (11.8 + dx)
            P.append(kit.box("pedestal", (1.3, 1.3, 1.6), (x, 0, 0.8), mat="marble_teal", bevel=0.05))
            P.append(sweep("ped_cap", [(0.0, 0.0), (0.06, 0.0), (0.1, 0.06), (0.08, 0.12), (0.0, 0.12)], [(x - 0.65, -0.65, 1.6), (x + 0.65, -0.65, 1.6)], "gilt"))
            col = fluted_column("giant_col", 10.0, 0.42, "marble_ivory", flutes=20)
            col.location = (x, 0, 1.6)
            P.append(col)
        # side wall of the frame between the columns and the hall wall
        P.append(kit.box("pros_jamb", (2.4, 1.0, 12.0), (sx * 14.0, 0.6, 6.0), mat="damask_ox"))
    # entablature across the full width
    P.append(kit.box("pros_architrave", (30.0, 1.4, 0.7), (0, 0, 11.95), mat="marble_ivory", bevel=0.04))
    P.append(kit.box("pros_frieze", (30.0, 1.2, 1.0), (0, 0, 12.8), mat="gilt_orn"))
    P.append(sweep("pros_cornice", [(u * 1.6, v * 1.6) for u, v in P_CORNICE], [(-15.0, -0.6, 13.3), (15.0, -0.6, 13.3)], "gilt"))
    # the arch: a moulded gilt band springing from the inner columns
    a = arc(0, 0, 11.0, math.pi, 0, 40, sy=0.32)
    path = [(x, -0.7, 7.6 + y) for x, y, _ in a]
    P.append(sweep("pros_arch", [(0.0, 0.0), (0.0, 0.5), (0.1, 0.55), (0.25, 0.45), (0.3, 0.2), (0.3, -0.1), (0.2, -0.2), (0.0, -0.2)],
                   [(-11.0, -0.7, 0.2)] + [(x, y, z) for x, y, z in path] + [(11.0, -0.7, 0.2)], "gilt", smooth=60, axis=(0, -1, 0)))
    # spandrels behind the arch
    sp = [(x, 0.0, 7.6 + y) for x, y, _ in a]
    bm = bmesh.new()
    top = 11.6
    for i in range(len(sp) - 1):
        (x0, _, z0), (x1, _, z1) = sp[i], sp[i + 1]
        v = [bm.verts.new((x0, -0.3, z0)), bm.verts.new((x1, -0.3, z1)), bm.verts.new((x1, -0.3, top)), bm.verts.new((x0, -0.3, top))]
        bm.faces.new(v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    P.append(kit._obj("spandrel", bm, "damask_ox", 30))
    # lyre cartouche at the keystone
    lyre = [kit.lathe("cart_disc", [(0.0, 0.0), (1.1, 0.0), (1.2, 0.08), (1.05, 0.18), (0.6, 0.24), (0.0, 0.26)], segments=32, mat="gilt")]
    lyre[-1].rotation_euler = (math.pi / 2, 0, 0)
    lyre[-1].scale = (1.0, 1.35, 1.0)
    lyre[-1].location = (0, -0.9, 11.6)
    for sx in (-1, 1):
        pts = [(sx * 0.15, -1.2, 10.9), (sx * 0.6, -1.25, 11.3), (sx * 0.55, -1.25, 11.9), (sx * 0.3, -1.25, 12.3), (sx * 0.45, -1.2, 12.6)]
        lyre.append(kit.tube("lyre_arm", pts, 0.07, 8, "gilt"))
        # palm fronds sweeping from the cartouche
        for k in range(5):
            ang = 0.25 + 0.28 * k
            pts = [(sx * 1.0, -0.9, 11.6), (sx * (1.0 + 1.0 * math.cos(ang)), -0.95, 11.6 + 1.0 * math.sin(ang) * 0.6),
                   (sx * (1.0 + 2.0 * math.cos(ang)), -0.9, 11.6 + 1.6 * math.sin(ang) * 0.5)]
            lyre.append(kit.tube("frond", pts, 0.06 - 0.008 * k, 6, "gilt"))
    for k in range(5):
        lyre.append(kit.tube("lyre_string", [(-0.3 + 0.15 * k, -1.22, 11.0), (-0.3 + 0.15 * k, -1.22, 12.3)], 0.012, 4, "brass"))
    P.extend(lyre)
    # the great swag across the opening and the side curtains, gathered by gilt cords
    for i in range(5):
        x0 = -11.0 + 4.4 * i
        P.extend(drape("swag", x0, x0 + 4.4, 11.4, 1.0, y=-1.0, depth=0.5, folds=5, tassel=True))

    def curtain(sx):
        def fn(u, v):
            # u across, v down. Hangs straight, then gathered at a tie-back, then pools.
            x_in = sx * 10.6
            x_out = sx * 13.6
            gather = 1.0 - 0.55 * math.exp(-((v - 0.62) / 0.12) ** 2)
            x = x_out + (x_in - x_out) * u * gather
            z = 11.4 - v * 11.6
            y = -0.9 - 0.18 * math.sin(9 * TAU * u * 0.5) - 0.3 * max(0.0, v - 0.9) * 6.0 * u
            return (x, y, max(z, 0.02))
        return grid("curtain", 36, 24, fn, "velvet_drape")
    P.append(curtain(-1))
    P.append(curtain(1))
    for sx in (-1, 1):
        P.append(kit.tube("tieback", [(sx * 13.6, -0.95, 4.4), (sx * 12.6, -1.4, 4.3), (sx * 12.1, -1.3, 4.5)], 0.05, 6, "gilt"))
    kit.join("proscenium", P)


def organ_case():
    """An organ façade, 12 m wide: three towers of tin pipes in gilt casework with flats between,
    pipe mouths banded in gilt, a carved impost and crowning urns. Front toward -Y."""
    P = [kit.box("impost", (12.0, 1.2, 3.0), (0, 0.3, 1.5), mat="ebony", bevel=0.04)]
    for k in range(4):
        P.append(frame("impost_panel", 2.2, 1.8, (-4.5 + 3.0 * k, -0.32, 1.5), mat="gilt"))
    P.append(sweep("impost_cornice", [(u * 0.8, v * 0.8) for u, v in P_CORNICE], [(-6.0, -0.3, 3.0), (6.0, -0.3, 3.0)], "gilt"))
    towers = [(-4.5, 1.6, 8.5), (0.0, 2.0, 10.5), (4.5, 1.6, 8.5)]
    pipe_count = 0
    for cx, half, h in towers:
        # tower: a bowed rank of pipes, tallest in the middle
        n = 7
        for i in range(n):
            t = (i - (n - 1) / 2) / ((n - 1) / 2)
            x = cx + t * half * 0.9
            y = -0.45 - 0.35 * (1 - t * t)
            ph = h - 3.6 - 1.0 * abs(t)
            r = 0.17 - 0.03 * abs(t)
            P.append(kit.lathe("pipe", [(0.02, 3.3), (r * 0.9, 3.3 + ph * 0.18), (r, 3.3 + ph * 0.2), (r, 3.3 + ph), (r * 1.06, 3.3 + ph + 0.04), (r, 3.3 + ph + 0.06)],
                               segments=14, mat="pipe_tin", cap=False))
            P[-1].location = (x, y, 0)
            P.append(kit.box("mouth", (r * 1.1, 0.03, ph * 0.08), (x, y - r * 0.98, 3.3 + ph * 0.24), mat="gilt"))
            pipe_count += 1
        # tower casework: side posts, a canopy cornice and an urn
        for sx in (-1, 1):
            P.append(kit.box("post", (0.3, 1.1, h - 3.0), (cx + sx * (half + 0.1), 0.0, 3.0 + (h - 3.0) / 2), mat="ebony", bevel=0.03))
            P.append(kit.box("post_gilt", (0.34, 0.06, h - 3.2), (cx + sx * (half + 0.1), -0.56, 3.0 + (h - 3.0) / 2), mat="gilt"))
        cap = arc(cx, -0.2, half + 0.25, math.pi, 2 * math.pi, 12, sy=0.45)
        P.append(sweep("canopy", [(u * 0.9, v * 0.9) for u, v in P_CORNICE], [(x, y, h) for x, y, _ in cap], "gilt"))
        P.append(kit.lathe("urn", [(0.0, 0.0), (0.25, 0.05), (0.32, 0.25), (0.2, 0.5), (0.14, 0.62), (0.22, 0.75), (0.0, 0.95)], segments=16, mat="gilt"))
        P[-1].location = (cx, -0.3, h + 0.5)
        # pierced cresting (gilt scrollwork) above the pipe mouths
        for i in range(6):
            t = (i + 0.5) / 6 * 2 - 1
            P.append(kit.torus("scroll", 0.2, 0.035, seg=14, rseg=5, mat="gilt", loc=(cx + t * half, -0.9, h - 0.5), rot=(math.pi / 2, 0, 0)))
    # flats between the towers: straight ranks of smaller pipes
    for cx in (-2.25, 2.25):
        for i in range(6):
            x = cx - 0.75 + 0.3 * i
            ph = 3.2 + 0.25 * abs(i - 2.5)
            P.append(kit.lathe("flat_pipe", [(0.02, 3.3), (0.1, 3.3 + 0.5), (0.11, 3.3 + 0.55), (0.11, 3.3 + ph), (0.0, 3.3 + ph)], segments=12, mat="pipe_tin"))
            P[-1].location = (x, -0.25, 0)
        P.append(sweep("flat_cornice", [(u * 0.5, v * 0.5) for u, v in P_CORNICE], [(cx - 1.0, -0.25, 7.0), (cx + 1.0, -0.25, 7.0)], "gilt"))
    P.append(kit.box("case_back", (12.0, 0.2, 9.0), (0, 0.5, 7.5), mat="ebony"))
    kit.join("organ_case", P)


def ceiling():
    """The auditorium ceiling, 30 x 46 m: a coffered gilt field with a round fresco well (its own
    material, UV-mapped 0..1 across the disc) at the centre."""
    W, D = 30.0, 46.0
    P = []
    R = 9.0
    # fresco disc, planar UVs across the disc, facing down
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((R * math.cos(TAU * i / 64), R * math.sin(TAU * i / 64), 0)) for i in range(64)]
    for i in range(64):
        f = bm.faces.new((c, ring[(i + 1) % 64], ring[i]))
        for lp in f.loops:
            lp[uv].uv = (0.5 + lp.vert.co.x / (2 * R), 0.5 + lp.vert.co.y / (2 * R))
    P.append(kit._obj("ceiling_fresco", bm, "ceiling_fresco", None))
    # the well's moulded rim, stepped up
    for k, (rr, zz) in enumerate([(R, 0.0), (R + 0.6, -0.5), (R + 1.2, -1.0)]):
        P.append(kit.torus("well_ring", rr, 0.18 + 0.06 * k, seg=64, rseg=8, mat="gilt", loc=(0, 0, zz)))
    P.append(kit.lathe("well_drum", [(R + 0.05, 0.0), (R + 0.05, -0.02), (R + 1.2, -1.0), (R + 1.25, -1.02)], segments=64, mat="damask_ox", cap=False))
    # coffers: a grid of sunk panels around the well
    for ix in range(-3, 4):
        for iy in range(-5, 6):
            x, y = ix * 4.2, iy * 4.2
            if math.hypot(x, y) < R + 2.4 or abs(x) > W / 2 - 1 or abs(y) > D / 2 - 1:
                continue
            P.append(kit.box("coffer", (3.2, 3.2, 0.25), (x, y, -0.9), mat="damask_ox"))
            ro = kit.lathe("coffer_rose", [(0.0, 0.0), (0.4, 0.0), (0.42, -0.05), (0.25, -0.12), (0.0, -0.16)], segments=16, mat="gilt")
            ro.location = (x, y, -1.03)
            P.append(ro)
    for k in range(-4, 4):
        x = k * 4.2 + 2.1
        P.append(kit.box("rib", (0.6, D, 0.5), (x, 0, -1.15), mat="gilt", bevel=0.04))
    for k in range(-6, 6):
        y = k * 4.2 + 2.1
        P.append(kit.box("rib", (W, 0.6, 0.5), (0, y, -1.15), mat="gilt", bevel=0.04))
    P.append(kit.box("deck", (W, D, 0.3), (0, 0, -0.65), mat="damask_ox"))
    kit.join("ceiling", P)


# --- props ----------------------------------------------------------------------------------------

def seat():
    """An opera fauteuil (stalls armchair), about 0.6 wide x 0.6 deep, seat 0.42, back top about 1.0.
    Origin on the floor between the legs, front toward -Y. Four gilt cabriole legs on scroll feet, a bowed
    moulded seat rail with a carved shell, a domed velvet cushion over a velvet underside panel, a
    10-degree-leaning oval back of buttoned velvet in a closed gilt moulding with a rear skin, and scrolled
    arms on curved supports. Every part is closed so it reads from below (chairs hang upside down)."""
    Matrix = kit.Matrix
    BACK = Matrix.Translation((0.0, 0.19, 0.36)) @ Matrix.Rotation(math.radians(-10), 4, "X")
    P = []

    def curve_tube(name, pts, radii, sides, mat):
        # tube with parallel-transport frames: no twist at vertical or reversing runs; capped ends
        V = [Vector(p) for p in pts]
        n = len(V)
        bm = bmesh.new()
        rings = []
        x = None
        for i, p in enumerate(V):
            d = (V[min(i + 1, n - 1)] - V[max(i - 1, 0)]).normalized()
            if x is None:
                up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
                x = d.cross(up).normalized()
            else:
                x = (x - d * x.dot(d)).normalized()
            y = d.cross(x)
            rings.append([bm.verts.new(p + (x * math.cos(TAU * k / sides) + y * math.sin(TAU * k / sides)) * radii[i]) for k in range(sides)])
        for i in range(n - 1):
            for k in range(sides):
                bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % sides], rings[i][(k + 1) % sides]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return kit._obj(name, bm, mat, 60.0)

    def at_back(ob, loc=(0.0, 0.0, 0.0), rot=0.0):
        # back parts are built in back-local space (origin at the rear rail pivot) and leaned here
        ob.matrix_world = BACK @ Matrix.Translation(loc) @ Matrix.Rotation(rot, 4, "X")
        return ob

    # legs: the knee bows out, the ankle pulls in, a small torus scroll foot
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * 0.225, sy * 0.16
            pts = [(cx, cy, 0.31), (cx + sx * 0.01, cy + sy * 0.01, 0.26), (cx + sx * 0.03, cy + sy * 0.03, 0.19),
                   (cx + sx * 0.005, cy + sy * 0.005, 0.13), (cx - sx * 0.012, cy - sy * 0.012, 0.08),
                   (cx - sx * 0.008, cy - sy * 0.008, 0.035), (cx, cy, 0.02)]
            P.append(curve_tube("leg", pts, [0.024, 0.024, 0.028, 0.021, 0.016, 0.017, 0.02], 8, "gilt"))
            P.append(kit.torus("leg_scroll", 0.02, 0.009, seg=12, rseg=5, mat="gilt", loc=(cx, cy, 0.009)))

    # seat rail: a bowed front, a closed moulded loop
    ts = [-1 + 2 * i / 8 for i in range(9)]
    # sides sit at x +-0.2 (not 0.25): sharp corners miter-scale the profile outward, so the tail must stay narrow
    rail = [(0.2 * t, -0.2 - 0.02 * (1 - t * t), 0.30) for t in ts]
    rail += [(0.2, 0.0, 0.30), (0.2, 0.19, 0.30), (0.0, 0.19, 0.30), (-0.2, 0.19, 0.30), (-0.2, 0.0, 0.30)]
    P.append(sweep("seat_rail", [(-0.03, 0.0), (0.03, 0.0), (0.045, 0.02), (0.035, 0.045), (0.0, 0.06), (-0.035, 0.045), (-0.045, 0.02)],
                   rail, "gilt", closed_path=True))

    # carved shell at the front centre, fanning down from the rail top
    def shell(u, v):
        ph = (u - 0.5) * 1.2
        r = 0.065 * v
        return (r * math.sin(ph), -0.25 - 0.025 * v - 0.006 * v * math.cos(18 * ph), 0.36 - r * math.cos(ph))
    P.append(grid("seat_shell", 12, 4, shell, "gilt"))

    # velvet underside panel closing the seat from below
    P.append(kit.box("seat_underside", (0.44, 0.32, 0.012), (0.0, -0.01, 0.352), mat="velvet"))

    # domed cushion: a sheet whose edges puff down onto the rail, crown at 0.42
    def cushion(u, v):
        sx, sy = -1 + 2 * u, -1 + 2 * v
        f = max(0.0, 1 - sx ** 6) * max(0.0, 1 - sy ** 6)
        return (0.225 * sx, -0.01 + 0.16 * sy, 0.36 + 0.05 * math.sqrt(f) + 0.01 * f)
    P.append(grid("seat_cushion", 24, 16, cushion, "velvet"))

    # back: an oval (0.5 x 0.54) with its crest, leaning 10 degrees; local origin is the rear pivot
    NO = 28
    a, b, zc = 0.25, 0.27, 0.32
    oval = [(a * math.cos(TAU * i / NO), 0.0, zc + b * math.sin(TAU * i / NO)) for i in range(NO)]

    def panel(u, v):
        th = TAU * u
        return (v * a * math.cos(th), -0.035 * (1 - v * v), zc + v * b * math.sin(th))

    def skin(u, v):
        th = TAU * u
        return (v * a * math.cos(th), 0.006, zc + v * b * math.sin(th))
    P.append(at_back(grid("back_panel", 28, 5, panel, "velvet")))
    P.append(at_back(grid("back_skin", 28, 5, skin, "velvet")))
    P.append(at_back(sweep("back_frame", [(-0.03, 0.0), (-0.032, 0.012), (-0.02, 0.03), (0.0, 0.036), (0.02, 0.03),
                                          (0.032, 0.012), (0.03, 0.0), (0.02, -0.01), (-0.02, -0.01)],
                           oval, "gilt", closed_path=True, axis=(0, -1, 0))))
    crest = [(-0.13, -0.012, 0.55), (-0.09, -0.012, 0.61), (-0.03, -0.012, 0.64), (0.03, -0.012, 0.64), (0.09, -0.012, 0.61), (0.13, -0.012, 0.55)]
    P.append(at_back(kit.tube("back_crest", crest, 0.012, 6, "gilt")))
    for sx in (-1, 1):
        P.append(at_back(kit.torus("crest_scroll", 0.022, 0.008, seg=12, rseg=5, mat="gilt", loc=(sx * 0.15, -0.012, 0.6), rot=(math.pi / 2, 0, 0))))
    # seven buttons: one centre, six round it, pressed into the velvet
    for bx, bz in [(0.0, zc)] + [(0.5 * a * math.cos(TAU * k / 6), zc + 0.5 * b * math.sin(TAU * k / 6)) for k in range(6)]:
        s2 = min(1.0, (bx / a) ** 2 + ((bz - zc) / b) ** 2)
        by = -0.035 * (1 - s2) - 0.002
        btn = kit.lathe("button", [(0.0, 0.0), (0.011, 0.0), (0.012, 0.004), (0.008, 0.009), (0.0, 0.011)], segments=10, mat="velvet")
        P.append(at_back(btn, (bx, by, bz), math.pi / 2))
    for sx in (-1, 1):
        P.append(at_back(kit.tube("back_post", [(sx * 0.15, 0.0, -0.07), (sx * 0.15, 0.0, 0.1)], 0.014, 6, "gilt")))

    # arms: a curved support from the rail, then the arm running forward into a volute
    for sx in (-1, 1):
        P.append(curve_tube("arm_support", [(sx * 0.25, -0.02, 0.33), (sx * 0.29, -0.05, 0.42), (sx * 0.28, -0.08, 0.53),
                                            (sx * 0.27, -0.10, 0.635)], [0.015, 0.015, 0.013, 0.013], 8, "gilt"))
        arm = [(sx * 0.27, 0.14, 0.64), (sx * 0.27, 0.0, 0.66), (sx * 0.27, -0.14, 0.66), (sx * 0.27, -0.22, 0.65), (sx * 0.27, -0.26, 0.64)]
        for k in range(1, 14):
            ang = math.pi / 2 + 0.55 * k
            r = 0.05 - 0.0015 * k
            arm.append((sx * 0.27, -0.26 + r * math.cos(ang), 0.59 + r * math.sin(ang)))
        P.append(curve_tube("arm", arm, [0.016] * len(arm), 8, "gilt"))
        ts = [-1 + i / 3 for i in range(7)]
        pad = kit.lathe("arm_pad", [(math.sqrt(1 - t * t), t) for t in ts], segments=14, mat="velvet")
        pad.location = (sx * 0.27, -0.04, 0.665)
        pad.scale = (0.034, 0.11, 0.014)
        P.append(pad)
    kit.join("seat", P)


def figure():
    """A drowned listener, seated: shrouded torso, lap and knees, hands folded, hair drifting upward.
    The body only; the head is figure_head (pivots in the wing). Origin at the seat base."""
    body = kit.lathe("torso", [(0.0, 0.48), (0.2, 0.5), (0.23, 0.7), (0.21, 0.95), (0.24, 1.15), (0.2, 1.28), (0.09, 1.36), (0.06, 1.42), (0.0, 1.43)], segments=18, mat="pale")
    body.scale = (1.0, 0.75, 1.0)
    body.location = (0, 0.12, 0)
    P = [body]
    for sx in (-1, 1):
        P.append(kit.tube("thigh", [(sx * 0.11, 0.1, 0.52), (sx * 0.12, -0.15, 0.54), (sx * 0.12, -0.38, 0.52)], 0.09, 10, "pale"))
        P.append(kit.tube("shin", [(sx * 0.12, -0.4, 0.5), (sx * 0.12, -0.44, 0.25), (sx * 0.12, -0.45, 0.05)], 0.065, 10, "pale"))
        P.append(kit.tube("arm", [(sx * 0.24, 0.08, 1.24), (sx * 0.27, 0.02, 0.98), (sx * 0.2, -0.16, 0.8), (sx * 0.06, -0.3, 0.68)], 0.055, 8, "pale"))
    # shroud: a drape over the lap falling past the knees
    def lap(u, v):
        x = -0.3 + 0.6 * u
        y = 0.05 - 0.5 * min(v * 1.6, 1.0)
        z = 0.62 - max(0.0, v * 1.6 - 1.0) * 0.9 + 0.03 * math.sin(7 * math.pi * u)
        return (x, y + 0.02 * math.sin(5 * math.pi * u), z)
    P.append(grid("shroud", 14, 10, lap, "pale_cloth"))
    for i in range(5):
        a = -0.5 + 0.25 * i
        pts = [(0.08 * math.sin(a), 0.1, 1.55)]
        for k in range(1, 6):
            t = k / 5
            pts.append((0.08 * math.sin(a) + 0.18 * t * math.sin(a * 2 + t), 0.12 + 0.12 * t, 1.6 + 0.9 * t))
        P.append(kit.tube("hair", pts, 0.025 * (1.0 - 0.1 * i % 2), 5, "pale_hair"))
    kit.join("figure", P)


def figure_head():
    h = kit.lathe("head", [(0.0, -0.13), (0.07, -0.12), (0.1, -0.06), (0.11, 0.02), (0.1, 0.08), (0.06, 0.13), (0.0, 0.14)], segments=16, mat="pale")
    h.scale = (0.9, 1.0, 1.05)
    nose = kit.box("nose", (0.03, 0.05, 0.05), (0, -0.11, 0.0), mat="pale", bevel=0.012)
    wig = kit.lathe("wig", [(0.0, 0.02), (0.11, 0.03), (0.13, 0.08), (0.11, 0.13), (0.05, 0.17), (0.0, 0.17)], segments=16, mat="pale_hair")
    wig.location = (0, 0.02, 0)
    curls = []
    for sx in (-1, 1):
        for k in range(3):
            curls.append(kit.torus("curl", 0.035, 0.018, seg=10, rseg=5, mat="pale_hair", loc=(sx * 0.12, 0.02, 0.06 - 0.06 * k), rot=(0, math.pi / 2, 0)))
    kit.join("figure_head", [h, nose, wig] + curls)


def horn():
    """The brass horn on a caryatid plinth (2.9 m): a moulded plinth with a gilt lyre panel, a draped
    bronze figure, raised arms holding a long trumpet whose bell flares toward the hall."""
    P = [kit.lathe("plinth", [(0.7, 0.0), (0.7, 0.14), (0.62, 0.2), (0.6, 0.3), (0.5, 0.36), (0.48, 1.1), (0.54, 1.16), (0.6, 1.24), (0.62, 1.34), (0.0, 1.34)], segments=8, mat="marble_teal", smooth_angle=20)]
    P[-1].rotation_euler = (0, 0, math.pi / 8)
    for k in range(4):
        a = TAU * k / 4
        pn = frame("plinth_panel", 0.5, 0.56, (0, 0, 0), mat="gilt", prof=[(0.0, 0.0), (0.0, 0.02), (0.02, 0.03), (0.03, 0.0)])
        pn.location = (0.52 * math.sin(a), -0.52 * math.cos(a), 0.73)
        pn.rotation_euler = (0, 0, a)
        P.append(pn)

    def gown(z, th):
        t = (z - 1.34) / 1.3
        base = 0.34 - 0.12 * t + 0.05 * math.sin(t * math.pi)
        return base + 0.025 * math.sin(9 * th + 2 * z) * (1.0 - t)
    P.append(lathe_fn("gown", [1.34 + 1.3 * k / 14 for k in range(15)], gown, 36, "bronze"))
    P.append(kit.lathe("bodice", [(0.2, 2.6), (0.22, 2.8), (0.2, 2.95), (0.12, 3.05), (0.06, 3.1), (0.06, 3.16)], segments=18, mat="bronze"))
    hd = kit.lathe("head", [(0.0, 0.0), (0.08, 0.02), (0.11, 0.1), (0.1, 0.19), (0.05, 0.25), (0.0, 0.26)], segments=14, mat="bronze")
    hd.location = (0, 0, 3.14)
    P.append(hd)
    P.append(kit.lathe("bun", [(0.0, 0.0), (0.07, 0.02), (0.08, 0.07), (0.0, 0.1)], segments=10, mat="bronze"))
    P[-1].location = (0, 0.08, 3.34)
    for sx in (-1, 1):
        P.append(kit.tube("arm", [(sx * 0.18, 0.0, 2.95), (sx * 0.28, -0.12, 3.1), (sx * 0.16, -0.32, 3.28), (sx * 0.04, -0.42, 3.34)], 0.045, 8, "bronze"))
    # trumpet: a long tube from the lips to a flared bell
    P.append(kit.tube("leadpipe", [(0, -0.12, 3.26), (0, -0.4, 3.36), (0, -0.9, 3.55), (0, -1.3, 3.7)], 0.035, 10, "brass"))
    bell = kit.lathe("bell", [(0.035, 0.0), (0.05, 0.25), (0.09, 0.45), (0.18, 0.6), (0.32, 0.68), (0.36, 0.7), (0.34, 0.7)], segments=24, mat="brass", cap=False)
    bell.rotation_euler = (math.radians(70), 0, 0)
    bell.location = (0, -1.28, 3.69)
    P.append(bell)
    P.append(kit.torus("bell_rim", 0.355, 0.02, seg=24, rseg=6, mat="gilt", loc=(0, -1.28 - 0.7 * math.sin(math.radians(70)), 3.69 + 0.7 * math.cos(math.radians(70))), rot=(math.radians(70), 0, 0)))
    for k in range(2):
        P.append(kit.torus("ferrule", 0.045, 0.012, seg=10, rseg=4, mat="gilt", loc=(0, -0.55 - 0.4 * k, 3.42 + 0.14 * k), rot=(math.radians(70), 0, 0)))
    kit.join("horn", P)


def rect_loop(hx, hy, z):
    """Closed CCW rectangle loop (half-sizes hx, hy) at height z: a sweep_closed path."""
    return [(-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]


def ext_box(name, ext, mat, bevel=0.0):
    """A box from per-axis extents {"x": (a, b), "y": (a, b), "z": (a, b)}, in any order."""
    lo = [min(ext[a]) for a in "xyz"]
    hi = [max(ext[a]) for a in "xyz"]
    return kit.box(name, [h - l for l, h in zip(lo, hi)], [(h + l) / 2 for l, h in zip(lo, hi)], mat=mat, bevel=bevel)


def prism_x(name, prof, x0, x1, mat):
    """A closed (y, z) profile extruded along X from x0 to x1."""
    import bmesh
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    n = len(prof)
    for j in range(n):
        bm.faces.new((a[j], b[j], b[(j + 1) % n], a[(j + 1) % n]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit._obj(name, bm, mat, 40.0)


def fielded_panels(P, axis, sign, centres, w, z0, z1, D, mat):
    """Raised fields on one body face: axis 'y' (front/back, centres along x) or 'x' (ends, centres along y).
    Each field stands 0.012 proud of the face at depth D and is framed by a gilt bead 0.02 proud."""
    along = "x" if axis == "y" else "y"

    def at(a0, a1, d0, d1, zl, zh):
        return {axis: (sign * d0, sign * d1), along: (a0, a1), "z": (zl, zh)}

    for s in centres:
        a0, a1 = s - w / 2, s + w / 2
        P.append(ext_box("field", at(a0, a1, D - 0.02, D + 0.012, z0, z1), mat, 0.004))
        P.append(ext_box("bead", at(a0 - 0.008, a1 + 0.008, D - 0.004, D + 0.02, z1 - 0.008, z1 + 0.008), "gilt", 0.003))
        P.append(ext_box("bead", at(a0 - 0.008, a1 + 0.008, D - 0.004, D + 0.02, z0 - 0.008, z0 + 0.008), "gilt", 0.003))
        P.append(ext_box("bead", at(a0 - 0.008, a0 + 0.008, D - 0.004, D + 0.02, z0 - 0.008, z1 + 0.008), "gilt", 0.003))
        P.append(ext_box("bead", at(a1 - 0.008, a1 + 0.008, D - 0.004, D + 0.02, z0 - 0.008, z1 + 0.008), "gilt", 0.003))


PIPE_PLINTH = [(-0.05, 0.0), (0.02, 0.0), (0.03, 0.008), (0.03, 0.05), (0.025, 0.06), (0.03, 0.075), (0.02, 0.09), (-0.05, 0.09)]
PIPE_FILLET = [(-0.02, 0.0), (0.01, 0.0), (0.014, 0.004), (0.01, 0.008), (-0.02, 0.008)]
PIPE_CORNICE = [(-0.02, 0.0), (0.04, 0.0), (0.04, 0.012), (0.025, 0.02), (0.012, 0.035), (0.02, 0.05), (0.0, 0.07), (-0.02, 0.07)]


def pipes():
    """Three speaking pipes (C, E, G) on a wind-chest: conical feet, gilt-banded mouths with upper lips,
    tin bodies, and a panelled ebony wind-chest: moulded toe, raised teal and damask fields in gilt beads,
    gilt corner pilasters and capitals, an ogee cornice, three brass pallet knobs on the front."""
    P = [kit.box("chest", (2.1, 0.7, 0.55), (0, 0, 0.275), mat="ebony", bevel=0.02),
         kit.sweep_closed("plinth", PIPE_PLINTH, rect_loop(1.05, 0.35, 0.0), mat="ebony"),
         kit.sweep_closed("plinth_fillet", PIPE_FILLET, rect_loop(1.05, 0.35, 0.09), mat="gilt"),
         kit.sweep_closed("chest_cornice", PIPE_CORNICE, rect_loop(1.05, 0.35, 0.48), mat="gilt")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(ext_box("pilaster", {"x": (sx * 0.93, sx * 1.065), "y": (sy * 0.33, sy * 0.365), "z": (0.09, 0.48)}, "gilt", 0.006))
            P.append(ext_box("capital", {"x": (sx * 0.92, sx * 1.075), "y": (sy * 0.32, sy * 0.375), "z": (0.44, 0.48)}, "gilt", 0.008))
            P.append(ext_box("capital", {"x": (sx * 0.92, sx * 1.075), "y": (sy * 0.32, sy * 0.375), "z": (0.09, 0.13)}, "gilt", 0.008))
    fielded_panels(P, "y", -1, (-0.65, 0.0, 0.65), 0.46, 0.17, 0.42, 0.35, "marble_teal")
    fielded_panels(P, "y", 1, (-0.65, 0.0, 0.65), 0.46, 0.17, 0.42, 0.35, "marble_teal")
    for sx in (-1, 1):
        fielded_panels(P, "x", sx, (-0.17, 0.17), 0.22, 0.17, 0.42, 1.05, "damask_ox")
    for x in (-0.65, 0.0, 0.65):
        k = kit.lathe("pallet", [(0.0, 0.0), (0.02, 0.0), (0.022, 0.006), (0.016, 0.014), (0.0, 0.018)], segments=14, mat="brass")
        k.rotation_euler = (math.pi / 2, 0, 0)
        k.location = (x, -0.37, 0.295)
        P.append(k)
    for x, h, r in [(-0.62, 3.6, 0.15), (0.0, 3.0, 0.135), (0.62, 2.45, 0.12)]:
        foot = kit.lathe("foot", [(0.03, 0.55), (r * 0.9, 0.55 + 0.45), (r, 1.0)], segments=16, mat="pipe_tin", cap=False)
        body = kit.lathe("body", [(r, 1.0), (r, 1.0 + h), (r * 1.08, 1.04 + h), (r, 1.08 + h)], segments=20, mat="pipe_tin", cap=False)
        mouth = kit.box("mouth", (r * 1.2, 0.02, 0.16), (0, -r * 0.98, 1.12), mat="gilt", bevel=0.005)
        lip = kit.box("lip", (r * 1.05, 0.04, 0.03), (0, -r * 1.0, 1.21), mat="gilt", bevel=0.008)
        band = kit.torus("band", r * 1.01, 0.012, seg=20, rseg=4, mat="gilt", loc=(0, 0, 1.0 + h * 0.7))
        for o in (foot, body, mouth, lip, band):
            o.location = (o.location.x + x, o.location.y, o.location.z)
        P += [foot, body, mouth, lip, band]
    kit.join("pipes", P)


def glass_bowls():
    """A glass armonica table: a gilt tripod with scrolled legs carrying a round tray, and five tuned
    crystal bowls of falling size standing open on it."""
    P = []
    for k in range(3):
        a = TAU * k / 3
        P.append(kit.tube("tripod", [(0.5 * math.cos(a), 0.5 * math.sin(a), 0.0), (0.42 * math.cos(a), 0.42 * math.sin(a), 0.25), (0.2 * math.cos(a), 0.2 * math.sin(a), 0.55), (0.12 * math.cos(a), 0.12 * math.sin(a), 0.85)], 0.032, 6, "gilt"))
        P.append(kit.torus("scroll", 0.07, 0.022, seg=12, rseg=5, mat="gilt", loc=(0.5 * math.cos(a), 0.5 * math.sin(a), 0.07), rot=(math.pi / 2, 0, a + math.pi / 2)))
    P.append(kit.lathe("stem", [(0.1, 0.8), (0.13, 0.86), (0.07, 0.95), (0.09, 1.02), (0.06, 1.06)], segments=14, mat="gilt"))
    P.append(kit.lathe("tray", [(0.0, 1.04), (0.78, 1.04), (0.82, 1.08), (0.8, 1.12), (0.0, 1.1)], segments=40, mat="ebony"))
    P.append(kit.torus("tray_rim", 0.81, 0.025, seg=48, rseg=6, mat="gilt", loc=(0, 0, 1.11)))
    for i, r in enumerate([0.24, 0.21, 0.18, 0.15, 0.13]):
        a = TAU * i / 5 + 0.3
        rr = 0.5 if i else 0.0
        x, y = 0.5 * math.cos(a), 0.5 * math.sin(a)
        if i == 0:
            x, y = 0.0, 0.0
            r = 0.27
        prof = [(0.0, 0.0), (r * 0.45, 0.005), (r * 0.8, 0.06), (r, r * 0.75), (r * 1.02, r * 0.8), (r * 0.98, r * 0.8), (r * 0.95, r * 0.75), (r * 0.76, 0.07), (r * 0.42, 0.02), (0.0, 0.015)]
        b = kit.lathe("bowl", prof, segments=32, mat="crystal", cap=False, smooth_angle=70)
        b.location = (x, y, 1.12)
        P.append(b)
        P.append(kit.torus("rim", r * 1.0, 0.005, seg=32, rseg=4, mat="gilt", loc=(x, y, 1.12 + r * 0.8)))
    kit.join("glass_bowls", P)


FORK_FLOOR = [(-0.1, 0.0), (0.02, 0.0), (0.05, 0.015), (0.045, 0.035), (0.025, 0.05), (-0.1, 0.05)]
FORK_CYMA = [(-0.1, 0.0), (0.02, 0.0), (0.05, 0.008), (0.04, 0.022), (0.02, 0.034), (0.035, 0.05), (0.01, 0.065), (-0.1, 0.065)]
FORK_CAP = [(-0.1, 0.0), (0.12, 0.0), (0.14, 0.02), (0.12, 0.05), (0.08, 0.08), (0.02, 0.1), (-0.02, 0.12), (-0.1, 0.12)]


def sunk_die(name, c, k, z0, z1, mat, rim=0.1, depth=0.02):
    """An octagonal die (half-size c, vertical corners chamfered by k). Each side carries a sunk fielded
    panel: the rim is inset by rim and the field pushed back by depth, with a gilt bead round each field."""
    import bmesh
    from mathutils import Vector
    bm = bmesh.new()
    ring = [(-c + k, -c), (c - k, -c), (c, -c + k), (c, c - k), (c - k, c), (-c + k, c), (-c, c - k), (-c, -c + k)]
    bot = [bm.verts.new((x, y, z0)) for x, y in ring]
    top = [bm.verts.new((x, y, z1)) for x, y in ring]
    n = len(ring)
    for i in range(n):
        bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    out = []
    A = c - k - rim
    zl, zh = z0 + rim, z1 - rim
    for axis, sign in (("x", 1), ("x", -1), ("y", 1), ("y", -1)):
        along = "y" if axis == "x" else "x"
        for a0, a1, b0, b1 in ((-A - 0.012, A + 0.012, zh - 0.012, zh + 0.012), (-A - 0.012, A + 0.012, zl - 0.012, zl + 0.012),
                               (-A - 0.012, -A + 0.012, zl - 0.012, zh + 0.012), (A - 0.012, A + 0.012, zl - 0.012, zh + 0.012)):
            out.append(ext_box("die_bead", {axis: (sign * (c - depth), sign * (c + 0.012)), along: (a0, a1), "z": (b0, b1)}, "gilt", 0.005))
    out.insert(0, kit._obj(name, bm, mat, 40.0))
    return out


def fork_statue():
    """The tuning fork: a 3.6 m verdigris bronze fork on a moulded marble pedestal (a two-step base with
    torus and cyma mouldings, a chamfered die with sunk fielded panels, a cyma cap). The gilt A sits proud
    of the front panel."""
    P = [kit.box("base_core", (1.4, 1.4, 0.24), (0, 0, 0.12), mat="marble_teal", bevel=0.01),
         kit.sweep_closed("base_floor", FORK_FLOOR, rect_loop(0.7, 0.7, 0.0), mat="marble_teal"),
         kit.sweep_closed("base_cyma", FORK_CYMA, rect_loop(0.7, 0.7, 0.24), mat="marble_teal"),
         kit.box("step_core", (1.1, 1.1, 0.16), (0, 0, 0.32), mat="marble_teal", bevel=0.01),
         kit.sweep_closed("step_cyma", FORK_CYMA, rect_loop(0.55, 0.55, 0.40), mat="marble_teal")]
    P += sunk_die("die", 0.45, 0.06, 0.40, 1.40, "marble_ivory")
    P.append(kit.sweep_closed("cap_cyma", FORK_CAP, rect_loop(0.45, 0.45, 1.40), mat="marble_teal"))
    P.append(kit.box("cap_core", (0.72, 0.72, 0.12), (0, 0, 1.46), mat="marble_teal", bevel=0.01))
    P.append(kit.lathe("ball", [(0.0, 0.0), (0.15, 0.03), (0.22, 0.18), (0.15, 0.33), (0.0, 0.36)], segments=20, mat="gilt"))
    P[-1].location = (0, 0, 1.52)
    P.append(kit.lathe("stem", [(0.06, 0.0), (0.06, 0.5), (0.09, 0.56), (0.07, 0.62)], segments=12, mat="verdigris"))
    P[-1].location = (0, 0, 1.85)
    P.append(sweep("fork", [(-0.06, -0.05), (0.06, -0.05), (0.07, -0.04), (0.07, 0.04), (0.06, 0.05), (-0.06, 0.05), (-0.07, 0.04), (-0.07, -0.04)],
                   [(-0.32, 0, 4.7), (-0.32, 0, 2.9)] + [(0.32 * math.cos(math.pi + math.pi * k / 10), 0, 2.9 + 0.32 * math.sin(math.pi + math.pi * k / 10)) for k in range(1, 10)] + [(0.32, 0, 2.9), (0.32, 0, 4.7)],
                   "verdigris", smooth=30.0))
    P.append(kit.box("fork_neck", (0.16, 0.12, 0.42), (0, 0, 2.5), mat="verdigris", bevel=0.03))
    P.append(kit.box("a_l", (0.05, 0.03, 0.42), (-0.07, -0.44, 0.9), mat="gilt"))
    P[-1].rotation_euler = (0, math.radians(-17), 0)
    P.append(kit.box("a_r", (0.05, 0.03, 0.42), (0.07, -0.44, 0.9), mat="gilt"))
    P[-1].rotation_euler = (0, math.radians(17), 0)
    P.append(kit.box("a_bar", (0.14, 0.03, 0.04), (0, -0.44, 0.85), mat="gilt"))
    kit.join("fork_statue", P)


def chandelier():
    """The great chandelier (origin at the hanging point): a gilt corona, three tiers of scrolled arms
    with candle cups and flames, swags of crystal chains, a cascade of drops and a pendant ball."""
    P = [kit.lathe("stem", [(0.08, 0.0), (0.08, -1.0), (0.14, -1.05), (0.08, -1.1), (0.08, -2.6)], segments=10, mat="gilt")]
    P.append(kit.lathe("corona", [(0.0, -0.9), (0.6, -1.0), (0.9, -1.25), (0.75, -1.45), (0.25, -1.55), (0.0, -1.6)], segments=24, mat="gilt"))
    P.append(kit.lathe("body", [(0.0, -2.4), (0.5, -2.6), (0.7, -3.1), (0.55, -3.6), (0.8, -4.0), (0.6, -4.3), (0.2, -4.7), (0.12, -5.1), (0.25, -5.3), (0.0, -5.5)], segments=24, mat="gilt"))
    P.append(kit.lathe("pendant", [(0.0, 0.0), (0.18, -0.1), (0.2, -0.25), (0.1, -0.42), (0.0, -0.5)], segments=12, mat="crystal"))
    P[-1].location = (0, 0, -5.5)
    flames = []
    drops = []
    for z, R, n in [(-2.7, 1.7, 8), (-3.6, 2.7, 12), (-4.4, 3.5, 16)]:
        P.append(kit.torus("ring", R, 0.06, seg=48, rseg=8, mat="gilt", loc=(0, 0, z)))
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            arm = [(c * 0.3, s * 0.3, z + 0.25), (c * R * 0.5, s * R * 0.5, z - 0.25), (c * R * 0.85, s * R * 0.85, z + 0.05), (c * R, s * R, z + 0.25)]
            P.append(kit.tube("arm", arm, 0.035, 6, "gilt"))
            cup = kit.lathe("cup", [(0.0, 0.0), (0.08, 0.02), (0.1, 0.06), (0.05, 0.08)], segments=10, mat="gilt")
            cup.location = (c * R, s * R, z + 0.25)
            P.append(cup)
            cdl = kit.lathe("candle", [(0.025, 0.0), (0.025, 0.2), (0.0, 0.21)], segments=8, mat="wax")
            cdl.location = (c * R, s * R, z + 0.32)
            P.append(cdl)
            fl = kit.lathe("flame", [(0.0, 0.0), (0.02, 0.02), (0.025, 0.05), (0.0, 0.1)], segments=6, mat="flame")
            fl.location = (c * R, s * R, z + 0.53)
            flames.append(fl)
            # crystal swag to the next arm: a chain of beads hanging in a catenary
            a2 = TAU * (i + 1) / n
            for k in range(1, 6):
                t = k / 6
                aa = a + (a2 - a) * t
                d = kit.lathe("bead", [(0.0, 0.0), (0.04, -0.03), (0.0, -0.06)], segments=6, mat="crystal", smooth_angle=None)
                d.location = (math.cos(aa) * R * 0.98, math.sin(aa) * R * 0.98, z + 0.2 - 0.35 * math.sin(math.pi * t))
                drops.append(d)
            dd = kit.lathe("drop", [(0.0, 0.0), (0.07, -0.1), (0.1, -0.28), (0.07, -0.44), (0.0, -0.55)], segments=6, mat="crystal", smooth_angle=None)
            dd.location = (c * R * 0.92, s * R * 0.92, z - 0.15)
            drops.append(dd)
    # the cascade: long strands from the lowest ring down to the pendant
    for i in range(24):
        a = TAU * i / 24
        for k in range(6):
            t = k / 6
            rr = 3.2 * (1 - t) + 0.35 * t
            d = kit.lathe("cascade", [(0.0, 0.0), (0.05, -0.05), (0.06, -0.14), (0.0, -0.22)], segments=6, mat="crystal", smooth_angle=None)
            d.location = (math.cos(a) * rr, math.sin(a) * rr, -4.6 - 1.0 * math.sin(math.pi * 0.5 * t) - 0.1 * k)
            drops.append(d)
    kit.join("chandelier", P)
    kit.join("chandelier_glass", drops)
    kit.join("chandelier_flames", flames)


def _stair_panel(x, sx, ya, yb, zb, ta, tb):
    """Raised marble panel on a string face at x (sx = outward side): a quad in (y, z) with bottom zb,
    top ta at ya and tb at yb, standing 0.035 proud along sx. Outward edges bevelled."""
    bm = bmesh.new()
    yz = ((ya, zb), (yb, zb), (yb, tb), (ya, ta))
    outer = [bm.verts.new((x + sx * 0.035, y, z)) for y, z in yz]
    inner = [bm.verts.new((x - sx * 0.01, y, z)) for y, z in yz]
    bm.faces.new(outer)
    bm.faces.new(inner[::-1])
    for k in range(4):
        bm.faces.new((outer[k], inner[k], inner[(k + 1) % 4], outer[(k + 1) % 4]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    edges = [bm.edges.get((outer[k], outer[(k + 1) % 4])) for k in range(4)]
    bmesh.ops.bevel(bm, geom=edges, offset=0.012, segments=2, affect="EDGES")
    return kit._obj("panel", bm, "marble_ivory", 40.0)


def stair(width=12.0, rise=2.8, run=7.0, steps=8):
    """A grand stair visual laid over the wing's ramp collider: bullnosed marble treads with a velvet
    runner, string walls with gilt rails. Rises toward -Y (Godot +Z is turned by the wing)."""
    P = []
    h = rise / steps
    d = run / steps
    for i in range(steps):
        z = h * (i + 1)
        y = -d * i
        # each step is solid to the ground, so the flight reads as one carved mass, not floating slabs
        P.append(kit.box("riser", (width, d + 0.02, z), (0, y - d / 2, z / 2), mat="marble_ivory", bevel=0.01))
        P.append(sweep("nosing", [(0.0, -0.04), (0.04, -0.03), (0.05, 0.0), (0.0, 0.0)], [(-width / 2, y, z), (width / 2, y, z)], "marble_ivory", cap=True))
        P.append(kit.box("runner", (width * 0.45, d + 0.02, 0.02), (0, y - d / 2, z + 0.01), mat="velvet"))
        P.append(kit.lathe("rod", [(0.015, -width * 0.24), (0.015, width * 0.24)], segments=6, mat="brass"))
        P[-1].rotation_euler = (0, math.pi / 2, 0)
        P[-1].location = (0, y - 0.04, z + 0.03)
    for sx in (-1, 1):
        bm = bmesh.new()
        # the string wall stands proud of the step ends and above the nosing line, so the flight's
        # sides read as a carved panelled string, not stacked blocks
        top0, top1 = 0.65, rise + 0.65
        x = sx * (width / 2 + 0.2)
        prof = [(x, 0.3, 0.0), (x, -run, 0.0), (x, -run, top1), (x, 0.3, top0)]
        bm.faces.new([bm.verts.new(p) for p in prof])
        ob = kit._obj("string", bm, "marble_teal", 30)
        mod = ob.modifiers.new("solid", "SOLIDIFY")
        mod.thickness = 0.4
        mod.offset = 0.0
        P.append(ob)
        rail = [(x, 0.3 - (0.3 + run) * t, top0 + (top1 - top0) * t) for t in (0.0, 0.5, 1.0)]
        P.append(kit.tube("cap_rail", rail, 0.13, 10, "gilt"))
        # carved panelled face on the outer side of the string
        xf = x + sx * 0.2
        n = max(2, round(run / 1.7))
        pl = (run - 0.14 * (n - 1)) / n
        top = lambda y: top0 + rise * (0.3 - y) / (run + 0.3)
        for i in range(n):
            ya = 0.15 - i * (pl + 0.14)
            yb = ya - pl
            ta, tb = top(ya) - 0.18, top(yb) - 0.18
            P.append(_stair_panel(xf, sx, ya, yb, 0.32, ta, tb))
            g = 0.03  # gilt bead lies 0.03 outside each panel edge
            loop = [(xf + sx * 0.01, ya + g, 0.32 - g), (xf + sx * 0.01, yb - g, 0.32 - g),
                    (xf + sx * 0.01, yb - g, tb + g), (xf + sx * 0.01, ya + g, ta + g)]
            P.append(kit.tube("panel_bead", loop + loop[:1], 0.014, 6, "gilt"))
        # marble plinth along the foot of the string, with a gilt half-round bead on top
        P.append(kit.box("plinth", (0.08, run + 0.3, 0.24), (xf + sx * 0.02, (0.3 - run) / 2, 0.12), mat="marble_ivory", bevel=0.01))
        P.append(kit.tube("plinth_bead", [(xf + sx * 0.06, 0.3, 0.245), (xf + sx * 0.06, -run, 0.245)], 0.02, 6, "gilt"))
    kit.join("stair", P)


def stair_pit():
    stair(8.0, 3.0, 6.0, 9)


def balustrade():
    """2.5 m of gilt balustrade: moulded rail and plinth with twelve vase balusters."""
    P = [sweep("rail", [(-0.09, 0.0), (0.09, 0.0), (0.11, 0.04), (0.09, 0.1), (0.05, 0.13), (-0.05, 0.13), (-0.09, 0.1), (-0.11, 0.04)], [(-1.25, 0, 0.95), (1.25, 0, 0.95)], "gilt"),
         kit.box("plinth", (2.5, 0.24, 0.14), (0, 0, 0.07), mat="marble_teal", bevel=0.02)]
    for i in range(12):
        x = -1.15 + i * (2.3 / 11)
        b = kit.lathe("baluster", [(0.05, 0.14), (0.07, 0.18), (0.05, 0.24), (0.09, 0.42), (0.1, 0.55), (0.05, 0.72), (0.04, 0.8), (0.07, 0.86), (0.07, 0.95)], segments=12, mat="gilt")
        b.location = (x, 0, 0)
        P.append(b)
    kit.join("balustrade", P)


def wind_chest():
    """The pit gantry block (8 x 5 m, 5 m tall): a great panelled wind-chest of ebony with gilt
    mouldings, a brass-railed walkway deck on top and bellows on its face."""
    W, D, H = 8.0, 5.0, 5.0
    P = [kit.box("chest", (W, D, H - 0.2), (0, 0, (H - 0.2) / 2), mat="ebony", bevel=0.05)]
    for face_y, rot in [(-D / 2 - 0.01, 0.0), (D / 2 + 0.01, math.pi)]:
        for k in range(4):
            f = frame("chest_panel", 1.6, 2.6, (0, 0, 0), mat="gilt")
            f.location = (-3.0 + 2.0 * k, face_y, 2.2)
            f.rotation_euler = (0, 0, rot)
            P.append(f)
    for face_x in (-1, 1):
        for k in range(2):
            f = frame("chest_panel", 1.6, 2.6, (0, 0, 0), mat="gilt")
            f.location = (face_x * (W / 2 + 0.01), -1.2 + 2.4 * k, 2.2)
            f.rotation_euler = (0, 0, face_x * math.pi / 2)
            P.append(f)
    P.append(kit.box("deck", (W + 0.2, D + 0.2, 0.2), (0, 0, H - 0.1), mat="boards", bevel=0.02))
    P.append(sweep("deck_edge", [(0.0, -0.1), (0.06, -0.1), (0.08, -0.05), (0.06, 0.0), (0.0, 0.0)],
                   [(-W / 2 - 0.1, -D / 2 - 0.1, H - 0.2), (W / 2 + 0.1, -D / 2 - 0.1, H - 0.2), (W / 2 + 0.1, D / 2 + 0.1, H - 0.2), (-W / 2 - 0.1, D / 2 + 0.1, H - 0.2)], "gilt", closed_path=True))
    # rail on three sides of the deck (the open side faces the pipes)
    rail = [(-W / 2, D / 2 - 0.1, H + 1.0), (W / 2, D / 2 - 0.1, H + 1.0)]
    P.append(kit.tube("rail", rail, 0.035, 8, "brass"))
    for k in range(9):
        x = -W / 2 + W * k / 8
        P.append(kit.tube("post", [(x, D / 2 - 0.1, H), (x, D / 2 - 0.1, H + 1.0)], 0.025, 6, "brass"))
    # bellows on the front face
    for k in range(3):
        b = kit.box("bellows_%d" % k, (2.0 - 0.1 * k, 0.25, 0.3), (-2.0, -D / 2 - 0.15 - 0.03 * k, 0.6 + 0.32 * k), mat="velvet", bevel=0.08)
        P.append(b)
    kit.join("wind_chest", P)


def royal_box():
    """The dome's exit ledge (6 x 4 m at 7.5 m): a royal box. A bellied gilt parapet on carved corbels,
    a velvet canopy with a crown, the ledge slab dressed as a marble floor. Origin at the slab top."""
    P = [kit.box("slab", (6.0, 4.0, 1.0), (0, 0, -0.5), mat="marble_teal", bevel=0.04)]
    plan = arc(0, -1.6, 3.0, math.pi, 2 * math.pi, 18, sy=0.3)
    P.append(sweep("parapet", [(-0.1, 0.0), (0.04, 0.0), (0.08, 0.12), (0.08, 0.85), (0.04, 0.95), (-0.1, 0.95)], plan, "gilt_orn"))
    P.append(sweep("parapet_rail", [(-0.14, 0.92), (0.12, 0.92), (0.15, 1.0), (0.12, 1.06), (-0.14, 1.06)], plan, "velvet"))
    P.append(sweep("soffit", [(0.0, -1.0), (0.1, -1.0), (0.1, 0.0), (0.0, 0.0)], [(x, y, 0) for x, y, _ in plan], "gilt"))
    for k in range(5):
        x = -2.4 + 1.2 * k
        P.append(kit.tube("corbel", [(x, -1.4, -2.2), (x, -1.6, -1.6), (x, -1.9, -1.1), (x, -2.0, -0.6)], 0.14, 8, "gilt"))
        P.append(kit.torus("corbel_scroll", 0.12, 0.05, seg=12, rseg=5, mat="gilt", loc=(x, -1.45, -2.25), rot=(0, math.pi / 2, 0)))
    for sx in (-1, 1):
        P.append(fluted_column("box_col", 4.2, 0.16, "marble_ivory", flutes=12))
        P[-1].location = (sx * 2.8, -1.2, 0)
    P.extend(drape("canopy", -3.0, 3.0, 4.6, 0.4, y=-1.5, depth=0.3, folds=6))
    crown = kit.lathe("crown", [(0.0, 0.0), (0.45, 0.0), (0.5, 0.1), (0.38, 0.35), (0.48, 0.6), (0.2, 0.7), (0.06, 0.95), (0.0, 1.0)], segments=16, mat="gilt")
    crown.location = (0, -1.4, 4.7)
    P.append(crown)
    kit.join("royal_box", P)


def coffer_panel():
    """The corridor's flip ceiling dressed (10 x 6 m, faces down at z=0): a gilt-ribbed walk face of 3 x 2
    marble coffers with rosettes, a moulded entablature and scrolled consoles at each short end, a moulded
    cornice strip along each long side, and four gilt hanger rods rising to the flies."""
    OX, OY = 5.0, 2.99
    fx = (2 * OX - 2 * 0.12) / 3
    fy = (2 * OY - 0.12) / 2
    rib = OX - fx - 0.06
    P = [kit.box("deck", (2 * OX, 6.0, 0.4), (0, 0, 0.2), mat="ebony", bevel=0.03),
         kit.box("walk_border", (2 * OX, 2 * OY, 0.005), (0, 0, -0.0025), mat="marble_teal")]
    for sx in (-1, 1):
        P.append(kit.box("rib", (0.12, 2 * OY, 0.025), (sx * rib, 0, -0.0025), mat="gilt", bevel=0.006))
    P.append(kit.box("rib", (2 * OX, 0.12, 0.025), (0, 0, -0.0025), mat="gilt", bevel=0.006))
    for i in range(3):
        xc = -OX + fx / 2 + i * (fx + 0.12)
        for yc in (-(0.06 + fy / 2), 0.06 + fy / 2):
            P.append(kit.box("coffer_ivory", (fx - 0.6, fy - 0.6, 0.008), (xc, yc, -0.009), mat="marble_ivory", bevel=0.003))
            hx, hy = fx / 2 - 0.3, fy / 2 - 0.3
            P.append(kit.box("fillet", (2 * hx + 0.024, 0.024, 0.012), (xc, yc + hy, -0.011), mat="gilt", bevel=0.004))
            P.append(kit.box("fillet", (2 * hx + 0.024, 0.024, 0.012), (xc, yc - hy, -0.011), mat="gilt", bevel=0.004))
            P.append(kit.box("fillet", (0.024, 2 * hy + 0.024, 0.012), (xc - hx, yc, -0.011), mat="gilt", bevel=0.004))
            P.append(kit.box("fillet", (0.024, 2 * hy + 0.024, 0.012), (xc + hx, yc, -0.011), mat="gilt", bevel=0.004))
            ro = kit.lathe("rosette", [(0.0, -0.028), (0.1, -0.028), (0.16, -0.022), (0.25, -0.014), (0.34, -0.006), (0.42, 0.0), (0.45, 0.0)], segments=24, mat="gilt")
            ro.location = (xc, yc, 0.0)
            P.append(ro)
            P.append(kit.torus("rosette_ring", 0.32, 0.012, seg=32, rseg=6, mat="gilt", loc=(xc, yc, -0.014)))
    ARCH = [(-0.1, -0.25), (0.12, -0.25), (0.13, -0.24), (0.12, -0.22), (0.1, -0.2), (0.1, -0.15), (0.12, -0.13), (0.1, -0.11),
            (0.09, -0.07), (0.07, -0.05), (0.07, 0.0), (-0.1, 0.0)]
    FRIEZE = [(-0.1, 0.0), (0.06, 0.0), (0.07, 0.02), (0.06, 0.04), (0.06, 0.38), (0.07, 0.4), (0.06, 0.42), (-0.1, 0.42)]
    CROWN = [(0.1, 0.5), (0.2, 0.5), (0.22, 0.52), (0.2, 0.54), (0.26, 0.58), (0.31, 0.64), (0.33, 0.72), (0.3, 0.8),
             (0.22, 0.86), (0.2, 0.9), (0.24, 0.93), (0.22, 0.95), (-0.1, 0.95), (-0.1, 0.5)]
    for sx in (-1, 1):
        path = [(sx * OX, -2.99, 0.0), (sx * OX, 2.99, 0.0)]
        if sx < 0:
            path.reverse()
        P.append(sweep("arch_band", ARCH, path, "gilt"))
        P.append(sweep("frieze", FRIEZE, path, "marble_teal"))
        P.append(sweep("crown", CROWN, path, "gilt"))
        for k in range(49):
            P.append(kit.box("dentil", (0.08, 0.06, 0.08), (sx * 5.1, -2.88 + 0.12 * k, 0.46), mat="gilt", bevel=0.008))
        for sy in (-1, 1):
            y = sy * 2.45
            P.append(kit.box("console", (0.18, 0.2, 0.06), (sx * 5.09, y, -0.27), mat="gilt", bevel=0.012))
            scroll = [(sx * u, y, z) for u, z in [(5.12, -0.3), (5.24, -0.34), (5.32, -0.42), (5.26, -0.5), (5.16, -0.565), (5.07, -0.5)]]
            P.append(kit.tube("scroll", scroll, 0.03, sides=8, mat="gilt"))
            P.append(kit.torus("volute", 0.05, 0.018, seg=14, rseg=6, mat="gilt", loc=(sx * 5.2, y, -0.42), rot=(math.pi / 2, 0, 0)))
            x = sx * 4.6
            zs = [0.4 + 0.5 * k for k in range(16)] + [8.0]
            P.append(kit.tube("hanger", [(x, sy * 2.55, z) for z in zs], 0.045, sides=12, mat="gilt"))
            for k in range(1, 8):
                P.append(kit.torus("collar", 0.06, 0.02, seg=16, rseg=6, mat="gilt", loc=(x, sy * 2.55, float(k))))
            P.append(kit.torus("hanger_ring", 0.12, 0.025, seg=24, rseg=6, mat="gilt", loc=(x, sy * 2.55, 8.0)))
    CORNICE = [(2.65, 0.0), (2.70, -0.02), (2.78, -0.07), (2.88, -0.115), (2.985, -0.115), (2.995, -0.06), (2.98, -0.035),
               (2.995, -0.01), (2.95, 0.12), (2.88, 0.22), (2.94, 0.36), (2.90, 0.5), (2.84, 0.56), (2.92, 0.62), (2.92, 0.66),
               (2.90, 0.70), (2.65, 0.70)]
    P.append(prism_x("cornice", CORNICE, -OX, OX, "gilt"))
    P.append(prism_x("cornice", [(-y, z) for y, z in CORNICE], -OX, OX, "gilt"))
    kit.join("coffer_panel", P)


def stave():
    """The corridor's stave: five brass rods on gilt brackets, 4 m long, with a treble clef boss."""
    P = []
    for k in range(5):
        z = k * 0.22
        P.append(kit.lathe("line", [(0.022, -2.0), (0.022, 2.0)], segments=8, mat="brass"))
        P[-1].rotation_euler = (0, math.pi / 2, 0)
        P[-1].location = (0, -0.12, z)
        for x in (-1.8, 0.0, 1.8):
            P.append(kit.tube("bracket", [(x, 0.0, z), (x, -0.12, z)], 0.015, 5, "gilt"))
    # a clef: a spiral and a long stroke
    pts = []
    for k in range(40):
        t = k / 39
        a = TAU * 1.6 * t
        r = 0.32 * (1 - t) + 0.04
        pts.append((-1.4 + r * math.cos(a), -0.16, 0.44 + r * math.sin(a)))
    P.append(kit.tube("clef", pts, 0.025, 6, "gilt"))
    P.append(kit.tube("clef_stroke", [(-1.4, -0.16, -0.2), (-1.35, -0.16, 0.6), (-1.25, -0.16, 1.0), (-1.4, -0.16, 1.2)], 0.025, 6, "gilt"))
    kit.join("stave", P)


def mirror():
    """A tall gilt pier mirror, 1.4 x 3.2 m, with a crest."""
    P = [frame("mirror_frame", 1.4, 3.2, (0, 0, 1.6), mat="gilt", prof=[(0.0, 0.0), (0.0, 0.05), (0.04, 0.09), (0.09, 0.08), (0.13, 0.04), (0.15, 0.0)])]
    P.append(kit.box("glass", (1.3, 0.02, 3.1), (0, 0.01, 1.6), mat="mirror"))
    crest = kit.lathe("crest", [(0.0, 0.0), (0.35, 0.0), (0.4, 0.05), (0.3, 0.1), (0.0, 0.12)], segments=20, mat="gilt")
    crest.rotation_euler = (math.pi / 2, 0, 0)
    crest.scale = (1.2, 1.0, 1.0)
    crest.location = (0, -0.06, 3.35)
    P.append(crest)
    kit.join("mirror", P)


def stand():
    """A music stand: tripod base, brass column, a pierced desk tilted back."""
    P = []
    for k in range(3):
        a = TAU * k / 3
        P.append(kit.tube("leg", [(0, 0, 0.35), (0.3 * math.cos(a), 0.3 * math.sin(a), 0.0)], 0.012, 5, "iron"))
    P.append(kit.lathe("col", [(0.014, 0.3), (0.014, 1.15), (0.02, 1.17)], segments=8, mat="brass"))
    desk = kit.box("desk", (0.5, 0.012, 0.34), (0, 0, 0), mat="iron", bevel=0.004)
    desk.rotation_euler = (math.radians(-18), 0, 0)
    desk.location = (0, -0.03, 1.28)
    P.append(desk)
    lip = kit.box("lip", (0.5, 0.06, 0.012), (0, -0.07, 1.12), mat="iron")
    P.append(lip)
    kit.join("stand", P)


def cello():
    """A cello on its side: carved waisted body with f-holes suggested, neck, scroll, pin."""
    def body(z, th):
        t = z / 0.78
        w = 0.21 + 0.06 * math.cos(TAU * t) * 0.0 + (0.22 if t < 0.5 else 0.18) - 0.06 * math.exp(-((t - 0.5) / 0.1) ** 2)
        return w * (0.55 + 0.45 * abs(math.cos(th))) ** 0.3
    P = [lathe_fn("body", [0.78 * k / 20 for k in range(21)], lambda z, th: (0.2 + 0.07 * math.sin(math.pi * z / 0.78) - 0.06 * math.exp(-((z / 0.78 - 0.5) / 0.1) ** 2)) * (1.0 if abs(math.sin(th)) < 0.7 else 0.55), 24, "cello_wood")]
    P[-1].scale = (1.0, 0.45, 1.0)
    P.append(kit.box("neck", (0.06, 0.04, 0.55), (0, -0.08, 1.05), mat="ebony", bevel=0.01))
    P.append(kit.torus("scroll", 0.04, 0.018, seg=12, rseg=5, mat="cello_wood", loc=(0, -0.08, 1.36), rot=(0, math.pi / 2, 0)))
    P.append(kit.lathe("pin", [(0.01, 0.0), (0.01, -0.3), (0.0, -0.32)], segments=6, mat="iron"))
    for k in range(4):
        P.append(kit.tube("string", [(-0.03 + 0.02 * k, -0.11, 0.12), (-0.015 + 0.01 * k, -0.11, 1.28)], 0.002, 3, "brass"))
    kit.join("cello", P)


def backdrop():
    """A flown painted backdrop, 14 x 9 m: canvas hanging from a batten with a slight belly and ripples,
    weighted at the hem by a pipe. UVs 0..1 across the canvas (own material)."""
    def fn(u, v):
        x = -7.0 + 14.0 * u
        z = -v * 9.0
        y = 0.12 * math.sin(3 * TAU * u + 1.3 * v) * v + 0.25 * math.sin(math.pi * u) * v
        return (x, y, z)
    P = [grid("canvas", 48, 24, fn, "backdrop")]
    P.append(kit.lathe("batten", [(0.05, -7.2), (0.05, 7.2)], segments=10, mat="iron"))
    P[-1].rotation_euler = (0, math.pi / 2, 0)
    P.append(kit.lathe("hem", [(0.04, -7.0), (0.04, 7.0)], segments=8, mat="iron"))
    P[-1].rotation_euler = (0, math.pi / 2, 0)
    P[-1].location = (0, 0.25, -9.0)
    for k in range(6):
        x = -6.5 + 2.6 * k
        P.append(kit.tube("lift_line", [(x, 0, 0), (x, 0, 9.0)], 0.012, 4, "rope"))
    kit.join("backdrop", P)


def rigging():
    """A bay of fly-loft rigging, 4 m: a timber gridiron beam, ten hemp lines dropping to a pin rail,
    sandbags on some, a batten across. Tall: 12 m."""
    P = [kit.box("grid_beam", (4.0, 0.3, 0.45), (0, 0, 12.0), mat="boards", bevel=0.03),
         kit.box("pin_rail", (4.0, 0.25, 0.25), (0, 0, 1.0), mat="boards", bevel=0.02)]
    for k in range(10):
        x = -1.8 + 0.4 * k
        sway = 0.06 * math.sin(k * 1.7)
        P.append(kit.tube("line", [(x, 0, 11.8), (x + sway, -0.05, 6.0), (x, 0, 1.1)], 0.014, 5, "rope"))
        P.append(kit.lathe("pin", [(0.02, 0.85), (0.03, 1.0), (0.02, 1.35), (0.035, 1.42), (0.0, 1.45)], segments=8, mat="boards"))
        P[-1].location = (x, -0.13, 0)
        P.append(kit.tube("coil", [(x - 0.06, -0.15, 1.3), (x, -0.22, 0.9), (x + 0.06, -0.15, 1.3)], 0.02, 5, "rope"))
        if k % 3 == 1:
            bag = kit.lathe("sandbag", [(0.0, 0.0), (0.16, 0.05), (0.19, 0.25), (0.14, 0.45), (0.05, 0.55), (0.03, 0.62), (0.0, 0.63)], segments=12, mat="canvas")
            bag.location = (x + sway, -0.05, 4.0 + 1.5 * (k % 2))
            P.append(bag)
    kit.join("rigging", P)


def catwalk():
    """4 m of fly-gallery catwalk rail: iron stanchions, a timber handrail, a toe-board."""
    P = [kit.box("toe", (4.0, 0.03, 0.15), (0, 0, 0.075), mat="boards", bevel=0.005),
         kit.box("hand", (4.0, 0.08, 0.06), (0, 0, 1.05), mat="boards", bevel=0.01),
         kit.box("mid", (4.0, 0.03, 0.03), (0, 0, 0.55), mat="iron")]
    for k in range(3):
        x = -1.8 + 1.8 * k
        P.append(kit.box("stanchion", (0.05, 0.05, 1.05), (x, 0, 0.525), mat="iron", bevel=0.005))
    kit.join("catwalk", P)


def fragment():
    """The fragment: a long faceted crystal shard ringed by a gilt stave of five fine bands."""
    P = [kit.lathe("shard", [(0.0, -0.45), (0.12, -0.25), (0.16, 0.0), (0.1, 0.3), (0.0, 0.5)], segments=6, mat="fragment_crystal", smooth_angle=None)]
    for k in range(5):
        P.append(kit.torus("band", 0.24 + 0.012 * k, 0.006, seg=40, rseg=4, mat="gilt", loc=(0, 0, -0.1 + 0.05 * k), rot=(0.25, 0, 0)))
    kit.join("fragment", P)


def prov_score():
    """Provenance: a pencilled score, page nine, on a small gilt lectern (origin on the floor)."""
    P = [kit.lathe("lectern", [(0.18, 0.0), (0.18, 0.03), (0.04, 0.05), (0.03, 0.75), (0.06, 0.8)], segments=12, mat="gilt")]
    desk = kit.box("desk", (0.42, 0.3, 0.025), (0, 0, 0.0), mat="ebony", bevel=0.006)
    desk.rotation_euler = (math.radians(25), 0, 0)
    desk.location = (0, 0, 0.84)
    P.append(desk)

    def page(u, v):
        x = -0.2 + 0.4 * u
        y = -0.14 + 0.28 * v
        z = 0.03 * math.sin(math.pi * u) * (1 - v) + 0.015
        return (x, y, z)
    pg = grid("page", 10, 6, page, "score_paper")
    pg.rotation_euler = (math.radians(25), 0, 0)
    pg.location = (0, 0, 0.86)
    P.append(pg)
    kit.join("prov_score", P)


def prov_baton():
    """Provenance: an ash conductor's baton resting on a velvet cushion."""
    cush = kit.box("cushion", (0.5, 0.32, 0.1), (0, 0, 0.05), mat="velvet", bevel=0.04)
    bat = kit.lathe("baton", [(0.0, 0.0), (0.02, 0.01), (0.022, 0.08), (0.012, 0.1), (0.008, 0.45), (0.0, 0.46)], segments=10, mat="ash")
    bat.rotation_euler = (0, math.pi / 2, 0.3)
    bat.location = (-0.2, 0, 0.12)
    tass = [kit.lathe("tassel", [(0.0, 0.0), (0.02, 0.01), (0.025, 0.06), (0.0, 0.07)], segments=8, mat="gilt")]
    tass[0].location = (0.24, 0.15, 0.0)
    kit.join("prov_baton", [cush, bat] + tass)


def prov_fork():
    """Provenance: a small steel tuning fork in an open velvet-lined case."""
    case = kit.box("case", (0.36, 0.16, 0.06), (0, 0, 0.03), mat="ebony", bevel=0.01)
    lining = kit.box("lining", (0.32, 0.12, 0.01), (0, 0, 0.061), mat="velvet")
    lid = kit.box("lid", (0.36, 0.16, 0.02), (0, 0.11, 0.1), mat="ebony", bevel=0.006)
    lid.rotation_euler = (math.radians(-70), 0, 0)
    stem = kit.lathe("stem", [(0.006, 0.0), (0.006, 0.08)], segments=6, mat="pipe_tin")
    stem.rotation_euler = (0, math.pi / 2, 0)
    stem.location = (-0.16, 0, 0.075)
    prongs = []
    for sy in (-0.012, 0.012):
        prongs.append(kit.box("prong", (0.18, 0.006, 0.006), (0.0, sy, 0.075), mat="pipe_tin"))
    yoke = kit.box("yoke", (0.012, 0.03, 0.006), (-0.085, 0, 0.075), mat="pipe_tin")
    kit.join("prov_fork", [case, lining, lid, stem, yoke] + prongs)


def _arch_band(name, cx, half, spring, rise, y, prof, mat="gilt"):
    a = arc(cx, 0, half, math.pi, 0, 24, sy=rise / half)
    path = [(cx - half, y, 0.3)] + [(x, y, spring + z) for x, z, _ in a] + [(cx + half, y, 0.3)]
    return sweep(name, prof, path, mat, smooth=60, axis=(0, -1, 0))


def _spandrel(name, cx, half, spring, rise, top, y, mat):
    a = arc(cx, 0, half, math.pi, 0, 24, sy=rise / half)
    bm = bmesh.new()
    for i in range(len(a) - 1):
        (x0, z0, _), (x1, z1, _) = a[i], a[i + 1]
        bm.faces.new([bm.verts.new((x0, y, spring + z0)), bm.verts.new((x1, y, spring + z1)), bm.verts.new((x1, y, top)), bm.verts.new((x0, y, top))])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    ob = kit._obj(name, bm, mat, 30)
    ob.modifiers.new("solid", "SOLIDIFY").thickness = 0.5
    return ob


AB_PROF = [(0.0, 0.0), (0.0, 0.35), (0.08, 0.4), (0.2, 0.32), (0.24, 0.12), (0.2, -0.1), (0.0, -0.1)]


def screen():
    """The colonnade between foyer and stalls, 30 m: four paired columns on pedestals carrying three
    arches, an entablature and an attic with a central clock-less cartouche. Open below the arches."""
    P = []
    for x in (-13.6, -4.6, 4.6, 13.6):
        for dx in (-0.55, 0.55):
            P.append(kit.box("ped", (0.95, 0.95, 1.2), (x + dx, 0, 0.6), mat="marble_teal", bevel=0.04))
            col = fluted_column("col", 7.2, 0.32, "marble_ivory", flutes=18)
            col.location = (x + dx, 0, 1.2)
            P.append(col)
        P.append(kit.box("pier_back", (2.2, 0.8, 8.4), (x, 0.55, 4.2), mat="damask_ox"))
    for cx, half in ((-9.1, 3.9), (0.0, 4.0), (9.1, 3.9)):
        P.append(_arch_band("arch", cx, half, 5.4, 2.6, -0.5, AB_PROF))
        P.append(_spandrel("spandrel", cx, half, 5.4, 2.6, 8.4, 0.0, "damask_ox"))
        k = kit.box("keystone", (0.6, 0.7, 0.9), (cx, -0.3, 8.1), mat="gilt", bevel=0.06)
        P.append(k)
    P.append(kit.box("architrave", (30.0, 1.2, 0.6), (0, 0.1, 8.7), mat="marble_ivory", bevel=0.03))
    P.append(kit.box("frieze", (30.0, 1.0, 0.9), (0, 0.1, 9.45), mat="gilt_orn"))
    P.append(sweep("cornice", [(u * 1.3, v * 1.3) for u, v in P_CORNICE], [(-15.0, -0.45, 9.9), (15.0, -0.45, 9.9)], "gilt"))
    P.append(kit.box("attic", (30.0, 0.8, 3.6), (0, 0.2, 12.4), mat="damask_ox"))
    for x in (-9.1, 9.1):
        P.append(frame("attic_panel", 5.0, 2.4, (x, -0.2, 12.3), mat="gilt"))
    cart = kit.lathe("cartouche", [(0.0, 0.0), (1.3, 0.0), (1.4, 0.1), (1.2, 0.22), (0.7, 0.3), (0.0, 0.32)], segments=32, mat="gilt")
    cart.rotation_euler = (math.pi / 2, 0, 0)
    cart.scale = (1.4, 1.0, 1.0)
    cart.location = (0, -0.2, 12.3)
    P.append(cart)
    for sx in (-1, 1):
        for k in range(4):
            ang = 0.2 + 0.3 * k
            P.append(kit.tube("frond", [(sx * 1.6, -0.4, 12.3), (sx * (1.6 + 1.0 * math.cos(ang)), -0.45, 12.3 + 0.6 * math.sin(ang)), (sx * (1.6 + 2.2 * math.cos(ang)), -0.4, 12.3 + 0.9 * math.sin(ang))], 0.07, 6, "gilt"))
    kit.join("screen", P)


def portal():
    """The arch over the pit stair, 8 m wide and 14 m tall: an open arch 6.5 m high in a gilt band,
    damask spandrels, a balconied tier above and a cornice, so the horseshoe continues over it."""
    P = [_arch_band("portal_arch", 0.0, 3.8, 4.2, 2.3, -0.3, AB_PROF), _spandrel("portal_spandrel", 0.0, 3.8, 4.2, 2.3, 7.4, 0.05, "damask_ox")]
    for sx in (-1, 1):
        col = fluted_column("portal_col", 7.0, 0.3, "marble_ivory", flutes=16)
        col.location = (sx * 4.1, -0.4, 0)
        P.append(col)
    P.append(kit.box("lintel", (8.6, 0.9, 0.5), (0, -0.2, 7.3), mat="marble_ivory", bevel=0.03))
    P.append(kit.box("upper", (8.6, 0.2, 6.6), (0, 0.1, 10.8), mat="damask_ox"))
    plan = arc(0, -0.2, 3.6, math.pi, 2 * math.pi, 18, sy=0.3)
    P.append(sweep("balcony", [(-0.08, 0.0), (0.02, 0.0), (0.06, 0.12), (0.06, 0.8), (0.02, 0.9), (-0.08, 0.9)], [(x, y, 7.6) for x, y, _ in plan], "gilt_orn"))
    P.append(sweep("balcony_rail", [(-0.12, 0.88), (0.1, 0.88), (0.14, 0.94), (0.12, 1.0), (-0.12, 1.04)], [(x, y, 7.6) for x, y, _ in plan], "velvet"))
    P.append(sweep("balcony_floor", [(0.0, 0.0), (0.0, 0.25), (-1.0, 0.25), (-1.0, 0.0)], [(x, y, 7.35) for x, y, _ in plan], "gilt"))
    P.append(frame("upper_panel", 4.0, 2.8, (0, -0.05, 10.9), mat="gilt"))
    P.extend(drape("valance", -3.4, 3.4, 10.8, 0.4, y=-1.1, depth=0.25, folds=7))
    P.append(sweep("cornice", P_CORNICE, [(-4.3, -0.3, 12.8), (4.3, -0.3, 12.8)], "gilt"))
    kit.join("portal", P)


def chain():
    """26 m of chandelier chain: gilt links, alternate links turned 90 degrees, hanging down from z=0."""
    P = []
    for i in range(110):
        rot = (math.pi / 2, 0, 0) if i % 2 == 0 else (math.pi / 2, 0, math.pi / 2)
        lk = kit.torus("link", 0.09, 0.025, seg=10, rseg=5, mat="gilt", loc=(0, 0, -0.24 * i), rot=rot)
        lk.scale = (1.0, 1.0, 1.0)
        P.append(lk)
    kit.join("chain", P)


def page():
    """A loose score page, 0.42 x 0.3, lying in XY (centred): a soft cylindrical bow across it, one corner
    curling up and a little ripple, so it tumbles like paper rather than a card."""
    def fn(u, v):
        x, y = (u - 0.5) * 0.42, (v - 0.5) * 0.3
        z = 0.035 * math.sin(math.pi * u) + 0.006 * math.sin(7.0 * u + 3.0 * v)
        c = max(0.0, u + v - 1.25)  # the far corner curls
        z += 0.15 * c * c
        return (x, y, z)
    grid("page_sheet", 14, 10, fn, "score_paper", 80)
    kit.join("page", [bpy.data.objects["page_sheet"]])


def dome_shell():
    """The rotunda dome, 14 m radius hemisphere on z=0, seen from inside. Polar UVs: the apex is the centre
    of the square fresco and the rim its circle, so the painting reads straight up. A gilt cornice ring at the rim."""
    R, NS, NR = 14.0, 72, 24
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    rows = []
    for j in range(NR + 1):
        phi = (math.pi / 2) * j / NR  # 0 apex .. 90 deg rim
        rows.append([bm.verts.new((R * math.sin(phi) * math.cos(TAU * i / NS), R * math.sin(phi) * math.sin(TAU * i / NS),
                                   R * math.cos(phi))) for i in range(NS)])
    for j in range(NR):
        for i in range(NS):
            i2 = (i + 1) % NS
            f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            for lp in f.loops:
                x, y, z = lp.vert.co
                phi = math.acos(max(-1.0, min(1.0, z / R)))
                r = 0.49 * phi / (math.pi / 2)
                th = math.atan2(y, x)
                if j == 0 and lp.vert in rows[0]:  # apex ring: take the face's own angle so the seam stays clean
                    th = TAU * (i + 0.5) / NS
                lp[uv].uv = (0.5 + r * math.cos(th), 0.5 - r * math.sin(th))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:  # normals point inward: the dome is seen from below
        if f.normal.dot(f.calc_center_median()) > 0:
            f.normal_flip()
    P = [kit._obj("dome_painted", bm, "dome_painted", 60)]
    P.append(sweep("cornice", [(-0.6, 0.0), (0.0, 0.0), (0.25, 0.2), (0.15, 0.45), (0.4, 0.6), (0.35, 0.8), (-0.6, 0.8)],
                   [(R * math.cos(TAU * i / 96), R * math.sin(TAU * i / 96), -0.6) for i in range(96)], "gilt", closed_path=True))
    kit.join("dome_shell", P)


KINDS = {k: v for k, v in globals().items() if callable(v) and k in (
    "tier_bay", "panel_bay", "proscenium", "organ_case", "ceiling", "seat", "figure", "figure_head", "horn", "pipes",
    "glass_bowls", "fork_statue", "chandelier", "stair", "stair_pit", "balustrade", "wind_chest", "royal_box",
    "coffer_panel", "stave", "mirror", "stand", "cello", "backdrop", "rigging", "catwalk", "fragment",
    "prov_score", "prov_baton", "prov_fork", "screen", "portal", "chain", "dome_shell", "page")}


def build(args):
    KINDS[args[0]]()
