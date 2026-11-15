shader_type spatial;
render_mode unshaded, fog_disabled;
// The inside face of the museum wall: from within the picture it is painted out, a backdrop that
// carries the sky (the same studies, the same lookup as paint_sky) so the edge is read by the gilt
// frame alone and never as a beige slab. Collision is the wall's; this is only its paint.

uniform sampler2D fair : source_color, filter_linear, repeat_enable;
uniform sampler2D storm : source_color, filter_linear, repeat_enable;
uniform float storm_amount = 0.0;
uniform vec3 tint : source_color = vec3(1.0);
uniform vec3 haze : source_color = vec3(1.0, 0.86, 0.68);
uniform float haze_width = 0.18;
uniform float drift = 0.0015;
uniform vec3 fog_colour : source_color = vec3(1.0, 0.87, 0.72);
uniform float fog_amount = 0.25;   // the scene fog's share on the sky (Environment.fog_sky_affect)

uniform vec3 gallery_side : source_color = vec3(0.16, 0.26, 0.25);   // its face toward the gallery

varying vec3 v_p;
varying vec3 v_n;

void vertex() {
	v_p = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_n = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;
}

void fragment() {
	vec3 d = normalize(v_p - CAMERA_POSITION_WORLD);
	float el = asin(clamp(d.y, -1.0, 1.0));
	float u = fract((atan(d.x, d.z) / TAU + 0.5) * 2.0 + TIME * drift);
	float v = 1.0 - clamp(pow(max(el, 0.0) / 1.5708, 0.8), 0.0, 1.0);
	float seam = smoothstep(0.0, 0.14, min(u, 1.0 - u));
	vec2 uv = vec2(u, mix(0.02, 0.98, v));
	vec2 uv2 = vec2(fract(u + 0.5), uv.y);
	vec3 cf = mix(texture(fair, uv2).rgb, texture(fair, uv).rgb, seam);
	vec3 cs = mix(texture(storm, uv2).rgb, texture(storm, uv).rgb, seam);
	vec3 c = mix(cf, cs, storm_amount) * tint;
	c = mix(c, haze, smoothstep(haze_width, 0.0, el) * 0.85);
	ALBEDO = normalize(v_n).x < -0.5 ? gallery_side : mix(c, fog_colour, fog_amount);
}
