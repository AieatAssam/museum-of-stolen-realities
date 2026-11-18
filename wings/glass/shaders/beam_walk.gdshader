shader_type spatial;
// The walkable skin of a beam: a faint sheet of slow caustic light at the walking height, like sunlight on
// shallow water. Densest down the middle and fading to nothing at the edges (the width reads from the
// falloff, not a line); where the player stands, a ripple of brighter light spreads from their feet.
// A flat quad, x = the beam's width, z = 1 stretched to the walkable length: exactly the collider's top.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
instance uniform float walk_len = 10.0;
instance uniform vec3 foot = vec3(0.0, -1000.0, 0.0);
uniform float half_w = 0.675;
uniform float intensity = 0.55;

varying vec3 lp;
varying vec3 wp;

void vertex() {
	lp = VERTEX;
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float along = (lp.z + 0.5) * walk_len;
	float u = abs(lp.x) / half_w;
	float fall = 1.0 - smoothstep(0.1, 1.0, u);
	fall *= fall;
	float ends = smoothstep(0.0, 0.7, along) * smoothstep(0.0, 0.7, walk_len - along);
	// caustic web: bright filaments where crossing waves cancel, drifting slowly along the beam
	vec2 p = vec2(lp.x * 5.0, along * 2.4);
	float t = TIME * 0.45;
	float c1 = sin(p.x * 1.3 + sin(p.y * 0.9 + t) * 1.6 + t);
	float c2 = sin(p.y * 1.1 + sin(p.x * 1.7 - t * 0.8) * 1.8 - t * 0.7);
	float web = pow(max(0.0, 1.0 - abs(c1 + 0.7 * c2)), 3.0);
	vec3 c = beam_color.rgb;
	vec3 col = c * (0.16 + web * 0.9) * fall * ends;
	// the light answers her weight: a ring spreading from her feet, and a glow under them
	float d = distance(wp, foot);
	float ring = 0.5 + 0.5 * sin(d * 14.0 - TIME * 4.5);
	float step_glow = exp(-d * d * 3.0) * 0.6 + exp(-d * 1.4) * ring * 0.5;
	col += mix(c, vec3(1.0), 0.12) * step_glow * (0.25 + 0.75 * fall) * ends;
	ALBEDO = col * intensity;
}
