shader_type spatial;
// Broken edges of Exhibit 0's shards: raw strata glowing from within, warm gold.
#include "res://core/shaders/noise.gdshaderinc"

uniform float heat = 1.0;
uniform vec4 tint : source_color = vec4(1.0, 0.72, 0.36, 1.0);

varying vec3 opos;

void vertex() { opos = VERTEX; }

void fragment() {
	float r = length(opos);
	float strata = 0.5 + 0.5 * sin(r * 60.0 + n_fbm(opos.xy * 6.0) * 6.0);
	float crack = n_fbm(opos.xz * 9.0 + TIME * 0.05);
	ALBEDO = mix(vec3(0.08, 0.05, 0.03), vec3(0.3, 0.2, 0.1), strata);
	ROUGHNESS = 0.7;
	EMISSION = tint.rgb * (0.25 + 1.4 * pow(crack, 3.0) + 0.3 * strata) * heat;
}
