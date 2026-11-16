shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// The deformable ground. Untouched flat ground is pressed green plasticine moss; steep or reshaped
// ground is raw terracotta (fingerprint whorls show strongest where the player worked it). Regions by
// place: a trodden sandy path (the leading line), the blue clay riverbed under the film, and the
// workbench top, which is wood. Textures supply only detail (value and normals); colour is ours.
#include "res://wings/clay/shaders/triplanar.gdshaderinc"

uniform sampler2D moss_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D moss_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D clay_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D clay_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D wood_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D wood_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform vec3 moss_col : source_color = vec3(0.24, 0.46, 0.11);
uniform vec3 moss_col2 : source_color = vec3(0.40, 0.56, 0.13);
uniform vec3 clay_col : source_color = vec3(0.80, 0.36, 0.13);
uniform vec3 path_col : source_color = vec3(0.86, 0.64, 0.40);
uniform vec3 bed_col : source_color = vec3(0.10, 0.30, 0.66);
uniform vec3 groove_tint : source_color = vec3(0.40, 0.17, 0.07);
uniform float moss_tiles = 0.42;
uniform float clay_tiles = 0.55;
uniform float detail_contrast = 1.8;
uniform float whorl_span = 0.22;
uniform vec4 bench_rect = vec4(-6.0, -46.0, 6.0, -36.0);  // x0, z0, x1, z1
uniform float bench_top = 2.2;
uniform float boil = 1.0;  // stop-motion boil of the detail, 0 with Reduced Motion

// The heights live in `heightmap` (R = height, G = player mark) on the 1 m collision grid; the mesh
// is a finer static grid that samples it with a Catmull-Rom patch, so pulled clay renders with
// rounded shoulders and a base that eases into the moss instead of 1 m facets and a crease.
uniform sampler2D heightmap : filter_nearest, repeat_disable;
uniform float half_size = 40.0;

float cr(float p0, float p1, float p2, float p3, float t) {
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t);
}

float crd(float p0, float p1, float p2, float p3, float t) {
	return 0.5 * ((p2 - p0) + 2.0 * (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t + 3.0 * (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t);
}

// height, d/dx, d/dz and the bilinear mark at grid coordinate g
vec4 sample_clay(vec2 g) {
	ivec2 sz = textureSize(heightmap, 0);
	vec2 c = clamp(g, vec2(0.0), vec2(sz - 1));
	ivec2 i = ivec2(floor(c));
	i = min(i, sz - 2);
	vec2 t = c - vec2(i);
	float rows[4];
	float drows[4];
	for (int r = 0; r < 4; r++) {
		int z = clamp(i.y + r - 1, 0, sz.y - 1);
		float p[4];
		for (int k = 0; k < 4; k++) {
			p[k] = texelFetch(heightmap, ivec2(clamp(i.x + k - 1, 0, sz.x - 1), z), 0).r;
		}
		rows[r] = cr(p[0], p[1], p[2], p[3], t.x);
		drows[r] = crd(p[0], p[1], p[2], p[3], t.x);
	}
	float h = cr(rows[0], rows[1], rows[2], rows[3], t.y);
	// no overshoot past the cell's own corners: no dip round the foot of a pulled column
	float c00 = texelFetch(heightmap, i, 0).r;
	float c10 = texelFetch(heightmap, i + ivec2(1, 0), 0).r;
	float c01 = texelFetch(heightmap, i + ivec2(0, 1), 0).r;
	float c11 = texelFetch(heightmap, i + ivec2(1, 1), 0).r;
	h = clamp(h, min(min(c00, c10), min(c01, c11)), max(max(c00, c10), max(c01, c11)));
	float dx = cr(drows[0], drows[1], drows[2], drows[3], t.y);
	float dz = crd(rows[0], rows[1], rows[2], rows[3], t.y);
	float m00 = texelFetch(heightmap, i, 0).g;
	float m10 = texelFetch(heightmap, i + ivec2(1, 0), 0).g;
	float m01 = texelFetch(heightmap, i + ivec2(0, 1), 0).g;
	float m11 = texelFetch(heightmap, i + ivec2(1, 1), 0).g;
	float m = mix(mix(m00, m10, t.x), mix(m01, m11, t.x), t.y);
	return vec4(h, dx, dz, m);
}

varying float v_mark;
varying vec3 v_world;
varying vec3 v_wn;

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float cellular(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	float d = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = vec2(hash21(i + g), hash21(i + g + 17.0));
			vec2 r = g + o - f;
			d = min(d, dot(r, r));
		}
	}
	return sqrt(d);
}

// value detail around 1.0 from a texture whose mean linear luminance is `mean`
float detail(vec3 t, float mean) {
	float l = dot(t, vec3(0.2126, 0.7152, 0.0722)) / mean;
	return clamp(1.0 + (l - 1.0) * detail_contrast, 0.45, 1.7);
}

void vertex() {
	vec4 c = sample_clay(VERTEX.xz + half_size);
	VERTEX.y = c.x;
	NORMAL = normalize(vec3(-c.y, 1.0, -c.z));
	v_mark = c.w;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 n = normalize(v_wn);
	vec3 w = tri_weights(n);
	float bf = floor(TIME * 12.0);
	vec3 jit = vec3(fract(bf * 0.618), 0.0, fract(bf * 0.382)) * 0.01 * boil;
	float macro = tri_vnoise(v_world * 0.16) * 0.6 + tri_vnoise(v_world * 0.63) * 0.4;

	// moss: two scales of the same pressed-plasticine detail so the tiling never lines up
	vec3 pm = (v_world + jit) * moss_tiles;
	float dm = detail(tri_sample(moss_tex, pm, w).rgb, 0.293) * 0.65
		+ detail(tri_sample(moss_tex, pm * 0.37 + 0.31, w).rgb, 0.293) * 0.35;
	vec3 moss = mix(moss_col, moss_col2, smoothstep(0.35, 0.75, macro)) * dm;
	vec3 pc = (v_world + jit) * clay_tiles;
	float dc = detail(tri_sample(clay_tex, pc, w).rgb, 0.209);
	vec3 clay = clay_col * dc * (0.9 + 0.2 * macro);

	// raw clay: steep, or reshaped by the player; a ragged edge, as if the moss were torn
	float steep = 1.0 - smoothstep(0.72, 0.97, n.y);
	float raw = clamp(max(v_mark * 1.4, steep) + (macro - 0.5) * 0.5, 0.0, 1.0);
	raw = smoothstep(0.2, 0.75, raw);

	// the path: a wandering band down the middle of the set, the brightest line in view
	float px = abs(v_world.x - 1.6 * sin(v_world.z * 0.14) - 0.6 * sin(v_world.z * 0.41));
	float path = (1.0 - smoothstep(0.9, 1.5 + 0.4 * macro, px)) * step(v_world.z, 33.0) * step(-34.0, v_world.z);
	path *= (1.0 - steep) * (1.0 - smoothstep(0.6, 1.0, v_mark));
	vec3 pathc = path_col * dc * (0.9 + 0.2 * macro);

	// riverbed: the trench floor under the film is blue plasticine
	float bed = (1.0 - smoothstep(-0.9, -0.5, v_world.y)) * (1.0 - smoothstep(1.8, 2.4, abs(v_world.z + 4.5)));
	vec3 bedc = bed_col * dc;

	// the workbench top is wood
	vec2 bx = step(bench_rect.xy, v_world.xz) * step(v_world.xz, bench_rect.zw);
	// inside the rect the plateau is the flat top (base noise can sink it below bench_top, so be generous)
	float bench = bx.x * bx.y * smoothstep(bench_top - 0.8, bench_top - 0.4, v_world.y);
	vec2 wuv = v_world.xz * vec2(0.08, 0.16);
	vec3 wood = texture(wood_tex, wuv).rgb;

	vec3 base = mix(moss, clay, raw);
	base = mix(base, pathc, path * (1.0 - raw));
	base = mix(base, bedc, bed);
	base = mix(base, wood, bench);

	// fingerprint whorls where the player worked the clay (feedback for the verb)
	vec2 p = v_world.xz / whorl_span;
	float ridge = sin(cellular(p) * 58.0) * 0.5 + 0.5;
	float groove = smoothstep(0.55, 0.95, ridge) * smoothstep(0.05, 0.6, v_mark) * (1.0 - bench);
	ALBEDO = mix(base, groove_tint, groove * 0.4);

	vec3 nm = tri_normal(moss_normal, pm, n, w, 2.2);
	vec3 nc = tri_normal(clay_normal, pc, n, w, 2.2);
	vec3 tw = texture(wood_normal, wuv).xyz * 2.0 - 1.0;
	vec3 nw = normalize(vec3(tw.x * 0.8, 1.0, -tw.y * 0.8));
	vec3 wn = normalize(mix(mix(nm, nc, max(raw, path * 0.7)), nw, bench));
	NORMAL = normalize((VIEW_MATRIX * vec4(wn, 0.0)).xyz);
	ROUGHNESS = mix(mix(0.8, 0.52, raw), 0.62, bench) - groove * 0.12;
	SPECULAR = 0.38;
	SSS_STRENGTH = 0.2 * (1.0 - bench);
}
