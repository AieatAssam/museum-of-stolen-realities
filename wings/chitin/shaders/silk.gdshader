// A silk line: a real strand with sag, a satin sheen that runs along its length, beads of dew that
// catch the light, and a standing-wave shiver when plucked. Mesh: a CylinderMesh (axis = local Y,
// height `len`). Per-line values are instance uniforms, so every line shares one material.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

instance uniform float len = 8.0;
instance uniform float sag = 0.0;        // metres at the middle
instance uniform float pluck = 0.0;      // 0..1, decays in script
instance uniform float pitch = 1.0;
instance uniform float beads = 12.0;     // dew beads along the line
uniform vec4 silk : source_color = vec4(0.96, 0.9, 0.76, 1.0);
uniform vec4 glow : source_color = vec4(1.0, 0.78, 0.42, 1.0);
uniform float glow_energy = 1.4;
uniform float dew = 1.0;

varying float t;

void vertex() {
	t = VERTEX.y / max(len, 0.001) + 0.5;
	float bow = 4.0 * t * (1.0 - t);
	vec3 down = normalize((inverse(MODEL_MATRIX) * vec4(0.0, -1.0, 0.0, 0.0)).xyz);
	vec3 side = normalize(cross(down, vec3(0.0, 1.0, 0.0)) + vec3(1e-4));
	float wave = sin(3.14159 * t) * sin(TIME * 70.0 * pitch) * pluck * 0.12 + sin(6.2832 * t) * sin(TIME * 140.0 * pitch) * pluck * 0.04;
	VERTEX += down * sag * bow;
	VERTEX += side * wave;
	// a twisted-fibre look: thicken slightly in a slow spiral
	VERTEX.xz *= 1.0 + 0.18 * sin(VERTEX.y * 22.0 + atan(VERTEX.z, VERTEX.x) * 3.0);
}

void fragment() {
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALBEDO = silk.rgb;
	ROUGHNESS = 0.28;
	SPECULAR = 0.8;
	float sheen = pow(1.0 - ndv, 2.0);
	float d = fract(t * beads + sin(t * beads * 0.22) * 0.5);
	float bead = smoothstep(0.06, 0.0, abs(d - 0.5)) * dew;
	EMISSION = glow.rgb * glow_energy * (0.35 + 0.65 * sheen) + vec3(1.0, 0.95, 0.85) * bead * 3.0 + glow.rgb * pluck * 3.0;
}
