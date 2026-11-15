shader_type canvas_item;
// Title painting: left-side ink veil for type, slow light breathing on the sphere, faint shafts.
#include "res://core/shaders/noise.gdshaderinc"

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	float t = TIME;
	// breathing glow around the floating sphere (upper centre of the painting)
	float d = length((UV - vec2(0.5, 0.2)) * vec2(1.7, 1.0));
	float breathe = 0.5 + 0.5 * sin(t * 0.6);
	c.rgb += vec3(1.0, 0.78, 0.45) * smoothstep(0.32, 0.0, d) * 0.12 * breathe;
	// slow drifting light shafts
	float shaft = n_fbm(vec2(UV.x * 6.0 + UV.y * 1.5 - t * 0.03, t * 0.05));
	c.rgb += vec3(1.0, 0.85, 0.6) * smoothstep(0.55, 0.85, shaft) * smoothstep(0.9, 0.1, UV.y) * 0.05;
	// ink veil on the left for the typography
	float veil = smoothstep(0.62, 0.0, UV.x);
	c.rgb = mix(c.rgb, vec3(0.03, 0.025, 0.018), veil * 0.82);
	// gentle top/bottom vignette
	c.rgb *= mix(0.55, 1.0, smoothstep(0.0, 0.25, UV.y) * smoothstep(1.0, 0.7, UV.y));
	COLOR = c;
}
