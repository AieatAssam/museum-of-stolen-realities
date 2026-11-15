# Credits: The Drowned Aria (wings/aria)

Recorded sounds below are downloaded with `tools/fetch_cc.sh` into `audio/src/` (not imported, `.gdignore`)
and cut into the game files by `wings/aria/tools/make_audio.py`. Each derived file names its source rows.

| Path | Title | Author | Source | Licence |
|---|---|---|---|---|
| wings/aria/models/*.glb | Opera kit (tiers, proscenium, organ cases, chandelier, seats, stair, instruments, La Sirena, props) | modelled in code | wings/aria/models/src/*.py via tools/blender_build.sh | project-original |
| wings/aria/textures/* | Damask, velvet, fresco, verdigris, marble and score-paper PBR sets; dome fresco and seascape drop (graded from textures_raw/) | generated | tools/gen_image.sh + tools/make_pbr.py | project-original |
| wings/aria/shaders/* | Water and cymatics shaders | written for this project | wings/aria/shaders | project-original |
| wings/aria/audio/src/organ_loud_c4.ogg | Organ loud C4 | sgossner | https://freesound.org/s/373703/ | CC0-1.0 |
| wings/aria/audio/src/organ_quiet_c4.ogg | Organ quiet C4 | sgossner | https://freesound.org/s/373735/ | CC0-1.0 |
| wings/aria/audio/src/fhorn_18.ogg | FHorn 18 | HenKonen | https://freesound.org/s/682231/ | CC0-1.0 |
| wings/aria/audio/src/wine_glass_fs6.ogg | Wine Glass Sustained Note F#6 | spectral9 | https://freesound.org/s/256251/ | CC0-1.0 |
| wings/aria/audio/src/cello_section_fs4.ogg | Cello Section vibrato sustain F#4 | sgossner | https://freesound.org/s/372840/ | CC0-1.0 |
| wings/aria/audio/src/tuning_fork_a4.ogg | tuning_fork_A4_440Hz | lacimarsik | https://freesound.org/s/361922/ | CC0-1.0 |
| wings/aria/audio/src/female_voice_sustained.ogg | Female Voice Sustained Slight Variation | REVERBERA | https://freesound.org/s/851043/ | CC0-1.0 |
| wings/aria/audio/src/choir_high.ogg | How Long Choir High 1 | f-r-a-g-i-l-e | https://freesound.org/s/679482/ | CC0-1.0 |
| wings/aria/audio/src/theatre_room_tone.ogg | room-tone theater with silent woman | klankbeeld | https://freesound.org/s/210882/ | CC-BY-4.0 |
| wings/aria/audio/src/underwater.ogg | Underwater Ambience | Fission9 | https://freesound.org/s/504641/ | CC0-1.0 |
| wings/aria/audio/src/creaking.ogg | Slow Creaking Stereo | harveyism | https://freesound.org/s/130364/ | CC0-1.0 |
| wings/aria/audio/src/crystal_lamp.ogg | Crystal Lamp with Swing Front | Andreas.Mustola | https://freesound.org/s/84526/ | CC0-1.0 |
| wings/aria/audio/src/dripping_echo.ogg | Water Dripping (Large Echo) | editor_adp | https://freesound.org/s/162116/ | CC0-1.0 |
| wings/aria/audio/src/bubbles.ogg | Bubbles | hotpin7 | https://freesound.org/s/840042/ | CC0-1.0 |
| wings/aria/audio/note_organ_c.ogg, note_organ_e.ogg, note_organ_g.ogg | Organ notes C3/E3/G3 (re-pitched) | sgossner | https://freesound.org/s/373703/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/note_horn.ogg | Horn note | HenKonen | https://freesound.org/s/682231/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/note_cello.ogg, aria_strings.ogg | Cello note and string stem (re-pitched) | sgossner | https://freesound.org/s/372840/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/note_glass.ogg | Glass note C6 (re-pitched) | spectral9 | https://freesound.org/s/256251/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/note_sirena.ogg | La Sirena's sung note C5 (re-pitched) | REVERBERA | https://freesound.org/s/851043/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/aria_motif.ogg | Leitmotif stem: voice G-E-C answered by glass | REVERBERA; spectral9 | https://freesound.org/s/851043/ + https://freesound.org/s/256251/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/aria_bed.ogg | Organ fifth bed stem | sgossner | https://freesound.org/s/373735/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/aria_choir.ogg | Choir stem (re-pitched) | f-r-a-g-i-l-e | https://freesound.org/s/679482/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/fork_strike.ogg | Tuning fork strike | lacimarsik | https://freesound.org/s/361922/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/gravity_release.ogg | Gravity release (bubbles over underwater swell) | hotpin7; Fission9 | https://freesound.org/s/840042/ + https://freesound.org/s/504641/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/amb_hall.ogg | Hall room tone loop | klankbeeld | https://freesound.org/s/210882/ via wings/aria/tools/make_audio.py | CC-BY-4.0 |
| wings/aria/audio/amb_crystal.ogg | Dome: hall tone with swung crystal lamp | klankbeeld; Andreas.Mustola | https://freesound.org/s/210882/ (CC-BY-4.0) + https://freesound.org/s/84526/ (CC0) via wings/aria/tools/make_audio.py | CC-BY-4.0 |
| wings/aria/audio/amb_water.ogg | Underwater loop | Fission9 | https://freesound.org/s/504641/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/amb_drips.ogg | Pit drips loop | editor_adp | https://freesound.org/s/162116/ via wings/aria/tools/make_audio.py | CC0-1.0 |
| wings/aria/audio/amb_rigging.ogg | Fly-loft rigging creaks loop | harveyism | https://freesound.org/s/130364/ via wings/aria/tools/make_audio.py | CC0-1.0 |
