shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;
// Exhibit 0's shell: cut crystal, nearly clear at the centre of each facet and gilded by fresnel at
// the edges, so the lit world inside reads through it. A faint frost of etched filigree catches light.
#include "res://core/shaders/noise.gdshaderinc"

uniform vec4 tint : source_color = vec4(1.0, 0.86, 0.62, 1.0);
uniform float clarity = 0.93;
uniform float glow = 1.0;

varying vec3 opos;

void vertex() { opos = VERTEX; }

void fragment() {
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.6);
	vec3 d = normalize(opos);
	// etched filigree: thin swirling lines on the glass
	float fil = n_fbm(d.xy * 7.0 + d.z * 3.0);
	float line = smoothstep(0.02, 0.0, abs(fract(fil * 6.0) - 0.5) - 0.46);
	ALBEDO = mix(vec3(0.01), tint.rgb * 0.6, line * 0.6);
	METALLIC = 0.0;
	ROUGHNESS = mix(0.06, 0.3, line);
	SPECULAR = 0.55;
	ALPHA = clamp(1.0 - clarity + f * 0.4 + line * 0.25, 0.0, 0.7);
	EMISSION = tint.rgb * (f * 0.12 + line * 0.3) * glow;
	RIM = 0.4;
	RIM_TINT = 0.6;
}
