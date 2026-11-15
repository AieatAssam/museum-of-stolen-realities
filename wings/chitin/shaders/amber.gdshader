// Translucent backlit stuff: amber, shed husk, wing membrane, wax and the fungus lamps. Opaque (cheap,
// sorts cleanly) with a faked subsurface: light that would come through the far side shows as an
// emissive core, strongest where the surface is seen face-on and thin, plus a rim of transmitted glow.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform bool use_uv = false;         // membranes and tapestries map their panel; the rest triplanar
uniform float scale = 0.6;
uniform vec4 tint : source_color = vec4(1.0, 0.62, 0.18, 1.0);
uniform vec4 core : source_color = vec4(1.0, 0.55, 0.12, 1.0);
uniform float through = 1.2;         // transmitted (emissive) light
uniform float rim = 0.6;
uniform float rough = 0.15;
uniform float pulse = 0.0;           // fungus breathe (0 off)

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 t;
	if (use_uv) {
		t = texture(albedo_tex, UV).rgb;
	} else {
		vec3 w = pow(abs(wnrm), vec3(4.0));
		w /= (w.x + w.y + w.z);
		vec3 p = wpos * scale;
		t = texture(albedo_tex, p.zy).rgb * w.x + texture(albedo_tex, p.xz).rgb * w.y + texture(albedo_tex, p.xy).rgb * w.z;
	}
	float ndv = abs(dot(NORMAL, VIEW));
	ALBEDO = t * tint.rgb * 0.5;
	ROUGHNESS = rough;
	SPECULAR = 0.6;
	float b = 1.0 + pulse * sin(TIME * 1.3 + wpos.x * 0.7 + wpos.z * 0.4);
	EMISSION = core.rgb * t * through * b * (0.35 + 0.65 * ndv) + core.rgb * rim * pow(1.0 - ndv, 3.0) * b;
}
