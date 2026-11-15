"""Gallery bench: oxblood velvet cushion on an ebony + brass frame. 2.4 m long, seat at 0.48 m."""
import kit


def build(args):
    p = []
    p.append(kit.box("cushion", (2.4, 0.62, 0.16), (0, 0, 0.42), mat="velvet", bevel=0.06, segments=4))
    p.append(kit.box("rail", (2.36, 0.58, 0.08), (0, 0, 0.3), mat="ebony", bevel=0.01))
    for x in (-1.05, 1.05):
        for y in (-0.22, 0.22):
            leg = kit.lathe("leg", [(0.05, 0.0), (0.06, 0.03), (0.035, 0.08), (0.04, 0.24), (0.06, 0.27), (0.0, 0.27)], 16, mat="brass")
            kit.place(leg, (x, y, 0))
            p.append(leg)
    kit.join("bench", p)
    kit.box("bench-convcolonly", (2.4, 0.62, 0.5), (0, 0, 0.25))
