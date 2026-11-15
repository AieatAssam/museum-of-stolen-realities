shader_type spatial;
// Translucent leaded glass for walls, floors and piers. World-projected so code-built boxes need no UVs.
// The glass is lit from *behind* (backlight): colour passes, lead stays black — the only true dark.
render_mode diffuse_burley;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D rough_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float scale = 0.33;
uniform vec4 tint : source_color = vec4(1.0);
uniform float backlight = 0.6;
uniform float lead_cut = 0.13;     // luminance below which a texel is lead
uniform float dark = 0.0;          // heist: windows going out
uniform float shimmer = 0.15;
uniform bool triplanar = false;    // modelled (curved) meshes: blend 3 projections, no seams

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}


void fragment() {
	// Nearly every surface is an axis-aligned box face: project on the dominant axis only
	// (2 fetches instead of 6 triplanar; this material covers most of the 1440p frame).
	vec3 p = wpos * scale;
	vec3 an = abs(wnrm);
	vec2 uv = an.x > an.y && an.x > an.z ? p.zy : (an.y > an.z ? p.xz : p.xy);
	vec3 c;
	vec3 nt;
	if (triplanar) {
		vec3 w = pow(an, vec3(6.0));
		w /= (w.x + w.y + w.z);
		c = (texture(albedo_tex, p.zy) * w.x + texture(albedo_tex, p.xz) * w.y + texture(albedo_tex, p.xy) * w.z).rgb;
		nt = (texture(normal_tex, p.zy) * w.x + texture(normal_tex, p.xz) * w.y + texture(normal_tex, p.xy) * w.z).rgb;
	} else {
		c = texture(albedo_tex, uv).rgb;
		nt = texture(normal_tex, uv).rgb;
	}
	float lum = dot(c, vec3(0.299, 0.587, 0.114));
	float glass = smoothstep(lead_cut, lead_cut + 0.08, lum);
	NORMAL_MAP = nt;
	NORMAL_MAP_DEPTH = 0.8;
	ALBEDO = c * tint.rgb * mix(0.25, 0.7, glass);
	ROUGHNESS = mix(0.85, 0.12, glass) * (0.8 + 0.4 * nt.b) + 0.05;  // rough from the normal map's z: one fewer triplanar fetch
	SPECULAR = 0.6;
	float sh = 1.0 + shimmer * sin(TIME * 0.7 + wpos.x * 0.3 + wpos.z * 0.23);
	EMISSION = c * tint.rgb * glass * backlight * sh * (1.0 - dark);
}
