shader_type spatial;
// The Rose Widow's floor. Each tile is a MultiMesh instance; it glows only where her projected
// colour falls. The same f(r, θ, t) as rose_widow.gd lit_at() — the collision and the picture agree.
render_mode unshaded, cull_back;

uniform float rose_t = 0.0;
uniform int phase = 1;
uniform vec3 centre = vec3(0.0);
uniform vec3 lantern_pos = vec3(1e6);  // hall-local
uniform float lantern_r = 4.0;
uniform float petals = 6.0;
uniform float half_width = 0.31;
uniform float edge = 0.08;
uniform float omega = 0.11;
uniform float r_in = 4.0;
uniform float r_out = 20.0;

varying vec3 tile_c;
varying flat float kind;
varying flat float rnd;
varying vec2 local_xz;
varying vec3 wp;

const vec3 PAL[6] = vec3[](vec3(0.70, 0.13, 0.26), vec3(0.91, 0.71, 0.29), vec3(0.17, 0.33, 0.79),
	vec3(0.10, 0.48, 0.37), vec3(0.54, 0.25, 0.82), vec3(0.91, 0.71, 0.29));

void vertex() {
	tile_c = MODEL_MATRIX[3].xyz;  // instance origin, world space (the hall is unrotated)
	kind = INSTANCE_CUSTOM.r;
	rnd = INSTANCE_CUSTOM.g;
	local_xz = VERTEX.xz;
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float lit(vec3 p, out float idx) {
	float r = length(p.xz);
	float seg = 6.2831853 / petals;
	float a = atan(p.z, p.x) - omega * rose_t;
	idx = mod(round(a / seg), petals);
	if (r < r_in) return 1.0;
	a = mod(a + seg * 0.5, seg) - seg * 0.5;
	float ang = smoothstep(half_width + edge, half_width - edge, abs(a));
	float rad = smoothstep(r_out + 0.6, r_out - 0.6, r);
	return ang * rad;
}

void fragment() {
	vec3 lp = tile_c - centre;
	float idx;
	float l = lit(lp, idx);
	vec3 col = PAL[int(idx)];
	if (length(lp.xz) < r_in) col = vec3(0.6, 0.35, 0.85);
	float on = 0.0;
	float glow = 0.0;
	if (phase == 1) {
		on = step(0.5, l);
		float ip;
		glow = lit(wp - centre, ip);  // per pixel: the light's edge drawn exactly across the tile
	} else if (phase == 2) {
		float d = length(lp.xz - lantern_pos.xz);
		float dp = length((wp - centre).xz - lantern_pos.xz);  // per pixel: a warm pool that falls off
		on = step(0.5, kind) * step(kind, 1.5) * step(d, lantern_r);
		glow = on * pow(1.0 - smoothstep(0.0, lantern_r, dp), 1.6) + step(0.5, kind) * step(kind, 1.5) * 0.04;
		col = vec3(1.0, 0.78, 0.45);
	} else {
		on = step(0.5, kind);
		glow = on * 0.55;
		col = mix(vec3(1.0, 0.78, 0.45), vec3(0.54, 0.25, 0.82), 0.3);
	}
	// leaded tile: a dark border, a quarry diamond inside
	vec2 q = abs(local_xz) / 0.735;
	float border = smoothstep(0.86, 0.9, max(q.x, q.y));
	float diamond = smoothstep(0.03, 0.0, abs(q.x + q.y - 0.95)) * 0.6;
	float lead = max(border, diamond);
	vec3 c = col * (0.18 + (phase == 1 ? 1.5 : 1.2) * glow) * (0.85 + 0.3 * rnd);
	ALBEDO = mix(c, vec3(0.0), lead) * max(on, 0.05);
	ALPHA = 1.0;
}
