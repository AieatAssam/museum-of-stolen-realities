"""Exposure gate for The Long Shadow's screenshots:  python wings/noir/tests/shot_check.py [dir|png ...]
Default dir: shots/noir. Prints one row per shot and exits 1 if any fails.

Noir is meant to be dark, so the shared gate (mean 0.18-0.40, <=30% under luma 0.04, >=3% vivid) would
fail every good frame here. The thresholds below are calibrated on the seven concept plates
(wings/noir/_concept, `--concepts` prints their numbers), with a margin either side:
  mean   0.09..0.30   plates 0.14..0.21: night, but readable
  black  <= 0.40      fraction under luma 0.04; plates 0.05..0.17. Deep blacks, not a black screen
  lit    >= 0.015     fraction over luma 0.55: every frame needs a focal light (plates 0.025..0.062)
  mid    >= 0.35      fraction in 0.08..0.45: the blacks hold detail, there is a middle (plates 0.54..0.70)
  leak   <= 0.04      fraction of pixels with chroma that is not neon red: the city stays monochrome
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

GATE = {"mean": (0.09, 0.30), "black": (0.0, 0.40), "lit": (0.015, 1.0), "mid": (0.35, 1.0), "leak": (0.0, 0.04)}


def stats(path):
    im = np.asarray(Image.open(path).convert("RGB").resize((640, 360)), dtype=np.float32) / 255.0
    luma = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]  # display (gamma) luma
    mx, mn = im.max(-1), im.min(-1)
    chroma = mx - mn
    red = (im[..., 0] >= mx - 1e-3) & (im[..., 0] > 1.6 * im[..., 2]) & (im[..., 0] > 1.6 * im[..., 1])
    return {
        "mean": float(luma.mean()),
        "black": float((luma < 0.04).mean()),
        "lit": float((luma > 0.55).mean()),
        "mid": float(((luma >= 0.08) & (luma <= 0.45)).mean()),
        "leak": float(((chroma > 0.12) & ~red).mean()),
    }


def main(args):
    if args and args[0] == "--concepts":
        args = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "_concept", "*.png")))
    paths = []
    for a in args or ["shots/noir"]:
        paths += sorted(glob.glob(os.path.join(a, "*.png"))) if os.path.isdir(a) else [a]
    bad = 0
    print("%-18s %6s %6s %6s %6s %6s" % ("shot", "mean", "black", "lit", "mid", "leak"))
    for p in paths:
        s = stats(p)
        fails = [k for k, (lo, hi) in GATE.items() if not lo <= s[k] <= hi]
        bad += bool(fails)
        print("%-18s %6.3f %6.3f %6.3f %6.3f %6.3f  %s" % (os.path.basename(p)[:-4], s["mean"], s["black"], s["lit"], s["mid"], s["leak"],
                                                           "FAIL " + ",".join(fails) if fails else "ok"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
