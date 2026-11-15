shader_type spatial;
// A Chladni figure of light laid on a floor (or held in haze as a hanging disc): nodal lines of a
// circular plate's standing wave, mode (n radial, m angular). `level` 0..1 is how loudly the room is
// sounding; the pattern slowly rotates between modes as notes change. Additive, no depth write.
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec3 tint : source_color = vec3(0.45, 1.0, 0.85);
uniform float level = 0.3;
uniform float n_mode = 5.0;
uniform float m_mode = 6.0;
uniform float energy = 1.5;

void fragment() {
	vec2 q = UV * 2.0 - 1.0;
	float r = length(q);
	if (r > 1.0) discard;
	float a = atan(q.y, q.x) + TIME * 0.04;
	float w = cos(n_mode * 3.14159 * r) * cos(m_mode * a) + 0.6 * cos((n_mode + 2.0) * 3.14159 * r - TIME * 0.5);
	float line = 1.0 - smoothstep(0.0, 0.12, abs(w));
	float rings = 1.0 - smoothstep(0.0, 0.05, abs(fract(r * n_mode - TIME * 0.08) - 0.5) - 0.42);
	float edge = smoothstep(1.0, 0.75, r);
	float shimmer = 0.75 + 0.25 * sin(TIME * 4.0 + r * 20.0);
	vec3 c = tint * (line * 0.8 + rings * 0.35) * edge * shimmer * level * energy;
	ALBEDO = c;
	ALPHA = 1.0;
}
