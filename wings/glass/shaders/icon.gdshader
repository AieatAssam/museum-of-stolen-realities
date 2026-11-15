shader_type spatial;
// A glass icon's robe: coloured glass lit from behind. The colour is the MultiMesh instance colour.
render_mode diffuse_burley;

uniform float energy = 1.4;
varying vec3 tint;

void vertex() {
	tint = COLOR.rgb;
}

void fragment() {
	float rim = 1.0 - abs(dot(NORMAL, VIEW));
	ALBEDO = tint * 0.15;
	ROUGHNESS = 0.08;
	SPECULAR = 0.7;
	EMISSION = tint * energy * (0.55 + 0.45 * rim);
}
