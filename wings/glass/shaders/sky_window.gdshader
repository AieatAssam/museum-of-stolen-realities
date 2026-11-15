shader_type sky;
render_mode use_half_res_pass;
// The sky of the Vitrine Kingdom is ONE window: a colossal leaded dome lit from outside. Panes are laid
// in rings like a real rose (fewer, larger panes toward the crown), held by black lead and a heavy iron
// armature of meridians and rings. Three suns are glazed into it. (The onlooker that leans over it
// after the reveal is a far quad, shaders/onlooker.gdshader, placed by glass.gd.)
// `haze` (1 = the interior haze that hides the leading) clears on the rooftops.

uniform vec3 sun_a = vec3(0.35, 0.55, -0.76);
uniform vec3 sun_b = vec3(-0.62, 0.42, -0.66);
uniform vec3 sun_c = vec3(0.1, 0.78, 0.62);
uniform sampler2D dome : source_color, filter_linear_mipmap;
uniform float haze : hint_range(0.0, 1.0) = 1.0;
uniform float reveal : hint_range(0.0, 1.0) = 0.0;
uniform float dark : hint_range(0.0, 1.0) = 0.0;
uniform float energy = 1.5;

float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

vec3 pal(float k) {
	if (k < 0.30) return vec3(0.10, 0.22, 0.75);
	if (k < 0.48) return vec3(0.05, 0.10, 0.42);
	if (k < 0.60) return vec3(0.70, 0.08, 0.16);
	if (k < 0.74) return vec3(0.95, 0.66, 0.20);
	if (k < 0.84) return vec3(0.06, 0.42, 0.30);
	if (k < 0.92) return vec3(0.40, 0.16, 0.66);
	return vec3(0.75, 0.80, 0.85);
}

float sun(vec3 d, vec3 s, float size) {
	return smoothstep(cos(size), cos(size * 0.7), dot(d, normalize(s)));
}

void sky() {
	if (!AT_HALF_RES_PASS && !AT_CUBEMAP_PASS) {
		COLOR = HALF_RES_COLOR.rgb;
	} else {
	vec3 d = EYEDIR;
	float el = asin(clamp(d.y, -1.0, 1.0));
	float az = atan(d.x, d.z);
	float e01 = clamp(el / 1.5708, 0.0, 1.0);
	// the dome is one colossal wheel window (sky_rose), zenith at its boss, its rim on the horizon
	vec2 pol = vec2(sin(az), cos(az)) * (1.0 - e01) * 0.5;
	vec2 duv = 0.5 + pol;
	float px = fwidth(el) + 0.0005;
	vec3 glass = textureLod(dome, duv, 0.0).rgb;
	// hand-blown: streaks, seeds and uneven thickness, and an uneven light behind it
	float streak = 0.85 + 0.15 * sin(duv.y * 900.0 + sin(duv.x * 140.0) * 3.0);
	float seeds = 1.0 + 0.5 * step(0.995, h1(floor(duv * 700.0)));
	float back = 0.55 + 0.9 * smoothstep(-0.3, 1.0, sin(az * 2.0 + 1.3) * 0.5 + sin(e01 * 5.0 + az) * 0.5);
	glass *= streak * seeds * back * 1.6;
	float lead = 1.0 - smoothstep(0.02, 0.06, dot(glass, vec3(0.33)));  // the art's own black tracery
	float iron = 0.0;
	float suns = sun(d, sun_a, 0.075) + sun(d, sun_b, 0.06) * 0.9 + sun(d, sun_c, 0.05) * 0.8;
	float corona = pow(max(dot(d, normalize(sun_a)), 0.0), 10.0) * 1.6 + pow(max(dot(d, normalize(sun_b)), 0.0), 14.0) + pow(max(dot(d, normalize(sun_c)), 0.0), 16.0) * 0.7;
	vec3 col = glass * energy * (0.55 + corona * 2.2 + 0.25 * e01);
	col = mix(col, vec3(0.004, 0.004, 0.006), max(lead, iron) * (1.0 - suns));
	col += vec3(1.0, 0.86, 0.55) * suns * 7.0;

	vec3 fogc = mix(vec3(0.02, 0.03, 0.08), vec3(0.08, 0.1, 0.22), smoothstep(-0.2, 0.6, d.y));
	col = mix(col, fogc + vec3(1.0, 0.86, 0.55) * suns * 2.0, haze * 0.85);
	if (d.y < 0.0) col = mix(col, vec3(0.005, 0.006, 0.015), smoothstep(0.0, -0.15, d.y));
	col *= dark > 0.96 ? 0.0 : 1.0 - dark * 0.92;  // the Widow's black is total; the heist only dims
	COLOR = col;
	}
}
