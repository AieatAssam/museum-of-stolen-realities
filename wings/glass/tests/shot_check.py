"""Exposure gate for the Vitrine Kingdom beauty shots.
    tools/.venv/bin/python wings/glass/tests/shot_check.py [wings/glass/_shots/*.png]
Each shot: mean luma 0.18-0.40, <=30% of pixels below luma 0.04, >=3% vivid (sat>0.5 and value>0.5).
12_rose_dark is the one exception: it must instead show a lit lantern radius (>=2% of pixels luma>0.25).
Exit 1 if any shot fails."""
import glob
import sys

import numpy as np
from PIL import Image


def stats(path):
    a = np.asarray(Image.open(path).convert("RGB").reduce(4), dtype=np.float32) / 255.0
    luma = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return float(luma.mean()), float((luma < 0.04).mean()), float(((sat > 0.5) & (mx > 0.5)).mean()), float((luma > 0.25).mean())


def verdict(name, mean, black, vivid, lit):
    if "rose_dark" in name:
        return lit >= 0.02
    return 0.18 <= mean <= 0.40 and black <= 0.30 and vivid >= 0.03


def main(paths):
    bad = 0
    print(f"{'shot':22} {'mean':>5} {'<.04':>5} {'vivid':>5}  {'lit':>5}")
    for p in paths:
        s = stats(p)
        name = p.rsplit("/", 1)[-1][:-4]
        ok = verdict(name, *s)
        bad += not ok
        print(f"{name:22} {s[0]:5.3f} {s[1]:5.2f} {s[2]:5.3f}  {s[3]:5.3f}  {'PASS' if ok else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    assert verdict("x", 0.25, 0.1, 0.05, 0) and not verdict("x", 0.1, 0.9, 0.0, 0) and verdict("12_rose_dark", 0.02, 0.95, 0, 0.03)
    sys.exit(main(sys.argv[1:] or sorted(glob.glob("wings/glass/_shots/*.png"))))
