class_name ShadowField
extends RefCounted
## The noir light test. A point is LIT when some light in group "shadow_lights" reaches it with an
## unbroken ray. Occluders are world geometry (layer 1) and shadow casters (layer 7, 1 << 6).
## Casters are not in the player's collision mask, so the player walks through them while light
## rays are still stopped by them: that is how moving shade is made.

const OCCLUDER_MASK := 1 | (1 << 6)


static func lit(ctx: Node3D, point: Vector3, exclude: Array[RID] = []) -> bool:
	for node in ctx.get_tree().get_nodes_in_group(&"shadow_lights"):
		if reaches(ctx, node as Light3D, point, exclude):
			return true
	return false


static func lit_by(ctx: Node3D, light: Light3D, point: Vector3, exclude: Array[RID] = []) -> bool:
	return reaches(ctx, light, point, exclude)


static func reaches(ctx: Node3D, light: Light3D, point: Vector3, exclude: Array[RID]) -> bool:
	if light == null or not light.is_visible_in_tree() or light.light_energy <= 0.0:
		return false
	var from := light.global_position
	var d := point - from
	if light is OmniLight3D:
		if d.length() > (light as OmniLight3D).omni_range:
			return false
	elif light is SpotLight3D:
		var s := light as SpotLight3D
		if d.length() > s.spot_range or (-light.global_basis.z).angle_to(d) > deg_to_rad(s.spot_angle):
			return false
	var q := PhysicsRayQueryParameters3D.create(from, point, OCCLUDER_MASK, exclude)
	return ctx.get_world_3d().direct_space_state.intersect_ray(q).is_empty()
