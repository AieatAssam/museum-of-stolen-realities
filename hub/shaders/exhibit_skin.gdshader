shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;
// Exhibit 0's vessel: thick clear crystal. Each pixel of the shell refracts what lies behind it (the
// opaque scene in the screen texture, depth-checked so nothing in front smears in), then marches the
// hollow interior (an analytic sphere around `centre`, stopping at the world globe) and adds the
// light that lives inside: a warm glow, plus one weather per returned fragment in its own sector,
// each gated by its own uniform (0 = absent, 1 = fully home); see wing_light().
// Etched filigree catches light; fresnel carries a warm reflection of the hall.
#include "res://core/shaders/noise.gdshaderinc"

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform vec4 tint : source_color = vec4(1.0, 0.86, 0.62, 1.0);
uniform float refraction = 0.05;
uniform float glow = 1.0;
uniform float volume = 1.0;        // 0 on the loose chips (they are outside the vessel)
uniform vec3 centre = vec3(0.0, 6.2, 0.0);
uniform float r_shell = 2.25;
uniform float r_world = 1.5;
uniform float w_glass = 0.0;
uniform float w_clay = 0.0;
uniform float w_noir = 0.0;
uniform float w_aria = 0.0;
uniform float w_chitin = 0.0;
uniform float w_paint = 0.0;

varying vec3 opos;
varying vec3 wpos;

void vertex() {
	opos = VERTEX;
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float v3(vec3 p) {
	vec3 i = floor(p), f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
		mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
vec3 hue(float h) { return clamp(abs(fract(h + vec3(0.0, 2.0, 1.0) / 3.0) * 6.0 - 3.0) - 1.0, 0.0, 1.0); }

// One wing's weather at p, unweighted. Each has ONE hue and ONE motion so it reads at a glance:
//   0 glass  prismatic shards: hard-edged facets flashing through the spectrum
//   1 clay   terracotta, a slow thick churn stepped at 12 fps
//   2 noir   silver rain on black, falling straight and fast
//   3 aria   teal standing waves: shells breathing in place
//   4 chitin amber hex cells pulsing like a hive
//   5 paint  violet brush strokes combed round a swirl
vec3 wing_light(int k, vec3 p, float t) {
	float r = length(p);
	if (k == 0) {
		vec3 q = p * 2.6 + vec3(0.0, t * 0.08, 0.0);
		float cell = h3(floor(q + floor(q.yzx * 0.5)));  // staggered facets, not a grid
		vec3 f = abs(fract(q) - 0.5);
		float edge = smoothstep(0.5, 0.38, max(f.x, max(f.y, f.z)));
		float flash = pow(0.5 + 0.5 * sin(t * 1.6 + cell * 40.0), 6.0);
		return hue(cell + t * 0.03) * step(0.45, cell) * edge * (0.35 + 1.4 * flash) * 1.3;
	} else if (k == 1) {
		float f = floor(t * 12.0);
		float b = v3(p * 1.3 + vec3(0.0, f / 12.0 * 0.25, 0.0) + f * 0.011);
		return vec3(1.0, 0.36, 0.16) * smoothstep(0.45, 0.7, b) * 1.1;
	} else if (k == 2) {
		vec2 col = floor(p.xz * 9.0);
		float sp = 2.6 + 1.6 * h3(vec3(col, 1.0));
		float y = fract(p.y * 0.8 + t * sp * 0.4 + h3(vec3(col, 2.0)));
		vec2 fx = fract(p.xz * 9.0) - 0.5;
		float streak = smoothstep(0.1, 0.0, length(fx)) * smoothstep(0.0, 0.05, y) * smoothstep(0.35, 0.05, y);
		return vec3(0.82, 0.86, 0.92) * streak * 2.4 * step(0.72, h3(vec3(col, 4.0)));  // sparse: lines on black, not haze
	} else if (k == 3) {
		float s = sin(r * 9.0) * sin(t * 1.3);
		return vec3(0.12, 0.78, 0.74) * pow(abs(s), 6.0) * 1.3;
	} else if (k == 4) {
		vec2 h = vec2(p.x + p.y * 0.5, p.y * 0.866) * 3.2;
		vec2 hf = fract(h) - 0.5;
		float cell = h3(vec3(floor(h), 7.0));
		float wall = smoothstep(0.38, 0.48, max(abs(hf.x), abs(hf.y)));
		float pulse = 0.5 + 0.5 * sin(t * 0.9 + cell * 6.28);
		return vec3(1.0, 0.7, 0.12) * (0.15 + 0.85 * pulse * step(0.4, cell) * (1.0 - wall) + wall * 0.5) * 0.8;
	}
	float a = atan(p.z, p.x) + t * 0.12 + r * 1.4;
	float stroke = v3(vec3(a * 2.5, p.y * 7.0, r * 2.0));
	float band = smoothstep(0.55, 0.68, stroke) * smoothstep(0.95, 0.78, stroke);
	return vec3(0.4, 0.1, 1.0) * band * (0.7 + 0.6 * v3(vec3(a * 24.0, p.y * 3.0, 1.0))) * 1.4;  // bristle streaks
}

// light emitted per metre at p (p relative to the centre, metres). The interior is cut into six
// 60-degree sectors, one per wing in WING_ORDER, turning slowly so each faces the entrance in turn;
// a sector is dark-warm until its fragment comes home. One weather per sample keeps the march cheap.
vec3 weather(vec3 p, float t) {
	float r = length(p);
	vec3 c = vec3(1.0, 0.62, 0.3) * 0.12 * exp(-r * 1.1);  // warm core, always present
	float s = (atan(p.x, p.z) + t * 0.05) / (TAU / 6.0);
	float fs = fract(s);
	int k = int(mod(floor(s), 6.0));
	float w[6] = float[6](w_glass, w_clay, w_noir, w_aria, w_chitin, w_paint);
	float wk = w[k] * smoothstep(0.0, 0.08, fs) * smoothstep(1.0, 0.92, fs);  // dark seams between sectors
	if (wk > 0.001) {
		c += wing_light(k, p, t) * wk;
	}
	return c;
}

void fragment() {
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float f = pow(1.0 - ndv, 4.0);
	vec3 d = normalize(opos);
	float fil = n_fbm(d.xy * 7.0 + d.z * 3.0);
	float line = smoothstep(0.44, 0.48, abs(fract(fil * 6.0) - 0.5));  // thin etched veins, clear glass between

	// refraction: bend the screen lookup by the view-space normal; keep only what lies behind us
	vec2 off = NORMAL.xy * refraction * (1.0 - f);
	vec2 uv = SCREEN_UV - off;
	float scene_z = texture(depth_tex, uv).r;
	vec4 sv = INV_PROJECTION_MATRIX * vec4(uv * 2.0 - 1.0, scene_z, 1.0);
	if (-sv.z / sv.w < -VERTEX.z) {
		uv = SCREEN_UV;
	}
	vec3 behind = textureLod(screen_tex, uv, 0.5).rgb;
	// chromatic split at the rims, as a thick lens would
	behind.r = mix(behind.r, textureLod(screen_tex, uv - off * 0.35, 0.5).r, f);
	behind.b = mix(behind.b, textureLod(screen_tex, uv + off * 0.35, 0.5).b, f);

	// march the hollow interior from this shell pixel to the far shell or the globe
	vec3 inner = vec3(0.0);
	if (volume > 0.0 && FRONT_FACING) {  // back faces would march the same air twice
		vec3 ro = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz - centre;
		vec3 rd = normalize((INV_VIEW_MATRIX * vec4(VERTEX, 0.0)).xyz);
		float b = dot(ro, rd);
		float tf = -b + sqrt(max(b * b - dot(ro, ro) + r_shell * r_shell, 0.0));
		float cw = b * b - dot(ro, ro) + r_world * r_world;
		if (cw > 0.0 && -b - sqrt(cw) > 0.0) {
			tf = min(tf, -b - sqrt(cw));
		}
		tf = max(tf, 0.0);
		const int N = 10;
		float dt = tf / float(N);
		float j = h3(vec3(FRAGCOORD.xy, TIME)) * dt;  // dither the steps; TAA/grain hide the noise
		for (int i = 0; i < N; i++) {
			float x = j + dt * float(i);
			// absorb with depth: a pixel shows the sector it enters, not the average of all six (white)
			inner += weather(ro + rd * x, TIME) * dt * 1.8 * exp(-x * 1.1);
		}
		// soft shoulder: six weathers together stay readable as weather, not a white bulb
		inner = inner * volume * 0.6 / (1.0 + dot(inner, vec3(0.3, 0.5, 0.2)) * 1.4);
	}

	vec3 hall = tint.rgb * (0.35 + 0.65 * smoothstep(-0.2, 0.8, reflect(-VIEW, NORMAL).y));
	ALBEDO = vec3(0.0);
	METALLIC = 0.0;
	ROUGHNESS = mix(0.02, 0.25, line);
	SPECULAR = 0.7;
	// the glass dims what lies behind it (smoked crystal) so the weathers inside carry the colour
	EMISSION = (behind * vec3(0.3, 0.29, 0.28) * (1.0 - f * 0.6) + inner * glow * 0.8 + hall * f * 0.2 + tint.rgb * line * 0.12 * glow);
	ALPHA = 1.0;
}
