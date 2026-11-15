shader_type spatial;
render_mode unshaded, cull_back;
// The six living windows. `art` is the wing's painted view (hub/textures/portal_<id>.png); it is
// sampled with view-dependent parallax (near layers slide more than far ones, keyed on height in
// the picture) and each `medium` adds its own motion on top, so a frame reads as a window you are
// walking past, not a poster.
#include "res://core/shaders/noise.gdshaderinc"

uniform sampler2D art : source_color, filter_linear_mipmap_anisotropic;
uniform int medium = 0;
uniform vec4 c0 : source_color = vec4(1.0);
uniform vec4 c1 : source_color = vec4(0.5);
uniform vec4 c2 : source_color = vec4(0.0);
uniform float brightness = 1.15;
uniform float restoration = 0.0; // 1 = gallery closed: dust sheet, dimmer, slower
uniform float awaken = 1.0;      // 0..1, used by the intro and the endings

varying vec3 v_view_ts;

void vertex() {
	vec3 view_ws = normalize(CAMERA_POSITION_WORLD - (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz);
	vec3 t = normalize((MODEL_MATRIX * vec4(TANGENT, 0.0)).xyz);
	vec3 b = normalize((MODEL_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	vec3 n = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	v_view_ts = vec3(dot(view_ws, t), dot(view_ws, b), dot(view_ws, n));
}

void fragment() {
	vec2 uv = UV;                         // 0,0 = top-left of the picture
	float t = TIME * mix(1.0, 0.35, restoration);
	// parallax: the bottom of the picture (foreground) shifts most, the horizon least
	vec2 o = v_view_ts.xy / max(v_view_ts.z, 0.3);
	float depth = mix(0.02, 0.09, smoothstep(0.35, 1.0, uv.y));
	vec2 p = (uv - 0.5) * 0.9 + 0.5 - vec2(o.x, -o.y) * depth;
	p += vec2(sin(t * 0.07), cos(t * 0.05)) * 0.006; // slow breathing drift

	if (medium == 1) {            // clay: stop-motion boil at 12 fps
		float f = floor(TIME * 12.0);
		p += (vec2(n_hash(vec2(f, 1.0)), n_hash(vec2(f, 2.0))) - 0.5) * 0.0025;
	} else if (medium == 3) {     // aria: underwater wobble
		p += vec2(sin(p.y * 22.0 + t * 1.1), cos(p.x * 18.0 + t * 0.9)) * 0.0022;
	} else if (medium == 5) {     // paint: wet paint creeping
		p += (vec2(n_fbm(p * 5.0 + t * 0.05), n_fbm(p * 5.0 - t * 0.04 + 7.0)) - 0.5) * 0.008;
	}
	vec3 col = texture(art, p).rgb;
	float lum = dot(col, vec3(0.299, 0.587, 0.114));

	if (medium == 0) {            // glass: light beams sweeping through the panes
		float beam = smoothstep(0.08, 0.0, abs(fract(p.x * 1.2 - p.y * 0.6 - t * 0.03) - 0.5) - 0.2);
		col += col * beam * 0.35;
	} else if (medium == 2) {     // noir: rain and a flickering lamp
		float rx = floor(p.x * 220.0);
		float rain = step(0.94, fract(p.y * 2.5 - t * 2.2 + n_hash(vec2(rx, 1.0)) * 9.0)) * step(0.55, n_hash(vec2(rx, 4.0)));
		col += rain * 0.18;
		col *= 0.93 + 0.07 * step(0.08, n_hash(vec2(floor(TIME * 9.0), 3.0)));
		col = vec3(dot(col, vec3(0.333)));
	} else if (medium == 3) {     // aria: caustics and rising bubbles
		vec3 v = n_voronoi(p * 7.0 + vec2(t * 0.2, -t * 0.12));
		col += c1.rgb * pow(1.0 - smoothstep(0.0, 0.12, v.y), 3.0) * 0.18 * (1.0 - p.y);
		for (int i = 0; i < 10; i++) {
			float fi = float(i);
			vec2 bp = vec2(n_hash(vec2(fi, 7.0)), 1.0 - fract(n_hash(vec2(fi, 3.0)) + t * (0.03 + 0.03 * n_hash(vec2(fi, 9.0)))));
			col += vec3(0.8, 1.0, 1.0) * smoothstep(0.006, 0.002, abs(length((p - bp) * vec2(1.0, 1.56)) - 0.006)) * 0.6;
		}
	} else if (medium == 4) {     // chitin: the hive's glow pulses
		float pulse = 0.5 + 0.5 * sin(t * 0.9 + n_fbm(p * 4.0) * 6.0);
		col += col * smoothstep(0.55, 0.9, lum) * pulse * 0.4;
	} else if (medium == 5) {     // paint: a wet sheen slides over the impasto
		float sheen = pow(max(0.0, 1.0 - abs(fract(p.x * 0.6 + p.y * 0.4 - t * 0.04) - 0.5) * 5.0), 6.0);
		col += vec3(1.0) * sheen * 0.15 * smoothstep(0.3, 0.8, lum);
	}

	if (restoration > 0.0) {      // closed gallery: a dust sheet hangs over the window
		float weave = 0.5 + 0.5 * sin(UV.x * 1400.0) * sin(UV.y * 1400.0);
		float fold = n_fbm(vec2(UV.x * 3.0, UV.y * 0.6 + sin(TIME * 0.1) * 0.05));
		vec3 sheet = vec3(0.72, 0.68, 0.6) * (0.55 + 0.45 * fold) * (0.9 + 0.1 * weave);
		col = mix(col, sheet * 0.3 + col * 0.55, restoration * 0.35);
	}
	// edges sink into the moulding
	float e = smoothstep(0.0, 0.06, UV.x) * smoothstep(1.0, 0.94, UV.x) * smoothstep(0.0, 0.05, UV.y) * smoothstep(1.0, 0.95, UV.y);
	ALBEDO = col * brightness * mix(0.3, 1.0, e) * awaken;
}
