"""Writes the Unfinished Wing's surface materials into wings/paint/materials/. Run from the repo root:
    python3 wings/paint/tools/make_materials.py
One table for the wing's whole palette. Names starting p_ are the Blender contract (object space, so
props that move keep their brushwork); g_ are the world-space ground and wall finishes paint.gd uses.
Shadow hue per material is the painter's choice for its dark side, never grey."""
import os

D = os.path.join(os.path.dirname(__file__), "..", "materials")
T = "res://wings/paint/textures/paint_"
VIOLET, BLUE, UMBER, TEAL = "0.42, 0.36, 0.66", "0.30, 0.38, 0.72", "0.45, 0.25, 0.30", "0.20, 0.40, 0.50"

# name: texture, colour, colour2, shade, tiles/m, normal, tex_value, mix, rough, gloss, emission, object space
M = {
    # props (Blender material names)
    "p_bark":       ("impasto", "0.36, 0.20, 0.11", "0.62, 0.30, 0.42", VIOLET, 1.2, 1.6, 0.8, 0.55, 0.55, 0.2, 0.0, True),
    "p_leaf":       ("impasto", "0.12, 0.42, 0.20", "0.20, 0.55, 0.62", BLUE, 1.5, 1.4, 0.7, 0.55, 0.5, 0.25, 0.0, True),
    "p_leaf_light": ("impasto", "0.55, 0.72, 0.18", "0.96, 0.82, 0.30", TEAL, 1.5, 1.4, 0.6, 0.6, 0.45, 0.25, 0.04, True),
    "p_blossom":    ("impasto", "0.98, 0.92, 0.90", "1.0, 0.72, 0.80", VIOLET, 2.0, 1.2, 0.5, 0.5, 0.45, 0.2, 0.06, True),
    "p_stone":      ("knife", "0.78, 0.68, 0.62", "0.62, 0.56, 0.78", VIOLET, 0.8, 1.6, 0.7, 0.6, 0.65, 0.0, 0.0, True),
    "p_varnish":    ("varnish", "0.85, 0.52, 0.12", "1.0, 0.75, 0.30", UMBER, 1.2, 0.8, 0.6, 0.4, 0.2, 0.9, 0.05, True),
    "p_wood":       ("knife", "0.62, 0.42, 0.22", "0.85, 0.60, 0.30", VIOLET, 1.4, 1.3, 0.7, 0.5, 0.6, 0.1, 0.0, True),
    "p_wood_dark":  ("knife", "0.30, 0.17, 0.10", "0.45, 0.22, 0.20", VIOLET, 1.4, 1.2, 0.6, 0.45, 0.4, 0.4, 0.0, True),
    "p_plaster":    ("knife", "0.95, 0.90, 0.80", "0.98, 0.80, 0.66", VIOLET, 0.9, 1.4, 0.6, 0.5, 0.7, 0.0, 0.0, True),
    "p_roof":       ("impasto", "0.82, 0.36, 0.20", "0.95, 0.55, 0.28", UMBER, 1.0, 1.5, 0.7, 0.5, 0.6, 0.1, 0.0, True),
    "p_red":        ("stroke", "0.86, 0.14, 0.08", "1.0, 0.40, 0.18", UMBER, 2.0, 1.4, 0.6, 0.4, 0.2, 0.9, 0.05, True),
    "p_blue":       ("stroke", "0.08, 0.18, 0.72", "0.25, 0.45, 0.95", BLUE, 2.0, 1.4, 0.6, 0.4, 0.2, 0.9, 0.05, True),
    "p_yellow":     ("stroke", "0.98, 0.76, 0.12", "1.0, 0.92, 0.45", UMBER, 2.0, 1.4, 0.6, 0.4, 0.2, 0.9, 0.2, True),
    "p_violet":     ("knife", "0.42, 0.18, 0.62", "0.58, 0.30, 0.75", BLUE, 3.0, 1.4, 0.6, 0.4, 0.4, 0.3, 0.0, True),
    "p_steel":      ("knife", "0.62, 0.64, 0.70", "0.80, 0.78, 0.86", BLUE, 3.0, 0.8, 0.4, 0.4, 0.25, 0.6, 0.0, True),
    "p_brass":      ("gilt", "0.86, 0.62, 0.24", "1.0, 0.80, 0.40", UMBER, 3.0, 0.8, 0.5, 0.4, 0.3, 0.6, 0.0, True),
    "p_gilt":       ("gilt", "0.92, 0.68, 0.26", "1.0, 0.84, 0.45", UMBER, 0.6, 1.0, 0.8, 0.35, 0.3, 0.5, 0.12, True),
    "p_canvas":     ("canvas", "0.86, 0.76, 0.58", "0.92, 0.84, 0.70", UMBER, 2.0, 0.8, 0.8, 0.3, 0.85, 0.0, 0.0, True),
    "p_graphite":   ("pencil", "0.28, 0.28, 0.32", "0.40, 0.40, 0.44", BLUE, 3.0, 0.6, 0.5, 0.3, 0.4, 0.3, 0.0, True),
    "p_skin":       ("impasto", "0.90, 0.68, 0.54", "0.98, 0.78, 0.66", VIOLET, 0.8, 1.2, 0.5, 0.5, 0.55, 0.1, 0.0, True),
    "p_skin_shadow": ("impasto", "0.62, 0.40, 0.42", "0.50, 0.36, 0.55", BLUE, 0.8, 1.2, 0.5, 0.5, 0.55, 0.1, 0.0, True),
    "p_robe":       ("stroke", "0.62, 0.62, 0.72", "0.80, 0.72, 0.78", BLUE, 0.4, 1.4, 0.6, 0.55, 0.5, 0.1, 0.0, True),
    "p_robe_light": ("stroke", "0.90, 0.86, 0.82", "0.98, 0.88, 0.76", VIOLET, 0.4, 1.4, 0.6, 0.55, 0.5, 0.1, 0.0, True),
    "p_hair":       ("stroke", "0.30, 0.20, 0.18", "0.50, 0.30, 0.24", VIOLET, 0.6, 1.4, 0.6, 0.5, 0.4, 0.2, 0.0, True),
    # world finishes (paint.gd COL keys map to these)
    "g_primed":     ("knife", "0.95, 0.86, 0.68", "1.0, 0.66, 0.40", VIOLET, 0.13, 1.1, 0.75, 0.7, 0.62, 0.0, 0.0, False),
    "g_weave":      ("canvas", "0.24, 0.15, 0.10", "0.30, 0.18, 0.26", UMBER, 0.35, 1.8, 0.9, 0.4, 0.9, 0.0, 0.0, False),
    "g_goal":       ("impasto", "0.95, 0.68, 0.24", "1.0, 0.86, 0.48", UMBER, 0.18, 1.6, 0.7, 0.6, 0.45, 0.2, 0.12, False),
    "g_crust":      ("knife", "0.62, 0.45, 0.30", "0.78, 0.52, 0.42", VIOLET, 0.15, 1.6, 0.7, 0.5, 0.6, 0.1, 0.0, False),
    "g_wall":       ("gesso", "0.90, 0.86, 0.76", "0.86, 0.78, 0.84", VIOLET, 0.2, 1.4, 0.6, 0.4, 0.75, 0.0, 0.0, False),
    "g_frame":      ("gilt", "0.92, 0.68, 0.26", "1.0, 0.84, 0.45", UMBER, 0.6, 1.0, 0.8, 0.35, 0.3, 0.5, 0.02, False),
    "g_museum":     ("knife", "0.58, 0.30, 0.13", "0.66, 0.38, 0.17", UMBER, 0.2, 0.3, 0.15, 0.3, 0.2, 0.8, 0.0, False),
    "g_museum_wall": ("plaster", "0.74, 0.68, 0.60", "0.66, 0.62, 0.70", VIOLET, 0.05, 0.6, 0.5, 0.3, 0.85, 0.0, 0.0, False),
    "g_gallery":    ("plaster", "0.60, 0.59, 0.57", "0.56, 0.55, 0.55", "0.40, 0.40, 0.42", 0.05, 0.6, 0.5, 0.3, 0.85, 0.0, 0.0, False),
    "g_figure":     ("stroke", "0.80, 0.62, 0.52", "0.70, 0.66, 0.78", BLUE, 0.3, 1.4, 0.6, 0.5, 0.5, 0.1, 0.0, False),
    "g_varnish":    ("varnish", "0.85, 0.52, 0.12", "1.0, 0.75, 0.30", UMBER, 0.3, 0.9, 0.6, 0.4, 0.2, 0.9, 0.08, False),
}

for name, (tex, col, col2, shade, tiles, ns, tv, mx, rough, gloss, em, obj) in M.items():
    with open(os.path.join(D, name + ".tres"), "w") as f:
        f.write(f"""[gd_resource type="ShaderMaterial" load_steps=4 format=3]

[ext_resource type="Shader" path="res://wings/paint/shaders/paint_surface.gdshader" id="1"]
[ext_resource type="Texture2D" path="{T}{tex}_albedo.png" id="2"]
[ext_resource type="Texture2D" path="{T}{tex}_normal.png" id="3"]

[resource]
shader = ExtResource("1")
shader_parameter/colour = Color({col}, 1)
shader_parameter/colour2 = Color({col2}, 1)
shader_parameter/shade = Color({shade}, 1)
shader_parameter/detail_albedo = ExtResource("2")
shader_parameter/detail_normal = ExtResource("3")
shader_parameter/tiles_per_m = {tiles}
shader_parameter/normal_strength = {ns}
shader_parameter/tex_value = {tv}
shader_parameter/mix_amount = {mx}
shader_parameter/rough = {rough}
shader_parameter/gloss = {gloss}
shader_parameter/emission_gain = {em}
shader_parameter/object_space = {"true" if obj else "false"}
""")
print(len(M), "materials")
