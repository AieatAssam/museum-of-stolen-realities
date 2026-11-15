"""Writes the Vitrine Kingdom's structural glass materials (smoked_glass.gdshader). Run from repo root:
    python3 wings/glass/tools/make_materials.py
One table, so the whole wing's value structure is tuned in one place."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
# name: tint, pane, facet, rough, glow, vary, proj, stagger
MATS = {
    "glass_wall":    ("0.05, 0.08, 0.2", "0.9, 1.4", 0.25, 0.08, 1.15, 0.35, 0, 0.5),
    "glass_floor":   ("0.03, 0.04, 0.08", "1.5, 1.5", 0.06, 0.1, 0.4, 0.25, 0, 0.0),
    "glass_red":     ("0.17, 0.012, 0.035", "0.38, 0.55", 0.35, 0.05, 0.5, 0.3, 0, 0.5),
    "glass_gold":    ("0.24, 0.12, 0.025", "0.38, 0.55", 0.35, 0.05, 0.5, 0.3, 0, 0.5),
    "glass_quarry":  ("0.06, 0.08, 0.1", "0.55, 0.8", 0.3, 0.08, 0.6, 0.3, 0, 0.5),
    "glass_red_m":   ("0.16, 0.02, 0.04", "1, 1", 0.0, 0.08, 0.5, 0.0, 2, 0.0),
    "glass_gold_m":  ("0.2, 0.12, 0.03", "1, 1", 0.0, 0.08, 0.5, 0.0, 2, 0.0),
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

# Glazed walls (glazed_wall.gdshader): name: proj, bay, bay_off, lw, tier_a, tier_b
GLAZED = {
    "glazed_nave":     (0, 5.5, -24.75, 4.4, "0.5, 12.0", "14.2, 11.0"),
    "glazed_cloister": (0, 3.0, 0.0, 2.2, "0.6, 7.4", "0, 0"),
    "glass_crypt":     (0, 2.9714, -84.85, 1.9, "-7.6, 4.4", "0, 0", "0.03, 0.08, 0.09"),  # between the vault piers
    "glazed_ruby":     (0, 1.7, -91.2, 1.1, "-7.5, 3.9", "0, 0", "0.17, 0.015, 0.04"),  # the ruby chapel
    "glazed_tower":    (0, 4.0, -24.0, 2.4, "-6.5, 9.5", "5.5, 11.5"),
    "glass_wall_uv":   (1, 4.8, 0.0, 3.0, "0.8, 8.0", "10.8, 11.0"),
}
ENERGY = {"glazed_cloister": 4.0, "glass_crypt": 2.1}  # the cloister has no clerestory: its lancets carry the room
for name, (proj, bay, off, lw, ta, tb, *tint) in GLAZED.items():
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=3 format=3]

[ext_resource type="Shader" path="res://wings/glass/shaders/glazed_wall.gdshader" id="1"]
[ext_resource type="Texture2D" path="res://wings/glass/textures/lancet_atlas.png" id="2"]

[resource]
shader = ExtResource("1")
shader_parameter/atlas = ExtResource("2")
shader_parameter/proj = {proj}
shader_parameter/bay = {bay}
shader_parameter/bay_off = {off}
shader_parameter/lw = {lw}
shader_parameter/tier_a = Vector2({ta})
shader_parameter/tier_b = Vector2({tb})
""" + (f"shader_parameter/tint = Color({tint[0]}, 1)\n" if tint else "")
            + (f"shader_parameter/energy = {ENERGY[name]}\n" if name in ENERGY else ""))
print("wrote", len(GLAZED), "glazed")
