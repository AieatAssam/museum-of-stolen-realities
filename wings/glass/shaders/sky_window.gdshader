shader_type sky;
render_mode use_half_res_pass;
// The sky of the Vitrine Kingdom is one window. A dome of leaded panes (Voronoi cells, black lead),
// three suns glazed into it, and — once `reveal` rises — something museum-sized leaning in to look
// through: a dark curved silhouette and a single round loupe, glinting, where a fourth sun should be.
// `haze` (1 = the interior haze that hides the leading) clears on the rooftops.

uniform vec3 sun_a = vec3(0.35, 0.55, -0.76);
uniform vec3 sun_b = vec3(-0.62, 0.42, -0.66);
uniform vec3 sun_c = vec3(0.1, 0.78, 0.62);
uniform vec3 eye_dir = vec3(-0.92, 0.32, 0.0);
uniform float haze : hint_range(0.0, 1.0) = 1.0;
uniform float reveal : hint_range(0.0, 1.0) = 0.0;
uniform float dark : hint_range(0.0, 1.0) = 0.0;
uniform float scale = 7.0;

vec2 h2(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453);
}

// returns (edge distance, cell id hash)
vec2 voronoi(vec2 x) {
	vec2 n = floor(x), f = fract(x);
	vec2 mg, mr;
	float md = 8.0;
	for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
		vec2 g = vec2(float(i), float(j));
		vec2 o = h2(n + g);
		vec2 r = g + o - f;
		float d = dot(r, r);
		if (d < md) { md = d; mr = r; mg = g; }
	}
	md = 8.0;
	for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
		vec2 g = mg + vec2(float(i), float(j));
		vec2 o = h2(n + g);
		vec2 r = g + o - f;
		if (dot(mr - r, mr - r) > 0.00001) md = min(md, dot(0.5 * (mr + r), normalize(r - mr)));
	}
	return vec2(md, h2(n + mg).x);
}

vec3 pal(float k) {
	if (k < 0.34) return vec3(0.17, 0.33, 0.79);
	if (k < 0.52) return vec3(0.12, 0.22, 0.6);
	if (k < 0.66) return vec3(0.70, 0.13, 0.26);
	if (k < 0.80) return vec3(0.91, 0.71, 0.29);
	if (k < 0.90) return vec3(0.10, 0.48, 0.37);
	return vec3(0.25, 0.4, 0.85);
}

float sun(vec3 d, vec3 s, float size) {
	float c = dot(d, normalize(s));
	return smoothstep(cos(size), cos(size * 0.6), c);
}

void sky() {
	// the Voronoi dome is costly: draw it at half resolution, upsample on the full-res pass
	if (!AT_HALF_RES_PASS && !AT_CUBEMAP_PASS) {
		COLOR = HALF_RES_COLOR.rgb;
	} else {
	vec3 d = EYEDIR;
	// dome projection: azimuth/elevation, cells grow toward the horizon like a real rose
	float el = asin(clamp(d.y, -1.0, 1.0));
	float az = atan(d.x, d.z);
	vec2 p = vec2(az * scale * 0.6, (1.0 - el / 1.5708) * scale);
	if (d.y < 0.0) p.y = scale + (-d.y) * scale * 2.0;
	vec2 v = voronoi(p);
	vec3 glass = pal(v.y) * (0.75 + 0.5 * h2(vec2(v.y * 91.0)).x);
	// the great radiating mullions: 16 spokes and 3 rings of heavier lead
	float spoke = abs(fract(az / 6.2831853 * 16.0) - 0.5) * 2.0;
	float ring = abs(fract(el / 1.5708 * 3.0) - 0.5) * 2.0;
	float heavy = max(smoothstep(0.96, 0.99, spoke) * step(0.12, d.y), smoothstep(0.97, 0.995, ring));
	float lead = max(1.0 - smoothstep(0.03, 0.07, v.x), heavy);

	float suns = sun(d, sun_a, 0.09) + sun(d, sun_b, 0.07) * 0.9 + sun(d, sun_c, 0.06) * 0.8;
	vec3 sun_col = vec3(1.0, 0.86, 0.55) * suns * 6.0;
	float corona = pow(max(dot(d, normalize(sun_a)), 0.0), 18.0) + pow(max(dot(d, normalize(sun_b)), 0.0), 22.0);

	vec3 col = glass * (1.1 + corona * 2.5);
	col = mix(col, vec3(0.0), lead * (1.0 - suns));
	col += sun_col;

	// the onlooker: a vast dark head-and-shoulder curve occluding part of the dome, and a loupe
	if (reveal > 0.001) {
		vec3 e = normalize(eye_dir);
		float c = dot(d, e);
		float body = smoothstep(0.80, 0.84, c + 0.06 * sin(az * 3.0));
		vec3 occl = vec3(0.012, 0.012, 0.02);
		float loupe_ring = smoothstep(0.004, 0.0, abs(c - 0.982));
		float loupe = smoothstep(0.981, 0.984, c);
		vec3 iris = mix(vec3(0.85, 0.83, 0.78), vec3(0.08, 0.06, 0.05), smoothstep(0.9975, 0.9985, c));
		vec3 eye_col = mix(occl, iris * 1.6, loupe) + vec3(1.0, 0.85, 0.5) * loupe_ring * 3.0;
		col = mix(col, eye_col, max(body, loupe) * reveal);
	}

	// haze: the inside of a church — leading lost in luminous fog, palette held
	vec3 fogc = mix(vec3(0.05, 0.07, 0.16), vec3(0.2, 0.22, 0.42), smoothstep(-0.2, 0.6, d.y));
	col = mix(col, fogc + sun_col * 0.3, haze * 0.82);
	if (d.y < -0.02) col = mix(col, vec3(0.02, 0.025, 0.06), smoothstep(-0.02, -0.25, d.y));
	col *= 1.0 - dark * 0.85;
	COLOR = col;
	}
}
