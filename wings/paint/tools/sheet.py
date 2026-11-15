"""Contact sheet of shots: python sheet.py out.jpg a.png b.png ... (4 per row, 640x360 tiles)."""
import sys

from PIL import Image

fs = sys.argv[2:]
ims = [Image.open(f).convert("RGB").resize((640, 360)) for f in fs]
W = Image.new("RGB", (640 * 4, 360 * ((len(ims) + 3) // 4)))
for i, im in enumerate(ims):
    W.paste(im, ((i % 4) * 640, (i // 4) * 360))
W.save(sys.argv[1], quality=80)
