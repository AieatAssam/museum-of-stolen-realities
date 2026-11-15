shader_type canvas_item;
render_mode blend_mul, unshaded;
// A faint canvas weave over the whole view, so the picture never stops being a picture.

uniform float strength = 0.05;
uniform float threads_px = 3.0;

void fragment() {
	vec2 p = FRAGCOORD.xy / threads_px;
	float warp = sin(p.x * 3.14159) * 0.5 + 0.5;
	float weft = sin(p.y * 3.14159) * 0.5 + 0.5;
	float over = mod(floor(p.x) + floor(p.y), 2.0);
	float w = mix(warp, weft, over);
	COLOR = vec4(vec3(1.0 - strength + strength * w), 1.0);
}
