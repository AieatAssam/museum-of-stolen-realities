"""Partition membranes for the Chitin Court Foundry: visual-only models that hide the room's interior box walls.

Build: tools/blender_build.sh wings/chitin/models/src/partitions.py wings/chitin/models/<part>.glb <part>
  <part> is part_guild, part_vault or part_rim. All are visual only (no collision suffixes): the collision
  boxes stay as they are and these meshes sit on the outside of them.
part_rim: grown carapace wall over the heist exit slab (z -41..-40, x 104..131, top y 4): a shingle-plate face
  toward +z (0.3 m proud below y=0, 0.8 m above), a tine crest 0.5..3 m above y=4 curling back, round ends,
  4 carapace_dull ribs, a floor fillet at y=-3 and comb patches (comb_patch.build_flows) on the face.

part_guild: two-sided carapace membrane on the faces z=80 and z=81 of the guild partition (x95..126 and
x134..160, y-31..-10), a door opening x126..134 below y=-26 that stays clear, door jamb beads, the membrane
carried up into the shell_foundry vault (rooms.py profile), a floor fillet at y=-31, and comb patches
(comb_patch.py) on both faces.

part_vault: wax comb cocoon around the vault collision walls (x95..105, z63.5..74) with a domed amber roof
cap. Outer surfaces stay within 0.3 m of the collision boxes, edges are rounded outward, the door opening
x98..102 below y=-26 on z=74 stays clear.

Both parts are checked on their final vertex positions (Godot coordinates) by the asserts in build().
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import comb_patch  # noqa: E402
import rooms  # noqa: E402
import kit  # noqa: E402

ROOM = "shell_foundry"
BAND = 0.3          # max distance from a vertex to the collision boxes, below the collision top
TOL = 0.005
MEMBRANE_STEP = 0.5  # x sampling of the membrane grid (m)
NY = 44              # rows per membrane column (y from the floor to the vault crown)
PATCH_BUDGET = 30000


def _smooth01(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def _box_dist(p, lo, hi):
    d = [max(lo[k] - p[k], 0.0, p[k] - hi[k]) for k in range(3)]
    return math.sqrt(sum(v * v for v in d))


def _tris(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def _grid(bm, G):
    """G[i][j] are Godot points; quads join neighbouring columns and rows."""
    V = [[bm.verts.new(rooms._blender(p)) for p in col] for col in G]
    for i in range(len(V) - 1):
        for j in range(len(V[i]) - 1):
            try:
                bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
            except ValueError:
                pass


def _finish(name, bm, mats):
    me = bpy.data.meshes.new(name)
    for m in mats:
        me.materials.append(kit.material(m))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# --- part_guild ------------------------------------------------------------------------------------

G_FLOOR = -31.0
G_TOP = -10.0              # collision top of the guild partition
G_DOOR = (126.0, 134.0)    # door opening x, below y = -26
G_DOOR_Y = -26.0
G_BOXES = [                 # collision boxes (Godot lo, hi)
    ((95.0, -31.0, 80.0), (126.0, -10.0, 81.0)),
    ((134.0, -31.0, 80.0), (160.0, -10.0, 81.0)),
    ((126.0, -26.0, 80.0), (134.0, -10.0, 81.0)),
]


def _hw(y):
    """Jamb half-width along x: 0.6 mid height, flaring to 1.0 at the floor and at the lintel."""
    fl = _smooth01((-29.0 - y) / 2.0)
    tp = _smooth01((y + 27.0) / 1.0)
    return 0.6 + 0.4 * max(fl, tp)


def _offset(x, y, yt, edges, floor_foot, seed):
    """Outward offset (m, >= 0) of the membrane from its collision face at (x, y)."""
    lo, hi = edges
    n = noise.noise(Vector((x * 0.23, y * 0.23, seed)))          # about [-1, 1]
    fx = _smooth01(min(x - lo, hi - x) / 0.6)                    # flush with the walls at the ends
    ft = _smooth01((yt - y) / 1.0)                               # seams into the vault crown
    d = (0.08 + 0.06 * n) * ft                                  # low bulge: leaves the 0.3 m band to the comb
    if floor_foot:
        h = y - G_FLOOR
        if h < 0.5:                                              # 0.5 m tall floor fillet, 0.28 m out
            d = max(d, 0.28 * math.sqrt(max(0.0, 1.0 - (h / 0.5) ** 2)))
    return min(0.28, max(0.0, d)) * fx


def _membrane(x0, x1, y0, face, sgn, top, edges, floor_foot, seed):
    nx = int(round((x1 - x0) / MEMBRANE_STEP)) + 1
    G = []
    for i in range(nx):
        x = x0 + (x1 - x0) * i / (nx - 1)
        yt = top(x)
        col = []
        for j in range(NY):
            y = y0 + (yt - y0) * j / (NY - 1)
            col.append((x, y, face + sgn * _offset(x, y, yt, edges, floor_foot, seed)))
        G.append(col)
    return G


def _jamb(side, face, sgn):
    """Door jamb bead: a half-ellipse in x and z, its outer edge on the wall end, 0.3 m proud of the face."""
    G = []
    nt, ny = 7, 11
    for i in range(nt):
        t = i / (nt - 1)
        dz = 0.3 * math.sqrt(max(0.0, 1.0 - (2.0 * t - 1.0) ** 2))
        col = []
        for j in range(ny):
            y = G_FLOOR + 5.0 * j / (ny - 1)
            hw = _hw(y)
            x = 126.0 - 2.0 * hw + 2.0 * hw * t if side < 0 else 134.0 + 2.0 * hw * t
            col.append((x, y, face + sgn * dz))
        G.append(col)
    return G


def _guild_hooks():
    def sample(rng):
        sgn = -1.0 if rng.random() < 0.5 else 1.0
        face = 80.0 if sgn < 0 else 81.0
        x = rng.uniform(97.0, 124.0) if rng.random() < 0.6 else rng.uniform(136.0, 158.0)
        y = rng.uniform(-28.0, -12.0)
        origin = rooms._blender((x, y, face + 3.0 * sgn))
        target = rooms._blender((x, y, face + 0.5 * sgn))
        return origin, target, (x, y, sgn)

    def accept(g, meta):
        x, y = g[0], g[1]
        if y < -28.0 or x < 96.5 or x > 158.5:
            return 0.0
        if 118.0 < x < 142.0 and y < -20.0:                      # keep the door and its lintel clear
            return 0.0
        return 0.25

    def radius(g, meta):
        x = g[0]
        dx = min(abs(x - 95.0), abs(x - 126.0), abs(x - 134.0), abs(x - 160.0))
        return max(0.0, min(comb_patch.MAX_R, dx - 0.8, g[1] - G_FLOOR - 0.8))

    def dn(g):
        lo = 80.0 - g[2]
        hi = g[2] - 81.0
        return lo if abs(lo) <= abs(hi) else hi

    return sample, accept, radius, dn


def _build_guild():
    room = rooms._room(ROOM)
    H, uc, ys, D, yof, slope = rooms._vault(room)

    def top(x):
        return yof(x - uc) - 0.1                                 # sunk slightly into the crown

    bm = bmesh.new()
    for sgn, face, seed in ((-1.0, 80.0, 0.31), (1.0, 81.0, 0.67)):
        for x0, x1, y0, edges, foot in ((95.0, 126.0, G_FLOOR, (95.0, 126.0), True),
                                        (126.0, 134.0, G_DOOR_Y, (126.0, 134.0), False),
                                        (134.0, 160.0, G_FLOOR, (134.0, 160.0), True)):
            _grid(bm, _membrane(x0, x1, y0, face, sgn, top, edges, foot, seed))
        _grid(bm, _jamb(-1, face, sgn))
        _grid(bm, _jamb(+1, face, sgn))
    bm.normal_update()
    print("MEMBRANE part_guild shell tris %d" % _tris(bm))

    sample, accept, radius, dn = _guild_hooks()
    pbm, pst = comb_patch.build_patches(bm, "part_guild_comb", sample, radius, accept, dn,
                                        G_TOP, 0.3, PATCH_BUDGET)

    # self-check on final positions (Godot coordinates)
    pts = [comb_patch.to_g(v.co) for v in bm.verts] + [comb_patch.to_g(v.co) for v in pbm.verts]
    worst = 0.0
    for p in pts:
        x, y, z = p
        assert not (G_DOOR[0] < x < G_DOOR[1] and G_FLOOR < y < G_DOOR_Y and 79.0 < z < 82.0), \
            "part_guild: vertex in the door opening at %s" % (p,)
        if y < G_TOP:
            d = min(_box_dist(p, lo, hi) for lo, hi in G_BOXES)
            worst = max(worst, d)
            assert d <= BAND + TOL, "part_guild: vertex %s is %.3f from collision" % (p, d)
    print("SELFCHECK part_guild: %d verts, door clear, worst distance below y=%.1f is %.3f (limit %.2f)"
          % (len(pts), G_TOP, worst, BAND))

    print("TRIS part_guild membrane %d, comb %d (%d patches)" % (_tris(bm), pst["tris"], pst["patches"]))
    membrane = _finish("part_guild", bm, ["carapace"])
    patches = comb_patch.make_object("part_guild_comb", pbm)
    return [membrane, patches]


# --- part_vault ------------------------------------------------------------------------------------

V_BOXES = [                 # collision boxes (Godot lo, hi): walls from the floor to the roof underside
    ((95.0, -31.0, 63.5), (105.0, -26.0, 64.0)),
    ((104.5, -31.0, 64.0), (105.0, -26.0, 74.0)),
    ((95.0, -31.0, 73.5), (98.0, -26.0, 74.0)),
    ((102.0, -31.0, 73.5), (105.0, -26.0, 74.0)),
    ((95.0, -26.0, 63.5), (105.0, -25.5, 74.0)),                 # roof
]
V_WALLS = [                 # cocoon around each wall: 0.3 m outside, the x=95 side left flush
    ((95.0, -31.0, 63.2), (105.3, -25.8, 64.3), 0.4),
    ((104.2, -31.0, 63.7), (105.3, -25.8, 74.3), 0.4),
    ((95.0, -31.0, 73.2), (98.0, -25.8, 74.3), 0.4),              # door side stops at x=98
    ((102.0, -31.0, 73.2), (105.3, -25.8, 74.3), 0.4),            # door side starts at x=102
]
V_ROOF = ((95.0, -26.0, 63.2), (105.3, -25.5, 74.3), 0.4)
V_DOOR = ((98.0, -31.0, 73.5), (102.0, -26.0, 74.5))
V_DOME = 0.5                                                      # roof rises to y=-25.0 at the centre


def _rounded_cube(bm, lo, hi, r, dome=0.0, plan_only=False):
    """Cube grid added to bm, projected onto a rounded box (outward rounding only: the box keeps its lo/hi
    extents). plan_only rounds the x-z corners only (for a thin roof, whose y extent cannot take the radius).
    dome lifts the top face by up to `dome` at its centre."""
    axes = (0, 2) if plan_only else (0, 1, 2)
    before_v, before_e = set(bm.verts), set(bm.edges)
    bmesh.ops.create_cube(bm, size=1.0)
    cube_edges = [e for e in bm.edges if e not in before_e]
    bmesh.ops.subdivide_edges(bm, edges=cube_edges, cuts=6, use_grid_fill=True)
    new_verts = [v for v in bm.verts if v not in before_v]
    c = [(lo[k] + hi[k]) / 2.0 for k in range(3)]
    s = [hi[k] - lo[k] for k in range(3)]
    for v in new_verts:
        unit = (v.co.x, v.co.z, -v.co.y)                          # Blender -> Godot unit cube
        p = [c[k] + s[k] * unit[k] for k in range(3)]
        q = list(p)
        for k in axes:
            q[k] = min(max(p[k], lo[k] + r), hi[k] - r)
        d = [p[k] - q[k] for k in range(3)]
        L = math.sqrt(sum(d[k] * d[k] for k in axes))
        if L > 1e-9:
            for k in axes:
                p[k] = q[k] + d[k] / L * r
        if dome and p[1] >= hi[1] - 1e-6:
            u = (p[0] - c[0]) / (s[0] / 2.0)
            vv = (p[2] - c[2]) / (s[2] / 2.0)
            p[1] += dome * max(0.0, 1.0 - u * u) * max(0.0, 1.0 - vv * vv)
        v.co = rooms._blender(p)
    return new_verts


def _build_vault():
    walls = bmesh.new()
    for lo, hi, r in V_WALLS:
        _rounded_cube(walls, lo, hi, r)
    roof = bmesh.new()
    roof_lo, roof_hi, roof_r = V_ROOF
    _rounded_cube(roof, roof_lo, roof_hi, roof_r, dome=V_DOME, plan_only=True)

    pts = [comb_patch.to_g(v.co) for bmx in (walls, roof) for v in bmx.verts]
    print("TRIS part_vault walls %d, roof %d" % (_tris(walls), _tris(roof)))
    worst = 0.0
    for p in pts:
        x, y, z = p
        in_door = (V_DOOR[0][0] < x < V_DOOR[1][0] and V_DOOR[0][1] < y < V_DOOR[1][1]
                   and V_DOOR[0][2] < z < V_DOOR[1][2])
        assert not in_door, "part_vault: vertex in the door opening at %s" % (p,)
        if y < -25.5:
            d = min(_box_dist(p, lo, hi) for lo, hi in V_BOXES)
            worst = max(worst, d)
            assert d <= BAND + TOL, "part_vault: vertex %s is %.3f from collision" % (p, d)
    print("SELFCHECK part_vault: %d verts, door clear, worst distance below y=-25.5 is %.3f (limit %.2f)"
          % (len(pts), worst, BAND))

    # roof dome top check
    top_y = max(p[1] for p in pts)
    assert top_y <= -25.0 + 1e-6, "part_vault: roof rises above -25.0 (%.3f)" % top_y

    wall_ob = _finish("part_vault", walls, ["wax"])
    roof_ob = _finish("part_vault_cap", roof, ["amber"])
    return [wall_ob, roof_ob]


# --- part_rim --------------------------------------------------------------------------------------

RIM_BOX = ((104.0, -4.0, -41.0), (131.0, 4.0, -40.0))  # collision slab behind the balcony (Godot)
RIM_FRONT = -40.0          # slab face toward the balcony (+z)
RIM_BACK = -41.2           # closing back surface
RIM_X = (103.8, 131.2)     # plan x extent: slab x 104..131 plus 0.3
RIM_R = 0.6                # round end return radius (half the wall depth)
RIM_FLOOR = -3.0           # rim walkway top: the wall foot
RIM_TOP = 4.0              # slab top: the crest rises from here
RIM_CROWN_MAX = 7.0        # highest tine tip
RIM_NY = 40                # rows per column, floor to crest
RIM_STEP = 0.3             # plan spacing along the face and back (m)
RIM_RIBS = (111.0, 116.2, 121.5, 126.0)   # carapace_dull ribs, each climbs into a tine
RIM_TINES = ((106.5, 1.2, 0.9), (111.0, 1.4, 2.6), (116.2, 1.5, 1.4),   # (centre x, half width, height above 4)
             (121.5, 1.4, 2.9), (126.0, 1.3, 1.8), (129.5, 1.0, 0.8))
RIM_COMB_BUDGET = 4000     # comb triangles


def _rim_tine(x):
    """Crest height above y = RIM_TOP (>= 0): pointed tines, valleys sit flush with the slab top."""
    t = 0.0
    for cx, hw, h in RIM_TINES:
        u = abs(x - cx) / hw
        if u < 1.0:
            t = max(t, h * (1.0 - u) ** 1.5)
    return t


def _rim_disp(x, y):
    """Outward offset (m) of the face toward +z at (x, y): shingle plates, rib bumps, a floor fillet at the
    foot and a lean above y=0. Capped at 0.3 m below y=0, 0.8 m above."""
    h = y - RIM_FLOOR
    plate = rooms._plate(x - RIM_X[0], h, 0.9, 0.7, 0.45)
    rib = 0.0
    for xr in RIM_RIBS:
        rib = max(rib, 0.2 * math.exp(-((x - xr) / 0.28) ** 2))
    rib *= _smooth01((h - 0.4) / 0.8)
    fil = (0.3 * math.sqrt(max(0.0, 1.0 - (h / 0.6) ** 2))
           * _smooth01((x - 104.4) / 0.6) * _smooth01((130.6 - x) / 0.6))   # fades off the walkway ends
    lean = 0.4 * _smooth01(y / 3.0) if y > 0.0 else 0.0
    cap = 0.3 + 0.5 * _smooth01(y / 1.0)
    return min(cap, plate + rib + fil + lean)


def _rim_plan():
    """Closed plan loop (x, z, nx, nz): front face z=-40, back z=-41.2, half-round ends of radius RIM_R."""
    cl, cr = RIM_X[0] + RIM_R, RIM_X[1] - RIM_R
    zc = (RIM_FRONT + RIM_BACK) / 2.0
    nf = int(math.ceil((cr - cl) / RIM_STEP))
    P = [(cl + (cr - cl) * i / nf, RIM_FRONT, 0.0, 1.0) for i in range(nf + 1)]
    for k in range(1, 9):                                         # right return, front to back
        th = math.pi / 2 - math.pi * k / 9
        P.append((cr + RIM_R * math.cos(th), zc + RIM_R * math.sin(th), math.cos(th), math.sin(th)))
    P += [(cr - (cr - cl) * i / nf, RIM_BACK, 0.0, -1.0) for i in range(nf + 1)]   # back, right to left
    for k in range(1, 9):                                         # left return, back to front
        th = -math.pi / 2 - math.pi * k / 9
        P.append((cl + RIM_R * math.cos(th), zc + RIM_R * math.sin(th), math.cos(th), math.sin(th)))
    return P


def _rim_vertex(p, y):
    """Plan point p at height y -> Godot (x, y, z). Front points take the face offset; crest tips above the
    slab top curl back toward -z."""
    x, z, nx, nz = p
    wf = max(0.0, nz)
    d = _rim_disp(x, y) * wf
    T = _rim_tine(x)
    curl = 0.0
    if y > RIM_TOP and T > 1e-6:
        curl = 0.5 * min(1.0, T / 3.0) * ((y - RIM_TOP) / T) ** 2 * wf
    return (x + nx * d, y, z + nz * d - curl)


def _rim_dn(g):
    """Signed distance of g from the rim face, positive toward the balcony (the room side)."""
    return g[2] - (RIM_FRONT + _rim_disp(g[0], g[1]))


def _rim_radius(g):
    x, y = g[0], g[1]
    return max(0.0, min(comb_patch.MAX_R, y + 1.0, 3.0 - y, x - 104.6, 130.4 - x))


def _rim_flows():
    flows = []
    for y, x0, x1, n in ((0.4, 105.0, 130.0, 14), (1.9, 106.5, 129.0, 10)):
        flow = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            origin = rooms._blender((x, y, RIM_FRONT + 2.0))      # start in the balcony air
            direction = rooms._blender((0.0, 0.0, -1.0))          # ray runs into the face
            flow.append((origin, direction, math.sin(math.pi * i / n)))
        flows.append(flow)
    return flows


def _build_rim():
    P = _rim_plan()
    K = len(P)
    bm = bmesh.new()
    V = []
    tops, front_pts = [], []
    for p in P:
        top = RIM_TOP + _rim_tine(p[0])
        col = []
        for j in range(RIM_NY):
            y = RIM_FLOOR + (top - RIM_FLOOR) * j / (RIM_NY - 1)
            g = _rim_vertex(p, y)
            col.append(bm.verts.new(rooms._blender(g)))
            if j == RIM_NY - 1:
                tops.append(g)
            if p[3] == 1.0 and y < 0.0:
                front_pts.append(g)
        V.append(col)
    for k in range(K):
        k2 = (k + 1) % K
        for j in range(RIM_NY - 1):
            try:
                bm.faces.new((V[k][j], V[k2][j], V[k2][j + 1], V[k][j + 1]))
            except ValueError:
                pass
    for ring in ([V[k][0] for k in range(K)], [V[k][-1] for k in range(K)]):   # floor and crest caps
        bmesh.ops.triangulate(bm, faces=[bm.faces.new(ring)])
    # outward normals: flip everything if the loop came out inside-out
    cen = rooms._blender((117.5, 0.5, -40.6))
    score = sum(f.normal.dot(f.calc_center_median() - cen) for f in bm.faces)
    if score < 0.0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    for f in bm.faces:
        g = comb_patch.to_g(f.calc_center_median())
        rib = (f.normal.z < 0.5 and g[2] > RIM_FRONT - 0.5 and -2.5 < g[1] < RIM_TOP
               and any(abs(g[0] - xr) < 0.3 for xr in RIM_RIBS))
        f.material_index = 1 if rib else 0
        f.smooth = True
    print("MEMBRANE part_rim tris %d (%d plan points, %d rows)" % (_tris(bm), K, RIM_NY))
    return bm, tops, front_pts


def _build_rim_model():
    bm, tops, front_pts = _build_rim()

    # self-check on final positions (Godot coordinates)
    worst = 0.0
    for p in (comb_patch.to_g(v.co) for v in bm.verts):
        if p[1] < 0.0:
            d = _box_dist(p, RIM_BOX[0], RIM_BOX[1])
            worst = max(worst, d)
            assert d <= BAND + TOL, "part_rim: vertex %s is %.3f from collision below y=0" % (p, d)
    for g in front_pts:
        off = g[2] - RIM_FRONT
        assert -TOL <= off <= BAND + TOL, "part_rim: face offset %.3f at %s below y=0 (limit %.2f)" % (off, g, BAND)
    crest = [g[1] for g in tops]
    assert min(crest) >= RIM_TOP - TOL, "part_rim: crest dips below y=%.1f (%.3f)" % (RIM_TOP, min(crest))
    assert max(crest) <= RIM_CROWN_MAX + TOL, "part_rim: crest rises above %.1f (%.3f)" % (RIM_CROWN_MAX, max(crest))
    assert max(crest) >= RIM_TOP + 0.5, "part_rim: no tine reaches 0.5 m above y=%.1f" % RIM_TOP
    max_off = max(g[2] - RIM_FRONT for g in front_pts)
    print("SELFCHECK part_rim: band worst distance below y=0 is %.3f (limit %.2f), face offset max %.3f, "
          "crest %.2f..%.2f above y=%.1f" % (worst, BAND, max_off, min(crest) - RIM_TOP,
                                             max(crest) - RIM_TOP, RIM_TOP))

    # comb patches on the face, between y -1 and 3
    bm.normal_update()
    pbm, pst = comb_patch.build_flows(bm, "part_rim_comb", _rim_flows(), _rim_radius, _rim_dn,
                                      3.5, 0.3, RIM_COMB_BUDGET)
    for v in pbm.verts:
        g = comb_patch.to_g(v.co)
        assert -1.5 <= g[1] <= 3.6 and RIM_BOX[0][0] < g[0] < RIM_BOX[1][0], "part_rim: comb patch at %s" % (g,)
    print("TRIS part_rim membrane %d, comb %d" % (_tris(bm), pst["tris"]))
    membrane = _finish("part_rim", bm, ["carapace", "carapace_dull"])
    if not pbm.faces:   # ponytail: comb places nothing on this rim (mound tops overshoot the 0.3 band); skipped
        return [membrane]
    patches = comb_patch.make_object("part_rim_comb", pbm)
    return [membrane, patches]


def build(args):
    name = args[0] if args else "part_guild"
    if name == "part_guild":
        return _build_guild()
    if name == "part_vault":
        return _build_vault()
    if name == "part_rim":
        return _build_rim_model()
    raise SystemExit("partitions.py: unknown part %r (part_guild, part_vault or part_rim)" % name)
