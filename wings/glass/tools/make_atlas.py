"""Packs the figurative lancets into one strip for glazed_wall.gdshader (12 columns, 256x896 each).
    tools/.venv/bin/python wings/glass/tools/make_atlas.py"""
import os
from PIL import Image

T = os.path.join(os.path.dirname(__file__), "..", "textures")
names = [f"story_{i}" for i in range(1, 9)] + [f"cloister_{i}" for i in range(1, 5)]
out = Image.new("RGB", (256 * len(names), 896))
for i, n in enumerate(names):
    out.paste(Image.open(os.path.join(T, n + ".png")).convert("RGB").resize((256, 896), Image.LANCZOS), (256 * i, 0))
out.save(os.path.join(T, "lancet_atlas.png"))
print("atlas", out.size)
