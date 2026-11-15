"""Exposure gate for the Unfinished Wing's beauty shots (tests/shots.tscn -- --wing=paint).
    tools/.venv/bin/python wings/paint/tests/shot_check.py [shots/paint/*.png]
Thresholds come from the concepts in wings/paint/_concept/ (bright, saturated oil studies, mean luma
0.4-0.6): a lit shot must have mean luma 0.30-0.68 (not dim, not blown), <=12% of pixels below luma
0.04 (no crushed voids), >=4% vivid pixels (sat>0.45, value>0.45: the painting is never grey), and no
single 30-degree hue bin over 75% of the coloured pixels (no single-hue frames).
The two dark passages (unpainted, source) are keyed low on purpose: they must instead keep >=3% of
pixels above luma 0.35 (the lamp reads) and <=45% crushed black.
Exit 1 if any shot fails."""
import glob
import sys

import numpy as np
from PIL import Image

DARK = ("unpainted", "source")


def stats(path):
    a = np.asarray(Image.open(path).convert("RGB").reduce(4), dtype=np.float32) / 255.0
    luma = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    vivid = float(((sat > 0.45) & (mx > 0.45)).mean())
    col = sat > 0.12
    hue = np.asarray(Image.open(path).convert("HSV").reduce(4))[..., 0][col]
    top = float(np.bincount((hue.astype(int) * 12) // 256, minlength=12).max() / max(hue.size, 1))
    return float(luma.mean()), float((luma < 0.04).mean()), vivid, top, float((luma > 0.35).mean())


def verdict(name, mean, black, vivid, top, lit):
    if any(k in name for k in DARK):
        return lit >= 0.03 and black <= 0.45
    return 0.30 <= mean <= 0.68 and black <= 0.12 and vivid >= 0.04 and top <= 0.75


def main(paths):
    bad = 0
    print(f"{'shot':18} {'mean':>5} {'<.04':>5} {'vivid':>5} {'hue1':>5} {'lit':>5}")
    for p in paths:
        s = stats(p)
        name = p.rsplit("/", 1)[-1][:-4]
        ok = verdict(name, *s)
        bad += not ok
        print(f"{name:18} {s[0]:5.3f} {s[1]:5.2f} {s[2]:5.3f} {s[3]:5.2f} {s[4]:5.3f}  {'PASS' if ok else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    assert verdict("x", 0.45, 0.05, 0.1, 0.5, 0) and not verdict("x", 0.1, 0.9, 0.0, 0.9, 0)
    assert not verdict("x", 0.45, 0.05, 0.1, 0.9, 0) and verdict("08_source", 0.1, 0.4, 0, 1, 0.05)
    sys.exit(main(sys.argv[1:] or sorted(glob.glob("shots/paint/*.png"))))
