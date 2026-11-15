shader_type spatial;
// A wall that is mostly window: bays of tall pointed lancets (figurative art from lancet_atlas, 12
// columns), in up to two tiers, set in deep sapphire structural glass with a faint inner glow. The
// lancets are emissive (they feed SDFGI and SSR, so the floor mirrors them and the room fills with
// their colour); a black lead/tracery frame rims each one. Vertical faces only.
// proj: 0 = world projection on the dominant axis (code-built boxes), 1 = mesh UV in metres (models).
render_mode diffuse_burley, specular_schlick_ggx;

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform float cols = 12.0;
uniform vec4 tint : source_color = vec4(0.05, 0.08, 0.2, 1.0);
uniform float glow = 0.9;
uniform float bay = 5.5;               // metres between lancet centres
uniform float bay_off = 0.0;           // a lancet centre sits here
uniform float lw = 3.2;                // lancet width
uniform vec2 tier_a = vec2(0.5, 9.0);  // base, height (height 0 = no tier)
uniform vec2 tier_b = vec2(0.0, 0.0);
uniform float energy = 2.2;
uniform float dark = 0.0;              // the heist dims them
uniform int proj = 0;

varying vec3 wpos;
varying vec3 wnrm;

float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

// inside a lancet of width w (rectangle with an equilateral pointed head) at p (x from centre, y from base)
float lancet(vec2 p, float w, float h) {
	float hw = w * 0.5;
	float spring = h - w * 0.866;
	float side = step(abs(p.x), hw) * step(0.0, p.y);
	float head = step(max(length(vec2(p.x + hw, p.y - spring)), length(vec2(p.x - hw, p.y - spring))), w);
	return side * (p.y < spring ? 1.0 : head);
}

void fragment() {
	vec3 an = abs(wnrm);
	vec2 uv = proj == 1 ? UV : (an.x > an.z ? wpos.zy : wpos.xy);
	vec3 c = tint.rgb * (0.8 + 0.4 * h1(floor(uv / vec2(0.9, 1.4))));
	vec3 em = c * glow;
	float rough = 0.08;
	float metal = 0.0;
	if (an.y < 0.5) {
		float u = uv.x - bay_off;
		float k = floor(u / bay + 0.5);
		vec2 p = vec2(u - k * bay, uv.y);
		for (int t = 0; t < 2; t++) {
			vec2 tier = t == 0 ? tier_a : tier_b;
			if (tier.y <= 0.0) continue;
			vec2 q = vec2(p.x, p.y - tier.x);
			float outer = lancet(q, lw + 0.24, tier.y + 0.12);
			float inner = lancet(q, lw, tier.y);
			if (outer > 0.0) {
				// the tracery rim: black stone/lead with a bright specular edge
				c = vec3(0.03, 0.03, 0.035);
				em = vec3(0.0);
				rough = 0.25;
				metal = 0.9;
			}
			if (inner > 0.0) {
				float idx = floor(h1(vec2(k, tier.x)) * cols);
				vec2 luv = vec2(q.x / lw + 0.5, 1.0 - q.y / tier.y);
				vec3 art = texture(atlas, vec2((idx + clamp(luv.x, 0.01, 0.99)) / cols, clamp(luv.y, 0.0, 1.0))).rgb;
				c = art * 0.1;
				em = art * energy * (1.0 - dark * 0.9);
				rough = 0.1;
				metal = 0.0;
			}
		}
	}
	ALBEDO = c;
	ROUGHNESS = rough;
	METALLIC = metal;
	SPECULAR = 0.6;
	EMISSION = em;
}
