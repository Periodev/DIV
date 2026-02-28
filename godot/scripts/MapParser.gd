# MapParser.gd - Parse ASCII level files into LevelSource data
# Mirrors Python's map_parser.py and level_constructor.py
class_name MapParser


## Parse floor_map and object_map strings → LevelSource.
static func parse_dual_layer(floor_map_str: String, object_map_str: String) -> LevelSource:
	var floor_lines  := _clean_lines(floor_map_str)
	var object_lines := _clean_lines(object_map_str)

	if floor_lines.size() != object_lines.size():
		push_error("MapParser: floor and object maps must have the same height")
		return null

	# Grid size = max of height and width
	var max_width := 0
	for line in floor_lines:
		max_width = max(max_width, line.length())
	var grid_size: int = max(floor_lines.size(), max_width)

	var terrain: Dictionary         = {}
	var entity_defs: Dictionary     = {}
	var next_uid := 0

	# Parse terrain
	for y in floor_lines.size():
		var line: String = floor_lines[y]
		for x in line.length():
			var ch := line[x]
			var pos := Vector2i(x, y)
			if Enums.CHAR_TO_TERRAIN.has(ch):
				terrain[pos] = Enums.CHAR_TO_TERRAIN[ch]
			# '.' → FLOOR (default, not stored)

	# Parse entities
	for y in object_lines.size():
		var line: String = object_lines[y]
		for x in line.length():
			var ch := line[x]
			var pos := Vector2i(x, y)
			if ch == "@":
				entity_defs[0] = [Enums.EntityType.PLAYER, pos]
			elif ch == "B":
				next_uid += 1
				entity_defs[next_uid] = [Enums.EntityType.BOX, pos]

	if not entity_defs.has(0):
		push_error("MapParser: player start position (@) not found")
		return null

	var has_goal := false
	for tt in terrain.values():
		if tt == Enums.TerrainType.GOAL:
			has_goal = true
			break
	if not has_goal:
		push_error("MapParser: goal position (G) not found")
		return null

	var source     := LevelSource.new()
	source.grid_size         = grid_size
	source.terrain           = terrain
	source.entity_definitions = entity_defs
	source.next_uid          = next_uid + 1
	return source


## Parse a level file (Level0.txt, etc.) → Array of level dicts.
## Each dict: { name, floor_map, object_map, hints, objective }
## Infers world_num from filename (LevelN.txt → world_num=N) so that levels
## without an explicit "hints = ..." line get progressive-unlock defaults,
## matching Python's level_constructor._hints_for_level logic.
static func parse_level_file(path: String) -> Array:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("MapParser: cannot open file: " + path)
		return []

	var text := file.get_as_text()
	file.close()

	# Infer world number from filename (e.g. "Level3.txt" → 3)
	var world_num := -1
	var noext := path.get_file().get_basename()  # "Level3"
	var digits := noext.substr(5)                # strip leading "Level"
	if digits.is_valid_int():
		world_num = digits.to_int()

	var levels := _parse_sections(text)

	# Back-fill hints for sections that had no explicit "hints = ..." line
	# (those have hints == null after parsing).
	for level in levels:
		if level.get("hints") == null:
			level["hints"] = _hints_for_level(world_num)

	return levels


## Parse levels from a res:// path (using Godot's resource system).
static func parse_level_resource(res_path: String) -> Array:
	return parse_level_file(res_path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

static func _clean_lines(block: String) -> Array:
	var lines: Array = []
	for line in block.strip_edges().split("\n"):
		lines.append(line.strip_edges(false, true))
	# Remove empty leading/trailing lines
	while lines.size() > 0 and (lines[0] as String).strip_edges() == "":
		lines.pop_front()
	while lines.size() > 0 and (lines[-1] as String).strip_edges() == "":
		lines.pop_back()
	return lines


## Progressive hint unlocks by world number.
## Mirrors Python's level_constructor._hints_for_level exactly.
## world_num = -1 (unknown) → base hints only (diverge=true, rest false).
static func _hints_for_level(world_num: int) -> Dictionary:
	var h := {"diverge": true, "pickup": false, "converge": false, "fetch": false}
	if world_num >= 1:
		h["converge"] = true
	if world_num >= 3:
		h["pickup"] = true
	if world_num >= 4:
		h["fetch"] = true
	return h


static func _parse_sections(text: String) -> Array:
	var levels: Array = []
	# Split on separator lines (4+ dashes)
	var sections := text.replace("\r", "").split("\n")
	var section_texts: Array = []
	var current_lines: Array = []

	for line in sections:
		if line.strip_edges().left(4) == "----":
			if current_lines.size() > 0:
				section_texts.append("\n".join(current_lines))
				current_lines = []
		else:
			current_lines.append(line)
	if current_lines.size() > 0:
		section_texts.append("\n".join(current_lines))

	for section_text in section_texts:
		var level := _parse_one_section(section_text)
		if level != null:
			levels.append(level)

	return levels


static func _parse_one_section(text: String) -> Dictionary:
	# Extract floor_map
	var floor_match := RegEx.new()
	floor_match.compile("floor_map\\s*=\\s*'''([\\s\\S]*?)'''")
	var floor_result := floor_match.search(text)
	if floor_result == null:
		return {}

	var object_match := RegEx.new()
	object_match.compile("object_map\\s*=\\s*'''([\\s\\S]*?)'''")
	var object_result := object_match.search(text)
	if object_result == null:
		return {}

	# Extract name (first # comment line)
	var name_val := ""
	for line in text.split("\n"):
		var stripped := line.strip_edges()
		if stripped.begins_with("#"):
			name_val = stripped.trim_prefix("#").strip_edges()
			break

	# Extract hints — null means no explicit line (caller will apply world defaults)
	var hints_match := RegEx.new()
	hints_match.compile("(?m)^\\s*hints\\s*=\\s*(.+?)\\s*$")
	var hints_result := hints_match.search(text)
	var parsed_hints = null
	if hints_result != null:
		parsed_hints = {"diverge": false, "pickup": false, "converge": false, "fetch": false}
		var tokens := hints_result.get_string(1).strip_edges().split(" ")
		if tokens.size() > 0 and tokens[0] != "none":
			for token in tokens:
				if (parsed_hints as Dictionary).has(token):
					parsed_hints[token] = true

	# Extract objective
	var obj_match := RegEx.new()
	obj_match.compile("objective\\s*=\\s*'''([\\s\\S]*?)'''")
	var obj_result := obj_match.search(text)
	var objective := ""
	if obj_result != null:
		objective = obj_result.get_string(1).strip_edges()

	return {
		"name":       name_val,
		"floor_map":  floor_result.get_string(1),
		"object_map": object_result.get_string(1),
		"hints":      parsed_hints,
		"objective":  objective,
	}
