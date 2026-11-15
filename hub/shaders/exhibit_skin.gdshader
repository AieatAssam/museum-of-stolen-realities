shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;
// Exhibit 0's vessel: thick clear crystal. Each pixel of the shell refracts what lies behind it (the
// opaque scene in the screen texture, depth-checked so nothing in front smears in), then marches the
// hollow interior (an analytic sphere around `centre`, stopping at the world globe) and adds the
// light that lives inside: a warm volumetric glow, plus one weather per returned fragment, each
// gated by its own uniform (0 = absent, 1 = fully home):
//   glass  slow shafts of coloured light, as through leaded panes
//   clay   a thumb-warm boil, stepped at 12 frames a second
//   noir   black-and-white rain, falling straight
//   aria   standing waves: concentric shells that breathe in and out of phase
//   chitin amber: honey light in hexagonal cells, slowly pulsing
//   paint  swirling wet brush strokes in saturated colour
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

// light emitted per metre at p (p relative to the centre, metres)
vec3 weather(vec3 p, float t) {
	float r = length(p);
	// warm core glow, always present: the world inside is lit
	vec3 c = vec3(1.0, 0.62, 0.3) * 0.22 * exp(-r * 1.1) * (0.8 + 0.4 * v3(p * 1.4 + t * 0.15));
	if (w_glass > 0.001) {  // shafts slanting down from one side, each a pane colour
		vec3 dir = normalize(vec3(0.45, -1.0, 0.2));
		vec3 q = p - dir * dot(p, dir);
		vec2 cell = floor(vec2(q.x + q.y * 0.3, q.z) * 2.2 + vec2(t * 0.05, 0.0));
		float pane = h3(vec3(cell, 3.0));
		vec2 f = fract(vec2(q.x + q.y * 0.3, q.z) * 2.2 + vec2(t * 0.05, 0.0));
		float beam = step(0.62, pane) * smoothstep(0.5, 0.36, max(abs(f.x - 0.5), abs(f.y - 0.5)));
		c += hue(pane * 3.7) * beam * 1.6 * w_glass;
	}
	if (w_clay > 0.001) {  // boiling plasticine light, stepped at 12 fps
		float tq = floor(t * 12.0) / 12.0;
		float b = v3(p * 1.6 + vec3(0.0, tq * 0.6, 0.0) + floor(t * 12.0) * 0.13);
		c += mix(vec3(0.85, 0.42, 0.2), vec3(0.45, 0.62, 0.3), v3(p * 0.7)) * smoothstep(0.55, 0.75, b) * 0.9 * w_clay;
	}
	if (w_noir > 0.001) {  // straight rain, silver on black
		vec2 col = floor(p.xz * 9.0);
		float sp = 2.6 + 1.6 * h3(vec3(col, 1.0));
		float y = fract(p.y * 0.8 + t * sp * 0.4 + h3(vec3(col, 2.0)));
		vec2 fx = fract(p.xz * 9.0) - 0.5;
		float streak = smoothstep(0.08, 0.0, length(fx)) * smoothstep(0.0, 0.05, y) * smoothstep(0.35, 0.05, y);
		c += vec3(0.85, 0.88, 0.92) * streak * 2.2 * step(0.55, h3(vec3(col, 4.0))) * w_noir;
	}
	if (w_aria > 0.001) {  // standing waves: shells breathing in place
		float s = sin(r * 9.0) * sin(t * 1.3 + p.y * 0.8);
		c += vec3(0.25, 0.75, 0.8) * pow(abs(s), 8.0) * 0.9 * w_aria;
	}
	if (w_chitin > 0.001) {  // amber in hex cells, pulsing like a hive
		vec2 h = vec2(p.x + p.z * 0.5, p.z * 0.866) * 3.0;
		vec2 hf = fract(h) - 0.5;
		float cell = h3(vec3(floor(h), 7.0));
		float wall = smoothstep(0.42, 0.5, max(abs(hf.x), abs(hf.y)));
		float pulse = 0.5 + 0.5 * sin(t * 0.9 + cell * 6.28);
		c += vec3(1.0, 0.58, 0.12) * (0.25 + 0.55 * pulse * step(0.5, cell) + wall * 0.4) * 0.5 * smoothstep(1.0, -0.6, p.y) * w_chitin;
	}
	if (w_paint > 0.001) {  // swirled strokes: noise combed along a slow vortex
		float a = atan(p.z, p.x) + t * 0.12 + r * 0.9;
		vec3 q = vec3(cos(a) * r, p.y * 1.5, sin(a) * r);
		float stroke = v3(vec3(a * 3.0, p.y * 6.0, r * 2.0));
		float band = smoothstep(0.62, 0.72, stroke) * smoothstep(0.95, 0.75, stroke);
		c += hue(fract(v3(q * 0.8) * 2.0 + 0.1)) * band * 1.4 * w_paint;
	}
	return c;
}

void fragment() {
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float f = pow(1.0 - ndv, 4.0);
	vec3 d = normalize(opos);
	float fil = n_fbm(d.xy * 7.0 + d.z * 3.0);
	float line = smoothstep(0.02, 0.0, abs(fract(fil * 6.0) - 0.5) - 0.46);

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
			inner += weather(ro + rd * (j + dt * float(i)), TIME) * dt;
		}
		// soft shoulder: six weathers together stay readable as weather, not a white bulb
		inner = inner * volume * 0.55 / (1.0 + dot(inner, vec3(0.3, 0.5, 0.2)) * 1.2);
	}

	vec3 hall = tint.rgb * (0.35 + 0.65 * smoothstep(-0.2, 0.8, reflect(-VIEW, NORMAL).y));
	ALBEDO = vec3(0.0);
	METALLIC = 0.0;
	ROUGHNESS = mix(0.02, 0.25, line);
	SPECULAR = 0.7;
	EMISSION = (behind * vec3(0.97, 0.95, 0.9) * (1.0 - f * 0.6) + inner * glow + hall * f * 0.25 + tint.rgb * line * 0.18 * glow);
	ALPHA = 1.0;
}
