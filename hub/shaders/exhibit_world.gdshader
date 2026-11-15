shader_type spatial;
// The world kept inside Exhibit 0: oceans, coasts, cloud and the lights of cities, lit from within
// so it glows like a lantern through the crystal. Mapped by object-space direction.
#include "res://core/shaders/noise.gdshaderinc"

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
	vec3 ocean = mix(vec3(0.02, 0.1, 0.2), vec3(0.08, 0.32, 0.42), smoothstep(0.3, 0.5, land));
	vec3 ground = mix(vec3(0.3, 0.42, 0.16), vec3(0.62, 0.5, 0.3), smoothstep(0.55, 0.7, land));
	ground = mix(ground, vec3(0.9, 0.9, 0.86), smoothstep(0.75, 0.9, abs(d.y)));
	vec3 col = mix(ocean, ground, coast);
	float cloud = smoothstep(0.55, 0.72, fbm3(d * 3.5 + vec3(TIME * 0.01, 0.0, 0.0)));
	col = mix(col, vec3(0.95, 0.93, 0.9), cloud * 0.6);
	float cities = step(0.982, n_hash(floor(d.xz * 90.0 + d.y * 40.0))) * coast * (1.0 - cloud);
	float f = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = col;
	ROUGHNESS = mix(0.15, 0.6, coast);
	EMISSION = (col * 0.55 + vec3(1.0, 0.75, 0.4) * cities * 3.0 + vec3(0.5, 0.75, 1.0) * f * 0.8) * glow;
}
