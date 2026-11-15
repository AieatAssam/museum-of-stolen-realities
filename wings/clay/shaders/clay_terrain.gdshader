shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

// Moss where the ground is untouched and flat; raw wet clay where it is steep or was shaped.
// Fingerprint whorls come from a cellular pattern, strongest where the player pressed or pulled.
uniform vec3 clay_albedo : source_color = vec3(0.56, 0.34, 0.20);
uniform vec3 moss_albedo : source_color = vec3(0.22, 0.31, 0.11);
uniform vec3 groove_tint : source_color = vec3(0.30, 0.16, 0.09);
uniform float whorl_span = 0.22;

varying float v_mark;
varying vec3 v_world;
varying vec3 v_normal;

float hash21(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
		mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x), u.y);
}

// Distance to the nearest jittered feature point: rings of it read as whorled skin.
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

void vertex() {
	v_mark = COLOR.r;
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_normal = NORMAL;
}

void fragment() {
	vec3 wn = normalize((MODEL_MATRIX * vec4(v_normal, 0.0)).xyz);
	float raw = max(v_mark, 1.0 - smoothstep(0.80, 0.97, wn.y));
	vec3 moss = moss_albedo * (0.75 + 0.5 * vnoise(v_world.xz * 3.0));
	vec3 base = mix(moss, clay_albedo * (0.9 + 0.2 * vnoise(v_world.xz * 5.0)), raw);

	vec2 p = v_world.xz / whorl_span;
	float ridge = sin(cellular(p) * 58.0) * 0.5 + 0.5;
	float groove = smoothstep(0.55, 0.95, ridge) * (0.25 + 0.75 * max(v_mark, 0.15));
	ALBEDO = mix(base, groove_tint, groove * 0.55);
	ROUGHNESS = mix(0.72, 0.42, raw);
	SPECULAR = 0.35;
}
