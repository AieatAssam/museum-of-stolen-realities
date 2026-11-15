shader_type spatial;
// The onlooker: a vast face and hand with a loupe pressed to the far side of the sky window, seen
// through the glass (textures/onlooker_face.png, keyed RGBA: dark indigo form, warm rim, a glint in
// the magnified eye). A quad far out along its gaze; glass.gd places it. Borders melt; `reveal` fades it.
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D face : source_color, filter_linear_mipmap;
uniform float reveal = 0.0;

void fragment() {
	vec2 uv = UV;
	vec4 f = texture(face, uv);
	float edge = smoothstep(0.0, 0.08, uv.x) * smoothstep(1.0, 0.9, uv.x) * smoothstep(0.0, 0.05, uv.y) * smoothstep(1.0, 0.8, uv.y);
	// through a few metres of tinted glass: the form stays readable, the rim and the eye carry
	vec3 c = mix(f.rgb * 1.15, vec3(0.06, 0.08, 0.2), 0.2) + f.rgb * smoothstep(0.55, 0.9, max(f.r, f.g)) * 3.0;
	ALBEDO = c;
	ALPHA = f.a * edge * reveal;
}
