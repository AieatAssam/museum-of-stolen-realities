class_name Quality
## Quality presets. Wing calls `Quality.apply(env)` on load and whenever settings change, so a wing
## authors its Environment at "ultra" intent and this only switches costly features off.

const PRESETS := ["low", "medium", "high", "ultra"]


static func level() -> int:
	return maxi(PRESETS.find(String(Save.settings.get("quality", "high"))), 0)


static func apply(env: Environment) -> void:
	if env == null:
		return
	var q := level()
	# Remember what the author enabled, so lowering then raising quality restores it.
	if not env.has_meta("authored"):
		env.set_meta("authored", {
			"ssr": env.ssr_enabled, "ssao": env.ssao_enabled, "ssil": env.ssil_enabled,
			"sdfgi": env.sdfgi_enabled, "fog": env.volumetric_fog_enabled, "glow": env.glow_enabled,
		})
	var a: Dictionary = env.get_meta("authored")
	env.ssr_enabled = a["ssr"] and q >= 2
	env.ssao_enabled = a["ssao"] and q >= 1
	env.ssil_enabled = a["ssil"] and q >= 3
	env.sdfgi_enabled = a["sdfgi"] and q >= 3
	env.volumetric_fog_enabled = a["fog"] and q >= 1
	env.glow_enabled = a["glow"]
	env.ssr_max_steps = 48 if q >= 3 else 32
	RenderingServer.directional_shadow_atlas_set_size(4096 if q >= 2 else 2048, true)
	var vp := (Engine.get_main_loop() as SceneTree).root
	vp.positional_shadow_atlas_size = 4096 if q >= 2 else 2048
	vp.msaa_3d = Viewport.MSAA_2X if q >= 2 else Viewport.MSAA_DISABLED
	RenderingServer.environment_set_volumetric_fog_volume_size(96 if q >= 2 else 64, 96 if q >= 2 else 48)
