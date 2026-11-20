shader_type spatial;
// A shaft of coloured light: a soft translucent body, brightest down its core, feathered at the edges,
// with god-ray streaks running along its length. Additive, so the room shows through it. Walkable
// beams add a thin caustic skin (beam_walk.gdshader) at the walking height; this is the light itself.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

instance uniform vec4 beam_color : source_color = vec4(1.0, 0.9, 0.7, 1.0);
instance uniform float beam_len = 10.0;
uniform float intensity = 1.5;

varying vec3 local_pos;

void vertex() {
	local_pos = VERTEX;
}

void fragment() {
	float nv = abs(dot(NORMAL, VIEW));
	// near the eye (standing in a beam) the core would fill the screen: let it thin to halo
	float near = smoothstep(1.5, 9.0, length(VERTEX));
	float core = pow(nv, 5.0) * mix(0.1, 1.0, near);
	float halo = pow(nv, 1.8) * mix(0.4, 1.0, near);
	// along-beam coordinate in metres (cylinder Y axis was stretched to length)
	float along = (local_pos.y + 0.5) * beam_len;
	// god-ray streaks: constant along the length, drifting slowly around the shaft
	float ang = atan(local_pos.z, local_pos.x);
	float rays = 0.55 + 0.45 * sin(ang * 9.0 + TIME * 0.35) * sin(ang * 5.0 - TIME * 0.22 + along * 0.05);
	// fade the ends so the shaft meets surfaces softly
	float ends = smoothstep(0.0, 0.15, along) * smoothstep(0.0, 0.15, beam_len - along);  // short: the shaft must reach the mirror it hits
	vec3 c = beam_color.rgb;
	vec3 warm = mix(c, vec3(1.0), 0.15);  // stays in the beam's own colour: no clipping to white
	ALBEDO = (c * halo * 0.5 * rays + warm * core * 0.75) * intensity * ends;
}
