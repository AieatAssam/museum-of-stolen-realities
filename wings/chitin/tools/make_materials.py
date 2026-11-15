"""Writes the Chitin Court materials (the names models use; see models/src/SPEC.txt). Run from repo root:
    python3 wings/chitin/tools/make_materials.py
One table so the wing's value structure is tuned in one place. brass comes from assets/materials."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
T = "res://wings/chitin/textures/"
HIVE = "res://wings/chitin/shaders/hive.gdshader"
AMBER = "res://wings/chitin/shaders/amber.gdshader"

# hive.gdshader: name: texture set, params
HIVE_MATS = {
    "carapace":      ("carapace", dict(tint="Color(0.55, 0.7, 0.6, 1)", scale=0.45, normal_depth=1.2, rough_lo=0.08, rough_hi=0.35, iridescence=0.55, film=1.1)),
    "carapace_dull": ("carapace", dict(tint="Color(0.32, 0.36, 0.3, 1)", scale=0.6, normal_depth=1.0, rough_lo=0.45, rough_hi=0.85, iridescence=0.08, film=0.8)),
    "floor":         ("floor", dict(tint="Color(0.3, 0.42, 0.36, 1)", scale=0.22, normal_depth=1.0, rough_lo=0.04, rough_hi=0.4, iridescence=0.3, film=0.9,
                                    glow_color="Color(1, 0.58, 0.16, 1)", glow=0.08, glow_cut=0.25)),
    "comb":          ("comb", dict(tint="Color(1, 0.9, 0.75, 1)", scale=0.32, normal_depth=1.4, rough_lo=0.2, rough_hi=0.6,
                                   glow_color="Color(1, 0.55, 0.14, 1)", glow=0.9, glow_cut=0.45)),
    "comb_dim":      ("comb", dict(tint="Color(0.6, 0.5, 0.38, 1)", scale=0.32, normal_depth=1.4, rough_lo=0.2, rough_hi=0.6,
                                   glow_color="Color(1, 0.5, 0.12, 1)", glow=0.45, glow_cut=0.45)),
    "silk":          ("silk", dict(tint="Color(1, 0.96, 0.88, 1)", scale=1.2, normal_depth=0.8, rough_lo=0.35, rough_hi=0.7)),
    "ink":           ("carapace", dict(tint="Color(0.05, 0.05, 0.06, 1)", scale=2.0, normal_depth=0.2, rough_lo=0.02, rough_hi=0.1, iridescence=0.3, film=1.6)),
}
# amber.gdshader: name: texture, use_uv, scale, tint, core, through, rim, rough, pulse
AMBER_MATS = {
    "amber":    ("amber", False, 0.9, "Color(1, 0.75, 0.35, 1)", "Color(1, 0.66, 0.25, 1)", 1.0, 0.6, 0.08, 0.0),
    "molt":     ("membrane", False, 0.35, "Color(0.55, 0.42, 0.26, 1)", "Color(0.8, 0.55, 0.25, 1)", 0.22, 0.45, 0.25, 0.0),
    "wax":      ("comb", False, 0.6, "Color(1, 0.85, 0.55, 1)", "Color(1, 0.7, 0.3, 1)", 0.25, 0.3, 0.35, 0.0),
    "membrane": ("membrane", True, 1.0, "Color(0.85, 0.6, 0.35, 1)", "Color(0.9, 0.5, 0.18, 1)", 0.9, 0.4, 0.3, 0.0),
    "fungus":   ("silk", False, 1.5, "Color(0.7, 1, 0.95, 1)", "Color(0.45, 1, 0.85, 1)", 2.4, 1.4, 0.4, 0.12),
    "tapestry": ("tapestry_a", True, 1.0, "Color(1, 0.95, 0.85, 1)", "Color(0.5, 0.4, 0.28, 1)", 0.18, 0.0, 0.8, 0.0),
    "eye":      ("eye", False, 0.05, "Color(1, 0.7, 0.3, 1)", "Color(1, 0.55, 0.12, 1)", 1.2, 0.8, 0.1, 0.0),
}


def tex_path(name, kind):
    return f"{T}{name}/{name}_{kind}.png"


os.makedirs(D, exist_ok=True)
for name, (tex, p) in HIVE_MATS.items():
    lines = ["shader = ExtResource(\"s\")",
             "shader_parameter/albedo_tex = ExtResource(\"a\")",
             "shader_parameter/normal_tex = ExtResource(\"n\")",
             "shader_parameter/rough_tex = ExtResource(\"r\")",
             "shader_parameter/height_tex = ExtResource(\"h\")"]
    lines += [f"shader_parameter/{k} = {v}" for k, v in p.items()]
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=6 format=3]

[ext_resource type="Shader" path="{HIVE}" id="s"]
[ext_resource type="Texture2D" path="{tex_path(tex, 'albedo')}" id="a"]
[ext_resource type="Texture2D" path="{tex_path(tex, 'normal')}" id="n"]
[ext_resource type="Texture2D" path="{tex_path(tex, 'roughness')}" id="r"]
[ext_resource type="Texture2D" path="{tex_path(tex, 'height')}" id="h"]

[resource]
resource_name = "{name}"
""" + "\n".join(lines) + "\n")
for name, (tex, uv, scale, tint, core, through, rim, rough, pulse) in AMBER_MATS.items():
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=3 format=3]

[ext_resource type="Shader" path="{AMBER}" id="s"]
[ext_resource type="Texture2D" path="{tex_path(tex, 'albedo')}" id="a"]

[resource]
resource_name = "{name}"
shader = ExtResource("s")
shader_parameter/albedo_tex = ExtResource("a")
shader_parameter/use_uv = {"true" if uv else "false"}
shader_parameter/scale = {scale}
shader_parameter/tint = {tint}
shader_parameter/core = {core}
shader_parameter/through = {through}
shader_parameter/rim = {rim}
shader_parameter/rough = {rough}
shader_parameter/pulse = {pulse}
""")
print("wrote", len(HIVE_MATS) + len(AMBER_MATS))
