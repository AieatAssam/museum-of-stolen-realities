#!/usr/bin/env python3
"""Make wings/paint/textures/paint_damask_albedo.png: tone-on-tone damask over plaster.

1024 px greyscale-in-RGB seamless tile. Everything is periodic: the plaster is
cross-faded with its half-shifted copy, blurs are FFT (circular), the motif uses
minimum-image distances and the mottling uses integer frequencies.

Usage: tools/.venv/bin/python wings/paint/tools/make_damask.py [--preview OUT.png]
"""
import functools
import sys
from pathlib import Path

import numpy as np
from PIL import Image

N = 1024
CELL = N / 3.0  # three motifs across; centred half-drop lattice closes on the tile
ROOT = Path(__file__).resolve().parents[3]
PLASTER = ROOT / "assets/textures/plaster/plaster_albedo.png"
OUT = ROOT / "wings/paint/textures/paint_damask_albedo.png"


def blur(a, sigma):
    """Periodic Gaussian blur (FFT), so the tile stays seamless."""
    f = np.fft.fftfreq(N)
    fy, fx = np.meshgrid(f, f, indexing="ij")
    g = np.exp(-2 * np.pi**2 * sigma**2 * (fx**2 + fy**2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))


def plaster():
    p = np.asarray(Image.open(PLASTER).convert("L").resize((N, N), Image.LANCZOS), float) / 255.0
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N) / N)  # 0 at the seam, 1 mid-tile
    # Cross-fade with the half-shifted copy: column 0 then meets column N-1 as
    # neighbouring source columns (511 / 512), so the photo tile wraps.
    p = w[None, :] * p + (1 - w[None, :]) * np.roll(p, N // 2, axis=1)
    p = w[:, None] * p + (1 - w[:, None]) * np.roll(p, N // 2, axis=0)
    p = blur(p, 2.5)
    z = np.clip((p - p.mean()) / p.std(), -2.5, 2.5)  # clip photo outliers so the range stays tight
    return z / z.std() * 0.04 + 0.82


def leaf(along, across, s):
    """Pointed leaf along the `along` axis (both arguments already abs'd)."""
    t = np.clip((along - s * 46) / (s * 60), 0, 1)
    half_width = s * 15 * np.sin(np.pi * t)
    return np.maximum(across - half_width, np.abs(along - s * 76) - s * 30)


def motif_shapes(dx, dy, s):
    """Signed-ish distance to the motif (<= 0 inside). Mirror-symmetric in x."""
    rho = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    ax, ay = np.abs(dx), np.abs(dy)
    a = (dx + dy) / np.sqrt(2)
    b = (dx - dy) / np.sqrt(2)
    parts = [
        rho - s * (34 + 8 * np.cos(6 * th)),        # rosette medallion (cos 6th: even, mirror-safe)
        np.abs(rho - s * 62) - s * 1.6,             # thin ring round the medallion
        leaf(ay, ax, s), leaf(ax, ay, s),           # axial leaves, up/down and left/right
        leaf(np.abs(a), np.abs(b), s), leaf(np.abs(b), np.abs(a), s),  # diagonal leaves
    ]
    return functools.reduce(np.minimum, parts)


def centres():
    c = CELL
    # Rows every c/2, odd rows shifted c/2 (centred half-drop). 6 rows x 3 columns per tile.
    return [(m * c + (n % 2) * c / 2, n * c / 2) for n in range(6) for m in range(3)]


def motif(s=1.7):
    Y, X = np.mgrid[0:N, 0:N].astype(float)
    G = np.full((N, N), 1e9)
    for cx, cy in centres():
        dx = (X - cx + N / 2) % N - N / 2
        dy = (Y - cy + N / 2) % N - N / 2
        G = np.minimum(G, motif_shapes(dx, dy, s))
    inside = (G <= 0).astype(float)
    outline = ((G <= 0) & (G > -2.5)).astype(float)  # thin band just inside the edge
    m = blur(inside, 1.5)
    o = blur(outline, 1.5)
    return (1 + 0.10 * m) * (1 - 0.06 * o)            # lighter motif, outline x0.94


def mottle(rng):
    Y, X = np.mgrid[0:N, 0:N] / N
    m = 0
    for kx, ky in [(1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2), (2, -1), (3, 1)]:
        m = m + rng.uniform(0.5, 1) * np.cos(2 * np.pi * (kx * X + ky * Y) + rng.uniform(0, 2 * np.pi))
    return 1 + 0.03 * m / np.abs(m).max()


def seam(u8):
    a = u8.astype(float)
    lr = np.abs(a[:, 0] - a[:, -1]).mean()  # left column vs its wrap neighbour (right column)
    tb = np.abs(a[0] - a[-1]).mean()        # top row vs bottom row
    ref = np.abs(a[:, 0] - a[:, 1]).mean()  # ordinary adjacent column, for scale
    return lr, tb, ref


if __name__ == "__main__":
    rng = np.random.default_rng(20240)
    x = plaster() * mottle(rng) * motif()
    # soft shoulder above 0.90 so the lifted motif tops out near 0.96 instead of clipping white
    v = np.where(x > 0.90, 0.90 + 0.06 * np.tanh((x - 0.90) / 0.06), x)
    v = np.clip(v, 0, 1)
    u8 = np.round(v * 255).astype(np.uint8)

    lr, tb, ref = seam(u8)
    print(f"seam mean-abs (8-bit): left/right {lr:.2f}, top/bottom {tb:.2f}, adjacent-col ref {ref:.2f}")
    assert lr / 255 < 0.02 and tb / 255 < 0.02, "tile does not wrap"
    print(f"value range: min {v.min():.3f} max {v.max():.3f} "
          f"p0.5 {np.percentile(v, 0.5):.3f} p99.5 {np.percentile(v, 99.5):.3f} mean {v.mean():.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(u8).convert("RGB").save(OUT)
    print("wrote", OUT)

    if "--preview" in sys.argv:
        path = sys.argv[sys.argv.index("--preview") + 1]
        Image.fromarray(np.tile(u8, (2, 2))).convert("RGB").save(path)
        print("preview", path)
