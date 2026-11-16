"""Walk rubble: the collapsed west walk of the Glass cloister. Five broken floor slabs hang in a void and fall
away in a staircase. Blender Z up, metres. Chunk k is centred at (0.55k, -2.0k, -0.7k), each about 1.9 x 1.1 x 0.4 m.
Each chunk is shattered into 2-3 pieces by crack polylines; the pieces are pushed apart and tilted so the cracks open.
Build with tools/blender_build.sh wings/glass/models/src/rubble.py wings/glass/models/walk_rubble.glb."""
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402

GLASS_FLOOR, RED, LEAD = "glass_floor", "glass_red_m", "lead"
HX, HY = 0.95, 0.55                              # half sizes of the nominal slab
TOPZ, MIDZ, BOTZ = 0.2, 0.0, -0.2                # the three layers, centred on the origin
STEP = Vector((0.55, -2.0, -0.7))                # offset from one chunk centre to the next
CORNERS = [(-HX, -HY), (HX, -HY), (HX, HY), (-HX, HY)]   # CCW; side s runs corner s -> corner s+1
PIECE_TILT = math.radians(6)


# ---------------------------------------------------------------- 2D helpers

def _area(p):
    n = len(p)
    return 0.5 * sum(p[i].x * p[(i + 1) % n].y - p[(i + 1) % n].x * p[i].y for i in range(n))


def _cross(o, a, b):
    return (a - o).x * (b - o).y - (a - o).y * (b - o).x


def _hit(a, b, c, d):
    return _cross(a, b, c) * _cross(a, b, d) < 0 and _cross(c, d, a) * _cross(c, d, b) < 0


def _simple(p):
    n = len(p)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _hit(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]):
                return False
    return True


def _ccw(ring, flags):
    """Reverse a ring (and its edge flags) if it runs clockwise."""
    if _area(ring) > 0:
        return ring, flags
    n = len(ring)
    return ring[::-1], [flags[(n - 2 - k) % n] for k in range(n)]


# ---------------------------------------------------------------- outline and cracks
# Edge flags: 'S' straight original edge (gets the lead came), 'B' broken, 'C' crack.

def _outline(rng):
    """Slab outline: one straight long side, three broken saw-tooth sides with 4-7 interior points each."""
    for _ in range(300):
        straight = rng.randrange(4)
        ring, flags = [], []
        for s in range(4):
            a, b = Vector(CORNERS[s]), Vector(CORNERS[(s + 1) % 4])
            out = Vector(((b - a).normalized().y, -(b - a).normalized().x))
            fl = "S" if s == straight else "B"
            ring.append(a)
            flags.append(fl)
            if s == straight:
                pts = [a + (b - a) * 0.5 + out * rng.uniform(-0.02, 0.02)]
            else:
                m = rng.randint(4, 7)
                ts = sorted(rng.uniform(0.08, 0.92) for _ in range(m))
                sign = rng.choice((-1, 1))
                pts = [a + (b - a) * t + out * (sign * (-1) ** i * rng.uniform(0.10, 0.30)) for i, t in enumerate(ts)]
            for p in pts:
                ring.append(p)
                flags.append(fl)
        if _simple(ring):
            break
    return ring, flags


def _cut(rng, ring, flags):
    """Split a ring along a zigzag crack between two boundary vertices. Returns two (ring, flags) or None."""
    n = len(ring)
    for _ in range(60):
        i = rng.randrange(n)
        j = (i + rng.randint(max(2, n // 3), max(2, (2 * n) // 3))) % n
        a, b = ring[i], ring[j]
        d = b - a
        perp = Vector((-d.y, d.x)).normalized()
        m = rng.randint(4, 6)
        crack = [a + d * ((k + 1) / (m + 1)) + perp * ((-1) ** k) * rng.uniform(0.04, 0.08) for k in range(m)]
        l1 = (j - i) % n + 1
        l2 = (i - j) % n + 1
        p1 = [ring[(i + q) % n] for q in range(l1)] + crack[::-1]
        f1 = [flags[(i + q) % n] for q in range(l1 - 1)] + ["C"] * (m + 1)
        p2 = [ring[(j + q) % n] for q in range(l2)] + crack
        f2 = [flags[(j + q) % n] for q in range(l2 - 1)] + ["C"] * (m + 1)
        if all(_simple(p) and abs(_area(p)) > 0.15 for p in (p1, p2)):
            return (p1, f1), (p2, f2)
    return None


# ---------------------------------------------------------------- piece geometry

def _piece(bm, ring, flags, rng, tilt):
    """One fractured piece: three stacked rings (top, middle, bottom), walls between them, a bevel on the
    straight edge, and a lead came strip on it. Material slots: 0 glass_floor, 1 glass_red_m, 2 lead."""
    n = len(ring)
    en = []
    for e in range(n):
        d = (ring[(e + 1) % n] - ring[e]).normalized()
        en.append(Vector((d.y, -d.x)))
    T, M, B = [], [], []
    for i, p in enumerate(ring):
        free = flags[i - 1] != "S" and flags[i] != "S"     # vertices on the straight edge keep their xy
        nv = (en[i - 1] + en[i]).normalized() if free else Vector((0.0, 0.0))
        dm = rng.choice((-1, 1)) * rng.uniform(0.03, 0.12) if free else 0.0
        db = rng.choice((-1, 1)) * rng.uniform(0.03, 0.12) if free else 0.0
        T.append(bm.verts.new((p.x, p.y, TOPZ)))
        M.append(bm.verts.new((p.x + nv.x * dm, p.y + nv.y * dm, MIDZ)))
        B.append(bm.verts.new((p.x + nv.x * db, p.y + nv.y * db, BOTZ + tilt[0] * p.x + tilt[1] * p.y)))

    before = set(bm.faces)
    bm.faces.new(T)
    bm.faces.new(B[::-1])
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((T[i], T[j], M[j], M[i]))
        bm.faces.new((M[i], M[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(set(bm.faces) - before))

    # 2-segment bevel on the straight top edge so it catches light
    edges = [e for i in range(n) if flags[i] == "S" for e in [bm.edges.get((T[i], T[(i + 1) % n]))] if e]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=0.02, segments=2, affect="EDGES")
    new = list(set(bm.faces) - before)
    bmesh.ops.triangulate(bm, faces=new)
    new = list(set(bm.faces) - before)
    bmesh.ops.recalc_face_normals(bm, faces=new)
    for f in new:                                    # top and bevels glass_floor, sides and bottom glass_red_m
        f.material_index = 0 if f.normal.z > 0.3 else 1

    # lead came strip on the straight edge: 0.04 wide, 0.03 tall, sitting on the top face
    for i in range(n):
        if flags[i] != "S":
            continue
        a, b = ring[i], ring[(i + 1) % n]
        seen = set(bm.faces)
        res = bmesh.ops.create_cube(bm, size=1.0)
        vs = res["verts"]
        bmesh.ops.scale(bm, vec=((b - a).length, 0.04, 0.03), verts=vs)
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.atan2(b.y - a.y, b.x - a.x), 3, "Z"), verts=vs)
        mid = (a + b) / 2
        bmesh.ops.translate(bm, vec=(mid.x, mid.y, TOPZ + 0.015), verts=vs)
        for f in set(bm.faces) - seen:
            f.material_index = 2


def _chunk(k):
    rng = random.Random(100 + k)
    ring, flags = _outline(rng)
    tilt = (rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04))

    pieces = [(ring, flags)]
    for _ in range(rng.choice((1, 2))):              # one or two cracks
        big = max(range(len(pieces)), key=lambda q: abs(_area(pieces[q][0])))
        cut = _cut(rng, *pieces[big])
        if cut:
            pieces[big:big + 1] = list(cut)

    bm = bmesh.new()
    for pring, pflags in pieces:
        pring, pflags = _ccw(pring, pflags)
        before = set(bm.verts)
        _piece(bm, pring, pflags, rng, tilt)
        new = list(set(bm.verts) - before)
        # open the cracks: push each piece away from the chunk centre, tilt it a little and let it drop
        cp = sum(pring, Vector((0.0, 0.0))) / len(pring)
        gap = (cp.normalized() if cp.length > 1e-6 else Vector((0.0, 0.0))) * rng.uniform(0.012, 0.02)
        c3 = Vector((cp.x, cp.y, 0.0))
        R = Matrix.Rotation(rng.uniform(-PIECE_TILT, PIECE_TILT), 4, "X") @ Matrix.Rotation(rng.uniform(-PIECE_TILT, PIECE_TILT), 4, "Y")
        drop = Vector((gap.x, gap.y, -rng.uniform(0.0, 0.08)))
        bmesh.ops.transform(bm, matrix=Matrix.Translation(drop) @ Matrix.Translation(c3) @ R @ Matrix.Translation(-c3), verts=new)

    # keep the chunk centred on the origin, then shards, then the chunk's own tilt and its place on the stair
    c = sum((v.co for v in bm.verts), Vector((0.0, 0.0, 0.0))) / len(bm.verts)
    bmesh.ops.translate(bm, vec=-c, verts=list(bm.verts))
    for _ in range(rng.randint(3, 5)):
        size = rng.uniform(0.1, 0.25)
        if rng.random() < 0.5:                       # hanging below the slab
            ctr = Vector((rng.uniform(-0.7, 0.7), rng.uniform(-0.4, 0.4), BOTZ - rng.uniform(0.05, 0.4)))
        else:                                        # lying loose just off the slab
            ctr = Vector((rng.choice((-1, 1)) * rng.uniform(HX + 0.1, HX + 0.45), rng.uniform(-0.8, 0.8), BOTZ - rng.uniform(0.0, 0.1)))
        sv = [bm.verts.new(ctr + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * (size / 2))
              for _ in range(4)]
        for tri in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            bm.faces.new([sv[q] for q in tri]).material_index = 1

    amp = math.radians(10 + 2 * k)                   # chunk 4 droops most, up to 18 degrees
    R = (Matrix.Rotation(rng.uniform(-amp, amp), 4, "X") @ Matrix.Rotation(rng.uniform(-amp, amp), 4, "Y")
         @ Matrix.Rotation(rng.uniform(-math.radians(8), math.radians(8)), 4, "Z"))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(STEP * k) @ R, verts=list(bm.verts))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    ob = kit._obj(f"walk_rubble_{k}", bm, None, 30.0)
    for m in (GLASS_FLOOR, RED, LEAD):              # slot order matches the material_index values above
        ob.data.materials.append(kit.material(m))
    return ob


def build(args):
    kit.join("walk_rubble", [_chunk(k) for k in range(5)])
