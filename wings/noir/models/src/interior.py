"""Interiors (precinct, cinema, booth) and the hand props. Arg = part. Blender Z up, fronts face -Y
(Godot +Z); origins at the floor under the object's centre unless noted.
Precinct: desk, desk_lamp (origin on the desk top), chair, file_cabinet, locker (1.0 x 0.8 x 1.6, doors -Y),
  blind_window (1.6 x 2.0, origin at sill centre, front -Y), hanging_lamp (origin at the cord's top, hangs
  0.9 m), switch_box (origin on the wall), wainscot (2 m run, front -Y), door_frame (4 m opening, 3.2 m high)
Cinema: seat_block (2 rows of 3 seats on a 1.6 m square, backs to +Y), proscenium (10 m wide arch, front -Y),
  curtain (4 m swag), pilaster (6 m), balcony (4 m box front with balustrade, origin at its floor, front -Y),
  pedestal_reel (pedestal 1.0 m with a reel on top)
Booth: projector (faces -Y), film_shelf (2 m shelving with cans), port_window (origin centre)
Props (centred): pawn_ticket, matchbook, stub, frame_stand (the fragment: a frame of film in a stand)"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import kit  # noqa: E402


def B(name, size, loc, mat, bevel=0.0, seg=2):
    """A box built about its own centre and moved to `loc`, so a rotation set afterwards turns it in place
    (kit.box bakes `loc` into the vertices, which would swing a rotated part about the world origin)."""
    ob = kit.box(name, size, (0, 0, 0), mat=mat, bevel=bevel, segments=seg)
    ob.location = loc
    return ob


_join = kit.join


def _join_baked(name, objs):
    """kit.join, then bake the transforms so the mesh's own origin is the part's origin."""
    ob = _join(name, objs)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


kit.join = _join_baked


def desk():
    p = [B("top", (1.7, 0.85, 0.05), (0, 0, 0.76), "wood", bevel=0.012)]
    for x in (-0.6, 0.6):
        p.append(B("pedestal", (0.44, 0.78, 0.7), (x, 0.02, 0.36), "wood", bevel=0.008))
        for k in range(3):
            z = 0.15 + k * 0.21
            p.append(B("drawer", (0.4, 0.02, 0.18), (x, -0.38, z + 0.04), "wood", bevel=0.006))
            p.append(B("pull", (0.1, 0.03, 0.02), (x, -0.4, z + 0.08), "chrome", bevel=0.005))
    p.append(B("modesty", (0.8, 0.02, 0.5), (0, 0.38, 0.45), "wood"))
    p.append(B("blotter", (0.6, 0.4, 0.01), (0.1, -0.1, 0.79), "felt"))
    # files, a phone and an ashtray on the top
    for i, (dx, dz) in enumerate(((0.55, 0.0), (0.56, 0.03), (0.54, 0.06))):
        f = B("file", (0.32, 0.24, 0.025), (dx, 0.1, 0.8 + dz), "paper")
        f.rotation_euler = (0, 0, 0.1 * i - 0.1)
        p.append(f)
    p.append(B("phone_base", (0.2, 0.22, 0.07), (-0.55, 0.05, 0.82), "black", bevel=0.02))
    p.append(kit.tube("handset", [(-0.62, 0.05, 0.9), (-0.55, 0.05, 0.92), (-0.48, 0.05, 0.9)], 0.025, 8, mat="black"))
    p.append(kit.lathe("ashtray", [(0.0, 0.79), (0.07, 0.79), (0.08, 0.81), (0.06, 0.805), (0.0, 0.805)], 16, mat="chrome"))
    kit.join("desk", p)


def desk_lamp():
    p = [kit.lathe("base", [(0.0, 0.0), (0.1, 0.0), (0.1, 0.015), (0.05, 0.04), (0.0, 0.045)], 20, mat="chrome")]
    p.append(kit.tube("stem", [(0, 0, 0.04), (0, 0, 0.32), (0.04, 0, 0.36)], 0.012, 8, mat="chrome"))
    shade = kit.lathe("shade", [(0.0, 0.08), (0.04, 0.08), (0.11, 0.0), (0.12, -0.03), (0.0, -0.03)], 20, mat="felt")
    shade.rotation_euler = (0, math.pi / 2, 0)
    shade.scale = (1, 2.0, 1)
    shade.location = (0.06, 0, 0.38)
    p.append(shade)
    bulb = kit.lathe("bulb", [(0.0, -0.02), (0.03, -0.02), (0.03, 0.02), (0.0, 0.02)], 10, mat="bulb")
    bulb.rotation_euler = (0, math.pi / 2, 0)
    bulb.location = (0.06, 0, 0.36)
    p.append(bulb)
    kit.join("desk_lamp", p)


def chair():
    p = [B("seat", (0.46, 0.44, 0.06), (0, 0, 0.46), "wood", bevel=0.012)]
    for x in (-0.2, 0.2):
        for y in (-0.18, 0.18):
            p.append(B("leg", (0.04, 0.04, 0.46), (x, y, 0.23), "wood", bevel=0.006))
    for x in (-0.2, 0.2):
        p.append(B("post", (0.04, 0.04, 0.45), (x, 0.2, 0.7), "wood", bevel=0.006))
    p.append(B("back", (0.44, 0.03, 0.22), (0, 0.2, 0.8), "wood", bevel=0.01))
    p.append(B("rail", (0.42, 0.02, 0.04), (0, 0.2, 0.58), "wood"))
    kit.join("chair", p)


def file_cabinet():
    p = [B("body", (0.46, 0.65, 1.32), (0, 0, 0.66), "steel", bevel=0.01)]
    for k in range(4):
        z = 0.17 + k * 0.32
        p.append(B("drawer", (0.42, 0.02, 0.29), (0, -0.33, z), "steel", bevel=0.008))
        p.append(B("pull", (0.12, 0.04, 0.025), (0, -0.35, z + 0.05), "chrome", bevel=0.006))
        p.append(B("label", (0.08, 0.01, 0.05), (0, -0.345, z + 0.1), "paper"))
    kit.join("file_cabinet", p)


def locker():
    p = [B("body", (1.0, 0.8, 1.6), (0, 0, 0.8), "steel", bevel=0.01)]
    for x in (-0.25, 0.25):
        p.append(B("door", (0.46, 0.03, 1.5), (x, -0.41, 0.8), "steel", bevel=0.008))
        for k in range(6):  # wire-mesh panel: grid of thin bars over a dark back
            p.append(B("mesh_h", (0.34, 0.012, 0.012), (x, -0.43, 0.95 + k * 0.1), "iron"))
        for k in range(5):
            p.append(B("mesh_v", (0.012, 0.012, 0.5), (x - 0.14 + k * 0.07, -0.43, 1.2), "iron"))
        p.append(B("vent", (0.3, 0.02, 0.3), (x, -0.42, 0.35), "black"))
        for k in range(5):
            p.append(B("louvre", (0.3, 0.025, 0.02), (x, -0.43, 0.24 + k * 0.055), "steel"))
    p.append(B("hasp", (0.06, 0.05, 0.16), (0, -0.44, 0.9), "chrome", bevel=0.01))
    p.append(kit.torus("padlock", 0.035, 0.008, 16, 6, mat="chrome", loc=(0, -0.47, 0.86), rot=(math.pi / 2, 0, 0)))
    p.append(B("lock_body", (0.06, 0.03, 0.06), (0, -0.47, 0.81), "zinc", bevel=0.008))
    p.append(B("plinth", (1.0, 0.8, 0.06), (0, 0, 0.03), "black"))
    kit.join("locker", p)


def blind_window():
    p = []
    w, h = 1.6, 2.0
    path = [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)]
    p.append(kit.sweep_closed("frame", [(-0.1, -0.05), (0.0, -0.05), (0.0, 0.05), (-0.1, 0.05)], path, mat="wood"))
    p.append(B("glass", (w, 0.02, h), (0, 0.06, h / 2), "window_glass"))
    p.append(B("sill", (w + 0.2, 0.22, 0.05), (0, -0.05, -0.03), "wood", bevel=0.01))
    p.append(B("head", (w + 0.1, 0.12, 0.1), (0, -0.07, h - 0.02), "wood", bevel=0.01))
    for i in range(26):
        s = B("slat", (w - 0.06, 0.055, 0.006), (0, -0.07, 0.08 + i * 0.072), "zinc")
        s.rotation_euler = (math.radians(35), 0, 0)
        p.append(s)
    for x in (-0.55, 0.0, 0.55):
        p.append(B("ladder", (0.006, 0.006, h - 0.1), (x, -0.08, h / 2), "canvas"))
    p.append(kit.tube("pull_cord", [(0.7, -0.09, h - 0.05), (0.7, -0.09, 0.7)], 0.004, 4, mat="canvas"))
    kit.join("blind_window", p)


def hanging_lamp():
    p = [kit.tube("cord", [(0, 0, 0), (0, 0, -0.75)], 0.006, 6, mat="black")]
    p.append(kit.lathe("shade", [(0.0, -0.72), (0.04, -0.72), (0.06, -0.78), (0.24, -0.9), (0.26, -0.93), (0.0, -0.93)], 20, mat="zinc", cap=False))
    p.append(kit.lathe("bulb", [(0.0, -0.8), (0.04, -0.82), (0.05, -0.88), (0.03, -0.94), (0.0, -0.95)], 12, mat="bulb"))
    kit.join("hanging_lamp", p)


def switch_box():
    p = [B("box", (0.24, 0.1, 0.34), (0, -0.05, 0), "steel", bevel=0.015)]
    p.append(kit.tube("conduit", [(0, -0.04, 0.17), (0, -0.04, 1.6)], 0.018, 8, mat="iron"))
    lever = B("lever", (0.03, 0.12, 0.03), (0.0, -0.14, 0.04), "black", bevel=0.008)
    lever.rotation_euler = (math.radians(-30), 0, 0)
    p.append(lever)
    p.append(B("plate", (0.12, 0.01, 0.04), (0, -0.1, 0.13), "paper"))
    kit.join("switch_box", p)


def wainscot():
    p = [B("board", (2.0, 0.03, 1.1), (0, 0, 0.55), "wood")]
    for x in (-0.5, 0.5):
        path = [(x - 0.42, -0.02, 0.15), (x + 0.42, -0.02, 0.15), (x + 0.42, -0.02, 0.95), (x - 0.42, -0.02, 0.95)]
        p.append(kit.sweep_closed("panel", [(-0.03, -0.0), (0.0, -0.0), (0.0, -0.025), (-0.03, -0.025)], path, mat="wood"))
    p.append(B("cap", (2.0, 0.06, 0.05), (0, -0.02, 1.12), "wood", bevel=0.01))
    p.append(B("skirt", (2.0, 0.05, 0.14), (0, -0.02, 0.07), "wood", bevel=0.005))
    kit.join("wainscot", p)


def door_frame():
    """Surround for the 4 m precinct opening: architrave and a transom panel with wired glass."""
    p = []
    for x in (-2.05, 2.05):
        p.append(B("jamb", (0.18, 0.3, 3.2), (x, 0, 1.6), "wood", bevel=0.015))
    p.append(B("head", (4.5, 0.3, 0.22), (0, 0, 3.3), "wood", bevel=0.02))
    p.append(B("transom", (3.9, 0.04, 0.6), (0, 0, 3.75), "window_glass"))
    p.append(B("transom_bar", (4.3, 0.2, 0.08), (0, 0, 4.08), "wood", bevel=0.01))
    for i in range(14):
        p.append(B("wire", (0.008, 0.05, 0.6), (-1.9 + i * 0.29, 0, 3.75), "iron"))
    kit.join("door_frame", p)


# --- cinema --------------------------------------------------------------------------------------

def _seat(p, x, y):
    p.append(B("cushion", (0.46, 0.44, 0.1), (x, y - 0.02, 0.44), "velvet", bevel=0.04, seg=3))
    back = B("back", (0.46, 0.1, 0.5), (x, y + 0.2, 0.72), "velvet", bevel=0.04, seg=3)
    back.rotation_euler = (math.radians(-10), 0, 0)
    p.append(back)
    p.append(B("back_shell", (0.48, 0.03, 0.52), (x, y + 0.27, 0.72), "wood", bevel=0.01))


def seat_block():
    p = []
    for row, y in enumerate((-0.4, 0.4)):
        for k in range(3):
            _seat(p, -0.53 + k * 0.53, y)
        for k in range(4):  # cast-iron standards with an armrest between seats
            x = -0.8 + k * 0.53
            p.append(B("standard", (0.05, 0.5, 0.62), (x, y + 0.02, 0.31), "iron", bevel=0.01))
            p.append(B("arm", (0.07, 0.42, 0.04), (x, y - 0.02, 0.64), "wood", bevel=0.012))
            p.append(B("scroll", (0.06, 0.14, 0.14), (x, y - 0.18, 0.2), "gilt", bevel=0.03))
    kit.join("seat_block", p)


def proscenium():
    """10 m wide, 9 m tall arch frame; opening 7.6 x 6.6. Front at y=0, depth 0.8."""
    p = []
    W, H, ow, oh = 10.0, 9.0, 7.6, 6.6
    p.append(B("left", ((W - ow) / 2, 0.8, H), (-(ow + (W - ow) / 2) / 2, 0.4, H / 2), "plaster", bevel=0.03))
    p.append(B("right", ((W - ow) / 2, 0.8, H), ((ow + (W - ow) / 2) / 2, 0.4, H / 2), "plaster", bevel=0.03))
    p.append(B("top", (ow, 0.8, H - oh), (0, 0.4, (oh + H) / 2), "plaster", bevel=0.03))
    # stepped gilt mouldings around the opening, an arch of fans in the head
    for k, (d, t) in enumerate(((0.0, 0.18), (0.25, 0.12), (0.45, 0.08))):
        path = [(-ow / 2 - d, -0.02 - k * 0.05, 0), (ow / 2 + d, -0.02 - k * 0.05, 0), (ow / 2 + d, -0.02 - k * 0.05, oh + d), (-ow / 2 - d, -0.02 - k * 0.05, oh + d)]
        p.append(kit.sweep_closed("moulding", [(-t, 0.0), (0.0, 0.0), (0.0, -0.08 - k * 0.04), (-t, -0.08 - k * 0.04)], path, mat="gilt"))
    for i in range(13):
        a = math.pi * (i + 0.5) / 13
        r0, r1 = 0.6, 1.7
        f = kit.tube("fan", [(r0 * math.cos(a), -0.1, oh + 0.3 + r0 * math.sin(a) * 0.9), (r1 * math.cos(a), -0.1, oh + 0.3 + r1 * math.sin(a) * 0.9)], 0.05, 6, mat="gilt")
        p.append(f)
    p.append(kit.lathe("boss", [(0.0, 0.0), (0.5, 0.0), (0.45, 0.12), (0.0, 0.2)], 24, mat="gilt"))
    p[-1].rotation_euler = (math.pi / 2, 0, 0)
    p[-1].location = (0, -0.05, oh + 0.3)
    for x in (-ow / 2 - 0.9, ow / 2 + 0.9):  # engaged columns with fluting
        p.append(kit.lathe("col", [(0.0, 0.0), (0.42, 0.0), (0.42, 0.3), (0.32, 0.4), (0.3, 6.0), (0.4, 6.2), (0.46, 6.5), (0.0, 6.5)], 20, mat="plaster"))
        p[-1].location = (x, -0.3, 0)
    p.append(B("stage", (ow + 1.0, 1.4, 0.9), (0, -0.4, 0.45), "wood", bevel=0.02))
    p.append(B("stage_lip", (ow + 1.0, 0.1, 0.1), (0, -1.1, 0.85), "gilt"))
    kit.join("proscenium", p)


def curtain():
    """4 m wide, 6.6 m drop of heavy folds (a sine-pleated sheet), tied back at the base."""
    import bmesh
    bm = bmesh.new()
    nx, nz = 48, 16
    W, H = 4.0, 6.6
    rows = []
    for j in range(nz + 1):
        z = H * j / nz
        tie = 1.0 - 0.35 * math.exp(-((z - 1.6) / 0.9) ** 2)  # gathered toward one side near the tie
        row = []
        for i in range(nx + 1):
            u = i / nx
            x = -W / 2 + W * u * tie
            y = 0.12 * math.sin(u * math.pi * 14) * (0.6 + 0.4 * z / H)
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    ob = kit._obj("curtain", bm, "velvet", 80.0)
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.03
    kit.join("curtain", [ob, B("pelmet", (4.2, 0.3, 0.6), (0, -0.1, H + 0.2), "velvet", bevel=0.05)])


def pilaster():
    p = [B("shaft", (0.6, 0.25, 6.0), (0, 0.125, 3.0), "plaster", bevel=0.02)]
    for k in range(4):
        p.append(B("flute", (0.06, 0.04, 4.8), (-0.18 + k * 0.12, -0.01, 3.0), "plaster_dark" if False else "stone"))
    p.append(B("base", (0.8, 0.35, 0.4), (0, 0.1, 0.2), "plaster", bevel=0.03))
    p.append(B("capital", (0.85, 0.4, 0.5), (0, 0.08, 5.75), "gilt", bevel=0.04))
    p.append(kit.lathe("sconce", [(0.0, 0.0), (0.12, 0.0), (0.22, 0.25), (0.0, 0.25)], 6, mat="window_lit"))
    p[-1].location = (0, -0.18, 3.6)
    kit.join("pilaster", p)


def balcony():
    p = [B("slab", (4.0, 1.4, 0.25), (0, -0.4, -0.12), "plaster", bevel=0.03)]
    p.append(B("front", (4.0, 0.12, 0.9), (0, -1.1, 0.45), "plaster", bevel=0.02))
    p.append(B("rail", (4.1, 0.22, 0.08), (0, -1.1, 0.94), "gilt", bevel=0.02))
    for i in range(16):
        p.append(kit.lathe("baluster", [(0.0, 0.0), (0.05, 0.0), (0.04, 0.12), (0.07, 0.4), (0.03, 0.7), (0.05, 0.78), (0.0, 0.8)], 8, mat="gilt"))
        p[-1].location = (-1.9 + i * 0.253, -1.2, 0.08)
    p.append(B("soffit_band", (4.0, 0.1, 0.25), (0, -1.12, -0.3), "gilt", bevel=0.02))
    kit.join("balcony", p)


def pedestal_reel():
    p = [kit.lathe("pedestal", [(0.0, 0.0), (0.42, 0.0), (0.42, 0.08), (0.34, 0.14), (0.26, 0.2), (0.22, 0.9), (0.3, 0.96), (0.34, 1.02), (0.0, 1.02)], 24, mat="iron")]
    # a 35 mm reel standing on edge: two flanges with spoke cut-outs (as spokes) and film between
    for y in (-0.06, 0.06):
        p.append(kit.torus("flange_rim", 0.38, 0.012, 40, 6, mat="chrome", loc=(0, y, 1.42), rot=(math.pi / 2, 0, 0)))
        hub = kit.lathe("hub", [(0.0, -0.01), (0.07, -0.01), (0.07, 0.01), (0.0, 0.01)], 16, mat="chrome")
        hub.rotation_euler = (math.pi / 2, 0, 0)
        hub.location = (0, y, 1.42)
        p.append(hub)
        for k in range(6):
            a = k * math.pi / 3
            s = B("spoke", (0.32, 0.01, 0.04), (0.2 * math.cos(a), y, 1.42 + 0.2 * math.sin(a)), "chrome")
            s.rotation_euler = (0, -a, 0)
            p.append(s)
    film = kit.lathe("film", [(0.08, -0.055), (0.3, -0.055), (0.3, 0.055), (0.08, 0.055)], 32, mat="film")
    film.rotation_euler = (math.pi / 2, 0, 0)
    film.location = (0, 0, 1.42)
    p.append(film)
    p.append(B("cradle", (0.16, 0.2, 0.42), (0, 0, 1.2), "iron", bevel=0.02))
    kit.join("pedestal_reel", p)


def cinema_gate():
    """Collapsible scissor gate across the cinema mouth, 11 x 4 m, origin at its centre (front -Y)."""
    p = []
    W, H = 11.0, 4.0
    n = 20
    pitch = W / n
    for i in range(n + 1):
        x = -W / 2 + i * pitch
        p.append(B("post", (0.05, 0.06, H - 0.1), (x, 0, 0), "iron", bevel=0.008))
    # lazy-tongs: flat bars crossing between posts, three bays high
    bays = 3
    bh = (H - 0.5) / bays
    L = math.hypot(pitch, bh)
    a = math.atan2(bh, pitch)
    for i in range(n):
        cx = -W / 2 + (i + 0.5) * pitch
        for j in range(bays):
            cz = -H / 2 + 0.25 + (j + 0.5) * bh
            for s, y in ((1, -0.04), (-1, 0.04)):
                b = B("tong", (L, 0.012, 0.035), (cx, y, cz), "steel")
                b.rotation_euler = (0, -s * a, 0)
                p.append(b)
    for z in (-H / 2 + 0.05, H / 2 - 0.05):
        p.append(B("track", (W + 0.2, 0.14, 0.1), (0, 0, z), "iron", bevel=0.02))
    # hasp and padlock at the meeting posts
    p.append(B("hasp", (0.16, 0.1, 0.24), (0.0, -0.07, -0.25), "steel", bevel=0.01))
    p.append(B("lock", (0.12, 0.06, 0.14), (0.0, -0.13, -0.42), "zinc", bevel=0.02))
    p.append(kit.torus("shackle", 0.04, 0.008, 16, 6, mat="chrome", loc=(0.0, -0.13, -0.33), rot=(math.pi / 2, 0, 0)))
    kit.join("cinema_gate", p)


# --- booth ---------------------------------------------------------------------------------------

def projector():
    p = [B("stand", (0.5, 0.9, 1.0), (0, 0, 0.5), "iron", bevel=0.04)]
    p.append(B("foot", (0.8, 1.2, 0.08), (0, 0, 0.04), "iron", bevel=0.02))
    p.append(B("lamphouse", (0.55, 0.75, 0.6), (0, 0.35, 1.35), "steel", bevel=0.05))
    for k in range(5):
        p.append(B("vent", (0.02, 0.4, 0.04), (0.28, 0.35, 1.2 + k * 0.07), "bulb"))
    p.append(kit.lathe("chimney", [(0.0, 1.65), (0.1, 1.65), (0.1, 2.3), (0.13, 2.32), (0.0, 2.34)], 12, mat="steel"))
    p[-1].location = (0, 0.35, 0)
    p.append(B("head", (0.35, 0.5, 0.5), (0, -0.25, 1.35), "paint", bevel=0.04))
    lens = kit.lathe("lens", [(0.0, 0.0), (0.08, 0.0), (0.08, 0.3), (0.1, 0.32), (0.1, 0.38), (0.0, 0.38)], 16, mat="chrome")
    lens.rotation_euler = (math.pi / 2, 0, 0)
    lens.location = (0, -0.5, 1.35)
    p.append(lens)
    p.append(kit.lathe("lens_glass", [(0.0, 0.0), (0.075, 0.0), (0.0, 0.01)], 16, mat="beam_lens"))
    p[-1].rotation_euler = (math.pi / 2, 0, 0)
    p[-1].location = (0, -0.885, 1.35)
    for z, y in ((2.05, -0.2), (0.85, -0.2)):  # feed and take-up magazines with reels
        mag = kit.lathe("magazine", [(0.0, -0.08), (0.4, -0.08), (0.42, -0.06), (0.42, 0.06), (0.4, 0.08), (0.0, 0.08)], 28, mat="paint")
        mag.rotation_euler = (0, math.pi / 2, 0)
        mag.location = (0, y, z + (0.0 if z > 1 else 0.0))
        p.append(mag)
    p.append(B("arm", (0.1, 0.1, 0.5), (0, -0.2, 1.75), "iron"))
    kit.join("projector", p)


def film_shelf():
    p = []
    for z in (0.02, 0.6, 1.2, 1.8):
        p.append(B("shelf", (2.0, 0.42, 0.03), (0, 0, z), "wood", bevel=0.005))
    for x in (-0.98, 0.98):
        p.append(B("upright", (0.04, 0.42, 2.0), (x, 0, 1.0), "wood"))
    p.append(B("back", (2.0, 0.02, 2.0), (0, 0.2, 1.0), "wood"))
    for si, z in enumerate((0.02, 0.6, 1.2, 1.8)):
        for k in range(5 - si % 2):
            for j in range(3 + (k + si) % 3):
                can = kit.lathe("can", [(0.0, 0.0), (0.17, 0.0), (0.18, 0.01), (0.18, 0.04), (0.17, 0.045), (0.0, 0.045)], 18, mat="zinc")
                can.location = (-0.75 + k * 0.38, 0.0, z + 0.015 + j * 0.046)
                p.append(can)
    kit.join("film_shelf", p)


def port_window():
    p = [B("plate", (0.9, 0.08, 0.6), (0, 0, 0), "steel", bevel=0.02)]
    path = [(-0.2, -0.05, -0.12), (0.2, -0.05, -0.12), (0.2, -0.05, 0.12), (-0.2, -0.05, 0.12)]
    p.append(kit.sweep_closed("rim", [(-0.04, 0.0), (0.0, 0.0), (0.0, -0.03), (-0.04, -0.03)], path, mat="chrome"))
    p.append(B("glass", (0.4, 0.02, 0.24), (0, -0.03, 0), "window_glass"))
    p.append(B("shutter", (0.46, 0.02, 0.1), (0, -0.06, 0.2), "iron"))
    kit.join("port_window", p)


# --- props ---------------------------------------------------------------------------------------

def pawn_ticket():
    p = [B("card", (0.09, 0.004, 0.16), (0, 0, 0), "paper", bevel=0.001)]
    p.append(B("stripe", (0.09, 0.006, 0.02), (0, 0, 0.055), "card_red"))
    p.append(kit.torus("eyelet", 0.008, 0.002, 12, 4, mat="zinc", loc=(0, 0, 0.068), rot=(math.pi / 2, 0, 0)))
    p.append(kit.tube("string", [(0, 0, 0.07), (0.02, 0, 0.12), (0.05, 0, 0.13), (0.07, 0, 0.1)], 0.0015, 4, mat="canvas"))
    p.append(B("perf", (0.09, 0.006, 0.002), (0, 0, -0.03), "black"))
    kit.join("pawn_ticket", p)


def matchbook():
    p = [B("cover_back", (0.05, 0.004, 0.09), (0, 0.006, 0), "card_red", bevel=0.001)]
    front = B("cover_front", (0.05, 0.004, 0.07), (0, 0, 0.035), "card_red", bevel=0.001)
    front.rotation_euler = (math.radians(-60), 0, 0)
    front.location = (0, -0.01, 0.035)
    p.append(front)
    p.append(B("striker", (0.05, 0.006, 0.012), (0, 0.006, -0.04), "black"))
    for k in range(9):
        if k in (3, 6):
            continue  # two missing
        x = -0.02 + k * 0.005
        p.append(B("match", (0.003, 0.002, 0.055), (x, 0.002, 0.0), "paper"))
        p.append(kit.lathe("head", [(0.0, 0.0), (0.0025, 0.0), (0.0025, 0.007), (0.0, 0.008)], 6, mat="card_red"))
        p[-1].location = (x, 0.002, 0.027)
    kit.join("matchbook", p)


def stub():
    p = [B("stub", (0.07, 0.003, 0.05), (0, 0, 0), "paper", bevel=0.0008)]
    p.append(B("band", (0.07, 0.005, 0.012), (0, 0, 0.012), "card_red"))
    for k in range(10):
        p.append(B("perf", (0.003, 0.005, 0.003), (-0.034, 0, -0.022 + k * 0.005), "black"))
    kit.join("stub", p)


def frame_stand():
    """The fragment: one frame of film, 0.5 x 0.38, held in a brass stand on a small lightbox."""
    p = [B("lightbox", (0.62, 0.24, 0.12), (0, 0, -0.33), "paint", bevel=0.02)]
    p.append(B("diffuser", (0.5, 0.16, 0.01), (0, 0, -0.265), "bulb"))
    for x in (-0.3, 0.3):
        p.append(kit.tube("post", [(x, 0, -0.3), (x, 0, 0.24)], 0.012, 8, mat="gilt"))
        p.append(kit.lathe("finial", [(0.0, 0.0), (0.02, 0.0), (0.0, 0.05)], 8, mat="gilt"))
        p[-1].location = (x, 0, 0.24)
    p.append(B("film_l", (0.06, 0.008, 0.5), (-0.23, 0, -0.02), "film"))
    p.append(B("film_r", (0.06, 0.008, 0.5), (0.23, 0, -0.02), "film"))
    for x in (-0.23, 0.23):
        for k in range(8):
            p.append(B("sprocket", (0.025, 0.012, 0.03), (x, 0, -0.24 + k * 0.062), "bulb"))
    p.append(B("picture", (0.38, 0.006, 0.42), (0, 0, -0.02), "frame_picture"))
    kit.join("frame_stand", p)


# --- office and street props ---------------------------------------------------------------------

def _front_to_plus_y(ob):
    """Built with the front on -Y; turn about Z so the front faces +Y, and bake it."""
    ob.rotation_euler = (0, 0, math.pi)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


def typewriter():
    """Origin at the floor under the body centre, front +Y. Keys sit on a tilted deck (front lower), platen roller
    across the back with chrome knobs, a sheet of paper standing up from the roller."""
    p = [B("body", (0.45, 0.38, 0.2), (0, 0, 0.1), "paint", bevel=0.015)]
    th = math.radians(20)
    c, s = math.cos(th), math.sin(th)
    PY, PZ = -0.02, 0.25
    p.append(B("deck", (0.42, 0.22, 0.02), (0, PY, PZ), "paint", bevel=0.006))
    p[-1].rotation_euler = (th, 0, 0)
    for row, v in enumerate((-0.075, -0.045, -0.015, 0.015)):  # 4 tiers of keys, staggered
        n, off = (11, 0.0) if row % 2 == 0 else (10, 0.017)
        for i in range(n):
            x = -0.17 + i * 0.034 + off
            k = kit.lathe("key", [(0, 0), (0.008, 0), (0.008, 0.005), (0, 0.005)], 8, mat="paint")
            k.rotation_euler = (th, 0, 0)
            # deck-local (x, v, 0.011) turned about X, in world space
            k.location = (x, PY + v * c - 0.011 * s, PZ + v * s + 0.011 * c)
            p.append(k)
    roll = kit.lathe("platen", [(0, -0.2), (0.03, -0.2), (0.03, 0.2), (0, 0.2)], 16, mat="black")
    roll.rotation_euler = (0, math.pi / 2, 0)
    roll.location = (0, 0.14, 0.3)
    p.append(roll)
    for sx in (-1, 1):
        p.append(B("arm", (0.02, 0.06, 0.14), (sx * 0.22, 0.14, 0.27), "paint", bevel=0.005))
        knob = kit.lathe("knob", [(0, -0.02), (0.02, -0.02), (0.02, 0.02), (0, 0.02)], 12, mat="chrome")
        knob.rotation_euler = (0, math.pi / 2, 0)
        knob.location = (sx * 0.24, 0.14, 0.3)
        p.append(knob)
    p.append(kit.tube("lever", [(0.22, -0.02, 0.16), (0.28, -0.02, 0.2), (0.28, 0.12, 0.26)], 0.008, 6, mat="chrome"))
    sheet = B("sheet", (0.32, 0.008, 0.24), (0, 0.1, 0.44), "paper", bevel=0.005)
    sheet.rotation_euler = (math.radians(-8), 0, 0)
    p.append(sheet)
    _front_to_plus_y(kit.join("typewriter", p))


def telephone():
    """1940s cradle desk phone, origin at the base floor centre, dial toward +Y. Chrome forks and dial, paint body,
    curved handset resting on the forks, finger holes as small black discs in a ring on the dial."""
    p = [B("base", (0.22, 0.2, 0.07), (0, 0, 0.035), "paint", bevel=0.02)]
    for sx in (-1, 1):
        p.append(B("fork", (0.024, 0.03, 0.08), (sx * 0.07, 0.06, 0.11), "chrome", bevel=0.006))
    dial = kit.lathe("dial", [(0, 0), (0.055, 0), (0.055, 0.006), (0, 0.006)], 24, mat="chrome")
    dial.location = (0, -0.04, 0.07)
    p.append(dial)
    for k in range(10):
        a = math.radians(30 * k + 60)
        hole = kit.lathe("hole", [(0, 0), (0.008, 0), (0.008, 0.003), (0, 0.003)], 10, mat="black")
        hole.location = (0.036 * math.cos(a), -0.04 + 0.036 * math.sin(a), 0.076)
        p.append(hole)
    p.append(kit.tube("handset", [(-0.12, 0, 0.19), (-0.07, 0, 0.166), (0, 0, 0.158), (0.07, 0, 0.166), (0.12, 0, 0.19)], 0.014, 8, mat="paint"))
    for sx in (-1, 1):  # earpiece and mouthpiece cups
        cup = kit.lathe("cup", [(0, 0), (0.03, 0), (0.035, 0.02), (0.02, 0.035), (0, 0.035)], 14, mat="paint")
        cup.location = (sx * 0.12, 0, 0.19)
        p.append(cup)
    _front_to_plus_y(kit.join("telephone", p))


def coat_stand():
    """1.85 m turned pole (lathe) on three legs, four hooks; a trench coat on the east hook and a fedora
    on the west one. Origin at the floor under the pole."""
    prof = [(0.0, 0.0), (0.05, 0.0), (0.05, 0.03), (0.03, 0.07), (0.025, 0.12), (0.035, 0.2), (0.025, 0.3),
            (0.02, 0.6), (0.035, 0.95), (0.02, 1.0), (0.02, 1.4), (0.04, 1.48), (0.02, 1.55), (0.02, 1.7),
            (0.035, 1.78), (0.045, 1.8), (0.02, 1.84), (0.0, 1.85)]
    p = [kit.lathe("pole", prof, 20, mat="wood")]
    for a in (90, 210, 330):
        r = math.radians(a)
        p.append(kit.tube("leg", [(0, 0, 0.04), (0.26 * math.cos(r), 0.26 * math.sin(r), 0.018)], 0.018, 6, mat="wood"))
    for a, z in ((0, 1.55), (90, 1.55), (180, 1.62), (270, 1.55)):
        r = math.radians(a)
        cr, sr = math.cos(r), math.sin(r)
        pts = [(0.02 * cr, 0.02 * sr, z), (0.12 * cr, 0.12 * sr, z), (0.22 * cr, 0.22 * sr, z), (0.24 * cr, 0.24 * sr, z - 0.05)]
        p.append(kit.tube("hook", pts, 0.008, 6, mat="iron"))
    coat = kit.lathe("coat", [(0.0, 0.0), (0.2, 0.0), (0.21, 0.25), (0.19, 0.6), (0.17, 0.8), (0.12, 0.92), (0.05, 0.99), (0.0, 1.02)], 24, mat="coat")
    coat.scale = (1.0, 0.35, 1.0)
    coat.location = (0.23, 0.0, 0.49)
    p.append(coat)
    brim = kit.lathe("brim", [(0.0, 0.0), (0.17, 0.0), (0.18, 0.012), (0.1, 0.02), (0.0, 0.02)], 24, mat="hat")
    brim.location = (-0.23, 0, 1.6)
    p.append(brim)
    crown = kit.lathe("crown", [(0.0, 0.02), (0.085, 0.02), (0.09, 0.05), (0.085, 0.1), (0.08, 0.12), (0.0, 0.125)], 24, mat="hat")
    crown.location = (-0.23, 0, 1.6)
    p.append(crown)
    kit.join("coat_stand", p)


def wall_clock():
    """0.4 m school clock. Origin at the centre of its back so it mounts flat on a wall; face to +Y."""
    p = []
    case = kit.lathe("case", [(0, 0), (0.2, 0), (0.2, 0.08), (0, 0.08)], 32, mat="paint")
    case.rotation_euler = (-math.pi / 2, 0, 0)  # lathe Z becomes +Y
    p.append(case)
    face = kit.lathe("face", [(0, 0), (0.18, 0), (0.18, 0.004), (0, 0.004)], 32, mat="paper")
    face.rotation_euler = (-math.pi / 2, 0, 0)
    face.location = (0, 0.08, 0)
    p.append(face)
    p.append(kit.torus("rim", 0.2, 0.014, 48, 10, mat="chrome", loc=(0, 0.08, 0), rot=(math.pi / 2, 0, 0)))
    for i in range(12):
        a = i * math.pi / 6
        t = B("tick", (0.012, 0.012, 0.035), (0.16 * math.sin(a), 0.086, 0.16 * math.cos(a)), "black", bevel=0.005)
        t.rotation_euler = (0, a, 0)
        p.append(t)
    ah = math.radians(60)  # hour hand at two
    hour = B("hour", (0.016, 0.012, 0.11), (0.055 * math.sin(ah), 0.09, 0.055 * math.cos(ah)), "black", bevel=0.005)
    hour.rotation_euler = (0, ah, 0)
    p.append(hour)
    am = math.radians(150)  # minute hand at twenty-five past
    minute = B("minute", (0.012, 0.012, 0.16), (0.08 * math.sin(am), 0.1, 0.08 * math.cos(am)), "black", bevel=0.005)
    minute.rotation_euler = (0, am, 0)
    p.append(minute)
    hub = kit.lathe("hub", [(0, 0), (0.014, 0), (0.014, 0.012), (0, 0.012)], 12, mat="chrome")
    hub.rotation_euler = (-math.pi / 2, 0, 0)
    hub.location = (0, 0.08, 0)
    p.append(hub)
    kit.join("wall_clock", p)


def pinboard():
    """1.2 x 0.9 m felt board in a wood frame, origin at the back centre (on the wall), face to +Y.
    Ten pinned notes at fixed random spots (seeded); a red string runs between four of the pins."""
    import random
    rng = random.Random(11)
    p = [B("board", (1.2, 0.03, 0.9), (0, 0.015, 0), "felt", bevel=0.008)]
    p.append(B("frame_t", (1.3, 0.05, 0.05), (0, 0.025, 0.475), "wood", bevel=0.008))
    p.append(B("frame_b", (1.3, 0.05, 0.05), (0, 0.025, -0.475), "wood", bevel=0.008))
    for sx in (-1, 1):
        p.append(B("frame_s", (0.05, 0.05, 0.9), (sx * 0.625, 0.025, 0), "wood", bevel=0.008))
    pins = []
    for i in range(10):
        x = rng.uniform(-0.5, 0.5)
        z = rng.uniform(-0.3, 0.3)
        a = math.radians(rng.uniform(-9, 9))
        w, h = rng.uniform(0.1, 0.14), rng.uniform(0.13, 0.17)
        note = B("note", (w, 0.008, h), (x, 0.034, z), "card_red" if i in (2, 7) else "paper", bevel=0.005)
        note.rotation_euler = (0, a, 0)
        p.append(note)
        lz = h / 2 - 0.02  # pin near the top edge of the note
        px, pz = x + lz * math.sin(a), z + lz * math.cos(a)
        pins.append((px, pz))
        pin = kit.lathe("pin", [(0, 0), (0.006, 0), (0.006, 0.008), (0, 0.008)], 8, mat="card_red")
        pin.rotation_euler = (-math.pi / 2, 0, 0)
        pin.location = (px, 0.038, pz)
        p.append(pin)
    pts = [(pins[i][0], 0.047, pins[i][1]) for i in (0, 3, 6, 9)]
    p.append(kit.tube("string", pts, 0.003, 6, mat="card_red"))
    kit.join("pinboard", p)


def frosted_door():
    """0.95 x 2.15 m door in a sash frame, origin at the floor centre, front +Y. Wood door, upper frosted pane
    (material glass_frosted, left plain), chrome rose and knob on the handle side at 1 m."""
    p = [B("door", (0.95, 0.05, 2.15), (0, 0, 1.075), "wood", bevel=0.01)]
    p.append(B("panel_low", (0.7, 0.02, 0.8), (0, -0.035, 0.5), "wood", bevel=0.008))
    p.append(B("pane", (0.6, 0.01, 0.9), (0, -0.03, 1.6), "glass_frosted", bevel=0.005))
    p.append(B("sash_t", (0.7, 0.03, 0.05), (0, -0.03, 2.075), "sash", bevel=0.008))
    p.append(B("sash_b", (0.7, 0.03, 0.05), (0, -0.03, 1.125), "sash", bevel=0.008))
    for sx in (-1, 1):
        p.append(B("sash_s", (0.05, 0.03, 1.0), (sx * 0.325, -0.03, 1.6), "sash", bevel=0.008))
        p.append(B("jamb", (0.06, 0.12, 2.2), (sx * 0.505, 0, 1.1), "sash", bevel=0.008))
    p.append(B("head", (1.07, 0.12, 0.06), (0, 0, 2.18), "sash", bevel=0.008))
    rose = kit.lathe("rose", [(0, 0), (0.03, 0), (0.03, 0.006), (0, 0.006)], 16, mat="chrome")
    rose.rotation_euler = (math.pi / 2, 0, 0)
    rose.location = (0.36, -0.025, 1.0)
    p.append(rose)
    knob = kit.lathe("knob", [(0, 0), (0.022, 0), (0.028, 0.012), (0.03, 0.025), (0.024, 0.04), (0, 0.045)], 16, mat="chrome")
    knob.rotation_euler = (math.pi / 2, 0, 0)
    knob.location = (0.36, -0.031, 1.0)
    p.append(knob)
    _front_to_plus_y(kit.join("frosted_door", p))


def ceiling_fan():
    """Canopy at the origin (the ceiling mount point), 0.4 m downrod, motor housing; hangs down -Z.
    The hub the blades turn on is at (0, 0, -0.58), where ceiling_fan_blades' origin goes."""
    p = [kit.lathe("canopy", [(0, -0.03), (0.07, -0.03), (0.07, 0), (0, 0)], 20, mat="paint")]
    p.append(kit.tube("downrod", [(0, 0, -0.02), (0, 0, -0.4)], 0.012, 8, mat="iron"))
    p.append(kit.lathe("housing", [(0, -0.56), (0.13, -0.56), (0.14, -0.5), (0.13, -0.46), (0.07, -0.42), (0.035, -0.4), (0, -0.4)], 24, mat="paint"))
    kit.join("ceiling_fan", p)


def ceiling_fan_blades():
    """Four 0.6 m wooden blades, pitched, on an iron hub. Origin at the hub centre (spins about Z)."""
    p = [kit.lathe("hub", [(0, -0.03), (0.075, -0.03), (0.09, -0.02), (0.09, 0.02), (0.075, 0.03), (0, 0.03)], 20, mat="iron")]
    for k in range(4):
        th = k * math.pi / 2
        blade = B("blade", (0.6, 0.13, 0.012), (0.38 * math.cos(th), 0.38 * math.sin(th), 0), "wood", bevel=0.005)
        blade.rotation_euler = (math.radians(12), 0, th)
        p.append(blade)
    kit.join("ceiling_fan_blades", p)


PARTS = {n: globals()[n] for n in (
    "desk", "desk_lamp", "chair", "file_cabinet", "locker", "blind_window", "hanging_lamp", "switch_box",
    "wainscot", "door_frame", "seat_block", "proscenium", "curtain", "pilaster", "balcony", "pedestal_reel",
    "cinema_gate", "projector", "film_shelf", "port_window", "pawn_ticket", "matchbook", "stub", "frame_stand",
    "typewriter", "telephone", "coat_stand", "wall_clock", "pinboard", "frosted_door", "ceiling_fan", "ceiling_fan_blades")}


def build(args):
    PARTS[args[0]]()
