# TutorialController.gd - Data-driven instruction toasts keyed by tutorial ID
class_name TutorialController

var _scene: GameScene
var _tutorial_id: String = ""
var _objective: String = ""
var _active: bool = false

# Checklist state: array of { "label": String, "done": bool }
var _items: Array = []
var _last_bbcode: String = ""


func start_level(tutorial_id: String, objective: String, scene: GameScene) -> void:
	_scene = scene
	_tutorial_id = tutorial_id
	_objective = objective
	_items.clear()
	_last_bbcode = ""
	_active = tutorial_id != ""
	if _active:
		_enter()
	elif _objective != "":
		_scene.show_instruction(_objective, "")


func stop() -> void:
	_active = false


func on_state_changed() -> void:
	if not _active:
		return
	match _tutorial_id:
		"diverge_intro":
			_check_diverge_intro()
		"switch_progress":
			_check_switches()


func on_input(key: int) -> void:
	if not _active:
		return
	match _tutorial_id:
		"diverge_intro":
			_input_diverge_intro(key)


# ---------------------------------------------------------------------------
# Checklist rendering
# ---------------------------------------------------------------------------

func _refresh_toast() -> void:
	var bbcode := ""
	for item in _items:
		if item["done"]:
			bbcode += "[color=#666666]☑ " + item["label"] + "[/color]\n"
		else:
			bbcode += "☐ " + item["label"] + "\n"
	bbcode = bbcode.strip_edges(false, true)
	if bbcode == _last_bbcode:
		return
	_last_bbcode = bbcode
	var title := _objective if _objective != "" else "任務"
	_scene.show_instruction(title, bbcode)


func _complete_item(index: int) -> void:
	if index >= 0 and index < _items.size():
		_items[index]["done"] = true
	_refresh_toast()
	# Check if all done
	var all_done := true
	for item in _items:
		if not item["done"]:
			all_done = false
			break
	if all_done:
		_active = false


# ---------------------------------------------------------------------------
# Initial entry — build checklist for this tutorial
# ---------------------------------------------------------------------------

func _enter() -> void:
	match _tutorial_id:
		"diverge_intro":
			_enter_diverge_intro()
		"switch_progress":
			_enter_switches()


# ---------------------------------------------------------------------------
# diverge_intro — branch → activate switch → switch focus → walk to goal → merge
# ---------------------------------------------------------------------------

func _enter_diverge_intro() -> void:
	_items = [
		{"label": "按 [V] 分裂出平行空間", "done": false},
		{"label": "啟動開關", "done": false},
		{"label": "按 [Tab] 切換空間到另一角色", "done": false},
		{"label": "走到終點", "done": false},
		{"label": "按 [V] 合併", "done": false},
	]
	_refresh_toast()


func _check_diverge_intro() -> void:
	if _scene.controller == null:
		return
	var c := _scene.controller

	# Step 0: branched?
	if not _items[0]["done"] and c.has_branched:
		_complete_item(0)

	# Step 1: any switch activated?
	if not _items[1]["done"] and c.has_branched:
		var branch := c.get_active_branch()
		if branch != null:
			for pos in branch.terrain:
				if branch.terrain[pos] == Enums.TerrainType.SWITCH:
					if branch.switch_activated(pos):
						_complete_item(1)
						break

	# Step 3: player on goal?
	if not _items[3]["done"]:
		var branch := c.get_active_branch()
		if branch != null:
			var player := branch.get_player()
			if player != null:
				var t = branch.terrain.get(player.pos, Enums.TerrainType.FLOOR)
				if t == Enums.TerrainType.GOAL:
					_complete_item(3)

	# Step 4: merged (no longer branched, after having branched)?
	if not _items[4]["done"] and _items[0]["done"] and not c.has_branched:
		_complete_item(4)


func _input_diverge_intro(key: int) -> void:
	# Step 2: Tab pressed while branched
	if not _items[2]["done"] and key == KEY_TAB:
		_complete_item(2)


# ---------------------------------------------------------------------------
# switch_progress — show activated/total switch count as checklist
# ---------------------------------------------------------------------------

func _enter_switches() -> void:
	_items = []
	_update_switch_items()


func _check_switches() -> void:
	_update_switch_items()


func _update_switch_items() -> void:
	if _scene.controller == null:
		return
	var branch: BranchState = _scene.controller.get_active_branch()
	if branch == null:
		return
	var total := 0
	var activated := 0
	for pos in branch.terrain:
		var t: int = branch.terrain[pos]
		if t == Enums.TerrainType.SWITCH:
			total += 1
			if branch.switch_activated(pos):
				activated += 1
	if total == 0:
		_scene.hide_instruction()
		_active = false
		return
	_items.resize(total)
	for i in total:
		_items[i] = {"label": "開關 %d" % (i + 1), "done": i < activated}
	_refresh_toast()
	if activated >= total:
		_active = false
