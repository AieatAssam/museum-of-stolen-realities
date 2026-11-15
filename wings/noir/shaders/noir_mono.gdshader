shader_type canvas_item;
// The city in black and white. Everything goes to a silver-gelatin grey except light that is both
// strongly saturated and bright (neon, the fragment frame), which keeps its hue. `amount` 0 gives the
// colour back (the fragment's eleven seconds). Sits just under the museum's Post layer, so the
// shared grade, vignette and grain still land on top.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float amount : hint_range(0.0, 1.0) = 1.0;
uniform float keep_sat = 0.55;   // chroma above this (and bright enough) keeps its colour
uniform vec3 paper = vec3(1.0, 0.985, 0.955);  // a faint warm paper tone in the highlights
uniform float toe = 0.012;       // holds detail in the blacks

void fragment() {
	vec3 c = textureLod(screen_tex, SCREEN_UV, 0.0).rgb;
	float mx = max(c.r, max(c.g, c.b));
	float mn = min(c.r, min(c.g, c.b));
	float sat = (mx - mn) / max(mx, 1e-4);
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	float keep = smoothstep(keep_sat, keep_sat + 0.25, sat) * smoothstep(0.05, 0.25, mx);
	vec3 mono = vec3(l) * mix(vec3(1.0), paper, smoothstep(0.2, 0.9, l));
	mono = mono + toe * (1.0 - mono) * (1.0 - smoothstep(0.0, 0.1, l));
	vec3 neon = mix(mono, c, 0.85);
	COLOR = vec4(mix(c, mix(mono, neon, keep), amount), 1.0);
}
