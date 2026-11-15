shader_type canvas_item;
// The city in black and white. Everything goes to a silver-gelatin grey except light that is both
// pure red (the neon and its spill), which keeps its hue. `amount` 0 gives the
// colour back (the fragment's eleven seconds). Sits just under the museum's Post layer, so the
// shared grade, vignette and grain still land on top.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float amount : hint_range(0.0, 1.0) = 1.0;
uniform float keep_ratio = 0.3;  // pure red only: green and blue under this fraction of red keep their hue
uniform vec3 paper = vec3(1.0, 0.985, 0.955);  // a faint warm paper tone in the highlights
uniform float toe = 0.012;       // holds detail in the blacks

void fragment() {
	vec3 c = textureLod(screen_tex, SCREEN_UV, 0.0).rgb;
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	// neon red (and its spill on wet ground) is the only colour: wood, brick and skin go grey
	float ratio = max(c.g, c.b) / max(c.r, 1e-4);
	float keep = smoothstep(keep_ratio, keep_ratio * 0.5, ratio) * smoothstep(0.02, 0.12, c.r);
	vec3 mono = vec3(l) * mix(vec3(1.0), paper, smoothstep(0.2, 0.9, l));
	mono = mono + toe * (1.0 - mono) * (1.0 - smoothstep(0.0, 0.1, l));
	vec3 neon = mix(mono, c, 0.85);
	COLOR = vec4(mix(c, mix(mono, neon, keep), amount), 1.0);
}
