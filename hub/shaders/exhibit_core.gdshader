shader_type spatial;
// Broken edges of Exhibit 0's shards: gold leaf laid along the breaks (kintsugi), with light from
// the world inside leaking through the seams.
#include "res://core/shaders/noise.gdshaderinc"

uniform float heat = 1.0;
uniform vec4 tint : source_color = vec4(1.0, 0.72, 0.36, 1.0);

varying vec3 opos;

void vertex() { opos = VERTEX; }

void fragment() {
	float n = n_fbm(opos.xz * 14.0 + opos.y * 5.0);
	float leak = pow(n_fbm(opos.xy * 6.0 + TIME * 0.06), 2.0);
	ALBEDO = vec3(1.0, 0.78, 0.42) * (0.75 + 0.25 * n);
	METALLIC = 1.0;
	ROUGHNESS = 0.22 + 0.2 * n;
	EMISSION = tint.rgb * (0.35 + 2.2 * leak) * heat;
}
