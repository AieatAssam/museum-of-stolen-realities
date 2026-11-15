// The court's secreted surfaces: carapace, fused chitin floors, wax comb. World-space triplanar (so
// scaled boxes and stretched kit pieces never smear), a thin-film sheen on carapace (the hue walks
// with the view angle, like a beetle's elytra) and a backlit glow from the comb's cell floors.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rough_tex : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D height_tex : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec4 tint : source_color = vec4(1.0);
uniform float scale = 0.35;          // tiles per metre
uniform float normal_depth = 1.0;
uniform float rough_lo = 0.15;
uniform float rough_hi = 0.7;
uniform float iridescence = 0.0;     // thin-film sheen strength
uniform float film = 1.0;            // film thickness: shifts the hue band
uniform float metal = 0.0;
uniform vec4 glow_color : source_color = vec4(1.0, 0.6, 0.15, 1.0);
uniform float glow = 0.0;            // emission from the low (cell floor) parts of the height map
uniform float glow_cut = 0.45;
uniform float grime = 0.25;          // large-scale value variation, breaks tiling

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec4 tri(sampler2D t, vec3 p, vec3 w) {
	return texture(t, p.zy) * w.x + texture(t, p.xz) * w.y + texture(t, p.xy) * w.z;
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}

void fragment() {
	vec3 w = pow(abs(wnrm), vec3(4.0));
	w /= (w.x + w.y + w.z);
	vec3 p = wpos * scale;
	vec3 alb = tri(albedo_tex, p, w).rgb;
	float h = tri(height_tex, p, w).r;
	float r = tri(rough_tex, p, w).r;
	// triplanar normal (whiteout blend) in world space, then to view space
	vec3 nx = texture(normal_tex, p.zy).xyz * 2.0 - 1.0;
	vec3 ny = texture(normal_tex, p.xz).xyz * 2.0 - 1.0;
	vec3 nz = texture(normal_tex, p.xy).xyz * 2.0 - 1.0;
	nx.xy *= normal_depth; ny.xy *= normal_depth; nz.xy *= normal_depth;
	vec3 sn = sign(wnrm);
	vec3 n = normalize(vec3(nx.z * sn.x, nx.y, nx.x) * w.x + vec3(ny.x, ny.z * sn.y, ny.y) * w.y + vec3(nz.x, nz.y, nz.z * sn.z) * w.z + wnrm);
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	float g = mix(1.0 - grime, 1.0 + grime * 0.5, vnoise(wpos.xz * 0.11 + wpos.y * 0.07));
	vec3 base = alb * tint.rgb * g;
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	// thin film: a cosine palette indexed by optical path, green -> blue -> violet -> bronze
	float path = film * (1.6 - ndv) + h * 0.35 + vnoise(wpos.xy * 0.23 + wpos.zx * 0.17) * 0.7;
	vec3 tf = 0.5 + 0.5 * cos(6.2832 * (path + vec3(0.0, 0.33, 0.67)));
	tf = tf * tf;
	// the film tints both the diffuse (a sheen readable in any light) and the reflections
	float fres = 0.35 + 0.65 * pow(1.0 - ndv, 1.5);
	ALBEDO = mix(base, base * 0.4 + tf * 0.6, iridescence * fres);
	METALLIC = clamp(metal + iridescence * 0.45, 0.0, 1.0);
	ROUGHNESS = mix(rough_lo, rough_hi, r);
	SPECULAR = 0.5;
	if (glow > 0.0) {
		float cell = smoothstep(glow_cut, glow_cut - 0.3, h);
		EMISSION = glow_color.rgb * glow * cell * (0.6 + 0.4 * alb.r);
	}
}
