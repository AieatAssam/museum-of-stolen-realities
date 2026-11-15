shader_type spatial;
// The prism's dispersed light on the floor: a fan of spectrum (vertex colours), added over whatever
// lies beneath, strongest at the crystal and dying with distance.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform float energy = 2.4;

void fragment() {
	ALBEDO = COLOR.rgb * COLOR.a * energy;
}
