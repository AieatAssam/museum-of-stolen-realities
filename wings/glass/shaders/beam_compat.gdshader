shader_type spatial;
// The Compatibility-renderer beam (web build): no instance uniforms, no HDR glow, so the shaft is
// built from plain emission instead. Bright down the core, feathered toward the rim, ends softened.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
uniform float beam_len = 10.0;
uniform float intensity = 1.0;

varying vec3 local_pos;

void vertex() {
	local_pos = VERTEX;
}

void fragment() {
	float nv = abs(dot(NORMAL, VIEW));
	float rim = smoothstep(0.0, 0.7, nv) * (1.0 - smoothstep(0.7, 1.0, nv)) * 0.5 + smoothstep(0.0, 0.5, nv) * 0.5;
	float core = pow(nv, 2.5);
	float along = (local_pos.y + 0.5) * beam_len;
	float ends = smoothstep(0.0, 0.15, along) * smoothstep(0.0, 0.15, beam_len - along);
	vec3 c = beam_color.rgb;
	ALBEDO = (c * (0.22 * rim + 0.5 * core) + mix(c, vec3(1.0), 0.3) * 0.08) * intensity * ends;
}
