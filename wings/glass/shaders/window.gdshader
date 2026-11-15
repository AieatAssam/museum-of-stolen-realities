shader_type spatial;
// A stained-glass window, lit from outside. `edited` (0..1) is the Curator's re-leading: the saint is
// cut out of her own miracle and an empty museum pedestal glazed in her place, in cheap grey quarry.
// `dark` puts the sun out behind it (the heist). `crack` webs it before it shatters.
render_mode unshaded, cull_disabled;

uniform sampler2D window_tex : source_color, filter_linear_mipmap_anisotropic;
uniform float edited = 0.0;
uniform float dark = 0.0;
uniform float crack = 0.0;
uniform float energy = 1.6;
uniform vec2 figure_c = vec2(0.5, 0.42);   // where the saint stands, in UV
uniform vec2 figure_r = vec2(0.2, 0.34);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// distance to the lead line of a diamond quarry lattice
float quarry(vec2 uv) {
	vec2 q = uv * vec2(9.0, 13.0);
	vec2 d = vec2(q.x + q.y, q.x - q.y);
	vec2 f = abs(fract(d) - 0.5);
	return min(f.x, f.y);
}

vec3 pedestal(vec2 uv, vec3 bg) {
	// a plinth: base, shaft, capital — museum-white glass with black leading round it
	vec2 c = uv - vec2(figure_c.x, figure_c.y + figure_r.y * 0.35);
	float shaft = step(abs(c.x), 0.07) * step(abs(c.y), 0.18);
	float cap = step(abs(c.x), 0.1) * step(abs(c.y + 0.2), 0.025);
	float base = step(abs(c.x), 0.11) * step(abs(c.y - 0.2), 0.03);
	float m = max(shaft, max(cap, base));
	float edge = max(step(abs(c.x), 0.12) * step(abs(c.y), 0.24) - m, 0.0);
	vec3 white = vec3(0.92, 0.9, 0.86);
	return mix(bg * (1.0 - edge * 0.85), white, m);
}

void fragment() {
	vec2 uv = UV;
	vec3 c = texture(window_tex, uv).rgb;
	if (edited > 0.001) {
		vec2 e = (uv - figure_c) / figure_r;
		float inside = 1.0 - smoothstep(0.92, 1.0, length(e));
		float lead = 1.0 - smoothstep(0.02, 0.05, quarry(uv));
		vec3 grey = vec3(0.42, 0.45, 0.47) * (0.85 + 0.3 * hash(floor(uv * vec2(9.0, 13.0) * 2.0)));
		grey *= 1.0 - lead * 0.9;
		grey = pedestal(uv, grey);
		c = mix(c, grey, inside * edited);
	}
	if (crack > 0.001) {
		vec2 k = uv - vec2(0.5, 0.45);
		float a = atan(k.y, k.x);
		float rays = smoothstep(0.985, 1.0, abs(sin(a * 11.0 + hash(vec2(floor(a * 3.0))) * 4.0)));
		float rings = smoothstep(0.96, 1.0, abs(sin(length(k) * 60.0)));
		c *= 1.0 - (rays + rings * 0.5) * crack * step(length(k), crack * 0.8);
	}
	float lum = dot(c, vec3(0.3, 0.59, 0.11));
	float glass = smoothstep(0.06, 0.14, lum);
	ALBEDO = c * energy * mix(1.0, 0.06, dark) * glass;
	// never fully black panes except the lead
}
