"""Write the art-pass StandardMaterial3D resources into wings/aria/materials/ (names = Blender material names).
  python3 wings/aria/tools/make_materials.py
"""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "materials")
T = "res://wings/aria/textures/"
A = "res://assets/textures/"


def tex_set(base, name):
    return {"albedo_texture": f"{base}{name}/{name}_albedo.png", "normal_texture": f"{base}{name}/{name}_normal.png",
            "roughness_texture": f"{base}{name}/{name}_roughness.png"}


def relief(base, name):
    """Normal + roughness only: the generated gilt albedos are orange-brown, so gold takes a flat yellow albedo."""
    return {k: v for k, v in tex_set(base, name).items() if k != "albedo_texture"}


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, tuple):
        return "Color(%s)" % ", ".join("%g" % x for x in (v + (1.0,) if len(v) == 3 else v))
    if isinstance(v, (int, float)):
        return "%g" % v
    return v


def write(name, props, tri=None, cull=None):
    ext = [(k, v) for k, v in props.items() if k.endswith("_texture")]
    lines = ['[gd_resource type="StandardMaterial3D" load_steps=%d format=3]' % (len(ext) + 1), ""]
    ids = {}
    for i, (k, path) in enumerate(ext):
        ids[k] = "t%d" % i
        lines.append('[ext_resource type="Texture2D" path="%s" id="t%d"]' % (path, i))
    lines += ["", "[resource]", 'resource_name = "%s"' % name]
    for k, v in props.items():
        if k in ids:
            lines.append('%s = ExtResource("%s")' % (k, ids[k]))
            if k == "normal_texture":
                lines.append("normal_enabled = true")
        else:
            lines.append("%s = %s" % (k, fmt(v)))
    if cull is not None:  # BaseMaterial3D.CullMode: 0 back, 1 front, 2 disabled
        lines.append("cull_mode = %d" % cull)
    if tri:
        lines += ["uv1_scale = Vector3(%g, %g, %g)" % (tri, tri, tri), "uv1_triplanar = true", "uv1_triplanar_sharpness = 4.0", "uv1_world_triplanar = true"]
    lines.append("texture_filter = 5")
    open(os.path.join(ROOT, name + ".tres"), "w").write("\n".join(lines) + "\n")


def main():
    # palette: yellow gold, oxblood velvet, cream marble, near-black ebony; teal marble and water as the counter-colour.
    # Aria-local overrides of the shared core materials (MAT_DIRS looks here first).
    write("gilt", {**relief(A, "gilt"), "albedo_color": (1.0, 0.8, 0.42), "normal_scale": 1.0, "metallic": 1.0, "roughness": 0.42,
                   "metallic_specular": 0.7}, tri=1.1)
    write("velvet", {**tex_set(A, "velvet"), "albedo_color": (0.46, 0.05, 0.08), "normal_scale": 0.6, "roughness": 1.0,
                     "rim_enabled": True, "rim": 0.55, "rim_tint": 0.35}, tri=1.5)
    write("marble_ivory", {**tex_set(A, "marble_ivory"), "albedo_color": (1.0, 0.96, 0.86), "normal_scale": 0.4, "roughness": 0.32,
                           "metallic_specular": 0.6}, tri=0.6)
    write("ebony", {**tex_set(A, "ebony"), "albedo_color": (0.3, 0.24, 0.22), "normal_scale": 0.6, "roughness": 0.45,
                    "clearcoat_enabled": True, "clearcoat": 0.4}, tri=1.0)
    write("marble_teal", {**tex_set(T, "marble_teal"), "albedo_color": (0.62, 0.86, 0.95), "normal_scale": 0.35, "roughness": 0.4, "metallic_specular": 0.6}, tri=0.45)
    write("damask_ox", {**tex_set(T, "damask_ox"), "albedo_color": (0.72, 0.5, 0.52), "normal_scale": 0.8, "roughness": 0.85}, tri=1.25)
    write("boards", {**tex_set(T, "boards"), "albedo_color": (0.75, 0.68, 0.62), "normal_scale": 0.8, "roughness": 0.8}, tri=0.4)
    write("gilt_orn", {**relief(T, "ornament"), "albedo_color": (1.0, 0.8, 0.42), "normal_scale": 2.0, "metallic": 1.0, "roughness": 0.5, "metallic_specular": 0.7}, tri=1.1)
    write("velvet_drape", {**tex_set(T, "velvet"), "albedo_color": (0.5, 0.06, 0.09), "normal_scale": 0.6, "roughness": 1.0,
                           "rim_enabled": True, "rim": 0.5, "rim_tint": 0.6}, tri=0.5, cull=2)
    write("pipe_tin", {**tex_set(A, "brass"), "albedo_color": (0.78, 0.8, 0.82), "normal_scale": 0.3, "metallic": 1.0, "roughness": 0.55}, tri=1.5)
    write("bronze", {**tex_set(A, "brass"), "albedo_color": (0.5, 0.36, 0.22), "normal_scale": 0.6, "metallic": 0.9, "roughness": 0.8}, tri=1.2)
    write("iron", {**tex_set(A, "ebony"), "albedo_color": (0.12, 0.13, 0.14), "metallic": 0.8, "roughness": 0.9}, tri=1.0)
    write("rope", {**tex_set(T, "boards"), "albedo_color": (0.75, 0.62, 0.45), "roughness": 1.0}, tri=3.0)
    write("canvas", {**tex_set(A, "plaster"), "albedo_color": (0.55, 0.47, 0.36), "roughness": 1.0}, tri=1.0)
    write("cello_wood", {**tex_set(T, "boards"), "albedo_color": (0.85, 0.42, 0.2), "roughness": 0.6, "clearcoat_enabled": True, "clearcoat": 0.6}, tri=1.5)
    write("ash", {**tex_set(T, "boards"), "albedo_color": (1.0, 0.9, 0.75), "roughness": 0.5}, tri=3.0)
    write("pale", {**tex_set(A, "plaster"), "albedo_color": (0.62, 0.72, 0.7), "roughness": 0.9, "rim_enabled": True, "rim": 0.6, "rim_tint": 0.3,
                   "emission_enabled": True, "emission": (0.05, 0.12, 0.11), "emission_energy_multiplier": 1.0}, tri=1.0)
    write("pale_cloth", {**tex_set(A, "plaster"), "albedo_color": (0.55, 0.64, 0.62), "roughness": 1.0, "rim_enabled": True, "rim": 0.6, "rim_tint": 0.3}, tri=1.0, cull=2)
    write("pale_hair", {**tex_set(A, "plaster"), "albedo_color": (0.75, 0.8, 0.76), "roughness": 0.8}, tri=3.0, cull=2)
    write("lamp_glow", {"albedo_color": (1.0, 0.85, 0.6), "emission_enabled": True, "emission": (1.0, 0.68, 0.36), "emission_energy_multiplier": 6.0, "roughness": 0.3})
    write("flame", {"albedo_color": (1.0, 0.8, 0.5), "emission_enabled": True, "emission": (1.0, 0.62, 0.25), "emission_energy_multiplier": 12.0, "shading_mode": 0})
    write("wax", {"albedo_color": (0.95, 0.9, 0.8), "roughness": 0.5, "emission_enabled": True, "emission": (0.4, 0.3, 0.2), "emission_energy_multiplier": 0.4})
    write("crystal", {"albedo_color": (0.85, 0.97, 1.0, 0.35), "transparency": 1, "metallic": 0.4, "metallic_specular": 1.0, "roughness": 0.02,
                      "emission_enabled": True, "emission": (0.55, 0.85, 0.9), "emission_energy_multiplier": 0.6, "rim_enabled": True, "rim": 1.0}, cull=2)
    write("fragment_crystal", {"albedo_color": (0.8, 1.0, 0.95, 0.8), "transparency": 1, "roughness": 0.05, "emission_enabled": True,
                               "emission": (0.5, 1.0, 0.9), "emission_energy_multiplier": 5.0, "rim_enabled": True, "rim": 1.0})
    write("mirror", {"albedo_color": (0.32, 0.42, 0.42), "metallic": 1.0, "roughness": 0.08})
    write("backdrop", {"albedo_texture": T + "backdrop.png", "albedo_color": (0.8, 0.8, 0.8), "roughness": 0.95,
                       "emission_enabled": True, "emission_texture": T + "backdrop.png", "emission": (1, 1, 1), "emission_energy_multiplier": 0.0}, cull=2)
    write("ceiling_fresco", {"albedo_texture": T + "ceiling.png", "roughness": 0.9, "emission_enabled": True, "emission_texture": T + "ceiling.png",
                             "emission": (1, 1, 1), "emission_energy_multiplier": 0.35}, cull=2)
    write("dome_painted", {"albedo_texture": T + "dome.png", "albedo_color": (0.8, 0.8, 0.8), "roughness": 0.85, "emission_enabled": True, "emission_texture": T + "dome.png",
                           "emission": (1, 1, 1), "emission_energy_multiplier": 0.0}, cull=2)
    write("score_paper", {"albedo_texture": T + "score.png", "albedo_color": (0.72, 0.66, 0.56), "roughness": 0.9}, cull=2)
    # La Sirena: a drowned voice made visible - pale teal skin lit from within, a sea-glass gown, dark drifting hair
    write("sirena_skin", {"albedo_color": (0.78, 0.95, 0.9), "roughness": 0.5, "rim_enabled": True, "rim": 1.0, "rim_tint": 0.2,
                          "emission_enabled": True, "emission": (0.45, 0.95, 0.85), "emission_energy_multiplier": 0.5,
                          "subsurf_scatter_enabled": True, "subsurf_scatter_strength": 0.6})
    write("sirena_gown", {"albedo_color": (0.35, 0.78, 0.74), "roughness": 0.3, "metallic_specular": 0.8, "rim_enabled": True, "rim": 1.0,
                          "rim_tint": 0.1, "emission_enabled": True, "emission": (0.2, 0.75, 0.68), "emission_energy_multiplier": 0.45}, cull=2)
    write("sirena_hair", {"albedo_color": (0.05, 0.16, 0.16), "roughness": 0.6, "rim_enabled": True, "rim": 0.8, "rim_tint": 0.0,
                          "emission_enabled": True, "emission": (0.1, 0.45, 0.42), "emission_energy_multiplier": 0.25}, cull=2)


if __name__ == "__main__":
    main()
