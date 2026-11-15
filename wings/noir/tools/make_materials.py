"""Writes the noir wing's materials (wings/noir/materials/*.tres). Run from the repo root:
    python3 wings/noir/tools/make_materials.py
One table so the wing's value structure is tuned in one place. Albedo is authored in colour (the
mono pass in noir_mono.gdshader takes it to black and white; the fragment's reveal gives it back)."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
T = "res://wings/noir/textures/"
A = "res://assets/textures/"

# name: (texture base or None, albedo tint, uv scale (tiles per metre), roughness, metallic, normal strength, extra lines)
TEX = {
    "brick":      (T + "brick", "0.62, 0.52, 0.48", 0.45, 1.0, 0.0, 1.0, ""),
    "brick_dark": (T + "brick", "0.34, 0.3, 0.29", 0.45, 1.0, 0.0, 1.0, ""),
    "stone":      (A + "plaster/plaster", "0.36, 0.35, 0.33", 0.6, 0.9, 0.0, 0.8, ""),
    "pavement":   (T + "pavement", "0.7, 0.7, 0.7", 0.33, 0.55, 0.0, 0.6, ""),
    "roof":       (T + "roof", "0.55, 0.55, 0.55", 0.3, 0.75, 0.0, 0.8, ""),
    "floorboards": (T + "floorboards", "0.6, 0.5, 0.42", 0.5, 0.55, 0.0, 0.7, ""),
    "wood":       (T + "floorboards", "0.42, 0.3, 0.22", 1.2, 0.45, 0.0, 0.5, ""),
    "iron":       (T + "steel", "0.38, 0.38, 0.4", 0.8, 0.55, 0.6, 0.8, ""),
    "steel":      (T + "steel", "0.55, 0.55, 0.57", 0.4, 0.5, 0.5, 1.0, ""),
    "carpet":     (T + "carpet", "0.75, 0.6, 0.6", 0.6, 0.95, 0.0, 0.6, ""),
    "plaster":    (A + "plaster/plaster", "0.7, 0.68, 0.64", 0.5, 0.95, 0.0, 0.6, ""),
    "velvet":     (A + "velvet/velvet", "0.34, 0.16, 0.16", 1.5, 1.0, 0.0, 0.8, "rim_enabled = true\nrim = 0.5\nrim_tint = 0.6\n"),
    "gilt":       (A + "gilt/gilt", "0.6, 0.5, 0.35", 1.0, 0.35, 0.9, 0.6, ""),
}
# flat materials: name: (albedo, roughness, metallic, extra)
FLAT = {
    "sash":         ("0.08, 0.08, 0.08", 0.5, 0.0, ""),
    "paint":        ("0.03, 0.03, 0.035", 0.12, 0.3, "clearcoat_enabled = true\nclearcoat = 1.0\nclearcoat_roughness = 0.05\n"),
    "chrome":       ("0.8, 0.8, 0.82", 0.08, 1.0, ""),
    "tyre":         ("0.03, 0.03, 0.03", 0.8, 0.0, ""),
    "zinc":         ("0.5, 0.5, 0.52", 0.35, 0.8, ""),
    "coat":         ("0.2, 0.19, 0.17", 0.9, 0.0, ""),
    "hat":          ("0.09, 0.085, 0.08", 0.85, 0.0, ""),
    "skin":         ("0.55, 0.45, 0.4", 0.6, 0.0, ""),
    "shirt":        ("0.8, 0.8, 0.78", 0.8, 0.0, ""),
    "paper":        ("0.86, 0.83, 0.76", 0.85, 0.0, ""),
    "card_red":     ("0.6, 0.05, 0.05", 0.6, 0.0, ""),
    "felt":         ("0.08, 0.2, 0.1", 0.95, 0.0, ""),
    "film":         ("0.05, 0.04, 0.03", 0.25, 0.0, ""),
    "black":        ("0.015, 0.015, 0.015", 0.9, 0.0, ""),
    "canvas":       ("0.25, 0.25, 0.24", 0.95, 0.0, ""),
    "screen":       ("0.7, 0.7, 0.7", 0.9, 0.0, "emission_enabled = true\nemission = Color(0.55, 0.57, 0.6, 1)\nemission_energy_multiplier = 0.35\n"),
    "awning":       ("0.18, 0.18, 0.18", 0.9, 0.0, ""),
    # window glass: dark mirror with a faint lit-room glow; unlit windows read black and reflect
    "window_glass": ("0.02, 0.02, 0.025", 0.05, 0.6, ""),
    "window_lit":   ("0.9, 0.82, 0.62", 0.3, 0.0, "emission_enabled = true\nemission = Color(1, 0.86, 0.6, 1)\nemission_energy_multiplier = 2.6\n"),
    # light sources (bloom above the glow threshold)
    "glass":        ("1, 0.96, 0.88", 0.2, 0.0, "emission_enabled = true\nemission = Color(1, 0.93, 0.8, 1)\nemission_energy_multiplier = 6.0\n"),
    "bulb":         ("1, 0.95, 0.85", 0.2, 0.0, "emission_enabled = true\nemission = Color(1, 0.9, 0.75, 1)\nemission_energy_multiplier = 9.0\n"),
    "neon_red":     ("1, 0.1, 0.12", 0.3, 0.0, "emission_enabled = true\nemission = Color(1, 0.02, 0.04, 1)\nemission_energy_multiplier = 1.4\n"),
    "neon_tube_off": ("0.25, 0.08, 0.08", 0.2, 0.0, ""),
    "diner_glow":   ("1, 0.9, 0.7", 0.4, 0.0, "emission_enabled = true\nemission = Color(1, 0.88, 0.66, 1)\nemission_energy_multiplier = 0.35\n"),
    "beam_lens":    ("1, 1, 1", 0.1, 0.0, "emission_enabled = true\nemission = Color(1, 0.98, 0.92, 1)\nemission_energy_multiplier = 12.0\n"),
    "silhouette":   ("0.0, 0.0, 0.0", 1.0, 0.0, "shading_mode = 0\n"),
    "lamp":         ("1, 0.97, 0.9", 0.3, 0.0, "emission_enabled = true\nemission = Color(1, 0.95, 0.85, 1)\nemission_energy_multiplier = 1.6\n"),
    "lamp_letter":  ("0.02, 0.02, 0.02", 0.6, 0.0, ""),
    "iron_grate":   ("0.12, 0.12, 0.13", 0.6, 0.6, ""),
    # clear plate glass: the street shows in it, the lit room shows through it
    "glass_frosted": ("0.5, 0.5, 0.48", 0.6, 0.0, "transparency = 1\nalbedo_color = Color(0.5, 0.5, 0.48, 0.6)\nemission_enabled = true\nemission = Color(1, 0.92, 0.78, 1)\nemission_energy_multiplier = 0.05\n"),
    "window_clear": ("0.06, 0.065, 0.07", 0.02, 0.0, "transparency = 1\nalbedo_color = Color(0.06, 0.065, 0.07, 0.22)\nspecular_mode = 0\nmetallic_specular = 1.0\n"),
}
# textured one-offs written by hand
SPECIAL = {
    "frame_picture": """[gd_resource type="StandardMaterial3D" load_steps=2 format=3]

[ext_resource type="Texture2D" path="res://wings/noir/textures/frame_picture.png" id="t"]

[resource]
resource_name = "frame_picture"
albedo_texture = ExtResource("t")
roughness = 0.3
emission_enabled = true
emission_texture = ExtResource("t")
emission_energy_multiplier = 2.5
uv1_triplanar = true
uv1_scale = Vector3(2.4, 2.4, 2.4)
""",
}


def write(name, body, ext=""):
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(body)


os.makedirs(D, exist_ok=True)
for name, (tex, tint, uv, rough, metal, nrm, extra) in TEX.items():
    write(name, f"""[gd_resource type="StandardMaterial3D" load_steps=4 format=3]

[ext_resource type="Texture2D" path="{tex}_albedo.png" id="a"]
[ext_resource type="Texture2D" path="{tex}_normal.png" id="n"]
[ext_resource type="Texture2D" path="{tex}_roughness.png" id="r"]

[resource]
resource_name = "{name}"
albedo_color = Color({tint}, 1)
albedo_texture = ExtResource("a")
normal_enabled = true
normal_scale = {nrm}
normal_texture = ExtResource("n")
roughness_texture = ExtResource("r")
roughness_texture_channel = 0
roughness = {rough}
metallic = {metal}
uv1_scale = Vector3({uv}, {uv}, {uv})
uv1_triplanar = true
uv1_triplanar_sharpness = 6.0
uv1_world_triplanar = true
texture_filter = 5
{extra}""")
for name, (alb, rough, metal, extra) in FLAT.items():
    write(name, f"""[gd_resource type="StandardMaterial3D" format=3]

[resource]
resource_name = "{name}"
albedo_color = Color({alb}, 1)
roughness = {rough}
metallic = {metal}
{extra}""")

# wet ground (wet_ground.gdshader): name: (texture base, uv scale, tint, puddles 0..1, base wetness)
WET = {
    "wet_asphalt": (T + "asphalt", 0.3, "0.4, 0.4, 0.4", 0.85, 0.95),
    "wet_cobble":  (T + "cobble", 0.55, "0.6, 0.6, 0.6", 0.6, 0.8),
    "wet_pavement": (T + "pavement", 0.33, "0.7, 0.7, 0.7", 0.45, 0.7),
    "wet_roof":    (T + "roof", 0.3, "0.5, 0.5, 0.5", 0.6, 0.75),
    "wet_floorboards": (T + "floorboards", 0.5, "0.55, 0.45, 0.38", 0.0, 0.45),
    "wet_carpet":  (T + "carpet", 0.6, "0.6, 0.45, 0.45", 0.25, 0.1),
}
for name, (tex, uv, tint, puddles, wet) in WET.items():
    write(name, f"""[gd_resource type="ShaderMaterial" load_steps=5 format=3]

[ext_resource type="Shader" path="res://wings/noir/shaders/wet_ground.gdshader" id="s"]
[ext_resource type="Texture2D" path="{tex}_albedo.png" id="a"]
[ext_resource type="Texture2D" path="{tex}_normal.png" id="n"]
[ext_resource type="Texture2D" path="{tex}_roughness.png" id="r"]

[resource]
resource_name = "{name}"
shader = ExtResource("s")
shader_parameter/albedo_tex = ExtResource("a")
shader_parameter/normal_tex = ExtResource("n")
shader_parameter/rough_tex = ExtResource("r")
shader_parameter/uv_scale = {uv}
shader_parameter/tint = Color({tint}, 1)
shader_parameter/puddles = {puddles}
shader_parameter/wetness = {wet}
""")
for name, body in SPECIAL.items():
    write(name, body)
print("wrote", len(TEX) + len(FLAT) + len(WET) + len(SPECIAL))
