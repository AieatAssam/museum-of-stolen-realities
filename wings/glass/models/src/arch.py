"""Nave arcade arch: a moulded pointed arch springing from two pier capitals 11 m apart.
Origin at the middle of the spring line; spans Blender X (Godot turns it into the arcade).
Arg "vault": one nave vault bay instead (transverse rib, two diagonals, ridge rib and a carved boss),
origin at spring height on the bay's west pier line; piers at x = +/-9.5, bay 11 m long (Godot -Z)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit  # noqa: E402
from gothic import RIB, pointed, roll, sweep  # noqa: E402

ARCADE = [(-0.42, -0.2), (0.0, -0.2), (0.06, -0.14), (0.06, 0.14), (0.0, 0.2), (-0.42, 0.2)]


def arcade():
    path = pointed(10.0, 6.0, 28)
    p = [sweep("arch", ARCADE, path, "glass_red_m")]
    for v in (-0.13, 0.0, 0.13):  # three rolls on the soffit
        p.append(sweep("roll", roll(0.07, 10, 0.08, v), path, "lead", smooth=70.0))
    p.append(sweep("hood", roll(0.07, 8), pointed(10.9, 6.5, 28), "brass", smooth=70.0))
    for s in (-1, 1):  # hood stops: carved bosses where the hood mould ends
        stop = kit.lathe("stop", [(0.0, -0.12), (0.1, -0.07), (0.12, 0.02), (0.07, 0.1), (0.0, 0.12)], 14, mat="brass")
        stop.location = (s * 5.45, 0, 0.0)
        p.append(stop)
    kit.join("arch_arcade", p)


def vault():
    rise = 11.3
    p = []
    tpath = pointed(18.0, rise, 32)
    p.append(sweep("transverse", RIB, tpath, "lead"))
    p.append(sweep("transverse_roll", roll(0.06, 10, 0.2), tpath, "brass", smooth=70.0))
    for sgn in (-1, 1):
        a = (9.0 * sgn, 0.3)
        b = (-9.0 * sgn, 10.7)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        half = math.hypot(b[0] - a[0], b[1] - a[1]) / 2
        c, s = math.cos(ang), math.sin(ang)

        def place(h, y, v, mid=mid, c=c, s=s):
            return (mid[0] + h * c - v * s, mid[1] + h * s + v * c, y)
        dpath = pointed(2 * half, rise, 36)
        p.append(sweep("diag", RIB, dpath, "lead", place))
        p.append(sweep("diag_roll", roll(0.06, 10, 0.2), dpath, "brass", place, smooth=70.0))
    p.append(sweep("ridge", RIB, [(0.0, rise), (11.0, rise)], "lead", lambda h, y, v: (v, h, y)))
    # a gilded rose boss where the diagonals cross, the Kingdom's emblem
    boss = kit.lathe("boss", [(0.0, -0.45), (0.18, -0.4), (0.32, -0.27), (0.36, -0.1), (0.3, 0.05), (0.0, 0.1)], 24, mat="brass")
    boss.location = (0.0, 5.5, rise)
    p.append(boss)
    for k in range(8):
        a = k * math.pi / 4
        pet = kit.lathe("petal%d" % k, [(0.0, -0.07), (0.11, -0.03), (0.12, 0.02), (0.0, 0.06)], 10, mat="brass")
        pet.location = (math.cos(a) * 0.32, 5.5 + math.sin(a) * 0.32, rise - 0.3)
        pet.scale = (1.7, 1.0, 1.0)
        pet.rotation_euler = (0, 0, a)
        p.append(pet)
    kit.join("vault_bay", p)


def build(args):
    vault() if args and args[0] == "vault" else arcade()
