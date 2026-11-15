"""Exposure gate for the Chitin Court shots (adapted from wings/glass/tests/shot_check.py).
    tools/.venv/bin/python wings/chitin/tests/shot_check.py [shots/chitin/*.png]
Bands come from the eight concept frames (wings/chitin/_concept, run this script on them): their mean
luma is 0.28-0.42, under 2% crushed black, 10-42% vivid, 1.6-8% non-amber accent (iridescence, fungus).
A real-time frame keeps deeper shadows than a painting, so the floor is lower:
  mean luma 0.15-0.45   readable but not washed out (the shaft and arena are meant to be dark)
  <= 25% of pixels below luma 0.04   no crushed frames
  >= 4% vivid (sat > 0.5 and value > 0.5)   the amber/honey practicals read
  >= 0.5% accent (saturated, hue outside 15-65 deg)   not a single-hue frame
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
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    accent = ((sat > 0.35) & (mx > 0.25) & ((h < 15) | (h > 65))).mean()
    return float(luma.mean()), float((luma < 0.04).mean()), float(((sat > 0.5) & (mx > 0.5)).mean()), float(accent)


def verdict(mean, black, vivid, accent):
    return 0.15 <= mean <= 0.45 and black <= 0.25 and vivid >= 0.04 and accent >= 0.005


def main(paths):
    bad = 0
    print(f"{'shot':22} {'mean':>5} {'<.04':>5} {'vivid':>5} {'accent':>6}")
    for p in paths:
        s = stats(p)
        ok = verdict(*s)
        bad += not ok
        print(f"{p.rsplit('/', 1)[-1][:-4]:22} {s[0]:5.3f} {s[1]:5.2f} {s[2]:5.3f} {s[3]:6.3f}  {'PASS' if ok else 'FAIL'}")
    return 1 if bad else 0


if __name__ == "__main__":
    assert verdict(0.25, 0.1, 0.05, 0.02) and not verdict(0.1, 0.9, 0.0, 0.0) and not verdict(0.3, 0.05, 0.2, 0.0)
    sys.exit(main(sys.argv[1:] or sorted(glob.glob("shots/chitin/*.png"))))
