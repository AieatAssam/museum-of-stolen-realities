shader_type spatial;
// Exhibit 0's outer skin: Vesper's world, small and still wet. Oceans, coasts, a few cities' lights
// on the night side, cloud wisps. Mapped by object-space direction so shards line up.
#include "res://core/shaders/noise.gdshaderinc"

uniform float wet = 1.0;
uniform float glow = 1.0;

varying vec3 dir;

void vertex() { dir = normalize(VERTEX); }

float fbm3(vec3 p) {
	return n_fbm(p.xy + p.z * 1.7) * 0.5 + n_fbm(p.yz * 1.1 + 3.1) * 0.5;
}

void fragment() {
	vec3 d = normalize(dir);
	float land = fbm3(d * 2.2 + 1.3);
	float coast = smoothstep(0.5, 0.53, land);
	vec3 ocean = mix(vec3(0.02, 0.08, 0.14), vec3(0.05, 0.22, 0.3), smoothstep(0.3, 0.5, land));
	vec3 ground = mix(vec3(0.32, 0.36, 0.16), vec3(0.55, 0.45, 0.28), smoothstep(0.55, 0.7, land));
	ground = mix(ground, vec3(0.85, 0.85, 0.82), smoothstep(0.75, 0.9, abs(d.y)));
	vec3 col = mix(ocean, ground, coast);
	float cloud = smoothstep(0.55, 0.72, fbm3(d * 3.5 + vec3(TIME * 0.01, 0.0, 0.0)));
	col = mix(col, vec3(0.9, 0.9, 0.88), cloud * 0.55);
	float cities = step(0.985, n_hash(floor(d.xz * 90.0 + d.y * 40.0))) * coast * (1.0 - cloud);
	ALBEDO = col;
	ROUGHNESS = mix(mix(0.08, 0.45, coast), 0.6, cloud) / mix(1.0, 1.6, wet);
	SPECULAR = 0.7;
	EMISSION = vec3(1.0, 0.75, 0.4) * cities * 2.5 * glow;
	RIM = 0.6;
	RIM_TINT = 0.3;
}
