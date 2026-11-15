shader_type canvas_item;
// One-take wing transition. Stage 0: the destination medium bleeds across a snapshot of the
// current frame. Stage 1: the medium drains away, revealing the new scene underneath.
#include "res://core/shaders/noise.gdshaderinc"

uniform sampler2D snapshot : filter_linear, source_color;
uniform float progress = 0.0;
uniform int stage = 0;
uniform int medium = 0;
uniform vec4 c0 : source_color = vec4(0.8, 0.6, 0.3, 1.0);
uniform vec4 c1 : source_color = vec4(0.3, 0.2, 0.5, 1.0);
uniform vec4 c2 : source_color = vec4(0.05, 0.04, 0.03, 1.0);
uniform vec2 aspect = vec2(1.7778, 1.0);

vec3 medium_field(vec2 uv, float t) {
	vec2 p = uv * aspect * 3.0;
	vec2 w = vec2(n_fbm(p + t * 0.25), n_fbm(p + 5.2 - t * 0.2));
	float f = n_fbm(p + w * 2.4 + t * 0.1);
	vec3 col = mix(c2.rgb, c1.rgb, smoothstep(0.25, 0.6, f));
	col = mix(col, c0.rgb, smoothstep(0.55, 0.85, f));
	if (medium == 0) { // glass: leaded cells
		vec3 v = n_voronoi(p * 1.6 + w);
		col = mix(col * (0.7 + 0.6 * v.z), vec3(0.02), 1.0 - smoothstep(0.02, 0.06, v.y));
	} else if (medium == 1) { // clay: posterised, stepped time
		col = floor(col * 5.0) / 5.0;
	} else if (medium == 2) { // noir: zero chroma + rain
		float l = dot(col, vec3(0.3, 0.59, 0.11));
		float rain = step(0.985, n_hash(floor(vec2(uv.x * 220.0, uv.y * 8.0 + t * 30.0 + n_hash(vec2(floor(uv.x * 220.0))) * 50.0))));
		col = vec3(l * 1.2 + rain * 0.4);
	} else if (medium == 3) { // aria: caustics
		vec3 v = n_voronoi(p * 1.2 + vec2(t * 0.3, -t * 0.2));
		col += c0.rgb * pow(1.0 - smoothstep(0.0, 0.18, v.y), 3.0) * 0.8;
	} else if (medium == 4) { // chitin: hex-ish cells, amber
		vec3 v = n_voronoi(p * 2.4);
		col *= 0.55 + 0.6 * smoothstep(0.02, 0.15, v.y);
	} else if (medium == 5) { // paint: directional strokes
		float s = n_fbm(vec2(p.x * 0.4 + w.y, p.y * 6.0 + w.x * 3.0));
		col = mix(col, c0.rgb * 1.2, smoothstep(0.55, 0.7, s));
		col = mix(col, c1.rgb * 1.1, smoothstep(0.62, 0.75, n_fbm(vec2(p.y * 0.5, p.x * 5.0) + 9.0)));
	} else { // museum ink & gold
		col = mix(vec3(0.02), vec3(0.78, 0.64, 0.35), smoothstep(0.62, 0.7, f) - smoothstep(0.7, 0.78, f));
	}
	return col;
}

void fragment() {
	vec2 uv = UV;
	float t = TIME;
	// mask grows from the centre outward with a ragged medium edge
	float edge_noise = n_fbm(uv * aspect * 4.0 + t * 0.15);
	float d = length((uv - 0.5) * aspect) * 0.9 + edge_noise * 0.45;
	float p = progress * 1.6;
	float m = smoothstep(p - 0.12, p, d); // 1 = untouched
	vec3 field = medium_field(uv, t);
	float rim = (1.0 - m) * smoothstep(p - 0.12, p - 0.02, d);
	if (stage == 0) {
		vec2 suv = uv + (1.0 - m) * (vec2(n_fbm(uv * 6.0 + t), n_fbm(uv * 6.0 - t)) - 0.5) * 0.04;
		vec3 snap = texture(snapshot, suv).rgb;
		vec3 col = mix(field, snap, m);
		col += c0.rgb * rim * 1.5;
		COLOR = vec4(col, 1.0);
	} else {
		// stage 1: progress 0 = all medium, 1 = all clear
		// the medium recedes from the centre: alpha = m (1 where not yet cleared)
		COLOR = vec4(field + c0.rgb * rim * 1.5, m);
	}
}
