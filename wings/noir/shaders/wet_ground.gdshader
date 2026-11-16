shader_type spatial;
// Wet city ground: a PBR set projected on world XZ, darkened and glossed by rain, with puddles that
// go mirror-smooth and flat (SSR and the area's reflection probe do the rest) and rain rings on them.

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rough_tex : hint_roughness_r, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float uv_scale = 0.3;
uniform vec4 tint : source_color = vec4(1.0);
uniform float puddles : hint_range(0.0, 1.0) = 0.5;
uniform float wetness : hint_range(0.0, 1.0) = 0.5;
uniform float rain = 1.0;

varying vec3 wpos;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = wpos.xz * uv_scale;
	vec3 alb = texture(albedo_tex, uv).rgb * tint.rgb;
	float r = texture(rough_tex, uv).r;
	vec3 n = texture(normal_tex, uv).rgb;
	// puddles collect in low, broad patches; the height of the surface (rough map) breaks their edge
	float m = vnoise(wpos.xz * 0.28) * 0.65 + vnoise(wpos.xz * 0.9) * 0.35;
	float pud = smoothstep(1.0 - puddles * 0.75, 1.0 - puddles * 0.75 + 0.08, m + (r - 0.5) * 0.12);
	// rain rings on standing water
	float ring = 0.0;
	vec2 cell = floor(wpos.xz * 2.2);
	vec2 f = fract(wpos.xz * 2.2) - 0.5;
	float h = hash(cell);
	float t = fract(TIME * 0.9 + h);
	float d = length(f - (vec2(hash(cell + 3.1), hash(cell + 7.7)) - 0.5) * 0.5);
	ring = smoothstep(0.03, 0.0, abs(d - t * 0.35)) * (1.0 - t) * rain;
	float wet = clamp(wetness + pud, 0.0, 1.0);
	// standing water is a black mirror: its albedo all but goes, so the reflection carries the surface
	ALBEDO = alb * mix(1.0, 0.3, wet) * (1.0 - 0.8 * pud);
	ROUGHNESS = mix(r, r * 0.15, wetness) * (1.0 - pud) + mix(0.0, 0.1, ring) * pud;
	SPECULAR = 0.5 + 0.5 * wet;
	vec3 flat_n = vec3(0.5, 0.5, 1.0);
	vec3 rn = vec3(0.5 + (f.x) * ring * 0.6, 0.5 + (f.y) * ring * 0.6, 1.0);
	NORMAL_MAP = mix(n, mix(flat_n, rn, ring), pud);
	NORMAL_MAP_DEPTH = 1.0;
}
