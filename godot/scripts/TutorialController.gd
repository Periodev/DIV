# TutorialController.gd - Data-driven instruction toasts keyed by tutorial ID
# Check logic is defined per tutorial ID in code.
# Display labels come from tutorial_steps in the level file.
class_name TutorialController

# Check type constants — each tutorial ID maps to a fixed sequence of these.
enum Check { PLAYER_ON_GOAL, GOAL_ACTIVE, GOAL_ACTIVE_CROSS, HAS_BRANCHED, SWITCH_ACTIVATED, SWITCH_PROGRESS, SWITCH_ALL_CROSS, INPUT_TAB, INPUT_M, MERGED, MERGE_SUCCESS, SPACE_RESTORE, GAIN_DIV_POINT, BRANCH_TWICE, INSTANT, INPUT_F1_DISMISS, INPUT_Z, SWITCH_ACTIVATED_BRANCHED, RESTORE_COUNT }

# Tutorial ID → array of check types (defines the check sequence).
# Level files provide matching labels via tutorial_steps.
const TUTORIAL_CHECKS := {
	"walk_to_goal": [Check.PLAYER_ON_GOAL],
	"core_intro":   [Check.PLAYER_ON_GOAL],
	"switch_and_goal": [Check.SWITCH_PROGRESS, Check.GOAL_ACTIVE],
	"revert": [Check.SWITCH_PROGRESS, Check.GOAL_ACTIVE],

	"split_switches": [
		Check.SWITCH_ACTIVATED,
		Check.INPUT_TAB,
		Check.SWITCH_ALL_CROSS,
	],
	"split_switches_merge": [
		Check.SWITCH_ACTIVATED,
		Check.INPUT_TAB,
		Check.SWITCH_ALL_CROSS,
	],
	"preview_intro": [
		Check.HAS_BRANCHED,
		Check.INPUT_M,
	],
	"restore_intro": [
		Check.HAS_BRANCHED,
		Check.MERGE_SUCCESS,
		Check.SPACE_RESTORE,
	],
	"charge_intro": [
		Check.GAIN_DIV_POINT,
		Check.BRANCH_TWICE,
	],
	"diverge_guided": [
		Check.SWITCH_ACTIVATED,
		Check.INPUT_F1_DISMISS,
		Check.HAS_BRANCHED,
		Check.INPUT_TAB,
		Check.PLAYER_ON_GOAL,
		Check.MERGE_SUCCESS,
	],
	"loop_practice": [
		Check.HAS_BRANCHED,
		Check.SWITCH_ALL_CROSS,
		Check.INPUT_TAB,
		Check.PLAYER_ON_GOAL,
		Check.MERGE_SUCCESS,
	],
	"mutex": [
		Check.HAS_BRANCHED,
		Check.SWITCH_ALL_CROSS,
		Check.MERGE_SUCCESS,
	],

	"branch_only":    [Check.HAS_BRANCHED],
	"switches_cross": [Check.SWITCH_ALL_CROSS],
	"trace_intro":    [Check.SWITCH_ALL_CROSS],
	"re_restore":     [Check.RESTORE_COUNT],
}

## Blocking tutorial: check → required action string.
## "" = no blocking (free step). "horizontal" = A/D movement only.
const BLOCKING_ACTION := {
	Check.SWITCH_ACTIVATED:  "",
	Check.INPUT_F1_DISMISS:  "f1",
	Check.HAS_BRANCHED:      "branch_v",
	Check.INPUT_TAB:         "tab",
	Check.PLAYER_ON_GOAL:    "horizontal",
	Check.MERGE_SUCCESS:     "branch_v",
}

## Highlight node names used by SystemCalloutUI (control bar).
## Check type → { "node": String, "annotations": Array[String] }
const CHECK_HIGHLIGHTS := {
	Check.BRANCH_TWICE: {
		"node": "diverge",
		"annotations": ["綠色 = 可分裂", "灰色 = 無法分裂"],
		"include": ["charge_intro"],
	},
}

## Blocking spotlight sequences per tutorial ID.
## Each item: { "domain": "entity"/"terrain", "type": int, "title": String, "lines": Array[String] }
const SPOTLIGHT_SEQUENCES := {
	"walk_to_goal": [
		{
			"domain": "entity",
			"type": Enums.EntityType.PLAYER,
			"title": "角色",
			"lines": ["藍色圓圈是你控制的角色", "白色箭頭代表角色面向方向", "使用 W/A/S/D 或方向鍵移動"]
		},
		{
			"domain": "terrain",
			"type": Enums.TerrainType.GOAL,
			"title": "終點",
			"lines": ["黃色圓圈是終點", "走到閃爍的終點即可過關"]
		},
	],
	"core_intro": [
		{
			"domain": "pos",
			"pos": Vector2i(1, 1),
			"title": "核心",
			"lines": ["菱形色塊，可被推動"]
		},
		{
			"domain": "pos",
			"pos": Vector2i(1, 5),
			"title": "核心",
			"lines": ["面對核心移動可推動一格", "一次只能推動一個核心"]
		},
	],
	"switch_and_goal": [
		{
			"domain": "terrain",
			"type": Enums.TerrainType.SWITCH,
			"title": "目標",
			"lines": ["灰色菱形框，啟動點", "將核心推進目標格可啟動", "所有目標啟動後，終點將開啟"]
		}
	],
	"charge_intro": [
		{
			"domain": "terrain",
			"type": Enums.TerrainType.BRANCH1,
			"title": "分裂點",
			"lines": ["綠色圓點是分裂點", "取得分裂點增加可分裂次數", "合併狀態才能取得分裂點"]
		}
	],
}

var _scene: GameScene
var _tutorial_id: String = ""
var _active: bool = false
var _was_branched: bool = false
var _branch_v_accum: int = 0
var _sequential_mode: bool = false
var _blocking_mode: bool = false
var _pending_panel_spotlight: Array = []
var _core_turn_hint_shown: bool = false
var _shadow_hint_shown: bool = false

# Checklist state: array of { "label": String, "check": Check, "done": bool }
var _items: Array = []
var _last_bbcode: String = ""


func start_level(tutorial_id: String, steps: Array, scene: GameScene, display_mode: String = "") -> void:
	_scene = scene
	_tutorial_id = tutorial_id
	_items.clear()
	_last_bbcode = ""
	_was_branched = false
	_branch_v_accum = 0
	_pending_panel_spotlight = []
	_core_turn_hint_shown = false
	_shadow_hint_shown = false
	_blocking_mode = display_mode == "blocking"
	_sequential_mode = display_mode == "sequential" or _blocking_mode
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
		elif checks[i] == Check.BRANCH_TWICE:
			item["base_label"] = label
			var v_count := mini(_branch_v_accum, 2)
			item["label"] = label + " (%d/2)" % [v_count]
		elif checks[i] == Check.RESTORE_COUNT:
			item["base_label"] = label
			item["label"] = label + " (0/3)"
		_items.append(item)
	_refresh_toast()


func stop() -> void:
	_active = false


## Returns the required blocking action for the current step, or "" if no blocking.
## "f1" = F1 key; "branch_v" = V key; "tab" = Tab key; "horizontal" = A/D only; "" = free.
func get_blocking_action() -> String:
	if not _blocking_mode or not _active:
		return ""
	for item in _items:
		if not item["done"]:
			return BLOCKING_ACTION.get(item["check"], "")
	return ""


## Returns true if the tutorial sequence contains the given check type.
func has_check(check_type: Check) -> bool:
	for item in _items:
		if item["check"] == check_type:
			return true
	return false


## Returns and clears any pending panel spotlight items.
func get_pending_panel_spotlight() -> Array:
	var result := _pending_panel_spotlight.duplicate()
	_pending_panel_spotlight.clear()
	return result


## Returns spotlight sequence for this tutorial ID, or [] if none.
func get_spotlight_sequence() -> Array:
	if SPOTLIGHT_SEQUENCES.has(_tutorial_id):
		return SPOTLIGHT_SEQUENCES[_tutorial_id]
	return []


## Returns highlight info for SystemCalloutUI, or empty dict if none.
func get_highlight() -> Dictionary:
	if not _active:
		return {}
	# Find first uncompleted item that has a highlight (respecting include/exclude lists)
	for item in _items:
		if item["done"]:
			continue
		var check: Check = item["check"] as Check
		if not CHECK_HIGHLIGHTS.has(check):
			continue
		var hl: Dictionary = CHECK_HIGHLIGHTS[check]
		var exclude: Array = hl.get("exclude", [])
		if exclude.has(_tutorial_id):
			continue
		var include: Array = hl.get("include", [])
		if not include.is_empty() and not include.has(_tutorial_id):
			continue
		return hl
	return {}


func on_state_changed() -> void:
	# Shadow hint: checked before _active guard because the tutorial step
	# (SWITCH_ALL_CROSS) completes while still branched, setting _active=false
	# before the player merges and the shadow appears.
	if _tutorial_id == "trace_intro" and not _shadow_hint_shown:
		var c2 := _scene.controller
		if c2 != null and _was_branched and not c2.has_branched:
			var pos: Vector2i = _get_shadow_entity_pos()
			if pos != Vector2i(-1, -1):
				_shadow_hint_shown = true
				_pending_panel_spotlight = [{
					"domain": "pos",
					"pos": pos,
					"title": "殘影",
					"lines": ["虛線菱形","不可推動也不可穿透"]
				}]
	if not _active:
		if _scene.controller != null:
			_was_branched = _scene.controller.has_branched
		return
	_evaluate_checks()
	if _tutorial_id == "core_intro" and not _core_turn_hint_shown:
		var pos := _get_unfaced_adjacent_box_pos()
		if pos != Vector2i(-1, -1):
			_core_turn_hint_shown = true
			_pending_panel_spotlight = [{
				"domain": "pos",
				"pos": pos,
				"title": "轉向",
				"lines": ["若核心在側面，朝核心按方向鍵", "會原地轉向正對核心"]
			}]


func on_f1_dismissed() -> void:
	if not _active:
		return
	for i in _items.size():
		if _items[i]["done"]:
			continue
		if _items[i]["check"] == Check.INPUT_F1_DISMISS:
			# Allow completion if all previous steps are done (normal flow),
			# OR if the current step is a free step (blocking action = ""),
			# which lets the player read F1 before completing step 0.
			var prev_done := true
			for j in i:
				if not _items[j]["done"]:
					prev_done = false
					break
			if prev_done or get_blocking_action() == "":
				_complete_item(i)
				_evaluate_checks()
			break


func on_restore() -> void:
	if not _active:
		return
	for i in _items.size():
		if _items[i]["done"]:
			continue
		if _items[i]["check"] == Check.SPACE_RESTORE:
			_complete_item(i)
			break


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
		if _items[i]["check"] == Check.INPUT_Z and key == KEY_Z \
				and _has_done_check(Check.SWITCH_ACTIVATED):
			_complete_item(i)


# ---------------------------------------------------------------------------
# Checklist rendering
# ---------------------------------------------------------------------------

func _refresh_toast() -> void:
	var bbcode := ""
	if _sequential_mode:
		var found_current := false
		for item in _items:
			if item["done"]:
				bbcode += "[color=#73c073][✓][/color] [color=#666666]" + item["label"] + "[/color]\n"
			elif not found_current:
				bbcode += "[  ] " + item["label"] + "\n"
				found_current = true
			# future steps hidden until sequential mode ends
		bbcode = bbcode.strip_edges(false, true)
	else:
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
		if _tutorial_id == "preview_intro" \
				and _items[index]["check"] == Check.INPUT_M:
			_pending_panel_spotlight = [{
				"domain": "panel",
				"corner": true,
				"title": "預覽模式",
				"lines": [
					"兩空間疊合，另一空間的角色變灰，核心呈現縮小半透明",
					"可以繼續操作，按 [Tab] 可即時切換角色",
					"再按 [V] 合併或 [M] 退出預覽"
				],
			}]
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
			Check.GAIN_DIV_POINT:
				passed = c.div_points >= 1
			Check.SWITCH_ACTIVATED_BRANCHED:
				passed = c.has_branched and _any_switch_activated()
			Check.INSTANT:
				passed = i > 0 and _items[i - 1]["done"]
			Check.INPUT_F1_DISMISS:
				pass  # handled in on_f1_dismissed()
			Check.BRANCH_TWICE:
				var branch_count := 0
				for raw_in in c.input_log:
					if str(raw_in) == "V":
						branch_count += 1
				_branch_v_accum = maxi(_branch_v_accum, branch_count)
				var v_count_now := mini(_branch_v_accum, 2)
				var new_label3: String = _items[i]["base_label"] + " (%d/2)" % [v_count_now]
				if new_label3 != _items[i]["label"]:
					_items[i]["label"] = new_label3
					changed = true
				passed = _branch_v_accum >= 2
			Check.RESTORE_COUNT:
				var restore_count := 0
				for raw_in in c.input_log:
					if str(raw_in) == "C":
						restore_count += 1
				var new_label_r: String = _items[i]["base_label"] + " (%d/3)" % [mini(restore_count, 3)]
				if new_label_r != _items[i]["label"]:
					_items[i]["label"] = new_label_r
					changed = true
				passed = restore_count >= 3
			# INPUT_TAB is handled in on_input()
		if passed:
			_items[i]["done"] = true
			changed = true
			if check == Check.HAS_BRANCHED and _tutorial_id == "diverge_guided":
				_pending_panel_spotlight = [{
					"domain": "panel",
					"title": "分裂空間",
					"lines": ["當前狀態複製成兩個空間",
					"一次可控制一個空間的角色", "目前控制對象會在中央大圖"],
				}]

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


func _get_unfaced_adjacent_box_pos() -> Vector2i:
	var c := _scene.controller
	if c == null:
		return Vector2i(-1, -1)
	var branch := c.get_active_branch()
	if branch == null:
		return Vector2i(-1, -1)
	var player := branch.get_player()
	if player == null:
		return Vector2i(-1, -1)
	for ent in branch.entities:
		if ent.uid == 0 or ent.type != Enums.EntityType.BOX:
			continue
		var diff: Vector2i = ent.pos - player.pos
		if abs(diff.x) + abs(diff.y) == 1 and diff != player.direction:
			return ent.pos
	return Vector2i(-1, -1)


func _get_shadow_entity_pos() -> Vector2i:
	var c := _scene.controller
	if c == null:
		return Vector2i(-1, -1)
	var branch := c.get_active_branch()
	if branch == null:
		return Vector2i(-1, -1)
	for ent in branch.entities:
		var e := ent as Entity
		if e.uid == 0 or e.type != Enums.EntityType.BOX:
			continue
		if branch.is_shadow(e.uid):
			return e.pos
	return Vector2i(-1, -1)


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


func _branch_v_count() -> int:
	if _scene == null or _scene.controller == null:
		return 0
	var c := _scene.controller
	var count := 0
	for raw_in in c.input_log:
		if str(raw_in) == "V":
			count += 1
	return count
