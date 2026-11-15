"""Clay wing villagers, hand-built in plasticine: a fat little figure with a big head, facing +Y.
B_villager(variant) builds one of five: a praying, b in a red dress (arms up), c with a waistcoat, a
lantern and a cap, d a stooped old one with a stick, e a child at 0.75 scale. Materials are the contract
(see wings/clay/tools/make_materials.py). Imported into props.py by star-import."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
import sculpt as S  # noqa: E402
from mathutils import Vector  # noqa: E402

__all__ = ["B_villager"]

_DEPTH = 0.78  # bodies are squashed front to back: wider than deep
_HZ = 1.3      # head centre height
_HR = 0.19     # head radius

# (radius, z) profiles, bottom to top: trunk, skirt (b), robe (d)
_TORSO = [(0.0, 0.55), (0.25, 0.56), (0.27, 0.7), (0.25, 0.9), (0.22, 1.05), (0.18, 1.14), (0.12, 1.2), (0.0, 1.21)]
_SKIRT = [(0.0, 0.2), (0.36, 0.2), (0.33, 0.45), (0.27, 0.7), (0.25, 0.9), (0.22, 1.05), (0.18, 1.14), (0.12, 1.2), (0.0, 1.21)]
_ROBE = [(0.0, 0.1), (0.2, 0.1), (0.26, 0.3), (0.3, 0.6), (0.27, 0.8), (0.25, 0.9), (0.22, 1.05), (0.18, 1.14), (0.12, 1.2), (0.0, 1.21)]


def _prof_r(prof, z):
    """Radius of a (radius, z) profile at height z."""
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if z0 <= z <= z1:
            if z1 - z0 < 1e-9:  # flat step (a hem or a robe's floor): take the wider radius
                return max(r0, r1)
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 0.0


def _ring(prof, z, n, grow=0.0):
    """Closed loop of points round the body at height z (for belts, collars, scarves)."""
    r = _prof_r(prof, z) + grow
    return [(r * math.cos(2 * math.pi * k / n), r * _DEPTH * math.sin(2 * math.pi * k / n), z) for k in range(n + 1)]


def _at(ob, loc):
    for vtx in ob.data.vertices:
        vtx.co += Vector(loc)
    return ob


def _trunk(name, prof, mat, sd, z0=None, z1=None, grow=0.0):
    """A lathe body from a profile, optionally clipped to z0..z1, squashed front to back."""
    z0 = prof[0][1] if z0 is None else z0
    z1 = prof[-1][1] if z1 is None else z1
    pts = [(_prof_r(prof, z0) + grow, z0)] + [(r + grow, z) for r, z in prof if z0 < z < z1] + [(_prof_r(prof, z1) + grow, z1)]
    ob = S.lathe(name, pts, mat=mat, seed=sd, segments=32, lump=0.02, scale=2.0, dents=8)
    for vtx in ob.data.vertices:
        vtx.co.y *= _DEPTH
    ob.data.update()
    return ob


def _buttons(parts, prof, zs, mat, sd, grow=0.0):
    for k, z in enumerate(zs):
        y = _DEPTH * (_prof_r(prof, z) + grow) + 0.01
        parts.append(S.blob("v_btn%d" % k, (0.035, 0.025, 0.035), (0, y, z), mat, sd + k, lump=0.002, subdiv=2))


def _front(prof, x, z, grow=0.0, lift=0.01):
    """A point on the front (+Y) of a body at height z, x sideways, lifted off the surface by `lift`."""
    r = max(_prof_r(prof, z) + grow, abs(x) + 0.01)
    return (x, _DEPTH * math.sqrt(r * r - x * x) + lift, z)


def _pocket(parts, prof, x, z, mat, sd, grow=0.0):
    """A square patch pocket pressed onto the front."""
    px, py, pz = _front(prof, x, z, grow, 0.01)
    parts.append(S.slab("v_pocket", (0.08, 0.02, 0.07), (px, py, pz), mat, sd, lump=0.004, bevel=0.008, cuts=3))


def _stitch(parts, prof, x, z0, z1, mat, sd, grow=0.0):
    """A line of hand-run stitching down the front, a bead of thread at each step."""
    n = 7
    pts = [_front(prof, x, z0 + (z1 - z0) * k / (n - 1), grow, 0.008) for k in range(n)]
    parts.append(S.snake("v_seam%d" % sd, pts, 0.008, mat, sd, sides=5, wobble=0.0, steps=2))


def _lean(parts, z0=0.6, k=math.tan(math.radians(10))):
    """Stoop: shear everything above z0 forward. Position-only, so separate parts stay joined."""
    for ob in parts:
        for vtx in ob.data.vertices:
            vtx.co.y += max(0.0, vtx.co.z - z0) * k
        ob.data.update()


def _face_parts(sd):
    """Head, ears, neck, two big eyes with pupils, brows, cheeks, nose and smile. Facing +Y."""
    r, hz = _HR, _HZ
    p = [S.blob("v_head", (2 * r, 2 * r, 2 * r * 1.05), (0, 0, hz), "skin", sd, lump=0.02, subdiv=4, dents=2, dent_r=0.08, dent_d=0.01)]
    p.append(S.snake("v_neck", [(0, 0, 1.1), (0, 0, 1.25)], 0.07, "skin", sd, sides=8, wobble=0.05))
    for s in (-1, 1):
        p.append(S.blob("v_ear%d" % s, (0.05, 0.07, 0.09), (s * (r + 0.005), 0, hz - 0.01), "skin", sd + s, lump=0.01, subdiv=2))
        p.append(S.blob("v_eye%d" % s, (0.075, 0.05, 0.09), (s * 0.075, 0.17, hz + 0.03), "ivory", sd + s, lump=0.003, subdiv=3))
        p.append(S.blob("v_pupil%d" % s, (0.04, 0.03, 0.05), (s * 0.075, 0.2, hz + 0.025), "ink", sd + s, lump=0.0, subdiv=2))
        p.append(S.snake("v_brow%d" % s, [(s * 0.02, 0.165, hz + 0.1), (s * 0.08, 0.17, hz + 0.12)], 0.013, "bark", sd + s, sides=6, wobble=0.05, steps=2))
        p.append(S.blob("v_cheek%d" % s, (0.07, 0.03, 0.05), (s * 0.13, 0.14, hz - 0.04), "pink", sd + s, lump=0.01, subdiv=2))
    p.append(S.blob("v_nose", (0.07, 0.07, 0.07), (0, 0.195, hz - 0.03), "skin", sd + 3, lump=0.01, subdiv=3))
    p.append(S.snake("v_smile", [(-0.07, 0.165, hz - 0.075), (0, 0.19, hz - 0.095), (0.07, 0.165, hz - 0.075)], 0.013, "roof", sd, sides=6, wobble=0.0, steps=3))
    return p


def _hair(sd, mat, tufts=True):
    """Thumb-pressed hair cap over the top and back of the head, with curl tufts on top."""
    hz = _HZ
    out = [S.blob("v_hair", (0.4, 0.38, 0.28), (0, -0.04, hz + 0.09), mat, sd, lump=0.02, subdiv=3, dents=12, dent_r=0.05, dent_d=0.015)]
    if tufts:
        for i in range(6):
            a = i * 1.05
            bx, by = 0.11 * math.sin(a), -0.04 + 0.1 * math.cos(a)
            dx, dy = 0.035 * math.cos(a + 1.3), 0.035 * math.sin(a + 1.3)
            out.append(S.snake("v_tuft%d" % i, [(bx, by, hz + 0.19), (bx + dx, by + dy, hz + 0.25), (bx + 2 * dx, by + 2 * dy, hz + 0.24)],
                               0.02, mat, sd + i, sides=6, wobble=0.1, steps=2))
    return out


def _hand(prefix, c, side, seed, mat="skin"):
    """Mitten hand: a soft blob with a small thumb snake on the outer side (side = sign of its x)."""
    x, y, z = c
    return [S.blob(prefix + "_mitt", (0.1, 0.085, 0.11), c, mat, seed, lump=0.012, subdiv=3, dents=1, dent_r=0.04, dent_d=0.008),
            S.snake(prefix + "_thumb", [(x + side * 0.03, y + 0.02, z + 0.01), (x + side * 0.07, y + 0.045, z - 0.005)], 0.02, mat, seed, sides=6, steps=2)]


def _cuff(prefix, pts, mat, sd):
    """A snake ring round the sleeve just above the hand: a contrasting cuff."""
    end = Vector(pts[-1])
    d = (end - Vector(pts[-2])).normalized()
    c = end - d * 0.07
    u = d.cross(Vector((0, 0, 1)))
    if u.length < 1e-3:
        u = d.cross(Vector((1, 0, 0)))
    u.normalize()
    w = d.cross(u).normalized()
    ring = [tuple(c + (u * math.cos(2 * math.pi * k / 10) + w * math.sin(2 * math.pi * k / 10)) * 0.063) for k in range(11)]
    return S.snake(prefix, ring, 0.014, mat, sd, sides=6, wobble=0.0, steps=1, caps=False)


def _arm(prefix, pts, mat, side, sd, cuff=None):
    """A sleeve snake from the shoulder, ending at the mitten; optional cuff colour at the wrist."""
    out = [S.snake(prefix, pts, 0.055, mat, sd, sides=8, wobble=0.1, steps=4)] + _hand(prefix, pts[-1], side, sd + 1)
    if cuff:
        out.append(_cuff(prefix + "_cuff", pts, cuff, sd + 2))
    return out


def _shoes(sd, mat):
    return [S.blob("v_shoe%d" % s, (0.16, 0.26, 0.11), (s * 0.12, 0.04, 0.055), mat, sd + s, lump=0.012, subdiv=3, rot=(0, 0, s * 0.2))
            for s in (-1, 1)]


def B_villager(variant="a"):
    """A villager. a: praying, blue tunic, yellow belt. b: red dress, ivory apron, yellow bun, arms up.
    c: leaf waistcoat, bark trousers, flat cap, holding a lantern. d: stooped, purple robe, white hair and
    beard, stick. e: child at 0.75 scale, yellow jumper, blue shorts, orange pigtails, arms out."""
    if variant not in ("a", "b", "c", "d", "e"):
        raise ValueError("villager variant must be a-e, got %r" % (variant,))
    sd = 300 + 17 * "abcde".index(variant)
    parts = _face_parts(sd)
    legs, feet = None, "bark"

    if variant == "a":
        parts.append(_trunk("v_torso", _TORSO, "blue", sd))
        parts.append(S.snake("v_belt", _ring(_TORSO, 0.68, 12, 0.012), 0.03, "yellow", sd, sides=6, wobble=0.05, caps=False))
        _buttons(parts, _TORSO, (0.8, 0.92, 1.03), "ivory", sd)
        _pocket(parts, _TORSO, -0.12, 0.8, "yellow", sd)
        _stitch(parts, _TORSO, -0.12, 0.7, 0.9, "ivory", sd)
        parts.append(S.snake("v_collar", _ring(_TORSO, 1.19, 12, 0.02), 0.03, "ivory", sd + 1, sides=6, wobble=0.05, caps=False))
        parts += _hair(sd, "bark")
        for s in (-1, 1):  # hands pressed together in front of the chest
            parts += _arm("v_arm%d" % s, [(s * 0.2, 0, 1.1), (s * 0.25, 0.12, 0.95), (s * 0.1, 0.24, 0.98), (s * 0.035, 0.26, 1.02)],
                          "blue", s, sd + 5 * (s + 1), cuff="ivory")
        legs, feet = "blue", "bark"

    elif variant == "b":
        parts.append(_trunk("v_skirt", _SKIRT, "red", sd))
        parts.append(S.slab("v_apron", (0.3, 0.035, 0.5), (0, _DEPTH * _prof_r(_SKIRT, 0.6) + 0.02, 0.6), "ivory", sd, lump=0.006, bevel=0.012, cuts=4))
        parts.append(S.snake("v_bow", _ring(_SKIRT, 0.84, 12, 0.012), 0.025, "ivory", sd, sides=6, caps=False))
        _pocket(parts, _SKIRT, 0.14, 0.42, "pink", sd)
        _stitch(parts, _SKIRT, -0.2, 0.45, 0.8, "pink", sd)
        _stitch(parts, _SKIRT, 0.2, 0.45, 0.8, "pink", sd + 1)
        parts += _hair(sd, "yellow")
        parts.append(S.blob("v_bun", (0.13, 0.13, 0.13), (0, -0.2, _HZ + 0.14), "yellow", sd + 8, lump=0.015, subdiv=3))
        for s in (-1, 1):  # arms raised in a V
            parts += _arm("v_arm%d" % s, [(s * 0.2, 0, 1.1), (s * 0.36, 0.02, 1.34), (s * 0.43, 0, 1.6)], "red", s, sd + 5 * (s + 1), cuff="ivory")

    elif variant == "c":
        parts.append(_trunk("v_shirt", _TORSO, "ivory", sd))
        parts.append(_trunk("v_waistcoat", _TORSO, "leaf", sd + 1, z0=0.6, z1=1.02, grow=0.02))
        _buttons(parts, _TORSO, (0.7, 0.82, 0.94), "brass", sd, grow=0.02)
        _pocket(parts, _TORSO, 0.13, 0.78, "leaf_lt", sd, grow=0.02)
        _stitch(parts, _TORSO, 0.13, 0.7, 0.86, "ivory", sd, grow=0.02)
        parts.append(S.lathe("v_cap", [(0.0, 0.0), (0.2, 0.0), (0.21, 0.05), (0.18, 0.11), (0.0, 0.12)], mat="felt", seed=sd,
                             segments=24, lump=0.01, scale=3.0))
        _at(parts[-1], (0, 0, _HZ + 0.12))
        parts.append(S.slab("v_brim", (0.36, 0.24, 0.025), (0, 0.11, _HZ + 0.125), "felt", sd, lump=0.005, bevel=0.008, cuts=4))
        parts += _hair(sd, "ink", tufts=False)
        # lantern arm forward: brass tube frame, glowing yellow centre, hand on top
        parts.append(_at(S.lathe("v_lantube", [(0.055, 0.0), (0.06, 0.02), (0.06, 0.14), (0.055, 0.16)], mat="brass", seed=sd,
                                 segments=12, lump=0.0, cap=False), (0.2, 0.42, 0.86)))
        parts.append(_at(S.lathe("v_lanbase", [(0.0, 0.0), (0.065, 0.0), (0.065, 0.02), (0.0, 0.02)], mat="brass", seed=sd,
                                 segments=12, lump=0.0), (0.2, 0.42, 0.84)))
        parts.append(_at(S.lathe("v_lantop", [(0.0, 0.0), (0.065, 0.0), (0.065, 0.02), (0.0, 0.02)], mat="brass", seed=sd,
                                 segments=12, lump=0.0), (0.2, 0.42, 1.0)))
        parts.append(S.blob("v_glow", (0.08, 0.08, 0.12), (0.2, 0.42, 0.93), "yellow", sd, lump=0.01, subdiv=3))
        parts += _arm("v_armR", [(0.2, 0, 1.1), (0.23, 0.2, 1.0), (0.2, 0.36, 1.02), (0.2, 0.42, 1.05)], "ivory", 1, sd + 5, cuff="leaf")
        parts += _arm("v_armL", [(-0.2, 0, 1.1), (-0.26, 0.02, 0.92), (-0.27, 0.03, 0.74)], "ivory", -1, sd + 10, cuff="leaf")
        legs, feet = "bark", "ink"

    elif variant == "d":
        parts.append(_trunk("v_robe", _ROBE, "purple", sd))
        parts.append(S.snake("v_scarf", _ring(_ROBE, 1.14, 12, 0.025), 0.035, "orange", sd, sides=7, caps=False))
        parts.append(S.snake("v_scarftail", [(0.02, 0.165, 1.12), (0.05, 0.2, 1.0), (0.07, 0.22, 0.9)], 0.03, "orange", sd + 1, sides=7))
        parts.append(S.blob("v_beard", (0.2, 0.14, 0.2), (0, 0.1, _HZ - 0.17), "cloud", sd, lump=0.02, subdiv=3, dents=3, dent_r=0.06, dent_d=0.015))
        parts += _hair(sd, "cloud")
        parts.append(S.snake("v_robeseam", [_front(_ROBE, 0.0, z, 0.0, 0.008) for z in (0.3, 0.5, 0.7, 0.9)], 0.008, "orange", sd, sides=5, wobble=0.0, steps=2))
        parts += _arm("v_armL", [(-0.2, 0, 1.1), (-0.34, 0.04, 1.3), (-0.4, 0.06, 1.5)], "purple", -1, sd + 10, cuff="orange")
        parts += _arm("v_armR", [(0.2, 0, 1.1), (0.27, 0.06, 0.95), (0.3, 0.05, 0.74)], "purple", 1, sd + 5, cuff="orange")
        feet = "ink"
        _lean(parts)  # stooped ~10 degrees forward, from the waist up
        # the walking stick, set on the ground and under the hand after the lean
        parts.append(S.snake("v_stick", [(0.36, 0.26, 0.0), (0.33, 0.17, 0.4), (0.3, 0.09, 0.76)], 0.02, "bark", sd, sides=7, taper=(1.0, 0.8)))

    elif variant == "e":
        parts.append(_trunk("v_jumper", _TORSO, "yellow", sd))
        _pocket(parts, _TORSO, -0.13, 0.78, "red", sd)
        _stitch(parts, _TORSO, -0.13, 0.7, 0.86, "orange", sd)
        parts += _hair(sd, "orange", tufts=False)
        for s in (-1, 1):  # pigtails
            parts.append(S.snake("v_pig%d" % s, [(s * 0.15, -0.03, _HZ + 0.12), (s * 0.27, -0.03, _HZ + 0.04), (s * 0.27, -0.03, _HZ - 0.1)],
                                 0.035, "orange", sd + s, sides=8, wobble=0.1, steps=3))
        for s in (-1, 1):  # arms out wide
            parts += _arm("v_arm%d" % s, [(s * 0.2, 0, 1.08), (s * 0.4, 0, 1.06), (s * 0.55, 0, 1.0)], "yellow", s, sd + 5 * (s + 1), cuff="blue")
        legs, feet = "shorts", "ink"

    if legs == "bark" or legs == "blue":
        for s in (-1, 1):
            parts.append(S.snake("v_leg%d" % s, [(s * 0.11, 0, 0.52), (s * 0.12, 0, 0.16)], 0.085, legs, sd + s, sides=8, wobble=0.05, steps=2))
    elif legs == "shorts":
        for s in (-1, 1):
            parts.append(S.snake("v_short%d" % s, [(s * 0.11, 0, 0.52), (s * 0.12, 0, 0.4)], 0.085, "blue", sd + s, sides=8, wobble=0.05, steps=2))
            parts.append(S.snake("v_shin%d" % s, [(s * 0.12, 0, 0.42), (s * 0.12, 0, 0.16)], 0.07, "skin", sd + s, sides=8, wobble=0.05, steps=2))
    parts += _shoes(sd, feet)

    if variant == "e":
        for p in parts:
            for vtx in p.data.vertices:
                vtx.co *= 0.75
    kit.join("villager", parts).name = "villager"
