extends Node2D
class_name HintOverlay

# Converge line color (cyan) matches V-merge hint border.
const COLOR_CONVERGE := Color8(75, 150, 200)
const COLOR_FETCH := Color8(255, 150, 50)
const ENABLE_CROSS_SPACE_CONVERGE := false
const DASH_SCROLL_SPEED := 28.0

var _frame_spec: PresentationModel.FrameViewSpec = null
var _controller: GameController = null
var _merge_preview_active: bool = false
var _animation_frame: int = 0


func update_overlay(
		frame_spec: PresentationModel.FrameViewSpec,
		controller: GameController,
		merge_preview_active: bool,
		animation_frame: int) -> void:
	_frame_spec = frame_spec
	_controller = controller
	_merge_preview_active = merge_preview_active
	_animation_frame = animation_frame
	queue_redraw()


func clear_overlay() -> void:
	_frame_spec = null
	_controller = null
	_merge_preview_active = false
	_animation_frame = 0
	queue_redraw()


func _draw() -> void:
	if _frame_spec == null or _controller == null:
		return
	if not _controller.has_branched:
		return
	if _frame_spec.main_branch == null or _frame_spec.sub_branch == null:
		return

	var focus: int = _controller.current_focus
	var focused_spec: PresentationModel.BranchViewSpec
	var other_spec: PresentationModel.BranchViewSpec
	if focus == 0:
		focused_spec = _frame_spec.main_branch
		other_spec = _frame_spec.sub_branch
	else:
		focused_spec = _frame_spec.sub_branch
		other_spec = _frame_spec.main_branch

	var focused_state: BranchState = _controller.get_active_branch()
	var other_state: BranchState = _controller.sub_branch if focus == 0 else _controller.main_branch

	if _merge_preview_active:
		_draw_fetch_and_converge_lines(focused_state, other_state, focused_spec, other_spec)
	else:
		_draw_converge_lines(focused_state, other_state, focused_spec, other_spec)


func _draw_converge_lines(
		focused_state: BranchState,
		other_state: BranchState,
		focused_spec: PresentationModel.BranchViewSpec,
		other_spec: PresentationModel.BranchViewSpec) -> void:
	if not ENABLE_CROSS_SPACE_CONVERGE:
		return
	var held_uids: Array[int] = focused_state.get_held_items()
	if held_uids.is_empty():
		return

	var target_pos: Vector2i = focused_state.get_player().pos
	var target_center: Vector2 = _grid_to_screen(focused_spec, target_pos)
	var offset: float = _dash_offset()

	for uid in held_uids:
		var others: Array = other_state.get_non_held_instances(uid)
		for raw in others:
			var ent: Entity = raw as Entity
			if ent == null:
				continue
			var src_center: Vector2 = _grid_to_screen(other_spec, ent.pos)
			_draw_dashed_line(src_center, target_center, COLOR_CONVERGE, 3.0, 12.0, offset)


func _draw_fetch_and_converge_lines(
		focused_state: BranchState,
		other_state: BranchState,
		focused_spec: PresentationModel.BranchViewSpec,
		other_spec: PresentationModel.BranchViewSpec) -> void:
	var focused_held: Array[int] = focused_state.get_held_items()
	var other_held: Array[int] = other_state.get_held_items()
	if not focused_held.is_empty() or other_held.is_empty():
		return

	var focused_player_center: Vector2 = _grid_to_screen(focused_spec, focused_state.get_player().pos)
	var other_player_center: Vector2 = _grid_to_screen(other_spec, other_state.get_player().pos)
	var offset: float = _dash_offset()
	var pulse: float = 0.65 + 0.35 * (0.5 + 0.5 * sin(Time.get_ticks_msec() / 1000.0 * 4.0))
	var fetch_col := COLOR_FETCH
	fetch_col.a = pulse

	# Fetch line: other branch player -> focused player.
	_draw_dashed_line(other_player_center, focused_player_center, fetch_col, 3.0, 12.0, offset)

	# Converge lines for fetched UIDs: focused instances -> focused player.
	var seen: Dictionary = {}
	for uid in other_held:
		if seen.has(uid):
			continue
		seen[uid] = true
		var focused_instances: Array = focused_state.get_non_held_instances(uid)
		for raw in focused_instances:
			var ent: Entity = raw as Entity
			if ent == null:
				continue
			var src_center: Vector2 = _grid_to_screen(focused_spec, ent.pos)
			_draw_dashed_line(src_center, focused_player_center, COLOR_CONVERGE, 2.0, 10.0, offset)


func _grid_to_screen(spec: PresentationModel.BranchViewSpec, pos: Vector2i) -> Vector2:
	var eff: float = spec.cell_size * spec.scale
	return Vector2(
		spec.pos_x + (float(pos.x) + 0.5) * eff,
		spec.pos_y + (float(pos.y) + 0.5) * eff
	)


func _draw_dashed_line(
		from_pos: Vector2,
		to_pos: Vector2,
		col: Color,
		width: float = 3.0,
		dash_len: float = 9.0,
		offset: float = 0.0) -> void:
	var dist: float = from_pos.distance_to(to_pos)
	if dist <= 0.001:
		return
	var dir: Vector2 = (to_pos - from_pos) / dist
	var period: float = dash_len * 2.0
	var pos: float = fmod(offset, period)
	while pos < dist:
		var seg_start: float = maxf(0.0, pos)
		var seg_end: float = minf(dist, pos + dash_len)
		if seg_end > seg_start:
			var p0: Vector2 = from_pos + dir * seg_start
			var p1: Vector2 = from_pos + dir * seg_end
			draw_line(p0, p1, col, width, true)
		pos += period


func _dash_offset(speed: float = DASH_SCROLL_SPEED) -> float:
	return (Time.get_ticks_msec() / 1000.0) * speed
