shader_type spatial;
// A solid beam of coloured light: a hot core, a soft fresnel halo, motes drifting along it and
// faint lead-line bands so it reads as *glass light* you could stand on.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
instance uniform float beam_len = 10.0;
uniform float intensity = 1.9;

varying vec3 local_pos;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void vertex() {
	local_pos = VERTEX;
}

void fragment() {
	float nv = abs(dot(NORMAL, VIEW));
	// near the eye (standing on a beam) the core would fill the screen white: let it thin to halo
	float near = smoothstep(1.5, 9.0, length(VERTEX));
	float core = pow(nv, 9.0) * mix(0.12, 1.0, near);
	float halo = pow(nv, 1.6) * mix(0.45, 1.0, near);
	// along-beam coordinate in metres (cylinder Y axis was stretched to length)
	float along = (local_pos.y + 0.5) * beam_len;
	float t = TIME * 1.4;
	float motes = smoothstep(0.82, 1.0, hash(vec2(floor(along * 3.0 - t * 3.0), floor(local_pos.x * 9.0 + local_pos.z * 7.0))));
	float bands = 0.75 + 0.25 * sin(along * 1.7 - t * 2.0);
	// fade the last half-metre at each end so slabs meet surfaces softly
	float ends = smoothstep(0.0, 0.5, along) * smoothstep(0.0, 0.35, beam_len - along);
	// caustic sparkle where it lands: glints flicker in the last metre
	float land = smoothstep(1.2, 0.2, beam_len - along);
	float glint = land * step(0.93, hash(vec2(floor(along * 8.0), floor(local_pos.x * 23.0 + local_pos.z * 19.0) + floor(TIME * 9.0))));
	vec3 c = beam_color.rgb;
	vec3 hot = mix(c, vec3(1.0), 0.55);
	ALBEDO = (c * halo * 0.55 * bands + hot * core * 1.4 + c * motes * 0.8) * intensity * ends + mix(c, vec3(1.0), 0.6) * glint * 3.0;
}
