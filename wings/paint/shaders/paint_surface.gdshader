shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
// Every dry-ish painted surface of the Unfinished Wing: ground slabs, walls, modelled props.
// Triplanar impasto (world space for the static world, object space for props that move) whose
// top projection swings between two stroke directions in patches, as a painter changes direction.
// Colour is two pigments dragged into each other by the texture's own ridges. Light is painterly:
// a warm terminator band and a hue-shifted shadow side (cool, violet) instead of grey.

uniform vec3 colour : source_color = vec3(0.93, 0.89, 0.80);
uniform vec3 colour2 : source_color = vec3(0.98, 0.84, 0.70);   // the second pigment, dragged in
uniform vec3 shade : source_color = vec3(0.42, 0.36, 0.62);     // the painter's shadow hue
uniform sampler2D detail_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D detail_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float tiles_per_m = 0.35;
uniform float normal_strength = 1.2;
uniform float tex_value = 0.75;        // how much the texture's own value shades the colour
uniform float mix_amount = 0.45;
uniform float rough = 0.62;
uniform float gloss = 0.0;             // 0 dry, 1 wet (varnish, fresh paint)
uniform float emission_gain = 0.0;
uniform float shade_amount = 0.55;
uniform bool object_space = false;
// world finishes only: broad pigment patches across the land, a worn path, raw linen on the sides
// below the primed lip, and a painter's simplification with distance (detail and contrast drop away)
uniform float patch_amount = 0.0;
uniform vec3 patch_a : source_color = vec3(0.46, 0.62, 0.22);   // sap green
uniform vec3 patch_b : source_color = vec3(0.90, 0.66, 0.24);   // yellow ochre
uniform vec3 patch_c : source_color = vec3(0.58, 0.48, 0.78);   // violet
uniform float path_width = 0.0;
uniform vec3 path_colour : source_color = vec3(0.80, 0.55, 0.34);
uniform float side_linen = 0.0;
uniform vec3 linen : source_color = vec3(0.70, 0.62, 0.50);
uniform float simplify_near = 30.0;
uniform float simplify_far = 160.0;

varying vec3 v_p;
varying vec3 v_n;

void vertex() {
	if (object_space) {
		vec3 s = vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), length(MODEL_MATRIX[2].xyz));
		v_p = VERTEX * s;
		v_n = NORMAL;
	} else {
		v_p = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		v_n = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	}
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(vec2(c, s), vec2(-s, c)); }

void fragment() {
	vec3 n = normalize(v_n);
	vec3 w = pow(abs(n), vec3(6.0));
	w /= (w.x + w.y + w.z);
	vec3 p = v_p * tiles_per_m;
	// two stroke directions on the top face, chosen in painterly patches
	float patch = smoothstep(0.35, 0.65, vnoise(v_p.xz * 0.11 + 3.1));
	vec2 ta = rot(0.5) * p.xz;
	vec2 tb = rot(-1.1) * p.xz + 0.37;
	vec3 ya = texture(detail_albedo, ta).rgb;
	vec3 yb = texture(detail_albedo, tb).rgb;
	vec3 ytex = mix(ya, yb, patch);
	vec3 na = texture(detail_normal, ta).rgb * 2.0 - 1.0;
	vec3 nb = texture(detail_normal, tb).rgb * 2.0 - 1.0;
	vec2 an = mix(rot(-0.5) * na.xy, rot(1.1) * nb.xy, patch);
	vec3 xtex = texture(detail_albedo, p.zy).rgb;
	vec3 ztex = texture(detail_albedo, p.xy).rgb;
	vec3 tex = xtex * w.x + ytex * w.y + ztex * w.z;
	vec2 nx = (texture(detail_normal, p.zy).rg * 2.0 - 1.0);
	vec2 nz = (texture(detail_normal, p.xy).rg * 2.0 - 1.0);
	// whiteout blend of the three projections in world (or object) space
	vec3 wn = normalize(vec3(0.0, nx.y, nx.x) * w.x * sign(n.x) + vec3(an.x, 0.0, an.y) * w.y + vec3(nz.x, nz.y, 0.0) * w.z) ;
	vec3 on = normalize(n + wn * normal_strength);
	float lum = dot(tex, vec3(0.299, 0.587, 0.114));
	float k = vnoise(v_p.xz * 0.35 + v_p.y * 0.2) * 0.6 + lum * 0.8 - 0.3;
	float far = object_space ? 0.0 : smoothstep(simplify_near, simplify_far, distance(v_p, CAMERA_POSITION_WORLD));
	vec3 col = mix(colour, colour2, smoothstep(0.3, 0.8, k) * mix_amount);
	if (!object_space) {
		float top = smoothstep(0.55, 0.8, n.y);
		// patches the size of fields, edges dragged by the strokes
		float q = vnoise(v_p.xz * 0.022 + 7.3) + (lum - 0.5) * 0.25;
		float r = vnoise(v_p.xz * 0.05 - 2.1) + (lum - 0.5) * 0.2;
		vec3 pc = mix(patch_a, patch_b, smoothstep(0.42, 0.58, q));
		pc = mix(pc, patch_c, smoothstep(0.62, 0.74, r) * 0.8);
		col = mix(col, pc, patch_amount * top * smoothstep(0.25, 0.55, abs(q - 0.5) * 2.0 + 0.3));
		// the worn path: the walking line, wandering
		float px = abs(v_p.x - 1.6 * sin(v_p.z * 0.045) - 0.8 * sin(v_p.z * 0.13 + 1.0));
		float path = (1.0 - smoothstep(path_width * 0.5, path_width * 0.5 + 0.9 + lum, px)) * top * step(0.01, path_width);
		col = mix(col, path_colour * (0.85 + 0.3 * lum), path * 0.85);
		// below the primed lip the slab is raw linen
		col = mix(col, linen * (0.8 + 0.4 * lum), side_linen * (1.0 - smoothstep(0.35, 0.6, n.y)));
	}
	col *= mix(1.0, clamp(lum / 0.72, 0.55, 1.25), tex_value * (1.0 - far * 0.85));
	on = normalize(mix(on, n, far * 0.8));
	ALBEDO = col;
	ROUGHNESS = mix(rough, 0.12, gloss) + (1.0 - lum) * 0.15;
	SPECULAR = mix(0.35, 0.6, gloss);
	CLEARCOAT = gloss;
	CLEARCOAT_ROUGHNESS = 0.15;
	mat3 vm = mat3(VIEW_MATRIX) * (object_space ? mat3(MODEL_MATRIX) : mat3(1.0));
	NORMAL = normalize(vm * on);
	EMISSION = col * emission_gain;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float lit = clamp(ndl, 0.0, 1.0) * ATTENUATION;
	// a warm band where light turns to shadow, as a painter pushes the terminator
	float term = smoothstep(0.0, 0.25, ndl) * (1.0 - smoothstep(0.25, 0.6, ndl)) * ATTENUATION;
	vec3 warm = vec3(1.0, 0.72, 0.5);
	vec3 lc = LIGHT_COLOR / PI;
	DIFFUSE_LIGHT += lc * (lit + term * 0.3 * warm);
	// the unlit side drifts toward the shadow hue instead of grey (the sun only: a lamp has no
	// "unlit side" outside its own reach)
	if (LIGHT_IS_DIRECTIONAL) {
		DIFFUSE_LIGHT += lc * shade * (1.0 - lit) * shade_amount * 0.18;
	}
	vec3 h = normalize(VIEW + LIGHT);
	float spec = pow(clamp(dot(NORMAL, h), 0.0, 1.0), mix(8.0, 220.0, 1.0 - ROUGHNESS)) * (1.0 - ROUGHNESS);
	SPECULAR_LIGHT += lc * spec * lit * (0.8 + gloss * 3.0);
}
