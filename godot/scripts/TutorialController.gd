# TutorialController.gd - Data-driven instruction toasts keyed by tutorial ID
# Check logic is defined per tutorial ID in code.
# Display labels come from tutorial_steps in the level file.
class_name TutorialController

# Check type constants — each tutorial ID maps to a fixed sequence of these.
enum Check { PLAYER_ON_GOAL, GOAL_ACTIVE, GOAL_ACTIVE_CROSS, HAS_BRANCHED, SWITCH_ACTIVATED, SWITCH_PROGRESS, SWITCH_ALL_CROSS, INPUT_TAB, INPUT_M, MERGED, MERGE_SUCCESS }

# Tutorial ID → array of check types (defines the check sequence).
# Level files provide matching labels via tutorial_steps.
const TUTORIAL_CHECKS := {
	"walk_to_goal": [Check.PLAYER_ON_GOAL],
	"switch_and_goal": [Check.SWITCH_PROGRESS, Check.GOAL_ACTIVE],
	"split_switches": [
		Check.SWITCH_ACTIVATED,
		Check.INPUT_TAB,
		Check.SWITCH_ALL_CROSS,
	],
	"split_switches_merge": [
		Check.SWITCH_ACTIVATED,
		Check.INPUT_TAB,
		Check.SWITCH_ALL_CROSS,
		Check.GOAL_ACTIVE_CROSS,
		Check.MERGE_SUCCESS,
	],
	"preview_intro": [
		Check.HAS_BRANCHED,
		Check.INPUT_M,
	],
	"diverge_intro": [
		Check.HAS_BRANCHED,
		Check.SWITCH_ACTIVATED,
		Check.INPUT_TAB,
		Check.GOAL_ACTIVE,
		Check.MERGE_SUCCESS,
	],
}

var _scene: GameScene
var _tutorial_id: String = ""
var _active: bool = false
var _was_branched: bool = false

# Checklist state: array of { "label": String, "check": Check, "done": bool }
var _items: Array = []
var _last_bbcode: String = ""


func start_level(tutorial_id: String, steps: Array, scene: GameScene) -> void:
	_scene = scene
	_tutorial_id = tutorial_id
	_items.clear()
	_last_bbcode = ""
	_was_branched = false
	_active = tutorial_id != "" and TUTORIAL_CHECKS.has(tutorial_id)
	if not _active:
		return

	var checks: Array = TUTORIAL_CHECKS[tutorial_id]
	for i in checks.size():
		var label: String = steps[i] if i < steps.size() else "???"
		var item := {"label": label, "check": checks[i], "done": false}
		if checks[i] == Check.SWITCH_PROGRESS:
			item["base_label"] = label
			var counts := _switch_counts()
			item["label"] = label + " (%d/%d)" % [counts[0], counts[1]]
		elif checks[i] == Check.SWITCH_ALL_CROSS:
			item["base_label"] = label
			var cross := _switch_counts_cross()
			item["label"] = label + " (%d/%d)" % [cross[0], cross[1]]
		_items.append(item)
	_refresh_toast()


func stop() -> void:
	_active = false


func on_state_changed() -> void:
	if not _active:
		return
	_evaluate_checks()


func on_input(key: int) -> void:
	if not _active:
		return
	# Input-based checks
	for i in _items.size():
		if _items[i]["done"]:
			continue
		if _items[i]["check"] == Check.INPUT_TAB and key == KEY_TAB \
				and _scene.controller != null and _scene.controller.has_branched:
			_complete_item(i)
		if _items[i]["check"] == Check.INPUT_M and key == KEY_M \
				and _scene.controller != null and _scene.controller.has_branched:
			_complete_item(i)


# ---------------------------------------------------------------------------
# Checklist rendering
# ---------------------------------------------------------------------------

func _refresh_toast() -> void:
	var bbcode := ""
	for item in _items:
		if item["done"]:
			bbcode += "[color=#73c073][✓][/color] [color=#666666]" + item["label"] + "[/color]\n"
		else:
			bbcode += "[  ] " + item["label"] + "\n"
	bbcode = bbcode.strip_edges(false, true)
	if bbcode == _last_bbcode:
		return
	_last_bbcode = bbcode
	_scene.show_instruction("任務", bbcode)


func _complete_item(index: int) -> void:
	if index >= 0 and index < _items.size():
		_items[index]["done"] = true
	_refresh_toast()
	var all_done := true
	for item in _items:
		if not item["done"]:
			all_done = false
			break
	if all_done:
		_active = false


# ---------------------------------------------------------------------------
# Unified check evaluation
# ---------------------------------------------------------------------------

func _evaluate_checks() -> void:
	if _scene.controller == null:
		return
	var c := _scene.controller
	var changed := false

	for i in _items.size():
		if _items[i]["done"]:
			continue
		var check: Check = _items[i]["check"] as Check
		var passed := false
		match check:
			Check.PLAYER_ON_GOAL:
				passed = _player_on_goal()
			Check.GOAL_ACTIVE:
				passed = _player_on_goal() and _all_switches_activated()
			Check.GOAL_ACTIVE_CROSS:
				passed = _player_on_goal() and _all_switches_cross()
			Check.HAS_BRANCHED:
				passed = c.has_branched
			Check.SWITCH_ACTIVATED:
				passed = _any_switch_activated()
			Check.SWITCH_PROGRESS:
				var counts := _switch_counts()
				var new_label: String = _items[i]["base_label"] + " (%d/%d)" % [counts[0], counts[1]]
				if new_label != _items[i]["label"]:
					_items[i]["label"] = new_label
					changed = true
				passed = counts[0] >= counts[1] and counts[1] > 0
			Check.SWITCH_ALL_CROSS:
				var cross := _switch_counts_cross()
				var new_label2: String = _items[i]["base_label"] + " (%d/%d)" % [cross[0], cross[1]]
				if new_label2 != _items[i]["label"]:
					_items[i]["label"] = new_label2
					changed = true
				passed = cross[0] >= cross[1] and cross[1] > 0
			Check.MERGED:
				passed = _has_done_check(Check.HAS_BRANCHED) and not c.has_branched
			Check.MERGE_SUCCESS:
				passed = _was_branched and not c.has_branched
			# INPUT_TAB is handled in on_input()
		if passed:
			_items[i]["done"] = true
			changed = true

	_was_branched = c.has_branched

	if changed:
		_refresh_toast()
		var all_done := true
		for item in _items:
			if not item["done"]:
				all_done = false
				break
		if all_done:
			_active = false


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

func _has_done_check(check_type: Check) -> bool:
	for item in _items:
		if item["check"] == check_type and item["done"]:
			return true
	return false


func _get_all_branches() -> Array:
	var result: Array = []
	if _scene.controller == null:
		return result
	var c := _scene.controller
	if c.main_branch != null:
		result.append(c.main_branch)
	if c.sub_branch != null:
		result.append(c.sub_branch)
	return result


func _player_on_goal() -> bool:
	for branch in _get_all_branches():
		var player: Entity = branch.get_player()
		if player != null:
			if branch.terrain.get(player.pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.GOAL:
				return true
	return false


func _any_switch_activated() -> bool:
	for branch in _get_all_branches():
		for pos in branch.terrain:
			if branch.terrain[pos] == Enums.TerrainType.SWITCH:
				if branch.switch_activated(pos):
					return true
	return false


func _all_switches_activated() -> bool:
	for branch in _get_all_branches():
		if branch.all_switches_activated():
			return true
	return false


func _all_switches_cross() -> bool:
	var cross := _switch_counts_cross()
	return cross[1] > 0 and cross[0] >= cross[1]


func _switch_counts() -> Array:
	# Returns [activated, total] for the best single branch
	var best_activated := 0
	var best_total := 0
	for branch in _get_all_branches():
		var total := 0
		var activated := 0
		for pos in branch.terrain:
			if branch.terrain[pos] == Enums.TerrainType.SWITCH:
				total += 1
				if branch.switch_activated(pos):
					activated += 1
		if total > best_total or activated > best_activated:
			best_total = total
			best_activated = activated
	return [best_activated, best_total]


func _switch_counts_cross() -> Array:
	# Returns [activated, total] across all branches (union by position)
	var switch_positions: Dictionary = {}  # pos → bool (activated in any branch)
	for branch in _get_all_branches():
		for pos in branch.terrain:
			if branch.terrain[pos] == Enums.TerrainType.SWITCH:
				if not switch_positions.has(pos):
					switch_positions[pos] = false
				if branch.switch_activated(pos):
					switch_positions[pos] = true
	var total := switch_positions.size()
	var activated := 0
	for v in switch_positions.values():
		if v:
			activated += 1
	return [activated, total]
