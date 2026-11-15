shader_type spatial;
// The onlooker: a vast silhouette (head, hand, loupe) pressed against the far side of the sky window.
// A quad far out along its gaze (glass.gd places it); fully opaque black where it blocks the light
// (the sky behind is HDR, so any leak shows), a warm rim where the outside light wraps its edge.
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D shape : hint_default_white, filter_linear_mipmap;
uniform float reveal = 0.0;

void fragment() {
	vec2 uv = vec2(1.0 - UV.x, UV.y);  // seen from its back face
	float edge = smoothstep(0.0, 0.1, uv.x) * smoothstep(1.0, 0.82, uv.x) * smoothstep(0.0, 0.06, uv.y) * smoothstep(1.0, 0.72, uv.y);
	float m = smoothstep(0.25, 0.55, 1.0 - textureLod(shape, uv, 0.0).r) * edge;  // shoulders and border melt into the light
	float soft = 1.0 - textureLod(shape, uv, 4.0).r;
	float rim = clamp(soft * edge - m, 0.0, 1.0);
	ALBEDO = mix(vec3(1.0, 0.72, 0.42) * rim * 3.0, vec3(0.0), m);
	ALPHA = clamp(m + rim * 0.9, 0.0, 1.0) * reveal;
}
