"""Paint wing gallery fittings: real museum kit, not painterly. Clean, precise, bevelled edges (bevel
applied, 2-3 segments), proper UVs, smooth shading with sharp creases marked by angle.
One script, selected by args[0]. Run through tools/blender_build.sh (wings/paint/tools/build_gallery.sh
builds them all).
Blender: +Z up, 1 unit = 1 m, origin at base centre on the floor unless stated. Material names are the
contract (Godot swaps them): r_oak r_leather r_brass r_velvet r_plaster r_marble r_gilt."""
import math

import bmesh
from mathutils import Matrix

import kit

TAU = 2 * math.pi


# --- helpers ------------------------------------------------------------------------------------

def _uv_box(ob):
    """Planar UVs, one projection per face along its dominant normal axis (1 UV unit = 1 m)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        ax = max(range(3), key=lambda i: abs(f.normal[i]))
        a, b = [i for i in range(3) if i != ax]
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co[a], lp.vert.co[b])
    bm.to_mesh(me)
    bm.free()
    return ob


def _uv_turn(ob):
    """Cylindrical UVs for a lathe along local Z: u = around the axis, v = along it. Faces that cross
    the seam are unwrapped past 1 so they do not smear across the texture."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        us = [(math.atan2(lp.vert.co.y, lp.vert.co.x) / TAU) % 1.0 for lp in f.loops]
        if max(us) - min(us) > 0.5:
            us = [u + 1.0 if u < 0.5 else u for u in us]
        for lp, u in zip(f.loops, us):
            lp[uv].uv = (u, lp.vert.co.z)
    bm.to_mesh(me)
    bm.free()
    return ob


def _bm_obj(name, bm, mat, smooth=35.0):
    """Finish a bmesh: fix normals, make an object with hard creases past `smooth` degrees, planar UVs."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _uv_box(kit._obj(name, bm, mat, smooth))


def _slab(name, size, loc, mat, bevel=0.01, segs=3):
    """A bevelled box (bevel applied, `segs` segments), centred at loc."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segs, affect="EDGES", profile=0.5)
    bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
    return _bm_obj(name, bm, mat, 35.0)


def _turn(name, profile, mat, segments=24, loc=(0, 0, 0), rot=(0, 0, 0)):
    """A turned part: profile (radius, z) bottom -> top around local Z, then placed."""
    ob = kit.lathe(name, profile, segments=segments, mat=mat, smooth_angle=40.0, cap=True)
    ob.location = loc
    ob.rotation_euler = rot
    return _uv_turn(ob)


def _rod(name, length, radius, mat, loc, rot):
    """A turned rod of `length` along local Z with two small beads and square-ish ends."""
    prof = [(radius, 0.0), (radius + 0.006, 0.03), (radius, 0.06), (radius, length - 0.06),
            (radius + 0.006, length - 0.03), (radius, length)]
    return _turn(name, prof, mat, 16, loc, rot)


def _sweep_x(bm, loop, x0, x1):
    """A closed (y, z) loop extruded along X from x0 to x1, both ends capped. A loop that runs down the
    wall (y = 0) makes a wall-backed moulding."""
    rings = [[bm.verts.new((x, y, z)) for y, z in loop] for x in (x0, x1)]
    n = len(loop)
    for j in range(n):
        k = (j + 1) % n
        bm.faces.new((rings[0][j], rings[1][j], rings[1][k], rings[0][k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])


def _add_box(bm, size, loc):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=ret["verts"])
    bmesh.ops.translate(bm, vec=loc, verts=ret["verts"])


def _bez(p0, p1, p2, p3, n):
    """Cubic bezier in (y, z), n samples (p0 excluded, p3 included)."""
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k] for k in (0, 1)))
    return out


def _cubic3(p0, p1, p2, p3, n):
    """Cubic bezier in 3D, n + 1 samples including both ends."""
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append(tuple(u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k] for k in range(3)))
    return out


def _catenary_a(length, sag):
    """Catenary parameter a: sag = a (cosh(L / 2a) - 1). Solved by bisection on t = L / 2a."""
    k = 2 * sag / length
    lo, hi = 1e-3, 3.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if math.cosh(mid) - 1 - k * mid < 0:
            lo = mid
        else:
            hi = mid
    return length / (2 * lo)


def _domes(name, pts, r, z, mat):
    """Flattened icosphere studs (leather buttons) at (x, y) on height z."""
    bm = bmesh.new()
    for x, y in pts:
        ret = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
        bmesh.ops.scale(bm, vec=(1.0, 1.0, 0.5), verts=ret["verts"])
        bmesh.ops.translate(bm, vec=(x, y, z), verts=ret["verts"])
    return _bm_obj(name, bm, mat, 40.0)


# --- 1. bench -----------------------------------------------------------------------------------

LEG = [(0.028, 0.0), (0.034, 0.012), (0.026, 0.03), (0.018, 0.05), (0.018, 0.1), (0.026, 0.15),
       (0.016, 0.2), (0.016, 0.26), (0.024, 0.3), (0.034, 0.32), (0.032, 0.34), (0.02, 0.36)]


def B_bench():
    out = []
    # oak seat board, then the buttoned leather cushion on top (seat height 0.46)
    out.append(_slab("bench_board", (2.6, 0.55, 0.04), (0, 0, 0.38), "r_oak", bevel=0.008))
    out.append(_slab("bench_cushion", (2.5, 0.5, 0.06), (0, 0, 0.43), "r_leather", bevel=0.02))
    pts = [(x, y) for x in (-0.9, -0.45, 0.0, 0.45, 0.9) for y in (-0.13, 0.0, 0.13)]
    out.append(_domes("bench_buttons", pts, 0.012, 0.46, "r_leather"))
    # turned legs at the four corners, then turned rails: two along X, two along Y at each end
    for x in (-1.15, 1.15):
        for y in (-0.2, 0.2):
            out.append(_turn("bench_leg", LEG, "r_oak", 16, loc=(x, y, 0.0)))
    for y in (-0.2, 0.2):
        out.append(_rod("bench_rail", 2.3, 0.02, "r_oak", (-1.15, y, 0.14), (0, math.pi / 2, 0)))
    for x in (-1.15, 1.15):
        out.append(_rod("bench_end_rail", 0.4, 0.02, "r_oak", (x, -0.2, 0.14), (-math.pi / 2, 0, 0)))
    return out


# --- 2. stanchion -------------------------------------------------------------------------------

def B_stanchion():
    out = []
    prof = [(0.13, 0.0), (0.152, 0.0), (0.16, 0.008), (0.16, 0.046), (0.152, 0.06), (0.12, 0.068),
            (0.05, 0.074), (0.03, 0.085), (0.02, 0.1)]
    prof += [(0.02, 0.27), (0.032, 0.29), (0.032, 0.31), (0.02, 0.33)]          # ring
    prof += [(0.02, 0.6), (0.032, 0.62), (0.032, 0.64), (0.02, 0.66)]           # ring
    prof += [(0.02, 0.8)]
    for i in range(1, 9):                                                       # urn / ball top
        a = 0.6 + (math.pi - 0.6) * i / 8
        prof.append((0.045 * math.sin(a), 0.86 - 0.045 * math.cos(a)))
    out.append(_turn("stanchion_post", prof, "r_brass", 20))
    # eye on the ball top for the rope clip (ring in the XZ plane)
    hook = kit.torus("stanchion_hook", 0.03, 0.007, seg=20, rseg=8, mat="r_brass", loc=(0, 0, 0.935), rot=(math.pi / 2, 0, 0))
    out.append(_uv_box(hook))
    return out


# --- 3. rope ------------------------------------------------------------------------------------

def B_rope():
    out = []
    length, sag = 2.4, 0.22
    a = _catenary_a(length, sag)
    n = 48
    pts = [(length * i / n, 0.0, a * (math.cosh((length * i / n - length / 2) / a) - math.cosh(length / (2 * a))))
           for i in range(n + 1)]
    out.append(_uv_box(kit.tube("velvet_rope", pts, 0.0175, sides=10, mat="r_velvet")))
    # brass sleeves over each end, along +X from the hook
    clip = [(0.02, 0.0), (0.025, 0.006), (0.025, 0.044), (0.02, 0.05)]
    out.append(_turn("rope_clip", clip, "r_brass", 20, loc=(0.0, 0, 0), rot=(0, math.pi / 2, 0)))
    out.append(_turn("rope_clip", clip, "r_brass", 20, loc=(length - 0.05, 0, 0), rot=(0, math.pi / 2, 0)))
    return out


# --- 4. picture light ---------------------------------------------------------------------------

def B_picture_light():
    out = []
    # back plate on the wall (wall is y = 0)
    out.append(_slab("pl_plate", (0.16, 0.012, 0.12), (0, 0.006, 0.0), "r_brass", bevel=0.004))
    # curved arm reaching 0.45 m out (+Y), ending in the hood's top
    pts = _cubic3((0, 0.012, 0.0), (0, 0.15, 0.09), (0, 0.30, 0.10), (0, 0.44, 0.06), 24)
    out.append(_uv_box(kit.tube("pl_arm", pts, 0.0085, sides=12, mat="r_brass")))
    # hood: a U-band shade 0.7 m wide along X, tilted to point down and back at the picture
    yc, zc, rot = 0.44, -0.01, math.radians(-20)
    ro, ri = 0.075, 0.064
    loop = [(ro * math.cos(math.pi * i / 12), ro * math.sin(math.pi * i / 12)) for i in range(13)]
    loop += [(ri * math.cos(math.pi * i / 12), ri * math.sin(math.pi * i / 12)) for i in range(12, -1, -1)]
    c, s = math.cos(rot), math.sin(rot)
    loop = [(yc + y * c - z * s, zc + y * s + z * c) for y, z in loop]
    bm = bmesh.new()
    _sweep_x(bm, loop, -0.35, 0.35)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.002, segments=2, affect="EDGES")
    out.append(_bm_obj("pl_hood", bm, "r_brass", 35.0))
    return out


# --- 5. cornice ---------------------------------------------------------------------------------

def B_cornice():
    """Profile in (y out from the wall, z down from the top back edge). Runs 10 m along +X."""
    prof = [(0.0, 0.0)]
    prof += _bez((0.0, 0.0), (0.05, 0.0), (0.10, -0.01), (0.12, -0.05), 5)       # cove under the ceiling
    prof += [(0.15, -0.07), (0.40, -0.07)]                                       # corona top
    prof += _bez((0.40, -0.07), (0.47, -0.07), (0.50, -0.10), (0.50, -0.15), 4)  # round over to fascia
    prof += [(0.50, -0.20)]                                                      # fascia
    prof += _bez((0.50, -0.20), (0.50, -0.23), (0.46, -0.24), (0.44, -0.25), 3)  # ovolo under the corona
    prof += [(0.20, -0.26)]                                                      # soffit (dentils hang here)
    prof += [(0.20, -0.40)]                                                      # frieze, set back
    prof += [(0.36, -0.42)]
    prof += _bez((0.36, -0.42), (0.36, -0.48), (0.30, -0.50), (0.30, -0.54), 4)  # base ogee
    prof += _bez((0.30, -0.54), (0.30, -0.58), (0.34, -0.60), (0.36, -0.60), 3)  # base fillet
    prof += [(0.0, -0.60)]                                                       # base meets the wall
    bm = bmesh.new()
    _sweep_x(bm, prof, 0.0, 10.0)
    for i in range(83):                                                          # dentils under the corona
        _add_box(bm, (0.06, 0.08, 0.06), (0.09 + i * 0.12, 0.40, -0.29))
    return [_bm_obj("cornice", bm, "r_plaster", 35.0)]


# --- 6. dado and skirting -----------------------------------------------------------------------

DADO = [(0.0, 0.0), (0.045, 0.0), (0.06, -0.015), (0.06, -0.035), (0.052, -0.04), (0.06, -0.045),
        (0.06, -0.10), (0.05, -0.12), (0.0, -0.12)]
SKIRT = [(0.0, 0.0), (0.03, 0.0), (0.04, -0.01), (0.04, -0.04), (0.035, -0.05), (0.04, -0.06),
         (0.04, -0.30), (0.0, -0.30)]


def _moulding(name, prof, height, mat):
    """Floor-standing moulding: the profile's top is at z = 0, shifted so the base sits on z = 0."""
    bm = bmesh.new()
    _sweep_x(bm, [(y, z + height) for y, z in prof], 0.0, 10.0)
    return _bm_obj(name, bm, mat, 35.0)


def B_dado():
    return [_moulding("dado", DADO, 0.12, "r_oak")]


def B_skirting():
    return [_moulding("skirting", SKIRT, 0.30, "r_oak")]


# --- 7. pedestal --------------------------------------------------------------------------------

def B_pedestal():
    out = []
    out.append(_slab("pedestal_plinth", (0.5, 0.5, 0.1), (0, 0, 0.05), "r_marble", bevel=0.012))
    out.append(_slab("pedestal_base_moulding", (0.46, 0.46, 0.04), (0, 0, 0.12), "r_marble", bevel=0.012))
    out.append(_slab("pedestal_die", (0.42, 0.42, 0.82), (0, 0, 0.55), "r_marble", bevel=0.008))
    out.append(_slab("pedestal_cap_moulding", (0.46, 0.46, 0.04), (0, 0, 0.98), "r_marble", bevel=0.012))
    out.append(_slab("pedestal_cap", (0.5, 0.5, 0.1), (0, 0, 1.05), "r_marble", bevel=0.012))
    return out


# --- 8. ceiling coffer --------------------------------------------------------------------------

def B_coffer():
    """One 1 x 1 m coffer of a plaster ceiling, origin at its centre on the ceiling plane, hanging down -Z.
    Half a beam on each side (neighbours complete it), a stepped moulding into the sunk panel, a gilt bead
    round the panel and a gilt rosette in its middle."""
    bm = bmesh.new()
    for s in (-1, 1):
        for ax in (0, 1):
            def at(u, v, z):  # u across the edge (into the coffer), v along it
                c = s * (0.5 - u)
                return (c, v, z) if ax == 0 else (v, c, z)
            for (u0, u1, z0) in ((0.0, 0.07, -0.16), (0.07, 0.11, -0.11), (0.11, 0.14, -0.06)):
                size = (u1 - u0, 1.0 - 2 * u0 if u0 else 1.0, -z0)
                cx = at((u0 + u1) / 2, 0.0, z0 / 2)
                _add_box(bm, size if ax == 0 else (size[1], size[0], size[2]), cx)
    plaster = _bm_obj("coffer", bm, "r_plaster", 35.0)
    gb = bmesh.new()
    for s in (-1, 1):
        _add_box(gb, (0.74, 0.018, 0.018), (0, s * 0.36, -0.05))
        _add_box(gb, (0.018, 0.74, 0.018), (s * 0.36, 0, -0.05))
    gilt = _bm_obj("coffer_bead", gb, "r_gilt", 35.0)
    rose = _turn("rosette", [(0.0, 0.0), (0.09, 0.0), (0.1, -0.015), (0.07, -0.03), (0.075, -0.045), (0.03, -0.06), (0.0, -0.065)], "r_gilt", 16)
    return [plaster, kit.join("coffer_gilt", [gilt, rose])]


# --- dispatch -----------------------------------------------------------------------------------

def build(args):
    fns = {"coffer": B_coffer, "bench": B_bench, "stanchion": B_stanchion, "rope": B_rope, "picture_light": B_picture_light,
           "cornice": B_cornice, "dado": B_dado, "skirting": B_skirting, "pedestal": B_pedestal}
    fn = fns.get(args[0]) if args else None
    if fn is None:
        raise SystemExit("unknown gallery piece: " + (args[0] if args else ""))
    fn()
