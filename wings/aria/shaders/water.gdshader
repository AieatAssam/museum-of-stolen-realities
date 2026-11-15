shader_type spatial;
// The drowned stalls: still, black-teal water that mirrors the hall (SSR, so it stays opaque), stirred
// by cymatics. Every sounding instrument (src[i] = x, z, envelope, ring frequency) sets up a standing
// wave around it: concentric rings crossed by a lobed (angular) mode, so a chord draws an interference
// figure on the surface. A slow ambient swell keeps it alive when the hall is silent.
render_mode cull_disabled;

uniform vec4 src[8];
uniform int src_count = 0;
uniform vec3 deep : source_color = vec3(0.004, 0.03, 0.035);
uniform vec3 glint : source_color = vec3(0.35, 0.95, 0.85);
uniform float ring_glow = 1.6;

float swell(vec2 p, float t) {
	return sin(p.x * 0.7 + t * 0.6) * 0.5 + sin(p.y * 0.9 - t * 0.45) * 0.5 + sin((p.x + p.y) * 1.7 + t) * 0.25;
}

// height of the field and a bright-line mask where the standing wave has antinodes
vec2 field(vec2 p, float t) {
	float h = swell(p, t) * 0.02;
	float lines = 0.0;
	for (int i = 0; i < 8; i++) {
		if (i >= src_count) break;
		vec4 s = src[i];
		vec2 d = p - s.xy;
		float r = length(d);
		float env = s.z;
		if (env < 0.01 || r > 9.0) continue;
		float k = s.w;
		float lobes = cos(6.0 * atan(d.y, d.x) + t * 0.3);
		float wave = cos(k * r - t * 2.2) * (0.75 + 0.25 * lobes) * cos(t * 3.1);
		float fall = env * exp(-r * 0.32);
		h += wave * fall * 0.06;
		lines += smoothstep(0.82, 1.0, abs(wave)) * fall;
	}
	return vec2(h, lines);
}

void fragment() {
	vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = TIME;
	vec2 p = wp.xz;
	float e = 0.06;
	vec2 f0 = field(p, t);
	float hx = field(p + vec2(e, 0.0), t).x - f0.x;
	float hz = field(p + vec2(0.0, e), t).x - f0.x;
	vec3 n_world = normalize(vec3(-hx / e, 1.0, -hz / e));
	NORMAL = normalize((VIEW_MATRIX * vec4(n_world, 0.0)).xyz);
	ALBEDO = deep;
	ROUGHNESS = 0.04;
	METALLIC = 0.0;
	SPECULAR = 0.8;
	EMISSION = glint * f0.y * ring_glow;
}
