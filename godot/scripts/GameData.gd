# GameData.gd - Global autoload: passes data between scenes
extends Node

var selected_level_idx: int = 0
var all_levels: Array = []   # loaded once, shared between scenes

const PROGRESS_PATH := "user://progress.json"

var played_ids: Dictionary = {}  # id -> true


func _ready() -> void:
	load_progress()


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


func mark_level_played(level_id: String) -> void:
	if level_id == "":
		return
	if played_ids.has(level_id):
		return
	played_ids[level_id] = true
	save_progress()


func is_level_played(level_id: String) -> bool:
	return played_ids.has(level_id)
