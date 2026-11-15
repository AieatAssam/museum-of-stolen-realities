shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
// The river of ultramarine: opaque wet paint laid in long horizontal strokes that creep downstream,
// pale highlights dragged across the crests, glossy everywhere.

uniform vec3 deep : source_color = vec3(0.04, 0.09, 0.42);
uniform vec3 mid : source_color = vec3(0.10, 0.25, 0.78);
uniform vec3 crest : source_color = vec3(0.70, 0.82, 1.0);
uniform sampler2D stroke_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stroke_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float speed = 0.25;

varying vec3 v_w;
void vertex() { v_w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

void fragment() {
	vec2 p = v_w.xz;
	float warp = vnoise(p * 0.08) * 2.0;
	vec2 uv1 = vec2(p.x * 0.18 + TIME * speed * 0.2, p.y * 0.5 + sin(p.x * 0.12 + warp) * 0.6);
	vec2 uv2 = vec2(p.x * 0.11 - TIME * speed * 0.12, p.y * 0.33 + 0.4 + warp * 0.3);
	float t = dot(texture(stroke_albedo, uv1).rgb, vec3(0.333)) * 0.6 + dot(texture(stroke_albedo, uv2).rgb, vec3(0.333)) * 0.4;
	float band = vnoise(vec2(p.x * 0.05, p.y * 0.7) + warp);
	vec3 col = mix(deep, mid, smoothstep(0.25, 0.7, band + (t - 0.5)));
	col = mix(col, crest, smoothstep(0.72, 0.92, t + band * 0.25) * 0.8);
	ALBEDO = col;
	vec3 n1 = texture(stroke_normal, uv1).rgb;
	vec3 n2 = texture(stroke_normal, uv2).rgb;
	NORMAL_MAP = normalize(n1 + n2 - 1.0) * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = 1.2;
	ROUGHNESS = 0.08;
	SPECULAR = 0.7;
	CLEARCOAT = 1.0;
	CLEARCOAT_ROUGHNESS = 0.05;
}
