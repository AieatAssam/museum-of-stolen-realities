shader_type spatial;
// Structural glass of the Vitrine Kingdom: thick, smoked, opaque and polished. Large leaded panes
// (procedural, no textures) whose facets tilt a little each, so reflections break up softly pane by
// pane. Value is kept low on purpose: windows and the light they throw are the only bright things.
// proj: 0 = world projection on the dominant axis (code-built boxes), 1 = mesh UV in metres (models),
// 2 = no leading (modelled parts that carry their own lead).
render_mode diffuse_burley, specular_schlick_ggx;

uniform vec4 tint : source_color = vec4(0.05, 0.07, 0.16, 1.0);
uniform vec4 lead_color : source_color = vec4(0.04, 0.04, 0.045, 1.0);
uniform vec2 pane = vec2(0.9, 1.3);      // pane size in metres
uniform float lead_w = 0.035;            // half-width of the came, metres
uniform float facet = 0.22;              // how much each pane tilts
uniform float rough = 0.07;
uniform float glow = 0.03;               // faint light held inside the glass
uniform float vary = 0.35;               // pane-to-pane colour variation
uniform int proj = 0;
uniform float stagger = 0.5;             // running-bond offset of alternate rows

varying vec3 wpos;
varying vec3 wnrm;

float h1(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec2 uv;
	if (proj == 1) {
		uv = UV;
	} else {
		vec3 an = abs(wnrm);
		uv = an.x > an.y && an.x > an.z ? wpos.zy : (an.y > an.z ? wpos.xz : wpos.xy);
	}
	vec3 c = tint.rgb;
	float lead = 0.0;
	vec2 tilt = vec2(0.0);
	if (proj < 2) {
		vec2 q = uv / pane;
		q.x += stagger * step(0.5, fract(floor(q.y) * 0.5));
		vec2 cell = floor(q);
		vec2 f = fract(q);
		vec2 d = min(f, 1.0 - f) * pane;          // metres to the nearest came
		float e = min(d.x, d.y);
		float aa = fwidth(e) + 0.004;
		lead = 1.0 - smoothstep(lead_w - aa, lead_w + aa, e);
		float r = h1(cell);
		c *= 1.0 - vary + 2.0 * vary * r;
		tilt = (vec2(h1(cell + 7.3), h1(cell + 3.1)) - 0.5) * facet;
		// the came is a rounded bead: bend the normal across it
		vec2 g = (f - 0.5);
		vec2 across = abs(g.x) * pane.x > abs(g.y) * pane.y ? vec2(sign(g.x), 0.0) : vec2(0.0, sign(g.y));
		tilt += across * lead * 0.6 * (1.0 - e / lead_w);
	}
	NORMAL_MAP = normalize(vec3(tilt, 1.0)) * 0.5 + 0.5;
	ALBEDO = mix(c, lead_color.rgb, lead);
	ROUGHNESS = mix(rough, 0.25, lead);  // lead catches bright specular edges
	METALLIC = lead * 0.9;
	SPECULAR = 0.6;
	EMISSION = c * glow * (1.0 - lead);
}
