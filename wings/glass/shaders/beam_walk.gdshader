shader_type spatial;
// The walkable top of a solid beam: a slab of light with a leaded-glass diamond pane pattern, a caustic
// shimmer that drifts slowly along it, bright crisp kerbs down both edges and across both ends, and sides
// that fall away softly below so it has thickness. The slab is a unit-length box (x = beam width, z = 1
// stretched to the walkable length, y = 0.2 thick); its top face is exactly the collider's top.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
instance uniform float walk_len = 10.0;
uniform float half_w = 0.675;
uniform float thick = 0.2;
uniform float intensity = 0.55;

varying vec3 lp;
varying vec3 ln;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void vertex() {
	lp = VERTEX;
	ln = NORMAL;
}

void fragment() {
	float along = (lp.z + 0.5) * walk_len;
	float ax = abs(lp.x);
	vec3 c = beam_color.rgb;
	vec3 hot = mix(c, vec3(1.0), 0.65);
	vec3 col = vec3(0.0);
	if (ln.y > 0.5) {
		// leaded diamond panes, each its own brightness
		vec2 q = vec2(lp.x / 0.34, along / 0.5);
		float fa = fract(q.x + q.y);
		float fb = fract(q.x - q.y);
		float lead = 1.0 - smoothstep(0.03, 0.08, min(min(fa, 1.0 - fa), min(fb, 1.0 - fb)));
		float pane = 0.62 + 0.38 * hash(vec2(floor(q.x + q.y), floor(q.x - q.y)));
		// caustic shimmer drifting along the beam
		float cs = sin(lp.x * 7.0 + along * 2.2 - TIME * 1.1) * sin(along * 3.1 + lp.x * 4.0 - TIME * 0.8);
		float caustic = pow(clamp(0.5 + 0.5 * cs, 0.0, 1.0), 4.0);
		col = mix(c * pane * 0.9 + hot * caustic * 0.8, c * 0.1, lead);
		// crisp kerbs: a hot band on each edge with a dark line inside it, and the same across both ends
		float kerb = smoothstep(half_w - 0.1, half_w - 0.095, ax);
		float gap = smoothstep(half_w - 0.125, half_w - 0.12, ax) * (1.0 - smoothstep(half_w - 0.105, half_w - 0.1, ax));
		float endk = 1.0 - smoothstep(0.085, 0.09, min(along, walk_len - along));
		float endg = smoothstep(0.1, 0.105, min(along, walk_len - along)) * (1.0 - smoothstep(0.12, 0.125, min(along, walk_len - along)));
		col *= 1.0 - 0.7 * max(gap, endg);
		col = mix(col, hot * 2.6, max(kerb, endk));
	} else if (ln.y < -0.5) {
		col = c * 0.08;
	} else {
		// the sides: bright at the top edge, falling away softly downward
		float d = clamp((0.5 * thick - lp.y) / thick, 0.0, 1.0);
		float bands = 0.8 + 0.2 * sin(along * 5.0 - TIME * 0.6);
		col = mix(hot * 2.2, c * 0.9 * bands, smoothstep(0.0, 0.12, d)) * pow(1.0 - d, 1.8);
	}
	ALBEDO = col * intensity;
}
