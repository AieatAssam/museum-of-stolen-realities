#!/usr/bin/env python3
"""Apply the project's texture import conventions to every PNG .import file under a folder,
then delete stale imported copies so the next `Godot --headless --import` re-imports them.

  python3 tools/fix_imports.py [folder ...]      (default: assets hub wings)

Rules (by filename suffix):
  *_albedo / *_height / anything in a textures/ folder  -> VRAM compressed, mipmaps
  *_normal     -> VRAM compressed as normal map (RGTC), mipmaps
  *_roughness  -> VRAM compressed, mipmaps
  ui/, fonts, *_ui.png -> lossless, no mipmaps (crisp 2D)
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rules(path):
    name = os.path.basename(path)[:-len(".png.import")]
    p = path.replace(os.sep, "/")
    if "/ui/" in p or name.endswith("_ui"):
        return {"compress/mode": "0", "mipmaps/generate": "false"}
    if "/textures/" in p or re.search(r"_(albedo|normal|roughness|height)$", name):
        r = {"compress/mode": "2", "mipmaps/generate": "true", "detect_3d/compress_to": "0"}
        r["compress/normal_map"] = "1" if name.endswith("_normal") else "2"
        return r
    return None


def main():
    dirs = sys.argv[1:] or ["assets", "hub", "wings"]
    changed = 0
    for d in dirs:
        for imp in glob.glob(os.path.join(ROOT, d, "**", "*.png.import"), recursive=True):
            want = rules(imp)
            if not want:
                continue
            txt = open(imp).read()
            new = txt
            for k, v in want.items():
                pat = re.compile(r"^%s=.*$" % re.escape(k), re.M)
                new = pat.sub("%s=%s" % (k, v), new) if pat.search(new) else new.replace("[params]\n", "[params]\n%s=%s\n" % (k, v), 1)
            if new != txt:
                open(imp, "w").write(new)
                for dest in re.findall(r'"(res://\.godot/imported/[^"]+)"', txt):
                    f = os.path.join(ROOT, dest[len("res://"):])
                    for g in glob.glob(f.rsplit(".", 1)[0] + "*"):
                        os.remove(g)
                md5 = os.path.join(ROOT, ".godot", "imported", os.path.basename(imp)[:-len(".import")] + "-*.md5")
                for g in glob.glob(md5):
                    os.remove(g)
                changed += 1
    print("updated %d import files; now run: Godot --headless --path . --import" % changed)


if __name__ == "__main__":
    main()
