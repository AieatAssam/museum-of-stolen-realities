shader_type spatial;
// A soft pool of light where a walkable beam lands: a feathered disc with the same slow caustic in it.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
uniform float intensity = 0.5;

varying vec3 lp;

void vertex() {
	lp = VERTEX;
}

void fragment() {
	float r = length(lp.xz) / 1.3;
	float glow = pow(1.0 - smoothstep(0.0, 1.0, r), 2.2);
	float t = TIME * 0.45;
	float c1 = sin(lp.x * 6.0 + sin(lp.z * 4.0 + t) * 1.6 + t);
	float c2 = sin(lp.z * 5.0 + sin(lp.x * 7.0 - t * 0.8) * 1.8 - t * 0.7);
	float web = pow(max(0.0, 1.0 - abs(c1 + 0.7 * c2)), 3.0);
	ALBEDO = beam_color.rgb * glow * (0.35 + 0.65 * web) * intensity;
}
