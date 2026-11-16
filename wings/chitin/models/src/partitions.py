"""Partition membranes for the Chitin Court Foundry: visual-only models that hide the room's interior box walls.

Build: tools/blender_build.sh wings/chitin/models/src/partitions.py wings/chitin/models/<part>.glb <part>
  <part> is part_guild or part_vault. Both are visual only (no collision suffixes): the collision boxes
  stay as they are and these meshes sit on the outside of them.

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


def build(args):
    name = args[0] if args else "part_guild"
    if name == "part_guild":
        return _build_guild()
    if name == "part_vault":
        return _build_vault()
    raise SystemExit("partitions.py: unknown part %r (part_guild or part_vault)" % name)
