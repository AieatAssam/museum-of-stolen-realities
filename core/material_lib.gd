class_name MaterialLib
## Material-by-name remapping for imported .glb models. Blender material NAMES are the contract:
## a surface whose material is called "gilt" gets res://assets/materials/gilt.tres, or a wing's own
## res://wings/<id>/materials/gilt.tres when listed first in `dirs`.
##   var m := MaterialLib.instance("res://hub/models/frame.glb")       # instantiate + remap
##   MaterialLib.apply(node, ["res://wings/glass/materials", MaterialLib.CORE_DIR])

const CORE_DIR := "res://assets/materials"

static var _cache: Dictionary = {}


static func lookup(mat_name: String, dirs: Array = [CORE_DIR]) -> Material:
	for d: String in dirs:
		var key := d + "/" + mat_name
		if _cache.has(key):
			if _cache[key]:
				return _cache[key]
			continue
		var path := key + ".tres"
		var m: Material = load(path) if ResourceLoader.exists(path) else null
		_cache[key] = m
		if m:
			return m
	return null


static func apply(root: Node, dirs: Array = [CORE_DIR]) -> void:
	var meshes: Array[Node] = root.find_children("*", "MeshInstance3D", true, false)
	if root is MeshInstance3D:
		meshes.append(root)
	for mi: MeshInstance3D in meshes:
		var mesh := mi.mesh
		if mesh == null:
			continue
		for i in mesh.get_surface_count():
			var src := mesh.surface_get_material(i)
			if src == null:
				continue
			var m := lookup(src.resource_name, dirs)
			if m:
				mi.set_surface_override_material(i, m)


static func instance(path: String, dirs: Array = [CORE_DIR]) -> Node3D:
	var n := (load(path) as PackedScene).instantiate() as Node3D
	apply(n, dirs)
	return n
