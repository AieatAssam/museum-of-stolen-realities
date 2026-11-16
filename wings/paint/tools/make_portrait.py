"""The Pentimento's paintings from wings/paint/_raw (gen_pass2.sh): the portrait as a texture plus a
relief height map (paint is raised where it is thick and dark against bare canvas, smoothed so the
drawing's forms become soft modelling), and the earlier compositions as textures.
    tools/.venv/bin/python wings/paint/tools/make_portrait.py"""
import numpy as np
from PIL import Image, ImageFilter

R, T = "wings/paint/_raw/", "wings/paint/textures/"
im = Image.open(R + "portrait.png").convert("RGB")
im.resize((1024, 1120), Image.LANCZOS).save(T + "paint_portrait.jpg", quality=90)
a = np.asarray(im.resize((256, 280), Image.LANCZOS), dtype=np.float32) / 255.0
canvas = np.array([0.80, 0.70, 0.56], dtype=np.float32)
paint = np.clip(np.linalg.norm(a - canvas, axis=-1) / 0.35, 0, 1)
luma = a @ np.array([0.3, 0.59, 0.11], dtype=np.float32)
def blur(x, r):
    return np.asarray(Image.fromarray((x * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0
h = 0.55 * blur(paint, 3) + 0.30 * blur(paint, 10) + 0.15 * blur(1.0 - luma, 6)
h = (h - h.min()) / (h.max() - h.min())
# the relief itself: a 27.4 x 30 m grid (feet at y 0, facing +Z) raised up to DEPTH where the paint is
NX, NY, W, H, DEPTH = 100, 110, 27.4, 30.0, 2.4
g = np.asarray(Image.fromarray((h * 255).astype(np.uint8)).resize((NX, NY), Image.BILINEAR), dtype=np.float32)[::-1] / 255.0
xs, ys = np.meshgrid(np.linspace(-W / 2, W / 2, NX), np.linspace(0, H, NY))
P = np.stack([xs, ys, g * DEPTH], -1)
dx = np.gradient(P, axis=1); dy = np.gradient(P, axis=0)
N = np.cross(dx, dy); N /= np.linalg.norm(N, axis=-1, keepdims=True)
with open("wings/paint/models/portrait_relief.obj", "w") as f:
    f.write("# Pentimento portrait relief (tools/make_portrait.py)\n")
    for (x, y, z), (a, b, c) in zip(P.reshape(-1, 3), N.reshape(-1, 3)):
        f.write(f"v {x:.3f} {y:.3f} {z:.3f}\nvn {a:.4f} {b:.4f} {c:.4f}\n")
    for j in range(NY):
        for i in range(NX):
            f.write(f"vt {i / (NX - 1):.4f} {j / (NY - 1):.4f}\n")
    for j in range(NY - 1):
        for i in range(NX - 1):
            a, b, c, d = j * NX + i + 1, j * NX + i + 2, (j + 1) * NX + i + 2, (j + 1) * NX + i + 1
            f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\nf {a}/{a}/{a} {c}/{c}/{c} {d}/{d}/{d}\n")
for n in ("earlier_harbour", "earlier_house", "earlier_still"):
    Image.open(R + n + ".png").convert("RGB").resize((1024, 1024), Image.LANCZOS).save(T + "paint_" + n + ".jpg", quality=88)
print("ok")
