// Shared noise helpers for museum shaders.
float n_hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
vec2 n_hash2(vec2 p) { return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453); }
float n_value(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(n_hash(i), n_hash(i + vec2(1, 0)), u.x), mix(n_hash(i + vec2(0, 1)), n_hash(i + vec2(1, 1)), u.x), u.y);
}
float n_fbm(vec2 p) {
	float a = 0.5, s = 0.0;
	for (int i = 0; i < 5; i++) { s += a * n_value(p); p = p * 2.03 + 17.1; a *= 0.5; }
	return s;
}
// returns (dist to nearest, dist to edge, cell id)
vec3 n_voronoi(vec2 p) {
	vec2 n = floor(p), f = fract(p);
	vec2 mg, mr; float md = 8.0;
	for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
		vec2 g = vec2(float(i), float(j));
		vec2 o = n_hash2(n + g);
		vec2 r = g + o - f; float d = dot(r, r);
		if (d < md) { md = d; mr = r; mg = g; }
	}
	float ed = 8.0;
	for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
		vec2 g = mg + vec2(float(i), float(j));
		vec2 o = n_hash2(n + g);
		vec2 r = g + o - f;
		if (dot(mr - r, mr - r) > 0.00001) ed = min(ed, dot(0.5 * (mr + r), normalize(r - mr)));
	}
	return vec3(sqrt(md), ed, n_hash(n + mg));
}
