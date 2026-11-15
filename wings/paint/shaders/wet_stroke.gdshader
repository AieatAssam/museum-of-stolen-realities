shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
// A wet brushstroke (the rails). UV.x runs along the stroke in widths, UV.y across it (0..1 over
// the top). Bristle grooves follow the stroke; the specular is stretched along it (anisotropy) so
// the gloss reads as a dragged stroke. Pigment varies across the bristles; a fresnel rim of the
// stroke's own colour keeps each colour readable at 30 m. The rider presses a wake into the wet
// paint (rider = xyz, w = strength). `dry` 0..1 dulls, greys and cracks it (heist).

uniform vec3 colour : source_color = vec3(0.1, 0.2, 0.8);
uniform vec3 hi : source_color = vec3(0.6, 0.75, 1.0);      // lighter pigment caught on the ridges
uniform vec3 lo : source_color = vec3(0.05, 0.08, 0.35);    // darker pigment in the grooves
uniform vec3 dry_colour : source_color = vec3(0.62, 0.57, 0.48);
uniform sampler2D stroke_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stroke_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float dry : hint_range(0.0, 1.0) = 0.0;
uniform float rim = 0.55;
uniform float glow = 0.0;          // lamp paint (yellow, orange) gives light
uniform float flow = 0.04;         // wet paint creeps along the stroke
uniform float normal_strength = 1.4;
uniform vec4 rider = vec4(0.0, -999.0, 0.0, 0.0);

varying vec3 v_w;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float d = distance(wp.xz, rider.xz);
	float near = step(abs(wp.y - rider.y), 1.5) * rider.w * (1.0 - dry);
	// a dimple under her feet and a bow wave around it
	float wake = -0.07 * exp(-d * d / 0.35) + 0.06 * exp(-(d - 1.0) * (d - 1.0) / 0.12);
	VERTEX += NORMAL * wake * near * step(0.02, UV.y) * step(UV.y, 0.98);
	v_w = wp;
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

vec2 cell(vec2 p) {   // distance to the nearest crack (voronoi edge)
	vec2 i = floor(p); vec2 f = fract(p);
	float d1 = 8.0; float d2 = 8.0;
	for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
		vec2 g = vec2(float(x), float(y));
		vec2 o = vec2(hash(i + g), hash(i + g + 17.0));
		float d = length(g + o - f);
		if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
	}
	return vec2(d1, d2 - d1);
}

void fragment() {
	vec2 uv = vec2(UV.x * 0.45 - TIME * flow * (1.0 - dry), UV.y);
	vec3 tn = texture(stroke_normal, uv).rgb * 2.0 - 1.0;
	float t = dot(texture(stroke_albedo, uv).rgb, vec3(0.333));
	// pigment streaks across the bristles: lighter on the ridges, darker in the grooves
	float streak = vnoise(vec2(UV.x * 0.6, UV.y * 9.0)) * 0.6 + vnoise(vec2(UV.x * 2.5, UV.y * 23.0)) * 0.4;
	vec3 col = mix(lo, colour, smoothstep(0.15, 0.55, streak + (t - 0.5) * 0.8));
	col = mix(col, hi, smoothstep(0.68, 0.95, streak + (t - 0.5) * 0.6) * 0.7);
	// drying: dull, grey, then cracked
	vec2 c = cell(UV * vec2(1.2, 4.0) + 3.0);
	float crack = (1.0 - smoothstep(0.02, 0.07, c.y)) * smoothstep(0.45, 0.9, dry);
	col = mix(col, dry_colour * (0.85 + 0.3 * t), smoothstep(0.0, 1.0, dry));
	col *= 1.0 - crack * 0.7;
	// wet paint is the most saturated thing in the picture
	float g = dot(col, vec3(0.333));
	col = mix(col, max(vec3(0.0), g + (col - g) * 1.35), 1.0 - dry);
	ALBEDO = col;
	ROUGHNESS = mix(0.07 + (1.0 - t) * 0.15, 0.85, dry);
	SPECULAR = 0.65;
	CLEARCOAT = 1.0 - dry;
	CLEARCOAT_ROUGHNESS = 0.06;
	ANISOTROPY = 0.55 * (1.0 - dry);
	ANISOTROPY_FLOW = vec2(1.0, 0.0);
	NORMAL_MAP = normalize(vec3(tn.xy * normal_strength * (1.0 + crack * 2.0), 1.0)) * 0.5 + 0.5;
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	// a little of its own light so a rail reads at 30 m against the ground, and a bright rim
	EMISSION = colour * ((0.22 + rim * f * 1.6) * (1.0 - dry) + glow * (0.6 + 0.4 * t)) + hi * smoothstep(0.75, 0.95, streak) * 0.25 * (1.0 - dry);
}
