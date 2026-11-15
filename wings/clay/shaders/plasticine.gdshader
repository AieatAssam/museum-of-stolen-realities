shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
// Hand-worked plasticine for every modelled prop: object-space triplanar fingerprints and smears
// (so moving props never swim), kneaded colour streaks, a soft waxy sheen and subsurface warmth.

#include "res://wings/clay/shaders/triplanar.gdshaderinc"

uniform vec3 colour : source_color = vec3(0.8, 0.45, 0.25);
uniform vec3 streak : source_color = vec3(1.0, 0.9, 0.8);   // the lighter colour kneaded in
uniform float streak_amount : hint_range(0.0, 1.0) = 0.18;
uniform sampler2D detail_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D detail_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D detail_rough : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float tiles_per_m = 1.6;
uniform float normal_strength = 1.0;
uniform float grime = 0.35;          // how much of the texture's own value darkens the colour
uniform float rough_lo = 0.38;
uniform float rough_hi = 0.62;
uniform float sss = 0.35;
uniform float emission_gain = 0.0;   // lit windows, lamp bulbs

varying vec3 v_p;
varying vec3 v_n;

void vertex() {
	vec3 s = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
	v_p = VERTEX * s;
	v_n = NORMAL;
}

void fragment() {
	vec3 n = normalize(v_n);
	vec3 w = tri_weights(n);
	vec3 p = v_p * tiles_per_m;
	vec3 tex = tri_sample(detail_albedo, p, w).rgb;
	float lum = dot(tex, vec3(0.299, 0.587, 0.114));
	float k = tri_vnoise(v_p * 2.3) * 0.65 + tri_vnoise(v_p * 7.1) * 0.35;
	vec3 col = mix(colour, colour * streak * 1.25, smoothstep(0.45, 0.85, k) * streak_amount);
	col *= mix(1.0, clamp(lum / 0.25, 0.5, 1.6), grime);  // 0.25: the detail texture's mean luminance
	ALBEDO = col;
	float r = tri_sample(detail_rough, p, w).r;
	ROUGHNESS = mix(rough_lo, rough_hi, r);
	SPECULAR = 0.4;
	vec3 on = tri_normal(detail_normal, p, n, w, normal_strength);
	NORMAL = normalize((VIEW_MATRIX * MODEL_MATRIX * vec4(on, 0.0)).xyz);
	SSS_STRENGTH = sss;
	BACKLIGHT = col * sss * 0.35;
	EMISSION = col * emission_gain;
}
