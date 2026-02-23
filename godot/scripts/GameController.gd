# GameController.gd - Input handling + game state management
# Mirrors Python's GameController class in game_controller.py
class_name GameController

## Emitted when game state changes (renderer should redraw).
signal state_changed
## Emitted when the player wins.
signal victory_achieved
## Emitted when a branch collapses (player falls).
signal collapse_occurred


# ---------------------------------------------------------------------------
# Snapshot for undo
# ---------------------------------------------------------------------------

class GameSnapshot:
	var main_branch:   BranchState
	var sub_branch:    BranchState  # null if not branched
	var current_focus: int
	var has_branched:  bool

	func _init(
		p_main: BranchState,
		p_sub: BranchState,
		p_focus: int,
		p_branched: bool
	) -> void:
		main_branch   = p_main
		sub_branch    = p_sub
		current_focus = p_focus
		has_branched  = p_branched


# ---------------------------------------------------------------------------
# State variables
# ---------------------------------------------------------------------------

var source: LevelSource
var solver_mode: bool = false

var main_branch:   BranchState
var sub_branch:    BranchState  # null when not branched
var current_focus: int = 0      # 0 = main, 1 = sub
var has_branched:  bool = false

var collapsed: bool = false
var victory:   bool = false

var history:   Array = []       # Array[GameSnapshot]
var input_log: Array = []       # Array[String]

# Flash effect (NO_CARRY violation)
var failed_action_pos:  Vector2i = Vector2i(-1, -1)
var failed_action_time: float    = 0.0

# Falling animation (box → hole)
var falling_boxes: Dictionary = {}  # {[uid, pos]: start_time}

# Flag: suppress re-triggering animations right after undo
var just_undid: bool = false


# ---------------------------------------------------------------------------
# Init / Reset
# ---------------------------------------------------------------------------

func _init(p_source: LevelSource, p_solver: bool = false) -> void:
	source      = p_source
	solver_mode = p_solver
	reset()


func reset() -> void:
	main_branch   = source.init_branch()
	sub_branch    = null
	current_focus = 0
	has_branched  = false
	collapsed     = false
	victory       = false
	history.clear()
	input_log.clear()
	failed_action_pos  = Vector2i(-1, -1)
	failed_action_time = 0.0
	falling_boxes.clear()
	just_undid = false
	_save_snapshot()


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

func get_active_branch() -> BranchState:
	return main_branch if current_focus == 0 else sub_branch


# ---------------------------------------------------------------------------
# Snapshot / Undo
# ---------------------------------------------------------------------------

func _save_snapshot() -> void:
	if solver_mode:
		return
	var snap := GameSnapshot.new(
		main_branch.copy(),
		sub_branch.copy() if sub_branch != null else null,
		current_focus,
		has_branched
	)
	history.append(snap)


func undo() -> bool:
	if history.size() <= 1:
		return false

	history.pop_back()
	if input_log.size() > 0:
		input_log.pop_back()
	var snap := history[-1] as GameSnapshot

	main_branch   = snap.main_branch.copy()
	sub_branch    = snap.sub_branch.copy() if snap.sub_branch != null else null
	current_focus = snap.current_focus
	has_branched  = snap.has_branched
	collapsed     = false
	victory       = false

	falling_boxes.clear()
	failed_action_pos  = Vector2i(-1, -1)
	failed_action_time = 0.0
	just_undid         = true

	state_changed.emit()
	return true


# ---------------------------------------------------------------------------
# Physics update (call once per frame in game loop)
# ---------------------------------------------------------------------------

func update_physics() -> void:
	var active := get_active_branch()

	if solver_mode:
		var result := Physics.step(active)
		if result == Enums.PhysicsResult.FALL:
			collapsed = true
		return

	var now := Time.get_unix_time_from_system()

	# Track boxes before physics to detect new falls
	var before_underground: Dictionary = {}
	for e in active.entities:
		var ent := e as Entity
		if ent.z == -1:
			var key := [ent.uid, ent.pos]
			before_underground[key] = true

	var result := Physics.step(active)

	if not just_undid:
		for e in active.entities:
			var ent := e as Entity
			if ent.z == -1:
				var key := [ent.uid, ent.pos]
				if not before_underground.has(key):
					falling_boxes[key] = now

	just_undid = false

	if result == Enums.PhysicsResult.FALL:
		collapsed = true
		collapse_occurred.emit()


## Returns falling progress 0.0–1.0 for box (uid, pos), or -1 if not falling.
func get_falling_progress(uid: int, pos: Vector2i) -> float:
	var key := [uid, pos]
	if not falling_boxes.has(key):
		return -1.0

	var elapsed: float = Time.get_unix_time_from_system() - (falling_boxes[key] as float)
	var duration: float = 0.2  # 200 ms

	if elapsed >= duration:
		falling_boxes.erase(key)
		return -1.0

	var t: float = elapsed / duration
	if t < 0.6:
		return 0.0
	var t_fall: float = (t - 0.6) / 0.6
	return t_fall * t_fall


# ---------------------------------------------------------------------------
# Actions: Branch / Merge / Switch
# ---------------------------------------------------------------------------

func try_branch() -> bool:
	if has_branched:
		return false

	var active  := get_active_branch()
	var terrain: int = active.terrain.get(active.get_player().pos, Enums.TerrainType.FLOOR)

	if not (terrain in Enums.BRANCH_DECREMENT):
		return false

	# Decrement branch uses
	var new_terrain: int = Enums.BRANCH_DECREMENT[terrain]
	main_branch.terrain[active.get_player().pos] = new_terrain

	var pair    := Timeline.diverge(main_branch)
	main_branch  = pair[0]
	sub_branch   = pair[1]
	has_branched = true

	_log_input("V")
	_save_snapshot()
	state_changed.emit()
	return true


func try_merge() -> bool:
	if not has_branched:
		return false
	return _merge_branches("normal")


func try_fetch_merge() -> bool:
	return _merge_branches("fetch")


func _merge_branches(mode: String) -> bool:
	if not has_branched:
		return false

	var focused := get_active_branch()
	var other   := sub_branch if current_focus == 0 else main_branch

	var merged: BranchState
	var log_char: String

	if mode == "fetch":
		var focused_held := focused.get_held_items()
		var other_held   := other.get_held_items()
		var total_items  := 0
		var union: Array[int] = focused_held.duplicate()
		for uid in other_held:
			if not union.has(uid):
				union.append(uid)
		total_items = union.size()
		if total_items > Physics.effective_capacity(focused):
			return false
		merged   = Timeline.merge_fetch(focused, other, union)
		log_char = "F"
	else:
		merged   = Timeline.merge_normal(focused, other)
		log_char = "C"

	main_branch   = merged
	sub_branch    = null
	has_branched  = false
	current_focus = 0

	_log_input(log_char)
	_save_snapshot()
	state_changed.emit()
	return true


func can_show_fetch_hint() -> bool:
	if not has_branched:
		return false
	var focused := get_active_branch()
	var other   := sub_branch if current_focus == 0 else main_branch
	var f_held  := focused.get_held_items()
	var o_held  := other.get_held_items()
	if not f_held.is_empty() or o_held.is_empty():
		return false
	var union: Array[int] = []
	for uid in f_held:
		union.append(uid)
	for uid in o_held:
		if not union.has(uid):
			union.append(uid)
	return union.size() <= Physics.effective_capacity(focused)


func switch_focus() -> bool:
	if not has_branched:
		return false
	current_focus = 1 - current_focus
	_log_input("T")
	_save_snapshot()
	state_changed.emit()
	return true


# ---------------------------------------------------------------------------
# Actions: Movement / Interaction
# ---------------------------------------------------------------------------

func handle_move(direction: Vector2i) -> bool:
	var active    := get_active_branch()
	var target_pos := active.get_player().pos + direction

	var has_box_ahead := active.has_box_at(target_pos)
	var is_holding    := not active.get_held_items().is_empty()

	var dir_key: String = ({
		Vector2i(0, -1): "U",
		Vector2i(0,  1): "D",
		Vector2i(-1, 0): "L",
		Vector2i( 1, 0): "R",
	} as Dictionary)[direction]

	# Two-step turning: when holding OR facing a box
	if is_holding or has_box_ahead:
		if active.get_player().direction != direction:
			active.get_player().direction = direction
			_log_input(dir_key)
			_save_snapshot()
			state_changed.emit()
			return true
	else:
		active.get_player().direction = direction

	if GameLogic.can_move(active, direction):
		GameLogic.execute_move(active, direction)
		_log_input(dir_key)
		_save_snapshot()
		state_changed.emit()
		return true
	else:
		# Flash if blocked by NO_CARRY
		if is_holding and active.terrain.get(target_pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.NO_CARRY:
			_trigger_flash(target_pos)
		return false


func handle_pickup(allow_pickup: bool = true) -> bool:
	if not allow_pickup:
		return false
	var active     := get_active_branch()
	var player_pos := active.get_player().pos
	var on_no_carry: bool = (active.terrain.get(player_pos, Enums.TerrainType.FLOOR) as int) == Enums.TerrainType.NO_CARRY

	var result := GameLogic.try_pickup(active)
	if result:
		_log_input("P")
		_save_snapshot()
		state_changed.emit()
	else:
		if on_no_carry and active.get_held_items().is_empty():
			var front_pos := player_pos + active.get_player().direction
			if active.find_box_at(front_pos) != null:
				_trigger_flash(player_pos)
	return result


func handle_drop() -> bool:
	var active := get_active_branch()
	var result := GameLogic.try_drop(active)
	if result:
		_log_input("O")
		_save_snapshot()
		state_changed.emit()
	return result


## Adaptive X action: drop if holding, converge if facing shadow, else pickup.
func handle_adaptive_action(allow_converge: bool = true, allow_pickup: bool = true) -> bool:
	var active    := get_active_branch()
	var player    := active.get_player()
	var front_pos := player.pos + player.direction

	# If holding → drop
	if not active.get_held_items().is_empty():
		return handle_drop()

	var target := active.find_box_at(front_pos)
	if target == null:
		return false

	# Check for overlap (2+ distinct uids at front_pos)
	var uids_at_front: Dictionary = {}
	for e in active.entities:
		var ent := e as Entity
		if ent.uid != 0 and ent.type == Enums.EntityType.BOX \
		   and ent.pos == front_pos and ent.is_grounded():
			uids_at_front[ent.uid] = true
	var has_overlap := uids_at_front.size() >= 2

	if has_overlap or active.is_shadow(target.uid):
		if not allow_converge:
			return false
		var fused := Timeline.try_fuse(active, front_pos)
		if not fused:
			var entity := active.get_entities_by_uid(target.uid)[0] as Entity if not active.get_entities_by_uid(target.uid).is_empty() else null
			if entity != null and entity.fused_from.size() > 0:
				var source_present := false
				for e in active.entities:
					if entity.fused_from.has((e as Entity).uid):
						source_present = true
						break
				if source_present:
					Timeline.resolve_fusion_toward_fusion(active, target.uid)
				else:
					Timeline.converge_one(active, target.uid, front_pos)
			else:
				# Check if a fusion has absorbed this uid
				var fusion_present := false
				for e in active.entities:
					var ent := e as Entity
					if ent.fused_from.size() > 0 and ent.fused_from.has(target.uid):
						fusion_present = true
						break
				if fusion_present:
					Timeline.resolve_fusion_toward_sources(active, target.uid)
				else:
					Timeline.converge_one(active, target.uid, front_pos)

		_log_input("X")
		_save_snapshot()
		state_changed.emit()
		return true
	else:
		return handle_pickup(allow_pickup)


# ---------------------------------------------------------------------------
# Victory check
# ---------------------------------------------------------------------------

func check_victory() -> bool:
	if has_branched:
		return false
	var preview := get_merge_preview()
	var switches_ok: bool = preview.all_switches_activated()
	var goal_ok: bool = (preview.terrain.get(preview.get_player().pos, Enums.TerrainType.FLOOR) as int) == Enums.TerrainType.GOAL
	victory = switches_ok and goal_ok
	if victory:
		victory_achieved.emit()
	return victory


func get_merge_preview() -> BranchState:
	if not has_branched:
		return main_branch
	var focused := get_active_branch()
	var other   := sub_branch if current_focus == 0 else main_branch
	return Timeline.merge_normal(focused, other)


# ---------------------------------------------------------------------------
# Hint helpers
# ---------------------------------------------------------------------------

func get_interaction_hint() -> Dictionary:
	## Returns {text, color, target_pos, is_drop}
	var active    := get_active_branch()
	var player    := active.get_player()
	var front_pos := player.pos + player.direction

	if not active.get_held_items().is_empty():
		var can_drop := Physics.collision_at(front_pos, active) <= 0
		if can_drop:
			return {text="放下", color=Color(0.2,0.78,0.2), target_pos=front_pos, is_drop=true}
		return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}

	var target := active.find_box_at(front_pos)
	if target == null:
		return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}

	var uids_at_front: Dictionary = {}
	for e in active.entities:
		var ent := e as Entity
		if ent.uid != 0 and ent.type == Enums.EntityType.BOX \
		   and ent.pos == front_pos and ent.is_grounded():
			uids_at_front[ent.uid] = true
	if uids_at_front.size() >= 2 or active.is_shadow(target.uid):
		return {text="收束", color=Color(0,0.86,0.86), target_pos=front_pos, is_drop=false}

	if Physics.effective_capacity(active, player.pos) == 0:
		return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}

	return {text="拾取", color=Color(0.2,0.78,0.2), target_pos=front_pos, is_drop=false}


func get_timeline_hint() -> String:
	if not has_branched:
		var active  := get_active_branch()
		var terrain: int = active.terrain.get(active.get_player().pos, Enums.TerrainType.FLOOR)
		if terrain in Enums.BRANCH_DECREMENT:
			return "V 分裂"
		return ""

	var focused    := get_active_branch()
	var other      := sub_branch if current_focus == 0 else main_branch
	var f_held     := focused.get_held_items()
	var o_held     := other.get_held_items()

	if not f_held.is_empty() and not o_held.is_empty():
		# Check if they hold different items
		var different := false
		for uid in f_held:
			if not o_held.has(uid):
				different = true
				break
		if different:
			return "F 抓取合併"

	if f_held.is_empty() and not o_held.is_empty():
		if focused.terrain.get(focused.get_player().pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.NO_CARRY:
			return "C 合併  [抓取禁止]"
		return "C 合併  F 抓取"

	return "C 合併"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

func _trigger_flash(pos: Vector2i) -> void:
	failed_action_pos  = pos
	failed_action_time = Time.get_unix_time_from_system()


func _log_input(ch: String) -> void:
	if not solver_mode:
		input_log.append(ch)
