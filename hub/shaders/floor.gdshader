shader_type spatial;
render_mode cull_back;
// Atrium floor: polished nero marble with an ivory + brass compass inlay around Exhibit 0 and a
// ring of radial bands. World-space XZ mapping (one material, no UV seams).

uniform sampler2D marble_a : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D marble_a_n : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D marble_b : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float scale_a = 0.12;
uniform float scale_b = 0.25;
uniform float inner_r = 7.9;
uniform float outer_r = 16.0;

varying vec3 wpos;

void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

float line(float d, float w) { return smoothstep(w, w * 0.4, abs(d)); }

void fragment() {
	vec2 p = wpos.xz;
	float r = length(p);
	float a = atan(p.y, p.x);
	vec3 black = texture(marble_a, p * scale_a).rgb * 1.05;  // nero marquina, not a void: the fill must find it
	vec3 ivory = texture(marble_b, p * scale_b).rgb * vec3(0.36, 0.32, 0.27);
	vec3 brass = vec3(0.78, 0.6, 0.32);
	vec3 col = black;
	float metal = 0.0;
	float rough = 0.05 + 0.05 * (1.0 - texture(marble_a, p * scale_a * 3.0).r);  // honed a touch: carries the light pools

	// 12-point star between inner_r and outer_r
	float sector = 3.14159265 / 6.0;
	float aa = abs(mod(a + sector * 0.5, sector) - sector * 0.5) / sector; // 0 centre of point..0.5 between
	float star_r = mix(outer_r - 1.5, inner_r + 1.6, smoothstep(0.0, 0.5, aa));
	float in_band = step(inner_r, r) * step(r, outer_r);
	float star = in_band * step(r, star_r);
	col = mix(col, ivory, star * 0.9);
	// split each point into light/dark halves (bevelled look)
	float half_side = step(0.0, mod(a + sector * 0.5, sector) - sector * 0.5);
	col *= mix(1.0, mix(0.82, 1.0, half_side), star);
	// brass outlines
	float edge = in_band * line(r - star_r, 0.05);
	float rings = line(r - inner_r, 0.04) + line(r - outer_r, 0.05) + line(r - (outer_r + 0.6), 0.03) + line(r - 21.0, 0.05) + line(r - 21.5, 0.03);
	float spokes = step(outer_r + 0.6, r) * step(r, 21.0) * line(abs(mod(a + sector * 0.25, sector * 0.5) - sector * 0.25) * r, 0.03);
	// an engraved brass circle around the dais: twin rings with a band of ticks between them
	rings += line(r - (inner_r + 0.5), 0.025) + line(r - (inner_r + 1.1), 0.025) + line(r - 11.6, 0.02);
	float ticks = step(inner_r + 0.55, r) * step(r, inner_r + 1.05) * line(abs(mod(a, 3.14159265 / 48.0) - 3.14159265 / 96.0) * r, 0.018);
	float b = clamp(edge + rings + spokes + ticks, 0.0, 1.0);
	col = mix(col, brass, b);
	metal = b;
	rough = mix(rough, 0.25, b);
	// alternating ivory/black ring band between outer_r+0.6 and 21
	float band = step(outer_r + 0.6, r) * step(r, 21.0) * step(0.5, fract(a / (sector * 0.5)));
	col = mix(col, ivory * 0.8, band * 0.85);

	ALBEDO = col;
	METALLIC = metal;
	ROUGHNESS = rough;
	SPECULAR = 0.6;
	NORMAL_MAP = texture(marble_a_n, p * scale_a).rgb;
	NORMAL_MAP_DEPTH = 0.35;
}
