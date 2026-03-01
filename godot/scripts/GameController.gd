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
	var div_points:    int

	func _init(
		p_main: BranchState,
		p_sub: BranchState,
		p_focus: int,
		p_branched: bool,
		p_div: int
	) -> void:
		main_branch   = p_main
		sub_branch    = p_sub
		current_focus = p_focus
		has_branched  = p_branched
		div_points    = p_div


# ---------------------------------------------------------------------------
# State variables
# ---------------------------------------------------------------------------

var source: LevelSource
var solver_mode: bool = false

var main_branch:   BranchState
var sub_branch:    BranchState  # null when not branched
var current_focus: int = 0      # 0 = main, 1 = sub
var has_branched:  bool = false
var div_points:    int  = 0     # charge for branching (game-level, not per-branch)

var collapsed: bool = false
var victory:   bool = false

var history:   Array = []       # Array[GameSnapshot]
var input_log: Array = []       # Array[String]

# Flash effect (NO_CARRY violation)
var failed_action_pos:  Vector2i = Vector2i(-1, -1)
var failed_action_time: float    = 0.0
var failed_action_style: String  = "cell"

# Falling animation (box → hole)
var falling_boxes: Dictionary = {}  # {[uid, pos]: start_time}

# Flag: suppress re-triggering animations right after undo
var just_undid: bool = false

# Interaction-hint gates (synced from tutorial/progression hints)
var hint_allow_converge: bool = true
var hint_allow_pickup: bool = true
var hint_allow_face_box: bool = true
var hint_allow_fetch: bool = true


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
	div_points    = 0
	collapsed     = false
	victory       = false
	history.clear()
	input_log.clear()
	failed_action_pos  = Vector2i(-1, -1)
	failed_action_time = 0.0
	failed_action_style = "cell"
	falling_boxes.clear()
	just_undid = false
	_check_charge_pickup(main_branch)  # ?��?站在?�能?�直?�給 charge
	_save_snapshot()


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

func get_active_branch() -> BranchState:
	return main_branch if current_focus == 0 else sub_branch


func set_interaction_hint_gates(
		allow_converge: bool,
		allow_pickup: bool,
		allow_face_box: bool = true,
		allow_fetch: bool = true) -> void:
	hint_allow_converge = allow_converge
	hint_allow_pickup = allow_pickup
	hint_allow_face_box = allow_face_box
	hint_allow_fetch = allow_fetch


func is_fetch_hint_unlocked() -> bool:
	return hint_allow_fetch


func get_facing_box_hint_target_pos() -> Vector2i:
	if not hint_allow_face_box:
		return Vector2i(-1, -1)
	var active := get_active_branch()
	var player := active.get_player()
	if player == null:
		return Vector2i(-1, -1)
	if not active.get_held_items().is_empty():
		return Vector2i(-1, -1)
	var front_pos := player.pos + player.direction
	var target := active.find_box_at(front_pos)
	if target == null:
		return Vector2i(-1, -1)
	return front_pos


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
		has_branched,
		div_points
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
	div_points    = snap.div_points
	collapsed     = false
	victory       = false

	falling_boxes.clear()
	failed_action_pos  = Vector2i(-1, -1)
	failed_action_time = 0.0
	failed_action_style = "cell"
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
					falling_boxes[key] = true

	just_undid = false

	if result == Enums.PhysicsResult.FALL:
		collapsed = true
		collapse_occurred.emit()


## Whether a box (uid, pos) is registered as newly fallen (Tween driven by GameScene).
func is_box_falling(uid: int, pos: Vector2i) -> bool:
	return falling_boxes.has([uid, pos])


# ---------------------------------------------------------------------------
# Actions: Branch / Merge / Switch
# ---------------------------------------------------------------------------

func try_branch() -> bool:
	if has_branched:
		return false

	if div_points < 1:
		_trigger_player_fail_flash(main_branch)
		return false           # No charge

	div_points -= 1            # Consume one charge

	var pair    := Timeline.diverge(main_branch)
	main_branch  = pair[0]
	sub_branch   = pair[1]
	has_branched = true

	_log_input("V")
	_save_snapshot()
	state_changed.emit()
	return true


## Called after every successful move. Awards +1 charge when the player steps
## onto a branch terrain tile, and decrements that tile one level.
func _check_charge_pickup(branch: BranchState) -> void:
	if has_branched:
		return   # 分裂期間充能格變灰，不可收集
	var pos := branch.get_player().pos
	var terrain: int = branch.terrain.get(pos, Enums.TerrainType.FLOOR)
	if terrain in Enums.BRANCH_TERRAINS:
		div_points += Enums.BRANCH_CHARGE[terrain]
		branch.terrain[pos] = Enums.TerrainType.FLOOR


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
		var fetch_uids: Array[int] = _fetch_uids_from_other(focused_held, other_held)
		# Fetch merge must actually fetch from the other branch; never degrade to normal merge.
		if fetch_uids.is_empty():
			_trigger_player_fail_flash(focused)
			return false
		var union: Array[int] = focused_held.duplicate()
		for uid in fetch_uids:
			if not union.has(uid):
				union.append(uid)
		var total_items: int  = union.size()
		if total_items > Physics.effective_capacity(focused):
			_trigger_player_fail_flash(focused)
			return false
		merged   = Timeline.merge_fetch(focused, other, fetch_uids)
		log_char = "F"
	else:
		merged   = Timeline.merge_normal(focused, other)
		log_char = "M"

	if _has_player_on_ground_box_after_merge(merged):
		_trigger_player_fail_flash(focused)
		return false
	if not _merge_respects_storage_capacity(merged):
		_trigger_player_fail_flash(focused)
		return false

	main_branch   = merged
	sub_branch    = null
	has_branched  = false
	current_focus = 0

	_check_charge_pickup(main_branch)  # 合併後站在充能格也能收集

	_log_input(log_char)
	_save_snapshot()
	state_changed.emit()
	return true


func _has_player_on_ground_box_after_merge(branch: BranchState) -> bool:
	"""True if player stands on any grounded box after merge."""
	var player_pos := branch.get_player().pos
	for e in branch.entities:
		var ent := e as Entity
		if ent == null:
			continue
		if ent.uid != 0 and ent.type == Enums.EntityType.BOX and ent.z == 0 and ent.collision > 0 and ent.pos == player_pos:
			return true
	return false


func can_show_fetch_hint() -> bool:
	if not has_branched:
		return false
	var focused := get_active_branch()
	var other   := sub_branch if current_focus == 0 else main_branch
	var f_held: Array[int] = focused.get_held_items()
	var o_held: Array[int] = other.get_held_items()
	var fetch_uids: Array[int] = _fetch_uids_from_other(f_held, o_held)
	if fetch_uids.is_empty():
		return false
	var union: Array[int] = []
	for uid in f_held:
		union.append(uid)
	for uid in fetch_uids:
		if not union.has(uid):
			union.append(uid)
	if union.size() > Physics.effective_capacity(focused):
		return false
	var merged := Timeline.merge_fetch(focused, other, fetch_uids)
	if _has_player_on_ground_box_after_merge(merged):
		return false
	return _merge_respects_storage_capacity(merged)


func can_normal_merge() -> bool:
	if not has_branched:
		return false
	var focused := get_active_branch()
	var other   := sub_branch if current_focus == 0 else main_branch
	var merged  := Timeline.merge_normal(focused, other)
	if _has_player_on_ground_box_after_merge(merged):
		return false
	return _merge_respects_storage_capacity(merged)


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
		_check_charge_pickup(active)
		_log_input(dir_key)
		_save_snapshot()
		state_changed.emit()
		return true
	else:
		# Flash if blocked by NO_CARRY
		if is_holding and active.terrain.get(target_pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.NO_CARRY:
			_trigger_player_fail_flash(active)
		return false


func handle_pickup(allow_pickup: bool = true) -> bool:
	if not allow_pickup:
		return false
	var active     := get_active_branch()
	var player_pos := active.get_player().pos
	var on_no_carry: bool = (active.terrain.get(player_pos, Enums.TerrainType.FLOOR) as int) == Enums.TerrainType.NO_CARRY

	var result := GameLogic.try_pickup(active)
	if result:
		_log_input("K")
		_save_snapshot()
		state_changed.emit()
	else:
		if on_no_carry and active.get_held_items().is_empty():
			var front_pos := player_pos + active.get_player().direction
			if active.find_box_at(front_pos) != null:
				_trigger_player_fail_flash(active)
	return result


func handle_drop() -> bool:
	var active := get_active_branch()
	var held_count: int = active.get_held_items().size()
	var front_pos: Vector2i = active.get_player().pos + active.get_player().direction
	var result := GameLogic.try_drop(active)
	if result:
		_log_input("P")
		_save_snapshot()
		state_changed.emit()
	else:
		if held_count > 0 and Physics.collision_at(front_pos, active) > 0:
			_trigger_player_fail_flash(active)
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
					Timeline.converge(active, target.uid, front_pos)
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
					Timeline.converge(active, target.uid, front_pos)

		_log_input("C")
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
		if not hint_allow_converge:
			return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}
		return {text="還原", color=Color(0,0.86,0.86), target_pos=front_pos, is_drop=false}

	if not hint_allow_pickup:
		return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}

	if Physics.effective_capacity(active, player.pos) == 0:
		return {text="", color=Color.BLACK, target_pos=Vector2i(-1,-1), is_drop=false}

	return {text="撿取", color=Color(0.2,0.78,0.2), target_pos=front_pos, is_drop=false}


func get_timeline_hint() -> String:
	if not has_branched:
		if div_points > 0:
			return "V 分裂"
		return ""

	var focused    := get_active_branch()
	var other      := sub_branch if current_focus == 0 else main_branch
	var f_held     := focused.get_held_items()
	var o_held     := other.get_held_items()

	if not f_held.is_empty() and not o_held.is_empty():
		# Check if the held sets are unequal (symmetric — matches Python's focused_held != other_held)
		var different := f_held.size() != o_held.size()
		if not different:
			for uid in f_held:
				if not o_held.has(uid):
					different = true
					break
		if different:
			return "F 抓取合併"

	if f_held.is_empty() and not o_held.is_empty():
		if focused.terrain.get(focused.get_player().pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.NO_CARRY:
			return "V 合併  [抓取禁止]"
		return "V 合併  F 抓取"

	return "V 合併"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

func _trigger_flash(pos: Vector2i, style: String = "cell") -> void:
	failed_action_pos  = pos
	failed_action_time = Time.get_unix_time_from_system()
	failed_action_style = style


func _trigger_player_fail_flash(branch: BranchState) -> void:
	if branch == null:
		return
	var player := branch.get_player()
	if player == null:
		return
	var style: String = "player_square" if not branch.get_held_items().is_empty() else "player_circle"
	_trigger_flash(player.pos, style)


func _fetch_uids_from_other(focused_held: Array[int], other_held: Array[int]) -> Array[int]:
	var result: Array[int] = []
	for uid in other_held:
		if not focused_held.has(uid) and not result.has(uid):
			result.append(uid)
	return result


func _merge_respects_storage_capacity(branch: BranchState) -> bool:
	var held_count: int = branch.get_held_items().size()
	var cap: int = Physics.effective_capacity(branch, branch.get_player().pos)
	return held_count <= cap


func _log_input(ch: String) -> void:
	if not solver_mode:
		input_log.append(ch)

