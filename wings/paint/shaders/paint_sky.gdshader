shader_type sky;
render_mode use_half_res_pass;
// The sky is painted: two oil studies (fair and storm) wrapped around the dome and blended by the
// painter's mood, drifting slowly, fading into a haze band at the horizon. Below the horizon, an
// unfinished landscape laid in bands. The sun is a thick dab of light, not a disc.

uniform sampler2D fair : source_color, filter_linear, repeat_enable;
uniform sampler2D storm : source_color, filter_linear, repeat_enable;
uniform float storm_amount : hint_range(0.0, 1.0) = 0.0;
uniform vec3 tint : source_color = vec3(1.0);
uniform vec3 haze : source_color = vec3(1.0, 0.86, 0.68);
uniform vec3 below : source_color = vec3(0.62, 0.50, 0.30);
uniform float haze_width = 0.18;
uniform float energy = 1.0;
uniform float drift = 0.0015;

void sky() {
	vec3 d = normalize(EYEDIR);
	float el = asin(clamp(d.y, -1.0, 1.0));
	float u = fract((atan(d.x, d.z) / TAU + 0.5) * 2.0 + TIME * drift);
	float v = 1.0 - clamp(pow(max(el, 0.0) / 1.5708, 0.8), 0.0, 1.0);
	// two wraps of the study; each seam is hidden under a crossfade with the study's own middle
	float seam = smoothstep(0.0, 0.14, min(u, 1.0 - u));
	vec2 uv = vec2(u, mix(0.02, 0.98, v));
	vec2 uv2 = vec2(fract(u + 0.5), uv.y);
	vec3 cf = mix(texture(fair, uv2).rgb, texture(fair, uv).rgb, seam);
	vec3 cs = mix(texture(storm, uv2).rgb, texture(storm, uv).rgb, seam);
	vec3 c = mix(cf, cs, storm_amount);
	c *= tint;
	c = mix(c, haze, smoothstep(haze_width, 0.0, el) * 0.85);
	if (LIGHT0_ENABLED) {
		float s = dot(d, LIGHT0_DIRECTION);
		c += LIGHT0_COLOR * (smoothstep(0.9975, 0.999, s) * 2.0 + pow(max(s, 0.0), 40.0) * 0.35) * (1.0 - storm_amount * 0.7);
	}
	// below the horizon: the landscape the picture never finished, laid in bands of field colour
	// (the study's own strokes as the brushwork), dissolving into haze toward the horizon
	float dn = max(-el, 0.0);
	vec2 luv = vec2(u * 3.0, fract(0.3 / (dn + 0.04) * 0.25));
	float br = dot(texture(fair, luv).rgb, vec3(0.33));
	float band = fract(0.12 / (dn + 0.03) + 0.4 * sin(u * TAU * 3.0));
	vec3 land = mix(below, vec3(0.42, 0.55, 0.30), smoothstep(0.3, 0.7, band));
	land = mix(land, vec3(0.56, 0.48, 0.74), smoothstep(0.75, 0.95, band) * 0.6);
	land *= 0.75 + 0.5 * br;
	land = mix(land, haze, smoothstep(0.25, 0.0, dn) * 0.7);
	c = mix(c, land, smoothstep(0.0, -0.03, el));
	COLOR = c * energy;
}
