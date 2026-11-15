shader_type canvas_item;
// Museum post stack: grade, chromatic aberration, vignette, film grain. Sits below all UI layers.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform vec4 tint : source_color = vec4(1.0);
uniform float saturation = 1.0;
uniform float contrast = 1.0;
uniform vec4 lift : source_color = vec4(0.0);
uniform float grain = 0.045;
uniform float aberration = 0.6;
uniform float vignette = 0.55;
uniform float grain_fps = 24.0;
uniform float fade = 0.0;   // 0 = clear, 1 = ink black

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void fragment() {
	vec2 uv = SCREEN_UV;
	vec2 c = uv - 0.5;
	float r2 = dot(c, c);
	vec2 off = c * r2 * aberration * 0.012;
	vec3 col;
	col.r = textureLod(screen_tex, uv - off, 0.0).r;
	col.g = textureLod(screen_tex, uv, 0.0).g;
	col.b = textureLod(screen_tex, uv + off, 0.0).b;
	col = max(col + lift.rgb * (1.0 - col), 0.0);
	float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
	col = mix(vec3(l), col, saturation);
	col = (col - 0.5) * contrast + 0.5;
	col *= tint.rgb;
	float v = smoothstep(0.85, 0.2, length(c * vec2(1.0, 0.82)) * vignette * 1.35);
	col *= mix(1.0, v, clamp(vignette, 0.0, 1.0));
	float t = grain_fps > 0.0 ? floor(TIME * grain_fps) : TIME;
	float n = hash(FRAGCOORD.xy + fract(t * 0.618) * 113.0) - 0.5;
	col += n * grain * (1.0 - l * 0.6);
	col = mix(col, vec3(0.012, 0.01, 0.008), fade);
	COLOR = vec4(max(col, 0.0), 1.0);
}
