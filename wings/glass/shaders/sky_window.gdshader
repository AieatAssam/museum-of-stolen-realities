shader_type sky;
render_mode use_half_res_pass;
// The sky of the Vitrine Kingdom is ONE window: a colossal leaded dome lit from outside. Panes are laid
// in rings like a real rose (fewer, larger panes toward the crown), held by black lead and a heavy iron
// armature of meridians and rings. Three suns are glazed into it. Once `reveal` rises, something
// museum-sized leans over it: a head and a raised hand with a loupe (the `onlooker` silhouette),
// throwing the glass behind it into shadow, its edge rimmed by the outside light.
// `haze` (1 = the interior haze that hides the leading) clears on the rooftops.

uniform vec3 sun_a = vec3(0.35, 0.55, -0.76);
uniform vec3 sun_b = vec3(-0.62, 0.42, -0.66);
uniform vec3 sun_c = vec3(0.1, 0.78, 0.62);
uniform vec3 eye_dir = vec3(-0.75, 0.45, -0.48);
uniform sampler2D onlooker : hint_default_white, filter_linear_mipmap;
uniform vec2 onlooker_ext = vec2(2.3, 1.75);   // radians across, up
uniform float haze : hint_range(0.0, 1.0) = 1.0;
uniform float reveal : hint_range(0.0, 1.0) = 0.0;
uniform float dark : hint_range(0.0, 1.0) = 0.0;
uniform float rings = 14.0;
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
	// rings: index and distance (radians) to the nearest ring lead
	float rr = e01 * rings;
	float ri = floor(rr);
	float rf = fract(rr);
	float d_ring = min(rf, 1.0 - rf) * 1.5708 / rings;
	// sectors per ring shrink toward the crown, in multiples of 8 so the meridians run through
	float nsec = max(8.0, floor(96.0 * cos((ri + 0.5) / rings * 1.5708) / 8.0) * 8.0);
	float sa = (az / 6.2831853 + 0.5) * nsec;
	float si = floor(sa);
	float sf = fract(sa);
	float d_sec = min(sf, 1.0 - sf) * 6.2831853 / nsec * cos(el);
	float pid = h1(vec2(ri, si));
	vec3 glass = pal(pid);
	// painted grisaille and streaky antique glass inside each pane
	vec2 local = vec2(sf, rf);
	float streak = 0.88 + 0.12 * sin(local.y * 4.0 + sin(local.x * 5.0 + pid * 40.0) * 1.5);
	float centre = 1.0 - 0.35 * length(local - 0.5);
	glass *= streak * centre * (0.7 + 0.6 * h1(vec2(si, ri) + 3.3));
	float px = fwidth(el) + 0.0005;
	float lead = 1.0 - smoothstep(0.0035, 0.0035 + px, min(d_ring, d_sec));
	// the iron armature: every 8th meridian, every 4th ring, much heavier
	float mer = abs(fract(az / 6.2831853 * 8.0 + 0.5 / 8.0 * 0.0) - 0.5) * 2.0;
	float d_mer = (1.0 - mer) * 6.2831853 / 16.0 * cos(el);
	float ring4 = abs(fract(rr / 4.0) - 0.5) * 2.0;
	float d_r4 = (1.0 - ring4) * 1.5708 / rings * 2.0;
	float iron = 1.0 - smoothstep(0.012, 0.012 + px, min(d_mer, d_r4));
	iron = max(iron, 1.0 - smoothstep(0.02, 0.02 + px, 1.5708 - el));  // the boss at the crown

	float suns = sun(d, sun_a, 0.075) + sun(d, sun_b, 0.06) * 0.9 + sun(d, sun_c, 0.05) * 0.8;
	float corona = pow(max(dot(d, normalize(sun_a)), 0.0), 10.0) * 1.6 + pow(max(dot(d, normalize(sun_b)), 0.0), 14.0) + pow(max(dot(d, normalize(sun_c)), 0.0), 16.0) * 0.7;
	vec3 col = glass * energy * (0.55 + corona * 2.2 + 0.25 * e01);
	col = mix(col, vec3(0.004, 0.004, 0.006), max(lead, iron) * (1.0 - suns));
	col += vec3(1.0, 0.86, 0.55) * suns * 7.0;

	// the onlooker
	if (reveal > 0.001) {
		vec3 f = normalize(eye_dir);
		vec3 rgt = normalize(cross(f, vec3(0.0, 1.0, 0.0)));
		vec3 up = cross(rgt, f);
		float fz = dot(d, f);
		if (fz > 0.0) {
			vec2 ang = vec2(atan(dot(d, rgt), fz), atan(dot(d, up), fz));
			vec2 uv = vec2(0.5 + ang.x / onlooker_ext.x, 0.5 - ang.y / onlooker_ext.y);
			if (uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0) {
				float m = 1.0 - textureLod(onlooker, uv, 1.5).r;
				float soft = 1.0 - textureLod(onlooker, uv, 3.5).r;
				float rim = clamp(soft - m, 0.0, 1.0);
				vec3 shadowed = col * 0.03 + vec3(0.003, 0.004, 0.008);
				col = mix(col, shadowed, clamp(max(m, soft * 0.6), 0.0, 1.0) * reveal);
				col += vec3(1.0, 0.78, 0.5) * rim * rim * 1.2 * reveal * (1.0 - m);
			}
		}
	}

	vec3 fogc = mix(vec3(0.02, 0.03, 0.08), vec3(0.08, 0.1, 0.22), smoothstep(-0.2, 0.6, d.y));
	col = mix(col, fogc + vec3(1.0, 0.86, 0.55) * suns * 2.0, haze * 0.85);
	if (d.y < 0.0) col = mix(col, vec3(0.005, 0.006, 0.015), smoothstep(0.0, -0.15, d.y));
	col *= 1.0 - dark * 0.92;
	COLOR = col;
	}
}
