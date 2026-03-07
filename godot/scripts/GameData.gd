# GameData.gd - Global autoload: passes data between scenes
extends Node

var selected_level_idx: int = 0
var all_levels: Array = []   # loaded once, shared between scenes

const PROGRESS_PATH := "user://progress.json"
const SETTINGS_PATH := "user://settings.json"

var played_ids: Dictionary = {}  # id -> true
var language: String = "en"     # "zh" | "en"


func _ready() -> void:
	var cjk := load("res://fonts/NotoSansTC_subset.ttf") as Font
	if cjk != null:
		# Embolden slightly to match original built-in font weight.
		var fv := FontVariation.new()
		fv.base_font = cjk
		fv.variation_embolden = 0.8
		ThemeDB.fallback_font = fv
		# Inject into Labels so web doesn't skip to built-in Control font first.
		get_tree().node_added.connect(func(node: Node) -> void:
			if node is Label:
				(node as Label).add_theme_font_override("font", fv)
			elif node is RichTextLabel:
				(node as RichTextLabel).add_theme_font_override("normal_font", fv))
	load_settings()
	load_progress()


func load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.READ)
	if f == null:
		return
	var text := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return
	var lang: String = str((parsed as Dictionary).get("language", "en"))
	if lang == "zh" or lang == "en":
		language = lang


func save_settings() -> void:
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"language": language}, "\t"))
	f.close()


func load_progress() -> void:
	played_ids.clear()
	if not FileAccess.file_exists(PROGRESS_PATH):
		return

	var f := FileAccess.open(PROGRESS_PATH, FileAccess.READ)
	if f == null:
		return
	var text := f.get_as_text()
	f.close()

	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return
	var arr: Array = (parsed as Dictionary).get("played", [])
	for raw_id in arr:
		var level_id := str(raw_id)
		if level_id != "":
			played_ids[level_id] = true


func save_progress() -> void:
	var arr: Array = played_ids.keys()
	arr.sort()
	var payload := {"played": arr}
	var f := FileAccess.open(PROGRESS_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(payload, "\t"))
	f.close()


func level_text(level: Dictionary, key: String) -> String:
	if language == "en":
		var k_en := key + "_en"
		if level.has(k_en):
			return str(level[k_en])
	return str(level.get(key, ""))


func level_text_array(level: Dictionary, key: String) -> Array:
	if language == "en":
		var k_en := key + "_en"
		if level.has(k_en):
			return level[k_en] as Array
	return level.get(key, []) as Array


func level_name(level: Dictionary) -> String:
	if language == "en":
		if level.has("name_en"):
			return str(level["name_en"])
	return _extract_cjk_name(str(level.get("name", "")))


func _extract_cjk_name(raw_name: String) -> String:
	for i in raw_name.length():
		var ch := raw_name.unicode_at(i)
		if (ch >= 0x4E00 and ch <= 0x9FFF) or (ch >= 0x3400 and ch <= 0x4DBF):
			return raw_name.substr(i).strip_edges()
	return raw_name


func mark_level_played(level_id: String) -> void:
	if level_id == "":
		return
	if played_ids.has(level_id):
		return
	played_ids[level_id] = true
	save_progress()


func is_level_played(level_id: String) -> bool:
	return played_ids.has(level_id)
