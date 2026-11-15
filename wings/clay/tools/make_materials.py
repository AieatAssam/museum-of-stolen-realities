"""Writes the Pinched Forest's materials into wings/clay/materials/. Run from the repo root:
    python3 wings/clay/tools/make_materials.py
One table for the whole plasticine palette, so the wing's colour is tuned in one place.
Blender material names in models/src/*.py are the contract."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
T = "res://wings/clay/textures/"

# name: colour, streak, streak_amount, tiles/m, normal strength, sss, emission
CLAY = {
    "clay":      ("0.78, 0.34, 0.13", "1.0, 0.85, 0.6", 0.25, 1.4, 1.6, 0.35, 0.0),
    "moss":      ("0.26, 0.50, 0.13", "1.0, 1.1, 0.6", 0.30, 1.4, 1.6, 0.25, 0.0),
    "leaf":      ("0.17, 0.42, 0.11", "1.3, 1.25, 0.6", 0.35, 1.6, 1.8, 0.35, 0.0),
    "leaf_lt":   ("0.46, 0.66, 0.16", "1.0, 1.0, 0.6", 0.30, 1.6, 1.8, 0.35, 0.0),
    "bark":      ("0.38, 0.21, 0.10", "1.2, 1.0, 0.8", 0.30, 2.0, 2.2, 0.2, 0.0),
    "ivory":     ("0.92, 0.86, 0.72", "1.0, 0.95, 0.85", 0.15, 1.8, 1.4, 0.45, 0.0),
    "red":       ("0.78, 0.08, 0.06", "1.1, 0.7, 0.6", 0.20, 1.8, 1.4, 0.4, 0.0),
    "yellow":    ("0.95, 0.70, 0.10", "1.0, 1.0, 0.8", 0.15, 1.8, 1.4, 0.4, 0.0),
    "pink":      ("0.92, 0.46, 0.62", "1.0, 0.9, 1.0", 0.20, 1.8, 1.4, 0.4, 0.0),
    "purple":    ("0.46, 0.26, 0.70", "1.2, 1.0, 1.0", 0.20, 1.8, 1.4, 0.4, 0.0),
    "blue":      ("0.16, 0.40, 0.80", "1.0, 1.1, 1.0", 0.20, 1.6, 1.4, 0.35, 0.0),
    "stone":     ("0.52, 0.50, 0.47", "1.15, 1.1, 1.0", 0.30, 1.4, 2.0, 0.15, 0.0),
    "cloud":     ("0.96, 0.95, 0.92", "0.95, 0.97, 1.0", 0.20, 0.5, 1.2, 0.6, 0.0),
    "skin":      ("0.84, 0.62, 0.44", "1.05, 0.95, 0.85", 0.20, 2.2, 1.6, 0.5, 0.0),
    "roof":      ("0.50, 0.17, 0.10", "1.2, 1.0, 0.9", 0.30, 1.8, 2.0, 0.2, 0.0),
    "plaster":   ("0.88, 0.78, 0.60", "0.95, 0.9, 0.85", 0.25, 1.4, 1.8, 0.3, 0.0),
    "window":    ("1.0, 0.66, 0.30", "1.0, 1.0, 1.0", 0.0, 2.0, 0.5, 0.0, 3.0),
    "bulb":      ("1.0, 0.80, 0.50", "1.0, 1.0, 1.0", 0.0, 2.0, 0.3, 0.0, 9.0),
    "lampshade": ("0.62, 0.10, 0.08", "1.2, 0.9, 0.9", 0.20, 2.0, 1.0, 0.1, 0.0),
    "felt":      ("0.10, 0.22, 0.16", "1.1, 1.1, 1.1", 0.20, 1.0, 1.5, 0.1, 0.0),
    "ink":       ("0.04, 0.035, 0.035", "1.0, 1.0, 1.0", 0.0, 2.0, 0.8, 0.0, 0.0),
    "orange":    ("0.95, 0.42, 0.08", "1.0, 0.9, 0.7", 0.20, 1.8, 1.4, 0.4, 0.0),
}
for name, (col, st, sa, tiles, ns, sss, em) in CLAY.items():
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=5 format=3]

[ext_resource type="Shader" path="res://wings/clay/shaders/plasticine.gdshader" id="1"]
[ext_resource type="Texture2D" path="{T}clay_plasticine_albedo.png" id="2"]
[ext_resource type="Texture2D" path="{T}clay_plasticine_normal.png" id="3"]
[ext_resource type="Texture2D" path="{T}clay_plasticine_roughness.png" id="4"]

[resource]
shader = ExtResource("1")
shader_parameter/colour = Color({col}, 1)
shader_parameter/streak = Color({st}, 1)
shader_parameter/streak_amount = {sa}
shader_parameter/detail_albedo = ExtResource("2")
shader_parameter/detail_normal = ExtResource("3")
shader_parameter/detail_rough = ExtResource("4")
shader_parameter/tiles_per_m = {tiles}
shader_parameter/normal_strength = {ns}
shader_parameter/sss = {sss}
shader_parameter/emission_gain = {em}
""")


def standard(name, body, tex=None):
    ext = ""
    steps = 1
    if tex:
        for i, (slot, path) in enumerate(tex, start=1):
            ext += f'[ext_resource type="Texture2D" path="{T}{path}" id="{i}"]\n'
            body += f'{slot} = ExtResource("{i}")\n'
        steps += len(tex)
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f'[gd_resource type="StandardMaterial3D" load_steps={steps} format=3]\n\n{ext}\n[resource]\n{body}')


standard("wood", "albedo_color = Color(1, 0.95, 0.88, 1)\nroughness = 0.75\nnormal_enabled = true\nnormal_scale = 1.4\n"
         "uv1_triplanar = true\nuv1_world_triplanar = false\nuv1_scale = Vector3(0.35, 0.35, 0.35)\n",
         [("albedo_texture", "clay_wood_albedo.png"), ("normal_texture", "clay_wood_normal.png"),
          ("roughness_texture", "clay_wood_roughness.png")])
standard("film", "transparency = 1\ncull_mode = 2\nalbedo_color = Color(0.82, 0.9, 1.0, 0.22)\nroughness = 0.06\nmetallic_specular = 0.9\n"
         "normal_enabled = true\nnormal_scale = 1.6\nuv1_triplanar = true\nuv1_scale = Vector3(0.45, 0.45, 0.45)\n"
         "rim_enabled = true\nrim = 0.4\nrim_tint = 0.2\n",
         [("normal_texture", "clay_film_normal.png")])
standard("glass", "transparency = 1\ncull_mode = 2\nalbedo_color = Color(0.78, 0.9, 0.88, 0.18)\nroughness = 0.03\nmetallic_specular = 1.0\nrim_enabled = true\nrim = 0.5\n")
standard("wire", "albedo_color = Color(0.32, 0.3, 0.28, 1)\nmetallic = 1.0\nroughness = 0.42\n")
standard("steel", "albedo_color = Color(0.78, 0.78, 0.8, 1)\nmetallic = 1.0\nroughness = 0.18\n")
standard("brass", "albedo_color = Color(0.86, 0.62, 0.3, 1)\nmetallic = 1.0\nroughness = 0.3\n")
print("wrote", len(CLAY) + 6)
