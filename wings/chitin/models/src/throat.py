"""Chitin Court hive shaft (shell_shaft): a round, ribbed, organic throat rising from the floor to the light.

Built from shells.json "throat" (Godot world coords; Blender = (x, -z, y)). The wall is a Voronoi plate
field that bulges up to `bulge` m into the shaft; a shallow spiral of raised ribs (one turn per `turn_drop`
m, evenly phased) winds it with dull collar bands; the top curls outward into a rolled lip; the west stair
opening gets a carapace arch. Comb is NOT painted on the wall: comb patches (comb_patch.py) are separate
blob meshes placed on the finished wall, object "shell_shaft_comb". Normals face into the shaft.

Build: tools/blender_build.sh wings/chitin/models/src/throat.py wings/chitin/models/shell_shaft.glb shell_shaft
       tools/blender_build.sh wings/chitin/models/src/throat.py wings/chitin/models/shell_shaft_comb.glb shell_shaft_comb
(the comb model is its own file: same deterministic shell, comb patches only)
"""
import bisect
import json
import math
import os
import random
import sys
import zlib

import bmesh
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402
import comb_patch  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "shells.json")))["throat"]
FLOOR = float(CFG["floor"])
X0, X1 = float(CFG["x"][0]), float(CFG["x"][1])
Z0, Z1 = float(CFG["z"][0]), float(CFG["z"][1])
RC = float(CFG["corner"])
ROLL = float(CFG["lip"]) / 2.0  # rolled lip: a half-round of radius lip/2, so it reaches `lip` m outward
BULGE = float(CFG["bulge"])
NRIB = int(CFG["spiral_ribs"])
DROP = float(CFG["turn_drop"])
SIDE = {"W": float(CFG["tops"]["west"]), "N": float(CFG["tops"]["north"]),
        "E": float(CFG["tops"]["east"]), "S": float(CFG["tops"]["south"])}
TOP_MIN = min(SIDE.values())
OX0, OY0, OZ0, OX1, OY1, OZ1 = (float(v) for v in CFG["openings"][0])
OZC = (OZ0 + OZ1) / 2.0
OR = (OZ1 - OZ0) / 2.0
OYC = OY1 - OR  # arch spring line
Y_BOT = FLOOR + 0.6  # floor fillet top; the wall starts here
FIL_W = 0.3  # fillet reaches 0.3 m into the shaft, flush with the floor there
BLEND = 3.0  # half window (m) of the top blend around each corner
RIB_OFFS = (-0.35, -0.175, 0.0, 0.175, 0.35)
RIB_HALF = 0.35
RIB_STEP = 1.0
SEAM = 0.9  # Voronoi seam blend width (m)
CY = 4.0  # plate row height (m); plate columns are ~4 m along the perimeter
STEP = 0.02  # dense plan sampling (m)
GRID_S = 1.1  # wall grid along the perimeter (m): ~50k shell tris, under SHELL_CAP
NV = 70  # wall rows per column
NA = 8  # roll segments
NF = 4  # fillet segments
RN = 8  # opening lip ring sides
SHELL_CAP = 58500  # shell model alone (MOSR_MAX_TRIS is 60000)
TOTAL_CAP = 58500  # comb model alone
MATS = ["carapace", "carapace_dull"]
CORNERS = (("NW", "W", "N"), ("NE", "N", "E"), ("SE", "E", "S"), ("SW", "S", "W"))


def _hash(a, b):
    v = math.sin(a * 127.1 + b * 311.7) * 43758.5453
    return v - math.floor(v)


def _in_open(p):
    """True inside the stair opening (west wall), so faces there are deleted."""
    x, y, z = p
    if abs(x - X0) > 1.5 or y < OY0 - 0.01 or y > OY1 + 0.01:
        return False
    if OZ0 <= z <= OZ1 and y <= OYC:
        return True
    return y > OYC and (z - OZC) ** 2 + (y - OYC) ** 2 <= OR * OR


def _perimeter():
    """Dense ccw plan of the collision rect (corner radius RC): (x, z, inward nx, nz, seg) and arc-length s."""
    pts, first = [], {}

    def line(a, b, n, seg):
        k = max(1, int(round(math.hypot(b[0] - a[0], b[1] - a[1]) / STEP)))
        for i in range(k):
            t = i / k
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, n[0], n[1], seg))

    def arc(c, a0, a1, seg):
        first[seg] = len(pts)
        k = max(2, int(round(abs(a1 - a0) * RC / STEP)))
        for i in range(k):
            a = a0 + (a1 - a0) * i / k
            pts.append((c[0] + RC * math.cos(a), c[1] + RC * math.sin(a), -math.cos(a), -math.sin(a), seg))

    line((X0, Z0 + RC), (X0, Z1 - RC), (1.0, 0.0), "W")
    arc((X0 + RC, Z1 - RC), math.pi, math.pi / 2, "NW")
    line((X0 + RC, Z1), (X1 - RC, Z1), (0.0, -1.0), "N")
    arc((X1 - RC, Z1 - RC), math.pi / 2, 0.0, "NE")
    line((X1, Z1 - RC), (X1, Z0 + RC), (-1.0, 0.0), "E")
    arc((X1 - RC, Z0 + RC), 0.0, -math.pi / 2, "SE")
    line((X1 - RC, Z0), (X0 + RC, Z0), (0.0, 1.0), "S")
    arc((X0 + RC, Z0 + RC), -math.pi / 2, -math.pi, "SW")
    S = [0.0]
    for i in range(1, len(pts)):
        S.append(S[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    P = S[-1] + math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    return pts, S, P, first


def _dn(g):
    """Signed inward distance from the rounded collision rect (positive into the shaft)."""
    cx, cz = (X0 + X1) / 2.0, (Z0 + Z1) / 2.0
    hx, hz = (X1 - X0) / 2.0, (Z1 - Z0) / 2.0
    qx = abs(g[0] - cx) - (hx - RC)
    qz = abs(g[2] - cz) - (hz - RC)
    d = math.hypot(max(qx, 0.0), max(qz, 0.0)) + min(max(qx, qz), 0.0) - RC
    return -d


def _tines(P):
    """Chitin tines on the top edge: (arc s, height m), one every 11-17 m, deterministic."""
    out, s, i = [], 0.0, 0
    while True:
        s += 11.0 + 6.0 * _hash(i + 0.5, 3.3)
        if s >= P:
            return out
        out.append((s, 1.2 * (0.7 + 0.6 * _hash(i + 0.5, 8.1))))
        i += 1


def _crest(s, P, tines):
    """Organic raise of the top edge at arc length s (m, always >= 0), periodic in P."""
    raw = 0.0
    for lam, amp, ph in ((23.0, 1.4, 0.6), (9.0, 0.7, 2.1), (3.7, 0.25, 4.0)):
        k = max(1, round(P / lam))  # integer count of waves round the perimeter: no seam
        raw += amp * math.sin(2 * math.pi * k * s / P + ph)
    crest = 2.6 * (raw + 2.35) / 4.7  # shifted so min is 0 and max is 2.6 m (sum of amplitudes is 2.35)
    for c, h in tines:
        ds = (s - c + P / 2) % P - P / 2
        crest += h * math.exp(-((ds / 0.64) ** 2))  # ~1.5 m wide at half height
    return crest


class _Throat:
    def __init__(self):
        pts, self.S, self.P, first = _perimeter()
        self.tines = _tines(self.P)
        # top height: side values, blended smoothly over +-BLEND m around each corner (smoothstep)
        mids = {c: self.S[first[c]] + RC * math.pi / 4 for c, _, _ in CORNERS}
        self.FR = []  # (x, z, inward nx, nz, top y) per dense sample
        for (x, z, nx, nz, seg), s in zip(pts, self.S):
            T = SIDE.get(seg)
            for name, a, b in CORNERS:
                off = (s - mids[name] + self.P / 2) % self.P - self.P / 2
                if abs(off) <= BLEND:
                    u = (off + BLEND) / (2 * BLEND)
                    u = u * u * (3 - 2 * u)
                    T = SIDE[a] + (SIDE[b] - SIDE[a]) * u
                    break
            self.FR.append((x, z, nx, nz, T + _crest(s, self.P, self.tines)))
        self.ncol = 2 * max(2, int(round(self.P / 8.0)))  # even, so the row stagger wraps
        self.cs = self.P / self.ncol
        self.slope = DROP / self.P  # rib climb per metre of run
        self.phi = [k * self.P / NRIB for k in range(NRIB)]

    def fr(self, s):
        i = bisect.bisect_right(self.S, s % self.P) - 1
        return self.FR[max(0, i)]

    def _site(self, r, k):
        kk = k % self.ncol
        su = (k + 0.5 + 0.5 * (r % 2)) * self.cs + (_hash(r * 1.7 + 0.3, kk * 2.3 + 1.1) - 0.5) * 0.9 * self.cs
        sv = (r + 0.5 + (_hash(r * 3.1 + 2.2, kk * 0.7 + 5.5) - 0.5) * 0.8) * CY
        return su, sv

    def plate(self, s, v):
        """Overlapping plate dome at (s along perimeter, v above floor): 0 on seams, BULGE at centres,
        with each plate's free lower edge proud and its top tucked under the row above."""
        s %= self.P
        r0 = math.floor(v / CY)
        b1 = b2 = 1e9
        for r in (r0 - 1, r0, r0 + 1):
            kc = math.floor(s / self.cs - 0.5 - 0.5 * (r % 2))
            for k in range(kc - 1, kc + 3):
                su, sv = self._site(r, k)
                ds = (s - su + self.P / 2) % self.P - self.P / 2
                dd = math.hypot(ds, v - sv)
                if dd < b1:
                    b1, b2 = dd, b1
                elif dd < b2:
                    b2 = dd
        t = min(1.0, (b2 - b1) / SEAM)
        return BULGE * t * t * (3 - 2 * t) * (1.0 - 0.45 * (v / CY - r0))

    def build(self, comb):
        """comb=False: the shell model (shell_shaft). comb=True: the comb-patch model (shell_shaft_comb)."""
        P = self.P
        bm = bmesh.new()
        pos = {}
        recs = []  # (inward offset n, y, top) of every wall-side vertex, for the self-check

        def V(p):
            v = bm.verts.new((p[0], -p[2], p[1]))
            pos[v] = p
            return v

        def F(vs, tgt, mat, cut=True):
            c = [sum(pos[v][i] for v in vs) / len(vs) for i in range(3)]
            if cut and _in_open(c):
                return
            try:
                f = bm.faces.new(vs)
            except ValueError:
                return
            f.normal_update()
            if f.normal.dot(Vector((tgt[0], -tgt[2], tgt[1]))) < 0:
                f.normal_flip()
            f.material_index = mat

        def rec(p, fr):
            X, Z, NX, NZ, T = fr
            recs.append(((p[0] - X) * NX + (p[2] - Z) * NZ, p[1], T))

        # --- wall grid: plates
        ns = int(round(P / GRID_S))
        cols = []
        for i in range(ns):
            s = i * P / ns
            fr = self.fr(s)
            T = fr[4]
            ys = [Y_BOT + (T - Y_BOT) * j / NV for j in range(NV + 1)]
            cols.append((s, fr, ys))
        G = []
        for s, fr, ys in cols:
            X, Z, NX, NZ, T = fr
            gcol = []
            for y in ys:
                fade = min(1.0, max(0.0, (T - y) / 1.5)) * min(1.0, max(0.0, (y - Y_BOT) / 1.0))
                d = self.plate(s, y - FLOOR) * fade
                p = (X + NX * d, y, Z + NZ * d)
                gcol.append(V(p))
                rec(p, fr)
            G.append(gcol)
        for i in range(ns):
            i2 = (i + 1) % ns
            fr = cols[i][1]
            for j in range(NV):
                vs = [G[i][j], G[i2][j], G[i2][j + 1], G[i][j + 1]]
                F(vs, (fr[2], 0.0, fr[3]), 0)

        # --- rolled lip: a half-round curling outward over the top; its lower end sits exactly on the top
        L = []
        for i in range(ns):
            X, Z, NX, NZ, T = cols[i][1]
            row = [G[i][NV]]
            for k in range(1, NA + 1):
                a = math.pi * k / NA
                n = -ROLL + ROLL * math.cos(a)
                y = T + ROLL * math.sin(a)
                row.append(V((X + NX * n, y, Z + NZ * n)))
            L.append(row)
        for i in range(ns):
            i2 = (i + 1) % ns
            X, Z, NX, NZ, T = cols[i][1]
            for k in range(NA):
                am = math.pi * (k + 0.5) / NA
                nc = -ROLL + ROLL * math.cos(am)
                yc = T + ROLL * math.sin(am)
                tgt = (NX * (-ROLL - nc), T - yc, NZ * (-ROLL - nc))  # visible side faces the hollow
                F([L[i][k], L[i2][k], L[i2][k + 1], L[i][k + 1]], tgt, 0, cut=False)
            F([L[i][0], L[i2][0], L[i2][NA], L[i][NA]], (0.0, 1.0, 0.0), 0, cut=False)

        # --- floor fillet: flush with the floor 0.3 m in, rising to the wall at Y_BOT
        Fr = []
        for i in range(ns):
            X, Z, NX, NZ, T = cols[i][1]
            row = []
            for t in range(NF + 1):
                if t == NF:
                    row.append(G[i][0])
                    continue
                th = (math.pi / 2) * t / NF
                n = FIL_W * (1 - math.sin(th))
                y = FLOOR + 0.6 * (1 - math.cos(th))
                p = (X + NX * n, y, Z + NZ * n)
                row.append(V(p))
                rec(p, cols[i][1])
            Fr.append(row)
        for i in range(ns):
            i2 = (i + 1) % ns
            NX, NZ = cols[i][1][2], cols[i][1][3]
            for t in range(NF):
                F([Fr[i][t], Fr[i2][t], Fr[i2][t + 1], Fr[i][t + 1]], (NX, 1.0, NZ), 0)

        # --- spiral ribs: one turn per DROP m of descent, all the same way, evenly phased
        ps = self.slope / math.hypot(1.0, self.slope)  # rib perpendicular in (s, y): across-rib offsets
        pb = 1.0 / math.hypot(1.0, self.slope)
        for k in range(NRIB):
            ph = self.phi[k]
            rows = []
            tau = 0.0
            while True:
                s_c = (ph - tau) % P
                y_c = Y_BOT + tau * self.slope
                fc = self.fr(s_c)
                if y_c >= fc[4] - 1.6:
                    break
                row = []
                for off in RIB_OFFS:
                    s_p, y_p = s_c + off * ps, y_c + off * pb
                    fp = self.fr(s_p)
                    X, Z, NX, NZ, T = fp
                    g = math.sqrt(max(0.0, 1 - (off / RIB_HALF) ** 2))  # rounded crest, proud BULGE
                    raw = self.plate(s_p, y_p - FLOOR) * (1 - g) + BULGE * g
                    fade = min(1.0, max(0.0, (T - y_p) / 1.5)) * min(1.0, max(0.0, (y_p - Y_BOT) / 1.0))
                    d = raw * fade
                    p = (X + NX * d, y_p, Z + NZ * d)
                    row.append(V(p))
                    rec(p, fp)
                rows.append((fc, row))
                tau += RIB_STEP
            for j in range(len(rows) - 1):
                fc, row = rows[j]
                row2 = rows[j + 1][1]
                mat = 1 if j % 2 == 0 else 0  # every 2 m a dull collar band
                for q in range(len(RIB_OFFS) - 1):
                    F([row[q], row[q + 1], row2[q + 1], row2[q]], (fc[2], 0.0, fc[3]), mat)

        # --- west stair opening: rolled carapace arch, elliptical section 0.6 x 0.3 m, inside the wall face
        path = []
        for k in range(5):
            path.append((OZ0, FLOOR + (OYC - FLOOR) * k / 4.0))
        for k in range(1, 13):
            a = math.pi - math.pi * k / 12.0
            path.append((OZC + OR * math.cos(a), OYC + OR * math.sin(a)))
        for k in range(1, 5):
            path.append((OZ1, OYC - (OYC - FLOOR) * k / 4.0))
        path = [(X0 + 0.15, y, z) for z, y in path]
        ring_rows = []
        for k, p in enumerate(path):
            a, b = path[max(0, k - 1)], path[min(len(path) - 1, k + 1)]
            ty, tz = b[1] - a[1], b[2] - a[2]
            ln = math.hypot(ty, tz) or 1.0
            qy, qz = -tz / ln, ty / ln
            ring = []
            for m in range(RN):
                ph = 2 * math.pi * m / RN
                ring.append(V((p[0] + 0.15 * math.sin(ph), p[1] + 0.3 * math.cos(ph) * qy,
                               p[2] + 0.3 * math.cos(ph) * qz)))
            ring_rows.append(ring)
        for k in range(len(path) - 1):
            for m in range(RN):
                vs = [ring_rows[k][m], ring_rows[k][(m + 1) % RN], ring_rows[k + 1][(m + 1) % RN], ring_rows[k + 1][m]]
                c = [sum(pos[v][i] for v in vs) / 4.0 for i in range(3)]
                tgt = [c[i] - path[k][i] for i in range(3)]
                F(vs, tgt, 0, cut=False)

        # --- self-check (before any vertex merge; checks against the recorded positions)
        below = [(n, y) for n, y, T in recs if y < T - 1e-6]
        lo = min(n for n, _ in below)
        hi = max(n for n, _ in below)
        assert -0.05 <= lo and hi <= BULGE + 1e-6, ("wall outside collision band", lo, hi)
        top_err = max(abs(pos[G[i][NV]][1] - cols[i][1][4]) for i in range(ns))
        assert top_err < 1e-9, top_err
        for i in range(ns):
            X, Z, NX, NZ, _ = cols[i][1]
            p = pos[Fr[i][0]]
            assert abs(p[1] - FLOOR) < 1e-9 and abs((p[0] - X) * NX + (p[2] - Z) * NZ - FIL_W) < 1e-6, \
                "fillet not flush with the floor"
        ring_n = [v[0] - X0 for row in ring_rows for v in (pos[x] for x in row)]
        assert all(-1e-6 <= n <= 0.3 + 1e-6 for n in ring_n), "opening arch outside the wall band"
        print("SELF-CHECK shell_shaft: %d wall-side verts below top, inward offset in [%.3f, %.3f] "
              "(limit -0.05..%.2f); top rows exact (err %.1e); floor fillet flush; arch n in [%.2f, %.2f]"
              % (len(below), lo, hi, BULGE, top_err, min(ring_n), max(ring_n)))

        # --- cleanup: drop unused verts (cut faces), then count triangles
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        print("TRIS shell_shaft shell %d (cap %d)" % (tris, SHELL_CAP))
        assert tris <= SHELL_CAP, tris

        if not comb:
            ob = kit._obj("shell_shaft", bm, None, 60.0)
            for name in MATS:
                ob.data.materials.append(kit.material(name))
            return ob

        # --- comb flows: each runs 40-60 m along the wall between two spiral ribs (the rib crests sit at BULGE, so no
        # room for a mound there), from a random height near the top; blobs big at the core, sparse at the ends
        rng = random.Random(zlib.crc32(b"shell_shaft_comb flows") & 0xFFFFFFFF)
        cx, cz = (X0 + X1) / 2.0, (Z0 + Z1) / 2.0
        NS = 240
        flows = []
        for k in rng.sample(range(NRIB), rng.randint(3, 6)):
            tau_top = (rng.uniform(FLOOR + 14.0, TOP_MIN - 3.0) - Y_BOT) / self.slope
            run = rng.uniform(40.0, 60.0)
            flow = []
            for i in range(NS):
                t = i / (NS - 1.0)
                tau = tau_top - run * t             # run metres along the rib, descending
                X, Z = self.fr((self.phi[k] + self.P / (2.0 * NRIB) - tau) % self.P)[0:2]  # midway between ribs k, k+1
                y = Y_BOT + tau * self.slope
                size = math.sin(math.pi * (0.04 + 0.92 * t)) ** 0.6
                flow.append((Vector((cx, -cz, y)), Vector((X - cx, -(Z - cz), 0.0)), size))
            flows.append(flow)

        def radius(g):
            """Largest blob at g (Godot): 0 near the floor, the top rim and the stair arch."""
            y = g[1]
            if y < FLOOR + 1.0 or y > TOP_MIN - 1.0:
                return 0.0
            if abs(g[0] - X0) < 2.0 and OY0 - 1.2 < y < OY1 + 1.2 and abs(g[2] - OZC) < OR + 1.2:
                return 0.0  # keep patches off the stair arch
            return min(comb_patch.MAX_R, TOP_MIN - 0.4 - y, y - FLOOR - 1.0)

        pbm, pst = comb_patch.build_flows(bm, "shell_shaft_comb", flows, radius, _dn, TOP_MIN, BULGE,
                                          TOTAL_CAP, cheap=True)
        bm.free()
        print("TRIS shell_shaft_comb %d (cap 60000, budget %d)" % (pst["tris"], TOTAL_CAP))
        assert pst["tris"] <= 60000, pst["tris"]
        return comb_patch.make_object("shell_shaft_comb", pbm)


def B_shell_shaft():
    return _Throat().build(False)


def B_shell_shaft_comb():
    return _Throat().build(True)


def build(args):
    name = args[0] if args else "shell_shaft"
    fn = globals().get("B_" + name)
    if fn is None:
        raise SystemExit("unknown throat piece: " + name)
    fn()
