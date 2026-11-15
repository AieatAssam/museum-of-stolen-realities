"""Exposure gate for the atrium shots (tests/shots.tscn -- --wing=atrium [--fragments=N]).
    tools/.venv/bin/python tests/atrium_shot_check.py [shots/atrium*/*.png]
Each shot: mean luma 0.13-0.40 (a dark museum, never a void), <=35% of pixels below luma 0.04
(no dead black areas), >=2% of pixels above luma 0.45 (a lit focal point), and the brightest 1%
not blown (p99 luma <= 0.97). Exit 1 if any shot fails."""
import glob
import sys

import numpy as np
from PIL import Image


def stats(path):
    a = np.asarray(Image.open(path).convert("RGB").reduce(4), dtype=np.float32) / 255.0
    luma = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return float(luma.mean()), float((luma < 0.04).mean()), float((luma > 0.45).mean()), float(np.percentile(luma, 99))


def verdict(mean, black, lit, p99):
    return 0.13 <= mean <= 0.40 and black <= 0.35 and lit >= 0.02 and p99 <= 0.97


def main(paths):
    bad = 0
    print(f"{'shot':28} {'mean':>5} {'<.04':>5} {'>.45':>5} {'p99':>5}")
    for p in paths:
        s = stats(p)
        ok = verdict(*s)
        bad += not ok
        name = "/".join(p.rsplit("/", 2)[-2:])[:-4]
        print(f"{name:28} {s[0]:5.3f} {s[1]:5.2f} {s[2]:5.3f} {s[3]:5.3f}  {'PASS' if ok else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    assert verdict(0.2, 0.1, 0.05, 0.9) and not verdict(0.05, 0.8, 0.0, 0.5) and not verdict(0.2, 0.1, 0.05, 1.0)
    sys.exit(main(sys.argv[1:] or sorted(glob.glob("shots/atrium*/*.png"))))
