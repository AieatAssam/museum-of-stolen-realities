class_name Credits
## Credits merged from res://CREDITS.md and every res://wings/<id>/CREDITS.md (same table format:
## | Path | Title | Author | Source | Licence |). A wing adds its third-party files to its own
## CREDITS.md (tools/fetch_cc.sh <url> wings/<id>/... writes there) and never edits the root file.
##   Credits.rows()   every row, root first, then wings in folder order
##   Credits.cards()  the end-of-game credits as Cinematics steps (the hub's _credits() returns this)
## Export note: add "*.md" to the export preset's non-resource include filter.


static func files() -> PackedStringArray:
	var out: PackedStringArray = ["res://CREDITS.md"]
	for d in DirAccess.get_directories_at("res://wings"):
		if FileAccess.file_exists("res://wings/%s/CREDITS.md" % d):
			out.append("res://wings/%s/CREDITS.md" % d)
	return out


static func rows() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for path in files():
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			continue
		for line in f.get_as_text().split("\n"):
			var c := line.split("|")
			if c.size() < 7 or c[1].strip_edges() in ["Path", ""] or c[1].strip_edges().begins_with("-"):
				continue
			out.append({"path": c[1].strip_edges(), "title": c[2].strip_edges(), "author": c[3].strip_edges(),
				"source": c[4].strip_edges(), "licence": c[5].strip_edges(), "file": path})
	return out


const PER_CARD := 8


## Every row, as cards: the typefaces, then every Creative Commons Attribution item (with author and
## licence, as CC-BY requires), then every other third-party item, PER_CARD lines a card.
static func cards() -> Array:
	var type: PackedStringArray = []
	var cc: PackedStringArray = []
	var other: PackedStringArray = []
	for r in rows():
		var lic := String(r["licence"])
		var line := line_for(r)
		if lic.begins_with("OFL"):
			if not String(r["title"]) in type:
				type.append(String(r["title"]))
		elif lic.begins_with("CC-BY"):
			if not line in cc:
				cc.append(line)
		elif not line in other:
			other.append(line)
	var steps: Array = [
		{"card": "Museum of Stolen Realities", "sub": "Credits", "t": 4.0},
		{"card": "Made with Godot Engine (MIT).\nType set in %s (SIL Open Font License)." % " and ".join(type), "sub": "With thanks", "t": 5.0, "style": "body"},
	]
	for pair: Array in [[cc, "Under Creative Commons Attribution"], [other, "Also used, in the public domain or free to use"]]:
		var lines: PackedStringArray = pair[0]
		for i in range(0, lines.size(), PER_CARD):
			steps.append({"card": "\n".join(lines.slice(i, i + PER_CARD)), "sub": pair[1], "t": 5.0, "style": "body"})
	return steps


## How one row reads on a card: title, author, licence.
static func line_for(r: Dictionary) -> String:
	return "%s, %s (%s)" % [r["title"], r["author"], r["licence"]]
