shader_type spatial;
// The light a mirror is receiving: a soft additive disc over its face, lit only while struck.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 glow_color : source_color = vec4(1.0);
uniform float strength = 0.0;

void fragment() {
	float r = length(UV * 2.0 - 1.0);
	ALBEDO = glow_color.rgb * smoothstep(1.0, 0.25, r) * strength;
}
