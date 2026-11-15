#!/usr/bin/env python3
"""Make a seamless tileable PBR set (albedo / normal / roughness / height) from one image.

  tools/.venv/bin/python tools/make_pbr.py <src.png|noise:SEED> <out_dir> <name> [options]

Writes <out_dir>/<name>_albedo.png, _normal.png (OpenGL / Godot convention, +Y up),
_roughness.png, _height.png. Run `--help` for knobs. Re-run is deterministic.
"""
import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def make_seamless(img: np.ndarray, margin: float) -> np.ndarray:
    """Four-way offset blend (variance preserving). Kills edge seams; keeps texture contrast."""
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    wx = smooth(np.minimum(xs, w - 1 - xs) / (w * margin))
    wy = smooth(np.minimum(ys, h - 1 - ys) / (h * margin))
    a = img
    b = np.roll(img, w // 2, axis=1)
    c = np.roll(img, h // 2, axis=0)
    d = np.roll(b, h // 2, axis=0)
    ws = [wx * wy, (1 - wx) * wy, wx * (1 - wy), (1 - wx) * (1 - wy)]
    mean = img.reshape(-1, img.shape[2]).mean(0)
    acc = np.zeros_like(img)
    norm = np.zeros((h, w), np.float32)
    for wi, im in zip(ws, (a, b, c, d)):
        acc += wi[..., None] * (im - mean)
        norm += wi * wi
    return np.clip(acc / np.sqrt(norm)[..., None] + mean, 0, 1)


def fbm(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for octave in range(7):
        cells = 4 * 2 ** octave
        grid = rng.random((cells, cells)).astype(np.float32)
        layer = ndimage.zoom(np.tile(grid, (3, 3)), size / cells, order=3)[size:2 * size, size:2 * size]
        out += layer * amp
        total += amp
        amp *= 0.55
    out /= total
    out = (out - out.min()) / (out.max() - out.min())
    return np.repeat(out[..., None], 3, axis=2)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", help="image path, or noise:SEED for procedural fbm")
    p.add_argument("out_dir")
    p.add_argument("name")
    p.add_argument("--size", type=int, default=1024, help="output size (power of two)")
    p.add_argument("--no-seamless", action="store_true", help="source already tiles")
    p.add_argument("--margin", type=float, default=0.22, help="seam blend width (fraction)")
    p.add_argument("--tint", default=None, help="multiply albedo by hex colour, e.g. c8a35a")
    p.add_argument("--normal-strength", type=float, default=4.0)
    p.add_argument("--height-blur", type=float, default=1.2, help="px blur on height before normals")
    p.add_argument("--height-highpass", type=float, default=48.0, help="px sigma; removes large-scale shading")
    p.add_argument("--rough-min", type=float, default=0.25)
    p.add_argument("--rough-max", type=float, default=0.7)
    p.add_argument("--rough-invert", action="store_true", help="bright = rough (default: dark = rough)")
    args = p.parse_args()

    if args.src.startswith("noise:"):
        img = fbm(args.size, int(args.src.split(":")[1]))
    else:
        im = Image.open(args.src).convert("RGB")
        side = min(im.size)
        im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                      (im.width + side) // 2, (im.height + side) // 2))
        img = np.asarray(im.resize((args.size, args.size), Image.LANCZOS), np.float32) / 255.0
        if not args.no_seamless:
            img = make_seamless(img, args.margin)
    if args.tint:
        t = np.array([int(args.tint[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)
        img = img * t

    lum = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    height = lum - ndimage.gaussian_filter(lum, args.height_highpass, mode="wrap")
    height = ndimage.gaussian_filter(height, args.height_blur, mode="wrap")
    lo, hi = np.percentile(height, 1), np.percentile(height, 99)
    height = np.clip((height - lo) / max(hi - lo, 1e-6), 0, 1)

    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    s = args.normal_strength
    n = np.dstack([-gx * s, gy * s, np.ones_like(height)])  # +Y up (OpenGL), image rows go down
    n /= np.linalg.norm(n, axis=2, keepdims=True)

    r = lum if args.rough_invert else 1.0 - lum
    r = (r - r.min()) / max(r.max() - r.min(), 1e-6)
    rough = args.rough_min + r * (args.rough_max - args.rough_min)

    os.makedirs(args.out_dir, exist_ok=True)
    base = os.path.join(args.out_dir, args.name)
    u8 = lambda a: (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(u8(img)).save(base + "_albedo.png")
    Image.fromarray(u8(n * 0.5 + 0.5)).save(base + "_normal.png")
    Image.fromarray(u8(rough)).save(base + "_roughness.png")
    Image.fromarray(u8(height)).save(base + "_height.png")
    print(base + "_{albedo,normal,roughness,height}.png")


if __name__ == "__main__":
    main()
