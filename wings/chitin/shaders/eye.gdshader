// The eye-sky: a compound eye seen from inside. Hex facets laid out by stereographic projection (small
// at the crown, growing toward the rim, like a real eye), each a recessed lens with a parallaxed amber
// core and a glint, dark seams between. The pseudopupil is physical: the facets whose axes point at
// the viewer go dark, so a black pupil follows the player wherever she stands. Seams are filtered
// with fwidth, so no moire at distance.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled;

uniform vec4 glow : source_color = vec4(1.0, 0.6, 0.18, 1.0);
uniform float energy = 0.55;       // tweened to ~0 for a blink
uniform float radius = 60.0;
uniform float facet = 3.6;         // facet size in projected metres
uniform float pupil_in = 0.975;    // cos of the pupil's dark core
uniform float pupil_out = 0.93;    // cos of its soft edge

varying vec3 lpos;
varying vec3 lcam;

void vertex() {
	lpos = VERTEX;
	lcam = (inverse(MODEL_MATRIX) * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// xy: offset from the cell centre, zw: cell id (centre in lattice units)
vec4 hexcell(vec2 p) {
	const vec2 s = vec2(1.0, 1.7320508);
	vec4 hc = floor(vec4(p, p - vec2(0.5, 1.0)) / s.xyxy) + 0.5;
	vec4 h = vec4(p - hc.xy * s, p - (hc.zw + 0.5) * s);
	return dot(h.xy, h.xy) < dot(h.zw, h.zw) ? vec4(h.xy, hc.xy * s) : vec4(h.zw, (hc.zw + 0.5) * s);
}

vec3 unproject(vec2 q) {
	float s = 4.0 * radius * radius / (dot(q, q) + 4.0 * radius * radius);
	return vec3(s * q.x, -radius + 2.0 * radius * s, s * q.y);
}

void fragment() {
	vec2 q = lpos.xz * 2.0 * radius / (radius + max(lpos.y, 0.0));
	vec4 h = hexcell(q / facet);
	vec2 loc = h.xy;
	float d = max(dot(abs(loc), vec2(0.5, 0.8660254)), abs(loc.x));   // hex distance, edge at 0.5
	float aa = fwidth(d) * 1.5 + 1e-4;
	float lens = smoothstep(0.035, 0.035 + aa, 0.5 - d);               // 0 in the seams
	vec3 v = normalize(lcam - lpos);
	// recessed core: parallax the glow against the view, so each facet reads as a lens with depth
	vec2 par = v.xz * 0.22;
	float r = length(loc + par) / 0.5;
	float core = exp(-r * r * 2.2);
	float rim = smoothstep(0.25, 0.5, d) * lens;                        // a darker lens rim
	float glint = smoothstep(0.14, 0.0, length(loc - vec2(-0.16, 0.14) - par * 0.6)) * lens;
	// pseudopupil, per facet: its axis points into the eye (toward the dome centre)
	vec3 axis = -normalize(unproject(h.zw * facet));
	float pp = smoothstep(pupil_out, pupil_in, dot(axis, v));
	float cell = 0.82 + 0.36 * hash(h.zw);
	float band = 0.85 + 0.15 * sin(length(q) * 0.11);                   // faint iris banding
	vec3 lit = glow.rgb * (0.18 + 1.25 * core) * cell * band * (1.0 - 0.45 * rim);
	lit += vec3(1.0, 0.9, 0.7) * glint * 0.8;
	vec3 col = mix(vec3(0.02, 0.012, 0.006), lit, lens);
	col *= mix(1.0, 0.04, pp);
	col += glow.rgb * 0.12 * pp * smoothstep(pupil_in, pupil_out, dot(axis, v) + 0.01);  // ember edge
	ALBEDO = col * energy * 1.8;
}
