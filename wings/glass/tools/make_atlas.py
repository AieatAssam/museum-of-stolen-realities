"""Packs the figurative lancets into one strip for glazed_wall.gdshader (12 columns, 512x1792 each, from the raw art).
    tools/.venv/bin/python wings/glass/tools/make_atlas.py"""
import os
from PIL import Image

T = os.path.join(os.path.dirname(__file__), "..", "textures")
R = os.path.join(os.path.dirname(__file__), "..", "_raw")
names = [f"story_{i}" for i in range(1, 9)] + [f"cloister_{i}" for i in range(1, 5)]
out = Image.new("RGB", (512 * len(names), 1792))
for i, n in enumerate(names):
    src = os.path.join(R, n + ".png") if os.path.exists(os.path.join(R, n + ".png")) else os.path.join(T, n + ".png")
    out.paste(Image.open(src).convert("RGB").resize((512, 1792), Image.LANCZOS), (512 * i, 0))
out.save(os.path.join(T, "lancet_atlas.png"))
print("atlas", out.size)
