// Triplanar helpers for hand-worked plasticine (whiteout normal blend, after Ben Golus).
// p: sample position in texture tiles, n: unit normal in the same space as p.

vec3 tri_weights(vec3 n) {
	vec3 w = pow(abs(n), vec3(4.0));
	return w / (w.x + w.y + w.z);
}

vec4 tri_sample(sampler2D tex, vec3 p, vec3 w) {
	return texture(tex, p.zy) * w.x + texture(tex, p.xz) * w.y + texture(tex, p.xy) * w.z;
}

// Returns the perturbed normal in the space of n. strength scales the tangent-space slopes.
vec3 tri_normal(sampler2D nmap, vec3 p, vec3 n, vec3 w, float strength) {
	vec3 tx = texture(nmap, p.zy).xyz * 2.0 - 1.0;
	vec3 ty = texture(nmap, p.xz).xyz * 2.0 - 1.0;
	vec3 tz = texture(nmap, p.xy).xyz * 2.0 - 1.0;
	tx.xy *= strength;
	ty.xy *= strength;
	tz.xy *= strength;
	tx = vec3(tx.xy + n.zy, abs(tx.z) * n.x);
	ty = vec3(ty.xy + n.xz, abs(ty.z) * n.y);
	tz = vec3(tz.xy + n.xy, abs(tz.z) * n.z);
	return normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);
}

float tri_hash(vec3 p) {
	return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
}

float tri_vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(tri_hash(i), tri_hash(i + vec3(1, 0, 0)), f.x),
			mix(tri_hash(i + vec3(0, 1, 0)), tri_hash(i + vec3(1, 1, 0)), f.x), f.y),
		mix(mix(tri_hash(i + vec3(0, 0, 1)), tri_hash(i + vec3(1, 0, 1)), f.x),
			mix(tri_hash(i + vec3(0, 1, 1)), tri_hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
