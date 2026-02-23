# LevelSelect.gd - Level selection screen
extends Control

@onready var list_label:  RichTextLabel = $ListLabel
@onready var title_label: Label         = $TitleLabel

var levels: Array = []
var cursor: int   = 0


func _ready() -> void:
	# Load levels once and cache in GameData
	if GameData.all_levels.is_empty():
		var zone_files := [
			"res://Level/Level0.txt", "res://Level/Level1.txt",
			"res://Level/Level2.txt", "res://Level/Level3.txt",
			"res://Level/Level4.txt",
		]
		for path in zone_files:
			var parsed := MapParser.parse_level_resource(path)
			GameData.all_levels.append_array(parsed)

	levels = GameData.all_levels
	cursor = GameData.selected_level_idx
	_refresh()


func _input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed:
		return
	var ke := event as InputEventKey
	match ke.keycode:
		KEY_UP, KEY_W:
			cursor = max(cursor - 1, 0)
			_refresh()
		KEY_DOWN, KEY_S:
			cursor = min(cursor + 1, levels.size() - 1)
			_refresh()
		KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
			_start_level()
		KEY_ESCAPE:
			get_tree().quit()


func _start_level() -> void:
	GameData.selected_level_idx = cursor
	get_tree().change_scene_to_file("res://scenes/game_scene.tscn")


func _refresh() -> void:
	if levels.is_empty():
		list_label.text = "[color=red]找不到關卡資料[/color]"
		return

	var sb := PackedStringArray()
	for i in levels.size():
		var lv: Dictionary = levels[i]
		var name_str: String = lv.get("name", "Level %d" % i) as String
		if i == cursor:
			sb.append("[color=white][b]▶  %s[/b][/color]" % name_str)
		else:
			sb.append("[color=gray]   %s[/color]" % name_str)

	list_label.bbcode_enabled = true
	list_label.text = "\n".join(sb)
