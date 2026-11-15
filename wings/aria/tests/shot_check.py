"""Exposure gate for the Drowned Aria shots (same thresholds as the glass wing's gate).
    tools/.venv/bin/python wings/aria/tests/shot_check.py [shots/aria/*.png]
Each shot: mean luma 0.18-0.40, <=30% of pixels below luma 0.04, >=3% vivid (sat>0.5 and value>0.5).
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
    return float(luma.mean()), float((luma < 0.04).mean()), float(((sat > 0.5) & (mx > 0.5)).mean())


def verdict(mean, black, vivid):
    return 0.18 <= mean <= 0.40 and black <= 0.30 and vivid >= 0.03


def main(paths):
    bad = 0
    print(f"{'shot':22} {'mean':>5} {'<.04':>5} {'vivid':>5}")
    for p in paths:
        s = stats(p)
        ok = verdict(*s)
        bad += not ok
        print(f"{p.rsplit('/', 1)[-1][:-4]:22} {s[0]:5.3f} {s[1]:5.2f} {s[2]:5.3f}  {'PASS' if ok else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    assert verdict(0.25, 0.1, 0.05) and not verdict(0.1, 0.9, 0.0)
    sys.exit(main(sys.argv[1:] or sorted(glob.glob("shots/aria/*.png"))))
