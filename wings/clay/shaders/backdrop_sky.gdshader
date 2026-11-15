shader_type sky;
render_mode use_half_res_pass;
// The painted backdrop flat around the set: a scenic-paint gradient with visible brush strokes, a
// cut-out painted sun, and pin-prick stars once the studio lights go down. Colours are driven per
// area by clay_look.gd (morning at the meadow, dusk over the village, night at the workbench).

uniform vec3 zenith : source_color = vec3(0.30, 0.55, 0.92);
uniform vec3 horizon : source_color = vec3(0.78, 0.88, 0.98);
uniform vec3 below : source_color = vec3(0.16, 0.22, 0.12);
uniform vec3 sun_col : source_color = vec3(1.0, 0.92, 0.7);
uniform float sun_size = 0.045;
uniform float stars = 0.0;
uniform float energy = 1.0;
uniform sampler2D canvas : source_color, filter_linear_mipmap, repeat_enable;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(41.3, 289.1))) * 45758.5453);
}

void sky() {
	vec3 d = EYEDIR;
	float el = d.y;
	vec2 cyl = vec2(atan(d.x, d.z) / 6.2831853 * 6.0, el * 2.2);
	float strokes = dot(texture(canvas, cyl).rgb, vec3(0.333)) / 0.78;
	float strokes2 = dot(texture(canvas, cyl * 0.41 + 0.2).rgb, vec3(0.333)) / 0.78;
	float g = smoothstep(-0.02, 0.55, el + (strokes2 - 1.0) * 0.12);
	vec3 col = mix(horizon, zenith, g);
	col *= mix(1.0, strokes, 0.55);
	col = mix(below, col, smoothstep(-0.06, 0.0, el));
	// painted sun: a flat disc with a soft painted halo
	float sd = distance(d, normalize(LIGHT0_DIRECTION));
	if (LIGHT0_ENABLED) {
		col = mix(col, sun_col * 1.4, (1.0 - smoothstep(sun_size * 0.9, sun_size, sd)));
		col += sun_col * 0.25 * (1.0 - smoothstep(sun_size, sun_size * 5.0, sd));
	}
	// stars: pin-holes pricked in the night flat, round on the dome (3D cells on the view sphere, so
	// they never stretch the way the cylindrical brush strokes do)
	vec3 q = d * 70.0;
	vec3 c = floor(q);
	float hs = fract(sin(dot(c, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
	vec3 o = c + 0.5 + (vec3(fract(hs * 13.1), fract(hs * 71.7), fract(hs * 37.3)) - 0.5) * 0.5;
	float pr = 0.09 + 0.08 * fract(hs * 5.3);
	float s = step(0.93, hs) * (1.0 - smoothstep(pr * 0.5, pr, length(q - o))) * smoothstep(0.05, 0.3, el);
	col = mix(col, vec3(1.0, 0.95, 0.85) * (1.2 + 1.5 * fract(hs * 3.1)), s * stars);
	COLOR = col * energy;
}
