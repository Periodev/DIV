# PresentationModel.gd - Presentation layer data types and builder
# Mirrors Python's presentation_model.py
# Transforms GameController state → visual specs consumed by GameRenderer
class_name PresentationModel


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class InteractionHint:
	var text:       String   = ""
	var color:      Color    = Color.WHITE
	var target_pos: Vector2i = Vector2i(-1, -1)
	var is_inset:   bool     = false

	func _init(p_text: String, p_color: Color, p_pos: Vector2i, p_inset: bool) -> void:
		text = p_text
		color = p_color
		target_pos = p_pos
		is_inset = p_inset


## Visual specification for one branch panel.
class BranchViewSpec:
	var state:                  BranchState = null
	var title:                  String      = ""
	var is_focused:             bool        = false
	var border_color:           Color       = Color.WHITE
	var interaction_hint                    = null   # InteractionHint or null
	var facing_box_hint_pos:    Vector2i    = Vector2i(-1, -1)
	var timeline_hint:          String      = ""
	var highlight_branch_point: bool        = false
	var has_branched:           bool        = false
	var is_merge_preview:       bool        = false
	var scale:                  float       = 1.0
	var pos_x:                  int         = 0
	var pos_y:                  int         = 0
	var alpha:                  float       = 1.0
	var cell_size:              int         = 80
	# Rendering state (not in Python BranchViewSpec, added for renderer convenience)
	var goal_glow:              int         = 0  # 0=off 1=weak(branched+preview ok) 2=strong(merged+ok)
	var animation_frame:        int         = 0
	var flash_pos:              Vector2i    = Vector2i(-1, -1)
	var flash_intensity:        float       = 0.0
	var flash_style:            String      = "cell"
	var falling_progress:       Dictionary  = {}
	# Adaptive hint flags (mirrors render_arc high-level behavior)
	var branch_hint_active:     bool        = false
	var show_merge_preview_hint: bool       = false
	var show_merge_hint:        bool        = false
	var merge_hint_enabled:     bool        = true
	var show_fetch_indicator:   bool        = false
	var fetch_mode_enabled:     bool        = false
	var show_player_direction:  bool        = true


## Complete visual specification for one frame.
class FrameViewSpec:
	var main_branch:   BranchViewSpec = null   # DIV 0
	var sub_branch:    BranchViewSpec = null   # DIV 1 (null if not branched)
	var has_branched:  bool           = false
	var current_focus: int            = 0
	var is_collapsed:  bool           = false
	var is_victory:    bool           = false
	var timeline_hint: String         = ""


# ---------------------------------------------------------------------------
# Layout constants (matching presentation_model.py actual computed values)
# ---------------------------------------------------------------------------

const WINDOW_W     := 1280
const WINDOW_H     := 720
const TARGET_PANEL := 480
const GAP          := 30
const FOCUS_SCALE  := 1.0
const SIDE_SCALE   := 0.7

const SIDE_GRID := int(TARGET_PANEL * SIDE_SCALE)   # 336
const CENTER_X  := (WINDOW_W - TARGET_PANEL) / 2    # 400
const CENTER_Y  := (WINDOW_H - TARGET_PANEL) / 2    # 120
const RIGHT_X   := CENTER_X + TARGET_PANEL + GAP    # 910
const LEFT_X    := CENTER_X - GAP - SIDE_GRID       # 34
const SIDE_Y    := (WINDOW_H - SIDE_GRID) / 2       # 192
const BORDER_FOCUSED := Color(0.72, 0.72, 0.72)
const BORDER_UNFOCUSED := Color(0.4, 0.4, 0.4)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

static func build(
		controller: GameController,
		animation_frame: int,
		fall_progress:        Dictionary = {},
		slide_progress:       float = 0.0,
		slide_direction:      int   = 0,
		merge_preview_active: bool  = false,
		merge_preview_progress: float = 0.0) -> FrameViewSpec:

	var spec := FrameViewSpec.new()
	spec.has_branched  = controller.has_branched
	spec.current_focus = controller.current_focus
	spec.is_collapsed  = controller.collapsed
	spec.is_victory    = controller.victory
	spec.timeline_hint = controller.get_timeline_hint()

	var focus      := controller.current_focus
	var has_branched := controller.has_branched
	var branch_hint_active: bool = false
	if not has_branched:
		branch_hint_active = controller.div_points > 0
	var show_merge_preview_hint: bool = has_branched
	var show_merge_hint: bool = has_branched
	var merge_hint_enabled: bool = has_branched
	if has_branched and controller.has_method("can_normal_merge"):
		merge_hint_enabled = bool(controller.call("can_normal_merge"))
	# F indicator is always shown in branched state.
	# Color indicates whether fetch merge is currently usable.
	var show_fetch_indicator: bool = has_branched
	var fetch_mode_enabled: bool = has_branched and controller.can_show_fetch_hint()

	# Goal glow level: 2=strong (merged+switches done), 1=weak (branched+preview switches done).
	var preview := controller.get_merge_preview()
	var goal_glow := 0
	if preview.all_switches_activated():
		goal_glow = 1 if controller.has_branched else 2

	# Flash effect
	var flash_pos := Vector2i(-1, -1)
	var flash_int := 0.0
	var flash_style := "cell"
	if controller.failed_action_pos != Vector2i(-1, -1):
		var elapsed := Time.get_unix_time_from_system() - controller.failed_action_time
		if elapsed < 0.3:
			flash_int = 1.0 - elapsed / 0.3
			flash_pos = controller.failed_action_pos
			flash_style = controller.failed_action_style

	# Falling boxes: progress driven by GameScene Tweens.
	# Split mode must isolate animations per branch to avoid cross-panel bleed.
	var falling_main: Dictionary = _filter_falling_for_branch(fall_progress, controller.main_branch, 0)
	var falling_sub: Dictionary = _filter_falling_for_branch(fall_progress, controller.sub_branch, 1)

	# Cell size (focused panel always TARGET_PANEL pixels wide)
	var gs: int      = controller.main_branch.grid_size
	var cell_sz: int = TARGET_PANEL / gs

	# Panel positions and scales
	var main_x := CENTER_X; var main_y := CENTER_Y; var main_s := FOCUS_SCALE
	var sub_x  := RIGHT_X;  var sub_y  := SIDE_Y;   var sub_s  := SIDE_SCALE
	var main_a := 1.0;      var sub_a  := 1.0

	var preview_on := merge_preview_active or merge_preview_progress > 0.0

	if not has_branched:
		main_x = CENTER_X; main_y = CENTER_Y; main_s = FOCUS_SCALE
	elif preview_on:
		var p := _calc_merge_preview_positions(focus, merge_preview_progress)
		main_x = p[0]; main_y = p[1]; main_s = p[2]
		sub_x  = p[3]; sub_y  = p[4]; sub_s  = p[5]
		main_a = p[6]; sub_a  = p[7]
	elif slide_progress > 0.0:
		var p := _calc_slide_positions(focus, slide_progress, slide_direction)
		main_x = p[0]; main_y = p[1]; main_s = p[2]
		sub_x  = p[3]; sub_y  = p[4]; sub_s  = p[5]
	else:
		if focus == 0:
			main_x = CENTER_X; main_y = CENTER_Y; main_s = FOCUS_SCALE
			sub_x  = RIGHT_X;  sub_y  = SIDE_Y;   sub_s  = SIDE_SCALE
		else:
			main_x = LEFT_X;   main_y = SIDE_Y;   main_s = SIDE_SCALE
			sub_x  = CENTER_X; sub_y  = CENTER_Y; sub_s  = FOCUS_SCALE

	# Interaction hint (only for focused branch)
	var hint_d: Dictionary = controller.get_interaction_hint()
	var hint_text: String  = hint_d.get("text", "") as String
	var ih = null
	var face_box_hint_pos: Vector2i = Vector2i(-1, -1)
	if hint_text != "":
		var is_inset: bool = bool(hint_d.get("is_drop", hint_d.get("is_inset", false)))
		ih = InteractionHint.new(
			hint_text,
			hint_d.get("color", Color.WHITE) as Color,
			hint_d.get("target_pos", Vector2i(-1, -1)) as Vector2i,
			is_inset)
	if controller.has_method("get_facing_box_hint_target_pos"):
		face_box_hint_pos = controller.get_facing_box_hint_target_pos()

	# Build main branch spec (DIV 0)
	spec.main_branch = _make_spec(
		controller.main_branch,
		focus == 0,
		"DIV 0" if has_branched else "MAIN",
		BORDER_FOCUSED if (focus == 0) else BORDER_UNFOCUSED,
		ih if (focus == 0) else null,
		face_box_hint_pos if (focus == 0) else Vector2i(-1, -1),
		spec.timeline_hint if (focus == 0) else "",
		has_branched, preview_on, cell_sz,
		main_s, main_x, main_y, main_a,
		goal_glow, animation_frame,
		flash_pos if (focus == 0) else Vector2i(-1, -1),
		flash_int if (focus == 0) else 0.0,
		flash_style if (focus == 0) else "cell",
		falling_main,
		branch_hint_active if (focus == 0) else false,
		show_merge_preview_hint,
		show_merge_hint,
		merge_hint_enabled,
		show_fetch_indicator,
		fetch_mode_enabled)

	# Build sub branch spec (DIV 1)
	if has_branched and controller.sub_branch != null:
		spec.sub_branch = _make_spec(
			controller.sub_branch,
			focus == 1,
			"DIV 1",
			BORDER_FOCUSED if (focus == 1) else BORDER_UNFOCUSED,
			ih if (focus == 1) else null,
			face_box_hint_pos if (focus == 1) else Vector2i(-1, -1),
			spec.timeline_hint if (focus == 1) else "",
			has_branched, preview_on, cell_sz,
			sub_s, sub_x, sub_y, sub_a,
			goal_glow, animation_frame,
			flash_pos if (focus == 1) else Vector2i(-1, -1),
			flash_int if (focus == 1) else 0.0,
			flash_style if (focus == 1) else "cell",
			falling_sub,
			branch_hint_active if (focus == 1) else false,
			show_merge_preview_hint,
			show_merge_hint,
			merge_hint_enabled,
			show_fetch_indicator,
			fetch_mode_enabled)

	return spec


static func _make_spec(
		p_state:      BranchState,
		p_focused:    bool,
		p_title:      String,
		p_border:     Color,
		p_hint,
		p_facing_box_hint_pos: Vector2i,
		p_timeline:   String,
		p_branched:   bool,
		p_preview:    bool,
		p_cell:       int,
		p_scale:      float,
		p_x:          int,
		p_y:          int,
		p_alpha:      float,
		p_goal:       int,
		p_anim:       int,
		p_flash:      Vector2i,
		p_flash_i:    float,
		p_flash_style: String,
		p_falling:    Dictionary,
		p_branch_hint_active: bool,
		p_show_merge_preview_hint: bool,
		p_show_merge_hint: bool,
		p_merge_hint_enabled: bool,
		p_show_fetch_indicator: bool,
		p_fetch_mode_enabled: bool) -> BranchViewSpec:

	var s := BranchViewSpec.new()
	s.state                  = p_state
	s.is_focused             = p_focused
	s.title                  = p_title
	s.border_color           = p_border
	s.interaction_hint       = p_hint
	s.facing_box_hint_pos    = p_facing_box_hint_pos
	s.timeline_hint          = p_timeline
	s.has_branched           = p_branched
	s.highlight_branch_point = _is_on_branch_point(p_state) and p_focused and not p_branched
	s.is_merge_preview       = p_preview
	s.cell_size              = p_cell
	s.scale                  = p_scale
	s.pos_x                  = p_x
	s.pos_y                  = p_y
	s.alpha                  = p_alpha
	s.goal_glow              = p_goal
	s.animation_frame        = p_anim
	s.flash_pos              = p_flash
	s.flash_intensity        = p_flash_i
	s.flash_style            = p_flash_style
	s.falling_progress       = p_falling
	s.branch_hint_active     = p_branch_hint_active
	s.show_merge_preview_hint = p_show_merge_preview_hint
	s.show_merge_hint        = p_show_merge_hint
	s.merge_hint_enabled     = p_merge_hint_enabled
	s.show_fetch_indicator   = p_show_fetch_indicator
	s.fetch_mode_enabled     = p_fetch_mode_enabled
	return s


static func _calc_merge_preview_positions(focus: int, progress: float) -> Array:
	# Returns [main_x, main_y, main_scale, sub_x, sub_y, sub_scale, main_alpha, sub_alpha]
	var t := _ease_in_out(clampf(progress, 0.0, 1.0))
	var offset_x := 2
	var offset_y := 2
	var main_x: int; var main_y: int; var main_s: float; var main_a: float
	var sub_x: int;  var sub_y: int;  var sub_s: float;  var sub_a: float

	if focus == 0:
		# Focused DIV0 stays centered and opaque.
		main_x = CENTER_X; main_y = CENTER_Y; main_s = FOCUS_SCALE; main_a = 1.0
		# DIV1 slides/grows from side to center+offset and fades to preview alpha.
		sub_x = int(lerpf(RIGHT_X, CENTER_X + offset_x, t))
		sub_y = int(lerpf(SIDE_Y, CENTER_Y + offset_y, t))
		sub_s = lerpf(SIDE_SCALE, FOCUS_SCALE, t)
		sub_a = lerpf(1.0, 0.7, t)
	else:
		# Focused DIV1 stays centered and opaque.
		sub_x = CENTER_X; sub_y = CENTER_Y; sub_s = FOCUS_SCALE; sub_a = 1.0
		# DIV0 slides/grows from side to center+offset and fades to preview alpha.
		main_x = int(lerpf(LEFT_X, CENTER_X + offset_x, t))
		main_y = int(lerpf(SIDE_Y, CENTER_Y + offset_y, t))
		main_s = lerpf(SIDE_SCALE, FOCUS_SCALE, t)
		main_a = lerpf(1.0, 0.7, t)

	return [main_x, main_y, main_s, sub_x, sub_y, sub_s, main_a, sub_a]


static func _calc_slide_positions(
		focus: int, progress: float, direction: int) -> Array:
	# Returns [main_x, main_y, main_scale, sub_x, sub_y, sub_scale]
	var t := _ease_in_out(progress)
	var main_x: int;  var main_y: int;  var main_s: float
	var sub_x: int;   var sub_y: int;   var sub_s: float

	if direction == 1:  # focus 0→1: DIV0 shrinks left, DIV1 grows to center
		main_x = int(CENTER_X + (LEFT_X  - CENTER_X) * t)
		main_y = int(CENTER_Y + (SIDE_Y  - CENTER_Y) * t)
		main_s = FOCUS_SCALE + (SIDE_SCALE  - FOCUS_SCALE) * t
		sub_x  = int(RIGHT_X  + (CENTER_X - RIGHT_X)  * t)
		sub_y  = int(SIDE_Y   + (CENTER_Y - SIDE_Y)   * t)
		sub_s  = SIDE_SCALE  + (FOCUS_SCALE - SIDE_SCALE)  * t
	else:               # focus 1→0: DIV0 grows to center, DIV1 shrinks right
		main_x = int(LEFT_X   + (CENTER_X - LEFT_X)   * t)
		main_y = int(SIDE_Y   + (CENTER_Y - SIDE_Y)   * t)
		main_s = SIDE_SCALE  + (FOCUS_SCALE - SIDE_SCALE)  * t
		sub_x  = int(CENTER_X + (RIGHT_X  - CENTER_X) * t)
		sub_y  = int(CENTER_Y + (SIDE_Y   - CENTER_Y) * t)
		sub_s  = FOCUS_SCALE + (SIDE_SCALE  - FOCUS_SCALE) * t

	return [main_x, main_y, main_s, sub_x, sub_y, sub_s]


static func _ease_in_out(t: float) -> float:
	if t < 0.5:
		return 2.0 * t * t
	return 1.0 - pow(-2.0 * t + 2.0, 2.0) / 2.0


static func _is_on_branch_point(state: BranchState) -> bool:
	if state == null:
		return false
	var player := state.get_player()
	if player == null:
		return false
	var tt: int = state.terrain.get(player.pos, Enums.TerrainType.FLOOR)
	return tt in Enums.BRANCH_DECREMENT


static func _filter_falling_for_branch(
		fall_progress: Dictionary, branch: BranchState, branch_id: int) -> Dictionary:
	var filtered: Dictionary = {}
	if branch == null:
		return filtered
	for raw_key in fall_progress.keys():
		var k: Array = raw_key as Array
		if k.size() < 2:
			continue
		var uid: int = -1
		var pos: Vector2i = Vector2i(-1, -1)
		if k.size() >= 3:
			var k_branch: int = int(k[0])
			if k_branch != branch_id:
				continue
			uid = int(k[1])
			pos = k[2] as Vector2i
		else:
			uid = int(k[0])
			pos = k[1] as Vector2i
		if not _branch_has_underground_entity(branch, uid, pos):
			continue
		filtered[[uid, pos]] = float(fall_progress[raw_key])
	return filtered


static func _branch_has_underground_entity(branch: BranchState, uid: int, pos: Vector2i) -> bool:
	if branch == null:
		return false
	for e in branch.entities:
		var ent := e as Entity
		if ent != null and ent.uid == uid and ent.pos == pos and ent.z == -1:
			return true
	return false
