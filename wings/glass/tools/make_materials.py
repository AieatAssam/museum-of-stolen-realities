"""Writes the Vitrine Kingdom's structural glass materials (smoked_glass.gdshader). Run from repo root:
    python3 wings/glass/tools/make_materials.py
One table, so the whole wing's value structure is tuned in one place."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
# name: tint, pane, facet, rough, glow, vary, proj, stagger
MATS = {
    "glass_wall":    ("0.022, 0.03, 0.075", "0.9, 1.4", 0.25, 0.06, 0.05, 0.35, 0, 0.5),
    "glass_wall_uv": ("0.022, 0.03, 0.075", "0.9, 1.4", 0.25, 0.06, 0.05, 0.35, 1, 0.5),
    "glass_floor":   ("0.012, 0.014, 0.024", "1.5, 1.5", 0.06, 0.03, 0.0, 0.25, 0, 0.0),
    "glass_crypt":   ("0.016, 0.03, 0.032", "1.0, 1.0", 0.2, 0.06, 0.03, 0.4, 0, 0.0),
    "glass_red":     ("0.13, 0.01, 0.025", "0.6, 0.9", 0.3, 0.06, 0.12, 0.4, 0, 0.5),
    "glass_gold":    ("0.17, 0.09, 0.018", "0.6, 0.9", 0.3, 0.06, 0.14, 0.4, 0, 0.5),
    "glass_quarry":  ("0.03, 0.04, 0.05", "0.55, 0.8", 0.3, 0.08, 0.03, 0.3, 0, 0.5),
    "glass_red_m":   ("0.07, 0.008, 0.016", "1, 1", 0.0, 0.08, 0.1, 0.0, 2, 0.0),
    "glass_gold_m":  ("0.08, 0.05, 0.014", "1, 1", 0.0, 0.08, 0.1, 0.0, 2, 0.0),
}
for name, (tint, pane, facet, rough, glow, vary, proj, stagger) in MATS.items():
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=2 format=3]

[ext_resource type="Shader" path="res://wings/glass/shaders/smoked_glass.gdshader" id="1"]

[resource]
shader = ExtResource("1")
shader_parameter/tint = Color({tint}, 1)
shader_parameter/pane = Vector2({pane})
shader_parameter/facet = {facet}
shader_parameter/rough = {rough}
shader_parameter/glow = {glow}
shader_parameter/vary = {vary}
shader_parameter/proj = {proj}
shader_parameter/stagger = {stagger}
""")
print("wrote", len(MATS))
